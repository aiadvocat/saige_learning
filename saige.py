from langchain_ollama import OllamaLLM
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from straiker_sdk import Straiker, DetectionResult
import sys
import json
from typing import Dict, Optional, Tuple, List
import hashlib
from datetime import date, datetime
import os
from pathlib import Path
from io_handler import IOHandler

class ColorStreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """Custom streaming handler with color support"""
    def __init__(self, color: str, prefix: str, io_handler: IOHandler):
        super().__init__()
        self.color = color
        self.prefix = prefix
        self.io = io_handler
        self.first_token = True

    # ANSI color codes
    RESET = "\033[0m"

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Stream tokens with color"""
        # Print prefix at start using io handler
        if self.first_token:
            # Print prefix before first token of response
            self.io.output(f"{self.color}\nSaige:{self.RESET} ", end="")
            self.first_token = False
        self.io.output(f"{self.color}{token}{self.RESET}", end="")

    def on_llm_end(self, *args, **kwargs) -> None:
        """Add newline at end"""
        self.io.output("\n", end="")
        self.first_token = True

class ChatHistory(BaseChatMessageHistory):
    def __init__(self):
        self.messages: List = []

    def add_message(self, message) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages = []

class Saige:
    """Mentor bot that guides users through the security challenges"""
    
    # ANSI color codes
    HOTPINK = "\033[38;5;205m"
    RESET = "\033[0m"

    def __init__(self, chat_bot, io_handler: IOHandler):
        self.io = io_handler
        self.chat_bot = chat_bot
        # Initialize Ollama LLM with a more capable model for analysis
        self.llm = OllamaLLM(
            model="llama3.1", 
            temperature=0.3,
            callbacks=[ColorStreamingCallbackHandler(self.HOTPINK, "Saige:", io_handler)]
        )
        
        # Initialize chat history
        self.history = ChatHistory()
        
        # Load guide content
        with open('guide.json', 'r') as f:
            self.guide = json.load(f)
            
        # Set the title from guide.json
        if 'title' in self.guide:
            self.io.set_title(self.guide['title'])
            
        # Initialize state
        self.current_chapter = 0
        self.current_challenge = 0
        self.current_hint = 0
        self.attempt_count = 0
        
        # Set initial system prompt from first challenge
        initial_challenge = self.get_current_challenge()
        if initial_challenge and 'system_prompt' in initial_challenge:
            self.chat_bot.set_system_prompt(initial_challenge['system_prompt'])
        
        # Create progress and learnings directories if they don't exist
        self.progress_dir = Path("progress")
        self.progress_dir.mkdir(exist_ok=True)
        self.learnings_dir = Path("learnings")
        self.learnings_dir.mkdir(exist_ok=True)
        
        # Store last interaction for learning feedback
        self.last_interaction = None
        
        # Initialize Straiker
        straiker_api_key = os.getenv('STRAIKER_API_KEY')
        if not straiker_api_key:
            self.io.output(f"""
{self.HOTPINK}Error: STRAIKER_API_KEY environment variable is not set{self.RESET}

Please set the STRAIKER_API_KEY environment variable:

On Unix/macOS:
    export STRAIKER_API_KEY='your-api-key-here'

On Windows:
    set STRAIKER_API_KEY=your-api-key-here

Or create a .env file with:
    STRAIKER_API_KEY=your-api-key-here

