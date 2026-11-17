"""Turn a description line into a WAV file with the selected narration provider.

Windows voices stay on the existing SAPI / OneCore path. Piper runs piper.exe.
Cloud providers use the request builders in narration_requests.
"""
import json
import os
import shutil
import subprocess
import tempfile
import wave

from ..models import config_model
from ..utils.logger import app_logger
from ..utils.system_utils import get_ffmpeg_path
from . import narration_requests as requests


class NarrationError(Exception):
    pass

PROVIDER_SETTING = "narration_provider"
MODEL_SETTING = "narration_model"
VOICE_SETTING = "narration_voice"


def current_provider():
    value = config_model.get_setting(PROVIDER_SETTING) or "windows"
    return value if any(item["id"] == value for item in requests.PROVIDERS) else "windows"


def _api_key(provider_id):
    if provider_id == "gemini":
        return config_model.get_setting("user_gemini_api_key") or ""
    if provider_id == "openai":
        return config_model.get_setting("user_openai_api_key") or ""
    keys = config_model.get_setting("narration_api_keys") or {}
    if isinstance(keys, dict):
        return keys.get(provider_id) or ""
    return ""


def _write_wav_header(pcm, sample_rate, path):
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(pcm)


def _ffmpeg_to_wav(source_path, wav_path):
    ffmpeg = get_ffmpeg_path("ffmpeg")
    result = subprocess.run(
        [ffmpeg, "-y", "-i", source_path, "-ac", "1", wav_path],
        capture_output=True,
    )
    if result.returncode != 0 or not os.path.isfile(wav_path):
        raise NarrationError("Could not convert narration audio to WAV.")


def bytes_to_wav(payload, mime, wav_path, sample_rate=24000):
    """Write provider audio bytes to a WAV file the mixer already understands."""
    mime = (mime or "").lower()
    if payload[:4] == b"RIFF":
        with open(wav_path, "wb") as handle:
            handle.write(payload)
        return
    if "mpeg" in mime or "mp3" in mime or payload[:3] == b"ID3" or payload[:2] == b"\xff\xfb":
        temp = wav_path + ".mp3"
        with open(temp, "wb") as handle:
            handle.write(payload)
        try:
            _ffmpeg_to_wav(temp, wav_path)
        finally:
            if os.path.exists(temp):
                os.remove(temp)
        return
    if mime.startswith("audio/l16") or "pcm" in mime or mime.startswith("audio/raw"):
        rate = sample_rate
        if "rate=" in mime:
            try:
                rate = int(mime.split("rate=")[1].split(";")[0])
            except ValueError:
                rate = sample_rate
        _write_wav_header(payload, rate, wav_path)
        return
    # Last resort: let ffmpeg sniff the container.
    temp = wav_path + ".bin"
    with open(temp, "wb") as handle:
        handle.write(payload)
    try:
        _ffmpeg_to_wav(temp, wav_path)
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def _decode_audio_field(data, mime):
    import base64
    text = (data or "").strip()
    if not text:
        return b""
    if mime == "hex":
        try:
            return bytes.fromhex(text)
        except ValueError:
            return b""
    try:
        return base64.b64decode(text)
    except Exception:
        return b""


def _find_audio(value):
    if isinstance(value, dict):
        data = value.get("data") or value.get("audio") or value.get("audio_data") or value.get("encodedAudio")
        if isinstance(data, str):
            mime = value.get("mimeType") or value.get("mime_type") or ""
            raw = _decode_audio_field(data, "hex" if value.get("output_format") == "hex" else mime)
            if raw and (mime.lower().startswith("audio/") or raw[:4] == b"RIFF" or len(raw) > 64):
                return raw, mime or "audio/wav"
        for child in value.values():
            found = _find_audio(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_audio(child)
            if found:
                return found
    return None


def _http_json(method, url, headers, body, timeout=120):
    import urllib.error
    import urllib.request
    data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode("utf-8"))
    request_headers = dict(headers)
    if body is not None and not isinstance(body, bytes) and "Content-Type" not in request_headers:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            mime = response.headers.get("Content-Type", "")
            return payload, mime
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise NarrationError(f"{exc.code}: {detail}") from exc


