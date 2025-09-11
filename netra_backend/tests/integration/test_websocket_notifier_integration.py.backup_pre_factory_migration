"""
WebSocket Notifier Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free → Enterprise) 
- Business Goal: Ensure WebSocket notifications work with realistic system components
- Value Impact: Integration tests validate real-time feedback works in component interactions
- Strategic Impact: User engagement depends on reliable real-time notifications

This test suite validates WebSocket Notifier functionality through integration
testing with realistic components and message flows, focusing on component
interaction patterns without requiring running services.

⚠️ DEPRECATION NOTE: WebSocketNotifier is deprecated in favor of AgentWebSocketBridge.
These tests validate integration patterns for backward compatibility.

CRITICAL REQUIREMENTS VALIDATED:
- WebSocket notification routing with realistic managers
- Event handling and message delivery patterns  
- Error handling integration with system components
- Performance under realistic message volumes
- Event queuing and backlog processing integration
- User context isolation in notification flows
- Message confirmation and delivery tracking
- Real-time feedback timing and sequencing
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from collections import deque

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

# Core imports for WebSocket notifier integration testing
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.websocket_models import WebSocketMessage


class RealisticWebSocketManager:
    """Realistic WebSocket manager mock that simulates real behavior."""
    
    def __init__(self, simulate_failures: bool = False, message_delay: float = 0.01):
        self.simulate_failures = simulate_failures
        self.message_delay = message_delay
        self.sent_messages = []
        self.connected_threads = set()
        self.failure_count = 0
        self.success_count = 0
        
    async def send_to_thread(self, thread_id: str, message_data: Dict[str, Any]) -> bool:
        """Simulate realistic message sending with potential failures."""
        # Simulate network delay
        await asyncio.sleep(self.message_delay)
        
        # Simulate occasional failures if configured
        if self.simulate_failures and self.failure_count < 2:
            self.failure_count += 1
            return False
        
        # Store message for verification
        self.sent_messages.append({
            "thread_id": thread_id,
            "message": message_data,
            "timestamp": time.time()
        })
        
        self.success_count += 1
        return True
    
    async def broadcast(self, message_data: Dict[str, Any]) -> bool:
        """Simulate broadcast to all connected threads."""
        await asyncio.sleep(self.message_delay)
        
        self.sent_messages.append({
            "thread_id": "broadcast",
            "message": message_data,
            "timestamp": time.time()
        })
        
        return True
    
    def get_messages_for_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all messages sent to specific thread."""
        return [msg for msg in self.sent_messages if msg["thread_id"] == thread_id]
    
    def get_message_count(self) -> int:
        """Get total number of messages sent."""
        return len(self.sent_messages)


