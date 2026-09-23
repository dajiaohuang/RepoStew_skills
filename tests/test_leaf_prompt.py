from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compile_leaf_prompt as compiler


def valid_packet():
    return dict(dict.fromkeys(compiler.REQUIRED_FIELDS, "test-value"),
                role="repostew-repository", phase="discovery")


class LeafPromptTests(unittest.TestCase):
    def test_cli_writes_utf8_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "prompt.txt"
            packet_file = Path(directory) / "packet.json"
            packet = valid_packet()
            packet["goal"] = "完整审计"
            packet_file.write_text(json.dumps(packet), encoding="utf-8")
            command = [sys.executable, str(Path(compiler.__file__)),
                       "--packet", str(packet_file), "--output", str(output)]
            first = subprocess.run(command, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = output.read_bytes()
            self.assertEqual(original.decode("utf-8"), compiler.render(packet))
            self.assertNotIn(b"\r\n", original)
            second = subprocess.run(command, capture_output=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(output.read_bytes(), original)

    def test_different_repositories_share_complete_prefix(self):
        first = valid_packet()
        first.update(owner_repo="one/project", issue_urls=[], pr_urls=[])
        second = dict(first, owner_repo="two/project", job_id="second-job")
        a = compiler.render(first)
        b = compiler.render(second)
        prefix, revision = compiler.compile_prefix()
        self.assertEqual(a.split(compiler.BOUNDARY)[0], prefix)
        self.assertEqual(b.split(compiler.BOUNDARY)[0], prefix)
        self.assertNotIn("one/project", prefix)
        self.assertNotIn("second-job", prefix)
        suffix = json.loads(a.split(compiler.BOUNDARY)[1])
        self.assertEqual(suffix["instruction_revision"], revision)
        self.assertEqual(suffix["display_name"], "one/project")
        self.assertEqual(suffix["issue_urls"], [])
        self.assertNotIn("instruction_revision", first)
        for source in compiler.SOURCES + compiler.PHASE_SOURCES["discovery"]:
            content = (compiler.SKILL_ROOT / source).read_text(encoding="utf-8")
            self.assertIn(content, prefix)

    def test_source_change_invalidates_old_packet_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source in compiler.SOURCES + compiler.PHASE_SOURCES["discovery"]:
                path = root / source
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"policy for {source}\n", encoding="utf-8")
            _, before = compiler.compile_prefix(root)
            packet = valid_packet()
            packet["instruction_revision"] = before
            compiler.render(packet, root)
            (root / "SKILL.md").write_text("changed policy\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "instruction_revision"):
                compiler.render(packet, root)

    def test_missing_sources_or_contract_fail_closed(self):
        packet = valid_packet()
        packet.update(owner_repo="owner/repo", display_name="another/repo")
        with self.assertRaisesRegex(ValueError, "display_name"):
            compiler.render(packet)
        with self.assertRaisesRegex(ValueError, "Missing packet fields"):
            compiler.render({"owner_repo": "owner/repo"})
        with self.assertRaisesRegex(ValueError, "JSON object"):
            compiler.render([])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                compiler.compile_prefix(Path(directory))

    def test_single_role_and_phase_specific_policy(self):
        packet = valid_packet()
        with self.assertRaisesRegex(ValueError, "Packet role"):
            compiler.render(dict(packet, role="retired-role"))
        with self.assertRaisesRegex(ValueError, "Unknown packet phase"):
            compiler.render(dict(packet, phase="unknown"))
        for phase, sources in compiler.PHASE_SOURCES.items():
            rendered = compiler.render(dict(packet, phase=phase))
            for other_sources in compiler.PHASE_SOURCES.values():
                for source in other_sources:
                    marker = f"=== CANONICAL SOURCE: {source} ==="
                    self.assertEqual(marker in rendered, source in sources)
        _, discovery = compiler.compile_prefix()
        with self.assertRaisesRegex(ValueError, "instruction_revision"):
            compiler.render(dict(packet, phase="review", instruction_revision=discovery))

    def test_only_repository_role_is_shipped(self):
        import tomllib
        roles = list((compiler.SKILL_ROOT / "references/worker-agents").glob("*.toml"))
        self.assertEqual([path.stem for path in roles], ["repostew-repository"])
        role = tomllib.loads(roles[0].read_text(encoding="utf-8"))
        self.assertEqual(role["model"], "gpt-6-luna")
        self.assertEqual(role["model_reasoning_effort"], "xhigh")


if __name__ == "__main__":
    unittest.main()