def synthesize_cloud(provider_id, text, wav_path):
    model = config_model.get_setting(MODEL_SETTING) or requests.models_for(provider_id)[0][0]
    voice = config_model.get_setting(VOICE_SETTING) or ""
    if not voice:
        builtin = requests.builtin_voices(provider_id, model)
        if builtin:
            voice = builtin[0]["id"]
    style = config_model.get_setting("narration_style") or ""
    region = config_model.get_setting("azure_speech_region") or ""
    rate = config_model.get_setting("narration_rate_percent") or 100
    speed = max(0.7, min(1.5, float(rate) / 100.0))
    method, url, headers, json_body, raw_body = requests.speech_request(
        provider_id, model, voice, text,
        api_key=_api_key(provider_id),
        language="pt-BR",
        style=style,
        azure_region=region,
        speed=speed,
    )
    if provider_id == "mvsep":
        raise NarrationError("MVSEP narration is prepared as form fields, but exporting it needs the separation upload, which this version does not run.")
    body = raw_body if raw_body is not None else json_body
    payload, mime = _http_json(method, url, headers, body)
    if mime.lower().startswith("application/json") or (payload[:1] == b"{"):
        parsed = json.loads(payload.decode("utf-8", errors="replace"))
        found = _find_audio(parsed)
        if not found:
            raise NarrationError("The provider response did not include audio.")
        payload, mime = found
    sample_rate = requests.CARTESIA_RATE if provider_id == "cartesia" else 24000
    bytes_to_wav(payload, mime, wav_path, sample_rate=sample_rate)
    return True


def synthesize_piper(text, wav_path):
    exe = (config_model.get_setting("piper_exe") or "").strip() or shutil.which("piper")
    model = (config_model.get_setting(VOICE_SETTING) or config_model.get_setting("piper_model") or "").strip()
    if not exe or not os.path.isfile(exe):
        raise NarrationError("Piper was not found. Set the piper.exe path in Settings.")
    if not model.lower().endswith(".onnx") or not os.path.isfile(model) or not os.path.isfile(model + ".json"):
        raise NarrationError("Choose a Piper voice (.onnx with the .onnx.json beside it).")
    process = subprocess.run(
        [exe, "--model", model, "--output_file", wav_path],
        input=text.encode("utf-8"),
        capture_output=True,
    )
    if process.returncode != 0 or not os.path.isfile(wav_path):
        detail = (process.stderr or b"").decode("utf-8", errors="replace")[:300]
        raise NarrationError(f"Piper failed. {detail}")
    return True


def list_piper_voices():
    folder = (config_model.get_setting("piper_voices_dir") or "").strip()
    extra = (config_model.get_setting("piper_model") or "").strip()
    files = []
    if folder and os.path.isdir(folder):
        files.extend(
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if name.lower().endswith(".onnx")
        )
    if extra.lower().endswith(".onnx"):
        files.append(extra)
    voices = []
    seen = set()
    for path in files:
        full = os.path.abspath(path)
        if full in seen or not os.path.isfile(full + ".json"):
            continue
        seen.add(full)
        voices.append({"id": full, "name": os.path.splitext(os.path.basename(full))[0]})
    return voices


def _voices_in_payload(data):
    raw_list = []
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        for key in ("voices", "data", "items", "system_voice", "voice_list"):
            if isinstance(data.get(key), list):
                raw_list.extend(data[key])
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                raw_list.extend(value)
    voices = []
    seen = set()
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        voice_id = item.get("voice_id") or item.get("id") or item.get("voiceId") or item.get("ShortName") or item.get("_id") or ""
        name = (
            item.get("display_name") or item.get("displayName") or item.get("name")
            or item.get("LocalName") or item.get("title") or voice_id
        )
        voice_id = str(voice_id)
        if not voice_id or voice_id.lower() in seen:
            continue
        seen.add(voice_id.lower())
        voices.append({"id": voice_id, "name": str(name)})
    return voices


def fetch_remote_voices(provider_id, api_key, model="", azure_region=""):
    """Refresh the full voice catalog. Follows pagination. Network required where a list API exists."""
    from . import narration_requests as requests
    builtin = requests.builtin_voices(provider_id, model)
    if provider_id in ("openai", "deepgram", "mvsep", "windows", "piper"):
        return builtin
    if provider_id == "azure":
        url = requests.azure_base(azure_region) + "/voices/list"
        headers = requests.auth_headers("azure", api_key)
        payload, _mime = _http_json("GET", url, headers, None, timeout=20)
        items = json.loads(payload.decode("utf-8", errors="replace"))
        return requests.merge_voices(builtin, _voices_in_payload(items if isinstance(items, list) else {"voices": items}))
    listed = requests.voice_list_request(provider_id, api_key, model)
    if not listed:
        return builtin
    method, url, headers, body = listed
    voices = []
    seen_urls = set()
    for _page in range(100):
        if not url or url in seen_urls:
            break
        seen_urls.add(url)
        payload, _mime = _http_json(method, url, headers, body, timeout=20)
        data = json.loads(payload.decode("utf-8", errors="replace") or "{}")
        voices.extend(_voices_in_payload(data))
        url = requests.next_voice_page(url, data)
        body = None
        method = "GET"
    return requests.merge_voices(builtin, voices)


def windows_engine_for_model(model):
    if model == "onecore":
        return "onecore"
    if model == "sapi4":
        return "sapi5_32bit"
    return "sapi5"
