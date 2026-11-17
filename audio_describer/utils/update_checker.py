# audio_describer/utils/update_checker.py
import hashlib
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import subprocess
import wx

from ..utils.logger import app_logger
from ..utils.update_plan import asset_filename, is_newer, select_asset, sha256_from_sums
from .. import config

API_TIMEOUT = 8
DOWNLOAD_TIMEOUT = 30


def get_app_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    import __main__
    return os.path.abspath(__main__.__file__)


def get_app_dir():
    return os.path.dirname(get_app_path())


def is_portable_copy():
    return os.path.isfile(os.path.join(get_app_dir(), config.portable_marker_name()))


def fetch_latest_release(repo, timeout=API_TIMEOUT):
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = urllib.request.Request(url, headers={
        "User-Agent": "Descritudo",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_for_updates(parent_frame, current_version, repo, lang_code, _, announce=False):
    """Background check. Startup stays silent when the network fails or nothing is newer."""
    try:
        release = fetch_latest_release(repo)
        remote = release.get("tag_name") or ""
        if is_newer(remote, current_version):
            wx.CallAfter(
                _show_update_prompt, parent_frame, remote.lstrip("vV"),
                release.get("body") or "", release.get("assets") or [], lang_code, _,
            )
        elif announce:
            wx.CallAfter(
                wx.MessageBox,
                _("You are already on the latest version (%s).") % current_version,
                config.APP_NAME,
                wx.OK | wx.ICON_INFORMATION,
                parent_frame,
            )
    except Exception as exc:
        if announce:
            app_logger.info("Update check failed: %s", exc)
            wx.CallAfter(
                wx.MessageBox,
                _("Could not check for updates."),
                config.APP_NAME,
                wx.OK | wx.ICON_INFORMATION,
                parent_frame,
            )
        else:
            app_logger.info("Update check skipped: %s", exc)


def _show_update_prompt(parent, version, notes, assets, lang_code, _):
    dialog = UpdateOfferDialog(parent, version, notes)
    if dialog.ShowModal() != wx.ID_OK:
        dialog.Destroy()
        return
    dialog.Destroy()
    portable = is_portable_copy()
    filename = asset_filename(config.APP_NAME, portable)
    asset = select_asset(assets, filename)
    if not asset or not asset.get("browser_download_url"):
        wx.MessageBox(_("The update file was not published."), config.APP_NAME, wx.OK | wx.ICON_INFORMATION, parent)
        return
    checksum = _published_checksum(assets, filename)
    if checksum is False:
        wx.MessageBox(_("The downloaded file does not match the published checksum."), config.APP_NAME, wx.OK | wx.ICON_INFORMATION, parent)
        return
    _download_and_apply(parent, asset["browser_download_url"], filename, checksum or "", portable, lang_code, _)


class UpdateOfferDialog(wx.Dialog):
    def __init__(self, parent, version, notes):
        sentence = _("Descritudo %s is available. Update now?") % version
        super().__init__(parent, title=sentence)
        self.notes = notes or ""
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=sentence), 0, wx.ALL, 12)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.update_button = wx.Button(self, wx.ID_OK, _("&Update"))
        later = wx.Button(self, wx.ID_CANCEL, _("Not &now"))
        notes_button = wx.Button(self, label=_("Read release n&otes"))
        self.update_button.SetDefault()
        buttons.Add(self.update_button, 0, wx.RIGHT, 8)
        buttons.Add(later, 0, wx.RIGHT, 8)
        buttons.Add(notes_button, 0)
        sizer.Add(buttons, 0, wx.ALL, 12)
        self.SetSizerAndFit(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        notes_button.Bind(wx.EVT_BUTTON, self._read_notes)
        self.Bind(wx.EVT_SHOW, self._focus_update)

    def _focus_update(self, event):
        self.update_button.SetFocus()
        event.Skip()

    def _read_notes(self, event):
        text = self.notes.strip() or _("No release notes.")
        wx.MessageBox(text, _("Release notes"), wx.OK | wx.ICON_INFORMATION, self)


def _published_checksum(assets, filename):
    """None when no checksum was published. False when it was published but cannot be used."""
    sums = select_asset(assets, "SHA256SUMS.txt")
    if not sums or not sums.get("browser_download_url"):
        return None
    try:
        request = urllib.request.Request(sums["browser_download_url"], headers={"User-Agent": "Descritudo"})
        with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
            text = response.read().decode("utf-8", errors="replace")
        return sha256_from_sums(text, filename) or False
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        app_logger.info("Checksum file was not read: %s", exc)
        return False


def _download_and_apply(parent, url, filename, checksum, portable, lang_code, _):
    from .accessibility_utils import speak_message
    progress = wx.ProgressDialog(
        config.APP_NAME, _("Downloading the update."),
        maximum=100, parent=parent, style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE,
    )
    destination = os.path.join(tempfile.gettempdir(), filename)
    announced = set()

    def report(percent):
        bucket = percent // 25
        if bucket in announced or bucket <= 0:
            return
        announced.add(bucket)
        speak_message(_("%d percent downloaded.") % (bucket * 25))
        progress.Update(bucket * 25, _("%d percent downloaded.") % (bucket * 25))

    try:
        _download(url, destination, report)
        if checksum:
            with open(destination, "rb") as payload:
                digest = hashlib.sha256(payload.read()).hexdigest()
            if digest.lower() != checksum.lower():
                raise ValueError("checksum mismatch")
        progress.Destroy()
        _launch_updater(destination, portable, lang_code)
        app = wx.GetApp()
        app.is_updating = True
        frame = getattr(app, "main_frame", None) or parent
        frame.Close()
    except Exception as exc:
        progress.Destroy()
        app_logger.info("Update was not applied: %s", exc)
        if "checksum" in str(exc):
            wx.MessageBox(_("The downloaded file does not match the published checksum."), config.APP_NAME, wx.OK | wx.ICON_INFORMATION, parent)
        else:
            wx.MessageBox(_("Could not check for updates."), config.APP_NAME, wx.OK | wx.ICON_INFORMATION, parent)


def _download(url, destination, report):
    request = urllib.request.Request(url, headers={"User-Agent": "Descritudo"})
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response, open(destination, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        read = 0
        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            out.write(chunk)
            read += len(chunk)
            if total:
                report(int(read * 100 / total))


def _launch_updater(payload_path, portable, lang_code):
    app_dir = get_app_dir()
    app_path = get_app_path()
    command = _updater_command(app_dir)
    parent_pid = str(os.getpid())
    if portable:
        command.extend([payload_path, app_dir, app_path, lang_code, parent_pid])
    else:
        command.extend(["--installer", payload_path, parent_pid, app_path])
    subprocess.Popen(command)


def _updater_command(app_dir):
    bundled = os.path.join(app_dir, "updater.exe")
    if os.path.isfile(bundled):
        return [bundled]
    source = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "updater.py"))
    if os.path.isfile(source):
        return [sys.executable, source]
    raise FileNotFoundError(bundled)


def start_check(parent_frame, lang_code, _, announce=False):
    from ..models import config_model
    if not announce and not config_model.get_setting("check_updates_on_startup"):
        return
    threading.Thread(
        target=check_for_updates,
        args=(parent_frame, config.APP_VERSION, config.UPDATE_REPO, lang_code, _, announce),
        daemon=True,
    ).start()
