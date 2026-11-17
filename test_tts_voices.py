"""Built-in TTS catalogs are complete, and voice refresh follows every page."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_describer.core.narration_requests import (
    GEMINI_PREBUILT_VOICES,
    OPENAI_VOICES,
    builtin_voices,
    next_voice_page,
    voice_catalog_report,
    voice_list_request,
)

GEMINI_30 = (
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
)


def test_gemini_has_all_30_prebuilt_voices():
    names = [item["name"] for item in builtin_voices("gemini", "gemini-2.5-flash-preview-tts")]
    assert tuple(names) == GEMINI_30
    assert len(names) == 30
    assert len(set(names)) == 30
    assert tuple(GEMINI_PREBUILT_VOICES) == GEMINI_30


def test_openai_voices_are_not_filtered_by_model():
    full = [item["id"] for item in builtin_voices("openai", "gpt-4o-mini-tts")]
    legacy = [item["id"] for item in builtin_voices("openai", "tts-1")]
    assert full == list(OPENAI_VOICES)
    assert legacy == full
    assert "marin" in legacy and "cedar" in legacy


def test_voice_pages_are_followed():
    first = "https://example.invalid/voices?page_size=100"
    nxt = next_voice_page(first, {"voices": [{}] * 100, "next_page_token": "page-2"})
    assert "page_token=page-2" in nxt
    assert next_voice_page(nxt, {"voices": [{}]}) is None
    fish = "https://api.fish.audio/model?page_size=100&page_number=1"
    page2 = next_voice_page(fish, {"items": [{}] * 100})
    assert "page_number=2" in page2
    listed = voice_list_request("fish", "key")
    assert "language=pt" not in listed[1]


def test_catalog_report_covers_every_provider():
    rows = voice_catalog_report()
    assert len(rows) == 15
    gemini = next(row for row in rows if row["id"] == "gemini")
    assert gemini["builtin"] == 30
    assert "paginated" in gemini["live"]


if __name__ == "__main__":
    test_gemini_has_all_30_prebuilt_voices()
    test_openai_voices_are_not_filtered_by_model()
    test_voice_pages_are_followed()
    test_catalog_report_covers_every_provider()
    for row in voice_catalog_report():
        print(f"{row['id']}: builtin {row['builtin']}; live {row['live']}")
    print("tts voice checks passed")
