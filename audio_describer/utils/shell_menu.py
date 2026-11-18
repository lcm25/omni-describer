"""HKCU Explorer verb. Portable copies stay unregistered until Settings turns this on."""
import os
import sys

from ..core.image_files import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

SHELL_VERB = "Descritudo"
SHELL_LABEL = "Descrever com Descritudo"
PERCEIVED_TYPES = ("image", "video")


def association_names():
    names = [ext if ext.startswith(".") else f".{ext}" for ext in sorted(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)]
    return names + list(PERCEIVED_TYPES)


def launch_argv():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return [sys.executable, os.path.join(root, "run_app.py")]


def command_value(argv=None):
    parts = [f'"{item}"' for item in (argv or launch_argv())]
    return " ".join(parts + ['"%1"'])


def registry_entries(command=None):
    """(key, value_name, data) rows. MultiSelectModel=Player sends every selected file once."""
    command = command or command_value()
    rows = []
    for name in association_names():
        key = rf"Software\Classes\SystemFileAssociations\{name}\shell\{SHELL_VERB}"
        rows.append((key, "", SHELL_LABEL))
        rows.append((key, "MultiSelectModel", "Player"))
        rows.append((key + r"\command", "", command))
    return rows


def _keys():
    return {row[0] for row in registry_entries()}


def is_registered():
    if os.name != "nt":
        return False
    import winreg
    probe = rf"Software\Classes\SystemFileAssociations\image\shell\{SHELL_VERB}\command"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, probe):
            return True
    except OSError:
        return False


def apply_shell_menu(enabled):
    """Write or delete the HKCU verb. No effect off Windows."""
    if os.name != "nt":
        return False
    import winreg
    if not enabled:
        for key in sorted(_keys(), key=len, reverse=True):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
            except OSError:
                pass
        return False
    command = command_value()
    for key, name, data in registry_entries(command):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as handle:
            winreg.SetValueEx(handle, name, 0, winreg.REG_SZ, data)
    return True
