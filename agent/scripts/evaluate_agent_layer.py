from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.evaluation.runner import EvaluationRunner


def main() -> None:
    report = EvaluationRunner().run_file(ROOT / "evaluation" / "golden_cases.json")
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    output = ROOT / "runtime" / "evaluations" / "agent-evaluation-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
