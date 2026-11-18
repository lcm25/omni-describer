"""Secret scan: full key shapes, zip members, and no LZMA false positive."""
import zipfile
from pathlib import Path

from installer.scan_for_secrets import hits, scan_path


def test_shapes():
    assert hits(b"xai-tts") == []
    assert hits(b"prefix xai-" + b"a" * 69) == []
    assert hits(b"xai-" + b"a" * 70) == ["xai-"]
    assert hits(b"AIza") == []
    assert hits(b"AIza" + b"B" * 35) == ["AIza"]
    assert hits(b"sk-ant-user") == []
    assert hits(b"sk-ant-" + b"c" * 20) == ["sk-ant-"]
    assert hits(b"sk-proj-" + b"d" * 20) == ["sk-proj-"]
    assert hits(b"sk-" + b"e" * 19) == []
    assert hits(b"sk-" + b"e" * 20) == ["sk-"]


def test_zip_and_installer(tmp):
    plain = tmp / "note.txt"
    plain.write_bytes(b"the model is xai-tts and nothing else")
    archive = tmp / "Descritudo-portable.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(plain, "note.txt")
    assert scan_path(archive) == []

    leaked = tmp / "leak.txt"
    leaked.write_bytes(b"xai-" + b"f" * 70)
    leaked_zip = tmp / "leaked.zip"
    with zipfile.ZipFile(leaked_zip, "w") as zf:
        zf.write(leaked, "leak.txt")
    found = scan_path(leaked_zip)
    assert len(found) == 1 and "xai-" in found[0] and "leak.txt" in found[0]

    setup = tmp / "Descritudo-Setup.exe"
    setup.write_bytes(b"MZ" + b"Nullsoft" + b"xai-" * 50 + b"AIza" * 50)
    assert scan_path(setup) == []

    real = tmp / "app.py"
    real.write_bytes(b"KEY = 'sk-ant-" + b"g" * 20 + b"'\n")
    assert scan_path(real)


def main():
    test_shapes()
    root = Path(__file__).resolve().parent
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        test_zip_and_installer(Path(directory))
    repo_hits = []
    for folder in ("audio_describer", "installer"):
        repo_hits.extend(scan_path(root / folder))
    assert repo_hits == [], repo_hits
    print("secret scan checks passed")


if __name__ == "__main__":
    main()
