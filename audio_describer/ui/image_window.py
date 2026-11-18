"""Description of one photo or sticker, and a list when several were opened together."""
import os
import tempfile
import threading
import wx

from ..i18n_setup import _
from ..utils.logger import app_logger
from ..utils import sound_player
from .accessibility_utils import set_control_accessible_name, speak_message
from ..core.image_describe import ImageDescribeError, describe_frames
from ..core.image_files import is_image_path, load_image_frames
from ..core.image_prompt import image_prompt
from ..core.tts_engine import TTSError, synthesize_description_to_wav


def _short_error(exc):
    if isinstance(exc, ImageDescribeError) and str(exc) == "twelvelabs":
        return _("This model does not describe images.")
    if isinstance(exc, ImageDescribeError) and str(exc) == "missing":
        return _("The local model is not installed. Open Settings, choose Local, and download it.")
    text = str(exc).lower()
    if "api key" in text or "not configured" in text or "key required" in text:
        return _("The AI key is missing.")
    return _("Could not describe the image.")


def read_image(path):
    frames = load_image_frames(path)
    animated = len(frames) > 1 or (frames and int(frames[0].get("count") or 1) > 1)
    text = describe_frames(frames, image_prompt("short", animated=animated))
    return {"path": path, "frames": frames, "animated": animated, "text": text, "error": None}


def clipboard_image_path():
    """A temp PNG from a copied bitmap, or a copied image file path."""
    if not wx.TheClipboard.Open():
        return None
    try:
        if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
            data = wx.BitmapDataObject()
            if wx.TheClipboard.GetData(data):
                image = data.GetBitmap().ConvertToImage()
                if image.IsOk():
                    folder = os.path.join(tempfile.gettempdir(), "descritudo")
                    os.makedirs(folder, exist_ok=True)
                    path = os.path.join(folder, "clipboard.png")
                    if image.SaveFile(path, wx.BITMAP_TYPE_PNG):
                        return path
        if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
            data = wx.FileDataObject()
            if wx.TheClipboard.GetData(data):
                for path in data.GetFilenames():
                    if is_image_path(path) and os.path.isfile(path):
                        return path
        if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
            data = wx.TextDataObject()
            if wx.TheClipboard.GetData(data):
                path = (data.GetText() or "").strip().strip('"')
                if is_image_path(path) and os.path.isfile(path):
                    return path
    finally:
        wx.TheClipboard.Close()
    return None


