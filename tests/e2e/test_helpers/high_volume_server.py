"""
High-volume WebSocket server infrastructure for throughput testing.

This module provides mock server and client infrastructure for testing
high-volume message throughput and system scalability.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Set

import psutil
import websockets

from tests.e2e.fixtures.throughput_metrics import HIGH_VOLUME_CONFIG

logger = logging.getLogger(__name__)


class HighVolumeWebSocketServer:
    """High-performance mock WebSocket server for throughput testing."""
    
    def __init__(self, port=8765, max_connections=1000):
        self.port = port
        self.max_connections = max_connections
        self.server = None
        self.clients = set()
        self.message_counter = 0
        self.processed_messages = {}
        self.queue_depth = 0
        self.start_time = time.time()
        
        # Performance tracking
        self.throughput_history = []
        self.latency_history = []
        self.error_count = 0
        self.backpressure_triggered = False
        
        # Resource monitoring
        self.initial_memory = psutil.Process().memory_info().rss
        self.peak_memory = self.initial_memory
        
    async def start(self):
        """Start high-performance WebSocket server."""
        self.server = await websockets.serve(
            self.handle_client,
            "localhost",
            self.port,
            max_size=2**20,  # 1MB max message size
            max_queue=1000,   # High connection queue
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        )
        logger.info(f"High-volume WebSocket server started on ws://localhost:{self.port}")
        
        # Start background monitoring
        asyncio.create_task(self._monitor_performance())
        
    async def stop(self):
        """Stop WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("High-volume WebSocket server stopped")
            
    async def handle_client(self, websocket):
        """Handle WebSocket client connections with high throughput."""
        if len(self.clients) >= self.max_connections:
            await websocket.close(code=1013, reason="Server overloaded")
            return
            
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.debug(f"Client {client_id} connected ({len(self.clients)} total)")
        
        try:
            async for message in websocket:
                await self._process_message_high_volume(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Client {client_id} error: {e}")
            self.error_count += 1
        finally:
            self.clients.discard(websocket)
            logger.debug(f"Client {client_id} disconnected ({len(self.clients)} total)")
    
    async def _process_message_high_volume(self, websocket, message):
        """Process messages with high-volume optimizations."""
        try:
            # Parse message
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            message_id = data.get("message_id", f"auto-{self.message_counter}")
            
            self.message_counter += 1
            current_time = time.time()
            
            # Check for backpressure conditions
            if self.queue_depth > HIGH_VOLUME_CONFIG["queue_overflow_threshold"]:
                if not self.backpressure_triggered:
                    self.backpressure_triggered = True
                    await self._send_backpressure_signal(websocket, data)
                    return
            else:
                self.backpressure_triggered = False
            
            # Simulate queue processing
            self.queue_depth += 1
            
            # Fast path for high-volume messages
            if message_type == "user_message":
                await self._handle_user_message_optimized(websocket, data, current_time)
            elif message_type == "throughput_test":
                await self._handle_throughput_test(websocket, data, current_time)
            elif message_type == "latency_probe":
                await self._handle_latency_probe(websocket, data, current_time)
            elif message_type == "get_performance_stats":
                await self._send_performance_stats(websocket)
            else:
                # Generic handler for other message types
                await self._handle_generic_message(websocket, data, current_time)
                
            self.queue_depth = max(0, self.queue_depth - 1)
            
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON format",
                "timestamp": time.time()
            }))
            self.error_count += 1
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            self.error_count += 1
    
    async def _handle_user_message_optimized(self, websocket, data, current_time):
        """Optimized user message handling for high throughput."""
        message_id = data.get("message_id")
        
        # Idempotency check
        if message_id in self.processed_messages:
            await websocket.send(json.dumps({
                "type": "duplicate_rejected",
                "message_id": message_id,
                "original_timestamp": self.processed_messages[message_id],
                "timestamp": current_time
            }))
            return
        
        # Record processing
        self.processed_messages[message_id] = current_time
        
        # Simulate minimal processing delay
        processing_start = time.perf_counter()
        await asyncio.sleep(0.001)  # 1ms simulated processing
        processing_end = time.perf_counter()
        
        # Send response
        response = {
            "type": "ai_response",
            "message_id": message_id,
            "sequence_id": data.get("sequence_id"),
            "content": f"High-volume response to: {data.get('content', 'unknown')[:50]}...",
            "processing_time": processing_end - processing_start,
            "server_timestamp": current_time,
            "queue_depth": self.queue_depth,
            "timestamp": time.time()
        }
        
        await websocket.send(json.dumps(response))
    
    async def _handle_throughput_test(self, websocket, data, current_time):
        """Handle throughput test messages with minimal overhead."""
        message_id = data.get("message_id")
        sequence_id = data.get("sequence_id", 0)
        
        # Ultra-fast response for throughput testing
        response = {
            "type": "throughput_response",
            "message_id": message_id,
            "sequence_id": sequence_id,
            "server_time": current_time,
            "queue_depth": self.queue_depth
        }
        
        await websocket.send(json.dumps(response))
    
    async def _handle_latency_probe(self, websocket, data, current_time):
        """Handle latency probe messages with precise timing."""
        message_id = data.get("message_id")
        client_send_time = data.get("send_time", current_time)
        
        # Precise timing response
        response = {
            "type": "latency_response", 
            "message_id": message_id,
            "client_send_time": client_send_time,
            "server_receive_time": current_time,
            "server_send_time": time.time(),
            "queue_depth": self.queue_depth
        }
        
        await websocket.send(json.dumps(response))
    
    async def _handle_generic_message(self, websocket, data, current_time):
        """Generic message handler for compatibility."""
        response = {
            "type": "generic_response",
            "message_id": data.get("message_id"),
            "echo": data,
            "timestamp": current_time
        }
        await websocket.send(json.dumps(response))
    
    async def _send_backpressure_signal(self, websocket, data):
        """Send backpressure signal to client."""
        response = {
            "type": "backpressure",
            "message": "Server queue overflow, please reduce message rate",
            "queue_depth": self.queue_depth,
            "max_queue": HIGH_VOLUME_CONFIG["queue_overflow_threshold"],
            "timestamp": time.time()
        }
        await websocket.send(json.dumps(response))
    
    async def _send_performance_stats(self, websocket):
        """Send current performance statistics."""
        current_memory = psutil.Process().memory_info().rss
        uptime = time.time() - self.start_time
        
        stats = {
            "type": "performance_stats",
            "uptime": uptime,
            "message_count": self.message_counter,
            "connection_count": len(self.clients),
            "queue_depth": self.queue_depth,
            "error_count": self.error_count,
            "memory_usage_mb": current_memory / 1024 / 1024,
            "memory_growth_mb": (current_memory - self.initial_memory) / 1024 / 1024,
            "peak_memory_mb": self.peak_memory / 1024 / 1024,
            "throughput_history": self.throughput_history[-100:],  # Last 100 samples
            "timestamp": time.time()
        }
        
        await websocket.send(json.dumps(stats))
    
    async def _monitor_performance(self):
        """Monitor server performance metrics."""
        while self.server:
            try:
                current_memory = psutil.Process().memory_info().rss
                self.peak_memory = max(self.peak_memory, current_memory)
                
                # Record throughput sample
                throughput_sample = {
                    "timestamp": time.time(),
                    "message_count": self.message_counter,
                    "connection_count": len(self.clients),
                    "queue_depth": self.queue_depth,
                    "memory_mb": current_memory / 1024 / 1024
                }
                
                self.throughput_history.append(throughput_sample)
                
                # Keep history manageable
                if len(self.throughput_history) > 1000:
                    self.throughput_history = self.throughput_history[-500:]
                
                await asyncio.sleep(1.0)  # Sample every second
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(5.0)


