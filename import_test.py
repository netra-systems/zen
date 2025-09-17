#!/usr/bin/env python3
"""
Test basic imports to validate system health
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

print("Testing basic imports...")

try:
    print("1. Testing config import...")
    from netra_backend.app.config import get_config
    print("   ✅ Config import successful")

    print("2. Testing test runner import...")
    import tests.unified_test_runner
    print("   ✅ Test runner import successful")

    print("3. Testing WebSocket manager import...")
    from netra_backend.app.websocket_core.manager import WebSocketManager
    print("   ✅ WebSocket manager import successful")

    print("4. Testing database manager import...")
    from netra_backend.app.db.database_manager import DatabaseManager
    print("   ✅ Database manager import successful")

    print("5. Testing agent registry import...")
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    print("   ✅ Agent registry import successful")

    print("\n✅ ALL BASIC IMPORTS SUCCESSFUL")
    print("System appears ready for testing.")

except ImportError as e:
    print(f"\n❌ IMPORT FAILED: {e}")
    print("System may have infrastructure issues.")
    sys.exit(1)
except Exception as e:
    print(f"\n💥 UNEXPECTED ERROR: {e}")
    sys.exit(1)