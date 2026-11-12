"""Distribution checks for portable skill metadata and local documentation links."""

import json
import re
import unittest
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "venturemorph"


class DistributionTests(unittest.TestCase):
    def test_skill_frontmatter_is_portable_and_complete(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = re.match(r'^---\nname: ([a-z0-9-]+)\ndescription: (".*")\n---\n', content)
        self.assertIsNotNone(frontmatter, "Use portable name and quoted description fields")
        self.assertEqual(frontmatter.group(1), "venturemorph")
        description = json.loads(frontmatter.group(2))
        self.assertTrue(1 <= len(description) <= 1024)
        self.assertNotRegex(description, r"[<>]")
        self.assertLess(len(content.splitlines()), 500)
        self.assertNotIn("TODO", content)

    def test_host_metadata_matches_the_skill(self):
        lines = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "interface:")
        fields = {}
        for line in lines[1:]:
            key, value = line.strip().split(": ", 1)
            fields[key] = json.loads(value)
        self.assertEqual(fields["display_name"], "Venturemorph")
        self.assertTrue(25 <= len(fields["short_description"]) <= 64)
        self.assertIn("$venturemorph", fields["default_prompt"])

    def test_all_relative_markdown_targets_exist(self):
        errors = []
        for source in ROOT.rglob("*.md"):
            if ".git" in source.parts:
                continue
            text = source.read_text(encoding="utf-8")
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                if target.startswith(("https:", "http:", "mailto:", "#")):
                    continue
                path = unquote(target.split("#", 1)[0])
                if not path:
                    continue
                resolved = (source.parent / path).resolve()
                try:
                    resolved.relative_to(ROOT)
                except ValueError:
                    errors.append("{}: target escapes repository: {}".format(source.relative_to(ROOT), target))
                    continue
                if not resolved.exists():
                    errors.append("{}: missing {}".format(source.relative_to(ROOT), target))
        self.assertEqual(errors, [])

    def test_installable_directory_has_all_runtime_resources(self):
        expected = [
            "SKILL.md", "LICENSE", "agents/openai.yaml", "references/evidence-and-change.md",
            "references/growth-and-experiments.md", "references/brand-and-naming.md",
            "references/state-format.md", "assets/review.template.md",
            "assets/project-state.template.json", "assets/project-state.example.json",
            "scripts/check_state.py",
        ]
        for relative in expected:
            with self.subTest(path=relative):
                self.assertTrue((SKILL / relative).is_file())
        self.assertFalse((SKILL / ".venturemorph").exists())

    def test_standalone_skill_preserves_the_same_license(self):
        root_license = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertEqual((SKILL / "LICENSE").read_text(encoding="utf-8"), root_license)
        self.assertIn("Copyright (c) 2026 ufodia", root_license)

    def test_populated_example_is_valid_without_promoting_proposals(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("example_state_checker", SKILL / "scripts" / "check_state.py")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        state = json.loads((SKILL / "assets" / "project-state.example.json").read_text(encoding="utf-8"))
        self.assertEqual(checker.validate_state(state, "stillcue"), [])
        self.assertEqual(state["experiments"][0]["status"], "proposed")
        self.assertIsNone(state["experiments"][0]["result"])
        self.assertIsNone(state["experiments"][0]["timebox"]["started_at"])


if __name__ == "__main__":
    unittest.main()
