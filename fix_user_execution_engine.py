#!/usr/bin/env python3
"""Fix user_execution_engine.py factory import"""

import re

def fix_user_execution_engine():
    file_path = 'netra_backend/app/agents/supervisor/user_execution_engine.py'

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Fix the factory import
    content = content.replace(
        'from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory',
        'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge'
    )

    # Fix any WebSocketBridgeFactory references
    content = re.sub(r'WebSocketBridgeFactory', 'AgentWebSocketBridge', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Fixed user_execution_engine.py")

if __name__ == "__main__":
    fix_user_execution_engine()