#!/usr/bin/env python3
"""Fix factories/__init__.py imports"""

def fix_factories_init():
    file_path = 'netra_backend/app/factories/__init__.py'

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Replace the entire websocket_bridge_factory import block
    old_import = """from netra_backend.app.factories.websocket_bridge_factory import (
    WebSocketBridgeProtocol,
    StandardWebSocketBridge,
    create_standard_websocket_bridge,"""

    new_import = """# SSOT PHASE 2 FIX: Replace factory imports with SSOT agent bridge
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge"""

    # Find the complete import block (it may span multiple lines)
    import re

    # Match the import block up to the closing parenthesis
    pattern = r'from netra_backend\.app\.factories\.websocket_bridge_factory import \([^)]*\)'
    content = re.sub(pattern, new_import, content, flags=re.MULTILINE | re.DOTALL)

    # Also handle simple one-line imports
    content = content.replace(
        'from netra_backend.app.factories.websocket_bridge_factory import',
        '# SSOT PHASE 2 FIX: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge #'
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Fixed factories/__init__.py")

if __name__ == "__main__":
    fix_factories_init()