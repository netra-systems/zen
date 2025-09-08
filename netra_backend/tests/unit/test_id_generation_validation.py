"""
Test ID Generation and Validation Business Logic - Core Unit Tests

Business Value Justification (BVJ):
- Segment: All (ID generation affects all user interactions and system operations)
- Business Goal: System reliability and data integrity through proper request isolation
- Value Impact: Prevents ID collisions that could cause user data leakage and system failures
- Strategic Impact: CRITICAL - Proper ID isolation prevents security vulnerabilities and ensures multi-user system stability

This test suite validates the core business logic for unified ID generation
that enables proper request isolation and context tracking across the system.
"""

import pytest
import time
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment

from shared.id_generation.unified_id_generator import (
    UnifiedIdGenerator,
    generate_uuid_replacement,
    create_user_execution_context_factory,
    TestIdUtils,
    IdComponents,
    reset_global_counter
)


class TestIdGenerationValidation(BaseTestCase):
    """Test ID generation delivers reliable isolation for business operations."""
    
    def setup_method(self):
        """Setup test environment with isolated configuration."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        # Reset counter for test isolation
        reset_global_counter()
        
    def teardown_method(self):
        """Clean up test environment."""
        super().teardown_method()
        
    @pytest.mark.unit
    def test_base_id_generation_uniqueness_guarantee(self):
        """Test that base ID generation guarantees uniqueness for business data integrity."""
        # Generate many IDs quickly to test collision resistance
        ids = []
        for i in range(1000):
            id_value = UnifiedIdGenerator.generate_base_id("test", include_random=True)
            ids.append(id_value)
            
            # Each ID should follow expected format: prefix_timestamp_counter_random
            parts = id_value.split('_')
            assert len(parts) >= 4, f"ID should have at least 4 parts: {id_value}"
            assert parts[0] == "test", f"Prefix should be preserved: {id_value}"
            
            # Timestamp should be reasonable (within last few seconds)
            timestamp = int(parts[1])
            current_time = int(time.time() * 1000)
            time_diff = abs(current_time - timestamp)
            assert time_diff < 10000, f"Timestamp too old/future: {id_value} (diff: {time_diff}ms)"
            
            # Counter should be numeric
            counter = int(parts[2])
            assert counter > 0, f"Counter should be positive: {id_value}"
            
            # Random part should exist and be reasonable length
            random_part = parts[3]
            assert len(random_part) >= 6, f"Random part too short: {id_value}"
            
        # All IDs should be unique (critical business requirement)
        unique_ids = set(ids)
        assert len(unique_ids) == len(ids), \
            f"ID collision detected! Generated {len(ids)} IDs but only {len(unique_ids)} unique"
            
    @pytest.mark.unit
    def test_user_context_id_generation_consistency(self):
        """Test that user context ID generation maintains consistency for session management."""
        user_id = "business_user_123"
        operation = "chat_session"
        
        # Generate context IDs multiple times
        for i in range(10):
            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
                user_id, operation
            )
            
            # All IDs should be strings
            assert isinstance(thread_id, str), f"thread_id should be string: {thread_id}"
            assert isinstance(run_id, str), f"run_id should be string: {run_id}"
            assert isinstance(request_id, str), f"request_id should be string: {request_id}"
            
            # Should contain operation context
            assert operation in thread_id, f"thread_id should contain operation: {thread_id}"
            assert operation in run_id, f"run_id should contain operation: {run_id}"
            assert operation in request_id, f"request_id should contain operation: {request_id}"
            
            # Should have proper prefixes for identification
            assert thread_id.startswith("thread_"), f"thread_id should have proper prefix: {thread_id}"
            assert run_id.startswith("run_"), f"run_id should have proper prefix: {run_id}"
            assert request_id.startswith("req_"), f"request_id should have proper prefix: {request_id}"
            
            # All three should be different (no duplicates)
            assert thread_id != run_id, "thread_id and run_id should be different"
            assert thread_id != request_id, "thread_id and request_id should be different"
            assert run_id != request_id, "run_id and request_id should be different"
            
    @pytest.mark.unit
    def test_websocket_connection_id_business_logic(self):
        """Test WebSocket connection ID generation supports proper connection management."""
        user_id = "websocket_user_456"
        connection_timestamp = time.time()
        
        # Generate multiple connection IDs
        connection_ids = []
        for i in range(20):
            conn_id = UnifiedIdGenerator.generate_websocket_connection_id(
                user_id, connection_timestamp + i
            )
            connection_ids.append(conn_id)
            
            # Should have websocket-specific prefix
            assert conn_id.startswith("ws_conn_"), f"Connection ID should have ws_conn_ prefix: {conn_id}"
            
            # Should contain user identifier for traceability
            user_prefix = user_id[:8]
            assert user_prefix in conn_id, f"Connection ID should contain user prefix: {conn_id}"
            
            # Should be reasonable length for efficient storage/lookup
            assert 20 <= len(conn_id) <= 80, f"Connection ID length unreasonable: {conn_id}"
            
        # All connection IDs should be unique
        unique_conn_ids = set(connection_ids)
        assert len(unique_conn_ids) == len(connection_ids), \
            "WebSocket connection ID collision detected"
            
    @pytest.mark.unit
    def test_agent_execution_id_traceability(self):
        """Test that agent execution IDs provide proper traceability for business operations."""
        agent_types = ["data_analyzer", "cost_optimizer", "quality_validator"]
        user_id = "agent_user_789"
        
        execution_ids = []
        
        for agent_type in agent_types:
            for execution in range(5):
                exec_id = UnifiedIdGenerator.generate_agent_execution_id(agent_type, user_id)
                execution_ids.append(exec_id)
                
                # Should contain agent type for operational visibility
                assert agent_type in exec_id, f"Execution ID should contain agent type: {exec_id}"
                
                # Should contain user context for isolation
                user_prefix = user_id[:8]
                assert user_prefix in exec_id, f"Execution ID should contain user context: {exec_id}"
                
                # Should start with "agent_" for categorization
                assert exec_id.startswith(f"agent_{agent_type}"), \
                    f"Execution ID should have proper prefix: {exec_id}"
                    
        # All execution IDs should be unique even for same agent type
        unique_exec_ids = set(execution_ids)
        assert len(unique_exec_ids) == len(execution_ids), \
            "Agent execution ID collision detected"
            
    @pytest.mark.unit
    def test_id_parsing_business_intelligence(self):
        """Test that ID parsing provides business intelligence for operations and debugging."""
        # Generate test ID with known components
        test_prefix = "business_op"
        test_id = UnifiedIdGenerator.generate_base_id(test_prefix, include_random=True)
        
        # Parse the ID
        parsed = UnifiedIdGenerator.parse_id(test_id)
        
        assert parsed is not None, f"Should be able to parse valid ID: {test_id}"
        assert isinstance(parsed, IdComponents), "Parsed result should be IdComponents"
        
        # Verify parsed components
        assert parsed.prefix == test_prefix, f"Prefix should match: {parsed.prefix} vs {test_prefix}"
        assert parsed.timestamp > 0, f"Timestamp should be positive: {parsed.timestamp}"
        assert parsed.counter > 0, f"Counter should be positive: {parsed.counter}"
        assert len(parsed.random) > 0, f"Random part should exist: {parsed.random}"
        assert parsed.full_id == test_id, f"Full ID should match original: {parsed.full_id}"
        
        # Test invalid ID parsing
        invalid_ids = ["", "invalid", "too_few_parts", "non_numeric_timestamp_abc_1_xyz"]
        for invalid_id in invalid_ids:
            parsed_invalid = UnifiedIdGenerator.parse_id(invalid_id)
            assert parsed_invalid is None, f"Should not parse invalid ID: {invalid_id}"
            
    @pytest.mark.unit
    def test_id_validation_business_rules(self):
        """Test that ID validation enforces business rules for system integrity."""
        # Generate valid ID
        valid_id = UnifiedIdGenerator.generate_base_id("valid_test")
        
        # Should validate as true
        assert UnifiedIdGenerator.is_valid_id(valid_id), f"Valid ID should validate: {valid_id}"
        
        # Should validate with expected prefix
        assert UnifiedIdGenerator.is_valid_id(valid_id, "valid_test"), \
            f"Valid ID should validate with correct prefix: {valid_id}"
            
        # Should not validate with wrong prefix
        assert not UnifiedIdGenerator.is_valid_id(valid_id, "wrong_prefix"), \
            f"Valid ID should not validate with wrong prefix: {valid_id}"
            
        # Test business rule: IDs should not be too old (prevent replay attacks)
        old_timestamp = int((time.time() - (400 * 24 * 60 * 60)) * 1000)  # 400 days old
        old_id = f"old_test_{old_timestamp}_1_abc123"
        assert not UnifiedIdGenerator.is_valid_id(old_id), \
            f"Old ID should not validate: {old_id}"
            
        # Test business rule: IDs should not be too far in future (prevent clock skew attacks)
        future_timestamp = int((time.time() + (2 * 60 * 60)) * 1000)  # 2 hours future
        future_id = f"future_test_{future_timestamp}_1_abc123"
        assert not UnifiedIdGenerator.is_valid_id(future_id), \
            f"Future ID should not validate: {future_id}"
            
    @pytest.mark.unit
    def test_session_management_business_continuity(self):
        """Test that session management maintains business continuity across user interactions."""
        user_id = "session_user_321"
        operation = "user_session"
        
        # Create initial session
        session1 = UnifiedIdGenerator.get_or_create_user_session(user_id, operation=operation)
        
        assert "thread_id" in session1
        assert "run_id" in session1
        assert "request_id" in session1
        
        initial_thread_id = session1["thread_id"]
        initial_run_id = session1["run_id"]
        
        # Get session again - should maintain continuity
        session2 = UnifiedIdGenerator.get_or_create_user_session(
            user_id, thread_id=initial_thread_id, operation=operation
        )
        
        # Thread ID should be preserved for conversation continuity
        assert session2["thread_id"] == initial_thread_id, \
            "Thread ID should be preserved for session continuity"
            
        # Run ID should be preserved when no new run_id specified
        assert session2["run_id"] == initial_run_id, \
            "Run ID should be preserved for session continuity"
            
        # Request ID should be new for each request
        assert session2["request_id"] != session1["request_id"], \
            "Request ID should be unique for each request"
            
        # Test new run within same thread (different agent execution)
        new_run_id = UnifiedIdGenerator.generate_base_id("new_run")
        session3 = UnifiedIdGenerator.get_or_create_user_session(
            user_id, thread_id=initial_thread_id, run_id=new_run_id, operation=operation
        )
        
        # Thread should be preserved
        assert session3["thread_id"] == initial_thread_id
        # Run should be updated
        assert session3["run_id"] == new_run_id
        # Request should be new
        assert session3["request_id"] not in [session1["request_id"], session2["request_id"]]
        
    @pytest.mark.unit
    def test_batch_id_generation_efficiency(self):
        """Test that batch ID generation provides efficiency for bulk operations."""
        prefix = "batch_test"
        count = 100
        
        # Generate batch of IDs
        batch_ids = UnifiedIdGenerator.generate_batch_ids(prefix, count, include_random=True)
        
        # Should generate exactly the requested count
        assert len(batch_ids) == count, f"Should generate {count} IDs, got {len(batch_ids)}"
        
        # All should have correct prefix
        for id_value in batch_ids:
            assert id_value.startswith(prefix), f"Batch ID should have correct prefix: {id_value}"
            
        # All should be unique
        unique_batch_ids = set(batch_ids)
        assert len(unique_batch_ids) == count, \
            f"All batch IDs should be unique: {len(unique_batch_ids)} unique out of {count}"
            
        # Test without random component for simpler scenarios
        simple_batch = UnifiedIdGenerator.generate_batch_ids(prefix, 10, include_random=False)
        
        for id_value in simple_batch:
            parts = id_value.split('_')
            assert len(parts) == 3, f"Simple batch ID should have 3 parts: {id_value}"
            assert parts[0] == prefix
            
    @pytest.mark.unit
    def test_id_age_calculation_operational_value(self):
        """Test that ID age calculation provides operational value for monitoring and cleanup."""
        # Create ID with current timestamp
        recent_id = UnifiedIdGenerator.generate_base_id("recent_test")
        
        # Age should be very small (just created)
        age_ms = UnifiedIdGenerator.get_id_age(recent_id)
        assert 0 <= age_ms <= 1000, f"Recent ID age should be minimal: {age_ms}ms"
        
        # Test with older simulated ID
        old_timestamp = int((time.time() - 60) * 1000)  # 1 minute ago
        old_id = f"old_test_{old_timestamp}_1_abc123"
        old_age = UnifiedIdGenerator.get_id_age(old_id)
        
        # Should be approximately 1 minute (allowing for processing time)
        assert 50000 <= old_age <= 70000, f"Old ID age should be ~60s: {old_age}ms"
        
        # Test with invalid ID
        invalid_age = UnifiedIdGenerator.get_id_age("invalid_id")
        assert invalid_age == -1, "Invalid ID should return -1 for age"
        
    @pytest.mark.unit
    def test_session_cleanup_business_maintenance(self):
        """Test that session cleanup provides proper business maintenance capabilities."""
        user_id = "cleanup_test_user"
        
        # Create multiple sessions
        for i in range(5):
            UnifiedIdGenerator.get_or_create_user_session(f"{user_id}_{i}", operation="test")
            
        initial_count = UnifiedIdGenerator.get_active_sessions_count()
        assert initial_count >= 5, "Should have at least 5 active sessions"
        
        # Cleanup expired sessions (use very short age for testing)
        cleaned_count = UnifiedIdGenerator.cleanup_expired_sessions(max_age_hours=0)
        
        # Should have cleaned up some sessions
        final_count = UnifiedIdGenerator.get_active_sessions_count()
        assert final_count <= initial_count, "Session count should not increase after cleanup"
        
        # Test user-specific invalidation
        test_user = "specific_user_test"
        UnifiedIdGenerator.get_or_create_user_session(test_user, operation="test")
        UnifiedIdGenerator.get_or_create_user_session(test_user, thread_id="thread1", operation="test")
        
        invalidated_count = UnifiedIdGenerator.invalidate_user_sessions(test_user)
        assert invalidated_count >= 1, f"Should invalidate at least 1 session for user: {invalidated_count}"
        
    @pytest.mark.unit
    def test_uuid_replacement_business_compatibility(self):
        """Test that UUID replacement function maintains business compatibility."""
        # Generate multiple replacements
        replacements = []
        for i in range(50):
            replacement = generate_uuid_replacement()
            replacements.append(replacement)
            
            # Should be 8 characters (original uuid4().hex[:8] format)
            assert len(replacement) == 8, f"UUID replacement should be 8 chars: {replacement}"
            
            # Should be hex characters only
            assert all(c in '0123456789abcdef' for c in replacement.lower()), \
                f"UUID replacement should be hex: {replacement}"
                
        # All should be unique
        unique_replacements = set(replacements)
        assert len(unique_replacements) == len(replacements), \
            "UUID replacements should all be unique"
            
    @pytest.mark.unit
    def test_user_execution_context_factory_integration(self):
        """Test that user execution context factory provides proper business integration."""
        user_id = "factory_test_user"
        operation = "business_operation"
        
        context_data = create_user_execution_context_factory(user_id, operation)
        
        # Should contain all required fields
        required_fields = ['user_id', 'thread_id', 'run_id', 'request_id']
        for field in required_fields:
            assert field in context_data, f"Context should contain {field}"
            assert context_data[field] is not None, f"Context {field} should not be None"
            
        # User ID should match input
        assert context_data['user_id'] == user_id, "User ID should match input"
        
        # IDs should contain operation context
        assert operation in context_data['thread_id'], "Thread ID should contain operation"
        assert operation in context_data['run_id'], "Run ID should contain operation"