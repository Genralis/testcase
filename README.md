# Modular Local BMO Agent


## Features

- Ollama text model with streamed responses
- Piper neural speech loaded once for reliable repeated audio
- whisper.cpp offline speech recognition
- OpenWakeWord custom wake-word support
- Tkinter reactive face states with optional PNG animation folders
- Local JSON conversation memory
- Optional webcam + Ollama vision
- Optional current-information web search
- Text-only, push-to-talk, continuous, and wake-word modes

## Project layout

```text
bmo_modular_agent/
├── bmo_main.py
├── config.json
├── requirements.txt
├── ai/
│   └── ollama_client.py
├── audio/
│   ├── audio_manager.py
│   ├── whisper_stt.py
│   ├── piper_tts.py
│   └── wakeword.py
├── ui/
│   └── bmo_gui.py
├── tools/
│   ├── action_router.py
│   ├── camera.py
│   ├── web_search.py
│   └── clock.py
├── memory/
│   └── conversation_memory.py
├── faces/
└── sounds/
```

## 1. Python setup

Python 3.10 or newer is recommended.

### Raspberry Pi / Debian

```bash
sudo apt update
sudo apt install -y \
  python3-venv python3-tk libportaudio2 portaudio19-dev \
  libsndfile1 ffmpeg git cmake build-essential

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Windows

Create and activate a virtual environment:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Tkinter normally ships with the standard Windows Python installer.

## 2. Ollama

Install Ollama, start it, and download the configured models:

```bash
ollama pull gemma3:1b
ollama pull moondream
ollama serve
```

The vision model is only required when camera support is enabled.

## 3. whisper.cpp

Clone and build whisper.cpp inside the project directory:

```bash
git clone https://github.com/ggml-org/whisper.cpp
cmake -S whisper.cpp -B whisper.cpp/build
cmake --build whisper.cpp/build --config Release -j 4
```

Download an English model:

```bash
bash whisper.cpp/models/download-ggml-model.sh base.en
```

On Windows, the compiled executable may be under
`whisper.cpp/build/bin/Release/whisper-cli.exe`. Update `binary_path` in
`config.json` accordingly.

## 4. Piper voice

Download a voice into the `piper` directory:

```bash
mkdir -p piper
python -m piper.download_voices --data-dir piper en_US-lessac-medium
```

Piper needs both:

```text
piper/en_US-lessac-medium.onnx
piper/en_US-lessac-medium.onnx.json
```

## 5. Wake word

Place your OpenWakeWord ONNX model at:

```text
wakeword.onnx
```

Until you have one, run without wake-word detection:

```bash
python bmo_main.py --no-wakeword
```

That uses push-to-talk: press Enter, then speak.

## 6. Run

Full voice and GUI mode:

```bash
python bmo_main.py
```

Push-to-talk:

```bash
python bmo_main.py --no-wakeword
```

Text-only test:

```bash
python bmo_main.py --text
```

No GUI:

```bash
python bmo_main.py --no-gui --no-wakeword
```

## Face animations

Add PNG sequences under:

```text
faces/idle/
faces/listening/
faces/thinking/
faces/speaking/
faces/error/
faces/warmup/
```

Files are displayed alphabetically. When no images exist, the program draws a
simple animated fallback face.

## Sound effects

The folders are included for future effects:

```text
sounds/greeting_sounds/
sounds/thinking_sounds/
sounds/ack_sounds/
sounds/error_sounds/
```

The included `AudioManager.play_random_sound()` method can be called before
listening, during thinking, or on errors.

## Useful configuration changes

For Raspberry Pi speed:

- Keep `gemma3:1b`
- Use `ggml-tiny.en.bin` or `ggml-base.en.bin`
- Set Ollama `num_ctx` to 2048
- Keep answers short with `num_predict`
- Use a medium or low Piper voice

For a desktop computer, use a larger Ollama model and a larger Whisper model.

## Troubleshooting

### It speaks only once

This version uses a single Piper model and a dedicated queue worker. Do not
recreate `PiperTTS` for every response.

### It listens to itself

The main loop waits for the Piper queue to finish before reopening the
microphone. Keep the speaker away from the microphone when tuning thresholds.

### It is slow

Check which stage is slow:

1. Transcription: use `tiny.en`.
2. Model generation: use a 1B model and smaller context.
3. Speech generation: use a lower-quality Piper voice.
4. First response only: Ollama warm-up is enabled automatically.

### Wake word triggers constantly

Raise `wakeword.threshold` from `0.5` to `0.6` or `0.7`.

### Speech starts too late or cuts off

Tune:

- `audio.silence_threshold`
- `audio.silence_seconds`
- `audio.pre_roll_seconds`
