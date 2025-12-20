"""
Utility functions and classes for the scraping system
"""
import uuid
from typing import Optional

from .user_agents import UserAgentRotator, get_user_agent_rotator
from .helpers import clean_text, sanitize_url

__all__ = [
    'UserAgentRotator',
    'get_user_agent_rotator',
    'clean_text',
    'sanitize_url',
    'generate_request_id',
]


def generate_request_id() -> str:
    """Generate a unique request ID"""
    return str(uuid.uuid4())[:8]
