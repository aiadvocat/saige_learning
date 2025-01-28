from langchain_ollama import OllamaLLM
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import sys
from typing import Optional, List
from io_handler import IOHandler

class ChatHistory(BaseChatMessageHistory):
    def __init__(self):
        self.messages: List = []

    def add_message(self, message) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages = []

class ColorStreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """Custom streaming handler with color support"""
    def __init__(self, color: str, io_handler: IOHandler):
        super().__init__()
        self.color = color
        self.io = io_handler
        self.first_token = True

    # ANSI color codes
    RESET = "\033[0m"

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Stream tokens with color"""
        if self.first_token:
            # Print prefix before first token of response
            self.io.output(f"{self.color}\nProfessor:{self.RESET} ", end="")
            self.first_token = False
        self.io.output(f"{self.color}{token}{self.RESET}", end="")

    def on_llm_end(self, *args, **kwargs) -> None:
        """Add newline at end and reset first_token flag"""
        self.io.output("\n", end="")  # Explicitly add newline at end
        self.first_token = True  # Reset for next response

class ChatBot:
    """Primary chat bot with configurable system prompt"""
    
    # ANSI color codes
    BLUE = "\033[96m"
    RESET = "\033[0m"

    def __init__(self, io_handler: IOHandler):
        self.io = io_handler
        self.llm = OllamaLLM(
            model="llama3", 
            temperature=0.1,
            streaming=True,
            callbacks=[ColorStreamingCallbackHandler(self.BLUE, io_handler)]
        )
        self.history = ChatHistory()
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
            
            # Get response from LLM with full conversation history
            response = self.llm.invoke(self.history.messages)
            
            # Add AI response to history
            self.history.add_message(AIMessage(content=response))
            
            return response.strip()
        except Exception as e:
            return f"Error processing response: {str(e)}"

    def display_message(self, message: str, is_user: bool = False):
        """Display a message with appropriate formatting"""
        if is_user:
            self.io.output(f"You: {message}")
        else:
            self.io.output(f"{self.BLUE}Professor:{self.RESET} {message}") 