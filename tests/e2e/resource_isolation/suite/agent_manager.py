"""
Tenant Agent Manager for Resource Isolation Testing

Manages creation, connection, and cleanup of tenant agents.
"""

import asyncio
import json
import logging
import secrets
import time
import uuid
from typing import Any, Dict, List, Optional

import websockets

from tests.e2e.resource_isolation.test_infrastructure import TenantAgent

logger = logging.getLogger(__name__)

class TenantAgentManager:
    """Manages tenant agents for resource isolation testing."""
    
    def __init__(self, test_config: Dict[str, Any]):
        self.test_config = test_config
        self.tenant_agents: Dict[str, TenantAgent] = {}
        
    async def create_tenant_agents(self, count: int) -> List[TenantAgent]:
        """Create multiple tenant agents for testing."""
        agents = []
        
        for i in range(count):
            tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
            user_id = f"user-{uuid.uuid4().hex[:8]}"
            
            # Generate JWT token
            jwt_token = await self._generate_test_jwt(user_id, tenant_id)
            
            agent = TenantAgent(
                tenant_id=tenant_id,
                user_id=user_id,
                websocket_uri=self.test_config["websocket_url"],
                jwt_token=jwt_token
            )
            
            agents.append(agent)
            self.tenant_agents[tenant_id] = agent
            
        logger.info(f"Created {len(agents)} tenant agents")
        return agents

    async def _generate_test_jwt(self, user_id: str, tenant_id: str) -> str:
        """Generate a test JWT token."""
        # For testing, we'll use a mock token
        # In real scenarios, this would call the auth service
        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "exp": int(time.time()) + 3600,  # 1 hour expiry
            "iat": int(time.time()),
            "test_mode": True
        }
        
        # Simple mock token for testing
        return f"test-jwt-{secrets.token_urlsafe(32)}"

    async def establish_agent_connections(self, agents: List[TenantAgent]) -> List[TenantAgent]:
        """Establish WebSocket connections for tenant agents."""
        connected_agents = []
        
        for agent in agents:
            try:
                connection = await self._establish_single_connection(agent)
                if connection:
                    agent.connection = connection
                    connected_agents.append(agent)
                        
            except Exception as e:
                logger.error(f"Failed to establish connection for {agent.tenant_id}: {e}")
        
        logger.info(f"Established connections for {len(connected_agents)}/{len(agents)} agents")
        return connected_agents

    async def _establish_single_connection(self, agent: TenantAgent) -> Optional[websockets.WebSocketServerProtocol]:
        """Establish a single WebSocket connection."""
        try:
            # Add authentication headers
            headers = {"Authorization": f"Bearer {agent.jwt_token}"}
            
            connection = await websockets.connect(
                agent.websocket_uri,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Send initial handshake
            handshake = {
                "type": "handshake",
                "tenant_id": agent.tenant_id,
                "user_id": agent.user_id,
                "timestamp": time.time()
            }
            
            await connection.send(json.dumps(handshake))
            
            # Wait for acknowledgment
            response = await asyncio.wait_for(connection.recv(), timeout=10.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "handshake_ack":
                logger.info(f"Connection established for tenant {agent.tenant_id}")
                return connection
            else:
                logger.error(f"Unexpected handshake response: {response_data}")
                await connection.close()
                return None
                
        except Exception as e:
            logger.error(f"Connection establishment failed for {agent.tenant_id}: {e}")
            return None

    async def cleanup_all_agents(self):
        """Clean up all tenant agents."""
        for tenant_agent in self.tenant_agents.values():
            try:
                if tenant_agent.connection:
                    await tenant_agent.connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection for {tenant_agent.tenant_id}: {e}")
        
        # Clear agent registry
        self.tenant_agents.clear()
        logger.info("All tenant agents cleaned up")
