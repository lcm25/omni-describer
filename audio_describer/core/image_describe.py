"""Ask the selected analysis model to describe image frames. No network in the builders."""


class ImageDescribeError(Exception):
    pass


def gemini_image_parts(prompt, frames):
    """Plain structure a test can inspect. The live call turns this into SDK parts."""
    parts = []
    total = len(frames or [])
    for frame in frames or []:
        if total > 1:
            count = int(frame.get("count") or total)
            parts.append({"text": f"Quadro {int(frame['index']) + 1} de {count}."})
        parts.append({
            "inline_data": {"mime_type": "image/jpeg", "byte_length": len(frame.get("jpeg") or b"")},
        })
    parts.append({"text": prompt})
    return parts


def image_request(provider_id, model, api_key, prompt, frames):
    from .analysis_providers import build_request
    if provider_id == "local":
        return {"provider": "local", "offline": True, "model": model}
    if provider_id == "twelvelabs":
        raise ImageDescribeError("twelvelabs")
    if provider_id == "gemini":
        return {"provider": "gemini", "model": model, "parts": gemini_image_parts(prompt, frames)}
    timed = []
    for frame in frames or []:
        item = dict(frame)
        item.setdefault("time", float(frame.get("index") or 0))
        timed.append(item)
    method, url, headers, body = build_request(
        provider_id, model, api_key, "", prompt, frames=timed, json_mode=False,
    )
    return {"provider": provider_id, "method": method, "url": url, "headers": headers, "body": body}


def describe_frames(frames, prompt):
    """One network call. Returns the model's text."""
    from ..models import config_model
    from .analysis_providers import active_analysis_provider, parse_chat_text, post_json
    from .audio_describer import _analysis_api_key, _analysis_model_name

    provider_id = active_analysis_provider(config_model.get_setting)
    model = _analysis_model_name(provider_id)
    from ..utils.logger import app_logger
    from .analysis_providers import job_log_line
    app_logger.info(job_log_line(provider_id, model))
    if provider_id == "local":
        from .local_model import describe_local
        return describe_local(frames, prompt)
    if provider_id == "twelvelabs":
        raise ImageDescribeError("twelvelabs")
    if provider_id == "gemini":
        return _describe_with_gemini(model, prompt, frames)
    prepared = image_request(provider_id, model, _analysis_api_key(provider_id), prompt, frames)
    payload = post_json(prepared["url"], prepared["headers"], prepared["body"])
    text = (parse_chat_text(payload) or "").strip()
    if not text:
        raise ImageDescribeError("empty")
    return text


def _describe_with_gemini(model, prompt, frames):
    from google.genai import types
    from . import gemini_helpers as gemini

    parts = []
    total = len(frames)
    for frame in frames:
        if total > 1:
            count = int(frame.get("count") or total)
            parts.append(f"Quadro {int(frame['index']) + 1} de {count}.")
        parts.append(types.Part.from_bytes(data=frame["jpeg"], mime_type="image/jpeg"))
    parts.append(prompt)
    client = gemini.get_gemini_client()
    config = gemini.build_generation_config(is_json_response=False, enable_thinking=False)
    response = gemini.generate_content_with_retry(client, model=model, contents=parts, config=config)
    text, success = gemini.process_gemini_response(response, None)
    if not success or not (text or "").strip():
        raise ImageDescribeError("empty")
    return text.strip()
