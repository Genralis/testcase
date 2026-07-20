"""Camera capture and local Ollama vision description."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Mapping

import cv2

from ai.ollama_client import OllamaClient


class CameraTool:
    def __init__(self, config: Mapping[str, object]) -> None:
        self.enabled = bool(config.get("enabled", False))
        self.device_index = int(config.get("device_index", 0))
        self.rotation = int(config.get("rotation", 0))
        self.warmup_frames = int(config.get("warmup_frames", 8))

    def capture(self, output_path: str | Path | None = None) -> Path:
        if not self.enabled:
            raise RuntimeError("Camera support is disabled in config.json.")

        camera = cv2.VideoCapture(self.device_index)
        if not camera.isOpened():
            raise RuntimeError(f"Could not open camera index {self.device_index}.")

        frame = None
        try:
            for _ in range(max(1, self.warmup_frames)):
                ok, candidate = camera.read()
                if ok:
                    frame = candidate
        finally:
            camera.release()

        if frame is None:
            raise RuntimeError("The camera opened but returned no image.")

        frame = self._rotate(frame)

        if output_path is None:
            handle = tempfile.NamedTemporaryFile(
                prefix="bmo_camera_",
                suffix=".jpg",
                delete=False,
            )
            handle.close()
            destination = Path(handle.name)
        else:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)

        if not cv2.imwrite(str(destination), frame):
            raise RuntimeError("OpenCV could not save the captured image.")
        return destination

    def describe(self, question: str, ollama: OllamaClient) -> str:
        image_path = self.capture()
        try:
            return ollama.describe_image(image_path, question)
        finally:
            image_path.unlink(missing_ok=True)

    def _rotate(self, frame):
        if self.rotation == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        if self.rotation == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        if self.rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame
