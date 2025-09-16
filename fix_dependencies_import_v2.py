#!/usr/bin/env python3
"""
Phase 2 Import Migration: Fix dependencies.py to use SSOT patterns
Part of Issue #1098 remediation plan
"""

import re

def fix_dependencies_imports():
    """Fix the critical dependencies.py file imports to use SSOT patterns"""

    file_path = 'netra_backend/app/dependencies.py'

    with open(file_path, 'r') as f:
        content = f.read()

    # Fix 1: Replace websocket_bridge_factory import with SSOT
    old_import = """from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    WebSocketFactoryConfig
)"""

    new_import = """# SSOT PHASE 2 FIX: Import from SSOT agent websocket bridge instead of deprecated factory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge"""

    content = content.replace(old_import, new_import)

    # Fix 2: Update type annotations and function signatures
    content = re.sub(
        r'WebSocketBridgeFactory',
        'AgentWebSocketBridge',
        content
    )

    # Fix 3: Update WebSocketFactoryConfig references
    content = re.sub(
        r'WebSocketFactoryConfig',
        'dict',  # Use simple dict for config instead of factory pattern
        content
    )

    # Fix 4: Update factory function names
    content = re.sub(
        r'get_websocket_bridge_factory',
        'get_agent_websocket_bridge',
        content
    )

    # Fix 5: Update variable names
    content = re.sub(
        r'websocket_bridge_factory',
        'agent_websocket_bridge',
        content
    )

    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(content)

    print(f"Fixed {file_path} - Updated to SSOT patterns")
    print("   - Replaced websocket_bridge_factory with agent_websocket_bridge")
    print("   - Updated all function names and type annotations")
    print("   - Removed factory pattern dependencies")

if __name__ == "__main__":
    fix_dependencies_imports()