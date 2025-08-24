#!/usr/bin/env python3
"""
L4 Integration Test: Dev Environment WebSocket Connection Establishment

Tests comprehensive WebSocket connection scenarios:
1. Initial connection handshake
2. Authentication via WebSocket
3. Connection persistence and heartbeat
4. Reconnection logic
5. Multiple concurrent connections
6. Message queuing and delivery
7. Connection state management
8. Rate limiting and backpressure

BVJ:
- Segment: Free, Early, Mid, Enterprise
- Business Goal: Retention
- Value Impact: Real-time communication for AI agent interactions
- Strategic Impact: Core platform capability for live agent responses
"""

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiohttp
import pytest
import websockets

# Service URLs
AUTH_SERVICE_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/websocket"

# Test configuration
MAX_CONNECTIONS = 10
MESSAGE_BATCH_SIZE = 100
HEARTBEAT_INTERVAL = 30  # seconds
RECONNECT_ATTEMPTS = 3

class WebSocketConnectionTester:
    """Test WebSocket connection establishment and management."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.connections: Dict[str, Any] = {}
        self.message_queues: Dict[str, deque] = {}
        self.connection_stats: Dict[str, Dict] = {}
        self.auth_token: Optional[str] = None
        self.test_logs: List[str] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self._setup_auth()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._cleanup_connections()
        if self.session:
            await self.session.close()
    
    async def _setup_auth(self):
        """Setup authentication for WebSocket connections."""
        # Register and login test user
        user_data = {
            "email": "ws_test@example.com",
            "password": "TestPass123!",
            "name": "WebSocket Test User"
        }
        
        # Register
        await self.session.post(f"{AUTH_SERVICE_URL}/auth/register", json=user_data)
        
        # Login
        async with self.session.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]}
        ) as response:
            if response.status == 200:
                data = await response.json()
                self.auth_token = data.get("access_token")
    
    async def _cleanup_connections(self):
        """Clean up all WebSocket connections."""
        for conn_id, ws in self.connections.items():
            if ws and not ws.closed:
                await ws.close()
    
    def log_event(self, conn_id: str, event: str, details: str = ""):
        """Log WebSocket events."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{conn_id}] {event}"
        if details:
            log_entry += f" - {details}"
        self.test_logs.append(log_entry)
        print(log_entry)
    
    @pytest.mark.asyncio
    async def test_basic_connection(self) -> Dict[str, Any]:
        """Test basic WebSocket connection establishment."""
        result = {
            "connected": False,
            "authenticated": False,
            "connection_time": 0,
            "handshake_data": {}
        }
        
        conn_id = "basic_conn"
        start_time = time.time()
        
        try:
            # Connect with auth header
            headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
            
            ws = await websockets.connect(WEBSOCKET_URL, extra_headers=headers)
            self.connections[conn_id] = ws
            result["connected"] = True
            
            # Send auth message
            if self.auth_token:
                auth_msg = {"type": "auth", "token": self.auth_token}
                await ws.send(json.dumps(auth_msg))
                
                # Wait for auth response
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)
                
                if data.get("type") == "auth_success":
                    result["authenticated"] = True
                    result["handshake_data"] = data
                    
            result["connection_time"] = time.time() - start_time
            self.log_event(conn_id, "CONNECTION_SUCCESS", f"Time: {result['connection_time']:.2f}s")
            
        except Exception as e:
            self.log_event(conn_id, "CONNECTION_FAILED", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self) -> Dict[str, Any]:
        """Test multiple concurrent WebSocket connections."""
        result = {
            "target_connections": MAX_CONNECTIONS,
            "successful_connections": 0,
            "failed_connections": 0,
            "connection_times": [],
            "avg_connection_time": 0
        }
        
        tasks = []
        for i in range(MAX_CONNECTIONS):
            conn_id = f"concurrent_{i}"
            task = asyncio.create_task(self._establish_connection(conn_id))
            tasks.append((conn_id, task))
        
        # Wait for all connections
        for conn_id, task in tasks:
            try:
                conn_result = await task
                if conn_result["success"]:
                    result["successful_connections"] += 1
                    result["connection_times"].append(conn_result["time"])
                else:
                    result["failed_connections"] += 1
            except Exception as e:
                result["failed_connections"] += 1
                self.log_event(conn_id, "CONCURRENT_ERROR", str(e))
        
        if result["connection_times"]:
            result["avg_connection_time"] = sum(result["connection_times"]) / len(result["connection_times"])
            
        return result
    
    async def _establish_connection(self, conn_id: str) -> Dict[str, Any]:
        """Establish a single WebSocket connection."""
        start_time = time.time()
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
            ws = await websockets.connect(WEBSOCKET_URL, extra_headers=headers)
            self.connections[conn_id] = ws
            
            # Initialize message queue
            self.message_queues[conn_id] = deque(maxlen=1000)
            
            # Initialize stats
            self.connection_stats[conn_id] = {
                "connected_at": datetime.now(),
                "messages_sent": 0,
                "messages_received": 0,
                "bytes_sent": 0,
                "bytes_received": 0
            }
            
            return {"success": True, "time": time.time() - start_time}
        except Exception as e:
            return {"success": False, "time": time.time() - start_time, "error": str(e)}
    
    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self) -> Dict[str, Any]:
        """Test WebSocket heartbeat and keepalive."""
        result = {
            "heartbeat_sent": 0,
            "heartbeat_received": 0,
            "connection_maintained": False,
            "test_duration": 0
        }
        
        conn_id = "heartbeat_test"
        if conn_id not in self.connections:
            await self._establish_connection(conn_id)
            
        ws = self.connections.get(conn_id)
        if not ws:
            return result
            
        start_time = time.time()
        test_duration = 10  # seconds
        
        try:
            while time.time() - start_time < test_duration:
                # Send ping
                await ws.ping()
                result["heartbeat_sent"] += 1
                
                # Send heartbeat message
                heartbeat_msg = {
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                }
                await ws.send(json.dumps(heartbeat_msg))
                
                # Wait for any response
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2)
                    data = json.loads(response)
                    if data.get("type") == "heartbeat_ack":
                        result["heartbeat_received"] += 1
                except asyncio.TimeoutError:
                    pass
                    
                await asyncio.sleep(2)
                
            result["connection_maintained"] = not ws.closed
            result["test_duration"] = time.time() - start_time
            
        except Exception as e:
            self.log_event(conn_id, "HEARTBEAT_ERROR", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_reconnection_logic(self) -> Dict[str, Any]:
        """Test WebSocket reconnection after disconnection."""
        result = {
            "initial_connection": False,
            "forced_disconnect": False,
            "reconnection_attempts": 0,
            "reconnection_success": False,
            "total_downtime": 0
        }
        
        conn_id = "reconnect_test"
        
        # Initial connection
        conn_result = await self._establish_connection(conn_id)
        result["initial_connection"] = conn_result["success"]
        
        if not result["initial_connection"]:
            return result
            
        # Force disconnect
        ws = self.connections[conn_id]
        await ws.close()
        result["forced_disconnect"] = True
        
        disconnect_time = time.time()
        
        # Attempt reconnection
        for attempt in range(RECONNECT_ATTEMPTS):
            result["reconnection_attempts"] += 1
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            reconn_result = await self._establish_connection(conn_id)
            if reconn_result["success"]:
                result["reconnection_success"] = True
                result["total_downtime"] = time.time() - disconnect_time
                break
                
        return result
    
    @pytest.mark.asyncio
    async def test_message_delivery(self) -> Dict[str, Any]:
        """Test message queuing and delivery."""
        result = {
            "messages_sent": 0,
            "messages_received": 0,
            "delivery_rate": 0,
            "avg_latency": 0,
            "message_order_preserved": True
        }
        
        conn_id = "message_test"
        if conn_id not in self.connections:
            await self._establish_connection(conn_id)
            
        ws = self.connections.get(conn_id)
        if not ws:
            return result
            
        # Send batch of messages
        sent_messages = []
        latencies = []
        
        for i in range(MESSAGE_BATCH_SIZE):
            msg = {
                "type": "test_message",
                "id": str(uuid.uuid4()),
                "sequence": i,
                "timestamp": time.time(),
                "content": f"Test message {i}"
            }
            
            await ws.send(json.dumps(msg))
            sent_messages.append(msg)
            result["messages_sent"] += 1
            
            # Try to receive echo/response
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=0.1)
                recv_data = json.loads(response)
                
                if "timestamp" in msg:
                    latency = time.time() - msg["timestamp"]
                    latencies.append(latency)
                    
                result["messages_received"] += 1
                
                # Check order
                if "sequence" in recv_data:
                    if recv_data["sequence"] != i:
                        result["message_order_preserved"] = False
                        
            except asyncio.TimeoutError:
                pass
                
        # Calculate metrics
        if result["messages_sent"] > 0:
            result["delivery_rate"] = (result["messages_received"] / result["messages_sent"]) * 100
            
        if latencies:
            result["avg_latency"] = sum(latencies) / len(latencies)
            
        return result
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self) -> Dict[str, Any]:
        """Test WebSocket rate limiting and backpressure."""
        result = {
            "burst_messages_sent": 0,
            "rate_limited": False,
            "backpressure_applied": False,
            "messages_dropped": 0
        }
        
        conn_id = "rate_limit_test"
        if conn_id not in self.connections:
            await self._establish_connection(conn_id)
            
        ws = self.connections.get(conn_id)
        if not ws:
            return result
            
        # Send burst of messages
        burst_size = 1000
        send_errors = 0
        
        for i in range(burst_size):
            msg = {
                "type": "burst_message",
                "id": i,
                "timestamp": time.time()
            }
            
            try:
                await ws.send(json.dumps(msg))
                result["burst_messages_sent"] += 1
            except Exception as e:
                send_errors += 1
                if "rate limit" in str(e).lower():
                    result["rate_limited"] = True
                if "backpressure" in str(e).lower():
                    result["backpressure_applied"] = True
                    
        result["messages_dropped"] = send_errors
        
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all WebSocket connection tests."""
        all_results = {
            "test_timestamp": datetime.now().isoformat(),
            "basic_connection": {},
            "concurrent_connections": {},
            "heartbeat": {},
            "reconnection": {},
            "message_delivery": {},
            "rate_limiting": {},
            "summary": {}
        }
        
        print("\n" + "="*60)
        print("WEBSOCKET CONNECTION TESTS")
        print("="*60)
        
        # Run tests
        all_results["basic_connection"] = await self.test_basic_connection()
        all_results["concurrent_connections"] = await self.test_concurrent_connections()
        all_results["heartbeat"] = await self.test_heartbeat_mechanism()
        all_results["reconnection"] = await self.test_reconnection_logic()
        all_results["message_delivery"] = await self.test_message_delivery()
        all_results["rate_limiting"] = await self.test_rate_limiting()
        
        # Generate summary
        all_results["summary"] = {
            "total_connections_established": len(self.connections),
            "active_connections": sum(1 for ws in self.connections.values() if ws and not ws.closed),
            "total_messages_processed": sum(stats["messages_sent"] + stats["messages_received"] 
                                           for stats in self.connection_stats.values()),
            "test_logs_count": len(self.test_logs)
        }
        
        return all_results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.level_4
@pytest.mark.asyncio
async def test_dev_environment_websocket_connection():
    """Test WebSocket connection establishment and management."""
    async with WebSocketConnectionTester() as tester:
        results = await tester.run_all_tests()
        
        # Print results
        print("\n" + "="*60)
        print("WEBSOCKET CONNECTION TEST RESULTS")
        print("="*60)
        
        # Basic connection
        basic = results["basic_connection"]
        print(f"\nBasic Connection:")
        print(f"  Connected: {'✓' if basic['connected'] else '✗'}")
        print(f"  Authenticated: {'✓' if basic['authenticated'] else '✗'}")
        print(f"  Connection Time: {basic['connection_time']:.2f}s")
        
        # Concurrent connections
        concurrent = results["concurrent_connections"]
        print(f"\nConcurrent Connections:")
        print(f"  Success: {concurrent['successful_connections']}/{concurrent['target_connections']}")
        print(f"  Avg Time: {concurrent['avg_connection_time']:.2f}s")
        
        # Message delivery
        delivery = results["message_delivery"]
        print(f"\nMessage Delivery:")
        print(f"  Delivery Rate: {delivery['delivery_rate']:.1f}%")
        print(f"  Avg Latency: {delivery['avg_latency']*1000:.1f}ms")
        
        # Assert critical conditions
        assert basic["connected"], "Failed to establish basic WebSocket connection"
        assert concurrent["successful_connections"] >= 5, "Too few concurrent connections succeeded"
        assert delivery["delivery_rate"] >= 80, "Message delivery rate too low"
        
        print("\n[SUCCESS] WebSocket connection tests completed!")

async def main():
    """Run the test standalone."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    async with WebSocketConnectionTester() as tester:
        results = await tester.run_all_tests()
        return 0 if results["basic_connection"]["connected"] else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)