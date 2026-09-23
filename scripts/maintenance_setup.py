"""Plan and verify the RepoStew continuous-maintenance installation.

This module deliberately does not write automation TOML files or call a
scheduler API.  ``plan`` reads the selected installation and emits payloads for
the host's ``automation_update`` tool.  ``verify`` re-reads the host files and
the Windows collector task after the host has applied those payloads.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from typing import Any, Iterable

import repostew_state
import state_store


MODEL = "gpt-6-luna"
EFFORT = "xhigh"
INSTALLATION_ID = "maintenance-installation:v2"
TASK_NAME = "RepoStew-Events-Luna"
TASK_INTERVAL_MINUTES = 5
TASK_DESCRIPTION = "RepoStew v2 lightweight event intake and Luna dispatch"

# Keep this order stable: it is the order used by the host payloads and JSON
# output, which makes a plan suitable for review and repeatable tests.
LANE_SPECS: tuple[dict[str, str], ...] = (
    {
        "key": "mail",
        "id": "repostew-mail-intake-luna",
        "name": "RepoStew · mail intake · Luna",
        "reference": "mail.md",
        "rrule": "FREQ=HOURLY;INTERVAL=1",
        "summary": "hourly authorized mailbox intake",
    },
    {
        "key": "reconcile",
        "id": "repostew-maintenance-reconciliation-luna",
        "name": "RepoStew · maintenance reconciliation · Luna",
        "reference": "reconcile.md",
        "rrule": "FREQ=HOURLY;INTERVAL=6",
        "summary": "six-hour target reconciliation",
    },
    {
        "key": "issues",
        "id": "repostew-new-issues-to-pr-luna",
        "name": "RepoStew · new issues to PR · Luna",
        "reference": "issues.md",
        "rrule": "FREQ=HOURLY;INTERVAL=6",
        "summary": "six-hour followed-issue discovery",
    },
    {
        "key": "portfolio",
        "id": "repostew-profile-and-site-luna",
        "name": "RepoStew · profile and site · Luna",
        "reference": "portfolio.md",
        "rrule": "FREQ=DAILY;BYHOUR=9;BYMINUTE=30",
        "summary": "daily portfolio maintenance at 09:30",
    },
)


def _absolute_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise argparse.ArgumentTypeError(
            f"expected an absolute path, got: {value}"
        )
    return path.resolve(strict=False)


def _path_from_record(home: Path, value: Any) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        raise ValueError(f"saved installation path is not absolute: {value!r}")
    return path.resolve()


def validate_state_home(state_home: Path) -> dict[str, Path]:
    """Validate an existing schema-2 state anchor without creating anything."""

    home = Path(state_home).expanduser()
    if not home.is_absolute():
        raise ValueError("--state-home must be an absolute path")
    home = home.resolve()
    if not home.is_dir():
        raise ValueError(f"state home does not exist: {home}")
    paths_file = home / state_store.PATHS_NAME
    try:
        record = json.loads(paths_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read state root record {paths_file}: {exc}") from exc
    if record.get("schema_version") != 2:
        raise ValueError(
            f"{paths_file} must use schema_version=2, got {record.get('schema_version')!r}"
        )
    paths = record.get("paths")
    if not isinstance(paths, dict) or paths.get("state_home") != ".":
        raise ValueError(f"{paths_file} must set paths.state_home='.'")

    try:
        roots = repostew_state.resolved_roots(home)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"invalid selected roots: {exc}") from exc
    if roots["state_home"] != home:
        raise ValueError("paths.json state_home does not resolve to --state-home")
    for role, root in roots.items():
        if not root.is_dir():
            raise ValueError(f"selected {role} root does not exist: {root}")
    database = state_store.database_path(home)
    if not database.is_file():
        raise ValueError(f"selected live SQLite state is missing: {database}")

    # A set value is an explicit binding.  A missing process-only value is
    # intentionally allowed; scheduled prompts initialize it after validation.
    expected = {
        "REPOSTEW_HOME": roots["state_home"],
        "REPOSTEW_SKILL_HOME": roots["skill_home"],
        "REPOSTEW_REPOS_HOME": roots["repos_home"],
    }
    for env_name, expected_path in expected.items():
        configured = os.environ.get(env_name)
        if not configured:
            continue
        configured_path = Path(configured).expanduser()
        if not configured_path.is_absolute():
            raise ValueError(f"{env_name} must be absolute when set")
        if configured_path.resolve() != expected_path:
            raise ValueError(
                f"{env_name} ({configured_path.resolve()}) disagrees with "
                f"selected {expected_path}"
            )
    return roots


def _load_automations(home: Path) -> list[dict[str, Any]]:
    """Read every TOML file under the explicit host automation directory."""

    root = Path(home).expanduser()
    if not root.is_absolute():
        raise ValueError("--automations-home must be an absolute path")
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"automation home does not exist: {root}")
    loaded: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/automation.toml"), key=lambda item: str(item).casefold()):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ValueError(f"cannot read automation TOML {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"automation TOML is not an object: {path}")
        loaded.append(
            {
                "path": path,
                "id": str(data.get("id") or path.parent.name),
                "data": data,
            }
        )
    return loaded


def _fold_path(value: str) -> str:
    return str(value).replace("/", "\\").rstrip("\\").casefold()


def _contains_path(prompt: str, path: Path) -> bool:
    """Match an absolute path in a prompt across Windows slash spellings."""

    folded_prompt = prompt.replace("/", "\\").casefold()
    token = _fold_path(str(path))
    # Roots must be standalone tokens, not parent paths or similarly named roots.
    return bool(re.search(r"(?<![\w\\:/.-])" + re.escape(token)
                          + r"(?=$|[\s,;)'\"`]|\.(?:\s|$))", folded_prompt))


def _prompt_binding_matches(prompt: str, roots: dict[str, Path], reference: Path) -> bool:
    return bool(
        _contains_path(prompt, reference)
        and all(_contains_path(prompt, roots[role]) for role in ("state_home", "skill_home", "repos_home"))
    )


def _lane_matches(
    spec: dict[str, str], automations: Iterable[dict[str, Any]], roots: dict[str, Path]
) -> dict[str, Any] | None:
    reference = roots["skill_home"] / "references" / "automation" / spec["reference"]
    by_id = [item for item in automations if item["id"] == spec["id"]]
    if len(by_id) > 1:
        raise ValueError(f"ambiguous automation id {spec['id']!r}")
    if by_id and not _prompt_binding_matches(str(by_id[0]["data"].get("prompt", "")), roots, reference):
        raise ValueError(
            f"automation id {spec['id']!r} exists but does not match the selected "
            f"workspace roots and {reference}"
        )

    by_prompt = [
        item
        for item in automations
        if _prompt_binding_matches(str(item["data"].get("prompt", "")), roots, reference)
    ]
    # A candidate found by ID and prompt is the same file; deduplicate by path.
    candidates: dict[Path, dict[str, Any]] = {item["path"]: item for item in by_id + by_prompt}
    if len(candidates) > 1:
        paths = ", ".join(str(item["path"]) for item in candidates.values())
        raise ValueError(
            f"ambiguous {spec['key']} automation lanes for {reference}: {paths}"
        )
    return next(iter(candidates.values()), None)


def _find_automation_by_id(automation_id: str, automations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    matches = [item for item in automations if item["id"] == automation_id]
    if len(matches) != 1:
        if not matches:
            raise ValueError(f"retired automation id {automation_id!r} was not found")
        raise ValueError(f"ambiguous retired automation id {automation_id!r}")
    return matches[0]


def _validate_retired_binding(item: dict[str, Any], roots: dict[str, Path], automation_id: str) -> None:
    if automation_id in {spec["id"] for spec in LANE_SPECS}:
        raise ValueError(f"retired automation id {automation_id!r} is a current split lane")
    prompt = str(item["data"].get("prompt", ""))
    if not _prompt_binding_matches(prompt, roots, roots["skill_home"] / "SKILL.md"):
        raise ValueError(
            f"retired automation {automation_id!r} does not bind the selected "
            "workspace roots and skill"
        )


def _discover_retired(automations: Iterable[dict[str, Any]], roots: dict[str, Path]) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for item in automations:
        data = item["data"]
        prompt = str(data.get("prompt", ""))
        name = str(data.get("name", ""))
        text = f"{name} {prompt}".casefold()
        # Legacy combined loops were heartbeat/inbox or explicitly called
        # combined.  Root binding is required so another project's old loop is
        # never paused by this installer.
        if (
            ("combined" in text or "maintenance inbox" in text or "maintenance-inbox" in text)
            and _prompt_binding_matches(
                prompt,
                roots,
                roots["skill_home"] / "SKILL.md",
            )
        ):
            candidates.append(item)
    if len(candidates) > 1:
        paths = ", ".join(str(item["path"]) for item in candidates)
        raise ValueError(f"ambiguous retired maintenance automations: {paths}")
    return candidates[0] if candidates else None


def _read_saved_record(home: Path) -> dict[str, Any] | None:
    value = state_store.load_document(home, "maintenance_batches.json", [])
    if isinstance(value, dict):
        if value.get("batch_id") == INSTALLATION_ID or value.get("record_id") == INSTALLATION_ID:
            return value
        value = value.get("records", [])
    if not isinstance(value, list):
        return None
    for item in value:
        if isinstance(item, dict) and (
            item.get("batch_id") == INSTALLATION_ID
            or item.get("record_id") == INSTALLATION_ID
        ):
            return item
    return None


def _resolve_config(
    roots: dict[str, Path],
    saved: dict[str, Any] | None,
    *,
    project_id: str | None,
    mail_account: str | None,
    mail_folder: str | None,
    portfolio_repos: list[str] | None,
    old_automation_id: str | None,
    automations: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    saved_config = saved.get("config", {}) if saved else {}
    if not isinstance(saved_config, dict):
        saved_config = {}

    def choose(value: Any, key: str) -> Any:
        return value if value not in (None, "") else saved_config.get(key)

    project = choose(project_id, "project_id")
    account = choose(mail_account, "mail_account")
    folder = choose(mail_folder, "mail_folder")
    repos = portfolio_repos if portfolio_repos else saved_config.get("portfolio_repos")
    old_id = choose(old_automation_id, "old_automation_id")
    if not project:
        # Existing split lanes carry a project binding.  This is safe to reuse
        # only when all discovered values agree.
        values: set[str] = set()
        for spec in LANE_SPECS:
            item = _lane_matches(spec, automations, roots)
            if item:
                target = item["data"].get("target") or {}
                candidate = target.get("project_id") or target.get("projectId")
                if candidate:
                    values.add(str(candidate))
        if len(values) == 1:
            project = values.pop()
    if not project:
        raise ValueError("missing --project-id (and no saved/existing project binding)")
    if not account:
        raise ValueError("missing --mail-account (and no saved mailbox binding)")
    if not folder:
        raise ValueError("missing --mail-folder (and no saved mailbox binding)")
    if not repos:
        raise ValueError("missing --portfolio-repo (repeat for each selected repository)")
    if isinstance(repos, str):
        repos = [repos]
    repos = [str(repo) for repo in repos if str(repo).strip()]
    if not repos:
        raise ValueError("at least one --portfolio-repo is required")
    if old_id:
        old_id = str(old_id)
    return {
        "project_id": str(project),
        "mail_account": str(account),
        "mail_folder": str(folder),
        "portfolio_repos": repos,
        "old_automation_id": old_id,
    }


def _bootstrap(roots: dict[str, Path]) -> str:
    return (
        f"Bootstrap: read {roots['state_home'] / 'paths.json'} (schema_version=2, "
        "paths.state_home='.') and verify the selected state, skill and repository "
        f"roots ({roots['state_home']}, {roots['skill_home']}, {roots['repos_home']}) "
        "plus REPOSTEW_* environment conflicts before work. Use the existing SQLite; "
        "never reset, import, or create another state home."
    )


def _lane_prompt(spec: dict[str, str], roots: dict[str, Path], config: dict[str, Any]) -> str:
    reference = roots["skill_home"] / "references" / "automation" / spec["reference"]
    actions = (
        "Read and queue normalized mail metadata only; no repository edits, commits, "
        "pushes, PRs, public replies or mail-state changes. "
        if spec["key"] == "mail" else
        "Only within the selected lane's permissions and standing scope, "
        "autonomously investigate, make focused fixes, test, commit/push, open "
        "compliant PRs and send evidence-backed replies; "
    )
    prompt = (
        f"Run the RepoStew {spec['key']} maintenance lane with the selected local project. "
        f"{_bootstrap(roots)} Read {roots['skill_home'] / 'SKILL.md'} and execute the "
        f"lane contract at {reference}. All model execution and delegated "
        f"leaves use {MODEL}/{EFFORT}; do not substitute. Preserve unrelated state and "
        f"report gaps instead of inventing coverage. {actions}Never merge/close issues or PRs, "
        "delete remote branches/forks, change credentials, or add permissions/dependencies. Report only "
        "new meaningful outcomes, failures, or decisions; do not run other lanes."
    )
    if spec["key"] in {"mail", "reconcile"}:
        prompt += (
            f" Mail binding: account={config['mail_account']!r}, "
            f"folder={config['mail_folder']!r}; verify access and folder identity each run."
        )
    if spec["key"] == "portfolio":
        prompt += " Portfolio repositories: " + ", ".join(config["portfolio_repos"]) + "."
    return prompt


def _canonical_payload(
    spec: dict[str, str], roots: dict[str, Path], config: dict[str, Any], status: str
) -> dict[str, Any]:
    return {
        "kind": "cron",
        "name": spec["name"],
        "prompt": _lane_prompt(spec, roots, config),
        "status": status,
        "rrule": spec["rrule"],
        "model": MODEL,
        "reasoning_effort": EFFORT,
        "execution_environment": "local",
        "target": {"type": "project", "project_id": config["project_id"]},
        "cwds": [str(roots["repos_home"])],
    }


def _merge_payload(existing: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(existing)
    for key, value in canonical.items():
        if key == "target" and isinstance(merged.get(key), dict):
            target = copy.deepcopy(merged[key])
            target.update(copy.deepcopy(value))
            merged[key] = target
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _tool_payload(payload: dict[str, Any], *, mode: str, automation_id: str | None = None) -> dict[str, Any]:
    """Translate only supported fields to a host ``automation_update`` call."""

    target = payload.get("target", {}) or {}
    result: dict[str, Any] = {
        "mode": mode,
        "destination": "local",
        "executionEnvironment": payload.get("execution_environment", "local"),
        "kind": payload.get("kind", "cron"),
        "model": payload.get("model", MODEL),
        "name": payload.get("name"),
        "prompt": payload.get("prompt"),
        "projectId": target.get("project_id") or target.get("projectId"),
        "reasoningEffort": payload.get("reasoning_effort", EFFORT),
        "rrule": payload.get("rrule"),
        "status": payload.get("status"),
    }
    notification = payload.get("notificationPolicy", payload.get("notification_policy"))
    if notification is not None:
        result["notificationPolicy"] = notification
    if automation_id:
        result["id"] = automation_id
    return {key: value for key, value in result.items() if value is not None}


def _collector_preview(roots: dict[str, Path]) -> dict[str, Any]:
    script = roots["skill_home"] / "scripts" / "register_event_task.ps1"
    return {
        "task_name": TASK_NAME,
        "script": str(script),
        "state_home": str(roots["state_home"]),
        "working_directory": str(roots["repos_home"]),
        "interval_minutes": TASK_INTERVAL_MINUTES,
        "model": MODEL,
        "reasoning_effort": EFFORT,
        "apply": False,
        "command": ["powershell", "-NoProfile", "-File", str(script), "-StateHome", str(roots["state_home"])],
    }


def build_plan(
    state_home: Path,
    automations_home: Path,
    *,
    project_id: str | None = None,
    mail_account: str | None = None,
    mail_folder: str | None = None,
    portfolio_repos: list[str] | None = None,
    old_automation_id: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, read-only host-application plan."""

    roots = validate_state_home(state_home)
    automations = _load_automations(automations_home)
    saved = _read_saved_record(roots["state_home"])
    config = _resolve_config(
        roots,
        saved,
        project_id=project_id,
        mail_account=mail_account,
        mail_folder=mail_folder,
        portfolio_repos=portfolio_repos,
        old_automation_id=old_automation_id,
        automations=automations,
    )

    lanes: list[dict[str, Any]] = []
    lane_ids: dict[str, str | None] = {}
    for spec in LANE_SPECS:
        existing = _lane_matches(spec, automations, roots)
        existing_status = str(existing["data"].get("status", "PAUSED")) if existing else "PAUSED"
        canonical = _canonical_payload(spec, roots, config, existing_status)
        if existing:
            lane_id = str(existing["id"])
            payload = _merge_payload(existing["data"], canonical)
            action = "reuse" if payload == existing["data"] else "update"
            mode = "update"
            path = str(existing["path"])
        else:
            lane_id = None
            payload = canonical
            action = "create"
            mode = "suggested_create"
            path = None
        lane_ids[spec["key"]] = lane_id
        lanes.append(
            {
                "key": spec["key"],
                "reference": str(roots["skill_home"] / "references" / "automation" / spec["reference"]),
                "automation_id": lane_id,
                "mode": mode,
                "action": action,
                "path": path,
                "payload": payload,
                "tool_payload": _tool_payload(payload, mode=mode, automation_id=lane_id),
                "preserves_existing_status": bool(existing),
            }
        )

    old = None
    if config.get("old_automation_id"):
        old = _find_automation_by_id(config["old_automation_id"], automations)
        _validate_retired_binding(old, roots, str(config["old_automation_id"]))
    else:
        old = _discover_retired(automations, roots)
        if old:
            config["old_automation_id"] = str(old["id"])
    retired: dict[str, Any] | None = None
    if old:
        old_payload = copy.deepcopy(old["data"])
        old_payload["status"] = "PAUSED"
        retired = {
            "automation_id": str(old["id"]),
            "path": str(old["path"]),
            "mode": "update",
            "action": "pause",
            "payload": old_payload,
        }

    return {
        "schema_version": 2,
        "kind": "maintenance_setup_plan",
        "record_id": INSTALLATION_ID,
        "roots": {role: str(path) for role, path in roots.items()},
        "config": config,
        "lane_ids": lane_ids,
        "lanes": lanes,
        "retired_old_automation_id": config.get("old_automation_id"),
        "retired_old_automation": retired,
        "collector_registration": _collector_preview(roots),
        "scheduler_mutations": False,
    }


