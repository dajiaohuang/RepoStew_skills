from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import maintained_repositories  # noqa: E402


def registry(*rows: str) -> str:
    return "\n".join(
        [
            "# Maintained Repositories",
            "",
            "| Repository | Role | Maintenance status | Verified at | Source | Notes |",
            "|---|---|---|---|---|---|",
            *rows,
            "",
        ]
    )


class MaintainedRepositoryRegistryTests(unittest.TestCase):
    def test_parses_and_sorts_enabled_and_paused_entries(self):
        entries = maintained_repositories.parse_registry_text(
            registry(
                "| [Org/Service](https://github.com/Org/Service) | admin | active | 2026-08-27 | gh repo view | organization ADMIN |",
                "| owner/tool | owner | self | 2026-08-27 | gh repo view | owner matched viewer |",
                "| org/paused | maintain | paused | 2026-08-26 | gh repo view | permission review due |",
            )
        )
        self.assertEqual([entry["repository"] for entry in entries], ["org/paused", "Org/Service", "owner/tool"])
        self.assertEqual([entry["enabled"] for entry in entries], [False, True, True])

    def test_rejects_case_insensitive_duplicates(self):
        text = registry(
            "| Org/Service | admin | active | 2026-08-27 | gh repo view | first |",
            "| org/service | maintain | active | 2026-08-27 | gh repo view | duplicate |",
        )
        with self.assertRaisesRegex(maintained_repositories.RegistryError, "duplicate repository"):
            maintained_repositories.parse_registry_text(text)

    def test_rejects_invalid_role(self):
        text = registry(
            "| Org/Service | write | active | 2026-08-27 | gh repo view | invalid |"
        )
        with self.assertRaisesRegex(maintained_repositories.RegistryError, "invalid role"):
            maintained_repositories.parse_registry_text(text)

    def test_rejects_invalid_status(self):
        text = registry(
            "| Org/Service | admin | historical | 2026-08-27 | gh repo view | invalid |"
        )
        with self.assertRaisesRegex(maintained_repositories.RegistryError, "invalid maintenance status"):
            maintained_repositories.parse_registry_text(text)

    def test_rejects_label_and_link_mismatch(self):
        text = registry(
            "| [Org/Service](https://github.com/Other/Service) | admin | active | 2026-08-27 | gh repo view | invalid |"
        )
        with self.assertRaisesRegex(maintained_repositories.RegistryError, "label and link do not match"):
            maintained_repositories.parse_registry_text(text)

    def test_rejects_missing_verification_source(self):
        text = registry("| Org/Service | admin | active | 2026-08-27 |  | invalid |")
        with self.assertRaisesRegex(maintained_repositories.RegistryError, "source is required"):
            maintained_repositories.parse_registry_text(text)


if __name__ == "__main__":
    unittest.main()
