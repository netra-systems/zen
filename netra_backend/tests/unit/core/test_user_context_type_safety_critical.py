"""
CRITICAL Unit Tests for User Context Type Safety Violations

These tests are DESIGNED TO FAIL initially to expose the critical type safety violations
in user context management that cause cross-user data corruption.

Business Risk: Enterprise user results sent to free user due to string-based ID mixing
Technical Risk: Context corruption in multi-user agent execution scenarios

KEY VIOLATIONS TO EXPOSE:
1. netra_backend/app/data_contexts/user_data_context.py:56 - user_id: str, request_id: str, thread_id: str
2. netra_backend/app/data_contexts/user_data_context.py:175 - Same pattern repeated
3. netra_backend/app/data_contexts/user_data_context.py:416 - Same pattern repeated
4. netra_backend/app/dependencies.py:385 - user_id: str, thread_id: Optional[str], run_id: Optional[str]

These tests MUST initially FAIL to demonstrate the violations exist.
"""

import pytest
import asyncio
import uuid
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set, Optional
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the problematic modules to test
from netra_backend.app.data_contexts.user_data_context import UserDataContext
from netra_backend.app.dependencies import get_user_scoped_db_session

# Import the CORRECT strongly-typed identifiers that SHOULD be used
from shared.types import (
    UserID, ThreadID, RequestID, RunID, ExecutionID,
    ensure_user_id, ensure_thread_id, ensure_request_id,
    StronglyTypedUserExecutionContext,
    ContextValidationError, IsolationViolationError
)


