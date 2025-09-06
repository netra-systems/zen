"""Integration test for timing collector in BaseAgent

Tests the execution timing collection functionality integrated
into BaseAgent and verifies that timing data is properly collected
during agent execution.

Business Value: Validates performance monitoring capabilities
BVJ: Platform | Stability | Ensures timing infrastructure works correctly
"""""

import asyncio
import time
from typing import Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.timing_decorators import time_operation, TimingCategory
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager


class TimedTestAgent(BaseAgent):
    """Test agent with timing instrumentation."""

    def __init__(self, llm_manager: Optional[LLMManager] = None):
        super().__init__(
        llm_manager=llm_manager,
        name="TimedTestAgent",
        description="Agent for testing timing collection"
        )

        @time_operation("simulate_database_query", TimingCategory.DATABASE)
        async def _simulate_database(self):
            """Simulate a database operation."""
            await asyncio.sleep(0.05)  # 50ms
            return {"records": 100}

        @time_operation("simulate_llm_call", TimingCategory.LLM)
        async def _simulate_llm(self):
            """Simulate an LLM API call."""
            await asyncio.sleep(0.1)  # 100ms
            return {"response": "Generated text"}

        @time_operation("process_data", TimingCategory.PROCESSING)
        async def _process_data(self, data):
            """Simulate data processing."""
            await asyncio.sleep(0.02)  # 20ms
            return {"processed": len(data)}

        async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool):
            """Main execution with multiple timed operations."""
        # Use context manager for manual timing
            with self.timing_collector.time_operation("execution_setup", TimingCategory.ORCHESTRATION):
                setup_data = {"initialized": True}
                await asyncio.sleep(0.01)  # 10ms

        # Nested timing operations
                db_result = await self._simulate_database()
                llm_result = await self._simulate_llm()
                processed = await self._process_data(db_result)

        # Store results in state
                state.messages.append({
                "type": "result",
                "db": db_result,
                "llm": llm_result,
                "processed": processed
                })


                @pytest.mark.asyncio
                async def test_timing_collector_integration():
                    """Test that timing collector properly tracks agent execution."""
    # Create agent
                    agent = TimedTestAgent()

    # Create state and run ID
                    state = DeepAgentState()
                    run_id = "test-run-123"

    # Execute agent
                    await agent.run(state, run_id, stream_updates=False)

    # Verify timing data was collected
                    assert agent.timing_collector is not None
                    assert len(agent.timing_collector.completed_trees) > 0

    # Get the completed execution tree
                    tree = agent.timing_collector.completed_trees[0]
                    assert tree.correlation_id == run_id
                    assert tree.agent_name == "TimedTestAgent"

    # Verify total duration is reasonable (should be > 180ms due to sleeps)
                    total_duration = tree.get_total_duration_ms()
                    assert total_duration > 180  # Sum of all sleeps
                    assert total_duration < 500  # Reasonable upper bound

    # Check that all operations were tracked
                    operations = [entry.operation for entry in tree.entries.values()]
                    assert "TimedTestAgent.execute" in operations  # Root operation
                    assert "execution_setup" in operations
                    assert "simulate_database_query" in operations
                    assert "simulate_llm_call" in operations
                    assert "process_data" in operations


                    @pytest.mark.asyncio
                    async def test_timing_categories_and_aggregation():
                        """Test timing category detection and aggregation."""
                        agent = TimedTestAgent()
                        state = DeepAgentState()

    # Execute multiple times to build aggregation data
                        for i in range(3):
                            await agent.run(state, f"run-{i}", stream_updates=False)

    # Get aggregated statistics
                            stats = agent.timing_collector.get_aggregated_stats()

    # Verify categories were properly assigned
                            assert "llm" in stats
                            assert "database" in stats
                            assert "processing" in stats
                            assert "orchestration" in stats

    # Verify LLM stats
                            llm_stats = stats["llm"]
                            assert llm_stats.count == 3  # 3 executions
                            assert llm_stats.avg_time_ms > 100  # Should be ~100ms
                            assert "simulate_llm_call" in llm_stats.operations

    # Verify database stats
                            db_stats = stats["database"]
                            assert db_stats.count == 3
                            assert db_stats.avg_time_ms > 50  # Should be ~50ms
                            assert "simulate_database_query" in db_stats.operations


                            @pytest.mark.asyncio
                            async def test_timing_bottleneck_identification():
                                """Test identification of performance bottlenecks."""
                                agent = TimedTestAgent()
                                state = DeepAgentState()

    # Execute agent
                                await agent.run(state, "bottleneck-test", stream_updates=False)

    # Get bottlenecks (operations > 40ms)
                                bottlenecks = agent.timing_collector.get_bottlenecks(threshold_ms=40)

    # Should identify database and LLM operations as bottlenecks
                                bottleneck_operations = [b.operation for b in bottlenecks]
                                assert "simulate_database_query" in bottleneck_operations
                                assert "simulate_llm_call" in bottleneck_operations
                                assert "process_data" not in bottleneck_operations  # Only 20ms


                                @pytest.mark.asyncio
                                async def test_timing_critical_path():
                                    """Test critical path identification."""
                                    agent = TimedTestAgent()
                                    state = DeepAgentState()

    # Execute agent
                                    await agent.run(state, "critical-path-test", stream_updates=False)

    # Get the execution tree
                                    tree = agent.timing_collector.completed_trees[0]

    # Get critical path
                                    critical_path = tree.get_critical_path()

    # Critical path should include the longest operations
                                    path_operations = [entry.operation for entry in critical_path]
                                    assert len(path_operations) > 0

    # The root operation should be in the critical path
                                    assert any("execute" in op for op in path_operations)


                                    @pytest.mark.asyncio
                                    async def test_timing_with_errors():
                                        """Test timing collection when operations fail."""

                                        class ErrorTestAgent(BaseAgent):
                                            """Agent that throws errors for testing."""

                                            @time_operation("failing_operation", TimingCategory.PROCESSING)
                                            async def _fail_operation(self):
                                                raise ValueError("Test error")

                                            async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool):
                                                await self._fail_operation()

                                                agent = ErrorTestAgent(name="ErrorTestAgent")
                                                state = DeepAgentState()

    # Execute should fail but timing should still be recorded
                                                with pytest.raises(ValueError, match="Test error"):
                                                    await agent.run(state, "error-test", stream_updates=False)

    # Timing should still be collected for failed operations
                                                    assert len(agent.timing_collector.completed_trees) > 0
                                                    tree = agent.timing_collector.completed_trees[0]

    # Find the failed operation
                                                    failed_entries = [e for e in tree.entries.values() 
                                                    if e.error and "Test error" in e.error]
                                                    assert len(failed_entries) > 0


                                                    @pytest.mark.asyncio
                                                    async def test_slowest_operations_tracking():
                                                        """Test tracking of slowest operations."""
                                                        agent = TimedTestAgent()
                                                        state = DeepAgentState()

    # Execute multiple times
                                                        for i in range(2):
                                                            await agent.run(state, f"slow-test-{i}", stream_updates=False)

    # Get slowest operations
                                                            slowest = agent.timing_collector.get_slowest_operations(limit=5)

    # Verify results
                                                            assert len(slowest) > 0

    # LLM calls should be among the slowest (100ms)
                                                            llm_operations = [op for op in slowest if op.operation == "simulate_llm_call"]
                                                            assert len(llm_operations) > 0

    # Verify ordering (slowest first)
                                                            for i in range(len(slowest) - 1):
                                                                assert slowest[i].duration_ms >= slowest[i + 1].duration_ms


                                                                if __name__ == "__main__":
    # Run tests with asyncio
                                                                    asyncio.run(test_timing_collector_integration())
                                                                    asyncio.run(test_timing_categories_and_aggregation())
                                                                    asyncio.run(test_timing_bottleneck_identification())
                                                                    asyncio.run(test_timing_critical_path())
                                                                    asyncio.run(test_timing_with_errors())
                                                                    asyncio.run(test_slowest_operations_tracking())
                                                                    print("All timing integration tests passed!")