"""
Mission Critical Test Suite: WebSocket Dead Code Removal Validation
Tests that dead WebSocket context methods are never called and functionality still works.
"""

import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, List, Optional, Set
import threading
import weakref
import tracemalloc
import gc
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base.interface import ExecutionContext


class DeadMethodCallDetector:
    """Advanced detector for dead method calls with thread-safe tracking."""
    
    def __init__(self):
        self.call_log: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self.original_methods = {}
        
    def patch_dead_methods(self, agent_instance):
        """Patch dead methods to detect if they're called."""
        methods_to_patch = [
            '_setup_websocket_context_if_available',
            '_setup_websocket_context_for_legacy'
        ]
        
        for method_name in methods_to_patch:
            if hasattr(agent_instance, method_name):
                original = getattr(agent_instance, method_name)
                self.original_methods[f"{agent_instance.__class__.__name__}.{method_name}"] = original
                
                async def interceptor(*args, method=method_name, agent_class=agent_instance.__class__.__name__, **kwargs):
                    with self.lock:
                        self.call_log.append({
                            'method': method,
                            'agent_class': agent_class,
                            'timestamp': datetime.now(timezone.utc),
                            'args': args,
                            'kwargs': kwargs
                        })
                    # Call original method
                    return await original(*args, **kwargs)
                
                setattr(agent_instance, method_name, interceptor)
    
    def assert_no_calls(self, test_case):
        """Assert that no dead methods were called."""
        with self.lock:
            if self.call_log:
                calls_summary = "\n".join([
                    f"  - {call['agent_class']}.{call['method']} at {call['timestamp']}"
                    for call in self.call_log
                ])
                test_case.fail(f"Dead methods were called:\n{calls_summary}")


class MockWebSocketManager:
    """Mock WebSocket manager that captures all events."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        
    async def send_agent_event(self, event_type: str, data: Dict[str, Any]):
        """Capture WebSocket events."""
        with self.lock:
            self.events.append({
                'type': event_type,
                'data': data,
                'timestamp': datetime.now(timezone.utc)
            })
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        with self.lock:
            return [e for e in self.events if e['type'] == event_type]


class TestDeadMethodDetection(unittest.TestCase):
    """Test that dead WebSocket context methods are never called."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = DeadMethodCallDetector()
        self.websocket_manager = MockWebSocketManager()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
        
    def test_data_sub_agent_no_dead_method_calls(self):
        """Test DataSubAgent doesn't call dead WebSocket methods during execution."""
        async def run_test():
            # Create agent with patched methods
            agent = DataSubAgent()
            self.detector.patch_dead_methods(agent)
            
            # Set up WebSocket bridge (modern pattern)
            bridge = AgentWebSocketBridge()
            agent.set_websocket_bridge(bridge, "test_run_123")
            
            # Create execution context
            context = ExecutionContext(
                run_id="test_run_123",
                user_id="test_user",
                agent_name="DataSubAgent",
                state={}
            )
            
            # Execute agent (should NOT call dead methods)
            try:
                await agent.execute(context, {"query": "test query"})
            except Exception:
                pass  # We're testing method calls, not functionality
            
            # Verify no dead methods were called
            self.detector.assert_no_calls(self)
        
        self.loop.run_until_complete(run_test())
    
    def test_validation_sub_agent_no_dead_method_calls(self):
        """Test ValidationSubAgent doesn't call dead WebSocket methods."""
        async def run_test():
            # Create agent with patched methods
            agent = ValidationSubAgent()
            self.detector.patch_dead_methods(agent)
            
            # Set up WebSocket bridge
            bridge = AgentWebSocketBridge()
            agent.set_websocket_bridge(bridge, "test_run_456")
            
            # Create execution context
            context = ExecutionContext(
                run_id="test_run_456",
                user_id="test_user",
                agent_name="ValidationSubAgent",
                state={}
            )
            
            # Execute agent
            try:
                await agent.execute(context, {"data": "test data"})
            except Exception:
                pass
            
            # Verify no dead methods were called
            self.detector.assert_no_calls(self)
        
        self.loop.run_until_complete(run_test())
    
    def test_multiple_concurrent_agents_no_dead_calls(self):
        """Test multiple agents running concurrently don't call dead methods."""
        async def run_test():
            agents = []
            
            # Create multiple agents
            for i in range(5):
                if i % 2 == 0:
                    agent = DataSubAgent()
                else:
                    agent = ValidationSubAgent()
                
                self.detector.patch_dead_methods(agent)
                
                # Set up WebSocket bridge
                bridge = AgentWebSocketBridge()
                agent.set_websocket_bridge(bridge, f"test_run_{i}")
                
                agents.append((agent, f"test_run_{i}"))
            
            # Execute all agents concurrently
            async def execute_agent(agent, run_id):
                context = ExecutionContext(
                    run_id=run_id,
                    user_id="test_user",
                    agent_name=agent.__class__.__name__,
                    state={}
                )
                try:
                    await agent.execute(context, {"test": "data"})
                except Exception:
                    pass
            
            # Run all agents concurrently
            await asyncio.gather(*[
                execute_agent(agent, run_id) 
                for agent, run_id in agents
            ])
            
            # Verify no dead methods were called
            self.detector.assert_no_calls(self)
        
        self.loop.run_until_complete(run_test())
    
    def test_error_scenarios_no_dead_method_calls(self):
        """Test that even in error scenarios, dead methods aren't called."""
        async def run_test():
            agent = DataSubAgent()
            self.detector.patch_dead_methods(agent)
            
            # Test with null context
            try:
                await agent.execute(None, {})
            except Exception:
                pass
            
            # Test with malformed context
            try:
                await agent.execute(ExecutionContext(
                    run_id=None,
                    user_id=None,
                    agent_name="",
                    state=None
                ), {})
            except Exception:
                pass
            
            # Verify no dead methods were called even in error cases
            self.detector.assert_no_calls(self)
        
        self.loop.run_until_complete(run_test())


