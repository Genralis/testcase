"""Thread-safe, bounded JSON conversation memory."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Mapping


class ConversationMemory:
    def __init__(
        self,
        path: str | Path,
        *,
        enabled: bool = True,
        max_messages: int = 12,
    ) -> None:
        self.path = Path(path)
        self.enabled = enabled
        self.max_messages = max(2, int(max_messages))
        self._lock = threading.RLock()
        self._messages: list[dict[str, str]] = []
        self._load()

    def get_messages(self) -> list[dict[str, str]]:
        with self._lock:
            return [dict(item) for item in self._messages]

    def add(self, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Memory role must be 'user' or 'assistant'.")

        clean = content.strip()
        if not clean:
            return

        with self._lock:
            self._messages.append({"role": role, "content": clean})
            self._messages = self._messages[-self.max_messages :]
            self._save()

    def add_exchange(self, user_message: str, assistant_message: str) -> None:
        with self._lock:
            self._messages.extend(
                [
                    {"role": "user", "content": user_message.strip()},
                    {"role": "assistant", "content": assistant_message.strip()},
                ]
            )
            self._messages = [
                item for item in self._messages if item["content"]
            ][-self.max_messages :]
            self._save()

    def reset(self) -> None:
        with self._lock:
            self._messages.clear()
            self._save()

    def _load(self) -> None:
        if not self.enabled or not self.path.exists():
            return

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(raw, list):
            return

        messages: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            role = str(item.get("role", ""))
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})

        self._messages = messages[-self.max_messages :]

    def _save(self) -> None:
        if not self.enabled:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self._messages, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