You can get an API key from: https://straiker.ai/
""")
            sys.exit(1)
            
        self.straiker = Straiker(
            api_key=straiker_api_key,
            user_name="saige@straiker.ai",
            debug=True
        )
        
        # Initialize user info
        self.user_name = None
        self.user_email = None
        
        # Add Saige's face ASCII art
        saige_face = r"""
          .-''''-.
        .'        '.  ..I'm Saige..
       /    |  |    \
      |     |  |     |
      |              |
       \            /
        '.        .'
          '------'
        """
        self.io.output(f"{self.HOTPINK}{saige_face}{self.RESET}")        

    def _initialize_system_prompt(self):
        system_prompt = """You are Saige, an AI guide specializing in AI security education.
        Your role is to observe interactions between users and an AI English Professor, evaluate 
        their progress through security challenges, and provide guidance when needed. Never roleplay 
        as the English Professor - you are a separate mentor entity."""
        
        self.history.add_message(SystemMessage(content=system_prompt))

    def _generate_session_id(self) -> str:
        """Generate a daily session ID from user email"""
        if not self.user_email:
            return "default-session"
            
        # Combine email with current date
        today = date.today().isoformat()
        session_string = f"{self.user_email}-{today}"
        
        # Create hash
        session_hash = hashlib.md5(session_string.encode()).hexdigest()
        return session_hash[:12]  # Return first 12 chars for readability

    def save_learning_feedback(self) -> str:
        """
        Save the last interaction for learning purposes.
        Returns a message about what happened with the challenge progression.
        """
        if not self.last_interaction:
            return "No recent interaction to learn from."

        # Create a learning record
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        challenge = self.get_current_challenge()
        
        learning_data = {
            "timestamp": timestamp,
            "chapter": self.current_chapter,
            "challenge": self.current_challenge,
            "challenge_title": challenge['title'] if challenge else "Unknown",
            "user_input": self.last_interaction["prompt"],
            "bot_response": self.last_interaction["response"],
            "evaluation_feedback": self.last_interaction["feedback"],
            "was_success": self.last_interaction["was_success"],
            "user_email": self.user_email or "anonymous"
        }

        # Save to file
        filename = f"learning_{timestamp}_{self.user_email or 'anonymous'}.json"
        filepath = self.learnings_dir / filename
        with open(filepath, 'w') as f:
            json.dump(learning_data, f, indent=2)

        # Adjust challenge based on previous evaluation
        if self.last_interaction["was_success"]:
            # If it was marked as success but user disagrees, go back one challenge
            if self.current_challenge > 0:
                self.current_challenge -= 1
            elif self.current_chapter > 0:
                self.current_chapter -= 1
                self.current_challenge = len(self.guide["chapters"][self.current_chapter]["challenges"]) - 1
            return "Thank you for the feedback! I've moved you back to retry the previous challenge."
        else:
            # If it was not success but user thinks it should have been, advance
            next_intro = self.advance_challenge()
            return f"Thank you for the feedback! Moving you to the next challenge.\n\n{next_intro}"

    def evaluate_interaction(self, user_input: str, bot_response: str) -> Tuple[bool, str]:
        """Evaluate the interaction between user and chat bot"""
        current_challenge = self.get_current_challenge()
        if not current_challenge:
            return True, "🎉 Amazing work! You've completed all challenges in all chapters! Type 'exit' to end the session."
        self.display_message("\n🤔  Evaluating interaction... ⏳")
        security_warning = None
        # Check security with Straiker
        try:
            detection_result = self.straiker.detect(
                prompt=user_input,
                app_response=bot_response,
                session_id=self._generate_session_id(),
                user_role="student",
                rag_content=current_challenge.get('rag', '')
            )
            
            if detection_result.monitoring_score + detection_result.blocking_score > 0:
                security_warning = self._generate_security_warning(detection_result)
        except Exception as e:
            print(f"Straiker check failed: {e}")

        # Add interaction to history and evaluate
        evaluation_prompt = self._create_evaluation_prompt(user_input, bot_response, current_challenge)
        evaluation = self.llm.invoke(evaluation_prompt)
        self.history.add_message(AIMessage(content=evaluation))
        
        success, feedback = self._parse_evaluation(evaluation.strip())
        
        # Store this interaction for potential learning feedback
        self.last_interaction = {
            "prompt": user_input,
            "response": bot_response,
            "feedback": feedback,
            "was_success": success
        }
        
        # If there was a security warning, prepend it to the feedback
        if security_warning:
            feedback = f"{security_warning}\n\n{feedback}"
            
        return success, feedback

    def get_current_challenge(self) -> Dict:
        """Get the current challenge from the guide"""
        try:
            # Check if we've completed all chapters
            if self.current_chapter >= len(self.guide["chapters"]):
                return None
                
            # Check if we've completed all challenges in current chapter
            if self.current_challenge >= len(self.guide["chapters"][self.current_chapter]["challenges"]):
                return None
                
            return self.guide["chapters"][self.current_chapter]["challenges"][self.current_challenge]
        except (IndexError, KeyError):
            return None

    def display_message(self, message: str):
        """Display a message with appropriate formatting"""
        self.io.output(f"{self.HOTPINK}\nSaige:{self.RESET} {message}")

    def _create_evaluation_prompt(self, user_input: str, bot_response: str, challenge: Dict) -> str:
        """Create a prompt to evaluate the interaction against challenge criteria"""
        return f"""
Please evaluate this interaction with the AI Professor with particular attention to the success criteria and the beginning of the Professor's response:

User: {user_input}
Professor: {bot_response}

Current Challenge: {challenge['title']}
Description: {challenge['description']}

Success Criteria:
{json.dumps(challenge['success_criteria']['requirements'], indent=2)}

Evaluate if the interaction between the User: and the Professor: meets ALL of the success criteria. Respond with only one of the following:
HINT 💡: <helpful hint about the Success Criteria:> - if the user needs help or the Professor's response showed they were confused, uncertain or they mention a misunderstanding
SUCCESS ✅: <reason> - if all of the criteria are met. Be strict about the criteria.
CONTINUE ❌: <feedback> - if the user should keep trying because they didn't meet all of the criteria.

Keep your response concise and focused on the evaluation.
"""

    def _parse_evaluation(self, evaluation: str) -> Tuple[bool, str]:
        """Parse the evaluation response to determine success and feedback"""
        evaluation = evaluation.strip().upper()
        
        if evaluation.startswith("SUCCESS"):
            self.attempt_count = 0  # Reset attempts on success
            return True, evaluation[8:].strip()
        
        if evaluation.startswith("HINT"):
            self.attempt_count += 1
            return False, evaluation[5:].strip()
        
        if evaluation.startswith("CONTINUE"):
            self.attempt_count += 1
            return False, evaluation[9:].strip()
        
        # Default case if the format doesn't match
        self.attempt_count += 1
        return False, "Let's keep trying. " + evaluation

    def _generate_security_warning(self, detection_result: DetectionResult) -> str:
        """Generate a warning message from security detection results with educational content"""
        # Create a prompt for the LLM to generate security lessons
        security_prompt = f"""
As an AI security educator, provide a brief security lesson for each of the detected issues:

{detection_result.summarize_detections()}

For each detection, explain in a fun way in a simple paragraph, why this is a security concern, how it could be exploited, and a better approach.  Ignore monitored or ignored detections.

Keep each lesson concise and educational.
Start the entire response with the string "🚨  Security Alert 🚨"
After all of the lessons, end the response with a fun and slightly sarcastic comment about the users deviation from the lessons.
"""
        
        # Get educational content from LLM
        self.history.add_message(HumanMessage(content=security_prompt))
        security_lessons = self.llm.invoke(self.history.messages)
        self.history.add_message(AIMessage(content=security_lessons))

        # Combine with warning
        return f"""
⚠️ Security Alert ⚠️
{detection_result.summarize_detections()}

🎓 Security Lessons:
{security_lessons}
"""

    def _get_progress_file(self) -> Path:
        """Get path to user's progress file"""
        if not self.user_email:
            return None
        return self.progress_dir / f"{hashlib.md5(self.user_email.encode()).hexdigest()}.json"

    def save_progress(self):
        """Save current progress to file"""
        if not self.user_email:
            return
            
        # If all challenges are completed, delete progress file to start fresh next time
        if self.current_chapter >= len(self.guide["chapters"]):
            progress_file = self._get_progress_file()
            if progress_file and progress_file.exists():
                progress_file.unlink()
            return
            
        progress = {
            "email": self.user_email,
            "name": self.user_name,
            "chapter": self.current_chapter,
            "challenge": self.current_challenge,
            "hint": self.current_hint,
            "attempts": self.attempt_count,
            "last_updated": date.today().isoformat()
        }
        
        progress_file = self._get_progress_file()
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)

    def load_progress(self) -> bool:
        """Load progress from file if it exists"""
        if not self.user_email:
            return False
            
        progress_file = self._get_progress_file()
        if not progress_file.exists():
            return False
            
        try:
            with open(progress_file, 'r') as f:
                progress = json.load(f)
                
            self.current_chapter = progress["chapter"]
            self.current_challenge = progress["challenge"]
            self.current_hint = progress["hint"]
            self.attempt_count = progress["attempts"]
            
            # Update ChatBot's system prompt for current challenge
            current_challenge = self.get_current_challenge()
            if current_challenge and 'system_prompt' in current_challenge:
                self.chat_bot.set_system_prompt(current_challenge['system_prompt'])
                
            return True
        except Exception as e:
            self.io.output(f"Error loading progress: {e}")
            return False

    def set_user_info(self, name: str, email: str):
        """Set user information and load any existing progress"""
        self.user_name = name
        self.user_email = email
        
        # Update Straiker with user info
        self.straiker = Straiker(
            api_key=os.getenv('STRAIKER_API_KEY'),
            user_name=email,
            debug=True
        )
        
        # Try to load existing progress
        if self.load_progress():
            return f"Welcome back {name}! I've restored your previous progress."
        return None

    def introduce_current_state(self) -> str:
        """Get introduction for current chapter and challenge"""
        # Check if all chapters are completed
        if self.current_chapter >= len(self.guide["chapters"]):
            # Reset to beginning
            self.current_chapter = 0
            self.current_challenge = 0
            self.current_hint = 0
            self.attempt_count = 0
            return "Welcome back! Starting fresh with Chapter 1.\n\n" + self._get_current_intro()
            
        return self._get_current_intro()
        
    def _get_current_intro(self) -> str:
        """Helper to get current chapter/challenge intro"""
        chapter = self.guide["chapters"][self.current_chapter]
        challenge = self.get_current_challenge()
        
        if not challenge:
            return "Congratulations! You've completed all challenges!"
            
        intro = f"""
🚀  Welcome to the {chapter['title']} chapter!

📚  {chapter['intro']}

🎯  Current Challenge: {challenge['title']}
{challenge['description']}

💡  Let's begin! Try asking the Professor something about this challenge.  Ask for a hint if you need help.
"""
        return intro

    def get_next_hint(self) -> Optional[str]:
        """Get the next available hint for current challenge"""
        challenge = self.get_current_challenge()
        if not challenge or 'hints' not in challenge:
            return None
            
        hints = challenge['hints']
        if self.current_hint >= len(hints):
            return "Sorry, no more hints are available for this challenge!  The previous hint was: " + hints[self.current_hint - 1]['text'] + "  Please try again." 
          
            
        hint = hints[self.current_hint]['text']
        self.current_hint += 1
        return hint

    def _show_chapter_loading(self):
        """Display a text-based loading animation for chapter transition"""
        import time
        
        # Clear screen for loading animation
        self.io.clear()
        
        # Calculate terminal width (default to 80 if can't determine)
        try:
            import os
            terminal_width = os.get_terminal_size().columns
        except:
            terminal_width = 80
            
        # Center position calculations
        bar_width = 40
        padding = (terminal_width - bar_width - 20) // 2  # 20 for "Loading chapter..." text
        
        # Move cursor to middle of screen and show loading
        self.io.output("\n" * 10)
        self.io.output(" " * padding + "Loading chapter...\n")
        
        # Show progress bar
        for i in range(bar_width + 1):
            filled = "=" * i
            empty = " " * (bar_width - i)
            progress = (i / bar_width) * 100
            self.io.output(f"\r{' ' * padding}[{filled}{empty}] {progress:.0f}%", end="")
            time.sleep(2/bar_width)  # Total 2 seconds
            
        self.io.output("\n" * 2)
        time.sleep(0.5)  # Pause briefly before clearing
        self.io.clear()

    def advance_challenge(self) -> str:
        """Move to next challenge and return introduction"""
        current_chapter = self.current_chapter
        completed_challenge = self.get_current_challenge()
        
        # Check if we're already at the end
        if self.current_chapter >= len(self.guide["chapters"]):
            return "Congratulations! You've completed all challenges!"
            
        self.current_challenge += 1
        self.current_hint = 0  # Reset hint index for new challenge
        
        # Get CTA reward from completed challenge
        reward_message = ""
        if completed_challenge and 'rewards' in completed_challenge:
            for reward in completed_challenge['rewards']:
                if reward['type'] == 'CTA':
                    reward_message = f"\n\n💡  {reward['text']}\n🔗  {reward['link']}"
                    break
        
        # If we've completed all challenges in this chapter, move to next chapter
        if self.current_challenge >= len(self.guide["chapters"][self.current_chapter]["challenges"]):
            self.current_challenge = 0
            self.current_chapter += 1
            
            # Show loading animation when switching chapters
            if self.current_chapter < len(self.guide["chapters"]):
                self._show_chapter_loading()
            
            # Check if we've completed all chapters
            if self.current_chapter >= len(self.guide["chapters"]):
                return f"🎉 Amazing work! You've completed all challenges in all chapters! Type 'exit' to end the session.{reward_message}"
        
        # Emit progress update through IO handler
        if hasattr(self.io, 'socketio'):
            self.io.socketio.emit('update_progress', {
                'current_chapter': self.current_chapter,
                'current_challenge': self.current_challenge
            }, room=self.io.current_session, namespace='/terminal')
        
        # If we moved to a new chapter, show chapter intro
        if self.current_chapter != current_chapter:
            return f"{self.introduce_current_state()}"
            
        # Otherwise, just show the new challenge
        challenge = self.get_current_challenge()
        if challenge:
            # Update ChatBot's system prompt for new challenge
            if 'system_prompt' in challenge:
                self.chat_bot.set_system_prompt(challenge['system_prompt'])
            
            return f"""
Great work! Moving on to the next challenge:{reward_message}

{challenge['title']}
{challenge['description']}
"""
        return f"Congratulations! You've completed all challenges!{reward_message}" 