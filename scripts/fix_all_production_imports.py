#!/usr/bin/env python3
"""
Phase 2 Import Migration: Fix all production files to use SSOT patterns
Part of Issue #1098 remediation plan - Critical production files
"""

import re
import os

def fix_file_imports(file_path, fixes):
    """Apply import fixes to a specific file"""
    if not os.path.exists(file_path):
        print(f"SKIP: {file_path} does not exist")
        return False

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    for old_pattern, new_pattern in fixes:
        if isinstance(old_pattern, str):
            content = content.replace(old_pattern, new_pattern)
        else:  # regex pattern
            content = re.sub(old_pattern, new_pattern, content)

    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"FIXED: {file_path}")
        return True
    else:
        print(f"NO_CHANGE: {file_path}")
        return False

def fix_all_production_imports():
    """Fix all critical production files to use SSOT patterns"""

    files_to_fix = [
        # Critical production files
        'netra_backend/app/handlers/example_message_handler.py',
        'netra_backend/app/services/factory_adapter.py',
        'netra_backend/app/smd.py',
        'netra_backend/app/agents/supervisor/user_execution_engine.py',
        'netra_backend/app/factories/__init__.py'
    ]

    # Common fixes for all files
    common_fixes = [
        # Fix 1: WebSocketBridgeFactory import from services
        ('from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory',
         'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge'),

        # Fix 2: WebSocketBridgeFactory import from factories
        ('from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory',
         'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge'),

        # Fix 3: Multiple imports from services
        (re.compile(r'from netra_backend\.app\.services\.websocket_bridge_factory import.*WebSocketBridgeFactory.*'),
         'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge'),

        # Fix 4: Update type annotations
        (re.compile(r'WebSocketBridgeFactory'), 'AgentWebSocketBridge'),

        # Fix 5: Update function names
        (re.compile(r'get_websocket_bridge_factory'), 'get_agent_websocket_bridge'),

        # Fix 6: Update UserWebSocketEmitter imports
        ('UserWebSocketEmitter', 'AgentWebSocketBridge'),  # Simplify to single SSOT class
    ]

    print("=== PHASE 2 IMPORT MIGRATION: Critical Production Files ===")
    print()

    fixed_count = 0

    for file_path in files_to_fix:
        if fix_file_imports(file_path, common_fixes):
            fixed_count += 1

    print()
    print(f"=== MIGRATION COMPLETE ===")
    print(f"Files processed: {len(files_to_fix)}")
    print(f"Files fixed: {fixed_count}")
    print()
    print("NEXT STEPS:")
    print("1. Test imports: python -c 'from netra_backend.app.handlers.example_message_handler import ...'")
    print("2. Run Golden Path validation")
    print("3. Process remaining test files")

if __name__ == "__main__":
    fix_all_production_imports()