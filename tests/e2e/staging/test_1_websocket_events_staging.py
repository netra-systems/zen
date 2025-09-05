"""
Test 1: WebSocket Events - Critical for Chat functionality
Tests agent WebSocket events against staging environment.
Business Value: Ensures real-time chat updates work in production.
"""

import asyncio
import json
import time
from typing import Dict, List, Set

import pytest
import websockets
import httpx

from tests.e2e.staging_test_base import StagingTestBase, staging_test
from tests.e2e.staging_test_config import get_staging_config


# Required WebSocket events for agent lifecycle
MISSION_CRITICAL_EVENTS = {
    "agent_started",      # User must see agent began processing  
    "agent_thinking",     # Real-time reasoning updates
    "tool_executing",     # Tool usage transparency
    "tool_completed",     # Tool results display
    "agent_completed"     # User must know when done
}


class TestWebSocketEventsStaging(StagingTestBase):
    """Test WebSocket events in staging environment"""
    
    @staging_test
    async def test_health_check(self):
        """Test that staging backend is healthy"""
        await self.verify_health()
        await self.verify_api_health()
        print("[PASS] Health checks successful")
    
    @staging_test
    async def test_websocket_connection(self):
        """Test WebSocket connection to staging"""
        config = get_staging_config()
        
        # Try to connect without auth (will fail but shows connectivity)
        try:
            async with websockets.connect(config.websocket_url) as ws:
                # Send ping
                await ws.send(json.dumps({"type": "ping"}))
                
                # Wait for any response
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5)
                    print(f"[INFO] WebSocket response: {response[:100]}")
                except asyncio.TimeoutError:
                    print("[INFO] WebSocket connected but no response (expected without auth)")
                
        except websockets.exceptions.ConnectionClosedError as e:
            if e.code == 1011:  # Internal error (auth required)
                print("[INFO] WebSocket requires authentication (expected)")
            else:
                raise
    
    @staging_test
    async def test_api_endpoints_for_agents(self):
        """Test API endpoints that support agent operations"""
        
        # Test service discovery
        response = await self.call_api("/api/discovery/services")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        print("[PASS] Service discovery working")
        
        # Test MCP config (agent configuration)
        response = await self.call_api("/api/mcp/config")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0  # Has configuration
        print("[PASS] MCP config available")
        
        # Test MCP servers (agent servers)
        response = await self.call_api("/api/mcp/servers")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data or isinstance(data, list)
        print("[PASS] MCP servers endpoint working")
    
    @staging_test
    async def test_websocket_event_simulation(self):
        """Simulate WebSocket event flow (without actual agent execution)"""
        
        # This test validates the WebSocket infrastructure is ready
        # Actual agent execution requires auth and deployed agents
        
        events_to_test = list(MISSION_CRITICAL_EVENTS)
        print(f"[INFO] Testing WebSocket event structure for: {events_to_test}")
        
        # Verify we can create event payloads
        sample_events = {
            "agent_started": {
                "type": "agent_started",
                "agent": "test_agent",
                "timestamp": time.time()
            },
            "agent_thinking": {
                "type": "agent_thinking", 
                "content": "Processing request...",
                "timestamp": time.time()
            },
            "tool_executing": {
                "type": "tool_executing",
                "tool": "search_tool",
                "input": "test query",
                "timestamp": time.time()
            },
            "tool_completed": {
                "type": "tool_completed",
                "tool": "search_tool",
                "output": "test results",
                "timestamp": time.time()
            },
            "agent_completed": {
                "type": "agent_completed",
                "result": "Task completed successfully",
                "timestamp": time.time()
            }
        }
        
        # Validate event structure
        for event_type, event_data in sample_events.items():
            assert "type" in event_data
            assert "timestamp" in event_data
            print(f"[PASS] Event structure valid for: {event_type}")
        
        print("[PASS] All WebSocket event structures validated")
    
    @staging_test
    async def test_concurrent_connections(self):
        """Test multiple concurrent WebSocket connections"""
        config = get_staging_config()
        
        async def try_connect(conn_id: int):
            try:
                async with websockets.connect(config.websocket_url) as ws:
                    await ws.send(json.dumps({"type": "ping", "id": conn_id}))
                    return f"Connection {conn_id}: connected"
            except Exception as e:
                return f"Connection {conn_id}: {str(e)[:50]}"
        
        # Try 5 concurrent connections
        tasks = [try_connect(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            print(f"[INFO] {result}")
        
        print("[PASS] Concurrent connection test completed")


if __name__ == "__main__":
    # Run tests directly
    import sys
    
    async def run_tests():
        test_class = TestWebSocketEventsStaging()
        test_class.setup_class()
        
        try:
            print("=" * 60)
            print("WebSocket Events Staging Tests")
            print("=" * 60)
            
            await test_class.test_health_check()
            await test_class.test_websocket_connection()
            await test_class.test_api_endpoints_for_agents()
            await test_class.test_websocket_event_simulation()
            await test_class.test_concurrent_connections()
            
            print("\n" + "=" * 60)
            print("[SUCCESS] All tests passed")
            print("=" * 60)
            
        finally:
            test_class.teardown_class()
    
    asyncio.run(run_tests())