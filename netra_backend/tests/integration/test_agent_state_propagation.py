"""
State Propagation and Context Preservation Tests for Multi-Agent Orchestration

Business Value Justification (BVJ):
- Segment: Mid/Enterprise
- Business Goal: Agent reliability and state consistency
- Value Impact: Ensures agent outputs and context are preserved across the pipeline
- Strategic Impact: Prevents data loss and maintains user experience continuity

This module tests critical state propagation and context preservation requirements:
1. Context preservation across agent boundaries
2. Metadata tracking through the pipeline
3. Session state consistency
4. User context maintenance
5. State integrity when agents pass data between each other
6. Proper accumulation of agent outputs in the state
"""

import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.state import DeepAgentState, AgentMetadata
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.supervisor.agent_manager import AgentManager, AgentStatus
from netra_backend.app.services.state.state_manager import StateManager, StateStorage
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.schemas.agent_models import AgentMetadata as SchemaAgentMetadata
from test_framework.environment_isolation import IsolatedEnvironment
from test_framework.fixtures import (
    isolated_redis_client,
    setup_test_database
)


# Environment awareness - these tests can run in test and dev environments
pytestmark = [
    pytest.mark.env("test"),
    pytest.mark.env("dev")
]


@pytest.fixture
async def isolated_env():
    """Provide isolated test environment."""
    env = IsolatedEnvironment()
    await env.setup()
    yield env
    await env.cleanup()


@pytest.fixture
async def test_redis():
    """Setup test Redis connection."""
    # Use the isolated_redis_client fixture
    async for client in isolated_redis_client():
        yield client
        break


@pytest.fixture
async def test_database():
    """Setup test database connection."""
    return {
        "database_url": "sqlite+aiosqlite:///:memory:",
        "schema_created": True,
        "test_data_loaded": False
    }


@pytest.fixture
async def state_manager():
    """Create state manager with hybrid storage."""
    return StateManager(storage=StateStorage.HYBRID)


@pytest.fixture
async def agent_manager():
    """Create agent manager for testing."""
    manager = AgentManager(max_concurrent_agents=5)
    yield manager
    await manager.shutdown()


@pytest.fixture
def test_user():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create test user data."""
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "username": "test_user",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "preferences": {
            "language": "en",
            "timezone": "UTC"
        }
    }


@pytest.fixture
def test_thread():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create test thread data."""
    return {
        "id": "test_thread_123", 
        "user_id": "test_user_123",
        "title": "Test Thread",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {}
    }


@pytest.fixture
def base_execution_context(test_user, test_thread):
    """Use real service instance."""
    # TODO: Initialize real service
    """Create base execution context."""
    return AgentExecutionContext(
        run_id=str(uuid.uuid4()),
        thread_id=test_thread["id"],
        user_id=test_user["id"],
        agent_name="test_agent",
        metadata={
            "user_preferences": {
                "language": "en",
                "timezone": "UTC",
                "theme": "dark"
            },
            "request_params": {
                "query": "test optimization",
                "priority": "high",
                "category": "performance"
            },
            "auth_context": {
                "permissions": ["read", "write"],
                "roles": ["user", "analyst"],
                "tenant_id": "test_tenant"
            },
            "session_info": {
                "session_id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "user_agent": "test-client"
            }
        }
    )


@pytest.fixture
def initial_state(test_user, test_thread):
    """Use real service instance."""
    # TODO: Initialize real service
    """Create initial agent state."""
    return DeepAgentState(
        user_request="Analyze performance optimization opportunities",
        chat_thread_id=test_thread["id"],
        user_id=test_user["id"],
        agent_input={
            "original_query": "Analyze performance optimization opportunities",
            "context": "Production system with latency issues",
            "requirements": ["cost_effective", "minimal_disruption"]
        },
        metadata=AgentMetadata(
            execution_context={
                "pipeline_stage": "initialization",
                "request_timestamp": datetime.now(timezone.utc).isoformat()
            },
            custom_fields={
                "priority_level": "high",
                "department": "engineering"
            }
        )
    )


