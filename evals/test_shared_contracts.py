"""Exercise drift detection on two independent synthetic source checkouts."""
import json
from pathlib import Path
import tempfile
import unittest

from check_sibling_contracts import SHARED_REFERENCES, SHARED_SKILLS, compare


class SharedContractTests(unittest.TestCase):
    def test_independent_layouts_match_and_contract_drift_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = (Path(directory) / name for name in ("claude", "codex"))
            for repo in (first, second):
                (repo / "evals").mkdir(parents=True)
                (repo / "evals/outcome_contracts.json").write_text(json.dumps({"case": {"query": "natural task"}}))
                skills = repo if repo == first else repo / "plugins/ronny-codex-skills/skills"
                for name in SHARED_SKILLS:
                    (skills / name).mkdir(parents=True)
                    (skills / name / "SKILL.md").write_text("shared guidance")
                for reference in SHARED_REFERENCES:
                    target = skills / reference
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("shared data guidance")
            self.assertEqual(compare(first, second), [])
            (second / "evals/outcome_contracts.json").write_text(json.dumps({"case": {"query": "changed task"}}))
            self.assertEqual(len(compare(first, second)), 1)
            (first / "current-docs/SKILL.md").write_text("changed policy")
            self.assertEqual(len(compare(first, second)), 2)
            (first / SHARED_REFERENCES[0]).write_text("changed data policy")
            self.assertEqual(len(compare(first, second)), 3)


if __name__ == "__main__":
    unittest.main()
