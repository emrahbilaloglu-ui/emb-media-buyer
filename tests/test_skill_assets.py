import json
import re
import unittest
from collections import Counter
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class SkillAssetTests(unittest.TestCase):
    def test_skill_router_is_bounded_and_references_exist(self):
        body = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(body.splitlines()), 500)
        self.assertRegex(body, r"(?m)^name: emb-media-buyer$")
        self.assertIn("# EMB Omni Media Buyer", body)
        description = re.search(r"(?m)^description: (.+)$", body)
        self.assertIsNotNone(description)
        self.assertLessEqual(len(description.group(1)), 1024)

        referenced = set(re.findall(r"references/[a-z0-9-]+\.md", body))
        self.assertGreaterEqual(len(referenced), 10)
        missing = [path for path in referenced if not (SKILL_ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_public_brand_preserves_the_canonical_invocation(self):
        readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
        agent = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("# EMB Omni Media Buyer\n"))
        self.assertIn('display_name: "EMB Omni Media Buyer"', agent)
        self.assertIn("$emb-media-buyer", readme)
        self.assertIn("$emb-media-buyer", agent)

    def test_decision_evals_are_unique_and_adversarial(self):
        payload = json.loads(
            (SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        cases = payload["cases"]
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(cases), 44)
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
            SKILL_ROOT / "assets" / "research" / "tiktok-agentic-hub-55.json",
        ]:
            with self.subTest(path=path.name):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_tiktok_agentic_hub_ledger_is_complete_and_bounded(self):
        payload = json.loads(
            (
                SKILL_ROOT
                / "assets"
                / "research"
                / "tiktok-agentic-hub-55.json"
            ).read_text(encoding="utf-8")
        )
        skills = payload["skills"]
        self.assertEqual(payload["catalog_count"], 55)
        self.assertEqual(len(skills), 55)
        self.assertEqual([item["index"] for item in skills], list(range(1, 56)))
        self.assertEqual(len({item["name"] for item in skills}), 55)
        self.assertTrue(
            all(item["decision"] in {"adopt", "adapt", "route", "exclude"} for item in skills)
        )
        self.assertTrue(all(item["capability"].strip() for item in skills))
        self.assertEqual(
            Counter(item["decision"] for item in skills),
            Counter({"adopt": 12, "adapt": 28, "route": 12, "exclude": 3}),
        )
        by_index = {item["index"]: item for item in skills}
        for index in (5, 17, 24, 29, 39, 48):
            self.assertEqual(by_index[index]["decision"], "adapt")

    def test_new_operational_assets_are_linked(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for relative_path in [
            "references/account-review-and-optimization.md",
            "references/tiktok-mcp-operations.md",
            "scripts/account_review.py",
        ]:
            self.assertIn(relative_path, skill)
            self.assertTrue((SKILL_ROOT / relative_path).is_file())

    def test_ci_runs_deterministic_validation(self):
        workflow = SKILL_ROOT / ".github" / "workflows" / "validate.yml"
        self.assertTrue(workflow.is_file())
        body = workflow.read_text(encoding="utf-8")
        self.assertIn("python3 -m unittest discover", body)
        self.assertIn("Draft202012Validator.check_schema", body)


if __name__ == "__main__":
    unittest.main()
