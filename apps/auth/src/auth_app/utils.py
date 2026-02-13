"""Utility functions for auth app."""

import secrets
import string


def generate_random_password(length: int = 12) -> str:
    """Generate a secure random password.
    
    Args:
        length: Length of the password (default: 12)
    
    Returns:
        A random password string containing letters, digits, and special characters.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))






