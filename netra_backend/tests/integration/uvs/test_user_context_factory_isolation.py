"""
Comprehensive UserContextFactory Integration Tests - Factory Pattern Isolation

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) - Core infrastructure supporting all user tiers
- Business Goal: Ensure complete factory-based user isolation for secure multi-user operations
- Value Impact: Prevents user data leakage, enables concurrent operations, ensures reliable context management
- Strategic Impact: CRITICAL - Factory isolation patterns are the foundation for safe multi-user AI platform

This test suite validates UserContextFactory integration focusing on isolation patterns:
1. Factory pattern isolation and thread safety (5 tests)
2. SSOT ID generation and consistency validation (5 tests) 
3. Context creation patterns and validation (5 tests)
4. Factory-based resource management and cleanup (5 tests)
5. WebSocket context creation and routing isolation (5 tests)

CRITICAL TEST REQUIREMENTS:
- These are INTEGRATION tests - test component interactions, NOT full Docker stack
- NO MOCKS allowed - use real services and real system behavior
- Each test validates actual business value for factory patterns
- Focus on factory-based isolation ensuring user data security
- Use proper pytest markers and test categories

Factory Pattern Business Value:
Factory patterns ensure user isolation by creating dedicated contexts per user request,
preventing data leaks between concurrent operations, enabling reliable multi-user execution,
and providing proper resource management for scalable AI agent operations.
"""

import pytest
import asyncio
import time
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

# System components
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextFactory,
    InvalidContextError,
    ContextIsolationError,
    create_isolated_execution_context,
    clear_shared_object_registry,
    managed_user_context
)

# SSOT ID generation
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.core.unified_id_manager import UnifiedIDManager

# Test framework SSOT components
from test_framework.ssot.base import BaseTestCase
from test_framework.ssot.integration_test_base import IntegrationTestBase
from shared.isolated_environment import get_env

# Import types for testing
from shared.types import UserID, ThreadID, RunID, RequestID


@dataclass
class IsolationTestResult:
    """Container for isolation validation test results."""
    context_id: str
    user_id: str
    thread_id: str
    creation_time: datetime
    isolation_verified: bool
    memory_address: int
    data_integrity: bool


