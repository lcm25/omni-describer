"""Combo repopulation stays on the same control, and refresh leaves the UI thread."""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_describer.core.model_refresh import (
    call_with_timeout,
    choose_ids,
    fill_choice_in_place,
    is_vision_model,
)


class FakeChoice:
    def __init__(self):
        self.labels = []
        self.selection = -1
        self.destroyed = False

    def Clear(self):
        self.labels = []

    def Append(self, label):
        self.labels.append(label)

    def SetSelection(self, index):
        self.selection = index

    def GetSelection(self):
        return self.selection


def test_provider_change_does_not_replace_the_combo():
    voice = FakeChoice()
    same = voice
    fill_choice_in_place(voice, ["Alloy", "Nova"], ["alloy", "nova"], "nova")
    assert voice is same
    assert voice.destroyed is False
    assert voice.labels == ["Alloy", "Nova"]
    assert voice.selection == 1
    fill_choice_in_place(voice, ["Gemini"], ["gemini-2.5-flash"], "missing")
    assert voice is same
    assert voice.selection == 0


def test_vision_filter_keeps_builtin_when_nothing_matches():
    assert is_vision_model("openai", "gpt-4o")
    assert not is_vision_model("openai", "whisper-1")
    assert choose_ids("openai", ["whisper-1", "gpt-4o"], ["gpt-4o-mini"]) == ["gpt-4o"]
    assert choose_ids("openai", ["whisper-1"], ["gpt-4o"]) == ["gpt-4o"]


def test_refresh_runs_off_the_caller_thread():
    caller = threading.get_ident()
    seen = {}

    def work():
        seen["thread"] = threading.get_ident()
        return "ok"

    assert call_with_timeout(work, timeout=2) == "ok"
    assert seen["thread"] != caller
    try:
        call_with_timeout(lambda: time.sleep(1), timeout=0.05)
        raise AssertionError("should time out")
    except TimeoutError:
        pass


if __name__ == "__main__":
    test_provider_change_does_not_replace_the_combo()
    test_vision_filter_keeps_builtin_when_nothing_matches()
    test_refresh_runs_off_the_caller_thread()
    print("model refresh checks passed")
