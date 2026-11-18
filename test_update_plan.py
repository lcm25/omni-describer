"""Version comparison and which release file to download."""
from audio_describer.utils.update_plan import (
    asset_filename,
    is_newer,
    select_asset,
    sha256_from_sums,
    skip_portable_member,
)
from audio_describer.version import APP_VERSION, UPDATE_REPO


ASSETS = [
    {"name": "Descritudo-Setup.exe", "browser_download_url": "https://example.test/setup"},
    {"name": "Descritudo-portable.zip", "browser_download_url": "https://example.test/zip"},
    {"name": "SHA256SUMS.txt", "browser_download_url": "https://example.test/sums"},
    {"name": "updater.exe", "browser_download_url": "https://example.test/updater"},
]


def main():
    assert UPDATE_REPO == "lcm25/omni-describer"
    assert is_newer("2.2.0", "2.1.0")
    assert is_newer("v2.2.0", APP_VERSION)
    assert not is_newer("2.1.0", "2.1.0")
    assert not is_newer("v2.1.0", "2.1.0")
    assert not is_newer("2.0.0", "2.1.0")
    assert not is_newer("not-a-version", "2.1.0")
    assert not is_newer("", "2.1.0")

    assert asset_filename("Descritudo", False) == "Descritudo-Setup.exe"
    assert asset_filename("Descritudo", True) == "Descritudo-portable.zip"
    installed = select_asset(ASSETS, asset_filename("Descritudo", False))
    portable = select_asset(ASSETS, asset_filename("Descritudo", True))
    assert installed["name"] == "Descritudo-Setup.exe"
    assert portable["name"] == "Descritudo-portable.zip"
    assert select_asset(ASSETS, "updater.exe")["name"] == "updater.exe"
    assert select_asset(ASSETS, "missing.exe") is None

    sums = "abc123  Descritudo-Setup.exe\n" + ("d" * 64) + " *Descritudo-portable.zip\n"
    assert sha256_from_sums(sums, "Descritudo-Setup.exe") == "abc123"
    assert sha256_from_sums(sums, "Descritudo-portable.zip") == "d" * 64
    assert sha256_from_sums("abc  subdir/Descritudo-Setup.exe", "Descritudo-Setup.exe") == "abc"
    assert sha256_from_sums("e" * 64, "Descritudo-Setup.exe") == "e" * 64
    assert sha256_from_sums("", "Descritudo-Setup.exe") is None

    assert skip_portable_member("Dados/settings.dat2")
    assert skip_portable_member("prompts.json")
    assert not skip_portable_member("Descritudo.exe")
    print("update plan checks passed")


if __name__ == "__main__":
    main()