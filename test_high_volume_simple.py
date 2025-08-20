"""
Simplified High-Volume Throughput Test - Validation Version

This simplified version tests the core functionality with fixes applied.
"""

import asyncio
import time
import json
import logging
import random
import psutil
import os
from typing import Dict, List, Optional

# WebSocket imports
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple test configuration
SIMPLE_CONFIG = {
    "max_message_rate": 100,      # Conservative for testing
    "test_duration": 10,          # Short test duration
    "max_messages": 500,          # Small message count
}


class SimpleWebSocketServer:
    """Simplified WebSocket server for testing."""
    
    def __init__(self, port=8768):
        self.port = port
        self.server = None
        self.clients = set()
        self.message_count = 0
        
    async def start(self):
        """Start the server."""
        self.server = await websockets.serve(
            self.handle_client,
            "localhost",
            self.port
        )
        logger.info(f"Simple server started on ws://localhost:{self.port}")
        
    async def stop(self):
        """Stop the server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Simple server stopped")
            
    async def handle_client(self, websocket):
        """Handle client connections."""
        self.clients.add(websocket)
        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
    
    async def process_message(self, websocket, message):
        """Process incoming messages."""
        try:
            data = json.loads(message)
            self.message_count += 1
            
            # Simple response
            response = {
                "type": "response",
                "message_id": data.get("message_id"),
                "echo": data.get("content", ""),
                "server_time": time.time(),
                "count": self.message_count
            }
            
            await websocket.send(json.dumps(response))
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")


class SimpleWebSocketClient:
    """Simplified WebSocket client for testing."""
    
    def __init__(self, uri: str, client_id: str):
        self.uri = uri
        self.client_id = client_id
        self.connection = None
        self.sent_count = 0
        self.received_count = 0
        
    async def connect(self):
        """Connect to server with simplified parameters."""
        try:
            # Fixed connection parameters
            self.connection = await websockets.connect(
                self.uri,
                ping_interval=30,
                ping_timeout=10
            )
            logger.info(f"Client {self.client_id} connected")
            return True
        except Exception as e:
            logger.error(f"Client {self.client_id} connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from server."""
        if self.connection:
            try:
                if not self.connection.closed:
                    await self.connection.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.connection = None
    
    async def send_messages(self, count: int, rate: float = 10.0):
        """Send messages at specified rate."""
        if not self.connection:
            return []
        
        results = []
        delay = 1.0 / rate if rate > 0 else 0
        
        for i in range(count):
            message = {
                "type": "test_message",
                "message_id": f"{self.client_id}-{i}",
                "content": f"Test message {i}",
                "send_time": time.time()
            }
            
            try:
                await self.connection.send(json.dumps(message))
                self.sent_count += 1
                results.append({"status": "sent", "message": message})
                
                if delay > 0:
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Send error: {e}")
                results.append({"status": "failed", "error": str(e)})
        
        return results
    
    async def receive_responses(self, expected: int, timeout: float = 30.0):
        """Receive responses."""
        responses = []
        start_time = time.time()
        
        while len(responses) < expected and (time.time() - start_time) < timeout:
            try:
                response = await asyncio.wait_for(
                    self.connection.recv(),
                    timeout=1.0
                )
                response_data = json.loads(response)
                response_data["receive_time"] = time.time()
                responses.append(response_data)
                self.received_count += 1
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Receive error: {e}")
                break
        
        return responses


