"""Frontend WebSocket Development Utilities for E2E Testing

CRITICAL CONTEXT: WebSocket Client Simulation & Monitoring
Comprehensive utilities for WebSocket client simulation, connection state 
monitoring, and development-specific testing features.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development velocity
2. Business Goal: Accelerate WebSocket testing and debugging
3. Value Impact: Reduces time to detect and fix WebSocket issues
4. Revenue Impact: Prevents revenue loss from WebSocket failures

Module Architecture Compliance: Under 300 lines, functions under 8 lines
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import websockets

from tests.e2e.jwt_token_helpers import JWTTestHelper


class ConnectionState(Enum):
    """WebSocket connection state enumeration."""
    CONNECTING = "connecting"
    CONNECTED = "connected" 
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    FAILED = "failed"
    RECONNECTING = "reconnecting"


@dataclass
class ConnectionMetrics:
    """Metrics tracking for WebSocket connections."""
    connection_time: float = 0.0
    auth_time: float = 0.0
    message_count: int = 0
    error_count: int = 0
    reconnection_count: int = 0
    retry_count: int = 0
    requests_sent: int = 0
    responses_received: int = 0
    last_error: str = ""
    last_ping: Optional[float] = None
    last_pong: Optional[float] = None


@dataclass
class MessageEvent:
    """WebSocket message event tracking."""
    message_id: str
    timestamp: float
    direction: str  # 'sent' or 'received'
    message_type: str
    payload: Dict[str, Any]
    latency: Optional[float] = None


class WebSocketClientSimulator:
    """Simulates frontend WebSocket client behavior."""
    
    def __init__(self, client_id: str, base_url: str = "ws://localhost:8000"):
        self.client_id = client_id
        self.base_url = base_url
        self.jwt_helper = JWTTestHelper()
        self.connection: Optional[websockets.ClientConnection] = None
        self.state = ConnectionState.DISCONNECTED
        self.metrics = ConnectionMetrics()
        self.message_history: List[MessageEvent] = []
        self.event_handlers: Dict[str, Callable] = {}
        self.auto_ping = True
        self._running = False
    
    async def connect(self, user_role: str = "user", auto_auth: bool = True):
        """Connect to WebSocket server with authentication."""
        self.state = ConnectionState.CONNECTING
        start_time = time.time()
        
        try:
            token = await self.jwt_helper.create_valid_jwt_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            self.connection = await websockets.connect(
                f"{self.base_url}/websocket",
                additional_headers=headers
            )
            
            self.metrics.connection_time = time.time() - start_time
            self.state = ConnectionState.CONNECTED
            
            if auto_auth:
                await self._authenticate(token)
            
            return True
        except Exception as e:
            self.state = ConnectionState.ERROR
            self.metrics.error_count += 1
            return False
    
    async def _authenticate(self, token: str):
        """Perform authentication handshake."""
        self.state = ConnectionState.AUTHENTICATING
        auth_start = time.time()
        
        auth_msg = {"type": "auth_verify", "payload": {"token": token}}
        await self.send_message(auth_msg)
        
        response = await self.receive_message()
        if response and response.get("type") != "auth_error":
            self.state = ConnectionState.AUTHENTICATED
            self.metrics.auth_time = time.time() - auth_start
        else:
            self.state = ConnectionState.ERROR
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message and track metrics."""
        if not self.connection or self.connection.closed:
            return False
        
        message_id = str(uuid.uuid4())
        message["message_id"] = message_id
        timestamp = time.time()
        
        await self.connection.send(json.dumps(message))
        
        event = MessageEvent(
            message_id=message_id,
            timestamp=timestamp,
            direction="sent",
            message_type=message.get("type", "unknown"),
            payload=message
        )
        self.message_history.append(event)
        self.metrics.message_count += 1
        
        return message_id
    
    async def receive_message(self, timeout: float = 5.0):
        """Receive message and track metrics."""
        if not self.connection:
            return None
        
        try:
            raw_message = await asyncio.wait_for(
                self.connection.recv(), timeout=timeout
            )
            message = json.loads(raw_message)
            timestamp = time.time()
            
            event = MessageEvent(
                message_id=message.get("message_id", str(uuid.uuid4())),
                timestamp=timestamp,
                direction="received", 
                message_type=message.get("type", "unknown"),
                payload=message
            )
            self.message_history.append(event)
            
            # Calculate latency if possible
            if "message_id" in message:
                sent_event = self._find_sent_message(message["message_id"])
                if sent_event:
                    event.latency = timestamp - sent_event.timestamp
            
            await self._handle_message(message)
            return message
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.metrics.error_count += 1
            return None
    
    def _find_sent_message(self, message_id: str) -> Optional[MessageEvent]:
        """Find corresponding sent message for latency calculation."""
        for event in reversed(self.message_history):
            if event.direction == "sent" and event.message_id == message_id:
                return event
        return None
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle received message with registered handlers."""
        message_type = message.get("type")
        if message_type in self.event_handlers:
            await self.event_handlers[message_type](message)


class WebSocketConnectionMonitor:
    """Monitor WebSocket connection health and performance."""
    
    def __init__(self):
        self.clients: Dict[str, WebSocketClientSimulator] = {}
        self.monitoring_active = False
        self.health_checks: List[Dict[str, Any]] = []
    
    def add_client(self, client: WebSocketClientSimulator):
        """Add client to monitoring."""
        self.clients[client.client_id] = client
    
    def remove_client(self, client_id: str):
        """Remove client from monitoring."""
        if client_id in self.clients:
            del self.clients[client_id]
    
    async def start_monitoring(self, check_interval: float = 1.0):
        """Start connection health monitoring."""
        self.monitoring_active = True
        
        while self.monitoring_active:
            await self._perform_health_checks()
            await asyncio.sleep(check_interval)
    
    def stop_monitoring(self):
        """Stop connection health monitoring."""
        self.monitoring_active = False
    
    async def _perform_health_checks(self):
        """Perform health checks on all monitored clients."""
        check_time = time.time()
        health_report = {
            "timestamp": check_time,
            "clients": {}
        }
        
        for client_id, client in self.clients.items():
            client_health = await self._check_client_health(client)
            health_report["clients"][client_id] = client_health
        
        self.health_checks.append(health_report)
        
        # Keep only last 100 health checks
        if len(self.health_checks) > 100:
            self.health_checks = self.health_checks[-100:]
    
    async def _check_client_health(self, client: WebSocketClientSimulator):
        """Check health of individual client."""
        return {
            "state": client.state.value,
            "connection_alive": client.connection and not client.connection.closed,
            "message_count": client.metrics.message_count,
            "error_count": client.metrics.error_count,
            "reconnection_count": client.metrics.reconnection_count,
            "last_activity": max([
                event.timestamp for event in client.message_history[-10:]
            ], default=0.0)
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all clients."""
        summary = {
            "total_clients": len(self.clients),
            "connection_times": [],
            "auth_times": [],
            "message_counts": [],
            "error_counts": [],
            "states": {}
        }
        
        for client in self.clients.values():
            summary["connection_times"].append(client.metrics.connection_time)
            summary["auth_times"].append(client.metrics.auth_time) 
            summary["message_counts"].append(client.metrics.message_count)
            summary["error_counts"].append(client.metrics.error_count)
            
            state = client.state.value
            summary["states"][state] = summary["states"].get(state, 0) + 1
        
        return summary


class WebSocketDevTestFramework:
    """Development testing framework for WebSocket functionality."""
    
    def __init__(self):
        self.monitor = WebSocketConnectionMonitor()
        self.test_scenarios: Dict[str, Callable] = {}
        self.results: List[Dict[str, Any]] = []
    
    async def run_scenario(self, scenario_name: str, scenario_func: Callable):
        """Run specific test scenario."""
        start_time = time.time()
        
        try:
            result = await scenario_func()
            return {"success": True, "duration": time.time() - start_time, "result": result}
        except Exception as e:
            return {"success": False, "duration": time.time() - start_time, "error": str(e)}
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get test summary."""
        return {
            "total_tests": len(self.results),
            "performance": self.monitor.get_performance_summary()
        }