def _json_from_output(output: str) -> dict[str, Any]:
    text = output.strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        # RTK may print a compact diagnostic prefix.  Accept only the final
        # JSON object; never evaluate or otherwise interpret command output.
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError(f"scheduled-task query did not return JSON: {text[:300]}")
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("scheduled-task query returned a non-object")
    return value


def query_scheduled_task(
    roots: dict[str, Path], *, rtk_path: str | None = None, task_name: str = TASK_NAME
) -> dict[str, Any]:
    """Query the native Windows task through ``rtk proxy powershell``."""

    executable = rtk_path or os.environ.get("RTK_PATH") or shutil.which("rtk")
    if not executable:
        raise RuntimeError("an existing rtk executable is required for scheduled-task verification")
    # Keep the output intentionally small and structured.  PowerShell exposes
    # MultipleInstances as enum 2 on some Windows versions; normalize that to
    # the public IgnoreNew value before returning JSON.
    ps = (
        "$ErrorActionPreference='Stop';"
        f"$t=Get-ScheduledTask -TaskName {json.dumps(task_name)};"
        "$a=@($t.Actions)[0];$g=@($t.Triggers)[0];"
        "$m=[string]$t.Settings.MultipleInstances;"
        "if($m -eq '2'){$m='IgnoreNew'};"
        "[ordered]@{task_name=$t.TaskName;description=[string]$t.Description;"
        "enabled=[bool]$t.Settings.Enabled;action_count=@($t.Actions).Count;"
        "trigger_count=@($t.Triggers).Count;"
        "state=[string]$t.State;action_execute=[string]$a.Execute;"
        "action_arguments=[string]$a.Arguments;"
        "action_working_directory=[string]$a.WorkingDirectory;"
        "interval=[string]$g.Repetition.Interval;multiple_instances=$m}"
        "|ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        [str(executable), "proxy", "powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"scheduled-task query failed: {detail[:500]}")
    return _json_from_output(completed.stdout)


