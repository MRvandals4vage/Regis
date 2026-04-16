#!/usr/bin/env python3
# voice.py — Voice capture → accurate transcript via faster-whisper

import sys
import queue
import threading
import numpy as np

try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False
    print("⚠️  [Voice] sounddevice not installed. Run: pip install sounddevice", file=sys.stderr)

try:
    from faster_whisper import WhisperModel
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False
    print("⚠️  [Voice] faster-whisper not installed. Run: pip install faster-whisper", file=sys.stderr)

from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_LANGUAGE


class VoiceInput:
    # Audio configuration
    SAMPLE_RATE     = 16_000   # Hz — Whisper requires 16 kHz
    CHUNK_DURATION  = 6        # seconds to record per listen_once call
    SILENCE_THRESH  = 0.008    # RMS threshold — tune down = more sensitive

    def __init__(self):
        if not _WHISPER_AVAILABLE:
            raise RuntimeError("faster-whisper is not installed.")
        if not _SD_AVAILABLE:
            raise RuntimeError("sounddevice is not installed.")

        print(f"[Voice] Loading Whisper model '{WHISPER_MODEL_SIZE}' on {WHISPER_DEVICE}…")
        self.model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type="int8",
            cpu_threads=4,
            num_workers=1,
        )
        self._lock = threading.Lock()  # Prevent concurrent recordings

        # Verify a microphone exists
        try:
            devices = sd.query_devices()
            default_in = sd.default.device[0]
            if default_in < 0 or not any(d['max_input_channels'] > 0 for d in devices):
                print("⚠️  [Voice] No input device found.")
            else:
                name = devices[default_in]['name'] if isinstance(devices, list) else devices[default_in]['name']
                print(f"🎙️  [Voice] Microphone: {name}")
        except Exception as e:
            print(f"⚠️  [Voice] Could not query audio devices: {e}")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _record(self) -> np.ndarray:
        """Block-record CHUNK_DURATION seconds at 16 kHz, mono float32."""
        frames = int(self.SAMPLE_RATE * self.CHUNK_DURATION)
        audio = sd.rec(
            frames,
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype='float32',
            blocking=True,
        )
        return audio.flatten()

    def _is_silent(self, audio: np.ndarray) -> bool:
        rms = float(np.sqrt(np.mean(audio ** 2)))
        return rms < self.SILENCE_THRESH

    def _transcribe(self, audio: np.ndarray) -> str:
        segments, info = self.model.transcribe(
            audio,
            language=WHISPER_LANGUAGE if WHISPER_LANGUAGE else None,
            beam_size=5,
            best_of=5,
            vad_filter=True,          # Built-in voice-activity detection
            vad_parameters={
                "min_silence_duration_ms": 500,
            },
            condition_on_previous_text=False,
            temperature=0.0,          # Greedy — most accurate for commands
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        lang = info.language if hasattr(info, 'language') else '?'
        print(f"[Voice] Detected language: {lang}, transcript: {text!r}")
        return text

    # ── Public API ────────────────────────────────────────────────────────────

    def listen_once(self) -> str | None:
        """
        Record one chunk, transcribe it and return the text.
        Returns None if nothing was said (silence).
        Thread-safe — concurrent calls are serialised.
        """
        with self._lock:
            print("[Voice] Recording…")
            audio = self._record()

        if self._is_silent(audio):
            print("[Voice] Silence detected, ignoring.")
            return None

        text = self._transcribe(audio)
        return text or None

    def listen_loop(self, callback):
        """
        Continuously listen and call callback(text) for every non-empty result.
        Blocking — runs in the calling thread.
        """
        print("[Voice] Starting continuous listen loop. Ctrl-C to stop.")
        while True:
            try:
                text = self.listen_once()
                if text:
                    callback(text)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[Voice] Error during listen: {e}")
