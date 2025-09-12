"""
WebSocket Infrastructure Performance Validation Tests

This test suite validates the enhanced WebSocket infrastructure performance
improvements for the critical requirements:
- 5 concurrent users with <2s response times
- Connection recovery within 5 seconds 
- Zero message loss during normal operation
- All WebSocket events fire correctly
"""

import asyncio
import json
import time
import pytest
from datetime import datetime, timezone
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock
from concurrent.futures import ThreadPoolExecutor

from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.websocket_core.message_buffer import BufferConfig, BufferedMessage, BufferPriority
from netra_backend.app.core.websocket_reconnection_handler import WebSocketReconnectionHandler, ReconnectionConfig
from netra_backend.app.websocket_core.utils import is_websocket_connected


class MockWebSocketForPerformance:
    """High-performance mock WebSocket for validation testing."""
    
    def __init__(self, user_id: str, client_state=None):
        self.user_id = user_id
        self.client_state = client_state or "CONNECTED"
        self.messages_sent = []
        self.send_times = []
        self.is_closed = False
        self.send_delay = 0.0  # Configurable delay for testing
        
    async def send_json(self, data: Dict[str, Any], timeout: float = None) -> None:
        """Mock send_json with timing tracking."""
        start_time = time.time()
        
        if self.send_delay > 0:
            await asyncio.sleep(self.send_delay)
        
        if self.is_closed:
            raise RuntimeError("WebSocket is closed")
        
        self.messages_sent.append({
            "data": data,
            "timestamp": time.time(),
            "timeout_used": timeout
        })
        
        send_time = (time.time() - start_time) * 1000
        self.send_times.append(send_time)
    
    async def close(self, code: int = 1000, reason: str = ""):
        self.is_closed = True
        self.client_state = "DISCONNECTED"
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        if self.send_times:
            return {
                "messages_sent": len(self.messages_sent),
                "avg_send_time_ms": sum(self.send_times) / len(self.send_times),
                "max_send_time_ms": max(self.send_times),
                "min_send_time_ms": min(self.send_times)
            }
        return {
            "messages_sent": 0,
            "avg_send_time_ms": 0,
            "max_send_time_ms": 0,
            "min_send_time_ms": 0
        }


