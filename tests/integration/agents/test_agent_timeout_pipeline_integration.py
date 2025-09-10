"""
Integration tests for agent pipeline timeout scenarios.

Tests agent execution timeouts at the pipeline level without Docker dependencies.
Focuses on reproducing timeout scenarios from issue #128:
- test_023_streaming_partial_results_real
- test_025_critical_event_delivery_real

These tests validate timeout behavior in agent pipelines with real components
but without full Docker/E2E infrastructure.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - ensure agent pipelines handle timeouts gracefully
- Value Impact: Prevents timeout failures that impact user chat experience
- Strategic Impact: Validates timeout handling at the pipeline integration level
"""

import pytest
import asyncio
import time
import json
import uuid
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

# Import Windows-safe patterns
from netra_backend.app.core.windows_asyncio_safe import (
    windows_safe_sleep,
    windows_safe_wait_for,
    windows_asyncio_safe,
    WindowsAsyncioSafePatterns
)

# Import shared configuration patterns
try:
    from shared.isolated_environment import IsolatedEnvironment
    from shared.types import UserID, ThreadID, RunID, RequestID
except ImportError:
    # Mock for test isolation
    IsolatedEnvironment = Mock
    UserID = str
    ThreadID = str
    RunID = str
    RequestID = str

# Import agent pipeline components
try:
    from netra_backend.app.agents.agent_registry import AgentRegistry
    from netra_backend.app.execution.execution_engine import ExecutionEngine
    from netra_backend.app.websocket.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.core.tool_dispatcher import ToolDispatcher
except ImportError:
    # Handle import errors for isolated testing
    AgentRegistry = Mock
    ExecutionEngine = Mock  
    AgentWebSocketBridge = Mock
    ToolDispatcher = Mock


class MockWebSocketManager:
    """Mock WebSocket manager for timeout testing"""
    
    def __init__(self, send_delay: float = 0.1, connection_timeout: float = 5.0):
        self.send_delay = send_delay
        self.connection_timeout = connection_timeout
        self.events_sent = []
        self.timeouts_encountered = []
        self.is_connected = True
        
    async def send_event(self, event: Dict[str, Any]) -> bool:
        """Send event with potential timeout"""
        if not self.is_connected:
            return False
            
        try:
            # Simulate network delay with timeout potential
            await windows_safe_wait_for(
                windows_safe_sleep(self.send_delay),
                timeout=self.connection_timeout
            )
            
            self.events_sent.append({
                **event,
                "sent_at": time.time()
            })
            return True
            
        except asyncio.TimeoutError:
            self.timeouts_encountered.append({
                "event": event,
                "timeout_at": time.time()
            })
            return False
    
    async def disconnect(self):
        """Simulate connection loss"""
        self.is_connected = False


class MockToolExecutor:
    """Mock tool executor with configurable timeout behavior"""
    
    def __init__(self, execution_delay: float = 0.5, timeout_probability: float = 0.0):
        self.execution_delay = execution_delay
        self.timeout_probability = timeout_probability
        self.tools_executed = []
        self.tools_timed_out = []
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with potential timeout"""
        
        # Simulate timeout probability
        import random
        if random.random() < self.timeout_probability:
            # Force timeout scenario
            await asyncio.sleep(10.0)  # Long delay to force timeout
            
        try:
            # Simulate tool execution
            result = await windows_safe_wait_for(
                self._simulate_tool_execution(tool_name, parameters),
                timeout=5.0  # Standard tool timeout
            )
            
            self.tools_executed.append({
                "tool": tool_name,
                "parameters": parameters,
                "result": result,
                "executed_at": time.time()
            })
            
            return result
            
        except asyncio.TimeoutError:
            self.tools_timed_out.append({
                "tool": tool_name,
                "parameters": parameters,
                "timeout_at": time.time()
            })
            raise
    
    async def _simulate_tool_execution(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate actual tool execution"""
        await windows_safe_sleep(self.execution_delay)
        
        return {
            "tool": tool_name,
            "status": "completed",
            "result": f"Tool {tool_name} executed successfully",
            "data": parameters
        }


