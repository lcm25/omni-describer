"""Gemini calls stay on v1beta. v1 rejects system_instruction."""
from pathlib import Path

from audio_describer.core.analysis_providers import (
    endpoint_for,
    filter_gemini_models,
    gemini_models_url,
)
from audio_describer.core.gemini_api import (
    GEMINI_API_VERSION,
    gemini_api_root,
    gemini_client_http_options,
    is_api_version_error,
)
from audio_describer.core.model_refresh import analysis_list_request
from audio_describer.core.narration_requests import speech_request

ROOT = Path(__file__).resolve().parent


def test_client_is_v1beta():
    options = gemini_client_http_options()
    assert options["api_version"] == "v1beta"
    assert options["api_version"] != "v1"
    assert GEMINI_API_VERSION == "v1beta"
    source = (ROOT / "audio_describer" / "core" / "gemini_helpers.py").read_text(encoding="utf-8")
    assert "gemini_client_http_options()" in source
    assert "http_options=types.HttpOptions(**gemini_client_http_options())" in source
    assert "api_version='v1'" not in source
    assert 'api_version="v1"' not in source
    assert "api_version='v1'" not in (ROOT / "audio_describer" / "core" / "gemini_api.py").read_text(encoding="utf-8")


def test_urls_and_new_models_use_v1beta():
    root = gemini_api_root()
    assert root.endswith("/v1beta")
    assert "/v1/" not in (root + "/")
    assert gemini_models_url().startswith(root + "/models")
    assert endpoint_for("gemini").startswith(root + "/models")
    method, url, _headers = analysis_list_request("gemini", "key")
    assert method == "GET" and url.startswith(root)
    _method, speech_url, _headers, _body, _raw = speech_request(
        "gemini", "gemini-3.8-flash", "Kore", "Olá", api_key="key",
    )
    assert speech_url.startswith(root + "/models/gemini-3.8-flash:")
    listed = filter_gemini_models({
        "models": [
            {
                "name": "models/gemini-3.8-flash",
                "displayName": "3.8 flash",
                "supportedGenerationMethods": ["generateContent"],
            },
            {
                "name": "models/gemini-2.5-flash-preview-tts",
                "supportedGenerationMethods": ["generateContent"],
            },
        ]
    })
    assert [item["id"] for item in listed] == ["gemini-3.8-flash"]


def test_api_version_error_is_short():
    raw = (
        "400 INVALID_ARGUMENT. {'error': {'message': "
        "'Developer instruction is not enabled for api version v1. "
        "Use api version v1beta instead.'}}"
    )
    assert is_api_version_error(raw)
    assert not is_api_version_error("quota exceeded")
    helper = (ROOT / "audio_describer" / "core" / "gemini_helpers.py").read_text(encoding="utf-8")
    assert "is_api_version_error" in helper
    assert "Gemini rejected the request because of the API version. Try again." in helper


if __name__ == "__main__":
    test_client_is_v1beta()
    test_urls_and_new_models_use_v1beta()
    test_api_version_error_is_short()
    print("gemini api version checks passed")
