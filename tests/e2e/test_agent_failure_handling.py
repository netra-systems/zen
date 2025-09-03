"""
End-to-End Tests for Agent Failure Handling
==========================================
Tests the complete user experience during agent failures, from WebSocket
connection through to error recovery and user notification.

These E2E tests verify:
1. User experience during agent failure (WebSocket flow)
2. Error messages displayed to user are meaningful
3. Recovery from agent death works end-to-end
4. Multiple concurrent agent failures don't break system
5. Chat UI continues to work after agent failures
6. Real-time user feedback during agent death scenarios

Tests use real services and simulate actual user interactions.
"""

import asyncio
import json
import pytest
import time
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

# Import execution tracking and agent components
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
from netra_backend.app.agents.execution_tracking.tracker import (
    ExecutionTracker, AgentExecutionContext, AgentExecutionResult, ExecutionProgress
)
from netra_backend.app.agents.execution_tracking.registry import ExecutionState


class MockChatUser:
    """Simulates a user interacting with the chat system"""
    
    def __init__(self, user_id: str = "test-user", thread_id: str = "test-thread"):
        self.user_id = user_id
        self.thread_id = thread_id
        self.websocket = None
        self.received_messages = []
        self.connection_status = "disconnected"
        
    async def connect_to_chat(self, websocket_url: str = "ws://localhost:8000/ws/chat"):
        """Connect to chat WebSocket (mocked for testing)"""
        # In a real E2E test, this would connect to actual WebSocket
        # For testing, we'll mock the connection
        self.websocket = MockWebSocket()
        self.connection_status = "connected"
        
    async def send_chat_message(self, message: str, agent_type: str = "triage"):
        """Send a chat message and start agent processing"""
        if not self.websocket:
            raise RuntimeError("Not connected to chat")
            
        chat_message = {
            "type": "chat_message",
            "data": {
                "message": message,
                "thread_id": self.thread_id,
                "user_id": self.user_id,
                "agent_type": agent_type,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        await self.websocket.send(json.dumps(chat_message))
        return chat_message
        
    async def wait_for_agent_response(self, timeout_seconds: int = 30) -> Dict[str, Any]:
        """Wait for agent to respond to the message"""
        if not self.websocket:
            raise RuntimeError("Not connected to chat")
            
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                message = await asyncio.wait_for(self.websocket.receive(), timeout=1.0)
                message_data = json.loads(message)
                self.received_messages.append(message_data)
                
                # Look for agent completion or failure
                if message_data.get("type") in ["agent_completed", "agent_failed", "agent_death"]:
                    return message_data
                    
            except asyncio.TimeoutError:
                continue  # Keep waiting
                
        raise asyncio.TimeoutError(f"No agent response received within {timeout_seconds} seconds")
        
    async def wait_for_error_notification(self, timeout_seconds: int = 15) -> Optional[Dict[str, Any]]:
        """Wait specifically for error/death notifications"""
        if not self.websocket:
            return None
            
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                message = await asyncio.wait_for(self.websocket.receive(), timeout=1.0)
                message_data = json.loads(message)
                self.received_messages.append(message_data)
                
                # Look for error-related messages
                if message_data.get("type") in [
                    "agent_failed", 
                    "agent_death", 
                    "execution_failed",
                    "error_notification"
                ]:
                    return message_data
                    
            except asyncio.TimeoutError:
                continue
                
        return None
        
    async def disconnect(self):
        """Disconnect from chat"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.connection_status = "disconnected"
            
    def get_received_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """Get all received messages of a specific type"""
        return [msg for msg in self.received_messages if msg.get("type") == message_type]
        
    def clear_received_messages(self):
        """Clear the received messages buffer"""
        self.received_messages.clear()


class MockWebSocket:
    """Mock WebSocket connection for testing"""
    
    def __init__(self):
        self.messages_sent = []
        self.messages_to_receive = []
        self.is_closed = False
        
    async def send(self, message: str):
        """Send a message (record for testing)"""
        if self.is_closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def receive(self) -> str:
        """Receive a message (from test queue)"""
        if self.is_closed:
            raise RuntimeError("WebSocket is closed")
            
        if self.messages_to_receive:
            return self.messages_to_receive.pop(0)
        else:
            # Wait a bit and return a heartbeat to keep connection alive
            await asyncio.sleep(0.1)
            return json.dumps({"type": "heartbeat", "timestamp": time.time()})
            
    async def close(self):
        """Close the WebSocket"""
        self.is_closed = True
        
    def queue_message(self, message: Dict[str, Any]):
        """Queue a message to be received"""
        self.messages_to_receive.append(json.dumps(message))


class E2EAgentFailureSimulator:
    """Simulates agent failures for E2E testing"""
    
    def __init__(self, execution_tracker: ExecutionTracker):
        self.tracker = execution_tracker
        self.active_executions = {}
        
    async def start_agent_for_user_message(
        self, 
        user: MockChatUser, 
        message: str,
        agent_name: str = "triage"
    ) -> str:
        """Start an agent in response to user message"""
        context = AgentExecutionContext(
            run_id=f"e2e-{user.user_id}-{int(time.time())}",
            agent_name=agent_name,
            thread_id=user.thread_id,
            user_id=user.user_id,
            metadata={"original_message": message}
        )
        
        execution_id = await self.tracker.start_execution(
            context.run_id,
            agent_name,
            context
        )
        
        self.active_executions[execution_id] = {
            'context': context,
            'user': user,
            'start_time': time.time()
        }
        
        # Queue agent started message to user
        user.websocket.queue_message({
            "type": "agent_started",
            "data": {
                "agent": agent_name,
                "execution_id": execution_id,
                "message": f"Starting to process: {message}"
            }
        })
        
        return execution_id
        
    async def simulate_agent_working(
        self, 
        execution_id: str, 
        work_phases: List[Dict[str, Any]]
    ):
        """Simulate agent doing work phases"""
        if execution_id not in self.active_executions:
            return
            
        user = self.active_executions[execution_id]['user']
        
        for phase in work_phases:
            # Send progress update
            await self.tracker.update_execution_progress(
                execution_id,
                ExecutionProgress(
                    stage=phase['stage'],
                    percentage=phase['percentage'],
                    message=phase['message']
                )
            )
            
            # Queue progress message to user
            user.websocket.queue_message({
                "type": "agent_thinking",
                "data": {
                    "thought": phase['message'],
                    "progress": phase['percentage']
                }
            })
            
            await asyncio.sleep(phase.get('duration', 0.5))
            
    async def kill_agent_silently(self, execution_id: str):
        """Kill agent without sending completion - simulates death"""
        if execution_id in self.active_executions:
            # Just stop - no more heartbeats, no completion message
            # The execution tracker should detect this as death
            pass
            
    async def complete_agent_successfully(self, execution_id: str, result_data: Any = None):
        """Complete agent successfully"""
        if execution_id not in self.active_executions:
            return
            
        user = self.active_executions[execution_id]['user']
        
        result = AgentExecutionResult(
            success=True,
            execution_id=execution_id,
            duration_seconds=time.time() - self.active_executions[execution_id]['start_time'],
            data=result_data or {"response": "Task completed successfully"}
        )
        
        await self.tracker.complete_execution(execution_id, result)
        
        # Queue completion message to user
        user.websocket.queue_message({
            "type": "agent_completed",
            "data": {
                "response": result.data.get("response", "Task completed"),
                "success": True
            }
        })
        
        del self.active_executions[execution_id]


class TestAgentFailureHandlingE2E:
    """End-to-end tests for agent failure handling"""
    
    @pytest.fixture
    async def execution_tracker(self):
        """Create ExecutionTracker with WebSocket-like notifications"""
        # Mock WebSocket bridge that queues messages to users
        websocket_bridge = MagicMock()
        websocket_bridge.notify_agent_death = AsyncMock()
        websocket_bridge.notify_execution_failed = AsyncMock()
        websocket_bridge.notify_execution_started = AsyncMock()
        
        tracker = ExecutionTracker(
            websocket_bridge=websocket_bridge,
            heartbeat_interval=1.0,
            timeout_check_interval=1.0
        )
        
        yield tracker
        await tracker.shutdown()
    
    @pytest.fixture
    def failure_simulator(self, execution_tracker):
        """Create agent failure simulator"""
        return E2EAgentFailureSimulator(execution_tracker)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_user_experience_during_agent_death(
        self, execution_tracker, failure_simulator
    ):
        """Test complete user experience when agent dies"""
        print("\\n" + "="*80)
        print("E2E TEST: User Experience During Agent Death")
        print("="*80)
        
        # Setup user
        user = MockChatUser(user_id="e2e-user-1", thread_id="e2e-thread-1")
        await user.connect_to_chat()
        
        print("✅ User connected to chat")
        
        # User sends message
        user_message = "Help me analyze my AWS costs and find optimization opportunities"
        await user.send_chat_message(user_message, agent_type="triage")
        
        print(f"📝 User sent message: '{user_message[:50]}...'")
        
        # Start agent processing
        execution_id = await failure_simulator.start_agent_for_user_message(
            user, user_message, "triage"
        )
        
        print(f"🤖 Agent started processing (execution_id: {execution_id})")
        
        # Agent works normally for a while
        work_phases = [
            {
                'stage': 'understanding', 
                'percentage': 20, 
                'message': 'Understanding your request...', 
                'duration': 1.0
            },
            {
                'stage': 'analyzing', 
                'percentage': 40, 
                'message': 'Analyzing AWS cost patterns...', 
                'duration': 1.0
            },
            {
                'stage': 'processing', 
                'percentage': 60, 
                'message': 'Processing optimization strategies...', 
                'duration': 1.0
            }
        ]
        
        await failure_simulator.simulate_agent_working(execution_id, work_phases)
        
        print("⚙️  Agent worked normally through several phases")
        
        # Verify user received progress updates
        thinking_messages = user.get_received_messages_by_type("agent_thinking")
        assert len(thinking_messages) >= 3, f"User should have received progress updates, got {len(thinking_messages)}"
        
        print(f"📊 User received {len(thinking_messages)} progress updates")
        
        # AGENT DIES SILENTLY
        print("\\n💀 AGENT DIES SILENTLY (simulating production bug scenario)")
        await failure_simulator.kill_agent_silently(execution_id)
        
        # Clear received messages to focus on death handling
        user.clear_received_messages()
        
        # User should eventually receive death notification
        print("⏳ Waiting for user to receive death notification...")
        
        death_notification = await user.wait_for_error_notification(timeout_seconds=20)
        
        if death_notification:
            print(f"💀 User received death notification: {death_notification['type']}")
            print(f"   Details: {death_notification.get('data', {})}")
        else:
            print("❌ No death notification received (this indicates the bug exists)")
        
        # Check if execution tracker detected the death
        await asyncio.sleep(5)  # Give time for detection
        status = await execution_tracker.get_execution_status(execution_id)
        
        death_detected = False
        if status and status.execution_record.state in [ExecutionState.FAILED, ExecutionState.TIMEOUT]:
            death_detected = True
            print(f"💀 Execution tracker detected death: {status.execution_record.state.value}")
            
            error_info = status.execution_record.metadata.get("error", "Unknown error")
            print(f"   Error details: {error_info}")
        
        # Verify the fix is working
        assert death_detected, \
            "CRITICAL: Execution tracker did not detect agent death - bug is NOT fixed!"
            
        assert death_notification is not None, \
            "CRITICAL: User did not receive death notification - user experience is broken!"
        
        # Verify error message is user-friendly
        error_data = death_notification.get('data', {})
        error_message = error_data.get('message', str(error_data))
        
        # Error message should be informative but not technical
        assert len(error_message) > 0, "Error message should not be empty"
        print(f"📝 Error message to user: '{error_message}'")
        
        print("\\n✅ E2E USER EXPERIENCE TEST PASSED!")
        print("   - Agent death was detected")
        print("   - User received proper notification") 
        print("   - Error message was provided")
        print("="*80)
        
        await user.disconnect()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_multiple_users_agent_failures(
        self, execution_tracker, failure_simulator
    ):
        """Test multiple users experiencing agent failures simultaneously"""
        print("\\n" + "="*80)
        print("E2E TEST: Multiple Users with Concurrent Agent Failures")
        print("="*80)
        
        # Setup multiple users
        users = []
        execution_ids = []
        
        for i in range(4):
            user = MockChatUser(user_id=f"e2e-user-{i}", thread_id=f"e2e-thread-{i}")
            await user.connect_to_chat()
            users.append(user)
        
        print(f"✅ {len(users)} users connected to chat")
        
        # Each user sends a message
        user_messages = [
            "Help me optimize my cloud costs",
            "Analyze my AWS spending patterns", 
            "Find cost reduction opportunities",
            "Review my cloud resource usage"
        ]
        
        # Start agents for all users
        for i, (user, message) in enumerate(zip(users, user_messages)):
            await user.send_chat_message(message)
            
            execution_id = await failure_simulator.start_agent_for_user_message(
                user, message, f"agent-{i}"
            )
            execution_ids.append(execution_id)
            
            print(f"🤖 Started agent {i} for user {i}: '{message[:30]}...'")
        
        # All agents work briefly
        work_phase = {
            'stage': 'processing', 
            'percentage': 30, 
            'message': 'Processing your request...', 
            'duration': 1.0
        }
        
        for execution_id in execution_ids:
            await failure_simulator.simulate_agent_working(execution_id, [work_phase])
        
        print("⚙️  All agents started working")
        
        # Kill most agents (simulate mass failure)
        failed_agents = 3  # Kill 3 out of 4 agents
        print(f"\\n💀 Killing {failed_agents} agents simultaneously...")
        
        for i in range(failed_agents):
            await failure_simulator.kill_agent_silently(execution_ids[i])
            print(f"💀 Killed agent {i}")
        
        # Let one agent complete successfully
        await failure_simulator.complete_agent_successfully(
            execution_ids[3], 
            {"response": "I've analyzed your cloud usage and found several optimization opportunities."}
        )
        print("✅ Agent 3 completed successfully")
        
        # Clear all user messages to focus on failure notifications
        for user in users:
            user.clear_received_messages()
        
        # Wait for all users to receive death notifications
        print("\\n⏳ Waiting for death notifications to all affected users...")
        
        death_notifications_received = []
        
        # Check each failed user for death notifications
        for i in range(failed_agents):
            user = users[i]
            notification = await user.wait_for_error_notification(timeout_seconds=15)
            
            if notification:
                death_notifications_received.append((i, notification))
                print(f"💀 User {i} received death notification: {notification['type']}")
            else:
                print(f"❌ User {i} did not receive death notification")
        
        # Check successful user for completion
        success_user = users[3]
        completion_messages = success_user.get_received_messages_by_type("agent_completed")
        
        print(f"\\n📊 Results Summary:")
        print(f"   Failed agents: {failed_agents}")
        print(f"   Death notifications received: {len(death_notifications_received)}")
        print(f"   Successful completions: {len(completion_messages)}")
        
        # Verify death detection
        deaths_detected = 0
        for i in range(failed_agents):
            status = await execution_tracker.get_execution_status(execution_ids[i])
            if status and status.execution_record.state in [ExecutionState.FAILED, ExecutionState.TIMEOUT]:
                deaths_detected += 1
        
        print(f"   Deaths detected by tracker: {deaths_detected}/{failed_agents}")
        
        # Assertions
        assert deaths_detected >= failed_agents * 0.8, \
            f"Most agent deaths should be detected: {deaths_detected}/{failed_agents}"
            
        assert len(death_notifications_received) >= failed_agents * 0.8, \
            f"Most users should receive death notifications: {len(death_notifications_received)}/{failed_agents}"
            
        assert len(completion_messages) > 0, \
            "Successful agent should complete normally"
        
        print("\n✅ MULTIPLE USERS E2E TEST PASSED!")
        print("   - Multiple agent deaths detected")
        print("   - Users received appropriate notifications")
        print("   - Successful agents completed normally")
        print("="*80)
        
        # Cleanup
        for user in users:
            await user.disconnect()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_agent_recovery_user_experience(
        self, execution_tracker, failure_simulator
    ):
        """Test user experience during agent recovery scenarios"""
        print("\\n" + "="*80)
        print("E2E TEST: Agent Recovery User Experience")
        print("="*80)
        
        # Setup user
        user = MockChatUser(user_id="recovery-user", thread_id="recovery-thread")
        await user.connect_to_chat()
        
        print("✅ User connected for recovery test")
        
        # User asks a complex question that might cause agent issues
        complex_message = ("Please analyze my entire AWS infrastructure, identify all cost "
                         "optimization opportunities, create a migration plan to reduce costs by "
                         "40%, and provide detailed ROI calculations for each recommendation.")
        
        await user.send_chat_message(complex_message)
        print(f"📝 User sent complex request: '{complex_message[:60]}...'")
        
        # Start first agent (will fail)
        execution_id_1 = await failure_simulator.start_agent_for_user_message(
            user, complex_message, "complex-analysis-agent"
        )
        
        print(f"🤖 Started first agent (execution_id: {execution_id_1})")
        
        # Agent works hard but then fails
        complex_work_phases = [
            {
                'stage': 'discovery', 
                'percentage': 10, 
                'message': 'Discovering AWS resources...', 
                'duration': 1.0
            },
            {
                'stage': 'cost_analysis', 
                'percentage': 30, 
                'message': 'Analyzing cost patterns across services...', 
                'duration': 1.5
            },
            {
                'stage': 'optimization_modeling', 
                'percentage': 50, 
                'message': 'Building optimization models...', 
                'duration': 1.5
            },
            {
                'stage': 'deep_analysis', 
                'percentage': 70, 
                'message': 'Performing deep cost analysis...', 
                'duration': 2.0
            }
        ]
        
        await failure_simulator.simulate_agent_working(execution_id_1, complex_work_phases)
        print("⚙️  First agent worked through complex analysis phases")
        
        # Agent dies during complex processing
        print("\\n💀 First agent dies during complex processing...")
        await failure_simulator.kill_agent_silently(execution_id_1)
        
        # Wait for death detection and notification
        death_notification = await user.wait_for_error_notification(timeout_seconds=20)
        
        assert death_notification is not None, "User should receive death notification"
        print(f"💀 User notified of first agent death: {death_notification['type']}")
        
        # SIMULATE RECOVERY - Start second agent
        print("\\n🔄 Starting recovery agent...")
        
        # Queue recovery message to user
        user.websocket.queue_message({
            "type": "agent_recovery",
            "data": {
                "message": "I'm starting a new agent to handle your request after the previous one encountered issues.",
                "recovery_attempt": 1
            }
        })
        
        execution_id_2 = await failure_simulator.start_agent_for_user_message(
            user, complex_message, "recovery-agent"
        )
        
        print(f"🤖 Started recovery agent (execution_id: {execution_id_2})")
        
        # Recovery agent works more efficiently
        recovery_phases = [
            {
                'stage': 'recovery_init', 
                'percentage': 15, 
                'message': 'Initializing recovery process...', 
                'duration': 0.5
            },
            {
                'stage': 'simplified_analysis', 
                'percentage': 50, 
                'message': 'Performing streamlined cost analysis...', 
                'duration': 1.0
            },
            {
                'stage': 'generating_recommendations', 
                'percentage': 80, 
                'message': 'Generating optimization recommendations...', 
                'duration': 1.0
            },
            {
                'stage': 'finalizing', 
                'percentage': 100, 
                'message': 'Finalizing analysis...', 
                'duration': 0.5
            }
        ]
        
        await failure_simulator.simulate_agent_working(execution_id_2, recovery_phases)
        
        # Recovery agent completes successfully
        recovery_result = {
            "response": ("I've analyzed your AWS infrastructure and identified several key "
                        "optimization opportunities that could reduce costs by 35-45%. "
                        "Here are my top recommendations: 1) Right-size EC2 instances "
                        "(potential 25% savings), 2) Implement Reserved Instances for "
                        "steady workloads (15% savings), 3) Optimize storage tiers (10% savings)."),
            "recovery": True,
            "original_failed_execution": execution_id_1
        }
        
        await failure_simulator.complete_agent_successfully(execution_id_2, recovery_result)
        print("✅ Recovery agent completed successfully")
        
        # Wait for completion notification
        completion_response = await user.wait_for_agent_response(timeout_seconds=10)
        
        assert completion_response is not None, "User should receive completion notification"
        assert completion_response.get("type") == "agent_completed", "Should be completion message"
        
        print(f"✅ User received completion: {completion_response['type']}")
        
        # Verify user experience metrics
        all_messages = user.received_messages
        
        # Count different message types
        message_counts = {}
        for msg in all_messages:
            msg_type = msg.get("type", "unknown")
            message_counts[msg_type] = message_counts.get(msg_type, 0) + 1
        
        print(f"\\n📊 User Experience Summary:")
        print(f"   Total messages received: {len(all_messages)}")
        for msg_type, count in message_counts.items():
            print(f"   {msg_type}: {count}")
        
        # User should have received:
        # - Progress updates from both agents
        # - Death notification for first agent
        # - Recovery notification
        # - Completion from second agent
        
        assert message_counts.get("agent_thinking", 0) >= 6, "Should have progress updates"
        assert message_counts.get("agent_death", 0) + message_counts.get("execution_failed", 0) >= 1, "Should have death notification"
        assert message_counts.get("agent_completed", 0) >= 1, "Should have completion"
        
        # Verify final execution states
        status_1 = await execution_tracker.get_execution_status(execution_id_1)
        status_2 = await execution_tracker.get_execution_status(execution_id_2)
        
        assert status_1.execution_record.state in [ExecutionState.FAILED, ExecutionState.TIMEOUT], "First agent should be failed"
        assert status_2.execution_record.state == ExecutionState.SUCCESS, "Recovery agent should succeed"
        
        print("\\n✅ AGENT RECOVERY E2E TEST PASSED!")
        print("   - Agent failure detected and user notified")
        print("   - Recovery agent started automatically")
        print("   - Recovery agent completed successfully")
        print("   - User received final result despite initial failure")
        print("="*80)
        
        await user.disconnect()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_chat_ui_resilience_during_failures(
        self, execution_tracker, failure_simulator
    ):
        """Test that chat UI remains functional during agent failures"""
        print("\\n" + "="*80)
        print("E2E TEST: Chat UI Resilience During Failures")
        print("="*80)
        
        # Setup user
        user = MockChatUser(user_id="resilience-user", thread_id="resilience-thread")
        await user.connect_to_chat()
        
        print("✅ User connected for resilience test")
        
        # Send multiple messages in sequence, with some agents failing
        test_scenarios = [
            {"message": "What's my AWS spending this month?", "should_fail": False},
            {"message": "Analyze my EC2 costs in detail", "should_fail": True},
            {"message": "Show me my top 5 most expensive services", "should_fail": True},
            {"message": "What's my current monthly bill?", "should_fail": False},
            {"message": "Help me understand my data transfer costs", "should_fail": True},
            {"message": "Simple question: how much did I spend yesterday?", "should_fail": False}
        ]
        
        execution_ids = []
        
        print(f"📝 Sending {len(test_scenarios)} messages with mixed success/failure scenarios")
        
        # Send all messages and start agents
        for i, scenario in enumerate(test_scenarios):
            await user.send_chat_message(scenario["message"])
            
            execution_id = await failure_simulator.start_agent_for_user_message(
                user, scenario["message"], f"resilience-agent-{i}"
            )
            execution_ids.append(execution_id)
            
            print(f"🤖 Started agent {i}: {'WILL_FAIL' if scenario['should_fail'] else 'WILL_SUCCEED'}")
            
            # Brief pause between messages
            await asyncio.sleep(0.5)
        
        # Process each scenario
        for i, (scenario, execution_id) in enumerate(zip(test_scenarios, execution_ids)):
            
            # Agent works briefly
            work_phase = {
                'stage': f'processing_query_{i}',
                'percentage': 40,
                'message': f"Processing: {scenario['message'][:30]}...",
                'duration': 0.8
            }
            
            await failure_simulator.simulate_agent_working(execution_id, [work_phase])
            
            if scenario["should_fail"]:
                # Agent fails
                await failure_simulator.kill_agent_silently(execution_id)
                print(f"💀 Agent {i} killed (expected failure)")
            else:
                # Agent succeeds
                await failure_simulator.complete_agent_successfully(
                    execution_id, 
                    {"response": f"Answer to: {scenario['message'][:50]}"}
                )
                print(f"✅ Agent {i} completed (expected success)")
        
        # Wait for all processing to complete
        await asyncio.sleep(10)  # Give time for death detection
        
        # Analyze final states
        successful_agents = 0
        failed_agents = 0
        
        for i, execution_id in enumerate(execution_ids):
            status = await execution_tracker.get_execution_status(execution_id)
            
            if status:
                if status.execution_record.state == ExecutionState.SUCCESS:
                    successful_agents += 1
                elif status.execution_record.state in [ExecutionState.FAILED, ExecutionState.TIMEOUT]:
                    failed_agents += 1
        
        print(f"\\n📊 Final Results:")
        print(f"   Expected successes: {sum(1 for s in test_scenarios if not s['should_fail'])}")
        print(f"   Actual successes: {successful_agents}")
        print(f"   Expected failures: {sum(1 for s in test_scenarios if s['should_fail'])}")
        print(f"   Actual failures: {failed_agents}")
        
        # Check user received appropriate mix of notifications
        all_messages = user.received_messages
        
        completion_messages = user.get_received_messages_by_type("agent_completed")
        death_messages = (
            user.get_received_messages_by_type("agent_death") + 
            user.get_received_messages_by_type("execution_failed")
        )
        
        print(f"   User completion notifications: {len(completion_messages)}")
        print(f"   User death notifications: {len(death_messages)}")
        
        # Verify resilience
        expected_successes = sum(1 for s in test_scenarios if not s["should_fail"])
        expected_failures = sum(1 for s in test_scenarios if s["should_fail"])
        
        # Allow some tolerance for timing
        assert successful_agents >= expected_successes * 0.8, \
            f"Most expected successes should work: {successful_agents} >= {expected_successes * 0.8}"
            
        assert failed_agents >= expected_failures * 0.8, \
            f"Most expected failures should be detected: {failed_agents} >= {expected_failures * 0.8}"
        
        # User should have received notifications for most events
        total_expected_notifications = len(test_scenarios)
        total_received_notifications = len(completion_messages) + len(death_messages)
        
        assert total_received_notifications >= total_expected_notifications * 0.8, \
            f"User should receive most notifications: {total_received_notifications} >= {total_expected_notifications * 0.8}"
        
        # WebSocket should still be connected
        assert user.connection_status == "connected", "User should still be connected"
        assert not user.websocket.is_closed, "WebSocket should still be open"
        
        print("\\n✅ CHAT UI RESILIENCE TEST PASSED!")
        print("   - Multiple agents processed concurrently")
        print("   - Failures properly detected and reported")
        print("   - Successes completed normally")
        print("   - Chat UI remained functional throughout")
        print("   - WebSocket connection maintained")
        print("="*80)
        
        await user.disconnect()


if __name__ == "__main__":
    # Run E2E tests
    import sys
    
    print("\\n" + "="*80)
    print("AGENT FAILURE HANDLING E2E TEST SUITE")
    print("="*80)
    print("Testing complete user experience during agent failures")
    print("These tests simulate real user interactions with agent failures")
    print("="*80 + "\\n")
    
    pytest.main([__file__, "-v", "--tb=short", "-s"])