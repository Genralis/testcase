"""Route explicit requests to local tools before asking the general LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from ai.ollama_client import OllamaClient

from .camera import CameraTool
from .clock import ClockTool
from .web_search import SearchResult, WebSearchTool


@dataclass(frozen=True)
class ActionResult:
    response: str
    source: str
    sources: tuple[SearchResult, ...] = ()


class ActionRouter:
    def __init__(
        self,
        *,
        ollama: OllamaClient,
        camera_config: Mapping[str, object],
        web_config: Mapping[str, object],
    ) -> None:
        self.ollama = ollama
        self.clock = ClockTool()
        self.camera = CameraTool(camera_config)
        self.web = WebSearchTool(web_config)

    def maybe_handle(self, user_text: str) -> ActionResult | None:
        normalized = " ".join(user_text.lower().split())

        if re.search(r"\b(what time is it|current time|tell me the time)\b", normalized):
            return ActionResult(self.clock.current_time(), "clock")

        if re.search(r"\b(what(?:'s| is) the date|today(?:'s)? date|what day is it)\b", normalized):
            return ActionResult(self.clock.current_date(), "clock")

        if self._is_vision_request(normalized):
            question = user_text
            answer = self.camera.describe(question, self.ollama)
            return ActionResult(answer, "camera")

        search_query = self._extract_search_query(user_text)
        if search_query is not None:
            results = self.web.search(search_query)
            if not results:
                return ActionResult(
                    "BMO could not find useful search results right now.",
                    "web",
                )

            context = self.web.as_context(results)
            prompt = (
                f"User question: {user_text}\n\n"
                f"Search snippets:\n{context}\n\n"
                "Answer the question using only useful facts from these snippets. "
                "Keep it concise and spoken-language friendly. "
                "Do not invent facts. Say when the snippets are insufficient."
            )
            answer = self.ollama.complete(
                prompt,
                system_prompt=(
                    "You summarize supplied web-search snippets accurately. "
                    "Do not claim you opened pages that are not in the snippets."
                ),
            )
            return ActionResult(answer, "web", tuple(results))

        return None

    def _is_vision_request(self, normalized: str) -> bool:
        if not self.camera.enabled:
            return False
        phrases = (
            "what do you see",
            "look at this",
            "look around",
            "take a picture",
            "use the camera",
            "describe what you see",
        )
        return any(phrase in normalized for phrase in phrases)

    @staticmethod
    def _extract_search_query(user_text: str) -> str | None:
        normalized = " ".join(user_text.lower().split())
        explicit_patterns = (
            r"^(?:please\s+)?search(?: the web)? for\s+(.+)$",
            r"^(?:please\s+)?look up\s+(.+)$",
            r"^(?:please\s+)?find online\s+(.+)$",
        )

        for pattern in explicit_patterns:
            match = re.match(pattern, normalized, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        current_markers = (
            "latest ",
            "today's news",
            "current weather",
            "current price",
            "right now",
        )
        if any(marker in normalized for marker in current_markers):
            return user_text.strip()

        return None
