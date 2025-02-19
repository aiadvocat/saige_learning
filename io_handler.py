from abc import ABC, abstractmethod
from queue import Queue, Empty

class IOHandler(ABC):
    @abstractmethod
    def output(self, text: str, style: str = None, end: str = "\n"):
        """Handle output with optional styling and end character"""
        pass
    
    @abstractmethod
    def input(self, prompt: str = "", is_init: bool = False) -> str:
        """Get input with optional prompt"""
        pass
    
    @abstractmethod
    def clear(self, panel: str = "main"):
        """Clear the display for the specified panel"""
        pass

    @abstractmethod
    def set_title(self, title: str):
        """Set the display title"""
        pass

class TerminalIO(IOHandler):
    def output(self, text: str, style: str = None, end: str = "\n"):
        if style:
            # Use existing ANSI colors
            print(f"{style}{text}\033[0m", end=end)
        else:
            print(text, end=end)
    
    def input(self, prompt: str = "", is_init: bool = False) -> str:
        return input(prompt)
    
    def clear(self, panel: str = "main"):
        # Terminal only has one panel, so ignore panel parameter
        print("\033[2J\033[H")

    def set_title(self, title: str):
        # For terminal, we can use ANSI escape sequence to set terminal title
        print(f"\033]0;{title}\007", end="")

class WebIO(IOHandler):
    # ANSI color mapping to CSS classes
    COLOR_MAP = {
        "\033[34m": "color-cyan",      # Blue
        "\033[32m": "color-green",     # Green
        "\033[38;5;205m": "color-pink", # Hot Pink
        "\033[0m": ""                  # Reset
    }
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.current_session = None
        self.input_queue = Queue()  # Single queue per WebIO instance
        
    def set_socketio(self, socketio):
        self.socketio = socketio
        
    def _convert_ansi_to_css(self, text: str) -> tuple[str, str]:
        """Convert ANSI color codes to CSS classes"""
        style = None
        # Find the first color code
        for ansi, css in self.COLOR_MAP.items():
            if ansi in text:
                style = css
                # Remove all ANSI codes
                for code in self.COLOR_MAP.keys():
                    text = text.replace(code, '')
                break
        return text, style
        
    def output(self, text: str, style: str = None, end: str = "\n", panel: str = "main"):
        """Output text to specified panel (main or security)"""
        if self.socketio:
            try:
                event_name = 'security_output' if panel == 'security' else 'output'
                
                # Send text with ANSI codes intact
                if style:
                    # For prompts (end=""), ensure we don't add extra newlines
                    if end == "":
                        self.socketio.emit(event_name, {
                            'text': f"{style}{text}\033[0m",
                            'end': '',
                            'is_prompt': True,
                            'is_streaming': True,
                            'session': self.current_session
                        }, namespace='/terminal')
                    else:
                        self.socketio.emit(event_name, {
                            'text': f"{style}{text}\033[0m",
                            'end': end,
                            'is_streaming': False,
                            'session': self.current_session
                        }, namespace='/terminal')
                else:
                    # Same handling for non-styled text
                    if end == "":
                        self.socketio.emit(event_name, {
                            'text': text,
                            'end': '',
                            'is_prompt': False,
                            'is_streaming': True,
                            'session': self.current_session
                        }, namespace='/terminal')
                    else:
                        self.socketio.emit(event_name, {
                            'text': text,
                            'end': end,
                            'is_streaming': False,
                            'session': self.current_session
                        }, namespace='/terminal')
            except Exception as e:
                print(f"DEBUG Socket emit: Error sending output: {e}")
                raise
    
    def input(self, prompt: str = "", is_init: bool = False) -> str:
        """Get input for current session"""
        session_id = self.current_session
        if not session_id:
            raise RuntimeError("No active session")
            
        # Send prompt to client
        self.output(prompt, end="")
        
        try:
            # Wait up to 500 seconds for input
            result = self.input_queue.get(timeout=500)  # Use input_queue directly
            return result
        except Empty:
            if is_init:
                # During initialization, we should close the session gracefully
                self.socketio.emit('game_ended', room=session_id, namespace='/terminal')
                raise RuntimeError("Session timed out during initialization. Please refresh to start a new session.")
            else:
                # During normal gameplay, suggest hints/help
                raise RuntimeError("Everything ok? Try asking for a 'hint' or 'help'.")

    def set_session(self, session_id):
        """Set current session ID"""
        self.current_session = session_id

    def clear(self, panel: str = "main"):
        """Clear the specified panel"""
        if self.socketio:
            self.socketio.emit('clear', {
                'panel': panel,
                'session': self.current_session
            }, room=self.current_session, namespace='/terminal')

    def set_title(self, title: str):
        """Update the title in the web interface"""
        if self.socketio and self.current_session:
            self.socketio.emit('update_title', 
                             {'title': title}, 
                             room=self.current_session, 
                             namespace='/terminal') 