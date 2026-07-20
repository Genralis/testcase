#!/bin/bash
# BMO Setup Script for Linux/Mac/Raspberry Pi

echo "🎮 Setting up BMO AI Agent..."
echo "================================"

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1)
echo "Found: $python_version"

# Check if Ollama is installed
echo ""
echo "Checking for Ollama..."
if command -v ollama &> /dev/null
then
    echo "✅ Ollama is installed"
    ollama_version=$(ollama --version)
    echo "   Version: $ollama_version"
else
    echo "❌ Ollama not found"
    echo ""
    echo "Would you like to install Ollama? (y/n)"
    read -r install_ollama
    if [ "$install_ollama" = "y" ]; then
        echo "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "Please install Ollama from: https://ollama.com"
        exit 1
    fi
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."

# Check for pip
if ! command -v pip3 &> /dev/null
then
    echo "Installing pip..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi

# Install system audio dependencies (for Raspberry Pi/Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Installing system audio dependencies..."
    sudo apt-get update
    sudo apt-get install -y portaudio19-dev python3-pyaudio espeak
fi

# Install Python packages
echo "Installing Python packages..."
pip3 install -r requirements.txt

# Start Ollama service
echo ""
echo "Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!
sleep 3

# Pull the AI model
echo ""
echo "Downloading AI model (this may take a few minutes)..."
ollama pull llama3.2:3b

echo ""
echo "================================"
echo "✅ BMO setup complete!"
echo ""
echo "To start BMO, run:"
echo "  python3 bmo_main.py"
echo ""
echo "For text-only mode:"
echo "  python3 bmo_main.py --text"
echo ""
echo "🎮 Have fun with BMO! 💛"
