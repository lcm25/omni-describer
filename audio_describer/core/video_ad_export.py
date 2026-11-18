"""Build the ffmpeg command that muxes narration into a video without re-encoding the picture."""


def _between_expr(intervals):
    """ffmpeg enable expression. Commas are escaped because they separate filters."""
    parts = []
    for start, end in intervals:
        parts.append(f"between(t\\,{float(start):.3f}\\,{float(end):.3f})")
    return "+".join(parts)


def build_described_video_command(
    ffmpeg,
    video_path,
    clips,
    output_path,
    ducking_enabled=True,
    ducking_db=-15,
    keep_original_track=False,
    has_source_audio=True,
    video_duration_sec=None,
):
    """Return the argv for an MP4 with copied video and mixed narration.

    clips: sequence of {"path": wav, "start_sec": float, "end_sec": float}.
    end_sec is the moment the narration finishes, used only for ducking.
    """
    clips = list(clips or [])
    command = [ffmpeg, "-y", "-i", video_path]
    for clip in clips:
        command.extend(["-i", clip["path"]])

    filters = []
    mix_labels = []
    if has_source_audio:
        if ducking_enabled and clips:
            expr = _between_expr((clip["start_sec"], clip["end_sec"]) for clip in clips)
            filters.append(f"[0:a]volume=enable='{expr}':volume={int(ducking_db)}dB[bg]")
            mix_labels.append("[bg]")
        else:
            mix_labels.append("[0:a]")

    for index, clip in enumerate(clips, start=1):
        delay_ms = max(0, int(round(float(clip["start_sec"]) * 1000)))
        filters.append(f"[{index}:a]adelay={delay_ms}|{delay_ms}[n{index}]")
        mix_labels.append(f"[n{index}]")

    if not mix_labels:
        raise ValueError("Nothing to mix: the video has no audio and there is no narration.")

    if len(mix_labels) == 1 and mix_labels[0] == "[0:a]":
        mixed = "[0:a]"
    else:
        filters.append(
            "".join(mix_labels)
            + f"amix=inputs={len(mix_labels)}:duration=longest:dropout_transition=0:normalize=0[mixed]"
        )
        mixed = "[mixed]"

    if video_duration_sec and float(video_duration_sec) > 0:
        filters.append(f"{mixed}apad=whole_dur={float(video_duration_sec):.3f}[aout]")
    elif mixed == "[0:a]":
        filters.append("[0:a]anull[aout]")
    else:
        filters.append("[mixed]anull[aout]")

    command.extend(["-filter_complex", ";".join(filters)])
    command.extend(["-map", "0:v:0", "-map", "[aout]"])
    if keep_original_track and has_source_audio:
        command.extend(["-map", "0:a:0", "-c:a:0", "aac", "-b:a:0", "192k", "-c:a:1", "copy"])
    else:
        command.extend(["-c:a", "aac", "-b:a", "192k"])
    command.extend(["-c:v", "copy"])
    if video_duration_sec and float(video_duration_sec) > 0:
        # Audio was padded to the picture length, so this only trims narration that runs past the end.
        command.append("-shortest")
    command.append(output_path)
    return command


def described_video_filename(video_basename):
    return f"{video_basename}_com_audiodescricao.mp4"