class TestUserContextTypeSafetyViolations(SSotBaseTestCase):
    """
    CRITICAL FAILING TESTS: User Context Type Safety Violations
    
    These tests MUST initially FAIL to demonstrate that user context
    components are using unsafe string-based IDs that cause context mixing.
    
    EXPECTED INITIAL RESULT: ALL TESTS SHOULD FAIL
    BUSINESS IMPACT: Prevents cross-user data corruption
    """
    
    def setup_method(self, method):
        """Setup test with enhanced violation detection."""
        super().setup_method(method)
        
        # Enable strict type checking mode for enhanced detection
        self.set_env_var("STRICT_TYPE_CHECKING", "true")
        self.set_env_var("DETECT_ID_MIXING", "true")
        self.set_env_var("FAIL_ON_STRING_IDS", "true")
        
        # Track violations found during test
        self.violations_detected: List[str] = []
        
    def test_user_data_context_constructor_rejects_string_ids(self):
        """
        CRITICAL FAILING TEST: UserDataContext constructor should reject string IDs
        
        EXPECTED RESULT: FAIL - Constructor accepts string IDs (VIOLATION)
        BUSINESS RISK: String IDs cause context mixing between users
        
        This test will FAIL because UserDataContext.__init__ accepts:
        - user_id: str (should be UserID)
        - request_id: str (should be RequestID) 
        - thread_id: str (should be ThreadID)
        """
        print("🚨 TESTING: UserDataContext constructor type safety")
        
        # These should FAIL if type safety is working
        user_id_str = "test-user-123"
        request_id_str = "test-request-456" 
        thread_id_str = "test-thread-789"
        
        try:
            # This SHOULD raise a TypeError if type safety is implemented
            # But it WON'T because the current implementation accepts strings
            context = UserDataContext(
                user_id=user_id_str,      # VIOLATION: should be UserID type
                request_id=request_id_str, # VIOLATION: should be RequestID type
                thread_id=thread_id_str    # VIOLATION: should be ThreadID type
            )
            
            # If we reach here, the constructor accepted string IDs (VIOLATION)
            violation_msg = (
                f"CRITICAL VIOLATION: UserDataContext constructor accepted string IDs! "
                f"user_id='{user_id_str}' (type: {type(user_id_str)}), "
                f"request_id='{request_id_str}' (type: {type(request_id_str)}), "
                f"thread_id='{thread_id_str}' (type: {type(thread_id_str)})"
            )
            self.violations_detected.append(violation_msg)
            print(f"❌ {violation_msg}")
            
            # Record metrics about this violation
            self.record_metric("constructor_accepts_string_ids", True)
            self.record_metric("violation_location", "UserDataContext.__init__:56")
            
            # FAIL the test because type safety is NOT working
            pytest.fail(
                "CRITICAL TYPE SAFETY VIOLATION: UserDataContext constructor accepted string IDs. "
                "This enables cross-user context mixing. Constructor should require strongly-typed IDs: "
                "UserID, RequestID, ThreadID"
            )
            
        except TypeError as e:
            # If we get a TypeError, type safety IS working (test passes)
            print(f"✅ Type safety working: {e}")
            self.record_metric("constructor_rejects_string_ids", True)
            
        except Exception as e:
            # Unexpected error - still a violation because it should be a TypeError
            violation_msg = f"UNEXPECTED ERROR in UserDataContext constructor: {e}"
            self.violations_detected.append(violation_msg)
            print(f"⚠️  {violation_msg}")
            pytest.fail(f"Unexpected error (should be TypeError for string IDs): {e}")
    
    def test_strongly_typed_ids_are_enforced_in_context_creation(self):
        """
        CRITICAL FAILING TEST: Context creation should enforce strongly-typed IDs
        
        EXPECTED RESULT: FAIL - No enforcement of strongly-typed IDs
        BUSINESS RISK: Mixed ID types cause routing failures in multi-user scenarios
        """
        print("🚨 TESTING: Strongly-typed ID enforcement")
        
        # Create strongly-typed IDs (the CORRECT way)
        correct_user_id = UserID("user_12345")
        correct_request_id = RequestID("req_67890")
        correct_thread_id = ThreadID("thread_abcdef")
        
        # Create string IDs (the WRONG way that should be rejected)
        wrong_user_id = "user_12345"  # Should be UserID type
        wrong_request_id = "req_67890"  # Should be RequestID type
        wrong_thread_id = "thread_abcdef"  # Should be ThreadID type
        
        # Test 1: Strongly-typed IDs should work
        try:
            typed_context = UserDataContext(
                user_id=correct_user_id,
                request_id=correct_request_id,
                thread_id=correct_thread_id
            )
            print("✅ Strongly-typed IDs accepted (good)")
            self.record_metric("strongly_typed_ids_accepted", True)
        except Exception as e:
            pytest.fail(f"Strongly-typed IDs should be accepted but got error: {e}")
        
        # Test 2: String IDs should be REJECTED (this will likely FAIL)
        string_ids_accepted = False
        try:
            string_context = UserDataContext(
                user_id=wrong_user_id,      # VIOLATION: string instead of UserID
                request_id=wrong_request_id, # VIOLATION: string instead of RequestID
                thread_id=wrong_thread_id    # VIOLATION: string instead of ThreadID
            )
            string_ids_accepted = True
            print("❌ String IDs wrongly accepted - TYPE SAFETY VIOLATION!")
        except TypeError:
            print("✅ String IDs correctly rejected")
            self.record_metric("string_ids_rejected", True)
        except Exception as e:
            print(f"⚠️ Unexpected error with string IDs: {e}")
        
        # If string IDs were accepted, this is a CRITICAL violation
        if string_ids_accepted:
            violation_msg = (
                "CRITICAL TYPE SAFETY VIOLATION: UserDataContext accepted string IDs instead of "
                "strongly-typed IDs. This enables ID mixing bugs in multi-user scenarios."
            )
            self.violations_detected.append(violation_msg)
            self.record_metric("type_safety_violation_detected", True)
            
            pytest.fail(
                "TYPE SAFETY FAILURE: Constructor should reject string IDs and require "
                "UserID, RequestID, ThreadID types to prevent cross-user contamination."
            )
    
    def test_concurrent_user_contexts_detect_id_collision(self):
        """
        CRITICAL FAILING TEST: Concurrent user contexts should detect ID collisions
        
        EXPECTED RESULT: FAIL - No protection against ID collisions
        BUSINESS RISK: Race conditions cause user A to see user B's data
        """
        print("🚨 TESTING: Concurrent context ID collision detection")
        
        # Create contexts that might collide due to string ID weakness
        collision_results = []
        
        def create_context_with_potential_collision(user_suffix: str) -> Dict:
            """Create context that might collide with others."""
            try:
                # These IDs are designed to potentially collide due to string handling
                user_id = f"user_{user_suffix}"
                request_id = f"req_{user_suffix}"
                thread_id = f"thread_{user_suffix}"
                
                context = UserDataContext(
                    user_id=user_id,
                    request_id=request_id,
                    thread_id=thread_id
                )
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "context_id": id(context),
                    "thread": threading.current_thread().ident
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "thread": threading.current_thread().ident
                }
        
        # Create multiple contexts concurrently to test for collisions
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            # Create contexts with similar IDs that might collide
            for i in range(10):
                future = executor.submit(create_context_with_potential_collision, str(i))
                futures.append(future)
            
            # Collect results
            for future in futures:
                result = future.result()
                collision_results.append(result)
        
        # Analyze results for potential collisions
        successful_contexts = [r for r in collision_results if r.get("success", False)]
        context_ids = [r["context_id"] for r in successful_contexts]
        unique_context_ids = set(context_ids)
        
        print(f"Created contexts: {len(successful_contexts)}")
        print(f"Unique context IDs: {len(unique_context_ids)}")
        
        # Record metrics
        self.record_metric("concurrent_contexts_created", len(successful_contexts))
        self.record_metric("unique_context_ids", len(unique_context_ids))
        
        # Check for collision detection mechanisms
        collision_detection_working = False
        try:
            # Try to create two contexts with identical string IDs
            identical_user_id = "collision_test_user"
            identical_request_id = "collision_test_request"  
            identical_thread_id = "collision_test_thread"
            
            context1 = UserDataContext(
                user_id=identical_user_id,
                request_id=identical_request_id,
                thread_id=identical_thread_id
            )
            
            context2 = UserDataContext(
                user_id=identical_user_id,    # SAME ID - should detect collision
                request_id=identical_request_id, # SAME ID - should detect collision
                thread_id=identical_thread_id    # SAME ID - should detect collision
            )
            
            # If we reach here, no collision detection is implemented (VIOLATION)
            violation_msg = (
                "CRITICAL VIOLATION: No collision detection for identical context IDs. "
                "This allows multiple contexts with same IDs, causing user data mixing."
            )
            self.violations_detected.append(violation_msg)
            print(f"❌ {violation_msg}")
            
        except Exception as collision_error:
            # If we got an exception, collision detection might be working
            print(f"✅ Possible collision detection: {collision_error}")
            collision_detection_working = True
        
        # FAIL if no collision detection is working
        if not collision_detection_working:
            self.record_metric("collision_detection_missing", True)
            pytest.fail(
                "CRITICAL CONCURRENCY VIOLATION: No collision detection for user context IDs. "
                "Multiple contexts can have identical IDs, causing cross-user data corruption."
            )
        
        self.record_metric("collision_detection_working", collision_detection_working)
    
    def test_user_context_memory_isolation_boundaries(self):
        """
        CRITICAL FAILING TEST: User context memory should be strictly isolated
        
        EXPECTED RESULT: FAIL - No memory isolation between contexts
        BUSINESS RISK: Memory sharing allows user A to access user B's data
        """
        print("🚨 TESTING: User context memory isolation")
        
        # Create two contexts with different users
        user1_id = "memory_test_user_1"
        user2_id = "memory_test_user_2"
        
        context1 = UserDataContext(
            user_id=user1_id,
            request_id="req_1", 
            thread_id="thread_1"
        )
        
        context2 = UserDataContext(
            user_id=user2_id,
            request_id="req_2",
            thread_id="thread_2"
        )
        
        # Test memory isolation by checking internal state
        isolation_violations = []
        
        # Check if contexts share any memory references
        context1_dict = vars(context1)
        context2_dict = vars(context2)
        
        for attr_name in context1_dict:
            if attr_name in context2_dict:
                val1 = context1_dict[attr_name]
                val2 = context2_dict[attr_name]
                
                # Check for shared object references (violation)
                if id(val1) == id(val2) and val1 is not None:
                    violation = f"Shared memory reference in attribute '{attr_name}': {id(val1)}"
                    isolation_violations.append(violation)
                    print(f"❌ Memory isolation violation: {violation}")
        
        # Test context data modification isolation
        try:
            # Modify context1 and check if context2 is affected
            if hasattr(context1, '_metadata'):
                context1._metadata = {"test": "user1_data"}
            
            if hasattr(context2, '_metadata'):
                context2._metadata = {"test": "user2_data"}
                
                # Check if modification affected the other context
                if hasattr(context1, '_metadata') and context1._metadata.get("test") == "user2_data":
                    violation = "Context modification affected other user's context"
                    isolation_violations.append(violation)
                    print(f"❌ Data isolation violation: {violation}")
        
        except Exception as e:
            print(f"⚠️ Unexpected error in memory isolation test: {e}")
        
        # Record metrics
        self.record_metric("memory_isolation_violations", len(isolation_violations))
        
        # FAIL if isolation violations were found
        if isolation_violations:
            self.violations_detected.extend(isolation_violations)
            pytest.fail(
                f"CRITICAL MEMORY ISOLATION VIOLATIONS: {len(isolation_violations)} violations found. "
                f"User contexts are sharing memory, enabling cross-user data access: "
                f"{isolation_violations}"
            )
        
        print("✅ Memory isolation appears intact (test passed)")
    
    def test_dependencies_function_string_id_acceptance(self):
        """
        CRITICAL FAILING TEST: Dependencies should reject string-based IDs
        
        EXPECTED RESULT: FAIL - get_user_scoped_db_session accepts string IDs
        BUSINESS RISK: Database sessions can be mixed between users due to weak typing
        
        Tests the violation at netra_backend/app/dependencies.py:385
        """
        print("🚨 TESTING: Dependencies function string ID acceptance")
        
        # Test the problematic function signature from dependencies.py:385
        # async def get_user_scoped_db_session(
        #     user_id: str = "system",  # VIOLATION: should be UserID
        #     request_id: Optional[str] = None,  # VIOLATION: should be RequestID
        #     thread_id: Optional[str] = None   # VIOLATION: should be ThreadID
        # )
        
        string_ids_accepted = True
        dependency_violations = []
        
        try:
            # These string IDs should be REJECTED if type safety is working
            string_user_id = "dep_test_user"      # VIOLATION: str instead of UserID
            string_request_id = "dep_test_request" # VIOLATION: str instead of RequestID  
            string_thread_id = "dep_test_thread"   # VIOLATION: str instead of ThreadID
            
            # Test if the function accepts string IDs (it shouldn't)
            # Note: We can't actually call this async function easily in sync test,
            # but we can inspect the signature
            import inspect
            from netra_backend.app.dependencies import get_user_scoped_db_session
            
            sig = inspect.signature(get_user_scoped_db_session)
            params = sig.parameters
            
            # Check parameter types
            user_id_param = params.get('user_id')
            request_id_param = params.get('request_id') 
            thread_id_param = params.get('thread_id')
            
            if user_id_param and user_id_param.annotation == str:
                violation = f"user_id parameter has str annotation (should be UserID): {user_id_param}"
                dependency_violations.append(violation)
                print(f"❌ Type annotation violation: {violation}")
            
            if request_id_param and str(request_id_param.annotation).find('str') != -1:
                violation = f"request_id parameter uses str annotation (should be RequestID): {request_id_param}"
                dependency_violations.append(violation)
                print(f"❌ Type annotation violation: {violation}")
                
            if thread_id_param and str(thread_id_param.annotation).find('str') != -1:
                violation = f"thread_id parameter uses str annotation (should be ThreadID): {thread_id_param}"
                dependency_violations.append(violation)
                print(f"❌ Type annotation violation: {violation}")
            
        except Exception as e:
            print(f"⚠️ Error inspecting dependencies function: {e}")
            dependency_violations.append(f"Could not inspect function signature: {e}")
        
        # Record metrics
        self.record_metric("dependency_type_violations", len(dependency_violations))
        self.record_metric("dependencies_function_checked", True)
        
        # FAIL if violations were found (expected for initial test run)
        if dependency_violations:
            self.violations_detected.extend(dependency_violations)
            pytest.fail(
                f"CRITICAL DEPENDENCY TYPE VIOLATIONS: {len(dependency_violations)} violations in "
                f"get_user_scoped_db_session function. String-based IDs enable database session "
                f"mixing between users: {dependency_violations}"
            )
        
        print("✅ Dependencies function has proper type annotations")
    
    def test_context_factory_isolation_enforcement(self):
        """
        CRITICAL FAILING TEST: Context factory should enforce isolation
        
        EXPECTED RESULT: FAIL - Factory allows context mixing
        BUSINESS RISK: Factory creates contexts that can interfere with each other
        """
        print("🚨 TESTING: Context factory isolation enforcement")
        
        factory_violations = []
        
        # Create multiple contexts through factory pattern to test isolation
        contexts_created = []
        
        for i in range(5):
            try:
                context = UserDataContext(
                    user_id=f"factory_test_user_{i}",
                    request_id=f"factory_test_request_{i}",
                    thread_id=f"factory_test_thread_{i}"
                )
                contexts_created.append({
                    "index": i,
                    "context": context,
                    "memory_id": id(context)
                })
            except Exception as e:
                factory_violations.append(f"Context creation failed for index {i}: {e}")
        
        print(f"Created {len(contexts_created)} contexts via factory pattern")
        
        # Test for isolation violations between factory-created contexts
        for i, ctx_info in enumerate(contexts_created):
            for j, other_ctx_info in enumerate(contexts_created):
                if i != j:
                    # Check for shared state between contexts (violation)
                    ctx1 = ctx_info["context"]
                    ctx2 = other_ctx_info["context"]
                    
                    # Test if contexts share any internal state
                    if hasattr(ctx1, '__dict__') and hasattr(ctx2, '__dict__'):
                        shared_attrs = []
                        for attr_name, attr_val in ctx1.__dict__.items():
                            if (hasattr(ctx2, attr_name) and 
                                getattr(ctx2, attr_name) is attr_val and
                                attr_val is not None):
                                shared_attrs.append(attr_name)
                        
                        if shared_attrs:
                            violation = (
                                f"Factory contexts {i} and {j} share state in attributes: {shared_attrs}"
                            )
                            factory_violations.append(violation)
                            print(f"❌ Factory isolation violation: {violation}")
        
        # Test factory context cleanup and resource management
        context_cleanup_violations = []
        for ctx_info in contexts_created:
            try:
                ctx = ctx_info["context"]
                # Test if context has proper cleanup mechanisms
                if not hasattr(ctx, '__del__') and not hasattr(ctx, 'cleanup'):
                    violation = f"Context {ctx_info['index']} lacks cleanup mechanisms"
                    context_cleanup_violations.append(violation)
            except Exception as e:
                context_cleanup_violations.append(f"Cleanup test failed: {e}")
        
        # Record metrics
        self.record_metric("factory_contexts_created", len(contexts_created))
        self.record_metric("factory_isolation_violations", len(factory_violations))
        self.record_metric("factory_cleanup_violations", len(context_cleanup_violations))
        
        # Combine all violations
        all_factory_violations = factory_violations + context_cleanup_violations
        
        # FAIL if violations were found
        if all_factory_violations:
            self.violations_detected.extend(all_factory_violations)
            pytest.fail(
                f"CRITICAL FACTORY ISOLATION VIOLATIONS: {len(all_factory_violations)} violations "
                f"in context factory pattern. Contexts are not properly isolated, enabling "
                f"cross-user interference: {all_factory_violations}"
            )
        
        print("✅ Factory isolation appears intact")
    
    def teardown_method(self, method):
        """Enhanced teardown with violation reporting."""
        super().teardown_method(method)
        
        # Report all violations found during test
        if self.violations_detected:
            print(f"\n🚨 TOTAL VIOLATIONS DETECTED: {len(self.violations_detected)}")
            for i, violation in enumerate(self.violations_detected, 1):
                print(f"  {i}. {violation}")
            
            # Save violations to metrics for reporting
            self.record_metric("total_violations", len(self.violations_detected))
            self.record_metric("violations_list", self.violations_detected)
        else:
            print("\n✅ No type safety violations detected (unexpected - tests designed to fail)")
            self.record_metric("total_violations", 0)
        
        # Log test completion status
        test_metrics = self.get_all_metrics()
        print(f"\n📊 Test Metrics: {test_metrics}")


