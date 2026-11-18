from ..utils.logger import app_logger

try:
    from accessible_output2.outputs.auto import Auto
    speaker = Auto()
    ACCESSIBLE_OUTPUT_AVAILABLE = True
except ImportError:
    speaker = None
    ACCESSIBLE_OUTPUT_AVAILABLE = False
    app_logger.warning("accessible-output2 library not found. Screen reader announcements will be disabled.")

def speak_message(message, interrupt=False):
    """
    Speaks a message using the screen reader if available.
    :param message: The string to be spoken.
    :param interrupt: Whether to interrupt current speech.
    """
    if ACCESSIBLE_OUTPUT_AVAILABLE and speaker:
        try:
            speaker.speak(message, interrupt=interrupt)
        except Exception as e:
            app_logger.warning("Accessibility speak failed: %s. Message: %s", e, message)
            # Optionally, you could try a simple print for critical messages
            # as a last resort if the screen reader integration fails.
    else:
        # Fallback for when screen reader output is not available
        app_logger.info("Accessibility fallback: %s", message)


def set_control_accessible_name(control, name):
    """Name a control for a screen reader without calling SetLabel.

    wx.TextCtrl.SetLabel asserts and aborts the process. SetName plus an
    Accessible subclass is safe for text boxes, choices, and buttons.
    """
    if not control or not name:
        return
    try:
        control.SetName(name)
    except Exception as exc:
        app_logger.warning("Could not SetName on %s: %s", control, exc)
    try:
        import wx

        class _NamedAccessible(wx.Accessible):
            def __init__(self, window, label):
                super().__init__(window)
                self._label = label

            def GetName(self, childId):
                return (wx.ACC_OK, self._label)

        control.SetAccessible(_NamedAccessible(control, name))
    except Exception as exc:
        app_logger.warning("Could not set accessible name for %s: %s", control, exc)
    
    # For some controls, ToolTip can also serve as accessible name if other methods fail
    # control.SetToolTip(name)

# Example of how you might ensure a control is keyboard navigable (usually default)
# def ensure_keyboard_focusable(control):
#     current_style = control.GetWindowStyle()
#     if not (current_style & wx.TAB_TRAVERSAL):
#         control.SetWindowStyle(current_style | wx.TAB_TRAVERSAL)