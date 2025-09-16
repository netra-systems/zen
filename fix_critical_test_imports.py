#!/usr/bin/env python3
"""
Phase 2 Import Migration: Fix critical test infrastructure files
Part of Issue #1098 remediation plan - Test infrastructure
"""

import re
import os

def fix_test_file_imports(file_path):
    """Fix a single test file's imports to use SSOT patterns"""

    if not os.path.exists(file_path):
        return False, "File does not exist"

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return False, f"Read error: {e}"

    original_content = content

    # Common test file fixes
    fixes = [
        # Fix 1: WebSocketBridgeFactory imports
        ('from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory',
         'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge'),

        ('from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory',
         'from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge'),

        # Fix 2: WebSocket Manager Factory imports
        ('from netra_backend.app.websocket_core.websocket_manager_factory import',
         'from netra_backend.app.websocket_core.canonical_import_patterns import'),

        # Fix 3: Type annotations
        (re.compile(r'WebSocketBridgeFactory'), 'AgentWebSocketBridge'),

        # Fix 4: Function calls
        ('get_websocket_bridge_factory', 'get_agent_websocket_bridge'),
        ('create_websocket_manager', 'get_websocket_manager'),
        ('WebSocketManagerFactory', 'WebSocketManager'),

        # Fix 5: Test-specific patterns
        ('websocket_bridge_factory', 'agent_websocket_bridge'),
        ('websocket_manager_factory', 'websocket_manager'),
    ]

    # Apply fixes
    for old_pattern, new_pattern in fixes:
        if isinstance(old_pattern, str):
            content = content.replace(old_pattern, new_pattern)
        else:  # regex pattern
            content = re.sub(old_pattern, new_pattern, content)

    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Fixed successfully"
        except Exception as e:
            return False, f"Write error: {e}"
    else:
        return False, "No changes needed"

def fix_critical_test_imports():
    """Fix critical test infrastructure files"""

    # Critical test files to fix
    critical_test_files = [
        'tests/mission_critical/test_singleton_bridge_removal_validation.py',
        'tests/mission_critical/test_websocket_manager_resource_exhaustion_recovery_mission_critical.py',
        'tests/integration/test_bridge_removal_integration.py',
        'tests/integration/test_improved_ssot_compliance_scoring_issue_885.py',
        'tests/unit/websocket_core/test_websocket_manager_functional_ssot_issue_885.py',
    ]

    print("=== PHASE 2 IMPORT MIGRATION: Critical Test Infrastructure ===")
    print()

    fixed_count = 0
    for file_path in critical_test_files:
        success, message = fix_test_file_imports(file_path)
        status = "FIXED" if success else "SKIP"
        print(f"{status}: {file_path} - {message}")
        if success:
            fixed_count += 1

    print()
    print(f"=== TEST INFRASTRUCTURE MIGRATION COMPLETE ===")
    print(f"Files processed: {len(critical_test_files)}")
    print(f"Files fixed: {fixed_count}")
    print()
    print("NEXT STEPS:")
    print("1. Run architecture compliance check")
    print("2. Test critical mission-critical tests")
    print("3. Final validation")

if __name__ == "__main__":
    fix_critical_test_imports()