"""Fail if a build artifact contains an API key.

Short prefixes such as ``xai-`` and ``AIza`` occur inside LZMA-compressed
installers by chance, and ``xai-`` is also the start of the model id
``xai-tts``. A hit has to be a full key. Zip files are opened and their
members are scanned. An NSIS installer is not scanned as raw bytes: its
payload is LZMA, and those same files are already in the dist folder.
"""
import sys
import zipfile
from pathlib import Path

BASE62 = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
TOKEN = BASE62 | set(b"_-")


def _token_at(data, index, prefix, minimum, alphabet):
    end = index + len(prefix)
    count = 0
    limit = end + minimum
    if limit > len(data):
        return False
    while end < len(data) and data[end] in alphabet:
        count += 1
        end += 1
        if count >= minimum:
            return True
    return False


def _find_token(data, prefix, minimum, alphabet):
    start = 0
    while True:
        index = data.find(prefix, start)
        if index < 0:
            return False
        if _token_at(data, index, prefix, minimum, alphabet):
            return True
        start = index + len(prefix)


def hits(data):
    """Names of key shapes present in data. Short prefixes alone are ignored."""
    found = []
    # xAI keys are "xai-" plus a long base62 secret. "xai-tts" is a model id.
    if _find_token(data, b"xai-", 70, BASE62):
        found.append("xai-")
    # Google API keys are "AIza" plus 35 url-safe characters.
    if _find_token(data, b"AIza", 35, TOKEN):
        found.append("AIza")
    if _find_token(data, b"sk-ant-", 20, TOKEN):
        found.append("sk-ant-")
    if _find_token(data, b"sk-proj-", 20, TOKEN):
        found.append("sk-proj-")
    start = 0
    while True:
        index = data.find(b"sk-", start)
        if index < 0:
            break
        if data.startswith(b"sk-ant-", index) or data.startswith(b"sk-proj-", index):
            start = index + 3
            continue
        if _token_at(data, index, b"sk-", 20, BASE62):
            found.append("sk-")
            break
        start = index + 3
    return found


def _is_nsis_installer(data):
    return data.startswith(b"MZ") and b"Nullsoft" in data[:65536]


def scan_bytes(label, data):
    found = hits(data)
    if found:
        return [f"{label}: {', '.join(found)}"]
    return []


def scan_zip(path):
    failures = []
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        return [f"{path}: {exc}"]
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            try:
                data = archive.read(info)
            except Exception as exc:
                failures.append(f"{path}:{info.filename}: {exc}")
                continue
            failures.extend(scan_bytes(f"{path}:{info.filename}", data))
    return failures


def scan_path(path):
    path = Path(path)
    failures = []
    files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
    for item in files:
        try:
            if zipfile.is_zipfile(item):
                failures.extend(scan_zip(item))
                continue
            data = item.read_bytes()
        except OSError as exc:
            failures.append(f"{item}: {exc}")
            continue
        if _is_nsis_installer(data):
            print(f"skipping compressed installer {item}")
            continue
        failures.extend(scan_bytes(item, data))
    return failures


def main(argv):
    if len(argv) < 2:
        raise SystemExit("usage: scan_for_secrets.py PATH [PATH...]")
    failures = []
    for raw in argv[1:]:
        failures.extend(scan_path(raw))
    if failures:
        raise SystemExit("API key material in build output:\n" + "\n".join(failures))
    print("no API keys in " + ", ".join(argv[1:]))


if __name__ == "__main__":
    main(sys.argv)
