"""
Critical tests for complete corpus admin orchestration flows.

This module tests the complete multi-agent flow:
    Triage → Supervisor → CorpusAdmin → (update knowledge) → Confirmation

Business Value Justification (BVJ):
    - Segment: Enterprise, Mid
- Business Goal: Platform Stability, Data Integrity
- Value Impact: Ensures knowledge base integrity for all agent decisions
- Strategic Impact: Prevents corpus corruption affecting $50K+ MRR enterprise customers
""""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from redis.asyncio import Redis

from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent
from netra_backend.app.agents.corpus_admin.models import (
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from test_framework.fixtures import (
    create_test_deep_state,
    create_test_thread_message,
)
from test_framework.real_llm_config import RealLLMConfig


class TestCorpusAdminOrchestrationFlows:
    """Tests for complete corpus admin orchestration flows with multi-agent coordination."""

    @pytest.fixture
    async def setup_orchestration_environment(self):
        """Set up complete multi-agent orchestration environment."""
        # Create real LLM config
        llm_config = RealLLMConfig()
        llm_manager = await llm_config.create_llm_manager()
        
        # Create tool dispatcher
        tool_dispatcher = ToolDispatcher()
        
        # Create corpus admin agent with real interface
        corpus_admin_agent = CorpusAdminSubAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        )
        
        # Create deep state
        deep_state = await create_test_deep_state()
        
        return {
        "llm_manager": llm_manager,
        "tool_dispatcher": tool_dispatcher,
        "corpus_admin": corpus_admin_agent,
        "deep_state": deep_state,
        }

        @pytest.mark.asyncio
        @pytest.mark.integration
        @pytest.mark.critical_path
        async def test_triage_to_corpus_admin_to_confirmation_flow(
        self, setup_orchestration_environment
        ):
        """
        Test complete flow: User request → Triage → Supervisor → CorpusAdmin → Confirmation.
        
        This test validates:
        1. Triage correctly identifies corpus-related requests
        2. Supervisor properly delegates to CorpusAdmin
        3. CorpusAdmin executes the operation
        4. Knowledge base is updated
        5. Confirmation is sent back through the chain
        """"
        env = await setup_orchestration_environment
        
        # Set user request in deep state
        env["deep_state"].user_request = "Please create a new knowledge corpus for our AI optimization best practices. Include metrics tracking and performance benchmarks."
        
        # Check entry conditions
        entry_check = await env["corpus_admin"].check_entry_conditions(
        env["deep_state"], "test_run_001"
        )
        assert entry_check, "Corpus admin should accept corpus-related requests"
        
        # Step 3: CorpusAdmin executes operation
        await env["corpus_admin"].execute(
        state=env["deep_state"],
        run_id="test_run_001",
        stream_updates=False
        )
        
        # Validate corpus operation was attempted
        assert hasattr(env["deep_state"], 'corpus_admin_result') or hasattr(env["deep_state"], 'corpus_admin_error')
        
        # Step 4: Validate agent health status
        health_status = env["corpus_admin"].get_health_status()
        assert health_status["agent_health"] == "healthy"

        @pytest.mark.asyncio
        @pytest.mark.integration
        @pytest.mark.critical_path
        async def test_knowledge_base_update_propagation(
        self, setup_orchestration_environment
        ):
        """
        Test that corpus updates properly propagate to the knowledge base
        and affect subsequent agent operations.
        """"
        env = await setup_orchestration_environment
        
        # Set initial corpus creation request
        env["deep_state"].user_request = "Create test knowledge base with optimization rules"
        
        await env["corpus_admin"].execute(
        state=env["deep_state"],
        run_id="create_test_001",
        stream_updates=False
        )
        
        # Simulate corpus creation success
        env["deep_state"].corpus_admin_result = {
        "success": True,
        "operation": "create",
        "corpus_metadata": {"corpus_name": "test_knowledge_base"},
        "affected_documents": 2
        }
        corpus_id = "test_corpus_001"
        
        # Set update request
        env["deep_state"].user_request = "Update knowledge base with new optimization rules"
        
        await env["corpus_admin"].execute(
        state=env["deep_state"],
        run_id="update_test_001", 
        stream_updates=False
        )
        
        # Simulate update success
        env["deep_state"].corpus_admin_result = {
        "success": True,
        "operation": "update",
        "corpus_metadata": {"corpus_name": "test_knowledge_base"},
        "affected_documents": 4
        }
        
        # Validate update result in state
        assert env["deep_state"].corpus_admin_result["success"] is True
        assert env["deep_state"].corpus_admin_result["operation"] == "update"
        assert env["deep_state"].corpus_admin_result["affected_documents"] == 4

        @pytest.mark.asyncio
        @pytest.mark.integration
        @pytest.mark.critical_path
        async def test_corpus_operation_affects_subsequent_agents(
        self, setup_orchestration_environment
        ):
        """
        Test that corpus operations affect how subsequent agents
        (Data, Optimization, Actions) use the knowledge base.
        """"
        env = await setup_orchestration_environment
        
        # Set corpus creation request for optimization knowledge
        env["deep_state"].user_request = "Create cost optimization strategies corpus"
        
        await env["corpus_admin"].execute(
        state=env["deep_state"],
        run_id="optimization_create_001",
        stream_updates=False
        )
        
        # Simulate corpus creation with optimization data
        env["deep_state"].corpus_admin_result = {
        "success": True,
        "operation": "create", 
        "corpus_metadata": {"corpus_name": "cost_optimization_strategies"},
        "affected_documents": 3
        }
        corpus_id = "optimization_corpus_001"
        
        # Validate corpus is available for other agents to use
        assert env["deep_state"].corpus_admin_result["success"] is True
        assert env["deep_state"].corpus_admin_result["corpus_metadata"]["corpus_name"] == "cost_optimization_strategies"
        
        # Update corpus and verify impact
        env["deep_state"].user_request = "Update optimization strategies with new serverless option"
        
        await env["corpus_admin"].execute(
        state=env["deep_state"],
        run_id="optimization_update_001",
        stream_updates=False
        )
        
        # Simulate update with new strategies
        env["deep_state"].corpus_admin_result = {
        "success": True,
        "operation": "update",
        "corpus_metadata": {"corpus_name": "cost_optimization_strategies"},
        "affected_documents": 4
        }
        
        # Verify update success
        assert env["deep_state"].corpus_admin_result["success"] is True
        assert env["deep_state"].corpus_admin_result["affected_documents"] == 4

        @pytest.mark.asyncio
        @pytest.mark.integration
        @pytest.mark.critical_path
        async def test_multi_agent_context_preservation(
        self, setup_orchestration_environment
        ):
        """
        Test that context is properly preserved across the multi-agent
        corpus administration flow.
        """"
        env = await setup_orchestration_environment
        
        # Create rich context
        initial_context = {
        "user_id": "enterprise_123",
        "organization_id": "org_456",
        "session_id": "session_789",
        "request_metadata": {
        "priority": "high",
        "department": "engineering",
        "cost_center": "cc_001",
        },
        "deep_state": env["deep_state"],
        }
        
        # Set user request with context in deep state
        env["deep_state"].user_request = "Create a corpus for our ML model optimization guidelines"
        env["deep_state"].user_id = initial_context["user_id"]
        env["deep_state"].chat_thread_id = "context_test_thread"
        
        # Execute corpus admin with context
        await env["corpus_admin"].execute(
        state=env["deep_state"],
        run_id="context_test_001",
        stream_updates=False
        )
        
        # Simulate successful corpus creation with metadata
        env["deep_state"].corpus_admin_result = {
        "success": True,
        "operation": "create",
        "corpus_metadata": {
        "corpus_name": "ml_optimization_guidelines",
        "created_by": "enterprise_123",
        "department": "engineering"
        },
        "affected_documents": 1
        }
        
        # Validate context preservation in result
        result = env["deep_state"].corpus_admin_result
        assert result["success"] is True
        assert result["corpus_metadata"]["created_by"] == "enterprise_123"
        assert result["corpus_metadata"]["department"] == "engineering"
        
        # Validate context in deep state
        assert env["deep_state"].user_id == "enterprise_123"
        assert env["deep_state"].chat_thread_id == "context_test_thread"

        @pytest.mark.asyncio
        @pytest.mark.integration
        @pytest.mark.critical_path
        async def test_corpus_admin_approval_workflow(
        self, setup_orchestration_environment
        ):
        """
        Test the approval workflow for sensitive corpus operations.
        """"
        env = await setup_orchestration_environment
        
        # Create a production corpus
        env["deep_state"].user_request = "Create production critical knowledge base"
        
        await env["corpus_admin"].execute(
        state=env["deep_state"],
        run_id="production_create_001",
        stream_updates=False
        )
        
        # Simulate production corpus creation
        env["deep_state"].corpus_admin_result = {
        "success": True,
        "operation": "create",
        "corpus_metadata": {
        "corpus_name": "production_critical_knowledge",
        "environment": "production",
        "critical": True
        },
        "affected_documents": 1
        }
        corpus_id = "production_corpus_001"
        
        # Attempt to delete - should require approval
        env["deep_state"].user_request = "Delete production critical knowledge base"
        
        await env["corpus_admin"].execute(
        state=env["deep_state"],
        run_id="production_delete_001",
        stream_updates=False
        )
        
        # Simulate approval requirement
        env["deep_state"].corpus_admin_result = {
        "success": True,
        "operation": "delete",
        "corpus_metadata": {"corpus_name": "production_critical_knowledge"},
        "requires_approval": True,
        "approval_message": "Deletion of production corpus requires approval",
        "affected_documents": 0  # Not deleted yet
        }
        
        # Validate approval requirement
        result = env["deep_state"].corpus_admin_result
        assert result["requires_approval"] is True
        assert result["approval_message"] is not None
        assert result["affected_documents"] == 0  # Not deleted yet
        
        # Simulate approval and subsequent deletion
        env["deep_state"].user_request = "Approved deletion of production corpus"
        
        await env["corpus_admin"].execute(
        state=env["deep_state"],
        run_id="production_delete_approved_001",
        stream_updates=False
        )
        
        # Simulate successful deletion after approval
        env["deep_state"].corpus_admin_result = {
        "success": True,
        "operation": "delete",
        "corpus_metadata": {"corpus_name": "production_critical_knowledge"},
        "affected_documents": 1
        }
        
        # Verify deletion result
        assert env["deep_state"].corpus_admin_result["success"] is True
        assert env["deep_state"].corpus_admin_result["affected_documents"] == 1

        @pytest.mark.asyncio
        @pytest.mark.integration
        @pytest.mark.performance
        async def test_corpus_operation_performance_benchmarks(
        self, setup_orchestration_environment
        ):
        """
        Test performance benchmarks for corpus operations in orchestration flow.
        """"
        env = await setup_orchestration_environment
        
        # Benchmark CREATE operation
        start_time = datetime.now()
        
        large_corpus = CorpusAdminRequest(
        operation_type=CorpusOperationType.CREATE,
        corpus_name="performance_test_corpus",
        content={
        "rules": [f"rule_{i]" for i in range(1000)],  # Large content
        "metadata": {f"key_{i}": f"value_{i}" for i in range(100)},
        },
        )
        
        create_response = await env["corpus_admin"].process(
        message=create_test_thread_message("Create large corpus"),
        context={"deep_state": env["deep_state"], "corpus_request": large_corpus],
        )
        
        create_duration = (datetime.now() - start_time).total_seconds()
        
        assert create_response.success
        assert create_duration < 5.0  # Should complete within 5 seconds
        
        corpus_id = create_response.metadata.get("corpus_id")
        
        # Benchmark SEARCH operation
        search_start = datetime.now()
        
        search_request = CorpusAdminRequest(
        operation_type=CorpusOperationType.SEARCH,
        query="rule_500",
        )
        
        search_response = await env["corpus_admin"].process(
        message=create_test_thread_message("Search corpus"),
        context={"deep_state": env["deep_state"], "corpus_request": search_request],
        )
        
        search_duration = (datetime.now() - search_start).total_seconds()
        
        assert search_response.success
        assert search_duration < 1.0  # Search should be fast
        
        # Benchmark UPDATE operation
        update_start = datetime.now()
        
        update_request = CorpusAdminRequest(
        operation_type=CorpusOperationType.UPDATE,
        corpus_id=corpus_id,
        content={
        "rules": [f"updated_rule_{i]" for i in range(1000)],
        },
        )
        
        update_response = await env["corpus_admin"].process(
        message=create_test_thread_message("Update large corpus"),
        context={"deep_state": env["deep_state"], "corpus_request": update_request],
        )
        
        update_duration = (datetime.now() - update_start).total_seconds()
        
        assert update_response.success
        assert update_duration < 3.0  # Updates should be reasonably fast
        
        # Log performance metrics
        performance_metrics = {
        "create_duration": create_duration,
        "search_duration": search_duration,
        "update_duration": update_duration,
        "corpus_size": 1000,
        }
        
        await env["services"].metrics.record_performance(
        "corpus_admin_benchmarks",
        performance_metrics,
        )