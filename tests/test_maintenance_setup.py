import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import maintenance_setup
import repostew_state
import state_store


class MaintenanceSetupTests(unittest.TestCase):
    def test_path_binding_rejects_prefix_collisions(self):
        path = Path("C:/selected/state")
        self.assertTrue(maintenance_setup._contains_path("roots (C:/selected/state,)", path))
        for value in ("C:/selected/state-evil", "C:/selected/state/child", "XC:/selected/state"):
            self.assertFalse(maintenance_setup._contains_path(value, path), value)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.state = root / "state"
        self.skill = root / "skill"
        self.repos = root / "repos"
        self.automations = root / "automations"
        for path in (self.state, self.skill, self.repos, self.automations):
            path.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("skill", encoding="utf-8")
        (self.skill / "references" / "automation").mkdir(parents=True)
        (self.skill / "references" / "maintenance-initialization.md").write_text(
            "bootstrap", encoding="utf-8"
        )
        for spec in maintenance_setup.LANE_SPECS:
            (self.skill / "references" / "automation" / spec["reference"]).write_text(
                spec["key"], encoding="utf-8"
            )
        (self.state / "paths.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "paths": {
                        "state_home": ".",
                        "skill_home": "../skill",
                        "repos_home": "../repos",
                    },
                }
            ),
            encoding="utf-8",
        )
        with state_store.connect(self.state, create=True):
            pass
        self.config = {
            "project_id": "project-1",
            "mail_account": "mail@example.test",
            "mail_folder": "folder-42",
            "portfolio_repos": ["owner/profile", "owner/site"],
        }

    def tearDown(self):
        self.temp.cleanup()

    def write_automation(self, automation_id, data):
        directory = self.automations / automation_id
        directory.mkdir(parents=True, exist_ok=True)
        lines = [
            f'version = 1',
            f'id = {json.dumps(automation_id)}',
            f'kind = {json.dumps(data.get("kind", "cron"))}',
            f'name = {json.dumps(data.get("name", automation_id))}',
            f'prompt = {json.dumps(data.get("prompt", ""))}',
            f'status = {json.dumps(data.get("status", "ACTIVE"))}',
            f'rrule = {json.dumps(data.get("rrule", "FREQ=HOURLY;INTERVAL=1"))}',
            f'model = {json.dumps(data.get("model", maintenance_setup.MODEL))}',
            f'reasoning_effort = {json.dumps(data.get("reasoning_effort", maintenance_setup.EFFORT))}',
            f'execution_environment = "local"',
            f'cwds = [{json.dumps(str(self.repos.resolve()))}]',
            'target = { type = "project", project_id = "project-1" }',
        ]
        if "notificationPolicy" in data:
            lines.append(f'notificationPolicy = {json.dumps(data["notificationPolicy"])}')
        (directory / "automation.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def prompt_for(self, spec):
        reference = self.skill / "references" / "automation" / spec["reference"]
        roots = repostew_state.resolved_roots(self.state)
        return " ".join(
            [
                str(roots["state_home"]),
                str(roots["skill_home"]),
                str(roots["repos_home"]),
                str(reference.resolve()),
            ]
        )

    def write_split_and_old(self, *, statuses=None):
        statuses = statuses or {}
        for spec in maintenance_setup.LANE_SPECS:
            self.write_automation(
                spec["id"],
                {
                    "name": spec["name"],
                    "prompt": self.prompt_for(spec),
                    "status": statuses.get(spec["key"], "ACTIVE"),
                    "rrule": spec["rrule"],
                    "notificationPolicy": "failed_runs_only",
                },
            )
        self.write_automation(
            "legacy-combined",
            {
                "name": "RepoStew maintenance inbox",
                "prompt": " ".join(
                    [
                        str(repostew_state.resolved_roots(self.state)["state_home"]),
                        str(repostew_state.resolved_roots(self.state)["skill_home"]),
                        str(repostew_state.resolved_roots(self.state)["repos_home"]),
                        str((self.skill / "SKILL.md").resolve()),
                    ]
                ),
                "status": "PAUSED",
                "kind": "heartbeat",
            },
        )

    def plan(self, **kwargs):
        values = dict(self.config)
        values.update(kwargs)
        values["state_home"] = self.state
        values["automations_home"] = self.automations
        return maintenance_setup.build_plan(**values)

    def test_plan_missing_lanes_is_paused_host_payload_and_read_only(self):
        result = self.plan(old_automation_id=None)
        self.assertTrue(result["scheduler_mutations"] is False)
        self.assertEqual(
            [lane["mode"] for lane in result["lanes"]],
            ["suggested_create"] * 4,
        )
        self.assertEqual([lane["payload"]["status"] for lane in result["lanes"]], ["PAUSED"] * 4)
        self.assertFalse((self.automations / "repostew-mail-intake-luna").exists())
        self.assertIn(str((self.skill / "references" / "automation" / "mail.md").resolve()), result["lanes"][0]["payload"]["prompt"])
        self.assertIn("mail@example.test", result["lanes"][0]["payload"]["prompt"])
        self.assertNotIn("autonomously investigate", result["lanes"][0]["payload"]["prompt"])
        self.assertIn("no repository edits", result["lanes"][0]["payload"]["prompt"])

    def test_plan_reuses_and_preserves_existing_fields_and_notification_policy(self):
        self.write_split_and_old()
        result = self.plan(old_automation_id="legacy-combined")
        self.assertEqual(
            {lane["key"]: lane["automation_id"] for lane in result["lanes"]},
            {spec["key"]: spec["id"] for spec in maintenance_setup.LANE_SPECS},
        )
        lane = result["lanes"][0]
        self.assertEqual(lane["mode"], "update")
        self.assertEqual(lane["payload"]["notificationPolicy"], "failed_runs_only")
        self.assertEqual(lane["payload"]["status"], "ACTIVE")
        self.assertEqual(result["retired_old_automation_id"], "legacy-combined")
        self.assertEqual(result["retired_old_automation"]["payload"]["status"], "PAUSED")
        # Planning never rewrites the TOML.
        self.assertIn('notificationPolicy = "failed_runs_only"', (self.automations / maintenance_setup.LANE_SPECS[0]["id"] / "automation.toml").read_text(encoding="utf-8"))

    def test_matching_plan_needs_no_host_writes(self):
        initial = self.plan(old_automation_id=None)
        saved = [
            {"id": spec["id"], "path": self.automations / spec["id"] / "automation.toml",
             "data": lane["payload"]}
            for spec, lane in zip(maintenance_setup.LANE_SPECS, initial["lanes"])
        ]
        with patch.object(maintenance_setup, "_load_automations", return_value=saved):
            repeated = self.plan(old_automation_id=None)
        self.assertEqual([lane["action"] for lane in repeated["lanes"]], ["reuse"] * 4)

    def test_ambiguous_reference_fails_closed(self):
        spec = maintenance_setup.LANE_SPECS[0]
        prompt = self.prompt_for(spec)
        self.write_automation("one", {"prompt": prompt})
        self.write_automation("two", {"prompt": prompt})
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.plan()

    def test_state_environment_conflict_fails_without_mutation(self):
        with patch.dict(os.environ, {"REPOSTEW_REPOS_HOME": str(self.skill)}, clear=False):
            with self.assertRaisesRegex(ValueError, "REPOSTEW_REPOS_HOME"):
                maintenance_setup.validate_state_home(self.state)

    def test_verify_rereads_toml_task_and_records_compact_installation(self):
        self.write_split_and_old()
        task = {
            "task_name": maintenance_setup.TASK_NAME,
            "description": maintenance_setup.TASK_DESCRIPTION,
            "enabled": True,
            "action_count": 1,
            "trigger_count": 1,
            "action_execute": "powershell.exe",
            "multiple_instances": "IgnoreNew",
            "interval": "PT5M",
            "action_working_directory": str(self.repos.resolve()),
            "action_arguments": f'-File "{(self.skill / "scripts" / "run_event_task.ps1").resolve()}" -StateHome "{self.state.resolve()}"',
        }
        with patch.object(maintenance_setup, "query_scheduled_task", return_value=task):
            result = maintenance_setup.verify_installation(
                self.state,
                self.automations,
                **self.config,
                old_automation_id="legacy-combined",
                record=True,
            )
        self.assertTrue(result["verified"])
        self.assertTrue(result["recorded"])
        saved = state_store.load_document(self.state, "maintenance_batches.json", [])
        self.assertEqual(saved[0]["batch_id"], maintenance_setup.INSTALLATION_ID)
        self.assertEqual(saved[0]["lane_ids"]["mail"], "repostew-mail-intake-luna")
        self.assertNotIn("prompt", json.dumps(saved))
        reused = maintenance_setup.build_plan(self.state, self.automations)
        self.assertEqual(reused["config"]["project_id"], "project-1")
        self.assertEqual(reused["retired_old_automation_id"], "legacy-combined")

    def test_state_without_existing_sqlite_is_rejected(self):
        database = self.state / "repostew.sqlite"
        database.unlink()
        with self.assertRaisesRegex(ValueError, "SQLite"):
            maintenance_setup.validate_state_home(self.state)

    def test_collector_rejects_wrong_executable_and_path_prefix(self):
        task = {
            "task_name": maintenance_setup.TASK_NAME,
            "description": maintenance_setup.TASK_DESCRIPTION,
            "enabled": True,
            "action_count": 1,
            "trigger_count": 1,
            "action_execute": "evil-powershell.exe",
            "multiple_instances": "IgnoreNew",
            "interval": "PT5M",
            "action_working_directory": str(self.repos.resolve()),
            "action_arguments": f'-File "{(self.skill / "scripts" / "run_event_task.ps1").resolve()}-evil" -StateHome "{self.state.resolve()}"',
        }
        with self.assertRaisesRegex(ValueError, "executable"):
            maintenance_setup._assert_task(task, repostew_state.resolved_roots(self.state))


if __name__ == "__main__":
    unittest.main()
