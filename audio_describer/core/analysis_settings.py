"""Provider list, model list, and per-provider API keys. No wx."""
from .analysis_providers import ANALYSIS_PROVIDERS, FALLBACK_MODELS
from .local_model import LOCAL_MODELS

PROVIDER_KEY_LABELS = {
    "gemini": "Gemini API key:",
    "openai": "OpenAI API key:",
    "xai": "xAI API key:",
    "anthropic": "Anthropic API key:",
    "qwen": "Qwen API key:",
    "openrouter": "OpenRouter API key:",
}


def provider_ids():
    """Stable order. Callers must not rebuild this from the model list."""
    return [item["id"] for item in ANALYSIS_PROVIDERS]


def models_for(provider_id):
    if provider_id == "local":
        return [item["id"] for item in LOCAL_MODELS]
    return list(FALLBACK_MODELS.get(provider_id, ()))


def key_label(provider_id):
    return PROVIDER_KEY_LABELS.get(provider_id, "API key:")


def read_key(settings, provider_id):
    settings = settings or {}
    if provider_id == "gemini":
        return settings.get("user_gemini_api_key") or ""
    if provider_id == "openai":
        own = (settings.get("analysis_api_keys") or {}).get("openai")
        if own:
            return own
        return settings.get("user_openai_api_key") or ""
    if provider_id == "local":
        return ""
    return (settings.get("analysis_api_keys") or {}).get(provider_id) or ""


def write_key(settings, provider_id, value):
    settings = settings if settings is not None else {}
    value = (value or "").strip()
    if provider_id == "local":
        return settings
    if provider_id == "gemini":
        settings["user_gemini_api_key"] = value
    elif provider_id == "openai":
        settings["user_openai_api_key"] = value
    keys = dict(settings.get("analysis_api_keys") or {})
    if provider_id != "gemini":
        keys[provider_id] = value
    settings["analysis_api_keys"] = keys
    return settings


def clear_key(settings, provider_id):
    return write_key(settings, provider_id, "")


def should_migrate_legacy_settings(is_portable):
    """A portable copy must not import keys from %APPDATA%."""
    return not is_portable
