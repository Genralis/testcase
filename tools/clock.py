"""Local date and time tool."""

from __future__ import annotations

from datetime import datetime


class ClockTool:
    @staticmethod
    def current_time() -> str:
        return datetime.now().astimezone().strftime(
            "It is %-I:%M %p."
        ) if __import__("os").name != "nt" else datetime.now().astimezone().strftime(
            "It is %#I:%M %p."
        )

    @staticmethod
    def current_date() -> str:
        return datetime.now().astimezone().strftime(
            "Today is %A, %B %d, %Y."
        )
