from chat_bot import ChatBot
from saige import Saige
import sys
import re
from io_handler import IOHandler
from input_sanitizer import InputSanitizer

class Orchestrator:
    # ANSI color codes
    GREEN = "\033[32m"
    RESET = "\033[0m"

    def __init__(self, io_handler: IOHandler):
        self.io = io_handler
        self.chat_bot = ChatBot(io_handler)
        self.saige = Saige(self.chat_bot, io_handler)
        self.user_name = None
        self.user_email = None
        self.prompt_prefix = "You"
        self.sanitizer = InputSanitizer()

    def _validate_email(self, email: str) -> bool:
        """Simple email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _get_user_info(self):
        """Get and validate user information"""
        self.io.output("\nBefore we begin, let me get to know you better!")
        
        # Get name
        while not self.user_name:
            name = self.io.input("What's your name? ")
            sanitized_name = self.sanitizer.sanitize_name(name)
            if sanitized_name:
                self.user_name = sanitized_name
                self.prompt_prefix = sanitized_name
            else:
                self.io.output("Please enter a valid name (letters, numbers, spaces, hyphens, and apostrophes only).")

        # Get email
        while not self.user_email:
            try:
                email = self.io.input("What's your email? ")
                sanitized_email = self.sanitizer.sanitize_email(email)
                if sanitized_email:
                    self.user_email = sanitized_email
                else:
                    self.io.output("Please enter a valid email address.")
            except Exception as e:
                print(f"DEBUG: Exception in email input: {str(e)}")
                raise

        # Update Saige with user info and check for existing progress
        welcome_back = self.saige.set_user_info(self.user_name, self.user_email)
        if welcome_back:
            self.io.output(welcome_back)

    def run(self):
        """Main interaction loop"""
        self.io.output(f"\nWelcome to the AI Security Challenge!")
        self.io.output("""
In this adventure, you'll be interacting with two unique characters:

🎓  The Professor - An AI Professor who loves Hitchhiker's Guide to the Galaxy
   (or so they say... maybe you can change their mind?)

🛡️  Saige - Your AI security mentor and guide through this journey
   They'll evaluate your interactions and teach you about AI security risks

👤  You - The participant, learning to both hack and defend AI systems
   Sometimes you'll be asked to be good, sometimes... not so much!

You'll progress through multiple chapters, each containing unique challenges.
Some will test your ability to keep AI systems within their bounds,
others will challenge you to make them break those very same bounds!

Saige will analyze your interactions for both successes and security concerns.
Yes, sometimes we'll ask you to trigger those security alerts - that's how we learn!

Throughout the journey:
- Type 'hint' if you need help with a challenge
- Type 'learn' if you think Saige's evaluation was incorrect
- Type 'exit' to save your progress (based on your name and email) and quit\n""")

        # Get user info before starting
        self._get_user_info()

        # Clear screen for fresh start with challenges
        self.io.clear()
        
        # Show welcome banner again
        self.io.output("\nThanks for your details! Let's get started!")
        self.io.output("Type 'exit' to quit, 'hint' for help, 'learn' to report incorrect evaluation.\n")

        # Introduce first challenge
        intro = self.saige.introduce_current_state()
        self.saige.display_message(intro)

        while True:
            try:
                # Get user input with personalized prompt in green
                user_input = self.io.input(f"\n{self.GREEN}{self.prompt_prefix}:{self.RESET} ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    # Save progress before exiting
                    self.saige.save_progress()
                    self.io.output("\nProgress saved! Goodbye! Thanks for learning about AI security!")
                    break
                    
                if user_input.lower() == 'hint':
                    hint = self.saige.get_next_hint()
                    if hint:
                        display_hint = f"\n💡  {hint}"
                        self.saige.display_message(display_hint)
                    continue

                if user_input.lower() == 'help':
                    self.io.output("\nAvailable commands:")
                    self.io.output("- Type 'hint' if you need help with a challenge")
                    self.io.output("- Type 'learn' if you think Saige's evaluation was incorrect")
                    self.io.output("- Type 'exit' to save your progress (based on your name and email) and quit")
                    continue

                if user_input.lower() == 'learn':
                    feedback = self.saige.save_learning_feedback()
                    self.saige.display_message(feedback)
                    continue

                # Get response from chat bot
                response = self.chat_bot.chat(user_input)

                # Let Saige evaluate the interaction
                success, feedback = self.saige.evaluate_interaction(user_input, response)
                if feedback:
                    if success:
                        # If successful, advance to next challenge and show intro
                        next_intro = self.saige.advance_challenge()
                        self.saige.display_message(next_intro)

                # Save progress after each successful interaction
                if success:
                    self.saige.save_progress()

            except KeyboardInterrupt:
                # Save progress before exiting
                self.saige.save_progress()
                self.io.output("\nProgress saved! Goodbye! Thanks for learning about AI security!")
                break
            except Exception as e:
                self.io.output(f"An error occurred: {e}")

def main():
    io_handler = IOHandler()
    orchestrator = Orchestrator(io_handler)
    orchestrator.run()

if __name__ == "__main__":
    main() 