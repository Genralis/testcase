"""Microphone recording, resampling, WAV playback, and sound effects."""

from __future__ import annotations

import math
import random
import tempfile
import time
from collections import deque
from pathlib import Path
from typing import Mapping

import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy.signal import resample_poly


class AudioManager:
    def __init__(self, config: Mapping[str, object]) -> None:
        self.target_sample_rate = int(config.get("target_sample_rate", 16000))
        self.channels = int(config.get("channels", 1))
        self.input_device = config.get("input_device")
        self.output_device = config.get("output_device")
        self.block_ms = int(config.get("block_ms", 50))
        self.silence_threshold = float(config.get("silence_threshold", 500))
        self.silence_seconds = float(config.get("silence_seconds", 1.1))
        self.start_timeout_seconds = float(
            config.get("start_timeout_seconds", 6.0)
        )
        self.max_record_seconds = float(config.get("max_record_seconds", 15.0))
        self.pre_roll_seconds = float(config.get("pre_roll_seconds", 0.3))

        self.input_sample_rate = self._choose_input_sample_rate()
        self.block_frames = max(
            1,
            int(self.input_sample_rate * self.block_ms / 1000),
        )

    def _choose_input_sample_rate(self) -> int:
        """Prefer 16 kHz, but fall back to the microphone's native rate."""
        try:
            sd.check_input_settings(
                device=self.input_device,
                channels=self.channels,
                dtype="int16",
                samplerate=self.target_sample_rate,
            )
            return self.target_sample_rate
        except Exception:
            info = sd.query_devices(self.input_device, "input")
            return int(round(float(info["default_samplerate"])))

    def record_until_silence(self, output_path: str | Path | None = None) -> Path | None:
        """
        Record one utterance.

        Recording starts when RMS passes silence_threshold and ends after a
        continuous silent period. A small pre-roll prevents clipped first words.
        """
        pre_roll_blocks = max(
            1,
            int(self.pre_roll_seconds * 1000 / self.block_ms),
        )
        pre_roll: deque[np.ndarray] = deque(maxlen=pre_roll_blocks)
        recorded: list[np.ndarray] = []

        started = False
        start_time = time.monotonic()
        speech_start_time: float | None = None
        last_loud_time: float | None = None

        with sd.InputStream(
            samplerate=self.input_sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=self.block_frames,
            device=self.input_device,
        ) as stream:
            while True:
                block, overflowed = stream.read(self.block_frames)
                if overflowed:
                    # A dropped frame is not fatal for short voice commands.
                    pass

                mono = np.asarray(block[:, 0], dtype=np.int16).copy()
                rms = float(
                    np.sqrt(np.mean(mono.astype(np.float32) ** 2))
                )
                now = time.monotonic()

                if not started:
                    pre_roll.append(mono)

                    if rms >= self.silence_threshold:
                        started = True
                        speech_start_time = now
                        last_loud_time = now
                        recorded.extend(pre_roll)
                        pre_roll.clear()
                    elif now - start_time >= self.start_timeout_seconds:
                        return None
                else:
                    recorded.append(mono)

                    if rms >= self.silence_threshold:
                        last_loud_time = now

                    if (
                        last_loud_time is not None
                        and now - last_loud_time >= self.silence_seconds
                    ):
                        break

                    if (
                        speech_start_time is not None
                        and now - speech_start_time >= self.max_record_seconds
                    ):
                        break

        if not recorded:
            return None

        audio = np.concatenate(recorded)
        audio = self._resample_to_target(audio, self.input_sample_rate)

        if output_path is None:
            handle = tempfile.NamedTemporaryFile(
                prefix="bmo_input_",
                suffix=".wav",
                delete=False,
            )
            handle.close()
            destination = Path(handle.name)
        else:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)

        sf.write(
            destination,
            audio,
            self.target_sample_rate,
            subtype="PCM_16",
        )
        return destination

    def _resample_to_target(
        self,
        audio: np.ndarray,
        source_rate: int,
    ) -> np.ndarray:
        if source_rate == self.target_sample_rate:
            return audio.astype(np.int16, copy=False)

        divisor = math.gcd(source_rate, self.target_sample_rate)
        up = self.target_sample_rate // divisor
        down = source_rate // divisor
        converted = resample_poly(audio.astype(np.float32), up, down)
        converted = np.clip(converted, -32768, 32767)
        return converted.astype(np.int16)

    def resample_for_wakeword(self, audio: np.ndarray) -> np.ndarray:
        """Convert a native-rate microphone frame to 16 kHz int16."""
        return self._resample_to_target(audio, self.input_sample_rate)

    def play_wav(self, path: str | Path, *, wait: bool = True) -> None:
        audio, sample_rate = sf.read(path, dtype="float32")
        sd.play(
            audio,
            int(sample_rate),
            device=self.output_device,
            blocking=wait,
        )

    def play_random_sound(self, folder: str | Path) -> bool:
        candidates = list(Path(folder).glob("*.wav"))
        if not candidates:
            return False
        self.play_wav(random.choice(candidates), wait=True)
        return True

    def describe_devices(self) -> str:
        input_info = sd.query_devices(self.input_device, "input")
        output_info = sd.query_devices(self.output_device, "output")
        return (
            f"Input: {input_info['name']} at {self.input_sample_rate} Hz\n"
            f"Output: {output_info['name']}"
        )