class PerformanceTestRunner:
    """Test runner for WebSocket performance validation."""
    
    def __init__(self):
        self.manager = WebSocketManager()
        self.test_results = {}
        self.performance_metrics = {
            "response_times": [],
            "connection_times": [],
            "recovery_times": [],
            "message_delivery_confirmations": [],
            "buffer_performance": {}
        }
    
    async def setup(self):
        """Setup test environment."""
        # Ensure manager is properly initialized
        if not hasattr(self.manager, '_initialized'):
            self.manager._initialized = True
    
    async def test_concurrent_user_performance(self, user_count: int = 5) -> Dict[str, Any]:
        """Test concurrent user performance with <2s response time requirement."""
        print(f"Testing {user_count} concurrent users...")
        
        users = [f"perf_user_{i}" for i in range(user_count)]
        websockets = []
        connection_ids = []
        
        # Create concurrent connections
        connection_start = time.time()
        
        for user_id in users:
            websocket = MockWebSocketForPerformance(user_id)
            websockets.append(websocket)
            
            # Connect user
            conn_id = await self.manager.connect_user(user_id, websocket)
            connection_ids.append(conn_id)
        
        connection_time = time.time() - connection_start
        self.performance_metrics["connection_times"].append(connection_time)
        
        print(f"Connected {len(connection_ids)} users in {connection_time:.3f}s")
        
        # Test concurrent message sending with response time measurement
        test_message = {
            "type": "agent_started",
            "payload": {"agent_id": "test_agent", "task": "performance_test"},
            "timestamp": time.time()
        }
        
        send_tasks = []
        send_start = time.time()
        
        for user_id in users:
            task = self.manager.send_to_user(user_id, test_message, require_confirmation=True)
            send_tasks.append(task)
        
        results = await asyncio.gather(*send_tasks)
        send_time = time.time() - send_start
        
        # Validate response time requirement (<2s)
        response_time_ok = send_time < 2.0
        successful_sends = sum(1 for r in results if r)
        
        self.performance_metrics["response_times"].append(send_time)
        
        # Calculate per-websocket performance metrics
        websocket_metrics = [ws.get_performance_metrics() for ws in websockets]
        avg_per_message_time = sum(
            m["avg_send_time_ms"] for m in websocket_metrics if m["messages_sent"] > 0
        ) / len([m for m in websocket_metrics if m["messages_sent"] > 0]) if websocket_metrics else 0
        
        # Cleanup
        for user_id, websocket in zip(users, websockets):
            await self.manager.disconnect_user(user_id, websocket)
        
        return {
            "user_count": user_count,
            "connection_time": connection_time,
            "total_send_time": send_time,
            "avg_per_message_time_ms": avg_per_message_time,
            "successful_sends": successful_sends,
            "response_time_requirement_met": response_time_ok,
            "connections_established": len(connection_ids),
            "websocket_metrics": websocket_metrics
        }
    
    async def test_connection_recovery_performance(self) -> Dict[str, Any]:
        """Test connection recovery within 5 seconds."""
        print("Testing connection recovery performance...")
        
        user_id = "recovery_test_user"
        websocket = MockWebSocketForPerformance(user_id)
        
        # Establish initial connection
        conn_id = await self.manager.connect_user(user_id, websocket)
        
        # Simulate connection failure
        websocket.is_closed = True
        websocket.client_state = "DISCONNECTED"
        
        # Test reconnection with optimized handler
        config = ReconnectionConfig(
            max_attempts=5,
            initial_delay_seconds=0.1,  # Fast initial retry
            max_delay_seconds=2.0,
            backoff_multiplier=2.0,
            jitter_enabled=True
        )
        
        reconnection_handler = WebSocketReconnectionHandler(conn_id, config)
        
        recovery_start = time.time()
        recovery_successful = False
        
        async def mock_connect():
            # Simulate successful reconnection
            new_websocket = MockWebSocketForPerformance(user_id)
            await self.manager.connect_user(user_id, new_websocket)
            return True
        
        # Start reconnection process
        await reconnection_handler.start_reconnection("connection_lost", mock_connect)
        
        # Wait for recovery with timeout
        try:
            await asyncio.wait_for(reconnection_handler.reconnect_task, timeout=6.0)
            recovery_successful = True
        except asyncio.TimeoutError:
            recovery_successful = False
        
        recovery_time = time.time() - recovery_start
        recovery_within_requirement = recovery_time < 5.0
        
        self.performance_metrics["recovery_times"].append(recovery_time)
        
        return {
            "recovery_time": recovery_time,
            "recovery_successful": recovery_successful,
            "recovery_within_5s": recovery_within_requirement,
            "attempts_made": reconnection_handler.get_attempts()
        }
    
    async def test_zero_message_loss(self) -> Dict[str, Any]:
        """Test zero message loss during normal operation."""
        print("Testing zero message loss capabilities...")
        
        # Create optimized buffer configuration
        config = BufferConfig(
            max_buffer_size_per_user=200,
            max_buffer_size_global=1000,
            never_drop_critical=True
        )
        
        from netra_backend.app.websocket_core.message_buffer import WebSocketMessageBuffer
        buffer = WebSocketMessageBuffer(config)
        await buffer.start()
        
        user_id = "buffer_test_user"
        
        # Test critical message buffering
        critical_messages = []
        for i in range(10):
            msg = {
                "type": "agent_started",
                "payload": {"sequence": i, "agent_id": f"agent_{i}"},
                "timestamp": time.time()
            }
            critical_messages.append(msg)
            
            success = await buffer.buffer_message(user_id, msg, BufferPriority.CRITICAL)
            assert success, f"Failed to buffer critical message {i}"
        
        # Test non-critical message buffering with overflow
        non_critical_buffered = 0
        for i in range(300):  # Exceed buffer limit
            msg = {
                "type": "status_update",
                "payload": {"sequence": i},
                "timestamp": time.time()
            }
            
            success = await buffer.buffer_message(user_id, msg, BufferPriority.LOW)
            if success:
                non_critical_buffered += 1
        
        # Verify critical messages are preserved
        buffered_messages = await buffer.get_buffered_messages(user_id)
        critical_preserved = sum(1 for msg in buffered_messages 
                               if msg.message.get('type') == 'agent_started')
        
        await buffer.stop()
        
        return {
            "critical_messages_sent": len(critical_messages),
            "critical_messages_preserved": critical_preserved,
            "non_critical_messages_buffered": non_critical_buffered,
            "zero_loss_for_critical": critical_preserved == len(critical_messages),
            "buffer_stats": buffer.get_buffer_stats()
        }
    
    async def test_event_delivery_confirmation(self) -> Dict[str, Any]:
        """Test event delivery confirmation mechanisms."""
        print("Testing event delivery confirmation...")
        
        user_id = "confirmation_test_user"
        websocket = MockWebSocketForPerformance(user_id)
        
        conn_id = await self.manager.connect_user(user_id, websocket)
        
        # Test critical event types that require confirmation
        critical_events = [
            "agent_started", "agent_thinking", "tool_executing", 
            "tool_completed", "agent_completed"
        ]
        
        confirmation_results = []
        
        for event_type in critical_events:
            message = {
                "type": event_type,
                "payload": {"test": "confirmation"},
                "message_id": f"msg_{event_type}_{int(time.time() * 1000)}"
            }
            
            send_start = time.time()
            success = await self.manager.send_to_user(
                user_id, message, require_confirmation=True
            )
            send_time = (time.time() - send_start) * 1000
            
            # Simulate confirmation from client
            if success and message.get("message_id"):
                confirmation_success = await self.manager.confirm_message_delivery(
                    message["message_id"]
                )
                
                confirmation_results.append({
                    "event_type": event_type,
                    "send_successful": success,
                    "send_time_ms": send_time,
                    "confirmation_successful": confirmation_success
                })
        
        # Cleanup
        await self.manager.disconnect_user(user_id, websocket)
        
        successful_confirmations = sum(1 for r in confirmation_results 
                                     if r["confirmation_successful"])
        avg_send_time = sum(r["send_time_ms"] for r in confirmation_results) / len(confirmation_results)
        
        return {
            "events_tested": len(critical_events),
            "successful_confirmations": successful_confirmations,
            "confirmation_rate": successful_confirmations / len(critical_events),
            "average_send_time_ms": avg_send_time,
            "delivery_stats": self.manager.delivery_stats,
            "individual_results": confirmation_results
        }
    
    async def run_comprehensive_performance_test(self) -> Dict[str, Any]:
        """Run comprehensive performance validation test suite."""
        print("Starting comprehensive WebSocket infrastructure performance validation...")
        
        await self.setup()
        
        test_results = {}
        
        # Test 1: Concurrent user performance
        concurrent_result = await self.test_concurrent_user_performance(5)
        test_results["concurrent_users"] = concurrent_result
        
        # Test 2: Connection recovery performance 
        recovery_result = await self.test_connection_recovery_performance()
        test_results["connection_recovery"] = recovery_result
        
        # Test 3: Zero message loss
        message_loss_result = await self.test_zero_message_loss()
        test_results["message_loss_prevention"] = message_loss_result
        
        # Test 4: Event delivery confirmation
        confirmation_result = await self.test_event_delivery_confirmation()
        test_results["event_delivery_confirmation"] = confirmation_result
        
        # Overall performance summary
        test_results["performance_summary"] = {
            "response_time_requirement_met": concurrent_result["response_time_requirement_met"],
            "recovery_time_requirement_met": recovery_result["recovery_within_5s"],
            "zero_message_loss_achieved": message_loss_result["zero_loss_for_critical"],
            "event_confirmation_working": confirmation_result["confirmation_rate"] > 0.8,
            "overall_performance_metrics": self.performance_metrics
        }
        
        return test_results


