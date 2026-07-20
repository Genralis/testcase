"""Persistent, queued Piper speech synthesis with streaming audio playback."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

import sounddevice as sd


StateCallback = Callable[[], None]


@dataclass
class _SpeechTask:
    text: str
    completed: threading.Event


class PiperTTS:
    """
    Load Piper once and synthesize all speech on one worker thread.

    Keeping one model and one worker avoids the common "first reply speaks,
    later replies are silent" problem caused by repeatedly opening TTS engines.
    """

    def __init__(
        self,
        config: Mapping[str, object],
        *,
        output_device: object = None,
        on_speech_start: StateCallback | None = None,
        on_speech_end: StateCallback | None = None,
    ) -> None:
        try:
            from piper import PiperVoice, SynthesisConfig
        except ImportError as exc:
            raise RuntimeError(
                "Piper is not installed. Run: pip install piper-tts"
            ) from exc

        self._SynthesisConfig = SynthesisConfig
        self.model_path = Path(str(config["model_path"]))
        self.use_cuda = bool(config.get("use_cuda", False))
        self.output_device = output_device
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Piper voice model was not found at '{self.model_path}'. "
                "Download the .onnx voice and matching .onnx.json file."
            )

        self.voice = PiperVoice.load(
            str(self.model_path),
            use_cuda=self.use_cuda,
        )
        self.synthesis_config = self._SynthesisConfig(
            volume=float(config.get("volume", 1.0)),
            length_scale=float(config.get("length_scale", 1.0)),
            noise_scale=float(config.get("noise_scale", 0.667)),
            noise_w_scale=float(config.get("noise_w_scale", 0.8)),
        )

        self._queue: queue.Queue[_SpeechTask | None] = queue.Queue()
        self._closed = threading.Event()
        self._worker = threading.Thread(
            target=self._run,
            name="piper-tts",
            daemon=True,
        )
        self._worker.start()

    def speak(self, text: str, *, wait: bool = False) -> None:
        clean = " ".join(text.strip().split())
        if not clean or self._closed.is_set():
            return

        completed = threading.Event()
        self._queue.put(_SpeechTask(clean, completed))
        if wait:
            completed.wait()

    def wait_until_done(self) -> None:
        self._queue.join()

    def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        self._queue.put(None)
        self._worker.join(timeout=3)

    def _run(self) -> None:
        while True:
            task = self._queue.get()
            try:
                if task is None:
                    return

                if self.on_speech_start is not None:
                    self.on_speech_start()

                self._synthesize_and_play(task.text)
                task.completed.set()
            except Exception as exc:
                if task is not None:
                    task.completed.set()
                print(f"[Piper TTS error] {exc}")
            finally:
                if task is not None and self.on_speech_end is not None:
                    self.on_speech_end()
                self._queue.task_done()

    def _synthesize_and_play(self, text: str) -> None:
        stream: sd.RawOutputStream | None = None

        try:
            for chunk in self.voice.synthesize(
                text,
                syn_config=self.synthesis_config,
            ):
                if stream is None:
                    stream = sd.RawOutputStream(
                        samplerate=chunk.sample_rate,
                        channels=chunk.sample_channels,
                        dtype="int16",
                        device=self.output_device,
                    )
                    stream.start()

                stream.write(chunk.audio_int16_bytes)
        finally:
            if stream is not None:
                stream.stop()
                stream.close()
