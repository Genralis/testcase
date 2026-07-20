# BMO Quick Start Guide

## First Time Setup

### Option 1: Automatic Setup (Recommended)

**Windows:**
```powershell
.\setup.ps1
```

**Linux/Mac/Raspberry Pi:**
```bash
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

1. **Install Ollama**
   - Windows: Download from [ollama.com](https://ollama.com)
   - Linux/Mac: `curl -fsSL https://ollama.com/install.sh | sh`

2. **Start Ollama**
   ```bash
   ollama serve
   ```

3. **Download AI Model**
   ```bash
   ollama pull llama3.2:3b
   ```

4. **Install Python Packages**
   ```bash
   pip install -r requirements.txt
   ```

## Running BMO

### Start BMO (Voice Mode)
```bash
python bmo_main.py
```

### Start BMO (Text Mode)
```bash
python bmo_main.py --text
```

## Quick Test

1. Start BMO in text mode first to verify everything works:
   ```bash
   python bmo_main.py --text
   ```

2. Try these test conversations:
   - "Hi BMO!"
   - "What's your favorite game?"
   - "Tell me about Finn and Jake"
   - "What do you think about adventures?"

3. Type `exit` to close

## Troubleshooting

### Problem: "Could not connect to Ollama"
**Solution:** 
```bash
# Open a separate terminal and run:
ollama serve
```

### Problem: Microphone not working
**Solution (Windows):**
- Check microphone permissions in Windows Settings
- Ensure microphone is not muted

**Solution (Linux/Raspberry Pi):**
```bash
sudo apt-get install portaudio19-dev
pip install --upgrade pyaudio
```

### Problem: Voice sounds robotic
**Solution:** Edit `config.py` and adjust:
```python
VOICE_RATE = 150  # Try values between 100-200
```

### Problem: Slow responses on Raspberry Pi
**Solution:** Use a smaller model:
```bash
ollama pull llama3.2:1b
```
Then edit `config.py`:
```python
OLLAMA_MODEL = "llama3.2:1b"
```

## Tips for Best Experience

1. **Quiet Environment**: Use in a quiet room for better voice recognition
2. **Clear Speech**: Speak clearly and at normal volume
3. **Wait for Prompt**: Wait for "BMO is listening..." before speaking
4. **Microphone Distance**: Keep microphone 6-12 inches from your mouth
5. **First Run**: First response may be slow while model loads

## Next Steps

- Check out the full README.md for customization options
- Add LED eyes or buttons for more interactivity
- Create a 3D printed case to make BMO physical
- Share your BMO with friends!

---
**Have fun! BMO loves you! 💛🎮**
