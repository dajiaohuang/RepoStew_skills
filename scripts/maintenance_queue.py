"""Backend-neutral queue access over the existing maintenance_batches SQLite collection.

Queue changes are append-only rows in the same collection. No legacy task or
executor record is rewritten, and all consumers share one ordering and claim path.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

import repostew_state
import state_store


COLLECTION = "maintenance_batches"
DOCUMENT = "maintenance_batches.json"
DIRECTIONS = {"head", "tail"}
ACTIVE_WORKER_STATES = {"running", "dispatching", "claimed"}
HISTORY_BLOCKING_STATES = {
    "accepted", "blocked_missing_return", "completed", "completed_submitted", "completed_with_blockers",
    "completed_with_scope_limit", "exited_needs_outcome_verification", "needs_attention",
    "outcome_recorded", "released_awaiting_user", "awaiting_user", "skipped", "skipped_duplicate",
    "stopped_for_reconciliation", "superseded_duplicate",
    "timed_out_stopped", "timeout_no_save", "unfinalized_exit_requires_reconciliation",
    "verified", "waiting_maintainer",
}


class QueueError(RuntimeError):
    """A durable queue operation could not safely proceed."""


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _validate_home(state_home: Path) -> Path:
    home = Path(state_home).expanduser()
    if not home.is_absolute():
        raise QueueError("--state-home must be an absolute path")
    home = home.resolve()
    roots = repostew_state.resolved_roots(home)
    if roots["state_home"] != home:
        raise QueueError("selected state home disagrees with paths.json")
    for role, root in roots.items():
        if not root.is_dir():
            raise QueueError(f"selected {role} does not exist: {root}")
    database = state_store.database_path(home)
    if not database.is_file():
        raise QueueError(f"selected SQLite database does not exist: {database}")
    configured = os.environ.get("REPOSTEW_HOME")
    if configured and Path(configured).expanduser().resolve() != home:
        raise QueueError("REPOSTEW_HOME disagrees with --state-home")
    for env_name, role in (("REPOSTEW_SKILL_HOME", "skill_home"), ("REPOSTEW_REPOS_HOME", "repos_home")):
        configured = os.environ.get(env_name)
        if configured and Path(configured).expanduser().resolve() != roots[role]:
            raise QueueError(f"{env_name} disagrees with paths.json {role}")
    return home


def _rows(connection) -> list[tuple[str, int, dict[str, Any]]]:
    result = []
    for key, sort_index, payload in connection.execute(
        "SELECT key,sort_index,payload FROM records WHERE collection=? ORDER BY sort_index,key",
        (COLLECTION,),
    ):
        try:
            record = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(record, dict):
            result.append((key, sort_index, record))
    return result


def _latest(rows: Iterable[tuple[str, int, dict[str, Any]]]) -> dict[str, tuple[str, int, dict[str, Any]]]:
    latest: dict[str, tuple[str, int, dict[str, Any]]] = {}
    for row in rows:
        key, sort_index, record = row
        work_item_id = _text(record.get("work_item_id"))
        if not work_item_id:
            continue
        previous = latest.get(work_item_id)
        if previous is None or (sort_index, key) > (previous[1], previous[0]):
            latest[work_item_id] = row
    return latest


def _is_queued(record: dict[str, Any]) -> bool:
    if record.get("worker_status") != "queued" or record.get("status") not in (None, "queued"):
        return False
    if record.get("paused") is True or record.get("queue_paused") is True:
        return False
    return not any("paused" in _text(record.get(field)).casefold()
                   for field in ("status", "worker_status", "phase", "execution_state"))


def _active_repositories(latest: dict[str, tuple[str, int, dict[str, Any]]]) -> set[str]:
    return {
        _text(record.get("owner_repo")).casefold()
        for _, _, record in latest.values()
        if _text(record.get("owner_repo"))
        and _text(record.get("worker_status")).casefold() in ACTIVE_WORKER_STATES
    }


def _parse_time(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _issue_window(record: dict[str, Any]) -> tuple[datetime, datetime] | None:
    window = record.get("issue_window")
    source = record.get("source")
    if not isinstance(window, dict) or not isinstance(source, dict):
        return None
    if window.get("pagination") != "all_pages_required":
        return None
    start, end = _parse_time(window.get("since")), _parse_time(window.get("until"))
    if start is None or end is None or end <= start:
        return None
    if not _text(source.get("kind")) or _parse_time(source.get("captured_at")) is None:
        return None
    return start, end


def _handled(record: dict[str, Any]) -> bool:
    status = _text(record.get("worker_status")).casefold()
    record_status = _text(record.get("status")).casefold()
    return status in HISTORY_BLOCKING_STATES or record_status in HISTORY_BLOCKING_STATES


def _has_new_issue_window(candidate: dict[str, Any], previous: list[dict[str, Any]]) -> bool:
    current_window = _issue_window(candidate)
    if current_window is None:
        return False
    current_start, current_end = current_window
    previous_ends = []
    for record in previous:
        window = _issue_window(record)
        if window:
            previous_ends.append(window[1])
            continue
        for field in ("completed_at", "accepted_at", "finished_at", "current_live_verified_at", "created_at"):
            parsed = _parse_time(record.get(field))
            if parsed:
                previous_ends.append(parsed)
                break
    if previous_ends and current_end <= max(previous_ends):
        return False
    # An explicitly scoped, fully paginated source window is required. If a prior
    # record has no timestamp, the structured window still provides a new scope.
    return current_start < current_end


def _explicit_rework_or_retry(candidate: dict[str, Any], previous: list[dict[str, Any]]) -> bool:
    if _has_new_issue_window(candidate, previous):
        return True
    parent_batch = _text(candidate.get("parent_rework_batch"))
    parent_packet = _text(candidate.get("parent_rework_packet"))
    try:
        rework_pass = int(candidate.get("rework_pass", 0))
    except (TypeError, ValueError):
        rework_pass = 0
    if (candidate.get("rework_of_previous") is True and rework_pass > 0
            and parent_batch and parent_packet and _text(candidate.get("supersession_reason"))):
        if any(record.get("batch_id") == parent_batch
               and record.get("work_item_id") == parent_packet for record in previous):
            return True

    retry = candidate.get("retry")
    retry_authorized = candidate.get("retry_authorized") is True
    retry_trigger = _text(candidate.get("retry_trigger"))
    retry_reason = _text(candidate.get("retry_reason"))
    retry_of = _text(candidate.get("retry_of_packet") or candidate.get("retry_of"))
    if isinstance(retry, dict):
        retry_authorized = retry_authorized or retry.get("authorized") is True
        retry_trigger = retry_trigger or _text(retry.get("trigger"))
        retry_reason = retry_reason or _text(retry.get("reason"))
        retry_of = retry_of or _text(retry.get("work_item_id") or retry.get("packet_id"))
    return bool(retry_authorized and retry_trigger and retry_reason and retry_of
                and any(record.get("work_item_id") == retry_of for record in previous))


def _select(
    rows: list[tuple[str, int, dict[str, Any]]],
    *,
    direction: str,
    limit: int,
    eligible_backends: Iterable[str] | None = None,
    eligible_repos: Iterable[str] | None = None,
    eligible_batch_id: str | None = None,
) -> list[tuple[str, int, dict[str, Any]]]:
    if direction not in DIRECTIONS:
        raise ValueError("direction must be 'head' or 'tail'")
    if limit < 1:
        raise ValueError("limit must be positive")
    backends = ({_text(value).casefold() for value in eligible_backends if _text(value)}
                if eligible_backends is not None else None)
    repositories = ({_text(value).casefold() for value in eligible_repos if _text(value)}
                    if eligible_repos is not None else None)
    latest = _latest(rows)
    active_repos = _active_repositories(latest)
    by_repo: dict[str, list[tuple[str, int, dict[str, Any]]]] = {}
    for row in latest.values():
        repo = _text(row[2].get("owner_repo")).casefold()
        if repo:
            by_repo.setdefault(repo, []).append(row)
    candidates = []
    for key, sort_index, record in latest.values():
        repo = _text(record.get("owner_repo")).casefold()
        backend = _text(record.get("backend")).casefold()
        if not _is_queued(record) or not repo:
            continue
        if backends is not None and backend not in backends:
            continue
        if repositories is not None and repo not in repositories:
            continue
        if repo in active_repos:
            continue
        if eligible_batch_id is not None and _text(record.get("batch_id")) != eligible_batch_id:
            continue
        repo_rows = by_repo.get(repo, [])
        queued_rows = [row for row in repo_rows if _is_queued(row[2])]
        # Resolve duplicate queued records across all batches before applying the
        # requested head/tail direction. The newest queued source is canonical.
        if queued_rows and max(queued_rows, key=lambda row: (row[1], row[0]))[0] != key:
            continue
        previous = [row[2] for row in repo_rows if row[0] != key and _handled(row[2])]
        if previous and not _explicit_rework_or_retry(record, previous):
            continue
        candidates.append((key, sort_index, record))
    candidates.sort(key=lambda row: (row[1], row[0]), reverse=(direction == "tail"))
    return candidates[:limit]


def list_items(
    state_home: Path,
    *,
    direction: str = "head",
    limit: int = 100,
    eligible_backends: Iterable[str] | None = None,
    eligible_repos: Iterable[str] | None = None,
    eligible_batch_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return one latest queued row per work item in stable head/tail order."""
    home = _validate_home(Path(state_home))
    with state_store.connect(home) as connection:
        rows = _rows(connection)
    selected = _select(rows, direction=direction, limit=limit,
                       eligible_backends=eligible_backends, eligible_repos=eligible_repos,
                       eligible_batch_id=eligible_batch_id)
    return [
        {**deepcopy(record), "_queue": {"record_key": key, "sort_index": sort_index,
                                         "direction": direction}}
        for key, sort_index, record in selected
    ]


