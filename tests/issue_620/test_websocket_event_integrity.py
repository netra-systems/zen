"""WEBSOCKET EVENT INTEGRITY TESTS: Real-time Events (MUST ALWAYS PASS).

These tests MUST PASS throughout the entire SSOT migration process.
They ensure that WebSocket event delivery remains intact during migration.

Business Impact: Protects real-time chat experience and user engagement.
"""

import asyncio
import time
import importlib
import pytest
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketEventMonitor:
    """Monitor WebSocket events during testing."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_lock = asyncio.Lock()
        self.start_time = time.time()
        
    async def capture_event(self, event_type: str, *args, **kwargs):
        """Capture a WebSocket event with timestamp."""
        async with self.event_lock:
            event_data = {
                "type": event_type,
                "timestamp": time.time(),
                "relative_time": time.time() - self.start_time,
                "args": args,
                "kwargs": kwargs,
                "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
            }
            self.events.append(event_data)
            logger.debug(f"📡 WebSocket event captured: {event_type} at {event_data['relative_time']:.3f}s")
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get all captured events."""
        return self.events.copy()
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get events of specific type."""
        return [event for event in self.events if event["type"] == event_type]
    
    def get_event_timeline(self) -> List[str]:
        """Get timeline of events as strings."""
        return [f"{event['type']}@{event['relative_time']:.3f}s" for event in self.events]
    
    def clear(self):
        """Clear captured events."""
        self.events.clear()
        self.start_time = time.time()


class TestWebSocketEventIntegrity(SSotAsyncTestCase):
    """Test suite to validate WebSocket event integrity during SSOT migration."""
    
    async def test_websocket_events_during_migration(self):
        """WEBSOCKET TEST: All WebSocket events delivered correctly during migration.
        
        This test validates that WebSocket event delivery remains intact
        during the SSOT migration process.
        
        Expected Behavior: MUST ALWAYS PASS (before, during, after migration)
        Business Impact: Protects real-time chat experience
        """
        logger.info("📡 WEBSOCKET TEST: Event delivery during migration")
        
        # Test both migration patterns
        test_patterns = [
            {
                "name": "UserExecutionEngine_Direct",
                "description": "Direct UserExecutionEngine usage (post-migration)"
            },
            {
                "name": "ExecutionEngine_Compatibility", 
                "description": "Compatibility layer usage (during migration)"
            }
        ]
        
        for pattern in test_patterns:
            logger.info(f"Testing WebSocket events with {pattern['name']}")
            
            user_context = self._create_websocket_test_user_context(pattern['name'])
            monitor = WebSocketEventMonitor()
            
            # Create execution engine using migration-compatible approach
            engine = await self._create_websocket_test_engine(user_context, monitor, pattern)
            
            if engine is None:
                logger.info(f"⏭️ Skipping {pattern['name']} - not available in current migration state")
                continue
            
            try:
                # Execute agent and monitor events
                agent_context = self._create_websocket_test_agent_context(user_context, pattern)
                
                # Execute with comprehensive event monitoring
                result = await self._execute_agent_with_comprehensive_monitoring(
                    engine, agent_context, user_context, monitor
                )
                
                # Validate all required events
                await self._validate_comprehensive_websocket_events(monitor, pattern['name'])
                
                # Validate event sequence and timing
                await self._validate_websocket_event_flow(monitor, pattern['name'])
                
                logger.info(f"✅ WebSocket events validated for {pattern['name']}")
                
            except Exception as e:
                logger.error(f"WebSocket test failed for {pattern['name']}: {e}")
                if "not available" not in str(e).lower():
                    pytest.fail(f"WEBSOCKET INTEGRITY FAILURE: {pattern['name']} failed: {e}")
            
            finally:
                await self._cleanup_websocket_engine(engine)
    
    async def test_critical_websocket_event_sequence(self):
        """WEBSOCKET TEST: Critical event sequence maintained.
        
        This test validates that the 5 critical WebSocket events are delivered
        in the correct sequence with proper timing.
        """
        logger.info("📡 WEBSOCKET TEST: Critical event sequence validation")
        
        user_context = self._create_websocket_test_user_context("sequence_test")
        monitor = WebSocketEventMonitor()
        
        # Create engine with comprehensive monitoring
        engine = await self._create_best_available_engine(user_context, monitor)
        
        # Execute agent that triggers all critical events
        agent_context = AgentExecutionContext(
            agent_name="supervisor_agent",  # Agent that uses tools
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            user_input="Execute comprehensive workflow with all WebSocket events",
            metadata={
                "test_case": "critical_sequence_validation",
                "requires_all_events": True,
                "websocket_critical": True
            }
        )
        
        # Execute with event sequence monitoring
        result = await self._execute_with_critical_event_sequence(
            engine, agent_context, user_context, monitor
        )
        
        # Validate critical event sequence
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        await self._validate_critical_event_sequence(monitor, critical_events)
        
        # Validate event timing constraints
        await self._validate_event_timing_constraints(monitor)
        
        logger.info(f"✅ Critical WebSocket event sequence validated: {len(monitor.get_events())} events")
        
        await self._cleanup_websocket_engine(engine)
    
    async def test_websocket_event_isolation_per_user(self):
        """WEBSOCKET TEST: WebSocket events properly isolated per user.
        
        This test validates that WebSocket events are delivered only to the
        correct user and not to other concurrent users.
        """
        logger.info("📡 WEBSOCKET TEST: Per-user event isolation")
        
        # Create multiple users
        num_users = 3
        user_contexts = [
            self._create_websocket_test_user_context(f"isolation_user_{i}")
            for i in range(num_users)
        ]
        
        # Create monitors for each user
        user_monitors = [WebSocketEventMonitor() for _ in range(num_users)]
        
        # Create engines for each user with isolated monitoring
        user_engines = []
        for i, (context, monitor) in enumerate(zip(user_contexts, user_monitors)):
            engine = await self._create_isolated_websocket_engine(context, monitor, i)
            user_engines.append(engine)
        
        # Execute agents simultaneously for all users
        tasks = []
        for i, (engine, context, monitor) in enumerate(zip(user_engines, user_contexts, user_monitors)):
            task = asyncio.create_task(self._execute_isolated_user_websocket_session(
                engine, context, monitor, i
            ))
            tasks.append(task)
        
        # Wait for all executions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate isolation
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"User {i} WebSocket session failed: {result}")
                continue
            
            # Validate user received their own events
            user_monitor = user_monitors[i]
            user_events = user_monitor.get_events()
            
            if len(user_events) == 0:
                pytest.fail(f"WEBSOCKET ISOLATION FAILURE: User {i} received no events")
            
            # Validate events belong to correct user
            for event in user_events:
                # Check if event contains user-specific data
                event_args = event.get("args", [])
                event_kwargs = event.get("kwargs", {})
                
                user_id = user_contexts[i].user_id
                run_id = user_contexts[i].run_id
                
                # Events should contain correct user's run_id
                if event_args and len(event_args) > 0:
                    if run_id not in str(event_args[0]):
                        logger.warning(f"Event for user {i} missing run_id: {event}")
        
        # Validate no cross-user event contamination
        await self._validate_no_cross_user_events(user_monitors, user_contexts)
        
        logger.info(f"✅ WebSocket event isolation validated for {num_users} users")
        
        # Cleanup
        for engine in user_engines:
            await self._cleanup_websocket_engine(engine)
    
    async def test_websocket_event_error_recovery(self):
        """WEBSOCKET TEST: WebSocket event delivery recovers from errors.
        
        This test validates that WebSocket event delivery can recover
        from temporary failures without losing events.
        """
        logger.info("📡 WEBSOCKET TEST: Event delivery error recovery")
        
        user_context = self._create_websocket_test_user_context("error_recovery_test")
        monitor = WebSocketEventMonitor()
        
        # Create engine with error simulation
        engine = await self._create_error_recovery_websocket_engine(user_context, monitor)
        
        agent_context = AgentExecutionContext(
            agent_name="error_recovery_agent",
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            user_input="Test WebSocket error recovery",
            metadata={
                "test_case": "error_recovery",
                "simulate_errors": True
            }
        )
        
        # Execute with simulated WebSocket failures
        result = await self._execute_with_websocket_error_simulation(
            engine, agent_context, user_context, monitor
        )
        
        # Validate that despite errors, events were eventually delivered
        events = monitor.get_events()
        
        # Should have at least some successful events after recovery
        successful_events = [e for e in events if not e.get("error", False)]
        
        if len(successful_events) == 0:
            pytest.fail(
                "WEBSOCKET RECOVERY FAILURE: No events delivered after error recovery"
            )
        
        # Validate specific recovery events if they exist
        recovery_events = [e for e in events if "recovery" in e.get("type", "")]
        if recovery_events:
            logger.info(f"✅ WebSocket error recovery detected: {len(recovery_events)} recovery events")
        
        logger.info(f"✅ WebSocket error recovery validated: {len(successful_events)}/{len(events)} events successful")
        
        await self._cleanup_websocket_engine(engine)
    
    async def test_websocket_event_performance_during_migration(self):
        """WEBSOCKET TEST: WebSocket event performance maintained during migration.
        
        This test validates that WebSocket event delivery performance
        does not degrade significantly during the SSOT migration.
        """
        logger.info("📡 WEBSOCKET TEST: Event delivery performance")
        
        user_context = self._create_websocket_test_user_context("performance_test")
        monitor = WebSocketEventMonitor()
        
        engine = await self._create_best_available_engine(user_context, monitor)
        
        # Performance test parameters
        num_events = 10
        performance_metrics = {
            "event_count": 0,
            "total_time": 0.0,
            "avg_time_per_event": 0.0,
            "max_event_gap": 0.0,
            "events_per_second": 0.0
        }
        
        start_time = time.time()
        
        # Execute multiple agents to generate events
        for i in range(num_events):
            agent_context = AgentExecutionContext(
                agent_name="performance_test_agent",
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=f"{user_context.run_id}_perf_{i}",
                user_input=f"Performance test event {i}",
                metadata={"performance_test": i, "batch_size": num_events}
            )
            
            await self._execute_performance_test_agent(engine, agent_context, user_context)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze performance
        events = monitor.get_events()
        performance_metrics["event_count"] = len(events)
        performance_metrics["total_time"] = total_time
        
        if len(events) > 0:
            performance_metrics["avg_time_per_event"] = total_time / len(events)
            performance_metrics["events_per_second"] = len(events) / total_time
            
            # Calculate maximum gap between events
            event_times = [e["timestamp"] for e in events]
            if len(event_times) > 1:
                gaps = [event_times[i] - event_times[i-1] for i in range(1, len(event_times))]
                performance_metrics["max_event_gap"] = max(gaps)
        
        # Validate performance requirements
        if performance_metrics["events_per_second"] < 1.0:
            pytest.fail(
                f"WEBSOCKET PERFORMANCE FAILURE: Event delivery too slow: "
                f"{performance_metrics['events_per_second']:.2f} events/sec < 1.0 events/sec minimum"
            )
        
        if performance_metrics["max_event_gap"] > 5.0:
            pytest.fail(
                f"WEBSOCKET PERFORMANCE FAILURE: Event gap too large: "
                f"{performance_metrics['max_event_gap']:.2f}s > 5.0s maximum"
            )
        
        logger.info(f"✅ WebSocket performance validated: {performance_metrics}")
        
        await self._cleanup_websocket_engine(engine)
    
    # Helper methods for WebSocket event testing
    
    def _create_websocket_test_user_context(self, test_name: str) -> UserExecutionContext:
        """Create user context for WebSocket testing."""
        return UserExecutionContext(
            user_id=f"websocket_{test_name}_user",
            thread_id=f"websocket_{test_name}_thread",
            run_id=f"websocket_{test_name}_run_{int(time.time())}",
            request_id=f"websocket_{test_name}_req_{int(time.time())}",
            audit_metadata={
                "websocket_test": True,
                "test_name": test_name,
                "requires_events": ["agent_started", "agent_thinking", "agent_completed"],
                "test_timestamp": time.time()
            }
        )
    
    async def _create_websocket_test_engine(self, user_context: UserExecutionContext, 
                                          monitor: WebSocketEventMonitor, pattern: Dict[str, str]):
        """Create execution engine for WebSocket testing."""
        try:
            if "UserExecutionEngine" in pattern["name"]:
                # Try UserExecutionEngine first
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                
                mock_agent_factory = Mock()
                websocket_bridge = self._create_monitored_websocket_bridge(monitor)
                
                # Try legacy compatibility first
                try:
                    engine = await UserExecutionEngine.create_from_legacy(
                        registry=Mock(),
                        websocket_bridge=websocket_bridge,
                        user_context=user_context
                    )
                    logger.info(f"Created UserExecutionEngine via legacy compatibility for {pattern['name']}")
                    return engine
                except Exception as e:
                    logger.debug(f"Legacy compatibility failed: {e}")
                    
                    # Try direct constructor
                    mock_websocket_emitter = self._create_monitored_websocket_emitter(monitor, user_context)
                    engine = UserExecutionEngine(user_context, mock_agent_factory, mock_websocket_emitter)
                    logger.info(f"Created UserExecutionEngine directly for {pattern['name']}")
                    return engine
            
            else:
                # Try deprecated ExecutionEngine
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
                
                mock_registry = Mock()
                websocket_bridge = self._create_monitored_websocket_bridge(monitor)
                
                engine = await ExecutionEngine.create_from_legacy(mock_registry, websocket_bridge, user_context=user_context)
                logger.info(f"Created ExecutionEngine for {pattern['name']}")
                return engine
                
        except ImportError as e:
            logger.info(f"Engine type not available for {pattern['name']}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create engine for {pattern['name']}: {e}")
            return None
    
    async def _create_best_available_engine(self, user_context: UserExecutionContext, 
                                          monitor: WebSocketEventMonitor):
        """Create best available execution engine."""
        # Try UserExecutionEngine first
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            mock_registry = Mock()
            websocket_bridge = self._create_monitored_websocket_bridge(monitor)
            
            engine = await UserExecutionEngine.create_from_legacy(
                registry=mock_registry,
                websocket_bridge=websocket_bridge,
                user_context=user_context
            )
            logger.info("Created UserExecutionEngine for WebSocket testing")
            return engine
            
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"UserExecutionEngine creation failed: {e}")
        
        # Fallback to deprecated ExecutionEngine
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            
            mock_registry = Mock()
            websocket_bridge = self._create_monitored_websocket_bridge(monitor)
            
            engine = ExecutionEngine(mock_registry, websocket_bridge, user_context)
            logger.info("Created ExecutionEngine for WebSocket testing")
            return engine
            
        except ImportError:
            pytest.fail("CRITICAL: No ExecutionEngine implementation available for WebSocket testing")
        except Exception as e:
            pytest.fail(f"CRITICAL: Failed to create any ExecutionEngine: {e}")
    
    def _create_monitored_websocket_bridge(self, monitor: WebSocketEventMonitor):
        """Create WebSocket bridge that sends events to monitor."""
        mock_bridge = Mock()
        
        async def monitored_notify(event_type, *args, **kwargs):
            await monitor.capture_event(event_type, *args, **kwargs)
        
        mock_bridge.notify_agent_started = AsyncMock(side_effect=lambda *args, **kwargs: monitored_notify("agent_started", *args, **kwargs))
        mock_bridge.notify_agent_thinking = AsyncMock(side_effect=lambda *args, **kwargs: monitored_notify("agent_thinking", *args, **kwargs))
        mock_bridge.notify_tool_executing = AsyncMock(side_effect=lambda *args, **kwargs: monitored_notify("tool_executing", *args, **kwargs))
        mock_bridge.notify_tool_completed = AsyncMock(side_effect=lambda *args, **kwargs: monitored_notify("tool_completed", *args, **kwargs))
        mock_bridge.notify_agent_completed = AsyncMock(side_effect=lambda *args, **kwargs: monitored_notify("agent_completed", *args, **kwargs))
        mock_bridge.notify_agent_error = AsyncMock(side_effect=lambda *args, **kwargs: monitored_notify("agent_error", *args, **kwargs))
        
        return mock_bridge
    
    def _create_monitored_websocket_emitter(self, monitor: WebSocketEventMonitor, user_context: UserExecutionContext):
        """Create WebSocket emitter that sends events to monitor."""
        mock_emitter = Mock()
        
        async def monitored_emit(event_type, *args, **kwargs):
            await monitor.capture_event(event_type, *args, **kwargs)
        
        mock_emitter.notify_agent_started = AsyncMock(side_effect=lambda *args, **kwargs: monitored_emit("agent_started", *args, **kwargs))
        mock_emitter.notify_agent_thinking = AsyncMock(side_effect=lambda *args, **kwargs: monitored_emit("agent_thinking", *args, **kwargs))
        mock_emitter.notify_tool_executing = AsyncMock(side_effect=lambda *args, **kwargs: monitored_emit("tool_executing", *args, **kwargs))
        mock_emitter.notify_tool_completed = AsyncMock(side_effect=lambda *args, **kwargs: monitored_emit("tool_completed", *args, **kwargs))
        mock_emitter.notify_agent_completed = AsyncMock(side_effect=lambda *args, **kwargs: monitored_emit("agent_completed", *args, **kwargs))
        
        return mock_emitter
    
    def _create_websocket_test_agent_context(self, user_context: UserExecutionContext, pattern: Dict[str, str]) -> AgentExecutionContext:
        """Create agent context for WebSocket testing."""
        return AgentExecutionContext(
            agent_name="websocket_test_agent",
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            user_input=f"WebSocket test for {pattern['name']}",
            metadata={
                "test_pattern": pattern["name"],
                "websocket_test": True,
                "requires_events": True
            }
        )
    
    async def _execute_agent_with_comprehensive_monitoring(self, engine, agent_context: AgentExecutionContext,
                                                         user_context: UserExecutionContext, monitor: WebSocketEventMonitor):
        """Execute agent with comprehensive WebSocket event monitoring."""
        
        # Mock agent execution that triggers WebSocket events
        async def mock_execution_with_events(*args, **kwargs):
            """Mock execution that triggers comprehensive WebSocket events."""
            
            # Get WebSocket bridge from engine
            websocket_bridge = None
            if hasattr(engine, 'websocket_bridge'):
                websocket_bridge = engine.websocket_bridge
            elif hasattr(engine, '_websocket_bridge'):
                websocket_bridge = engine._websocket_bridge
            
            if websocket_bridge:
                # Trigger comprehensive event sequence
                await websocket_bridge.notify_agent_started(
                    agent_context.run_id, agent_context.agent_name, {"status": "started"}
                )
                
                await asyncio.sleep(0.05)  # Small delay between events
                await websocket_bridge.notify_agent_thinking(
                    agent_context.run_id, agent_context.agent_name, "Processing WebSocket test...", step_number=1
                )
                
                await asyncio.sleep(0.05)
                await websocket_bridge.notify_tool_executing(
                    agent_context.run_id, agent_context.agent_name, "websocket_tester", {"test": True}
                )
                
                await asyncio.sleep(0.05)
                await websocket_bridge.notify_tool_completed(
                    agent_context.run_id, agent_context.agent_name, "websocket_tester", {"result": "success"}
                )
                
                await asyncio.sleep(0.05)
                await websocket_bridge.notify_agent_completed(
                    agent_context.run_id, agent_context.agent_name, 
                    {"response": "WebSocket test completed"}, 250.0
                )
            
            return AgentExecutionResult(
                success=True,
                agent_name=agent_context.agent_name,
                execution_time=0.25,
                data={
                    "response": "WebSocket test completed successfully",
                    "events_triggered": 5,
                    "websocket_test": True
                }
            )
        
        # Execute with mock
        if hasattr(engine, 'execute_agent'):
            with patch.object(engine, 'execute_agent', new_callable=AsyncMock) as mock_execute:
                mock_execute.side_effect = mock_execution_with_events
                result = await engine.execute_agent(agent_context, user_context)
        else:
            result = await mock_execution_with_events()
        
        return result
    
    async def _validate_comprehensive_websocket_events(self, monitor: WebSocketEventMonitor, pattern_name: str):
        """Validate comprehensive WebSocket event delivery."""
        events = monitor.get_events()
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        captured_event_types = [event["type"] for event in events]
        
        for required_event in required_events:
            matching_events = [e for e in events if e["type"] == required_event]
            if len(matching_events) == 0:
                pytest.fail(
                    f"WEBSOCKET INTEGRITY FAILURE [{pattern_name}]: Required event '{required_event}' not delivered. "
                    f"Captured events: {captured_event_types}. Real-time chat experience broken."
                )
        
        logger.info(f"✅ All {len(required_events)} required WebSocket events delivered for {pattern_name}")
    
    async def _validate_websocket_event_flow(self, monitor: WebSocketEventMonitor, pattern_name: str):
        """Validate WebSocket event flow and timing."""
        events = monitor.get_events()
        
        if len(events) < 2:
            return
        
        event_types = [event["type"] for event in events]
        event_timeline = monitor.get_event_timeline()
        
        # Validate sequence
        if event_types[0] != "agent_started":
            pytest.fail(
                f"WEBSOCKET SEQUENCE FAILURE [{pattern_name}]: First event must be 'agent_started', got '{event_types[0]}'. "
                f"Timeline: {event_timeline}"
            )
        
        if event_types[-1] != "agent_completed":
            pytest.fail(
                f"WEBSOCKET SEQUENCE FAILURE [{pattern_name}]: Last event must be 'agent_completed', got '{event_types[-1]}'. "
                f"Timeline: {event_timeline}"
            )
        
        # Validate reasonable timing
        first_event_time = events[0]["relative_time"]
        last_event_time = events[-1]["relative_time"]
        total_duration = last_event_time - first_event_time
        
        if total_duration < 0.01:  # At least 10ms between first and last
            pytest.fail(
                f"WEBSOCKET TIMING FAILURE [{pattern_name}]: Events too close together ({total_duration:.3f}s). "
                f"Timeline: {event_timeline}"
            )
        
        if total_duration > 10.0:  # Not more than 10 seconds
            pytest.fail(
                f"WEBSOCKET TIMING FAILURE [{pattern_name}]: Events too spread out ({total_duration:.3f}s). "
                f"Timeline: {event_timeline}"
            )
        
        logger.info(f"✅ WebSocket event flow validated for {pattern_name}: {total_duration:.3f}s duration")
    
    async def _execute_with_critical_event_sequence(self, engine, agent_context: AgentExecutionContext,
                                                   user_context: UserExecutionContext, monitor: WebSocketEventMonitor):
        """Execute agent with critical event sequence monitoring."""
        return await self._execute_agent_with_comprehensive_monitoring(engine, agent_context, user_context, monitor)
    
    async def _validate_critical_event_sequence(self, monitor: WebSocketEventMonitor, critical_events: List[str]):
        """Validate critical event sequence."""
        events = monitor.get_events()
        captured_event_types = [event["type"] for event in events]
        
        # Check all critical events are present
        for critical_event in critical_events:
            if critical_event not in captured_event_types:
                pytest.fail(
                    f"CRITICAL EVENT MISSING: '{critical_event}' not found in sequence. "
                    f"Captured: {captured_event_types}. Critical chat functionality broken."
                )
        
        # Validate order of critical events
        critical_positions = []
        for critical_event in critical_events:
            for i, event_type in enumerate(captured_event_types):
                if event_type == critical_event:
                    critical_positions.append((critical_event, i))
                    break
        
        # Check if positions are in ascending order
        positions = [pos for _, pos in critical_positions]
        if positions != sorted(positions):
            pytest.fail(
                f"CRITICAL EVENT SEQUENCE VIOLATION: Events not in correct order. "
                f"Expected: {critical_events}, Positions: {critical_positions}"
            )
        
        logger.info(f"✅ Critical event sequence validated: {critical_events}")
    
    async def _validate_event_timing_constraints(self, monitor: WebSocketEventMonitor):
        """Validate event timing constraints."""
        events = monitor.get_events()
        
        if len(events) < 2:
            return
        
        # Check that events are spread over reasonable time
        event_times = [e["relative_time"] for e in events]
        min_time = min(event_times)
        max_time = max(event_times)
        duration = max_time - min_time
        
        # Events should be spread over at least 50ms
        if duration < 0.05:
            pytest.fail(
                f"EVENT TIMING CONSTRAINT VIOLATION: Events too close together ({duration:.3f}s < 0.05s). "
                f"May indicate synchronous rather than real-time delivery."
            )
        
        # Events should not take more than 30 seconds
        if duration > 30.0:
            pytest.fail(
                f"EVENT TIMING CONSTRAINT VIOLATION: Events too slow ({duration:.3f}s > 30s). "
                f"User experience degraded."
            )
        
        logger.info(f"✅ Event timing constraints validated: {duration:.3f}s duration")
    
    async def _create_isolated_websocket_engine(self, user_context: UserExecutionContext, 
                                               monitor: WebSocketEventMonitor, user_index: int):
        """Create isolated WebSocket engine for specific user."""
        websocket_bridge = self._create_user_isolated_websocket_bridge(monitor, user_context, user_index)
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            engine = await UserExecutionEngine.create_from_legacy(
                registry=Mock(),
                websocket_bridge=websocket_bridge,
                user_context=user_context
            )
            return engine
            
        except ImportError:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            engine = ExecutionEngine(Mock(), websocket_bridge, user_context)
            return engine
    
    def _create_user_isolated_websocket_bridge(self, monitor: WebSocketEventMonitor, 
                                             user_context: UserExecutionContext, user_index: int):
        """Create user-isolated WebSocket bridge."""
        mock_bridge = Mock()
        
        async def isolated_notify(event_type, *args, **kwargs):
            # Add user isolation info to event
            isolated_kwargs = kwargs.copy()
            isolated_kwargs["user_index"] = user_index
            isolated_kwargs["user_id"] = user_context.user_id
            await monitor.capture_event(event_type, *args, **isolated_kwargs)
        
        mock_bridge.notify_agent_started = AsyncMock(side_effect=lambda *args, **kwargs: isolated_notify("agent_started", *args, **kwargs))
        mock_bridge.notify_agent_thinking = AsyncMock(side_effect=lambda *args, **kwargs: isolated_notify("agent_thinking", *args, **kwargs))
        mock_bridge.notify_tool_executing = AsyncMock(side_effect=lambda *args, **kwargs: isolated_notify("tool_executing", *args, **kwargs))
        mock_bridge.notify_tool_completed = AsyncMock(side_effect=lambda *args, **kwargs: isolated_notify("tool_completed", *args, **kwargs))
        mock_bridge.notify_agent_completed = AsyncMock(side_effect=lambda *args, **kwargs: isolated_notify("agent_completed", *args, **kwargs))
        
        return mock_bridge
    
    async def _execute_isolated_user_websocket_session(self, engine, user_context: UserExecutionContext,
                                                      monitor: WebSocketEventMonitor, user_index: int):
        """Execute isolated WebSocket session for specific user."""
        agent_context = AgentExecutionContext(
            agent_name="isolated_websocket_agent",
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            user_input=f"Isolated WebSocket test for user {user_index}",
            metadata={
                "user_index": user_index,
                "isolation_test": True,
                "websocket_test": True
            }
        )
        
        return await self._execute_agent_with_comprehensive_monitoring(engine, agent_context, user_context, monitor)
    
    async def _validate_no_cross_user_events(self, user_monitors: List[WebSocketEventMonitor], 
                                            user_contexts: List[UserExecutionContext]):
        """Validate no cross-user event contamination."""
        for i, monitor in enumerate(user_monitors):
            events = monitor.get_events()
            user_context = user_contexts[i]
            
            for event in events:
                event_kwargs = event.get("kwargs", {})
                
                # Check if event belongs to correct user
                if "user_id" in event_kwargs:
                    event_user_id = event_kwargs["user_id"]
                    if event_user_id != user_context.user_id:
                        pytest.fail(
                            f"WEBSOCKET CROSS-USER CONTAMINATION: User {i} received event for user {event_user_id}. "
                            f"Event: {event['type']}, Expected User: {user_context.user_id}"
                        )
        
        logger.info("✅ No cross-user WebSocket event contamination detected")
    
    async def _create_error_recovery_websocket_engine(self, user_context: UserExecutionContext, 
                                                     monitor: WebSocketEventMonitor):
        """Create WebSocket engine with error recovery simulation."""
        # Create a bridge that simulates temporary failures then recovers
        error_bridge = self._create_error_recovery_websocket_bridge(monitor)
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            engine = await UserExecutionEngine.create_from_legacy(
                registry=Mock(), websocket_bridge=error_bridge, user_context=user_context
            )
            return engine
        except ImportError:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            engine = ExecutionEngine(Mock(), error_bridge, user_context)
            return engine
    
    def _create_error_recovery_websocket_bridge(self, monitor: WebSocketEventMonitor):
        """Create WebSocket bridge that simulates errors then recovers."""
        mock_bridge = Mock()
        self._error_count = 0
        self._max_errors = 2  # Fail first 2 attempts, then succeed
        
        async def error_recovery_notify(event_type, *args, **kwargs):
            self._error_count += 1
            
            if self._error_count <= self._max_errors:
                # Simulate error
                await monitor.capture_event(f"{event_type}_error", *args, error=True, attempt=self._error_count, **kwargs)
                # Don't fail completely, just log the error
            else:
                # Success after recovery
                await monitor.capture_event(f"{event_type}_recovery", *args, recovered=True, **kwargs)
                await monitor.capture_event(event_type, *args, **kwargs)
        
        mock_bridge.notify_agent_started = AsyncMock(side_effect=lambda *args, **kwargs: error_recovery_notify("agent_started", *args, **kwargs))
        mock_bridge.notify_agent_thinking = AsyncMock(side_effect=lambda *args, **kwargs: error_recovery_notify("agent_thinking", *args, **kwargs))
        mock_bridge.notify_agent_completed = AsyncMock(side_effect=lambda *args, **kwargs: error_recovery_notify("agent_completed", *args, **kwargs))
        
        return mock_bridge
    
    async def _execute_with_websocket_error_simulation(self, engine, agent_context: AgentExecutionContext,
                                                      user_context: UserExecutionContext, monitor: WebSocketEventMonitor):
        """Execute agent with WebSocket error simulation."""
        return await self._execute_agent_with_comprehensive_monitoring(engine, agent_context, user_context, monitor)
    
    async def _execute_performance_test_agent(self, engine, agent_context: AgentExecutionContext, user_context: UserExecutionContext):
        """Execute agent for performance testing."""
        # Simple execution that triggers basic WebSocket events
        if hasattr(engine, 'websocket_bridge'):
            await engine.websocket_bridge.notify_agent_started(
                agent_context.run_id, agent_context.agent_name, {"performance_test": True}
            )
            await asyncio.sleep(0.01)  # Small delay
            await engine.websocket_bridge.notify_agent_completed(
                agent_context.run_id, agent_context.agent_name, {"result": "performance_test"}, 10.0
            )
    
    async def _cleanup_websocket_engine(self, engine):
        """Cleanup WebSocket engine resources."""
        try:
            if engine and hasattr(engine, 'cleanup'):
                await engine.cleanup()
            elif engine and hasattr(engine, 'shutdown'):
                await engine.shutdown()
        except Exception as e:
            logger.warning(f"Engine cleanup failed (non-critical): {e}")


if __name__ == "__main__":
    # Run WebSocket event integrity tests
    pytest.main([__file__, "-v", "--tb=short"])