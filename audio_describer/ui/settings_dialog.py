# audio_describer/ui/settings_dialog.py
import wx
import sys
import threading
from audio_describer import config
from audio_describer.models import config_model, voice_model
from audio_describer.utils.logger import app_logger
from audio_describer.ui.accessibility_utils import set_control_accessible_name
from .manage_voices_dialog import ManageVoicesDialog
from ..i18n_setup import _
from ..core import tts_engine

# --- MODIFICATION: Check for all available TTS engines ---
PYTTSX3_AVAILABLE = tts_engine.PYTTSX3_AVAILABLE
SAPI5_32BIT_HELPER_AVAILABLE = tts_engine.SAPI5_32BIT_HELPER_AVAILABLE
ONECORE_AVAILABLE = tts_engine.WIN_ONECORE_AVAILABLE


# Custom event for when the test voice thread is done
EVT_TEST_VOICE_DONE_ID = wx.NewIdRef()
EVT_TEST_VOICE_DONE = wx.PyEventBinder(EVT_TEST_VOICE_DONE_ID, 0)

class TestVoiceDoneEvent(wx.PyCommandEvent):
    def __init__(self, error=None):
        super().__init__(EVT_TEST_VOICE_DONE_ID, 0)
        self.error = error

class SettingsDialog(wx.Dialog):
    def __init__(self, parent, title=None):
        if title is None:
            title = _("%s Settings") % config.APP_NAME
        
        self.YOUTUBE_QUALITY_CHOICES = [_("Best Available"), "1080p", "720p", "480p", "360p", "240p", "144p"]
        self.VERBOSITY_CHOICES = [(config.VERBOSITY_SHORT, _("Short - Concise descriptions")), (config.VERBOSITY_STANDARD, _("Standard - Balanced detail (Default)")), (config.VERBOSITY_DETAILED, _("Detailed - Rich descriptions"))]
        
        self.LANGUAGE_CHOICES = [
            ("", _("Auto-Detect on Startup")),
            ("ar", _("Arabic")),
            ("en", _("English")),
            ("es", _("Spanish")),
            ("fr", _("French")),
            ("it", _("Italian")),
            ("pt_BR", _("Portuguese (Brazil)")),
            ("pt", _("Portuguese (Portugal)")),
            ("ru", _("Russian")),
            ("tr", _("Türkçe")),
            ("uk", _("Ukrainian")),
            ("vi", _("Vietnamese")),
        ]

        self.LOGGING_LEVEL_CHOICES = [("INFO", _("Info (Default)")), ("DEBUG", _("Debug")), ("DISABLED", _("Disabled"))]
        self.FRAME_RATE_CHOICES = [
            (0, _("No Change (Original FPS)")),
            (10, _("10 FPS (Good balance, lower cost)")),
            (5, _("5 FPS (Very low cost, may miss fast action)")),
            (2, _("2 FPS (Extreme low cost, for static scenes)")),
            (1, _("1 FPS (Minimal cost, for static content)")),
        ]
        
        # --- MODIFICATION: Dynamically build TTS choices based on availability ---
        self.TTS_ENGINE_CHOICES = [("openai", _("OpenAI TTS (High Quality)"))]
        if PYTTSX3_AVAILABLE:
            self.TTS_ENGINE_CHOICES.append(("sapi5", _("SAPI5 (64-bit Voices)")))
        if SAPI5_32BIT_HELPER_AVAILABLE:
            self.TTS_ENGINE_CHOICES.append(("sapi5_32bit", _("SAPI5 (32-bit Voices)")))
        if ONECORE_AVAILABLE:
            self.TTS_ENGINE_CHOICES.append(("onecore", _("Windows OneCore (Modern Voices)")))

        self.OPENAI_VOICE_CHOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer", "coral", "ash", "ballad", "sage"]

        super(SettingsDialog, self).__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.settings_changed = False
        self.current_settings = config_model.app_settings.copy() 
        
        self.sapi_voices = [] # This will be populated dynamically

        self.InitUI()
        self.LoadSettingsToUI()
        self.SetSizerAndFit(self.main_sizer)
        self.Layout()
        self.CentreOnParent()

    def InitUI(self):
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self)
        
        # --- General Tab ---
        self.general_panel = wx.Panel(self.notebook)
        general_grid_sizer = wx.FlexGridSizer(cols=2, gap=(5,5)); general_grid_sizer.AddGrowableCol(1,1)
        general_grid_sizer.Add(wx.StaticText(self.general_panel, label=_("YouTube Video Download Quality:")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.yt_quality_choice = wx.Choice(self.general_panel, choices=self.YOUTUBE_QUALITY_CHOICES)
        general_grid_sizer.Add(self.yt_quality_choice, 1, wx.EXPAND | wx.ALL, 5)
        general_grid_sizer.Add(wx.StaticText(self.general_panel, label=_("Application Language (Requires Restart):")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.app_lang_display_choices = [lc[1] for lc in self.LANGUAGE_CHOICES]; self.app_lang_internal_values = [lc[0] for lc in self.LANGUAGE_CHOICES]
        self.app_lang_choice = wx.Choice(self.general_panel, choices=self.app_lang_display_choices)
        general_grid_sizer.Add(self.app_lang_choice, 1, wx.EXPAND | wx.ALL, 5)
        general_grid_sizer.Add(wx.StaticText(self.general_panel, label=_("Logging Level:")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.log_level_display_choices = [lc[1] for lc in self.LOGGING_LEVEL_CHOICES]; self.log_level_internal_values = [lc[0] for lc in self.LOGGING_LEVEL_CHOICES]
        self.log_level_choice = wx.Choice(self.general_panel, choices=self.log_level_display_choices)
        general_grid_sizer.Add(self.log_level_choice, 1, wx.EXPAND | wx.ALL, 5)
        self.interrupt_speech_checkbox = wx.CheckBox(self.general_panel, label=_("Allow descriptions to interrupt current speech"))
        general_grid_sizer.Add(self.interrupt_speech_checkbox, 1, wx.EXPAND | wx.ALL, 5)
        self.context_menu_checkbox = wx.CheckBox(self.general_panel, label=_("Add to the Windows &context menu"))
        general_grid_sizer.Add(self.context_menu_checkbox, 1, wx.EXPAND | wx.ALL, 5)
        self.check_updates_checkbox = wx.CheckBox(self.general_panel, label=_("Check for updates on startup"))
        general_grid_sizer.Add(self.check_updates_checkbox, 1, wx.EXPAND | wx.ALL, 5)
        self.check_updates_button = wx.Button(self.general_panel, label=_("Check for updates &now"))
        general_grid_sizer.Add(self.check_updates_button, 0, wx.ALL, 5)
        self.general_panel.SetSizer(general_grid_sizer)
        self.notebook.AddPage(self.general_panel, _("General"))

        # --- AI Settings Tab ---
        self.ai_panel = wx.Panel(self.notebook)
        ai_grid_sizer = wx.FlexGridSizer(cols=2, gap=(5, 5)); ai_grid_sizer.AddGrowableCol(1, 1)
        from ..core.analysis_providers import ANALYSIS_PROVIDERS, CUSTOM_MODEL, ui_label as analysis_label
        self._analysis_custom_id = CUSTOM_MODEL
        ai_grid_sizer.Add(wx.StaticText(self.ai_panel, label=_("Video analysis provider:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.analysis_provider_ids = [item["id"] for item in ANALYSIS_PROVIDERS]
        self.analysis_provider_choice = wx.Choice(self.ai_panel, choices=[analysis_label(item["label"]) for item in ANALYSIS_PROVIDERS])
        ai_grid_sizer.Add(self.analysis_provider_choice, 1, wx.EXPAND|wx.ALL, 5)
        self.provider_key_label = wx.StaticText(self.ai_panel, label=_("Gemini API key:"))
        ai_grid_sizer.Add(self.provider_key_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.api_key_text = wx.TextCtrl(self.ai_panel, style=wx.TE_PASSWORD)
        ai_grid_sizer.Add(self.api_key_text, 1, wx.EXPAND|wx.ALL, 5)
        self.clear_key_button = wx.Button(self.ai_panel, label=_("&Erase key"))
        ai_grid_sizer.Add((0, 0))
        ai_grid_sizer.Add(self.clear_key_button, 0, wx.ALL, 5)
        self.openai_key_label = wx.StaticText(self.ai_panel, label=_("OpenAI API Key (for TTS):"))
        self.openai_key_label.Hide()
        self.openai_api_key_text = wx.TextCtrl(self.ai_panel, style=wx.TE_PASSWORD)
        self.openai_api_key_text.Hide()
        ai_grid_sizer.Add(wx.StaticLine(self.ai_panel, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 10); ai_grid_sizer.Add(wx.StaticLine(self.ai_panel, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 10)
        ai_grid_sizer.Add(wx.StaticText(self.ai_panel, label=_("Frame Rate for AI Analysis:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.frame_rate_display_choices = [fc[1] for fc in self.FRAME_RATE_CHOICES]; self.frame_rate_internal_values = [fc[0] for fc in self.FRAME_RATE_CHOICES]
        self.frame_rate_choice = wx.Choice(self.ai_panel, choices=self.frame_rate_display_choices)
        ai_grid_sizer.Add(self.frame_rate_choice, 1, wx.EXPAND|wx.ALL, 5)
        ai_grid_sizer.Add(wx.StaticText(self.ai_panel, label=_("Description Verbosity:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.verbosity_display_choices = [vc[1] for vc in self.VERBOSITY_CHOICES]; self.verbosity_internal_values = [vc[0] for vc in self.VERBOSITY_CHOICES]
        self.verbosity_choice = wx.Choice(self.ai_panel, choices=self.verbosity_display_choices)
        ai_grid_sizer.Add(self.verbosity_choice, 1, wx.EXPAND|wx.ALL, 5)
        ai_grid_sizer.Add(wx.StaticText(self.ai_panel, label=_("Analysis model:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.analysis_model_choice = wx.Choice(self.ai_panel)
        ai_grid_sizer.Add(self.analysis_model_choice, 1, wx.EXPAND|wx.ALL, 5)
        self.refresh_analysis_models_button = wx.Button(self.ai_panel, label=_("&Refresh model list"))
        ai_grid_sizer.Add(self.refresh_analysis_models_button, 0, wx.ALL, 5)
        ai_grid_sizer.Add((0, 0))
        self.analysis_custom_label = wx.StaticText(self.ai_panel, label=_("Custom model name:"))
        ai_grid_sizer.Add(self.analysis_custom_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.model_override_text = wx.TextCtrl(self.ai_panel)
        ai_grid_sizer.Add(self.model_override_text, 1, wx.EXPAND|wx.ALL, 5)
        self.analysis_key_label = wx.StaticText(self.ai_panel, label=_("API key for this provider:"))
        ai_grid_sizer.Add(self.analysis_key_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.analysis_key_text = wx.TextCtrl(self.ai_panel, style=wx.TE_PASSWORD)
        ai_grid_sizer.Add(self.analysis_key_text, 1, wx.EXPAND|wx.ALL, 5)
        self.local_note = wx.StaticText(self.ai_panel, label=_("On this computer, offline. Slower and less detailed than the cloud. Video is a few frames only."))
        ai_grid_sizer.Add(self.local_note, 0, wx.EXPAND|wx.ALL, 5)
        ai_grid_sizer.Add((0, 0))
        self.local_download_button = wx.Button(self.ai_panel, label=_("&Download local model"))
        ai_grid_sizer.Add(self.local_download_button, 0, wx.ALL, 5)
        self.local_remove_button = wx.Button(self.ai_panel, label=_("&Remove model"))
        ai_grid_sizer.Add(self.local_remove_button, 0, wx.ALL, 5)
        ai_grid_sizer.Add(wx.StaticText(self.ai_panel, label=_("Temperature:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.temp_text_ctrl = wx.TextCtrl(self.ai_panel, value="0.7")
        ai_grid_sizer.Add(self.temp_text_ctrl, 1, wx.EXPAND|wx.ALL, 5)
        self.send_silenced_video_checkbox = wx.CheckBox(self.ai_panel, label=_("Send Video Only (No Audio) to AI"))
        ai_grid_sizer.Add(self.send_silenced_video_checkbox, 0, wx.EXPAND|wx.ALL, 5)
        self.disable_safety_checkbox = wx.CheckBox(self.ai_panel, label=_("Disable Safety Filters (Use with caution)"))
        ai_grid_sizer.Add(self.disable_safety_checkbox, 0, wx.EXPAND|wx.ALL, 5)
        self.enable_chunking_checkbox = wx.CheckBox(self.ai_panel, label=_("Enable Video Chunking for Long Videos"))
        ai_grid_sizer.Add(self.enable_chunking_checkbox, 0, wx.EXPAND|wx.ALL, 5)
        self.enable_character_glossary_checkbox = wx.CheckBox(self.ai_panel, label=_("Enable Character Glossary Pre-Analysis"))
        ai_grid_sizer.Add(self.enable_character_glossary_checkbox, 0, wx.EXPAND|wx.ALL, 5)
        self.chunk_duration_label = wx.StaticText(self.ai_panel, label=_("Chunk Duration (seconds):"))
        ai_grid_sizer.Add(self.chunk_duration_label, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.chunk_duration_spin = wx.SpinCtrl(self.ai_panel, value="120", min=30, max=2400)
        ai_grid_sizer.Add(self.chunk_duration_spin, 0, wx.EXPAND|wx.ALL, 5)
        self.ai_panel.SetSizer(ai_grid_sizer)
        self.notebook.AddPage(self.ai_panel, _("AI Settings"))

        # --- Audio Output Tab ---
        self.audio_output_panel = wx.Panel(self.notebook)
        audio_sizer = wx.BoxSizer(wx.VERTICAL)
        from ..core.narration_requests import PROVIDERS as NARRATION_PROVIDERS, ui_label as narration_label
        self.narration_provider_ids = [item["id"] for item in NARRATION_PROVIDERS]
        audio_sizer.Add(wx.StaticText(self.audio_output_panel, label=_("Narration provider:")), 0, wx.ALL, 5)
        self.narration_provider_choice = wx.Choice(self.audio_output_panel, choices=[narration_label(item["label"]) for item in NARRATION_PROVIDERS])
        audio_sizer.Add(self.narration_provider_choice, 0, wx.EXPAND | wx.ALL, 5)
        self.narration_model_label = wx.StaticText(self.audio_output_panel, label=_("Narration model:"))
        audio_sizer.Add(self.narration_model_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.narration_model_choice = wx.Choice(self.audio_output_panel)
        audio_sizer.Add(self.narration_model_choice, 0, wx.EXPAND | wx.ALL, 5)
        self.refresh_narration_models_button = wx.Button(self.audio_output_panel, label=_("&Refresh model list"))
        audio_sizer.Add(self.refresh_narration_models_button, 0, wx.ALL, 5)
        self.narration_voice_label = wx.StaticText(self.audio_output_panel, label=_("Narration voice:"))
        audio_sizer.Add(self.narration_voice_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.narration_voice_choice = wx.Choice(self.audio_output_panel)
        audio_sizer.Add(self.narration_voice_choice, 0, wx.EXPAND | wx.ALL, 5)
        self.narration_key_label = wx.StaticText(self.audio_output_panel, label=_("API key for this narration provider:"))
        audio_sizer.Add(self.narration_key_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.narration_key_text = wx.TextCtrl(self.audio_output_panel, style=wx.TE_PASSWORD)
        audio_sizer.Add(self.narration_key_text, 0, wx.EXPAND | wx.ALL, 5)
        self.erase_narration_key_button = wx.Button(self.audio_output_panel, label=_("&Erase key"))
        audio_sizer.Add(self.erase_narration_key_button, 0, wx.ALL, 5)
        self.refresh_voices_button = wx.Button(self.audio_output_panel, label=_("&Refresh voice list"))
        audio_sizer.Add(self.refresh_voices_button, 0, wx.ALL, 5)
        self.azure_region_label = wx.StaticText(self.audio_output_panel, label=_("Azure region (for example brazilsouth):"))
        audio_sizer.Add(self.azure_region_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.azure_region_text = wx.TextCtrl(self.audio_output_panel)
        audio_sizer.Add(self.azure_region_text, 0, wx.EXPAND | wx.ALL, 5)
        self.piper_exe_label = wx.StaticText(self.audio_output_panel, label=_("Piper program (piper.exe):"))
        audio_sizer.Add(self.piper_exe_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        self.piper_exe_text = wx.TextCtrl(self.audio_output_panel)
        audio_sizer.Add(self.piper_exe_text, 0, wx.EXPAND | wx.ALL, 5)
        self.tts_engine_choice = wx.RadioBox(self.audio_output_panel, label=_("Text-to-Speech Engine"), choices=[c[1] for c in self.TTS_ENGINE_CHOICES], majorDimension=1, style=wx.RA_SPECIFY_COLS)
        audio_sizer.Add(self.tts_engine_choice, 0, wx.EXPAND | wx.ALL, 5)
        self.openai_settings_panel = wx.Panel(self.audio_output_panel)
        openai_sizer = wx.StaticBoxSizer(wx.StaticBox(self.openai_settings_panel, label=_("OpenAI TTS Settings")), wx.VERTICAL)
        openai_grid = wx.FlexGridSizer(cols=2, gap=(5,5)); openai_grid.AddGrowableCol(1,1)
        openai_grid.Add(wx.StaticText(self.openai_settings_panel, label=_("Voice Preset:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.openai_voice_choice = wx.Choice(self.openai_settings_panel)
        openai_grid.Add(self.openai_voice_choice, 1, wx.EXPAND|wx.ALL, 5)
        openai_sizer.Add(openai_grid, 0, wx.EXPAND|wx.ALL, 5)
        self.manage_voices_button = wx.Button(self.openai_settings_panel, label=_("Manage Voice Presets..."))
        openai_sizer.Add(self.manage_voices_button, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.openai_settings_panel.SetSizer(openai_sizer)
        audio_sizer.Add(self.openai_settings_panel, 0, wx.EXPAND|wx.ALL, 5)
        self.sapi5_settings_panel = wx.Panel(self.audio_output_panel)
        
        # MODIFICATION: Keep a reference to the sizer, not just the panel
        self.sapi_sizer = wx.StaticBoxSizer(wx.StaticBox(self.sapi5_settings_panel, label=_("SAPI5 Settings")), wx.VERTICAL)
        sapi_grid = wx.FlexGridSizer(cols=2, gap=(5,5)); sapi_grid.AddGrowableCol(1,1)
        sapi_grid.Add(wx.StaticText(self.sapi5_settings_panel, label=_("Voice:")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.sapi_voice_choice = wx.Choice(self.sapi5_settings_panel) # Choices populated dynamically
        sapi_grid.Add(self.sapi_voice_choice, 1, wx.EXPAND|wx.ALL, 5)
        sapi_grid.Add(wx.StaticText(self.sapi5_settings_panel, label=_("Speed:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.sapi_rate_slider = wx.Slider(self.sapi5_settings_panel, value=100, minValue=50, maxValue=200)
        sapi_grid.Add(self.sapi_rate_slider, 1, wx.EXPAND|wx.ALL, 5)
        self.sapi_sizer.Add(sapi_grid, 1, wx.EXPAND | wx.ALL, 5)
        self.sapi5_settings_panel.SetSizer(self.sapi_sizer)
        
        audio_sizer.Add(self.sapi5_settings_panel, 0, wx.EXPAND|wx.ALL, 5)
        
        test_box = wx.StaticBox(self.audio_output_panel, label=_("Test Voice"))
        test_sizer = wx.StaticBoxSizer(test_box, wx.VERTICAL)
        self.test_text_ctrl = wx.TextCtrl(self.audio_output_panel, value=_("This is a test of the selected voice."))
        test_sizer.Add(self.test_text_ctrl, 0, wx.EXPAND|wx.ALL, 5)
        self.test_voice_button = wx.Button(self.audio_output_panel, label=_("Test"))
        test_sizer.Add(self.test_voice_button, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        audio_sizer.Add(test_sizer, 0, wx.EXPAND|wx.ALL, 5)
        
        self.ducking_checkbox = wx.CheckBox(self.audio_output_panel, label=_("&Duck original audio under the narration"))
        audio_sizer.Add(self.ducking_checkbox, 0, wx.ALL, 5)
        self.ducking_label = wx.StaticText(self.audio_output_panel, label=_("Ducking level (-dB):"))
        audio_sizer.Add(self.ducking_label, 0, wx.ALL, 5)
        self.ducking_spin = wx.SpinCtrl(self.audio_output_panel, value="-15", min=-60, max=0)
        audio_sizer.Add(self.ducking_spin, 0, wx.EXPAND|wx.ALL, 5)
        self.keep_original_checkbox = wx.CheckBox(self.audio_output_panel, label=_("&Keep the original audio as a second track"))
        audio_sizer.Add(self.keep_original_checkbox, 0, wx.ALL, 5)
        self.audio_output_panel.SetSizer(audio_sizer)
        self.notebook.AddPage(self.audio_output_panel, _("Audio Output"))

        self.main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        button_sizer = wx.StdDialogButtonSizer()
        self.apply_button = wx.Button(self, wx.ID_APPLY); button_sizer.AddButton(self.apply_button)
        self.ok_button = wx.Button(self, wx.ID_OK); self.ok_button.SetDefault(); button_sizer.AddButton(self.ok_button)
        self.cancel_button = wx.Button(self, wx.ID_CANCEL); button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize(); self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        self.BindAllEvents()
        self.apply_button.Disable()

    def BindAllEvents(self):
        self.Bind(EVT_TEST_VOICE_DONE, self._OnTestVoiceFinished)
        self.Bind(wx.EVT_BUTTON, self.OnTestVoice, self.test_voice_button)
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.OnApply, id=wx.ID_APPLY)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self.OnCancel)
        self.yt_quality_choice.Bind(wx.EVT_CHOICE, self.OnSettingChanged)
        self.app_lang_choice.Bind(wx.EVT_CHOICE, self.OnSettingChanged)
        self.log_level_choice.Bind(wx.EVT_CHOICE, self.OnSettingChanged)
        self.interrupt_speech_checkbox.Bind(wx.EVT_CHECKBOX, self.OnSettingChanged)
        self.api_key_text.Bind(wx.EVT_TEXT, self.OnSettingChanged)
        self.clear_key_button.Bind(wx.EVT_BUTTON, self.OnEraseKey)
        self.frame_rate_choice.Bind(wx.EVT_CHOICE, self.OnSettingChanged)
        self.verbosity_choice.Bind(wx.EVT_CHOICE, self.OnSettingChanged)
        self.model_override_text.Bind(wx.EVT_TEXT, self.OnSettingChanged)
        self.analysis_provider_choice.Bind(wx.EVT_CHOICE, self.OnAnalysisProviderChanged)
        self.local_download_button.Bind(wx.EVT_BUTTON, self.OnDownloadLocal)
        self.local_remove_button.Bind(wx.EVT_BUTTON, self.OnRemoveLocal)
        self.context_menu_checkbox.Bind(wx.EVT_CHECKBOX, self.OnSettingChanged)
        self.check_updates_checkbox.Bind(wx.EVT_CHECKBOX, self.OnSettingChanged)
        self.check_updates_button.Bind(wx.EVT_BUTTON, self.OnCheckUpdates)
        self.analysis_model_choice.Bind(wx.EVT_CHOICE, self.OnAnalysisModelChanged)
        self.analysis_key_text.Bind(wx.EVT_TEXT, self.OnSettingChanged)
        self.temp_text_ctrl.Bind(wx.EVT_TEXT, self.OnSettingChanged)
        self.temp_text_ctrl.Bind(wx.EVT_KILL_FOCUS, self.OnTemperatureKillFocus)
        self.send_silenced_video_checkbox.Bind(wx.EVT_CHECKBOX, self.OnSettingChanged)
        self.disable_safety_checkbox.Bind(wx.EVT_CHECKBOX, self.OnSettingChanged)
        self.enable_chunking_checkbox.Bind(wx.EVT_CHECKBOX, self.OnSettingChanged)
        self.chunk_duration_spin.Bind(wx.EVT_SPINCTRL, self.OnSettingChanged)
        self.enable_character_glossary_checkbox.Bind(wx.EVT_CHECKBOX, self.OnSettingChanged)
        self.tts_engine_choice.Bind(wx.EVT_RADIOBOX, self.OnTtsEngineChanged)
        self.narration_provider_choice.Bind(wx.EVT_CHOICE, self.OnNarrationProviderChanged)
        self.narration_model_choice.Bind(wx.EVT_CHOICE, self.OnNarrationModelChanged)
        self.narration_voice_choice.Bind(wx.EVT_CHOICE, self.OnSettingChanged)
        self.narration_key_text.Bind(wx.EVT_TEXT, self.OnSettingChanged)
        self.azure_region_text.Bind(wx.EVT_TEXT, self.OnSettingChanged)
        self.piper_exe_text.Bind(wx.EVT_TEXT, self.OnSettingChanged)
        self.refresh_voices_button.Bind(wx.EVT_BUTTON, self.OnRefreshVoices)
        self.refresh_analysis_models_button.Bind(wx.EVT_BUTTON, self.OnRefreshAnalysisModels)
        self.refresh_narration_models_button.Bind(wx.EVT_BUTTON, self.OnRefreshNarrationModels)
        self.erase_narration_key_button.Bind(wx.EVT_BUTTON, self.OnEraseNarrationKey)
        self.tts_engine_choice.Hide()
        self.openai_voice_choice.Bind(wx.EVT_CHOICE, self.OnSettingChanged)
        self.manage_voices_button.Bind(wx.EVT_BUTTON, self.OnManageVoices)
        self.sapi_voice_choice.Bind(wx.EVT_CHOICE, self.OnSettingChanged)
        self.sapi_rate_slider.Bind(wx.EVT_SLIDER, self.OnSettingChanged)
        self.ducking_spin.Bind(wx.EVT_SPINCTRL, self.OnSettingChanged)
        self.ducking_checkbox.Bind(wx.EVT_CHECKBOX, self.OnSettingChanged)
        self.keep_original_checkbox.Bind(wx.EVT_CHECKBOX, self.OnSettingChanged)

    def OnTestVoice(self, event):
        text = self.test_text_ctrl.GetValue()
        if not text:
            wx.MessageBox(_("Please enter some text to test."), _("Input Required"), wx.OK | wx.ICON_WARNING, self)
            return

        engine_choice = self.TTS_ENGINE_CHOICES[self.tts_engine_choice.GetSelection()][0]
        
        settings = {
            "openai_api_key": (getattr(self, "_key_cache", {}) or {}).get("openai", ""),
            "openai_voice_preset": self.openai_voice_choice.GetStringSelection(),
            "openai_tts_model": config_model.get_setting("openai_tts_model"),
            "sapi5_voice_id": self.sapi_voices[self.sapi_voice_choice.GetSelection()]['id'] if self.sapi_voices and self.sapi_voice_choice.GetSelection() != wx.NOT_FOUND else None,
            "sapi5_rate_percent": self.sapi_rate_slider.GetValue(),
            "onecore_voice_id": self.sapi_voices[self.sapi_voice_choice.GetSelection()]['id'] if self.sapi_voices and self.sapi_voice_choice.GetSelection() != wx.NOT_FOUND else None,
            "onecore_rate_percent": self.sapi_rate_slider.GetValue(),
        }
        
        self.test_voice_button.Disable()
        wx.BeginBusyCursor()
        thread = threading.Thread(target=self._TestVoiceThread, args=(engine_choice, text, settings))
        thread.daemon = True
        thread.start()

    def _TestVoiceThread(self, engine_choice, text, settings):
        error = None
        try:
            tts_engine.test_voice(engine_choice, text, settings)
        except Exception as e:
            error = e
        finally:
            wx.PostEvent(self, TestVoiceDoneEvent(error=error))

    def _OnTestVoiceFinished(self, event):
        wx.EndBusyCursor()
        self.test_voice_button.Enable()
        if event.error:
            wx.MessageBox(_("Error testing voice: %s") % event.error, _("Test Failed"), wx.OK | wx.ICON_ERROR, self)
            
    def OnTtsEngineChanged(self, event):
        self.UpdateTtsEnginePanels()
        self.OnSettingChanged(event)

    def UpdateTtsEnginePanels(self):
        selected_engine = self.TTS_ENGINE_CHOICES[self.tts_engine_choice.GetSelection()][0]
        
        is_openai = (selected_engine == "openai")
        is_sapi = selected_engine.startswith("sapi5") or selected_engine == "onecore"
        
        self.openai_settings_panel.Show(is_openai)
        self.sapi5_settings_panel.Show(is_sapi)

        if is_sapi:
            # MODIFICATION: Use the sizer reference to get the static box
            box_label = _("SAPI5 (64-bit) Settings")
            if selected_engine == "sapi5_32bit":
                self.sapi_voices = tts_engine.get_available_sapi5_voices_32bit()
                box_label = _("SAPI5 (32-bit) Settings")
            elif selected_engine == "onecore":
                self.sapi_voices = tts_engine.get_available_onecore_voices()
                box_label = _("Windows OneCore Settings")
            else: # sapi5 (64-bit)
                self.sapi_voices = tts_engine.get_available_sapi5_voices()
            self.sapi_sizer.GetStaticBox().SetLabel(box_label)
            
            self.sapi_voice_choice.Clear()
            self.sapi_voice_choice.Enable()
            self.sapi_voice_choice.Show()
            if self.sapi_voices:
                for voice in self.sapi_voices:
                    self.sapi_voice_choice.Append(voice['name'])
            else:
                self.sapi_voice_choice.Append(_("Could not list the voices."))
                app_logger.error("SAPI voice list is empty for engine %s.", selected_engine)
            self.sapi_voice_choice.SetSelection(0)

        self.audio_output_panel.Layout()
        
    def OnManageVoices(self, event):
        with ManageVoicesDialog(self) as dlg:
            dlg.ShowModal()
        self.PopulateOpenAiVoices()
        self.OnSettingChanged(event)

    def PopulateOpenAiVoices(self):
        self.openai_voice_choice.Clear()
        voices = voice_model.get_voices()
        for voice in voices:
            self.openai_voice_choice.Append(voice["name"])
        
        current_preset = self.current_settings.get("openai_tts_voice", "")
        if current_preset and self.openai_voice_choice.FindString(current_preset) != wx.NOT_FOUND:
            self.openai_voice_choice.SetStringSelection(current_preset)
        elif self.openai_voice_choice.GetCount() > 0:
            self.openai_voice_choice.SetSelection(0)

    def LoadSettingsToUI(self):
        self.current_settings = config_model.app_settings.copy()
        
        self.yt_quality_choice.SetStringSelection(self.current_settings.get("youtube_download_quality", "144p"))
        
        saved_lang = self.current_settings.get("application_language", "")
        try:
            self.app_lang_choice.SetSelection(self.app_lang_internal_values.index(saved_lang))
        except ValueError:
            self.app_lang_choice.SetSelection(0)
            
        self.log_level_choice.SetSelection(self.log_level_internal_values.index(self.current_settings.get("logging_level", "INFO")))
        self.interrupt_speech_checkbox.SetValue(self.current_settings.get("player_allow_speech_interruption", True))
        
        self._load_provider_keys()
        self.frame_rate_choice.SetSelection(self.frame_rate_internal_values.index(self.current_settings.get("frame_rate_for_ai", 0)))
        self.verbosity_choice.SetSelection(self.verbosity_internal_values.index(self.current_settings.get("gemini_description_verbosity", config.DEFAULT_VERBOSITY)))
        self._load_analysis_controls()
        self.model_override_text.SetValue(self.current_settings.get("analysis_model_custom") or self.current_settings.get("gemini_model_override", ""))
        self.temp_text_ctrl.SetValue(str(self.current_settings.get("gemini_temperature", 0.7)))
        self.send_silenced_video_checkbox.SetValue(self.current_settings.get("send_silenced_video_to_ai", True))
        self.disable_safety_checkbox.SetValue(self.current_settings.get("gemini_disable_safety_block_none", False))
        
        is_chunking = self.current_settings.get("enable_video_chunking", False)
        self.enable_chunking_checkbox.SetValue(is_chunking)
        self.chunk_duration_spin.SetValue(self.current_settings.get("video_chunk_duration_seconds", 120))
        self.chunk_duration_label.Enable(is_chunking)
        self.chunk_duration_spin.Enable(is_chunking)
        self.enable_character_glossary_checkbox.SetValue(self.current_settings.get("enable_character_glossary", False))
        
        tts_engine_val = self.current_settings.get("tts_engine", "sapi5")
        try:
            self.tts_engine_choice.SetSelection([c[0] for c in self.TTS_ENGINE_CHOICES].index(tts_engine_val))
        except ValueError:
            self.tts_engine_choice.SetSelection(0)
        
        self.UpdateTtsEnginePanels()
        self._load_narration_controls()
        self.PopulateOpenAiVoices()
        
        # Load voice settings based on the selected TTS engine
        selected_engine = self.current_settings.get("tts_engine", "sapi5")
        if selected_engine == "onecore":
            saved_voice_id = self.current_settings.get("onecore_voice_id")
        else:
            saved_voice_id = self.current_settings.get("sapi5_voice_id")
            
        for i, voice in enumerate(self.sapi_voices):
            if voice['id'] == saved_voice_id:
                self.sapi_voice_choice.SetSelection(i)
                break
        
        # Load rate setting
        if selected_engine == "onecore":
            self.sapi_rate_slider.SetValue(self.current_settings.get("onecore_voice_rate_percent", 100))
        else:
            self.sapi_rate_slider.SetValue(self.current_settings.get("sapi5_voice_rate_percent", 100))
        self.ducking_checkbox.SetValue(bool(self.current_settings.get("audio_ducking_enabled", True)))
        self.ducking_spin.SetValue(self.current_settings.get("mp3_audio_ducking_level_db", -15))
        self.keep_original_checkbox.SetValue(bool(self.current_settings.get("export_keep_original_audio", False)))
        self._sync_ducking_level_visibility()
        from ..utils.shell_menu import is_registered
        self.context_menu_checkbox.SetValue(is_registered())
        self.check_updates_checkbox.SetValue(bool(self.current_settings.get("check_updates_on_startup", True)))
        
        self.settings_changed = False
        self.apply_button.Disable()

    def _analysis_selection_is_custom(self):
        selection = self.analysis_model_choice.GetSelection()
        if selection == wx.NOT_FOUND or not getattr(self, "_analysis_model_ids", None):
            return False
        return self._analysis_model_ids[selection] == self._analysis_custom_id

    def _layout_keeping_focus(self, panel):
        focused = self.FindFocus()
        panel.Layout()
        self.Layout()
        if focused is not None and focused.IsShown():
            focused.SetFocus()

    def _fill_analysis_models(self, provider_id, selected_id=""):
        from ..core.analysis_providers import FALLBACK_MODELS
        from ..core.local_model import LOCAL_MODELS
        from ..core.model_refresh import ids_to_show
        from ..models import config_model
        if provider_id == "local":
            labels = {
                "qwen25vl-3b": _("Qwen2.5-VL 3B, about 3 GB, 8 GB of RAM"),
                "qwen25vl-7b": _("Qwen2.5-VL 7B, about 6 GB, 16 GB of RAM"),
                "gemma3-4b": _("Gemma 3 4B, about 3.3 GB, 8 GB of RAM"),
                "gemma3-12b": _("Gemma 3 12B, about 8.2 GB, 16 GB of RAM"),
            }
            builtin = [item["id"] for item in LOCAL_MODELS]
            shown = ids_to_show((config_model.get_setting("cached_analysis_models") or {}).get(provider_id), builtin)
            models = [(model_id, labels.get(model_id, model_id)) for model_id in shown]
        else:
            builtin = list(FALLBACK_MODELS.get(provider_id, ()))
            shown = ids_to_show((config_model.get_setting("cached_analysis_models") or {}).get(provider_id), builtin)
            models = [(model_id, model_id) for model_id in shown]
            models.append((self._analysis_custom_id, _("Custom model name")))
        self._analysis_model_ids = [item[0] for item in models]
        self.analysis_model_choice.Clear()
        for _model_id, label in models:
            self.analysis_model_choice.Append(label)
        try:
            self.analysis_model_choice.SetSelection(self._analysis_model_ids.index(selected_id))
        except ValueError:
            self.analysis_model_choice.SetSelection(0)
        self._show_analysis_extras()

    def _show_analysis_extras(self):
        provider_id = self.analysis_provider_ids[max(0, self.analysis_provider_choice.GetSelection())]
        custom = self._analysis_selection_is_custom()
        local = provider_id == "local"
        self.analysis_custom_label.Show(custom and not local)
        self.model_override_text.Show(custom and not local)
        self.analysis_key_label.Hide()
        self.analysis_key_text.Hide()
        show_key = not local
        self.provider_key_label.Show(show_key)
        self.api_key_text.Show(show_key)
        self.clear_key_button.Show(show_key)
        self.local_note.Show(local)
        installed = False
        if local:
            from ..core.local_model import is_installed
            model_id = self._analysis_model_ids[max(0, self.analysis_model_choice.GetSelection())]
            installed = is_installed(model_id)
        self.local_download_button.Show(local and not installed)
        self.local_remove_button.Show(local and installed)
        self._layout_keeping_focus(self.ai_panel)

    def _load_analysis_controls(self):
        provider_id = self.current_settings.get("analysis_provider") or "gemini"
        try:
            self.analysis_provider_choice.SetSelection(self.analysis_provider_ids.index(provider_id))
        except ValueError:
            self.analysis_provider_choice.SetSelection(0)
            provider_id = "gemini"
        selected = self.current_settings.get("analysis_model") or ""
        if not selected and self.current_settings.get("gemini_model_override"):
            selected = self._analysis_custom_id
        self._fill_analysis_models(provider_id, selected)
        self._shown_provider = provider_id
        self._show_provider_key(provider_id)

    def _load_provider_keys(self):
        from ..core.analysis_settings import provider_ids, read_key
        self._key_cache = {provider_id: read_key(self.current_settings, provider_id) for provider_id in provider_ids()}

    def _provider_key_label(self, provider_id):
        labels = {
            "gemini": _("Gemini API key:"),
            "openai": _("OpenAI API key:"),
            "xai": _("xAI API key:"),
            "anthropic": _("Anthropic API key:"),
            "qwen": _("Qwen API key:"),
            "openrouter": _("OpenRouter API key:"),
        }
        return labels.get(provider_id, _("API key:"))

    def _show_provider_key(self, provider_id):
        self.provider_key_label.SetLabel(self._provider_key_label(provider_id))
        self.api_key_text.ChangeValue(self._key_cache.get(provider_id, ""))

    def _remember_provider_key(self):
        provider_id = getattr(self, "_shown_provider", None)
        if not provider_id or not hasattr(self, "_key_cache"):
            return
        self._key_cache[provider_id] = self.api_key_text.GetValue().strip()

    def _save_analysis_controls(self):
        from ..core.analysis_settings import write_key
        self._remember_provider_key()
        provider_id = self.analysis_provider_ids[self.analysis_provider_choice.GetSelection()]
        self.current_settings["analysis_provider"] = provider_id
        model_id = self._analysis_model_ids[self.analysis_model_choice.GetSelection()]
        self.current_settings["analysis_model"] = model_id
        self.current_settings["analysis_model_custom"] = self.model_override_text.GetValue().strip()
        for saved_id, value in self._key_cache.items():
            write_key(self.current_settings, saved_id, value)

    def OnEraseKey(self, event):
        from .accessibility_utils import speak_message
        provider_id = getattr(self, "_shown_provider", None)
        self.api_key_text.ChangeValue("")
        if provider_id and hasattr(self, "_key_cache"):
            self._key_cache[provider_id] = ""
        self.OnSettingChanged(event)
        self.api_key_text.SetFocus()
        speak_message(_("Key erased."))

    def OnAnalysisProviderChanged(self, event):
        self._remember_provider_key()
        provider_id = self.analysis_provider_ids[self.analysis_provider_choice.GetSelection()]
        self._shown_provider = provider_id
        self._show_provider_key(provider_id)
        self._fill_analysis_models(provider_id)
        self.OnSettingChanged(event)

    def OnDownloadLocal(self, event):
        from .model_download_dialog import download_local_model
        model_id = self._analysis_model_ids[self.analysis_model_choice.GetSelection()]
        if download_local_model(self, model_id):
            self._show_analysis_extras()
        event.Skip()

    def OnRemoveLocal(self, event):
        from ..core.local_model import remove_model
        model_id = self._analysis_model_ids[self.analysis_model_choice.GetSelection()]
        remove_model(model_id)
        self._show_analysis_extras()
        event.Skip()

    def OnAnalysisModelChanged(self, event):
        self._show_analysis_extras()
        self.OnSettingChanged(event)

    def _narration_provider_id(self):
        selection = self.narration_provider_choice.GetSelection()
        if selection == wx.NOT_FOUND:
            return "windows"
        return self.narration_provider_ids[selection]

    def _fill_narration_models(self, provider_id, selected=""):
        from ..core.narration_requests import models_for
        from ..core.model_refresh import ids_to_show
        from ..models import config_model
        builtin = models_for(provider_id)
        cached = (config_model.get_setting("cached_narration_models") or {}).get(provider_id)
        if cached:
            labels = {item[0]: item[1] for item in builtin}
            models = [(model_id, labels.get(model_id, model_id)) for model_id in ids_to_show(cached, [item[0] for item in builtin])]
        else:
            models = builtin
        self._narration_model_ids = [item[0] for item in models]
        self.narration_model_choice.Clear()
        from ..core.narration_requests import ui_label as narration_label
        for _model_id, label in models:
            self.narration_model_choice.Append(narration_label(label))
        try:
            self.narration_model_choice.SetSelection(self._narration_model_ids.index(selected))
        except ValueError:
            self.narration_model_choice.SetSelection(0)
        self._fill_narration_voices()

    def _fill_narration_voices(self):
        from ..core.narration_engine import list_piper_voices
        from ..core.narration_requests import builtin_voices
        provider_id = self._narration_provider_id()
        model = self._narration_model_ids[max(0, self.narration_model_choice.GetSelection())]
        if provider_id == "piper":
            voices = list_piper_voices()
        elif provider_id == "windows":
            voices = []
        else:
            voices = builtin_voices(provider_id, model)
        self._narration_voice_ids = [item["id"] for item in voices]
        self.narration_voice_choice.Clear()
        if voices:
            for item in voices:
                self.narration_voice_choice.Append(item["name"])
            saved = self.current_settings.get("narration_voice") or ""
            try:
                self.narration_voice_choice.SetSelection(self._narration_voice_ids.index(saved))
            except ValueError:
                self.narration_voice_choice.SetSelection(0)
        else:
            self.narration_voice_choice.Append(_("(No voices found)"))
            self.narration_voice_choice.SetSelection(0)

    def _show_narration_fields(self):
        provider_id = self._narration_provider_id()
        model = self._narration_model_ids[max(0, self.narration_model_choice.GetSelection())]
        is_windows = provider_id == "windows"
        is_piper = provider_id == "piper"
        needs_key = provider_id not in ("windows", "piper", "gemini", "openai")
        self.narration_voice_label.Show(not is_windows)
        self.narration_voice_choice.Show(not is_windows)
        self.narration_key_label.Show(needs_key)
        self.narration_key_text.Show(needs_key)
        self.azure_region_label.Show(provider_id == "azure")
        self.azure_region_text.Show(provider_id == "azure")
        self.piper_exe_label.Show(is_piper)
        self.piper_exe_text.Show(is_piper)
        self.refresh_voices_button.Show(not is_windows and not is_piper)
        self.erase_narration_key_button.Show(needs_key)
        self.tts_engine_choice.Hide()
        if is_windows:
            engine = {"onecore": "onecore", "sapi4": "sapi5_32bit"}.get(model, "sapi5")
            try:
                self.tts_engine_choice.SetSelection([c[0] for c in self.TTS_ENGINE_CHOICES].index(engine))
            except ValueError:
                self.tts_engine_choice.SetSelection(0)
            self.UpdateTtsEnginePanels()
        else:
            self.openai_settings_panel.Hide()
            self.sapi5_settings_panel.Hide()
        self._layout_keeping_focus(self.audio_output_panel)

    def _load_narration_controls(self):
        provider_id = self.current_settings.get("narration_provider") or "windows"
        try:
            self.narration_provider_choice.SetSelection(self.narration_provider_ids.index(provider_id))
        except ValueError:
            self.narration_provider_choice.SetSelection(0)
            provider_id = "windows"
        model = self.current_settings.get("narration_model") or ""
        if provider_id == "windows" and not model:
            legacy = self.current_settings.get("tts_engine") or "sapi5"
            model = {"onecore": "onecore", "sapi5_32bit": "sapi4"}.get(legacy, "sapi5")
        self._fill_narration_models(provider_id, model)
        keys = self.current_settings.get("narration_api_keys") or {}
        self.narration_key_text.SetValue(keys.get(provider_id, "") if isinstance(keys, dict) else "")
        self.azure_region_text.SetValue(self.current_settings.get("azure_speech_region") or "")
        self.piper_exe_text.SetValue(self.current_settings.get("piper_exe") or "")
        self._show_narration_fields()

    def _save_narration_controls(self):
        provider_id = self._narration_provider_id()
        model = self._narration_model_ids[max(0, self.narration_model_choice.GetSelection())]
        self.current_settings["narration_provider"] = provider_id
        self.current_settings["narration_model"] = model
        if self._narration_voice_ids and self.narration_voice_choice.GetSelection() != wx.NOT_FOUND:
            index = self.narration_voice_choice.GetSelection()
            if index < len(self._narration_voice_ids):
                self.current_settings["narration_voice"] = self._narration_voice_ids[index]
        keys = dict(self.current_settings.get("narration_api_keys") or {})
        keys[provider_id] = self.narration_key_text.GetValue().strip()
        self.current_settings["narration_api_keys"] = keys
        self.current_settings["azure_speech_region"] = self.azure_region_text.GetValue().strip()
        self.current_settings["piper_exe"] = self.piper_exe_text.GetValue().strip()
        if provider_id == "windows":
            self.current_settings["tts_engine"] = {"onecore": "onecore", "sapi4": "sapi5_32bit"}.get(model, "sapi5")
        elif provider_id == "openai":
            self.current_settings["tts_engine"] = "openai"
            if self.current_settings.get("narration_voice"):
                self.current_settings["openai_tts_voice"] = self.current_settings["narration_voice"]
            self.current_settings["openai_tts_model"] = model

    def _narration_key_for_refresh(self):
        provider_id = self._narration_provider_id()
        if provider_id in ("gemini", "openai"):
            self._remember_provider_key()
            return (self._key_cache or {}).get(provider_id, "")
        return self.narration_key_text.GetValue().strip()

    def _run_refresh(self, button, start_message, work, apply_result):
        from .accessibility_utils import speak_message
        from ..core.model_refresh import MissingKey, call_with_timeout
        if getattr(self, "_refresh_busy", False):
            return
        self._refresh_busy = True
        button.Disable()
        speak_message(start_message)

        def worker():
            try:
                result = call_with_timeout(work, timeout=25)
                error = None
            except Exception as exc:
                result = None
                error = exc
            wx.CallAfter(self._refresh_done, button, result, error, apply_result)

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_done(self, button, result, error, apply_result):
        from .accessibility_utils import speak_message
        from ..core.model_refresh import MissingKey
        self._refresh_busy = False
        button.Enable()
        if button.IsShown():
            button.SetFocus()
        if isinstance(error, MissingKey):
            speak_message(_("The AI key is missing."))
            return
        if error is not None:
            from ..utils.logger import app_logger
            app_logger.error("Refresh failed: %s", error)
            speak_message(_("Could not update the list."))
            return
        apply_result(result)

    def OnRefreshVoices(self, event):
        from ..core.narration_engine import fetch_remote_voices
        from ..core.model_refresh import MissingKey
        provider_id = self._narration_provider_id()
        key = self._narration_key_for_refresh()
        if provider_id not in ("windows", "piper") and not key:
            from .accessibility_utils import speak_message
            speak_message(_("The AI key is missing."))
            return
        model = self._narration_model_ids[max(0, self.narration_model_choice.GetSelection())]
        region = self.azure_region_text.GetValue().strip()

        def work():
            if not key and provider_id not in ("windows", "piper"):
                raise MissingKey()
            return fetch_remote_voices(provider_id, key, model, region)

        def apply_result(voices):
            from .accessibility_utils import speak_message
            from ..core.model_refresh import fill_choice_in_place
            voices = voices or []
            keep = ""
            if self._narration_voice_ids and self.narration_voice_choice.GetSelection() != wx.NOT_FOUND:
                index = self.narration_voice_choice.GetSelection()
                if index < len(self._narration_voice_ids):
                    keep = self._narration_voice_ids[index]
            self._narration_voice_ids = [item["id"] for item in voices] or [""]
            labels = [item["name"] for item in voices] or [_("(No voices found)")]
            fill_choice_in_place(self.narration_voice_choice, labels, self._narration_voice_ids, keep)
            speak_message(_("%d voices.") % len(voices))

        self._run_refresh(self.refresh_voices_button, _("Updating voices..."), work, apply_result)

    def OnEraseNarrationKey(self, event):
        from .accessibility_utils import speak_message
        self.narration_key_text.ChangeValue("")
        self.OnSettingChanged(event)
        self.narration_key_text.SetFocus()
        speak_message(_("Key erased."))

    def OnNarrationProviderChanged(self, event):
        provider_id = self._narration_provider_id()
        previous = self.current_settings.get("narration_model") or ""
        self._fill_narration_models(provider_id, previous)
        keys = self.current_settings.get("narration_api_keys") or {}
        self.narration_key_text.ChangeValue(keys.get(provider_id, "") if isinstance(keys, dict) else "")
        self._show_narration_fields()
        self.OnSettingChanged(event)

    def OnNarrationModelChanged(self, event):
        self._fill_narration_voices()
        self._show_narration_fields()
        self.OnSettingChanged(event)

    def OnRefreshAnalysisModels(self, event):
        self._refresh_model_list(self.refresh_analysis_models_button, "analysis")

    def OnRefreshNarrationModels(self, event):
        self._refresh_model_list(self.refresh_narration_models_button, "narration")

    def _refresh_model_list(self, button, kind):
        from ..core.model_refresh import MissingKey, analysis_list_request, choose_ids, fetch_ids, narration_list_request
        from ..core.analysis_providers import FALLBACK_MODELS
        from ..core.local_model import LOCAL_MODELS
        from ..core.narration_requests import models_for
        if kind == "analysis":
            provider_id = self.analysis_provider_ids[max(0, self.analysis_provider_choice.GetSelection())]
            self._remember_provider_key()
            key = (self._key_cache or {}).get(provider_id, "")
            builtin = [item["id"] for item in LOCAL_MODELS] if provider_id == "local" else list(FALLBACK_MODELS.get(provider_id, ()))
            request_builder = analysis_list_request
            cache_name = "cached_analysis_models"
            vision = True
        else:
            provider_id = self._narration_provider_id()
            key = self._narration_key_for_refresh()
            builtin = [item[0] for item in models_for(provider_id)]
            request_builder = narration_list_request
            cache_name = "cached_narration_models"
            vision = False
        if provider_id != "local" and provider_id not in ("windows", "piper") and not key and request_builder(provider_id, "x"):
            from .accessibility_utils import speak_message
            speak_message(_("The AI key is missing."))
            return

        def work():
            if provider_id in ("local", "windows", "piper"):
                return list(builtin)
            if not key:
                raise MissingKey()
            request = request_builder(provider_id, key)
            if request is None:
                return list(builtin)
            payload = fetch_ids(request)
            from ..core.model_refresh import _ids_from_payload
            raw = _ids_from_payload(provider_id, payload)
            return choose_ids(provider_id, raw, builtin, vision=vision)

        def apply_result(ids):
            from .accessibility_utils import speak_message
            from ..models import config_model
            cache = dict(self.current_settings.get(cache_name) or {})
            cache[provider_id] = list(ids)
            self.current_settings[cache_name] = cache
            config_model.app_settings[cache_name] = cache
            config_model.save_settings(config_model.app_settings)
            if kind == "analysis":
                selected = self._analysis_model_ids[max(0, self.analysis_model_choice.GetSelection())] if self._analysis_model_ids else ""
                self._fill_analysis_models(provider_id, selected)
            else:
                selected = self._narration_model_ids[max(0, self.narration_model_choice.GetSelection())] if self._narration_model_ids else ""
                self._fill_narration_models(provider_id, selected)
            speak_message(_("%d models found.") % len(ids))

        self._run_refresh(button, _("Updating models..."), work, apply_result)

    def OnCheckUpdates(self, event):
        from ..utils import update_checker
        from .accessibility_utils import speak_message
        speak_message(_("Checking for updates."))
        update_checker.start_check(self, self._settings_language(), _, announce=True)

    def _settings_language(self):
        return self.current_settings.get("application_language") or "pt_BR"

    def ApplySettings(self):
        self.current_settings["youtube_download_quality"] = self.yt_quality_choice.GetStringSelection()
        self.current_settings["application_language"] = self.app_lang_internal_values[self.app_lang_choice.GetSelection()]
        self.current_settings["logging_level"] = self.log_level_internal_values[self.log_level_choice.GetSelection()]
        self.current_settings["player_allow_speech_interruption"] = self.interrupt_speech_checkbox.IsChecked()
        
        self.current_settings["frame_rate_for_ai"] = self.frame_rate_internal_values[self.frame_rate_choice.GetSelection()]
        self.current_settings["gemini_description_verbosity"] = self.verbosity_internal_values[self.verbosity_choice.GetSelection()]
        self._save_analysis_controls()
        self.current_settings["gemini_model_override"] = self.model_override_text.GetValue().strip() if self._analysis_selection_is_custom() else ""
        try: self.current_settings["gemini_temperature"] = float(self.temp_text_ctrl.GetValue().strip())
        except ValueError: self.current_settings["gemini_temperature"] = config_model.DEFAULT_SETTINGS["gemini_temperature"]
        self.current_settings["send_silenced_video_to_ai"] = self.send_silenced_video_checkbox.IsChecked()
        self.current_settings["gemini_disable_safety_block_none"] = self.disable_safety_checkbox.IsChecked()
        self.current_settings["enable_video_chunking"] = self.enable_chunking_checkbox.IsChecked()
        self.current_settings["video_chunk_duration_seconds"] = self.chunk_duration_spin.GetValue()
        self.current_settings["enable_character_glossary"] = self.enable_character_glossary_checkbox.IsChecked()
        self.current_settings["context_menu_enabled"] = self.context_menu_checkbox.IsChecked()
        self.current_settings["check_updates_on_startup"] = self.check_updates_checkbox.IsChecked()
        from ..utils.shell_menu import apply_shell_menu
        apply_shell_menu(self.context_menu_checkbox.IsChecked())
        
        self._save_narration_controls()
        if self._narration_provider_id() != "openai":
            picked_voice = self.openai_voice_choice.GetStringSelection()
            if picked_voice:
                self.current_settings["openai_tts_voice"] = picked_voice
        
        # Save voice settings based on the selected TTS engine
        selected_engine = self.current_settings["tts_engine"]
        voice_id = None
        if self.sapi_voices and self.sapi_voice_choice.GetSelection() != wx.NOT_FOUND:
            voice_id = self.sapi_voices[self.sapi_voice_choice.GetSelection()]['id']
        
        # Save to appropriate settings based on engine
        if selected_engine == "onecore":
            self.current_settings["onecore_voice_id"] = voice_id
            self.current_settings["onecore_voice_rate_percent"] = self.sapi_rate_slider.GetValue()
            # Also save to sapi5 for backward compatibility
            self.current_settings["sapi5_voice_id"] = voice_id
            self.current_settings["sapi5_voice_rate_percent"] = self.sapi_rate_slider.GetValue()
        else:
            # For other engines (sapi5, sapi5_32bit), save to sapi5 settings
            self.current_settings["sapi5_voice_id"] = voice_id
            self.current_settings["sapi5_voice_rate_percent"] = self.sapi_rate_slider.GetValue()
            # Clear onecore settings when not using onecore
            self.current_settings["onecore_voice_id"] = None
            self.current_settings["onecore_voice_rate_percent"] = 100

        self.current_settings["audio_ducking_enabled"] = self.ducking_checkbox.IsChecked()
        self.current_settings["mp3_audio_ducking_level_db"] = self.ducking_spin.GetValue()
        self.current_settings["export_keep_original_audio"] = self.keep_original_checkbox.IsChecked()
        
        config_model.app_settings.update(self.current_settings)
        if config_model.save_settings(config_model.app_settings):
            self.settings_changed = False
            self.apply_button.Disable()
            from audio_describer.utils import logger
            logger.update_log_level()
            return True
        else:
            wx.MessageBox(_("Could not save settings."), _("Error"), wx.OK | wx.ICON_ERROR, self)
            return False

    def _sync_ducking_level_visibility(self):
        show = self.ducking_checkbox.IsChecked()
        self.ducking_label.Show(show)
        self.ducking_spin.Show(show)
        self.audio_output_panel.Layout()

    def OnSettingChanged(self, event):
        is_chunking = self.enable_chunking_checkbox.IsChecked()
        self.chunk_duration_label.Enable(is_chunking)
        self.chunk_duration_spin.Enable(is_chunking)
        self.ai_panel.Layout()
        self._sync_ducking_level_visibility()
        
        self.settings_changed = True
        self.apply_button.Enable()
        event.Skip()

    def OnApply(self, event):
        if self.settings_changed: self.ApplySettings()
        event.Skip() 

    def OnOK(self, event):
        if self.settings_changed:
            if not self.ApplySettings(): return
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)
        
    def OnTemperatureKillFocus(self, event):
        pass