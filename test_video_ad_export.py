"""ffmpeg argv for a described MP4. No ffmpeg binary required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_describer.core.video_ad_export import (
    build_described_video_command,
    described_video_filename,
)


CLIPS = [
    {"path": "n1.wav", "start_sec": 1.5, "end_sec": 3.25},
    {"path": "n2.wav", "start_sec": 10, "end_sec": 12},
]


def test_filename():
    assert described_video_filename("filme") == "filme_com_audiodescricao.mp4"


def test_ducking_on_copies_video_and_lowers_original():
    command = build_described_video_command(
        "ffmpeg", "in.mp4", CLIPS, "out.mp4",
        ducking_enabled=True, ducking_db=-15, keep_original_track=False, has_source_audio=True,
        video_duration_sec=20,
    )
    graph = command[command.index("-filter_complex") + 1]
    assert command[0] == "ffmpeg"
    assert "-c:v" in command and command[command.index("-c:v") + 1] == "copy"
    assert "volume=-15dB" in graph
    assert "between(t\\,1.500\\,3.250)" in graph
    assert "adelay=1500|1500" in graph
    assert "apad=whole_dur=20.000" in graph
    assert "-shortest" in command
    assert "n1.wav" in command and "n2.wav" in command
    assert command[-1] == "out.mp4"
    assert "0:a:0" not in command


def test_ducking_off_keeps_original_level():
    command = build_described_video_command(
        "ffmpeg", "in.mp4", CLIPS, "out.mp4",
        ducking_enabled=False, ducking_db=-15, has_source_audio=True,
    )
    graph = command[command.index("-filter_complex") + 1]
    assert "volume=" not in graph
    assert "[0:a]" in graph


def test_second_track_is_copied():
    command = build_described_video_command(
        "ffmpeg", "in.mp4", CLIPS, "out.mp4",
        keep_original_track=True, has_source_audio=True,
    )
    assert command[command.index("-map") + 1] == "0:v:0"
    maps = [command[i + 1] for i, item in enumerate(command) if item == "-map"]
    assert maps == ["0:v:0", "[aout]", "0:a:0"]
    assert command[command.index("-c:a:1") + 1] == "copy"


def test_no_source_audio_mixes_narration_only():
    command = build_described_video_command(
        "ffmpeg", "silent.mp4", CLIPS, "out.mp4", has_source_audio=False,
    )
    graph = command[command.index("-filter_complex") + 1]
    assert "[0:a]" not in graph
    assert "amix=inputs=2" in graph


if __name__ == "__main__":
    test_filename()
    test_ducking_on_copies_video_and_lowers_original()
    test_ducking_off_keeps_original_level()
    test_second_track_is_copied()
    test_no_source_audio_mixes_narration_only()
    print("video export command checks passed")
