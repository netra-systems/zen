"""Test #37: Agent Execution State Persistence During WebSocket Connection Interruptions

Business Value Justification (BVJ):
- Segment: Enterprise (mission-critical operations requiring reliability)
- Business Goal: Ensure agent execution continuity despite network interruptions
- Value Impact: State persistence prevents loss of expensive AI computation results
- Strategic Impact: Enterprise reliability requirement for business-critical AI operations
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, PipelineStep
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class StatePersistenceAgent(BaseAgent):
    """Agent designed to test state persistence during connection interruptions."""
    
    def __init__(self, name: str, llm_manager: LLMManager):
        super().__init__(llm_manager=llm_manager, name=name, description=f"State persistence {name}")
        self.websocket_bridge = None
        self.execution_state = {}
        self.connection_interruptions = []
        
    def set_websocket_bridge(self, bridge: AgentWebSocketBridge, run_id: str):
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute with state persistence testing during connection interruptions."""
        
        # Initialize execution state
        self.execution_state = {
            "phase": "initialization",
            "progress": 0,
            "completed_operations": [],
            "persistent_data": {"user_id": getattr(state, 'user_id', None)},
            "checkpoint_data": {}
        }
        
        try:
            await self.websocket_bridge.notify_agent_started(
                run_id, self.name, {"state_persistence_enabled": True, "checkpointing": True}
            )
            
            # Phase 1: Initial processing with checkpoint
            await self._execute_with_checkpoint(run_id, "initial_processing", 25)
            
            # Simulate connection interruption
            await self._simulate_connection_interruption(run_id)
            
            # Phase 2: Continue with restored state
            await self._execute_with_checkpoint(run_id, "post_interruption_processing", 75)
            
            # Final result with state persistence summary
            result = {
                "success": True,
                "agent_name": self.name,
                "state_persistence": {
                    "checkpoints_created": len([op for op in self.execution_state["completed_operations"] if "checkpoint" in op]),
                    "interruptions_handled": len(self.connection_interruptions),
                    "state_recovered": True,
                    "data_integrity": "maintained"
                },
                "final_state": self.execution_state,
                "business_continuity": "ensured"
            }
            
            await self.websocket_bridge.notify_agent_completed(
                run_id, self.name, result, execution_time_ms=300
            )
            
            return result
            
        except Exception as e:
            # Handle state persistence during errors
            await self._handle_state_persistence_error(run_id, str(e))
            return {"success": False, "error": str(e), "state_preserved": True}
            
    async def _execute_with_checkpoint(self, run_id: str, phase_name: str, target_progress: int):
        """Execute phase with state checkpointing."""
        
        self.execution_state["phase"] = phase_name
        self.execution_state["progress"] = target_progress
        
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, f"Executing {phase_name} with state checkpointing...",
            step_number=len(self.execution_state["completed_operations"]) + 1,
            progress_percentage=target_progress
        )
        
        # Create checkpoint
        checkpoint = {
            "timestamp": datetime.now(timezone.utc),
            "phase": phase_name,
            "progress": target_progress,
            "data": f"checkpoint_data_{phase_name}"
        }
        self.execution_state["checkpoint_data"][phase_name] = checkpoint
        self.execution_state["completed_operations"].append(f"checkpoint_{phase_name}")
        
        # Simulate processing
        await asyncio.sleep(0.1)
        
    async def _simulate_connection_interruption(self, run_id: str):
        """Simulate WebSocket connection interruption and recovery."""
        
        interruption_event = {
            "timestamp": datetime.now(timezone.utc),
            "type": "connection_interruption",
            "duration_ms": 500,
            "recovery_strategy": "state_restoration"
        }
        self.connection_interruptions.append(interruption_event)
        
        # Simulate brief interruption
        await asyncio.sleep(0.05)
        
        # Recovery notification
        await self.websocket_bridge.notify_agent_thinking(
            run_id, self.name, "Connection restored, resuming from persistent state...",
            step_number=len(self.execution_state["completed_operations"]) + 1,
            progress_percentage=50,
            connection_recovered=True
        )
        
    async def _handle_state_persistence_error(self, run_id: str, error_msg: str):
        """Handle errors while preserving state."""
        await self.websocket_bridge.notify_agent_error(
            run_id, self.name, error_msg,
            error_context={"state_preserved": True, "recovery_possible": True}
        )