# Pytest test functions
@pytest.mark.asyncio
async def test_websocket_performance_requirements():
    """Test that WebSocket infrastructure meets all performance requirements."""
    runner = PerformanceTestRunner()
    results = await runner.run_comprehensive_performance_test()
    
    # Assert critical requirements
    assert results["concurrent_users"]["response_time_requirement_met"], \
        f"Response time requirement not met: {results['concurrent_users']['total_send_time']:.3f}s"
    
    assert results["connection_recovery"]["recovery_within_5s"], \
        f"Recovery time requirement not met: {results['connection_recovery']['recovery_time']:.3f}s"
    
    assert results["message_loss_prevention"]["zero_loss_for_critical"], \
        "Zero message loss requirement not met for critical messages"
    
    assert results["event_delivery_confirmation"]["confirmation_rate"] > 0.8, \
        f"Event confirmation rate too low: {results['event_delivery_confirmation']['confirmation_rate']:.2f}"
    
    # Print performance summary
    print("\n" + "="*60)
    print("WebSocket Infrastructure Performance Validation Results")
    print("="*60)
    
    concurrent = results["concurrent_users"]
    print(f"[U+2713] 5 concurrent users: {concurrent['total_send_time']:.3f}s (requirement: <2s)")
    
    recovery = results["connection_recovery"]
    print(f"[U+2713] Connection recovery: {recovery['recovery_time']:.3f}s (requirement: <5s)")
    
    message_loss = results["message_loss_prevention"]
    print(f"[U+2713] Zero message loss: {message_loss['critical_messages_preserved']}/{message_loss['critical_messages_sent']} critical messages preserved")
    
    confirmation = results["event_delivery_confirmation"]
    print(f"[U+2713] Event confirmation: {confirmation['confirmation_rate']:.1%} success rate")
    
    print("\nAll performance requirements validated successfully!")


if __name__ == "__main__":
    async def main():
        runner = PerformanceTestRunner()
        results = await runner.run_comprehensive_performance_test()
        
        print(json.dumps(results, indent=2, default=str))
    
    asyncio.run(main())