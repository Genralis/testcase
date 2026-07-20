"""Thread-safe Tkinter face animation with an asset-free fallback face."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Mapping

import tkinter as tk
from PIL import Image, ImageTk


class BMOFaceGUI:
    STATES = ("idle", "listening", "thinking", "speaking", "error", "warmup")

    def __init__(self, config: Mapping[str, object], assistant_name: str = "BMO") -> None:
        self.assistant_name = assistant_name
        self.assets_dir = Path(str(config.get("assets_dir", "faces")))
        self.fps = max(1, int(config.get("fps", 8)))
        width = int(config.get("width", 800))
        height = int(config.get("height", 480))

        self.root = tk.Tk()
        self.root.title(f"{assistant_name} Local Agent")
        self.root.geometry(f"{width}x{height}")
        self.root.configure(bg="#55c7b8")
        if bool(config.get("fullscreen", False)):
            self.root.attributes("-fullscreen", True)

        self.closed_event = threading.Event()
        self._events: queue.Queue[tuple[str, tuple[object, ...]]] = queue.Queue()
        self._state = "warmup"
        self._frame_index = 0
        self._frames = self._load_frames()
        self._current_photo: ImageTk.PhotoImage | None = None

        self.face_canvas = tk.Canvas(
            self.root,
            bg="#55c7b8",
            highlightthickness=0,
            height=int(height * 0.68),
        )
        self.face_canvas.pack(fill="both", expand=True)

        lower = tk.Frame(self.root, bg="#174f5b")
        lower.pack(fill="x")

        self.status_var = tk.StringVar(value="Starting...")
        self.status = tk.Label(
            lower,
            textvariable=self.status_var,
            bg="#174f5b",
            fg="white",
            font=("Arial", 14, "bold"),
            anchor="w",
            padx=12,
            pady=5,
        )
        self.status.pack(fill="x")

        self.transcript_var = tk.StringVar(value="")
        self.transcript = tk.Label(
            lower,
            textvariable=self.transcript_var,
            bg="#174f5b",
            fg="#d8ffff",
            font=("Arial", 11),
            anchor="w",
            justify="left",
            wraplength=max(300, width - 24),
            padx=12,
            pady=5,
        )
        self.transcript.pack(fill="x")

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(40, self._drain_events)
        self.root.after(int(1000 / self.fps), self._animate)

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        self.closed_event.set()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def set_state(self, state: str) -> None:
        self._events.put(("state", (state,)))

    def set_status(self, text: str) -> None:
        self._events.put(("status", (text,)))

    def set_transcript(self, text: str) -> None:
        self._events.put(("transcript", (text,)))

    def append_response(self, token: str) -> None:
        self._events.put(("append", (token,)))

    def clear_response(self) -> None:
        self._events.put(("clear", ()))

    def _drain_events(self) -> None:
        try:
            while True:
                action, args = self._events.get_nowait()
                if action == "state":
                    requested = str(args[0])
                    self._state = requested if requested in self.STATES else "idle"
                    self._frame_index = 0
                    self._draw_current()
                elif action == "status":
                    self.status_var.set(str(args[0]))
                elif action == "transcript":
                    self.transcript_var.set(str(args[0]))
                elif action == "append":
                    self.transcript_var.set(self.transcript_var.get() + str(args[0]))
                elif action == "clear":
                    self.transcript_var.set("")
        except queue.Empty:
            pass

        if not self.closed_event.is_set():
            self.root.after(40, self._drain_events)

    def _load_frames(self) -> dict[str, list[Image.Image]]:
        frames: dict[str, list[Image.Image]] = {}
        for state in self.STATES:
            state_dir = self.assets_dir / state
            state_frames: list[Image.Image] = []
            if state_dir.is_dir():
                for path in sorted(state_dir.glob("*.png")):
                    try:
                        state_frames.append(Image.open(path).convert("RGBA"))
                    except OSError:
                        continue
            frames[state] = state_frames
        return frames

    def _animate(self) -> None:
        frames = self._frames.get(self._state, [])
        if frames:
            self._frame_index = (self._frame_index + 1) % len(frames)
        self._draw_current()

        if not self.closed_event.is_set():
            self.root.after(int(1000 / self.fps), self._animate)

    def _draw_current(self) -> None:
        self.face_canvas.delete("all")
        frames = self._frames.get(self._state, [])

        if frames:
            image = frames[self._frame_index % len(frames)]
            canvas_width = max(1, self.face_canvas.winfo_width())
            canvas_height = max(1, self.face_canvas.winfo_height())
            ratio = min(canvas_width / image.width, canvas_height / image.height)
            size = (
                max(1, int(image.width * ratio)),
                max(1, int(image.height * ratio)),
            )
            resized = image.resize(size, Image.Resampling.LANCZOS)
            self._current_photo = ImageTk.PhotoImage(resized)
            self.face_canvas.create_image(
                canvas_width // 2,
                canvas_height // 2,
                image=self._current_photo,
            )
            return

        self._draw_fallback_face()

    def _draw_fallback_face(self) -> None:
        width = max(400, self.face_canvas.winfo_width())
        height = max(250, self.face_canvas.winfo_height())
        center_x = width / 2
        center_y = height / 2

        self.face_canvas.create_rectangle(
            center_x - 230,
            center_y - 125,
            center_x + 230,
            center_y + 125,
            fill="#d7f7e9",
            outline="#174f5b",
            width=8,
        )

        eye_y = center_y - 35
        if self._state == "listening":
            eye_height = 42
        elif self._state == "thinking":
            eye_height = 18
        else:
            eye_height = 32

        for eye_x in (center_x - 85, center_x + 85):
            self.face_canvas.create_oval(
                eye_x - 16,
                eye_y - eye_height / 2,
                eye_x + 16,
                eye_y + eye_height / 2,
                fill="#174f5b",
                outline="",
            )

        mouth_y = center_y + 55
        if self._state == "speaking":
            open_amount = 25 + (self._frame_index % 2) * 18
            self.face_canvas.create_oval(
                center_x - 58,
                mouth_y - open_amount / 2,
                center_x + 58,
                mouth_y + open_amount / 2,
                fill="#174f5b",
                outline="",
            )
        elif self._state == "error":
            self.face_canvas.create_arc(
                center_x - 65,
                mouth_y,
                center_x + 65,
                mouth_y + 65,
                start=20,
                extent=140,
                style="arc",
                width=8,
                outline="#174f5b",
            )
        else:
            self.face_canvas.create_arc(
                center_x - 65,
                mouth_y - 35,
                center_x + 65,
                mouth_y + 35,
                start=200,
                extent=140,
                style="arc",
                width=8,
                outline="#174f5b",
            )

        self.face_canvas.create_text(
            center_x,
            center_y - 150,
            text=f"{self.assistant_name} • {self._state.upper()}",
            fill="#174f5b",
            font=("Arial", 18, "bold"),
        )
