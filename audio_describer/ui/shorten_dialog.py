"""Pick one shorter line. Enter replaces the text. Escape keeps the original."""
import wx
from ..i18n_setup import _
from .accessibility_utils import speak_message


class ShortenChoiceDialog(wx.Dialog):
    def __init__(self, parent, alternatives, allow_stop=False):
        super().__init__(parent, title=_("Shorter texts"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.choice = None
        self.stopped = False
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=_("Three shorter texts. Arrows, Enter replaces, Escape keeps the original.")), 0, wx.ALL, 8)
        self.listbox = wx.ListBox(self, choices=alternatives, style=wx.LB_SINGLE)
        self.listbox.SetSelection(0)
        sizer.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        use_button = wx.Button(self, wx.ID_OK, _("&Use this text"))
        keep_button = wx.Button(self, wx.ID_CANCEL, _("&Keep original"))
        buttons.Add(use_button, 0, wx.ALL, 5)
        buttons.Add(keep_button, 0, wx.ALL, 5)
        if allow_stop:
            stop_button = wx.Button(self, wx.ID_NO, _("S&top batch"))
            stop_button.Bind(wx.EVT_BUTTON, self._on_stop)
            buttons.Add(stop_button, 0, wx.ALL, 5)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        self.SetSizerAndFit(sizer)
        self.SetMinSize((420, 220))
        use_button.Bind(wx.EVT_BUTTON, self._on_use)
        self.listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._on_use)
        accept_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self._on_use, id=accept_id)
        self.SetAcceleratorTable(wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_RETURN, accept_id)]))
        self.listbox.SetFocus()
        speak_message(_("Three shorter texts. Enter replaces. Escape keeps the original."))

    def _on_use(self, event):
        selection = self.listbox.GetSelection()
        if selection != wx.NOT_FOUND:
            self.choice = self.listbox.GetString(selection)
        self.EndModal(wx.ID_OK)

    def _on_stop(self, event):
        self.stopped = True
        self.EndModal(wx.ID_NO)
