"""Brazilian Portuguese default prompts, without touching prompts the user wrote."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_describer.models.prompt_model import (
    DEFAULT_PROMPTS,
    _get_default_prompts_for_lang,
    is_portuguese_language,
    merge_default_prompts,
)


def test_every_english_default_has_a_brazilian_counterpart():
    english = DEFAULT_PROMPTS["en"]
    portuguese = DEFAULT_PROMPTS["pt_BR"]
    assert len(english) == len(portuguese) == 10
    for item in portuguese:
        assert "português do Brasil" in item["prompt"]
        assert item["name"] not in {entry["name"] for entry in english}
    again = merge_default_prompts(portuguese, english, portuguese)
    assert again == portuguese


def test_portuguese_languages_use_the_brazilian_list():
    assert is_portuguese_language("pt_BR")
    assert is_portuguese_language("pt")
    assert _get_default_prompts_for_lang("pt") == DEFAULT_PROMPTS["pt_BR"]
    assert _get_default_prompts_for_lang("pt-BR") == DEFAULT_PROMPTS["pt_BR"]


def test_user_prompts_are_preserved_and_english_copies_are_replaced():
    english = DEFAULT_PROMPTS["en"]
    portuguese = DEFAULT_PROMPTS["pt_BR"]
    edited = {"name": english[0]["name"], "prompt": "My own trailer note."}
    mine = {"name": "Meu prompt", "prompt": "Descreva só os gatos."}
    existing = [dict(english[0]), edited, mine, dict(english[2])]
    # edited uses the same name as the first default, so don't also include the untouched first.
    existing = [edited, mine, dict(english[2])]
    merged = merge_default_prompts(existing, english, portuguese)
    assert {"name": "Meu prompt", "prompt": "Descreva só os gatos."} in merged
    assert edited in merged
    assert {"name": portuguese[2]["name"], "prompt": portuguese[2]["prompt"]} in merged
    assert english[2]["prompt"] not in [item["prompt"] for item in merged]
    assert portuguese[0]["name"] not in [item["name"] for item in merged]
    again = merge_default_prompts(merged, english, portuguese)
    assert again == merged


if __name__ == "__main__":
    test_every_english_default_has_a_brazilian_counterpart()
    test_portuguese_languages_use_the_brazilian_list()
    test_user_prompts_are_preserved_and_english_copies_are_replaced()
    print("default prompt checks passed")
