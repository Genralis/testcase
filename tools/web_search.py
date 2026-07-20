"""Current-information search through the DDGS Python package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearchTool:
    def __init__(self, config: Mapping[str, object]) -> None:
        self.enabled = bool(config.get("enabled", True))
        self.max_results = int(config.get("max_results", 4))
        self.region = str(config.get("region", "ca-en"))
        self.safesearch = str(config.get("safesearch", "moderate"))
        self.timeout_seconds = int(config.get("timeout_seconds", 8))

    def search(self, query: str) -> list[SearchResult]:
        if not self.enabled:
            return []

        try:
            from ddgs import DDGS
        except ImportError as exc:
            raise RuntimeError("Install web search support with: pip install ddgs") from exc

        raw_results = DDGS(timeout=self.timeout_seconds).text(
            query,
            region=self.region,
            safesearch=self.safesearch,
            max_results=self.max_results,
        )

        results: list[SearchResult] = []
        for item in raw_results or []:
            title = str(item.get("title", "")).strip()
            url = str(item.get("href") or item.get("url") or "").strip()
            snippet = str(item.get("body") or item.get("snippet") or "").strip()
            if title or snippet:
                results.append(SearchResult(title, url, snippet))
        return results

    @staticmethod
    def as_context(results: list[SearchResult]) -> str:
        lines: list[str] = []
        for index, item in enumerate(results, start=1):
            lines.append(
                f"[{index}] {item.title}\n"
                f"URL: {item.url}\n"
                f"Snippet: {item.snippet}"
            )
        return "\n\n".join(lines)
