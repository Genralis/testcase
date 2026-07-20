"""Entry point for the modular local BMO-style AI agent."""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from ai import OllamaClient, OllamaError
from audio import AudioManager, PiperTTS, WakeWordDetector, WhisperSTT
from memory import ConversationMemory
from tools import ActionRouter

if TYPE_CHECKING:
    from ui import BMOFaceGUI


class BMOAgent:
    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        base_dir: Path,
        text_only: bool = False,
        gui_enabled: bool = True,
        wakeword_override: bool | None = None,
    ) -> None:
        self.config = config
        self.base_dir = base_dir
        self.text_only = text_only
        self.stop_event = threading.Event()

        assistant_config = config["assistant"]
        self.name = str(assistant_config.get("name", "BMO"))
        self.system_prompt = str(assistant_config["system_prompt"])

        self.gui: "BMOFaceGUI | None" = None
        if gui_enabled and bool(config["gui"].get("enabled", True)):
            from ui import BMOFaceGUI

            self.gui = BMOFaceGUI(config["gui"], assistant_name=self.name)

        memory_config = dict(config["memory"])
        memory_path = self._path(memory_config["path"])
        self.memory = ConversationMemory(
            memory_path,
            enabled=bool(memory_config.get("enabled", True)),
            max_messages=int(memory_config.get("max_messages", 12)),
        )

        self.ollama = OllamaClient(config["ollama"])
        self.router = ActionRouter(
            ollama=self.ollama,
            camera_config=config["camera"],
            web_config=config["web_search"],
        )

        self.audio: AudioManager | None = None
        self.stt: WhisperSTT | None = None
        self.tts: PiperTTS | None = None
        self.wakeword: WakeWordDetector | None = None
        self.audio_mode = str(config["audio"].get("mode", "push_to_talk"))

        if not self.text_only:
            audio_config = dict(config["audio"])
            self.audio = AudioManager(audio_config)

            whisper_config = self._resolve_paths(dict(config["whisper"]))
            self.stt = WhisperSTT(whisper_config)

            piper_config = self._resolve_paths(dict(config["piper"]))
            self.tts = PiperTTS(
                piper_config,
                output_device=self.audio.output_device,
            )

            wake_config = self._resolve_paths(dict(config["wakeword"]))
            wake_enabled = bool(wake_config.get("enabled", True))
            if wakeword_override is not None:
                wake_enabled = wakeword_override

            if wake_enabled and self.audio_mode == "wakeword":
                try:
                    self.wakeword = WakeWordDetector(wake_config, self.audio)
                except (FileNotFoundError, RuntimeError) as exc:
                    print(f"[Wake word disabled] {exc}")
                    self.audio_mode = "push_to_talk"

    def run(self) -> None:
        self._state("warmup", "Loading the local AI model...")
        self.ollama.check_connection()
        self.ollama.warm_up()

        if self.text_only:
            self._run_text_loop()
        else:
            self._run_voice_loop()

    def _run_text_loop(self) -> None:
        greeting = f"{self.name} is online. Type 'exit' to stop or 'reset' to clear memory."
        print(greeting)

        while not self.stop_event.is_set():
            try:
                user_text = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_text:
                continue
            if self._handle_command(user_text):
                continue

            print(f"{self.name}: ", end="", flush=True)
            answer = self._respond(
                user_text,
                on_token=lambda token: print(token, end="", flush=True),
            )
            print()
            self.memory.add_exchange(user_text, answer)

        self.close()

    def _run_voice_loop(self) -> None:
        assert self.audio is not None
        assert self.stt is not None
        assert self.tts is not None

        greeting = f"Hello! {self.name} is online and ready to play."
        self._speak(greeting, wait=True)

        while not self.stop_event.is_set():
            if self.gui is not None and self.gui.closed_event.is_set():
                break

            if self.audio_mode == "wakeword" and self.wakeword is not None:
                self._state("idle", "Say the wake word")
                detected = self.wakeword.wait(stop_event=self.stop_event)
                if not detected:
                    continue
            elif self.audio_mode == "push_to_talk":
                self._state("idle", "Press Enter, then speak")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    break

            self._state("listening", "Listening...")
            recording = self.audio.record_until_silence()
            if recording is None:
                self._state("idle", "I did not hear speech")
                continue

            try:
                self._state("thinking", "Transcribing locally...")
                user_text = self.stt.transcribe(recording)
            except Exception as exc:
                self._show_error(str(exc))
                continue
            finally:
                recording.unlink(missing_ok=True)

            if not user_text:
                self._state("idle", "I could not understand that")
                continue

            print(f"You: {user_text}")
            if self.gui is not None:
                self.gui.set_transcript(f"You: {user_text}")

            if self._handle_command(user_text):
                continue

            try:
                answer = self._respond(user_text)
                self.memory.add_exchange(user_text, answer)
            except Exception as exc:
                self._show_error(str(exc))
                self._speak("BMO's circuits got tangled. Please try again.", wait=True)

        self.close()

    def _respond(
        self,
        user_text: str,
        *,
        on_token=None,
    ) -> str:
        self._state("thinking", "Thinking...")
        routed = self.router.maybe_handle(user_text)

        if routed is not None:
            if self.gui is not None:
                self.gui.set_transcript(f"{self.name}: {routed.response}")

            if on_token is not None:
                on_token(routed.response)
            else:
                print(f"{self.name}: {routed.response}")

            if self.tts is not None:
                self._speak(routed.response, wait=True)

            self._state("idle", "Ready")
            return routed.response

        if self.gui is not None:
            self.gui.clear_response()

        first_sentence = True

        def token_callback(token: str) -> None:
            if on_token is not None:
                on_token(token)
            if self.gui is not None:
                self.gui.append_response(token)

        def sentence_callback(sentence: str) -> None:
            nonlocal first_sentence
            if self.tts is None:
                return
            if first_sentence:
                self._state("speaking", "Speaking...")
                first_sentence = False
            self.tts.speak(sentence, wait=False)

        answer = self.ollama.stream_chat(
            user_text,
            system_prompt=self.system_prompt,
            history=self.memory.get_messages(),
            on_token=token_callback,
            on_sentence=sentence_callback if self.tts is not None else None,
        )

        if self.tts is not None:
            self.tts.wait_until_done()

        if on_token is None:
            print(f"{self.name}: {answer}")
        self._state("idle", "Ready")
        return answer

    def _handle_command(self, text: str) -> bool:
        command = text.strip().lower()

        if command in {"exit", "quit", "goodbye", "bye"}:
            self.stop_event.set()
            return True

        if command == "reset":
            self.memory.reset()
            response = "BMO's conversation memory is fresh and clean."
            if self.tts is None:
                print(f"{self.name}: {response}")
            else:
                self._speak(response, wait=True)
            return True

        return False

    def _speak(self, text: str, *, wait: bool) -> None:
        if self.tts is None:
            print(f"{self.name}: {text}")
            return
        self._state("speaking", "Speaking...")
        self.tts.speak(text, wait=wait)
        if wait:
            self._state("idle", "Ready")

    def _state(self, state: str, status: str) -> None:
        if self.gui is not None:
            self.gui.set_state(state)
            self.gui.set_status(status)

    def _show_error(self, message: str) -> None:
        print(f"[Error] {message}")
        self._state("error", message)

    def close(self) -> None:
        self.stop_event.set()
        if self.tts is not None:
            self.tts.close()

    def _path(self, value: object) -> Path:
        path = Path(str(value))
        return path if path.is_absolute() else self.base_dir / path

    def _resolve_paths(self, section: dict[str, Any]) -> dict[str, Any]:
        for key in ("binary_path", "model_path", "path", "assets_dir"):
            if key in section and section[key] is not None:
                section[key] = str(self._path(section[key]))
        return section


def load_config(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local BMO agent.")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config.json",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Use keyboard input and disable microphone/TTS.",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run without the Tkinter face window.",
    )
    parser.add_argument(
        "--no-wakeword",
        action="store_true",
        help="Skip wake-word detection and use push-to-talk.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)

    if args.no_wakeword:
        config["audio"]["mode"] = "push_to_talk"

    agent = BMOAgent(
        config,
        base_dir=config_path.parent,
        text_only=args.text,
        gui_enabled=not args.no_gui,
        wakeword_override=False if args.no_wakeword else None,
    )

    if agent.gui is None or args.text:
        try:
            agent.run()
        except (OllamaError, FileNotFoundError, RuntimeError) as exc:
            print(f"[Startup error] {exc}")
            agent.close()
        return

    worker = threading.Thread(
        target=_run_agent_safely,
        args=(agent,),
        name="bmo-agent",
        daemon=True,
    )
    worker.start()

    try:
        agent.gui.run()
    finally:
        agent.close()
        worker.join(timeout=2)


def _run_agent_safely(agent: BMOAgent) -> None:
    try:
        agent.run()
    except Exception as exc:
        agent._show_error(str(exc))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
