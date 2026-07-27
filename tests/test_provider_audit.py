"""Provider receipts preserve configured/reachable/executed/quality distinctions."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from humorvibes.config import Settings
from humorvibes.provider_audit import audit_providers


ROOT = Path(__file__).resolve().parents[1]


class FakeLLMs:
    def capabilities(self):
        return [
            {
                "model_id": "ollama:fixture",
                "provider": "ollama",
                "remote_model": "fixture",
                "key_configured": True,
                "local": False,
                "supports_json": True,
                "supports_thinking": True,
                "measured_logprobs": False,
            }
        ]

    def probe(self, model_id):
        return {"ok": True, "provider": "ollama", "version": "fixture"}

    def generate(self, prompt, **kwargs):
        return SimpleNamespace(text="OK", output_tokens=1, finish_reason="stop")


class FakeEmbeddings:
    def capabilities(self):
        return [
            {
                "model_id": "ollama:missing",
                "provider": "ollama",
                "remote_model": "missing",
                "semantic": True,
                "local": False,
                "key_configured": True,
                "configured_dimensions": None,
            }
        ]

    def probe(self, model_id):
        return {
            "ok": False,
            "provider": "ollama",
            "model_id": model_id,
            "error": {
                "code": "upstream_http_error",
                "retryable": False,
                "detail": {"upstream_status": 401},
            },
        }


def test_live_audit_keeps_reachability_execution_and_quality_separate() -> None:
    settings = Settings.from_env({"OLLAMA_API_KEY": "must-not-appear", "GEMMA_MODEL": "fixture"})
    receipt = audit_providers(
        settings,
        live=True,
        llms=FakeLLMs(),
        embeddings=FakeEmbeddings(),
    )
    llm = receipt["llm_models"][0]
    embedding = receipt["embedding_models"][0]
    assert llm["provider_reachable"] is True and llm["operation_executed"] is True
    assert llm["quality_validated"] is False
    assert embedding["provider_reachable"] is False
    assert embedding["operation_error"]["upstream_status"] == 401
    assert receipt["summary"] == {
        "models_configured": 2,
        "operations_executed": 1,
        "operations_failed_or_not_probed": 1,
        "quality_validated_models": 0,
    }
    assert receipt["secret_scan"] == {"configured_secret_count": 1, "secrets_absent": True}
    assert "must-not-appear" not in json.dumps(receipt)


def test_offline_cli_runs_hash_probe_without_network(tmp_path: Path) -> None:
    output = tmp_path / "providers.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "humorvibes.cli",
            "provider-audit",
            "--out",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": str(Path(sys.executable).parent)},
    )
    receipt = json.loads(completed.stdout)
    assert receipt == json.loads(output.read_text(encoding="utf-8"))
    assert receipt["mode"]["live"] is False
    hash_row = next(row for row in receipt["embedding_models"] if row["model_id"] == "hash:128")
    assert hash_row["operation_executed"] is True
    assert receipt["summary"]["quality_validated_models"] == 0
