"""Durable, event-driven RepoStew intake and action queue.

This module intentionally owns only its event tables.  The shared notification
collection remains the compact, source-neutral delivery ledger used by
``pr_tracker.py``; event targets are a coalesced routing/action view on top of
that ledger.  No notification body, attachment, or API export is persisted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlparse

import repostew_state
import state_store


GITHUB_SOURCE = "github-v2"
GITHUB_NOTIFICATION_SOURCE = "github"
DEFAULT_POLL_SECONDS = 300
INITIAL_LOOKBACK_DAYS = 7
OVERLAP_DAYS = 1
TARGET_STATES = {
    "queued",
    "waiting_maintainer",
    "awaiting_user",
    "retryable_failure",
    "done",
}


class QueueError(RuntimeError):
    """A safe, user-actionable queue error."""


class CollectionError(QueueError):
    """The source batch was incomplete or malformed and cannot be checkpointed."""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def parse_time(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be a non-empty ISO-8601 string")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _nonempty(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def validate_bootstrap(state_home: Path) -> Path:
    """Validate the selected state anchor before any stateful operation.

    The queue deliberately refuses to create a new installation or database.
    A caller must point it at the existing paths.json/schema-2 anchor and its
    existing ``repostew.sqlite``.
    """

    home = Path(state_home)
    if not home.is_absolute():
        raise QueueError("--state-home must be an absolute path")
    home = home.resolve()
    paths_file = home / state_store.PATHS_NAME
    if not paths_file.is_file():
        raise QueueError(f"missing selected root record: {paths_file}")
    try:
        record = json.loads(paths_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise QueueError(f"cannot read selected root record {paths_file}: {error}") from error
    if record.get("schema_version") != 2:
        raise QueueError("paths.json schema_version must be 2")
    paths = record.get("paths")
    if not isinstance(paths, dict) or set(("skill_home", "state_home", "repos_home")) - set(paths):
        raise QueueError("paths.json must contain skill_home, state_home and repos_home")
    roots = repostew_state.resolved_roots(home)
    if roots["state_home"] != home:
        raise QueueError("paths.json state_home must resolve to --state-home")
    for role, root in roots.items():
        if not root.is_dir():
            raise QueueError(f"selected {role} does not exist: {root}")
    database = state_store.database_path(home)
    if not database.is_file():
        raise QueueError(f"selected SQLite database does not exist: {database}")
    env_home = os.environ.get("REPOSTEW_HOME")
    if env_home and Path(env_home).expanduser().resolve() != home:
        raise QueueError("REPOSTEW_HOME disagrees with --state-home")
    for env_name, role in (("REPOSTEW_SKILL_HOME", "skill_home"), ("REPOSTEW_REPOS_HOME", "repos_home")):
        configured = os.environ.get(env_name)
        if configured and Path(configured).expanduser().resolve() != roots[role]:
            raise QueueError(f"{env_name} disagrees with paths.json {role}")
    return home


def _schema(connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS event_targets (
            target_key TEXT PRIMARY KEY,
            target_type TEXT NOT NULL,
            repo TEXT,
            number INTEGER,
            identity_json TEXT NOT NULL,
            state TEXT NOT NULL,
            revision_hash TEXT NOT NULL,
            revision_updated_at TEXT,
            source_keys TEXT NOT NULL,
            next_check_at TEXT NOT NULL,
            claim_owner TEXT,
            claim_generation TEXT,
            claim_revision_hash TEXT,
            claim_acquired_at TEXT,
            snapshot_coverage TEXT,
            snapshot_receipt TEXT,
            head TEXT,
            outcome TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS event_targets_due
            ON event_targets(state, next_check_at, target_key);
        CREATE TABLE IF NOT EXISTS event_cursors (
            source TEXT PRIMARY KEY,
            intake_checkpoint TEXT,
            handled_checkpoint TEXT,
            last_batch_id TEXT,
            last_batch_started_at TEXT,
            last_poll_seconds INTEGER,
            next_poll_at TEXT,
            last_error TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_batches (
            batch_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            batch_started_at TEXT NOT NULL,
            since TEXT NOT NULL,
            cutoff TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            delivery_count INTEGER NOT NULL,
            complete INTEGER NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_revisions (
            target_key TEXT NOT NULL,
            revision_hash TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            source_key TEXT NOT NULL,
            PRIMARY KEY(target_key, revision_hash)
        );
        """
    )
    # The queue may be upgraded after a scheduler has already created its
    # tables.  Keep this additive and local; never rebuild or reset state.
    columns = {row[1] for row in connection.execute("PRAGMA table_info(event_cursors)")}
    if "next_poll_at" not in columns:
        connection.execute("ALTER TABLE event_cursors ADD COLUMN next_poll_at TEXT")


def _connect(home: Path):
    connection = state_store.connect(home, create=False)
    return connection


def _cursor(connection, source: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT source,intake_checkpoint,handled_checkpoint,last_batch_id,last_batch_started_at,"
        "last_poll_seconds,next_poll_at,last_error,updated_at FROM event_cursors WHERE source=?",
        (source,),
    ).fetchone()
    if not row:
        return None
    return {
        "source": row[0], "intake_checkpoint": row[1], "handled_checkpoint": row[2],
        "last_batch_id": row[3], "last_batch_started_at": row[4],
        "last_poll_seconds": row[5], "next_poll_at": row[6], "last_error": row[7], "updated_at": row[8],
    }


def _cursor_start(connection, source: str, cutoff: datetime) -> datetime:
    existing = _cursor(connection, source)
    if existing and existing.get("intake_checkpoint"):
        return parse_time(existing["intake_checkpoint"]) - timedelta(days=OVERLAP_DAYS)
    return cutoff - timedelta(days=INITIAL_LOOKBACK_DAYS)


