from chat_bot import ChatBot
from saige import Saige
import sys
import re
from io_handler import IOHandler

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

    def _validate_email(self, email: str) -> bool:
        """Simple email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _get_user_info(self):
        """Get and validate user information"""
        self.io.output("\nBefore we begin, let me get to know you better!")
        
        # Get name
        while not self.user_name:
            name = self.io.input("What's your name? ").strip()
            if name and len(name) >= 2:
                self.user_name = name
                self.prompt_prefix = name
            else:
                self.io.output("Please enter a valid name (at least 2 characters).")

        # Get email
        while not self.user_email:
            try:
                email = self.io.input("What's your email? ").strip()
                if self._validate_email(email):
                    self.user_email = email
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
        self.io.output("\nWelcome to the AI Security Challenge!")
        self.io.output("Chat with the AI Professor while 'Saige' our AI Guardian guides you through security challenges.")
        self.io.output("Type 'exit' to quit, 'hint' for help.\n")

        # Get user info before starting
        self._get_user_info()

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
                        display_hint = f"\n💡 {hint}"
                        self.saige.display_message(display_hint)
                    continue

                # Get response from chat bot
                response = self.chat_bot.chat(user_input)
                #self.chat_bot.display_message(response)

                # Let Saige evaluate the interaction
                success, feedback = self.saige.evaluate_interaction(user_input, response)
                if feedback:
                    #self.saige.display_message(feedback)
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