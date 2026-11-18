"""SAPI voice tokens. One bad Language value must not drop the rest of the list."""


def parse_sapi_language(value):
    """LCIDs from a SAPI Language attribute. '409;9' is two values, not an error."""
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    found = []
    for part in text.replace(",", ";").split(";"):
        token = part.strip()
        if not token:
            continue
        if token.lower().startswith("0x"):
            token = token[2:]
        try:
            found.append(int(token, 16))
        except ValueError:
            continue
    return found


def voice_record(description, token_id, language=""):
    """One voice, or None if this token cannot be read."""
    try:
        parse_sapi_language(language)
        name = str(description or "").strip() or str(token_id or "").strip()
        voice_id = str(token_id or "").strip()
        if not name or not voice_id:
            return None
        return {"name": name, "id": voice_id}
    except Exception:
        return None


def collect_voice_records(records):
    voices = []
    seen = set()
    for record in records or []:
        try:
            item = voice_record(record.get("description"), record.get("id"), record.get("language"))
        except Exception:
            item = None
        if not item or item["id"] in seen:
            continue
        seen.add(item["id"])
        voices.append(item)
    return voices
