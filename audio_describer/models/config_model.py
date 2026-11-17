# audio_describer/models/config_model.py
import json
import os
import sys
import base64
from audio_describer import config

# --- Obfuscation Key ---
# Static app-level key for XOR obfuscation of settings.
# Not real encryption, but prevents casual reading and automated
# malware scanning for API key patterns in plain text files.
# This replaces the old machine-tied Fernet encryption which broke
# when hardware/OS changed and caused the _rust.pyd crash on some systems.
_OBFUSCATION_KEY = b"OmniDescriberSettingsKey2026!@#xK9"

# --- File Paths ---
def _settings_present(folder):
    if not folder or not os.path.isdir(folder):
        return False
    names = ("settings.dat2", "settings.dat", "settings.dat.json", "prompts.json", "voices.json")
    return any(os.path.isfile(os.path.join(folder, name)) for name in names)


def migrate_legacy_settings(new_dir, legacy_dirs):
    """Copy an older settings folder into new_dir when the new folder is empty.

    The old folder is left in place, so a failed copy cannot delete the user's data.
    """
    if _settings_present(new_dir):
        return False
    new_real = os.path.abspath(new_dir)
    for old in legacy_dirs:
        if not old or os.path.abspath(old) == new_real or not _settings_present(old):
            continue
        os.makedirs(new_dir, exist_ok=True)
        for name in os.listdir(old):
            src = os.path.join(old, name)
            dst = os.path.join(new_dir, name)
            if os.path.isfile(src) and not os.path.exists(dst):
                import shutil
                shutil.copy2(src, dst)
        return True
    return False


def _portable_data_dir():
    """When portable.txt sits next to the frozen exe, keep settings beside it."""
    if not getattr(sys, "frozen", False):
        return None
    exe_dir = os.path.dirname(sys.executable)
    marker = os.path.join(exe_dir, config.portable_marker_name())
    if os.path.isfile(marker):
        return os.path.join(exe_dir, "Dados")
    return None

_portable = _portable_data_dir()
if _portable:
    APP_DATA_BASE_DIR = os.path.dirname(_portable)
    APP_DATA_DIR = _portable
elif os.name == 'nt':
    APP_DATA_BASE_DIR = os.environ.get('APPDATA', os.path.expanduser("~"))
    APP_DATA_DIR = os.path.join(APP_DATA_BASE_DIR, config.APP_DATA_DIR_NAME)
else:
    APP_DATA_BASE_DIR = os.path.expanduser("~")
    APP_DATA_DIR = os.path.join(APP_DATA_BASE_DIR, ".config", config.APP_DATA_DIR_NAME)

if not _portable:
    migrate_legacy_settings(
        APP_DATA_DIR,
        [os.path.join(APP_DATA_BASE_DIR, name) for name in config.LEGACY_DATA_DIR_NAMES],
    )

try:
    if not os.path.exists(APP_DATA_DIR):
        os.makedirs(APP_DATA_DIR, exist_ok=True)
except Exception as e:
    print(f"CRITICAL: Could not create app data directory at {APP_DATA_DIR}. Error: {e}")
    APP_DATA_DIR = os.getcwd()

# New file extension to avoid conflicts with old encrypted files
CONFIG_FILE_PATH = os.path.join(APP_DATA_DIR, "settings.dat2")
# Old paths for migration
_OLD_CONFIG_FILE_PATH = os.path.join(APP_DATA_DIR, "settings.dat")
_OLD_SALT_FILE_PATH = os.path.join(APP_DATA_DIR, "key.salt")
_OLD_PLAIN_CONFIG_PATH = os.path.join(APP_DATA_DIR, "settings.dat.json")

