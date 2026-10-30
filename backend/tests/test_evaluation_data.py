import json
from pathlib import Path


def test_evaluation_dataset_covers_required_languages_and_risk_cases():
    dataset_path = (
        Path(__file__).resolve().parents[1]
        / "evaluation"
        / "legal_queries.json"
    )
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))

    assert {case["language"] for case in cases} >= {
        "English",
        "Hindi",
        "Marathi",
    }
    assert {
        "ipc-bns-timeframe",
        "synthetic-pii-redaction",
        "unsupported-section",
        "insufficient-evidence",
    } <= {case["id"] for case in cases}
    assert all(case["expected_checks"] for case in cases)
