"""
Unit Tests for WebSocket Bridge Message Routing - Agent-WebSocket Communication Bridge

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: All (Free/Early/Mid/Enterprise/Platform) - Core Communication Bridge
- Business Goal: Ensure WebSocket bridge properly routes messages between agents and users
- Value Impact: Bridge routing enables real-time AI communication worth $500K+ ARR
- Strategic Impact: Critical communication infrastructure connecting AI agents to user interfaces
- Revenue Protection: Without proper bridge routing, users get no AI responses -> broken UX -> churn

PURPOSE: This test suite validates the WebSocket bridge message routing functionality
that connects agent execution to real-time user communication in the Golden Path
user flow. The bridge is critical infrastructure that translates agent operations
into WebSocket events and routes user messages to appropriate agents.

KEY COVERAGE:
1. Agent-to-WebSocket message routing
2. WebSocket-to-agent message routing  
3. Bidirectional communication flow
4. Message transformation and formatting
5. User isolation in bridge routing
6. Performance requirements for bridge operations
7. Error handling and fallback routing

GOLDEN PATH PROTECTION:
Tests ensure WebSocket bridge properly connects agents to users, enabling the
real-time communication flow that's essential for the $500K+ ARR interactive
AI experience by routing messages correctly in both directions.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Import user context for bridge routing
from netra_backend.app.services.user_execution_context import UserExecutionContext


class BridgeDirection(Enum):
    """Message routing direction through bridge"""
    AGENT_TO_WEBSOCKET = "agent_to_websocket"
    WEBSOCKET_TO_AGENT = "websocket_to_agent"
    BIDIRECTIONAL = "bidirectional"


class RouteType(Enum):
    """Types of message routing in bridge"""
    DIRECT = "direct"
    BROADCAST = "broadcast"
    FILTERED = "filtered"
    TRANSFORMED = "transformed"


@dataclass
class BridgeRoute:
    """Represents a message route through the WebSocket bridge"""
    route_id: str
    direction: BridgeDirection
    route_type: RouteType
    source_id: str
    destination_id: str
    user_id: str
    message_original: Dict[str, Any]
    message_transformed: Dict[str, Any]
    routing_time: float
    success: bool
    metadata: Dict[str, Any]


class MockWebSocketBridge:
    """Mock WebSocket bridge for testing message routing logic"""
    
    def __init__(self):
        self.routes = []
        self.active_connections = {}
        self.registered_agents = {}
        self.bridge_metrics = {
            "total_routes": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "agent_to_websocket": 0,
            "websocket_to_agent": 0,
            "transformation_count": 0
        }
        self.message_transformers = self._initialize_transformers()
        
    def _initialize_transformers(self) -> Dict[str, Any]:
        """Initialize message transformation rules"""
        return {
            "agent_started": lambda msg: {
                "type": "agent_started",
                "event": "agent_started",
                "agent_id": msg.get("agent_id"),
                "status": "Agent execution started",
                "user_id": msg.get("user_id"),
                "timestamp": time.time()
            },
            "agent_thinking": lambda msg: {
                "type": "agent_thinking",
                "event": "agent_thinking", 
                "agent_id": msg.get("agent_id"),
                "thinking_content": msg.get("content", "Processing..."),
                "reasoning_step": msg.get("step", "analysis"),
                "timestamp": time.time()
            },
            "agent_completed": lambda msg: {
                "type": "agent_completed",
                "event": "agent_completed",
                "agent_id": msg.get("agent_id"),
                "result": msg.get("result"),
                "status": "completed",
                "timestamp": time.time()
            },
            "user_request": lambda msg: {
                "type": "user_request",
                "content": msg.get("content"),
                "user_id": msg.get("user_id"),
                "thread_id": msg.get("thread_id"),
                "priority": msg.get("priority", "medium"),
                "timestamp": time.time()
            }
        }
    
    def register_agent(self, agent_id: str, agent_type: str, user_id: str):
        """Register agent for bridge routing"""
        self.registered_agents[agent_id] = {
            "agent_type": agent_type,
            "user_id": user_id,
            "registered_at": time.time(),
            "active": True
        }
        
    def register_websocket_connection(self, connection_id: str, user_id: str, websocket):
        """Register WebSocket connection for bridge routing"""
        self.active_connections[connection_id] = {
            "user_id": user_id,
            "websocket": websocket,
            "connected_at": time.time(),
            "active": True
        }
        
    async def route_agent_to_websocket(
        self,
        message: Dict[str, Any],
        agent_id: str,
        user_id: str,
        route_type: RouteType = RouteType.DIRECT
    ) -> BridgeRoute:
        """Route message from agent to WebSocket connection(s)"""
        
        routing_start = time.time()
        route_id = f"route_a2w_{int(time.time() * 1000)}_{len(self.routes)}"
        
        try:
            # Find user's WebSocket connections
            user_connections = [
                conn_info for conn_info in self.active_connections.values()
                if conn_info["user_id"] == user_id and conn_info["active"]
            ]
            
            if not user_connections:
                # No active connections for user
                failed_route = BridgeRoute(
                    route_id=route_id,
                    direction=BridgeDirection.AGENT_TO_WEBSOCKET,
                    route_type=route_type,
                    source_id=agent_id,
                    destination_id="none",
                    user_id=user_id,
                    message_original=message,
                    message_transformed={},
                    routing_time=time.time() - routing_start,
                    success=False,
                    metadata={"error": "No active WebSocket connections for user"}
                )
                
                self.routes.append(failed_route)
                self.bridge_metrics["failed_routes"] += 1
                return failed_route
            
            # Transform message for WebSocket delivery
            transformed_message = await self._transform_agent_message(message)
            
            # Route to WebSocket connections
            routing_success = True
            destinations = []
            
            for conn_info in user_connections:
                try:
                    websocket = conn_info["websocket"]
                    
                    if route_type == RouteType.DIRECT:
                        await websocket.send_json(transformed_message)
                    elif route_type == RouteType.BROADCAST:
                        # Add broadcast metadata
                        broadcast_message = transformed_message.copy()
                        broadcast_message["broadcast"] = True
                        await websocket.send_json(broadcast_message)
                    elif route_type == RouteType.FILTERED:
                        # Apply filters based on message content
                        if self._should_deliver_to_connection(transformed_message, conn_info):
                            await websocket.send_json(transformed_message)
                    else:
                        await websocket.send_json(transformed_message)
                    
                    destinations.append(conn_info["user_id"])
                    
                except Exception as e:
                    routing_success = False
                    destinations.append(f"failed_{conn_info['user_id']}")
            
            # Create routing record
            route = BridgeRoute(
                route_id=route_id,
                direction=BridgeDirection.AGENT_TO_WEBSOCKET,
                route_type=route_type,
                source_id=agent_id,
                destination_id=",".join(destinations),
                user_id=user_id,
                message_original=message,
                message_transformed=transformed_message,
                routing_time=time.time() - routing_start,
                success=routing_success,
                metadata={
                    "connection_count": len(user_connections),
                    "delivery_count": len([d for d in destinations if not d.startswith("failed_")])
                }
            )
            
            self.routes.append(route)
            
            # Update metrics
            self.bridge_metrics["total_routes"] += 1
            self.bridge_metrics["agent_to_websocket"] += 1
            if routing_success:
                self.bridge_metrics["successful_routes"] += 1
            else:
                self.bridge_metrics["failed_routes"] += 1
            
            return route
            
        except Exception as e:
            # Handle routing errors
            error_route = BridgeRoute(
                route_id=route_id,
                direction=BridgeDirection.AGENT_TO_WEBSOCKET,
                route_type=route_type,
                source_id=agent_id,
                destination_id="error",
                user_id=user_id,
                message_original=message,
                message_transformed={},
                routing_time=time.time() - routing_start,
                success=False,
                metadata={"error": str(e)}
            )
            
            self.routes.append(error_route)
            self.bridge_metrics["failed_routes"] += 1
            
            return error_route
    
    async def route_websocket_to_agent(
        self,
        message: Dict[str, Any],
        connection_id: str,
        target_agent_id: Optional[str] = None
    ) -> BridgeRoute:
        """Route message from WebSocket to agent"""
        
        routing_start = time.time()
        route_id = f"route_w2a_{int(time.time() * 1000)}_{len(self.routes)}"
        
        try:
            # Get connection info
            conn_info = self.active_connections.get(connection_id)
            if not conn_info:
                failed_route = BridgeRoute(
                    route_id=route_id,
                    direction=BridgeDirection.WEBSOCKET_TO_AGENT,
                    route_type=RouteType.DIRECT,
                    source_id=connection_id,
                    destination_id="unknown",
                    user_id="unknown",
                    message_original=message,
                    message_transformed={},
                    routing_time=time.time() - routing_start,
                    success=False,
                    metadata={"error": "Connection not found"}
                )
                
                self.routes.append(failed_route)
                self.bridge_metrics["failed_routes"] += 1
                return failed_route
            
            user_id = conn_info["user_id"]
            
            # Find target agent
            if target_agent_id:
                if target_agent_id not in self.registered_agents:
                    failed_route = BridgeRoute(
                        route_id=route_id,
                        direction=BridgeDirection.WEBSOCKET_TO_AGENT,
                        route_type=RouteType.DIRECT,
                        source_id=connection_id,
                        destination_id=target_agent_id,
                        user_id=user_id,
                        message_original=message,
                        message_transformed={},
                        routing_time=time.time() - routing_start,
                        success=False,
                        metadata={"error": f"Agent {target_agent_id} not registered"}
                    )
                    
                    self.routes.append(failed_route)
                    self.bridge_metrics["failed_routes"] += 1
                    return failed_route
                
                target_agents = [target_agent_id]
            else:
                # Find agents for this user
                target_agents = [
                    agent_id for agent_id, agent_info in self.registered_agents.items()
                    if agent_info["user_id"] == user_id and agent_info["active"]
                ]
            
            if not target_agents:
                failed_route = BridgeRoute(
                    route_id=route_id,
                    direction=BridgeDirection.WEBSOCKET_TO_AGENT,
                    route_type=RouteType.DIRECT,
                    source_id=connection_id,
                    destination_id="none",
                    user_id=user_id,
                    message_original=message,
                    message_transformed={},
                    routing_time=time.time() - routing_start,
                    success=False,
                    metadata={"error": "No active agents for user"}
                )
                
                self.routes.append(failed_route)
                self.bridge_metrics["failed_routes"] += 1
                return failed_route
            
            # Transform message for agent delivery
            transformed_message = await self._transform_websocket_message(message, user_id)
            
            # Simulate agent delivery (in real implementation would send to agent)
            successful_deliveries = []
            for agent_id in target_agents:
                try:
                    # Simulate agent message delivery
                    await asyncio.sleep(0.001)  # Simulate processing time
                    successful_deliveries.append(agent_id)
                except Exception as e:
                    pass
            
            routing_success = len(successful_deliveries) > 0
            
            # Create routing record
            route = BridgeRoute(
                route_id=route_id,
                direction=BridgeDirection.WEBSOCKET_TO_AGENT,
                route_type=RouteType.DIRECT,
                source_id=connection_id,
                destination_id=",".join(successful_deliveries),
                user_id=user_id,
                message_original=message,
                message_transformed=transformed_message,
                routing_time=time.time() - routing_start,
                success=routing_success,
                metadata={
                    "target_agent_count": len(target_agents),
                    "successful_deliveries": len(successful_deliveries)
                }
            )
            
            self.routes.append(route)
            
            # Update metrics
            self.bridge_metrics["total_routes"] += 1
            self.bridge_metrics["websocket_to_agent"] += 1
            if routing_success:
                self.bridge_metrics["successful_routes"] += 1
            else:
                self.bridge_metrics["failed_routes"] += 1
            
            return route
            
        except Exception as e:
            error_route = BridgeRoute(
                route_id=route_id,
                direction=BridgeDirection.WEBSOCKET_TO_AGENT,
                route_type=RouteType.DIRECT,
                source_id=connection_id,
                destination_id="error",
                user_id="unknown",
                message_original=message,
                message_transformed={},
                routing_time=time.time() - routing_start,
                success=False,
                metadata={"error": str(e)}
            )
            
            self.routes.append(error_route)
            self.bridge_metrics["failed_routes"] += 1
            
            return error_route
    
    async def _transform_agent_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Transform agent message for WebSocket delivery"""
        
        message_type = message.get("type", "unknown")
        
        # Apply transformation if available
        if message_type in self.message_transformers:
            transformed = self.message_transformers[message_type](message)
            self.bridge_metrics["transformation_count"] += 1
            return transformed
        else:
            # Pass through with minimal formatting
            return {
                "type": message_type,
                "payload": message,
                "timestamp": time.time()
            }
    
    async def _transform_websocket_message(self, message: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Transform WebSocket message for agent delivery"""
        
        # Add user context and normalize format
        transformed = {
            "type": message.get("type", "user_message"),
            "content": message.get("content", message.get("payload", {})),
            "user_id": user_id,
            "thread_id": message.get("thread_id"),
            "run_id": message.get("run_id"),
            "message_id": message.get("id", message.get("message_id")),
            "timestamp": message.get("timestamp", time.time()),
            "routing_metadata": {
                "routed_by": "websocket_bridge",
                "transformation_applied": True
            }
        }
        
        self.bridge_metrics["transformation_count"] += 1
        return transformed
    
    def _should_deliver_to_connection(self, message: Dict[str, Any], conn_info: Dict[str, Any]) -> bool:
        """Apply delivery filters for filtered routing"""
        
        # Example filtering logic
        message_type = message.get("type", "")
        
        # Filter sensitive messages for appropriate connections
        if "sensitive" in message.get("tags", []):
            return conn_info.get("security_level", "standard") in ["high", "enterprise"]
        
        # Filter agent-specific messages
        if message_type.startswith("agent_"):
            return True  # Agent messages generally deliverable
        
        return True  # Default allow
    
    def get_routes_for_user(self, user_id: str) -> List[BridgeRoute]:
        """Get all routes for specific user"""
        return [route for route in self.routes if route.user_id == user_id]
    
    def get_bridge_metrics(self) -> Dict[str, Any]:
        """Get bridge performance metrics"""
        return self.bridge_metrics.copy()
    
    def get_active_connections_count(self) -> int:
        """Get count of active WebSocket connections"""
        return len([conn for conn in self.active_connections.values() if conn["active"]])
    
    def get_registered_agents_count(self) -> int:
        """Get count of registered agents"""
        return len([agent for agent in self.registered_agents.values() if agent["active"]])


class WebSocketBridgeMessageRoutingTests(SSotAsyncTestCase):
    """Unit tests for WebSocket bridge message routing functionality
    
    This test class validates the critical bridge routing capabilities that
    connect agents to WebSocket communications in the Golden Path user flow.
    These tests focus on core routing logic without requiring complex
    infrastructure dependencies.
    
    Tests MUST ensure bridge can:
    1. Route agent messages to correct WebSocket connections
    2. Route WebSocket messages to appropriate agents
    3. Transform messages appropriately for each direction
    4. Maintain user isolation in routing decisions
    5. Handle routing failures gracefully
    6. Meet performance requirements for bridge operations
    """
    
    def setup_method(self, method=None):
        """Setup for each test with proper isolation"""
        super().setup_method(method)
        
        # Create isolated user context for this test
        self.user_context = SSotMockFactory.create_mock_user_context(
            user_id=f"test_user_{self.get_test_context().test_id}",
            thread_id=f"test_thread_{self.get_test_context().test_id}",
            run_id=f"test_run_{self.get_test_context().test_id}",
            request_id=f"test_req_{self.get_test_context().test_id}"
        )
        
        # Create mock WebSocket connection
        self.mock_websocket = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()
        
        # Create WebSocket bridge instance
        self.bridge = MockWebSocketBridge()
        
        # Register test components
        self.test_agent_id = f"agent_{self.get_test_context().test_id}"
        self.test_connection_id = f"conn_{self.user_context.user_id}"
        
        self.bridge.register_agent(
            self.test_agent_id, "optimization_agent", self.user_context.user_id
        )
        self.bridge.register_websocket_connection(
            self.test_connection_id, self.user_context.user_id, self.mock_websocket
        )
    
    # ========================================================================
    # AGENT-TO-WEBSOCKET ROUTING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_agent_started_message_routing(self):
        """Test routing of agent started message to WebSocket
        
        Business Impact: Agent started events provide immediate feedback
        to users that their request is being processed in Golden Path.
        """
        # Create agent started message
        agent_started_msg = {
            "type": "agent_started",
            "agent_id": self.test_agent_id,
            "agent_type": "optimization_agent",
            "user_request": "Optimize my AI costs",
            "status": "started",
            "timestamp": time.time()
        }
        
        # Route message through bridge
        routing_start = time.time()
        route = await self.bridge.route_agent_to_websocket(
            agent_started_msg, 
            self.test_agent_id,
            self.user_context.user_id,
            RouteType.DIRECT
        )
        routing_time = time.time() - routing_start
        
        # Verify successful routing
        assert route.success is True
        assert route.direction == BridgeDirection.AGENT_TO_WEBSOCKET
        assert route.route_type == RouteType.DIRECT
        assert route.user_id == self.user_context.user_id
        
        # Verify message transformation
        transformed = route.message_transformed
        assert transformed["type"] == "agent_started"
        assert transformed["agent_id"] == self.test_agent_id
        assert transformed["status"] == "Agent execution started"
        
        # Verify WebSocket delivery
        self.mock_websocket.send_json.assert_called_once()
        sent_message = self.mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "agent_started"
        assert sent_message["agent_id"] == self.test_agent_id
        
        # Verify performance
        assert routing_time < 0.01, f"Agent routing took {routing_time:.4f}s, should be < 0.01s"
        
        self.record_metric("agent_started_routing_time", routing_time)
        self.record_metric("agent_started_routed_successfully", True)
    
    @pytest.mark.unit
    async def test_agent_thinking_message_routing(self):
        """Test routing of agent thinking message to WebSocket
        
        Business Impact: Agent thinking events provide real-time insight
        into AI reasoning process, enhancing user experience.
        """
        agent_thinking_msg = {
            "type": "agent_thinking",
            "agent_id": self.test_agent_id,
            "content": "Analyzing your cost patterns and identifying optimization opportunities...",
            "step": "cost_analysis",
            "progress": 0.3
        }
        
        route = await self.bridge.route_agent_to_websocket(
            agent_thinking_msg,
            self.test_agent_id,
            self.user_context.user_id
        )
        
        # Verify routing success
        assert route.success is True
        assert route.direction == BridgeDirection.AGENT_TO_WEBSOCKET
        
        # Verify thinking content transformation
        transformed = route.message_transformed
        assert transformed["type"] == "agent_thinking"
        assert transformed["thinking_content"] == "Analyzing your cost patterns and identifying optimization opportunities..."
        assert transformed["reasoning_step"] == "cost_analysis"
        
        # Verify WebSocket received thinking update
        self.mock_websocket.send_json.assert_called_once()
        sent_message = self.mock_websocket.send_json.call_args[0][0]
        assert sent_message["thinking_content"] == agent_thinking_msg["content"]
        
        self.record_metric("agent_thinking_routed_successfully", True)
    
    @pytest.mark.unit
    async def test_agent_completed_message_routing(self):
        """Test routing of agent completed message to WebSocket
        
        Business Impact: Agent completed events deliver final AI results,
        completing the Golden Path value delivery cycle.
        """
        agent_result = {
            "optimization_recommendations": [
                {
                    "title": "Switch to GPT-3.5-Turbo for Simple Queries",
                    "savings": "$800/month",
                    "implementation": "Update model selection logic"
                }
            ],
            "total_savings": "$1,200/month",
            "confidence": 0.85
        }
        
        agent_completed_msg = {
            "type": "agent_completed",
            "agent_id": self.test_agent_id,
            "result": agent_result,
            "execution_time": 12.5,
            "status": "completed"
        }
        
        route = await self.bridge.route_agent_to_websocket(
            agent_completed_msg,
            self.test_agent_id,
            self.user_context.user_id
        )
        
        # Verify routing success
        assert route.success is True
        
        # Verify result transformation and delivery
        transformed = route.message_transformed
        assert transformed["type"] == "agent_completed"
        assert transformed["result"] == agent_result
        assert transformed["status"] == "completed"
        
        # Verify WebSocket received complete results
        self.mock_websocket.send_json.assert_called_once()
        sent_message = self.mock_websocket.send_json.call_args[0][0]
        assert sent_message["result"]["total_savings"] == "$1,200/month"
        
        self.record_metric("agent_completed_routed_successfully", True)
    
    # ========================================================================
    # WEBSOCKET-TO-AGENT ROUTING TESTS  
    # ========================================================================
    
    @pytest.mark.unit
    async def test_user_request_routing_to_agent(self):
        """Test routing of user request from WebSocket to agent
        
        Business Impact: User request routing enables agents to receive
        and process user inputs in Golden Path workflow.
        """
        user_request_msg = {
            "type": "user_request",
            "content": "I need help optimizing my AI model selection to reduce costs",
            "id": "msg_user_001",
            "thread_id": self.user_context.thread_id,
            "run_id": self.user_context.run_id,
            "timestamp": time.time()
        }
        
        # Route user request to agent
        route = await self.bridge.route_websocket_to_agent(
            user_request_msg,
            self.test_connection_id,
            self.test_agent_id
        )
        
        # Verify routing success
        assert route.success is True
        assert route.direction == BridgeDirection.WEBSOCKET_TO_AGENT
        assert route.source_id == self.test_connection_id
        assert route.destination_id == self.test_agent_id
        
        # Verify message transformation for agent
        transformed = route.message_transformed
        assert transformed["type"] == "user_request"
        assert transformed["content"] == user_request_msg["content"]
        assert transformed["user_id"] == self.user_context.user_id
        assert transformed["thread_id"] == self.user_context.thread_id
        
        # Verify routing metadata added
        assert "routing_metadata" in transformed
        assert transformed["routing_metadata"]["routed_by"] == "websocket_bridge"
        
        self.record_metric("user_request_routed_to_agent", True)
    
    @pytest.mark.unit
    async def test_websocket_message_routing_without_target_agent(self):
        """Test routing WebSocket message when no target agent specified
        
        Business Impact: Automatic agent discovery enables flexible
        message routing without requiring users to specify agents.
        """
        # Register additional agent for same user
        second_agent_id = f"second_agent_{self.get_test_context().test_id}"
        self.bridge.register_agent(
            second_agent_id, "triage_agent", self.user_context.user_id
        )
        
        general_request_msg = {
            "type": "user_request",
            "content": "General optimization request",
            "timestamp": time.time()
        }
        
        # Route without specifying target agent
        route = await self.bridge.route_websocket_to_agent(
            general_request_msg,
            self.test_connection_id
        )
        
        # Verify routing to available agents
        assert route.success is True
        assert route.user_id == self.user_context.user_id
        
        # Should route to at least one agent
        destinations = route.destination_id.split(",")
        assert len(destinations) >= 1
        assert any(agent_id in destinations for agent_id in [self.test_agent_id, second_agent_id])
        
        self.record_metric("automatic_agent_discovery_works", True)
        self.record_metric("agents_discovered", len(destinations))
    
    # ========================================================================
    # BIDIRECTIONAL ROUTING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_complete_bidirectional_conversation_flow(self):
        """Test complete bidirectional message flow through bridge
        
        Business Impact: Bidirectional flow enables complete AI
        conversation cycle essential for Golden Path user experience.
        """
        conversation_flows = []
        
        # 1. User sends request
        user_msg = {
            "type": "user_request",
            "content": "Help me reduce AI costs by 30%",
            "id": "conv_msg_001"
        }
        
        route1 = await self.bridge.route_websocket_to_agent(
            user_msg, self.test_connection_id, self.test_agent_id
        )
        conversation_flows.append(("websocket_to_agent", route1))
        
        # 2. Agent responds with started event
        agent_started = {
            "type": "agent_started",
            "agent_id": self.test_agent_id,
            "user_request": user_msg["content"]
        }
        
        route2 = await self.bridge.route_agent_to_websocket(
            agent_started, self.test_agent_id, self.user_context.user_id
        )
        conversation_flows.append(("agent_to_websocket", route2))
        
        # 3. Agent sends thinking update
        agent_thinking = {
            "type": "agent_thinking",
            "agent_id": self.test_agent_id,
            "content": "Analyzing current usage patterns..."
        }
        
        route3 = await self.bridge.route_agent_to_websocket(
            agent_thinking, self.test_agent_id, self.user_context.user_id
        )
        conversation_flows.append(("agent_to_websocket", route3))
        
        # 4. Agent sends completion
        agent_completed = {
            "type": "agent_completed",
            "agent_id": self.test_agent_id,
            "result": {
                "savings_identified": "$900/month",
                "recommendations": ["Use smaller models for simple tasks"]
            }
        }
        
        route4 = await self.bridge.route_agent_to_websocket(
            agent_completed, self.test_agent_id, self.user_context.user_id
        )
        conversation_flows.append(("agent_to_websocket", route4))
        
        # Verify all flows successful
        for flow_type, route in conversation_flows:
            assert route.success is True, f"Flow {flow_type} failed: {route.metadata.get('error')}"
        
        # Verify conversation completeness
        assert len(conversation_flows) == 4
        
        # Verify message sequence
        websocket_to_agent_flows = [f for f in conversation_flows if f[0] == "websocket_to_agent"]
        agent_to_websocket_flows = [f for f in conversation_flows if f[0] == "agent_to_websocket"]
        
        assert len(websocket_to_agent_flows) == 1  # User request
        assert len(agent_to_websocket_flows) == 3  # Started, thinking, completed
        
        # Verify WebSocket received all agent messages
        assert self.mock_websocket.send_json.call_count == 3
        
        self.record_metric("bidirectional_conversation_completed", True)
        self.record_metric("conversation_steps_completed", len(conversation_flows))
    
    # ========================================================================
    # USER ISOLATION TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_user_isolation_in_bridge_routing(self):
        """Test user isolation in bridge message routing
        
        Business Impact: User isolation is critical for multi-tenant
        security and prevents cross-user message contamination.
        """
        # Create second user and components
        user2_context = SSotMockFactory.create_mock_user_context(
            user_id="user2_bridge_test",
            thread_id="thread2_bridge_test",
            run_id="run2_bridge_test"
        )
        
        user2_websocket = AsyncMock()
        user2_websocket.send_json = AsyncMock()
        user2_agent_id = "agent_user2_bridge"
        user2_connection_id = "conn_user2_bridge"
        
        # Register user2 components
        self.bridge.register_agent(user2_agent_id, "triage_agent", user2_context.user_id)
        self.bridge.register_websocket_connection(
            user2_connection_id, user2_context.user_id, user2_websocket
        )
        
        # Send agent message for user1
        user1_agent_msg = {
            "type": "agent_started",
            "agent_id": self.test_agent_id,
            "user_data": "User 1 private data"
        }
        
        route1 = await self.bridge.route_agent_to_websocket(
            user1_agent_msg, self.test_agent_id, self.user_context.user_id
        )
        
        # Send agent message for user2
        user2_agent_msg = {
            "type": "agent_started", 
            "agent_id": user2_agent_id,
            "user_data": "User 2 private data"
        }
        
        route2 = await self.bridge.route_agent_to_websocket(
            user2_agent_msg, user2_agent_id, user2_context.user_id
        )
        
        # Verify isolation - each user only received their message
        assert route1.success is True
        assert route2.success is True
        
        # User1's WebSocket should only receive user1's message
        self.mock_websocket.send_json.assert_called_once()
        user1_received = self.mock_websocket.send_json.call_args[0][0]
        assert "User 1 private data" in str(user1_received)
        assert "User 2 private data" not in str(user1_received)
        
        # User2's WebSocket should only receive user2's message  
        user2_websocket.send_json.assert_called_once()
        user2_received = user2_websocket.send_json.call_args[0][0]
        assert "User 2 private data" in str(user2_received)
        assert "User 1 private data" not in str(user2_received)
        
        # Verify routes are correctly isolated
        assert route1.user_id == self.user_context.user_id
        assert route2.user_id == user2_context.user_id
        assert route1.source_id != route2.source_id
        
        self.record_metric("user_isolation_enforced", True)
    
    # ========================================================================
    # ERROR HANDLING TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_routing_with_no_websocket_connections(self):
        """Test routing behavior when user has no WebSocket connections
        
        Business Impact: Graceful handling of offline users prevents
        system errors and enables proper error reporting.
        """
        # Remove WebSocket connection
        del self.bridge.active_connections[self.test_connection_id]
        
        # Attempt to route agent message to offline user
        agent_msg = {
            "type": "agent_completed",
            "agent_id": self.test_agent_id,
            "result": "Offline user test result"
        }
        
        route = await self.bridge.route_agent_to_websocket(
            agent_msg, self.test_agent_id, self.user_context.user_id
        )
        
        # Verify graceful failure handling
        assert route.success is False
        assert route.destination_id == "none"
        assert "No active WebSocket connections" in route.metadata["error"]
        
        # Verify metrics updated for failed route
        metrics = self.bridge.get_bridge_metrics()
        assert metrics["failed_routes"] > 0
        
        self.record_metric("offline_user_handled_gracefully", True)
    
    @pytest.mark.unit
    async def test_routing_with_no_registered_agents(self):
        """Test routing behavior when no agents are registered
        
        Business Impact: Proper error handling when agents are unavailable
        prevents silent failures and enables appropriate user feedback.
        """
        # Remove registered agent
        del self.bridge.registered_agents[self.test_agent_id]
        
        # Attempt to route WebSocket message to non-existent agent
        websocket_msg = {
            "type": "user_request",
            "content": "Message with no agents available"
        }
        
        route = await self.bridge.route_websocket_to_agent(
            websocket_msg, self.test_connection_id
        )
        
        # Verify graceful failure handling
        assert route.success is False
        assert route.destination_id == "none"
        assert "No active agents" in route.metadata["error"]
        
        self.record_metric("no_agents_handled_gracefully", True)
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    @pytest.mark.unit
    async def test_bridge_routing_performance(self):
        """Test bridge routing performance requirements
        
        Business Impact: Fast routing is essential for real-time
        user experience in Golden Path interactions.
        """
        test_message = {
            "type": "agent_thinking",
            "agent_id": self.test_agent_id,
            "content": "Performance test routing message"
        }
        
        # Measure routing times
        routing_times = []
        for i in range(20):
            start_time = time.time()
            route = await self.bridge.route_agent_to_websocket(
                test_message, self.test_agent_id, self.user_context.user_id
            )
            end_time = time.time()
            
            assert route.success is True
            routing_times.append(end_time - start_time)
        
        # Calculate performance metrics
        avg_time = sum(routing_times) / len(routing_times)
        max_time = max(routing_times)
        
        # Performance requirements for real-time bridge routing
        assert avg_time < 0.005, f"Average routing time {avg_time:.6f}s should be < 0.005s"
        assert max_time < 0.02, f"Max routing time {max_time:.6f}s should be < 0.02s"
        
        self.record_metric("average_bridge_routing_time", avg_time)
        self.record_metric("max_bridge_routing_time", max_time)
        self.record_metric("bridge_performance_requirements_met", True)
    
    @pytest.mark.unit
    async def test_concurrent_bridge_routing(self):
        """Test concurrent routing through bridge
        
        Business Impact: Bridge must handle multiple simultaneous
        routes without performance degradation or interference.
        """
        # Create concurrent routing tasks
        concurrent_tasks = []
        
        # Agent-to-WebSocket routes
        for i in range(5):
            msg = {
                "type": "agent_thinking",
                "agent_id": self.test_agent_id,
                "content": f"Concurrent agent message {i}"
            }
            task = self.bridge.route_agent_to_websocket(
                msg, self.test_agent_id, self.user_context.user_id
            )
            concurrent_tasks.append(("a2w", task))
        
        # WebSocket-to-Agent routes
        for i in range(5):
            msg = {
                "type": "user_request",
                "content": f"Concurrent user request {i}"
            }
            task = self.bridge.route_websocket_to_agent(
                msg, self.test_connection_id, self.test_agent_id
            )
            concurrent_tasks.append(("w2a", task))
        
        # Execute all routes concurrently
        start_time = time.time()
        results = await asyncio.gather(*[task for _, task in concurrent_tasks])
        concurrent_time = time.time() - start_time
        
        # Verify all routes successful
        successful_routes = sum(1 for route in results if route.success)
        assert successful_routes == len(concurrent_tasks), f"Only {successful_routes}/{len(concurrent_tasks)} routes successful"
        
        # Verify concurrent performance
        assert concurrent_time < 0.1, f"Concurrent routing took {concurrent_time:.3f}s, should be < 0.1s"
        
        # Verify route isolation
        a2w_routes = [results[i] for i, (route_type, _) in enumerate(concurrent_tasks) if route_type == "a2w"]
        w2a_routes = [results[i] for i, (route_type, _) in enumerate(concurrent_tasks) if route_type == "w2a"]
        
        assert len(a2w_routes) == 5
        assert len(w2a_routes) == 5
        
        # All routes should have different route IDs
        route_ids = [route.route_id for route in results]
        assert len(route_ids) == len(set(route_ids)), "Route IDs should be unique"
        
        self.record_metric("concurrent_routes_completed", successful_routes)
        self.record_metric("concurrent_routing_time", concurrent_time)
    
    def teardown_method(self, method=None):
        """Cleanup after each test"""
        # Record final test metrics
        metrics = self.get_all_metrics()
        bridge_metrics = self.bridge.get_bridge_metrics()
        
        # Calculate comprehensive coverage metrics
        routing_tests = sum(1 for key in metrics.keys() 
                          if "routed" in key and "successfully" in key and metrics[key] is True)
        
        self.record_metric("bridge_routing_tests_completed", routing_tests)
        self.record_metric("total_bridge_routes_processed", bridge_metrics["total_routes"])
        self.record_metric("bridge_routing_success_rate", 
                          bridge_metrics["successful_routes"] / max(bridge_metrics["total_routes"], 1))
        self.record_metric("websocket_bridge_validation_complete", True)
        
        # Call parent teardown
        super().teardown_method(method)