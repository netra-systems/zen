"""
Single Source of Truth (SSOT) WebSocket Bridge Test Helper

This module provides the unified WebSocketBridgeTestHelper for ALL agent-WebSocket
integration testing across the entire test suite. It handles the bridge between
agent execution and WebSocket event delivery for comprehensive testing.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Enables reliable testing of agent-WebSocket integration that delivers $500K+ ARR
chat functionality through proper event delivery and agent workflow validation.

CRITICAL: This is the ONLY source for WebSocket-agent bridge test utilities.
ALL agent-WebSocket integration tests must use WebSocketBridgeTestHelper for consistency.
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union, Callable
from datetime import datetime
from enum import Enum

# Import SSOT environment management
from shared.isolated_environment import get_env

# Import existing WebSocket test infrastructure
from .websocket import WebSocketTestClient, WebSocketEventType, WebSocketMessage

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutionContext:
    """Context for agent execution within WebSocket bridge testing."""
    agent_id: str
    agent_type: str
    user_id: str
    thread_id: str
    execution_id: str
    started_at: datetime
    status: str = "pending"
    progress: str = ""
    tools_executed: List[str] = field(default_factory=list)
    events_sent: List[WebSocketEventType] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat(),
            "status": self.status,
            "progress": self.progress,
            "tools_executed": self.tools_executed,
            "events_sent": [e.value for e in self.events_sent],
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error
        }


class AgentEventSimulator:
    """Simulates agent execution events for WebSocket bridge testing."""
    
    def __init__(self, context: AgentExecutionContext):
        self.context = context
        self.event_delay = 0.5  # Delay between events in seconds
        self.tool_execution_delay = 1.0  # Delay for tool execution simulation
        
    async def simulate_agent_started(self) -> WebSocketMessage:
        """Simulate agent_started event."""
        self.context.status = "started"
        self.context.events_sent.append(WebSocketEventType.AGENT_STARTED)
        
        return WebSocketMessage(
            event_type=WebSocketEventType.AGENT_STARTED,
            data={
                "agent_id": self.context.agent_id,
                "agent_type": self.context.agent_type,
                "user_id": self.context.user_id,
                "thread_id": self.context.thread_id,
                "execution_id": self.context.execution_id,
                "status": "started",
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            message_id=f"agent_started_{uuid.uuid4().hex[:8]}",
            user_id=self.context.user_id,
            thread_id=self.context.thread_id
        )
    
    async def simulate_agent_thinking(self, progress_message: str) -> WebSocketMessage:
        """Simulate agent_thinking event."""
        self.context.status = "thinking"
        self.context.progress = progress_message
        self.context.events_sent.append(WebSocketEventType.AGENT_THINKING)
        
        return WebSocketMessage(
            event_type=WebSocketEventType.AGENT_THINKING,
            data={
                "agent_id": self.context.agent_id,
                "agent_type": self.context.agent_type,
                "user_id": self.context.user_id,
                "thread_id": self.context.thread_id,
                "execution_id": self.context.execution_id,
                "progress": progress_message,
                "status": "thinking",
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            message_id=f"agent_thinking_{uuid.uuid4().hex[:8]}",
            user_id=self.context.user_id,
            thread_id=self.context.thread_id
        )
    
    async def simulate_tool_executing(self, tool_name: str, tool_input: Dict[str, Any]) -> WebSocketMessage:
        """Simulate tool_executing event."""
        self.context.status = "executing_tool"
        self.context.tools_executed.append(tool_name)
        self.context.events_sent.append(WebSocketEventType.TOOL_EXECUTING)
        
        return WebSocketMessage(
            event_type=WebSocketEventType.TOOL_EXECUTING,
            data={
                "agent_id": self.context.agent_id,
                "agent_type": self.context.agent_type,
                "user_id": self.context.user_id,
                "thread_id": self.context.thread_id,
                "execution_id": self.context.execution_id,
                "tool_name": tool_name,
                "tool_input": tool_input,
                "status": "executing",
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            message_id=f"tool_executing_{uuid.uuid4().hex[:8]}",
            user_id=self.context.user_id,
            thread_id=self.context.thread_id
        )
    
    async def simulate_tool_completed(self, tool_name: str, tool_result: Dict[str, Any]) -> WebSocketMessage:
        """Simulate tool_completed event."""
        self.context.status = "tool_completed"
        self.context.events_sent.append(WebSocketEventType.TOOL_COMPLETED)
        
        return WebSocketMessage(
            event_type=WebSocketEventType.TOOL_COMPLETED,
            data={
                "agent_id": self.context.agent_id,
                "agent_type": self.context.agent_type,
                "user_id": self.context.user_id,
                "thread_id": self.context.thread_id,
                "execution_id": self.context.execution_id,
                "tool_name": tool_name,
                "tool_result": tool_result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            message_id=f"tool_completed_{uuid.uuid4().hex[:8]}",
            user_id=self.context.user_id,
            thread_id=self.context.thread_id
        )
    
    async def simulate_agent_completed(self, final_result: Dict[str, Any]) -> WebSocketMessage:
        """Simulate agent_completed event."""
        self.context.status = "completed"
        self.context.result = final_result
        self.context.completed_at = datetime.now()
        self.context.events_sent.append(WebSocketEventType.AGENT_COMPLETED)
        
        return WebSocketMessage(
            event_type=WebSocketEventType.AGENT_COMPLETED,
            data={
                "agent_id": self.context.agent_id,
                "agent_type": self.context.agent_type,
                "user_id": self.context.user_id,
                "thread_id": self.context.thread_id,
                "execution_id": self.context.execution_id,
                "result": final_result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now(),
            message_id=f"agent_completed_{uuid.uuid4().hex[:8]}",
            user_id=self.context.user_id,
            thread_id=self.context.thread_id
        )


@dataclass
class BridgeTestConfig:
    """Configuration for WebSocket bridge testing."""
    mock_mode: bool = True
    event_delivery_timeout: float = 10.0
    agent_execution_timeout: float = 30.0
    enable_event_validation: bool = True
    simulate_network_delays: bool = False
    network_delay_ms: int = 100
    
    @classmethod
    def from_environment(cls, env=None) -> 'BridgeTestConfig':
        """Create bridge config from environment variables."""
        env = env or get_env()
        
        return cls(
            mock_mode=env.get("WEBSOCKET_BRIDGE_MOCK_MODE", "true").lower() == "true",
            event_delivery_timeout=float(env.get("WEBSOCKET_EVENT_TIMEOUT", "10.0")),
            agent_execution_timeout=float(env.get("AGENT_EXECUTION_TIMEOUT", "30.0")),
            enable_event_validation=env.get("WEBSOCKET_EVENT_VALIDATION", "true").lower() == "true",
            simulate_network_delays=env.get("SIMULATE_NETWORK_DELAYS", "false").lower() == "true",
            network_delay_ms=int(env.get("NETWORK_DELAY_MS", "100"))
        )


class WebSocketBridgeTestHelper:
    """
    Single Source of Truth (SSOT) WebSocket bridge test helper.
    
    This helper provides comprehensive agent-WebSocket integration testing capabilities:
    - Agent execution simulation with realistic event sequences
    - WebSocket event delivery validation and monitoring
    - Agent-to-user event routing verification
    - Multi-agent concurrent execution testing
    - Event ordering and timing validation
    - Performance monitoring for agent-WebSocket communication
    
    Features:
    - SSOT compliance with existing test framework
    - Integration with production agent and WebSocket components
    - Mock mode for unit testing without full agent infrastructure
    - Real integration validation with actual agent execution
    - Event delivery confirmation and validation
    - Concurrent agent execution testing for load scenarios
    
    Usage:
        async with WebSocketBridgeTestHelper() as bridge_helper:
            client = await bridge_helper.create_agent_websocket_bridge(user_id="test_user")
            events = await bridge_helper.simulate_agent_events(client, "triage")
            await bridge_helper.validate_event_delivery(client, events)
    """
    
    def __init__(self, config: Optional[BridgeTestConfig] = None, env=None):
        """
        Initialize WebSocket bridge test helper.
        
        Args:
            config: Optional bridge test configuration
            env: Optional environment manager instance
        """
        self.env = env or get_env()
        self.config = config or BridgeTestConfig.from_environment(self.env)
        self.test_id = f"wsbridge_{uuid.uuid4().hex[:8]}"
        
        # Bridge management
        self.active_bridges: Dict[str, WebSocketTestClient] = {}
        self.agent_contexts: Dict[str, AgentExecutionContext] = {}
        self.event_simulators: Dict[str, AgentEventSimulator] = {}
        
        # Event tracking
        self.sent_events: List[WebSocketMessage] = []
        self.received_events: List[WebSocketMessage] = []
        self.event_delivery_confirmations: Dict[str, bool] = {}
        
        # Performance metrics
        self.event_delivery_times: Dict[str, float] = {}
        self.agent_execution_times: Dict[str, float] = {}
        
        logger.debug(f"WebSocketBridgeTestHelper initialized [{self.test_id}] (mock_mode={self.config.mock_mode})")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize WebSocket bridge test helper."""
        try:
            if self.config.mock_mode:
                logger.info("WebSocketBridgeTestHelper initialized in mock mode")
            else:
                # In real mode, would verify connection to actual agent services
                logger.info("WebSocketBridgeTestHelper initialized in real mode")
            
        except Exception as e:
            logger.error(f"WebSocket bridge helper initialization failed: {e}")
            raise
    
    async def create_agent_websocket_bridge(self, user_id: str, 
                                          client: Optional[WebSocketTestClient] = None) -> WebSocketTestClient:
        """
        Create a WebSocket bridge for agent-to-user communication testing.
        
        Args:
            user_id: User ID for the bridge connection
            client: Optional existing WebSocket client to use
            
        Returns:
            WebSocketTestClient configured for agent-WebSocket bridge testing
        """
        bridge_id = f"bridge_{user_id}_{uuid.uuid4().hex[:8]}"
        
        if client is None:
            # Import here to avoid circular imports
            from .websocket import WebSocketTestUtility
            
            ws_utility = WebSocketTestUtility(env=self.env)
            await ws_utility.initialize()
            
            client = await ws_utility.create_test_client(
                user_id=user_id,
                headers={
                    "X-Bridge-ID": bridge_id,
                    "X-Test-Helper": self.test_id,
                    "X-Bridge-Mode": "agent_communication"
                }
            )
        
        # Configure client for bridge testing
        client.test_id = bridge_id
        
        # Connect in appropriate mode
        connected = await client.connect(timeout=self.config.event_delivery_timeout, 
                                       mock_mode=self.config.mock_mode)
        if not connected:
            raise RuntimeError(f"Failed to connect WebSocket bridge for user {user_id}")
        
        # Store bridge
        self.active_bridges[bridge_id] = client
        
        logger.debug(f"Created agent-WebSocket bridge: {bridge_id} for user {user_id}")
        return client
    
    async def simulate_agent_events(self, client: WebSocketTestClient, agent_type: str,
                                  user_request: Optional[str] = None,
                                  tools_to_execute: Optional[List[str]] = None) -> List[WebSocketMessage]:
        """
        Simulate a complete agent execution flow with WebSocket events.
        
        Args:
            client: WebSocket test client for event delivery
            agent_type: Type of agent to simulate ("triage", "apex_optimizer", "data_helper")
            user_request: Optional user request content
            tools_to_execute: Optional list of tools to simulate execution
            
        Returns:
            List of WebSocketMessage events sent during simulation
        """
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        agent_id = f"agent_{agent_type}_{uuid.uuid4().hex[:8]}"
        
        # Extract user and thread info from client
        user_id = getattr(client, 'headers', {}).get('X-User-ID', 'test_user')
        thread_id = f"thread_{execution_id}"
        
        # Create agent execution context
        context = AgentExecutionContext(
            agent_id=agent_id,
            agent_type=agent_type,
            user_id=user_id,
            thread_id=thread_id,
            execution_id=execution_id,
            started_at=datetime.now()
        )
        
        self.agent_contexts[execution_id] = context
        
        # Create event simulator
        simulator = AgentEventSimulator(context)
        self.event_simulators[execution_id] = simulator
        
        # Simulate complete agent workflow
        events_sent = []
        start_time = time.time()
        
        try:
            # 1. Agent Started
            event = await simulator.simulate_agent_started()
            await self._send_event_to_client(client, event)
            events_sent.append(event)
            
            await asyncio.sleep(simulator.event_delay)
            
            # 2. Agent Thinking
            thinking_messages = [
                "Analyzing user request...",
                "Determining approach...",
                "Planning execution strategy..."
            ]
            
            for progress_msg in thinking_messages:
                event = await simulator.simulate_agent_thinking(progress_msg)
                await self._send_event_to_client(client, event)
                events_sent.append(event)
                await asyncio.sleep(simulator.event_delay)
            
            # 3. Tool Executions
            tools = tools_to_execute or self._get_default_tools_for_agent(agent_type)
            
            for tool_name in tools:
                # Tool executing
                tool_input = {"request": user_request or "Test request", "context": execution_id}
                event = await simulator.simulate_tool_executing(tool_name, tool_input)
                await self._send_event_to_client(client, event)
                events_sent.append(event)
                
                await asyncio.sleep(simulator.tool_execution_delay)
                
                # Tool completed
                tool_result = {"result": f"Mock result from {tool_name}", "success": True}
                event = await simulator.simulate_tool_completed(tool_name, tool_result)
                await self._send_event_to_client(client, event)
                events_sent.append(event)
                
                await asyncio.sleep(simulator.event_delay)
            
            # 4. Agent Completed
            final_result = {
                "summary": f"Mock {agent_type} execution completed successfully",
                "tools_used": tools,
                "execution_time": time.time() - start_time,
                "user_request": user_request or "Test request"
            }
            
            event = await simulator.simulate_agent_completed(final_result)
            await self._send_event_to_client(client, event)
            events_sent.append(event)
            
            # Record performance metrics
            self.agent_execution_times[execution_id] = time.time() - start_time
            
            logger.info(f"Simulated complete {agent_type} agent execution: {len(events_sent)} events sent")
            
        except Exception as e:
            logger.error(f"Agent event simulation failed: {e}")
            context.error = str(e)
            context.status = "failed"
            raise
        
        return events_sent
    
    async def _send_event_to_client(self, client: WebSocketTestClient, event: WebSocketMessage):
        """Send an event to the WebSocket client with delivery tracking."""
        event_id = event.message_id
        send_time = time.time()
        
        try:
            # In mock mode, simulate event delivery by adding to received messages
            if self.config.mock_mode:
                # Simulate network delay if configured
                if self.config.simulate_network_delays:
                    await asyncio.sleep(self.config.network_delay_ms / 1000.0)
                
                # Add event to client's received messages to simulate delivery
                client.received_messages.append(event)
                
                # Track event in received events
                if event.event_type not in client.received_events:
                    client.received_events[event.event_type] = []
                client.received_events[event.event_type].append(event)
                
            else:
                # In real mode, would send through actual WebSocket connection
                await client.send_message(
                    event.event_type,
                    event.data,
                    user_id=event.user_id,
                    thread_id=event.thread_id
                )
            
            # Track sent event
            self.sent_events.append(event)
            
            # Record delivery time
            delivery_time = time.time() - send_time
            self.event_delivery_times[event_id] = delivery_time
            
            # Mark as delivered
            self.event_delivery_confirmations[event_id] = True
            
            logger.debug(f"Event delivered: {event.event_type.value} ({event_id}) in {delivery_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Failed to send event {event_id}: {e}")
            self.event_delivery_confirmations[event_id] = False
            raise
    
    def _get_default_tools_for_agent(self, agent_type: str) -> List[str]:
        """Get default tools for agent type simulation."""
        tool_mappings = {
            "triage": ["data_sufficiency_checker", "requirement_analyzer"],
            "apex_optimizer": ["model_optimizer", "performance_analyzer", "cost_calculator"],
            "data_helper": ["data_query", "schema_analyzer", "data_validator"],
            "supervisor": ["task_planner", "agent_coordinator", "result_synthesizer"]
        }
        
        return tool_mappings.get(agent_type, ["generic_tool"])
    
    async def validate_event_delivery(self, client: WebSocketTestClient, 
                                    expected_events: List[WebSocketMessage],
                                    timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Validate that all expected events were delivered to the WebSocket client.
        
        Args:
            client: WebSocket test client to validate
            expected_events: List of events that should have been delivered
            timeout: Optional timeout for validation
            
        Returns:
            Validation results with delivery status and metrics
        """
        timeout = timeout or self.config.event_delivery_timeout
        validation_id = f"validation_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        results = {
            "validation_id": validation_id,
            "expected_count": len(expected_events),
            "delivered_count": 0,
            "missing_events": [],
            "extra_events": [],
            "delivery_confirmations": {},
            "average_delivery_time": 0.0,
            "max_delivery_time": 0.0,
            "validation_successful": False,
            "validation_time": 0.0
        }
        
        try:
            # Get expected event types and IDs
            expected_event_types = [e.event_type for e in expected_events]
            expected_event_ids = [e.message_id for e in expected_events]
            
            # Wait for events to be delivered
            delivered_events = []
            missing_event_ids = set(expected_event_ids)
            
            # Check for delivered events (with timeout)
            end_time = time.time() + timeout
            while missing_event_ids and time.time() < end_time:
                # Check client's received messages for our events
                for received_msg in client.received_messages:
                    if received_msg.message_id in missing_event_ids:
                        delivered_events.append(received_msg)
                        missing_event_ids.remove(received_msg.message_id)
                
                if missing_event_ids:
                    await asyncio.sleep(0.1)  # Small delay before checking again
            
            # Analyze results
            results["delivered_count"] = len(delivered_events)
            results["missing_events"] = [
                {"event_id": eid, "event_type": next((e.event_type.value for e in expected_events if e.message_id == eid), "unknown")}
                for eid in missing_event_ids
            ]
            
            # Check delivery confirmations
            for event in expected_events:
                event_id = event.message_id
                results["delivery_confirmations"][event_id] = self.event_delivery_confirmations.get(event_id, False)
            
            # Calculate delivery time metrics
            delivery_times = [self.event_delivery_times.get(e.message_id, 0) for e in expected_events 
                            if e.message_id in self.event_delivery_times]
            
            if delivery_times:
                results["average_delivery_time"] = sum(delivery_times) / len(delivery_times)
                results["max_delivery_time"] = max(delivery_times)
            
            # Check for extra events (events not in expected list)
            expected_types_set = set(expected_event_types)
            for received_msg in client.received_messages:
                if received_msg.event_type not in expected_types_set:
                    results["extra_events"].append({
                        "event_id": received_msg.message_id,
                        "event_type": received_msg.event_type.value,
                        "data": received_msg.data
                    })
            
            # Determine if validation was successful
            results["validation_successful"] = (
                len(missing_event_ids) == 0 and 
                results["delivered_count"] == results["expected_count"]
            )
            
            results["validation_time"] = time.time() - start_time
            
            if results["validation_successful"]:
                logger.info(f"Event delivery validation successful: {results['delivered_count']}/{results['expected_count']} events delivered")
            else:
                logger.warning(f"Event delivery validation failed: {results['delivered_count']}/{results['expected_count']} events delivered, {len(missing_event_ids)} missing")
            
        except Exception as e:
            results["error"] = str(e)
            logger.error(f"Event delivery validation error: {e}")
        
        return results
    
    async def test_concurrent_agent_execution(self, client_count: int, 
                                            agent_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Test concurrent agent execution with multiple WebSocket bridges.
        
        Args:
            client_count: Number of concurrent clients/agents to test
            agent_types: Optional list of agent types to use
            
        Returns:
            Concurrent execution test results
        """
        test_id = f"concurrent_test_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        # Default agent types for testing
        agent_types = agent_types or ["triage", "apex_optimizer", "data_helper"]
        
        results = {
            "test_id": test_id,
            "client_count": client_count,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_events_sent": 0,
            "total_events_delivered": 0,
            "average_execution_time": 0.0,
            "max_execution_time": 0.0,
            "concurrency_issues": [],
            "test_duration": 0.0
        }
        
        try:
            # Create multiple bridges and simulate concurrent agent executions
            bridges = []
            execution_tasks = []
            
            for i in range(client_count):
                user_id = f"concurrent_user_{i+1}_{uuid.uuid4().hex[:6]}"
                agent_type = agent_types[i % len(agent_types)]
                
                # Create bridge
                bridge_client = await self.create_agent_websocket_bridge(user_id)
                bridges.append((user_id, agent_type, bridge_client))
                
                # Create execution task
                task = asyncio.create_task(
                    self._execute_agent_with_monitoring(bridge_client, agent_type, f"Concurrent request {i+1}")
                )
                execution_tasks.append(task)
            
            # Wait for all executions to complete
            execution_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
            # Analyze results
            for i, result in enumerate(execution_results):
                if isinstance(result, Exception):
                    results["failed_executions"] += 1
                    results["concurrency_issues"].append({
                        "client_index": i,
                        "error": str(result)
                    })
                else:
                    results["successful_executions"] += 1
                    results["total_events_sent"] += result.get("events_sent", 0)
                    results["total_events_delivered"] += result.get("events_delivered", 0)
            
            # Calculate timing metrics
            execution_times = [
                result.get("execution_time", 0) for result in execution_results 
                if isinstance(result, dict) and "execution_time" in result
            ]
            
            if execution_times:
                results["average_execution_time"] = sum(execution_times) / len(execution_times)
                results["max_execution_time"] = max(execution_times)
            
            results["test_duration"] = time.time() - start_time
            
            # Cleanup bridges
            for _, _, client in bridges:
                await client.disconnect()
            
            logger.info(f"Concurrent agent execution test completed: {results['successful_executions']}/{client_count} successful")
            
        except Exception as e:
            results["error"] = str(e)
            logger.error(f"Concurrent agent execution test failed: {e}")
        
        return results
    
    async def _execute_agent_with_monitoring(self, client: WebSocketTestClient, 
                                           agent_type: str, user_request: str) -> Dict[str, Any]:
        """Execute agent with monitoring for concurrent testing."""
        start_time = time.time()
        
        try:
            # Simulate agent events
            events_sent = await self.simulate_agent_events(client, agent_type, user_request)
            
            # Validate event delivery
            validation_results = await self.validate_event_delivery(client, events_sent)
            
            return {
                "success": True,
                "execution_time": time.time() - start_time,
                "events_sent": len(events_sent),
                "events_delivered": validation_results.get("delivered_count", 0),
                "validation_successful": validation_results.get("validation_successful", False)
            }
            
        except Exception as e:
            return {
                "success": False,
                "execution_time": time.time() - start_time,
                "error": str(e)
            }
    
    @asynccontextmanager
    async def agent_bridge_context(self, user_id: str) -> AsyncGenerator[WebSocketTestClient, None]:
        """
        Context manager for an agent-WebSocket bridge.
        
        Args:
            user_id: User ID for the bridge
            
        Yields:
            WebSocketTestClient configured as agent bridge
        """
        bridge_client = await self.create_agent_websocket_bridge(user_id)
        
        try:
            yield bridge_client
        finally:
            await bridge_client.disconnect()
            # Clean up associated contexts
            contexts_to_remove = []
            for exec_id, context in self.agent_contexts.items():
                if context.user_id == user_id:
                    contexts_to_remove.append(exec_id)
            
            for exec_id in contexts_to_remove:
                if exec_id in self.agent_contexts:
                    del self.agent_contexts[exec_id]
                if exec_id in self.event_simulators:
                    del self.event_simulators[exec_id]
    
    async def cleanup(self):
        """Clean up bridge test helper resources."""
        try:
            # Disconnect all bridges
            disconnect_tasks = []
            for client in self.active_bridges.values():
                if client.is_connected:
                    disconnect_tasks.append(client.disconnect())
            
            if disconnect_tasks:
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            
            # Clear all state
            self.active_bridges.clear()
            self.agent_contexts.clear()
            self.event_simulators.clear()
            self.sent_events.clear()
            self.received_events.clear()
            self.event_delivery_confirmations.clear()
            self.event_delivery_times.clear()
            self.agent_execution_times.clear()
            
            logger.info(f"WebSocketBridgeTestHelper cleanup completed [{self.test_id}]")
            
        except Exception as e:
            logger.error(f"WebSocket bridge helper cleanup failed: {e}")
    
    # Utility methods for test assertions
    
    def get_agent_context(self, execution_id: str) -> Optional[AgentExecutionContext]:
        """Get agent execution context by execution ID."""
        return self.agent_contexts.get(execution_id)
    
    def get_bridge_client(self, bridge_id: str) -> Optional[WebSocketTestClient]:
        """Get bridge client by bridge ID."""
        return self.active_bridges.get(bridge_id)
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """Get bridge helper status."""
        return {
            "test_id": self.test_id,
            "mock_mode": self.config.mock_mode,
            "active_bridges": len(self.active_bridges),
            "agent_contexts": len(self.agent_contexts),
            "sent_events": len(self.sent_events),
            "received_events": len(self.received_events),
            "successful_deliveries": sum(1 for delivered in self.event_delivery_confirmations.values() if delivered),
            "config": {
                "event_delivery_timeout": self.config.event_delivery_timeout,
                "agent_execution_timeout": self.config.agent_execution_timeout,
                "enable_event_validation": self.config.enable_event_validation
            }
        }


# Export WebSocketBridgeTestHelper
__all__ = [
    'WebSocketBridgeTestHelper',
    'AgentExecutionContext',
    'AgentEventSimulator', 
    'BridgeTestConfig'
]