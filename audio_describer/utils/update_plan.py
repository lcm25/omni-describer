"""Decide whether a GitHub release is newer and which file to download. No network."""
from packaging.version import InvalidVersion, Version


def parse_version(value):
    text = str(value or "").strip()
    if text.lower().startswith("v"):
        text = text[1:]
    if not text:
        return None
    try:
        return Version(text)
    except InvalidVersion:
        return None


def is_newer(remote, current):
    remote_version = parse_version(remote)
    current_version = parse_version(current)
    if remote_version is None or current_version is None:
        return False
    return remote_version > current_version


def asset_filename(app_name, portable):
    if portable:
        return f"{app_name}-portable.zip"
    return f"{app_name}-Setup.exe"


def select_asset(assets, filename):
    for asset in assets or []:
        if asset.get("name") == filename:
            return asset
    return None


def skip_portable_member(filename):
    """User settings beside a portable copy must survive the extract."""
    parts = str(filename or "").replace("\\", "/").split("/")
    if any(part.lower() == "dados" for part in parts):
        return True
    name = parts[-1].lower() if parts else ""
    return name in {
        "settings.dat", "settings.dat2", "settings.dat.json",
        "key.salt", "prompts.json", "voices.json",
    }


def sha256_from_sums(text, filename):
    stripped = (text or "").strip()
    if len(stripped) == 64 and all(c in "0123456789abcdefABCDEF" for c in stripped):
        return stripped.lower()
    for line in stripped.splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        name = parts[-1].lstrip("*").replace("\\", "/").rsplit("/", 1)[-1]
        if name == filename:
            return parts[0].lower()
    return None
