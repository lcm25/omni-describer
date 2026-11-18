# sapi5_helper_32bit.py
# This script MUST be compiled with a 32-BIT Python interpreter.
# It acts as a bridge for a 64-bit application to access 32-bit SAPI5 voices.
import sys
import json
import traceback
import platform

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

def parse_sapi_language(value):
    """Same rules as audio_describer.core.sapi_voices.parse_sapi_language."""
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    found = []
    for part in text.replace(",", ";").split(";"):
        token = part.strip()
        if not token:
            continue
        if token.lower().startswith("0x"):
            token = token[2:]
        try:
            found.append(int(token, 16))
        except ValueError:
            continue
    return found


def list_voices():
    """32-bit SAPI tokens, including WOW6432Node. One bad Language value is skipped."""
    voice_list = []
    seen = set()
    try:
        import comtypes.client
        sources = []
        voice = comtypes.client.CreateObject("SAPI.SpVoice")
        sources.append(voice.GetVoices())
        try:
            category = comtypes.client.CreateObject("SAPI.SpObjectTokenCategory")
            category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices", False)
            try:
                sources.append(category.EnumerateTokens("", ""))
            except Exception:
                sources.append(category.EnumerateTokens())
        except Exception as exc:
            print(f"Warning: OneCore voices were not listed: {exc}", file=sys.stderr)
        for tokens in sources:
            try:
                count = int(tokens.Count)
            except Exception as exc:
                print(f"Warning: SAPI voice source failed: {exc}", file=sys.stderr)
                continue
            for index in range(count):
                try:
                    token = tokens.Item(index)
                    language = ""
                    try:
                        language = token.GetAttribute("Language")
                    except Exception:
                        language = ""
                    parse_sapi_language(language)
                    name = token.GetDescription() or ""
                    voice_id = token.Id or ""
                    if voice_id and voice_id not in seen:
                        seen.add(voice_id)
                        voice_list.append({"name": name or voice_id, "id": voice_id})
                except Exception as exc:
                    print(f"Warning: Skipping a SAPI5 voice: {exc}", file=sys.stderr)
        return voice_list
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        return {"error": f"Failed to enumerate SAPI voices: {exc}"}

def _assign_onecore_voice(engine, voice_id):
    import comtypes.client
    category = comtypes.client.CreateObject("SAPI.SpObjectTokenCategory")
    category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices", False)
    try:
        tokens = category.EnumerateTokens("", "")
    except Exception:
        tokens = category.EnumerateTokens()
    for index in range(int(tokens.Count)):
        token = tokens.Item(index)
        if getattr(token, "Id", None) == voice_id:
            engine.proxy._driver._tts.Voice = token
            return


def synthesize(data):
    """Synthesizes text to a WAV file based on the provided data."""
    try:
        text = data['text']
        output_path = data['output_path']
        voice_id = data.get('voice_id')
        rate = data.get('rate', 180)

        engine = pyttsx3.init('sapi5')

        if voice_id:
            try:
                engine.setProperty('voice', voice_id)
            except Exception:
                _assign_onecore_voice(engine, voice_id)
        
        engine.setProperty('rate', rate)
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        engine.stop()

    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main entry point for the helper.
    - If run with --list-voices, it outputs JSON.
    - If given data via stdin, it synthesizes speech.
    """
    # 1. Critical dependency check
    if not PYTTSX3_AVAILABLE:
        error_msg = ("FATAL: 'pyttsx3' library not found in this Python environment. "
                     "Please install it in your 32-BIT Python environment using: "
                     "python.exe -m pip install pyttsx3")
        try:
            print(error_msg, file=sys.stderr)
        except Exception:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("SAPI Helper Error", error_msg)
        sys.exit(1)

    # 2. Handle --list-voices command
    if len(sys.argv) > 1 and sys.argv[1] == '--list-voices':
        voices = list_voices()
        print(json.dumps(voices))
        sys.exit(0)
    
    # 3. Handle synthesis command from stdin
    #    If not listing voices, assume we are synthesizing.
    try:
        if sys.stdin is None:
             print("Error: Standard input is not available.", file=sys.stderr)
             sys.exit(1)

        input_line = sys.stdin.readline()
        if not input_line:
            print("Error: No data received from stdin.", file=sys.stderr)
            sys.exit(1)
            
        data = json.loads(input_line)
        synthesize(data)
        sys.exit(0)

    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()