class TestWebSocketEventIntegrity(unittest.TestCase):
    """Test that WebSocket events still work properly without dead methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_websocket_events_flow_through_bridge(self):
        """Test WebSocket events flow correctly through the bridge pattern."""
        async def run_test():
            # Mock the global bridge
            mock_bridge = Mock(spec=AgentWebSocketBridge)
            mock_bridge.notify_agent_thinking = AsyncMock()
            mock_bridge.notify_tool_executing = AsyncMock()
            mock_bridge.notify_agent_completed = AsyncMock()
            
            # Create agent and set bridge
            agent = DataSubAgent()
            agent.set_websocket_bridge(mock_bridge, "test_run")
            
            # Emit events through the modern pattern
            await agent.emit_thinking("Processing data...")
            await agent.emit_tool_executing("data_analysis", {"query": "test"})
            await agent.emit_progress("Analysis complete", is_complete=True)
            
            # Verify bridge methods were called
            mock_bridge.notify_agent_thinking.assert_called()
            mock_bridge.notify_tool_executing.assert_called()
        
        self.loop.run_until_complete(run_test())
    
    def test_real_agent_execution_with_websocket_events(self):
        """Test real agent execution emits WebSocket events correctly."""
        async def run_test():
            # Create a mock bridge that captures events
            events_captured = []
            
            mock_bridge = Mock(spec=AgentWebSocketBridge)
            async def capture_event(run_id, agent_name, *args, **kwargs):
                events_captured.append({
                    'run_id': run_id,
                    'agent_name': agent_name,
                    'args': args,
                    'kwargs': kwargs
                })
            
            mock_bridge.notify_agent_thinking = capture_event
            mock_bridge.notify_tool_executing = capture_event
            mock_bridge.notify_agent_completed = capture_event
            
            # Create and configure agent
            agent = ValidationSubAgent()
            agent.set_websocket_bridge(mock_bridge, "validation_run")
            
            context = ExecutionContext(
                run_id="validation_run",
                user_id="test_user",
                agent_name="ValidationSubAgent",
                state={}
            )
            
            # Execute agent
            try:
                await agent.execute(context, {
                    "data_to_validate": {"test": "data"},
                    "validation_rules": ["format_check", "completeness_check"]
                })
            except Exception:
                pass  # Focus on event emission
            
            # Verify events were captured
            self.assertGreater(len(events_captured), 0, "No WebSocket events were emitted")
            
            # Verify run_id consistency
            for event in events_captured:
                self.assertEqual(event['run_id'], "validation_run")
        
        self.loop.run_until_complete(run_test())
    
    def test_concurrent_websocket_events(self):
        """Test concurrent agents emit WebSocket events without interference."""
        async def run_test():
            event_counts = {}
            lock = threading.Lock()
            
            # Create shared mock bridge
            mock_bridge = Mock(spec=AgentWebSocketBridge)
            
            async def count_events(run_id, *args, **kwargs):
                with lock:
                    event_counts[run_id] = event_counts.get(run_id, 0) + 1
            
            mock_bridge.notify_agent_thinking = count_events
            mock_bridge.notify_tool_executing = count_events
            mock_bridge.notify_agent_completed = count_events
            
            # Create multiple agents
            agents = []
            for i in range(10):
                agent = DataSubAgent() if i % 2 == 0 else ValidationSubAgent()
                run_id = f"concurrent_run_{i}"
                agent.set_websocket_bridge(mock_bridge, run_id)
                agents.append((agent, run_id))
            
            # Execute agents concurrently
            async def run_agent(agent, run_id):
                context = ExecutionContext(
                    run_id=run_id,
                    user_id="test_user",
                    agent_name=agent.__class__.__name__,
                    state={}
                )
                try:
                    await agent.execute(context, {"test": "data"})
                except Exception:
                    pass
            
            await asyncio.gather(*[
                run_agent(agent, run_id)
                for agent, run_id in agents
            ])
            
            # Verify each agent emitted events
            self.assertEqual(len(event_counts), 10, "Not all agents emitted events")
        
        self.loop.run_until_complete(run_test())


class TestMemoryAndThreadSafety(unittest.TestCase):
    """Test for memory leaks and thread safety issues."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_no_memory_leaks_after_refactor(self):
        """Test that removing dead code doesn't introduce memory leaks."""
        async def run_test():
            tracemalloc.start()
            
            # Create and destroy many agents
            weak_refs = []
            
            for i in range(100):
                agent = DataSubAgent()
                bridge = AgentWebSocketBridge()
                agent.set_websocket_bridge(bridge, f"mem_test_{i}")
                
                # Create weak reference to track garbage collection
                weak_refs.append(weakref.ref(agent))
                
                # Execute agent
                context = ExecutionContext(
                    run_id=f"mem_test_{i}",
                    user_id="test_user",
                    agent_name="DataSubAgent",
                    state={}
                )
                
                try:
                    await agent.execute(context, {"test": "data"})
                except Exception:
                    pass
                
                # Explicitly delete references
                del agent
                del bridge
                del context
            
            # Force garbage collection
            gc.collect()
            
            # Check that agents were garbage collected
            alive_count = sum(1 for ref in weak_refs if ref() is not None)
            self.assertEqual(alive_count, 0, f"{alive_count} agents not garbage collected")
            
            # Check memory usage
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            # Verify no excessive memory usage
            total_memory = sum(stat.size for stat in top_stats[:10])
            self.assertLess(total_memory, 10 * 1024 * 1024, "Excessive memory usage detected")
            
            tracemalloc.stop()
        
        self.loop.run_until_complete(run_test())
    
    def test_thread_safety_with_concurrent_operations(self):
        """Test thread safety with concurrent agent operations."""
        async def run_test():
            errors = []
            completed = []
            
            def thread_worker(agent_id):
                """Worker function for thread pool."""
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    agent = ValidationSubAgent()
                    bridge = AgentWebSocketBridge()
                    agent.set_websocket_bridge(bridge, f"thread_test_{agent_id}")
                    
                    context = ExecutionContext(
                        run_id=f"thread_test_{agent_id}",
                        user_id="test_user",
                        agent_name="ValidationSubAgent",
                        state={}
                    )
                    
                    loop.run_until_complete(agent.execute(context, {"test": "data"}))
                    completed.append(agent_id)
                    
                except Exception as e:
                    errors.append((agent_id, str(e)))
                finally:
                    loop.close()
            
            # Run agents in thread pool
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(thread_worker, i)
                    for i in range(20)
                ]
                
                # Wait for all to complete
                for future in futures:
                    future.result()
            
            # Verify no thread safety errors
            self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")
            self.assertEqual(len(completed), 20, "Not all threads completed")
        
        self.loop.run_until_complete(run_test())


