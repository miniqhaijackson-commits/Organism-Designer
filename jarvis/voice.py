"""Offline STT/TTS utilities for J.A.R.V.I.S (prototype).

This module provides:
- `transcribe_wav_bytes(wav_bytes)` — transcribe PCM16 WAV bytes using VOSK (local model required).
- `speak_text_to_file(text, out_path)` — synthesize text to WAV using pyttsx3.

Both functions fail gracefully with clear error messages when dependencies or models are missing.
"""
from pathlib import Path
import wave
import io
import time

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "vosk-model-small"


def _ensure_wav_mono_16k(wav_bytes: bytes) -> bytes:
    # Basic check that bytes look like a WAV file and are PCM16. We accept as-is; more
    # sophisticated conversion can be added later (ffmpeg wrapper).
    try:
        with wave.open(io.BytesIO(wav_bytes), 'rb') as w:
            params = w.getparams()
            # params: (nchannels, sampwidth, framerate, nframes, comptype, compname)
            nch, sampw, fr, _, comptype, _ = params
            if comptype != 'NONE':
                raise ValueError('Compressed WAV not supported; provide PCM WAV')
            if nch != 1 or sampw != 2:
                raise ValueError('WAV must be mono PCM16 (1 channel, 16-bit)')
            # Vosk works better around 16000 or 8000; we accept current framerate but warn
            return wav_bytes
    except wave.Error as e:
        raise ValueError(f'Invalid WAV file: {e}')


def transcribe_wav_bytes(wav_bytes: bytes) -> str:
    """Transcribe WAV bytes using VOSK.

    Requirements: `pip install vosk` and a local model at `models/vosk-model-small`.
    The function will raise RuntimeError with instructions if requirements are missing.
    """
    try:
        from vosk import Model, KaldiRecognizer
    except Exception as e:
        raise RuntimeError("VOSK not installed. Install with `pip install vosk` and add a local model.")

    if not MODEL_DIR.exists():
        raise RuntimeError(f"VOSK model not found at {MODEL_DIR}. Download a small model and place it there.")

    # Validate WAV structure
    wav_bytes = _ensure_wav_mono_16k(wav_bytes)

    model = Model(str(MODEL_DIR))
    rec = KaldiRecognizer(model, 16000)

    # Feed audio in chunks
    with wave.open(io.BytesIO(wav_bytes), 'rb') as w:
        results = []
        while True:
            data = w.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                results.append(rec.Result())
        results.append(rec.FinalResult())

    # Combine simple JSON outputs into text
    import json
    parts = []
    for r in results:
        try:
            j = json.loads(r)
            if 'text' in j and j['text'].strip():
                parts.append(j['text'].strip())
        except Exception:
            continue
    return ' '.join(parts)


def speak_text_to_file(text: str, out_path: str) -> str:
    """Synthesize `text` to a WAV file at `out_path` using pyttsx3.

    Requirements: `pip install pyttsx3`.
    Returns the path to the generated WAV file.
    """
    try:
        import pyttsx3
    except Exception:
        raise RuntimeError("pyttsx3 not installed. Install with `pip install pyttsx3`.")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    engine = pyttsx3.init()
    # Optionally tune voice properties here
    engine.setProperty('rate', 160)
    # Save to file
    engine.save_to_file(text, str(out))
    engine.runAndWait()
    # pyttsx3 may produce different formats depending on platform; ensure WAV extension
    return str(out)


if __name__ == '__main__':
    # quick manual test (requires dependencies and a WAV file)
    import sys
    if len(sys.argv) < 2:
        print('Usage: python -m jarvis.voice <command> [args]')
        print('Commands: transcribe <wavfile>, tts <text> <out.wav>')
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'transcribe' and len(sys.argv) >= 3:
        p = Path(sys.argv[2])
        b = p.read_bytes()
        print(transcribe_wav_bytes(b))
    elif cmd == 'tts' and len(sys.argv) >= 4:
        text = sys.argv[2]
        out = sys.argv[3]
        print(speak_text_to_file(text, out))
    else:
        print('Unknown command')
