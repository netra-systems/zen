"""Handler modules for message processing

This package contains specialized handlers for different types of messages
and processing workflows.
"""

from netra_backend.app.handlers.example_message_handler import (
    get_example_message_handler,
    handle_example_message,
)

__all__ = ['handle_example_message', 'get_example_message_handler']