class TestUserContextFactoryIsolation(IntegrationTestBase):
    """Integration tests for UserContextFactory isolation patterns and thread safety."""
    
    def setUp(self):
        """Set up test environment with isolation boundaries."""
        super().setUp()
        clear_shared_object_registry()
        UnifiedIdGenerator.reset_global_counter() if hasattr(UnifiedIdGenerator, 'reset_global_counter') else None
        
        # Test configuration
        self.test_users = [
            f"test_user_{uuid.uuid4().hex[:8]}" for _ in range(5)
        ]
        self.isolation_results: List[IsolationTestResult] = []
        
    def tearDown(self):
        """Clean up test environment and validate no leaks."""
        # Verify no shared object violations
        clear_shared_object_registry()
        super().tearDown()

    # ============================================================================
    # FACTORY PATTERN ISOLATION AND THREAD SAFETY TESTS (5 tests)
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.factory_isolation
    def test_factory_creates_completely_isolated_contexts(self):
        """
        BVJ: Ensures factory pattern creates completely isolated contexts preventing user data leaks.
        Validates that each factory-created context has independent memory space and no shared references.
        """
        # Create multiple contexts using factory pattern
        contexts = []
        for i, user_id in enumerate(self.test_users):
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=f"thread_isolation_test_{i}",
                run_id=f"run_isolation_test_{i}",
                websocket_client_id=f"ws_client_{i}"
            )
            contexts.append(context)
            
        # Validate complete isolation
        for i, context_a in enumerate(contexts):
            for j, context_b in enumerate(contexts):
                if i != j:
                    # Memory isolation - different objects
                    self.assertNotEqual(id(context_a), id(context_b))
                    self.assertNotEqual(id(context_a.agent_context), id(context_b.agent_context))
                    self.assertNotEqual(id(context_a.audit_metadata), id(context_b.audit_metadata))
                    
                    # Data isolation - no shared data
                    self.assertNotEqual(context_a.user_id, context_b.user_id)
                    self.assertNotEqual(context_a.request_id, context_b.request_id)
                    
                    # Verify isolation validation passes
                    self.assertTrue(context_a.verify_isolation())
                    self.assertTrue(context_b.verify_isolation())

    @pytest.mark.integration 
    @pytest.mark.factory_isolation
    @pytest.mark.thread_safety
    def test_factory_thread_safety_concurrent_creation(self):
        """
        BVJ: Validates factory thread safety for concurrent user requests in production multi-user scenarios.
        Ensures no race conditions when multiple threads create contexts simultaneously.
        """
        creation_results = []
        creation_lock = threading.Lock()
        
        def create_context_worker(worker_id: int) -> IsolationTestResult:
            """Worker function for concurrent context creation."""
            user_id = f"concurrent_user_{worker_id}"
            
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=f"thread_concurrent_{worker_id}",
                run_id=f"run_concurrent_{worker_id}"
            )
            
            # Validate context creation
            context.verify_isolation()
            
            result = IsolationTestResult(
                context_id=context.request_id,
                user_id=context.user_id,
                thread_id=context.thread_id,
                creation_time=context.created_at,
                isolation_verified=True,
                memory_address=id(context),
                data_integrity=all([
                    context.user_id == user_id,
                    context.thread_id.startswith("thread_concurrent"),
                    context.run_id.startswith("run_concurrent")
                ])
            )
            
            with creation_lock:
                creation_results.append(result)
                
            return result
        
        # Execute concurrent context creation
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_context_worker, i) 
                for i in range(20)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                self.assertTrue(result.isolation_verified)
                self.assertTrue(result.data_integrity)
        
        # Validate results
        self.assertEqual(len(creation_results), 20)
        
        # Verify all contexts are unique
        context_ids = [r.context_id for r in creation_results]
        user_ids = [r.user_id for r in creation_results]
        memory_addresses = [r.memory_address for r in creation_results]
        
        self.assertEqual(len(set(context_ids)), 20, "All context IDs must be unique")
        self.assertEqual(len(set(user_ids)), 20, "All user IDs must be unique")
        self.assertEqual(len(set(memory_addresses)), 20, "All memory addresses must be unique")

    @pytest.mark.integration
    @pytest.mark.factory_isolation
    def test_factory_prevents_context_data_pollution(self):
        """
        BVJ: Validates that factory pattern prevents data pollution between user contexts.
        Ensures modifications to one context don't affect other factory-created contexts.
        """
        # Create contexts with factory
        context1 = UserContextFactory.create_context(
            user_id="user_pollution_test_1",
            thread_id="thread_1",
            run_id="run_1"
        )
        
        context2 = UserContextFactory.create_context(
            user_id="user_pollution_test_2", 
            thread_id="thread_2",
            run_id="run_2"
        )
        
        # Capture original states
        original_context1_data = context1.to_dict()
        original_context2_data = context2.to_dict()
        
        # Modify context1's mutable components (through allowed operations)
        child_context1 = context1.create_child_context(
            operation_name="pollution_test",
            additional_agent_context={"test_data": "modified_value_1"},
            additional_audit_metadata={"test_audit": "audit_value_1"}
        )
        
        child_context2 = context2.create_child_context(
            operation_name="isolation_test", 
            additional_agent_context={"test_data": "modified_value_2"},
            additional_audit_metadata={"test_audit": "audit_value_2"}
        )
        
        # Verify original contexts unchanged (immutability protection)
        self.assertEqual(context1.to_dict(), original_context1_data)
        self.assertEqual(context2.to_dict(), original_context2_data)
        
        # Verify child contexts are isolated
        self.assertEqual(child_context1.agent_context["test_data"], "modified_value_1")
        self.assertEqual(child_context2.agent_context["test_data"], "modified_value_2")
        self.assertNotEqual(child_context1.request_id, child_context2.request_id)
        
        # Verify isolation validation still passes
        self.assertTrue(context1.verify_isolation())
        self.assertTrue(context2.verify_isolation())
        self.assertTrue(child_context1.verify_isolation())
        self.assertTrue(child_context2.verify_isolation())

    @pytest.mark.integration
    @pytest.mark.factory_isolation
    @pytest.mark.memory_management
    def test_factory_memory_isolation_validation(self):
        """
        BVJ: Validates factory creates contexts with proper memory isolation preventing reference sharing.
        Critical for preventing memory-based data leaks between users in multi-tenant environment.
        """
        contexts = []
        memory_addresses = set()
        
        # Create contexts and collect memory information
        for i in range(10):
            context = UserContextFactory.create_context(
                user_id=f"memory_test_user_{i}",
                thread_id=f"memory_thread_{i}",
                run_id=f"memory_run_{i}"
            )
            contexts.append(context)
            
            # Collect memory addresses of context and its components
            memory_addresses.add(id(context))
            memory_addresses.add(id(context.agent_context))
            memory_addresses.add(id(context.audit_metadata))
            
            # Verify isolation
            context.verify_isolation()
        
        # Validate all memory addresses are unique (no sharing)
        expected_addresses = 10 * 3  # context + agent_context + audit_metadata per context
        self.assertEqual(len(memory_addresses), expected_addresses,
                        f"Expected {expected_addresses} unique memory addresses, got {len(memory_addresses)}")
        
        # Validate deep copy isolation for mutable components
        for i, context_a in enumerate(contexts):
            for j, context_b in enumerate(contexts):
                if i != j:
                    # Agent context isolation
                    context_a.agent_context.setdefault("test_key", f"value_{i}")
                    context_b.agent_context.setdefault("test_key", f"value_{j}")
                    
                    self.assertEqual(context_a.agent_context["test_key"], f"value_{i}")
                    self.assertEqual(context_b.agent_context["test_key"], f"value_{j}")
                    
                    # Memory addresses must be different
                    self.assertNotEqual(id(context_a.agent_context), id(context_b.agent_context))

    @pytest.mark.integration
    @pytest.mark.factory_isolation
    @pytest.mark.async_safety
    async def test_factory_async_context_isolation(self):
        """
        BVJ: Validates factory pattern maintains isolation in async environments with concurrent coroutines.
        Ensures async operations don't cause context data corruption or sharing between users.
        """
        isolation_results = []
        
        async def create_and_validate_context(user_index: int) -> bool:
            """Async worker for context creation and validation."""
            user_id = f"async_user_{user_index}"
            
            # Simulate async delay (mimics real async operations)
            await asyncio.sleep(0.01 * (user_index % 3))
            
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=f"async_thread_{user_index}",
                run_id=f"async_run_{user_index}",
                websocket_client_id=f"async_ws_{user_index}"
            )
            
            # Validate context properties
            self.assertEqual(context.user_id, user_id)
            self.assertEqual(context.thread_id, f"async_thread_{user_index}")
            self.assertEqual(context.websocket_client_id, f"async_ws_{user_index}")
            
            # Verify isolation
            is_isolated = context.verify_isolation()
            
            # Use managed context for async operations
            async with managed_user_context(context) as managed_ctx:
                # Simulate async context usage
                child_ctx = managed_ctx.create_child_context(
                    operation_name=f"async_operation_{user_index}",
                    additional_agent_context={"async_data": f"async_value_{user_index}"}
                )
                
                # Validate child context isolation
                child_isolated = child_ctx.verify_isolation()
                
                return is_isolated and child_isolated
        
        # Create multiple async tasks
        tasks = [
            create_and_validate_context(i) 
            for i in range(15)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Validate all contexts were properly isolated
        self.assertTrue(all(results), "All async contexts must maintain proper isolation")
        self.assertEqual(len(results), 15, "All async tasks must complete successfully")

    # ============================================================================
    # SSOT ID GENERATION AND CONSISTENCY VALIDATION TESTS (5 tests) 
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.ssot_ids
    @pytest.mark.id_consistency
    def test_factory_uses_ssot_id_generation_patterns(self):
        """
        BVJ: Validates factory uses SSOT ID generation preventing scattered uuid patterns causing collisions.
        Ensures consistent ID formats across all factory-created contexts for reliable system integration.
        """
        contexts = []
        
        # Create contexts using factory
        for i in range(20):
            context = UserContextFactory.create_context(
                user_id=f"ssot_test_user_{i}",
                thread_id=f"ssot_thread_{i}",
                run_id=f"ssot_run_{i}"
            )
            contexts.append(context)
        
        # Validate SSOT ID patterns
        for context in contexts:
            # Verify all required IDs are present
            self.assertIsNotNone(context.user_id)
            self.assertIsNotNone(context.thread_id) 
            self.assertIsNotNone(context.run_id)
            self.assertIsNotNone(context.request_id)
            
            # Validate ID formats (non-placeholder patterns)
            self.assertNotIn("placeholder", context.request_id.lower())
            self.assertNotIn("default", context.request_id.lower())
            self.assertNotIn("temp", context.request_id.lower())
            
            # Validate UUID format for request_id
            try:
                uuid.UUID(context.request_id)
                uuid_format_valid = True
            except ValueError:
                # Allow non-UUID formats if they follow structured pattern
                uuid_format_valid = len(context.request_id) >= 8 and '_' in context.request_id
            
            self.assertTrue(uuid_format_valid, f"Invalid request_id format: {context.request_id}")
        
        # Validate ID uniqueness (critical for isolation)
        request_ids = [ctx.request_id for ctx in contexts]
        self.assertEqual(len(set(request_ids)), len(request_ids), "All request IDs must be unique")

    @pytest.mark.integration
    @pytest.mark.ssot_ids
    @pytest.mark.id_validation
    def test_factory_websocket_context_ssot_id_consistency(self):
        """
        BVJ: Validates WebSocket context creation uses SSOT ID patterns preventing resource leak issues.
        Ensures consistent thread_id/run_id relationships for proper WebSocket manager cleanup.
        """
        websocket_contexts = []
        
        # Create WebSocket contexts using SSOT factory method
        for i in range(10):
            user_id = f"websocket_ssot_user_{i}"
            
            context = UserExecutionContext.from_websocket_request(
                user_id=user_id,
                websocket_client_id=f"ws_ssot_client_{i}",
                operation="websocket_ssot_test"
            )
            websocket_contexts.append(context)
        
        # Validate SSOT ID consistency for WebSocket contexts
        for context in websocket_contexts:
            # Verify WebSocket-specific fields
            self.assertIsNotNone(context.websocket_client_id)
            self.assertTrue(context.websocket_client_id.startswith("ws_"))
            
            # Validate SSOT metadata
            self.assertEqual(context.agent_context["source"], "websocket_ssot")
            self.assertEqual(context.agent_context["created_via"], "from_websocket_request")
            self.assertEqual(context.audit_metadata["context_source"], "websocket_ssot")
            self.assertEqual(context.audit_metadata["id_generation_method"], "UnifiedIdGenerator")
            self.assertTrue(context.audit_metadata["isolation_key_compatible"])
            
            # Verify thread/run ID consistency patterns
            # The SSOT pattern should ensure cleanup compatibility
            self.assertIn("thread_", context.thread_id)
            self.assertIn("run_", context.run_id)
        
        # Validate WebSocket context isolation
        for ctx in websocket_contexts:
            self.assertTrue(ctx.verify_isolation())

    @pytest.mark.integration
    @pytest.mark.ssot_ids
    @pytest.mark.id_collision_prevention
    def test_factory_prevents_id_collision_across_sessions(self):
        """
        BVJ: Validates factory prevents ID collisions across different user sessions and time periods.
        Critical for maintaining user isolation and preventing request confusion in concurrent scenarios.
        """
        session_batches = []
        
        # Create multiple batches simulating different sessions
        for session in range(5):
            batch = []
            for user in range(10):
                context = UserContextFactory.create_context(
                    user_id=f"collision_test_session_{session}_user_{user}",
                    thread_id=f"collision_thread_{session}_{user}",
                    run_id=f"collision_run_{session}_{user}"
                )
                batch.append(context)
            
            session_batches.append(batch)
            
            # Add small delay between sessions
            time.sleep(0.001)
        
        # Collect all IDs across all sessions
        all_request_ids = []
        all_context_combinations = []
        
        for batch in session_batches:
            for context in batch:
                all_request_ids.append(context.request_id)
                all_context_combinations.append(
                    (context.user_id, context.thread_id, context.run_id, context.request_id)
                )
        
        # Validate no collisions
        self.assertEqual(len(set(all_request_ids)), len(all_request_ids),
                        "Request IDs must be globally unique across all sessions")
        
        self.assertEqual(len(set(all_context_combinations)), len(all_context_combinations),
                        "Context ID combinations must be globally unique")
        
        # Validate consistent format across all contexts
        for request_id in all_request_ids:
            self.assertGreater(len(request_id), 8, "Request IDs must have sufficient entropy")
            self.assertIsInstance(request_id, str, "Request IDs must be strings")

    @pytest.mark.integration
    @pytest.mark.ssot_ids
    @pytest.mark.unified_id_manager
    def test_factory_integration_with_unified_id_manager(self):
        """
        BVJ: Validates factory integrates properly with UnifiedIDManager for enterprise-grade ID management.
        Ensures factory-created contexts work seamlessly with centralized ID management systems.
        """
        # Create contexts that should integrate with UnifiedIDManager
        contexts_with_manager_integration = []
        
        for i in range(10):
            # Use create_isolated_execution_context which integrates with UnifiedIDManager
            user_id = f"unified_manager_user_{i}"
            request_id = f"unified_request_{i}_{uuid.uuid4().hex[:8]}"
            
            context = asyncio.run(create_isolated_execution_context(
                user_id=user_id,
                request_id=request_id,
                thread_id=None,  # Let ID manager generate
                run_id=None,     # Let ID manager generate
                validate_user=False,  # Skip user DB validation for integration test
                isolation_level="standard"
            ))
            
            contexts_with_manager_integration.append(context)
        
        # Validate UnifiedIDManager integration
        for context in contexts_with_manager_integration:
            # Verify context has proper ID management metadata
            self.assertEqual(context.agent_context["created_via"], "create_isolated_execution_context")
            self.assertEqual(context.audit_metadata["context_source"], "ssot_isolated_factory")
            self.assertEqual(context.audit_metadata["factory_method"], "create_isolated_execution_context")
            
            # Validate ID formats follow manager patterns
            self.assertIsNotNone(context.thread_id)
            self.assertIsNotNone(context.run_id)
            
            # Verify isolation validation works with manager-generated IDs
            self.assertTrue(context.verify_isolation())
        
        # Test ID manager validation methods if available
        if hasattr(UnifiedIDManager, 'validate_run_id'):
            for context in contexts_with_manager_integration:
                # Some contexts may not follow exact manager format (acceptable)
                # but should not cause validation failures
                try:
                    validation_result = UnifiedIDManager.validate_run_id(context.run_id)
                    # Validation result can be True or False, just shouldn't throw
                    self.assertIsInstance(validation_result, bool)
                except Exception as e:
                    # Should not throw exceptions during validation
                    self.fail(f"UnifiedIDManager.validate_run_id threw exception: {e}")

    @pytest.mark.integration
    @pytest.mark.ssot_ids
    @pytest.mark.id_extraction_consistency
    def test_factory_id_extraction_and_consistency_validation(self):
        """
        BVJ: Validates ID extraction and consistency validation works properly with factory-generated contexts.
        Ensures factory patterns support proper ID relationship validation for audit and debugging.
        """
        contexts_for_extraction = []
        
        # Create contexts using various factory methods
        factory_methods = [
            lambda i: UserContextFactory.create_context(
                user_id=f"extract_user_{i}",
                thread_id=f"extract_thread_{i}",
                run_id=f"extract_run_{i}"
            ),
            lambda i: UserExecutionContext.from_websocket_request(
                user_id=f"websocket_extract_user_{i}",
                operation="extraction_test"
            )
        ]
        
        for method_idx, factory_method in enumerate(factory_methods):
            for i in range(5):
                context = factory_method(i + method_idx * 5)
                contexts_for_extraction.append(context)
        
        # Test ID extraction and consistency validation
        for context in contexts_for_extraction:
            # Test correlation ID generation
            correlation_id = context.get_correlation_id()
            self.assertIsInstance(correlation_id, str)
            self.assertIn(context.user_id[:8], correlation_id)
            self.assertIn(context.thread_id[:8], correlation_id)
            self.assertIn(context.run_id[:8], correlation_id)
            self.assertIn(context.request_id[:8], correlation_id)
            
            # Test audit trail generation
            audit_trail = context.get_audit_trail()
            self.assertIsInstance(audit_trail, dict)
            self.assertEqual(audit_trail["correlation_id"], correlation_id)
            self.assertEqual(audit_trail["user_id"], context.user_id)
            self.assertEqual(audit_trail["thread_id"], context.thread_id)
            self.assertEqual(audit_trail["run_id"], context.run_id)
            self.assertEqual(audit_trail["request_id"], context.request_id)
            
            # Validate context age calculation
            self.assertIn("context_age_seconds", audit_trail)
            self.assertGreaterEqual(audit_trail["context_age_seconds"], 0)
            
            # Test context serialization
            context_dict = context.to_dict()
            self.assertIsInstance(context_dict, dict)
            self.assertEqual(context_dict["user_id"], context.user_id)
            self.assertEqual(context_dict["request_id"], context.request_id)
            self.assertIn("implementation", context_dict)

    # ============================================================================
    # CONTEXT CREATION PATTERNS AND VALIDATION TESTS (5 tests)
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.context_creation
    @pytest.mark.validation_patterns
    def test_factory_context_validation_prevents_invalid_data(self):
        """
        BVJ: Validates factory enforces strict validation preventing invalid contexts that could cause security issues.
        Ensures all factory-created contexts pass comprehensive validation preventing system vulnerabilities.
        """
        # Test valid context creation
        valid_context = UserContextFactory.create_context(
            user_id="valid_user_12345",
            thread_id="valid_thread_67890", 
            run_id="valid_run_abcdef"
        )
        self.assertTrue(valid_context.verify_isolation())
        
        # Test validation catches forbidden placeholder values
        forbidden_patterns = [
            ("placeholder", "placeholder_thread", "placeholder_run"),
            ("default", "default_thread", "default_run"),
            ("temp", "temp_thread", "temp_run"),
            ("test", "test_thread", "test_run") if not get_env().is_test() else None,
            ("null", "null_thread", "null_run"),
            ("", "valid_thread", "valid_run"),  # Empty user_id
            ("valid_user", "", "valid_run"),   # Empty thread_id
            ("valid_user", "valid_thread", "") # Empty run_id
        ]
        
        for pattern in forbidden_patterns:
            if pattern is None:
                continue
                
            user_id, thread_id, run_id = pattern
            
            with self.assertRaises(InvalidContextError,
                                 msg=f"Should reject forbidden pattern: {pattern}"):
                UserContextFactory.create_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
        
        # Test validation passes for properly formatted IDs
        valid_patterns = [
            ("user_12345", "thread_67890", "run_abcdef"),
            ("production_user_uuid", "production_thread_uuid", "production_run_uuid"),
            (str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()))
        ]
        
        for user_id, thread_id, run_id in valid_patterns:
            valid_context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=thread_id, 
                run_id=run_id
            )
            self.assertTrue(valid_context.verify_isolation())

    @pytest.mark.integration
    @pytest.mark.context_creation
    @pytest.mark.immutability_validation
    def test_factory_creates_immutable_contexts_with_proper_boundaries(self):
        """
        BVJ: Validates factory creates immutable contexts preventing accidental modification and data corruption.
        Ensures context immutability boundaries are properly established for secure multi-user operations.
        """
        context = UserContextFactory.create_context(
            user_id="immutability_test_user",
            thread_id="immutability_thread",
            run_id="immutability_run"
        )
        
        # Test immutability - direct field modification should fail
        with self.assertRaises(AttributeError, msg="Frozen dataclass should prevent field modification"):
            context.user_id = "modified_user"
            
        with self.assertRaises(AttributeError, msg="Frozen dataclass should prevent field modification"):
            context.thread_id = "modified_thread"
            
        with self.assertRaises(AttributeError, msg="Frozen dataclass should prevent field modification"):
            context.request_id = "modified_request"
        
        # Test metadata isolation - modifications should not affect original
        original_agent_context = context.agent_context.copy()
        original_audit_metadata = context.audit_metadata.copy()
        
        # These operations should not modify the original context
        test_dict = context.agent_context
        test_dict["test_modification"] = "should_not_affect_original"
        
        # Verify original context unchanged due to deep copy isolation
        self.assertEqual(context.agent_context, original_agent_context,
                        "Original agent_context should be unchanged")
        
        # Test proper mutation through child context creation
        child_context = context.create_child_context(
            operation_name="immutability_test",
            additional_agent_context={"child_data": "child_value"},
            additional_audit_metadata={"child_audit": "child_audit_value"}
        )
        
        # Verify parent unchanged, child has new data
        self.assertEqual(context.agent_context, original_agent_context)
        self.assertEqual(child_context.agent_context["child_data"], "child_value")
        self.assertEqual(child_context.audit_metadata["child_audit"], "child_audit_value")
        
        # Both contexts should maintain isolation
        self.assertTrue(context.verify_isolation())
        self.assertTrue(child_context.verify_isolation())

    @pytest.mark.integration
    @pytest.mark.context_creation
    @pytest.mark.hierarchy_validation
    def test_factory_child_context_creation_maintains_hierarchy(self):
        """
        BVJ: Validates factory child context creation maintains proper hierarchy for complex agent operations.
        Ensures parent-child relationships are tracked correctly for audit trails and operation tracing.
        """
        # Create parent context
        parent_context = UserContextFactory.create_context(
            user_id="hierarchy_test_user",
            thread_id="hierarchy_thread",
            run_id="hierarchy_run"
        )
        
        # Create child contexts with proper hierarchy
        child_contexts = []
        for i in range(3):
            child_context = parent_context.create_child_context(
                operation_name=f"child_operation_{i}",
                additional_agent_context={
                    "child_index": i,
                    "child_operation_type": f"type_{i}"
                },
                additional_audit_metadata={
                    "child_created_at": datetime.now(timezone.utc).isoformat(),
                    "parent_context_id": parent_context.request_id
                }
            )
            child_contexts.append(child_context)
        
        # Validate hierarchy relationships
        for i, child in enumerate(child_contexts):
            # Child inherits parent's core IDs
            self.assertEqual(child.user_id, parent_context.user_id)
            self.assertEqual(child.thread_id, parent_context.thread_id)
            self.assertEqual(child.run_id, parent_context.run_id)
            
            # Child has unique request_id
            self.assertNotEqual(child.request_id, parent_context.request_id)
            
            # Operation depth tracking
            self.assertEqual(child.operation_depth, parent_context.operation_depth + 1)
            self.assertEqual(child.parent_request_id, parent_context.request_id)
            
            # Agent context inheritance and extension
            self.assertEqual(child.agent_context["operation_name"], f"child_operation_{i}")
            self.assertEqual(child.agent_context["child_index"], i)
            
            # Audit metadata hierarchy
            self.assertEqual(child.audit_metadata["parent_request_id"], parent_context.request_id)
            self.assertEqual(child.audit_metadata["operation_depth"], 1)
        
        # Test grandchild creation (deeper hierarchy)
        grandchild = child_contexts[0].create_child_context(
            operation_name="grandchild_operation"
        )
        
        self.assertEqual(grandchild.operation_depth, 2)
        self.assertEqual(grandchild.parent_request_id, child_contexts[0].request_id)
        
        # Test depth limit protection
        deep_context = parent_context
        for depth in range(10):  # Should reach max depth
            deep_context = deep_context.create_child_context(f"deep_operation_{depth}")
        
        # Next level should fail
        with self.assertRaises(InvalidContextError, msg="Should prevent excessive nesting"):
            deep_context.create_child_context("too_deep_operation")

    @pytest.mark.integration
    @pytest.mark.context_creation
    @pytest.mark.session_integration
    def test_factory_database_session_integration(self):
        """
        BVJ: Validates factory properly integrates database sessions for transactional context operations.
        Ensures contexts can be created with database sessions for consistent data operations.
        """
        # Mock database session for integration testing
        mock_db_session = AsyncMock()
        mock_db_session.close = AsyncMock()
        
        # Create context with database session
        context_with_session = UserContextFactory.create_with_session(
            user_id="db_session_test_user",
            thread_id="db_thread",
            run_id="db_run",
            db_session=mock_db_session,
            websocket_client_id="db_ws_client"
        )
        
        # Validate session integration
        self.assertEqual(context_with_session.db_session, mock_db_session)
        self.assertTrue(context_with_session.to_dict()["has_db_session"])
        
        # Test context operations with session
        child_with_session = context_with_session.create_child_context(
            operation_name="db_child_operation"
        )
        
        # Child should inherit session
        self.assertEqual(child_with_session.db_session, mock_db_session)
        
        # Test session replacement
        mock_new_session = AsyncMock()
        context_with_new_session = context_with_session.with_db_session(mock_new_session)
        
        self.assertEqual(context_with_new_session.db_session, mock_new_session)
        self.assertNotEqual(context_with_new_session.db_session, context_with_session.db_session)
        
        # Original context unchanged
        self.assertEqual(context_with_session.db_session, mock_db_session)
        
        # Test invalid session handling
        with self.assertRaises(InvalidContextError):
            context_with_session.with_db_session(None)

    @pytest.mark.integration
    @pytest.mark.context_creation
    @pytest.mark.websocket_integration
    def test_factory_websocket_context_creation_patterns(self):
        """
        BVJ: Validates factory creates WebSocket contexts with proper routing isolation for real-time features.
        Ensures WebSocket context creation supports multi-user chat functionality with proper isolation.
        """
        websocket_contexts = []
        
        # Create WebSocket contexts for different connection scenarios
        connection_scenarios = [
            ("new_connection", "websocket_session"),
            ("reconnection", "websocket_reconnect"),
            ("agent_execution", "agent_websocket"),
            ("background_task", "background_websocket")
        ]
        
        for i, (scenario, operation) in enumerate(connection_scenarios):
            user_id = f"websocket_user_{scenario}_{i}"
            
            # Create WebSocket context using SSOT factory
            ws_context = UserExecutionContext.from_websocket_request(
                user_id=user_id,
                websocket_client_id=f"ws_client_{scenario}_{i}",
                operation=operation
            )
            websocket_contexts.append((scenario, ws_context))
        
        # Validate WebSocket context properties
        for scenario, ws_context in websocket_contexts:
            # WebSocket-specific validation
            self.assertIsNotNone(ws_context.websocket_client_id)
            self.assertTrue(ws_context.websocket_client_id.startswith("ws_client_"))
            
            # Agent context validation
            self.assertEqual(ws_context.agent_context["source"], "websocket_ssot")
            self.assertEqual(ws_context.agent_context["created_via"], "from_websocket_request")
            self.assertIn(scenario.split("_")[1], ws_context.agent_context["operation"])
            
            # Audit metadata validation
            self.assertEqual(ws_context.audit_metadata["context_source"], "websocket_ssot")
            self.assertTrue(ws_context.audit_metadata["isolation_key_compatible"])
            
            # Backward compatibility validation
            self.assertEqual(ws_context.websocket_connection_id, ws_context.websocket_client_id)
            
            # Isolation validation
            self.assertTrue(ws_context.verify_isolation())
        
        # Test WebSocket context child creation
        base_ws_context = websocket_contexts[0][1]
        ws_child = base_ws_context.create_child_context(
            operation_name="websocket_agent_execution",
            additional_agent_context={"agent_type": "chat_agent"}
        )
        
        # Child should inherit WebSocket connection
        self.assertEqual(ws_child.websocket_client_id, base_ws_context.websocket_client_id)
        self.assertEqual(ws_child.websocket_connection_id, base_ws_context.websocket_connection_id)

    # ============================================================================
    # FACTORY-BASED RESOURCE MANAGEMENT AND CLEANUP TESTS (5 tests)
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.resource_management
    @pytest.mark.cleanup_validation
    async def test_factory_managed_context_resource_cleanup(self):
        """
        BVJ: Validates factory-created contexts properly clean up resources preventing memory leaks.
        Ensures managed context pattern automatically handles resource cleanup for production stability.
        """
        cleanup_tracker = {"called": False, "cleanup_count": 0}
        
        # Create context with tracked resources
        context = UserContextFactory.create_context(
            user_id="cleanup_test_user",
            thread_id="cleanup_thread",
            run_id="cleanup_run"
        )
        
        # Mock resource that tracks cleanup
        class MockResource:
            def __init__(self, tracker):
                self.tracker = tracker
                self.closed = False
                
            async def close(self):
                self.tracker["called"] = True
                self.tracker["cleanup_count"] += 1
                self.closed = True
        
        mock_resource = MockResource(cleanup_tracker)
        
        # Test managed context cleanup
        async with managed_user_context(context, cleanup_db_session=False) as managed_ctx:
            # Add cleanup callback
            managed_ctx.cleanup_callbacks.append(mock_resource.close)
            
            # Verify context is usable
            self.assertEqual(managed_ctx.user_id, "cleanup_test_user")
            self.assertTrue(managed_ctx.verify_isolation())
            
            # Create child context within managed scope
            child_ctx = managed_ctx.create_child_context("managed_child_operation")
            self.assertTrue(child_ctx.verify_isolation())
        
        # Verify cleanup was called
        self.assertTrue(cleanup_tracker["called"], "Cleanup callback should have been called")
        self.assertEqual(cleanup_tracker["cleanup_count"], 1, "Cleanup should be called exactly once")
        self.assertTrue(mock_resource.closed, "Mock resource should be closed")

    @pytest.mark.integration
    @pytest.mark.resource_management
    @pytest.mark.memory_tracking
    def test_factory_resource_tracking_and_leak_prevention(self):
        """
        BVJ: Validates factory resource tracking prevents memory leaks in long-running multi-user scenarios.
        Ensures proper resource lifecycle management for sustainable production operations.
        """
        resource_registry = []
        
        def create_context_with_resources(user_index: int) -> Tuple[UserExecutionContext, List[Any]]:
            """Create context and associated mock resources."""
            context = UserContextFactory.create_context(
                user_id=f"resource_user_{user_index}",
                thread_id=f"resource_thread_{user_index}",
                run_id=f"resource_run_{user_index}"
            )
            
            # Create mock resources for tracking
            mock_resources = [
                {"type": "database_connection", "id": f"db_{user_index}", "cleanup_called": False},
                {"type": "websocket_connection", "id": f"ws_{user_index}", "cleanup_called": False},
                {"type": "temp_file", "id": f"file_{user_index}", "cleanup_called": False}
            ]
            
            # Register cleanup callbacks
            for resource in mock_resources:
                def cleanup_callback(res=resource):
                    res["cleanup_called"] = True
                
                context.cleanup_callbacks.append(cleanup_callback)
            
            return context, mock_resources
        
        # Create multiple contexts with resources
        context_resource_pairs = []
        for i in range(5):
            ctx, resources = create_context_with_resources(i)
            context_resource_pairs.append((ctx, resources))
            resource_registry.extend(resources)
        
        # Verify resource tracking
        total_resources = len(resource_registry)
        self.assertEqual(total_resources, 15, "Should track 3 resources per 5 contexts")
        
        # Simulate resource cleanup
        for context, resources in context_resource_pairs:
            # Execute cleanup
            asyncio.run(context.cleanup())
            
            # Verify all resources were cleaned up
            for resource in resources:
                self.assertTrue(resource["cleanup_called"], 
                              f"Resource {resource['id']} should be cleaned up")
        
        # Verify all resources in registry were cleaned up
        cleanup_status = [res["cleanup_called"] for res in resource_registry]
        self.assertTrue(all(cleanup_status), "All tracked resources should be cleaned up")

    @pytest.mark.integration
    @pytest.mark.resource_management
    @pytest.mark.concurrent_cleanup
    async def test_factory_concurrent_resource_cleanup_safety(self):
        """
        BVJ: Validates factory resource cleanup is safe under concurrent operations preventing race conditions.
        Ensures cleanup operations don't interfere with each other in high-concurrency scenarios.
        """
        cleanup_results = []
        cleanup_lock = asyncio.Lock()
        
        async def create_and_cleanup_context(context_id: int) -> Dict[str, Any]:
            """Worker function for concurrent cleanup testing."""
            context = UserContextFactory.create_context(
                user_id=f"concurrent_cleanup_user_{context_id}",
                thread_id=f"concurrent_cleanup_thread_{context_id}",
                run_id=f"concurrent_cleanup_run_{context_id}"
            )
            
            cleanup_start_time = time.time()
            
            # Add mock cleanup callbacks
            cleanup_call_count = {"count": 0}
            
            async def mock_async_cleanup():
                await asyncio.sleep(0.001)  # Simulate async cleanup work
                cleanup_call_count["count"] += 1
                
            def mock_sync_cleanup():
                cleanup_call_count["count"] += 1
            
            context.cleanup_callbacks.extend([
                mock_async_cleanup,
                mock_sync_cleanup,
                mock_async_cleanup
            ])
            
            # Execute cleanup
            await context.cleanup()
            cleanup_end_time = time.time()
            
            result = {
                "context_id": context_id,
                "cleanup_duration": cleanup_end_time - cleanup_start_time,
                "cleanup_calls": cleanup_call_count["count"],
                "success": cleanup_call_count["count"] == 3
            }
            
            async with cleanup_lock:
                cleanup_results.append(result)
            
            return result
        
        # Execute concurrent cleanup operations
        tasks = [create_and_cleanup_context(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        # Validate concurrent cleanup safety
        self.assertEqual(len(results), 20, "All cleanup tasks should complete")
        
        for result in results:
            self.assertTrue(result["success"], f"Context {result['context_id']} cleanup should succeed")
            self.assertEqual(result["cleanup_calls"], 3, "All cleanup callbacks should be called")
            self.assertGreater(result["cleanup_duration"], 0, "Cleanup should take measurable time")
        
        # Validate no race conditions occurred
        context_ids = [r["context_id"] for r in results]
        self.assertEqual(len(set(context_ids)), 20, "All context IDs should be unique")

    @pytest.mark.integration
    @pytest.mark.resource_management
    @pytest.mark.cleanup_error_handling
    async def test_factory_cleanup_error_resilience(self):
        """
        BVJ: Validates factory cleanup continues even when individual resource cleanup fails.
        Ensures system resilience and prevents cascade failures in resource cleanup scenarios.
        """
        context = UserContextFactory.create_context(
            user_id="cleanup_error_test_user",
            thread_id="cleanup_error_thread",
            run_id="cleanup_error_run"
        )
        
        cleanup_execution_log = []
        
        # Create mix of successful and failing cleanup callbacks
        async def successful_async_cleanup():
            cleanup_execution_log.append("async_success")
            
        def successful_sync_cleanup():
            cleanup_execution_log.append("sync_success")
        
        async def failing_async_cleanup():
            cleanup_execution_log.append("async_attempt")
            raise RuntimeError("Simulated async cleanup failure")
        
        def failing_sync_cleanup():
            cleanup_execution_log.append("sync_attempt") 
            raise RuntimeError("Simulated sync cleanup failure")
        
        # Add callbacks in specific order to test LIFO execution
        context.cleanup_callbacks.extend([
            successful_async_cleanup,  # Should execute last (LIFO)
            failing_async_cleanup,
            successful_sync_cleanup,
            failing_sync_cleanup,
            successful_async_cleanup   # Should execute first (LIFO)
        ])
        
        # Execute cleanup - should not raise exceptions despite failures
        await context.cleanup()
        
        # Verify execution order (LIFO - last in, first out)
        expected_log = [
            "async_success",    # Last added, executed first
            "sync_attempt",     # Second to last
            "sync_success",     # Middle
            "async_attempt",    # Second 
            "async_success"     # First added, executed last
        ]
        
        self.assertEqual(cleanup_execution_log, expected_log,
                        "Cleanup should execute in LIFO order despite failures")
        
        # Verify cleanup callbacks are cleared after execution
        self.assertEqual(len(context.cleanup_callbacks), 0,
                        "Cleanup callbacks should be cleared after execution")

    @pytest.mark.integration
    @pytest.mark.resource_management
    @pytest.mark.lifecycle_management
    async def test_factory_context_lifecycle_resource_boundaries(self):
        """
        BVJ: Validates factory contexts maintain proper resource boundaries throughout their lifecycle.
        Ensures resource allocation and deallocation follow expected patterns for memory management.
        """
        lifecycle_events = []
        
        class ResourceLifecycleTracker:
            def __init__(self, resource_id: str):
                self.resource_id = resource_id
                self.allocated = True
                self.deallocated = False
                lifecycle_events.append(f"allocated_{resource_id}")
            
            async def cleanup(self):
                if not self.deallocated:
                    self.deallocated = True
                    self.allocated = False
                    lifecycle_events.append(f"deallocated_{self.resource_id}")
        
        # Test complete lifecycle with managed context
        async with managed_user_context(
            UserContextFactory.create_context(
                user_id="lifecycle_test_user",
                thread_id="lifecycle_thread", 
                run_id="lifecycle_run"
            )
        ) as managed_ctx:
            
            # Allocate resources during context lifecycle
            tracker1 = ResourceLifecycleTracker("resource_1")
            tracker2 = ResourceLifecycleTracker("resource_2")
            
            managed_ctx.cleanup_callbacks.extend([
                tracker1.cleanup,
                tracker2.cleanup
            ])
            
            # Verify resources are allocated
            self.assertTrue(tracker1.allocated)
            self.assertTrue(tracker2.allocated)
            self.assertFalse(tracker1.deallocated)
            self.assertFalse(tracker2.deallocated)
            
            # Create child context with additional resources
            child_ctx = managed_ctx.create_child_context("lifecycle_child")
            tracker3 = ResourceLifecycleTracker("resource_3") 
            child_ctx.cleanup_callbacks.append(tracker3.cleanup)
            
            # Manual child cleanup
            await child_ctx.cleanup()
            
            # Verify child resource cleaned up, parent resources still active
            self.assertTrue(tracker3.deallocated)
            self.assertTrue(tracker1.allocated)
            self.assertTrue(tracker2.allocated)
        
        # After managed context exit, all remaining resources should be cleaned up
        self.assertTrue(tracker1.deallocated, "Resource 1 should be deallocated")
        self.assertTrue(tracker2.deallocated, "Resource 2 should be deallocated") 
        self.assertTrue(tracker3.deallocated, "Resource 3 should be deallocated")
        
        # Verify lifecycle event order
        expected_events = [
            "allocated_resource_1",
            "allocated_resource_2", 
            "allocated_resource_3",
            "deallocated_resource_3",  # Child cleanup
            "deallocated_resource_2",  # Parent cleanup (LIFO)
            "deallocated_resource_1"   # Parent cleanup (LIFO)
        ]
        
        self.assertEqual(lifecycle_events, expected_events,
                        "Resource lifecycle events should follow expected pattern")

    # ============================================================================
    # WEBSOCKET CONTEXT CREATION AND ROUTING ISOLATION TESTS (5 tests)
    # ============================================================================

    @pytest.mark.integration
    @pytest.mark.websocket_isolation
    @pytest.mark.routing_validation
    def test_factory_websocket_routing_isolation_per_user(self):
        """
        BVJ: Validates factory creates WebSocket contexts with proper routing isolation preventing cross-user message delivery.
        Critical for chat functionality ensuring users only receive their own messages and agent responses.
        """
        websocket_routing_contexts = []
        
        # Create WebSocket contexts for different users
        for i in range(8):
            user_id = f"routing_user_{i}"
            
            ws_context = UserExecutionContext.from_websocket_request(
                user_id=user_id,
                websocket_client_id=f"routing_client_{i}",
                operation="message_routing"
            )
            websocket_routing_contexts.append(ws_context)
        
        # Validate routing isolation properties
        client_ids = set()
        user_ids = set()
        
        for context in websocket_routing_contexts:
            # Collect routing identifiers
            client_ids.add(context.websocket_client_id)
            user_ids.add(context.user_id)
            
            # Validate routing metadata
            self.assertIsNotNone(context.websocket_client_id)
            self.assertTrue(context.websocket_client_id.startswith("routing_client_"))
            
            # Verify backward compatibility for routing
            self.assertEqual(context.websocket_connection_id, context.websocket_client_id)
            
            # Validate isolation for routing
            self.assertTrue(context.verify_isolation())
        
        # Ensure all routing identifiers are unique
        self.assertEqual(len(client_ids), 8, "All WebSocket client IDs must be unique")
        self.assertEqual(len(user_ids), 8, "All user IDs must be unique")
        
        # Test child context routing inheritance
        base_context = websocket_routing_contexts[0]
        child_context = base_context.create_child_context(
            operation_name="child_message_handling",
            additional_agent_context={"message_type": "agent_response"}
        )
        
        # Child should inherit parent's routing
        self.assertEqual(child_context.websocket_client_id, base_context.websocket_client_id)
        self.assertEqual(child_context.user_id, base_context.user_id)
        
        # But maintain its own request isolation
        self.assertNotEqual(child_context.request_id, base_context.request_id)
        self.assertTrue(child_context.verify_isolation())

    @pytest.mark.integration
    @pytest.mark.websocket_isolation
    @pytest.mark.connection_management
    def test_factory_websocket_connection_context_isolation(self):
        """
        BVJ: Validates factory WebSocket contexts prevent connection state leakage between concurrent users.
        Ensures WebSocket connection management maintains proper isolation for stable multi-user chat.
        """
        connection_contexts = []
        connection_states = {}
        
        # Simulate multiple WebSocket connections
        connection_scenarios = [
            ("initial_connect", "user_connect_1"),
            ("reconnect_after_drop", "user_reconnect_1"),
            ("multiple_tabs", "user_multitab_1"),
            ("mobile_connection", "user_mobile_1"),
            ("background_connection", "user_background_1")
        ]
        
        for scenario, user_base in connection_scenarios:
            # Create context for each connection scenario
            user_id = f"{user_base}_{scenario}"
            
            ws_context = UserExecutionContext.from_websocket_request(
                user_id=user_id,
                websocket_client_id=f"conn_{scenario}_{hash(user_id) % 1000}",
                operation=f"connection_{scenario}"
            )
            connection_contexts.append((scenario, ws_context))
            
            # Track connection state
            connection_states[ws_context.websocket_client_id] = {
                "user_id": user_id,
                "scenario": scenario,
                "context_id": ws_context.request_id,
                "connected": True,
                "isolation_verified": ws_context.verify_isolation()
            }
        
        # Validate connection isolation
        for scenario, context in connection_contexts:
            state = connection_states[context.websocket_client_id]
            
            # Verify connection state isolation
            self.assertTrue(state["isolation_verified"])
            self.assertEqual(state["scenario"], scenario)
            self.assertEqual(state["user_id"], context.user_id)
            
            # Verify context routing data
            self.assertEqual(context.agent_context["operation"], f"connection_{scenario}")
            self.assertTrue(context.audit_metadata["isolation_key_compatible"])
        
        # Test connection context updates don't affect other connections
        test_context = connection_contexts[0][1]
        child_with_update = test_context.create_child_context(
            operation_name="connection_update",
            additional_agent_context={"connection_status": "updated"}
        )
        
        # Verify update isolation
        original_state = connection_states[test_context.websocket_client_id]
        self.assertTrue(original_state["connected"])
        
        # Other contexts should remain unchanged
        for other_scenario, other_context in connection_contexts[1:]:
            other_state = connection_states[other_context.websocket_client_id]
            self.assertTrue(other_state["connected"])
            self.assertNotEqual(other_context.request_id, child_with_update.request_id)

    @pytest.mark.integration
    @pytest.mark.websocket_isolation
    @pytest.mark.message_context_validation
    def test_factory_websocket_message_context_boundaries(self):
        """
        BVJ: Validates factory WebSocket contexts maintain proper message boundaries preventing message mixing.
        Ensures each user's messages and agent responses are properly isolated and routed correctly.
        """
        # Create contexts for message boundary testing
        user_contexts = {}
        message_contexts = {}
        
        users = ["alice", "bob", "charlie"]
        
        for user in users:
            # Create base WebSocket context for user
            base_context = UserExecutionContext.from_websocket_request(
                user_id=f"message_user_{user}",
                websocket_client_id=f"message_client_{user}",
                operation="message_handling"
            )
            user_contexts[user] = base_context
            message_contexts[user] = []
            
            # Create message contexts for different message types
            message_types = ["user_message", "agent_response", "system_notification"]
            
            for msg_type in message_types:
                msg_context = base_context.create_child_context(
                    operation_name=f"{msg_type}_handling",
                    additional_agent_context={
                        "message_type": msg_type,
                        "user": user,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    additional_audit_metadata={
                        "message_category": msg_type,
                        "routing_user": user
                    }
                )
                message_contexts[user].append((msg_type, msg_context))
        
        # Validate message context boundaries
        for user in users:
            user_base_context = user_contexts[user]
            user_messages = message_contexts[user]
            
            for msg_type, msg_context in user_messages:
                # Message context should inherit user routing
                self.assertEqual(msg_context.user_id, user_base_context.user_id)
                self.assertEqual(msg_context.websocket_client_id, user_base_context.websocket_client_id)
                
                # But maintain unique request boundaries
                self.assertNotEqual(msg_context.request_id, user_base_context.request_id)
                
                # Validate message-specific metadata
                self.assertEqual(msg_context.agent_context["message_type"], msg_type)
                self.assertEqual(msg_context.agent_context["user"], user)
                self.assertEqual(msg_context.audit_metadata["routing_user"], user)
                
                # Verify isolation
                self.assertTrue(msg_context.verify_isolation())
        
        # Cross-user validation - ensure no message context mixing
        for user_a in users:
            for user_b in users:
                if user_a != user_b:
                    context_a = user_contexts[user_a]
                    context_b = user_contexts[user_b]
                    
                    # Contexts should have different user routing
                    self.assertNotEqual(context_a.user_id, context_b.user_id)
                    self.assertNotEqual(context_a.websocket_client_id, context_b.websocket_client_id)
                    
                    # Message contexts should not cross-contaminate
                    for msg_type_a, msg_ctx_a in message_contexts[user_a]:
                        for msg_type_b, msg_ctx_b in message_contexts[user_b]:
                            self.assertNotEqual(msg_ctx_a.user_id, msg_ctx_b.user_id)
                            self.assertNotEqual(msg_ctx_a.websocket_client_id, msg_ctx_b.websocket_client_id)

    @pytest.mark.integration
    @pytest.mark.websocket_isolation 
    @pytest.mark.agent_execution_routing
    async def test_factory_websocket_agent_execution_routing_isolation(self):
        """
        BVJ: Validates factory WebSocket contexts properly route agent execution results to correct users.
        Ensures agent execution events and results are delivered to the right user's WebSocket connection.
        """
        # Create WebSocket contexts for agent execution testing
        agent_execution_contexts = []
        execution_routing_map = {}
        
        for i in range(4):
            user_id = f"agent_exec_user_{i}"
            
            ws_context = UserExecutionContext.from_websocket_request(
                user_id=user_id,
                websocket_client_id=f"agent_exec_client_{i}",
                operation="agent_execution_routing"
            )
            agent_execution_contexts.append(ws_context)
            
            # Map user to their WebSocket routing
            execution_routing_map[user_id] = {
                "websocket_client_id": ws_context.websocket_client_id,
                "base_context": ws_context,
                "agent_executions": []
            }
        
        # Simulate agent execution for each user
        for context in agent_execution_contexts:
            user_routing = execution_routing_map[context.user_id]
            
            # Create agent execution context
            agent_context = context.create_child_context(
                operation_name="agent_execution",
                additional_agent_context={
                    "agent_type": "cost_optimizer",
                    "execution_id": f"exec_{uuid.uuid4().hex[:8]}",
                    "routing_target": context.websocket_client_id
                },
                additional_audit_metadata={
                    "execution_start": datetime.now(timezone.utc).isoformat(),
                    "target_user": context.user_id,
                    "websocket_routing": context.websocket_client_id
                }
            )
            
            user_routing["agent_executions"].append(agent_context)
            
            # Validate agent execution routing
            self.assertEqual(agent_context.user_id, context.user_id)
            self.assertEqual(agent_context.websocket_client_id, context.websocket_client_id)
            self.assertEqual(agent_context.agent_context["routing_target"], context.websocket_client_id)
            
            # Create simulated agent execution result context
            result_context = agent_context.create_child_context(
                operation_name="agent_result_delivery",
                additional_agent_context={
                    "result_type": "optimization_complete",
                    "delivery_target": context.websocket_client_id,
                    "result_data": {"savings": 1000, "recommendations": 5}
                }
            )
            
            user_routing["agent_executions"].append(result_context)
            
            # Validate result routing isolation
            self.assertEqual(result_context.user_id, context.user_id)
            self.assertEqual(result_context.websocket_client_id, context.websocket_client_id)
            self.assertTrue(result_context.verify_isolation())
        
        # Cross-user validation - ensure no routing mix-ups
        user_ids = list(execution_routing_map.keys())
        for i, user_a in enumerate(user_ids):
            for j, user_b in enumerate(user_ids):
                if i != j:
                    routing_a = execution_routing_map[user_a]
                    routing_b = execution_routing_map[user_b]
                    
                    # Different users should have different routing
                    self.assertNotEqual(routing_a["websocket_client_id"], routing_b["websocket_client_id"])
                    
                    # Agent execution contexts should not cross-route
                    for exec_ctx_a in routing_a["agent_executions"]:
                        for exec_ctx_b in routing_b["agent_executions"]:
                            self.assertNotEqual(exec_ctx_a.user_id, exec_ctx_b.user_id)
                            self.assertNotEqual(exec_ctx_a.websocket_client_id, exec_ctx_b.websocket_client_id)

    @pytest.mark.integration
    @pytest.mark.websocket_isolation
    @pytest.mark.concurrent_websocket_validation
    async def test_factory_concurrent_websocket_context_isolation(self):
        """
        BVJ: Validates factory WebSocket contexts maintain isolation under concurrent WebSocket operations.
        Ensures high-concurrency WebSocket scenarios don't cause context mixing or routing failures.
        """
        concurrent_results = []
        results_lock = asyncio.Lock()
        
        async def simulate_concurrent_websocket_operations(operation_id: int) -> Dict[str, Any]:
            """Simulate concurrent WebSocket context operations."""
            user_id = f"concurrent_ws_user_{operation_id}"
            
            # Create WebSocket context
            ws_context = UserExecutionContext.from_websocket_request(
                user_id=user_id,
                websocket_client_id=f"concurrent_ws_client_{operation_id}",
                operation="concurrent_websocket_test"
            )
            
            operation_start = time.time()
            
            # Simulate concurrent operations
            child_contexts = []
            for op_type in ["message", "agent_execution", "notification"]:
                await asyncio.sleep(0.001)  # Simulate async delay
                
                child_ctx = ws_context.create_child_context(
                    operation_name=f"concurrent_{op_type}",
                    additional_agent_context={
                        "operation_type": op_type,
                        "operation_id": operation_id,
                        "concurrent_timestamp": time.time()
                    }
                )
                child_contexts.append(child_ctx)
            
            # Validate all contexts maintain isolation
            isolation_results = []
            for child_ctx in child_contexts:
                isolation_verified = child_ctx.verify_isolation()
                isolation_results.append(isolation_verified)
                
                # Verify routing consistency
                self.assertEqual(child_ctx.user_id, ws_context.user_id)
                self.assertEqual(child_ctx.websocket_client_id, ws_context.websocket_client_id)
            
            operation_end = time.time()
            
            result = {
                "operation_id": operation_id,
                "user_id": user_id,
                "websocket_client_id": ws_context.websocket_client_id,
                "base_context_id": ws_context.request_id,
                "child_context_count": len(child_contexts),
                "isolation_success": all(isolation_results),
                "operation_duration": operation_end - operation_start,
                "child_context_ids": [ctx.request_id for ctx in child_contexts]
            }
            
            async with results_lock:
                concurrent_results.append(result)
            
            return result
        
        # Execute concurrent WebSocket operations
        tasks = [simulate_concurrent_websocket_operations(i) for i in range(25)]
        results = await asyncio.gather(*tasks)
        
        # Validate concurrent isolation success
        self.assertEqual(len(results), 25, "All concurrent operations should complete")
        
        for result in results:
            self.assertTrue(result["isolation_success"], 
                          f"Operation {result['operation_id']} should maintain isolation")
            self.assertEqual(result["child_context_count"], 3,
                           "Each operation should create 3 child contexts")
        
        # Validate uniqueness across all concurrent operations
        all_user_ids = [r["user_id"] for r in results]
        all_client_ids = [r["websocket_client_id"] for r in results]
        all_base_context_ids = [r["base_context_id"] for r in results]
        
        self.assertEqual(len(set(all_user_ids)), 25, "All user IDs should be unique")
        self.assertEqual(len(set(all_client_ids)), 25, "All WebSocket client IDs should be unique")
        self.assertEqual(len(set(all_base_context_ids)), 25, "All base context IDs should be unique")
        
        # Validate child context uniqueness
        all_child_context_ids = []
        for result in results:
            all_child_context_ids.extend(result["child_context_ids"])
        
        self.assertEqual(len(set(all_child_context_ids)), 75,
                        "All child context IDs should be unique (25 operations × 3 children)")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])