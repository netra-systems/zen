#!/usr/bin/env python3

import subprocess
import sys

files_to_test = [
    "netra_backend/tests/unit/agents/supervisor/test_agent_registry_issue758_comprehensive.py",
    "netra_backend/tests/unit/test_websocket_manager_factory.py",
    "netra_backend/tests/unit/websocket/test_connection_id_generation.py",
    "netra_backend/tests/unit/websocket/test_manager_factory_business_logic.py",
    "netra_backend/tests/unit/websocket/test_message_routing_logic.py",
    "netra_backend/tests/unit/websocket/test_websocket_id_migration_uuid_exposure.py",
    "netra_backend/tests/unit/websocket_core/test_isolated_websocket_manager_comprehensive.py",
    "netra_backend/tests/unit/websocket_core/test_unified_manager.py",
    "netra_backend/tests/unit/websocket_core/test_websocket_connection_management_unit.py",
    "netra_backend/tests/unit/websocket_core/test_websocket_manager_factory_comprehensive.py"
]

print("Validating Issue #824 WebSocket Manager Factory Import Fixes")
print("=" * 60)

success_count = 0
total_count = len(files_to_test)

for i, file_path in enumerate(files_to_test, 1):
    print(f"[{i:2d}/{total_count}] Testing: {file_path}")
    
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", file_path, "--collect-only", "-q"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"         ✅ SUCCESS - Collection passed")
            success_count += 1
        else:
            print(f"         ❌ FAILED - Collection failed")
            print(f"         Error: {result.stderr.strip()}")
            
    except Exception as e:
        print(f"         ❌ ERROR - Exception: {e}")

print("\n" + "=" * 60)
print(f"SUMMARY: {success_count}/{total_count} files fixed successfully")

if success_count == total_count:
    print("🎉 ALL TARGETED WEBSSOCKET MANAGER FACTORY IMPORT ISSUES RESOLVED!")
    sys.exit(0)
else:
    print(f"⚠️  {total_count - success_count} files still have issues")
    sys.exit(1)