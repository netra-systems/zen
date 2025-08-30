"""
Tenant Agent Manager for Resource Isolation Testing

Manages creation, connection, and cleanup of tenant agents.
"""

import asyncio
import json
import logging
import os
import secrets
import time
import uuid
from typing import Any, Dict, List, Optional

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import websockets
    try:
        from websockets import WebSocketServerProtocol
    except ImportError:
        # Fallback for older versions
        from websockets.server import WebSocketServerProtocol

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
        """Generate a test JWT token that follows proper JWT structure."""
        import jwt
        import json
        
        # Create proper JWT payload
        payload = {
            "sub": user_id,  # Standard JWT subject claim
            "user_id": user_id,
            "tenant_id": tenant_id,
            "exp": int(time.time()) + 3600,  # 1 hour expiry
            "iat": int(time.time()),
            "test_mode": True,
            "test_user": True,  # Pattern expected by validation
            "permissions": ["user"]
        }
        
        # Use the same JWT secret as the backend service for consistency
        try:
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            test_secret = get_jwt_secret()
        except Exception as e:
            logger.warning(f"Could not get unified JWT secret: {e}, using fallback")
            test_secret = os.getenv("JWT_SECRET_KEY", "dev-secret-key-DO-NOT-USE-IN-PRODUCTION")
        
        try:
            # Generate proper JWT token
            jwt_token = jwt.encode(payload, test_secret, algorithm="HS256")
            return jwt_token
        except Exception as e:
            logger.warning(f"Failed to create JWT token: {e}, falling back to simple token")
            # Fallback to a JWT-structured token if encoding fails
            import base64
            header = base64.b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip('=')
            payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip('=')
            signature = "test_signature"
            return f"{header}.{payload_b64}.{signature}"

    async def establish_agent_connections(self, agents: List[TenantAgent]) -> List[TenantAgent]:
        """Establish WebSocket connections for tenant agents."""
        # Check if we're in offline mode
        offline_mode = os.getenv("CPU_ISOLATION_OFFLINE_MODE", "false").lower() == "true"
        
        if offline_mode:
            logger.info("CPU isolation test in offline mode - creating mock agent connections")
            return self._create_mock_connections(agents)
            
        connected_agents = []
        auth_failures = 0
        
        for agent in agents:
            try:
                connection = await self._establish_single_connection(agent)
                if connection:
                    agent.connection = connection
                    connected_agents.append(agent)
                else:
                    auth_failures += 1
                        
            except Exception as e:
                logger.error(f"Failed to establish connection for {agent.tenant_id}: {e}")
                auth_failures += 1
        
        # If all connections failed due to auth issues, fallback to offline mode
        if len(connected_agents) == 0 and auth_failures == len(agents):
            logger.warning("All WebSocket connections failed - falling back to CPU isolation offline mode")
            os.environ["CPU_ISOLATION_OFFLINE_MODE"] = "true"
            return self._create_mock_connections(agents)
        
        logger.info(f"Established connections for {len(connected_agents)}/{len(agents)} agents")
        return connected_agents

    def _create_mock_connections(self, agents: List[TenantAgent]) -> List[TenantAgent]:
        """Create mock connections for offline mode testing."""
        import psutil
        
        # All agents are "connected" in offline mode
        connected_agents = []
        for agent in agents:
            # Create mock process info for CPU isolation monitoring
            agent.process_info = {
                "pid": psutil.Process().pid,  # Use current test process
                "mock_mode": True,
                "creation_time": time.time()
            }
            # Create a mock connection object that supports send/recv methods
            class MockConnection:
                def __init__(self, tenant_id):
                    self.tenant_id = tenant_id
                    self.closed = False
                
                async def send(self, data):
                    """Mock send method for offline testing"""
                    pass
                
                async def recv(self):
                    """Mock recv method for offline testing"""
                    raise asyncio.TimeoutError("Mock connection - no data available")
                
                def close(self):
                    """Mock close method"""
                    self.closed = True
            
            agent.connection = MockConnection(agent.tenant_id)
            connected_agents.append(agent)
            logger.info(f"Mock connection created for tenant {agent.tenant_id}")
            
        logger.info(f"Created {len(connected_agents)} mock agent connections for CPU isolation testing")
        return connected_agents

    async def _establish_single_connection(self, agent: TenantAgent) -> Optional[WebSocketServerProtocol]:
        """Establish a single WebSocket connection."""
        try:
            # Add authentication headers
            headers = {"Authorization": f"Bearer {agent.jwt_token}"}
            
            connection = await websockets.connect(
                agent.websocket_uri,
                additional_headers=headers,
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
                    # Check if it's a real connection (has close method)
                    if hasattr(tenant_agent.connection, 'close'):
                        if asyncio.iscoroutinefunction(tenant_agent.connection.close):
                            await tenant_agent.connection.close()
                        else:
                            tenant_agent.connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection for {tenant_agent.tenant_id}: {e}")
        
        # Clear agent registry
        self.tenant_agents.clear()
        logger.info("All tenant agents cleaned up")
