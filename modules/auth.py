"""
Handles user authentication.
"""
import re
import requests
from config import NESTJS_API_BASE_URL

def is_valid_email(email: str) -> bool:
    """Validates if the given string is a valid email."""
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None

async def authenticate_user(email: str, password: str) -> str | None:
    """Authenticates the user and returns the token."""
    try:
        response = requests.post(f"{NESTJS_API_BASE_URL}/auth/login", json={
            "email": email,
            "password": password
        })
        response.raise_for_status()
        data = response.json()
        return data.get('token')
    except requests.exceptions.RequestException as e:
        print(f"Error in authentication for {email}: {e}")
        return None
