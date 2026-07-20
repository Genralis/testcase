"""
BMO Voice Module - Handles speech recognition and text-to-speech
"""

import speech_recognition as sr
import pyttsx3
from config import VOICE_RATE, VOICE_VOLUME


class BMOVoice:
    """Handles BMO's voice input and output"""
    
    def __init__(self):
        # Initialize text-to-speech engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', VOICE_RATE)
        self.tts_engine.setProperty('volume', VOICE_VOLUME)
        
        # Try to set a higher-pitched voice for BMO
        voices = self.tts_engine.getProperty('voices')
        if len(voices) > 1:
            # Usually index 1 is a female/higher voice
            self.tts_engine.setProperty('voice', voices[1].id)
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        print("🎤 BMO's voice module initialized!")
    
    def speak(self, text: str):
        """
        Make BMO speak the given text
        
        Args:
            text: The text for BMO to speak
        """
        print(f"🎮 BMO: {text}")
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"❌ Voice error: {e}")
    
    def listen(self, timeout: int = 5, phrase_time_limit: int = 10) -> str:
        """
        Listen for user input through the microphone
        
        Args:
            timeout: Maximum time to wait for speech to start
            phrase_time_limit: Maximum time for the phrase
            
        Returns:
            The recognized text, or empty string if nothing recognized
        """
        with self.microphone as source:
            print("🎧 BMO is listening...")
            
            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
                
                print("🔄 Processing what BMO heard...")
                text = self.recognizer.recognize_google(audio)
                print(f"👤 You said: {text}")
                return text
                
            except sr.WaitTimeoutError:
                print("⏰ BMO didn't hear anything...")
                return ""
            except sr.UnknownValueError:
                print("❓ BMO couldn't understand that...")
                return ""
            except sr.RequestError as e:
                print(f"❌ Speech recognition error: {e}")
                return ""
    
    def test_microphone(self):
        """Test if the microphone is working"""
        print("\n🎤 Testing microphone...")
        print("Say something!")
        
        text = self.listen()
        if text:
            self.speak(f"BMO heard: {text}")
            return True
        else:
            self.speak("BMO couldn't hear anything!")
            return False


if __name__ == "__main__":
    # Test the voice module
    print("Testing BMO Voice Module...")
    voice = BMOVoice()
    
    voice.speak("Hello! BMO is online and ready to play!")
    
    print("\nTesting microphone (say something)...")
    voice.test_microphone()
