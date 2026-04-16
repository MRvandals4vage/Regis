# voice.py — Voice capture → transcribed text via faster-whisper

import queue
import threading
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_LANGUAGE


class VoiceInput:
    SAMPLE_RATE    = 16000   # Hz — required by Whisper
    CHUNK_DURATION = 5       # seconds per recording chunk
    SILENCE_THRESH = 0.01    # RMS threshold below which audio is considered silence

    def __init__(self):
        print(f"[Voice] Loading Whisper model '{WHISPER_MODEL_SIZE}' on {WHISPER_DEVICE}…")
        self.model  = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE,
                                   compute_type="int8")
        self._queue = queue.Queue()
        
        # Verify microphone availability
        if sd:
            try:
                devices = sd.query_devices()
                default_input = sd.default.device[0]
                if default_input < 0 or not any(d['max_input_channels'] > 0 for d in devices):
                    print("⚠️  [Voice] No input devices found. Voice mode will be disabled.")
                else:
                    print(f"🎙️  [Voice] Found input device: {devices[default_input]['name']}")
            except Exception as e:
                print(f"⚠️  [Voice] Could not query audio devices: {e}")
        else:
            print("⚠️  [Voice] 'sounddevice' not installed. Voice mode disabled.")

    # ── internal ─────────────────────────────────────────────────────────────

    def _record_chunk(self) -> np.ndarray:
        """Block until one CHUNK_DURATION seconds of audio is captured."""
        frames = int(self.SAMPLE_RATE * self.CHUNK_DURATION)
        audio  = sd.rec(frames, samplerate=self.SAMPLE_RATE,
                        channels=1, dtype="float32")
        sd.wait()
        return audio.flatten()

    def _is_silent(self, audio: np.ndarray) -> bool:
        rms = np.sqrt(np.mean(audio ** 2))
        return rms < self.SILENCE_THRESH

    def _transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(audio, language=WHISPER_LANGUAGE,
                                            beam_size=5)
        return " ".join(seg.text.strip() for seg in segments).strip()

    # ── public ────────────────────────────────────────────────────────────────

    def listen_once(self) -> str | None:
        """Record one chunk, return transcription or None if silent."""
        if sd is None:
            raise RuntimeError("sounddevice is not installed. Run: pip install sounddevice")

        print("[Voice] Listening…")
        audio = self._record_chunk()

        if self._is_silent(audio):
            return None

        text = self._transcribe(audio)
        print(f"[Voice] Heard: {text!r}")
        return text or None

    def listen_loop(self, callback):
        """
        Continuously listen and invoke callback(text) for each non-empty
        transcription.  Runs in the calling thread (blocking).
        """
        print("[Voice] Starting continuous listen loop. Press Ctrl+C to stop.")
        while True:
            text = self.listen_once()
            if text:
                callback(text)
