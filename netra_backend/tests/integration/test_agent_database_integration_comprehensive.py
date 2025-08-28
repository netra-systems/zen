"""
Comprehensive Agent-Database Integration Tests (Iterations 21-25).

Tests the integration between agent system and database operations,
including transaction handling, error recovery, and resilience patterns.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreaker
from netra_backend.app.core.health_types import HealthCheckResult


@pytest.mark.integration
class TestAgentDatabaseConnectionManagement:
    """Test database connection management within agents."""
    
    @pytest.mark.asyncio
    async def test_agent_database_connection_lifecycle(self):
        """Test agent manages database connections properly."""
        # Create a mock database manager
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            # Create agent with database dependency
            agent_state = DeepAgentState(
                agent_id="test_agent",
                session_id="test_session",
                thread_id="test_thread",
                context={"task": "database_query"}
            )
            
            # Initialize supervisor agent
            agent = SupervisorAgent(
                agent_id="supervisor_test",
                initial_state=agent_state
            )
            
            # Verify agent can access database through manager
            result = await agent._get_database_session()
            assert result is not None
            mock_db_manager.get_async_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_transaction_handling(self):
        """Test agent proper transaction management."""
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        mock_transaction = AsyncMock()
        
        # Setup transaction context
        mock_session.begin.return_value.__aenter__.return_value = mock_transaction
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="txn_agent",
                session_id="txn_session",
                thread_id="txn_thread",
                context={"operation": "multi_step_update"}
            )
            
            agent = SupervisorAgent(
                agent_id="txn_supervisor",
                initial_state=agent_state
            )
            
            # Execute transactional operation
            await agent._execute_transactional_operation([
                {"action": "insert", "table": "agents", "data": {"name": "test"}},
                {"action": "update", "table": "sessions", "data": {"status": "active"}}
            ])
            
            # Verify transaction was properly handled
            mock_session.begin.assert_called_once()
            mock_transaction.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_connection_recovery(self):
        """Test agent handles database connection failures gracefully."""
        mock_db_manager = Mock()
        
        # Simulate connection failure then recovery
        failure_then_success = [
            Exception("Connection lost"),
            AsyncMock()  # Successful session
        ]
        mock_db_manager.get_async_session.side_effect = failure_then_success
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="recovery_agent",
                session_id="recovery_session", 
                thread_id="recovery_thread",
                context={"retry_policy": "exponential_backoff"}
            )
            
            agent = SupervisorAgent(
                agent_id="recovery_supervisor",
                initial_state=agent_state
            )
            
            # Agent should retry and eventually succeed
            result = await agent._execute_with_retry(
                operation="database_query",
                max_retries=3
            )
            
            assert result["status"] == "success"
            assert result["attempts"] == 2
            assert mock_db_manager.get_async_session.call_count == 2


@pytest.mark.integration
class TestAgentDataSubAgentIntegration:
    """Test integration between supervisor and data sub-agents."""
    
    @pytest.mark.asyncio
    async def test_clickhouse_agent_integration(self):
        """Test ClickHouse data sub-agent integration with database operations."""
        # Mock ClickHouse client
        mock_clickhouse_client = Mock(spec=ClickHouseClient)
        mock_clickhouse_client.execute_query = AsyncMock(return_value=[
            {"metric": "latency", "value": 150, "timestamp": "2024-01-01T00:00:00Z"},
            {"metric": "throughput", "value": 1000, "timestamp": "2024-01-01T00:00:00Z"}
        ])
        mock_clickhouse_client.get_health_status.return_value = HealthCheckResult(
            component_name="clickhouse",
            success=True,
            health_score=1.0,
            status="healthy"
        )
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.ClickHouseClient', 
                  return_value=mock_clickhouse_client):
            
            # Create supervisor agent with data sub-agent task
            agent_state = DeepAgentState(
                agent_id="data_supervisor",
                session_id="data_session",
                thread_id="data_thread",
                context={
                    "task_type": "data_analysis",
                    "query_type": "workload_metrics",
                    "time_range": "24h"
                }
            )
            
            agent = SupervisorAgent(
                agent_id="data_integration_test",
                initial_state=agent_state
            )
            
            # Execute data analysis task
            result = await agent._delegate_to_data_agent({
                "analysis_type": "workload_analysis",
                "timeframe": "24h",
                "metrics": ["latency", "throughput"]
            })
            
            assert result["status"] == "completed"
            assert len(result["data"]) == 2
            assert result["data"][0]["metric"] == "latency"
            mock_clickhouse_client.execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_data_agent_error_handling_with_fallback(self):
        """Test data sub-agent error handling with database fallback."""
        # Primary ClickHouse fails, fallback to PostgreSQL
        mock_clickhouse_client = Mock(spec=ClickHouseClient)
        mock_clickhouse_client.execute_query = AsyncMock(
            side_effect=Exception("ClickHouse unavailable")
        )
        
        mock_postgres_manager = Mock()
        mock_postgres_session = AsyncMock()
        mock_postgres_manager.get_async_session.return_value.__aenter__.return_value = mock_postgres_session
        
        with patch('netra_backend.app.agents.data_sub_agent.clickhouse_client.ClickHouseClient', 
                  return_value=mock_clickhouse_client):
            with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', 
                      mock_postgres_manager):
                
                agent_state = DeepAgentState(
                    agent_id="fallback_agent",
                    session_id="fallback_session",
                    thread_id="fallback_thread",
                    context={"fallback_enabled": True}
                )
                
                agent = SupervisorAgent(
                    agent_id="fallback_test",
                    initial_state=agent_state
                )
                
                result = await agent._execute_data_query_with_fallback({
                    "query": "SELECT COUNT(*) FROM metrics",
                    "primary_source": "clickhouse",
                    "fallback_source": "postgres"
                })
                
                assert result["status"] == "completed_with_fallback"
                assert result["source_used"] == "postgres"
                mock_clickhouse_client.execute_query.assert_called_once()
                mock_postgres_manager.get_async_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_batch_database_operations(self):
        """Test agent handles batch database operations efficiently."""
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        # Mock batch execution
        mock_session.execute_batch = AsyncMock(return_value=Mock(rowcount=5))
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="batch_agent",
                session_id="batch_session",
                thread_id="batch_thread",
                context={"operation_type": "batch_insert"}
            )
            
            agent = SupervisorAgent(
                agent_id="batch_test",
                initial_state=agent_state
            )
            
            # Execute batch operations
            operations = [
                {"table": "agent_logs", "data": {"message": f"Log {i}", "level": "info"}}
                for i in range(5)
            ]
            
            result = await agent._execute_batch_operations(operations)
            
            assert result["status"] == "success"
            assert result["processed_count"] == 5
            mock_session.execute_batch.assert_called_once()


@pytest.mark.integration 
class TestAgentCircuitBreakerIntegration:
    """Test agent integration with circuit breaker patterns."""
    
    @pytest.mark.asyncio
    async def test_agent_database_circuit_breaker(self):
        """Test agent respects database circuit breaker state."""
        # Setup circuit breaker to be in open state
        mock_circuit_breaker = Mock(spec=UnifiedCircuitBreaker)
        mock_circuit_breaker.is_open = True
        mock_circuit_breaker.call = AsyncMock(
            side_effect=Exception("Circuit breaker open")
        )
        
        with patch('netra_backend.app.core.resilience.circuit_breaker_manager.get_circuit_breaker',
                  return_value=mock_circuit_breaker):
            
            agent_state = DeepAgentState(
                agent_id="circuit_agent",
                session_id="circuit_session",
                thread_id="circuit_thread",
                context={"circuit_breaker_enabled": True}
            )
            
            agent = SupervisorAgent(
                agent_id="circuit_test",
                initial_state=agent_state
            )
            
            # Attempt database operation with circuit breaker open
            result = await agent._execute_protected_database_operation({
                "operation": "SELECT * FROM agents",
                "circuit_breaker_name": "database_retry_circuit"
            })
            
            assert result["status"] == "circuit_breaker_open"
            assert result["fallback_used"] is True
            mock_circuit_breaker.call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_circuit_breaker_recovery(self):
        """Test agent handles circuit breaker recovery properly."""
        mock_circuit_breaker = Mock(spec=UnifiedCircuitBreaker)
        
        # Circuit breaker transitions from open -> half-open -> closed
        states = ["open", "half_open", "closed"]
        state_iter = iter(states)
        
        def get_state():
            return next(state_iter, "closed")
        
        mock_circuit_breaker.is_open = property(lambda self: get_state() == "open")
        mock_circuit_breaker.call = AsyncMock(return_value="success")
        
        with patch('netra_backend.app.core.resilience.circuit_breaker_manager.get_circuit_breaker',
                  return_value=mock_circuit_breaker):
            
            agent_state = DeepAgentState(
                agent_id="recovery_agent",
                session_id="recovery_session",
                thread_id="recovery_thread",
                context={"circuit_breaker_monitoring": True}
            )
            
            agent = SupervisorAgent(
                agent_id="recovery_test", 
                initial_state=agent_state
            )
            
            # Monitor circuit breaker recovery
            results = []
            for i in range(3):
                result = await agent._check_circuit_breaker_status("database_retry_circuit")
                results.append(result)
                await asyncio.sleep(0.01)  # Small delay
            
            # Verify progression through states
            assert len(results) == 3
            assert results[0]["circuit_state"] == "open"
            assert results[1]["circuit_state"] == "half_open"
            assert results[2]["circuit_state"] == "closed"


@pytest.mark.integration
class TestAgentDatabasePerformance:
    """Test agent database performance and optimization patterns."""
    
    @pytest.mark.asyncio
    async def test_agent_connection_pooling_efficiency(self):
        """Test agent efficiently uses database connection pooling."""
        mock_db_manager = Mock()
        mock_pool = Mock()
        mock_pool.stats = {
            "pool_size": 10,
            "checked_in": 8,
            "checked_out": 2,
            "overflow": 0,
            "invalidated": 0
        }
        mock_db_manager.get_pool_stats.return_value = mock_pool.stats
        
        # Create multiple concurrent agents
        agents = []
        for i in range(5):
            agent_state = DeepAgentState(
                agent_id=f"pool_agent_{i}",
                session_id=f"pool_session_{i}",
                thread_id=f"pool_thread_{i}",
                context={"concurrent_operation": True}
            )
            agent = SupervisorAgent(
                agent_id=f"pool_test_{i}",
                initial_state=agent_state
            )
            agents.append(agent)
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            # Execute concurrent database operations
            tasks = [
                agent._execute_database_operation({"query": f"SELECT {i}"})
                for i, agent in enumerate(agents)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all operations completed successfully
            assert len(results) == 5
            assert all(isinstance(r, dict) and r.get("status") == "success" for r in results)
            
            # Check pool stats
            pool_stats = mock_db_manager.get_pool_stats()
            assert pool_stats["pool_size"] == 10
            assert pool_stats["checked_out"] <= 5  # All concurrent operations
    
    @pytest.mark.asyncio
    async def test_agent_query_optimization(self):
        """Test agent applies query optimization strategies."""
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [{"id": 1, "name": "test"}]
        mock_session.execute.return_value = mock_result
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="optimization_agent",
                session_id="optimization_session",
                thread_id="optimization_thread",
                context={"query_optimization": True}
            )
            
            agent = SupervisorAgent(
                agent_id="optimization_test",
                initial_state=agent_state
            )
            
            # Execute query with optimization hints
            result = await agent._execute_optimized_query({
                "base_query": "SELECT * FROM large_table",
                "filters": {"status": "active", "created_at": "> '2024-01-01'"},
                "optimization_hints": ["use_index", "limit_results", "parallel_scan"],
                "limit": 1000
            })
            
            assert result["status"] == "success"
            assert result["optimization_applied"] is True
            assert result["execution_time_ms"] < 1000  # Should be optimized
            mock_session.execute.assert_called_once()
            
            # Verify query was optimized
            executed_query = mock_session.execute.call_args[0][0]
            assert "LIMIT 1000" in str(executed_query)
            assert "WHERE" in str(executed_query)


@pytest.mark.integration
class TestAgentDatabaseConsistency:
    """Test agent maintains database consistency across operations."""
    
    @pytest.mark.asyncio
    async def test_agent_state_persistence_consistency(self):
        """Test agent state changes are consistently persisted."""
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        # Track state changes
        state_changes = []
        
        def track_execute(query):
            state_changes.append(str(query))
            return AsyncMock()
        
        mock_session.execute = AsyncMock(side_effect=track_execute)
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="consistency_agent",
                session_id="consistency_session", 
                thread_id="consistency_thread",
                context={"state_tracking": True}
            )
            
            agent = SupervisorAgent(
                agent_id="consistency_test",
                initial_state=agent_state
            )
            
            # Execute state-changing operations
            await agent._update_agent_status("processing")
            await agent._update_task_progress(25)
            await agent._update_task_progress(50)
            await agent._update_agent_status("completed")
            
            # Verify all state changes were persisted in order
            assert len(state_changes) == 4
            assert "processing" in state_changes[0]
            assert "25" in state_changes[1]
            assert "50" in state_changes[2]  
            assert "completed" in state_changes[3]
    
    @pytest.mark.asyncio
    async def test_agent_concurrent_state_updates(self):
        """Test agent handles concurrent state updates without conflicts."""
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        
        # Simulate version-based optimistic locking
        current_version = 1
        
        def execute_with_version_check(query):
            nonlocal current_version
            if "UPDATE" in str(query) and f"version = {current_version}" in str(query):
                current_version += 1
                return AsyncMock(rowcount=1)  # Success
            return AsyncMock(rowcount=0)  # Version conflict
        
        mock_session.execute = AsyncMock(side_effect=execute_with_version_check)
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="concurrent_agent",
                session_id="concurrent_session",
                thread_id="concurrent_thread", 
                context={"version": current_version}
            )
            
            agent = SupervisorAgent(
                agent_id="concurrent_test",
                initial_state=agent_state
            )
            
            # Simulate concurrent updates with conflict resolution
            result1 = await agent._update_state_with_version_check({
                "status": "processing",
                "expected_version": current_version
            })
            
            result2 = await agent._update_state_with_version_check({
                "progress": 50, 
                "expected_version": current_version + 1
            })
            
            assert result1["status"] == "success"
            assert result1["new_version"] == 2
            assert result2["status"] == "success" 
            assert result2["new_version"] == 3
            assert mock_session.execute.call_count == 2