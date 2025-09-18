#!/usr/bin/env python3
"""
Script to update all WebSocket manager factories to provide SSOT authorization tokens.
"""

import re
import os

def patch_websocket_manager_factory():
    """Update websocket_manager_factory.py to provide authorization tokens."""

    file_path = 'netra_backend/app/websocket_core/websocket_manager_factory.py'

    print("Patching websocket_manager_factory.py...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add secrets import if not present
    if 'import secrets' not in content:
        print("Adding secrets import to websocket_manager_factory.py...")
        content = re.sub(
            r'(from typing import.*?\n)',
            r'\1import secrets\n',
            content,
            flags=re.MULTILINE
        )

    # Find and replace WebSocketManager instantiations
    print("Updating WebSocketManager instantiations in factory...")

    # Pattern 1: Direct WebSocketManager(user_context=user_context)
    content = re.sub(
        r'manager = WebSocketManager\(user_context=user_context\)',
        'manager = WebSocketManager(\n            user_context=user_context,\n            _ssot_authorization_token=secrets.token_urlsafe(16)\n        )',
        content
    )

    # Pattern 2: WebSocketManager(user_context=test_context)
    content = re.sub(
        r'manager = WebSocketManager\(user_context=test_context\)',
        'manager = WebSocketManager(\n            user_context=test_context,\n            _ssot_authorization_token=secrets.token_urlsafe(16)\n        )',
        content
    )

    # Pattern 3: Any other WebSocketManager instantiation patterns
    content = re.sub(
        r'WebSocketManager\(([^)]+)\)(?![^(]*_ssot_authorization_token)',
        lambda m: f'WebSocketManager({m.group(1)}, _ssot_authorization_token=secrets.token_urlsafe(16))',
        content
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ websocket_manager_factory.py patched")

def patch_init_file():
    """Update __init__.py wrapper functions."""

    file_path = 'netra_backend/app/websocket_core/__init__.py'

    print("Patching __init__.py...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add secrets import if not present
    if 'import secrets' not in content:
        print("Adding secrets import to __init__.py...")
        content = re.sub(
            r'(import warnings\n)',
            r'\1import secrets\n',
            content
        )

    # Replace WebSocketManager instantiations
    content = re.sub(
        r'return WebSocketManager\(user_context=user_context\)',
        'return WebSocketManager(\n        user_context=user_context,\n        _ssot_authorization_token=secrets.token_urlsafe(16)\n    )',
        content
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ __init__.py patched")

def patch_unified_manager_factory():
    """Update any factory functions in unified_manager.py."""

    file_path = 'netra_backend/app/websocket_core/unified_manager.py'

    print("Checking for factory functions in unified_manager.py...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Look for any direct UnifiedWebSocketManager instantiations without the token
    if 'UnifiedWebSocketManager(' in content and '_ssot_authorization_token' not in content:
        print("Found direct instantiations in unified_manager.py - these should be reviewed")

        # Add a factory function at the end if needed
        if 'def get_websocket_manager()' in content:
            # Update the existing factory function
            content = re.sub(
                r'def get_websocket_manager\(\) -> UnifiedWebSocketManager:\s*"""[^"]*"""\s*return UnifiedWebSocketManager\(\)',
                '''def get_websocket_manager() -> UnifiedWebSocketManager:
    """Get WebSocket manager instance through proper SSOT factory pattern."""
    import secrets
    # This should not be used - use the main factory in websocket_manager.py instead
    raise DeprecationWarning("Use get_websocket_manager() from websocket_manager.py instead")''',
                content,
                flags=re.DOTALL
            )

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("✓ unified_manager.py factory functions updated")

def apply_all_patches():
    """Apply all factory patches."""
    print("Applying Issue #712 factory authorization token patches...")

    patch_websocket_manager_factory()
    patch_init_file()
    patch_unified_manager_factory()

    print("All factory patches applied successfully!")

if __name__ == '__main__':
    apply_all_patches()