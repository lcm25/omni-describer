"""Decide whether a description fits the silence available for the narration voice."""

# Characters spoken per second at rate 100. Portuguese narration is about
# 2.5 words per second, and a typical word plus a space is about 6 characters.
DEFAULT_CHARS_PER_SECOND = {
    "windows": 14.0,
    "piper": 13.0,
    "gemini": 15.0,
    "elevenlabs": 15.0,
    "mvsep": 14.0,
    "openai": 15.0,
    "azure": 14.0,
    "cartesia": 15.0,
    "fish": 15.0,
    "minimax": 15.0,
    "speechma": 14.0,
    "xai": 15.0,
    "speechify": 15.0,
    "deepgram": 14.0,
    "murf": 14.0,
}


def normalized_text(text):
    return " ".join((text or "").split())


def speaking_seconds(text, chars_per_second, rate_percent=100):
    """Estimated speaking time. rate_percent 100 is the calibrated pace."""
    count = len(normalized_text(text))
    if count <= 0:
        return 0.0
    pace = float(chars_per_second) * (float(rate_percent) / 100.0)
    if pace <= 0:
        raise ValueError("chars_per_second must be positive")
    return count / pace


def chars_per_second_for(provider_id, measured=None):
    if measured:
        try:
            value = float(measured)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    return DEFAULT_CHARS_PER_SECOND.get(provider_id or "windows", 14.0)


def slot_seconds(descriptions, index, video_duration=None):
    """Seconds the narration may occupy.

    The description's own end is the silence the app already reserved.
    The next description's start is the hard stop. The slot is the tighter
    of those two. The last description uses its own duration, or the time
    left in the video when that is known and shorter.
    """
    start, end, _text = descriptions[index]
    own = max(0.0, float(end) - float(start))
    if index + 1 < len(descriptions):
        gap = float(descriptions[index + 1][0]) - float(start)
    elif video_duration is not None:
        gap = float(video_duration) - float(start)
    else:
        gap = own
    if gap < 0:
        gap = 0.0
    if own > 0 and gap > 0:
        return min(own, gap)
    return max(own, gap)


def fit_report(descriptions, index, chars_per_second, rate_percent=100, video_duration=None):
    text = descriptions[index][2]
    need = speaking_seconds(text, chars_per_second, rate_percent)
    slot = slot_seconds(descriptions, index, video_duration)
    return {
        "index": index,
        "need": need,
        "slot": slot,
        "too_long": need > slot + 0.05 and need > 0,
        "text": text,
    }


def long_descriptions(descriptions, chars_per_second, rate_percent=100, video_duration=None):
    reports = []
    for index in range(len(descriptions)):
        report = fit_report(descriptions, index, chars_per_second, rate_percent, video_duration)
        if report["too_long"]:
            reports.append(report)
    return reports


def format_seconds(value, language_code):
    text = f"{float(value):.1f}"
    if (language_code or "").lower().startswith("pt"):
        text = text.replace(".", ",")
    return text


def calibrate_chars_per_second(text, audio_seconds):
    """Measured pace: characters of `text` divided by the wav duration."""
    count = len(normalized_text(text))
    duration = float(audio_seconds)
    if count <= 0 or duration <= 0:
        raise ValueError("measurement needs text and a positive duration")
    return count / duration
