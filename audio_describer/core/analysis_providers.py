"""Video-analysis providers other than a full Gemini upload.

Gemini keeps the existing native-video path. The others receive a small set
of JPEG frames (ffmpeg) plus the timestamp of each frame. That is weaker than
watching the video: motion between frames and most of the soundtrack are absent
unless the caller also passes a transcript.
"""
import base64
import json
import os
import tempfile

from ..utils.logger import app_logger
from ..utils.system_utils import get_ffmpeg_path, run_command

# id, translated label msgid, whether the API accepts a video file natively
ANALYSIS_PROVIDERS = (
    {"id": "gemini", "label": "Gemini", "native_video": True},
    {"id": "openai", "label": "OpenAI", "native_video": False},
    {"id": "xai", "label": "xAI", "native_video": False},
    {"id": "anthropic", "label": "Anthropic", "native_video": False},
    {"id": "qwen", "label": "Qwen (DashScope)", "native_video": False},
    {"id": "openrouter", "label": "OpenRouter", "native_video": False},
    {"id": "twelvelabs", "label": "Twelve Labs", "native_video": True},
    {"id": "local", "label": "Local (on this computer, offline)", "native_video": False},
)

FALLBACK_MODELS = {
    "gemini": ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"),
    "openai": ("gpt-4o", "gpt-4o-mini"),
    "xai": ("grok-2-vision-1212", "grok-2-vision"),
    "anthropic": ("claude-sonnet-4-5", "claude-3-5-sonnet-latest"),
    "qwen": ("qwen-vl-max", "qwen2.5-vl-72b-instruct"),
    "openrouter": ("google/gemini-2.5-flash", "openai/gpt-4o"),
    "twelvelabs": ("pegasus1.2",),
    "local": ("qwen25vl-3b", "qwen25vl-7b", "gemma3-4b", "gemma3-12b"),
}

CUSTOM_MODEL = "__custom__"


def ui_label(text):
    from ..i18n_setup import _ as tr
    return {
        "Gemini": tr("Gemini"),
        "OpenAI": tr("OpenAI"),
        "xAI": tr("xAI"),
        "Anthropic": tr("Anthropic"),
        "Qwen (DashScope)": tr("Qwen (DashScope)"),
        "OpenRouter": tr("OpenRouter"),
        "Twelve Labs": tr("Twelve Labs"),
        "Local (on this computer, offline)": tr("Local (on this computer, offline)"),
    }.get(text, text)
MAX_FRAMES = 8


def endpoint_for(provider_id):
    from .gemini_api import gemini_api_root
    return {
        "openai": "https://api.openai.com/v1/chat/completions",
        "xai": "https://api.x.ai/v1/chat/completions",
        "anthropic": "https://api.anthropic.com/v1/messages",
        "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        "twelvelabs": "https://api.twelvelabs.io/v1.3/generate",
        "gemini": gemini_api_root() + "/models",
    }[provider_id]


def auth_headers(provider_id, api_key):
    key = (api_key or "").strip()
    if not key:
        raise ValueError("API key required")
    if provider_id == "gemini":
        return {"x-goog-api-key": key}
    if provider_id == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    if provider_id == "twelvelabs":
        return {"x-api-key": key}
    return {"Authorization": f"Bearer {key}"}


def sample_frame_times(duration_sec, count=MAX_FRAMES):
    duration = float(duration_sec or 0)
    if duration <= 0:
        return [0.0]
    count = max(1, min(int(count), MAX_FRAMES))
    if count == 1:
        return [min(0.5, duration / 2.0)]
    step = duration / count
    return [min(duration - 0.05, (index + 0.5) * step) for index in range(count)]


def extract_frames(video_path, times):
    """Return [{time, jpeg_bytes}, ...] using ffmpeg. Missing frames are skipped."""
    ffmpeg = get_ffmpeg_path("ffmpeg")
    frames = []
    for stamp in times:
        handle = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        handle.close()
        command = [
            ffmpeg, "-y", "-ss", f"{stamp:.3f}", "-i", video_path,
            "-frames:v", "1", "-q:v", "5", handle.name,
        ]
        try:
            result = run_command(command)
            if result.returncode == 0 and os.path.isfile(handle.name) and os.path.getsize(handle.name) > 0:
                with open(handle.name, "rb") as image:
                    frames.append({"time": float(stamp), "jpeg": image.read()})
            else:
                app_logger.warning("Frame extract failed at %.2fs: %s", stamp, (result.stderr or "")[:300])
        finally:
            if os.path.exists(handle.name):
                os.remove(handle.name)
    return frames


def _mmss(seconds):
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def openai_style_body(model, system_text, user_text, frames, json_mode=True):
    content = [{"type": "text", "text": user_text}]
    for frame in frames or []:
        encoded = base64.b64encode(frame["jpeg"]).decode("ascii")
        content.append({"type": "text", "text": f"Frame at {_mmss(frame['time'])}."})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
        })
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": content},
        ],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    return body


def anthropic_body(model, system_text, user_text, frames):
    content = []
    for frame in frames or []:
        content.append({"type": "text", "text": f"Frame at {_mmss(frame['time'])}."})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.b64encode(frame["jpeg"]).decode("ascii"),
            },
        })
    content.append({"type": "text", "text": user_text})
    return {
        "model": model,
        "max_tokens": 4096,
        "system": system_text,
        "messages": [{"role": "user", "content": content}],
    }


def twelvelabs_generate_body(video_id, prompt):
    return {"video_id": video_id, "prompt": prompt}


def gemini_models_url():
    from .gemini_api import gemini_api_root
    return gemini_api_root() + "/models?pageSize=1000"


def filter_gemini_models(payload, require_tts=False):
    """Keep models that can generateContent. TTS models are the ones with 'tts' in the id."""
    found = []
    for item in (payload or {}).get("models") or []:
        name = (item.get("name") or "").replace("models/", "")
        methods = item.get("supportedGenerationMethods") or item.get("supported_actions") or []
        if methods and "generateContent" not in methods and "generate_content" not in methods:
            continue
        is_tts = "tts" in name.lower()
        if require_tts != is_tts:
            continue
        if not name.startswith("gemini-"):
            continue
        label = item.get("displayName") or item.get("display_name") or name
        found.append({"id": name, "name": label})
    return found


def parse_chat_text(payload):
    """Text from an OpenAI-style or Anthropic message response."""
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if choices:
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    content = payload.get("content")
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    if isinstance(content, str):
        return content
    data = payload.get("data")
    if isinstance(data, str):
        return data
    return ""


def build_request(provider_id, model, api_key, system_text, user_text, frames=None, json_mode=True):
    headers = auth_headers(provider_id, api_key)
    headers["Content-Type"] = "application/json"
    if provider_id == "anthropic":
        body = anthropic_body(model, system_text, user_text, frames)
    elif provider_id == "twelvelabs":
        body = twelvelabs_generate_body("", system_text + "\n" + user_text)
    elif provider_id in ("openai", "xai", "qwen", "openrouter"):
        body = openai_style_body(model, system_text, user_text, frames, json_mode=json_mode)
    else:
        raise KeyError(provider_id)
    return "POST", endpoint_for(provider_id), headers, body


def active_analysis_provider(settings_getter):
    value = settings_getter("analysis_provider") or "gemini"
    return value if any(item["id"] == value for item in ANALYSIS_PROVIDERS) else "gemini"


def post_json(url, headers, body, timeout=120):
    import urllib.error
    import urllib.request
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    if not raw:
        return {}
    return json.loads(raw)
