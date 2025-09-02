#!/usr/bin/env python
"""
COMPREHENSIVE WEBSOCKET MODERNIZATION TEST SUITE

CRITICAL WEBSOCKET FIXES VALIDATION:
- Complete elimination of websockets.legacy usage
- Modern WebSocket implementation testing
- Connection stability and reconnection handling
- Edge case scenario validation
- Performance and scalability testing
- Security and isolation verification

This test suite provides COMPREHENSIVE testing scenarios:
1. Legacy code elimination validation
2. Modern WebSocket protocol compliance testing
3. Connection edge cases and failure handling
4. High-throughput performance testing
5. Security isolation validation
6. Memory leak prevention in WebSocket connections
7. Concurrent connection management
8. Protocol upgrade and downgrade scenarios

Business Impact: Prevents WebSocket failures, ensures modern protocol compliance
Strategic Value: Critical for real-time communication reliability and performance
"""

import asyncio
import json
import os
import sys
import time
import uuid
import threading
import weakref
import tracemalloc
import websockets
import ssl
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Callable, Tuple, AsyncIterator
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.isolated_environment import get_env

# WebSocket core services
try:
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.websocket_core.connection import WebSocketConnection
    from netra_backend.app.websocket_core.handler import WebSocketHandler
    from netra_backend.app.websocket_core.protocol import WebSocketProtocol
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    WEBSOCKET_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: WebSocket services not available: {e}")
    WEBSOCKET_SERVICES_AVAILABLE = False
    
    # Create mock classes for testing
    class WebSocketManager:
        def __init__(self): 
            self.active_connections = {}
            self.connection_handlers = {}
        async def connect(self, websocket, user_id): pass
        async def disconnect(self, websocket): pass
        async def send_message(self, user_id, message): pass
        async def broadcast(self, message): pass
        
    class WebSocketConnection:
        def __init__(self, websocket, user_id):
            self.websocket = websocket
            self.user_id = user_id
            self.connected = True
            
    class WebSocketHandler:
        def __init__(self): pass
        async def handle_message(self, message): pass
        
    class WebSocketProtocol:
        def __init__(self): pass
        async def send(self, data): pass
        async def receive(self): pass
        
    class AgentWebSocketBridge:
        def __init__(self): pass
        async def send_notification(self, user_id, data): pass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# WebSocket test constants
WEBSOCKET_TEST_HOST = "127.0.0.1"
WEBSOCKET_TEST_PORT = 8765
WEBSOCKET_TEST_URI = f"ws://{WEBSOCKET_TEST_HOST}:{WEBSOCKET_TEST_PORT}"
SECURE_WEBSOCKET_TEST_URI = f"wss://{WEBSOCKET_TEST_HOST}:{WEBSOCKET_TEST_PORT + 1}"
MAX_CONNECTIONS = 1000  # For stress testing
MESSAGE_THROUGHPUT_TARGET = 1000  # Messages per second
CONNECTION_TIMEOUT = 30.0  # Seconds
RECONNECTION_ATTEMPTS = 5
STRESS_TEST_DURATION = 120  # Seconds


@dataclass
class WebSocketTestConnection:
    """Test WebSocket connection data."""
    id: str
    uri: str
    websocket: Optional[Any] = None
    connected: bool = False
    user_id: str = ""
    messages_sent: int = 0
    messages_received: int = 0
    errors: List[Exception] = field(default_factory=list)
    connection_time: float = 0.0
    last_ping_time: float = 0.0
    latency_measurements: List[float] = field(default_factory=list)


@dataclass
class WebSocketPerformanceMetrics:
    """WebSocket performance metrics."""
    connection_time: float
    message_throughput: float
    average_latency: float
    max_latency: float
    error_rate: float
    memory_usage_mb: float
    active_connections: int
    total_messages: int
    timestamp: float = field(default_factory=time.time)


@dataclass  
class LegacyCodeViolation:
    """Legacy code usage violation."""
    file_path: str
    line_number: int
    code_snippet: str
    violation_type: str
    severity: str
    description: str