DEFAULT_SETTINGS = {
    "user_gemini_api_key": "",
    "gemini_description_verbosity": config.DEFAULT_VERBOSITY,
    "gemini_model_override": "",
    "gemini_disable_safety_block_none": True,
    "gemini_temperature": 0.3,
    "user_openai_api_key": "",
    "openai_tts_model": "gpt-4o-mini-tts",
    "openai_tts_voice": "alloy",
    "youtube_download_quality": "360p",
    "application_language": "",
    "logging_level": "INFO",
    "license_accepted": False,
    "player_allow_speech_interruption": False,
    "send_silenced_video_to_ai": False,
    "frame_rate_for_ai": 0,
    "enable_video_chunking": False,
    "video_chunk_duration_seconds": 600,
    "enable_character_glossary": False,
    "tts_engine": "sapi5",
    "narration_provider": "windows",
    "narration_model": "",
    "narration_voice": "",
    "narration_style": "",
    "narration_rate_percent": 100,
    "narration_api_keys": {},
    "narration_measured_cps": 0,
    "azure_speech_region": "",
    "piper_exe": "",
    "piper_model": "",
    "piper_voices_dir": "",
    "analysis_provider": "gemini",
    "analysis_model": "",
    "analysis_model_custom": "",
    "analysis_api_keys": {},
    "twelvelabs_index_id": "",
    "sapi5_voice_id": None,
    "sapi5_voice_rate_percent": 100,
    "sapi5_voice_volume": 1.0,
    "onecore_voice_id": None,
    "onecore_voice_rate_percent": 100,
    "mp3_audio_ducking_level_db": -15,
    "audio_ducking_enabled": True,
    "export_keep_original_audio": False,
    "player_volume_percent": 50,
    "webapp_banner_shown": False,
}


# --- XOR Obfuscation (pure Python, no native dependencies) ---

def _xor_bytes(data, key):
    """XOR data with a repeating key."""
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))


def _obfuscate(json_string):
    """Obfuscate a JSON string: XOR with static key, then base64 encode."""
    raw_bytes = json_string.encode('utf-8')
    xored = _xor_bytes(raw_bytes, _OBFUSCATION_KEY)
    return base64.b64encode(xored)


def _deobfuscate(encoded_data):
    """Deobfuscate: base64 decode, then XOR with static key."""
    xored = base64.b64decode(encoded_data)
    raw_bytes = _xor_bytes(xored, _OBFUSCATION_KEY)
    return raw_bytes.decode('utf-8')


# --- Migration from old Fernet-encrypted settings ---

def _try_migrate_old_settings():
    """Attempts to migrate settings from old formats to the new one.

    Migration priority:
    1. Old Fernet-encrypted settings.dat (try to decrypt with cryptography lib)
    2. Old plain JSON settings.dat.json
    3. Give up and return None

    Returns the migrated settings dict, or None if migration failed/not needed.
    """
    migrated = None

    # Try old Fernet-encrypted file first
    if os.path.exists(_OLD_CONFIG_FILE_PATH):
        migrated = _try_decrypt_old_fernet()
        if migrated is not None:
            print("Successfully migrated settings from old encrypted format.")

    # Try old plain JSON fallback file
    if migrated is None and os.path.exists(_OLD_PLAIN_CONFIG_PATH):
        try:
            with open(_OLD_PLAIN_CONFIG_PATH, 'r', encoding='utf-8') as f:
                migrated = json.load(f)
            print("Successfully migrated settings from old plain JSON format.")
        except Exception as e:
            print(f"Could not read old plain JSON settings: {e}")

    if migrated is not None:
        # Clean up old files
        for old_path in [_OLD_CONFIG_FILE_PATH, _OLD_SALT_FILE_PATH, _OLD_PLAIN_CONFIG_PATH]:
            _safe_rename_old_file(old_path)

    return migrated


def _try_decrypt_old_fernet():
    """Try to decrypt old Fernet-encrypted settings. Returns dict or None."""
    try:
        from cryptography.fernet import Fernet, InvalidToken
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import platform
        import uuid
        import subprocess

        # Reconstruct old machine-tied key
        identifier_parts = [
            platform.node(), platform.processor(), str(uuid.getnode())
        ]
        if os.name == 'nt':
            try:
                output = subprocess.check_output(['vol', 'C:'], shell=True, text=True)
                serial = output.split("is ")[-1].strip()
                identifier_parts.append(serial)
            except Exception:
                pass
        password = "".join(identifier_parts).encode('utf-8')

        if not os.path.exists(_OLD_SALT_FILE_PATH):
            return None
        with open(_OLD_SALT_FILE_PATH, 'rb') as f:
            salt = f.read()

        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
        key = base64.urlsafe_b64encode(kdf.derive(password))
        fernet = Fernet(key)

        with open(_OLD_CONFIG_FILE_PATH, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode('utf-8'))
    except Exception as e:
        print(f"Could not decrypt old Fernet settings (expected if hardware changed): {e}")
        return None


