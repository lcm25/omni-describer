"""Ask the active analysis model for shorter narration lines. Nothing is applied by itself."""
import json
import re


def build_shorten_prompt(text, language_name, max_seconds, chars_per_second, neighbours, glossary):
    max_chars = max(8, int(float(max_seconds) * float(chars_per_second)))
    before = neighbours.get("before") or ""
    after = neighbours.get("after") or ""
    names = []
    for item in glossary or []:
        if isinstance(item, dict):
            name = item.get("name") or item.get("id") or ""
            if name:
                names.append(str(name))
    return {
        "max_characters": max_chars,
        "system": (
            "You shorten audio-description lines so they can be spoken inside a time slot. "
            "Keep the essential visual meaning. Do not add facts. Reply with JSON only: "
            '{"alternatives": ["...", "...", "..."]} with exactly 3 strings.'
        ),
        "user": (
            f"Language: {language_name}\n"
            f"Maximum spoken length: {max_seconds:.1f} seconds, about {max_chars} characters.\n"
            f"Previous line: {before}\n"
            f"Next line: {after}\n"
            f"Character names: {', '.join(names) if names else '(none)'}\n"
            f"Original line:\n{text}\n"
        ),
    }


def parse_alternatives(raw_text, limit=3):
    """Pull up to `limit` shorter strings out of a model reply."""
    if not raw_text or not str(raw_text).strip():
        return []
    text = str(raw_text).strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    alternatives = []
    if start != -1 and end > start:
        try:
            payload = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            values = payload.get("alternatives") or payload.get("options") or payload.get("suggestions") or []
            if isinstance(values, list):
                alternatives = [str(item).strip() for item in values if str(item).strip()]
    if not alternatives:
        lines = [line.strip(" -\t") for line in str(raw_text).splitlines()]
        alternatives = [line for line in lines if line and not line.startswith("{") and not line.startswith("```")]
    unique = []
    for item in alternatives:
        if item not in unique:
            unique.append(item)
    return unique[:limit]