class MockAgent:
    """Mock agent for testing state propagation."""
    
    def __init__(self, name: str, processing_delay: float = 0.1):
        self.name = name
        self.processing_delay = processing_delay
        self.execution_history = []
    
    async def execute(self, context: AgentExecutionContext, state: DeepAgentState) -> AgentExecutionResult:
        """Execute mock agent with state processing."""
        await asyncio.sleep(self.processing_delay)
        
        # Record execution
        self.execution_history.append({
            "timestamp": datetime.now(timezone.utc),
            "context": context,
            "input_state": state,
            "run_id": context.run_id
        })
        
        # Process state based on agent type
        updated_state = await self._process_state(state, context)
        
        return AgentExecutionResult(
            success=True,
            state=updated_state,
            metadata={
                "agent_name": self.name,
                "processing_time": self.processing_delay,
                "context_preserved": self._verify_context_preservation(context)
            }
        )
    
    async def _process_state(self, state: DeepAgentState, context: AgentExecutionContext) -> DeepAgentState:
        """Process state with agent-specific logic."""
        # Add agent-specific metadata
        new_metadata = state.metadata.model_copy(
            update={
                'execution_context': {
                    **state.metadata.execution_context,
                    f'{self.name}_processed': True,
                    f'{self.name}_timestamp': datetime.now(timezone.utc).isoformat(),
                    f'{self.name}_run_id': context.run_id
                },
                'custom_fields': {
                    **state.metadata.custom_fields,
                    f'{self.name}_output': f"Processed by {self.name}",
                    f'{self.name}_context_data': json.dumps(context.metadata)
                }
            }
        )
        
        # Create updated state with incremented step count
        return state.copy_with_updates(
            step_count=state.step_count + 1,
            metadata=new_metadata
        )
    
    def _verify_context_preservation(self, context: AgentExecutionContext) -> bool:
        """Verify that context contains expected fields."""
        required_fields = ["user_preferences", "request_params", "auth_context", "session_info"]
        return all(field in context.metadata for field in required_fields)


@pytest.mark.asyncio
async def test_context_preservation_across_agent_boundaries(
    state_manager, agent_manager, base_execution_context, initial_state
):
    """Test that context is preserved when passed between agents."""
    # Setup agents
    triage_agent = MockAgent("triage_agent")
    analysis_agent = MockAgent("analysis_agent")
    optimization_agent = MockAgent("optimization_agent")
    
    # Register agents
    triage_id = await agent_manager.register_agent("triage", triage_agent)
    analysis_id = await agent_manager.register_agent("analysis", analysis_agent)
    optimization_id = await agent_manager.register_agent("optimization", optimization_agent)
    
    # Execute pipeline with state propagation
    current_state = initial_state
    current_context = base_execution_context
    
    # Store initial state
    await state_manager.set(f"state:{current_context.run_id}", current_state.to_dict())
    
    # Execute agents in sequence
    for agent_id, agent_instance in [
        (triage_id, triage_agent),
        (analysis_id, analysis_agent), 
        (optimization_id, optimization_agent)
    ]:
        # Update context for next agent
        current_context.agent_name = agent_instance.name
        
        # Execute agent
        result = await agent_instance.execute(current_context, current_state)
        assert result.success, f"Agent {agent_instance.name} execution failed"
        
        # Update state from result
        current_state = result.state
        
        # Store updated state
        await state_manager.set(f"state:{current_context.run_id}", current_state.to_dict())
    
    # Verify context preservation through entire pipeline
    assert current_state.step_count == 3, "Step count should reflect all agent executions"
    
    # Verify metadata contains all agent outputs
    for agent_name in ["triage_agent", "analysis_agent", "optimization_agent"]:
        assert f"{agent_name}_processed" in current_state.metadata.execution_context
        assert f"{agent_name}_output" in current_state.metadata.custom_fields
    
    # Verify original context preserved
    final_stored_state = await state_manager.get(f"state:{current_context.run_id}")
    assert final_stored_state is not None
    assert final_stored_state["user_request"] == initial_state.user_request
    assert final_stored_state["chat_thread_id"] == initial_state.chat_thread_id
    assert final_stored_state["user_id"] == initial_state.user_id


