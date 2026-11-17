"""Fail if a build artifact contains an API key."""
import sys
from pathlib import Path

PATTERNS = (
    b"AIza",
    b"sk-ant-",
    b"sk-proj-",
    b"xai-",
)


def hits(data):
    found = []
    for pattern in PATTERNS:
        if pattern in data:
            found.append(pattern.decode("ascii"))
    # OpenAI secret keys are "sk-" plus a long token. Ignore the shorter markers above.
    start = 0
    while True:
        index = data.find(b"sk-", start)
        if index < 0:
            break
        token = data[index:index + 12]
        if token.startswith(b"sk-ant-") or token.startswith(b"sk-proj-"):
            start = index + 3
            continue
        rest = data[index + 3:index + 24]
        if len(rest) >= 20 and all(chr(b) in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" for b in rest):
            found.append("sk-")
            break
        start = index + 3
    return found


def scan_path(path):
    path = Path(path)
    failures = []
    files = [path] if path.is_file() else [item for item in path.rglob("*") if item.is_file()]
    for item in files:
        try:
            data = item.read_bytes()
        except OSError as exc:
            failures.append(f"{item}: {exc}")
            continue
        found = hits(data)
        if found:
            failures.append(f"{item}: {', '.join(found)}")
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
