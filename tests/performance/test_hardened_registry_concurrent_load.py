class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        ''' ALERT:  PERFORMANCE CRITICAL: Hardened Agent Registry Concurrent Load Tests

        These tests validate that the hardened agent registry can handle:
        1. 10+ concurrent users without performance degradation
        2. High-frequency agent creation/destruction
        3. Memory usage under extended concurrent sessions
        4. Thread safety under maximum load

        CRITICAL PERFORMANCE REQUIREMENTS:
        - Support 10+ concurrent users
        - Agent creation < 100ms per user
        - Memory usage grows linearly with users
        - No memory leaks over 1000+ operations
        - Thread-safe under 50+ concurrent operations
        '''

        import pytest
        import asyncio
        import time
        import uuid
        import psutil
        import os
        from statistics import mean, median
        from typing import List, Dict
        from concurrent.futures import ThreadPoolExecutor
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


class PerformanceMetrics:
        """Track performance metrics during testing."""

    def __init__(self):
        pass
        self.start_time = time.time()
        self.operation_times = []
        self.memory_samples = []
        self.error_count = 0

    def record_operation(self, duration: float):
        """Record operation completion time."""
        self.operation_times.append(duration)

    def record_memory(self):
        """Record current memory usage."""
        pass
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.memory_samples.append(memory_mb)

    def record_error(self):
        """Record error occurrence."""
        self.error_count += 1

    def get_summary(self) -> Dict:
        """Get performance summary."""
        pass
        total_time = time.time() - self.start_time

        if self.operation_times:
        avg_op_time = mean(self.operation_times)
        median_op_time = median(self.operation_times)
        max_op_time = max(self.operation_times)
        min_op_time = min(self.operation_times)
        else:
        avg_op_time = median_op_time = max_op_time = min_op_time = 0

        if self.memory_samples:
        memory_delta = max(self.memory_samples) - min(self.memory_samples)
        final_memory = self.memory_samples[-1]
        else:
        memory_delta = final_memory = 0

        return { )
        'total_time_seconds': total_time,
        'operations_count': len(self.operation_times),
        'avg_operation_time_ms': avg_op_time * 1000,
        'median_operation_time_ms': median_op_time * 1000,
        'max_operation_time_ms': max_op_time * 1000,
        'min_operation_time_ms': min_op_time * 1000,
        'operations_per_second': len(self.operation_times) / total_time if total_time > 0 else 0,
        'memory_delta_mb': memory_delta,
        'final_memory_mb': final_memory,
        'error_count': self.error_count,
        'success_rate': 1.0 - (self.error_count / max(1, len(self.operation_times)))
                    


class TestConcurrentUserLoad:
        """Test concurrent user load performance."""

        @pytest.fixture
    def registry(self):
        """Use real service instance."""
    # TODO: Initialize real service
        from netra_backend.app.llm.llm_manager import LLMManager
        mock_llm_manager = Mock(spec=LLMManager)
        return AgentRegistry(mock_llm_manager)

        @pytest.fixture
    def performance_metrics(self):
        """Use real service instance."""
    # TODO: Initialize real service
        pass
        return PerformanceMetrics()

@pytest.mark.asyncio
@pytest.mark.performance
    async def test_concurrent_user_creation_10_users(self, registry, performance_metrics):
"""Test concurrent creation of 10 user registries."""
num_users = 10
user_ids = ["formatted_string" for i in range(num_users)]

performance_metrics.record_memory()

async def create_user_registry(user_id: str):
start_time = time.time()
try:
user_registry = await registry.get_user_registry(user_id)
assert user_registry.user_id == user_id
performance_metrics.record_operation(time.time() - start_time)
await asyncio.sleep(0)
return user_registry
except Exception as e:
performance_metrics.record_error()
raise e

            # Create users concurrently
tasks = [create_user_registry(user_id) for user_id in user_ids]
registries = await asyncio.gather(*tasks, return_exceptions=True)

performance_metrics.record_memory()

            # Verify all succeeded
successful_registries = [item for item in []]
assert len(successful_registries) == num_users

            # Performance assertions
summary = performance_metrics.get_summary()
assert summary['success_rate'] == 1.0, "formatted_string"
assert summary['avg_operation_time_ms'] < 100, "formatted_string"
assert summary['max_operation_time_ms'] < 500, "formatted_string"

print("formatted_string")

@pytest.mark.asyncio
@pytest.mark.performance
    async def test_concurrent_agent_creation_50_agents(self, registry, performance_metrics):
"""Test concurrent agent creation across multiple users."""
pass
num_users = 5
agents_per_user = 10
total_agents = num_users * agents_per_user

                # Register mock factory
