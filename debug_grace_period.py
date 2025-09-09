#!/usr/bin/env python3
"""
Debug script to test the grace period implementation directly.
"""

import asyncio
import time
from unittest.mock import Mock

# Set up path to import the validator
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'netra_backend'))

from netra_backend.app.websocket_core.gcp_initialization_validator import GCPWebSocketInitializationValidator

class SimpleRedisManager:
    def __init__(self):
        self._connected = True
        
    def is_connected(self):
        print(f"is_connected() called, returning {self._connected}")
        return self._connected

class SimpleAppState:
    def __init__(self):
        self.redis_manager = SimpleRedisManager()

def test_grace_period_direct():
    print("=== Testing Grace Period Direct ===")
    
    # Create app state with connected Redis
    app_state = SimpleAppState()
    
    # Create validator 
    validator = GCPWebSocketInitializationValidator(app_state)
    
    # Set GCP environment
    print(f"Before update: is_gcp_environment={validator.is_gcp_environment}")
    validator.update_environment_configuration("staging", True)
    print(f"After update: is_gcp_environment={validator.is_gcp_environment}")
    
    # Test the method directly
    print("Calling _validate_redis_readiness()...")
    start_time = time.time()
    result = validator._validate_redis_readiness()
    elapsed = time.time() - start_time
    
    print(f"Result: {result}")
    print(f"Elapsed time: {elapsed:.3f}s")
    
    if elapsed >= 0.49:
        print("✅ Grace period applied successfully")
    else:
        print(f"❌ Grace period not applied - elapsed: {elapsed}s")

if __name__ == "__main__":
    test_grace_period_direct()