def _assert_task(task: dict[str, Any], roots: dict[str, Path]) -> dict[str, Any]:
    expected_wrapper = roots["skill_home"] / "scripts" / "run_event_task.ps1"
    if task.get("task_name") != TASK_NAME:
        raise ValueError(f"scheduled task name mismatch: {task.get('task_name')!r}")
    if task.get("description") not in (None, TASK_DESCRIPTION):
        raise ValueError("collector scheduled-task description/ownership mismatch")
    if task.get("action_count") not in (None, 1) or task.get("trigger_count") not in (None, 1):
        raise ValueError("collector task must have exactly one action and trigger")
    if task.get("enabled") is not True:
        raise ValueError("collector scheduled task is not enabled")
    multiple = task.get("multiple_instances")
    if str(multiple).casefold() != "ignorenew":
        raise ValueError(f"collector task MultipleInstances must be IgnoreNew, got {multiple!r}")
    interval = str(task.get("interval", "")).upper()
    if interval not in {"PT5M", "00:05:00"}:
        raise ValueError(f"collector task interval must be five minutes, got {interval!r}")
    execute = str(task.get("action_execute", "")).strip().replace("/", "\\")
    if Path(execute).name.casefold() not in {"powershell.exe", "powershell"}:
        raise ValueError(f"collector action executable is not Windows PowerShell: {execute!r}")
    if _fold_path(str(task.get("action_working_directory", ""))) != _fold_path(str(roots["repos_home"])):
        raise ValueError("collector action working directory does not match selected repos root")
    arguments = str(task.get("action_arguments", ""))

    def exact_argument(name: str) -> str:
        match = re.search(
            rf"(?<!\S){re.escape(name)}\s+(?:\"([^\"]*)\"|(\S+))",
            arguments,
            flags=re.IGNORECASE,
        )
        if not match:
            raise ValueError(f"collector action is missing exact {name} argument")
        value = match.group(1) or match.group(2)
        if len(re.findall(rf"(?<!\S){re.escape(name)}\s+", arguments, flags=re.IGNORECASE)) != 1:
            raise ValueError(f"collector action has duplicate {name} arguments")
        return value

    wrapper_arg = exact_argument("-File")
    state_arg = exact_argument("-StateHome")
    if _fold_path(wrapper_arg) != _fold_path(str(expected_wrapper)):
        raise ValueError("collector action does not reference the selected run_event_task.ps1 exactly")
    if _fold_path(state_arg) != _fold_path(str(roots["state_home"])):
        raise ValueError("collector action does not bind the selected state home exactly")
    return {
        "task_name": TASK_NAME,
        "enabled": True,
        "multiple_instances": "IgnoreNew",
        "interval": "PT5M",
        "action_working_directory": str(roots["repos_home"]),
        "wrapper": str(expected_wrapper),
        "state_home": str(roots["state_home"]),
        "action_execute": execute,
    }


