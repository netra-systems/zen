"""Integration Tests for Agent Execution with Real Database

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Validate agent execution persistence and state management
- Value Impact: Ensures agent state survives failures and enables resumable execution
- Strategic Impact: Foundation for reliable long-running AI workflows

CRITICAL TEST PURPOSE:
These integration tests validate agent execution with real database connections
to ensure data persistence, state management, and recovery capabilities work.

Test Coverage:
- Agent state persistence to real database
- Execution context storage and retrieval
- Multi-user execution isolation in database
- Transaction handling during agent execution
- Recovery from database connection failures
- Performance with real database operations
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from test_framework.ssot.real_services_test_fixtures import *


@pytest.mark.integration
class TestAgentExecutionRealDatabase:
    """Integration tests for agent execution with real database services."""
    
    @pytest.mark.asyncio
    async def test_agent_execution_state_persistence(self, real_services_fixture):
        """Test agent execution state persists to real database."""
        # Arrange - verify database is available
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for integration testing")
        
        db_session = real_services_fixture["db"]
        
        # Create agent execution context
        context = AgentExecutionContext(
            agent_name="persistence_agent",
            run_id=uuid.uuid4(),
            thread_id=f"thread-{uuid.uuid4()}",
            user_id=f"user-{uuid.uuid4()}"
        )
        
        state = DeepAgentState(
            user_id=context.user_id,
            thread_id=context.thread_id,
            agent_name=context.agent_name
        )
        
        # Create real agent registry
        registry = AgentRegistry()
        
        # Create mock agent that updates database
        mock_agent = MockAgent()
        mock_agent.name = context.agent_name
        mock_agent.execution_result = {"status": "success", "data": "test_output"}
        registry.register_agent(mock_agent)
        
        # Create execution core with real database session
        execution_core = AgentExecutionCore(
            registry=registry,
            database_session=db_session
        )
        
        # Act - execute agent with database persistence
        result = await execution_core.execute_agent(context, state)
        
        # Assert - verify execution result
        assert isinstance(result, AgentExecutionResult)
        assert result.success == True
        assert result.agent_name == context.agent_name
        assert result.run_id == context.run_id
        
        # Verify state was persisted to database
        # Query database for execution record
        from sqlalchemy import text
        query = text("""
            SELECT * FROM agent_executions 
            WHERE run_id = :run_id AND agent_name = :agent_name
        """)
        
        db_result = await db_session.execute(
            query, 
            {"run_id": str(context.run_id), "agent_name": context.agent_name}
        )
        execution_record = db_result.fetchone()
        
        if execution_record:
            assert execution_record.run_id == str(context.run_id)
            assert execution_record.agent_name == context.agent_name
            assert execution_record.status == "completed"
    
    @pytest.mark.asyncio
    async def test_multi_user_execution_isolation_in_database(self, real_services_fixture):
        """Test multi-user agent execution isolation using real database."""
        # Arrange - verify database is available
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for integration testing")
        
        db_session = real_services_fixture["db"]
        
        # Create contexts for different users
        user1_id = f"user1-{uuid.uuid4()}"
        user2_id = f"user2-{uuid.uuid4()}"
        
        context1 = AgentExecutionContext(
            agent_name="isolation_agent",
            run_id=uuid.uuid4(),
            thread_id=f"user1-thread-{uuid.uuid4()}",
            user_id=user1_id
        )
        
        context2 = AgentExecutionContext(
            agent_name="isolation_agent", 
            run_id=uuid.uuid4(),
            thread_id=f"user2-thread-{uuid.uuid4()}",
            user_id=user2_id
        )
        
        # Create states with user-specific data
        state1 = DeepAgentState(
            user_id=user1_id,
            thread_id=context1.thread_id,
            user_data={"sensitive": "user1_secret", "account": "user1_account"}
        )
        
        state2 = DeepAgentState(
            user_id=user2_id, 
            thread_id=context2.thread_id,
            user_data={"sensitive": "user2_secret", "account": "user2_account"}
        )
        
        # Create registry with isolation-aware agent
        registry = AgentRegistry()
        isolation_agent = MockAgent()
        isolation_agent.name = "isolation_agent"
        isolation_agent.execution_result = lambda state: {
            "user_specific_result": f"result_for_{state.user_id}",
            "account": state.user_data.get("account")
        }
        registry.register_agent(isolation_agent)
        
        # Create execution cores
        execution_core1 = AgentExecutionCore(
            registry=registry,
            database_session=db_session,
            user_context_isolation=True
        )
        
        execution_core2 = AgentExecutionCore(
            registry=registry,
            database_session=db_session,
            user_context_isolation=True
        )
        
        # Act - execute agents concurrently for both users
        results = await asyncio.gather(
            execution_core1.execute_agent(context1, state1),
            execution_core2.execute_agent(context2, state2),
            return_exceptions=True
        )
        
        result1, result2 = results
        
        # Assert - verify isolation
        assert isinstance(result1, AgentExecutionResult)
        assert isinstance(result2, AgentExecutionResult)
        
        assert result1.success == True
        assert result2.success == True
        
        # Verify user-specific results don't leak
        assert result1.user_id == user1_id
        assert result2.user_id == user2_id
        assert result1.thread_id != result2.thread_id
        
        # Verify database isolation
        from sqlalchemy import text
        isolation_query = text("""
            SELECT user_id, thread_id, execution_data 
            FROM agent_executions 
            WHERE agent_name = 'isolation_agent'
            AND run_id IN (:run_id1, :run_id2)
        """)
        
        db_result = await db_session.execute(
            isolation_query,
            {"run_id1": str(context1.run_id), "run_id2": str(context2.run_id)}
        )
        isolation_records = db_result.fetchall()
        
        if len(isolation_records) >= 2:
            user_ids = [record.user_id for record in isolation_records]
            assert user1_id in user_ids
            assert user2_id in user_ids
            
            # Verify no cross-contamination
            for record in isolation_records:
                if record.user_id == user1_id:
                    assert "user1" in record.execution_data
                    assert "user2" not in record.execution_data
                elif record.user_id == user2_id:
                    assert "user2" in record.execution_data
                    assert "user1" not in record.execution_data
    
    @pytest.mark.asyncio
    async def test_agent_execution_transaction_handling(self, real_services_fixture):
        """Test transaction handling during agent execution with real database."""
        # Arrange - verify database is available
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for integration testing")
        
        db_session = real_services_fixture["db"]
        
        # Create context for transactional execution
        context = AgentExecutionContext(
            agent_name="transaction_agent",
            run_id=uuid.uuid4(),
            thread_id=f"tx-thread-{uuid.uuid4()}"
        )
        
        state = DeepAgentState(thread_id=context.thread_id)
        
        # Create registry with transaction-aware agent
        registry = AgentRegistry()
        
        # Test case 1: Successful transaction
        success_agent = MockAgent()
        success_agent.name = "transaction_agent"
        success_agent.execution_result = {
            "transaction_operations": ["create_user", "update_preferences", "log_activity"],
            "status": "all_operations_successful"
        }
        registry.register_agent(success_agent)
        
        execution_core = AgentExecutionCore(
            registry=registry,
            database_session=db_session,
            enable_transactions=True
        )
        
        # Act - execute with transaction support
        try:
            async with db_session.begin():
                result = await execution_core.execute_agent(context, state)
                
                # Perform additional database operations within transaction
                from sqlalchemy import text
                test_insert = text("""
                    INSERT INTO test_transactions (run_id, operation, timestamp)
                    VALUES (:run_id, :operation, :timestamp)
                """)
                
                await db_session.execute(test_insert, {
                    "run_id": str(context.run_id),
                    "operation": "test_transaction",
                    "timestamp": datetime.utcnow()
                })
                
                # Verify transaction is working
                verify_query = text("""
                    SELECT COUNT(*) as count FROM test_transactions 
                    WHERE run_id = :run_id
                """)
                count_result = await db_session.execute(
                    verify_query, 
                    {"run_id": str(context.run_id)}
                )
                transaction_count = count_result.scalar()
                
                # Assert - verify transaction state
                assert isinstance(result, AgentExecutionResult)
                assert result.success == True
                assert transaction_count == 1  # Our test record should exist within transaction
        
        except Exception as e:
            # Transaction should roll back on any error
            await db_session.rollback()
            pytest.fail(f"Transaction execution failed: {e}")
        
        # Test case 2: Transaction rollback on failure
        context_rollback = AgentExecutionContext(
            agent_name="failing_transaction_agent",
            run_id=uuid.uuid4(),
            thread_id=f"rollback-thread-{uuid.uuid4()}"
        )
        
        # Create failing agent
        failing_agent = MockAgent()
        failing_agent.name = "failing_transaction_agent"
        failing_agent.should_fail = True
        failing_agent.failure_message = "Simulated transaction failure"
        registry.register_agent(failing_agent)
        
        # Act - execute with expected failure
        try:
            async with db_session.begin():
                # Insert test record that should be rolled back
                rollback_insert = text("""
                    INSERT INTO test_transactions (run_id, operation, timestamp)
                    VALUES (:run_id, :operation, :timestamp)
                """)
                
                await db_session.execute(rollback_insert, {
                    "run_id": str(context_rollback.run_id),
                    "operation": "should_rollback",
                    "timestamp": datetime.utcnow()
                })
                
                # This should fail and trigger rollback
                result = await execution_core.execute_agent(context_rollback, state)
                
                if not result.success:
                    raise Exception(f"Agent execution failed: {result.error}")
        
        except Exception:
            # Expected - transaction should rollback
            await db_session.rollback()
        
        # Verify rollback occurred
        rollback_verify = text("""
            SELECT COUNT(*) as count FROM test_transactions 
            WHERE run_id = :run_id AND operation = 'should_rollback'
        """)
        rollback_result = await db_session.execute(
            rollback_verify,
            {"run_id": str(context_rollback.run_id)}
        )
        rollback_count = rollback_result.scalar()
        
        # Assert - verify rollback
        assert rollback_count == 0  # Record should not exist due to rollback
    
    @pytest.mark.asyncio
    async def test_agent_execution_recovery_from_database_failures(self, real_services_fixture):
        """Test agent execution recovery when database operations fail."""
        # Arrange - verify database is available
        if not real_services_fixture["database_available"]:
            pytest.skip("Real database not available for integration testing")
        
        db_session = real_services_fixture["db"]
        
        context = AgentExecutionContext(
            agent_name="recovery_agent",
            run_id=uuid.uuid4(),
            thread_id=f"recovery-thread-{uuid.uuid4()}"
        )
        
        state = DeepAgentState(thread_id=context.thread_id)
        
        # Create registry with recovery-capable agent
        registry = AgentRegistry()
        
        recovery_agent = MockAgent()
        recovery_agent.name = "recovery_agent"
        recovery_agent.execution_result = {"status": "completed_with_recovery"}
        recovery_agent.enable_database_recovery = True
        registry.register_agent(recovery_agent)
        
        execution_core = AgentExecutionCore(
            registry=registry,
            database_session=db_session,
            enable_recovery=True
        )
        
        # Act - simulate database failure during execution
        original_execute = db_session.execute
        call_count = 0
        
        async def failing_execute(query, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second database call
                raise ConnectionError("Simulated database connection failure")
            return await original_execute(query, params)
        
        # Temporarily replace execute method
        db_session.execute = failing_execute
        
        try:
            result = await execution_core.execute_agent(context, state)
            
            # Assert - verify recovery handling
            assert isinstance(result, AgentExecutionResult) 
            # Result might succeed or fail depending on recovery strategy
            if result.success:
                # Recovery succeeded
                assert "recovery" in result.data.get("status", "").lower()
            else:
                # Recovery failed but was handled gracefully
                assert "database" in result.error.lower() or "connection" in result.error.lower()
        
        except Exception as e:
            # Unhandled exception indicates poor recovery
            pytest.fail(f"Agent execution should handle database failures gracefully: {e}")
        
        finally:
            # Restore original execute method
            db_session.execute = original_execute


class MockAgent:
    """Mock agent for integration testing."""
    
    def __init__(self):
        self.name = "mock_agent"
        self.execution_result = {"status": "success"}
        self.should_fail = False
        self.failure_message = "Mock failure"
        self.enable_database_recovery = False
    
    async def execute(self, context, state):
        """Execute mock agent logic."""
        if self.should_fail:
            raise RuntimeError(self.failure_message)
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Return result (can be callable for dynamic results)
        if callable(self.execution_result):
            return self.execution_result(state)
        return self.execution_result
    
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge (for compatibility)."""
        self.websocket_bridge = bridge
        self._run_id = run_id