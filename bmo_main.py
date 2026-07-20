"""
BMO Main Controller - Brings everything together
"""

import sys
import time
from bmo_ai import BMOAI
from voice_module import BMOVoice


class BMOController:
    """Main controller for BMO AI Agent"""
    
    def __init__(self, use_voice: bool = True):
        """
        Initialize BMO
        
        Args:
            use_voice: Whether to use voice input/output (True) or text-only mode (False)
        """
        print("=" * 50)
        print("🎮 BMO is waking up...")
        print("=" * 50)
        
        # Initialize AI brain
        self.ai = BMOAI()
        
        # Initialize voice (optional)
        self.use_voice = use_voice
        self.voice = None
        if use_voice:
            try:
                self.voice = BMOVoice()
            except Exception as e:
                print(f"⚠️  Voice module failed to initialize: {e}")
                print("   Running in text-only mode")
                self.use_voice = False
        
        self.running = False
    
    def start(self):
        """Start BMO and begin conversation loop"""
        self.running = True
        
        greeting = "Hello! BMO is online and ready to play! What do you want to talk about?"
        
        if self.use_voice and self.voice:
            self.voice.speak(greeting)
        else:
            print(f"🎮 BMO: {greeting}")
        
        print("\n" + "=" * 50)
        print("BMO is ready! Commands:")
        print("  - Say/type 'exit' or 'quit' to shut down BMO")
        print("  - Say/type 'reset' to start a new conversation")
        if self.use_voice:
            print("  - Press Enter to switch to text mode temporarily")
        print("=" * 50 + "\n")
        
        self.conversation_loop()
    
    def conversation_loop(self):
        """Main conversation loop"""
        while self.running:
            try:
                # Get user input
                if self.use_voice and self.voice:
                    user_input = self.voice.listen(timeout=10)
                    
                    # If nothing heard, allow text input
                    if not user_input:
                        print("💬 Type your message (or press Enter to use voice again):")
                        user_input = input("> ").strip()
                else:
                    # Text-only mode
                    print("💬 You:")
                    user_input = input("> ").strip()
                
                # Skip empty input
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['exit', 'quit', 'goodbye', 'bye']:
                    self.shutdown()
                    break
                
                if user_input.lower() == 'reset':
                    self.ai.reset_conversation()
                    response = "Okay! BMO's memory is fresh and clean! Let's start over!"
                    if self.use_voice and self.voice:
                        self.voice.speak(response)
                    else:
                        print(f"🎮 BMO: {response}")
                    continue
                
                # Get response from AI
                response = self.ai.chat(user_input)
                
                # Output response
                if self.use_voice and self.voice:
                    self.voice.speak(response)
                else:
                    print(f"🎮 BMO: {response}")
                
                # Small delay for natural conversation
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n⚠️  Interrupted!")
                self.shutdown()
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
    
    def shutdown(self):
        """Shutdown BMO gracefully"""
        print("\n" + "=" * 50)
        farewell = "Goodbye! BMO will miss you! Come back soon to play!"
        
        if self.use_voice and self.voice:
            self.voice.speak(farewell)
        else:
            print(f"🎮 BMO: {farewell}")
        
        print("=" * 50)
        self.running = False


def main():
    """Entry point for BMO"""
    # Check command line arguments
    use_voice = True
    if len(sys.argv) > 1 and sys.argv[1] == '--text':
        use_voice = False
        print("🔇 Running in text-only mode")
    
    # Create and start BMO
    bmo = BMOController(use_voice=use_voice)
    bmo.start()


if __name__ == "__main__":
    main()
