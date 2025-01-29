import re
import html
from typing import Optional

class InputSanitizer:
    """Input sanitization utility class to prevent injection attacks and ensure data quality"""

    @staticmethod
    def sanitize_name(name: str) -> Optional[str]:
        """
        Sanitize a user's name input.
        Returns None if the input is invalid, sanitized string otherwise.
        
        Rules:
        - Must be at least 2 characters long
        - Must only contain letters, numbers, spaces, hyphens, and apostrophes
        - No HTML tags or script injection
        - Trim whitespace
        - Maximum length of 50 characters
        """
        if not name or len(name.strip()) < 2:
            return None
            
        # Trim whitespace and limit length
        name = name.strip()[:50]
        
        # Escape HTML entities
        name = html.escape(name)
        
        # Only allow letters, numbers, spaces, hyphens, and apostrophes
        allowed_pattern = r'^[a-zA-Z0-9\s\-\']+$'
        if not re.match(allowed_pattern, name):
            return None
            
        return name

    @staticmethod
    def sanitize_email(email: str) -> Optional[str]:
        """
        Sanitize an email address.
        Returns None if the input is invalid, sanitized string otherwise.
        
        Rules:
        - Must be a valid email format
        - No HTML tags or script injection
        - Trim whitespace
        - Maximum length of 254 characters (RFC 5321)
        """
        if not email:
            return None
            
        # Trim whitespace and limit length
        email = email.strip()[:254]
        
        # Basic email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return None
            
        # Escape HTML entities
        email = html.escape(email)
            
        return email

    @staticmethod
    def sanitize_command(command: str) -> Optional[str]:
        """
        Sanitize a command input.
        Returns None if the input is invalid, sanitized string otherwise.
        
        Rules:
        - No HTML tags or script injection
        - No shell metacharacters
        - Trim whitespace
        - Maximum length of 1000 characters
        """
        if not command:
            return None
            
        # Trim whitespace and limit length
        command = command.strip()[:1000]
        
        # Escape HTML entities
        command = html.escape(command)
        
        # Check for shell metacharacters
        shell_metacharacters = r'[;&|`$><]'
        if re.search(shell_metacharacters, command):
            return None
            
        return command

    @staticmethod
    def is_valid_input(text: str, min_length: int = 1, max_length: int = 1000) -> bool:
        """
        General input validation for any text input.
        Returns True if input is valid, False otherwise.
        
        Rules:
        - Must meet minimum length
        - Must not exceed maximum length
        - Must not contain HTML tags or script injection
        """
        if not text or len(text.strip()) < min_length:
            return False
            
        if len(text) > max_length:
            return False
            
        # Check for HTML tags or script tags
        html_pattern = r'<[^>]*>|javascript:|data:'
        if re.search(html_pattern, text, re.IGNORECASE):
            return False
            
        return True 