def parse_poll_interval(headers: str | dict[str, Any] | None, default: int = DEFAULT_POLL_SECONDS) -> int:
    """Extract X-Poll-Interval when a caller has a header response.

    GitHub's notification endpoint does not require a header probe for queue
    correctness.  When a probe is unavailable, the documented safe minimum is
    300 seconds; values below that are clamped to the same minimum.
    """

    candidate: Any = None
    if isinstance(headers, dict):
        for key, value in headers.items():
            if str(key).lower() == "x-poll-interval":
                candidate = value
                break
    elif isinstance(headers, str):
        for line in headers.splitlines():
            if ":" in line and line.split(":", 1)[0].strip().lower() == "x-poll-interval":
                candidate = line.split(":", 1)[1].strip()
                break
    try:
        parsed = int(float(candidate)) if candidate is not None else int(default)
    except (TypeError, ValueError):
        parsed = int(default)
    return max(DEFAULT_POLL_SECONDS, parsed)


def _api_endpoint(since: datetime) -> str:
    query = urlencode(
        [("all", "true"), ("participating", "false"), ("since", iso(since)), ("per_page", "50")]
    )
    return f"notifications?{query}"


def run_github_notifications(since: datetime, *, runner=None) -> tuple[list[list[dict[str, Any]]], str]:
    """Run the strict, paginated collection command.

    ``runner`` is injectable for tests and returns ``(returncode, stdout,
    stderr)``.  The production command intentionally goes through ``rtk
    proxy`` so scheduled collectors have the same command boundary as manual
    maintenance.
    """

    command = ["rtk", "proxy", "gh", "api", "--paginate", "--slurp", _api_endpoint(since)]
    if runner is None:
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, check=False
        )
        result = (completed.returncode, completed.stdout or "", completed.stderr or "")
    else:
        result = runner(command)
    if not isinstance(result, tuple) or len(result) < 2:
        raise CollectionError("GitHub collector returned no command result")
    returncode, stdout = result[0], result[1]
    if returncode != 0:
        raise CollectionError("GitHub notification pagination failed; intake cursor was not advanced")
    try:
        pages = json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as error:
        raise CollectionError("GitHub notification response was not JSON; intake cursor was not advanced") from error
    if not isinstance(pages, list) or not pages or not all(isinstance(page, list) for page in pages):
        raise CollectionError("GitHub pagination was not a strict list of pages; intake cursor was not advanced")
    normalized: list[list[dict[str, Any]]] = []
    for page in pages:
        clean_page: list[dict[str, Any]] = []
        for item in page:
            if not isinstance(item, dict) or not _nonempty(item.get("id")) or not _nonempty(item.get("updated_at")):
                raise CollectionError("GitHub page contained incomplete notification metadata; intake cursor was not advanced")
            try:
                parse_time(item["updated_at"])
            except ValueError as error:
                raise CollectionError("GitHub page contained an invalid notification timestamp") from error
            if not isinstance(item.get("repository") or {}, dict) or not isinstance(item.get("subject") or {}, dict):
                raise CollectionError("GitHub page contained malformed routing metadata")
            clean_page.append(item)
        normalized.append(clean_page)
    return normalized, _api_endpoint(since)


def run_github_headers(endpoint: str) -> str:
    """Probe response headers through the same authenticated gh boundary.

    Header probing is best-effort: the body collection remains the source of
    truth, while a missing header falls back to the documented five-minute
    minimum.  The probe never writes RepoStew state.
    """

    command = ["rtk", "proxy", "gh", "api", "--include", endpoint]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, check=False
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout or "" if completed.returncode == 0 else ""


def _subject_identity(notification: dict[str, Any]) -> dict[str, Any]:
    repository = notification.get("repository") or {}
    repo = _nonempty(repository.get("full_name")) if isinstance(repository, dict) else None
    repo = repo.lower() if repo else None
    subject = notification.get("subject") or {}
    subject_url = _nonempty(subject.get("url")) if isinstance(subject, dict) else None
    parsed = urlparse(subject_url or "")
    path = [part for part in parsed.path.split("/") if part]
    resource = path[3] if len(path) >= 5 and path[0] == "repos" else None
    identifier = path[4] if len(path) >= 5 and path[0] == "repos" else None
    kind_map = {
        "PullRequest": "pull_request",
        "Issue": "issue",
        "Discussion": "discussion",
        "CheckSuite": "checksuite",
    }
    subject_type = _nonempty(subject.get("type")) if isinstance(subject, dict) else None
    kind = kind_map.get(subject_type or "")
    if not kind and resource:
        kind = {
            "pulls": "pull_request", "issues": "issue", "discussions": "discussion",
            "check-suites": "checksuite", "check-runs": "checkrun",
        }.get(resource)
    if kind and identifier and repo:
        target_key = f"github:{repo}:{kind}:{identifier}"
    else:
        # Unknown/CheckSuite-like events remain actionable routing records.
        event_id = _nonempty(notification.get("id")) or hashlib.sha256((subject_url or "unknown").encode()).hexdigest()[:20]
        target_key = f"github:{repo or 'unknown'}:notification:{event_id}"
        kind = kind or "unknown"
    number: int | None = None
    if kind in {"pull_request", "issue", "discussion"} and identifier and identifier.isdigit():
        number = int(identifier)
    return {
        "target_key": target_key,
        "target_type": kind,
        "repo": repo,
        "number": number,
        "subject_url": subject_url,
        "subject_type": subject_type or "Unknown",
    }


def normalize_github_notification(notification: dict[str, Any], source: str = GITHUB_SOURCE) -> dict[str, Any]:
    identity = _subject_identity(notification)
    subject = notification.get("subject") or {}
    revision_material = {
        "target_key": identity["target_key"],
        "updated_at": parse_time(notification["updated_at"]).isoformat(),
        "subject_url": identity["subject_url"],
        "latest_comment_url": _nonempty(subject.get("latest_comment_url")),
        "title": _nonempty(subject.get("title")),
        "reason": _nonempty(notification.get("reason")),
    }
    revision_hash = hashlib.sha256(_json(revision_material).encode("utf-8")).hexdigest()
    source_key = f"{source}:{_nonempty(notification.get('id'))}"
    summary = {
        "key": source_key,
        "source": source,
        "thread_id": _nonempty(notification.get("id")),
        "repo": identity["repo"],
        "reason": _nonempty(notification.get("reason")),
        "unread": bool(notification.get("unread", True)),
        "updated_at": parse_time(notification["updated_at"]).isoformat(),
        "subject_type": identity["subject_type"],
        "title": _nonempty(subject.get("title")),
        "subject_api_url": identity["subject_url"],
        "latest_comment_api_url": _nonempty(subject.get("latest_comment_url")),
        "status": "pending",
        "queue_status": "queued-unread",
        "handled": False,
        "target_key": identity["target_key"],
        "revision_hash": revision_hash,
    }
    return {
        "summary": summary,
        "identity": identity,
        "revision_hash": revision_hash,
        "revision_updated_at": summary["updated_at"],
        "source_key": source_key,
    }


