"""Provider and model lists stay separate, and each provider keeps its own key."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_describer.core.analysis_settings import (
    clear_key,
    key_label,
    models_for,
    provider_ids,
    read_key,
    should_migrate_legacy_settings,
    write_key,
)


def test_provider_list_does_not_follow_the_model_list():
    providers = provider_ids()
    assert providers[0] == "gemini"
    assert "openai" in providers and "local" in providers
    gemini_models = models_for("gemini")
    openai_models = models_for("openai")
    assert gemini_models and all(item.startswith("gemini") for item in gemini_models)
    assert openai_models and all(item.startswith("gpt-") for item in openai_models)
    assert not set(gemini_models) & set(openai_models)
    assert provider_ids() == providers


def test_each_provider_keeps_its_own_key():
    settings = {}
    write_key(settings, "gemini", "AIza-user")
    write_key(settings, "openai", "sk-user")
    write_key(settings, "anthropic", "sk-ant-user")
    assert read_key(settings, "gemini") == "AIza-user"
    assert read_key(settings, "openai") == "sk-user"
    assert read_key(settings, "anthropic") == "sk-ant-user"
    clear_key(settings, "gemini")
    assert read_key(settings, "gemini") == ""
    assert read_key(settings, "openai") == "sk-user"
    assert "Gemini" in key_label("gemini")
    assert read_key(settings, "local") == ""


def test_portable_copy_does_not_import_keys():
    assert should_migrate_legacy_settings(False) is True
    assert should_migrate_legacy_settings(True) is False


if __name__ == "__main__":
    test_provider_list_does_not_follow_the_model_list()
    test_each_provider_keeps_its_own_key()
    test_portable_copy_does_not_import_keys()
    print("analysis settings checks passed")