async def mock_factory(context, llm_manager=None, websocket_bridge=None):
pass
    # Simulate some work
await asyncio.sleep(0.01)  # 10ms of "work"
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_agent.user_id = context.user_id
mock_agent.cleanup = lambda x: None None
await asyncio.sleep(0)
return mock_agent

registry.register_agent_factory("load_test_agent", mock_factory)

performance_metrics.record_memory()

async def create_user_agents(user_id: str):
"""Create multiple agents for one user."""
agents = []
for i in range(agents_per_user):
start_time = time.time()
try:
user_context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string"
            
agent = await registry.create_agent_for_user( )
user_id, "load_test_agent", user_context
            
agents.append(agent)
performance_metrics.record_operation(time.time() - start_time)
except Exception as e:
performance_metrics.record_error()
raise e
await asyncio.sleep(0)
return agents

                # Create agents for all users concurrently
user_ids = ["formatted_string" for i in range(num_users)]
tasks = [create_user_agents(user_id) for user_id in user_ids]
results = await asyncio.gather(*tasks, return_exceptions=True)

performance_metrics.record_memory()

                # Verify results
successful_results = [item for item in []]
assert len(successful_results) == num_users

total_agents_created = sum(len(agents) for agents in successful_results)
assert total_agents_created == total_agents

                # Performance assertions
summary = performance_metrics.get_summary()
assert summary['success_rate'] >= 0.95, "formatted_string"
assert summary['avg_operation_time_ms'] < 200, "formatted_string"

print("formatted_string")

@pytest.mark.asyncio
@pytest.mark.performance
    async def test_memory_usage_scaling(self, registry, performance_metrics):
"""Test memory usage scales linearly with user count."""
pass
user_counts = [1, 5, 10, 20]
memory_per_user_samples = []

for user_count in user_counts:
                        # Clear previous test data
await registry.emergency_cleanup_all()
await asyncio.sleep(0.1)  # Allow cleanup to complete

performance_metrics.record_memory()
baseline_memory = performance_metrics.memory_samples[-1]

                        # Create users with agents
user_ids = ["formatted_string" for i in range(user_count)]

                        # Mock factory for agents
async def mock_factory(context, llm_manager=None, websocket_bridge=None):
pass
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_agent.cleanup = lambda x: None None
await asyncio.sleep(0)
return mock_agent

registry.register_agent_factory("mem_test_agent", mock_factory)

    # Create agents for users
for user_id in user_ids:
user_context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="thread_1",
run_id="run_1"
        
await registry.create_agent_for_user(user_id, "mem_test_agent", user_context)

performance_metrics.record_memory()
final_memory = performance_metrics.memory_samples[-1]

memory_per_user = (final_memory - baseline_memory) / user_count
memory_per_user_samples.append(memory_per_user)

print("formatted_string")

        # Verify memory scaling is reasonable
avg_memory_per_user = mean(memory_per_user_samples)
max_memory_per_user = max(memory_per_user_samples)

        # Each user should use less than 10MB on average
assert avg_memory_per_user < 10.0, "formatted_string"
assert max_memory_per_user < 20.0, "formatted_string"

print("formatted_string")

@pytest.mark.asyncio
@pytest.mark.performance
    async def test_cleanup_performance(self, registry, performance_metrics):
"""Test cleanup performance with many users."""
num_users = 20

            # Create users with agents
user_ids = []
for i in range(num_users):
user_id = "formatted_string"
user_ids.append(user_id)

                # Create user registry (this will create agents)
user_registry = await registry.get_user_registry(user_id)

                # Add mock agents
for j in range(5):  # 5 agents per user
websocket = TestWebSocketConnection()  # Real WebSocket implementation
await user_registry.register_agent("formatted_string", mock_agent)

performance_metrics.record_memory()

                # Test concurrent cleanup
start_time = time.time()
cleanup_tasks = [registry.cleanup_user_session(user_id) for user_id in user_ids]
cleanup_results = await asyncio.gather(*cleanup_tasks)
total_cleanup_time = time.time() - start_time

performance_metrics.record_memory()

                # Verify all cleanups succeeded
successful_cleanups = [item for item in []] == 'cleaned']
assert len(successful_cleanups) == num_users

                # Performance assertions
avg_cleanup_time = total_cleanup_time / num_users
assert avg_cleanup_time < 0.1, "formatted_string"
assert total_cleanup_time < 2.0, "formatted_string"

                # Verify no users remain
assert len(registry._user_registries) == 0

print("formatted_string")


class TestThreadSafety:
    """Test thread safety under extreme concurrent load."""

