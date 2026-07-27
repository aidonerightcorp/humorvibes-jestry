"""Run the privacy-minimized study contract on deterministic synthetic data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from humorvibes.studies import synthetic_demo_receipt


if __name__ == "__main__":
    receipt = synthetic_demo_receipt()
    print(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True))
    assert receipt["data_origin"] == "synthetic_contract_fixture"
    assert receipt["claim_gate"]["claim_ready"] is False
