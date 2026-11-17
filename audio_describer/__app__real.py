# audio_describer/__app__real.py
import wx
import sys
import os
import time
# --- Top-level imports should be minimal ---
import audio_describer.i18n_setup 
from audio_describer.utils.logger import app_logger
from audio_describer.utils import sound_player
from audio_describer import app_state

def _quiet_asserts():
    """A frozen Windows build must not abort on a wx C++ assertion."""
    if not getattr(sys, "frozen", False) and "--smoke-test" not in sys.argv:
        return
    try:
        wx.DisableAsserts()
    except Exception:
        pass
    try:
        wx.App.SetAssertMode(wx.APP_ASSERT_LOG)
    except Exception:
        pass


class AudioDescriberApp(wx.App):
    def OnInit(self):
        self.is_updating = False
        self._smoke_ok = False
        _quiet_asserts()
        
        self.lang_code = audio_describer.i18n_setup.initialize_translations()
        
        from audio_describer.utils import logger
        logger.update_log_level()
        
        _ = audio_describer.i18n_setup._

        from audio_describer.models import prompt_model, config_model

        # Ensure settings are loaded safely - never let this crash the app
        try:
            initial_settings = config_model.load_settings()
            if initial_settings:
                config_model.app_settings = initial_settings
            else:
                config_model.app_settings = config_model.DEFAULT_SETTINGS.copy()
                app_logger.warning("Settings loaded as None, using defaults.")
            app_logger.info("Settings loaded successfully.")
        except Exception as e:
            app_logger.error(f"Failed to load settings: {e}. Using defaults.", exc_info=True)
            config_model.app_settings = config_model.DEFAULT_SETTINGS.copy()
        
        prompt_model.load_prompts()
        app_logger.info("Prompt model initialized.")

        from audio_describer.ui.license_dialog import LicenseDialog

        try:
            license_accepted = config_model.get_setting("license_accepted")
        except Exception:
            license_accepted = False
            app_logger.error("Failed to check license acceptance status.")
        
        if "--smoke-test" in sys.argv:
            license_accepted = True
        if not license_accepted:
            license_dlg = LicenseDialog(None)
            result = license_dlg.ShowModal()
            license_dlg.Destroy()

            if result == wx.ID_OK:
                app_logger.info("License accepted by user.")
                config_model.app_settings["license_accepted"] = True
                config_model.save_settings(config_model.app_settings)
            else:
                app_logger.warning("License was not accepted. Exiting application.")
                return False
        
        from audio_describer.ui.main_window import MainWindow 
        import audio_describer.config as app_config
        from audio_describer.ui.accessibility_utils import speak_message, ACCESSIBLE_OUTPUT_AVAILABLE
        from audio_describer.utils import single_instance

        launch_paths = [arg for arg in sys.argv[1:] if not str(arg).startswith("-") and os.path.isfile(arg)]
        if single_instance.forward(launch_paths):
            return False
        self._remote_paths = []

        def _on_remote(paths):
            def deliver():
                frame = getattr(self, "main_frame", None)
                if frame:
                    if paths:
                        frame.open_paths(paths)
                    else:
                        frame.Raise()
                else:
                    self._remote_paths.extend(paths)
            wx.CallAfter(deliver)

        single_instance.listen(_on_remote)
        
        app_logger.info("Core components loaded. Initializing main window.")

        # --- The update checker call is now moved from here ---
        
        full_app_display_name = app_config.APP_NAME

        app_logger.info(_("Starting %(app_name)s v%(app_version)s") % {
            "app_name": full_app_display_name, 
            "app_version": app_config.APP_VERSION
        })
        
        if ACCESSIBLE_OUTPUT_AVAILABLE: app_logger.info("accessible-output2 initialized.")
        else: app_logger.warning("accessible-output2 not available.")
        
        window_title = full_app_display_name + f" - v{app_config.APP_VERSION}" 

        try:
            self.main_frame = MainWindow(None, title=window_title)
            self.SetTopWindow(self.main_frame)
            self.main_frame.Show(True)
        except Exception as exc:
            app_logger.critical("Main window failed to open.", exc_info=True)
            if "--smoke-test" not in sys.argv:
                from audio_describer.utils.logger import get_log_file_path
                wx.MessageBox(
                    _("Descritudo could not open.\n\n%s\n\nThe log is at:\n%s") % (exc, get_log_file_path()),
                    app_config.APP_NAME,
                    wx.OK | wx.ICON_ERROR,
                )
            return False
        queued = list(launch_paths) + list(self._remote_paths)
        if queued and "--smoke-test" not in sys.argv:
            wx.CallAfter(self.main_frame.open_paths, queued)

        # Show settings migration warning if there was an issue
        load_warning = config_model.get_load_warning()
        if load_warning:
            app_logger.warning(f"Settings load warning: {load_warning}")
            wx.MessageBox(
                load_warning,
                _("Settings Notice"),
                wx.OK | wx.ICON_WARNING,
                self.main_frame
            )

        # The web platform stays in the File menu. No modal before the first action.

        # MODIFICATION: Start the update check in the background AFTER the UI is shown.
        if "--smoke-test" in sys.argv:
            wx.CallAfter(self._finish_smoke)
        else:
            self.StartBackgroundUpdateCheck()

        sound_player.play("start.mp3")

        speak_message(_("%(app_name)s started.") % {
            "app_name": full_app_display_name
        }, interrupt=True)

        return True

    def _show_webapp_banner_if_needed(self, config_model):
        """Shows a one-time banner informing users about the web platform."""
        import audio_describer.config as app_config
        _ = audio_describer.i18n_setup._

        try:
            already_shown = config_model.get_setting("webapp_banner_shown")
        except Exception:
            already_shown = False

        if already_shown:
            return

        message = _(
            "Omni Describer is now available as a web platform!\n\n"
            "The desktop app will continue to work, but new features and improvements "
            "are now focused on the web version at:\n\n"
            "%(webapp_url)s\n\n"
            "The web platform requires no installation, no API keys, and works on "
            "all devices including Mac and mobile.\n\n"
            "Would you like to open the web platform now?\n\n"
            "(This message will only be shown once.)"
        ) % {"webapp_url": app_config.WEBAPP_URL}

        result = wx.MessageBox(
            message,
            _("Omni Describer Web Platform"),
            wx.YES_NO | wx.ICON_INFORMATION,
            self.main_frame
        )

        if result == wx.YES:
            import webbrowser
            webbrowser.open(app_config.WEBAPP_URL)

        # Mark as shown regardless of choice
        config_model.app_settings["webapp_banner_shown"] = True
        config_model.save_settings(config_model.app_settings)

    # NEW METHOD: To handle the background thread for the update check.
    def StartBackgroundUpdateCheck(self):
        """
        Launches the update check in a separate thread to avoid blocking the UI.
        """
        from audio_describer.utils import update_checker
        _ = audio_describer.i18n_setup._
        update_checker.start_check(self.main_frame, self.lang_code, _)

    def _finish_smoke(self):
        app_logger.info("main window shown")
        marker = os.environ.get("OMNI_SMOKE_FILE")
        if marker:
            try:
                with open(marker, "w", encoding="utf-8") as handle:
                    handle.write("main window shown\n")
            except OSError as exc:
                app_logger.error("Could not write smoke marker: %s", exc)
                self._smoke_ok = False
                self.ExitMainLoop()
                return
        self._smoke_ok = True
        self.ExitMainLoop()

    def OnExit(self):
        if "--smoke-test" in sys.argv:
            app_state.shutdown_event.set()
            return super().OnExit()
        if getattr(self, 'is_updating', False):
            app_logger.info("Performing fast exit for update process. No sounds or delays.")
            app_state.shutdown_event.set()
            return super().OnExit()

        app_logger.info("Shutdown initiated. Setting global shutdown event.")
        app_state.shutdown_event.set()
        
        _ = audio_describer.i18n_setup._
        import audio_describer.config as app_config
        
        full_app_display_name = app_config.APP_NAME

        app_logger.info(_("%s is shutting down.") % full_app_display_name)
        
        from audio_describer.ui.accessibility_utils import speak_message
        speak_message(_("%(app_name)s closed.") % {
            "app_name": full_app_display_name
        })
        
        sound_player.play("shutdown.mp3")
        time.sleep(0.75) 
        
        return super().OnExit()

def main():
    _quiet_asserts()
    app = AudioDescriberApp(redirect=False)
    app.MainLoop()
    if "--smoke-test" in sys.argv and not getattr(app, "_smoke_ok", False):
        sys.exit(1)

if __name__ == '__main__':
    main()