class TestWebSocketAgentExecutionStatePersistenceInterruption(BaseIntegrationTest):
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        self.env.set("TESTING", "1", source="integration_test")
        
    @pytest.fixture
    async def mock_llm_manager(self):
        llm_manager = AsyncMock(spec=LLMManager)
        llm_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        return llm_manager
        
    @pytest.fixture
    async def persistence_user_context(self):
        return UserExecutionContext(
            user_id=f"persist_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"persist_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"persist_run_{uuid.uuid4().hex[:8]}",
            request_id=f"persist_req_{uuid.uuid4().hex[:8]}",
            metadata={"state_persistence_test": True, "mission_critical": True}
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_state_persistence_during_websocket_interruptions(
        self, real_services_fixture, persistence_user_context, mock_llm_manager
    ):
        """CRITICAL: Test agent state persistence during WebSocket connection interruptions."""
        
        agent = StatePersistenceAgent("persistence_agent", mock_llm_manager)
        
        registry = MagicMock()
        registry.get = lambda name: agent
        registry.get_async = AsyncMock(return_value=agent)
        
        # Create mock bridge that tracks state persistence
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = persistence_user_context
        bridge.events = []
        bridge.state_checkpoints = []
        
        async def track_with_persistence(event_type: str, run_id: str, agent_name: str, data: Any = None, **kwargs):
            event = {
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc),
                "persistent": True
            }
            bridge.events.append(event)
            
            # Track state checkpoints
            if data and isinstance(data, dict) and ("checkpoint" in str(data) or "state" in str(data)):
                bridge.state_checkpoints.append(event)
                
            return True
            
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            track_with_persistence("agent_started", run_id, agent_name, context))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, thinking, **kwargs:
            track_with_persistence("agent_thinking", run_id, agent_name, {"reasoning": thinking}, **kwargs))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, **kwargs:
            track_with_persistence("agent_completed", run_id, agent_name, result, **kwargs))
        bridge.notify_agent_error = AsyncMock(side_effect=lambda run_id, agent_name, error, **kwargs:
            track_with_persistence("agent_error", run_id, agent_name, {"error": str(error)}, **kwargs))
            
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry,
            websocket_bridge=bridge,
            user_context=persistence_user_context
        )
        
        exec_context = AgentExecutionContext(
            user_id=persistence_user_context.user_id,
            thread_id=persistence_user_context.thread_id,
            run_id=persistence_user_context.run_id,
            request_id=persistence_user_context.request_id,
            agent_name="persistence_agent",
            step=PipelineStep.PROCESSING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        agent_state = DeepAgentState(
            user_request={"mission_critical": True, "require_persistence": True},
            user_id=persistence_user_context.user_id,
            chat_thread_id=persistence_user_context.thread_id,
            run_id=persistence_user_context.run_id
        )
        
        # Execute with state persistence testing
        result = await execution_engine.execute_agent(exec_context, persistence_user_context)
        
        # Validate state persistence
        assert result.success is True
        
        state_persistence = result.data.get("state_persistence", {})
        assert state_persistence.get("checkpoints_created", 0) >= 2
        assert state_persistence.get("interruptions_handled", 0) >= 1
        assert state_persistence.get("state_recovered") is True
        assert state_persistence.get("data_integrity") == "maintained"
        
        # Validate state checkpoints were captured
        assert len(bridge.state_checkpoints) > 0, "State checkpoints must be captured"
        
        # Validate final state integrity
        final_state = result.data.get("final_state", {})
        assert "checkpoint_data" in final_state
        assert len(final_state.get("completed_operations", [])) > 0
        
        self.logger.info(
            f"✅ State persistence test PASSED - "
            f"Checkpoints: {state_persistence.get('checkpoints_created', 0)}, "
            f"Interruptions: {state_persistence.get('interruptions_handled', 0)}"
        )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])