def _target_row(connection, target_key: str):
    return connection.execute(
        "SELECT target_key,target_type,repo,number,identity_json,state,revision_hash,revision_updated_at,"
        "source_keys,next_check_at,claim_owner,claim_generation,claim_revision_hash,claim_acquired_at,"
        "snapshot_coverage,snapshot_receipt,head,outcome,last_error,created_at,updated_at "
        "FROM event_targets WHERE target_key=?", (target_key,)
    ).fetchone()


def _upsert_event(connection, event: dict[str, Any], seen_at: str) -> str:
    summary = event["summary"]
    identity = event["identity"]
    target_key = identity["target_key"]
    row = _target_row(connection, target_key)
    if row is None:
        connection.execute(
            "INSERT INTO event_targets(target_key,target_type,repo,number,identity_json,state,revision_hash,"
            "revision_updated_at,source_keys,next_check_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (target_key, identity["target_type"], identity["repo"], identity["number"], _json(identity), "queued",
             event["revision_hash"], event["revision_updated_at"], _json([summary["key"]]), seen_at, seen_at, seen_at),
        )
        connection.execute(
            "INSERT OR IGNORE INTO event_revisions(target_key,revision_hash,first_seen_at,source_key) VALUES(?,?,?,?)",
            (target_key, event["revision_hash"], seen_at, summary["key"]),
        )
        return "queued"

    old_revision = row[6]
    source_keys = json.loads(row[8]) if row[8] else []
    if summary["key"] not in source_keys:
        source_keys.append(summary["key"])
    # Overlap fetches can return delayed pages.  They are retained as
    # provenance, but must never move the target backwards or erase the
    # outcome/claim belonging to its newer revision.
    old_updated = parse_time(row[7]) if row[7] else None
    incoming_updated = parse_time(event["revision_updated_at"])
    if old_updated is not None and incoming_updated < old_updated:
        connection.execute(
            "UPDATE event_targets SET source_keys=?,updated_at=? WHERE target_key=?",
            (_json(source_keys[-2000:]), seen_at, target_key),
        )
        return "stale"
    if old_revision == event["revision_hash"]:
        connection.execute(
            "UPDATE event_targets SET source_keys=?,updated_at=? WHERE target_key=?",
            (_json(source_keys[-2000:]), seen_at, target_key),
        )
        return "duplicate"

    # A changed revision stays queued.  An active owner remains locked until a
    # supervisor explicitly reconciles it; its old claim revision then fails
    # finalization CAS without allowing a second mutation worker to enter.
    connection.execute(
        "UPDATE event_targets SET target_type=?,repo=?,number=?,identity_json=?,state='queued',revision_hash=?,"
        "revision_updated_at=?,source_keys=?,next_check_at=?,snapshot_coverage=NULL,snapshot_receipt=NULL,"
        "head=NULL,outcome=NULL,last_error=NULL,updated_at=? WHERE target_key=?",
        (identity["target_type"], identity["repo"], identity["number"], _json(identity), event["revision_hash"],
         event["revision_updated_at"], _json(source_keys[-2000:]), seen_at, seen_at, target_key),
    )
    connection.execute(
        "INSERT OR IGNORE INTO event_revisions(target_key,revision_hash,first_seen_at,source_key) VALUES(?,?,?,?)",
        (target_key, event["revision_hash"], seen_at, summary["key"]),
    )
    return "requeued"


def _merge_notification(connection, summary: dict[str, Any], seen_at: str) -> None:
    key = summary["key"]
    row = connection.execute(
        "SELECT payload FROM records WHERE collection='notifications' AND key=?", (key,)
    ).fetchone()
    existing = json.loads(row[0]) if row else {}
    old_updated = existing.get("updated_at")
    if old_updated and parse_time(old_updated) > parse_time(summary["updated_at"]):
        return
    # A newer revision reopens a resolved delivery.  Queue state is always
    # explicit: intake is not handling and is never silently marked read.
    if existing.get("status") == "resolved" and old_updated != summary["updated_at"]:
        summary["status"] = "pending"
        summary["resolved_at"] = None
    merged = dict(existing)
    merged.update(summary)
    merged["queue_status"] = "queued-unread"
    merged["handled"] = False
    connection.execute(
        "INSERT INTO records(collection,key,sort_index,payload,updated_at) VALUES('notifications',?,0,?,?) "
        "ON CONFLICT(collection,key) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at",
        (key, state_store.compact(merged), seen_at),
    )


def _flatten_pages(pages: list[list[dict[str, Any]]], cutoff: datetime) -> list[dict[str, Any]]:
    deliveries = []
    for page in pages:
        for item in page:
            if parse_time(item["updated_at"]) <= cutoff:
                deliveries.append(item)
    return deliveries


