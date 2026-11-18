"""Gemini API version shared by the SDK client and the REST calls.

google-genai 3.x defaults the developer API to v1. v1 rejects system_instruction
("Developer instruction is not enabled for api version v1"). v1beta accepts it,
including for models that show up later in the v1beta model list.
"""

GEMINI_API_VERSION = "v1beta"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
# The previous default. A saved copy of it must not replace a newer selection.
RETIRED_GEMINI_MODELS = frozenset({"gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"})


def gemini_client_http_options():
    """Passed to every genai.Client. Uploads and generate_content use this client."""
    return {"api_version": GEMINI_API_VERSION}


def gemini_api_root():
    return f"https://generativelanguage.googleapis.com/{GEMINI_API_VERSION}"


def is_api_version_error(text):
    lowered = str(text or "").lower()
    return "api version" in lowered or "api_version" in lowered


def is_retired_model_error(text):
    return "no longer available" in str(text or "").lower()


def canonical_model_id(value):
    """Turn a models/ prefix or a display name into the id generate_content expects."""
    text = str(value or "").strip()
    if text.lower().startswith("models/"):
        text = text.split("/", 1)[1].strip()
    if " " in text:
        slug = "-".join(text.lower().split())
        if slug.startswith("gemini-"):
            return slug
    return text


def resolve_gemini_model(settings, default=DEFAULT_GEMINI_MODEL):
    """Id for generate_content. analysis_model wins over an old override."""
    settings = settings or {}
    custom = canonical_model_id(settings.get("analysis_model_custom"))
    selected = canonical_model_id(settings.get("analysis_model"))
    if selected == "__custom__":
        return custom or default
    if selected:
        return selected
    override = canonical_model_id(settings.get("gemini_model_override"))
    if override and override not in RETIRED_GEMINI_MODELS:
        return override
    return default


def generate_content_model(client, settings, contents=None, config=None):
    """Call generate_content with the model selected in settings."""
    model = resolve_gemini_model(settings)
    return client.models.generate_content(model=model, contents=contents, config=config)
