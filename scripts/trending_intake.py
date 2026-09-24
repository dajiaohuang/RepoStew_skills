#!/usr/bin/env python3
"""Capture GitHub Trending and append verified repositories to the shared queue.

This is a root-only intake utility. It reads daily, weekly and monthly Trending
pages, follows any actual next-page links, verifies canonical repository metadata
through the authenticated GitHub CLI, saves a durable source report, then uses
maintenance_queue.append_candidates for cross-root atomic deduplication.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

import maintenance_queue
import repostew_state


PERIODS = ("daily", "weekly", "monthly")
TRENDING_ROOT = "https://github.com/trending"
MIN_STARS_DEFAULT = 100
ROLE = "repostew-repository"
MODEL = "gpt-6-luna"
REASONING_EFFORT = "xhigh"
CONTRACT_RELATIVE = Path("references/worker-contract.md")


class TrendingPageParser(HTMLParser):
    """Extract ranked repository links from GitHub's h2 cards and next control."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.repositories: list[str] = []
        self.next_href: str | None = None
        self._h2_depth = 0
        self._h2_link_seen = False
        self._next_anchor: dict[str, Any] | None = None

    @staticmethod
    def _repository_path(href: str) -> str | None:
        parts = [unquote(part) for part in urlsplit(href).path.strip("/").split("/")]
        if len(parts) != 2 or not all(parts):
            return None
        if parts[0].startswith("-") or parts[1].startswith("-"):
            return None
        return f"{parts[0]}/{parts[1]}"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        href = attributes.get("href", "")
        if tag == "h2":
            self._h2_depth += 1
            self._h2_link_seen = False
        elif tag == "a":
            if self._h2_depth and not self._h2_link_seen:
                repo = self._repository_path(href)
                if repo:
                    self.repositories.append(repo)
                    self._h2_link_seen = True
            rel = set(attributes.get("rel", "").lower().split())
            label = attributes.get("aria-label", "").strip().casefold()
            classes = set(attributes.get("class", "").split())
            if href:
                self._next_anchor = {"href": href, "text": ""}
            if href and (
                "next" in rel
                or label in {"next", "next page"}
                or "next_page" in classes
            ):
                self.next_href = href

    def handle_data(self, data: str) -> None:
        if self._next_anchor is not None:
            self._next_anchor["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._h2_depth:
            self._h2_depth -= 1
            self._h2_link_seen = False
        elif tag == "a" and self._next_anchor is not None:
            label = self._next_anchor["text"].strip().casefold()
            if re.fullmatch(r"next(?:\s+page)?(?:\s*[›»→])?", label):
                self.next_href = self._next_anchor["href"]
            self._next_anchor = None


def fetch_page(url: str, timeout: int = 30) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": "RepoStew-discovery/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return int(response.status), response.read().decode("utf-8", errors="replace")


def collect_period(period: str, page_limit: int = 100) -> dict[str, Any]:
    url = f"{TRENDING_ROOT}?since={period}"
    visited: set[str] = set()
    pages: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    while url and url not in visited and len(pages) < page_limit:
        visited.add(url)
        try:
            status, html = fetch_page(url)
            if not 200 <= status < 300:
                failures.append({"url": url, "error": f"http_status_{status}"})
                break
            parser = TrendingPageParser()
            parser.feed(html)
            if not parser.repositories:
                failures.append({"url": url, "error": "no_repository_cards_parsed"})
                break
            for rank, repo in enumerate(parser.repositories, start=len(entries) + 1):
                entries.append({"owner_repo": repo, "rank": rank, "url": url})
            pages.append({
                "url": url,
                "http_status": status,
                "repository_cards": len(parser.repositories),
                "has_next": bool(parser.next_href),
            })
            url = urljoin(url, parser.next_href) if parser.next_href else ""
        except Exception as error:  # preserve source failure, do not infer empty success
            failures.append({"url": url, "error": f"{type(error).__name__}: {error}"})
            break
    if url and url not in visited and len(pages) >= page_limit:
        failures.append({"url": url, "error": f"pagination_limit_{page_limit}_reached"})
    if url and url in visited and not failures:
        failures.append({"url": url, "error": "pagination_cycle_detected"})
    return {
        "period": period,
        "start_url": f"{TRENDING_ROOT}?since={period}",
        "pages": pages,
        "entries": entries,
        "failures": failures,
        "complete": not failures,
    }


def merge_entries(period_reports: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, list[dict[str, Any]]] = {}
    for report in period_reports:
        for entry in report["entries"]:
            repo = entry["owner_repo"]
            merged.setdefault(repo.casefold(), []).append({
                "period": report["period"],
                "rank": entry["rank"],
                "url": entry["url"],
                "owner_repo": repo,
            })
    return merged


def fetch_metadata(owner_repo: str) -> dict[str, Any]:
    query = (
        "{full_name: .full_name, html_url: .html_url, description: .description, "
        "stargazers_count: .stargazers_count, forks_count: .forks_count, "
        "archived: .archived, fork: .fork, default_branch: .default_branch, "
        "language: .language, topics: .topics, has_issues: .has_issues, "
        "license: .license.spdx_id, pushed_at: .pushed_at, updated_at: .updated_at}"
    )
    result = subprocess.run(
        ["gh", "api", f"repos/{owner_repo}", "--jq", query],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or "").strip().splitlines()
        raise RuntimeError(detail[-1] if detail else f"gh_exit_{result.returncode}")
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError("GitHub API returned a non-object repository record")
    return data


def canonical_metadata(repo_key: str, metadata: dict[str, Any], minimum_stars: int) -> tuple[bool, str]:
    full_name = metadata.get("full_name")
    html_url = metadata.get("html_url")
    if not isinstance(full_name, str) or full_name.casefold() != repo_key:
        return False, "canonical_name_mismatch"
    parsed = urlsplit(html_url or "")
    expected_path = "/" + full_name
    if parsed.scheme != "https" or parsed.netloc.casefold() != "github.com" or parsed.path.rstrip("/").casefold() != expected_path.casefold():
        return False, "canonical_url_mismatch"
    stars = metadata.get("stargazers_count")
    if not isinstance(stars, int) or stars < minimum_stars:
        return False, "below_minimum_stars"
    if metadata.get("archived") is True:
        return False, "archived"
    if metadata.get("fork") is True:
        return False, "fork"
    return True, "eligible"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def build_candidate(
    *, batch_id: str, owner_repo: str, ranks: list[dict[str, Any]], metadata: dict[str, Any],
    captured_at: str, evidence_path: Path, contract_path: Path, minimum_stars: int,
) -> dict[str, Any]:
    work_item_id = f"{batch_id}-trending-{slug(owner_repo)}"
    return {
        "batch_id": batch_id,
        "work_item_id": work_item_id,
        "packet_id": work_item_id,
        "owner_repo": metadata["full_name"],
        "backend": "native_subagent",
        "client": "codex_native",
        "provider": "openai",
        "model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "role": ROLE,
        "mode": "autonomous_continuous",
        "authority": "external_contributor_unverified_maintainer",
        "worker_status": "queued",
        "status": "queued",
        "phase": "recent_issue_window_then_full_audit",
        "branch": metadata.get("default_branch"),
        "job_id": None,
        "job_path": None,
        "workspace": None,
        "contract_path": str(contract_path),
        "evidence_path": str(evidence_path),
        "goal": "Complete the frozen recent issue window, then full audit, security triage, and all currently permitted contribution actions; return nested candidates to the root for shared-queue dedupe.",
        "minimum_stars": minimum_stars,
        "star_threshold": minimum_stars,
        "no_repeat": True,
        "candidate_append_owner": "root_only",
        "completion_signal_required": True,
        "completion_signal_policy": "return natural completion or needs-attention to owning root; reconcile before refill; no executor or peer-conversation polling; shared SQLite queue is the sole inter-root coordination channel",
        "orchestration_poll_interval_seconds": None,
        "issue_pr_mutation_gate": "recheck issue and PR capabilities independently immediately before each public write; use fork-first",
        "public_attribution_policy": "no_public_provider_tool_model_agent_bot_ai_or_generated_by_attribution; block_if_target_requires",
        "read_only_behavior": "inspect and audit first; public mutation only after live authority, policy, duplicate and submission gates pass",
        "security_triage_required": True,
        "security_triage_policy": "triage all security-related content; retain sensitive findings privately only",
        "security_route": "private_only_if_sensitive_or_security_gate_fails",
        "source": {
            "kind": "github-trending-union",
            "captured_at": captured_at,
            "capture_file": str(evidence_path),
            "period_ranks": ranks,
            "metadata": metadata,
        },
        "selection_reason": "appeared in one or more complete/current GitHub Trending windows; canonical repository metadata verified; globally deduplicated at atomic append time",
        "updated_at": captured_at,
        "result_links": [],
    }


def write_capture(path: Path, payload: dict[str, Any], *, create: bool) -> None:
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if create:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
        return
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def run_intake(state_home: Path, batch_id: str, minimum_stars: int, apply: bool) -> dict[str, Any]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,99}", batch_id):
        raise ValueError("batch_id must be a lowercase path-safe identifier")
    roots = repostew_state.validate_roots()
    resolved_home = state_home.resolve()
    if resolved_home != roots["state_home"]:
        raise ValueError(f"selected state home disagrees with paths.json: {resolved_home}")
    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    campaign_dir = resolved_home / "campaigns" / batch_id
    campaign_dir.mkdir(parents=True, exist_ok=True)
    capture_path = campaign_dir / f"trending-union-{stamp}.json"
    reports = [collect_period(period) for period in PERIODS]
    merged = merge_entries(reports)

    metadata_by_key: dict[str, dict[str, Any]] = {}
    metadata_failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_metadata, items[0]["owner_repo"]): key for key, items in merged.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                metadata_by_key[key] = future.result()
            except Exception as error:
                metadata_failures.append({
                    "owner_repo": merged[key][0]["owner_repo"],
                    "error": f"{type(error).__name__}: {error}",
                })

    decisions: list[dict[str, Any]] = []
    eligible: list[tuple[str, dict[str, Any]]] = []
    for key, ranks in merged.items():
        metadata = metadata_by_key.get(key)
        if metadata is None:
            decisions.append({"owner_repo": ranks[0]["owner_repo"], "period_ranks": ranks, "decision": "metadata_unavailable"})
            continue
        ok, reason = canonical_metadata(key, metadata, minimum_stars)
        decision = "selected" if ok else reason
        decisions.append({
            "owner_repo": metadata.get("full_name", ranks[0]["owner_repo"]),
            "period_ranks": ranks,
            "metadata": metadata,
            "decision": decision,
        })
        if ok:
            eligible.append((key, metadata))

    candidates = [
        build_candidate(
            batch_id=batch_id,
            owner_repo=metadata["full_name"],
            ranks=merged[key],
            metadata=metadata,
            captured_at=captured_at,
            evidence_path=capture_path,
            contract_path=roots["skill_home"] / CONTRACT_RELATIVE,
            minimum_stars=minimum_stars,
        )
        for key, metadata in eligible
    ]
    capture = {
        "schema_version": 1,
        "batch_id": batch_id,
        "captured_at": captured_at,
        "minimum_stars": minimum_stars,
        "source": "GitHub Trending",
        "periods": reports,
        "period_entry_count": sum(len(report["entries"]) for report in reports),
        "unique_repository_count": len(merged),
        "metadata_failures": metadata_failures,
        "decisions": decisions,
        "candidate_work_item_ids": [row["work_item_id"] for row in candidates],
        "queue_append": {"status": "not_requested" if not apply else "pending"},
    }
    write_capture(capture_path, capture, create=True)
    result: dict[str, Any] = {
        "capture_file": str(capture_path),
        "batch_id": batch_id,
        "complete": all(report["complete"] for report in reports) and not metadata_failures,
        "period_entry_count": capture["period_entry_count"],
        "unique_repository_count": len(merged),
        "selected_before_queue_dedupe": len(candidates),
        "queue_append": {"status": "not_requested"},
    }
    if apply:
        result["queue_append"] = maintenance_queue.append_candidates(resolved_home, candidates)
        result["queue_append"]["status"] = "applied"
    capture["queue_append"] = result["queue_append"]
    capture["intake_complete"] = result["complete"]
    result["report_file"] = str(capture_path)
    write_capture(capture_path, capture, create=False)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-home", required=True, type=Path)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--minimum-stars", type=int, default=MIN_STARS_DEFAULT)
    parser.add_argument("--apply", action="store_true", help="append verified candidates to the shared queue")
    args = parser.parse_args(argv)
    if not args.state_home.is_absolute():
        parser.error("--state-home must be absolute")
    if args.minimum_stars < 0:
        parser.error("--minimum-stars cannot be negative")
    try:
        result = run_intake(args.state_home, args.batch_id, args.minimum_stars, args.apply)
    except Exception as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