def collect_github(
    state_home: Path,
    *,
    cutoff: datetime | None = None,
    runner=None,
    headers: str | dict[str, Any] | None = None,
    poll_interval: int | None = None,
) -> dict[str, Any]:
    """Collect one complete GitHub batch and atomically advance intake only."""

    home = validate_bootstrap(Path(state_home))
    cutoff = (cutoff or now_utc()).astimezone(timezone.utc)
    batch_started_at = iso(cutoff)
    batch_id = str(uuid.uuid4())
    with _connect(home) as connection:
        _schema(connection)
        current = _cursor(connection, GITHUB_SOURCE)
        if current and current.get("next_poll_at") and parse_time(current["next_poll_at"]) > cutoff:
            raise QueueError(f"GitHub poll is not due until {current['next_poll_at']}")
        since = _cursor_start(connection, GITHUB_SOURCE, cutoff)
    try:
        pages, endpoint = run_github_notifications(since, runner=runner)
    except CollectionError as error:
        # Intake remains unchanged, but a durable backoff prevents a five
        # minute scheduler from hammering a failing provider.
        with _connect(home) as connection:
            _schema(connection)
            connection.execute("BEGIN IMMEDIATE")
            current = _cursor(connection, GITHUB_SOURCE)
            previous = int(current.get("last_poll_seconds") or DEFAULT_POLL_SECONDS) if current else DEFAULT_POLL_SECONDS
            backoff = max(DEFAULT_POLL_SECONDS, min(previous * 2, 3600))
            next_poll = iso(cutoff + timedelta(seconds=backoff))
            connection.execute(
                "INSERT INTO event_cursors(source,intake_checkpoint,handled_checkpoint,last_batch_id,last_batch_started_at,last_poll_seconds,next_poll_at,last_error,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET last_poll_seconds=excluded.last_poll_seconds,next_poll_at=excluded.next_poll_at,last_error=excluded.last_error,updated_at=excluded.updated_at",
                (GITHUB_SOURCE, current.get("intake_checkpoint") if current else None, None, None, batch_started_at, backoff, next_poll, str(error), batch_started_at),
            )
        raise
    deliveries = _flatten_pages(pages, cutoff)
    header_text = headers
    if poll_interval is None and headers is None and runner is None:
        header_text = run_github_headers(endpoint)
    poll_seconds = max(DEFAULT_POLL_SECONDS, int(poll_interval)) if poll_interval is not None else parse_poll_interval(header_text)
    next_poll_at = iso(cutoff + timedelta(seconds=poll_seconds))
    # The collector cursor is deliberately v2 and independent of the legacy
    # notification checkpoint, while delivery identities remain the shared
    # ``github:<thread-id>`` keys used by pr_tracker.py.
    events = [normalize_github_notification(item, source=GITHUB_NOTIFICATION_SOURCE) for item in deliveries]
    evidence = {
        "batch_id": batch_id,
        "source": GITHUB_SOURCE,
        "batch_started_at": batch_started_at,
        "since": iso(since),
        "cutoff": batch_started_at,
        "endpoint": endpoint,
        "page_count": len(pages),
        "delivery_count": len(deliveries),
        "poll_interval_seconds": poll_seconds,
        "poll_interval_source": "x-poll-interval" if header_text and parse_poll_interval(header_text) > DEFAULT_POLL_SECONDS else "documented-minimum",
        "complete": True,
    }
    with _connect(home) as connection:
        _schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        for event in events:
            _merge_notification(connection, event["summary"], batch_started_at)
            _upsert_event(connection, event, batch_started_at)
        connection.execute(
            "INSERT INTO event_batches(batch_id,source,batch_started_at,since,cutoff,page_count,delivery_count,complete,evidence_json,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (batch_id, GITHUB_SOURCE, batch_started_at, iso(since), batch_started_at, len(pages), len(deliveries), 1, _json(evidence), batch_started_at),
        )
        connection.execute(
            "INSERT INTO event_cursors(source,intake_checkpoint,handled_checkpoint,last_batch_id,last_batch_started_at,last_poll_seconds,next_poll_at,last_error,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET intake_checkpoint=excluded.intake_checkpoint,"
            "last_batch_id=excluded.last_batch_id,last_batch_started_at=excluded.last_batch_started_at,last_poll_seconds=excluded.last_poll_seconds,"
            "next_poll_at=excluded.next_poll_at,last_error=NULL,updated_at=excluded.updated_at",
            (GITHUB_SOURCE, batch_started_at, None, batch_id, batch_started_at, poll_seconds, next_poll_at, None, batch_started_at),
        )
    return {**evidence, "queued": sum(1 for event in events), "endpoint": endpoint}


def ingest_email(state_home: Path, *, seen_at: datetime | None = None) -> dict[str, Any]:
    """Route pending connector-normalized email metadata into event targets."""

    home = validate_bootstrap(Path(state_home))
    stamp = iso((seen_at or now_utc()))
    with _connect(home) as connection:
        _schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        rows = connection.execute(
            "SELECT payload FROM records WHERE collection='notifications' AND key LIKE 'email:%'"
        ).fetchall()
        routed = 0
        for row in rows:
            summary = json.loads(row[0])
            if summary.get("status") == "resolved" or not summary.get("subject_api_url"):
                continue
            notification = {
                "id": summary.get("thread_id"), "updated_at": summary.get("updated_at"),
                "reason": "email", "unread": True,
                "repository": {"full_name": summary.get("repo")},
                "subject": {"type": summary.get("subject_type"), "url": summary.get("subject_api_url"),
                             "title": summary.get("title"), "latest_comment_url": summary.get("latest_comment_api_url")},
            }
            try:
                event = normalize_github_notification(notification, source=summary.get("source") or "email")
            except (KeyError, TypeError, ValueError):
                continue
            _merge_notification(connection, event["summary"], stamp)
            _upsert_event(connection, event, stamp)
            routed += 1
        connection.execute(
            "INSERT INTO event_cursors(source,intake_checkpoint,handled_checkpoint,last_batch_id,last_batch_started_at,last_poll_seconds,last_error,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET updated_at=excluded.updated_at,last_error=NULL",
            ("email", None, None, None, stamp, None, None, stamp),
        )
    return {"source": "email", "routed": routed, "checkpoint_advanced": False}


