#!/usr/bin/env python
"""
Fixture Cleanup Verification Tests

These tests verify that our enhanced fixture cleanup system works properly
and prevents resource leaks, hanging connections, and memory accumulation.
"""

import asyncio
import gc
import os
import psutil
import pytest
import sys
import time
from typing import Dict, List

# Add project root for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tests.mission_critical.test_websocket_agent_events_suite import MockWebSocketManager, MissionCriticalEventValidator
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier


class ResourceMonitor:
    """Monitor system resources during tests to detect leaks."""
    
    def __init__(self):
        self.initial_memory = None
        self.initial_file_descriptors = None
        self.initial_threads = None
        self.initial_tasks = 0
        self.process = psutil.Process()
    
    def start_monitoring(self):
        """Start resource monitoring."""
        self.initial_memory = self.process.memory_info().rss
        try:
            self.initial_file_descriptors = len(self.process.open_files())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            self.initial_file_descriptors = 0
        
        self.initial_threads = self.process.num_threads()
        
        # Count async tasks if event loop exists
        try:
            loop = asyncio.get_running_loop()
            self.initial_tasks = len([task for task in asyncio.all_tasks(loop) if not task.done()])
        except RuntimeError:
            self.initial_tasks = 0
        
        gc.collect()  # Force garbage collection before measurement
    
    def get_resource_delta(self) -> Dict[str, float]:
        """Get change in resources since monitoring started."""
        current_memory = self.process.memory_info().rss
        memory_delta_mb = (current_memory - self.initial_memory) / 1024 / 1024
        
        try:
            current_fds = len(self.process.open_files())
            fd_delta = current_fds - self.initial_file_descriptors
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            fd_delta = 0
        
        current_threads = self.process.num_threads()
        thread_delta = current_threads - self.initial_threads
        
        # Count current async tasks
        try:
            loop = asyncio.get_running_loop()
            current_tasks = len([task for task in asyncio.all_tasks(loop) if not task.done()])
            task_delta = current_tasks - self.initial_tasks
        except RuntimeError:
            task_delta = 0
        
        return {
            'memory_mb': memory_delta_mb,
            'file_descriptors': fd_delta,
            'threads': thread_delta,
            'async_tasks': task_delta
        }


