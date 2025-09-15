#!/usr/bin/env python3
"""
Fix remaining factory functions missing authorization tokens.
"""

import re

def fix_websocket_manager_factory():
    """Fix the main websocket_manager.py factory function."""

    file_path = 'netra_backend/app/websocket_core/websocket_manager.py'

    print("Fixing websocket_manager.py factory function...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix 1: Test manager instantiation
    content = re.sub(
        r'            manager = UnifiedWebSocketManager\(\s*mode=WebSocketManagerMode\.ISOLATED,\s*user_context=test_context\s*\)',
        '''            manager = UnifiedWebSocketManager(
                mode=WebSocketManagerMode.ISOLATED,
                user_context=test_context,
                _ssot_authorization_token=secrets.token_urlsafe(16)
            )''',
        content,
        flags=re.MULTILINE
    )

    # Fix 2: Production manager instantiation (already has the token from previous patch)
    # Should be: manager = UnifiedWebSocketManager(mode=mode, user_context=user_context, _ssot_authorization_token=secrets.token_urlsafe(16))

    # Fix 3: Fallback manager instantiation
    content = re.sub(
        r'fallback_manager = UnifiedWebSocketManager\(mode=WebSocketManagerMode\.EMERGENCY\)',
        '''fallback_manager = UnifiedWebSocketManager(
            mode=WebSocketManagerMode.EMERGENCY,
            user_context=test_context if 'test_context' in locals() else user_context,
            _ssot_authorization_token=secrets.token_urlsafe(16)
        )''',
        content
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("websocket_manager.py factory function fixed!")

if __name__ == '__main__':
    fix_websocket_manager_factory()