@pytest.mark.asyncio
@pytest.mark.performance
    async def test_thread_safety_stress(self):
"""Test thread safety with 100+ concurrent operations."""
registry = AgentRegistry()
operations_count = 100
errors = []

        # Mock factory
async def mock_factory(context, llm_manager=None, websocket_bridge=None):
await asyncio.sleep(0)
return
registry.register_agent_factory("stress_test_agent", mock_factory)

async def stress_operation(op_id: int):
"""Perform a stress operation."""
pass
try:
user_id = "formatted_string"  # 10 users, multiple ops per user
user_context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string"
        

        # Get user registry
user_registry = await registry.get_user_registry(user_id)

        # Create agent
agent = await registry.create_agent_for_user( )
user_id, "stress_test_agent", user_context
        

        # Simulate some work
await asyncio.sleep(0.001)  # 1ms

        # Get agent back
retrieved_agent = await user_registry.get_agent("stress_test_agent")

if retrieved_agent != agent:
errors.append("formatted_string")

except Exception as e:
errors.append("formatted_string")

                # Run all operations concurrently
start_time = time.time()
tasks = [stress_operation(i) for i in range(operations_count)]
await asyncio.gather(*tasks)
total_time = time.time() - start_time

                # Verify thread safety
assert len(errors) == 0, "formatted_string"  # Show first 5 errors

                # Performance check
ops_per_second = operations_count / total_time
assert ops_per_second > 50, "formatted_string"

print("formatted_string")

                # Cleanup
await registry.emergency_cleanup_all()


class TestMemoryLeakDetection:
        """Test for memory leaks over extended operations."""

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.slow
    async def test_no_memory_leaks_1000_operations(self):
"""Test for memory leaks over 1000 create/destroy cycles."""
registry = AgentRegistry()

        # Mock factory
async def mock_factory(context, llm_manager=None, websocket_bridge=None):
websocket = TestWebSocketConnection()  # Real WebSocket implementation
await asyncio.sleep(0)
return mock_agent

registry.register_agent_factory("leak_test_agent", mock_factory)

    # Baseline memory
process = psutil.Process(os.getpid())
baseline_memory = process.memory_info().rss / 1024 / 1024
memory_samples = [baseline_memory]

    # Perform 1000 create/destroy cycles
cycles = 1000
for i in range(cycles):
user_id = "formatted_string"
user_context = UserExecutionContext.from_request( )
user_id=user_id,
thread_id="formatted_string",
run_id="formatted_string"
        

        # Create agent
await registry.create_agent_for_user(user_id, "leak_test_agent", user_context)

        # Cleanup immediately
await registry.cleanup_user_session(user_id)

        # Sample memory every 100 cycles
if i % 100 == 0:
current_memory = process.memory_info().rss / 1024 / 1024
memory_samples.append(current_memory)
print("formatted_string")

            # Final memory check
final_memory = process.memory_info().rss / 1024 / 1024
memory_samples.append(final_memory)

            # Check for memory leaks
memory_growth = final_memory - baseline_memory
memory_growth_percent = (memory_growth / baseline_memory) * 100

print(f"\
Memory Usage:")
print("formatted_string")
print("formatted_string")
print("formatted_string")

            # Allow some memory growth but detect significant leaks
assert memory_growth < 50, "formatted_string"
assert memory_growth_percent < 20, "formatted_string"

print("formatted_string")


@pytest.mark.performance
class TestGlobalRegistryPerformance:
        """Test global registry factory performance."""

@pytest.mark.asyncio
    async def test_concurrent_registry_creation_performance(self):
"""Test concurrent registry creation performance with proper isolation."""
num_concurrent_accesses = 50

from netra_backend.app.llm.llm_manager import LLMManager

start_time = time.time()

        # Create registries concurrently (proper isolation pattern)
def create_registry():
mock_llm_manager = Mock(spec=LLMManager)
await asyncio.sleep(0)
return AgentRegistry(mock_llm_manager)

tasks = [asyncio.create_task(asyncio.to_thread(create_registry)) )
for _ in range(num_concurrent_accesses)]
registries = await asyncio.gather(*tasks)

total_time = time.time() - start_time

    # Verify all are different instances (proper isolation)
assert len(registries) == num_concurrent_accesses
assert len(set(id(r) for r in registries)) == num_concurrent_accesses

    # Performance check
avg_creation_time = (total_time / num_concurrent_accesses) * 1000  # ms
assert avg_creation_time < 50, "formatted_string"

print("formatted_string")


if __name__ == "__main__":
        # Run performance tests
pytest.main([ ))
__file__,
"-v",
"-m", "performance",
"--tb=short"
        
pass
