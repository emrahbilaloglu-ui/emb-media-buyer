import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class SkillAssetTests(unittest.TestCase):
    def test_skill_router_is_bounded_and_references_exist(self):
        body = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(body.splitlines()), 500)
        self.assertRegex(body, r"(?m)^name: emb-media-buyer$")

        referenced = set(re.findall(r"references/[a-z0-9-]+\.md", body))
        self.assertGreaterEqual(len(referenced), 10)
        missing = [path for path in referenced if not (SKILL_ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_decision_evals_are_unique_and_adversarial(self):
        payload = json.loads(
            (SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        cases = payload["cases"]
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(cases), 15)
        for case in cases:
            self.assertTrue(case["expected_behaviors"])
            self.assertTrue(case["forbidden_behaviors"])

    def test_trigger_evals_are_balanced_and_unique(self):
        payload = json.loads(
            (SKILL_ROOT / "evals" / "trigger-evals.json").read_text(
                encoding="utf-8"
            )
        )
        queries = payload["queries"]
        ids = [case["id"] for case in queries]
        labels = [case["should_trigger"] for case in queries]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(labels.count(True), labels.count(False))
        self.assertGreaterEqual(len(queries), 20)

    def test_json_assets_parse(self):
        for path in [
            SKILL_ROOT / "evals" / "evals.json",
            SKILL_ROOT / "evals" / "trigger-evals.json",
            SKILL_ROOT / "assets" / "schemas" / "decision-packet.schema.json",
        ]:
            with self.subTest(path=path.name):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)


if __name__ == "__main__":
    unittest.main()