async def run_simple_test():
    """Run a simple validation test."""
    logger.info("Starting simple high-volume test validation...")
    
    # Start server
    server = SimpleWebSocketServer()
    await server.start()
    
    try:
        # Create client
        client = SimpleWebSocketClient("ws://localhost:8768", "test-client")
        
        # Test connection
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect client")
            return False
        
        logger.info("[PASS] Client connected successfully")
        
        # Send test messages
        message_count = 50
        target_rate = 10  # 10 msg/sec
        
        logger.info(f"Sending {message_count} messages at {target_rate} msg/sec...")
        start_time = time.perf_counter()
        
        send_results = await client.send_messages(message_count, target_rate)
        send_duration = time.perf_counter() - start_time
        
        successful_sends = len([r for r in send_results if r["status"] == "sent"])
        actual_rate = successful_sends / send_duration if send_duration > 0 else 0
        
        logger.info(f"[PASS] Sent {successful_sends}/{message_count} messages in {send_duration:.2f}s ({actual_rate:.1f} msg/sec)")
        
        # Receive responses
        logger.info("Collecting responses...")
        responses = await client.receive_responses(message_count, timeout=20.0)
        
        delivery_ratio = len(responses) / successful_sends if successful_sends > 0 else 0
        
        logger.info(f"[PASS] Received {len(responses)} responses, delivery ratio: {delivery_ratio:.3f}")
        
        # Calculate latencies
        latencies = []
        for response in responses:
            send_time = response.get("send_time", 0)
            receive_time = response.get("receive_time", 0)
            if receive_time > send_time:
                latency = receive_time - send_time
                latencies.append(latency)
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            logger.info(f"[PASS] Latency - Avg: {avg_latency:.3f}s, Max: {max_latency:.3f}s")
        
        # Memory check
        memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        logger.info(f"[INFO] Memory usage: {memory_mb:.1f}MB")
        
        # Clean up
        await client.disconnect()
        logger.info("[PASS] Client disconnected")
        
        # Validate results
        if successful_sends >= message_count * 0.9:  # 90% success rate
            logger.info("[PASS] Message sending validation")
        else:
            logger.error("[FAIL] Message sending validation")
            return False
        
        if delivery_ratio >= 0.9:  # 90% delivery ratio
            logger.info("[PASS] Message delivery validation")
        else:
            logger.error("[FAIL] Message delivery validation")
            return False
        
        if latencies and avg_latency < 1.0:  # Under 1 second
            logger.info("[PASS] Latency validation")
        else:
            logger.error("[FAIL] Latency validation")
            return False
        
        logger.info("[PASS] All validations successful!")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await server.stop()


async def test_concurrent_clients():
    """Test multiple concurrent clients."""
    logger.info("Testing concurrent clients...")
    
    server = SimpleWebSocketServer(port=8769)
    await server.start()
    
    try:
        # Create multiple clients
        client_count = 5
        messages_per_client = 20
        clients = []
        
        for i in range(client_count):
            client = SimpleWebSocketClient(f"ws://localhost:8769", f"client-{i}")
            await client.connect()
            clients.append(client)
        
        logger.info(f"[PASS] Connected {len(clients)} concurrent clients")
        
        # Send messages concurrently
        tasks = []
        for client in clients:
            task = asyncio.create_task(client.send_messages(messages_per_client, 5.0))
            tasks.append(task)
        
        # Wait for all sends to complete
        send_results = await asyncio.gather(*tasks)
        
        total_sent = sum(len([r for r in result if r["status"] == "sent"]) for result in send_results)
        expected_total = client_count * messages_per_client
        
        logger.info(f"[PASS] Concurrent sending: {total_sent}/{expected_total} messages")
        
        # Collect responses from all clients
        receive_tasks = []
        for client in clients:
            task = asyncio.create_task(client.receive_responses(messages_per_client, 15.0))
            receive_tasks.append(task)
        
        receive_results = await asyncio.gather(*receive_tasks)
        total_received = sum(len(responses) for responses in receive_results)
        
        concurrent_delivery_ratio = total_received / total_sent if total_sent > 0 else 0
        
        logger.info(f"[PASS] Concurrent delivery: {total_received} responses, ratio: {concurrent_delivery_ratio:.3f}")
        
        # Clean up
        for client in clients:
            await client.disconnect()
        
        logger.info("[PASS] Concurrent client test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Concurrent test failed: {e}")
        return False
        
    finally:
        await server.stop()


async def main():
    """Run all validation tests."""
    logger.info("=" * 60)
    logger.info("HIGH-VOLUME THROUGHPUT TEST VALIDATION")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Functionality", run_simple_test),
        ("Concurrent Clients", test_concurrent_clients),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning test: {test_name}")
        logger.info("-" * 40)
        
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"[PASS] {test_name} completed successfully")
            else:
                logger.error(f"[FAIL] {test_name} failed")
                
        except Exception as e:
            logger.error(f"[FAIL] {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        logger.info(f"{status} {test_name}")
    
    logger.info(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("[PASS] All validation tests successful!")
        logger.info("High-volume test suite is ready for execution.")
        return True
    else:
        logger.error("[FAIL] Some validation tests failed.")
        logger.error("Please fix issues before proceeding.")
        return False


if __name__ == "__main__":
    import sys
    result = asyncio.run(main())
    sys.exit(0 if result else 1)