def _automation_assertions(
    automations_home: Path,
    roots: dict[str, Path],
    config: dict[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Independently reload and assert the four native lane TOMLs."""

    automations = _load_automations(automations_home)
    ids: dict[str, str] = {}
    evidence: dict[str, Any] = {}
    for spec in LANE_SPECS:
        item = _lane_matches(spec, automations, roots)
        if not item:
            raise ValueError(f"missing verified {spec['key']} automation lane")
        data = item["data"]
        ids[spec["key"]] = str(item["id"])
        expected_ref = roots["skill_home"] / "references" / "automation" / spec["reference"]
        target = data.get("target") or {}
        if str(data.get("status", "")).upper() != "ACTIVE":
            raise ValueError(f"{spec['key']} automation is not ACTIVE")
        if data.get("model") != MODEL or data.get("reasoning_effort") != EFFORT:
            raise ValueError(f"{spec['key']} automation is not pinned to {MODEL}/{EFFORT}")
        if data.get("rrule") != spec["rrule"]:
            raise ValueError(f"{spec['key']} cadence mismatch: {data.get('rrule')!r}")
        if data.get("execution_environment") != "local":
            raise ValueError(f"{spec['key']} execution environment is not local")
        if target.get("type") != "project" or str(target.get("project_id") or target.get("projectId")) != config["project_id"]:
            raise ValueError(f"{spec['key']} project binding mismatch")
        cwds = data.get("cwds")
        cwd_matches = (
            isinstance(cwds, list)
            and len(cwds) == 1
            and Path(str(cwds[0])).expanduser().resolve() == roots["repos_home"]
        )
        if not cwd_matches:
            raise ValueError(f"{spec['key']} repository root binding mismatch: {cwds!r}")
        prompt = str(data.get("prompt", ""))
        if not _prompt_binding_matches(prompt, roots, expected_ref):
            raise ValueError(f"{spec['key']} prompt reference/root binding mismatch")
        evidence[spec["key"]] = {
            "id": str(item["id"]),
            "path": str(item["path"]),
            "status": data.get("status"),
            "model": data.get("model"),
            "reasoning_effort": data.get("reasoning_effort"),
            "rrule": data.get("rrule"),
            "reference": str(expected_ref),
            "project_id": config["project_id"],
            "repos_home": str(roots["repos_home"]),
        }

    old_id = config.get("old_automation_id")
    if old_id:
        old = _find_automation_by_id(str(old_id), automations)
        if str(old["data"].get("status", "")).upper() != "PAUSED":
            raise ValueError(f"retired automation {old_id!r} is not PAUSED")
        evidence["retired_old_automation"] = {
            "id": str(old["id"]),
            "path": str(old["path"]),
            "status": old["data"].get("status"),
        }
    return ids, evidence


def verify_installation(
    state_home: Path,
    automations_home: Path,
    *,
    project_id: str | None = None,
    mail_account: str | None = None,
    mail_folder: str | None = None,
    portfolio_repos: list[str] | None = None,
    old_automation_id: str | None = None,
    rtk_path: str | None = None,
    record: bool = False,
) -> dict[str, Any]:
    """Re-read native configuration and the actual collector task."""

    roots = validate_state_home(state_home)
    saved = _read_saved_record(roots["state_home"])
    automations = _load_automations(automations_home)
    config = _resolve_config(
        roots,
        saved,
        project_id=project_id,
        mail_account=mail_account,
        mail_folder=mail_folder,
        portfolio_repos=portfolio_repos,
        old_automation_id=old_automation_id,
        automations=automations,
    )
    # Independently read the TOMLs again inside _automation_assertions; the
    # plan (or a cached parsed object) is never proof of applied state.
    lane_ids, automation_evidence = _automation_assertions(automations_home, roots, config)
    task_raw = query_scheduled_task(roots, rtk_path=rtk_path)
    task_evidence = _assert_task(task_raw, roots)
    result = {
        "schema_version": 2,
        "kind": "maintenance_installation_verification",
        "record_id": INSTALLATION_ID,
        "batch_id": INSTALLATION_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "roots": {role: str(path) for role, path in roots.items()},
        "config": config,
        "lane_ids": lane_ids,
        "retired_old_automation_id": config.get("old_automation_id"),
        "evidence": {
            "automations": automation_evidence,
            "collector_task": task_evidence,
        },
        "verified": True,
    }
    if record:
        state_store.put_record(roots["state_home"], "maintenance_batches.json", INSTALLATION_ID, result)
        result["recorded"] = True
    else:
        result["recorded"] = False
    return result


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state-home", required=True, type=_absolute_path)
    parser.add_argument("--automations-home", required=True, type=_absolute_path)
    parser.add_argument("--project-id")
    parser.add_argument("--mail-account")
    parser.add_argument("--mail-folder")
    parser.add_argument("--portfolio-repo", action="append", dest="portfolio_repos")
    parser.add_argument("--old-automation-id")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="emit a read-only host automation plan")
    _add_common(plan)
    verify = subparsers.add_parser("verify", help="verify applied automation and collector")
    _add_common(verify)
    verify.add_argument("--rtk-path")
    verify.add_argument("--record", action="store_true", help="save the compact verified installation record")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        common = {
            "state_home": args.state_home,
            "automations_home": args.automations_home,
            "project_id": args.project_id,
            "mail_account": args.mail_account,
            "mail_folder": args.mail_folder,
            "portfolio_repos": args.portfolio_repos,
            "old_automation_id": args.old_automation_id,
        }
        if args.command == "plan":
            result = build_plan(**common)
        else:
            result = verify_installation(**common, rtk_path=args.rtk_path, record=args.record)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, RuntimeError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