@pytest.mark.asyncio
async def test_metadata_tracking_through_pipeline(
    state_manager, base_execution_context, initial_state
):
    """Test metadata accumulation and tracking through agent pipeline."""
    agents = [MockAgent(f"agent_{i}") for i in range(3)]
    current_state = initial_state
    
    # Execute pipeline
    for i, agent in enumerate(agents):
        context = base_execution_context
        context.agent_name = agent.name
        
        result = await agent.execute(context, current_state)
        current_state = result.state
        
        # Store state after each agent
        state_key = f"pipeline:{context.run_id}:step_{i}"
        await state_manager.set(state_key, {
            "state": current_state.to_dict(),
            "agent": agent.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": i
        })
    
    # Verify metadata accumulation
    assert current_state.step_count == 3
    
    # Verify each agent left metadata traces
    for i in range(3):
        agent_name = f"agent_{i}"
        assert f"{agent_name}_processed" in current_state.metadata.execution_context
        assert f"{agent_name}_timestamp" in current_state.metadata.execution_context
        assert f"{agent_name}_output" in current_state.metadata.custom_fields
    
    # Verify pipeline state history
    for i in range(3):
        step_state = await state_manager.get(f"pipeline:{base_execution_context.run_id}:step_{i}")
        assert step_state is not None
        assert step_state["step"] == i
        assert step_state["agent"] == f"agent_{i}"


