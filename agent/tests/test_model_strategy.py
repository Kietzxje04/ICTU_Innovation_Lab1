import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.config import Settings
from nexusops_agent.orchestration.model_router import ModelRegistry
from nexusops_agent.providers.fpt_factory import ProviderConfig


PERMITTED_MODELS = {
    "Qwen3.6-27B",
    "SaoLa3.1-medium",
    "GLM-5.1",
    "GLM-5.2",
    "Vietnamese_Embedding",
    "gemma-4-31B-it",
    "gemma-4-26B-A4B-it",
    "gpt-oss-20b",
    "DeepSeek-V4-Flash",
    "Qwen2.5-VL-7B-Instruct",
    "FPT.AI-whisper-medium",
    "FPT.AI-whisper-large-v3-turbo",
    "gemma-3-27b-it",
    "whisper-large-v3-turbo",
    "multilingual-e5-large",
    "FPT.AI-VITs",
    "bge-reranker-v2-m3",
    "gpt-oss-120b",
    "Llama-3.3-70B-Instruct",
}


class ModelStrategyTest(unittest.TestCase):
    def test_registry_models_are_permitted_and_critic_is_diverse(self) -> None:
        registry = ModelRegistry(ROOT / "configs" / "model_registry.json")
        registry.assert_critic_diversity()
        data = json.loads((ROOT / "configs" / "model_registry.json").read_text(encoding="utf-8"))
        for role in data["roles"].values():
            for key in ("primary_model", "fallback_model"):
                if role.get(key):
                    self.assertIn(role[key], PERMITTED_MODELS)

    def test_planner_is_deterministic_by_default(self) -> None:
        registry = ModelRegistry(ROOT / "configs" / "model_registry.json")
        self.assertIsNone(registry.select("planner"))
        self.assertEqual("DeepSeek-V4-Flash", registry.select("planner", use_fallback=True))

    def test_secret_is_redacted_from_settings_and_provider_repr(self) -> None:
        secret = "test-secret-that-must-not-appear"
        with patch.dict(os.environ, {"FPT_AI_API_KEY": secret}, clear=False):
            settings = Settings.from_env()
        self.assertNotIn(secret, repr(settings))
        provider_config = ProviderConfig(base_url="https://mkp-api.fptcloud.com/v1", api_key=secret)
        self.assertNotIn(secret, repr(provider_config))
        self.assertIn("<redacted>", repr(provider_config))


if __name__ == "__main__":
    unittest.main()
