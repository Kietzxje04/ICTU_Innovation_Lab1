import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.evaluation.runner import EvaluationRunner


class EvaluationAndSafetyTest(unittest.TestCase):
    def test_golden_cases_pass_and_never_write(self) -> None:
        report = EvaluationRunner().run_file(ROOT / "evaluation" / "golden_cases.json")
        self.assertEqual(3, report["scenario_count"])
        self.assertEqual(3, report["passed"])
        self.assertEqual(0, report["failed"])
        for result in report["results"]:
            self.assertTrue(result["checks"]["no_external_write"])
            self.assertTrue(result["checks"]["mandatory_tail"])


if __name__ == "__main__":
    unittest.main()