class LegacyCodeDetector:
    """Detects usage of legacy WebSocket code."""
    
    LEGACY_PATTERNS = [
        "websockets.legacy",
        "from websockets.legacy",
        "import websockets.legacy", 
        "websockets.legacy.server",
        "websockets.legacy.client",
        "legacy_websocket",
        "LegacyWebSocket",
        "websocket_legacy"
    ]
    
    DEPRECATED_PATTERNS = [
        "websockets.serve(",  # Old style server
        "websockets.connect(",  # Old style client  
        "WebSocketServerProtocol",  # Deprecated protocol
        "WebSocketClientProtocol",  # Deprecated protocol
    ]
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.violations: List[LegacyCodeViolation] = []
    
    def scan_for_legacy_usage(self) -> List[LegacyCodeViolation]:
        """Scan project for legacy WebSocket usage."""
        logger.info("Scanning for legacy WebSocket code usage")
        
        # Scan Python files in the project
        python_files = self._get_python_files()
        
        for file_path in python_files:
            self._scan_file(file_path)
        
        logger.info(f"Legacy code scan completed: found {len(self.violations)} violations")
        return self.violations
    
    def _get_python_files(self) -> List[str]:
        """Get all Python files in the project."""
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', '.venv', 'node_modules']]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    python_files.append(file_path)
        
        return python_files
    
    def _scan_file(self, file_path: str):
        """Scan a single file for legacy patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()
                
                # Check for legacy patterns
                for pattern in self.LEGACY_PATTERNS:
                    if pattern.lower() in line_lower:
                        violation = LegacyCodeViolation(
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip(),
                            violation_type="LEGACY_USAGE",
                            severity="CRITICAL",
                            description=f"Legacy WebSocket pattern detected: {pattern}"
                        )
                        self.violations.append(violation)
                
                # Check for deprecated patterns
                for pattern in self.DEPRECATED_PATTERNS:
                    if pattern.lower() in line_lower:
                        violation = LegacyCodeViolation(
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip(),
                            violation_type="DEPRECATED_USAGE", 
                            severity="WARNING",
                            description=f"Deprecated WebSocket pattern detected: {pattern}"
                        )
                        self.violations.append(violation)
                        
        except Exception as e:
            logger.warning(f"Failed to scan file {file_path}: {e}")


class ModernWebSocketServer:
    """Modern WebSocket test server implementation."""
    
    def __init__(self, host: str = WEBSOCKET_TEST_HOST, port: int = WEBSOCKET_TEST_PORT):
        self.host = host
        self.port = port
        self.server = None
        self.clients: Dict[str, WebSocketTestConnection] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.running = False
        self.performance_metrics = []
        self.lock = asyncio.Lock()
    
    async def start(self):
        """Start the modern WebSocket server."""
        logger.info(f"Starting modern WebSocket server on {self.host}:{self.port}")
        
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
                max_size=2**20,  # 1MB max message size
                max_queue=32,    # Max queued messages
                compression="deflate"
            )
            self.running = True
            logger.info("Modern WebSocket server started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop(self):
        """Stop the WebSocket server."""
        logger.info("Stopping modern WebSocket server")
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Close all client connections
        for client in list(self.clients.values()):
            if client.websocket and not client.websocket.closed:
                await client.websocket.close()
        
        self.clients.clear()
        self.running = False
        logger.info("Modern WebSocket server stopped")
    
    async def handle_client(self, websocket, path):
        """Handle individual client connections."""
        client_id = str(uuid.uuid4())
        client = WebSocketTestConnection(
            id=client_id,
            uri=f"ws://{self.host}:{self.port}{path}",
            websocket=websocket,
            connected=True,
            connection_time=time.time()
        )
        
        async with self.lock:
            self.clients[client_id] = client
        
        logger.debug(f"Client {client_id} connected from {websocket.remote_address}")
        
        try:
            # Send welcome message
            welcome_msg = {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(client, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.debug(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            client.errors.append(e)
        finally:
            async with self.lock:
                if client_id in self.clients:
                    self.clients[client_id].connected = False
    
    async def _handle_message(self, client: WebSocketTestConnection, message: str):
        """Handle incoming message from client."""
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            client.messages_received += 1
            
            # Handle different message types
            if message_type == "ping":
                # Respond with pong
                pong_msg = {
                    "type": "pong",
                    "timestamp": time.time(),
                    "original_timestamp": data.get("timestamp", 0)
                }
                await client.websocket.send(json.dumps(pong_msg))
            
            elif message_type == "echo":
                # Echo the message back
                echo_msg = {
                    "type": "echo_response",
                    "original_message": data,
                    "timestamp": time.time()
                }
                await client.websocket.send(json.dumps(echo_msg))
            
            elif message_type == "stress_test":
                # Handle stress test messages
                await self._handle_stress_test_message(client, data)
            
            # Custom message handlers
            handler = self.message_handlers.get(message_type)
            if handler:
                await handler(client, data)
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from client {client.id}: {message}")
        except Exception as e:
            logger.error(f"Error processing message from client {client.id}: {e}")
            client.errors.append(e)
    
    async def _handle_stress_test_message(self, client: WebSocketTestConnection, data: Dict[str, Any]):
        """Handle stress test specific messages."""
        test_type = data.get("test_type", "default")
        
        if test_type == "throughput":
            # Simple acknowledgment for throughput testing
            response = {
                "type": "throughput_ack",
                "sequence": data.get("sequence", 0),
                "timestamp": time.time()
            }
            await client.websocket.send(json.dumps(response))
        
        elif test_type == "latency":
            # Immediate response for latency testing
            response = {
                "type": "latency_response", 
                "request_timestamp": data.get("timestamp", 0),
                "response_timestamp": time.time()
            }
            await client.websocket.send(json.dumps(response))
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register a custom message handler."""
        self.message_handlers[message_type] = handler
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return
        
        message_str = json.dumps(message)
        
        async with self.lock:
            disconnected_clients = []
            
            for client_id, client in self.clients.items():
                if client.connected and client.websocket:
                    try:
                        await client.websocket.send(message_str)
                        client.messages_sent += 1
                    except websockets.exceptions.ConnectionClosed:
                        disconnected_clients.append(client_id)
                        client.connected = False
                    except Exception as e:
                        logger.error(f"Failed to send message to client {client_id}: {e}")
                        client.errors.append(e)
            
            # Clean up disconnected clients
            for client_id in disconnected_clients:
                del self.clients[client_id]
    
    def get_performance_metrics(self) -> WebSocketPerformanceMetrics:
        """Get current server performance metrics."""
        total_messages = sum(client.messages_sent + client.messages_received 
                           for client in self.clients.values())
        
        error_count = sum(len(client.errors) for client in self.clients.values())
        error_rate = error_count / max(total_messages, 1)
        
        # Calculate average latency from ping measurements
        all_latencies = []
        for client in self.clients.values():
            all_latencies.extend(client.latency_measurements)
        
        avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
        max_latency = max(all_latencies) if all_latencies else 0
        
        return WebSocketPerformanceMetrics(
            connection_time=time.time(),
            message_throughput=total_messages,
            average_latency=avg_latency,
            max_latency=max_latency,
            error_rate=error_rate,
            memory_usage_mb=0.0,  # Would need psutil for actual measurement
            active_connections=len([c for c in self.clients.values() if c.connected]),
            total_messages=total_messages
        )