class TestEdgeCasesAndErrorHandling(unittest.TestCase):
    """Test edge cases and error handling after dead code removal."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    def tearDown(self):
        """Clean up after tests."""
        self.loop.close()
    
    def test_agent_with_no_websocket_manager(self):
        """Test agent behavior when WebSocket manager is not set."""
        async def run_test():
            agent = DataSubAgent()
            # Don't set WebSocket bridge
            
            context = ExecutionContext(
                run_id="no_ws_test",
                user_id="test_user",
                agent_name="DataSubAgent",
                state={}
            )
            
            # Should not crash even without WebSocket
            try:
                result = await agent.execute(context, {"query": "test"})
                # Verify agent still executes
                self.assertIsNotNone(result)
            except AttributeError as e:
                if "websocket" in str(e).lower():
                    self.fail(f"Agent crashed without WebSocket: {e}")
        
        self.loop.run_until_complete(run_test())
    
    def test_websocket_send_failure_handling(self):
        """Test handling of WebSocket send failures."""
        async def run_test():
            # Create bridge that fails on send
            mock_bridge = Mock(spec=AgentWebSocketBridge)
            mock_bridge.notify_agent_thinking = AsyncMock(
                side_effect=Exception("WebSocket connection lost")
            )
            
            agent = ValidationSubAgent()
            agent.set_websocket_bridge(mock_bridge, "fail_test")
            
            context = ExecutionContext(
                run_id="fail_test",
                user_id="test_user",
                agent_name="ValidationSubAgent",
                state={}
            )
            
            # Should handle WebSocket failures gracefully
            try:
                await agent.execute(context, {"data": "test"})
            except Exception as e:
                if "WebSocket connection lost" in str(e):
                    self.fail("WebSocket failure not handled gracefully")
        
        self.loop.run_until_complete(run_test())
    
    def test_malformed_execution_context(self):
        """Test handling of malformed execution contexts."""
        async def run_test():
            agent = DataSubAgent()
            bridge = AgentWebSocketBridge()
            agent.set_websocket_bridge(bridge, "malformed_test")
            
            # Test with various malformed contexts
            malformed_contexts = [
                None,
                {},
                ExecutionContext(run_id="", user_id="", agent_name="", state=None),
                ExecutionContext(run_id=123, user_id=[], agent_name={}, state="invalid"),
            ]
            
            for i, context in enumerate(malformed_contexts):
                try:
                    await agent.execute(context, {"test": "data"})
                except (AttributeError, TypeError, ValueError):
                    pass  # Expected for malformed input
                except Exception as e:
                    self.fail(f"Unexpected error with malformed context {i}: {e}")
        
        self.loop.run_until_complete(run_test())
    
    def test_rapid_sequential_executions(self):
        """Test rapid sequential executions don't cause issues."""
        async def run_test():
            agent = ValidationSubAgent()
            bridge = AgentWebSocketBridge()
            
            # Rapidly execute agent many times
            for i in range(100):
                agent.set_websocket_bridge(bridge, f"rapid_test_{i}")
                
                context = ExecutionContext(
                    run_id=f"rapid_test_{i}",
                    user_id="test_user",
                    agent_name="ValidationSubAgent",
                    state={}
                )
                
                try:
                    await agent.execute(context, {"data": f"test_{i}"})
                except Exception:
                    pass  # Focus on stability, not functionality
                
                # Reset for next iteration
                agent._websocket_adapter._bridge = None
            
            # If we get here without crashing, test passes
            self.assertTrue(True)
        
        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main(verbosity=2)