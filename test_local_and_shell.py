"""Shell verb, single instance, local provider, and the download manager. No real downloads."""
import hashlib
import io
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_describer.core.analysis_providers import ANALYSIS_PROVIDERS, active_analysis_provider
from audio_describer.core.download_manager import (
    ChecksumError,
    DiskSpaceError,
    download_file,
    ensure_space,
)
from audio_describer.core.image_describe import image_request
from audio_describer.core.local_model import LOCAL_MODELS, mtmd_command, parse_timed_lines
from audio_describer.utils import single_instance
from audio_describer.utils.shell_menu import association_names, registry_entries


class _Body:
    def __init__(self, data):
        self._data = data

    def read(self, size):
        chunk = self._data[:size]
        self._data = self._data[size:]
        return chunk

    def close(self):
        pass


def test_shell_menu_covers_perceived_types_and_multi_select():
    names = association_names()
    assert ".webp" in names and ".gif" in names and ".mp4" in names
    assert "image" in names and "video" in names
    rows = registry_entries(r'"C:\Descritudo\Descritudo.exe" "%1"')
    models = [data for _key, name, data in rows if name == "MultiSelectModel"]
    assert models and set(models) == {"Player"}
    commands = [data for key, name, data in rows if key.endswith(r"\command")]
    assert all(data.endswith('"%1"') for data in commands)
    assert any(r"SystemFileAssociations\image\shell" in key for key, _n, _d in rows)
    assert any(r"SystemFileAssociations\.webp\shell" in key for key, _n, _d in rows)


def test_provider_local_stays_offline():
    assert any(item["id"] == "local" for item in ANALYSIS_PROVIDERS)
    assert active_analysis_provider(lambda key: "local" if key == "analysis_provider" else None) == "local"
    prepared = image_request("local", "qwen25vl-3b", "", "descreva", [])
    assert prepared["offline"] is True
    assert "url" not in prepared


def test_timed_lines_and_command():
    parsed = parse_timed_lines("00:01 | Um gato.\n00:04 | Ele pula.", 9)
    assert parsed[0] == (1.0, 4.0, "Um gato.")
    assert parsed[1][0] == 4.0 and parsed[1][2] == "Ele pula."
    prose = parse_timed_lines("Só um parágrafo.", 3)
    assert prose == [(0.0, 3.0, "Só um parágrafo.")]
    command = mtmd_command("llama-mtmd-cli.exe", "m.gguf", "mm.gguf", ["a.jpg"], "olá")
    assert command[0].endswith("llama-mtmd-cli.exe")
    assert "--mmproj" in command and "a.jpg" in command and "-ngl" in command
    assert LOCAL_MODELS[0]["id"] == "qwen25vl-3b"


def test_checksum_and_resume(tmp_path):
    payload = b"abcdefghijklmnopqrstuvwxyz"
    digest = hashlib.sha256(payload).hexdigest()
    dest = tmp_path / "model.gguf"
    seen = {}

    def opener(url, headers):
        seen["headers"] = headers
        start = 0
        if "Range" in headers:
            start = int(headers["Range"].split("=", 1)[1].split("-", 1)[0])
        return 206 if start else 200, {}, _Body(payload[start:])

    partial = tmp_path / "model.gguf.part"
    partial.write_bytes(payload[:10])
    download_file("https://example.invalid/m", dest, digest, len(payload), opener=opener)
    assert dest.read_bytes() == payload
    assert seen["headers"]["Range"] == "bytes=10-"
    try:
        download_file("https://example.invalid/m", tmp_path / "bad.gguf", "0" * 64, 4, opener=lambda url, headers: (200, {}, _Body(b"nope")))
        raise AssertionError("checksum should fail")
    except ChecksumError:
        assert not (tmp_path / "bad.gguf").exists()
        assert not (tmp_path / "bad.gguf.part").exists()


def test_disk_space(tmp_path, monkeypatch=None):
    import audio_describer.core.download_manager as manager
    original = manager.shutil.disk_usage
    manager.shutil.disk_usage = lambda folder: os.statvfs_result((0, 0, 0, 10, 0, 0, 0, 0, 0, 0)) if False else type("U", (), {"free": 5})()
    try:
        try:
            ensure_space(tmp_path, 100)
            raise AssertionError("should reject")
        except DiskSpaceError:
            pass
    finally:
        manager.shutil.disk_usage = original


def test_single_instance(tmp_path):
    received = []
    server = single_instance.listen(received.append, folder=str(tmp_path))
    try:
        assert single_instance.forward(["foto.webp", "clip.mp4"], folder=str(tmp_path))
        for _ in range(20):
            if received:
                break
            time.sleep(0.05)
        assert received == [["foto.webp", "clip.mp4"]]
    finally:
        server.close()


if __name__ == "__main__":
    test_shell_menu_covers_perceived_types_and_multi_select()
    test_provider_local_stays_offline()
    test_timed_lines_and_command()
    import tempfile
    folder = Path(tempfile.mkdtemp())
    test_checksum_and_resume(folder)
    test_disk_space(folder)
    test_single_instance(folder)
    print("local and shell checks passed")
