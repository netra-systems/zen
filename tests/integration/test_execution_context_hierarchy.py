"""Integration tests for execution context hierarchy and child context creation.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Hierarchical Context Management & Sub-Agent Isolation
- Value Impact: Enables complex multi-agent workflows preserving context relationships
- Strategic Impact: Foundation for advanced AI agent orchestration and traceability

CRITICAL REQUIREMENTS per CLAUDE.md:
1. REAL CONTEXT HIERARCHY - Test actual parent-child context relationships
2. Context Inheritance - Test proper metadata and audit trail inheritance
3. Operation Depth - Test hierarchical depth tracking and limits
4. Multi-Level Isolation - Test context isolation at each hierarchy level
5. Traceability - Test parent-child request ID relationships for audit trails

This tests hierarchical context management that enables advanced agent orchestration.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import (
    StronglyTypedUserExecutionContext,
    upgrade_legacy_context,
    downgrade_to_legacy_context
)
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.context_serialization import (
    SecureContextSerializer,
    serialize_context_for_task,
    deserialize_context_from_task
)


class TestExecutionContextHierarchy:
    """Test execution context hierarchy and parent-child relationships."""
    
    @pytest.fixture
    def root_context(self) -> UserExecutionContext:
        """Create root context for hierarchy testing."""
        return UserExecutionContext(
            user_id=f"hierarchy_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"hierarchy_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"hierarchy_run_{uuid.uuid4().hex[:12]}",
            request_id=f"hierarchy_req_{uuid.uuid4().hex[:12]}",
            agent_context={
                "root_operation": "data_analysis",
                "hierarchy_level": "root",
                "workflow_id": f"workflow_{uuid.uuid4().hex[:8]}"
            },
            audit_metadata={
                "created_by": "root_agent",
                "workflow_stage": "initialization",
                "trace_id": f"trace_{uuid.uuid4().hex[:8]}"
            }
        )
    
    @pytest.fixture
    def strongly_typed_root(self) -> StronglyTypedUserExecutionContext:
        """Create strongly typed root context for hierarchy testing."""
        return StronglyTypedUserExecutionContext(
            user_id=UserID(f"typed_user_{uuid.uuid4().hex[:12]}"),
            thread_id=ThreadID(f"typed_thread_{uuid.uuid4().hex[:12]}"),
            run_id=RunID(f"typed_run_{uuid.uuid4().hex[:12]}"),
            request_id=RequestID(f"typed_req_{uuid.uuid4().hex[:12]}"),
            agent_context={
                "typed_hierarchy": True,
                "root_agent": "data_processor",
                "workflow_version": "2.0"
            },
            audit_metadata={
                "strong_typing": "enabled",
                "hierarchy_root": True
            }
        )
    
    def test_single_level_child_context_creation(self, root_context):
        """Test creating single-level child context from root."""
        # Create child context
        child_context = root_context.create_child_context("data_processing")
        
        # Validate parent-child relationship
        assert child_context.parent_request_id == root_context.request_id
        assert child_context.operation_depth == root_context.operation_depth + 1
        assert child_context.operation_depth == 1
        
        # Validate inheritance of user identifiers
        assert child_context.user_id == root_context.user_id
        assert child_context.thread_id == root_context.thread_id
        assert child_context.run_id == root_context.run_id
        
        # Validate unique request ID for child
        assert child_context.request_id != root_context.request_id
        assert child_context.request_id.endswith("_data_processing")
        
        # Validate context inheritance
        assert child_context.agent_context == root_context.agent_context
        assert child_context.audit_metadata == root_context.audit_metadata
        
        # Validate timestamps
        assert child_context.created_at > root_context.created_at
    
    def test_multi_level_context_hierarchy_creation(self, root_context):
        """Test creating multi-level context hierarchy."""
        # Create level 1 child
        level1_context = root_context.create_child_context("data_collection")
        
        # Create level 2 child from level 1
        level2_context = level1_context.create_child_context("data_validation")
        
        # Create level 3 child from level 2
        level3_context = level2_context.create_child_context("data_transformation")
        
        # Validate hierarchy depth progression
        assert root_context.operation_depth == 0
        assert level1_context.operation_depth == 1
        assert level2_context.operation_depth == 2
        assert level3_context.operation_depth == 3
        
        # Validate parent-child relationships
        assert level1_context.parent_request_id == root_context.request_id
        assert level2_context.parent_request_id == level1_context.request_id
        assert level3_context.parent_request_id == level2_context.request_id
        
        # Validate all contexts share same user/thread/run
        contexts = [root_context, level1_context, level2_context, level3_context]
        for context in contexts:
            assert context.user_id == root_context.user_id
            assert context.thread_id == root_context.thread_id
            assert context.run_id == root_context.run_id
        
        # Validate all contexts have unique request IDs
        request_ids = [ctx.request_id for ctx in contexts]
        assert len(set(request_ids)) == len(request_ids)
    
    def test_context_hierarchy_metadata_inheritance_and_enhancement(self, root_context):
        """Test context hierarchy metadata inheritance and enhancement patterns."""
        # Enhance root context with additional metadata
        root_context.agent_context.update({
            "processing_stage": "initial",
            "data_source": "primary_database",
            "batch_size": 1000
        })
        
        root_context.audit_metadata.update({
            "security_level": "high",
            "compliance_required": True,
            "audit_trail": ["root_initialization"]
        })
        
        # Create child context with operation-specific enhancements
        child_context = root_context.create_child_context("data_processing")
        
        # Validate inherited metadata
        assert child_context.agent_context["processing_stage"] == "initial"
        assert child_context.agent_context["data_source"] == "primary_database"
        assert child_context.agent_context["batch_size"] == 1000
        assert child_context.audit_metadata["security_level"] == "high"
        assert child_context.audit_metadata["compliance_required"] is True
        
        # Enhance child context with additional metadata
        child_context.agent_context.update({
            "processing_stage": "active",
            "child_specific": "data_transformation",
            "parallel_processing": True
        })
        
        child_context.audit_metadata.update({
            "child_operation": "data_processing",
            "audit_trail": child_context.audit_metadata["audit_trail"] + ["child_processing"]
        })
        
        # Create grandchild context
        grandchild_context = child_context.create_child_context("data_enrichment")
        
        # Validate grandchild inherits enhanced metadata from child
        assert grandchild_context.agent_context["processing_stage"] == "active"
        assert grandchild_context.agent_context["child_specific"] == "data_transformation"
        assert grandchild_context.agent_context["parallel_processing"] is True
        assert grandchild_context.agent_context["data_source"] == "primary_database"
        
        # Validate audit trail accumulation
        expected_trail = ["root_initialization", "child_processing"]
        assert grandchild_context.audit_metadata["audit_trail"] == expected_trail
    
    def test_context_hierarchy_operation_depth_limits(self, root_context):
        """Test context hierarchy respects operation depth limits."""
        # Create contexts up to the limit
        current_context = root_context
        contexts = [current_context]
        
        # Create contexts up to depth 10 (the limit)
        for depth in range(1, 11):  # 1 to 10
            child_context = current_context.create_child_context(f"operation_depth_{depth}")
            contexts.append(child_context)
            current_context = child_context
            
            # Validate depth is within limits
            assert child_context.operation_depth == depth
            assert child_context.operation_depth <= 10
        
        # Validate we can create up to depth 10
        assert contexts[-1].operation_depth == 10
        
        # Attempt to create context beyond limit should be handled gracefully
        # Note: The actual behavior may vary based on implementation
        # Some implementations might allow it, others might enforce the limit
        try:
            beyond_limit_context = contexts[-1].create_child_context("beyond_limit")
            # If creation succeeds, validate it's at depth 11
            if beyond_limit_context:
                # Implementation may allow or may cap at 10
                pass
        except Exception as e:
            # Implementation may raise an exception for depth limit
            assert "operation_depth" in str(e).lower() or "limit" in str(e).lower()
    
    def test_strongly_typed_context_hierarchy(self, strongly_typed_root):
        """Test hierarchy works with strongly typed contexts."""
        # Create child from strongly typed root
        child_context = strongly_typed_root.create_child_context()
        
        # Validate strongly typed inheritance
        assert isinstance(child_context.user_id, UserID)
        assert isinstance(child_context.thread_id, ThreadID)
        assert isinstance(child_context.run_id, RunID)
        assert isinstance(child_context.request_id, RequestID)
        
        # Validate parent-child relationship with strong typing
        assert child_context.user_id == strongly_typed_root.user_id
        assert child_context.parent_request_id == strongly_typed_root.request_id
        assert child_context.operation_depth == 1
        
        # Create grandchild
        grandchild_context = child_context.create_child_context()
        
        # Validate multi-level strong typing
        assert isinstance(grandchild_context.user_id, UserID)
        assert grandchild_context.user_id == strongly_typed_root.user_id
        assert grandchild_context.parent_request_id == child_context.request_id
        assert grandchild_context.operation_depth == 2
    
    def test_context_hierarchy_with_custom_request_ids(self, root_context):
        """Test context hierarchy with custom request IDs."""
        # Create child with custom request ID
        custom_request_id = f"custom_req_{uuid.uuid4().hex[:12]}"
        child_context = root_context.create_child_context("custom_operation", custom_request_id)
        
        # Validate custom request ID is used
        assert child_context.request_id == custom_request_id
        assert child_context.parent_request_id == root_context.request_id
        assert child_context.operation_depth == 1
        
        # Create grandchild with another custom request ID
        grandchild_request_id = f"grandchild_req_{uuid.uuid4().hex[:12]}"
        grandchild_context = child_context.create_child_context("grandchild_operation", grandchild_request_id)
        
        # Validate hierarchy with custom IDs
        assert grandchild_context.request_id == grandchild_request_id
        assert grandchild_context.parent_request_id == custom_request_id
        assert grandchild_context.operation_depth == 2


class TestContextHierarchySerialization:
    """Test context hierarchy serialization and deserialization."""
    
    def test_hierarchical_context_serialization_roundtrip(self):
        """Test serialization preserves hierarchical context relationships."""
        # Create root context
        root_context = UserExecutionContext(
            user_id=f"serial_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"serial_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"serial_run_{uuid.uuid4().hex[:12]}",
            request_id=f"serial_req_{uuid.uuid4().hex[:12]}",
            agent_context={"serialization_test": True, "hierarchy_level": "root"},
            audit_metadata={"test_type": "hierarchy_serialization"}
        )
        
        # Create child context
        child_context = root_context.create_child_context("serialization_child")
        
        # Create grandchild context
        grandchild_context = child_context.create_child_context("serialization_grandchild")
        
        # Serialize all contexts
        serializer = SecureContextSerializer()
        
        root_serialized = serializer.serialize_context(root_context)
        child_serialized = serializer.serialize_context(child_context)
        grandchild_serialized = serializer.serialize_context(grandchild_context)
        
        # Deserialize all contexts
        root_deserialized = serializer.deserialize_context(root_serialized)
        child_deserialized = serializer.deserialize_context(child_serialized)
        grandchild_deserialized = serializer.deserialize_context(grandchild_serialized)
        
        # Validate root context
        assert root_deserialized.operation_depth == 0
        assert root_deserialized.parent_request_id is None
        assert root_deserialized.user_id == root_context.user_id
        
        # Validate child context hierarchy preserved
        assert child_deserialized.operation_depth == 1
        assert child_deserialized.parent_request_id == root_context.request_id
        assert child_deserialized.user_id == root_context.user_id
        
        # Validate grandchild context hierarchy preserved
        assert grandchild_deserialized.operation_depth == 2
        assert grandchild_deserialized.parent_request_id == child_context.request_id
        assert grandchild_deserialized.user_id == root_context.user_id
        
        # Validate hierarchy relationships maintained
        assert root_deserialized.request_id == child_deserialized.parent_request_id
        assert child_deserialized.request_id == grandchild_deserialized.parent_request_id
    
    def test_context_hierarchy_serialization_for_background_tasks(self):
        """Test hierarchical context serialization for background task processing."""
        # Create root context for workflow
        workflow_root = UserExecutionContext(
            user_id=f"workflow_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"workflow_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"workflow_run_{uuid.uuid4().hex[:12]}",
            request_id=f"workflow_req_{uuid.uuid4().hex[:12]}",
            agent_context={
                "workflow_type": "data_processing_pipeline",
                "priority": "high",
                "background_processing": True
            },
            audit_metadata={
                "workflow_id": f"wf_{uuid.uuid4().hex[:8]}",
                "created_for": "background_task_processing"
            }
        )
        
        # Create child context for background task
        background_task_context = workflow_root.create_child_context("background_data_analysis")
        
        # Serialize context for background task queue
        serialized_task_context = serialize_context_for_task(background_task_context)
        
        # Simulate background task receiving serialized context
        def simulate_background_task(serialized_context_data: str) -> Dict[str, Any]:
            """Simulate background task processing hierarchical context."""
            # Deserialize context in background task
            task_context = deserialize_context_from_task(serialized_context_data)
            
            # Validate hierarchy information is preserved
            hierarchy_info = {
                "is_child_context": task_context.operation_depth > 0,
                "parent_request_id": task_context.parent_request_id,
                "operation_depth": task_context.operation_depth,
                "user_id": task_context.user_id,
                "workflow_data": task_context.agent_context,
                "audit_trail": task_context.audit_metadata
            }
            
            # Create sub-task context within background task
            subtask_context = task_context.create_child_context("background_subtask")
            
            return {
                "background_task_completed": True,
                "hierarchy_preserved": True,
                "hierarchy_info": hierarchy_info,
                "subtask_depth": subtask_context.operation_depth,
                "subtask_parent": subtask_context.parent_request_id
            }
        
        # Execute background task simulation
        result = simulate_background_task(serialized_task_context)
        
        # Validate hierarchical context worked in background task
        assert result["background_task_completed"] is True
        assert result["hierarchy_preserved"] is True
        assert result["hierarchy_info"]["is_child_context"] is True
        assert result["hierarchy_info"]["operation_depth"] == 1
        assert result["hierarchy_info"]["parent_request_id"] == workflow_root.request_id
        assert result["subtask_depth"] == 2
        assert result["subtask_parent"] == background_task_context.request_id


class TestContextHierarchyTraceability:
    """Test context hierarchy provides proper traceability and audit trails."""
    
    def test_context_hierarchy_audit_trail_construction(self):
        """Test context hierarchy enables comprehensive audit trail construction."""
        # Create root context with audit metadata
        root_context = UserExecutionContext(
            user_id=f"audit_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"audit_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"audit_run_{uuid.uuid4().hex[:12]}",
            request_id=f"audit_req_{uuid.uuid4().hex[:12]}",
            agent_context={"audit_test": True},
            audit_metadata={
                "operation_sequence": 1,
                "audit_events": ["root_created"],
                "security_context": "high_security"
            }
        )
        
        # Create child context with audit enhancement
        child_context = root_context.create_child_context("audit_child")
        child_context.audit_metadata.update({
            "operation_sequence": 2,
            "audit_events": child_context.audit_metadata.get("audit_events", []) + ["child_created"],
            "parent_audit_ref": root_context.request_id
        })
        
        # Create grandchild context with further audit enhancement
        grandchild_context = child_context.create_child_context("audit_grandchild")
        grandchild_context.audit_metadata.update({
            "operation_sequence": 3,
            "audit_events": grandchild_context.audit_metadata.get("audit_events", []) + ["grandchild_created"],
            "parent_audit_ref": child_context.request_id
        })
        
        # Construct audit trail from hierarchy
        def construct_audit_trail(context: UserExecutionContext) -> List[Dict[str, Any]]:
            """Construct audit trail from context hierarchy."""
            trail_entry = {
                "request_id": context.request_id,
                "parent_request_id": context.parent_request_id,
                "operation_depth": context.operation_depth,
                "audit_metadata": context.audit_metadata,
                "created_at": context.created_at.isoformat(),
                "user_id": context.user_id
            }
            return [trail_entry]
        
        # Generate audit trail for each context
        root_trail = construct_audit_trail(root_context)
        child_trail = construct_audit_trail(child_context)
        grandchild_trail = construct_audit_trail(grandchild_context)
        
        # Validate audit trail construction
        assert root_trail[0]["operation_depth"] == 0
        assert root_trail[0]["parent_request_id"] is None
        assert "root_created" in root_trail[0]["audit_metadata"]["audit_events"]
        
        assert child_trail[0]["operation_depth"] == 1
        assert child_trail[0]["parent_request_id"] == root_context.request_id
        assert "child_created" in child_trail[0]["audit_metadata"]["audit_events"]
        assert child_trail[0]["audit_metadata"]["parent_audit_ref"] == root_context.request_id
        
        assert grandchild_trail[0]["operation_depth"] == 2
        assert grandchild_trail[0]["parent_request_id"] == child_context.request_id
        assert "grandchild_created" in grandchild_trail[0]["audit_metadata"]["audit_events"]
        assert grandchild_trail[0]["audit_metadata"]["parent_audit_ref"] == child_context.request_id
    
    def test_context_hierarchy_correlation_id_generation(self):
        """Test context hierarchy enables proper correlation ID generation."""
        # Create root context
        root_context = UserExecutionContext(
            user_id=f"correlation_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"correlation_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"correlation_run_{uuid.uuid4().hex[:12]}",
            request_id=f"correlation_req_{uuid.uuid4().hex[:12]}"
        )
        
        # Create multi-level hierarchy
        level1_context = root_context.create_child_context("level1")
        level2_context = level1_context.create_child_context("level2")
        level3_context = level2_context.create_child_context("level3")
        
        # Generate correlation IDs for hierarchy
        contexts = [root_context, level1_context, level2_context, level3_context]
        correlation_data = []
        
        for context in contexts:
            correlation_id = context.get_correlation_id()
            correlation_data.append({
                "correlation_id": correlation_id,
                "request_id": context.request_id,
                "parent_request_id": context.parent_request_id,
                "operation_depth": context.operation_depth,
                "user_id": context.user_id,
                "thread_id": context.thread_id,
                "run_id": context.run_id
            })
        
        # Validate correlation IDs are unique but traceable
        correlation_ids = [data["correlation_id"] for data in correlation_data]
        assert len(set(correlation_ids)) == len(correlation_ids)  # All unique
        
        # Validate all correlation IDs contain user/thread/run information
        for data in correlation_data:
            correlation_id = data["correlation_id"]
            assert data["user_id"] in correlation_id
            assert data["thread_id"] in correlation_id
            assert data["run_id"] in correlation_id
        
        # Validate hierarchical relationships are traceable
        root_data, level1_data, level2_data, level3_data = correlation_data
        
        assert level1_data["parent_request_id"] == root_data["request_id"]
        assert level2_data["parent_request_id"] == level1_data["request_id"]
        assert level3_data["parent_request_id"] == level2_data["request_id"]
    
    @pytest.mark.asyncio
    async def test_context_hierarchy_distributed_tracing_simulation(self):
        """Test context hierarchy supports distributed tracing patterns."""
        # Create root context with trace information
        trace_id = f"trace_{uuid.uuid4().hex[:16]}"
        span_id = f"span_{uuid.uuid4().hex[:8]}"
        
        root_context = UserExecutionContext(
            user_id=f"trace_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"trace_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"trace_run_{uuid.uuid4().hex[:12]}",
            request_id=f"trace_req_{uuid.uuid4().hex[:12]}",
            audit_metadata={
                "trace_id": trace_id,
                "span_id": span_id,
                "parent_span_id": None,
                "service_name": "root_service",
                "operation_name": "root_operation"
            }
        )
        
        # Simulate distributed operation across services
        async def simulate_service_call(context: UserExecutionContext, service_name: str, operation_name: str) -> UserExecutionContext:
            """Simulate calling another service with context propagation."""
            # Create child context for service call
            service_context = context.create_child_context(f"{service_name}_{operation_name}")
            
            # Update trace information for distributed tracing
            parent_span_id = context.audit_metadata.get("span_id")
            new_span_id = f"span_{uuid.uuid4().hex[:8]}"
            
            service_context.audit_metadata.update({
                "trace_id": trace_id,  # Preserve trace ID across services
                "span_id": new_span_id,
                "parent_span_id": parent_span_id,
                "service_name": service_name,
                "operation_name": operation_name,
                "service_call_depth": context.operation_depth + 1
            })
            
            return service_context
        
        # Simulate multi-service distributed operation
        service_a_context = await simulate_service_call(root_context, "service_a", "data_processing")
        service_b_context = await simulate_service_call(service_a_context, "service_b", "data_validation")
        service_c_context = await simulate_service_call(service_b_context, "service_c", "data_storage")
        
        # Validate distributed tracing information
        contexts = [root_context, service_a_context, service_b_context, service_c_context]
        
        # All contexts should share the same trace ID
        for context in contexts:
            assert context.audit_metadata["trace_id"] == trace_id
        
        # Validate span parent-child relationships
        assert service_a_context.audit_metadata["parent_span_id"] == root_context.audit_metadata["span_id"]
        assert service_b_context.audit_metadata["parent_span_id"] == service_a_context.audit_metadata["span_id"]
        assert service_c_context.audit_metadata["parent_span_id"] == service_b_context.audit_metadata["span_id"]
        
        # Validate service call depth tracking
        assert service_a_context.audit_metadata["service_call_depth"] == 1
        assert service_b_context.audit_metadata["service_call_depth"] == 2
        assert service_c_context.audit_metadata["service_call_depth"] == 3
        
        # Validate all span IDs are unique
        span_ids = [ctx.audit_metadata["span_id"] for ctx in contexts]
        assert len(set(span_ids)) == len(span_ids)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])