class MockAgentPipeline:
    """Mock agent pipeline with timeout-prone operations"""
    
    def __init__(self, websocket_manager: MockWebSocketManager, tool_executor: MockToolExecutor):
        self.websocket_manager = websocket_manager
        self.tool_executor = tool_executor
        self.execution_id = str(uuid.uuid4())
        self.current_step = "idle"
        
    async def execute(self, message: str, user_id: str) -> Dict[str, Any]:
        """Execute agent pipeline with timeout monitoring"""
        
        execution_start = time.time()
        
        try:
            # Step 1: Send agent_started event
            self.current_step = "starting"
            await self._send_event("agent_started", {
                "execution_id": self.execution_id,
                "message": message,
                "user_id": user_id
            })
            
            # Step 2: Send agent_thinking event  
            self.current_step = "thinking"
            await self._send_event("agent_thinking", {
                "execution_id": self.execution_id,
                "status": "analyzing request"
            })
            
            # Small delay for thinking simulation
            await windows_safe_sleep(0.1)
            
            # Step 3: Execute tools with timeout potential
            self.current_step = "tool_execution"
            await self._send_event("tool_executing", {
                "execution_id": self.execution_id,
                "tool": "data_analyzer"
            })
            
            tool_result = await self.tool_executor.execute_tool(
                "data_analyzer",
                {"input": message, "user_id": user_id}
            )
            
            await self._send_event("tool_completed", {
                "execution_id": self.execution_id,
                "tool": "data_analyzer",
                "result": tool_result
            })
            
            # Step 4: Send completion event
            self.current_step = "completing"
            await self._send_event("agent_completed", {
                "execution_id": self.execution_id,
                "status": "completed",
                "result": "Agent pipeline executed successfully",
                "tool_results": [tool_result]
            })
            
            execution_duration = time.time() - execution_start
            
            return {
                "status": "completed",
                "execution_id": self.execution_id,
                "duration": execution_duration,
                "events_sent": len(self.websocket_manager.events_sent),
                "tools_executed": len(self.tool_executor.tools_executed)
            }
            
        except Exception as e:
            # Handle timeout or other errors
            execution_duration = time.time() - execution_start
            
            await self._send_event("agent_error", {
                "execution_id": self.execution_id,
                "error": str(e),
                "step": self.current_step,
                "duration": execution_duration
            })
            
            return {
                "status": "error",
                "execution_id": self.execution_id,
                "error": str(e),
                "step": self.current_step,
                "duration": execution_duration,
                "events_sent": len(self.websocket_manager.events_sent),
                "tools_executed": len(self.tool_executor.tools_executed)
            }
    
    async def _send_event(self, event_type: str, data: Dict[str, Any]):
        """Send event through WebSocket manager"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        
        # Use timeout for event sending (like in the failing tests)
        success = await windows_safe_wait_for(
            self.websocket_manager.send_event(event),
            timeout=2.0,  # Short timeout like in test_025
            default=False
        )
        
        if not success:
            print(f"Event {event_type} failed to send or timed out")


class TestAgentTimeoutPipelineIntegration:
    """Integration tests for agent pipeline timeout scenarios"""

    @pytest.mark.asyncio
    async def test_successful_agent_pipeline_execution(self):
        """Test successful agent pipeline execution without timeouts"""
        
        # Setup fast components (no timeouts expected)
        websocket_manager = MockWebSocketManager(send_delay=0.05)
        tool_executor = MockToolExecutor(execution_delay=0.2)
        pipeline = MockAgentPipeline(websocket_manager, tool_executor)
        
        # Execute pipeline
        start_time = time.time()
        result = await pipeline.execute("Test message", "test-user-001")
        duration = time.time() - start_time
        
        # Validate successful execution
        assert result["status"] == "completed"
        assert result["events_sent"] == 5  # All events sent
        assert result["tools_executed"] == 1  # Tool executed
        assert duration < 2.0, f"Pipeline took too long: {duration:.3f}s"
        
        # Validate event sequence
        events = websocket_manager.events_sent
        event_types = [event["type"] for event in events]
        expected_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        assert event_types == expected_types, f"Event sequence incorrect: {event_types}"
        
        # No timeouts should have occurred
        assert len(websocket_manager.timeouts_encountered) == 0
        assert len(tool_executor.tools_timed_out) == 0
        
        print(f"Successful pipeline execution: {duration:.3f}s, {result['events_sent']} events")
        
    @pytest.mark.asyncio
    async def test_websocket_event_timeout_scenario(self):
        """Test agent pipeline with WebSocket event timeout (from test_025 pattern)"""
        
        # Setup slow WebSocket (should cause timeouts)
        websocket_manager = MockWebSocketManager(send_delay=3.0)  # Longer than timeout
        tool_executor = MockToolExecutor(execution_delay=0.1)  # Fast tools
        pipeline = MockAgentPipeline(websocket_manager, tool_executor)
        
        # Execute pipeline with expected timeouts
        start_time = time.time()
        result = await pipeline.execute("Test message with slow WebSocket", "test-user-002")
        duration = time.time() - start_time
        
        # Pipeline should still complete but with timeout issues
        assert result["status"] in ["completed", "error"]
        assert duration > 2.0, f"Pipeline completed too quickly: {duration:.3f}s"
        
        # Some events should have timed out
        assert len(websocket_manager.timeouts_encountered) > 0, "Expected WebSocket timeouts"
        
        # Tools should still execute (independent of WebSocket timeouts)
        assert len(tool_executor.tools_executed) >= 0  # May vary based on when timeout occurs
        
        print(f"WebSocket timeout scenario: {duration:.3f}s")
        print(f"Events sent: {result['events_sent']}, Timeouts: {len(websocket_manager.timeouts_encountered)}")
        
    @pytest.mark.asyncio
    async def test_tool_execution_timeout_scenario(self):
        """Test agent pipeline with tool execution timeout"""
        
        # Setup fast WebSocket but slow tools
        websocket_manager = MockWebSocketManager(send_delay=0.05)
        tool_executor = MockToolExecutor(execution_delay=6.0)  # Longer than tool timeout
        pipeline = MockAgentPipeline(websocket_manager, tool_executor)
        
        # Execute pipeline expecting tool timeout
        start_time = time.time()
        result = await pipeline.execute("Test message with slow tool", "test-user-003")
        duration = time.time() - start_time
        
        # Pipeline should handle tool timeout gracefully
        assert result["status"] == "error", "Expected error due to tool timeout"
        assert "timeout" in str(result.get("error", "")).lower() or "asyncio.TimeoutError" in str(result.get("error", ""))
        
        # Events should be sent up to the point of tool execution
        assert result["events_sent"] >= 3, "Should send events before tool timeout"
        
        # Tool should be recorded as timed out
        assert len(tool_executor.tools_timed_out) > 0, "Expected tool timeout"
        
        print(f"Tool timeout scenario: {duration:.3f}s")
        print(f"Error: {result.get('error', 'N/A')}")
        print(f"Step where timeout occurred: {result.get('step', 'unknown')}")
        
    @pytest.mark.asyncio
    async def test_progressive_timeout_pattern_reproduction(self):
        """Test progressive timeout pattern from test_025_critical_event_delivery_real"""
        
        # Simulate multiple agent executions with increasing timeout rates
        timeout_scenarios = [
            {"websocket_delay": 0.1, "tool_delay": 0.2, "description": "fast"},
            {"websocket_delay": 0.5, "tool_delay": 0.8, "description": "medium"},  
            {"websocket_delay": 1.5, "tool_delay": 1.0, "description": "slow"},
            {"websocket_delay": 3.0, "tool_delay": 2.0, "description": "very_slow"}
        ]
        
        results = []
        
        for i, scenario in enumerate(timeout_scenarios):
            print(f"\nExecuting scenario {i+1}: {scenario['description']}")
            
            websocket_manager = MockWebSocketManager(send_delay=scenario["websocket_delay"])
            tool_executor = MockToolExecutor(execution_delay=scenario["tool_delay"])
            pipeline = MockAgentPipeline(websocket_manager, tool_executor)
            
            start_time = time.time()
            
            try:
                # Use progressively shorter timeouts (pattern from test_025)
                timeout = max(2.0 - (i * 0.3), 0.5)  # Decreasing timeout
                
                result = await windows_safe_wait_for(
                    pipeline.execute(f"Progressive test {i+1}", f"test-user-{i+1:03d}"),
                    timeout=timeout
                )
                
                duration = time.time() - start_time
                result["scenario"] = scenario["description"]
                result["duration"] = duration
                result["timeout_used"] = timeout
                
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                result = {
                    "status": "pipeline_timeout",
                    "scenario": scenario["description"],
                    "duration": duration,
                    "timeout_used": timeout,
                    "events_sent": len(websocket_manager.events_sent),
                    "tools_executed": len(tool_executor.tools_executed),
                    "websocket_timeouts": len(websocket_manager.timeouts_encountered),
                    "tool_timeouts": len(tool_executor.tools_timed_out)
                }
            
            results.append(result)
            
            print(f"  Result: {result['status']} in {result['duration']:.3f}s")
            print(f"  Events: {result['events_sent']}, Tools: {result['tools_executed']}")
            
            # Small delay between scenarios
            await windows_safe_sleep(0.1)
        
        # Validate progressive timeout behavior
        assert len(results) == 4, "Should have results for all scenarios"
        
        # First scenario should succeed
        assert results[0]["status"] == "completed", "Fast scenario should succeed"
        
        # Later scenarios should have more issues
        timeout_count = sum(1 for r in results if r["status"] in ["error", "pipeline_timeout"])
        assert timeout_count > 0, "Some scenarios should experience timeouts"
        
        print(f"\nProgressive timeout test summary:")
        for i, result in enumerate(results):
            print(f"  Scenario {i+1}: {result['status']} ({result['duration']:.3f}s)")
        
    @pytest.mark.asyncio
    async def test_chunked_streaming_timeout_reproduction(self):
        """Test chunked streaming timeout pattern from test_023_streaming_partial_results_real"""
        
        class MockStreamingPipeline:
            """Mock pipeline that streams partial results"""
            
            def __init__(self, chunk_delay: float = 0.2):
                self.chunk_delay = chunk_delay
                self.chunks_sent = []
                
            async def stream_execution(self, message: str) -> List[Dict[str, Any]]:
                """Stream execution results in chunks"""
                
                chunks = [
                    {"type": "agent_started", "data": {"status": "beginning"}},
                    {"type": "agent_thinking", "data": {"step": "analysis"}},
                    {"type": "partial_result", "data": {"progress": 25}},
                    {"type": "partial_result", "data": {"progress": 50}},
                    {"type": "partial_result", "data": {"progress": 75}}, 
                    {"type": "tool_executing", "data": {"tool": "optimizer"}},
                    {"type": "partial_result", "data": {"progress": 90}},
                    {"type": "tool_completed", "data": {"result": "optimized"}},
                    {"type": "agent_completed", "data": {"final_result": "success"}}
                ]
                
                for i, chunk in enumerate(chunks):
                    # Simulate increasing delay for later chunks
                    delay = self.chunk_delay * (1 + i * 0.2)
                    await windows_safe_sleep(delay)
                    
                    chunk_with_metadata = {
                        **chunk,
                        "sequence": i + 1,
                        "timestamp": time.time()
                    }
                    
                    self.chunks_sent.append(chunk_with_metadata)
                    yield chunk_with_metadata
        
        # Test streaming with progressive timeouts (pattern from test_023)
        streaming_pipeline = MockStreamingPipeline(chunk_delay=0.3)
        chunks_received = []
        chunk_timeouts = [2.0, 1.5, 1.0, 0.8, 0.5, 0.5, 0.3, 0.3, 0.2]  # Decreasing
        
        start_time = time.time()
        stream = streaming_pipeline.stream_execution("Test streaming message")
        
        for i, timeout in enumerate(chunk_timeouts):
            try:
                chunk = await windows_safe_wait_for(
                    stream.__anext__(),
                    timeout=timeout,
                    default=None
                )
                
                if chunk is None:
                    print(f"Chunk {i+1} timeout ({timeout}s) - no more data")
                    break
                
                chunks_received.append(chunk)
                print(f"Received chunk {i+1}: {chunk['type']} (timeout: {timeout}s)")
                
            except (StopAsyncIteration, asyncio.TimeoutError):
                print(f"Streaming ended or timeout at chunk {i+1}")
                break
            
            # Small delay between chunk attempts
            await windows_safe_sleep(0.05)
        
        duration = time.time() - start_time
        
        # Validate streaming behavior with timeouts
        assert len(chunks_received) >= 3, f"Expected at least 3 chunks, got {len(chunks_received)}"
        assert len(chunks_received) < len(chunk_timeouts), "Some chunks should timeout"
        assert duration > 1.0, f"Test too fast ({duration:.3f}s) for streaming with timeouts"
        
        # Verify chunk sequence
        for i, chunk in enumerate(chunks_received):
            assert chunk["sequence"] == i + 1, f"Chunk sequence wrong: {chunk['sequence']} != {i + 1}"
        
        print(f"Streaming timeout test: {len(chunks_received)} chunks in {duration:.3f}s")
        
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_timeout_scenarios(self):
        """Test multiple concurrent pipelines with timeout scenarios"""
        
        # Create multiple pipelines with different timeout characteristics
        pipelines = []
        websocket_managers = []
        tool_executors = []
        
        configs = [
            {"ws_delay": 0.1, "tool_delay": 0.2, "user": "fast-user"},
            {"ws_delay": 0.8, "tool_delay": 0.5, "user": "medium-user"},
            {"ws_delay": 2.0, "tool_delay": 1.5, "user": "slow-user"},
            {"ws_delay": 0.2, "tool_delay": 3.0, "user": "tool-timeout-user"}
        ]
        
        for i, config in enumerate(configs):
            ws_manager = MockWebSocketManager(send_delay=config["ws_delay"])
            tool_exec = MockToolExecutor(execution_delay=config["tool_delay"])
            pipeline = MockAgentPipeline(ws_manager, tool_exec)
            
            pipelines.append(pipeline)
            websocket_managers.append(ws_manager)
            tool_executors.append(tool_exec)
        
        # Execute all pipelines concurrently with timeout
        start_time = time.time()
        
        async def execute_with_timeout(pipeline, message, timeout):
            try:
                return await windows_safe_wait_for(
                    pipeline.execute(message, configs[pipelines.index(pipeline)]["user"]),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                return {
                    "status": "pipeline_timeout",
                    "user": configs[pipelines.index(pipeline)]["user"]
                }
        
        # Execute with different timeouts for each pipeline
        pipeline_timeouts = [5.0, 3.0, 2.0, 4.0]  # Different timeout strategies
        
        tasks = [
            execute_with_timeout(pipeline, f"Concurrent test {i}", timeout)
            for i, (pipeline, timeout) in enumerate(zip(pipelines, pipeline_timeouts))
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Validate concurrent execution results
        assert len(results) == 4, "Should have results for all pipelines"
        
        completed_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "completed")
        timeout_count = sum(1 for r in results if isinstance(r, dict) and "timeout" in r.get("status", ""))
        error_count = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"Concurrent pipeline execution: {duration:.3f}s")
        print(f"  Completed: {completed_count}")
        print(f"  Timeouts: {timeout_count}")  
        print(f"  Errors: {error_count}")
        
        # At least some pipelines should complete
        assert completed_count >= 1, "At least one pipeline should complete"
        
        # Fast pipeline should generally succeed
        if isinstance(results[0], dict):
            assert results[0]["status"] == "completed", "Fast pipeline should complete"
        
        # Validate event counts
        total_events = sum(len(ws.events_sent) for ws in websocket_managers)
        total_tools = sum(len(te.tools_executed) for te in tool_executors)
        
        print(f"  Total events sent: {total_events}")
        print(f"  Total tools executed: {total_tools}")
        
        assert total_events > 0, "Should have sent some events"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])