# audio_describer/i18n_setup.py
import gettext
import os
import locale
import wx

from . import config
from .utils.logger import app_logger
# DO NOT import config_model at the top level. This is the root of the circular import.
# from .models import config_model

_ = gettext.gettext
wx_locale = None  # Store to prevent garbage collection

# Names passed to the model so generated descriptions match the UI language.
# Keys are lowercase, with '_' (pt_br, not pt-BR).
DESCRIPTION_LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "ar": "Arabic",
    "pt": "European Portuguese",
    "pt_br": "Brazilian Portuguese",
    "it": "Italian",
    "ru": "Russian",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
    "tr": "Turkish",
}

# Windows locale names that are not already ll_RR tags.
_LOCALE_NAME_ALIASES = {
    "portuguese_brazil": "pt_BR",
    "portuguese_portugal": "pt",
    "ptb": "pt_BR",
    "ptg": "pt",
}


def description_language_name(lang_code):
    """Language name for AI prompts. pt_BR stays Brazilian Portuguese."""
    if not lang_code:
        return "English"
    key = str(lang_code).strip().replace("-", "_").lower()
    if key in DESCRIPTION_LANGUAGE_NAMES:
        return DESCRIPTION_LANGUAGE_NAMES[key]
    primary = key.split("_")[0]
    return DESCRIPTION_LANGUAGE_NAMES.get(primary, "English")


def available_catalog_languages(locale_dir):
    """Catalog directory names that actually contain omni_describer.mo."""
    found = set()
    if not locale_dir or not os.path.isdir(locale_dir):
        return found
    for name in os.listdir(locale_dir):
        mo_path = os.path.join(locale_dir, name, "LC_MESSAGES", "omni_describer.mo")
        if os.path.isfile(mo_path):
            found.add(name)
    return found


def resolve_catalog_language(lang_code, available):
    """Map a locale tag onto a catalog directory we ship.

    A Brazilian tag (pt_BR, pt-BR, Portuguese_Brazil) stays pt_BR when that
    catalog exists. It is not collapsed to pt. European Portuguese (pt, pt_PT)
    uses the existing locale/pt catalog. Other regional tags (en_US, es_MX)
    fall back to the language we ship (en, es).
    """
    available = set(available or [])
    if lang_code is None:
        return "en"
    raw = str(lang_code).strip().replace("-", "_")
    raw = raw.split(".")[0]
    if not raw:
        return "en"

    if raw in available:
        return raw

    alias = _LOCALE_NAME_ALIASES.get(raw.lower())
    if alias and alias in available:
        return alias

    parts = [part for part in raw.split("_") if part]
    lang = parts[0].lower() if parts else ""
    region = parts[1].upper() if len(parts) > 1 else ""

    if lang == "pt" and region == "BR" and "pt_BR" in available:
        return "pt_BR"
    if lang == "pt" and region == "PT" and "pt" in available:
        return "pt"

    for code in available:
        if code.lower() == raw.lower():
            return code
        if region and code.lower() == f"{lang}_{region.lower()}":
            return code

    if lang in available:
        return lang
    return lang or "en"


def detect_system_locale_tag():
    """Full system locale tag, including the region (pt_BR, not just pt)."""
    if os.name == "nt":
        try:
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            tag = locale.windows_locale.get(int(lcid))
            if tag:
                return tag
        except Exception:
            app_logger.warning("i18n: Could not read the Windows UI language.", exc_info=True)

    tag = None
    try:
        # Deprecated in 3.11+, still the reliable user-default locale on Windows
        # when GetUserDefaultUILanguage is unavailable.
        tag, _encoding = locale.getdefaultlocale()
    except Exception:
        tag = None
    if not tag:
        try:
            tag = locale.getlocale()[0]
        except Exception:
            tag = None
    return tag or "en"


def initialize_translations():
    global _
    global wx_locale

    from .models import config_model

    locale_dir = config.get_locale_dir()
    available = available_catalog_languages(locale_dir)

    try:
        lang_code = config_model.get_setting("application_language")

        # Empty string means "detect on this startup".
        if not lang_code or not str(lang_code).strip():
            system_tag = detect_system_locale_tag()
            lang_code = resolve_catalog_language(system_tag, available)
            app_logger.info(
                f"i18n: No language set. System locale '{system_tag}' -> catalog '{lang_code}'."
            )
            config_model.app_settings['application_language'] = lang_code
            config_model.save_settings(config_model.app_settings)
        else:
            lang_code = resolve_catalog_language(lang_code, available)

        app_logger.info(f"i18n: Using language code: {lang_code}")
    except Exception as e:
        app_logger.warning(f"i18n: Error getting lang setting (default 'en'): {e}")
        lang_code = "en"

    domain = "omni_describer"

    app_logger.info(f"i18n: lang='{lang_code}', domain='{domain}', dir='{locale_dir}'")
    app_logger.info(f"i18n: Expected .mo: {os.path.join(locale_dir, lang_code, 'LC_MESSAGES', domain + '.mo')}")

    try:
        translation_obj = gettext.translation(domain, localedir=locale_dir, languages=[lang_code], fallback=True)
        _ = translation_obj.gettext

        config.APP_NAME_TRANSLATABLE = _(config.APP_NAME_BASE_UNTRANSLATED)

        app_logger.info(f"i18n: SUCCESS: Translations initialized for '{lang_code}'.")
        app_logger.info(f"i18n: Translatable app name set to: '{config.APP_NAME_TRANSLATABLE}'")
    except FileNotFoundError:
        app_logger.warning(f"i18n: No .mo file for lang='{lang_code}', domain='{domain}'. Using default strings.")
    except Exception as e:
        app_logger.error(f"i18n: CRITICAL Error initializing gettext: {e}", exc_info=True)

    try:
        lang_info = wx.Locale.FindLanguageInfo(lang_code)
        if lang_info:
            wx.Locale.AddCatalogLookupPathPrefix(locale_dir)
            wx_locale = wx.Locale(lang_info.Language)
            wx_locale.AddCatalog('wxstd')
            lang_display_name = getattr(lang_info, 'Description', getattr(lang_info, 'LanguageName', 'Unknown'))
            app_logger.info(f"i18n: wx.Locale initialized for '{lang_code}' ({lang_display_name}).")
        else:
            app_logger.warning(f"i18n: No matching wx.Locale for lang_code '{lang_code}'. Dialogs may not localize.")
    except Exception as e:
        app_logger.error(f"i18n: Failed to initialize wx.Locale: {e}", exc_info=True)

    return lang_code