def _append(connection, record: dict[str, Any], *, prefix: str) -> tuple[str, int]:
    key = f"{prefix}:{uuid.uuid4().hex}"
    sort_index = connection.execute(
        "SELECT COALESCE(MAX(sort_index),-1)+1 FROM records WHERE collection=?", (COLLECTION,)
    ).fetchone()[0]
    connection.execute(
        "INSERT INTO records(collection,key,sort_index,payload,updated_at) VALUES(?,?,?,?,?)",
        (COLLECTION, key, sort_index, state_store.compact(record), state_store.now_iso()),
    )
    return key, sort_index


def append_candidates(state_home: Path, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Atomically append new repository candidates, deduplicating across the shared queue.

    This is a root-only intake operation. The immediate transaction makes two
    independent queue managers contend on the same repository identity rather
    than racing through a read-then-write check.
    """
    if not isinstance(candidates, list):
        raise ValueError("candidate input must be a JSON array")
    home = _validate_home(Path(state_home))

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate {index} must be an object")
        required = ("batch_id", "work_item_id", "packet_id", "owner_repo", "backend",
                    "client", "provider", "model", "mode", "phase", "source",
                    "contract_path", "evidence_path")
        missing = [field for field in required if not _text(candidate.get(field))]
        if missing:
            raise ValueError(f"candidate {index} missing fields: {', '.join(missing)}")
        if candidate.get("role") != "repostew-repository":
            raise ValueError(f"candidate {index} role must be repostew-repository")
        if candidate.get("worker_status") != "queued" or not _is_queued(candidate):
            raise ValueError(f"candidate {index} must be an unpaused queued row")
        owner_repo = _text(candidate.get("owner_repo"))
        owner, separator, repo = owner_repo.partition("/")
        if not separator or not owner or not repo or "/" in repo or any(c.isspace() for c in owner_repo):
            raise ValueError(f"candidate {index} owner_repo must be canonical owner/repository")
        source = candidate.get("source")
        if not isinstance(source, dict) or not _text(source.get("kind")):
            raise ValueError(f"candidate {index} requires source.kind")
        if _parse_time(source.get("captured_at")) is None:
            raise ValueError(f"candidate {index} requires an ISO-8601 source.captured_at")

    added: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    with state_store.connect(home) as connection:
        connection.execute("BEGIN IMMEDIATE")
        rows = _rows(connection)
        existing_repos = {
            _text(record.get("owner_repo")).casefold()
            for _, _, record in rows if _text(record.get("owner_repo"))
        }
        existing_work_items = {
            _text(record.get("work_item_id"))
            for _, _, record in rows if _text(record.get("work_item_id"))
        }
        for candidate in candidates:
            owner_repo = _text(candidate["owner_repo"])
            work_item_id = _text(candidate["work_item_id"])
            folded_repo = owner_repo.casefold()
            if folded_repo in existing_repos:
                skipped.append({"owner_repo": owner_repo, "work_item_id": work_item_id,
                                "reason": "repository_already_in_shared_queue"})
                continue
            if work_item_id in existing_work_items:
                skipped.append({"owner_repo": owner_repo, "work_item_id": work_item_id,
                                "reason": "work_item_id_already_in_shared_queue"})
                continue
            record = deepcopy(candidate)
            key, sort_index = _append(connection, record, prefix="maintenance-queue-enqueue")
            existing_repos.add(folded_repo)
            existing_work_items.add(work_item_id)
            added.append({"owner_repo": owner_repo, "work_item_id": work_item_id,
                          "record_key": key, "sort_index": sort_index})

    return {"added": added, "skipped": skipped,
            "added_count": len(added), "skipped_count": len(skipped)}


def claim_item(
    state_home: Path,
    work_item_id: str,
    owner: str,
    *,
    expected_record_key: str,
    direction: str,
    eligible_backends: Iterable[str] | None = None,
    eligible_batch_id: str | None = None,
    execution_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Atomically append the root's claim to maintenance_batches.

    The latest row is rechecked under BEGIN IMMEDIATE, so parallel native or CLI
    consumers cannot claim the same work item or another mutation for its repo.
    """
    home = _validate_home(Path(state_home))
    work_item_id = _text(work_item_id)
    owner = _text(owner)
    expected_record_key = _text(expected_record_key)
    if not work_item_id or not owner or not expected_record_key:
        raise QueueError("work item, root owner and selected record key are required")
    if direction not in DIRECTIONS:
        raise ValueError("direction must be 'head' or 'tail'")
    backends = ({_text(value).casefold() for value in eligible_backends if _text(value)}
                if eligible_backends is not None else None)
    provenance = execution_provenance or {}
    if not isinstance(provenance, dict) or any(not _text(key) for key in provenance):
        raise ValueError("execution provenance must be an object with named fields")
    generation = uuid.uuid4().hex
    claimed_at = datetime.now(timezone.utc).isoformat()

    with state_store.connect(home) as connection:
        connection.execute("BEGIN IMMEDIATE")
        rows = _rows(connection)
        current = _latest(rows).get(work_item_id)
        if current is None:
            raise QueueError("work item no longer exists in maintenance_batches")
        key, sort_index, record = current
        if key != expected_record_key:
            raise QueueError("work item changed after queue selection; refresh the queue")
        if not _is_queued(record):
            raise QueueError("work item is no longer queued; refresh the queue")
        if backends is not None and _text(record.get("backend")).casefold() not in backends:
            raise QueueError("work item is not eligible for this executor")
        if eligible_batch_id is not None and _text(record.get("batch_id")) != eligible_batch_id:
            raise QueueError("work item is outside the selected batch")
        repo = _text(record.get("owner_repo")).casefold()
        if not repo:
            raise QueueError("work item has no canonical owner_repo")
        if repo in _active_repositories(_latest(rows)):
            raise QueueError("repository already has an active mutation claim")
        eligible = _select(rows, direction=direction, limit=len(rows) + 1,
                           eligible_backends=backends, eligible_batch_id=eligible_batch_id)
        if not any(candidate_key == key and candidate["work_item_id"] == work_item_id
                   for candidate_key, _, candidate in eligible):
            raise QueueError("repository history or duplicate queue item makes this work ineligible")

        claimed = deepcopy(record)
        claimed["status"] = "running"
        claimed["worker_status"] = "running"
        claimed["queue_claim"] = {
            "owner": owner,
            "generation": generation,
            "direction": direction,
            "claimed_at": claimed_at,
            "source_record_key": key,
            "source_sort_index": sort_index,
        }
        if provenance:
            attempts = list(claimed.get("execution_attempts") or [])
            attempts.append({"claim_generation": generation, **deepcopy(provenance)})
            claimed["execution_attempts"] = attempts
        claim_key, claim_index = _append(connection, claimed, prefix="maintenance-queue-claim")

    return {**claimed, "_queue": {"record_key": claim_key, "sort_index": claim_index,
                                  "direction": direction}}


def update_claim(
    state_home: Path,
    work_item_id: str,
    owner: str,
    generation: str,
    *,
    worker_status: str,
    phase: str | None = None,
    updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append a root-owned lifecycle update for the current claim."""
    home = _validate_home(Path(state_home))
    work_item_id, owner, generation = map(_text, (work_item_id, owner, generation))
    worker_status = _text(worker_status)
    if not work_item_id or not owner or not generation or not worker_status:
        raise QueueError("work item, owner, generation and worker_status are required")
    if worker_status == "queued":
        raise QueueError("use requeue_claim with stopped-writer and remote-reconciliation proof")
    updates = updates or {}
    if not isinstance(updates, dict):
        raise ValueError("updates must be an object")
    reserved = {"batch_id", "work_item_id", "status", "worker_status", "queue_claim"}
    if reserved.intersection(updates):
        raise ValueError("updates cannot replace queue identity, status or claim fields")

    with state_store.connect(home) as connection:
        connection.execute("BEGIN IMMEDIATE")
        rows = _rows(connection)
        current = _latest(rows).get(work_item_id)
        if current is None:
            raise QueueError("work item no longer exists in maintenance_batches")
        _, _, record = current
        claim = record.get("queue_claim") or {}
        if claim.get("owner") != owner or claim.get("generation") != generation:
            raise QueueError("claim owner or generation changed")
        if claim.get("released_at"):
            raise QueueError("claim was already released")
        updated = deepcopy(record)
        updated["status"] = worker_status
        updated["worker_status"] = worker_status
        if phase is not None:
            updated["phase"] = phase
        updated.update(deepcopy(updates))
        updated["queue_claim"] = {**claim, "updated_at": datetime.now(timezone.utc).isoformat()}
        key, sort_index = _append(connection, updated, prefix="maintenance-queue-update")
    return {**updated, "_queue": {"record_key": key, "sort_index": sort_index,
                                 "direction": claim.get("direction")}}


def requeue_claim(
    state_home: Path,
    work_item_id: str,
    owner: str,
    generation: str,
    *,
    reason: str,
    stopped_writer: str,
    remote_reconciliation: str,
) -> dict[str, Any]:
    """Append a retryable queue row only after writer and remote effects are reconciled."""
    proof = {"reason": _text(reason), "stopped_writer": _text(stopped_writer),
             "remote_reconciliation": _text(remote_reconciliation)}
    if not all(proof.values()):
        raise QueueError("requeue requires reason, stopped-writer proof and remote reconciliation")
    home = _validate_home(Path(state_home))
    work_item_id, owner, generation = map(_text, (work_item_id, owner, generation))
    with state_store.connect(home) as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = _latest(_rows(connection)).get(work_item_id)
        if current is None:
            raise QueueError("work item is not an active latest row")
        _, _, record = current
        claim = record.get("queue_claim") or {}
        if claim.get("owner") != owner or claim.get("generation") != generation:
            raise QueueError("claim owner or generation changed")
        if _text(record.get("worker_status")).casefold() not in ACTIVE_WORKER_STATES:
            raise QueueError("only an active claim can be requeued")
        updated = deepcopy(record)
        updated["status"] = "queued"
        updated["worker_status"] = "queued"
        updated["queue_requeue_proof"] = proof
        updated["queue_claim"] = {**claim, "released_at": datetime.now(timezone.utc).isoformat()}
        key, sort_index = _append(connection, updated, prefix="maintenance-queue-requeue")
    return {**updated, "_queue": {"record_key": key, "sort_index": sort_index,
                                 "direction": claim.get("direction")}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-home", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="list deduplicated queued work")
    list_parser.add_argument("--direction", choices=sorted(DIRECTIONS), default="head")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.add_argument("--eligible-backend", action="append")
    list_parser.add_argument("--eligible-repo", action="append")
    list_parser.add_argument("--eligible-batch")

    append_parser = sub.add_parser("append", help="root-only atomic append of new repository candidates")
    append_parser.add_argument("--records-file", required=True, type=Path,
                               help="JSON array of fully verified candidate rows")

    claim_parser = sub.add_parser("claim", help="atomically claim one selected work item")
    claim_parser.add_argument("--work-item-id", required=True)
    claim_parser.add_argument("--record-key", required=True)
    claim_parser.add_argument("--owner", required=True, help="root identity")
    claim_parser.add_argument("--direction", choices=sorted(DIRECTIONS), required=True)
    claim_parser.add_argument("--eligible-backend", action="append")
    claim_parser.add_argument("--eligible-batch")
    claim_parser.add_argument("--execution-provenance", help="JSON object for this actual attempt")

    update_parser = sub.add_parser("update", help="append a root-owned claim status update")
    update_parser.add_argument("--work-item-id", required=True)
    update_parser.add_argument("--owner", required=True)
    update_parser.add_argument("--generation", required=True)
    update_parser.add_argument("--worker-status", required=True)
    update_parser.add_argument("--phase")
    update_parser.add_argument("--updates", help="JSON object of factual provenance fields")

    requeue_parser = sub.add_parser("requeue", help="requeue only after reconciliation")
    requeue_parser.add_argument("--work-item-id", required=True)
    requeue_parser.add_argument("--owner", required=True)
    requeue_parser.add_argument("--generation", required=True)
    requeue_parser.add_argument("--reason", required=True)
    requeue_parser.add_argument("--stopped-writer", required=True)
    requeue_parser.add_argument("--remote-reconciliation", required=True)

    args = parser.parse_args(argv)
    try:
        home = _validate_home(args.state_home)
        if args.command == "list":
            result = list_items(home, direction=args.direction, limit=args.limit,
                                eligible_backends=args.eligible_backend,
                                eligible_repos=args.eligible_repo,
                                eligible_batch_id=args.eligible_batch)
        elif args.command == "append":
            candidates = json.loads(args.records_file.read_text(encoding="utf-8"))
            result = append_candidates(home, candidates)
        elif args.command == "claim":
            provenance = json.loads(args.execution_provenance) if args.execution_provenance else None
            result = claim_item(
                home, args.work_item_id, args.owner, expected_record_key=args.record_key,
                direction=args.direction, eligible_backends=args.eligible_backend,
                eligible_batch_id=args.eligible_batch,
                execution_provenance=provenance,
            )
        elif args.command == "update":
            updates = json.loads(args.updates) if args.updates else None
            result = update_claim(home, args.work_item_id, args.owner, args.generation,
                                  worker_status=args.worker_status, phase=args.phase, updates=updates)
        else:
            result = requeue_claim(home, args.work_item_id, args.owner, args.generation,
                                   reason=args.reason, stopped_writer=args.stopped_writer,
                                   remote_reconciliation=args.remote_reconciliation)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (QueueError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
