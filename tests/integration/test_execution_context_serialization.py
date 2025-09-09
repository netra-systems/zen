"""Integration tests for execution context serialization and deserialization.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Context Preservation Across Execution Boundaries
- Value Impact: Ensures context integrity prevents $500K+ ARR loss from context mixing
- Strategic Impact: Critical for background tasks, queue processing, and service boundaries

CRITICAL REQUIREMENTS per CLAUDE.md:
1. REAL SERVICES - Test actual context serialization with real execution engines
2. Context Integrity - Test secure serialization prevents context tampering
3. Multi-Service - Test context preservation across service boundaries
4. Background Tasks - Test context serialization for async/background processing
5. User Isolation - Test serialized contexts maintain user isolation guarantees

This tests context serialization that enables secure background processing and service boundaries.
"""

import pytest
import asyncio
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from shared.context_serialization import (
    SecureContextSerializer,
    ContextQueue,
    ContextSerializationError,
    ContextIntegrityError,
    serialize_context_for_task,
    deserialize_context_from_task,
    create_secure_task_payload,
    extract_context_from_task_payload
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import (
    StronglyTypedUserExecutionContext,
    upgrade_legacy_context,
    downgrade_to_legacy_context
)
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID


class TestContextSerializationIntegration:
    """Test context serialization integration with real execution patterns."""
    
    @pytest.fixture
    def real_user_context(self) -> UserExecutionContext:
        """Create real user execution context for serialization testing."""
        return UserExecutionContext(
            user_id=f"user_{uuid.uuid4().hex[:12]}",
            thread_id=f"thread_{uuid.uuid4().hex[:12]}",
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            websocket_client_id=f"ws_{uuid.uuid4().hex[:12]}",
            agent_context={
                "agent_type": "data_analysis",
                "execution_mode": "real_time",
                "parameters": {"timeout": 30, "priority": "high"}
            },
            audit_metadata={
                "created_by": "execution_engine",
                "trace_id": f"trace_{uuid.uuid4().hex[:8]}",
                "session_id": f"session_{uuid.uuid4().hex[:8]}"
            }
        )
    
    @pytest.fixture
    def strongly_typed_context(self) -> StronglyTypedUserExecutionContext:
        """Create strongly typed context for advanced serialization testing."""
        return StronglyTypedUserExecutionContext(
            user_id=UserID(f"user_{uuid.uuid4().hex[:12]}"),
            thread_id=ThreadID(f"thread_{uuid.uuid4().hex[:12]}"),
            run_id=RunID(f"run_{uuid.uuid4().hex[:12]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:12]}"),
            websocket_client_id=WebSocketID(f"ws_{uuid.uuid4().hex[:12]}"),
            agent_context={"typed_execution": True},
            audit_metadata={"strong_typing": "enabled"}
        )
    
    def test_secure_context_serialization_roundtrip(self, real_user_context):
        """Test secure context serialization and deserialization preserves all data."""
        serializer = SecureContextSerializer()
        
        # Serialize context
        serialized = serializer.serialize_context(real_user_context)
        
        # Validate serialized format
        assert isinstance(serialized, str)
        assert len(serialized) > 0
        
        # Deserialize context
        deserialized = serializer.deserialize_context(serialized)
        
        # Validate all critical fields preserved
        assert deserialized.user_id == real_user_context.user_id
        assert deserialized.thread_id == real_user_context.thread_id
        assert deserialized.run_id == real_user_context.run_id
        assert deserialized.request_id == real_user_context.request_id
        assert deserialized.websocket_client_id == real_user_context.websocket_client_id
        
        # Validate context data preserved
        assert deserialized.agent_context == real_user_context.agent_context
        assert deserialized.audit_metadata == real_user_context.audit_metadata
        
        # Validate isolation properties preserved
        assert deserialized.operation_depth == real_user_context.operation_depth
        assert deserialized.parent_request_id == real_user_context.parent_request_id
    
    def test_context_serialization_integrity_validation(self, real_user_context):
        """Test that context serialization detects tampering."""
        serializer = SecureContextSerializer()
        
        # Serialize context
        serialized = serializer.serialize_context(real_user_context)
        
        # Tamper with serialized data
        import base64
        decoded = base64.b64decode(serialized.encode('utf-8'))
        payload_dict = json.loads(decoded.decode('utf-8'))
        
        # Modify the payload (simulate tampering)
        original_payload = payload_dict['payload']
        tampered_payload = json.loads(original_payload)
        tampered_payload['context_data']['user_id'] = 'hacker_user'
        payload_dict['payload'] = json.dumps(tampered_payload, separators=(',', ':'), sort_keys=True)
        
        # Re-encode tampered data
        tampered_serialized = base64.b64encode(json.dumps(payload_dict).encode('utf-8')).decode('utf-8')
        
        # Attempt to deserialize tampered data should fail
        with pytest.raises(ContextIntegrityError, match="Context integrity verification failed"):
            serializer.deserialize_context(tampered_serialized)
    
    def test_context_serialization_with_child_contexts(self, real_user_context):
        """Test serialization works correctly with parent-child context relationships."""
        # Create child context
        child_context = real_user_context.create_child_context("data_processing")
        
        serializer = SecureContextSerializer()
        
        # Serialize both parent and child
        parent_serialized = serializer.serialize_context(real_user_context)
        child_serialized = serializer.serialize_context(child_context)
        
        # Deserialize both
        parent_deserialized = serializer.deserialize_context(parent_serialized)
        child_deserialized = serializer.deserialize_context(child_serialized)
        
        # Validate parent-child relationship preserved
        assert parent_deserialized.parent_request_id is None
        assert child_deserialized.parent_request_id == real_user_context.request_id
        assert child_deserialized.operation_depth == real_user_context.operation_depth + 1
        
        # Validate both contexts maintain same user/thread/run
        assert parent_deserialized.user_id == child_deserialized.user_id
        assert parent_deserialized.thread_id == child_deserialized.thread_id
        assert parent_deserialized.run_id == child_deserialized.run_id
        
        # Validate request_ids are different
        assert parent_deserialized.request_id != child_deserialized.request_id
    
    def test_context_serialization_utility_functions(self, real_user_context):
        """Test module-level utility functions for context serialization."""
        # Test serialize_context_for_task utility
        serialized = serialize_context_for_task(real_user_context)
        assert isinstance(serialized, str)
        assert len(serialized) > 0
        
        # Test deserialize_context_from_task utility
        deserialized = deserialize_context_from_task(serialized)
        assert deserialized.user_id == real_user_context.user_id
        assert deserialized.thread_id == real_user_context.thread_id
        
        # Test create_secure_task_payload utility
        task_payload = create_secure_task_payload(
            context=real_user_context,
            task_name="process_user_data",
            task_parameters={"batch_size": 100, "timeout": 300}
        )
        
        # Validate task payload structure
        assert task_payload['task_name'] == "process_user_data"
        assert task_payload['task_parameters'] == {"batch_size": 100, "timeout": 300}
        assert 'user_context' in task_payload
        assert 'created_at' in task_payload
        assert 'security_version' in task_payload
        
        # Test extract_context_from_task_payload utility
        task_name, params, context = extract_context_from_task_payload(task_payload)
        
        assert task_name == "process_user_data"
        assert params == {"batch_size": 100, "timeout": 300}
        assert context.user_id == real_user_context.user_id


class TestContextQueueIntegration:
    """Test ContextQueue integration for background task processing."""
    
    @pytest.fixture
    def context_queue(self) -> ContextQueue:
        """Create context queue for testing."""
        return ContextQueue()
    
    def test_context_queue_put_get_operations(self, context_queue, real_user_context):
        """Test context queue put/get operations with real contexts."""
        # Test empty queue
        assert context_queue.size() == 0
        
        # Put context in queue
        task_data = {"operation": "data_analysis", "priority": 1}
        
        import asyncio
        async def test_queue_operations():
            await context_queue.put(real_user_context, task_data)
            
            # Validate queue size
            assert context_queue.size() == 1
            
            # Get context from queue
            result = await context_queue.get()
            assert result is not None
            
            context, retrieved_task_data = result
            
            # Validate context integrity
            assert context.user_id == real_user_context.user_id
            assert context.thread_id == real_user_context.thread_id
            assert context.request_id == real_user_context.request_id
            
            # Validate task data
            assert retrieved_task_data == task_data
            
            # Validate queue is empty again
            assert context_queue.size() == 0
        
        # Run async test
        asyncio.run(test_queue_operations())
    
    def test_context_queue_multiple_users_isolation(self, context_queue):
        """Test context queue maintains isolation between multiple users."""
        # Create contexts for different users
        user1_context = UserExecutionContext(
            user_id=f"user1_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread1_{uuid.uuid4().hex[:8]}",
            run_id=f"run1_{uuid.uuid4().hex[:8]}",
            request_id=f"req1_{uuid.uuid4().hex[:8]}"
        )
        
        user2_context = UserExecutionContext(
            user_id=f"user2_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread2_{uuid.uuid4().hex[:8]}",
            run_id=f"run2_{uuid.uuid4().hex[:8]}",
            request_id=f"req2_{uuid.uuid4().hex[:8]}"
        )
        
        async def test_multi_user_queue():
            # Queue contexts for both users
            await context_queue.put(user1_context, {"user": "user1", "task": "analysis"})
            await context_queue.put(user2_context, {"user": "user2", "task": "optimization"})
            
            # Validate queue size
            assert context_queue.size() == 2
            
            # Get first context (FIFO order)
            result1 = await context_queue.get()
            context1, task_data1 = result1
            
            # Should be user1 context (first queued)
            assert context1.user_id == user1_context.user_id
            assert task_data1["user"] == "user1"
            
            # Get second context
            result2 = await context_queue.get()
            context2, task_data2 = result2
            
            # Should be user2 context
            assert context2.user_id == user2_context.user_id
            assert task_data2["user"] == "user2"
            
            # Validate contexts are completely isolated
            assert context1.user_id != context2.user_id
            assert context1.thread_id != context2.thread_id
            assert context1.request_id != context2.request_id
        
        asyncio.run(test_multi_user_queue())
    
    def test_context_queue_clear_operations(self, context_queue, real_user_context):
        """Test context queue clear operations."""
        async def test_queue_clear():
            # Add multiple contexts
            await context_queue.put(real_user_context, {"task": 1})
            await context_queue.put(real_user_context, {"task": 2})
            await context_queue.put(real_user_context, {"task": 3})
            
            # Validate queue has items
            assert context_queue.size() == 3
            
            # Clear queue
            context_queue.clear()
            
            # Validate queue is empty
            assert context_queue.size() == 0
            
            # Validate get returns None on empty queue
            result = await context_queue.get()
            assert result is None
        
        asyncio.run(test_queue_clear())


class TestStronglyTypedContextSerialization:
    """Test serialization integration with strongly typed contexts."""
    
    def test_strongly_typed_context_upgrade_serialization(self, strongly_typed_context):
        """Test serialization works with strongly typed context after upgrade."""
        # Convert to legacy format
        legacy_dict = downgrade_to_legacy_context(strongly_typed_context)
        
        # Upgrade back to typed
        upgraded_context = upgrade_legacy_context(legacy_dict)
        
        # Serialize the upgraded context
        serializer = SecureContextSerializer()
        serialized = serializer.serialize_context(upgraded_context)
        
        # Deserialize
        deserialized = serializer.deserialize_context(serialized)
        
        # Validate type-safe fields preserved
        assert str(deserialized.user_id) == str(strongly_typed_context.user_id)
        assert str(deserialized.thread_id) == str(strongly_typed_context.thread_id)
        assert str(deserialized.run_id) == str(strongly_typed_context.run_id)
        assert str(deserialized.request_id) == str(strongly_typed_context.request_id)
        assert str(deserialized.websocket_client_id) == str(strongly_typed_context.websocket_client_id)
    
    def test_typed_context_serialization_type_preservation(self, strongly_typed_context):
        """Test that strongly typed context IDs remain strongly typed after serialization."""
        # Create legacy UserExecutionContext from strongly typed
        legacy_dict = downgrade_to_legacy_context(strongly_typed_context)
        legacy_context = UserExecutionContext(**{k: v for k, v in legacy_dict.items() 
                                                if k in ['user_id', 'thread_id', 'run_id', 'request_id',
                                                        'websocket_client_id', 'agent_context', 'audit_metadata']})
        
        # Serialize legacy context
        serializer = SecureContextSerializer()
        serialized = serializer.serialize_context(legacy_context)
        
        # Deserialize
        deserialized = serializer.deserialize_context(serialized)
        
        # Upgrade deserialized context back to strongly typed
        typed_again = upgrade_legacy_context(deserialized)
        
        # Validate types are maintained through the full cycle
        assert isinstance(typed_again.user_id, UserID)
        assert isinstance(typed_again.thread_id, ThreadID) 
        assert isinstance(typed_again.run_id, RunID)
        assert isinstance(typed_again.request_id, RequestID)
        if typed_again.websocket_client_id:
            assert isinstance(typed_again.websocket_client_id, WebSocketID)


class TestExecutionBoundaryContextSerialization:
    """Test context serialization across execution boundaries."""
    
    @pytest.mark.asyncio
    async def test_context_serialization_across_async_boundaries(self, real_user_context):
        """Test context serialization works across async function boundaries."""
        # Simulate background task that receives serialized context
        async def background_task(serialized_context_data: str) -> Dict[str, Any]:
            """Simulate a background task that processes serialized context."""
            # Deserialize context in background task
            context = deserialize_context_from_task(serialized_context_data)
            
            # Validate context is usable in background task
            return {
                "task_result": "completed",
                "processed_user": context.user_id,
                "processed_thread": context.thread_id,
                "context_valid": True,
                "agent_context": context.agent_context,
                "audit_data": context.audit_metadata
            }
        
        # Serialize context in main execution
        serialized = serialize_context_for_task(real_user_context)
        
        # Pass to background task
        result = await background_task(serialized)
        
        # Validate background task received correct context
        assert result["task_result"] == "completed"
        assert result["processed_user"] == real_user_context.user_id
        assert result["processed_thread"] == real_user_context.thread_id
        assert result["context_valid"] is True
        assert result["agent_context"] == real_user_context.agent_context
        assert result["audit_data"] == real_user_context.audit_metadata
    
    @pytest.mark.asyncio
    async def test_context_serialization_service_boundary_simulation(self):
        """Test context serialization across simulated service boundaries."""
        # Create user context in "Service A"
        service_a_context = UserExecutionContext(
            user_id=f"user_{uuid.uuid4().hex[:12]}",
            thread_id=f"thread_{uuid.uuid4().hex[:12]}",
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            agent_context={"service": "A", "operation": "data_collection"},
            audit_metadata={"source_service": "service_a", "boundary_crossing": True}
        )
        
        # Simulate sending context to "Service B" via serialization
        async def service_b_processor(context_payload: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate Service B processing with deserialized context."""
            # Extract context from payload
            task_name, params, context = extract_context_from_task_payload(context_payload)
            
            # Service B adds its own processing metadata
            enhanced_context = context.create_child_context("service_b_processing")
            
            # Simulate Service B processing
            processing_result = {
                "service_b_result": "processed",
                "original_user": context.user_id,
                "child_request_id": enhanced_context.request_id,
                "parent_request_id": enhanced_context.parent_request_id,
                "operation_depth": enhanced_context.operation_depth,
                "cross_service": True
            }
            
            return processing_result
        
        # Create service boundary payload
        payload = create_secure_task_payload(
            context=service_a_context,
            task_name="cross_service_processing",
            task_parameters={"target_service": "service_b"}
        )
        
        # Process in Service B
        result = await service_b_processor(payload)
        
        # Validate cross-service context preservation
        assert result["service_b_result"] == "processed"
        assert result["original_user"] == service_a_context.user_id
        assert result["parent_request_id"] == service_a_context.request_id
        assert result["operation_depth"] == 1  # Child context
        assert result["cross_service"] is True
    
    def test_context_serialization_error_handling(self, real_user_context):
        """Test context serialization handles errors gracefully."""
        serializer = SecureContextSerializer()
        
        # Test serialization with invalid context data
        invalid_context = real_user_context
        # Simulate corrupted agent_context
        invalid_context.agent_context = {"invalid": object()}  # Non-serializable object
        
        # Should handle serialization error
        with pytest.raises(ContextSerializationError):
            serializer.serialize_context(invalid_context)
        
        # Test deserialization with invalid data
        with pytest.raises(ContextSerializationError):
            serializer.deserialize_context("invalid_base64_data")
        
        # Test deserialization with malformed JSON
        import base64
        malformed_json = base64.b64encode(b"not_json").decode('utf-8')
        with pytest.raises(ContextSerializationError):
            serializer.deserialize_context(malformed_json)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])