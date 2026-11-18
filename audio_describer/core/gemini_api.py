"""Gemini API version shared by the SDK client and the REST calls.

google-genai 3.x defaults the developer API to v1. v1 rejects system_instruction
("Developer instruction is not enabled for api version v1"). v1beta accepts it,
including for models that show up later in the v1beta model list.
"""

GEMINI_API_VERSION = "v1beta"


def gemini_client_http_options():
    """Passed to every genai.Client. Uploads and generate_content use this client."""
    return {"api_version": GEMINI_API_VERSION}


def gemini_api_root():
    return f"https://generativelanguage.googleapis.com/{GEMINI_API_VERSION}"


def is_api_version_error(text):
    lowered = str(text or "").lower()
    return "api version" in lowered or "api_version" in lowered
