"""
Agent Database Resilience Tests - Part of Iterations 21-25.

Tests resilience patterns, error recovery, and fault tolerance 
in agent-database interactions.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any
import time
from datetime import datetime

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.core.resilience.unified_circuit_breaker import CircuitBreakerOpenError


@pytest.mark.integration
class TestAgentDatabaseResilience:
    """Test agent resilience patterns with database operations."""
    
    @pytest.mark.asyncio
    async def test_agent_database_retry_with_exponential_backoff(self):
        """Test agent implements exponential backoff for database retries."""
        mock_db_manager = Mock()
        
        # Simulate failures followed by success
        call_count = 0
        retry_times = []
        
        def failing_get_session(*args, **kwargs):
            nonlocal call_count
            retry_times.append(time.time())
            call_count += 1
            if call_count < 4:
                raise ConnectionError("Temporary database unavailable")
            return AsyncMock()
        
        mock_db_manager.get_async_session.side_effect = failing_get_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="retry_agent",
                session_id="retry_session",
                thread_id="retry_thread",
                context={
                    "retry_config": {
                        "max_retries": 5,
                        "base_delay": 0.1,
                        "exponential_base": 2,
                        "max_delay": 2.0
                    }
                }
            )
            
            agent = SupervisorAgent(
                agent_id="retry_test",
                initial_state=agent_state
            )
            
            start_time = time.time()
            result = await agent._execute_with_exponential_backoff(
                operation="database_connection",
                max_retries=5
            )
            end_time = time.time()
            
            # Verify exponential backoff timing
            assert result["status"] == "success"
            assert result["attempts"] == 4
            assert len(retry_times) == 4
            
            # Check backoff intervals (approximately exponential)
            if len(retry_times) > 1:
                interval1 = retry_times[1] - retry_times[0]
                interval2 = retry_times[2] - retry_times[1]
                interval3 = retry_times[3] - retry_times[2]
                
                assert interval2 > interval1  # Exponential increase
                assert interval3 > interval2  # Continues to increase
                assert end_time - start_time >= 0.7  # Total backoff time
    
    @pytest.mark.asyncio
    async def test_agent_database_timeout_handling(self):
        """Test agent handles database operation timeouts gracefully."""
        mock_db_manager = Mock()
        
        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(2.0)  # Simulate slow operation
            return AsyncMock()
        
        mock_db_manager.get_async_session.side_effect = slow_operation
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="timeout_agent",
                session_id="timeout_session",
                thread_id="timeout_thread",
                context={"operation_timeout": 0.5}  # 500ms timeout
            )
            
            agent = SupervisorAgent(
                agent_id="timeout_test",
                initial_state=agent_state
            )
            
            start_time = time.time()
            result = await agent._execute_with_timeout(
                operation="slow_database_query",
                timeout_seconds=0.5
            )
            end_time = time.time()
            
            assert result["status"] == "timeout"
            assert result["timeout_seconds"] == 0.5
            assert end_time - start_time < 1.0  # Timeout was enforced
            assert "fallback_strategy" in result
    
    @pytest.mark.asyncio
    async def test_agent_database_deadlock_detection_recovery(self):
        """Test agent detects and recovers from database deadlocks."""
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        
        # Simulate deadlock on first attempt, success on retry
        deadlock_error = Exception("Deadlock detected")
        deadlock_error.orig = Mock()
        deadlock_error.orig.pgcode = "40001"  # PostgreSQL deadlock code
        
        call_count = 0
        
        def deadlock_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise deadlock_error
            return {"result": "success", "rows_affected": 1}
        
        mock_session.execute = AsyncMock(side_effect=deadlock_then_success)
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="deadlock_agent",
                session_id="deadlock_session",
                thread_id="deadlock_thread",
                context={"deadlock_detection": True}
            )
            
            agent = SupervisorAgent(
                agent_id="deadlock_test",
                initial_state=agent_state
            )
            
            result = await agent._execute_with_deadlock_recovery({
                "query": "UPDATE accounts SET balance = balance - 100 WHERE id = 1",
                "max_deadlock_retries": 3
            })
            
            assert result["status"] == "success"
            assert result["deadlock_retries"] == 1
            assert result["final_attempt"] == 2
            assert mock_session.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_agent_database_connection_pool_exhaustion(self):
        """Test agent handles connection pool exhaustion gracefully."""
        mock_db_manager = Mock()
        
        # Simulate pool exhaustion
        pool_exhaustion_error = Exception("Connection pool exhausted")
        pool_exhaustion_error.orig = Mock()
        pool_exhaustion_error.orig.pgcode = "53300"  # Too many connections
        
        mock_db_manager.get_async_session.side_effect = [
            pool_exhaustion_error,  # First attempt fails
            pool_exhaustion_error,  # Second attempt fails
            AsyncMock()  # Third attempt succeeds after pool recovery
        ]
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="pool_agent", 
                session_id="pool_session",
                thread_id="pool_thread",
                context={"pool_recovery_enabled": True}
            )
            
            agent = SupervisorAgent(
                agent_id="pool_test",
                initial_state=agent_state
            )
            
            result = await agent._execute_with_pool_recovery({
                "operation": "critical_query",
                "pool_wait_timeout": 1.0,
                "max_pool_retries": 3
            })
            
            assert result["status"] == "success"
            assert result["pool_exhaustion_retries"] == 2
            assert result["pool_recovery_time_ms"] > 0
            assert mock_db_manager.get_async_session.call_count == 3


@pytest.mark.integration
class TestAgentDatabaseFailover:
    """Test agent database failover scenarios."""
    
    @pytest.mark.asyncio
    async def test_agent_primary_secondary_failover(self):
        """Test agent fails over from primary to secondary database."""
        # Setup primary and secondary database managers
        mock_primary_db = Mock()
        mock_secondary_db = Mock()
        
        # Primary fails, secondary succeeds
        mock_primary_db.get_async_session.side_effect = Exception("Primary database unavailable")
        mock_secondary_session = AsyncMock()
        mock_secondary_db.get_async_session.return_value.__aenter__.return_value = mock_secondary_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_primary_db):
            with patch('netra_backend.app.core.unified.db_connection_manager.secondary_db_manager', mock_secondary_db):
                
                agent_state = DeepAgentState(
                    agent_id="failover_agent",
                    session_id="failover_session", 
                    thread_id="failover_thread",
                    context={"failover_enabled": True}
                )
                
                agent = SupervisorAgent(
                    agent_id="failover_test",
                    initial_state=agent_state
                )
                
                result = await agent._execute_with_failover({
                    "query": "SELECT * FROM critical_data",
                    "read_preference": "primary_preferred"
                })
                
                assert result["status"] == "success"
                assert result["database_used"] == "secondary"
                assert result["failover_triggered"] is True
                assert result["failover_time_ms"] > 0
                
                # Verify primary was tried first, then secondary
                mock_primary_db.get_async_session.assert_called_once()
                mock_secondary_db.get_async_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_read_replica_routing(self):
        """Test agent routes read operations to read replicas."""
        mock_primary_db = Mock()
        mock_replica_db = Mock()
        
        # Setup different response times
        mock_primary_session = AsyncMock()
        mock_replica_session = AsyncMock()
        
        mock_primary_db.get_async_session.return_value.__aenter__.return_value = mock_primary_session
        mock_replica_db.get_async_session.return_value.__aenter__.return_value = mock_replica_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_primary_db):
            with patch('netra_backend.app.core.unified.db_connection_manager.replica_db_manager', mock_replica_db):
                
                agent_state = DeepAgentState(
                    agent_id="replica_agent",
                    session_id="replica_session",
                    thread_id="replica_thread", 
                    context={"read_replica_routing": True}
                )
                
                agent = SupervisorAgent(
                    agent_id="replica_test",
                    initial_state=agent_state
                )
                
                # Execute read operation (should route to replica)
                read_result = await agent._execute_read_operation({
                    "query": "SELECT COUNT(*) FROM logs",
                    "read_preference": "replica_preferred"
                })
                
                # Execute write operation (should route to primary)
                write_result = await agent._execute_write_operation({
                    "query": "INSERT INTO logs (message) VALUES ('test')",
                    "consistency": "strong"
                })
                
                # Verify routing
                assert read_result["database_used"] == "replica"
                assert write_result["database_used"] == "primary"
                
                # Verify correct managers were called
                mock_replica_db.get_async_session.assert_called_once()  # For read
                mock_primary_db.get_async_session.assert_called_once()  # For write
    
    @pytest.mark.asyncio
    async def test_agent_database_health_aware_routing(self):
        """Test agent routes requests based on database health status."""
        mock_primary_db = Mock()
        mock_secondary_db = Mock()
        
        # Setup health check responses
        mock_primary_health = {
            "healthy": False,
            "response_time_ms": 2000,  # Slow response
            "error_rate": 0.15  # High error rate
        }
        
        mock_secondary_health = {
            "healthy": True,
            "response_time_ms": 100,  # Fast response  
            "error_rate": 0.01  # Low error rate
        }
        
        mock_primary_db.get_health_status.return_value = mock_primary_health
        mock_secondary_db.get_health_status.return_value = mock_secondary_health
        
        # Secondary should be preferred due to better health
        mock_secondary_session = AsyncMock()
        mock_secondary_db.get_async_session.return_value.__aenter__.return_value = mock_secondary_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_primary_db):
            with patch('netra_backend.app.core.unified.db_connection_manager.secondary_db_manager', mock_secondary_db):
                
                agent_state = DeepAgentState(
                    agent_id="health_agent",
                    session_id="health_session",
                    thread_id="health_thread",
                    context={"health_aware_routing": True}
                )
                
                agent = SupervisorAgent(
                    agent_id="health_test",
                    initial_state=agent_state
                )
                
                result = await agent._execute_with_health_aware_routing({
                    "query": "SELECT * FROM users WHERE active = true",
                    "routing_strategy": "best_health"
                })
                
                assert result["status"] == "success"
                assert result["database_selected"] == "secondary"
                assert result["selection_reason"] == "better_health_metrics"
                assert result["primary_health_score"] < result["secondary_health_score"]
                
                # Verify health checks were performed
                mock_primary_db.get_health_status.assert_called_once()
                mock_secondary_db.get_health_status.assert_called_once()
                mock_secondary_db.get_async_session.assert_called_once()


@pytest.mark.integration
class TestAgentDatabaseMonitoring:
    """Test agent database operation monitoring and alerting."""
    
    @pytest.mark.asyncio
    async def test_agent_database_performance_monitoring(self):
        """Test agent monitors database operation performance."""
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        
        # Simulate various operation times
        operation_times = [0.05, 0.15, 0.35, 0.85, 1.25]  # Increasing latency
        time_iter = iter(operation_times)
        
        async def timed_execute(*args, **kwargs):
            await asyncio.sleep(next(time_iter))
            return AsyncMock(rowcount=1)
        
        mock_session.execute = AsyncMock(side_effect=timed_execute)
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="monitoring_agent",
                session_id="monitoring_session",
                thread_id="monitoring_thread",
                context={"performance_monitoring": True}
            )
            
            agent = SupervisorAgent(
                agent_id="monitoring_test", 
                initial_state=agent_state
            )
            
            # Execute multiple operations and monitor performance
            results = []
            for i in range(5):
                result = await agent._execute_monitored_query({
                    "query": f"SELECT * FROM table_{i}",
                    "performance_threshold_ms": 500  # 500ms threshold
                })
                results.append(result)
            
            # Verify performance monitoring
            assert len(results) == 5
            
            # First operations should be normal
            assert results[0]["performance_status"] == "normal"
            assert results[1]["performance_status"] == "normal"
            
            # Later operations should trigger warnings/alerts
            assert results[3]["performance_status"] == "slow"  # 850ms > 500ms
            assert results[4]["performance_status"] == "critical"  # 1250ms >> 500ms
            
            # Verify metrics collection
            assert all("execution_time_ms" in r for r in results)
            assert all("query_id" in r for r in results)
            assert results[4]["alert_triggered"] is True
    
    @pytest.mark.asyncio
    async def test_agent_database_error_tracking(self):
        """Test agent tracks and categorizes database errors."""
        mock_db_manager = Mock()
        mock_session = AsyncMock()
        
        # Simulate different types of errors
        errors = [
            Exception("Connection timeout"),
            Exception("Syntax error in query"),
            Exception("Table does not exist"),
            Exception("Permission denied"),
            Exception("Disk full")
        ]
        error_iter = iter(errors)
        
        def error_execute(*args, **kwargs):
            raise next(error_iter)
        
        mock_session.execute = AsyncMock(side_effect=error_execute)
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        
        with patch('netra_backend.app.core.unified.db_connection_manager.db_manager', mock_db_manager):
            agent_state = DeepAgentState(
                agent_id="error_tracking_agent", 
                session_id="error_session",
                thread_id="error_thread",
                context={"error_tracking": True}
            )
            
            agent = SupervisorAgent(
                agent_id="error_test",
                initial_state=agent_state
            )
            
            # Execute operations that will fail and track errors
            results = []
            for i in range(5):
                result = await agent._execute_with_error_tracking({
                    "query": f"SELECT * FROM test_{i}",
                    "error_categorization": True
                })
                results.append(result)
            
            # Verify error categorization
            error_categories = [r["error_category"] for r in results]
            assert "connection" in error_categories[0]
            assert "syntax" in error_categories[1]
            assert "schema" in error_categories[2] 
            assert "permission" in error_categories[3]
            assert "resource" in error_categories[4]
            
            # Verify error metrics
            assert all(r["status"] == "error" for r in results)
            assert all("error_timestamp" in r for r in results)
            assert all("error_severity" in r for r in results)
            
            # Check escalation for critical errors
            assert results[4]["error_severity"] == "critical"  # Disk full
            assert results[4]["escalation_triggered"] is True