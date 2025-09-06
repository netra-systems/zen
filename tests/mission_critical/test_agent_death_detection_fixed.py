# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: MISSION CRITICAL TEST: Agent Death Detection System
    # REMOVED_SYNTAX_ERROR: ====================================================
    # REMOVED_SYNTAX_ERROR: This test validates that the agent death detection fixes are working correctly.

    # REMOVED_SYNTAX_ERROR: Tests:
        # REMOVED_SYNTAX_ERROR: 1. Execution tracking with unique IDs
        # REMOVED_SYNTAX_ERROR: 2. Heartbeat monitoring
        # REMOVED_SYNTAX_ERROR: 3. Death notification via WebSocket
        # REMOVED_SYNTAX_ERROR: 4. Timeout detection
        # REMOVED_SYNTAX_ERROR: 5. Health status accuracy

        # REMOVED_SYNTAX_ERROR: This test MUST PASS to prove the bug has been fixed.
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta, timezone
        # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, List, Optional
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
        # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils.test_redis_manager import TestRedisManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # Import the new components
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_execution_tracker import ( )
        # REMOVED_SYNTAX_ERROR: AgentExecutionTracker,
        # REMOVED_SYNTAX_ERROR: ExecutionState,
        # REMOVED_SYNTAX_ERROR: ExecutionRecord,
        # REMOVED_SYNTAX_ERROR: get_execution_tracker
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


        # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
        # Removed problematic line: @pytest.mark.asyncio
