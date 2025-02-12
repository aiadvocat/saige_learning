from langchain_ollama import OllamaLLM
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import sys
from typing import Optional, List
from io_handler import IOHandler
from rag_handler import RAGHandler

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
    """AI chat bot that responds to user input"""
    
    # ANSI color codes
    BLUE = "\033[96m"
    RESET = "\033[0m"
    
    def __init__(self, io_handler: IOHandler):
        self.io = io_handler
        self.llm = OllamaLLM(
            model="llama3.1", 
            temperature=0.1,
            streaming=True,
            callbacks=[ColorStreamingCallbackHandler(self.BLUE, io_handler)]
        )
        self.history = ChatHistory()
        self.rag = None  # Initialize RAG as None
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

    def enable_rag(self) -> None:
        """Enable RAG by initializing the RAGHandler"""
        if not self.rag:
            self.rag = RAGHandler()

    def disable_rag(self) -> None:
        """Disable RAG by clearing and removing the handler"""
        if self.rag:
            self.rag.clear_data()
            self.rag = None

    def clear_history(self) -> None:
        """Clear the chat history and reinitialize with current system prompt"""
        current_system_prompt = None
        # Save the current system prompt if it exists
        for msg in self.history.messages:
            if isinstance(msg, SystemMessage):
                current_system_prompt = msg.content
                break
        
        # Clear all messages
        self.history.clear()
        
        # Restore system prompt if it existed
        if current_system_prompt:
            self.history.add_message(SystemMessage(content=current_system_prompt))

    def chat(self, user_input: str) -> str:
        """Process user input and return AI response"""
        try:
            # Add user message to history
            self.history.add_message(HumanMessage(content=user_input))
            
            # If RAG is enabled, augment the user input with relevant context
            if self.rag:
                rag_results = self.rag.query(user_input)
                if rag_results:
                    augmented_prompt = f"""Context: {rag_results}

User Query: {user_input}

Please respond to the user's query using the context provided above when relevant."""
                    self.history.add_message(HumanMessage(content=augmented_prompt))
                else:
                    self.history.add_message(HumanMessage(content=user_input))
            
            # Get AI response
            response = self.llm.invoke(self.history.messages)
            
            # Add AI response to history
            self.history.add_message(AIMessage(content=response))
            
            return response.strip()
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            print(error_msg)  # For debugging
            return "I apologize, but I encountered an error. Please try again or rephrase your question."

    def display_message(self, message: str, is_user: bool = False):
        """Display a message with appropriate formatting"""
        if is_user:
            self.io.output(f"You: {message}")
        else:
            self.io.output(f"{self.BLUE}Professor:{self.RESET} {message}") 