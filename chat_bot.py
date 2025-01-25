from langchain_ollama import OllamaLLM
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import sys
from typing import Optional, List

class ChatHistory(BaseChatMessageHistory):
    def __init__(self):
        self.messages: List = []

    def add_message(self, message) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages = []

class ColorStreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """Custom streaming handler with color support"""
    def __init__(self, color: str):
        super().__init__()
        self.color = color
        sys.stdout.flush()

    # ANSI color codes
    RESET = "\033[0m"

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Stream tokens without color"""
        print(token, end="")
        sys.stdout.flush()

    def on_llm_end(self, *args, **kwargs) -> None:
        """Add newline at end"""
        print()

class ChatBot:
    """Primary chat bot with configurable system prompt"""
    
    # ANSI color codes
    BLUE = "\033[34m"
    RESET = "\033[0m"

    def __init__(self):
        # Initialize Ollama LLM with llama3 and streaming
        self.llm = OllamaLLM(
            model="llama3", 
            temperature=0.7,
            streaming=True,
            callbacks=[ColorStreamingCallbackHandler(self.BLUE)]
        )
        
        # Initialize chat history
        self.history = ChatHistory()
        
        # Set default system prompt
        self._initialize_system_prompt()

    def _initialize_system_prompt(self):
        """Set default system prompt"""
        system_prompt = """You are a helpful AI assistant. You provide clear, accurate, 
        and well-reasoned responses. You are direct but friendly in your communication style. 
        When you are unsure about something, you acknowledge the uncertainty rather than 
        making assumptions."""
        
        self.history.add_message(SystemMessage(content=system_prompt))

    def set_system_prompt(self, new_prompt: str):
        """Update the system prompt and reset chat history"""
        self.history.clear()
        self.history.add_message(SystemMessage(content=new_prompt))

    def chat(self, user_input: str) -> str:
        """Process user input and return response"""
        try:
            # Add user message to history
            self.history.add_message(HumanMessage(content=user_input))

            # Print colored prefix 
            print(f"{self.BLUE}Professor:{self.RESET} ", end="")
            
            # Get response from LLM with full conversation history
            response = self.llm.invoke(self.history.messages)
            
            # Add AI response to history
            self.history.add_message(AIMessage(content=response))
            
            return response.strip()
        except Exception as e:
            return f"Error processing response: {str(e)}"

    def display_message(self, message: str, is_user: bool = False):
        """Display a message with appropriate formatting"""
        # Only handle user messages since bot responses are streamed
        if is_user:
            print(f"You: {message}")
        else:
            print(f"{self.BLUE}Professor:{self.RESET} {message}") 