#!/usr/bin/env python3
"""Run bounded RepoStew discovery rounds without invoking a specific AI client."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DISCOVER = SCRIPT_DIR / "discover.py"


def discovery_command(round_number: int, max_candidates: int, focus_terms=()) -> list[str]:
    """Broaden search parameters after each empty round."""

    min_stars = (5, 3, 1)[min(round_number - 1, 2)]
    max_days = (120, 180, 365)[min(round_number - 1, 2)]
    command = [
        sys.executable,
        str(DISCOVER),
        "--max-days",
        str(max_days),
        "--max-candidates",
        str(max_candidates),
        "--json-only",
    ]
    if focus_terms:
        command.extend(["--min-stars", str(min_stars)])
        for term in focus_terms:
            command.extend(["--focus", term])
    else:
        command.extend(["--direct", "--keyword", "--kw-min-stars", str(min_stars)])
    return command


def discover_round(round_number: int, max_candidates: int, focus_terms=()) -> list[dict]:
    try:
        result = subprocess.run(
            discovery_command(round_number, max_candidates, focus_terms),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    candidates = payload.get("candidates", [])
    return candidates if isinstance(candidates, list) else []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repeat RepoStew discovery until candidates are found or the dry-round limit is reached"
    )
    parser.add_argument("--dry-rounds", type=int, default=3)
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--interval", type=float, default=0)
    parser.add_argument("--focus", action="append", default=[], metavar="TERM")
    args = parser.parse_args()
    if args.dry_rounds < 1 or args.max_candidates < 1 or args.interval < 0:
        parser.error("dry-rounds and max-candidates must be positive; interval cannot be negative")

    for round_number in range(1, args.dry_rounds + 1):
        candidates = discover_round(round_number, args.max_candidates, args.focus)
        if candidates:
            print(json.dumps({"round": round_number, "candidates": candidates}, indent=2, ensure_ascii=False))
            return 0
        print(f"Discovery round {round_number}/{args.dry_rounds}: no candidates", file=sys.stderr)
        if round_number < args.dry_rounds and args.interval:
            time.sleep(args.interval)

    print(json.dumps({"rounds": args.dry_rounds, "candidates": [], "message": "dry-round limit reached"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
