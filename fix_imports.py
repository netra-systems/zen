#!/usr/bin/env python3
"""
Script to systematically fix import paths across unit test files
"""
import os
import glob
import re

def fix_file(file_path):
    """Fix import paths in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Primary fix: unified_manager -> manager
        original_content = content
        content = re.sub(
            r'from netra_backend\.app\.websocket_core\.unified_manager import',
            'from netra_backend.app.websocket_core.manager import',
            content
        )

        # Secondary fixes if needed
        content = re.sub(r'UnifiedEventEmitter', 'UnifiedWebSocketEmitter', content)
        content = re.sub(r'EventValidator', 'WebSocketEventValidator', content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        else:
            return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    # List of files to fix
    websocket_core_files = [
        "netra_backend/tests/unit/websocket_core/test_connection_manager_comprehensive.py",
        "netra_backend/tests/unit/websocket_core/test_ssot_broadcast_consolidation.py",
        "netra_backend/tests/unit/websocket_core/test_ssot_migration_safety.py",
        "netra_backend/tests/unit/websocket_core/test_ssot_security_boundaries.py",
        "netra_backend/tests/unit/websocket_core/test_unified_manager_business_logic.py",
        "netra_backend/tests/unit/websocket_core/test_unified_manager_connection_lifecycle.py",
        "netra_backend/tests/unit/websocket_core/test_unified_manager_connection_validation.py",
        "netra_backend/tests/unit/websocket_core/test_unified_manager_unit_coverage.py",
        "netra_backend/tests/unit/websocket_core/test_unified_websocket_manager_comprehensive.py",
        "netra_backend/tests/unit/websocket_core/test_websocket_bridge_factory_unit.py",
        "netra_backend/tests/unit/websocket_core/test_websocket_broadcast_manager_unit.py",
        "netra_backend/tests/unit/websocket_core/test_websocket_core_unified_manager.py",
        "netra_backend/tests/unit/websocket_core/test_websocket_event_delivery_unit.py",
        "netra_backend/tests/unit/websocket_core/test_websocket_manager_compatibility_layer.py",
        "netra_backend/tests/unit/websocket_core/test_websocket_manager_event_integration_unit.py",
        "netra_backend/tests/unit/websocket_core/test_websocket_manager_factory_functions.py",
        "netra_backend/tests/unit/websocket_core/test_websocket_manager_race_conditions.py",
        "netra_backend/tests/unit/websocket_core/test_websocket_serialization_comprehensive.py"
    ]

    fixed_count = 0
    for file_path in websocket_core_files:
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            if fix_file(full_path):
                fixed_count += 1
        else:
            print(f"File not found: {full_path}")

    print(f"\nFixed {fixed_count} files in websocket_core")

    # Now fix auth service files
    auth_files = [
        "auth_service/tests/test_critical_bugs_simple.py"
    ]

    for file_path in auth_files:
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            if fix_file(full_path):
                fixed_count += 1
        else:
            print(f"File not found: {full_path}")

    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == "__main__":
    main()