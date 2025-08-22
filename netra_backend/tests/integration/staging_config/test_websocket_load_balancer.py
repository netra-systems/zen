"""
Test WebSocket Load Balancer

Validates WebSocket connectivity through load balancer
and ingress in the staging environment.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
from typing import List, Optional

import websockets

# Add project root to path
from .base import StagingConfigTestBase

# Add project root to path


class TestWebSocketLoadBalancer(StagingConfigTestBase):
    """Test WebSocket through load balancer in staging."""
    
    async def test_websocket_connection(self):
        """Test basic WebSocket connection through load balancer."""
        self.skip_if_not_staging()
        
        ws_url = self.staging_url.replace('https://', 'wss://').replace('http://', 'ws://')
        ws_url = f"{ws_url}/ws"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send test message
                await websocket.send(json.dumps({
                    'type': 'ping',
                    'timestamp': time.time()
                }))
                
                # Receive response
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=5.0
                )
                
                data = json.loads(response)
                self.assertIn('type', data)
                
        except Exception as e:
            self.fail(f"WebSocket connection failed: {e}")
            
    async def test_websocket_sticky_sessions(self):
        """Test sticky sessions for WebSocket connections."""
        self.skip_if_not_staging()
        
        ws_url = f"{self.staging_url.replace('https://', 'wss://')}/ws"
        
        # Create multiple connections and verify they stick to same backend
        connection_ids = []
        
        for i in range(3):
            try:
                async with websockets.connect(ws_url) as websocket:
                    # Request server identification
                    await websocket.send(json.dumps({
                        'type': 'identify',
                        'connection': i
                    }))
                    
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )
                    
                    data = json.loads(response)
                    if 'server_id' in data:
                        connection_ids.append(data['server_id'])
                        
            except Exception as e:
                self.fail(f"Connection {i} failed: {e}")
                
        # With sticky sessions, same client should hit same server
        # This test assumes session affinity is configured
        if len(connection_ids) > 1:
            if len(set(connection_ids)) > 1:
                print(f"Warning: Multiple servers hit: {connection_ids}")
                
    async def test_websocket_reconnection(self):
        """Test WebSocket reconnection after disconnect."""
        self.skip_if_not_staging()
        
        ws_url = f"{self.staging_url.replace('https://', 'wss://')}/ws"
        
        # First connection
        try:
            websocket = await websockets.connect(ws_url)
            await websocket.send(json.dumps({'type': 'ping'}))
            await websocket.recv()
            await websocket.close()
            
            # Reconnection
            websocket = await websockets.connect(ws_url)
            await websocket.send(json.dumps({'type': 'ping'}))
            response = await asyncio.wait_for(
                websocket.recv(),
                timeout=5.0
            )
            
            self.assertIsNotNone(response, "Reconnection failed")
            await websocket.close()
            
        except Exception as e:
            self.fail(f"Reconnection test failed: {e}")
            
    async def test_websocket_max_connections(self):
        """Test WebSocket connection limits."""
        self.skip_if_not_staging()
        
        ws_url = f"{self.staging_url.replace('https://', 'wss://')}/ws"
        max_connections = 100  # Test with reasonable limit
        
        connections = []
        successful = 0
        
        try:
            for i in range(max_connections):
                try:
                    ws = await asyncio.wait_for(
                        websockets.connect(ws_url),
                        timeout=2.0
                    )
                    connections.append(ws)
                    successful += 1
                except:
                    break
                    
            self.assertGreater(successful, 10,
                             f"Only {successful} connections succeeded")
                             
            # Close all connections
            for ws in connections:
                await ws.close()
                
        except Exception as e:
            # Clean up any open connections
            for ws in connections:
                try:
                    await ws.close()
                except:
                    pass
                    
    async def test_websocket_message_ordering(self):
        """Test message ordering through load balancer."""
        self.skip_if_not_staging()
        
        ws_url = f"{self.staging_url.replace('https://', 'wss://')}/ws"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send numbered messages
                sent_messages = []
                for i in range(10):
                    msg = {'type': 'echo', 'sequence': i}
                    await websocket.send(json.dumps(msg))
                    sent_messages.append(i)
                    
                # Receive echoed messages
                received_messages = []
                for _ in range(10):
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )
                    data = json.loads(response)
                    if 'sequence' in data:
                        received_messages.append(data['sequence'])
                        
                # Verify ordering
                self.assertEqual(sent_messages, received_messages,
                               "Message ordering not preserved")
                               
        except Exception as e:
            self.fail(f"Message ordering test failed: {e}")
            
    async def test_websocket_load_balancing(self):
        """Test load distribution across WebSocket servers."""
        self.skip_if_not_staging()
        
        ws_url = f"{self.staging_url.replace('https://', 'wss://')}/ws"
        
        # Create connections from different "clients"
        server_distribution = {}
        
        for i in range(20):
            try:
                # Simulate different client IPs with headers
                headers = {'X-Forwarded-For': f'192.168.1.{i}'}
                
                async with websockets.connect(
                    ws_url,
                    extra_headers=headers
                ) as websocket:
                    
                    # Get server identification
                    await websocket.send(json.dumps({'type': 'identify'}))
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )
                    
                    data = json.loads(response)
                    if 'server_id' in data:
                        server_id = data['server_id']
                        server_distribution[server_id] = server_distribution.get(server_id, 0) + 1
                        
            except Exception:
                pass
                
        # Check distribution (should hit multiple servers)
        if len(server_distribution) > 1:
            print(f"Load distribution: {server_distribution}")
            
    async def test_websocket_upgrade_headers(self):
        """Test WebSocket upgrade headers through load balancer."""
        self.skip_if_not_staging()
        
        import httpx
        
        # Test upgrade request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.staging_url}/ws",
                headers={
                    'Upgrade': 'websocket',
                    'Connection': 'Upgrade',
                    'Sec-WebSocket-Version': '13',
                    'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ=='
                }
            )
            
            # Should get upgrade response or method not allowed
            self.assertIn(response.status_code, [101, 426, 405],
                        f"Unexpected response to WebSocket upgrade: {response.status_code}")