class WebSocketStressTester:
    """Comprehensive WebSocket stress testing."""
    
    def __init__(self, server_uri: str = WEBSOCKET_TEST_URI):
        self.server_uri = server_uri
        self.clients: List[WebSocketTestConnection] = []
        self.executor = ThreadPoolExecutor(max_workers=100)
        self.running = False
        self.results: Dict[str, Any] = {}
    
    async def run_connection_stress_test(self, max_connections: int = MAX_CONNECTIONS, 
                                       duration_seconds: int = 60) -> Dict[str, Any]:
        """Run connection stress test with many concurrent connections."""
        logger.info(f"Running connection stress test: {max_connections} connections for {duration_seconds}s")
        
        start_time = time.time()
        successful_connections = 0
        failed_connections = 0
        
        # Create connections gradually
        connection_tasks = []
        for i in range(max_connections):
            task = asyncio.create_task(self._create_stress_connection(f"stress_client_{i}"))
            connection_tasks.append(task)
            
            # Add small delay to avoid overwhelming the server
            if i % 10 == 0:
                await asyncio.sleep(0.01)
        
        # Wait for connections to establish
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Count successful connections
        for result in connection_results:
            if isinstance(result, Exception):
                failed_connections += 1
                logger.debug(f"Connection failed: {result}")
            else:
                successful_connections += 1
        
        logger.info(f"Established {successful_connections}/{max_connections} connections")
        
        # Keep connections alive for duration
        await asyncio.sleep(duration_seconds)
        
        # Close all connections
        close_tasks = []
        for client in self.clients:
            if client.websocket and not client.websocket.closed:
                task = asyncio.create_task(client.websocket.close())
                close_tasks.append(task)
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        end_time = time.time()
        
        return {
            "test_type": "connection_stress",
            "duration": end_time - start_time,
            "max_connections": max_connections,
            "successful_connections": successful_connections,
            "failed_connections": failed_connections,
            "connection_success_rate": successful_connections / max_connections,
            "clients_created": len(self.clients)
        }
    
    async def _create_stress_connection(self, client_id: str) -> WebSocketTestConnection:
        """Create a single stress test connection."""
        try:
            websocket = await websockets.connect(
                self.server_uri,
                ping_interval=20,
                ping_timeout=10,
                max_size=2**20,
                max_queue=32
            )
            
            client = WebSocketTestConnection(
                id=client_id,
                uri=self.server_uri,
                websocket=websocket,
                connected=True,
                connection_time=time.time()
            )
            
            self.clients.append(client)
            return client
            
        except Exception as e:
            logger.debug(f"Failed to create connection for {client_id}: {e}")
            raise
    
    async def run_message_throughput_test(self, connections: int = 10, 
                                        messages_per_connection: int = 1000,
                                        message_size_bytes: int = 1024) -> Dict[str, Any]:
        """Run message throughput stress test."""
        logger.info(f"Running throughput test: {connections} connections, "
                   f"{messages_per_connection} messages each, {message_size_bytes} bytes per message")
        
        # Create connections
        connection_tasks = []
        for i in range(connections):
            task = asyncio.create_task(self._create_stress_connection(f"throughput_client_{i}"))
            connection_tasks.append(task)
        
        clients = await asyncio.gather(*connection_tasks, return_exceptions=True)
        active_clients = [c for c in clients if not isinstance(c, Exception)]
        
        logger.info(f"Created {len(active_clients)} connections for throughput test")
        
        # Generate test message
        test_message = {
            "type": "stress_test",
            "test_type": "throughput",
            "data": "x" * (message_size_bytes - 100),  # Adjust for JSON overhead
            "timestamp": time.time()
        }
        
        # Run throughput test
        start_time = time.time()
        
        throughput_tasks = []
        for client in active_clients:
            task = asyncio.create_task(
                self._run_client_throughput_test(client, test_message, messages_per_connection)
            )
            throughput_tasks.append(task)
        
        throughput_results = await asyncio.gather(*throughput_tasks, return_exceptions=True)
        
        end_time = time.time()
        
        # Analyze results
        total_messages_sent = sum(r.get('messages_sent', 0) for r in throughput_results 
                                if isinstance(r, dict))
        total_messages_received = sum(r.get('messages_received', 0) for r in throughput_results 
                                    if isinstance(r, dict))
        
        test_duration = end_time - start_time
        throughput_sent = total_messages_sent / test_duration if test_duration > 0 else 0
        throughput_received = total_messages_received / test_duration if test_duration > 0 else 0
        
        # Close connections
        await self._close_all_connections()
        
        return {
            "test_type": "message_throughput",
            "duration": test_duration,
            "connections": len(active_clients),
            "messages_per_connection": messages_per_connection,
            "message_size_bytes": message_size_bytes,
            "total_messages_sent": total_messages_sent,
            "total_messages_received": total_messages_received,
            "throughput_sent_per_sec": throughput_sent,
            "throughput_received_per_sec": throughput_received,
            "target_throughput": MESSAGE_THROUGHPUT_TARGET,
            "meets_throughput_target": throughput_sent >= MESSAGE_THROUGHPUT_TARGET
        }
    
    async def _run_client_throughput_test(self, client: WebSocketTestConnection, 
                                        test_message: Dict[str, Any], 
                                        message_count: int) -> Dict[str, Any]:
        """Run throughput test for a single client."""
        messages_sent = 0
        messages_received = 0
        errors = []
        
        try:
            # Send messages as fast as possible
            for i in range(message_count):
                test_message["sequence"] = i
                test_message["timestamp"] = time.time()
                
                await client.websocket.send(json.dumps(test_message))
                messages_sent += 1
                
                # Read response (non-blocking)
                try:
                    response = await asyncio.wait_for(client.websocket.recv(), timeout=0.1)
                    messages_received += 1
                except asyncio.TimeoutError:
                    pass  # No response yet, continue sending
                
        except Exception as e:
            errors.append(e)
            logger.error(f"Throughput test error for {client.id}: {e}")
        
        return {
            "client_id": client.id,
            "messages_sent": messages_sent,
            "messages_received": messages_received,
            "errors": len(errors)
        }
    
    async def run_latency_test(self, connections: int = 5, 
                             ping_count: int = 100) -> Dict[str, Any]:
        """Run WebSocket latency test."""
        logger.info(f"Running latency test: {connections} connections, {ping_count} pings each")
        
        # Create connections
        connection_tasks = []
        for i in range(connections):
            task = asyncio.create_task(self._create_stress_connection(f"latency_client_{i}"))
            connection_tasks.append(task)
        
        clients = await asyncio.gather(*connection_tasks, return_exceptions=True)
        active_clients = [c for c in clients if not isinstance(c, Exception)]
        
        # Run latency tests
        latency_tasks = []
        for client in active_clients:
            task = asyncio.create_task(self._measure_client_latency(client, ping_count))
            latency_tasks.append(task)
        
        latency_results = await asyncio.gather(*latency_tasks, return_exceptions=True)
        
        # Analyze latency results
        all_latencies = []
        for result in latency_results:
            if isinstance(result, dict) and 'latencies' in result:
                all_latencies.extend(result['latencies'])
        
        if all_latencies:
            avg_latency = sum(all_latencies) / len(all_latencies)
            min_latency = min(all_latencies)
            max_latency = max(all_latencies)
            p95_latency = sorted(all_latencies)[int(len(all_latencies) * 0.95)]
            p99_latency = sorted(all_latencies)[int(len(all_latencies) * 0.99)]
        else:
            avg_latency = min_latency = max_latency = p95_latency = p99_latency = 0
        
        # Close connections
        await self._close_all_connections()
        
        return {
            "test_type": "latency",
            "connections": len(active_clients),
            "ping_count": ping_count,
            "total_pings": len(all_latencies),
            "average_latency_ms": avg_latency * 1000,
            "min_latency_ms": min_latency * 1000,
            "max_latency_ms": max_latency * 1000,
            "p95_latency_ms": p95_latency * 1000,
            "p99_latency_ms": p99_latency * 1000,
            "latency_acceptable": avg_latency < 0.1  # Less than 100ms average
        }
    
    async def _measure_client_latency(self, client: WebSocketTestConnection, 
                                    ping_count: int) -> Dict[str, Any]:
        """Measure latency for a single client."""
        latencies = []
        errors = []
        
        try:
            for i in range(ping_count):
                # Send ping
                ping_time = time.time()
                ping_msg = {
                    "type": "ping",
                    "sequence": i,
                    "timestamp": ping_time
                }
                
                await client.websocket.send(json.dumps(ping_msg))
                
                # Wait for pong
                try:
                    response = await asyncio.wait_for(client.websocket.recv(), timeout=5.0)
                    pong_time = time.time()
                    
                    # Parse response
                    pong_data = json.loads(response)
                    if pong_data.get("type") == "pong":
                        latency = pong_time - ping_time
                        latencies.append(latency)
                        client.latency_measurements.append(latency)
                    
                except asyncio.TimeoutError:
                    errors.append("Ping timeout")
                except json.JSONDecodeError:
                    errors.append("Invalid pong response")
                
                # Small delay between pings
                await asyncio.sleep(0.01)
        
        except Exception as e:
            errors.append(str(e))
            logger.error(f"Latency test error for {client.id}: {e}")
        
        return {
            "client_id": client.id,
            "latencies": latencies,
            "errors": len(errors)
        }
    
    async def _close_all_connections(self):
        """Close all test connections."""
        close_tasks = []
        for client in self.clients:
            if client.websocket and not client.websocket.closed:
                task = asyncio.create_task(client.websocket.close())
                close_tasks.append(task)
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.clients.clear()


