"""Request builders for narration TTS providers.

Payloads follow NarraTudo 0.9.5 (ProviderCatalog, Providers, NewProviders,
MoreProviders, XaiProvider). These functions do not touch the network.
"""
import re
from urllib.parse import quote

CARTESIA_VERSION = "2024-06-10"
CARTESIA_RATE = 24000
XAI_MAX_CHARS = 60000

DEEPGRAM_VOICES = (
    ("Bianca", "flux-bianca-pt"),
    ("Bruno", "flux-bruno-pt"),
    ("Claudia", "flux-claudia-pt"),
    ("Leandro", "flux-leandro-pt"),
    ("Marcia", "flux-marcia-pt"),
    ("Mariana", "flux-mariana-pt"),
    ("Marta", "flux-marta-pt"),
    ("Mateus", "flux-mateus-pt"),
    ("Miguel", "flux-miguel-pt"),
    ("Renato", "flux-renato-pt"),
    ("Roberto", "flux-roberto-pt"),
    ("Rodrigo", "flux-rodrigo-pt"),
)

XAI_VOICES = (
    "eve", "ara", "leo", "rex", "sal", "orion", "zagan", "luna", "carina",
    "lux", "perseus", "altair", "helix", "iris", "kepler", "cosmo", "rigel",
    "zenith", "helios", "celeste", "ursa", "sirius", "lumen", "castor",
    "naksh", "atlas",
)

OPENAI_VOICES = (
    "alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx",
    "sage", "shimmer", "verse", "marin", "cedar",
)

# Official Gemini prebuilt studio voices (30). The extended library is extra
# and comes from GET /v1beta/voices with page_token.
GEMINI_PREBUILT_VOICES = (
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
)

# Stable ids. Display names are translated in the UI.
PROVIDERS = (
    {"id": "windows", "label": "Windows voices", "needs_key": False},
    {"id": "piper", "label": "Piper", "needs_key": False},
    {"id": "gemini", "label": "Gemini", "needs_key": True},
    {"id": "elevenlabs", "label": "ElevenLabs", "needs_key": True},
    {"id": "mvsep", "label": "MVSEP", "needs_key": True},
    {"id": "openai", "label": "OpenAI", "needs_key": True},
    {"id": "azure", "label": "Azure Speech", "needs_key": True},
    {"id": "cartesia", "label": "Cartesia", "needs_key": True},
    {"id": "fish", "label": "Fish Audio", "needs_key": True},
    {"id": "minimax", "label": "MiniMax", "needs_key": True},
    {"id": "speechma", "label": "Speechma", "needs_key": True},
    {"id": "xai", "label": "xAI", "needs_key": True},
    {"id": "speechify", "label": "Speechify", "needs_key": True},
    {"id": "deepgram", "label": "Deepgram", "needs_key": True},
    {"id": "murf", "label": "Murf", "needs_key": True},
)

WINDOWS_MODELS = (
    ("onecore", "Windows OneCore"),
    ("sapi5", "SAPI 5"),
    ("sapi4", "SAPI 5 (32-bit voices)"),
)


def provider_by_id(provider_id):
    for item in PROVIDERS:
        if item["id"] == provider_id:
            return item
    raise KeyError(provider_id)


def models_for(provider_id):
    table = {
        "windows": WINDOWS_MODELS,
        "piper": (("piper", "Piper — local ONNX voices"),),
        "gemini": (
            ("gemini-2.5-flash-preview-tts", "Gemini 2.5 Flash TTS"),
            ("gemini-2.5-pro-preview-tts", "Gemini 2.5 Pro TTS"),
        ),
        "elevenlabs": (("eleven_multilingual_v2", "Multilingual v2"), ("eleven_turbo_v2_5", "Turbo v2.5")),
        "mvsep": (
            ("104", "VibeVoice — TTS"),
            ("118", "Qwen3-TTS — custom voice"),
            ("119", "Qwen3-TTS — voice design"),
            ("103", "VibeVoice — voice clone"),
            ("120", "Qwen3-TTS — voice clone"),
        ),
        "openai": (
            ("gpt-4o-mini-tts", "GPT-4o mini TTS"),
            ("tts-1", "TTS-1"),
            ("tts-1-hd", "TTS-1 HD"),
        ),
        "azure": (("azure-neural", "Azure Speech voices"),),
        "cartesia": (("sonic-3.5", "Sonic 3.5"), ("sonic-3", "Sonic 3")),
        "fish": (("s2-pro", "S2 Pro"), ("s1", "S1")),
        "minimax": (
            ("speech-2.6-hd", "Speech 2.6 HD"),
            ("speech-2.6-turbo", "Speech 2.6 Turbo"),
        ),
        "speechma": (("speechma", "Speechma voices"),),
        "xai": (("xai-tts", "xAI text to speech"),),
        "speechify": (("simba-3.5", "Simba 3.5"), ("simba-3.0", "Simba 3.0")),
        "deepgram": (("flux", "Flux TTS"),),
        "murf": (("falcon-2.1", "Falcon 2.1"), ("gen2", "Gen2")),
    }
    return table[provider_id]