class HighVolumeThroughputClient:
    """High-performance WebSocket client for throughput testing."""
    
    def __init__(self, websocket_uri: str, auth_token: str, client_id: str = None):
        self.websocket_uri = websocket_uri
        self.auth_token = auth_token
        self.client_id = client_id or f"client-{uuid.uuid4().hex[:8]}"
        self.websocket = None
        self.connected = False
        
        # Performance tracking
        self.messages_sent = 0
        self.messages_received = 0
        self.latency_measurements = []
        self.response_queue = asyncio.Queue()
        self.receive_task = None
        
    async def connect(self):
        """Connect to WebSocket server."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            self.websocket = await websockets.connect(
                self.websocket_uri,
                additional_headers=headers,
                max_size=2**20,
                ping_interval=20,
                ping_timeout=10
            )
            self.connected = True
            
            # Start receiving messages
            self.receive_task = asyncio.create_task(self.receive_responses())
            
            logger.info(f"Client {self.client_id} connected to {self.websocket_uri}")
            
        except Exception as e:
            logger.error(f"Connection failed for {self.client_id}: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        self.connected = False
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        logger.info(f"Client {self.client_id} disconnected")
    
    async def send_throughput_burst(self, message_count: int, 
                                  target_rate: float = None, 
                                  rate_limit: float = None,
                                  message_type: str = "throughput_test") -> List[Dict]:
        """Send burst of messages for throughput testing."""
        if not self.connected:
            raise RuntimeError("Client not connected")
        
        start_time = time.time()
        sent_results = []
        
        # Use rate_limit or target_rate 
        effective_rate = rate_limit or target_rate
        
        # Calculate delay between messages for target rate
        if effective_rate:
            message_delay = 1.0 / effective_rate
        else:
            message_delay = 0.0
        
        logger.info(f"Sending {message_count} messages at {effective_rate or 'max'} msg/s")
        
        for i in range(message_count):
            try:
                message_id = f"{self.client_id}-{i}-{uuid.uuid4().hex[:8]}"
                message = {
                    "type": message_type,
                    "message_id": message_id,
                    "sequence_id": i,
                    "content": f"Throughput test message {i}",
                    "send_time": time.time(),
                    "client_id": self.client_id
                }
                
                await self.websocket.send(json.dumps(message))
                sent_results.append({"status": "sent", "message_id": message_id, "sequence_id": i})
                self.messages_sent += 1
                
                # Rate limiting
                if message_delay > 0:
                    await asyncio.sleep(message_delay)
                    
            except Exception as e:
                logger.error(f"Send error for message {i}: {e}")
                sent_results.append({"status": "failed", "message_id": f"failed-{i}", "error": str(e)})
        
        end_time = time.time()
        duration = end_time - start_time
        sent_count = len([r for r in sent_results if r["status"] == "sent"])
        actual_rate = sent_count / duration if duration > 0 else 0
        
        logger.info(f"Burst complete: {sent_count}/{message_count} sent at {actual_rate:.1f} msg/s")
        
        return sent_results
    
    async def send_latency_probes(self, probe_count: int, 
                                interval: float = 1.0) -> List[Dict]:
        """Send latency probe messages with precise timing."""
        if not self.connected:
            raise RuntimeError("Client not connected")
        
        probes = []
        
        for i in range(probe_count):
            try:
                message_id = f"probe-{self.client_id}-{i}-{uuid.uuid4().hex[:8]}"
                send_time = time.perf_counter()
                
                message = {
                    "type": "latency_probe",
                    "message_id": message_id,
                    "send_time": send_time,
                    "probe_index": i,
                    "client_id": self.client_id
                }
                
                await self.websocket.send(json.dumps(message))
                
                probes.append({
                    "message_id": message_id,
                    "send_time": send_time,
                    "probe_index": i
                })
                
                if interval > 0 and i < probe_count - 1:
                    await asyncio.sleep(interval)
                    
            except Exception as e:
                logger.error(f"Latency probe {i} failed: {e}")
        
        return probes
    
    async def receive_responses(self):
        """Continuously receive and queue responses."""
        try:
            while self.connected:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=1.0
                    )
                    data = json.loads(message)
                    data["receive_time"] = time.perf_counter()
                    
                    await self.response_queue.put(data)
                    self.messages_received += 1
                    
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"Connection closed for {self.client_id}")
                    break
                except Exception as e:
                    logger.error(f"Receive error for {self.client_id}: {e}")
                    
        except asyncio.CancelledError:
            logger.debug(f"Receive task cancelled for {self.client_id}")
        except Exception as e:
            logger.error(f"Receive task error for {self.client_id}: {e}")
    
    async def get_performance_stats(self) -> Dict:
        """Get client performance statistics."""
        if not self.connected:
            raise RuntimeError("Client not connected")
        
        # Request stats from server
        message = {
            "type": "get_performance_stats",
            "client_id": self.client_id,
            "timestamp": time.time()
        }
        
        await self.websocket.send(json.dumps(message))
        
        # Wait for response
        try:
            response = await asyncio.wait_for(
                self.response_queue.get(), 
                timeout=5.0
            )
            
            if response.get("type") == "performance_stats":
                return response
            else:
                logger.warning(f"Unexpected response type: {response.get('type')}")
                return {}
                
        except asyncio.TimeoutError:
            logger.error("Performance stats request timeout")
            return {}
    
    async def receive_responses(self, expected_count: int, timeout: float = 30.0) -> List[Dict]:
        """Receive responses from the server with timeout."""
        responses = []
        start_time = time.time()
        
        while len(responses) < expected_count and (time.time() - start_time) < timeout:
            try:
                # Try to get responses from the queue
                response = await asyncio.wait_for(
                    self.response_queue.get(),
                    timeout=1.0
                )
                responses.append(response)
                
            except asyncio.TimeoutError:
                # Check if we should continue waiting
                if len(responses) == 0 and (time.time() - start_time) > timeout / 2:
                    logger.warning(f"No responses received after {timeout/2:.1f}s")
                continue
            except Exception as e:
                logger.error(f"Error receiving response: {e}")
                break
        
        logger.info(f"Received {len(responses)}/{expected_count} responses in {time.time() - start_time:.1f}s")
        return responses