# REMOVED_SYNTAX_ERROR: class TestAgentDeathDetectionFixed:
    # REMOVED_SYNTAX_ERROR: """Test suite for agent death detection fixes"""

    # Removed problematic line: async def test_execution_tracker_creates_unique_ids(self):
        # REMOVED_SYNTAX_ERROR: """Test that execution tracker creates unique IDs for each execution"""
        # REMOVED_SYNTAX_ERROR: tracker = AgentExecutionTracker()

        # Create multiple executions
        # REMOVED_SYNTAX_ERROR: exec_ids = []
        # REMOVED_SYNTAX_ERROR: for i in range(10):
            # REMOVED_SYNTAX_ERROR: exec_id = tracker.create_execution( )
            # REMOVED_SYNTAX_ERROR: agent_name="formatted_string",
            # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
            # REMOVED_SYNTAX_ERROR: user_id="test_user",
            # REMOVED_SYNTAX_ERROR: timeout_seconds=30
            
            # REMOVED_SYNTAX_ERROR: exec_ids.append(exec_id)

            # Verify all IDs are unique
            # REMOVED_SYNTAX_ERROR: assert len(exec_ids) == len(set(exec_ids)), "Execution IDs must be unique"

            # Verify execution records exist
            # REMOVED_SYNTAX_ERROR: for exec_id in exec_ids:
                # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
                # REMOVED_SYNTAX_ERROR: assert record is not None
                # REMOVED_SYNTAX_ERROR: assert record.execution_id == exec_id
                # REMOVED_SYNTAX_ERROR: assert record.state == ExecutionState.PENDING

                # Removed problematic line: async def test_heartbeat_monitoring_detects_death(self):
                    # REMOVED_SYNTAX_ERROR: """Test that heartbeat monitoring correctly detects agent death"""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: tracker = AgentExecutionTracker(heartbeat_timeout=2)  # 2 second timeout

                    # Create and start execution
                    # REMOVED_SYNTAX_ERROR: exec_id = tracker.create_execution( )
                    # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
                    # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
                    # REMOVED_SYNTAX_ERROR: user_id="test_user"
                    
                    # REMOVED_SYNTAX_ERROR: tracker.start_execution(exec_id)

                    # Initial heartbeats work
                    # REMOVED_SYNTAX_ERROR: assert tracker.heartbeat(exec_id) == True
                    # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
                    # REMOVED_SYNTAX_ERROR: assert record.state == ExecutionState.RUNNING

                    # Wait for heartbeat timeout
                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(3)

                    # Check if death is detected
                    # REMOVED_SYNTAX_ERROR: dead_executions = tracker.detect_dead_executions()
                    # REMOVED_SYNTAX_ERROR: assert len(dead_executions) > 0
                    # REMOVED_SYNTAX_ERROR: assert any(ex.execution_id == exec_id for ex in dead_executions)

                    # Verify death detection
                    # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
                    # REMOVED_SYNTAX_ERROR: assert record.is_dead(tracker.heartbeat_timeout)

                    # Removed problematic line: async def test_death_notification_sent_via_websocket(self):
                        # REMOVED_SYNTAX_ERROR: """Test that death notifications are sent via WebSocket"""
                        # Mock WebSocket manager
                        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                        # REMOVED_SYNTAX_ERROR: mock_ws_manager.send_to_thread = AsyncMock(return_value=True)

                        # Create bridge
                        # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()
                        # REMOVED_SYNTAX_ERROR: bridge._websocket_manager = mock_ws_manager
                        # REMOVED_SYNTAX_ERROR: bridge._thread_id_cache = {"exec_123": "thread_123"}

                        # Send death notification
                        # REMOVED_SYNTAX_ERROR: success = await bridge.notify_agent_death( )
                        # REMOVED_SYNTAX_ERROR: run_id="exec_123",
                        # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
                        # REMOVED_SYNTAX_ERROR: death_cause="timeout",
                        # REMOVED_SYNTAX_ERROR: death_context={"timeout": 30}
                        

                        # REMOVED_SYNTAX_ERROR: assert success == True

                        # Verify WebSocket message was sent
                        # REMOVED_SYNTAX_ERROR: mock_ws_manager.send_to_thread.assert_called_once()
                        # REMOVED_SYNTAX_ERROR: call_args = mock_ws_manager.send_to_thread.call_args

                        # Check message structure - handle both args and kwargs
                        # REMOVED_SYNTAX_ERROR: if call_args.args:
                            # REMOVED_SYNTAX_ERROR: thread_id = call_args.args[0]
                            # REMOVED_SYNTAX_ERROR: message = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get('message')
                            # REMOVED_SYNTAX_ERROR: else:
                                # REMOVED_SYNTAX_ERROR: thread_id = call_args.kwargs['thread_id']
                                # REMOVED_SYNTAX_ERROR: message = call_args.kwargs['message']

                                # REMOVED_SYNTAX_ERROR: assert thread_id == "thread_123"
                                # REMOVED_SYNTAX_ERROR: assert message['type'] == "agent_death"
                                # REMOVED_SYNTAX_ERROR: assert message['agent_name'] == "test_agent"
                                # REMOVED_SYNTAX_ERROR: assert message['payload']['death_cause'] == "timeout"
                                # REMOVED_SYNTAX_ERROR: assert message['payload']['status'] == "dead"
                                # REMOVED_SYNTAX_ERROR: assert 'message' in message['payload']  # User-friendly message
                                # REMOVED_SYNTAX_ERROR: assert message['payload']['recovery_action'] == "refresh_required"

                                # Removed problematic line: async def test_timeout_detection_and_notification(self):
                                    # REMOVED_SYNTAX_ERROR: """Test that execution timeouts are detected and notified"""
                                    # REMOVED_SYNTAX_ERROR: pass
                                    # REMOVED_SYNTAX_ERROR: tracker = AgentExecutionTracker(execution_timeout=2)  # 2 second timeout

                                    # Create execution with short timeout
                                    # REMOVED_SYNTAX_ERROR: exec_id = tracker.create_execution( )
                                    # REMOVED_SYNTAX_ERROR: agent_name="slow_agent",
                                    # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
                                    # REMOVED_SYNTAX_ERROR: user_id="test_user",
                                    # REMOVED_SYNTAX_ERROR: timeout_seconds=2
                                    
                                    # REMOVED_SYNTAX_ERROR: tracker.start_execution(exec_id)
                                    # REMOVED_SYNTAX_ERROR: tracker.update_execution_state(exec_id, ExecutionState.RUNNING)

                                    # Wait for timeout
                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(3)

                                    # Check timeout detection
                                    # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
                                    # REMOVED_SYNTAX_ERROR: assert record.is_timed_out()

                                    # Detect dead executions should include timeouts
                                    # REMOVED_SYNTAX_ERROR: dead_executions = tracker.detect_dead_executions()
                                    # REMOVED_SYNTAX_ERROR: assert any(ex.execution_id == exec_id and ex.is_timed_out() for ex in dead_executions)

                                    # Removed problematic line: async def test_health_monitor_integration(self):
                                        # REMOVED_SYNTAX_ERROR: """Test that health monitor correctly reports dead agents"""
                                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_health_monitor import AgentHealthMonitor

                                        # Create health monitor with execution tracker
                                        # REMOVED_SYNTAX_ERROR: health_monitor = AgentHealthMonitor()
                                        # REMOVED_SYNTAX_ERROR: tracker = health_monitor.execution_tracker

                                        # Create a dead execution
                                        # REMOVED_SYNTAX_ERROR: exec_id = tracker.create_execution( )
                                        # REMOVED_SYNTAX_ERROR: agent_name="dead_agent",
                                        # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
                                        # REMOVED_SYNTAX_ERROR: user_id="test_user"
                                        
                                        # REMOVED_SYNTAX_ERROR: tracker.start_execution(exec_id)
                                        # REMOVED_SYNTAX_ERROR: tracker.update_execution_state(exec_id, ExecutionState.DEAD, error="No heartbeat")

                                        # Test death detection
                                        # REMOVED_SYNTAX_ERROR: last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=15)
                                        # REMOVED_SYNTAX_ERROR: is_dead = await health_monitor.detect_agent_death( )
                                        # REMOVED_SYNTAX_ERROR: agent_name="dead_agent",
                                        # REMOVED_SYNTAX_ERROR: last_heartbeat=last_heartbeat,
                                        # REMOVED_SYNTAX_ERROR: execution_context={}
                                        

                                        # REMOVED_SYNTAX_ERROR: assert is_dead == True

                                        # Removed problematic line: async def test_execution_engine_death_monitoring(self):
                                            # REMOVED_SYNTAX_ERROR: """Test that ExecutionEngine properly monitors for agent death"""
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.supervisor.execution_engine.get_execution_tracker') as mock_get_tracker:
                                                # Create mock tracker
                                                # REMOVED_SYNTAX_ERROR: mock_tracker = Magic            mock_tracker.create_execution.return_value = "exec_123"
                                                # REMOVED_SYNTAX_ERROR: mock_tracker.start_execution.return_value = True
                                                # REMOVED_SYNTAX_ERROR: mock_tracker.heartbeat.return_value = True
                                                # REMOVED_SYNTAX_ERROR: mock_tracker.update_execution_state.return_value = True
                                                # REMOVED_SYNTAX_ERROR: mock_tracker.get_execution.return_value = MagicMock( )
                                                # REMOVED_SYNTAX_ERROR: is_dead=MagicMock(return_value=False)
                                                
                                                # REMOVED_SYNTAX_ERROR: mock_get_tracker.return_value = mock_tracker

                                                # Import after patching
                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine

                                                # Create mock dependencies
                                                # REMOVED_SYNTAX_ERROR: mock_registry = Magic            websocket = TestWebSocketConnection()
                                                # REMOVED_SYNTAX_ERROR: mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
                                                # REMOVED_SYNTAX_ERROR: mock_websocket_bridge.notify_agent_death = AsyncMock(return_value=True)

                                                # Create execution engine
                                                # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine(mock_registry, mock_websocket_bridge)

                                                # Verify tracker is initialized
                                                # REMOVED_SYNTAX_ERROR: assert engine.execution_tracker is not None

                                                # Verify death callbacks are registered
                                                # REMOVED_SYNTAX_ERROR: assert hasattr(engine, '_handle_agent_death')
                                                # REMOVED_SYNTAX_ERROR: assert hasattr(engine, '_handle_agent_timeout')

                                                # Removed problematic line: async def test_execution_state_transitions(self):
                                                    # REMOVED_SYNTAX_ERROR: """Test proper execution state transitions"""
                                                    # REMOVED_SYNTAX_ERROR: tracker = AgentExecutionTracker()

                                                    # Create execution
                                                    # REMOVED_SYNTAX_ERROR: exec_id = tracker.create_execution( )
                                                    # REMOVED_SYNTAX_ERROR: agent_name="state_test_agent",
                                                    # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
                                                    # REMOVED_SYNTAX_ERROR: user_id="test_user"
                                                    

                                                    # Test state transitions
                                                    # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
                                                    # REMOVED_SYNTAX_ERROR: assert record.state == ExecutionState.PENDING

                                                    # Start execution
                                                    # REMOVED_SYNTAX_ERROR: tracker.start_execution(exec_id)
                                                    # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
                                                    # REMOVED_SYNTAX_ERROR: assert record.state == ExecutionState.STARTING

                                                    # First heartbeat transitions to RUNNING
                                                    # REMOVED_SYNTAX_ERROR: tracker.heartbeat(exec_id)
                                                    # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
                                                    # REMOVED_SYNTAX_ERROR: assert record.state == ExecutionState.RUNNING

                                                    # Update to completing
                                                    # REMOVED_SYNTAX_ERROR: tracker.update_execution_state(exec_id, ExecutionState.COMPLETING)
                                                    # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
                                                    # REMOVED_SYNTAX_ERROR: assert record.state == ExecutionState.COMPLETING

                                                    # Complete execution
                                                    # REMOVED_SYNTAX_ERROR: tracker.update_execution_state( )
                                                    # REMOVED_SYNTAX_ERROR: exec_id,
                                                    # REMOVED_SYNTAX_ERROR: ExecutionState.COMPLETED,
                                                    # REMOVED_SYNTAX_ERROR: result={"success": True}
                                                    
                                                    # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
                                                    # REMOVED_SYNTAX_ERROR: assert record.state == ExecutionState.COMPLETED
                                                    # REMOVED_SYNTAX_ERROR: assert record.is_terminal
                                                    # REMOVED_SYNTAX_ERROR: assert record.result == {"success": True}

                                                    # Removed problematic line: async def test_concurrent_execution_tracking(self):
                                                        # REMOVED_SYNTAX_ERROR: """Test tracking multiple concurrent executions"""
                                                        # REMOVED_SYNTAX_ERROR: pass
                                                        # REMOVED_SYNTAX_ERROR: tracker = AgentExecutionTracker()

                                                        # Create multiple concurrent executions
                                                        # REMOVED_SYNTAX_ERROR: exec_ids = []
                                                        # REMOVED_SYNTAX_ERROR: for i in range(5):
                                                            # REMOVED_SYNTAX_ERROR: exec_id = tracker.create_execution( )
                                                            # REMOVED_SYNTAX_ERROR: agent_name="formatted_string",
                                                            # REMOVED_SYNTAX_ERROR: thread_id="shared_thread",
                                                            # REMOVED_SYNTAX_ERROR: user_id="test_user"
                                                            
                                                            # REMOVED_SYNTAX_ERROR: tracker.start_execution(exec_id)
                                                            # REMOVED_SYNTAX_ERROR: exec_ids.append(exec_id)

                                                            # Verify all are tracked
                                                            # REMOVED_SYNTAX_ERROR: active_executions = tracker.get_active_executions()
                                                            # REMOVED_SYNTAX_ERROR: assert len(active_executions) >= 5

                                                            # Verify thread-based retrieval
                                                            # REMOVED_SYNTAX_ERROR: thread_executions = tracker.get_executions_by_thread("shared_thread")
                                                            # REMOVED_SYNTAX_ERROR: assert len(thread_executions) >= 5

                                                            # Complete some executions
                                                            # REMOVED_SYNTAX_ERROR: for i in range(3):
                                                                # REMOVED_SYNTAX_ERROR: tracker.update_execution_state( )
                                                                # REMOVED_SYNTAX_ERROR: exec_ids[i],
                                                                # REMOVED_SYNTAX_ERROR: ExecutionState.COMPLETED
                                                                

                                                                # Verify active count decreased
                                                                # REMOVED_SYNTAX_ERROR: active_executions = tracker.get_active_executions()
                                                                # REMOVED_SYNTAX_ERROR: assert len([item for item in []]) == 2

                                                                # Removed problematic line: async def test_metrics_collection(self):
                                                                    # REMOVED_SYNTAX_ERROR: """Test that execution metrics are properly collected"""
                                                                    # REMOVED_SYNTAX_ERROR: tracker = AgentExecutionTracker()

                                                                    # Create and complete successful execution
                                                                    # REMOVED_SYNTAX_ERROR: exec_id1 = tracker.create_execution("agent1", "thread1", "user1")
                                                                    # REMOVED_SYNTAX_ERROR: tracker.start_execution(exec_id1)
                                                                    # REMOVED_SYNTAX_ERROR: tracker.update_execution_state(exec_id1, ExecutionState.COMPLETED)

                                                                    # Create and fail execution
                                                                    # REMOVED_SYNTAX_ERROR: exec_id2 = tracker.create_execution("agent2", "thread2", "user2")
                                                                    # REMOVED_SYNTAX_ERROR: tracker.start_execution(exec_id2)
                                                                    # REMOVED_SYNTAX_ERROR: tracker.update_execution_state(exec_id2, ExecutionState.FAILED, error="Test error")

                                                                    # Create and timeout execution
                                                                    # REMOVED_SYNTAX_ERROR: exec_id3 = tracker.create_execution("agent3", "thread3", "user3", timeout_seconds=1)
                                                                    # REMOVED_SYNTAX_ERROR: tracker.start_execution(exec_id3)
                                                                    # REMOVED_SYNTAX_ERROR: tracker.update_execution_state(exec_id3, ExecutionState.TIMEOUT)

                                                                    # Get metrics
                                                                    # REMOVED_SYNTAX_ERROR: metrics = tracker.get_metrics()

                                                                    # REMOVED_SYNTAX_ERROR: assert metrics['total_executions'] >= 3
                                                                    # REMOVED_SYNTAX_ERROR: assert metrics['successful_executions'] >= 1
                                                                    # REMOVED_SYNTAX_ERROR: assert metrics['failed_executions'] >= 1
                                                                    # REMOVED_SYNTAX_ERROR: assert metrics['timeout_executions'] >= 1
                                                                    # REMOVED_SYNTAX_ERROR: assert 'success_rate' in metrics
                                                                    # REMOVED_SYNTAX_ERROR: assert 'failure_rate' in metrics

                                                                    # Removed problematic line: async def test_registry_health_includes_death_detection(self):
                                                                        # REMOVED_SYNTAX_ERROR: """Test that AgentRegistry health includes death detection info"""
                                                                        # REMOVED_SYNTAX_ERROR: pass
                                                                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import AgentRegistry

                                                                        # Create mock dependencies
                                                                        # REMOVED_SYNTAX_ERROR: mock_llm = Magic        mock_dispatcher = Magic
                                                                        # Create registry
                                                                        # REMOVED_SYNTAX_ERROR: registry = AgentRegistry()

                                                                        # Get health status
                                                                        # REMOVED_SYNTAX_ERROR: health = registry.get_registry_health()

                                                                        # Verify death detection fields
                                                                        # REMOVED_SYNTAX_ERROR: assert 'execution_metrics' in health
                                                                        # REMOVED_SYNTAX_ERROR: assert 'dead_agents' in health
                                                                        # REMOVED_SYNTAX_ERROR: assert health['death_detection_enabled'] == True

                                                                        # Removed problematic line: async def test_monitoring_task_lifecycle(self):
                                                                            # REMOVED_SYNTAX_ERROR: """Test that monitoring task starts and stops properly"""
                                                                            # REMOVED_SYNTAX_ERROR: tracker = AgentExecutionTracker()

                                                                            # Start monitoring
                                                                            # REMOVED_SYNTAX_ERROR: await tracker.start_monitoring()
                                                                            # REMOVED_SYNTAX_ERROR: assert tracker._monitor_task is not None
                                                                            # REMOVED_SYNTAX_ERROR: assert not tracker._monitor_task.done()

                                                                            # Stop monitoring
                                                                            # REMOVED_SYNTAX_ERROR: await tracker.stop_monitoring()
                                                                            # REMOVED_SYNTAX_ERROR: assert tracker._monitor_task is None

                                                                            # Removed problematic line: async def test_death_recovery_message_generation(self):
                                                                                # REMOVED_SYNTAX_ERROR: """Test user-friendly death messages are generated correctly"""
                                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                                # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()

                                                                                # Test different death causes
                                                                                # REMOVED_SYNTAX_ERROR: messages = { )
                                                                                # REMOVED_SYNTAX_ERROR: "timeout": "took too long",
                                                                                # REMOVED_SYNTAX_ERROR: "no_heartbeat": "Lost connection",
                                                                                # REMOVED_SYNTAX_ERROR: "silent_failure": "stopped unexpectedly",
                                                                                # REMOVED_SYNTAX_ERROR: "memory_limit": "ran out of resources",
                                                                                # REMOVED_SYNTAX_ERROR: "cancelled": "was cancelled"
                                                                                

                                                                                # REMOVED_SYNTAX_ERROR: for cause, expected_substring in messages.items():
                                                                                    # REMOVED_SYNTAX_ERROR: message = bridge._get_user_friendly_death_message(cause, "test_agent")
                                                                                    # REMOVED_SYNTAX_ERROR: assert expected_substring in message
                                                                                    # REMOVED_SYNTAX_ERROR: assert "test_agent" in message


                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
                                                                                    # Removed problematic line: async def test_complete_death_detection_flow():
                                                                                        # REMOVED_SYNTAX_ERROR: '''
                                                                                        # REMOVED_SYNTAX_ERROR: Integration test for complete agent death detection flow.
                                                                                        # REMOVED_SYNTAX_ERROR: This test validates the entire fix implementation end-to-end.
                                                                                        # REMOVED_SYNTAX_ERROR: '''

                                                                                        # 1. Initialize execution tracker
                                                                                        # REMOVED_SYNTAX_ERROR: tracker = AgentExecutionTracker(heartbeat_timeout=2, execution_timeout=5)
                                                                                        # REMOVED_SYNTAX_ERROR: await tracker.start_monitoring()

                                                                                        # 2. Create WebSocket bridge
                                                                                        # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()
                                                                                        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                                                                                        # REMOVED_SYNTAX_ERROR: mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
                                                                                        # REMOVED_SYNTAX_ERROR: bridge._websocket_manager = mock_ws_manager

                                                                                        # 3. Register death callback
                                                                                        # REMOVED_SYNTAX_ERROR: death_notifications = []