@pytest.mark.asyncio
async def test_session_state_consistency(
    state_manager, base_execution_context, initial_state
):
    """Test that session state remains consistent across agent executions."""
    session_id = base_execution_context.metadata["session_info"]["session_id"]
    
    # Create multiple execution contexts for same session
    contexts = []
    for i in range(3):
        context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id=base_execution_context.thread_id,
            user_id=base_execution_context.user_id,
            agent_name=f"agent_{i}",
            metadata={
                **base_execution_context.metadata,
                "session_info": {
                    **base_execution_context.metadata["session_info"],
                    "session_id": session_id  # Same session ID
                }
            }
        )
        contexts.append(context)
    
    # Store session-level state
    session_state = {
        "user_preferences": base_execution_context.metadata["user_preferences"],
        "auth_context": base_execution_context.metadata["auth_context"],
        "session_data": {
            "active_runs": [],
            "accumulated_context": {}
        }
    }
    await state_manager.set(f"session:{session_id}", session_state)
    
    # Execute agents and track session state
    for context in contexts:
        # Update session state with new run
        current_session_state = await state_manager.get(f"session:{session_id}")
        current_session_state["session_data"]["active_runs"].append(context.run_id)
        
        # Add context data to session
        current_session_state["session_data"]["accumulated_context"][context.run_id] = {
            "agent": context.agent_name,
            "request_params": context.metadata["request_params"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await state_manager.set(f"session:{session_id}", current_session_state)
        
        # Execute agent
        agent = MockAgent(context.agent_name)
        result = await agent.execute(context, initial_state)
        
        # Store individual run state
        await state_manager.set(f"state:{context.run_id}", result.state.to_dict())
    
    # Verify session state consistency
    final_session_state = await state_manager.get(f"session:{session_id}")
    
    assert len(final_session_state["session_data"]["active_runs"]) == 3
    assert len(final_session_state["session_data"]["accumulated_context"]) == 3
    
    # Verify all runs share same user preferences and auth context
    for run_id in final_session_state["session_data"]["active_runs"]:
        run_state = await state_manager.get(f"state:{run_id}")
        assert run_state["user_id"] == base_execution_context.user_id
        assert run_state["chat_thread_id"] == base_execution_context.thread_id
    
    # Verify session-level data preserved
    assert final_session_state["user_preferences"] == base_execution_context.metadata["user_preferences"]
    assert final_session_state["auth_context"] == base_execution_context.metadata["auth_context"]


@pytest.mark.asyncio
async def test_user_context_maintenance(
    state_manager, test_user, test_thread
):
    """Test that user context is maintained throughout agent execution."""
    user_context = {
        "user_id": test_user["id"],
        "preferences": {
            "language": "en",
            "notification_settings": {"email": True, "push": False},
            "ui_preferences": {"theme": "dark", "compact_mode": True}
        },
        "permissions": {
            "can_export": True,
            "can_share": True,
            "admin_access": False
        },
        "subscription": {
            "tier": "premium",
            "features": ["advanced_analytics", "custom_reports"],
            "limits": {"api_calls_per_hour": 1000}
        }
    }
    
    # Store user context
    await state_manager.set(f"user_context:{test_user['id']}", user_context)
    
    # Create execution contexts with different agents
    contexts = []
    for agent_name in ["triage", "analysis", "optimization", "reporting"]:
        context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id=test_thread["id"],
            user_id=test_user["id"],
            agent_name=agent_name,
            metadata={"agent_type": agent_name}
        )
        contexts.append(context)
    
    # Execute agents and verify user context preservation
    for context in contexts:
        # Retrieve user context
        stored_user_context = await state_manager.get(f"user_context:{test_user['id']}")
        assert stored_user_context is not None
        
        # Create state with user context
        state = DeepAgentState(
            user_request="Test request",
            chat_thread_id=context.thread_id,
            user_id=context.user_id,
            metadata=AgentMetadata(
                execution_context={
                    "user_preferences": stored_user_context["preferences"],
                    "user_permissions": stored_user_context["permissions"],
                    "user_subscription": stored_user_context["subscription"]
                }
            )
        )
        
        # Execute agent
        agent = MockAgent(context.agent_name)
        result = await agent.execute(context, state)
        
        # Verify user context preserved in result
        result_metadata = result.state.metadata.execution_context
        assert "user_preferences" in result_metadata
        assert "user_permissions" in result_metadata
        assert "user_subscription" in result_metadata
        
        # Verify specific user data
        assert result_metadata["user_preferences"]["language"] == "en"
        assert result_metadata["user_permissions"]["can_export"] is True
        assert result_metadata["user_subscription"]["tier"] == "premium"


@pytest.mark.asyncio
async def test_state_integrity_with_concurrent_agents(
    state_manager, agent_manager, base_execution_context, initial_state
):
    """Test state integrity when multiple agents access state concurrently."""
    # Create multiple agents
    agents = [MockAgent(f"concurrent_agent_{i}", processing_delay=0.2) for i in range(5)]
    
    # Register agents
    agent_ids = []
    for i, agent in enumerate(agents):
        agent_id = await agent_manager.register_agent(f"concurrent_{i}", agent)
        agent_ids.append((agent_id, agent))
    
    # Create shared state key
    state_key = f"concurrent_state:{base_execution_context.run_id}"
    await state_manager.set(state_key, initial_state.to_dict())
    
    # Execute agents concurrently
    tasks = []
    for agent_id, agent in agent_ids:
        context = AgentExecutionContext(
            run_id=f"{base_execution_context.run_id}_{agent.name}",
            thread_id=base_execution_context.thread_id,
            user_id=base_execution_context.user_id,
            agent_name=agent.name,
            metadata=base_execution_context.metadata
        )
        
        task = asyncio.create_task(
            execute_agent_with_state_handling(agent, context, state_key, state_manager)
        )
        tasks.append((task, agent.name))
    
    # Wait for all agents to complete
    results = []
    for task, agent_name in tasks:
        try:
            result = await task
            results.append((agent_name, result))
        except Exception as e:
            pytest.fail(f"Agent {agent_name} failed with error: {e}")
    
    # Verify all agents completed successfully
    assert len(results) == 5
    for agent_name, result in results:
        assert result.success, f"Agent {agent_name} failed"
    
    # Verify final state integrity
    final_state = await state_manager.get(state_key)
    assert final_state is not None
    
    # Verify state contains contributions from all agents
    metadata = final_state.get("metadata", {})
    execution_context = metadata.get("execution_context", {})
    custom_fields = metadata.get("custom_fields", {})
    
    # At least some agents should have left their mark
    processed_agents = [key for key in execution_context.keys() if key.endswith("_processed")]
    assert len(processed_agents) > 0, "No agents left processing traces"


@pytest.mark.asyncio
async def test_agent_output_accumulation_in_state(
    state_manager, base_execution_context, initial_state
):
    """Test that agent outputs properly accumulate in the state."""
    # Create pipeline of specialized agents
    agents_config = [
        ("triage_agent", {"triage_result": {"priority": "high", "category": "performance"}}),
        ("data_agent", {"data_result": {"metrics": [1, 2, 3], "trends": ["increasing"]}}),
        ("optimization_agent", {"optimizations_result": {"recommendations": ["cache_optimization", "query_tuning"]}}),
        ("action_plan_agent", {"action_plan_result": {"steps": ["step1", "step2"], "timeline": "2 weeks"}}),
        ("report_agent", {"report_result": {"summary": "Optimization complete", "attachments": ["report.pdf"]}})
    ]
    
    current_state = initial_state
    
    # Execute agents and accumulate outputs
    for agent_name, expected_output in agents_config:
        # Create specialized mock agent
        agent = SpecializedMockAgent(agent_name, expected_output)
        
        context = base_execution_context
        context.agent_name = agent_name
        
        result = await agent.execute(context, current_state)
        current_state = result.state
        
        # Store accumulated state
        await state_manager.set(
            f"accumulated:{base_execution_context.run_id}",
            current_state.to_dict()
        )
    
    # Verify all outputs accumulated
    final_state = await state_manager.get(f"accumulated:{base_execution_context.run_id}")
    
    # Check that each agent type left its specific output
    for agent_name, expected_output in agents_config:
        for field_name in expected_output.keys():
            assert field_name in final_state, f"Missing {field_name} from {agent_name}"
            
            # Verify output structure
            stored_output = final_state[field_name]
            expected_data = expected_output[field_name]
            
            # Basic structure verification
            if isinstance(expected_data, dict):
                for key in expected_data.keys():
                    assert key in stored_output, f"Missing key {key} in {field_name}"


@pytest.mark.asyncio
async def test_state_transaction_atomicity(base_execution_context):
    """Test that state changes are atomic and consistent."""
    # Use memory-only state manager to avoid Redis complications
    state_manager = StateManager(storage=StateStorage.MEMORY)
    state_key = f"atomic_test:{base_execution_context.run_id}"
    
    # Initial state
    initial_data = {
        "counter": 0,
        "items": [],
        "metadata": {"version": 1}
    }
    await state_manager.set(state_key, initial_data)
    
    # Test successful transaction
    async with state_manager.transaction() as txn_id:
        current_state = await state_manager.get(state_key)
        current_state["counter"] += 1
        current_state["items"].append("item1")
        current_state["metadata"]["version"] += 1
        
        await state_manager.set(state_key, current_state, transaction_id=txn_id)
    
    # Verify changes committed
    committed_state = await state_manager.get(state_key)
    assert committed_state["counter"] == 1
    assert "item1" in committed_state["items"]
    assert committed_state["metadata"]["version"] == 2
    
    # Test failed transaction (should rollback)
    try:
        async with state_manager.transaction() as txn_id:
            current_state = await state_manager.get(state_key)
            current_state["counter"] += 10
            current_state["items"].append("item2")
            
            await state_manager.set(state_key, current_state, transaction_id=txn_id)
            
            # Simulate failure
            raise ValueError("Simulated failure")
    except ValueError:
        pass  # Expected
    
    # Verify rollback occurred
    rolled_back_state = await state_manager.get(state_key)
    assert rolled_back_state["counter"] == 1  # Should be unchanged
    assert "item2" not in rolled_back_state["items"]
    assert rolled_back_state["metadata"]["version"] == 2


class SpecializedMockAgent(MockAgent):
    """Mock agent that produces specific output types."""
    
    def __init__(self, name: str, output_spec: Dict[str, Any]):
        super().__init__(name)
        self.output_spec = output_spec
    
    async def _process_state(self, state: DeepAgentState, context: AgentExecutionContext) -> DeepAgentState:
        """Process state with specialized output."""
        # Get base processed state
        processed_state = await super()._process_state(state, context)
        
        # Add specialized outputs
        updates = {}
        for field_name, field_value in self.output_spec.items():
            updates[field_name] = field_value
        
        return processed_state.copy_with_updates(**updates)


async def execute_agent_with_state_handling(
    agent: MockAgent, 
    context: AgentExecutionContext, 
    state_key: str, 
    state_manager: StateManager
) -> AgentExecutionResult:
    """Execute agent with proper state handling for concurrency tests."""
    # Get current state
    current_state_dict = await state_manager.get(state_key)
    current_state = DeepAgentState(**current_state_dict)
    
    # Execute agent
    result = await agent.execute(context, current_state)
    
    # Update state if successful
    if result.success:
        await state_manager.set(state_key, result.state.to_dict())
    
    return result


@pytest.mark.asyncio
async def test_authentication_context_preservation(
    state_manager, test_user, test_thread
):
    """Test that authentication context is preserved throughout agent execution."""
    auth_context = {
        "user_id": test_user["id"],
        "token_info": {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": (datetime.now(timezone.utc).timestamp() + 3600),
            "scopes": ["read", "write", "admin"]
        },
        "session_info": {
            "session_id": str(uuid.uuid4()),
            "ip_address": "127.0.0.1",
            "user_agent": "test-agent",
            "login_time": datetime.now(timezone.utc).isoformat()
        },
        "permissions": {
            "resources": ["threads", "agents", "reports"],
            "actions": ["create", "read", "update", "delete"],
            "restrictions": []
        }
    }
    
    # Store authentication context
    auth_key = f"auth:{test_user['id']}"
    await state_manager.set(auth_key, auth_context)
    
    # Create execution context with auth requirements
    context = AgentExecutionContext(
        run_id=str(uuid.uuid4()),
        thread_id=test_thread["id"],
        user_id=test_user["id"],
        agent_name="auth_sensitive_agent",
        metadata={
            "requires_auth": True,
            "required_scopes": ["read", "write"],
            "required_resources": ["threads"]
        }
    )
    
    # Create initial state with auth context
    initial_state = DeepAgentState(
        user_request="Sensitive operation requiring authentication",
        chat_thread_id=test_thread["id"],
        user_id=test_user["id"],
        metadata=AgentMetadata(
            execution_context={
                "auth_context": auth_context,
                "authenticated": True
            }
        )
    )
    
    # Execute agent
    agent = MockAgent("auth_sensitive_agent")
    result = await agent.execute(context, initial_state)
    
    # Verify authentication context preserved
    assert result.success
    result_auth = result.state.metadata.execution_context.get("auth_context")
    assert result_auth is not None
    
    # Verify token info preserved
    assert result_auth["token_info"]["access_token"] == "test_access_token"
    assert result_auth["token_info"]["scopes"] == ["read", "write", "admin"]
    
    # Verify session info preserved
    assert result_auth["session_info"]["session_id"] == auth_context["session_info"]["session_id"]
    assert result_auth["session_info"]["ip_address"] == "127.0.0.1"
    
    # Verify permissions preserved
    assert result_auth["permissions"]["resources"] == ["threads", "agents", "reports"]
    assert result_auth["permissions"]["actions"] == ["create", "read", "update", "delete"]


@pytest.mark.asyncio
async def test_request_parameters_flow_through_agents(
    state_manager, base_execution_context, initial_state
):
    """Test that request parameters flow through all agents in the pipeline."""
    # Enhanced request parameters
    enhanced_context = base_execution_context
    enhanced_context.metadata.update({
        "request_params": {
            "query": "optimization analysis",
            "filters": {
                "date_range": "last_30_days",
                "severity": ["high", "medium"],
                "categories": ["performance", "cost"]
            },
            "output_format": "detailed_report",
            "export_options": {
                "format": "pdf",
                "include_charts": True,
                "email_recipients": ["user@example.com"]
            },
            "analysis_depth": "comprehensive",
            "comparison_baseline": "previous_month"
        }
    })
    
    # Execute pipeline of agents
    agents = [
        MockAgent("filter_agent"),
        MockAgent("analysis_agent"),
        MockAgent("comparison_agent"),
        MockAgent("export_agent")
    ]
    
    current_state = initial_state
    
    for agent in agents:
        context = enhanced_context
        context.agent_name = agent.name
        
        result = await agent.execute(context, current_state)
        current_state = result.state
        
        # Verify request parameters are accessible in agent metadata
        agent_context_data = json.loads(
            current_state.metadata.custom_fields[f"{agent.name}_context_data"]
        )
        request_params = agent_context_data["request_params"]
        
        # Verify all parameter categories preserved
        assert "query" in request_params
        assert "filters" in request_params
        assert "output_format" in request_params
        assert "export_options" in request_params
        assert "analysis_depth" in request_params
        assert "comparison_baseline" in request_params
        
        # Verify nested parameters preserved
        assert request_params["filters"]["date_range"] == "last_30_days"
        assert request_params["export_options"]["format"] == "pdf"
        assert request_params["export_options"]["include_charts"] is True
    
    # Verify final state contains all parameter flow history
    final_metadata = current_state.metadata.custom_fields
    for agent in agents:
        assert f"{agent.name}_context_data" in final_metadata
        context_data = json.loads(final_metadata[f"{agent.name}_context_data"])
        assert context_data["request_params"]["query"] == "optimization analysis"


@pytest.mark.asyncio
async def test_previous_agent_decisions_inform_later_agents(
    state_manager, base_execution_context, initial_state
):
    """Test that decisions from previous agents inform later agents."""
    # Create decision-making agents
    decision_flow = [
        ("triage_agent", {"priority": "high", "complexity": "medium", "estimated_time": "2_hours"}),
        ("resource_agent", {"cpu_required": True, "memory_intensive": False, "storage_needed": "minimal"}),
        ("strategy_agent", {"approach": "incremental", "rollback_plan": True, "test_required": True}),
        ("execution_agent", {"batch_size": 100, "parallel_execution": True, "monitoring_enabled": True})
    ]
    
    current_state = initial_state
    accumulated_decisions = {}
    
    for agent_name, decisions in decision_flow:
        # Create agent that makes specific decisions
        agent = DecisionMakingMockAgent(agent_name, decisions, accumulated_decisions)
        
        context = base_execution_context
        context.agent_name = agent_name
        
        result = await agent.execute(context, current_state)
        current_state = result.state
        
        # Update accumulated decisions
        accumulated_decisions.update(decisions)
        
        # Store decision state
        await state_manager.set(
            f"decisions:{base_execution_context.run_id}:{agent_name}",
            {
                "agent": agent_name,
                "decisions": decisions,
                "previous_decisions": dict(accumulated_decisions),
                "influenced_by": list(accumulated_decisions.keys())
            }
        )
    
    # Verify decision flow
    final_decisions = {}
    for agent_name, _ in decision_flow:
        decision_state = await state_manager.get(
            f"decisions:{base_execution_context.run_id}:{agent_name}"
        )
        final_decisions[agent_name] = decision_state
    
    # Verify each agent had access to previous decisions
    for i, (agent_name, _) in enumerate(decision_flow):
        decision_state = final_decisions[agent_name]
        if i > 0:  # Not the first agent
            # Should have previous agents' decisions
            assert len(decision_state["previous_decisions"]) > 0
            assert len(decision_state["influenced_by"]) > 0
        else:
            # First agent has no previous decisions
            assert len(decision_state["previous_decisions"]) == 0
    
    # Verify later agents were influenced by earlier ones
    execution_agent_state = final_decisions["execution_agent"]
    assert "priority" in execution_agent_state["previous_decisions"]
    assert "cpu_required" in execution_agent_state["previous_decisions"]
    assert "approach" in execution_agent_state["previous_decisions"]


class DecisionMakingMockAgent(MockAgent):
    """Mock agent that makes decisions based on previous agent decisions."""
    
    def __init__(self, name: str, decisions: Dict[str, Any], previous_decisions: Dict[str, Any]):
        super().__init__(name)
        self.decisions = decisions
        self.previous_decisions = previous_decisions
    
    async def _process_state(self, state: DeepAgentState, context: AgentExecutionContext) -> DeepAgentState:
        """Process state with decision-making logic."""
        # Get base processed state
        processed_state = await super()._process_state(state, context)
        
        # Add decisions with context of previous decisions
        decision_context = {
            f"{self.name}_decisions": self.decisions,
            f"{self.name}_influenced_by": list(self.previous_decisions.keys()),
            f"{self.name}_decision_rationale": f"Based on {len(self.previous_decisions)} previous decisions"
        }
        
        new_metadata = processed_state.metadata.model_copy(
            update={
                'custom_fields': {
                    **processed_state.metadata.custom_fields,
                    **decision_context
                }
            }
        )
        
        return processed_state.copy_with_updates(metadata=new_metadata)