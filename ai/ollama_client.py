"""Small, streaming client for a local Ollama server."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import requests


TokenCallback = Callable[[str], None]
SentenceCallback = Callable[[str], None]


class OllamaError(RuntimeError):
    """Raised when Ollama is unavailable or returns an invalid response."""


class OllamaClient:
    """Talk to Ollama while keeping one HTTP session open."""

    def __init__(self, config: Mapping[str, object]) -> None:
        self.host = str(config.get("host", "http://localhost:11434")).rstrip("/")
        self.text_model = str(config.get("text_model", "gemma3:1b"))
        self.vision_model = str(config.get("vision_model", "moondream"))
        self.keep_alive = str(config.get("keep_alive", "30m"))
        self.options = dict(config.get("options", {}))
        self.connect_timeout = float(config.get("connect_timeout_seconds", 5))
        self.response_timeout = float(config.get("response_timeout_seconds", 120))
        self.session = requests.Session()

    @property
    def timeout(self) -> tuple[float, float]:
        return (self.connect_timeout, self.response_timeout)

    def check_connection(self) -> None:
        """Fail early with a useful message when Ollama is not running."""
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(
                f"Could not connect to Ollama at {self.host}. "
                "Start it with 'ollama serve'."
            ) from exc

    def warm_up(self) -> None:
        """Load the text model before the first real question."""
        payload = {
            "model": self.text_model,
            "messages": [],
            "stream": False,
            "keep_alive": self.keep_alive,
        }
        try:
            response = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(
                f"Could not load Ollama model '{self.text_model}'. "
                f"Run: ollama pull {self.text_model}"
            ) from exc

    def stream_chat(
        self,
        user_message: str,
        *,
        system_prompt: str,
        history: Sequence[Mapping[str, str]] = (),
        on_token: TokenCallback | None = None,
        on_sentence: SentenceCallback | None = None,
    ) -> str:
        """Stream a response and emit complete sentences for low-latency TTS."""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(
            {
                "role": str(item["role"]),
                "content": str(item["content"]),
            }
            for item in history
            if item.get("role") in {"user", "assistant"} and item.get("content")
        )
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.text_model,
            "messages": messages,
            "stream": True,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": self.options,
        }

        try:
            response = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                stream=True,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

        full_text: list[str] = []
        sentence_buffer = ""

        try:
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue

                try:
                    item = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                if item.get("error"):
                    raise OllamaError(str(item["error"]))

                token = str(item.get("message", {}).get("content", ""))
                if token:
                    full_text.append(token)
                    sentence_buffer += token

                    if on_token is not None:
                        on_token(token)

                    complete, sentence_buffer = self._take_complete_sentences(
                        sentence_buffer
                    )
                    if on_sentence is not None:
                        for sentence in complete:
                            on_sentence(sentence)

                if item.get("done"):
                    break
        finally:
            response.close()

        remainder = sentence_buffer.strip()
        if remainder and on_sentence is not None:
            on_sentence(remainder)

        answer = "".join(full_text).strip()
        if not answer:
            raise OllamaError("Ollama returned an empty response.")
        return answer

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str,
        model: str | None = None,
    ) -> str:
        """Return one non-streaming completion."""
        payload = {
            "model": model or self.text_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": self.options,
        }

        try:
            response = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise OllamaError(f"Ollama completion failed: {exc}") from exc

        answer = str(data.get("message", {}).get("content", "")).strip()
        if not answer:
            raise OllamaError("Ollama returned an empty completion.")
        return answer

    def describe_image(self, image_path: str | Path, question: str) -> str:
        """Ask the configured vision model about a local image."""
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(path)

        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": question,
                    "images": [encoded],
                }
            ],
            "stream": False,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0.2,
                "num_predict": 160,
            },
        }

        try:
            response = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise OllamaError(
                f"Vision request failed. Make sure '{self.vision_model}' is installed."
            ) from exc

        answer = str(data.get("message", {}).get("content", "")).strip()
        if not answer:
            raise OllamaError("The vision model returned an empty response.")
        return answer

    @staticmethod
    def _take_complete_sentences(buffer: str) -> tuple[list[str], str]:
        """
        Return sentences ending in punctuation followed by whitespace.

        Waiting for whitespace avoids speaking a sentence too early when a model
        streams punctuation before a closing quote.
        """
        sentences: list[str] = []
        start = 0
        boundary = re.compile(r'[.!?](?:["\')\]]*)\s+|\n+')

        for match in boundary.finditer(buffer):
            end = match.end()
            sentence = buffer[start:end].strip()
            if sentence:
                sentences.append(sentence)
            start = end

        return sentences, buffer[start:]