def enqueue_target(
    state_home: Path,
    repo: str,
    number: int,
    kind: str,
    revision: Any,
    source: str,
    source_proof: str,
    *,
    updated_at: datetime | None = None,
    head: str | None = None,
) -> dict[str, Any]:
    """Enqueue a scanner/reconciliation target without accepting a fetch URL.

    ``revision`` is a compact, caller-provided identity such as GitHub
    ``updated_at`` + head SHA + event ID.  It is hashed and retained as
    routing evidence; arbitrary issue bodies or endpoint URLs are rejected by
    omission from this API.
    """

    home = validate_bootstrap(Path(state_home))
    repo = _nonempty(repo) or ""
    if repo.count("/") != 1 or any(not part for part in repo.split("/")):
        raise QueueError("repo must be owner/repository")
    repo = repo.lower()
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise QueueError("number must be a positive integer")
    kind = _nonempty(kind) or ""
    if kind == "pull":
        kind = "pull_request"
    if kind not in {"pull_request", "issue", "discussion"}:
        raise QueueError("kind must be pull_request, issue or discussion")
    source = _nonempty(source) or ""
    proof = _nonempty(source_proof) or ""
    if not source or not proof:
        raise QueueError("source and source proof are required")
    if len(source) > 200 or len(proof) > 1000:
        raise QueueError("source metadata is too long")
    stamp = iso((updated_at or now_utc()).astimezone(timezone.utc))
    target_key = f"github:{repo}:{kind}:{number}"
    identity = {
        "target_key": target_key, "target_type": kind, "repo": repo, "number": number,
        "source": source, "source_proof": proof,
    }
    revision_material = {"target_key": target_key, "revision": revision, "head": head}
    revision_hash = hashlib.sha256(_json(revision_material).encode("utf-8")).hexdigest()
    source_key = f"{source}:{repo}#{number}:{revision_hash[:24]}"
    summary = {
        "key": source_key, "source": source, "thread_id": source_key, "repo": repo,
        "reason": source, "unread": True, "updated_at": stamp,
        "subject_type": {"pull_request": "PullRequest", "issue": "Issue", "discussion": "Discussion"}[kind],
        "title": None, "subject_api_url": None, "latest_comment_api_url": None,
        "status": "pending", "queue_status": "queued-unread", "handled": False,
        "target_key": target_key, "revision_hash": revision_hash,
        "source_proof": proof,
    }
    event = {
        "summary": summary, "identity": identity, "revision_hash": revision_hash,
        "revision_updated_at": stamp, "source_key": source_key,
    }
    with _connect(home) as connection:
        _schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        _merge_notification(connection, summary, stamp)
        action = _upsert_event(connection, event, stamp)
    return {"target_key": target_key, "revision_hash": revision_hash, "action": action, "source": source}


