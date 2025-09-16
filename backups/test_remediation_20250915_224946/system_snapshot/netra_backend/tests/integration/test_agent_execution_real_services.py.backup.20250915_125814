"""
Test Agent Execution with Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable AI agent execution for core value delivery
- Value Impact: Validates agent execution that provides 90% of user value
- Strategic Impact: Core AI functionality for customer satisfaction and retention
"""

import pytest
import uuid
from datetime import datetime, timezone

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.services.user_execution_context import UserExecutionContext
from test_framework.base_integration_test import BaseIntegrationTest


class TestAgentExecutionRealServices(BaseIntegrationTest):
    """Test agent execution with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_with_real_database(self):
        """Test agent execution with real database persistence."""
        # Given: User context for agent execution
        user_context = UserExecutionContext(
            user_id=str(uuid.uuid4()),
            email="test@company.com",
            subscription_tier="premium",
            permissions=["execute_agents"],
            thread_id=str(uuid.uuid4())
        )
        
        execution_core = AgentExecutionCore()
        
        # When: Executing agent with real database
        execution_result = await execution_core.execute_agent(
            agent_type="basic_triage_agent",
            user_input="Test user query",
            user_context=user_context
        )
        
        # Then: Execution should complete successfully
        assert execution_result is not None
        assert execution_result.get("status") == "completed"
        assert execution_result.get("user_id") == user_context.user_id