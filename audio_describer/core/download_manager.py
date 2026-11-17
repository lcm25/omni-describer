"""Resumable file download with a SHA256 check. Tests pass a fake opener."""
import hashlib
import os
import shutil
from pathlib import Path


class DownloadError(Exception):
    pass


class DiskSpaceError(DownloadError):
    pass


class ChecksumError(DownloadError):
    pass


class Cancelled(DownloadError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_space(folder, needed_bytes):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(folder).free
    if free < int(needed_bytes):
        raise DiskSpaceError(f"need {needed_bytes} bytes, free {free}")
    return free


def _default_opener(url, headers):
    import urllib.request
    request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request, timeout=120)
    status = getattr(response, "status", 200)
    return status, dict(response.headers.items()), response


def download_file(url, dest, expected_sha256, expected_size, on_progress=None, cancel=None, opener=None):
    """Download to dest. A sibling .part file is resumed with HTTP Range."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    expected_sha256 = (expected_sha256 or "").lower()
    expected_size = int(expected_size)
    if dest.is_file() and dest.stat().st_size == expected_size and sha256_file(dest) == expected_sha256:
        if on_progress:
            on_progress(expected_size, expected_size)
        return dest

    partial = dest.with_name(dest.name + ".part")
    have = partial.stat().st_size if partial.is_file() else 0
    if have > expected_size:
        partial.unlink()
        have = 0
    ensure_space(dest.parent, expected_size - have + 50 * 1024 * 1024)
    headers = {}
    if have:
        headers["Range"] = f"bytes={have}-"
    status, response_headers, body = (opener or _default_opener)(url, headers)
    if have and status not in (200, 206):
        raise DownloadError(f"resume failed: HTTP {status}")
    if status == 200 and have:
        have = 0
    mode = "ab" if have and status == 206 else "wb"
    if mode == "wb":
        have = 0
    done = have
    try:
        with open(partial, mode) as handle:
            while True:
                if cancel and cancel():
                    raise Cancelled("cancelled")
                chunk = body.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(min(done, expected_size), expected_size)
    finally:
        close = getattr(body, "close", None)
        if close:
            close()
    if cancel and cancel():
        raise Cancelled("cancelled")
    digest = sha256_file(partial)
    if digest != expected_sha256:
        partial.unlink(missing_ok=True)
        raise ChecksumError(digest)
    partial.replace(dest)
    return dest