def due_targets(
    state_home: Path,
    *,
    at: datetime | None = None,
    limit: int = 100,
    eligible_repos: Iterable[str] | None = None,
    target_types: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    home = validate_bootstrap(Path(state_home))
    if limit < 1:
        raise ValueError("limit must be positive")
    threshold = iso((at or now_utc()))
    with _connect(home) as connection:
        _schema(connection)
        clauses = ["state IN ('queued','waiting_maintainer','retryable_failure')", "next_check_at<=?", "claim_owner IS NULL"]
        values: list[Any] = [threshold]
        repositories = sorted({str(repo).lower() for repo in eligible_repos or [] if str(repo).strip()})
        kinds = sorted({str(kind) for kind in target_types or [] if str(kind).strip()})
        if repositories:
            clauses.append("repo IN (" + ",".join("?" for _ in repositories) + ")")
            values.extend(repositories)
        if kinds:
            clauses.append("target_type IN (" + ",".join("?" for _ in kinds) + ")")
            values.extend(kinds)
        values.append(limit)
        rows = connection.execute(
            "SELECT target_key,target_type,repo,number,identity_json,state,revision_hash,revision_updated_at,"
            "source_keys,next_check_at,claim_owner,claim_generation,claim_revision_hash,claim_acquired_at,"
            "snapshot_coverage,snapshot_receipt,head,outcome,last_error,created_at,updated_at FROM event_targets WHERE "
            + " AND ".join(clauses) + " ORDER BY next_check_at,target_key LIMIT ?", values
        ).fetchall()
    return [_row_dict(row) for row in rows]


def get_target(state_home: Path, target_key: str) -> dict[str, Any] | None:
    """Read one target for supervisor reconciliation without mutating state."""

    home = validate_bootstrap(Path(state_home))
    with _connect(home) as connection:
        _schema(connection)
        row = _target_row(connection, target_key)
    return _row_dict(row) if row is not None else None


def _row_dict(row) -> dict[str, Any]:
    keys = ("target_key", "target_type", "repo", "number", "identity_json", "state", "revision_hash",
            "revision_updated_at", "source_keys", "next_check_at", "claim_owner", "claim_generation",
            "claim_revision_hash", "claim_acquired_at", "snapshot_coverage", "snapshot_receipt", "head",
            "outcome", "last_error", "created_at", "updated_at")
    item = dict(zip(keys, row))
    for field in ("identity_json", "source_keys", "snapshot_coverage", "snapshot_receipt", "outcome"):
        if item[field]:
            try:
                item[field] = json.loads(item[field])
            except json.JSONDecodeError:
                pass
    return item


def claim_target(state_home: Path, target_key: str, owner: str, *, at: datetime | None = None) -> dict[str, Any]:
    home = validate_bootstrap(Path(state_home))
    owner = _nonempty(owner) or ""
    if not owner:
        raise QueueError("claim owner must be non-empty")
    stamp = iso(at or now_utc())
    generation = str(uuid.uuid4())
    with _connect(home) as connection:
        _schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        row = _target_row(connection, target_key)
        if row is None:
            raise QueueError(f"unknown event target: {target_key}")
        if row[10]:
            raise QueueError("target is owned; reconcile the interrupted owner before reclaiming")
        if row[5] not in {"queued", "waiting_maintainer", "retryable_failure"}:
            raise QueueError(f"target is not claimable in state {row[5]}")
        if row[2]:
            repository_owner = connection.execute(
                "SELECT claim_owner FROM event_targets WHERE repo=? AND claim_owner IS NOT NULL "
                "AND claim_owner<>? LIMIT 1", (row[2], owner)
            ).fetchone()
            if repository_owner:
                raise QueueError("repository is already owned by another mutation worker")
        connection.execute(
            "UPDATE event_targets SET claim_owner=?,claim_generation=?,claim_revision_hash=?,claim_acquired_at=?,updated_at=? WHERE target_key=? AND claim_owner IS NULL",
            (owner, generation, row[6], stamp, stamp, target_key),
        )
        if connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise QueueError("target ownership changed; retry claim")
        claimed = _target_row(connection, target_key)
    result = _row_dict(claimed)
    result["claim_owner"] = owner
    result["claim_generation"] = generation
    return result


def release_target(
    state_home: Path,
    target_key: str,
    owner: str,
    *,
    generation: str | None = None,
    state: str = "queued",
    next_check_at: datetime | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    home = validate_bootstrap(Path(state_home))
    if state not in TARGET_STATES - {"done"}:
        raise QueueError("release state must be queued, waiting_maintainer, awaiting_user or retryable_failure")
    stamp = iso(now_utc())
    check_at = iso(next_check_at or now_utc())
    with _connect(home) as connection:
        _schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        row = _target_row(connection, target_key)
        if row is None or row[10] != owner or (generation is not None and row[11] != generation):
            raise QueueError("target is not owned by this owner")
        if row[12] != row[6]:
            # A stopped old executor cannot park a newer delivery in its wait state.
            # Preserve uncertainty for the next executor's remote reconciliation.
            state = "queued"
            check_at = stamp
            error = "New revision arrived; reconcile previous executor effects before action. " + (error or "")
        where = "target_key=? AND claim_owner=?"
        values: list[Any] = [state, check_at, _nonempty(error), stamp, target_key, owner]
        if generation is not None:
            where += " AND claim_generation=?"
            values.append(generation)
        connection.execute(
            "UPDATE event_targets SET state=?,next_check_at=?,claim_owner=NULL,claim_generation=NULL,claim_revision_hash=NULL,claim_acquired_at=NULL,last_error=?,updated_at=? WHERE " + where,
            values,
        )
        if connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise QueueError("target claim changed during release")
        updated = _target_row(connection, target_key)
    return _row_dict(updated)


def _structured(value: Any, label: str) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise QueueError(f"{label} must be structured JSON") from error
    if not isinstance(value, dict) or not value:
        raise QueueError(f"{label} must be a nonempty object")
    return value


_COVERAGE_COLLECTIONS = {
    "issue_comments", "reviews", "review_comments", "commits", "review_threads",
    "check_runs", "statuses", "commit_comments", "review_thread_comments",
}
_BASE_PAGE_KEYS = {
    "issue", "repository", "issue_comments", "reviews", "review_comments", "commits",
    "review_threads", "review_thread_comments", "check_runs", "statuses",
}
_SNAPSHOT_SECTIONS = {
    "issue", "repository", "pull_request", "issue_comments", "reviews", "review_comments",
    "commits", "commit_comments", "review_threads", "check_runs", "statuses",
}


def _section_names(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {str(key) for key in value}
    if isinstance(value, (list, tuple, set)):
        return {str(key) for key in value}
    return set()


def _validate_coverage_shape(coverage: dict[str, Any], receipt: dict[str, Any], expected_kind: str) -> None:
    """Require the structural shape emitted by github_snapshot.py."""

    for field in ("page_counts", "counts", "ids", "revisions"):
        if not isinstance(coverage.get(field), dict):
            raise QueueError(f"snapshot coverage requires structured {field}")
    required_pages = set(_BASE_PAGE_KEYS)
    if expected_kind == "pull":
        required_pages.update({"pull_request", "head_recheck", "commit_comments"})
    missing_pages = required_pages - set(coverage["page_counts"])
    if missing_pages:
        raise QueueError(f"snapshot coverage page_counts missing: {', '.join(sorted(missing_pages))}")
    for field in ("counts", "ids", "revisions"):
        missing = _COVERAGE_COLLECTIONS - set(coverage[field])
        if missing:
            raise QueueError(f"snapshot coverage {field} missing: {', '.join(sorted(missing))}")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
           for value in coverage["counts"].values()):
        raise QueueError("snapshot coverage counts must be nonnegative integers")
    supplied_sections = (
        coverage.get("endpoint_sections") or coverage.get("sections") or
        receipt.get("endpoint_sections") or receipt.get("sections") or receipt
    )
    if not _SNAPSHOT_SECTIONS.issubset(_section_names(supplied_sections)):
        raise QueueError("snapshot receipt must enumerate all github_snapshot endpoint sections")


def _validate_done_evidence(
    row,
    snapshot_coverage: Any,
    snapshot_receipt: Any,
    head: str | None,
    outcome: Any,
) -> tuple[dict[str, Any], dict[str, Any], str | None, dict[str, Any]]:
    """Check the immutable coverage receipt against the claimed target.

    ``github_snapshot.py`` emits ``coverage`` with ``complete``, ``repo``,
    ``number``, ``kind``, ``head_sha``/``head`` and ``fingerprint``.  The
    separate receipt repeats those identity fields so a worker cannot mark a
    different target complete.  Issues explicitly carry ``head: null``;
    callers must not invent a fake SHA for them.
    """

    coverage = _structured(snapshot_coverage, "snapshot coverage")
    receipt = _structured(snapshot_receipt, "snapshot receipt")
    normalized_outcome = _structured(outcome, "outcome")
    if coverage.get("complete") is not True:
        raise QueueError("snapshot coverage must declare complete=true")
    if receipt.get("complete") is not True:
        raise QueueError("snapshot receipt must declare complete=true")
    expected_repo = row[2]
    expected_number = row[3]
    kind_aliases = {"pull_request": "pull", "pull": "pull", "issue": "issue", "discussion": "discussion"}
    expected_kind = kind_aliases.get(row[1], row[1])
    _validate_coverage_shape(coverage, receipt, expected_kind)
    for label, value in (("coverage", coverage), ("receipt", receipt)):
        if value.get("repo") != expected_repo or value.get("number") != expected_number:
            raise QueueError(f"{label} identity does not match target")
        supplied_kind = kind_aliases.get(value.get("kind"), value.get("kind"))
        if supplied_kind != expected_kind:
            raise QueueError(f"{label} kind does not match target")
    fingerprint = _nonempty(coverage.get("fingerprint"))
    if not fingerprint or fingerprint != _nonempty(receipt.get("fingerprint")):
        raise QueueError("snapshot coverage and receipt fingerprints must match")
    coverage_head = coverage.get("head_sha")
    if coverage_head is None and isinstance(coverage.get("head"), dict):
        coverage_head = coverage["head"].get("sha")
    receipt_head = receipt.get("head_sha", receipt.get("head"))
    if isinstance(receipt_head, dict):
        receipt_head = receipt_head.get("sha")
    if expected_kind == "issue":
        if ("head_sha" not in coverage or coverage.get("head_sha") is not None or
                "head" not in coverage or coverage.get("head") is not None or
                head is not None or coverage_head is not None or receipt_head is not None):
            raise QueueError("issue snapshot head must remain explicitly null")
        normalized_head = None
    else:
        normalized_head = _nonempty(head)
        if not normalized_head or normalized_head != _nonempty(coverage_head) or normalized_head != _nonempty(receipt_head):
            raise QueueError("snapshot head does not match coverage and receipt")
    for timestamp_key in ("captured_at", "snapshot_at", "receipt_at"):
        if timestamp_key in receipt:
            try:
                parse_time(receipt[timestamp_key])
            except ValueError as error:
                raise QueueError(f"snapshot receipt {timestamp_key} must be ISO-8601") from error
    return coverage, receipt, normalized_head, normalized_outcome


def _target_row_for_validation(home: Path, target_key: str):
    with _connect(home) as connection:
        _schema(connection)
        row = _target_row(connection, target_key)
    if row is None:
        raise QueueError(f"unknown event target: {target_key}")
    return row


def finalize_target(
    state_home: Path,
    target_key: str,
    owner: str,
    generation: str,
    *,
    state: str = "done",
    snapshot_coverage: Any = None,
    snapshot_receipt: Any = None,
    head: str | None = None,
    outcome: Any = None,
    next_check_at: datetime | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    home = validate_bootstrap(Path(state_home))
    if state not in TARGET_STATES:
        raise QueueError(f"invalid target state: {state}")
    if state == "done":
        snapshot_coverage, snapshot_receipt, head, outcome = _validate_done_evidence(
            row=_target_row_for_validation(home, target_key), snapshot_coverage=snapshot_coverage,
            snapshot_receipt=snapshot_receipt, head=head, outcome=outcome,
        )
    stamp = iso(now_utc())
    check_at = iso(next_check_at or now_utc())
    with _connect(home) as connection:
        _schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        row = _target_row(connection, target_key)
        if row is None:
            raise QueueError(f"unknown event target: {target_key}")
        if row[10] != owner or row[11] != generation or row[12] != row[6]:
            raise QueueError("claim ownership or revision changed; finalization refused (CAS)")
        connection.execute(
            "UPDATE event_targets SET state=?,next_check_at=?,snapshot_coverage=?,snapshot_receipt=?,head=?,outcome=?,last_error=?,"
            "claim_owner=NULL,claim_generation=NULL,claim_revision_hash=NULL,claim_acquired_at=NULL,updated_at=? "
            "WHERE target_key=? AND claim_owner=? AND claim_generation=? AND claim_revision_hash=?",
            (state, check_at, _json(snapshot_coverage) if snapshot_coverage else None,
             _json(snapshot_receipt) if snapshot_receipt else None, _nonempty(head), _json(outcome) if outcome else None,
             _nonempty(error), stamp, target_key, owner, generation, row[6]),
        )
        if connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise QueueError("claim changed during finalization; finalization refused (CAS)")
        updated = _target_row(connection, target_key)
    return _row_dict(updated)


def repair_replay(
    state_home: Path,
    *,
    target_key: str | None = None,
    owner: str | None = None,
    reason: str = "interrupted owner replay",
    stopped_writer: str | None = None,
) -> dict[str, Any]:
    home = validate_bootstrap(Path(state_home))
    stamp = iso(now_utc())
    if not _nonempty(target_key) or not _nonempty(owner):
        raise QueueError("repair replay requires one exact --target and --owner")
    if not _nonempty(stopped_writer):
        raise QueueError("repair replay requires stopped-writer evidence")
    if not _nonempty(reason):
        raise QueueError("repair replay requires a reason")
    with _connect(home) as connection:
        _schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        row = _target_row(connection, target_key)
        if row is None or row[10] != owner:
            raise QueueError("target is not owned by the specified interrupted owner")
        connection.execute(
            "UPDATE event_targets SET state='queued',next_check_at=?,claim_owner=NULL,claim_generation=NULL,claim_revision_hash=NULL,claim_acquired_at=NULL,last_error=?,updated_at=? WHERE target_key=? AND claim_owner=?",
            (stamp, f"{reason}; stopped_writer={stopped_writer}", stamp, target_key, owner),
        )
    return {"replayed": 1, "target": target_key, "owner": owner, "reason": reason, "stopped_writer": stopped_writer}


def queue_status(state_home: Path) -> dict[str, Any]:
    home = validate_bootstrap(Path(state_home))
    with _connect(home) as connection:
        _schema(connection)
        counts = {
            state: connection.execute("SELECT COUNT(*) FROM event_targets WHERE state=?", (state,)).fetchone()[0]
            for state in sorted(TARGET_STATES)
        }
        claimed = connection.execute("SELECT COUNT(*) FROM event_targets WHERE claim_owner IS NOT NULL").fetchone()[0]
        cursors = [dict(zip(("source", "intake_checkpoint", "handled_checkpoint", "last_batch_id", "last_batch_started_at", "last_poll_seconds", "next_poll_at", "last_error", "updated_at"), row))
                   for row in connection.execute("SELECT source,intake_checkpoint,handled_checkpoint,last_batch_id,last_batch_started_at,last_poll_seconds,next_poll_at,last_error,updated_at FROM event_cursors ORDER BY source")]
        batches = connection.execute("SELECT COUNT(*) FROM event_batches").fetchone()[0]
    return {"state_home": str(home), "database": str(state_store.database_path(home)), "targets": counts, "claimed": claimed, "cursors": cursors, "batches": batches, "automatic_expired_reclaim": False}


def _state_from_args(args) -> Path:
    value = getattr(args, "state_home", None)
    if not value:
        raise QueueError("--state-home is required; use the selected absolute state anchor")
    return validate_bootstrap(Path(value))


def _print(value: Any, as_json: bool = True) -> None:
    if as_json:
        print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))
    elif isinstance(value, list):
        for item in value:
            print(f"{item.get('target_key', '?')} [{item.get('state', '?')}] {item.get('repo') or '?'}")
    else:
        print(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Durable RepoStew event intake/action queue")
    # Accept the stable scheduler form ``--state-home HOME collect`` and the
    # equally useful interactive form ``collect --state-home HOME``.  The
    # bootstrap check below remains mandatory for both forms.
    parser.add_argument("--state-home", type=Path, help="absolute selected state anchor")
    sub = parser.add_subparsers(dest="command", required=True)
    collect_parser = sub.add_parser("collect", help="collect one complete GitHub notifications batch")
    collect_parser.add_argument("--poll-interval", type=int)
    collect_parser.add_argument("--json", action="store_true")
    email_parser = sub.add_parser("ingest-email", help="route pending pr_tracker email metadata")
    email_parser.add_argument("--json", action="store_true")
    enqueue_parser = sub.add_parser("enqueue", help="enqueue canonical scanner/reconciliation metadata")
    enqueue_parser.add_argument("--repo", required=True)
    enqueue_parser.add_argument("--number", required=True, type=int)
    enqueue_parser.add_argument("--kind", required=True, choices=("pull_request", "pull", "issue", "discussion"))
    enqueue_parser.add_argument("--revision", required=True,
                                help="stable metadata identity (updated_at/head/event), not a body")
    enqueue_parser.add_argument("--source", required=True)
    enqueue_parser.add_argument("--source-proof", required=True)
    enqueue_parser.add_argument("--updated-at")
    enqueue_parser.add_argument("--head")
    enqueue_parser.add_argument("--json", action="store_true")
    due_parser = sub.add_parser("due", help="list durable targets due for work")
    due_parser.add_argument("--now")
    due_parser.add_argument("--limit", type=int, default=100)
    due_parser.add_argument("--json", action="store_true")
    claim_parser = sub.add_parser("claim")
    claim_parser.add_argument("target_key")
    claim_parser.add_argument("--owner", required=True)
    claim_parser.add_argument("--json", action="store_true")
    release_parser = sub.add_parser("release")
    release_parser.add_argument("target_key")
    release_parser.add_argument("--owner", required=True)
    release_parser.add_argument("--state", default="queued", choices=sorted(TARGET_STATES - {"done"}))
    release_parser.add_argument("--next-check-at")
    release_parser.add_argument("--error")
    release_parser.add_argument("--json", action="store_true")
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("target_key")
    finalize_parser.add_argument("--owner", required=True)
    finalize_parser.add_argument("--generation", required=True)
    finalize_parser.add_argument("--state", default="done", choices=sorted(TARGET_STATES))
    finalize_parser.add_argument("--snapshot-coverage", "--coverage", dest="snapshot_coverage")
    finalize_parser.add_argument("--snapshot-receipt", "--receipt", dest="snapshot_receipt")
    finalize_parser.add_argument("--head")
    finalize_parser.add_argument("--outcome")
    finalize_parser.add_argument("--next-check-at")
    finalize_parser.add_argument("--error")
    finalize_parser.add_argument("--json", action="store_true")
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--json", action="store_true")
    repair_parser = sub.add_parser("repair")
    repair_parser.add_argument("--replay", action="store_true", required=True)
    repair_parser.add_argument("--target", required=True)
    repair_parser.add_argument("--owner", required=True)
    repair_parser.add_argument("--stopped-writer", required=True,
                               help="evidence that the interrupted writer is stopped")
    repair_parser.add_argument("--reason", required=True)
    repair_parser.add_argument("--json", action="store_true")
    for child in (collect_parser, email_parser, enqueue_parser, due_parser, claim_parser, release_parser,
                  finalize_parser, status_parser, repair_parser):
        child.add_argument("--state-home", type=Path, default=argparse.SUPPRESS,
                           help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        home = _state_from_args(args)
        if args.command == "collect":
            result = collect_github(home, poll_interval=args.poll_interval)
        elif args.command == "ingest-email":
            result = ingest_email(home)
        elif args.command == "enqueue":
            revision: Any = args.revision
            if args.revision.lstrip().startswith(("{", "[")):
                try:
                    revision = json.loads(args.revision)
                except json.JSONDecodeError as error:
                    raise QueueError("--revision must be valid compact JSON or text") from error
            result = enqueue_target(
                home, args.repo, args.number, args.kind, revision, args.source, args.source_proof,
                updated_at=parse_time(args.updated_at) if args.updated_at else None, head=args.head,
            )
        elif args.command == "due":
            result = due_targets(home, at=parse_time(args.now) if args.now else None, limit=args.limit)
        elif args.command == "claim":
            result = claim_target(home, args.target_key, args.owner)
        elif args.command == "release":
            result = release_target(home, args.target_key, args.owner, state=args.state,
                                    next_check_at=parse_time(args.next_check_at) if args.next_check_at else None, error=args.error)
        elif args.command == "finalize":
            result = finalize_target(home, args.target_key, args.owner, args.generation, state=args.state,
                                     snapshot_coverage=args.snapshot_coverage, snapshot_receipt=args.snapshot_receipt,
                                     head=args.head, outcome=args.outcome,
                                     next_check_at=parse_time(args.next_check_at) if args.next_check_at else None, error=args.error)
        elif args.command == "status":
            result = queue_status(home)
        else:
            result = repair_replay(home, target_key=args.target, owner=args.owner,
                                   reason=args.reason, stopped_writer=args.stopped_writer)
        _print(result, getattr(args, "json", False) or args.command in {"collect", "ingest-email", "enqueue", "claim", "release", "finalize", "status", "repair"})
        return 0
    except (QueueError, ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
