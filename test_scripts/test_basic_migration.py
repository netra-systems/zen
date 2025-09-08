#!/usr/bin/env python3
"""
Basic Validation Test for Singleton Migration
Tests basic functionality without full Docker dependencies
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

# Test if basic imports work
try:
    from shared.isolated_environment import IsolatedEnvironment
    print("PASS: Shared imports working")
except ImportError as e:
    print(f"FAIL: Import error: {e}")

try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    print("PASS: UserExecutionContext import working")
except ImportError as e:
    print(f"FAIL: UserExecutionContext import failed: {e}")

@dataclass
class BasicTest:
    """Basic performance test without external dependencies"""
    test_name: str
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    duration: float = 0.0
    success: bool = False
    error: str = ""
    
    def complete(self, success: bool = True, error: str = ""):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error = error

def test_user_context_creation():
    """Test UserExecutionContext creation without DB"""
    test = BasicTest("user_context_creation")
    
    try:
        # Create multiple user contexts
        contexts = []
        for i in range(10):
            context = UserExecutionContext(
                user_id=f"user_{i}",
                thread_id=f"thread_{i}",
                run_id=str(uuid.uuid4())
            )
            contexts.append(context)
        
        # Verify they're unique
        user_ids = [ctx.user_id for ctx in contexts]
        run_ids = [ctx.run_id for ctx in contexts]
        
        if len(set(user_ids)) == 10 and len(set(run_ids)) == 10:
            test.complete(success=True)
        else:
            test.complete(success=False, error="UserContext not unique")
            
    except Exception as e:
        test.complete(success=False, error=str(e))
    
    return test

def run_validation():
    """Run basic validation"""
    print("Running Basic Singleton Migration Validation")
    print("=" * 50)
    
    test = test_user_context_creation()
    
    status = "PASS" if test.success else "FAIL"
    duration_ms = test.duration * 1000
    
    print(f"{status}: {test.test_name} ({duration_ms:.1f}ms)")
    if not test.success:
        print(f"   Error: {test.error}")
    
    print("=" * 50)
    if test.success:
        print("PASS: Basic validation completed")
    else:
        print("FAIL: Basic validation failed")
    
    return test.success

if __name__ == "__main__":
    print("Starting Basic Singleton Migration Validation")
    result = run_validation()
    
    if result:
        print("SUCCESS: Basic functionality working")
    else:
        print("FAILURE: Critical issues detected")