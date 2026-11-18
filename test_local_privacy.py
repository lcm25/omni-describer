"""Local analysis must not call a cloud provider from any entry point."""
from audio_describer.core.analysis_providers import (
    DESCRIPTION_ENTRIES,
    LocalCloudBlocked,
    assert_cloud_allowed,
    job_log_line,
    route_entry,
)
from audio_describer.core.gemini_api import DEFAULT_GEMINI_MODEL, resolve_gemini_model
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _dispatch(entry, provider_id, chunking, cloud):
    route = route_entry(entry, provider_id, chunking)
    if route == "local":
        return "offline"
    cloud.append(entry)
    return "cloud"


def test_every_entry_stays_offline():
    cloud = []
    for entry in DESCRIPTION_ENTRIES:
        assert route_entry(entry, "local", chunking=True) == "local"
        assert _dispatch(entry, "local", True, cloud) == "offline"
        try:
            assert_cloud_allowed("local", entry)
            raise AssertionError(entry)
        except LocalCloudBlocked:
            pass
    assert cloud == []
    line = job_log_line("local", "qwen25vl-3b")
    assert line == "Provider: local, model: qwen25vl-3b"
    assert "key" not in line.lower()


def test_chunked_source_routes_before_upload():
    text = (ROOT / "audio_describer" / "core" / "audio_describer.py").read_text(encoding="utf-8")
    chunk = text.split("def generate_descriptions_chunked", 1)[1].split("\ndef ", 1)[0]
    assert chunk.index("video_route") < chunk.index("get_gemini_client")
    assert "assert_cloud_allowed" in chunk
    window = (ROOT / "audio_describer" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'video_route(provider_id, enable_chunking) == "gemini-chunk"' in window
    assert "log_analysis_job()" in window


def test_default_model_is_not_retired():
    assert DEFAULT_GEMINI_MODEL == "gemini-3.8-flash"
    assert resolve_gemini_model({"analysis_model": "gemini-3.8-flash", "gemini_model_override": "gemini-2.5-flash"}) == "gemini-3.8-flash"
    assert resolve_gemini_model({}) == "gemini-3.8-flash"


if __name__ == "__main__":
    test_every_entry_stays_offline()
    test_chunked_source_routes_before_upload()
    test_default_model_is_not_retired()
    print("local privacy checks passed")