class ImageResultDialog(wx.Dialog):
    def __init__(self, parent, item):
        super().__init__(parent, title=os.path.basename(item["path"]), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.item = item
        self._busy = False
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.text.SetValue(item.get("text") or "")
        self.text.SetMinSize((520, 220))
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label=_("Ask about the image")), 0, wx.LEFT | wx.RIGHT, 8)
        self.ask = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        set_control_accessible_name(self.ask, _("Ask about the image"))
        sizer.Add(self.ask, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.ask.Bind(wx.EVT_TEXT_ENTER, self.on_ask)
        copy_id = wx.NewIdRef()
        save_id = wx.NewIdRef()
        long_id = wx.NewIdRef()
        narrate_id = wx.NewIdRef()
        open_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_copy, id=copy_id)
        self.Bind(wx.EVT_MENU, self.on_save, id=save_id)
        self.Bind(wx.EVT_MENU, self.on_long, id=long_id)
        self.Bind(wx.EVT_MENU, self.on_narrate, id=narrate_id)
        self.Bind(wx.EVT_MENU, self.on_open_next, id=open_id)
        self.SetAcceleratorTable(wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord("C"), copy_id),
            (wx.ACCEL_CTRL, ord("S"), save_id),
            (wx.ACCEL_CTRL, ord("L"), long_id),
            (wx.ACCEL_NORMAL, wx.WXK_F5, narrate_id),
            (wx.ACCEL_CTRL, ord("O"), open_id),
        ]))
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        wx.CallAfter(self._focus_description)

    def _focus_description(self, at_end=False):
        self.text.SetFocus()
        if at_end:
            self.text.SetInsertionPointEnd()

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def on_copy(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.text.GetValue()))
            wx.TheClipboard.Close()

    def on_save(self, event):
        path = self.item["path"]
        folder = os.path.dirname(path) or os.getcwd()
        stem = os.path.splitext(os.path.basename(path))[0]
        target = os.path.join(folder, stem + ".txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(self.text.GetValue())
        app_logger.info("Saved image description: %s", target)
        speak_message(_("Saved."))

    def on_ask(self, event):
        question = self.ask.GetValue().strip()
        if not question or self._busy:
            return
        self.ask.Clear()
        self._run(_("Describing..."), self._answer, question)

    def _answer(self, question):
        text = describe_frames(
            self.item["frames"],
            image_prompt("short", animated=self.item["animated"], question=question),
        )
        return self.text.GetValue().rstrip() + "\n\n" + text, True

    def on_long(self, event):
        if self._busy:
            return
        self._run(_("Describing..."), self._long, None)

    def _long(self, _unused):
        text = describe_frames(self.item["frames"], image_prompt("long", animated=self.item["animated"]))
        return text, False

    def on_narrate(self, event):
        text = self.text.GetValue().strip()
        if not text or self._busy:
            return
        self._busy = True

        def work():
            try:
                wav = os.path.join(tempfile.gettempdir(), "descritudo-narrar.wav")
                if not synthesize_description_to_wav(text, wav):
                    raise TTSError("empty")
                wx.CallAfter(sound_player.play, wav, True)
            except Exception as exc:
                app_logger.error("Narrate failed: %s", exc)
                wx.CallAfter(speak_message, _("Could not narrate."))
            finally:
                wx.CallAfter(self._clear_busy)

        threading.Thread(target=work, daemon=True).start()

    def _clear_busy(self):
        self._busy = False

    def on_open_next(self, event):
        if self._busy:
            return
        from . import file_dialogs
        from ..core.image_files import IMAGE_WILDCARD
        paths = file_dialogs.show_open_files_dialog(
            self, _("Photos and stickers") + f"|{IMAGE_WILDCARD}", multiple=True,
        )
        if not paths:
            return
        speak_message(_("Describing..."))
        self._busy = True

        def work():
            items = []
            error = None
            for path in paths:
                try:
                    items.append(read_image(path))
                except Exception as exc:
                    app_logger.error("Image describe failed for %s: %s", path, exc)
                    error = exc
                    items.append({"path": path, "frames": [], "animated": False, "text": "", "error": exc})
            wx.CallAfter(self._opened, items, error)

        threading.Thread(target=work, daemon=True).start()

    def _opened(self, items, error):
        self._busy = False
        ready = [item for item in items if item.get("text")]
        if len(ready) == 1 and len(items) == 1:
            self._show_item(ready[0])
            return
        if not ready:
            speak_message(_short_error(error) if error else _("Could not describe the image."))
            return
        with ImageBatchDialog(self, items) as dialog:
            dialog.ShowModal()

    def _show_item(self, item):
        self.item = item
        self.SetTitle(os.path.basename(item["path"]))
        self.text.SetValue(item.get("text") or "")
        self._focus_description()

    def _run(self, spoken, function, argument):
        self._busy = True
        speak_message(spoken)

        def work():
            try:
                text, at_end = function(argument)
                wx.CallAfter(self._apply, text, at_end, None)
            except Exception as exc:
                app_logger.error("Image follow-up failed: %s", exc, exc_info=True)
                wx.CallAfter(self._apply, None, False, exc)

        threading.Thread(target=work, daemon=True).start()

    def _apply(self, text, at_end, error):
        self._busy = False
        if error is not None:
            speak_message(_short_error(error))
            return
        self.item["text"] = text
        self.text.SetValue(text)
        self._focus_description(at_end=at_end)


class ImageBatchDialog(wx.Dialog):
    def __init__(self, parent, items):
        super().__init__(parent, title=_("Images"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.items = items
        labels = []
        for item in items:
            name = os.path.basename(item["path"])
            if item.get("error"):
                name = _("%s, failed") % name
            labels.append(name)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ListBox(self, choices=labels)
        self.list.SetMinSize((420, 240))
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        if labels:
            self.list.SetSelection(0)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open)
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        wx.CallAfter(self.list.SetFocus)

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def on_key(self, event):
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.on_open(event)
            return
        event.Skip()

    def on_open(self, event):
        index = self.list.GetSelection()
        if index == wx.NOT_FOUND:
            return
        item = self.items[index]
        if item.get("error") or not item.get("text"):
            speak_message(_short_error(item.get("error")) if item.get("error") else _("Could not describe the image."))
            return
        with ImageResultDialog(self, item) as dialog:
            dialog.ShowModal()


def present_images(parent, items):
    ready = [item for item in items if item.get("text")]
    if len(items) == 1 and ready:
        with ImageResultDialog(parent, ready[0]) as dialog:
            dialog.ShowModal()
        return
    if not ready:
        error = next((item.get("error") for item in items if item.get("error")), None)
        speak_message(_short_error(error) if error else _("Could not describe the image."))
        return
    with ImageBatchDialog(parent, items) as dialog:
        dialog.ShowModal()
