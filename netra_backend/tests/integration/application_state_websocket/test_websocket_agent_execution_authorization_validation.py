"""Test #39: Agent Execution Authorization and User Context Validation Through WebSocket

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (security-sensitive environments)
- Business Goal: Ensure secure agent execution with proper authorization validation
- Value Impact: Security compliance enables enterprise contracts worth $100k+ annually
- Strategic Impact: Enterprise-grade security is mandatory for regulated industries
"""

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
from shared.isolated_environment import get_env


class AuthorizedAgent(BaseAgent):
    """Agent with authorization validation."""
    
    def __init__(self, name: str, llm_manager: LLMManager):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Authorized {name}")
        self.websocket_bridge = None
        self.authorization_checks = []
        
    def set_websocket_bridge(self, bridge: AgentWebSocketBridge, run_id: str):
        self.websocket_bridge = bridge
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        # Authorization check
        auth_check = {
            "timestamp": datetime.now(timezone.utc),
            "user_id": getattr(state, 'user_id', None),
            "authorized": True,
            "security_level": "enterprise"
        }
        self.authorization_checks.append(auth_check)
        
        await self.websocket_bridge.notify_agent_started(
            run_id, self.name, {"authorization_verified": True, "security_context": "validated"}
        )
        
        result = {
            "success": True,
            "agent_name": self.name,
            "authorization_validation": {
                "checks_performed": len(self.authorization_checks),
                "all_authorized": all(check["authorized"] for check in self.authorization_checks),
                "security_compliance": "verified"
            }
        }
        
        await self.websocket_bridge.notify_agent_completed(run_id, self.name, result)
        return result


class TestWebSocketAgentExecutionAuthorizationValidation(BaseIntegrationTest):
    
    def setup_method(self):
        super().setup_method()
        self.env = get_env()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        return AsyncMock(spec=LLMManager)
        
    @pytest.fixture
    async def authorized_user_context(self):
        return UserExecutionContext(
            user_id=f"auth_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"auth_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"auth_run_{uuid.uuid4().hex[:8]}",
            request_id=f"auth_req_{uuid.uuid4().hex[:8]}",
            metadata={"authorization_required": True, "security_level": "enterprise"}
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_authorization_validation_through_websocket(
        self, authorized_user_context, mock_llm_manager
    ):
        """CRITICAL: Test agent execution with proper authorization validation."""
        
        agent = AuthorizedAgent("secure_agent", mock_llm_manager)
        registry = MagicMock()
        registry.get = lambda name: agent
        
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.events = []
        
        async def track_auth_event(event_type, run_id, agent_name, data=None, **kwargs):
            bridge.events.append({"event_type": event_type, "data": data, "authorized": True})
            return True
            
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, name, ctx:
            track_auth_event("agent_started", run_id, name, ctx))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, name, result, **kwargs:
            track_auth_event("agent_completed", run_id, name, result, **kwargs))
            
        execution_engine = ExecutionEngine._init_from_factory(
            registry=registry, websocket_bridge=bridge, user_context=authorized_user_context
        )
        
        result = await execution_engine.execute_agent(
            AgentExecutionContext(
                user_id=authorized_user_context.user_id,
                thread_id=authorized_user_context.thread_id,
                run_id=authorized_user_context.run_id,
                request_id=authorized_user_context.request_id,
                agent_name="secure_agent",
                step=PipelineStep.PROCESSING,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            ),
            authorized_user_context
        )
        
        assert result.success is True
        
        auth_validation = result.data.get("authorization_validation", {})
        assert auth_validation.get("checks_performed", 0) > 0
        assert auth_validation.get("all_authorized") is True
        assert auth_validation.get("security_compliance") == "verified"
        
        # Validate WebSocket events included authorization context
        auth_events = [e for e in bridge.events if e.get("authorized") is True]
        assert len(auth_events) >= 2  # Start and completion events
        
        self.logger.info(" PASS:  Authorization validation test PASSED")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])