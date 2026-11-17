"""Fail if an NSIS installer stored Portuguese text as cp1252 mojibake.

Usage: python installer/check_installer_strings.py path/to/Setup.exe

The dialog text is compressed. The version resource is not, and it contains
"licença" and "Adaptação". A UTF-8 script read as cp1252 turns those into
"licenÃ§a" and "AdaptaÃ§Ã£o".
"""
import sys
from pathlib import Path


def _latin(code):
    if code in (9, 10, 13, 32):
        return True
    if 33 <= code <= 126:
        return True
    if 0xC0 <= code <= 0xFF or code in (0xA0, 0xAA, 0xBA, 0xB0):
        return True
    return False


def utf16_strings(data, minimum=8):
    found = []
    current = []
    index = 0
    while index + 1 < len(data):
        code = data[index] | (data[index + 1] << 8)
        if _latin(code):
            current.append(chr(code))
            index += 2
            continue
        if len(current) >= minimum:
            text = "".join(current)
            letters = sum(ch.isalpha() or ch == " " for ch in text)
            if letters >= len(text) * 0.55:
                found.append(text)
        current = []
        index += 2
    if len(current) >= minimum:
        text = "".join(current)
        if sum(ch.isalpha() or ch == " " for ch in text) >= len(text) * 0.55:
            found.append(text)
    return found


def check_exe(path):
    data = Path(path).read_bytes()
    strings = utf16_strings(data)
    bad = [item for item in strings if "Ã" in item]
    if bad:
        sample = "\n".join(item[:160] for item in bad[:8])
        raise SystemExit(f"Installer strings contain mojibake 'Ã':\n{sample}")
    joined = "\n".join(strings)
    for word in ("licença", "Adaptação"):
        if word not in joined:
            raise SystemExit(f"Installer is missing the UTF-16 string {word!r}")
    print(f"installer strings ok ({path})")


def main(argv):
    if len(argv) != 2:
        raise SystemExit("usage: check_installer_strings.py SETUP.exe")
    check_exe(argv[1])


if __name__ == "__main__":
    main(sys.argv)
