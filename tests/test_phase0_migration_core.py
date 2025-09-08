"""
Core Phase 0 Migration Tests - Simplified Version

This file contains the essential Phase 0 migration tests without complex dependencies.
Tests focus on the core UserExecutionContext and BaseAgent integration.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

# Core imports for Phase 0 migration - only essential ones
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestUserExecutionContextCore:
    """Core UserExecutionContext validation tests."""
    
    def test_context_creation_with_valid_data(self):
        """Test UserExecutionContext creation with valid data."""
        context = UserExecutionContext(
            user_id="user_123",
            thread_id="thread_456",
            run_id="run_789",
            request_id="req_012",
            websocket_connection_id="conn_345"
        )
        
        assert context.user_id == "user_123"
        assert context.thread_id == "thread_456"
        assert context.run_id == "run_789"
        assert context.request_id == "req_012"
        assert context.websocket_connection_id == "conn_345"
    
    def test_context_validation_rejects_none_user_id(self):
        """Test context validation fails for None user_id."""
        from netra_backend.app.agents.supervisor.user_execution_context import InvalidContextError
        with pytest.raises(InvalidContextError, match="Required field 'user_id' must be a non-empty string"):
            UserExecutionContext(
                user_id=None,
                thread_id="thread_456",
                run_id="run_789",
                request_id="req_012"
            )
    
    def test_context_validation_rejects_placeholder_user_id(self):
        """Test context validation fails for placeholder user_id."""
        from netra_backend.app.agents.supervisor.user_execution_context import InvalidContextError
        with pytest.raises(InvalidContextError, match="contains forbidden placeholder value"):
            UserExecutionContext(
                user_id="none",  # lowercase 'none' is a dangerous value
                thread_id="thread_456",
                run_id="run_789",
                request_id="req_012"
            )
    
    def test_context_validation_rejects_placeholder_run_id(self):
        """Test context validation fails for placeholder run_id."""
        from netra_backend.app.agents.supervisor.user_execution_context import InvalidContextError
        with pytest.raises(InvalidContextError, match="contains forbidden placeholder value"):
            UserExecutionContext(
                user_id="user_123",
                thread_id="thread_456",
                run_id="registry",
                request_id="req_012"
            )
    
    def test_context_attributes_accessible(self):
        """Test UserExecutionContext attributes are accessible."""
        context = UserExecutionContext(
            user_id="user_123",
            thread_id="thread_456",
            run_id="run_789",
            request_id="req_012",
            websocket_connection_id="conn_345"
        )
        
        # The supervisor UserExecutionContext doesn't have to_dict method, but attributes are accessible
        assert context.user_id == "user_123"
        assert context.thread_id == "thread_456"
        assert context.run_id == "run_789"
        assert context.request_id == "req_012"
        assert context.websocket_connection_id == "conn_345"
    
    def test_context_string_representation_security(self):
        """Test UserExecutionContext string representation is safe."""
        long_user_id = "very_long_user_id_that_should_be_handled_safely"
        context = UserExecutionContext(
            user_id=long_user_id,
            thread_id="thread_456",
            run_id="run_789",
            request_id="req_012"
        )
        
        str_repr = str(context)
        # Context should have a string representation
        assert str_repr is not None
        assert "UserExecutionContext" in str_repr


class TestAgentExecuteMethodMigration:
    """Test BaseAgent execute method migration to context-based execution."""
    
    class MigrationTestAgent(BaseAgent):
        """Test agent implementation for migration testing."""
        
        def __init__(self):
            super().__init__(name="TestAgent")
            self.execution_calls = []
        
        async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
            """New context-based execution method."""
            self.execution_calls.append({
                'method': 'execute_with_context',
                'context': context,
                'stream_updates': stream_updates,
                'timestamp': datetime.now(timezone.utc)
            })
            return {"status": "success", "method": "context_based", "user_id": context.user_id}
    
    class LegacyAgent(BaseAgent):
        """Legacy agent that hasn't been migrated (should fail tests)."""
        
        def __init__(self):
            super().__init__(name="LegacyAgent")
        
        # Intentionally no execute_with_context implementation
    
    @pytest.mark.asyncio
    async def test_agent_execute_with_context_success(self):
        """Test agent execute method with valid UserExecutionContext."""
        agent = self.MigrationTestAgent()
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        result = await agent.execute(context, stream_updates=True)
        
        assert result is not None
        assert result["status"] == "success"
        assert result["method"] == "context_based"
        assert result["user_id"] == "test_user"
        assert len(agent.execution_calls) == 1
        assert agent.execution_calls[0]["method"] == "execute_with_context"
    
    @pytest.mark.asyncio
    async def test_agent_execute_rejects_wrong_context_type(self):
        """Test agent execute method rejects non-UserExecutionContext."""
        agent = self.MigrationTestAgent()
        
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            await agent.execute({"invalid": "context"})
    
    @pytest.mark.asyncio
    async def test_legacy_agent_execute_works_with_fallback(self):
        """Test legacy agent uses fallback execute_core_logic implementation."""
        agent = self.LegacyAgent()
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # BaseAgent provides a default execute_core_logic fallback
        result = await agent.execute(context)
        
        assert result is not None
        assert result["status"] == "completed"
        assert "LegacyAgent executed successfully" in result["message"]


