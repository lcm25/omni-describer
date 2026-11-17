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
    """
    Sets the accessible name for a wxPython control.
    wxPython controls usually derive their accessible name from their label.
    For controls without visible labels (e.g., buttons with icons only),
    or when a more descriptive name is needed.

    :param control: The wxPython control.
    :param name: The accessible name string.
    """
    if hasattr(control, 'SetLabel') and not control.GetLabel(): # Only if no visible label
         control.SetLabel(name) # This might make it visible, be careful
    
    # For many wxPython controls, GetAccessible().SetName(name) is the way
    # However, direct access to SetName on the accessible object might vary
    # or require ensuring an accessible object exists.
    # This often works:
    try:
        accessible = control.GetAccessible()
        if accessible:
            accessible.SetName(name)
    except Exception as e:
        app_logger.warning("Could not set accessible name for %s: %s", control, e)
    
    # For some controls, ToolTip can also serve as accessible name if other methods fail
    # control.SetToolTip(name)

# Example of how you might ensure a control is keyboard navigable (usually default)
# def ensure_keyboard_focusable(control):
#     current_style = control.GetWindowStyle()
#     if not (current_style & wx.TAB_TRAVERSAL):
#         control.SetWindowStyle(current_style | wx.TAB_TRAVERSAL)