#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y \
  python3-venv python3-tk libportaudio2 portaudio19-dev \
  libsndfile1 ffmpeg git cmake build-essential

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -d whisper.cpp ]]; then
  git clone https://github.com/ggml-org/whisper.cpp
fi

cmake -S whisper.cpp -B whisper.cpp/build
cmake --build whisper.cpp/build --config Release -j 4

if [[ ! -f whisper.cpp/models/ggml-base.en.bin ]]; then
  bash whisper.cpp/models/download-ggml-model.sh base.en
fi

mkdir -p piper
python -m piper.download_voices --data-dir piper en_US-lessac-medium

echo
echo "Setup complete."
echo "Put your OpenWakeWord model at wakeword.onnx, then run:"
echo "source .venv/bin/activate"
echo "python bmo_main.py"
