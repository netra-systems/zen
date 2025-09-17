#!/usr/bin/env python3
"""
Script to update WebSocket manager factory to provide SSOT authorization tokens.
"""

import re
import secrets

def update_factory():
    """Update factory to provide SSOT authorization token."""

    file_path = 'netra_backend/app/websocket_core/websocket_manager.py'

    print("Reading factory file...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update the test manager creation
    print("Updating test manager instantiation...")
    old_test_instantiation = '''            manager = UnifiedWebSocketManager(
                mode=WebSocketManagerMode.ISOLATED,
                user_context=test_context
            )'''

    new_test_instantiation = '''            manager = UnifiedWebSocketManager(
                mode=WebSocketManagerMode.ISOLATED,
                user_context=test_context,
                _ssot_authorization_token=secrets.token_urlsafe(16)
            )'''

    content = content.replace(old_test_instantiation, new_test_instantiation)

    # Update the production manager creation
    print("Updating production manager instantiation...")
    old_prod_instantiation = '''            # Production mode with proper user context
            manager = UnifiedWebSocketManager(
                mode=mode,
                user_context=user_context
            )'''

    new_prod_instantiation = '''            # Production mode with proper user context
            manager = UnifiedWebSocketManager(
                mode=mode,
                user_context=user_context,
                _ssot_authorization_token=secrets.token_urlsafe(16)
            )'''

    content = content.replace(old_prod_instantiation, new_prod_instantiation)

    # Update the fallback manager creation
    print("Updating fallback manager instantiation...")
    old_fallback_instantiation = '''        fallback_manager = UnifiedWebSocketManager(mode=WebSocketManagerMode.EMERGENCY)'''

    new_fallback_instantiation = '''        fallback_manager = UnifiedWebSocketManager(
            mode=WebSocketManagerMode.EMERGENCY,
            user_context=test_context if 'test_context' in locals() else user_context,
            _ssot_authorization_token=secrets.token_urlsafe(16)
        )'''

    content = content.replace(old_fallback_instantiation, new_fallback_instantiation)

    # Add secrets import if not present
    if 'import secrets' not in content:
        print("Adding secrets import...")
        content = re.sub(
            r'(from typing import.*?\n)',
            r'\1import secrets\n',
            content,
            flags=re.MULTILINE
        )

    print("Writing updated factory file...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Factory update completed!")

if __name__ == '__main__':
    update_factory()