class TestUserContextTypeSafetyIntegration(SSotBaseTestCase):
    """
    CRITICAL INTEGRATION TESTS: Multi-component type safety violations
    
    These integration tests validate type safety across components working together.
    """
    
    def test_end_to_end_string_id_propagation_violation(self):
        """
        CRITICAL FAILING TEST: String IDs should not propagate through the system
        
        EXPECTED RESULT: FAIL - String IDs propagate without type conversion
        BUSINESS RISK: String ID propagation enables system-wide context mixing
        """
        print("🚨 TESTING: End-to-end string ID propagation")
        
        propagation_violations = []
        
        # Test the full flow: Dependencies → Context → Processing
        string_user_id = "e2e_test_user"       # VIOLATION: should be UserID
        string_request_id = "e2e_test_request" # VIOLATION: should be RequestID
        string_thread_id = "e2e_test_thread"   # VIOLATION: should be ThreadID
        
        try:
            # Step 1: Create context with string IDs (should fail with proper types)
            context = UserDataContext(
                user_id=string_user_id,
                request_id=string_request_id,
                thread_id=string_thread_id
            )
            
            # If context creation succeeded, we have a propagation violation
            violation = (
                "E2E propagation violation: UserDataContext accepted string IDs, "
                "allowing propagation through entire system"
            )
            propagation_violations.append(violation)
            print(f"❌ {violation}")
            
            # Step 2: Test if string IDs are stored internally without conversion
            if hasattr(context, 'user_id') and isinstance(context.user_id, str):
                violation = f"Context stores user_id as str internally: {type(context.user_id)}"
                propagation_violations.append(violation)
                print(f"❌ {violation}")
            
            if hasattr(context, 'request_id') and isinstance(context.request_id, str):
                violation = f"Context stores request_id as str internally: {type(context.request_id)}"
                propagation_violations.append(violation)
                print(f"❌ {violation}")
                
            if hasattr(context, 'thread_id') and isinstance(context.thread_id, str):
                violation = f"Context stores thread_id as str internally: {type(context.thread_id)}"
                propagation_violations.append(violation)
                print(f"❌ {violation}")
        
        except TypeError as e:
            # If we get TypeError, type safety is working (good)
            print(f"✅ Type safety blocked string ID propagation: {e}")
        except Exception as e:
            violation = f"Unexpected error in E2E test: {e}"
            propagation_violations.append(violation)
            print(f"⚠️ {violation}")
        
        # Record metrics
        self.record_metric("e2e_propagation_violations", len(propagation_violations))
        
        # FAIL if propagation violations were found
        if propagation_violations:
            self.violations_detected.extend(propagation_violations)
            pytest.fail(
                f"CRITICAL E2E PROPAGATION VIOLATIONS: {len(propagation_violations)} violations "
                f"found. String IDs propagate through system without type safety checks: "
                f"{propagation_violations}"
            )
        
        print("✅ E2E type safety appears intact")


# Mark these as critical tests that must be run
# Custom markers for this test file
critical_type_safety = pytest.mark.critical_type_safety
user_context_violations = pytest.mark.user_context_violations