def builtin_voices(provider_id, model):
    if provider_id == "openai":
        return [{"id": name, "name": name} for name in OPENAI_VOICES]
    if provider_id == "xai":
        return [{"id": name, "name": name.capitalize()} for name in XAI_VOICES]
    if provider_id == "deepgram":
        return [{"id": voice_id, "name": f"{label} ({voice_id})"} for label, voice_id in DEEPGRAM_VOICES]
    if provider_id == "gemini":
        return [{"id": name, "name": name} for name in GEMINI_PREBUILT_VOICES]
    if provider_id == "mvsep" and model == "104":
        return [
            {"id": "speaker1", "name": "Speaker 1"},
            {"id": "speaker2", "name": "Speaker 2"},
        ]
    return []


def _safe_id(value):
    return bool(re.fullmatch(r"[A-Za-z0-9_.:|-]{1,200}", value or ""))


def auth_headers(provider_id, api_key):
    """Headers NarraTudo's SpeechHttp.Authenticate adds for this provider."""
    if provider_id == "mvsep":
        return {}
    if not api_key or not str(api_key).strip():
        raise ValueError("API key required")
    key = str(api_key).strip()
    if provider_id == "gemini":
        return {"x-goog-api-key": key}
    if provider_id == "elevenlabs":
        return {"xi-api-key": key}
    if provider_id in ("openai", "fish", "minimax", "xai", "speechify", "cartesia"):
        headers = {"Authorization": f"Bearer {key}"}
        if provider_id == "cartesia":
            headers["Cartesia-Version"] = CARTESIA_VERSION
        return headers
    if provider_id == "deepgram":
        return {"Authorization": f"Token {key}"}
    if provider_id == "murf":
        return {"api-key": key}
    if provider_id == "speechma":
        return {"X-API-Key": key}
    if provider_id == "azure":
        return {
            "Ocp-Apim-Subscription-Key": key,
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
        }
    raise KeyError(provider_id)


def azure_base(region):
    if not re.fullmatch(r"[a-z][a-z0-9]{1,31}", region or ""):
        raise ValueError("Azure region must look like brazilsouth")
    return f"https://{region}.tts.speech.microsoft.com/cognitiveservices"


def cartesia_language(language):
    match = re.match(r"^([a-z]{2})(?:[-_][a-z]{2})?$", (language or "").strip().lower())
    return match.group(1) if match else "pt"


def openai_payload(model, voice, text, instructions=""):
    body = {"model": model, "voice": voice, "input": text, "response_format": "wav"}
    if str(model).startswith("gpt-4o-mini-tts") and instructions and instructions.strip():
        body["instructions"] = instructions.strip()
    return body


def azure_ssml(voice, text):
    if not re.fullmatch(r"[a-z]{2,3}-[A-Za-z]{2,4}-[A-Za-z0-9:._-]+", voice or ""):
        raise ValueError("Select an Azure voice")
    lang = "-".join(voice.split("-")[:2])
    safe_voice = (voice or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_text = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">'
        f'<voice name="{safe_voice}">{safe_text}</voice></speak>'
    )


def gemini_tts_payload(model, voice, text, style=""):
    modern = "3" in (model or "") or (model or "").startswith("gemini-3")
    if modern:
        voice_config = {"voice": voice}
        part = {"text": text}
        if style and style.strip():
            part["speech_metadata"] = {"style": style.strip()}
    else:
        voice_config = {"prebuiltVoiceConfig": {"voiceName": voice}}
        part = {"text": (style.strip() + "\n" + text) if style and style.strip() else text}
    return {
        "contents": [{"role": "user", "parts": [part]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": voice_config},
        },
    }


def elevenlabs_payload(model, voice, text):
    if model in ("eleven_v3", "eleven_v4"):
        return {"model_id": model, "inputs": [{"text": text, "voice_id": voice}]}
    return {"text": text, "model_id": model}


def elevenlabs_url(model, voice):
    if model in ("eleven_v3", "eleven_v4"):
        path = "/v1/text-to-dialogue"
    else:
        path = "/v1/text-to-speech/" + quote(voice, safe="")
    return "https://api.elevenlabs.io" + path + "?output_format=mp3_44100_128"


def cartesia_payload(model, voice, text, language="pt-BR"):
    if not _safe_id(voice):
        raise ValueError("Select a Cartesia voice")
    return {
        "model_id": model,
        "transcript": text,
        "voice": {"id": voice},
        "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": CARTESIA_RATE},
        "language": cartesia_language(language),
    }


