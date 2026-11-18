"""Duration fit and narration/analysis request builders. No network."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from audio_describer.core.speech_fit import (
    calibrate_chars_per_second,
    fit_report,
    long_descriptions,
    slot_seconds,
    speaking_seconds,
)
from audio_describer.core.narration_requests import (
    azure_ssml,
    deepgram_url,
    gemini_tts_payload,
    murf_payload,
    mvsep_fields,
    openai_payload,
    speech_request,
    xai_payload,
)
from audio_describer.core.analysis_providers import (
    anthropic_body,
    filter_gemini_models,
    openai_style_body,
    sample_frame_times,
)
from audio_describer.core.shorten import build_shorten_prompt, parse_alternatives


def test_slot_is_the_tighter_gap():
    descriptions = [(0.0, 4.0, "um texto"), (3.0, 6.0, "depois")]
    assert slot_seconds(descriptions, 0) == 3.0
    assert slot_seconds(descriptions, 1) == 3.0


def test_speaking_time_scales_with_rate():
    text = "a" * 14
    assert speaking_seconds(text, 14.0, 100) == 1.0
    assert speaking_seconds(text, 14.0, 200) == 0.5


def test_too_long_announces_the_overflow():
    descriptions = [(0.0, 1.0, "palavra " * 20), (1.0, 2.0, "ok")]
    report = fit_report(descriptions, 0, chars_per_second=14.0, rate_percent=100)
    assert report["too_long"]
    assert report["slot"] == 1.0
    assert long_descriptions(descriptions, 14.0)[0]["index"] == 0
    assert calibrate_chars_per_second("abcdef", 2.0) == 3.0


def test_openai_and_gemini_payloads():
    body = openai_payload("gpt-4o-mini-tts", "alloy", "Olá", "calmo")
    assert body["instructions"] == "calmo"
    assert body["response_format"] == "wav"
    plain = openai_payload("tts-1", "alloy", "Olá", "calmo")
    assert "instructions" not in plain
    gemini = gemini_tts_payload("gemini-2.5-flash-preview-tts", "Kore", "Olá")
    assert gemini["generationConfig"]["responseModalities"] == ["AUDIO"]
    assert gemini["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] == "Kore"


def test_provider_urls_match_narratudo():
    method, url, headers, body, raw = speech_request(
        "deepgram", "flux", "flux-leandro-pt", "texto", api_key="secret"
    )
    assert method == "POST"
    assert url == deepgram_url("flux-leandro-pt")
    assert headers["Authorization"] == "Token secret"
    assert body == {"text": "texto"}
    _method, xai_url, xai_headers, xai_body, _raw = speech_request(
        "xai", "xai-tts", "eve", "texto", api_key="k", speed=2
    )
    assert xai_url == "https://api.x.ai/v1/tts"
    assert xai_headers["Authorization"] == "Bearer k"
    assert xai_body["speed"] == 1.5
    assert xai_payload("eve", "texto")["voice_id"] == "eve"
    ssml = azure_ssml("pt-BR-FranciscaNeural", "Oi <b>")
    assert "pt-BR" in ssml and "&lt;b&gt;" in ssml
    model, murf = murf_payload("falcon-2.1", "abc", "Oi", "pt-BR")
    assert model == "falcon-2.1" and murf["model"] == "falcon-2.1" and murf["locale"] == "pt-BR"
    fields = mvsep_fields("104", "speaker2", "corre")
    assert fields["add_opt2"].startswith("Speaker 2:")
    try:
        mvsep_fields("103", "reference", "x")
        raise AssertionError("clone model should be refused")
    except ValueError:
        pass


def test_frame_request_keeps_timestamps():
    times = sample_frame_times(16, count=4)
    assert len(times) == 4
    assert times[0] < times[-1]
    frames = [{"time": 12, "jpeg": b"jpeg"}]
    body = openai_style_body("gpt-4o", "system", "user", frames)
    parts = body["messages"][1]["content"]
    assert any(part.get("text") == "Frame at 00:12." for part in parts)
    anthropic = anthropic_body("claude", "system", "user", frames)
    assert anthropic["messages"][0]["content"][1]["source"]["media_type"] == "image/jpeg"
    models = filter_gemini_models({
        "models": [
            {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-2.5-flash-preview-tts", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        ]
    })
    assert [item["id"] for item in models] == ["gemini-2.5-flash"]
    tts = filter_gemini_models({
        "models": [
            {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-2.5-flash-preview-tts", "supportedGenerationMethods": ["generateContent"]},
        ]
    }, require_tts=True)
    assert tts[0]["id"].endswith("tts")


def test_shorten_prompt_and_parse():
    prompt = build_shorten_prompt(
        "Um homem atravessa a sala correndo muito depressa.",
        "Brazilian Portuguese",
        1.5,
        10,
        {"before": "antes", "after": "depois"},
        [{"name": "Ana"}],
    )
    assert prompt["max_characters"] == 15
    assert "Ana" in prompt["user"]
    parsed = parse_alternatives('{"alternatives": ["corre", "atravessa", "corre", ""]}')
    assert parsed == ["corre", "atravessa"]


if __name__ == "__main__":
    test_slot_is_the_tighter_gap()
    test_speaking_time_scales_with_rate()
    test_too_long_announces_the_overflow()
    test_openai_and_gemini_payloads()
    test_provider_urls_match_narratudo()
    test_frame_request_keeps_timestamps()
    test_shorten_prompt_and_parse()
    print("narration and fit checks passed")