class TestFixtureCleanupVerification:
    """Verification tests for fixture cleanup functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_resource_monitoring(self):
        """Setup resource monitoring for each test."""
        self.resource_monitor = ResourceMonitor()
        self.resource_monitor.start_monitoring()
        
        yield
        
        # Check for resource leaks after test
        resource_delta = self.resource_monitor.get_resource_delta()
        
        # Allow some tolerance for normal variation
        assert resource_delta['memory_mb'] < 10, f"Memory leak detected: +{resource_delta['memory_mb']:.1f}MB"
        assert resource_delta['file_descriptors'] <= 2, f"File descriptor leak: +{resource_delta['file_descriptors']}"
        assert resource_delta['threads'] <= 1, f"Thread leak detected: +{resource_delta['threads']}"
        assert resource_delta['async_tasks'] <= 1, f"Async task leak: +{resource_delta['async_tasks']}"
    
    @pytest.mark.asyncio
    async def test_mock_websocket_manager_cleanup(self):
        """Test that MockWebSocketManager cleans up properly."""
        managers = []
        
        # Create multiple mock managers
        for i in range(5):
            manager = MockWebSocketManager()
            
            # Add some data
            await manager.send_to_thread(f"thread_{i}", {"type": "test", "data": f"data_{i}"})
            managers.append(manager)
        
        # Verify data exists
        assert len(managers) == 5
        for i, manager in enumerate(managers):
            events = manager.get_events_for_thread(f"thread_{i}")
            assert len(events) == 1
        
        # Cleanup all managers
        for manager in managers:
            manager.clear_messages()
        
        # Verify cleanup
        for manager in managers:
            assert len(manager.messages) == 0
            assert len(manager.connections) == 0
        
        # Force garbage collection
        managers.clear()
        gc.collect()
    
    @pytest.mark.asyncio
    async def test_mission_critical_validator_cleanup(self):
        """Test that MissionCriticalEventValidator cleans up properly."""
        validators = []
        
        # Create multiple validators
        for i in range(3):
            validator = MissionCriticalEventValidator()
            
            # Add some events
            for j in range(10):
                validator.record({
                    "type": f"test_event_{j}",
                    "timestamp": time.time(),
                    "data": f"test_data_{i}_{j}"
                })
            
            validators.append(validator)
        
        # Verify data exists
        for validator in validators:
            assert len(validator.events) == 10
            assert len(validator.event_timeline) == 10
            assert len(validator.event_counts) > 0
        
        # Cleanup validators
        for validator in validators:
            validator.events.clear()
            validator.event_timeline.clear()
            validator.event_counts.clear()
            validator.errors.clear()
            validator.warnings.clear()
        
        # Verify cleanup
        for validator in validators:
            assert len(validator.events) == 0
            assert len(validator.event_timeline) == 0
            assert len(validator.event_counts) == 0
        
        # Force garbage collection
        validators.clear()
        gc.collect()
    
    @pytest.mark.asyncio
    async def test_websocket_notifier_cleanup(self):
        """Test that WebSocketNotifier instances clean up properly."""
        notifiers = []
        
        try:
            # Create multiple notifiers
            for i in range(3):
                ws_manager = MockWebSocketManager()
                notifier = WebSocketNotifier(ws_manager)
                notifiers.append((notifier, ws_manager))
            
            # Use the notifiers
            for i, (notifier, ws_manager) in enumerate(notifiers):
                # Create a context for the notifier
                from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
                context = AgentExecutionContext(
                    run_id=f"test-run-{i}",
                    thread_id=f"test-thread-{i}",
                    user_id=f"test-user-{i}",
                    agent_name="test_agent",
                    retry_count=0,
                    max_retries=1
                )
                
                # Send some events
                await notifier.send_agent_started(context)
                await notifier.send_agent_thinking(context, f"Testing {i}")
            
            # Verify events were recorded
            for i, (notifier, ws_manager) in enumerate(notifiers):
                events = ws_manager.get_events_for_thread(f"test-thread-{i}")
                assert len(events) >= 2, f"Expected at least 2 events for notifier {i}, got {len(events)}"
        
        finally:
            # Cleanup
            for notifier, ws_manager in notifiers:
                try:
                    # Clear WebSocket manager data
                    ws_manager.clear_messages()
                    ws_manager.connections.clear()
                except Exception:
                    pass
            
            # Clear references
            notifiers.clear()
            gc.collect()
    
    @pytest.mark.asyncio
    async def test_repeated_test_execution_no_accumulation(self):
        """Test that running the same test multiple times doesn't accumulate resources."""
        initial_delta = self.resource_monitor.get_resource_delta()
        
        # Run the same WebSocket operations multiple times
        for iteration in range(10):
            manager = MockWebSocketManager()
            validator = MissionCriticalEventValidator()
            
            # Simulate test operations
            for i in range(5):
                await manager.send_to_thread(f"thread_{iteration}_{i}", {
                    "type": "test_event",
                    "iteration": iteration,
                    "index": i
                })
                
                validator.record({
                    "type": "test_event",
                    "iteration": iteration,
                    "index": i,
                    "timestamp": time.time()
                })
            
            # Verify operations worked
            assert len(manager.messages) == 5
            assert len(validator.events) == 5
            
            # Cleanup (simulating fixture cleanup)
            manager.clear_messages()
            manager.connections.clear()
            
            validator.events.clear()
            validator.event_timeline.clear()
            validator.event_counts.clear()
            validator.errors.clear()
            validator.warnings.clear()
            
            # Clear references
            del manager
            del validator
            
            # Force garbage collection every few iterations
            if iteration % 3 == 0:
                gc.collect()
        
        # Check that resources haven't accumulated significantly
        final_delta = self.resource_monitor.get_resource_delta()
        
        # Should not accumulate much more than initial
        memory_growth = final_delta['memory_mb'] - initial_delta['memory_mb']
        assert memory_growth < 5, f"Memory accumulated over iterations: +{memory_growth:.1f}MB"
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_operations_cleanup(self):
        """Test that concurrent WebSocket operations clean up properly."""
        async def websocket_operation(operation_id: int):
            """Single WebSocket operation."""
            manager = MockWebSocketManager()
            validator = MissionCriticalEventValidator()
            
            try:
                # Simulate concurrent operations
                for i in range(5):
                    await manager.send_to_thread(f"concurrent_{operation_id}_{i}", {
                        "type": "concurrent_test",
                        "operation_id": operation_id,
                        "index": i
                    })
                    
                    validator.record({
                        "type": "concurrent_test",
                        "operation_id": operation_id,
                        "index": i,
                        "timestamp": time.time()
                    })
                
                # Brief processing delay
                await asyncio.sleep(0.01)
                
                return len(manager.messages), len(validator.events)
            
            finally:
                # Cleanup
                manager.clear_messages()
                manager.connections.clear()
                validator.events.clear()
                validator.event_timeline.clear()
                validator.event_counts.clear()
        
        # Run multiple concurrent operations
        tasks = [websocket_operation(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        for messages_count, events_count in results:
            assert messages_count == 5
            assert events_count == 5
        
        # Force cleanup
        gc.collect()
        
        # Verify no tasks are lingering
        try:
            loop = asyncio.get_running_loop()
            remaining_tasks = [task for task in asyncio.all_tasks(loop) 
                             if not task.done() and 'websocket_operation' in str(task)]
            assert len(remaining_tasks) == 0, f"Lingering tasks: {len(remaining_tasks)}"
        except RuntimeError:
            pass  # No loop is fine
    
    @pytest.mark.asyncio
    async def test_fixture_exception_cleanup(self):
        """Test that cleanup works even when exceptions occur."""
        managers_created = []
        validators_created = []
        
        try:
            for i in range(3):
                manager = MockWebSocketManager()
                validator = MissionCriticalEventValidator()
                
                managers_created.append(manager)
                validators_created.append(validator)
                
                # Add some data
                await manager.send_to_thread(f"exception_test_{i}", {"type": "test"})
                validator.record({"type": "test", "timestamp": time.time()})
                
                # Simulate an exception on the second iteration
                if i == 1:
                    raise ValueError(f"Simulated exception in iteration {i}")
        
        except ValueError:
            # Expected exception - now test cleanup
            pass
        
        finally:
            # Cleanup should work even after exception
            for manager in managers_created:
                manager.clear_messages()
                manager.connections.clear()
            
            for validator in validators_created:
                validator.events.clear()
                validator.event_timeline.clear()
                validator.event_counts.clear()
        
        # Verify cleanup worked
        for manager in managers_created:
            assert len(manager.messages) == 0
            assert len(manager.connections) == 0
        
        for validator in validators_created:
            assert len(validator.events) == 0
            assert len(validator.event_timeline) == 0
        
        # Force garbage collection
        managers_created.clear()
        validators_created.clear()
        gc.collect()


if __name__ == "__main__":
    # Run verification tests
    pytest.main([__file__, "-v", "--tb=short"])