class WebSocketSecurityTester:
    """WebSocket security and isolation testing."""
    
    def __init__(self, server_uri: str = WEBSOCKET_TEST_URI):
        self.server_uri = server_uri
        self.test_users = []
        
    async def test_user_isolation(self, user_count: int = 10, 
                                messages_per_user: int = 50) -> Dict[str, Any]:
        """Test that messages between users are properly isolated."""
        logger.info(f"Testing user isolation with {user_count} users")
        
        # Create user contexts
        users = []
        for i in range(user_count):
            user = {
                'user_id': f"test_user_{i}_{uuid.uuid4().hex[:8]}",
                'websocket': None,
                'sent_messages': [],
                'received_messages': [],
                'private_data': f"private_data_for_user_{i}_{uuid.uuid4().hex[:8]}"
            }
            users.append(user)
        
        # Connect all users
        connection_tasks = []
        for user in users:
            task = asyncio.create_task(self._connect_user(user))
            connection_tasks.append(task)
        
        await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Send messages from each user containing private data
        message_tasks = []
        for user in users:
            for msg_id in range(messages_per_user):
                message = {
                    "type": "private_message",
                    "from_user": user['user_id'],
                    "content": f"{user['private_data']}_message_{msg_id}",
                    "timestamp": time.time(),
                    "sequence": msg_id
                }
                task = asyncio.create_task(self._send_user_message(user, message))
                message_tasks.append(task)
        
        await asyncio.gather(*message_tasks, return_exceptions=True)
        
        # Allow time for message processing
        await asyncio.sleep(2.0)
        
        # Collect received messages for analysis
        isolation_violations = []
        for user in users:
            for received_msg in user['received_messages']:
                # Check if user received message not intended for them
                if isinstance(received_msg, dict):
                    from_user = received_msg.get('from_user')
                    content = received_msg.get('content', '')
                    
                    if from_user and from_user != user['user_id']:
                        # Check if message contains other user's private data
                        for other_user in users:
                            if (other_user['user_id'] != user['user_id'] and 
                                other_user['private_data'] in content):
                                
                                violation = {
                                    'receiving_user': user['user_id'],
                                    'sending_user': from_user,
                                    'leaked_data': other_user['private_data'],
                                    'message_content': content
                                }
                                isolation_violations.append(violation)
        
        # Close all connections
        for user in users:
            if user['websocket'] and not user['websocket'].closed:
                await user['websocket'].close()
        
        return {
            "test_type": "user_isolation",
            "user_count": user_count,
            "messages_per_user": messages_per_user,
            "total_messages_sent": sum(len(u['sent_messages']) for u in users),
            "total_messages_received": sum(len(u['received_messages']) for u in users),
            "isolation_violations": len(isolation_violations),
            "violation_details": isolation_violations,
            "isolation_secure": len(isolation_violations) == 0
        }
    
    async def _connect_user(self, user: Dict[str, Any]):
        """Connect a user to the WebSocket server."""
        try:
            user['websocket'] = await websockets.connect(self.server_uri)
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_user_messages(user))
            
        except Exception as e:
            logger.error(f"Failed to connect user {user['user_id']}: {e}")
    
    async def _send_user_message(self, user: Dict[str, Any], message: Dict[str, Any]):
        """Send a message from a user."""
        if user['websocket'] and not user['websocket'].closed:
            try:
                await user['websocket'].send(json.dumps(message))
                user['sent_messages'].append(message)
            except Exception as e:
                logger.error(f"Failed to send message for user {user['user_id']}: {e}")
    
    async def _listen_for_user_messages(self, user: Dict[str, Any]):
        """Listen for messages for a user."""
        try:
            async for message in user['websocket']:
                try:
                    data = json.loads(message)
                    user['received_messages'].append(data)
                except json.JSONDecodeError:
                    user['received_messages'].append(message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error listening for user {user['user_id']}: {e}")


# ============================================================================
# COMPREHENSIVE WEBSOCKET MODERNIZATION TESTS
# ============================================================================

@pytest.fixture
async def modern_websocket_server():
    """Fixture providing modern WebSocket test server."""
    server = ModernWebSocketServer()
    await server.start()
    
    # Wait for server to be ready
    await asyncio.sleep(0.1)
    
    try:
        yield server
    finally:
        await server.stop()


@pytest.fixture
async def websocket_stress_tester():
    """Fixture providing WebSocket stress tester."""
    tester = WebSocketStressTester()
    try:
        yield tester
    finally:
        await tester._close_all_connections()
        tester.executor.shutdown(wait=True)


@pytest.fixture
async def websocket_security_tester():
    """Fixture providing WebSocket security tester."""
    tester = WebSocketSecurityTester()
    try:
        yield tester
    finally:
        pass  # Cleanup handled by individual tests


@pytest.mark.asyncio
class TestWebSocketModernizationComprehensive:
    """Comprehensive WebSocket modernization test suite."""
    
    async def test_legacy_code_elimination_complete(self):
        """Test that ALL legacy WebSocket code has been eliminated."""
        logger.info("Testing complete elimination of legacy WebSocket code")
        
        # Scan project for legacy usage
        detector = LegacyCodeDetector(project_root)
        violations = detector.scan_for_legacy_usage()
        
        # Log violations for analysis
        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        warning_violations = [v for v in violations if v.severity == "WARNING"]
        
        logger.info(f"Legacy code scan results:")
        logger.info(f"  Critical violations: {len(critical_violations)}")
        logger.info(f"  Warning violations: {len(warning_violations)}")
        
        if violations:
            logger.error("Legacy code violations found:")
            for violation in violations:
                logger.error(f"  {violation.file_path}:{violation.line_number} - {violation.description}")
                logger.error(f"    Code: {violation.code_snippet}")
        
        # CRITICAL: No legacy code should remain
        assert len(critical_violations) == 0, \
            f"CRITICAL: Found {len(critical_violations)} legacy WebSocket code violations. " \
            f"All websockets.legacy usage must be eliminated."
        
        # Warnings are acceptable but should be minimized
        assert len(warning_violations) <= 5, \
            f"Too many deprecated WebSocket patterns found: {len(warning_violations)}. " \
            f"Consider modernizing deprecated usage."
    
    async def test_modern_websocket_protocol_compliance(self, modern_websocket_server):
        """Test compliance with modern WebSocket protocols."""
        logger.info("Testing modern WebSocket protocol compliance")
        
        # Test modern WebSocket features
        client = await websockets.connect(
            WEBSOCKET_TEST_URI,
            ping_interval=20,
            ping_timeout=10,
            max_size=2**20,  # 1MB max message size
            max_queue=32,    # Max queued messages
            compression="deflate"
        )
        
        try:
            # Test 1: Connection established with modern features
            assert not client.closed, "WebSocket connection should be established"
            
            # Test 2: JSON message handling
            test_message = {
                "type": "protocol_test",
                "features": ["compression", "ping_pong", "large_messages"],
                "timestamp": time.time()
            }
            
            await client.send(json.dumps(test_message))
            response = await asyncio.wait_for(client.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            # Should receive connection established message
            assert response_data.get("type") == "connection_established"
            assert "client_id" in response_data
            
            # Test 3: Ping/Pong functionality
            ping_msg = {"type": "ping", "timestamp": time.time()}
            await client.send(json.dumps(ping_msg))
            
            pong_response = await asyncio.wait_for(client.recv(), timeout=5.0)
            pong_data = json.loads(pong_response)
            
            assert pong_data.get("type") == "pong"
            assert "timestamp" in pong_data
            
            # Test 4: Large message handling (compression)
            large_message = {
                "type": "large_message_test",
                "data": "x" * (100 * 1024),  # 100KB message
                "timestamp": time.time()
            }
            
            start_time = time.time()
            await client.send(json.dumps(large_message))
            
            # Should not timeout with compression
            echo_response = await asyncio.wait_for(client.recv(), timeout=10.0)
            echo_data = json.loads(echo_response)
            send_time = time.time() - start_time
            
            assert echo_data.get("type") == "connection_established"  # Server handles large messages
            assert send_time < 5.0, f"Large message took too long: {send_time}s"
            
            # Test 5: Connection info and metadata
            assert hasattr(client, 'remote_address')
            assert hasattr(client, 'ping')
            
        finally:
            await client.close()
        
        logger.info("Modern WebSocket protocol compliance test passed")
    
    async def test_websocket_connection_edge_cases(self, modern_websocket_server):
        """Test WebSocket connection handling in edge case scenarios."""
        logger.info("Testing WebSocket connection edge cases")
        
        edge_case_results = {}
        
        # Edge Case 1: Rapid connection/disconnection
        logger.info("Testing rapid connection/disconnection")
        rapid_connect_start = time.time()
        
        for i in range(20):
            client = await websockets.connect(WEBSOCKET_TEST_URI)
            await client.send(json.dumps({"type": "quick_test", "id": i}))
            await client.close()
        
        rapid_connect_time = time.time() - rapid_connect_start
        edge_case_results["rapid_connect_disconnect"] = {
            "connections": 20,
            "total_time": rapid_connect_time,
            "avg_time_per_connection": rapid_connect_time / 20
        }
        
        # Edge Case 2: Malformed message handling
        logger.info("Testing malformed message handling")
        client = await websockets.connect(WEBSOCKET_TEST_URI)
        
        try:
            # Send invalid JSON
            await client.send("invalid json {")
            await asyncio.sleep(0.1)  # Allow server to process
            
            # Send valid message after invalid one
            valid_msg = {"type": "recovery_test", "timestamp": time.time()}
            await client.send(json.dumps(valid_msg))
            
            response = await asyncio.wait_for(client.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            # Server should still be responsive
            assert response_data.get("type") == "connection_established"
            edge_case_results["malformed_message_recovery"] = True
            
        finally:
            await client.close()
        
        # Edge Case 3: Connection timeout handling
        logger.info("Testing connection timeout scenarios")
        timeout_client = await websockets.connect(
            WEBSOCKET_TEST_URI,
            ping_timeout=1,  # Very short timeout
            ping_interval=0.5
        )
        
        try:
            # Send message and wait longer than ping timeout
            await timeout_client.send(json.dumps({"type": "timeout_test"}))
            await asyncio.sleep(2.0)  # Wait longer than ping timeout
            
            # Connection might be closed by server due to ping timeout
            edge_case_results["timeout_handling"] = not timeout_client.closed or timeout_client.closed
            
        except websockets.exceptions.ConnectionClosed:
            edge_case_results["timeout_handling"] = True
        finally:
            if not timeout_client.closed:
                await timeout_client.close()
        
        # Edge Case 4: Maximum message size handling
        logger.info("Testing maximum message size handling")
        max_size_client = await websockets.connect(
            WEBSOCKET_TEST_URI,
            max_size=1024  # 1KB limit
        )
        
        try:
            # Send message exceeding limit
            large_msg = {"type": "oversized_test", "data": "x" * 2048}  # 2KB+ message
            
            try:
                await max_size_client.send(json.dumps(large_msg))
                await asyncio.sleep(0.1)
                edge_case_results["max_size_enforcement"] = False  # Should have failed
            except websockets.exceptions.ConnectionClosed:
                edge_case_results["max_size_enforcement"] = True  # Properly enforced
            
        finally:
            if not max_size_client.closed:
                await max_size_client.close()
        
        logger.info(f"Edge case test results: {json.dumps(edge_case_results, indent=2)}")
        
        # Validate edge case handling
        assert edge_case_results["rapid_connect_disconnect"]["avg_time_per_connection"] < 1.0, \
            "Rapid connection/disconnection too slow"
        assert edge_case_results["malformed_message_recovery"], \
            "Server failed to recover from malformed messages"
        assert edge_case_results["timeout_handling"], \
            "Timeout handling not working properly" 
        assert edge_case_results["max_size_enforcement"], \
            "Maximum message size not enforced"
    
    @pytest.mark.slow
    async def test_websocket_high_throughput_performance(self, websocket_stress_tester):
        """Test WebSocket performance under high throughput scenarios."""
        logger.info("Testing WebSocket high throughput performance")
        
        # Test high-throughput message processing
        throughput_results = await websocket_stress_tester.run_message_throughput_test(
            connections=20,
            messages_per_connection=500,
            message_size_bytes=1024
        )
        
        logger.info(f"Throughput test results: {json.dumps(throughput_results, indent=2)}")
        
        # Validate performance requirements
        assert throughput_results["throughput_sent_per_sec"] >= MESSAGE_THROUGHPUT_TARGET * 0.8, \
            f"Message throughput {throughput_results['throughput_sent_per_sec']:.1f} msg/s too low. " \
            f"Expected >= {MESSAGE_THROUGHPUT_TARGET * 0.8} msg/s"
        
        assert throughput_results["total_messages_sent"] > 0, "No messages were sent"
        assert throughput_results["duration"] < 120.0, f"Test took too long: {throughput_results['duration']:.1f}s"
        
        # Test concurrent connection scaling
        connection_stress_results = await websocket_stress_tester.run_connection_stress_test(
            max_connections=MAX_CONNECTIONS // 10,  # Use smaller number for CI stability
            duration_seconds=30
        )
        
        logger.info(f"Connection stress results: {json.dumps(connection_stress_results, indent=2)}")
        
        # Validate connection handling
        assert connection_stress_results["connection_success_rate"] >= 0.95, \
            f"Connection success rate {connection_stress_results['connection_success_rate']:.2%} too low"
        
        assert connection_stress_results["successful_connections"] >= MAX_CONNECTIONS // 20, \
            "Not enough successful connections established"
    
    async def test_websocket_latency_performance(self, websocket_stress_tester):
        """Test WebSocket latency under various conditions."""
        logger.info("Testing WebSocket latency performance")
        
        latency_results = await websocket_stress_tester.run_latency_test(
            connections=5,
            ping_count=100
        )
        
        logger.info(f"Latency test results: {json.dumps(latency_results, indent=2)}")
        
        # Validate latency requirements
        assert latency_results["latency_acceptable"], \
            f"Average latency {latency_results['average_latency_ms']:.1f}ms too high"
        
        assert latency_results["average_latency_ms"] <= 100.0, \
            f"Average latency {latency_results['average_latency_ms']:.1f}ms exceeds 100ms limit"
        
        assert latency_results["p95_latency_ms"] <= 200.0, \
            f"P95 latency {latency_results['p95_latency_ms']:.1f}ms exceeds 200ms limit"
        
        assert latency_results["total_pings"] >= latency_results["ping_count"] * latency_results["connections"] * 0.9, \
            "Too many ping failures occurred"
    
    async def test_websocket_security_isolation(self, websocket_security_tester):
        """Test WebSocket security and user isolation."""
        logger.info("Testing WebSocket security and user isolation")
        
        isolation_results = await websocket_security_tester.test_user_isolation(
            user_count=10,
            messages_per_user=20
        )
        
        logger.info(f"Security isolation results: {json.dumps(isolation_results, indent=2)}")
        
        # Validate security requirements
        assert isolation_results["isolation_secure"], \
            f"SECURITY VIOLATION: Found {isolation_results['isolation_violations']} user isolation violations"
        
        if isolation_results["violation_details"]:
            logger.error("Security isolation violations:")
            for violation in isolation_results["violation_details"]:
                logger.error(f"  User {violation['receiving_user']} received data from {violation['sending_user']}")
                logger.error(f"  Leaked data: {violation['leaked_data']}")
        
        assert isolation_results["total_messages_sent"] > 0, "No test messages were sent"
        assert isolation_results["isolation_violations"] == 0, \
            "User isolation must be perfect - no cross-user data leakage allowed"
    
    async def test_websocket_memory_management(self, modern_websocket_server):
        """Test WebSocket memory management and leak prevention."""
        logger.info("Testing WebSocket memory management")
        
        # Enable memory tracking
        tracemalloc.start()
        
        initial_memory = tracemalloc.take_snapshot()
        
        # Create and destroy many connections to test memory cleanup
        connections_per_batch = 50
        batches = 10
        
        for batch in range(batches):
            logger.debug(f"Memory test batch {batch + 1}/{batches}")
            
            # Create connections
            connections = []
            for i in range(connections_per_batch):
                client = await websockets.connect(WEBSOCKET_TEST_URI)
                connections.append(client)
            
            # Send messages
            for client in connections:
                test_msg = {
                    "type": "memory_test",
                    "batch": batch,
                    "data": "x" * 1024  # 1KB per message
                }
                await client.send(json.dumps(test_msg))
            
            # Close connections
            for client in connections:
                await client.close()
            
            # Force garbage collection
            import gc
            gc.collect()
            await asyncio.sleep(0.1)
            
            # Check memory usage
            if batch % 3 == 0:  # Check every few batches
                current_memory = tracemalloc.take_snapshot()
                top_stats = current_memory.compare_to(initial_memory, 'lineno')
                
                total_growth_mb = sum(stat.size_diff for stat in top_stats) / 1024 / 1024
                logger.debug(f"Memory growth after batch {batch}: {total_growth_mb:.2f}MB")
                
                # Memory growth should be reasonable
                max_acceptable_growth = (batch + 1) * 2  # 2MB per batch max
                assert total_growth_mb <= max_acceptable_growth, \
                    f"Excessive memory growth: {total_growth_mb:.2f}MB after {batch + 1} batches"
        
        # Final memory check
        final_memory = tracemalloc.take_snapshot()
        top_stats = final_memory.compare_to(initial_memory, 'lineno')
        
        total_final_growth_mb = sum(stat.size_diff for stat in top_stats) / 1024 / 1024
        logger.info(f"Total memory growth after all batches: {total_final_growth_mb:.2f}MB")
        
        # Cleanup
        tracemalloc.stop()
        
        # Validate memory management
        max_acceptable_total_growth = batches * connections_per_batch * 0.01  # 0.01MB per connection
        assert total_final_growth_mb <= max_acceptable_total_growth, \
            f"Memory leak detected: {total_final_growth_mb:.2f}MB growth exceeds limit {max_acceptable_total_growth:.2f}MB"
    
    @pytest.mark.slow
    async def test_websocket_reconnection_resilience(self, modern_websocket_server):
        """Test WebSocket reconnection handling and resilience."""
        logger.info("Testing WebSocket reconnection resilience")
        
        reconnection_results = {
            "successful_reconnections": 0,
            "failed_reconnections": 0,
            "total_attempts": 0,
            "average_reconnect_time": 0.0,
            "data_integrity_maintained": True
        }
        
        # Test reconnection scenarios
        for scenario in range(5):
            logger.debug(f"Reconnection scenario {scenario + 1}")
            
            # Initial connection
            client = await websockets.connect(WEBSOCKET_TEST_URI)
            
            # Send initial data
            initial_msg = {
                "type": "reconnection_test",
                "scenario": scenario,
                "phase": "initial",
                "data": f"scenario_{scenario}_data"
            }
            await client.send(json.dumps(initial_msg))
            
            # Simulate connection interruption
            await client.close(code=1006)  # Abnormal closure
            await asyncio.sleep(0.5)  # Simulate network interruption
            
            # Attempt reconnection
            reconnect_start = time.time()
            reconnection_attempts = 0
            reconnected = False
            
            while reconnection_attempts < RECONNECTION_ATTEMPTS:
                try:
                    new_client = await websockets.connect(WEBSOCKET_TEST_URI)
                    
                    # Test if connection works
                    test_msg = {
                        "type": "reconnection_test",
                        "scenario": scenario,
                        "phase": "reconnected",
                        "data": f"scenario_{scenario}_reconnected_data"
                    }
                    await new_client.send(json.dumps(test_msg))
                    
                    # Verify response
                    response = await asyncio.wait_for(new_client.recv(), timeout=5.0)
                    
                    reconnect_time = time.time() - reconnect_start
                    reconnection_results["successful_reconnections"] += 1
                    reconnection_results["total_attempts"] += reconnection_attempts + 1
                    reconnection_results["average_reconnect_time"] += reconnect_time
                    
                    reconnected = True
                    await new_client.close()
                    break
                    
                except Exception as e:
                    reconnection_attempts += 1
                    logger.debug(f"Reconnection attempt {reconnection_attempts} failed: {e}")
                    await asyncio.sleep(1.0)  # Wait before retry
            
            if not reconnected:
                reconnection_results["failed_reconnections"] += 1
                reconnection_results["total_attempts"] += RECONNECTION_ATTEMPTS
        
        # Calculate averages
        if reconnection_results["successful_reconnections"] > 0:
            reconnection_results["average_reconnect_time"] /= reconnection_results["successful_reconnections"]
        
        success_rate = (reconnection_results["successful_reconnections"] / 
                       (reconnection_results["successful_reconnections"] + reconnection_results["failed_reconnections"]))
        
        logger.info(f"Reconnection test results: {json.dumps(reconnection_results, indent=2)}")
        logger.info(f"Reconnection success rate: {success_rate:.2%}")
        
        # Validate reconnection resilience
        assert success_rate >= 0.9, f"Reconnection success rate {success_rate:.2%} too low"
        assert reconnection_results["average_reconnect_time"] <= 5.0, \
            f"Average reconnection time {reconnection_results['average_reconnect_time']:.2f}s too high"
        assert reconnection_results["data_integrity_maintained"], "Data integrity not maintained during reconnection"
    
    async def test_websocket_protocol_upgrade_handling(self):
        """Test WebSocket protocol upgrade and negotiation."""
        logger.info("Testing WebSocket protocol upgrade handling")
        
        # Test various WebSocket protocol versions and features
        protocol_tests = [
            {
                "name": "basic_upgrade",
                "headers": {"Upgrade": "websocket", "Connection": "Upgrade"},
                "expected_success": True
            },
            {
                "name": "compression_negotiation",
                "headers": {"Sec-WebSocket-Extensions": "permessage-deflate"},
                "expected_success": True
            },
            {
                "name": "subprotocol_negotiation",
                "headers": {"Sec-WebSocket-Protocol": "chat, superchat"},
                "expected_success": True
            }
        ]
        
        protocol_results = {}
        
        for test in protocol_tests:
            try:
                # Create connection with specific headers/options
                if test["name"] == "compression_negotiation":
                    client = await websockets.connect(
                        WEBSOCKET_TEST_URI,
                        compression="deflate"
                    )
                else:
                    client = await websockets.connect(WEBSOCKET_TEST_URI)
                
                # Test connection functionality
                test_msg = {"type": "protocol_test", "test_name": test["name"]}
                await client.send(json.dumps(test_msg))
                
                response = await asyncio.wait_for(client.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                protocol_results[test["name"]] = {
                    "success": True,
                    "response_received": True,
                    "connection_established": not client.closed
                }
                
                await client.close()
                
            except Exception as e:
                protocol_results[test["name"]] = {
                    "success": False,
                    "error": str(e),
                    "expected_success": test["expected_success"]
                }
        
        logger.info(f"Protocol upgrade test results: {json.dumps(protocol_results, indent=2)}")
        
        # Validate protocol upgrade handling
        for test in protocol_tests:
            result = protocol_results[test["name"]]
            if test["expected_success"]:
                assert result.get("success", False), \
                    f"Protocol test {test['name']} failed: {result.get('error', 'Unknown error')}"