"""
BMO System Test Script
Run this to verify all components are working correctly
"""

import sys


def test_python_version():
    """Check Python version"""
    print("\n📋 Testing Python Version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False


def test_imports():
    """Test if all required packages are installed"""
    print("\n📦 Testing Python Packages...")
    packages = {
        'requests': 'requests',
        'speech_recognition': 'SpeechRecognition',
        'pyttsx3': 'pyttsx3',
    }
    
    all_ok = True
    for module_name, package_name in packages.items():
        try:
            __import__(module_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} (not installed)")
            all_ok = False
    
    # Special check for PyAudio (might fail but that's ok for text mode)
    try:
        import pyaudio
        print(f"✅ PyAudio (voice features available)")
    except ImportError:
        print(f"⚠️  PyAudio (not installed - voice features disabled)")
        print(f"   This is OK if you only want text mode")
    
    return all_ok


def test_ollama():
    """Test Ollama connection"""
    print("\n🤖 Testing Ollama Connection...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama is running")
            
            # Check for models
            models = response.json().get('models', [])
            if models:
                print(f"📚 Available models:")
                for model in models:
                    print(f"   - {model['name']}")
                return True
            else:
                print("⚠️  No models installed")
                print("   Run: ollama pull llama3.2:3b")
                return False
        else:
            print("❌ Ollama responded with error")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama")
        print("   Make sure it's running: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_microphone():
    """Test microphone availability"""
    print("\n🎤 Testing Microphone...")
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        print("✅ Microphone detected")
        
        # List available microphones
        mic_list = sr.Microphone.list_microphone_names()
        if mic_list:
            print(f"📻 Available microphones:")
            for i, name in enumerate(mic_list[:5]):  # Show first 5
                print(f"   {i}: {name}")
            if len(mic_list) > 5:
                print(f"   ... and {len(mic_list) - 5} more")
        return True
    except Exception as e:
        print(f"⚠️  Microphone test failed: {e}")
        print("   Voice features may not work, but text mode will")
        return False


def test_tts():
    """Test text-to-speech"""
    print("\n🔊 Testing Text-to-Speech...")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        print("✅ Text-to-speech engine initialized")
        
        voices = engine.getProperty('voices')
        print(f"🎵 Available voices: {len(voices)}")
        return True
    except Exception as e:
        print(f"⚠️  TTS test failed: {e}")
        return False


def run_full_test():
    """Run all tests"""
    print("=" * 60)
    print("🎮 BMO System Test")
    print("=" * 60)
    
    results = {
        "Python Version": test_python_version(),
        "Python Packages": test_imports(),
        "Ollama": test_ollama(),
        "Microphone": test_microphone(),
        "Text-to-Speech": test_tts()
    }
    
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    print("=" * 60)
    
    # Determine what modes are available
    can_run_text = results["Python Version"] and results["Python Packages"] and results["Ollama"]
    can_run_voice = can_run_text and results["Microphone"] and results["Text-to-Speech"]
    
    print("\n🎯 What You Can Do:")
    if can_run_voice:
        print("✅ Full voice mode: python bmo_main.py")
        print("✅ Text mode: python bmo_main.py --text")
    elif can_run_text:
        print("⚠️  Voice mode: Not available (missing audio components)")
        print("✅ Text mode: python bmo_main.py --text")
    else:
        print("❌ BMO cannot run yet. Fix the issues above first.")
        print("\nQuick fixes:")
        if not results["Python Packages"]:
            print("  - Run: pip install -r requirements.txt")
        if not results["Ollama"]:
            print("  - Start Ollama: ollama serve")
            print("  - Install model: ollama pull llama3.2:3b")
    
    print("\n💛 BMO is ready to help!")
    return all(results.values())


if __name__ == "__main__":
    success = run_full_test()
    sys.exit(0 if success else 1)
