import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "delegate-codex-cli" / "scripts" / "delegate_codex.py"


def load_delegate_module():
    spec = importlib.util.spec_from_file_location("delegate_codex", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillTests(unittest.TestCase):
    def test_skill_frontmatter_and_metadata_exist(self):
        skill = (ROOT / "skills" / "delegate-codex-cli" / "SKILL.md").read_text(encoding="utf-8")
        metadata = (ROOT / "skills" / "delegate-codex-cli" / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\n"))
        self.assertIn("name: delegate-codex-cli", skill)
        self.assertIn("description:", skill)
        self.assertIn("display_name:", metadata)

    def test_help_is_portable(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--role", result.stdout)
        self.assertIn("--kdd-prefix", result.stdout)

    def test_kdd_prefix_is_deterministic_and_goal_is_last(self):
        module = load_delegate_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.md").write_text("A\r\n", encoding="utf-8")
            (root / "b.md").write_text("B\n", encoding="utf-8")
            args = Namespace(
                kdd_root=str(root),
                kdd_prefix=["a.md", "b.md"],
                kdd_contract=None,
                goal="dynamic goal",
            )
            first = module.build_prompt(args, root)
            second = module.build_prompt(args, root)
            self.assertEqual(first, second)
            self.assertEqual(hashlib.sha256(first.encode()).hexdigest(), hashlib.sha256(second.encode()).hexdigest())
            self.assertLess(first.index("KDD_STATIC_FILE: a.md"), first.index("KDD_STATIC_FILE: b.md"))
            self.assertLess(first.index("--- DYNAMIC_GOAL ---"), len(first))
            self.assertTrue(first.endswith("dynamic goal"))


if __name__ == "__main__":
    unittest.main()