class TestConcurrentUserHandling:
    """Test system behavior with concurrent users."""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_execution_isolation(self):
        """Test that concurrent users are properly isolated."""
        
        class IsolationTestAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="IsolationTestAgent")
                self.user_data = {}  # This should be isolated per execution
            
            async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
                # Store user-specific data (should not leak between users)
                user_secret = f"secret_for_{context.user_id}"
                self.user_data[context.run_id] = user_secret
                
                # Simulate processing time
                await asyncio.sleep(0.01)
                
                # Verify our data is still there and not contaminated
                if context.run_id not in self.user_data:
                    raise Exception(f"Data for {context.run_id} was lost")
                
                if self.user_data[context.run_id] != user_secret:
                    raise Exception(f"Data contamination detected for {context.user_id}")
                
                return {
                    "user_id": context.user_id,
                    "secret": user_secret,
                    "data_integrity": "verified"
                }
        
        # Create multiple users with concurrent execution
        async def execute_for_user(user_id: str) -> Dict[str, Any]:
            agent = IsolationTestAgent()  # Each user gets fresh agent instance
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{user_id}",
                run_id=f"run_{user_id}_{uuid.uuid4()}",
                request_id=f"req_{user_id}_{uuid.uuid4()}"
            )
            
            return await agent.execute(context)
        
        # Execute concurrently for 10 users
        user_count = 10
        tasks = [
            execute_for_user(f"user_{i}")
            for i in range(user_count)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all executions succeeded with proper isolation
        assert len(results) == user_count
        
        user_ids_seen = set()
        for result in results:
            assert result["data_integrity"] == "verified"
            assert result["user_id"] not in user_ids_seen, "User ID collision detected"
            user_ids_seen.add(result["user_id"])
            assert result["secret"].startswith(f"secret_for_{result['user_id']}")


class TestPerformanceValidation:
    """Performance tests to ensure no degradation from Phase 0 migration."""
    
    @pytest.mark.asyncio
    async def test_context_creation_performance(self):
        """Test UserExecutionContext creation performance."""
        
        start_time = time.time()
        
        # Create many contexts rapidly
        contexts = []
        for i in range(1000):
            context = UserExecutionContext(
                user_id=f"perf_user_{i}",
                thread_id=f"perf_thread_{i}",
                run_id=f"perf_run_{i}",
                request_id=f"perf_req_{i}"
            )
            contexts.append(context)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_context = (total_time / 1000) * 1000  # milliseconds
        
        # Performance assertion: should create contexts quickly
        assert avg_time_per_context < 0.5, f"Context creation too slow: {avg_time_per_context:.3f}ms per context"
        assert len(contexts) == 1000
        
        # Verify all contexts are valid
        for context in contexts[:10]:  # Check first 10
            assert context.user_id is not None
            assert context.thread_id is not None
            assert context.run_id is not None
            assert context.request_id is not None
    
    @pytest.mark.asyncio
    async def test_agent_execution_performance(self):
        """Test agent execution performance with new context-based approach."""
        
        class PerformanceTestAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="PerformanceTestAgent")
            
            async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
                # Minimal processing to measure overhead
                return {
                    "user_id": context.user_id,
                    "execution_time": time.time()
                }
        
        agent = PerformanceTestAgent()
        execution_times = []
        
        # Measure execution time for multiple calls
        for i in range(100):
            context = UserExecutionContext(
                user_id=f"perf_user_{i}",
                thread_id=f"perf_thread_{i}",
                run_id=f"perf_run_{i}",
                request_id=f"perf_req_{i}"
            )
            
            start_time = time.time()
            result = await agent.execute(context)
            end_time = time.time()
            
            execution_times.append(end_time - start_time)
            assert result["user_id"] == f"perf_user_{i}"
        
        # Performance analysis
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        
        # Performance assertions
        assert avg_execution_time < 0.01, f"Average execution too slow: {avg_execution_time:.4f}s"
        assert max_execution_time < 0.05, f"Maximum execution too slow: {max_execution_time:.4f}s"


# Test execution configuration
if __name__ == "__main__":
    # Configure test execution
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-x",  # Stop on first failure to identify issues quickly
    ])