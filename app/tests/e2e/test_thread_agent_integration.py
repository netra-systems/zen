"""Thread Agent Integration E2E Testing
Tests thread management with real agent workflows and data integrity validation.
"""

import pytest
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.thread_service import ThreadService
from app.services.agent_service import AgentService
from app.services.state_persistence_service import state_persistence_service
from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.schemas.agent_state import StatePersistenceRequest, CheckpointType, AgentPhase
from app.db.models_postgres import Thread, Message, Run
from app.core.exceptions_agent import AgentError


class ThreadAgentWorkflowTests:
    """Tests for thread management with real agent workflows."""
    
    @pytest.mark.asyncio
    async def test_thread_agent_workflow_integration(self, db_session: AsyncSession):
        """Test complete thread workflow with agent execution."""
        thread_service = ThreadService()
        agent_service = Mock(spec=AgentService)
        user_id = "workflow_user"
        
        await self._test_complete_agent_workflow(
            thread_service, agent_service, user_id, db_session
        )
    
    async def _test_complete_agent_workflow(
        self, thread_service: ThreadService, agent_service: Mock,
        user_id: str, db_session: AsyncSession
    ) -> None:
        """Test complete agent workflow within thread context."""
        # Create thread
        thread = await thread_service.get_or_create_thread(user_id, db_session)
        
        # Create user message
        user_message = await thread_service.create_message(
            thread.id, "user", "Optimize my database performance", db=db_session
        )
        
        # Start agent run
        run = await thread_service.create_run(
            thread.id, "supervisor_agent", 
            instructions="Provide database optimization recommendations",
            db=db_session
        )
        
        await self._simulate_agent_execution(
            thread_service, agent_service, thread, run, db_session
        )
    
    async def _simulate_agent_execution(
        self, thread_service: ThreadService, agent_service: Mock,
        thread: Thread, run: Run, db_session: AsyncSession
    ) -> None:
        """Simulate agent execution with state management."""
        # Mock agent execution phases
        execution_phases = [
            (AgentPhase.TRIAGE, "Analyzing request"),
            (AgentPhase.DATA_ANALYSIS, "Examining database metrics"),
            (AgentPhase.OPTIMIZATION, "Generating recommendations"),
            (AgentPhase.REPORTING, "Preparing response")
        ]
        
        for phase, description in execution_phases:
            await self._execute_agent_phase(
                thread_service, thread, run, phase, description, db_session
            )
        
        # Complete the run
        await thread_service.update_run_status(run.id, "completed", db=db_session)
    
    async def _execute_agent_phase(
        self, thread_service: ThreadService, thread: Thread, run: Run,
        phase: AgentPhase, description: str, db_session: AsyncSession
    ) -> None:
        """Execute single agent phase with state persistence."""
        # Persist agent state for this phase
        state_data = {
            "step_count": 1,
            "user_request": "Optimize database performance",
            "metadata": {
                "phase": phase.value,
                "description": description,
                "thread_id": thread.id,
                "run_id": run.id
            }
        }
        
        request = StatePersistenceRequest(
            run_id=run.id,
            thread_id=thread.id,
            user_id=thread.metadata_.get("user_id"),
            state_data=state_data,
            checkpoint_type=CheckpointType.PHASE_TRANSITION,
            agent_phase=phase
        )
        
        success, snapshot_id = await state_persistence_service.save_agent_state(
            request, db_session
        )
        assert success
        assert snapshot_id is not None
    
    @pytest.mark.asyncio
    async def test_multi_agent_thread_coordination(self, db_session: AsyncSession):
        """Test multiple agents coordinating within same thread."""
        thread_service = ThreadService()
        user_id = "multi_agent_user"
        
        thread = await thread_service.get_or_create_thread(user_id, db_session)
        
        await self._test_agent_coordination(thread_service, thread, db_session)
    
    async def _test_agent_coordination(
        self, thread_service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test coordination between multiple agents."""
        # Create runs for different agents
        supervisor_run = await thread_service.create_run(
            thread.id, "supervisor_agent", model="gpt-4", db=db_session
        )
        data_run = await thread_service.create_run(
            thread.id, "data_sub_agent", model="gpt-3.5-turbo", db=db_session
        )
        
        # Simulate agent coordination
        await self._simulate_agent_handoff(
            thread_service, thread, supervisor_run, data_run, db_session
        )
    
    async def _simulate_agent_handoff(
        self, thread_service: ThreadService, thread: Thread,
        supervisor_run: Run, data_run: Run, db_session: AsyncSession
    ) -> None:
        """Simulate handoff between supervisor and data agent."""
        # Supervisor delegates to data agent
        handoff_message = await thread_service.create_message(
            thread.id, "assistant", 
            "Delegating to data analysis agent",
            assistant_id="supervisor_agent",
            run_id=supervisor_run.id,
            metadata={"handoff_to": "data_sub_agent"},
            db=db_session
        )
        
        # Data agent processes request
        analysis_message = await thread_service.create_message(
            thread.id, "assistant",
            "Completed data analysis",
            assistant_id="data_sub_agent", 
            run_id=data_run.id,
            metadata={"completed_analysis": True},
            db=db_session
        )
        
        # Verify coordination integrity
        await self._verify_coordination_integrity(
            thread_service, thread, [handoff_message, analysis_message], db_session
        )
    
    async def _verify_coordination_integrity(
        self, thread_service: ThreadService, thread: Thread,
        messages: List[Message], db_session: AsyncSession
    ) -> None:
        """Verify agent coordination maintains data integrity."""
        thread_messages = await thread_service.get_thread_messages(
            thread.id, db=db_session
        )
        
        # Verify all coordination messages are present
        coordination_messages = [
            msg for msg in thread_messages 
            if msg.metadata_ and ("handoff_to" in msg.metadata_ or "completed_analysis" in msg.metadata_)
        ]
        
        assert len(coordination_messages) == 2
        
        # Verify proper sequencing
        assert coordination_messages[0].metadata_.get("handoff_to") == "data_sub_agent"
        assert coordination_messages[1].metadata_.get("completed_analysis") is True


class ThreadDataIntegrityTests:
    """Tests for data integrity validation in thread operations."""
    
    @pytest.mark.asyncio
    async def test_thread_data_integrity_validation(self, db_session: AsyncSession):
        """Test comprehensive data integrity validation."""
        thread_service = ThreadService()
        user_id = "integrity_user"
        
        thread = await thread_service.get_or_create_thread(user_id, db_session)
        
        await self._test_data_consistency_checks(thread_service, thread, db_session)
    
    async def _test_data_consistency_checks(
        self, thread_service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test data consistency throughout thread lifecycle."""
        # Create multiple related entities
        user_msg = await thread_service.create_message(
            thread.id, "user", "Test message", db=db_session
        )
        
        run = await thread_service.create_run(
            thread.id, "test_agent", db=db_session
        )
        
        agent_msg = await thread_service.create_message(
            thread.id, "assistant", "Agent response",
            assistant_id="test_agent", run_id=run.id, db=db_session
        )
        
        await self._verify_relational_integrity(
            thread_service, thread, user_msg, run, agent_msg, db_session
        )
    
    async def _verify_relational_integrity(
        self, thread_service: ThreadService, thread: Thread,
        user_msg: Message, run: Run, agent_msg: Message, db_session: AsyncSession
    ) -> None:
        """Verify relational integrity between thread entities."""
        # Verify message-thread relationships
        assert user_msg.thread_id == thread.id
        assert agent_msg.thread_id == thread.id
        
        # Verify run-thread relationship
        assert run.thread_id == thread.id
        
        # Verify message-run relationship
        assert agent_msg.run_id == run.id
        assert agent_msg.assistant_id == run.assistant_id
        
        # Verify temporal consistency
        assert user_msg.created_at <= agent_msg.created_at
    
    @pytest.mark.asyncio
    async def test_thread_state_consistency(self, db_session: AsyncSession):
        """Test thread state remains consistent across operations."""
        thread_service = ThreadService()
        user_id = "consistency_user"
        
        thread = await thread_service.get_or_create_thread(user_id, db_session)
        
        await self._test_state_consistency_validation(thread_service, thread, db_session)
    
    async def _test_state_consistency_validation(
        self, thread_service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test state consistency validation."""
        initial_metadata = thread.metadata_.copy() if thread.metadata_ else {}
        
        # Perform multiple operations
        operations = [
            lambda: thread_service.create_message(thread.id, "user", "Msg 1", db=db_session),
            lambda: thread_service.create_message(thread.id, "user", "Msg 2", db=db_session),
            lambda: thread_service.create_run(thread.id, "agent1", db=db_session)
        ]
        
        for operation in operations:
            await operation()
            await self._verify_thread_state_unchanged(
                thread_service, thread, initial_metadata, db_session
            )
    
    async def _verify_thread_state_unchanged(
        self, thread_service: ThreadService, thread: Thread,
        initial_metadata: Dict, db_session: AsyncSession
    ) -> None:
        """Verify thread core state remains unchanged."""
        current_thread = await thread_service.get_thread(thread.id, db_session)
        
        # Verify core attributes unchanged
        assert current_thread.id == thread.id
        assert current_thread.object == thread.object
        assert current_thread.created_at == thread.created_at
        
        # Verify user_id in metadata unchanged
        if initial_metadata.get("user_id"):
            assert current_thread.metadata_.get("user_id") == initial_metadata.get("user_id")


class ThreadErrorHandlingTests:
    """Tests for comprehensive error handling in thread operations."""
    
    @pytest.mark.asyncio
    async def test_thread_agent_error_recovery(self, db_session: AsyncSession):
        """Test thread operations recover gracefully from agent errors."""
        thread_service = ThreadService()
        user_id = "error_recovery_user"
        
        thread = await thread_service.get_or_create_thread(user_id, db_session)
        
        await self._test_agent_error_scenarios(thread_service, thread, db_session)
    
    async def _test_agent_error_scenarios(
        self, thread_service: ThreadService, thread: Thread, db_session: AsyncSession
    ) -> None:
        """Test various agent error scenarios."""
        # Create run that will fail
        run = await thread_service.create_run(
            thread.id, "failing_agent", db=db_session
        )
        
        # Simulate agent failure
        error_details = {
            "code": "AGENT_EXECUTION_ERROR",
            "message": "Agent failed during processing",
            "context": {"phase": "analysis", "step": 3}
        }
        
        # Update run with error
        failed_run = await thread_service.update_run_status(
            run.id, "failed", error=error_details, db=db_session
        )
        
        await self._verify_error_handling_integrity(
            thread_service, thread, failed_run, error_details, db_session
        )
    
    async def _verify_error_handling_integrity(
        self, thread_service: ThreadService, thread: Thread,
        failed_run: Run, error_details: Dict, db_session: AsyncSession
    ) -> None:
        """Verify error handling maintains thread integrity."""
        # Verify run status updated correctly
        assert failed_run.status == "failed"
        assert failed_run.last_error == error_details
        assert failed_run.failed_at is not None
        
        # Verify thread remains accessible
        current_thread = await thread_service.get_thread(thread.id, db_session)
        assert current_thread is not None
        assert current_thread.id == thread.id
        
        # Verify new operations can still be performed
        recovery_message = await thread_service.create_message(
            thread.id, "user", "Retry the operation", db=db_session
        )
        assert recovery_message is not None
        assert recovery_message.thread_id == thread.id
    
    @pytest.mark.asyncio
    async def test_concurrent_error_isolation(self, db_session: AsyncSession):
        """Test errors in one thread don't affect others."""
        thread_service = ThreadService()
        
        # Create multiple threads
        thread1 = await thread_service.get_or_create_thread("user1", db_session)
        thread2 = await thread_service.get_or_create_thread("user2", db_session)
        
        await self._test_error_isolation_between_threads(
            thread_service, thread1, thread2, db_session
        )
    
    async def _test_error_isolation_between_threads(
        self, thread_service: ThreadService, thread1: Thread, 
        thread2: Thread, db_session: AsyncSession
    ) -> None:
        """Test error isolation between concurrent threads."""
        # Create runs in both threads
        run1 = await thread_service.create_run(thread1.id, "agent1", db=db_session)
        run2 = await thread_service.create_run(thread2.id, "agent2", db=db_session)
        
        # Fail one run
        await thread_service.update_run_status(
            run1.id, "failed", 
            error={"code": "TEST_ERROR", "message": "Simulated failure"},
            db=db_session
        )
        
        # Verify the other thread is unaffected
        await self._verify_thread_isolation_after_error(
            thread_service, thread1, thread2, run2, db_session
        )
    
    async def _verify_thread_isolation_after_error(
        self, thread_service: ThreadService, failed_thread: Thread,
        healthy_thread: Thread, healthy_run: Run, db_session: AsyncSession
    ) -> None:
        """Verify healthy thread operations continue after error in other thread."""
        # Verify healthy thread can still operate normally
        success_message = await thread_service.create_message(
            healthy_thread.id, "assistant", "Operation successful",
            run_id=healthy_run.id, db=db_session
        )
        
        assert success_message is not None
        assert success_message.thread_id == healthy_thread.id
        
        # Complete the healthy run
        completed_run = await thread_service.update_run_status(
            healthy_run.id, "completed", db=db_session
        )
        
        assert completed_run.status == "completed"
        assert completed_run.completed_at is not None


@pytest.fixture
def mock_supervisor_agent():
    """Mock supervisor agent for testing."""
    agent = Mock(spec=SupervisorAgent)
    agent.process_request = AsyncMock()
    agent.delegate_to_subagent = AsyncMock()
    agent.finalize_response = AsyncMock()
    return agent


@pytest.fixture
def mock_data_sub_agent():
    """Mock data sub-agent for testing."""
    agent = Mock(spec=DataSubAgent)
    agent.analyze_data = AsyncMock()
    agent.generate_insights = AsyncMock()
    agent.create_recommendations = AsyncMock()
    return agent


@pytest.fixture
async def db_session():
    """Mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session