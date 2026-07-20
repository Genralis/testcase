"""Offline speech-to-text wrapper around whisper.cpp's whisper-cli."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Mapping


class WhisperSTT:
    def __init__(self, config: Mapping[str, object]) -> None:
        self.binary_path = Path(str(config["binary_path"]))
        self.model_path = Path(str(config["model_path"]))
        self.language = str(config.get("language", "en"))
        self.threads = int(config.get("threads", 4))
        self.timeout_seconds = float(config.get("timeout_seconds", 90))

    def validate(self) -> None:
        if not self.binary_path.is_file():
            raise FileNotFoundError(
                f"whisper-cli was not found at '{self.binary_path}'. "
                "Build whisper.cpp or correct whisper.binary_path in config.json."
            )
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Whisper model was not found at '{self.model_path}'. "
                "Download a ggml model or correct whisper.model_path."
            )

    def transcribe(self, wav_path: str | Path) -> str:
        self.validate()
        source = Path(wav_path)
        if not source.is_file():
            raise FileNotFoundError(source)

        with tempfile.TemporaryDirectory(prefix="bmo_whisper_") as temp_dir:
            output_prefix = Path(temp_dir) / "transcript"
            command = [
                str(self.binary_path),
                "-m",
                str(self.model_path),
                "-f",
                str(source),
                "-l",
                self.language,
                "-t",
                str(self.threads),
                "-otxt",
                "-of",
                str(output_prefix),
                "-np",
                "-nt",
            ]

            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("Whisper transcription timed out.") from exc

            transcript_path = output_prefix.with_suffix(".txt")
            if result.returncode != 0 or not transcript_path.exists():
                details = (result.stderr or result.stdout).strip()
                raise RuntimeError(
                    f"whisper-cli failed with code {result.returncode}: {details}"
                )

            return transcript_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).strip()
