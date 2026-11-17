"""The Pix page is not skipped on upgrade, reinstall, or portable mode."""
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "installer" / "Setup.nsi"


def pagina_apoio_body(text):
    start = text.index("Function PaginaApoio\n")
    end = text.index("FunctionEnd", start)
    return text[start:end]


def main():
    text = SCRIPT.read_text(encoding="utf-8-sig")
    body = pagina_apoio_body(text)
    assert "Page custom PaginaApoio" in text
    finish = text.index("!insertmacro MUI_PAGE_FINISH")
    apoio = text.index("Page custom PaginaApoio")
    instfiles = text.index("!insertmacro MUI_PAGE_INSTFILES")
    assert instfiles < apoio < finish
    for forbidden in ("$Atualizar", "IfSilent", "ApoioMostrado"):
        assert forbidden not in body, forbidden
    assert "nsDialogs::Show" in body
    assert "&Copiar chave Pix" in body
    assert "+5521977425383" in text
    assert "Chave Pix copiada" in text
    print("pix page is unconditional")


if __name__ == "__main__":
    main()
