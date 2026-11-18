"""Download the local vision model. Speech is the percent, every 10 points, or on request."""
import os
import threading
import zipfile
import wx

from ..i18n_setup import _
from ..utils.logger import app_logger
from .accessibility_utils import speak_message
from ..core.download_manager import Cancelled, ChecksumError, DiskSpaceError, download_file
from ..core.local_model import RUNTIME, bytes_still_needed, model_by_id, models_dir, runtime_dir


class _Progress(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title=_("Download local model"), style=wx.DEFAULT_DIALOG_STYLE)
        self.cancel = False
        self.percent = 0
        self._spoken_bucket = 0
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.gauge = wx.Gauge(self, range=100)
        sizer.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 12)
        button = wx.Button(self, label=_("Hear the &percent"))
        button.Bind(wx.EVT_BUTTON, self.on_hear)
        sizer.Add(button, 0, wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)
        wx.CallAfter(button.SetFocus)

    def on_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.cancel = True
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def on_hear(self, event):
        speak_message(_("%d percent.") % self.percent)

    def note(self, done, total):
        percent = 0 if not total else min(100, int(done * 100 / total))
        self.percent = percent
        self.gauge.SetValue(percent)
        bucket = percent // 10
        if 0 < bucket < 10 and bucket > self._spoken_bucket:
            self._spoken_bucket = bucket
            speak_message(_("%d percent.") % (bucket * 10))


def _jobs(model_id):
    model = model_by_id(model_id)
    jobs = []
    runtime_zip = os.path.join(runtime_dir(), "runtime.zip")
    if not os.path.isfile(runtime_zip):
        jobs.append((RUNTIME["url"], runtime_zip, RUNTIME["sha256"], RUNTIME["size"]))
    for spec in model["files"]:
        path = os.path.join(models_dir(), model["id"], spec["name"])
        jobs.append((spec["url"], path, spec["sha256"], spec["size"]))
    return jobs


def _unpack_runtime():
    archive = os.path.join(runtime_dir(), "runtime.zip")
    if os.path.isfile(archive):
        with zipfile.ZipFile(archive) as handle:
            handle.extractall(runtime_dir())


def download_local_model(parent, model_id):
    from ..core.download_manager import ensure_space
    try:
        ensure_space(models_dir(), bytes_still_needed(model_id))
    except DiskSpaceError:
        speak_message(_("Not enough disk space."))
        return False
    dialog = _Progress(parent)
    holder = {"error": None, "done": False}

    def work():
        try:
            jobs = _jobs(model_id)
            total = sum(item[3] for item in jobs) or 1
            finished = 0

            def progress(done, _job_total, base=0):
                wx.CallAfter(dialog.note, base + done, total)

            for url, dest, digest, size in jobs:
                if dialog.cancel:
                    raise Cancelled("cancelled")
                base = finished
                download_file(
                    url, dest, digest, size,
                    on_progress=lambda done, job_total, base=base: progress(done, job_total, base),
                    cancel=lambda: dialog.cancel,
                )
                finished += size
            _unpack_runtime()
            holder["done"] = True
        except Cancelled:
            holder["error"] = "cancel"
        except ChecksumError:
            holder["error"] = "checksum"
        except Exception as exc:
            app_logger.error("Local model download failed: %s", exc, exc_info=True)
            holder["error"] = "other"
        wx.CallAfter(dialog.EndModal, wx.ID_OK)

    threading.Thread(target=work, daemon=True).start()
    dialog.ShowModal()
    dialog.Destroy()
    if holder["error"] == "cancel":
        speak_message(_("Cancelled."))
        return False
    if holder["error"] == "checksum":
        speak_message(_("The download did not match."))
        return False
    if holder["error"]:
        speak_message(_("Could not describe the image."))
        return False
    speak_message(_("Model ready."))
    return True