def _safe_rename_old_file(file_path):
    """Rename old file to .migrated to avoid re-processing."""
    if os.path.exists(file_path):
        try:
            migrated_path = file_path + ".migrated"
            if os.path.exists(migrated_path):
                os.remove(migrated_path)
            os.rename(file_path, migrated_path)
        except Exception:
            pass


# --- Core Settings API ---

def save_settings(settings_dict):
    """Save settings to disk with XOR obfuscation."""
    try:
        json_string = json.dumps(settings_dict, indent=4)
        obfuscated_data = _obfuscate(json_string)
        with open(CONFIG_FILE_PATH, 'wb') as f:
            f.write(obfuscated_data)
        return True
    except Exception as e:
        print(f"Failed to save settings: {e}")
        return False


app_settings = None
_settings_load_warning = None


def load_settings():
    """Load settings from disk, with migration from old formats.

    Returns a settings dict. Never raises - falls back to defaults on any error.
    Sets _settings_load_warning if there was a recoverable issue.
    """
    global app_settings, _settings_load_warning
    _settings_load_warning = None

    # Try loading from new format first
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'rb') as f:
                encoded_data = f.read()
            json_string = _deobfuscate(encoded_data)
            settings = json.loads(json_string)
            settings = _apply_defaults_and_cleanup(settings)
            return settings
        except Exception as e:
            print(f"Settings file corrupted (error: {e}). Attempting migration or reset.")
            _settings_load_warning = f"Settings file was corrupted and has been reset. Your previous settings could not be recovered. (Error: {e})"
            try:
                os.rename(CONFIG_FILE_PATH, CONFIG_FILE_PATH + ".corrupted")
            except Exception:
                pass

    # Try migrating from old format
    migrated = _try_migrate_old_settings()
    if migrated is not None:
        settings = _apply_defaults_and_cleanup(migrated)
        # Save in new format immediately
        save_settings(settings)
        return settings

    # Check if old files exist but couldn't be migrated
    if os.path.exists(_OLD_CONFIG_FILE_PATH):
        _settings_load_warning = (
            "Your previous settings could not be migrated from the old encrypted format. "
            "This typically happens after a Windows update or hardware change. "
            "Settings have been reset to defaults. You will need to re-enter your API keys."
        )
        _safe_rename_old_file(_OLD_CONFIG_FILE_PATH)
        _safe_rename_old_file(_OLD_SALT_FILE_PATH)

    return DEFAULT_SETTINGS.copy()


def _apply_defaults_and_cleanup(settings):
    """Ensure all default keys exist and remove obsolete keys."""
    updated = False
    for key, default_value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = default_value.copy() if isinstance(default_value, dict) else default_value
            updated = True
    obsolete_keys = [
        "sapi5_voice_rate", "gemini_top_p", "gemini_top_k",
        "gemini_max_output_tokens"
    ]
    for key in obsolete_keys:
        if key in settings:
            del settings[key]
            updated = True
    if updated:
        save_settings(settings)
    return settings


def get_setting(key_name):
    """Get a setting value by key. Loads settings on first access."""
    global app_settings
    if app_settings is None:
        app_settings = load_settings()
    if key_name not in app_settings:
        default_val = DEFAULT_SETTINGS.get(key_name)
        if default_val is None and key_name not in DEFAULT_SETTINGS:
            return None
        app_settings[key_name] = default_val
    return app_settings.get(key_name)


def get_load_warning():
    """Returns a warning message if settings loading had issues, or None."""
    return _settings_load_warning
