"""Offline CPU speech recognition with a Chinese-first SenseVoice backend."""

from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Literal, Protocol

# speech.py 位於 backend 根部，模型快取放在專案根目錄的 .data/models。
MODEL_CACHE = Path(__file__).resolve().parents[1] / ".data" / "models"
SENSEVOICE_MODEL_DIR = (
    MODEL_CACHE / "sensevoice" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
)
MAX_AUDIO_BYTES = 20 * 1024 * 1024
MAX_AUDIO_SECONDS = 180
_lock = Lock()
_transcriber = None
_provider: Literal["sensevoice", "whisper"] = "sensevoice"


class TranscriptionUnavailable(RuntimeError):
    pass


class InvalidAudio(ValueError):
    pass


class Transcriber(Protocol):
    def transcribe(self, audio: bytes) -> str: ...


def decode_audio(audio: bytes):
    """Decode browser audio once and enforce shared duration limits."""
    from faster_whisper.audio import decode_audio as faster_whisper_decode

    try:
        samples = faster_whisper_decode(BytesIO(audio), sampling_rate=16000)
    except Exception as exc:
        raise InvalidAudio("錄音無法讀取，請重新錄音。") from exc
    if len(samples) > MAX_AUDIO_SECONDS * 16000:
        raise InvalidAudio("錄音超過三分鐘，請分段說明。")
    if len(samples) < 1600:
        return samples[:0]
    return samples


class SenseVoiceTranscriber:
    """Fast Chinese-first recognition through sherpa-onnx on CPU."""

    def __init__(self):
        model = SENSEVOICE_MODEL_DIR / "model.int8.onnx"
        tokens = SENSEVOICE_MODEL_DIR / "tokens.txt"
        try:
            import sherpa_onnx
            from opencc import OpenCC

            if not model.is_file() or not tokens.is_file():
                raise FileNotFoundError(model)
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(model),
                tokens=str(tokens),
                num_threads=4,
                language="zh",
                use_itn=True,
                provider="cpu",
            )
            self.converter = OpenCC("s2twp")
        except Exception as exc:
            raise TranscriptionUnavailable(
                "SenseVoice 尚未準備好，請執行 python -m tools.prepare_speech。"
            ) from exc

    def transcribe(self, audio: bytes) -> str:
        samples = decode_audio(audio)
        if not samples.size:
            return ""
        stream = self.recognizer.create_stream()
        stream.accept_waveform(16000, samples)
        self.recognizer.decode_stream(stream)
        return self.converter.convert(stream.result.text.strip())


class WhisperTranscriber:
    def __init__(self):
        try:
            from faster_whisper import WhisperModel
            from opencc import OpenCC

            self.model = WhisperModel(
                "base",
                device="cpu",
                compute_type="int8",
                cpu_threads=4,
                download_root=str(MODEL_CACHE),
                local_files_only=True,
            )
            self.converter = OpenCC("s2twp")
        except Exception as exc:
            raise TranscriptionUnavailable("語音服務尚未準備好，請稍後再試。") from exc

    def transcribe(self, audio: bytes) -> str:
        samples = decode_audio(audio)
        if not samples.size:
            return ""
        segments, _ = self.model.transcribe(
            samples,
            language="zh",
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            beam_size=5,
            condition_on_previous_text=False,
        )
        return self.converter.convert("".join(segment.text for segment in segments).strip())


def configure_speech(provider: Literal["sensevoice", "whisper"]) -> None:
    """Select the backend before the app begins accepting requests."""
    global _provider, _transcriber
    with _lock:
        if provider != _provider:
            _provider = provider
            _transcriber = None


def transcribe_audio(audio: bytes) -> str:
    # Called from a worker thread; serialize model loading and CPU inference.
    global _transcriber
    with _lock:
        if _transcriber is None:
            _transcriber = (
                SenseVoiceTranscriber() if _provider == "sensevoice" else WhisperTranscriber()
            )
        return _transcriber.transcribe(audio)
