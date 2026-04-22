import os
import json
import queue
import threading
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class HotwordListener:
    """
    A lightweight background listener for a specific wake word using Vosk.
    """
    def __init__(self, hotword="regis", model_path=None):
        self.hotword = hotword.lower()
        self.model_path = model_path
        self._stop_event = threading.Event()
        self._audio_queue = queue.Queue()
        
        # Load Vosk model
        # If model_path is None, Vosk will try to find/download a default small model
        if not model_path:
            # This triggers an automatic download of the small US English model if not present
            print("[Hotword] Initializing Vosk model (may take a moment on first run)...")
            self.model = Model(lang="en-us")
        else:
            self.model = Model(model_path)
            
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(True)

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from separate thread) for each audio block."""
        if status:
            print(f"[Hotword] Audio status: {status}")
        self._audio_queue.put(bytes(indata))

    def listen_continuously(self, on_detected_callback):
        """
        Starts the microphone stream and calls the callback when the hotword is heard.
        """
        print(f"[Hotword] Listening for wake word: '{self.hotword}'...")
        
        try:
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                                   channels=1, callback=self._audio_callback):
                while not self._stop_event.is_set():
                    data = self._audio_queue.get()
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").lower()
                        if self.hotword in text:
                            print(f"[Hotword] ✨ Wake word '{self.hotword}' detected!")
                            on_detected_callback()
                    else:
                        # Partial results can be checked here if needed
                        pass
        except Exception as e:
            print(f"[Hotword] ❌ Listener error: {e}")

    def start(self, on_detected_callback):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self.listen_continuously, 
                                        args=(on_detected_callback,), 
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if hasattr(self, '_thread'):
            self._thread.join(timeout=1)
