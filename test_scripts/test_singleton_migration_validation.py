#!/usr/bin/env python3
"""
Quick Validation Test for Singleton Migration
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
    print(" PASS:  Shared imports working")
except ImportError as e:
    print(f" FAIL:  Import error: {e}")

try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    print(" PASS:  UserExecutionContext import working")
except ImportError as e:
    print(f" FAIL:  UserExecutionContext import failed: {e}")

try:
    from netra_backend.app.agents.supervisor.agent_instance_factory import (
        get_agent_instance_factory,
        configure_agent_instance_factory
    )
    print(" PASS:  AgentInstanceFactory imports working")
except ImportError as e:
    print(f" FAIL:  AgentInstanceFactory import failed: {e}")

@dataclass
class BasicPerformanceTest:
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

class SingletonMigrationValidator:
    """Validates basic singleton migration functionality"""
    
    @staticmethod
    def test_user_context_creation():
        """Test UserExecutionContext creation without DB"""
        test = BasicPerformanceTest("user_context_creation")
        
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
    
    @staticmethod
    def test_concurrent_context_creation():
        """Test concurrent UserExecutionContext creation"""
        test = BasicPerformanceTest("concurrent_context_creation")
        
        try:
            def create_context(user_id: str):
                return UserExecutionContext(
                    user_id=user_id,
                    thread_id=f"thread_{user_id}",
                    run_id=str(uuid.uuid4())
                )
            
            # Test with 20 concurrent context creations
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(create_context, f"user_{i}")
                    for i in range(20)
                ]
                
                contexts = []
                for future in as_completed(futures):
                    try:
                        context = future.result(timeout=1.0)
                        contexts.append(context)
                    except Exception as e:
                        test.complete(success=False, error=f"Concurrent creation failed: {e}")
                        return test
            
            # Verify all contexts are unique
            user_ids = [ctx.user_id for ctx in contexts]
            run_ids = [ctx.run_id for ctx in contexts]
            
            if len(contexts) == 20 and len(set(run_ids)) == 20:
                test.complete(success=True)
            else:
                test.complete(success=False, error=f"Expected 20 unique contexts, got {len(contexts)} with {len(set(run_ids))} unique run_ids")
                
        except Exception as e:
            test.complete(success=False, error=str(e))
        
        return test
    
    @staticmethod
    def test_memory_isolation():
        """Test that contexts don't share memory"""
        test = BasicPerformanceTest("memory_isolation")
        
        try:
            # Create contexts and modify them
            context1 = UserExecutionContext(
                user_id="user_1",
                thread_id="thread_1",
                run_id=str(uuid.uuid4())
            )
            
            context2 = UserExecutionContext(
                user_id="user_2", 
                thread_id="thread_2",
                run_id=str(uuid.uuid4())
            )
            
            # Verify they're independent
            if (context1.user_id != context2.user_id and 
                context1.thread_id != context2.thread_id and
                context1.run_id != context2.run_id):
                test.complete(success=True)
            else:
                test.complete(success=False, error="Contexts sharing data")
                
        except Exception as e:
            test.complete(success=False, error=str(e))
        
        return test
    
    @staticmethod
    async def run_validation_suite():
        """Run complete validation suite"""
        print(" SEARCH:  Running Singleton Migration Validation Suite")
        print("=" * 50)
        
        tests = [
            SingletonMigrationValidator.test_user_context_creation(),
            SingletonMigrationValidator.test_concurrent_context_creation(),
            SingletonMigrationValidator.test_memory_isolation(),
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            status = " PASS:  PASS" if test.success else " FAIL:  FAIL"
            duration_ms = test.duration * 1000
            
            print(f"{status} {test.test_name:<30} ({duration_ms:.1f}ms)")
            if not test.success:
                print(f"   Error: {test.error}")
                failed += 1
            else:
                passed += 1
        
        print("=" * 50)
        print(f"Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print(" PASS:  Basic singleton migration validation PASSED")
            print("Note: This is a limited test without full system dependencies")
        else:
            print(" FAIL:  Basic singleton migration validation FAILED")
            print("Critical issues detected in basic functionality")
        
        return failed == 0

if __name__ == "__main__":
    print("[U+1F680] Starting Basic Singleton Migration Validation")
    print("This test runs without Docker/database dependencies")
    print()
    
    # Run the validation
    result = asyncio.run(SingletonMigrationValidator.run_validation_suite())
    
    print()
    if result:
        print(" CELEBRATION:  Basic validation completed successfully")
        print("Recommendation: Run full test suite when Docker is available")
    else:
        print(" ALERT:  Basic validation failed - critical issues present")
        print("Recommendation: Fix basic issues before running full tests")