"""Setup.nsi must be UTF-8 with a BOM so makensis does not read it as ACP."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "installer" / "Setup.nsi"


def main():
    raw = SCRIPT.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "Setup.nsi is missing a UTF-8 BOM"
    text = raw.decode("utf-8-sig")
    first = text.splitlines()[0].strip()
    assert first == "Unicode true", first
    for word in ("portátil", "licença", "opção", "você", "Descrever com Descritudo"):
        assert word in text, word
    assert "cÃ" not in text
    print("installer source encoding ok")


if __name__ == "__main__":
    main()
