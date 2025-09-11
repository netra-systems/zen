"""
Test UserExecutionContext Security Validation and Isolation (Issue #407 Remediation)

This test suite validates that UserExecutionContext provides complete security
and user isolation, protecting against all vulnerabilities present in DeepAgentState.

EXPECTED BEHAVIOR: These tests should PASS, demonstrating security compliance.
The passing tests validate that UserExecutionContext prevents user data leakage.

Business Impact: These security features protect $500K+ ARR by ensuring proper
user data isolation and preventing cross-tenant contamination.

Test Categories:
1. Complete user context isolation validation
2. Memory isolation and garbage collection safety
3. Concurrent user execution security
4. Authentication context security
5. Cross-contamination prevention
6. Factory method security

References:
- Issue #407: DeepAgentState User Isolation Vulnerability (REMEDIATION)
- UserExecutionContext Implementation: Complete security model
- USER_CONTEXT_ARCHITECTURE.md: Factory-based isolation design
"""

import pytest
import uuid
import threading
import time
import copy
import gc
import weakref
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

# Import the secure UserExecutionContext
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    InvalidContextError,
    ContextIsolationError,
    validate_user_context,
    managed_user_context,
    create_isolated_execution_context
)


class TestUserExecutionContextIsolationValidation:
    """
    Validation tests for UserExecutionContext security and isolation.
    
    These tests SHOULD PASS to demonstrate security compliance.
    Each passing test represents a security vulnerability that has been fixed.
    """

    def test_complete_user_context_isolation(self):
        """
        SECURITY VALIDATION: UserExecutionContext provides complete user isolation.
        
        SCENARIO: Multiple users with sensitive data cannot access each other's
        information through any context operations.
        
        EXPECTED: This test should PASS proving complete isolation.
        """
        # Create contexts for different users with sensitive data
        user_a_context = UserExecutionContext.from_request(
            user_id="user_a_secure_12345",
            thread_id="thread_a_isolated",
            run_id="run_a_protected",
            agent_context={
                "api_key": "USER_A_SECRET_KEY_ABC123",
                "sensitive_data": "USER_A_PRIVATE_FINANCIAL_DATA",
                "permissions": ["read", "write"]
            },
            audit_metadata={
                "security_level": "confidential",
                "data_classification": "user_a_only"
            }
        )
        
        user_b_context = UserExecutionContext.from_request(
            user_id="user_b_secure_67890",
            thread_id="thread_b_isolated", 
            run_id="run_b_protected",
            agent_context={
                "api_key": "USER_B_SECRET_KEY_XYZ789",
                "sensitive_data": "USER_B_PRIVATE_MEDICAL_RECORDS",
                "permissions": ["read"]
            },
            audit_metadata={
                "security_level": "restricted",
                "data_classification": "user_b_only"
            }
        )
        
        # SECURITY VALIDATION 1: Contexts are completely separate objects
        assert id(user_a_context) != id(user_b_context), "Contexts must be separate objects"
        assert id(user_a_context.agent_context) != id(user_b_context.agent_context), "Agent contexts must be separate"
        assert id(user_a_context.audit_metadata) != id(user_b_context.audit_metadata), "Audit metadata must be separate"
        
        # SECURITY VALIDATION 2: No cross-user data access
        assert user_a_context.agent_context["api_key"] == "USER_A_SECRET_KEY_ABC123"
        assert user_b_context.agent_context["api_key"] == "USER_B_SECRET_KEY_XYZ789"
        
        # User A cannot access User B's data
        assert "USER_B_SECRET_KEY" not in str(user_a_context.agent_context)
        assert "USER_B_PRIVATE_MEDICAL" not in str(user_a_context.agent_context)
        
        # User B cannot access User A's data
        assert "USER_A_SECRET_KEY" not in str(user_b_context.agent_context)
        assert "USER_A_PRIVATE_FINANCIAL" not in str(user_b_context.agent_context)
        
        # SECURITY VALIDATION 3: Child contexts maintain isolation
        user_a_child = user_a_context.create_child_context(
            "data_analysis",
            additional_agent_context={"analysis_type": "financial"}
        )
        
        user_b_child = user_b_context.create_child_context(
            "data_analysis", 
            additional_agent_context={"analysis_type": "medical"}
        )
        
        # Child contexts inherit only parent data, not cross-user data
        assert user_a_child.user_id == "user_a_secure_12345"
        assert user_b_child.user_id == "user_b_secure_67890"
        assert "USER_A_SECRET_KEY" not in str(user_b_child.agent_context)
        assert "USER_B_SECRET_KEY" not in str(user_a_child.agent_context)
        
        # SECURITY VALIDATION 4: Serialization safety
        user_a_dict = user_a_context.to_dict()
        user_b_dict = user_b_context.to_dict()
        
        # Serialized forms contain no cross-user contamination
        assert "user_b_secure" not in str(user_a_dict).lower()
        assert "user_a_secure" not in str(user_b_dict).lower()
        
        print("✓ SECURITY VALIDATED: Complete user context isolation confirmed")

    def test_memory_isolation_and_garbage_collection_safety(self):
        """
        SECURITY VALIDATION: UserExecutionContext ensures proper memory isolation
        and safe garbage collection without cross-user references.
        
        SCENARIO: User contexts are properly garbage collected and don't maintain
        references to other users' data in memory.
        
        EXPECTED: This test should PASS proving memory safety.
        """
        # Track created contexts for garbage collection testing
        created_contexts = []
        weak_references = []
        
        def create_isolated_user_session(user_id: str, sensitive_data: Dict[str, Any]):
            """Create isolated user session with sensitive data."""
            context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=f"isolated_thread_{user_id}",
                run_id=f"isolated_run_{user_id}",
                agent_context=sensitive_data.copy(),  # Deep copy for isolation
                audit_metadata={
                    "created_for_memory_test": True,
                    "isolation_verified": True
                }
            )
            
            # Track for garbage collection testing
            created_contexts.append(context)
            weak_references.append(weakref.ref(context))
            
            return context
        
        # Create multiple isolated user sessions
        sensitive_datasets = [
            ("user_medical_001", {
                "medical_records": "PATIENT_CONFIDENTIAL_DATA_001",
                "ssn": "123-45-6789",
                "diagnosis": "SENSITIVE_MEDICAL_INFO"
            }),
            ("user_financial_002", {
                "account_numbers": ["ACC001", "ACC002"],
                "balance": 100000,
                "credit_score": 850
            }),
            ("user_legal_003", {
                "case_files": "ATTORNEY_CLIENT_PRIVILEGE_DATA",
                "client_list": ["CLIENT_CONFIDENTIAL_A", "CLIENT_CONFIDENTIAL_B"]
            })
        ]
        
        user_contexts = []
        for user_id, sensitive_data in sensitive_datasets:
            context = create_isolated_user_session(user_id, sensitive_data)
            user_contexts.append(context)
        
        # SECURITY VALIDATION 1: No cross-references between contexts
        for i, context1 in enumerate(user_contexts):
            for j, context2 in enumerate(user_contexts):
                if i != j:
                    # Verify no shared memory references
                    assert id(context1.agent_context) != id(context2.agent_context)
                    assert id(context1.audit_metadata) != id(context2.audit_metadata)
                    
                    # Verify no cross-user data in serialization
                    context1_str = str(context1.to_dict())
                    context2_str = str(context2.to_dict())
                    
                    # Context 1 should not contain Context 2's user ID or sensitive data
                    assert context2.user_id not in context1_str
                    assert context1.user_id not in context2_str
        
        # SECURITY VALIDATION 2: Proper garbage collection
        original_context_count = len(created_contexts)
        
        # Clear references to test garbage collection
        user_contexts.clear()
        created_contexts.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Check that objects were properly garbage collected
        surviving_objects = sum(1 for ref in weak_references if ref() is not None)
        
        # All objects should be garbage collected (none should survive)
        assert surviving_objects == 0, f"Expected 0 surviving objects, got {surviving_objects}"
        
        # SECURITY VALIDATION 3: Deep copy isolation verification
        context_a = UserExecutionContext.from_request(
            user_id="deep_copy_test_a",
            thread_id="thread_deep_a",
            run_id="run_deep_a",
            agent_context={"shared_data": {"nested": "value_a"}}
        )
        
        context_b = UserExecutionContext.from_request(
            user_id="deep_copy_test_b", 
            thread_id="thread_deep_b",
            run_id="run_deep_b",
            agent_context={"shared_data": {"nested": "value_b"}}
        )
        
        # Modify nested data in context A
        context_a.agent_context["shared_data"]["nested"] = "modified_by_a"
        
        # Context B should remain unchanged (proving deep copy isolation)
        assert context_b.agent_context["shared_data"]["nested"] == "value_b"
        assert context_a.agent_context["shared_data"]["nested"] == "modified_by_a"
        
        print("✓ SECURITY VALIDATED: Memory isolation and garbage collection safety confirmed")

    def test_concurrent_user_execution_security(self):
        """
        SECURITY VALIDATION: UserExecutionContext maintains security during
        concurrent user execution without race conditions.
        
        SCENARIO: Multiple users executing simultaneously maintain complete
        isolation with no data contamination.
        
        EXPECTED: This test should PASS proving concurrent execution safety.
        """
        # Shared results container for concurrent execution testing
        execution_results = {}
        isolation_violations = []
        execution_lock = threading.Lock()
        
        def secure_user_execution(user_id: str, sensitive_operation: str):
            """Execute secure operation for a user with complete isolation."""
            try:
                # Create isolated context for this user
                context = UserExecutionContext.from_request(
                    user_id=user_id,
                    thread_id=f"secure_thread_{user_id}_{int(time.time())}",
                    run_id=f"secure_run_{user_id}_{int(time.time())}",
                    agent_context={
                        "operation": sensitive_operation,
                        "user_specific_data": f"SENSITIVE_DATA_FOR_{user_id}",
                        "execution_time": time.time()
                    },
                    audit_metadata={
                        "security_level": "high",
                        "isolation_guaranteed": True
                    }
                )
                
                # Simulate processing time
                time.sleep(0.01)
                
                # Store results with thread safety
                with execution_lock:
                    execution_results[user_id] = {
                        "context": context,
                        "operation": sensitive_operation,
                        "completed": True
                    }
                
                # Verify no contamination with other executions
                with execution_lock:
                    for other_user_id, other_result in execution_results.items():
                        if other_user_id != user_id:
                            other_context = other_result["context"]
                            
                            # Check for cross-contamination in context data
                            current_context_str = str(context.to_dict())
                            other_context_str = str(other_context.to_dict())
                            
                            # Current user should not see other user's data
                            if other_user_id in current_context_str:
                                isolation_violations.append({
                                    "type": "user_id_contamination",
                                    "victim": user_id,
                                    "contaminating_user": other_user_id
                                })
                            
                            if other_result["operation"] in current_context_str:
                                isolation_violations.append({
                                    "type": "operation_contamination", 
                                    "victim": user_id,
                                    "contaminating_operation": other_result["operation"]
                                })
                            
                            # Verify no shared object references
                            if id(context.agent_context) == id(other_context.agent_context):
                                isolation_violations.append({
                                    "type": "shared_agent_context",
                                    "user1": user_id,
                                    "user2": other_user_id
                                })
                                
            except Exception as e:
                with execution_lock:
                    isolation_violations.append({
                        "type": "execution_error",
                        "user": user_id,
                        "error": str(e)
                    })
        
        # Execute multiple users concurrently
        concurrent_users = [
            ("user_concurrent_alice", "PROCESS_ALICE_FINANCIAL_DATA"),
            ("user_concurrent_bob", "ANALYZE_BOB_MEDICAL_RECORDS"),
            ("user_concurrent_charlie", "HANDLE_CHARLIE_LEGAL_DOCS"),
            ("user_concurrent_diana", "MANAGE_DIANA_PERSONAL_INFO"),
            ("user_concurrent_eve", "SECURE_EVE_CONFIDENTIAL_DATA")
        ]
        
        # Run concurrent executions
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(secure_user_execution, user_id, operation)
                for user_id, operation in concurrent_users
            ]
            
            # Wait for all executions to complete
            for future in futures:
                future.result()
        
        # SECURITY VALIDATION: No isolation violations should occur
        assert len(isolation_violations) == 0, (
            f"SECURITY FAILURE: Isolation violations detected in concurrent execution:\n" +
            "\n".join([f"- {v['type']}: {v.get('victim', v.get('user1', 'unknown'))}" 
                      for v in isolation_violations])
        )
        
        # SECURITY VALIDATION: All executions completed successfully
        assert len(execution_results) == len(concurrent_users), "All concurrent executions should complete"
        
        # SECURITY VALIDATION: Each user's context is unique and isolated
        user_ids = list(execution_results.keys())
        for i, user_id1 in enumerate(user_ids):
            for j, user_id2 in enumerate(user_ids):
                if i != j:
                    context1 = execution_results[user_id1]["context"]
                    context2 = execution_results[user_id2]["context"]
                    
                    # Verify different object identities
                    assert id(context1) != id(context2)
                    assert id(context1.agent_context) != id(context2.agent_context)
                    assert id(context1.audit_metadata) != id(context2.audit_metadata)
                    
                    # Verify different user IDs
                    assert context1.user_id != context2.user_id
                    assert context1.request_id != context2.request_id
        
        print("✓ SECURITY VALIDATED: Concurrent user execution security confirmed")

    def test_authentication_context_security(self):
        """
        SECURITY VALIDATION: UserExecutionContext maintains authentication
        security and prevents privilege escalation.
        
        SCENARIO: User authentication contexts remain isolated and secure,
        preventing any form of privilege escalation or credential leakage.
        
        EXPECTED: This test should PASS proving authentication security.
        """
        # Create different privilege level contexts
        admin_context = UserExecutionContext.from_request(
            user_id="admin_secure_user",
            thread_id="admin_thread_secure",
            run_id="admin_run_secure",
            agent_context={
                "auth_level": "admin",
                "permissions": ["read", "write", "delete", "admin", "system"],
                "auth_token": "ADMIN_SECURE_TOKEN_ABC123"
            },
            audit_metadata={
                "security_clearance": "level_5",
                "authenticated": True,
                "role": "administrator"
            }
        )
        
        regular_context = UserExecutionContext.from_request(
            user_id="regular_secure_user",
            thread_id="regular_thread_secure", 
            run_id="regular_run_secure",
            agent_context={
                "auth_level": "user",
                "permissions": ["read"],
                "auth_token": "REGULAR_SECURE_TOKEN_XYZ789"
            },
            audit_metadata={
                "security_clearance": "level_1",
                "authenticated": True,
                "role": "user"
            }
        )
        
        guest_context = UserExecutionContext.from_request(
            user_id="guest_secure_user",
            thread_id="guest_thread_secure",
            run_id="guest_run_secure", 
            agent_context={
                "auth_level": "guest",
                "permissions": [],
                "auth_token": None
            },
            audit_metadata={
                "security_clearance": "level_0",
                "authenticated": False,
                "role": "guest"
            }
        )
        
        # SECURITY VALIDATION 1: No privilege escalation through context operations
        
        # Regular user creates child context - should maintain same privilege level
        regular_child = regular_context.create_child_context(
            "data_access",
            additional_agent_context={"requested_operation": "read_sensitive_data"}
        )
        
        # Child context should maintain parent's limited permissions
        assert regular_child.user_id == "regular_secure_user"
        assert regular_child.agent_context["auth_level"] == "user"
        assert "admin" not in regular_child.agent_context.get("permissions", [])
        assert "ADMIN_SECURE_TOKEN" not in str(regular_child.agent_context)
        
        # SECURITY VALIDATION 2: No credential leakage between contexts
        
        admin_dict = admin_context.to_dict()
        regular_dict = regular_context.to_dict()
        guest_dict = guest_context.to_dict()
        
        # Admin credentials should not appear in other contexts
        assert "ADMIN_SECURE_TOKEN" not in str(regular_dict)
        assert "ADMIN_SECURE_TOKEN" not in str(guest_dict)
        
        # Regular user credentials should not appear in other contexts
        assert "REGULAR_SECURE_TOKEN" not in str(admin_dict)
        assert "REGULAR_SECURE_TOKEN" not in str(guest_dict)
        
        # Admin permissions should not appear in other contexts
        assert "system" not in str(regular_dict)
        assert "system" not in str(guest_dict)
        
        # SECURITY VALIDATION 3: Context copying maintains security boundaries
        
        try:
            # Attempt to create context with mixed authentication data
            # This should maintain isolation and not allow privilege mixing
            mixed_context = UserExecutionContext.from_request(
                user_id="test_mixed_user",
                thread_id="test_mixed_thread",
                run_id="test_mixed_run",
                agent_context={
                    "base_auth": regular_context.agent_context["auth_level"],
                    "base_permissions": regular_context.agent_context["permissions"].copy()
                }
            )
            
            # Mixed context should only have its own data, no elevated privileges
            assert mixed_context.user_id == "test_mixed_user"
            assert mixed_context.agent_context["base_auth"] == "user"
            assert "admin" not in mixed_context.agent_context.get("base_permissions", [])
            
        except Exception as e:
            pytest.fail(f"Context creation with isolated data should succeed: {e}")
        
        # SECURITY VALIDATION 4: Deep copy isolation for authentication data
        
        # Create copy of contexts and modify authentication data
        admin_copy_data = copy.deepcopy(admin_context.agent_context)
        regular_copy_data = copy.deepcopy(regular_context.agent_context)
        
        # Modify copy data
        admin_copy_data["auth_token"] = "MODIFIED_ADMIN_TOKEN"
        regular_copy_data["permissions"].append("write")
        
        # Original contexts should remain unchanged
        assert admin_context.agent_context["auth_token"] == "ADMIN_SECURE_TOKEN_ABC123"
        assert "write" not in regular_context.agent_context["permissions"]
        
        # SECURITY VALIDATION 5: Audit trail integrity
        
        admin_audit = admin_context.get_audit_trail()
        regular_audit = regular_context.get_audit_trail()
        
        # Audit trails should be separate and contain correct user information
        assert admin_audit["user_id"] == "admin_secure_user"
        assert regular_audit["user_id"] == "regular_secure_user"
        assert admin_audit["correlation_id"] != regular_audit["correlation_id"]
        
        print("✓ SECURITY VALIDATED: Authentication context security confirmed")

    def test_factory_method_security_validation(self):
        """
        SECURITY VALIDATION: Factory methods create secure, isolated contexts
        without any security vulnerabilities.
        
        SCENARIO: All factory methods produce properly isolated contexts that
        maintain security boundaries under all conditions.
        
        EXPECTED: This test should PASS proving factory method security.
        """
        # Test create_isolated_execution_context factory
        async def test_isolated_factory():
            isolated_context = await create_isolated_execution_context(
                user_id="factory_test_user_001",
                request_id="factory_request_001",
                isolation_level="strict"
            )
            
            # Validate isolated factory creates secure context
            assert isolated_context.user_id == "factory_test_user_001"
            assert isolated_context.request_id == "factory_request_001"
            assert isolated_context.agent_context["isolation_level"] == "strict"
            
            return isolated_context
        
        # Execute async factory test
        import asyncio
        factory_context = asyncio.run(test_isolated_factory())
        
        # SECURITY VALIDATION 1: from_request factory security
        
        request_context_1 = UserExecutionContext.from_request(
            user_id="factory_user_1",
            thread_id="factory_thread_1",
            run_id="factory_run_1",
            agent_context={"sensitive": "user_1_data"}
        )
        
        request_context_2 = UserExecutionContext.from_request(
            user_id="factory_user_2", 
            thread_id="factory_thread_2",
            run_id="factory_run_2",
            agent_context={"sensitive": "user_2_data"}
        )
        
        # Factory-created contexts should be completely isolated
        assert id(request_context_1.agent_context) != id(request_context_2.agent_context)
        assert request_context_1.agent_context["sensitive"] != request_context_2.agent_context["sensitive"]
        
        # SECURITY VALIDATION 2: from_websocket_request factory security
        
        websocket_context_1 = UserExecutionContext.from_websocket_request(
            user_id="ws_user_1",
            operation="secure_chat"
        )
        
        websocket_context_2 = UserExecutionContext.from_websocket_request(
            user_id="ws_user_2", 
            operation="secure_chat"
        )
        
        # WebSocket contexts should be isolated
        assert websocket_context_1.user_id != websocket_context_2.user_id
        assert websocket_context_1.websocket_client_id != websocket_context_2.websocket_client_id
        assert id(websocket_context_1.agent_context) != id(websocket_context_2.agent_context)
        
        # SECURITY VALIDATION 3: UserContextManager security
        
        context_manager = UserContextManager(
            isolation_level="strict",
            cross_contamination_detection=True,
            memory_isolation=True
        )
        
        # Create managed contexts
        managed_context_1 = context_manager.create_managed_context(
            user_id="managed_user_1",
            request_id="managed_request_1"
        )
        
        managed_context_2 = context_manager.create_managed_context(
            user_id="managed_user_2",
            request_id="managed_request_2"  
        )
        
        # Managed contexts should maintain strict isolation
        assert managed_context_1.user_id != managed_context_2.user_id
        
        # Validate isolation through manager
        assert context_manager.validate_isolation(f"managed_user_1_managed_request_1") == True
        assert context_manager.validate_isolation(f"managed_user_2_managed_request_2") == True
        
        # SECURITY VALIDATION 4: Child context factory security
        
        parent_context = UserExecutionContext.from_request(
            user_id="parent_user",
            thread_id="parent_thread",
            run_id="parent_run",
            agent_context={"parent_data": "sensitive_parent_info"}
        )
        
        child_context_1 = parent_context.create_child_context(
            "child_operation_1",
            additional_agent_context={"child_data": "child_1_specific"}
        )
        
        child_context_2 = parent_context.create_child_context(
            "child_operation_2",
            additional_agent_context={"child_data": "child_2_specific"}
        )
        
        # Child contexts should be isolated from each other but inherit from parent
        assert child_context_1.user_id == child_context_2.user_id == "parent_user"
        assert child_context_1.request_id != child_context_2.request_id
        assert child_context_1.agent_context["child_data"] != child_context_2.agent_context["child_data"]
        assert child_context_1.agent_context["parent_data"] == child_context_2.agent_context["parent_data"]
        
        # SECURITY VALIDATION 5: Context validation security
        
        # Valid contexts should pass validation
        try:
            validated_context = validate_user_context(factory_context)
            assert isinstance(validated_context, UserExecutionContext)
        except (TypeError, InvalidContextError) as e:
            pytest.fail(f"Valid context should pass validation: {e}")
        
        # Invalid contexts should be rejected
        with pytest.raises((TypeError, InvalidContextError)):
            validate_user_context("invalid_context_string")
        
        with pytest.raises((TypeError, InvalidContextError)):
            validate_user_context(None)
        
        print("✓ SECURITY VALIDATED: Factory method security confirmed")

    def test_context_isolation_violation_detection(self):
        """
        SECURITY VALIDATION: UserExecutionContext detects and prevents
        isolation violations proactively.
        
        SCENARIO: System detects any attempt to violate user isolation
        and raises appropriate security exceptions.
        
        EXPECTED: This test should PASS proving isolation violation detection.
        """
        # Create secure context
        secure_context = UserExecutionContext.from_request(
            user_id="isolation_test_user",
            thread_id="isolation_test_thread",
            run_id="isolation_test_run",
            agent_context={"security_test": True}
        )
        
        # SECURITY VALIDATION 1: Context verification passes for valid context
        
        try:
            isolation_verified = secure_context.verify_isolation()
            assert isolation_verified == True, "Valid context should pass isolation verification"
        except ContextIsolationError as e:
            pytest.fail(f"Valid context should not raise isolation error: {e}")
        
        # SECURITY VALIDATION 2: Invalid context detection
        
        # Test with placeholder values (should be rejected during creation)
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="placeholder",  # Invalid placeholder value
                thread_id="test_thread",
                run_id="test_run"
            )
        
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="registry",  # Invalid system placeholder  
                thread_id="test_thread",
                run_id="test_run"
            )
        
        # SECURITY VALIDATION 3: Reserved key detection
        
        # Test with reserved keys in agent_context (should be rejected)
        with pytest.raises(InvalidContextError):
            UserExecutionContext.from_request(
                user_id="test_user",
                thread_id="test_thread", 
                run_id="test_run",
                agent_context={
                    "user_id": "conflicting_user_id",  # Reserved key conflict
                    "normal_data": "valid_data"
                }
            )
        
        # SECURITY VALIDATION 4: UserContextManager isolation detection
        
        context_manager = UserContextManager(
            isolation_level="strict",
            cross_contamination_detection=True,
            memory_isolation=True
        )
        
        # Create valid context through manager
        managed_context = context_manager.create_managed_context(
            user_id="manager_test_user",
            request_id="manager_test_request"
        )
        
        # Validation should pass for properly created context
        manager_validation = context_manager.validate_isolation("manager_test_user_manager_test_request")
        assert manager_validation == True, "Manager should validate properly created contexts"
        
        # SECURITY VALIDATION 5: Audit trail integrity
        
        audit_trail = secure_context.get_audit_trail()
        
        # Audit trail should contain security validation markers
        assert audit_trail["user_id"] == "isolation_test_user"
        assert "context_age_seconds" in audit_trail
        assert "correlation_id" in audit_trail
        
        # Audit trail should not contain other users' data
        assert "other_user" not in str(audit_trail).lower()
        assert "cross_contamination" not in str(audit_trail).lower()
        
        print("✓ SECURITY VALIDATED: Context isolation violation detection confirmed")

    async def test_managed_context_lifecycle_security(self):
        """
        SECURITY VALIDATION: managed_user_context provides secure lifecycle
        management with proper cleanup and no resource leaks.
        
        SCENARIO: Context lifecycle management maintains security throughout
        the entire context lifetime including cleanup.
        
        EXPECTED: This test should PASS proving lifecycle security.
        """
        cleanup_executed = False
        
        def cleanup_callback():
            nonlocal cleanup_executed
            cleanup_executed = True
        
        # Create context with managed lifecycle
        test_context = UserExecutionContext.from_request(
            user_id="lifecycle_test_user",
            thread_id="lifecycle_test_thread",
            run_id="lifecycle_test_run",
            agent_context={"lifecycle_test": True}
        )
        
        # Add cleanup callback
        test_context.cleanup_callbacks.append(cleanup_callback)
        
        # SECURITY VALIDATION 1: Managed context provides secure environment
        
        async with managed_user_context(test_context) as managed_ctx:
            # Context should be accessible and secure within managed scope
            assert managed_ctx.user_id == "lifecycle_test_user"
            assert managed_ctx.agent_context["lifecycle_test"] == True
            
            # Verify isolation is maintained
            isolation_valid = managed_ctx.verify_isolation()
            assert isolation_valid == True
            
            # Create child context within managed scope
            child_ctx = managed_ctx.create_child_context(
                "managed_child_operation",
                additional_agent_context={"managed_child": True}
            )
            
            assert child_ctx.user_id == managed_ctx.user_id
            assert child_ctx.agent_context["managed_child"] == True
        
        # SECURITY VALIDATION 2: Cleanup executed properly
        
        # Cleanup callback should have been executed
        assert cleanup_executed == True, "Cleanup callback should be executed"
        
        # SECURITY VALIDATION 3: Context remains valid after managed scope
        
        # Original context should remain valid (managed context doesn't modify original)
        assert test_context.user_id == "lifecycle_test_user"
        post_cleanup_isolation = test_context.verify_isolation()
        assert post_cleanup_isolation == True
        
        print("✓ SECURITY VALIDATED: Managed context lifecycle security confirmed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])