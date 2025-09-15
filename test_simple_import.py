#!/usr/bin/env python3
"""
Simple test script to validate Issue #1236 fix
"""

import warnings
import sys
import os

# Enable all warnings
warnings.simplefilter('always')

print("Testing specific module import (should NOT warn):")
try:
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as SpecificManager
    print("✅ Specific import succeeded without warnings")
except Exception as e:
    print(f"❌ Specific import failed: {e}")

print("\nTesting direct import (should warn):")
try:
    from netra_backend.app.websocket_core import create_websocket_manager
    print("✅ Direct import succeeded")
except Exception as e:
    print(f"❌ Direct import failed: {e}")