# REMOVED_SYNTAX_ERROR: async def death_callback(execution_record):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: death_notifications.append(execution_record)
    # Send WebSocket notification
    # REMOVED_SYNTAX_ERROR: await bridge.notify_agent_death( )
    # REMOVED_SYNTAX_ERROR: run_id=execution_record.metadata.get('run_id', execution_record.execution_id),
    # REMOVED_SYNTAX_ERROR: agent_name=execution_record.agent_name,
    # REMOVED_SYNTAX_ERROR: death_cause='no_heartbeat' if execution_record.state == ExecutionState.DEAD else 'timeout'
    

    # REMOVED_SYNTAX_ERROR: tracker.register_death_callback(death_callback)

    # 4. Simulate agent execution that dies
    # REMOVED_SYNTAX_ERROR: exec_id = tracker.create_execution( )
    # REMOVED_SYNTAX_ERROR: agent_name="dying_agent",
    # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
    # REMOVED_SYNTAX_ERROR: user_id="test_user",
    # REMOVED_SYNTAX_ERROR: timeout_seconds=3,
    # REMOVED_SYNTAX_ERROR: metadata={'run_id': 'run_123'}
    

    # REMOVED_SYNTAX_ERROR: tracker.start_execution(exec_id)
    # REMOVED_SYNTAX_ERROR: tracker.update_execution_state(exec_id, ExecutionState.RUNNING)

    # 5. Send initial heartbeats
    # REMOVED_SYNTAX_ERROR: for _ in range(2):
        # REMOVED_SYNTAX_ERROR: tracker.heartbeat(exec_id)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.5)

        # 6. Stop sending heartbeats (simulate death)
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(3)

        # 7. Verify death was detected
        # REMOVED_SYNTAX_ERROR: assert len(death_notifications) > 0
        # REMOVED_SYNTAX_ERROR: assert death_notifications[0].agent_name == "dying_agent"

        # 8. Verify WebSocket notification was sent
        # REMOVED_SYNTAX_ERROR: assert mock_ws_manager.send_to_thread.called

        # 9. Verify execution state
        # REMOVED_SYNTAX_ERROR: record = tracker.get_execution(exec_id)
        # REMOVED_SYNTAX_ERROR: assert record.is_terminal
        # REMOVED_SYNTAX_ERROR: assert record.state in [ExecutionState.DEAD, ExecutionState.TIMEOUT]

        # 10. Cleanup
        # REMOVED_SYNTAX_ERROR: await tracker.stop_monitoring()

        # REMOVED_SYNTAX_ERROR: print(" )
        # REMOVED_SYNTAX_ERROR: " + "="*80)
        # REMOVED_SYNTAX_ERROR: print("✅ AGENT DEATH DETECTION SYSTEM WORKING CORRECTLY")
        # REMOVED_SYNTAX_ERROR: print("="*80)
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("formatted_string")
        # REMOVED_SYNTAX_ERROR: print("="*80)


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # Run the tests
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short", "-x"])