def fish_payload(voice, text):
    if not _safe_id(voice):
        raise ValueError("Select a Fish Audio voice")
    return {"text": text, "reference_id": voice, "format": "mp3", "latency": "normal"}


def minimax_payload(model, voice, text):
    if not _safe_id(voice):
        raise ValueError("Select a MiniMax voice")
    boost = "Portuguese" if str(voice).startswith("Portuguese_") else "auto"
    return {
        "model": model,
        "text": text,
        "stream": False,
        "language_boost": boost,
        "voice_setting": {"voice_id": voice, "speed": 1, "vol": 1, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
        "output_format": "hex",
    }


def speechma_payload(voice, text):
    return {"text": text, "voice": voice}


def xai_payload(voice, text, language="pt-BR", speed=1.0):
    if not _safe_id(voice):
        raise ValueError("Select an xAI voice")
    if len(text or "") > XAI_MAX_CHARS:
        raise ValueError("xAI accepts at most 60000 characters")
    speed = max(0.7, min(1.5, 1.0 if not speed or speed <= 0 else float(speed)))
    lang = (language or "").strip() or "pt-BR"
    return {
        "text": text,
        "voice_id": voice,
        "language": lang,
        "output_format": {"codec": "wav", "sample_rate": 24000},
        "speed": speed,
    }


def speechify_payload(model, voice, text, language="pt-BR"):
    if not _safe_id(voice):
        raise ValueError("Select a Speechify voice")
    chosen = "simba-3.0" if model == "simba-3.0" else "simba-3.5"
    return {
        "input": text,
        "voice_id": voice,
        "model": chosen,
        "audio_format": "wav",
        "language": language or "pt-BR",
    }


def deepgram_url(voice):
    if not re.fullmatch(r"flux-[a-z]{2,20}-[a-z]{2}(?:-[A-Za-z]{2})?", voice or ""):
        raise ValueError("Select a Deepgram Flux voice")
    return (
        "https://api.deepgram.com/v2/speak?model="
        + quote(voice, safe="")
        + "&encoding=linear16&container=wav&sample_rate=24000"
    )


def murf_payload(model, voice, text, language="pt-BR"):
    chosen_model = model
    chosen_voice = voice or ""
    if "|" in chosen_voice:
        chosen_model, chosen_voice = chosen_voice.split("|", 1)
    if not _safe_id(chosen_voice):
        raise ValueError("Select a Murf voice")
    chosen_model = "gen2" if chosen_model == "gen2" else "falcon-2.1"
    body = {
        "text": text,
        "voiceId": chosen_voice,
        "format": "WAV",
        "sampleRate": 24000,
        "channelType": "MONO",
    }
    if (language or "").lower().startswith("pt"):
        body["locale"] = "pt-BR"
    if chosen_model == "gen2":
        body["modelVersion"] = "GEN2"
        body["encodeAsBase64"] = True
    else:
        body["model"] = "falcon-2.1"
    return chosen_model, body


def mvsep_fields(model, voice, text, style=""):
    """Form fields for MVSEP separation/create. Clone models are refused here."""
    if model in ("103", "120"):
        raise ValueError("MVSEP voice cloning needs a reference recording, which this screen does not collect")
    fields = {"sep_type": str(model), "output_format": "1", "is_demo": "0"}
    if model in ("103", "104"):
        fields["add_opt1"] = "1"
    if model == "104":
        speaker = "2" if voice == "speaker2" else "1"
        flat = (text or "").replace("\r\n", " ").replace("\n", " ")
        fields["add_opt2"] = f"Speaker {speaker}: {flat}"
    elif model in ("118", "119"):
        if not (style or "").strip():
            raise ValueError("This Qwen3-TTS model needs a voice description")
        fields["add_opt1"] = style.strip()
        fields["add_opt2"] = text
    else:
        fields["add_opt2"] = text
    return fields


def speech_request(provider_id, model, voice, text, api_key="", language="pt-BR", style="", azure_region="", speed=1.0):
    """Return method, url, headers, json body or None, and raw body or None."""
    headers = auth_headers(provider_id, api_key) if provider_id not in ("windows", "piper") else {}
    if provider_id == "openai":
        return "POST", "https://api.openai.com/v1/audio/speech", headers, openai_payload(model, voice, text, style), None
    if provider_id == "azure":
        headers = dict(headers)
        headers["Content-Type"] = "application/ssml+xml"
        return "POST", azure_base(azure_region) + "/v1", headers, None, azure_ssml(voice, text).encode("utf-8")
    if provider_id == "gemini":
        from .gemini_api import gemini_api_root
        url = gemini_api_root() + "/models/" + quote(model, safe="") + ":generateContent"
        return "POST", url, headers, gemini_tts_payload(model, voice, text, style), None
    if provider_id == "elevenlabs":
        return "POST", elevenlabs_url(model, voice), headers, elevenlabs_payload(model, voice, text), None
    if provider_id == "cartesia":
        return "POST", "https://api.cartesia.ai/tts/bytes", headers, cartesia_payload(model, voice, text, language), None
    if provider_id == "fish":
        return "POST", "https://api.fish.audio/v1/tts", headers, fish_payload(voice, text), None
    if provider_id == "minimax":
        return "POST", "https://api.minimax.io/v1/t2a_v2", headers, minimax_payload(model, voice, text), None
    if provider_id == "speechma":
        return "POST", "https://speechma.com/api/v1/tts", headers, speechma_payload(voice, text), None
    if provider_id == "xai":
        return "POST", "https://api.x.ai/v1/tts", headers, xai_payload(voice, text, language, speed), None
    if provider_id == "speechify":
        return "POST", "https://api.speechify.ai/v1/audio/speech", headers, speechify_payload(model, voice, text, language), None
    if provider_id == "deepgram":
        return "POST", deepgram_url(voice), headers, {"text": text}, None
    if provider_id == "murf":
        chosen, body = murf_payload(model, voice, text, language)
        url = "https://api.murf.ai/v1/speech/generate" if chosen == "gen2" else "https://global.api.murf.ai/v1/speech/stream"
        return "POST", url, headers, body, None
    if provider_id == "mvsep":
        return "POST", "https://mvsep.com/api/separation/create", {}, None, mvsep_fields(model, voice, text, style)
    raise KeyError(provider_id)


def ui_label(text):
    """Translate a catalog label. Literals stay visible to gettext."""
    from ..i18n_setup import _ as tr
    return {
        "Windows voices": tr("Windows voices"),
        "Piper": tr("Piper"),
        "Gemini": tr("Gemini"),
        "ElevenLabs": tr("ElevenLabs"),
        "MVSEP": tr("MVSEP"),
        "OpenAI": tr("OpenAI"),
        "Azure Speech": tr("Azure Speech"),
        "Cartesia": tr("Cartesia"),
        "Fish Audio": tr("Fish Audio"),
        "MiniMax": tr("MiniMax"),
        "Speechma": tr("Speechma"),
        "xAI": tr("xAI"),
        "Speechify": tr("Speechify"),
        "Deepgram": tr("Deepgram"),
        "Murf": tr("Murf"),
        "Windows OneCore": tr("Windows OneCore"),
        "SAPI 5": tr("SAPI 5"),
        "SAPI 5 (32-bit voices)": tr("SAPI 5 (32-bit voices)"),
        "Piper — local ONNX voices": tr("Piper — local ONNX voices"),
        "Gemini 2.5 Flash TTS": tr("Gemini 2.5 Flash TTS"),
        "Gemini 2.5 Pro TTS": tr("Gemini 2.5 Pro TTS"),
        "Multilingual v2": tr("Multilingual v2"),
        "Turbo v2.5": tr("Turbo v2.5"),
        "VibeVoice — TTS": tr("VibeVoice — TTS"),
        "Qwen3-TTS — custom voice": tr("Qwen3-TTS — custom voice"),
        "Qwen3-TTS — voice design": tr("Qwen3-TTS — voice design"),
        "VibeVoice — voice clone": tr("VibeVoice — voice clone"),
        "Qwen3-TTS — voice clone": tr("Qwen3-TTS — voice clone"),
        "GPT-4o mini TTS": tr("GPT-4o mini TTS"),
        "TTS-1": tr("TTS-1"),
        "TTS-1 HD": tr("TTS-1 HD"),
        "Azure Speech voices": tr("Azure Speech voices"),
        "Sonic 3.5": tr("Sonic 3.5"),
        "Sonic 3": tr("Sonic 3"),
        "S2 Pro": tr("S2 Pro"),
        "S1": tr("S1"),
        "Speech 2.6 HD": tr("Speech 2.6 HD"),
        "Speech 2.6 Turbo": tr("Speech 2.6 Turbo"),
        "Speechma voices": tr("Speechma voices"),
        "xAI text to speech": tr("xAI text to speech"),
        "Simba 3.5": tr("Simba 3.5"),
        "Simba 3.0": tr("Simba 3.0"),
        "Flux TTS": tr("Flux TTS"),
        "Falcon 2.1": tr("Falcon 2.1"),
        "Gen2": tr("Gen2"),
    }.get(text, text)


def voice_list_request(provider_id, api_key, model=""):
    """GET/POST used to refresh the voice list. Returns method, url, headers, json or None."""
    headers = auth_headers(provider_id, api_key)
    if provider_id == "gemini":
        from .gemini_api import gemini_api_root
        return "GET", gemini_api_root() + "/voices?page_size=1000", headers, None
    if provider_id == "elevenlabs":
        return "GET", "https://api.elevenlabs.io/v2/voices?page_size=100", headers, None
    if provider_id == "openai":
        return None
    if provider_id == "azure":
        raise ValueError("Azure voice listing needs a region; call azure voice list separately")
    if provider_id == "cartesia":
        return "GET", "https://api.cartesia.ai/voices?limit=100", headers, None
    if provider_id == "fish":
        return "GET", "https://api.fish.audio/model?page_size=100&page_number=1", headers, None
    if provider_id == "minimax":
        return "POST", "https://api.minimax.io/v1/get_voice", headers, {"voice_type": "all"}
    if provider_id == "speechma":
        return "GET", "https://speechma.com/api/v1/voices", headers, None
    if provider_id == "xai":
        return "GET", "https://api.x.ai/v1/tts/voices", headers, None
    if provider_id == "speechify":
        return "GET", "https://api.speechify.ai/v1/voices?limit=200", headers, None
    if provider_id == "murf":
        chosen = "gen2" if model == "gen2" else "falcon-2.1"
        return "GET", f"https://api.murf.ai/v1/speech/voices?model={chosen}", headers, None
    if provider_id == "deepgram":
        return None
    raise KeyError(provider_id)


def next_voice_page(url, data):
    """Next page URL, or None when this response is the last page."""
    if not isinstance(data, dict) or not url:
        return None
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
    token = data.get("next_page_token") or data.get("nextPageToken")
    if token:
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["page_token"] = token
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    nxt = data.get("next_page")
    if data.get("has_more") and isinstance(nxt, str) and nxt.startswith("http"):
        return nxt
    items = data.get("items") or data.get("data") or data.get("voices") or []
    if not isinstance(items, list) or len(items) < 100:
        return None
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if "page_number" in query:
        query["page_number"] = str(int(query["page_number"]) + 1)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    return None


def merge_voices(first, second):
    """Keep every voice. Earlier entries win when the id repeats."""
    found = []
    seen = set()
    for item in list(first or []) + list(second or []):
        voice_id = str(item.get("id") or "")
        if not voice_id or voice_id.lower() in seen:
            continue
        seen.add(voice_id.lower())
        found.append({"id": voice_id, "name": str(item.get("name") or voice_id)})
    return found


def voice_catalog_report():
    """builtin count and whether Refresh voice list calls a live catalog."""
    live = {
        "gemini": "yes, paginated /v1beta/voices, merged with the 30 prebuilt",
        "elevenlabs": "yes, paginated account library",
        "azure": "yes, full regional voices/list",
        "cartesia": "yes, paginated",
        "fish": "yes, paginated, all languages",
        "minimax": "yes, voice_type=all",
        "speechma": "yes",
        "xai": "yes, merged with the built-in names",
        "speechify": "yes, paginated",
        "murf": "yes, per model",
        "openai": "no voice-list API; the built-in 13 are the catalog",
        "deepgram": "no voice-list API; refresh returns the built-in Flux list",
        "mvsep": "no; two speakers on the VibeVoice model",
        "windows": "local Windows voices, not a cloud catalog",
        "piper": "local .onnx files in the chosen folder",
    }
    rows = []
    for item in PROVIDERS:
        provider_id = item["id"]
        model = models_for(provider_id)[0][0]
        count = len(builtin_voices(provider_id, model))
        rows.append({"id": provider_id, "builtin": count, "live": live[provider_id]})
    return rows
