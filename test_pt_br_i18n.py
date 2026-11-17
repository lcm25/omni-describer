"""Checks for the Brazilian Portuguese catalog and locale selection.

Run from the repository root: python test_pt_br_i18n.py
"""
import ast
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("wx", types.ModuleType("wx"))

from audio_describer import config
from audio_describer.i18n_setup import (
    available_catalog_languages,
    description_language_name,
    resolve_catalog_language,
)

LOCALE = ROOT / "audio_describer" / "locale"
PO_PATH = LOCALE / "pt_BR" / "LC_MESSAGES" / "omni_describer.po"
DOC_PATH = ROOT / "audio_describer" / "doc" / "pt_BR" / "help.html"


def _unescape(raw):
    val = raw.encode("utf-8").decode("unicode_escape")
    return val.encode("latin1").decode("utf-8")


def parse_po(path):
    entries = []
    cur = None
    mode = None
    buf = []

    def flush_buf():
        nonlocal buf, mode
        if cur is not None and mode and buf:
            raw = "".join(re.findall(r'"(.*)"', "\n".join(buf)))
            cur[mode] = _unescape(raw)
        buf = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("msgid "):
            flush_buf()
            if cur and cur["id"]:
                entries.append(cur)
            cur = {"id": "", "str": ""}
            mode = "id"
            buf = [line[len("msgid "):].strip()]
            continue
        if line.startswith("msgstr "):
            flush_buf()
            mode = "str"
            buf = [line[len("msgstr "):].strip()]
            continue
        if line.startswith('"') and mode:
            buf.append(line)
            continue
        if line.startswith("#") or line.strip() == "":
            flush_buf()
            mode = None
    flush_buf()
    if cur and cur["id"]:
        entries.append(cur)
    return {entry["id"]: entry["str"] for entry in entries}


def source_msgids():
    funcs = {"_", "gettext_", "trans_func"}
    found = set()
    files = list((ROOT / "audio_describer").rglob("*.py"))
    files += [ROOT / "updater.py", ROOT / "sapi32.py", ROOT / "run_app.py"]
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (
                func.attr if isinstance(func, ast.Attribute) else None
            )
            if name not in funcs:
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                found.add(arg.value)
    return found


def accelerators(label):
    found = []
    index = 0
    while index < len(label):
        if label[index] == "&" and index + 1 < len(label) and label[index + 1] not in "& \t":
            found.append(label[index + 1].lower())
            index += 2
        else:
            index += 1
    return found


def check_language_resolution():
    available = available_catalog_languages(config.get_locale_dir())
    assert "pt_BR" in available, available
    assert "pt" in available
    cases = {
        "pt_BR": "pt_BR",
        "pt-BR": "pt_BR",
        "Portuguese_Brazil": "pt_BR",
        "Portuguese_Brazil.1252": "pt_BR",
        "pt_PT": "pt",
        "pt-PT": "pt",
        "Portuguese_Portugal": "pt",
        "pt": "pt",
        "en_US": "en",
        "es_MX": "es",
        "fr_FR": "fr",
    }
    for raw, expected in cases.items():
        got = resolve_catalog_language(raw, available)
        assert got == expected, f"{raw!r} -> {got!r}, expected {expected!r}"
    assert description_language_name("pt_BR") == "Brazilian Portuguese"
    assert description_language_name("pt-br") == "Brazilian Portuguese"
    assert description_language_name("pt") == "European Portuguese"
    assert description_language_name("en_US") == "English"


def check_catalog():
    catalog = parse_po(PO_PATH)
    needed = source_msgids()
    missing = sorted(needed - set(catalog))
    assert not missing, "Untranslated msgids:\n" + "\n".join(missing[:20])

    placeholder = re.compile(r"%(?:\([^)]+\))?[sdif]|\{[^{}]*\}")
    european = re.compile(
        r"\b(ficheiro|ficheiros|utilizador|utilizadores|ecrã|ecrãs|guardar|descarregar)\b",
        re.IGNORECASE,
    )
    for msgid in needed:
        msgstr = catalog[msgid]
        assert msgstr.strip(), f"Empty translation for {msgid!r}"
        assert placeholder.findall(msgid) == placeholder.findall(msgstr), (
            f"Placeholder mismatch for {msgid!r}: {msgstr!r}"
        )
        assert not european.search(msgstr), f"European Portuguese wording in {msgstr!r}"
        if "&" in msgid.split("\t", 1)[0]:
            assert "&" in msgstr, f"Missing accelerator in {msgid!r} -> {msgstr!r}"
        if "\t" in msgid:
            assert msgstr.split("\t", 1)[1] == msgid.split("\t", 1)[1]

    assert catalog["&Save"] == "&Salvar"
    # The export dialog's confirm button is this string. It must not be the
    # old email-verification sentence.
    assert "e-mail" not in catalog["&Save"].lower()
    assert "verificação" not in catalog["&Save"].lower()

    groups = {
        "main": [
            "&File", "&Help", "&Local Video File", "Describe a photo or &sticker",
            "Direct Video &URL",
            "&YouTube Video URL", "Open &Web Platform", "&Settings...", "E&xit",
        ],
        "file_menu": [
            "&Open Local File...\tCtrl+O", "Describe clipboard &image\tCtrl+Shift+V",
            "Open Video from &URL...\tCtrl+U",
            "Open from &YouTube...\tCtrl+Y", "Manage &Prompt Presets...",
            "Open &Web Platform...\tCtrl+W", "&Settings...\tCtrl+,", "E&xit\tAlt+F4",
        ],
        "help_menu": [
            "&View Help\tF1", "&Changelog", "Co&ntributors", "View &License", "&About...",
        ],
        "ask_more": ["&Submit Question", "&Add to Descriptions"],
        "edit": ["&Add New...", "&Delete", "&Save Changes"],
        "manage": ["&Add...", "&Edit...", "&Delete"],
        "player": ["&Rewind %ss", "&Forward %ss"],
    }
    for name, msgids in groups.items():
        letters = []
        for msgid in msgids:
            letters.extend(accelerators(catalog[msgid]))
        duplicates = sorted({letter for letter in letters if letters.count(letter) > 1})
        assert not duplicates, f"Accelerator collision in {name}: {duplicates}"


def check_help_and_wxstd():
    assert DOC_PATH.is_file(), DOC_PATH
    help_html = DOC_PATH.read_text(encoding="utf-8")
    assert 'lang="pt-BR"' in help_html
    assert "studio.binclusive.io" in help_html
    assert "info@audioses.com" in help_html
    for word in ("você", "arquivo", "tela", "salvar", "baixar"):
        assert word in help_html.lower(), word
    wxstd = LOCALE / "pt_BR" / "LC_MESSAGES" / "wxstd.mo"
    assert wxstd.is_file() and wxstd.stat().st_size > 1000
    # The app looks up docs by the same code it stores as the language.
    assert (ROOT / "audio_describer" / "doc" / "pt_BR" / "help.html").is_file()


def main():
    check_language_resolution()
    check_catalog()
    check_help_and_wxstd()
    print("pt_BR i18n checks passed")


if __name__ == "__main__":
    main()
