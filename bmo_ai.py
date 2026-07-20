"""
BMO AI Agent - Main AI interaction module using Ollama
"""

import requests
import json
from typing import List, Dict
from config import OLLAMA_HOST, OLLAMA_MODEL, BMO_SYSTEM_PROMPT


class BMOAI:
    """BMO's brain - handles conversation using Ollama"""
    
    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.system_prompt = BMO_SYSTEM_PROMPT
        print("🎮 BMO's brain is initializing...")
        self._check_ollama_connection()
    
    def _check_ollama_connection(self):
        """Check if Ollama is running and model is available"""
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/tags")
            if response.status_code == 200:
                print(f"✅ Connected to Ollama at {OLLAMA_HOST}")
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                if OLLAMA_MODEL not in model_names:
                    print(f"⚠️  Model {OLLAMA_MODEL} not found. Available models: {model_names}")
                    print(f"   Run: ollama pull {OLLAMA_MODEL}")
                else:
                    print(f"✅ Model {OLLAMA_MODEL} is ready!")
            else:
                print(f"❌ Could not connect to Ollama at {OLLAMA_HOST}")
        except Exception as e:
            print(f"❌ Error connecting to Ollama: {e}")
            print("   Make sure Ollama is running: ollama serve")
    
    def chat(self, user_message: str) -> str:
        """
        Send a message to BMO and get a response
        
        Args:
            user_message: The user's input message
            
        Returns:
            BMO's response
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Prepare the full conversation with system prompt
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history
        
        try:
            # Call Ollama API
            response = requests.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                bmo_response = result['message']['content']
                
                # Add BMO's response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": bmo_response
                })
                
                return bmo_response
            else:
                return "BMO is confused! Something went wrong with the thinking box!"
                
        except Exception as e:
            print(f"❌ Error communicating with Ollama: {e}")
            return "BMO's circuits are all tangled! Try again?"
    
    def reset_conversation(self):
        """Clear the conversation history"""
        self.conversation_history = []
        print("🔄 BMO's memory has been refreshed!")


if __name__ == "__main__":
    # Test the BMO AI
    print("Testing BMO AI...")
    bmo = BMOAI()
    
    test_messages = [
        "Hi BMO! How are you?",
        "What's your favorite game?",
        "Tell me about Finn and Jake"
    ]
    
    for message in test_messages:
        print(f"\n👤 User: {message}")
        response = bmo.chat(message)
        print(f"🎮 BMO: {response}")
