"""Fetch model ids off the UI thread. Tests can pass a fake opener."""
import json
import threading

REFRESH_TIMEOUT = 20


class MissingKey(Exception):
    pass


def call_with_timeout(fn, timeout=REFRESH_TIMEOUT):
    """Run fn on a worker thread. Raise TimeoutError if it is still running."""
    box = {}

    def run():
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
        box["thread"] = threading.get_ident()
        try:
            box["value"] = fn()
        except Exception as exc:
            box["error"] = exc

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise TimeoutError("timeout")
    if "error" in box:
        raise box["error"]
    return box.get("value")


def fill_choice_in_place(choice, labels, ids, keep_id):
    """Replace items on the same control. Does not create a new combo or move focus."""
    choice.Clear()
    for label in labels:
        choice.Append(label)
    if not ids:
        return choice
    try:
        index = list(ids).index(keep_id)
    except ValueError:
        index = 0
    choice.SetSelection(index)
    return choice


def ids_to_show(cached, builtin):
    if cached:
        return list(cached)
    return list(builtin)


def is_vision_model(provider_id, model_id):
    text = (model_id or "").lower()
    if any(word in text for word in ("embed", "whisper", "tts", "audio", "dall-e", "moderation", "realtime")):
        return False
    if provider_id == "gemini":
        return text.startswith("gemini")
    if provider_id == "openai":
        return any(token in text for token in ("gpt-4o", "gpt-4.1", "gpt-5", "vision"))
    if provider_id == "anthropic":
        return "claude" in text
    if provider_id == "xai":
        return "grok" in text
    if provider_id == "qwen":
        return "vl" in text or "qwen" in text
    if provider_id == "openrouter":
        return any(token in text for token in ("gemini", "gpt-4o", "claude", "vision", "/vl"))
    return False


def choose_ids(provider_id, fetched, builtin, vision=True):
    fetched = [item for item in (fetched or []) if item]
    if vision:
        picked = [item for item in fetched if is_vision_model(provider_id, item)]
    else:
        builtin_set = set(builtin)
        picked = [item for item in fetched if item in builtin_set or "tts" in item.lower()]
    return picked or list(builtin)


def analysis_list_request(provider_id, api_key):
    from .analysis_providers import auth_headers, gemini_models_url
    headers = auth_headers(provider_id, api_key)
    urls = {
        "gemini": gemini_models_url(),
        "openai": "https://api.openai.com/v1/models",
        "xai": "https://api.x.ai/v1/models",
        "anthropic": "https://api.anthropic.com/v1/models",
        "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models",
        "openrouter": "https://openrouter.ai/api/v1/models",
    }
    if provider_id not in urls:
        return None
    return "GET", urls[provider_id], headers


def narration_list_request(provider_id, api_key):
    from .narration_requests import auth_headers
    if provider_id not in ("openai", "gemini", "elevenlabs"):
        return None
    headers = auth_headers(provider_id, api_key)
    from .analysis_providers import gemini_models_url
    urls = {
        "openai": "https://api.openai.com/v1/models",
        "gemini": gemini_models_url(),
        "elevenlabs": "https://api.elevenlabs.io/v1/models",
    }
    return "GET", urls[provider_id], headers


def _ids_from_payload(provider_id, payload):
    if not isinstance(payload, dict):
        return []
    if provider_id == "gemini":
        found = []
        for item in payload.get("models") or []:
            name = (item.get("name") or "").replace("models/", "")
            if name:
                found.append(name)
        return found
    rows = payload.get("data") or payload.get("models") or []
    found = []
    for item in rows:
        if isinstance(item, str):
            found.append(item)
        elif isinstance(item, dict):
            model_id = item.get("id") or item.get("model_id") or item.get("name") or ""
            if model_id:
                found.append(str(model_id).replace("models/", ""))
    return found


def fetch_ids(request, timeout=REFRESH_TIMEOUT, opener=None):
    if request is None:
        return []
    method, url, headers = request
    if opener:
        payload = opener(method, url, headers, timeout)
    else:
        import urllib.request
        req = urllib.request.Request(url, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace") or "{}")
    return payload
