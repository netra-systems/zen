"""
Focused Integration Test: UserExecutionContext Isolation Patterns

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure UserExecutionContext provides complete user isolation
- Value Impact: Validates multi-user platform isolation, prevents user data leakage
- Strategic Impact: Critical for multi-user business model and regulatory compliance

Tests UserExecutionContext SSOT isolation patterns:
- Context creation and immutability validation
- Context passing between components without leakage
- Context isolation validation (different users)
- Context metadata and threading patterns
- Context factory methods and child context creation

This is a NON-DOCKER integration test that focuses on core UserExecutionContext SSOT patterns.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context,
    InvalidContextError,
    clear_shared_objects,
    register_shared_object
)

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment


class TestUserExecutionContextIsolation(BaseIntegrationTest):
    """Focused integration tests for UserExecutionContext isolation SSOT patterns."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_MODE", "true", source="test")
        # Clear shared objects registry for clean testing
        clear_shared_objects()
        
    @pytest.fixture
    async def test_user_context(self):
        """Create test user execution context."""
        context = UserExecutionContext(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            websocket_connection_id=f"ws_conn_{uuid.uuid4().hex[:8]}",
            metadata={
                "user_request": "Test user request for isolation validation",
                "request_type": "isolation_test"
            }
        )
        return context
    
    @pytest.fixture
    async def mock_db_session(self):
        """Create mock database session."""
        mock_session = AsyncMock(spec=AsyncSession)
        return mock_session
    
    @pytest.mark.integration
    async def test_user_execution_context_immutability_patterns(self, test_user_context):
        """Test UserExecutionContext immutability SSOT patterns."""
        
        # Validate basic immutability (frozen dataclass)
        original_user_id = test_user_context.user_id
        original_thread_id = test_user_context.thread_id
        original_run_id = test_user_context.run_id
        original_metadata = test_user_context.metadata.copy()
        
        # Test that direct modification raises exception
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            test_user_context.user_id = "modified_user"
            
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            test_user_context.thread_id = "modified_thread"
            
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            test_user_context.run_id = "modified_run"
        
        # Verify values remain unchanged
        assert test_user_context.user_id == original_user_id
        assert test_user_context.thread_id == original_thread_id
        assert test_user_context.run_id == original_run_id
        assert test_user_context.metadata == original_metadata
        
        # Test metadata isolation (should be separate dict instance)
        assert id(test_user_context.metadata) != id(original_metadata)
        
        self.logger.info(" PASS:  UserExecutionContext immutability patterns validated")
    
    @pytest.mark.integration
    async def test_user_execution_context_creation_patterns(self):
        """Test UserExecutionContext creation patterns and validation."""
        
        # Test successful creation with all valid data
        context = UserExecutionContext(
            user_id="integration_user_12345",
            thread_id="integration_thread_67890", 
            run_id="integration_run_abcde",
            metadata={"test": "creation_patterns"}
        )
        
        assert context.user_id == "integration_user_12345"
        assert context.thread_id == "integration_thread_67890"
        assert context.run_id == "integration_run_abcde"
        assert context.metadata["test"] == "creation_patterns"
        assert context.request_id is not None
        assert len(context.request_id) > 0
        
        # Test factory method creation
        factory_context = UserExecutionContext.from_request(
            user_id="factory_user_98765",
            thread_id="factory_thread_54321",
            run_id="factory_run_zyxwv",
            metadata={"factory": "creation_test"}
        )
        
        assert factory_context.user_id == "factory_user_98765"
        assert factory_context.thread_id == "factory_thread_54321"
        assert factory_context.run_id == "factory_run_zyxwv"
        assert factory_context.metadata["factory"] == "creation_test"
        
        # Test creation validation failures
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="",  # Empty user_id should fail
                thread_id="valid_thread",
                run_id="valid_run"
            )
        
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="placeholder",  # Dangerous placeholder value should fail
                thread_id="valid_thread",
                run_id="valid_run"
            )
        
        self.logger.info(" PASS:  UserExecutionContext creation patterns validated")
    
    @pytest.mark.integration
    async def test_user_execution_context_isolation_between_users(self):
        """Test UserExecutionContext provides complete isolation between different users."""
        
        # Create contexts for two different users
        user1_context = UserExecutionContext(
            user_id="isolation_user_1_alpha",
            thread_id="isolation_thread_1_beta",
            run_id="isolation_run_1_gamma",
            metadata={
                "user_data": "sensitive_user_1_data",
                "user_preference": "user_1_preference"
            }
        )
        
        user2_context = UserExecutionContext(
            user_id="isolation_user_2_delta",
            thread_id="isolation_thread_2_epsilon",
            run_id="isolation_run_2_zeta",
            metadata={
                "user_data": "sensitive_user_2_data",
                "user_preference": "user_2_preference"
            }
        )
        
        # Validate complete isolation
        assert user1_context.user_id != user2_context.user_id
        assert user1_context.thread_id != user2_context.thread_id
        assert user1_context.run_id != user2_context.run_id
        assert user1_context.request_id != user2_context.request_id
        
        # Validate metadata isolation (separate instances and data)
        assert id(user1_context.metadata) != id(user2_context.metadata)
        assert user1_context.metadata["user_data"] != user2_context.metadata["user_data"]
        assert user1_context.metadata["user_preference"] != user2_context.metadata["user_preference"]
        
        # Validate correlation IDs are different
        assert user1_context.get_correlation_id() != user2_context.get_correlation_id()
        
        # Validate isolation verification passes for both
        assert user1_context.verify_isolation() is True
        assert user2_context.verify_isolation() is True
        
        # Validate serialization isolation
        user1_dict = user1_context.to_dict()
        user2_dict = user2_context.to_dict()
        assert user1_dict != user2_dict
        assert user1_dict["user_id"] != user2_dict["user_id"]
        
        self.logger.info(" PASS:  UserExecutionContext isolation between users validated")
    
    @pytest.mark.integration
    async def test_user_execution_context_database_session_patterns(self, mock_db_session):
        """Test UserExecutionContext database session handling patterns."""
        
        # Create context without database session
        context_without_db = UserExecutionContext(
            user_id="db_test_user_alpha",
            thread_id="db_test_thread_beta",
            run_id="db_test_run_gamma"
        )
        
        assert context_without_db.db_session is None
        
        # Create context with database session using with_db_session method
        context_with_db = context_without_db.with_db_session(mock_db_session)
        
        # Validate immutability - original context unchanged
        assert context_without_db.db_session is None
        # New context has session
        assert context_with_db.db_session is mock_db_session
        
        # Validate all other data preserved
        assert context_with_db.user_id == context_without_db.user_id
        assert context_with_db.thread_id == context_without_db.thread_id
        assert context_with_db.run_id == context_without_db.run_id
        assert context_with_db.request_id == context_without_db.request_id
        
        # Validate metadata is copied, not shared
        assert id(context_with_db.metadata) != id(context_without_db.metadata)
        assert context_with_db.metadata == context_without_db.metadata
        
        # Test serialization excludes db_session but tracks its presence
        serialized = context_with_db.to_dict()
        assert "db_session" not in serialized
        assert serialized["has_db_session"] is True
        
        self.logger.info(" PASS:  UserExecutionContext database session patterns validated")
    
    @pytest.mark.integration
    async def test_user_execution_context_child_context_patterns(self):
        """Test UserExecutionContext child context creation patterns."""
        
        # Create parent context
        parent_context = UserExecutionContext(
            user_id="parent_user_delta",
            thread_id="parent_thread_epsilon",
            run_id="parent_run_zeta",
            metadata={
                "parent_data": "parent_specific_info",
                "shared_data": "data_for_children"
            }
        )
        
        # Create child context for sub-operation
        child_context = parent_context.create_child_context(
            operation_name="data_processing",
            additional_metadata={"child_specific": "child_data"}
        )
        
        # Validate parent data inherited
        assert child_context.user_id == parent_context.user_id
        assert child_context.thread_id == parent_context.thread_id
        assert child_context.run_id == parent_context.run_id
        assert child_context.db_session == parent_context.db_session
        assert child_context.websocket_connection_id == parent_context.websocket_connection_id
        
        # Validate child gets new request_id
        assert child_context.request_id != parent_context.request_id
        
        # Validate metadata inheritance and enhancement
        assert child_context.metadata["parent_data"] == "parent_specific_info"
        assert child_context.metadata["shared_data"] == "data_for_children"
        assert child_context.metadata["child_specific"] == "child_data"
        assert child_context.metadata["operation_name"] == "data_processing"
        assert child_context.metadata["parent_request_id"] == parent_context.request_id
        assert child_context.metadata["operation_depth"] == 1
        
        # Validate metadata isolation (separate instances)
        assert id(child_context.metadata) != id(parent_context.metadata)
        
        # Create grandchild context
        grandchild_context = child_context.create_child_context(
            operation_name="result_formatting"
        )
        
        assert grandchild_context.metadata["operation_depth"] == 2
        assert grandchild_context.metadata["parent_request_id"] == child_context.request_id
        assert grandchild_context.user_id == parent_context.user_id
        
        self.logger.info(" PASS:  UserExecutionContext child context patterns validated")
    
    @pytest.mark.integration
    async def test_user_execution_context_websocket_connection_patterns(self):
        """Test UserExecutionContext WebSocket connection handling patterns."""
        
        # Create context without WebSocket connection
        context_without_ws = UserExecutionContext(
            user_id="ws_test_user_alpha",
            thread_id="ws_test_thread_beta", 
            run_id="ws_test_run_gamma"
        )
        
        assert context_without_ws.websocket_connection_id is None
        
        # Add WebSocket connection using with_websocket_connection method
        ws_connection_id = f"ws_conn_{uuid.uuid4().hex[:8]}"
        context_with_ws = context_without_ws.with_websocket_connection(ws_connection_id)
        
        # Validate immutability - original context unchanged
        assert context_without_ws.websocket_connection_id is None
        # New context has WebSocket connection
        assert context_with_ws.websocket_connection_id == ws_connection_id
        
        # Validate all other data preserved
        assert context_with_ws.user_id == context_without_ws.user_id
        assert context_with_ws.thread_id == context_without_ws.thread_id
        assert context_with_ws.run_id == context_without_ws.run_id
        assert context_with_ws.request_id == context_without_ws.request_id
        
        # Validate metadata is copied, not shared
        assert id(context_with_ws.metadata) != id(context_without_ws.metadata)
        assert context_with_ws.metadata == context_without_ws.metadata
        
        # Test serialization includes WebSocket connection ID
        serialized = context_with_ws.to_dict()
        assert serialized["websocket_connection_id"] == ws_connection_id
        
        self.logger.info(" PASS:  UserExecutionContext WebSocket connection patterns validated")
    
    @pytest.mark.integration
    async def test_user_execution_context_concurrent_isolation_safety(self):
        """Test UserExecutionContext maintains isolation under concurrent operations."""
        
        async def create_and_modify_context(user_suffix: str) -> Dict[str, Any]:
            """Create a context and perform operations to test concurrent safety."""
            context = UserExecutionContext(
                user_id=f"concurrent_user_{user_suffix}",
                thread_id=f"concurrent_thread_{user_suffix}",
                run_id=f"concurrent_run_{user_suffix}",
                metadata={
                    "user_data": f"sensitive_data_{user_suffix}",
                    "processing_step": "initial"
                }
            )
            
            # Simulate concurrent operations
            await asyncio.sleep(0.001)  # Small delay to allow interleaving
            
            # Create child context
            child_context = context.create_child_context(
                operation_name=f"process_{user_suffix}",
                additional_metadata={"step": "processing"}
            )
            
            await asyncio.sleep(0.001)  # Another small delay
            
            # Create another child
            final_context = child_context.create_child_context(
                operation_name=f"finalize_{user_suffix}"
            )
            
            return {
                "original_user_id": context.user_id,
                "child_user_id": child_context.user_id,
                "final_user_id": final_context.user_id,
                "original_metadata": context.metadata,
                "child_metadata": child_context.metadata,
                "final_metadata": final_context.metadata
            }
        
        # Run multiple concurrent operations
        tasks = []
        for i in range(5):
            task = create_and_modify_context(f"test_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Validate no cross-contamination between concurrent operations
        user_ids = set()
        for i, result in enumerate(results):
            expected_user_id = f"concurrent_user_test_{i}"
            
            # All contexts for this user should have same user_id
            assert result["original_user_id"] == expected_user_id
            assert result["child_user_id"] == expected_user_id
            assert result["final_user_id"] == expected_user_id
            
            # Each user should have unique user_id
            assert result["original_user_id"] not in user_ids
            user_ids.add(result["original_user_id"])
            
            # Metadata should be specific to this user
            expected_data = f"sensitive_data_test_{i}"
            assert result["original_metadata"]["user_data"] == expected_data
            assert result["child_metadata"]["user_data"] == expected_data
            assert result["final_metadata"]["user_data"] == expected_data
        
        # Validate all users had unique IDs
        assert len(user_ids) == 5
        
        self.logger.info(" PASS:  UserExecutionContext concurrent isolation safety validated")


# Additional helper functions for context validation

def validate_context_isolation(context1: UserExecutionContext, context2: UserExecutionContext) -> None:
    """Validate that two contexts are completely isolated."""
    # ID isolation
    assert context1.user_id != context2.user_id
    assert context1.thread_id != context2.thread_id
    assert context1.run_id != context2.run_id
    assert context1.request_id != context2.request_id
    
    # Metadata isolation (separate instances)
    assert id(context1.metadata) != id(context2.metadata)
    
    # Isolation verification passes
    assert context1.verify_isolation() is True
    assert context2.verify_isolation() is True


def validate_context_immutability(context: UserExecutionContext) -> None:
    """Validate that a context is properly immutable."""
    original_data = {
        "user_id": context.user_id,
        "thread_id": context.thread_id,
        "run_id": context.run_id,
        "metadata": context.metadata.copy()
    }
    
    # Test that context attributes cannot be modified
    with pytest.raises(Exception):
        context.user_id = "modified"
    
    with pytest.raises(Exception):
        context.thread_id = "modified"
    
    with pytest.raises(Exception):
        context.run_id = "modified"
    
    # Verify data unchanged
    assert context.user_id == original_data["user_id"]
    assert context.thread_id == original_data["thread_id"] 
    assert context.run_id == original_data["run_id"]
    assert context.metadata == original_data["metadata"]


def validate_context_structure(context: UserExecutionContext) -> None:
    """Validate that a context has the expected SSOT structure."""
    # Required fields present and non-empty
    assert isinstance(context.user_id, str) and len(context.user_id) > 0
    assert isinstance(context.thread_id, str) and len(context.thread_id) > 0
    assert isinstance(context.run_id, str) and len(context.run_id) > 0
    assert isinstance(context.request_id, str) and len(context.request_id) > 0
    
    # Metadata is a dict
    assert isinstance(context.metadata, dict)
    
    # Created timestamp exists
    assert isinstance(context.created_at, datetime)
    
    # Passes validate_user_context check
    validated = validate_user_context(context)
    assert validated is context