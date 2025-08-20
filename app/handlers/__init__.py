"""Handler modules for message processing

This package contains specialized handlers for different types of messages
and processing workflows.
"""

from .example_message_handler import handle_example_message, get_example_message_handler

__all__ = ['handle_example_message', 'get_example_message_handler']