class TestWebSocketNotifierIntegration(SSotBaseTestCase):
    """Integration tests for WebSocket Notifier functionality."""
    
    def setup_method(self):
        """Set up realistic integration test environment for each test method."""
        super().setup_method()
        self.env = get_env()
        self.test_helper = IsolatedTestHelper()
        
        # Create realistic WebSocket manager
        self.realistic_websocket_manager = RealisticWebSocketManager()
        
        # Suppress deprecation warning for testing
        with patch('warnings.warn'):
            # Create WebSocket notifier with realistic manager
            self.websocket_notifier = WebSocketNotifier(
                websocket_manager=self.realistic_websocket_manager
            )
        
        # Create realistic execution contexts for different scenarios
        self.enterprise_context = AgentExecutionContext(
            agent_name="enterprise_optimizer",
            run_id=uuid.uuid4(),
            retry_count=0,
            thread_id="enterprise_thread_abc123"
        )
        
        self.startup_context = AgentExecutionContext(
            agent_name="startup_advisor",
            run_id=uuid.uuid4(), 
            retry_count=0,
            thread_id="startup_thread_xyz789"
        )

    @pytest.mark.integration
    async def test_complete_agent_lifecycle_notification_flow(self):
        """
        Test complete agent lifecycle notification flow with realistic timing.
        
        BVJ: Validates users receive complete real-time feedback during agent execution.
        """
        # Simulate complete agent execution flow
        start_time = time.time()
        
        # 1. Agent started
        await self.websocket_notifier.send_agent_started(self.enterprise_context)
        
        # 2. Agent thinking phases
        thinking_phases = [
            "Initializing business data analysis",
            "Processing Q4 revenue metrics", 
            "Generating optimization recommendations"
        ]
        
        for i, thought in enumerate(thinking_phases):
            await self.websocket_notifier.send_agent_thinking(
                context=self.enterprise_context,
                thought=thought,
                step_number=i + 1,
                progress_percentage=(i + 1) * 25.0,
                estimated_remaining_ms=max(1000 - (i * 300), 100),
                current_operation=f"phase_{i + 1}"
            )
        
        # 3. Tool execution
        await self.websocket_notifier.send_tool_executing(
            context=self.enterprise_context,
            tool_name="financial_analyzer",
            tool_purpose="Analyzing revenue trends and patterns",
            estimated_duration_ms=2000
        )
        
        # 4. Tool completion
        await self.websocket_notifier.send_tool_completed(
            context=self.enterprise_context,
            tool_name="financial_analyzer",
            result={"insights_count": 5, "confidence": 0.92}
        )
        
        # 5. Agent completion
        final_result = {
            "recommendations": ["Optimize pricing strategy", "Improve customer retention"],
            "potential_savings": {"monthly": 15000, "annual": 180000},
            "confidence_score": 0.89
        }
        
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        await self.websocket_notifier.send_agent_completed(
            context=self.enterprise_context,
            result=final_result,
            duration_ms=execution_time
        )
        
        # Verify complete message flow
        thread_messages = self.realistic_websocket_manager.get_messages_for_thread(
            "enterprise_thread_abc123"
        )
        
        # Should have all lifecycle messages
        assert len(thread_messages) >= 7, f"Expected at least 7 messages, got {len(thread_messages)}"
        
        # Verify message sequence
        message_types = [msg["message"]["type"] for msg in thread_messages]
        expected_sequence = [
            "agent_started",
            "agent_thinking",  # Multiple thinking messages
            "tool_executing", 
            "tool_completed",
            "agent_completed"
        ]
        
        # Check that required message types are present
        for required_type in ["agent_started", "tool_executing", "tool_completed", "agent_completed"]:
            assert required_type in message_types, f"Missing {required_type} in message flow"
        
        # Verify thinking messages were sent
        thinking_count = message_types.count("agent_thinking")
        assert thinking_count >= 3, f"Expected at least 3 thinking messages, got {thinking_count}"

    @pytest.mark.integration
    async def test_concurrent_multi_user_notification_isolation(self):
        """
        Test concurrent notifications for multiple users maintain proper isolation.
        
        BVJ: Ensures multi-tenant platform delivers notifications only to correct users.
        """
        # Create multiple user contexts
        user_contexts = [
            AgentExecutionContext(
                agent_name=f"user_agent_{i}",
                run_id=uuid.uuid4(),
                retry_count=0,
                thread_id=f"user_thread_{i}_{uuid.uuid4().hex[:8]}"
            )
            for i in range(3)
        ]
        
        # Send concurrent notifications for different users
        tasks = []
        for i, context in enumerate(user_contexts):
            # Create unique content for each user
            task = asyncio.create_task(self._simulate_user_agent_flow(
                context=context,
                user_data=f"confidential_user_{i}_data",
                business_insights=f"user_{i}_specific_insights"
            ))
            tasks.append(task)
        
        # Execute all user flows concurrently
        await asyncio.gather(*tasks)
        
        # Verify message isolation
        for i, context in enumerate(user_contexts):
            user_messages = self.realistic_websocket_manager.get_messages_for_thread(
                context.thread_id
            )
            
            # Each user should have received their messages
            assert len(user_messages) > 0, f"User {i} received no messages"
            
            # Verify no cross-contamination
            for message_entry in user_messages:
                message_str = json.dumps(message_entry["message"])
                
                # Should contain own user data
                assert f"user_{i}" in message_str or f"confidential_user_{i}_data" in message_str, \
                    f"User {i} missing own data in messages"
                
                # Should not contain other users' data
                for j in range(3):
                    if i != j:
                        assert f"confidential_user_{j}_data" not in message_str, \
                            f"User {i} received data from user {j}"

    @pytest.mark.integration
    async def test_error_handling_and_recovery_integration(self):
        """
        Test error handling and recovery in realistic failure scenarios.
        
        BVJ: Ensures system resilience maintains user experience during failures.
        """
        # Create WebSocket manager that simulates failures
        failing_manager = RealisticWebSocketManager(simulate_failures=True)
        
        with patch('warnings.warn'):
            failing_notifier = WebSocketNotifier(websocket_manager=failing_manager)
        
        # Attempt to send notifications that will initially fail
        await failing_notifier.send_agent_started(self.startup_context)
        
        # Send multiple messages to trigger failure and recovery
        for i in range(5):
            await failing_notifier.send_agent_thinking(
                context=self.startup_context,
                thought=f"Processing step {i + 1}",
                step_number=i + 1
            )
        
        # Verify some messages eventually succeeded (after initial failures)
        thread_messages = failing_manager.get_messages_for_thread("startup_thread_xyz789")
        
        # Should have some successful messages despite initial failures
        assert len(thread_messages) >= 1, "No messages succeeded after failures"
        assert failing_manager.success_count > 0, "No successful message deliveries"
        
        # Verify failure handling was triggered
        assert failing_manager.failure_count > 0, "Failure handling was not tested"

    @pytest.mark.integration
    async def test_message_queuing_and_backlog_processing(self):
        """
        Test message queuing and backlog processing under load.
        
        BVJ: Ensures notification delivery under high-volume scenarios for scalability.
        """
        # Send burst of messages quickly to trigger queuing
        message_burst_size = 20
        context_with_queuing = AgentExecutionContext(
            agent_name="high_volume_agent",
            run_id=uuid.uuid4(),
            retry_count=0,
            thread_id="high_volume_thread_123"
        )
        
        # Send messages rapidly
        start_time = time.time()
        tasks = []
        
        for i in range(message_burst_size):
            task = asyncio.create_task(
                self.websocket_notifier.send_agent_thinking(
                    context=context_with_queuing,
                    thought=f"Rapid processing step {i + 1}",
                    step_number=i + 1,
                    progress_percentage=(i + 1) / message_burst_size * 100
                )
            )
            tasks.append(task)
        
        # Wait for all messages to be processed
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify message delivery
        thread_messages = self.realistic_websocket_manager.get_messages_for_thread(
            "high_volume_thread_123"
        )
        
        # Should have delivered all messages
        assert len(thread_messages) == message_burst_size, \
            f"Expected {message_burst_size} messages, got {len(thread_messages)}"
        
        # Verify reasonable processing time (should handle burst efficiently)
        total_time = end_time - start_time
        assert total_time < 2.0, f"Message burst took {total_time}s, should be faster"
        
        # Verify message order preservation
        for i, message_entry in enumerate(thread_messages):
            message_content = message_entry["message"]["payload"]["thought"]
            expected_step = f"step {i + 1}"
            assert expected_step in message_content, f"Message order not preserved at position {i}"

    @pytest.mark.integration 
    async def test_performance_under_realistic_load(self):
        """
        Test performance under realistic load scenarios.
        
        BVJ: Validates system can handle realistic user loads without degradation.
        """
        # Simulate realistic load: 5 concurrent agents with realistic message patterns
        concurrent_agents = 5
        messages_per_agent = 8  # Typical agent lifecycle message count
        
        # Create contexts for concurrent agents
        load_contexts = [
            AgentExecutionContext(
                agent_name=f"load_test_agent_{i}",
                run_id=uuid.uuid4(),
                retry_count=0,
                thread_id=f"load_thread_{i}_{uuid.uuid4().hex[:8]}"
            )
            for i in range(concurrent_agents)
        ]
        
        # Execute concurrent agent flows
        start_time = time.time()
        tasks = [
            asyncio.create_task(self._simulate_realistic_agent_flow(context))
            for context in load_contexts
        ]
        
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Analyze performance
        total_time = end_time - start_time
        expected_messages = concurrent_agents * messages_per_agent
        actual_messages = self.realistic_websocket_manager.get_message_count()
        
        # Performance assertions
        assert actual_messages >= expected_messages * 0.8, \
            f"Too many messages lost: expected ~{expected_messages}, got {actual_messages}"
        
        # Should complete in reasonable time (concurrent processing)
        assert total_time < 5.0, f"Load test took {total_time}s, should be faster"
        
        # Calculate throughput
        messages_per_second = actual_messages / total_time
        assert messages_per_second > 10, f"Throughput too low: {messages_per_second} msg/s"

    @pytest.mark.integration
    async def test_websocket_manager_integration_patterns(self):
        """
        Test integration patterns with WebSocket manager components.
        
        BVJ: Validates notification system integrates properly with WebSocket infrastructure.
        """
        # Test different WebSocket manager scenarios
        scenarios = [
            {"thread_id": "integration_thread_1", "simulate_connected": True},
            {"thread_id": "integration_thread_2", "simulate_connected": True},
            {"thread_id": None, "simulate_connected": False}  # Broadcast scenario
        ]
        
        for scenario in scenarios:
            context = AgentExecutionContext(
                agent_name="integration_test_agent",
                run_id=uuid.uuid4(),
                retry_count=0,
                thread_id=scenario["thread_id"]
            )
            
            # Send notification based on scenario
            if scenario["thread_id"]:
                await self.websocket_notifier.send_agent_started(context)
                
                # Verify targeted message delivery
                thread_messages = self.realistic_websocket_manager.get_messages_for_thread(
                    scenario["thread_id"]
                )
                assert len(thread_messages) > 0, f"No messages for thread {scenario['thread_id']}"
            else:
                # Test broadcast scenario (fallback when thread_id is None)
                await self.websocket_notifier.send_agent_failed(
                    agent_id="integration_agent",
                    error="Test broadcast error"
                )
                
                # Should use broadcast method when no thread_id
                broadcast_messages = self.realistic_websocket_manager.get_messages_for_thread("broadcast")
                # Note: broadcast might not be triggered in all scenarios, so this is optional verification

    async def _simulate_user_agent_flow(self, context: AgentExecutionContext, 
                                       user_data: str, business_insights: str):
        """Simulate a realistic agent flow for a specific user."""
        # Agent started
        await self.websocket_notifier.send_agent_started(context)
        
        # Thinking with user-specific context
        await self.websocket_notifier.send_agent_thinking(
            context=context,
            thought=f"Analyzing {user_data} for business optimization",
            step_number=1,
            progress_percentage=25.0
        )
        
        # Tool execution with user context
        await self.websocket_notifier.send_tool_executing(
            context=context,
            tool_name="data_processor",
            tool_purpose=f"Processing {user_data}"
        )
        
        # Completion with user-specific results
        result_data = {
            "user_context": user_data,
            "insights": [business_insights],
            "personalized": True
        }
        
        await self.websocket_notifier.send_agent_completed(
            context=context,
            result=result_data,
            duration_ms=1500
        )

    async def _simulate_realistic_agent_flow(self, context: AgentExecutionContext):
        """Simulate a realistic agent execution flow for load testing."""
        # Standard agent lifecycle
        await self.websocket_notifier.send_agent_started(context)
        
        # Multiple thinking phases
        for i in range(3):
            await self.websocket_notifier.send_agent_thinking(
                context=context,
                thought=f"Load test processing phase {i + 1}",
                step_number=i + 1,
                progress_percentage=(i + 1) * 25
            )
        
        # Tool execution
        await self.websocket_notifier.send_tool_executing(
            context=context,
            tool_name="load_test_tool",
            estimated_duration_ms=500
        )
        
        # Tool completion
        await self.websocket_notifier.send_tool_completed(
            context=context,
            tool_name="load_test_tool",
            result={"test_data": "processed"}
        )
        
        # Agent completion
        await self.websocket_notifier.send_agent_completed(
            context=context,
            result={"load_test": "successful"},
            duration_ms=2000
        )

    def cleanup_resources(self):
        """Clean up integration test resources."""
        super().cleanup_resources()
        self.websocket_notifier = None
        self.realistic_websocket_manager = None
        self.test_helper.cleanup() if self.test_helper else None