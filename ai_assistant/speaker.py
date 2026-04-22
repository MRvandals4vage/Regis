import subprocess
import threading

def say(text: str):
    """
    Speak the given text using the macOS 'say' command.
    Runs in a background thread to avoid blocking the main server loop.
    """
    if not text:
        return

    def _run():
        try:
            # -v 'Siri' or other voices can be specified, but default is usually best
            subprocess.run(["say", text], check=True)
        except Exception as e:
            print(f"[Speaker] ❌ Failed to speak: {e}")

    threading.Thread(target=_run, daemon=True).start()
