"""
Unicode output utilities for cross-platform compatibility.
"""

import os
import sys
from shared.isolated_environment import get_env


def safe_print(text: str, fallback_text: str = None):
    """
    Safely print text with Unicode characters, falling back to ASCII on Windows if needed.
    
    Args:
        text: The text to print (may contain Unicode/emoji)
        fallback_text: Alternative text without Unicode (optional)
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # On Windows with certain encodings, fall back to ASCII
        if fallback_text:
            print(fallback_text)
        else:
            # Strip emojis and special characters
            ascii_text = text.encode('ascii', 'ignore').decode('ascii').strip()
            if not ascii_text:
                # If everything was Unicode, use a simple fallback
                print("[Unicode content removed]")
            else:
                print(ascii_text)


def setup_unicode_console():
    """
    Set up the console for better Unicode support on Windows.
    """
    if sys.platform == 'win32':
        # Try to set UTF-8 mode for Windows console
        try:
            import locale
            locale.setlocale(locale.LC_ALL, '')
            
            # Enable UTF-8 mode in Python
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8')
                
            # Set environment variable for better Unicode support
            env_manager = get_env()
            env_manager.set('PYTHONIOENCODING', 'utf-8', 'unicode_utils')
        except Exception:
            # If we can't set up UTF-8, we'll fall back to ASCII in safe_print
            pass


def emoji_safe(emoji: str, fallback: str) -> str:
    """
    Return emoji if supported, otherwise return fallback.
    
    Args:
        emoji: The emoji character(s)
        fallback: ASCII fallback text
    
    Returns:
        The emoji if supported, otherwise the fallback
    """
    if sys.platform == 'win32':
        # Check if we can encode the emoji
        try:
            emoji.encode(sys.stdout.encoding or 'utf-8')
            return emoji
        except (UnicodeEncodeError, AttributeError):
            return fallback
    return emoji


# Common emoji replacements for development messages
EMOJI_MAP = {
    'rocket': ('[U+1F680]', '[START]'),
    'check': (' PASS: ', '[OK]'),
    'warning': (' WARNING: [U+FE0F]', '[WARN]'),
    'error': (' FAIL: ', '[ERROR]'),
    'info': ('[U+1F4DD]', '[INFO]'),
    'wave': ('[U+1F44B]', '[HELLO]'),
    'gear': ('[U+1F527]', '[CONFIG]'),
    'fire': (' FIRE: ', '[HOT]'),
    'globe': ('[U+1F310]', '[WEB]'),
    'folder': ('[U+1F4C2]', '[DIR]'),
    'key': ('[U+1F511]', '[KEY]'),
    'lock': ('[U+1F510]', '[SECURE]'),
    'magnifier': (' SEARCH: ', '[SEARCH]'),
    'clock': ('[U+23F0]', '[TIME]'),
    'recycle': ('[U+267B][U+FE0F]', '[RELOAD]'),
    'sparkles': ('[U+2728]', '[NEW]'),
}


def get_emoji(name: str) -> str:
    """
    Get an emoji by name with automatic fallback.
    
    Args:
        name: The name of the emoji (e.g., 'rocket', 'check')
    
    Returns:
        The emoji or its ASCII fallback
    """
    if name in EMOJI_MAP:
        emoji, fallback = EMOJI_MAP[name]
        return emoji_safe(emoji, fallback)
    return ''