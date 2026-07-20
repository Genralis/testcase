"""Local microphone, speech recognition, wake word, and speech synthesis."""

from .audio_manager import AudioManager
from .piper_tts import PiperTTS
from .wakeword import WakeWordDetector
from .whisper_stt import WhisperSTT

__all__ = ["AudioManager", "PiperTTS", "WakeWordDetector", "WhisperSTT"]
