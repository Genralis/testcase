"""Offline OpenWakeWord microphone listener."""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Callable, Mapping

import numpy as np
import sounddevice as sd

from .audio_manager import AudioManager


ScoreCallback = Callable[[float], None]


class WakeWordDetector:
    def __init__(
        self,
        config: Mapping[str, object],
        audio_manager: AudioManager,
    ) -> None:
        try:
            from openwakeword.model import Model
        except ImportError as exc:
            raise RuntimeError(
                "openWakeWord is not installed. Run: pip install openwakeword"
            ) from exc

        self.audio_manager = audio_manager
        self.model_path = Path(str(config["model_path"]))
        self.threshold = float(config.get("threshold", 0.5))
        self.framework = str(config.get("inference_framework", "onnx"))
        self.frame_ms = int(config.get("frame_ms", 80))

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Wake-word model was not found at '{self.model_path}'. "
                "Put your custom .onnx model there or disable wakeword in config.json."
            )

        self.model = Model(
            wakeword_models=[str(self.model_path)],
            inference_framework=self.framework,
        )

    def wait(
        self,
        *,
        stop_event: threading.Event | None = None,
        on_score: ScoreCallback | None = None,
        timeout_seconds: float | None = None,
    ) -> bool:
        """Block until the wake word crosses the configured score threshold."""
        blocks: queue.Queue[np.ndarray] = queue.Queue(maxsize=20)
        native_rate = self.audio_manager.input_sample_rate
        block_frames = max(1, int(native_rate * self.frame_ms / 1000))
        started = time.monotonic()

        def callback(indata, frames, time_info, status) -> None:
            del frames, time_info
            if status:
                pass
            mono = np.asarray(indata[:, 0], dtype=np.int16).copy()
            try:
                blocks.put_nowait(mono)
            except queue.Full:
                try:
                    blocks.get_nowait()
                except queue.Empty:
                    pass

        try:
            self.model.reset()
        except AttributeError:
            pass

        with sd.InputStream(
            samplerate=native_rate,
            channels=1,
            dtype="int16",
            blocksize=block_frames,
            device=self.audio_manager.input_device,
            callback=callback,
        ):
            while stop_event is None or not stop_event.is_set():
                if timeout_seconds is not None:
                    if time.monotonic() - started >= timeout_seconds:
                        return False

                try:
                    native_audio = blocks.get(timeout=0.25)
                except queue.Empty:
                    continue

                audio_16k = self.audio_manager.resample_for_wakeword(native_audio)
                prediction = self.model.predict(audio_16k)
                if not prediction:
                    continue

                score = max(float(value) for value in prediction.values())
                if on_score is not None:
                    on_score(score)

                if score >= self.threshold:
                    try:
                        self.model.reset()
                    except AttributeError:
                        pass
                    return True

        return False
