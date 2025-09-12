"""
Tenant Agent Manager for Resource Isolation Testing

This module provides the TenantAgentManager class for managing
agent instances in resource isolation test scenarios.

Business Value Justification (BVJ):
- Segment: Internal/Platform stability
- Business Goal: Enable reliable multi-tenant testing
- Value Impact: Ensures proper resource isolation testing
- Revenue Impact: Protects multi-user system reliability
"""

import asyncio
import json
import jwt
import logging
import time
import warnings
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from uuid import uuid4

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import websockets
    try:
        from websockets import WebSocketServerProtocol
    except ImportError:
        # Fallback for older versions
        from websockets import ServerConnection as WebSocketServerProtocol

from shared.isolated_environment import IsolatedEnvironment
from tests.e2e.resource_isolation.infrastructure.data_models import TenantAgent


logger = logging.getLogger(__name__)


@dataclass
class AgentInstance:
    """Represents an agent instance for testing."""
    id: str
    tenant_id: str
    status: str = "idle"
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    resources_used: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TenantContext:
    """Represents a tenant context for resource isolation."""
    tenant_id: str
    agents: Dict[str, AgentInstance] = field(default_factory=dict)
    resource_limits: Dict[str, float] = field(default_factory=dict)
    current_usage: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class TenantAgentManager:
    """
    Manages agent instances across multiple tenants for resource isolation testing.
    
    This class provides functionality to:
    - Create and manage agent instances per tenant
    - Track resource usage and isolation
    - Simulate multi-tenant agent workloads
    - Monitor resource boundaries and violations
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the tenant agent manager."""
        self.config = config or {}
        self.env = IsolatedEnvironment()
        
        # Tenant management
        self.tenants: Dict[str, TenantContext] = {}
        self.global_limits = {
            "max_agents_per_tenant": self.config.get("max_agents_per_tenant", 10),
            "max_memory_per_tenant": self.config.get("max_memory_per_tenant", 1024),  # MB
            "max_cpu_per_tenant": self.config.get("max_cpu_per_tenant", 2.0),  # CPU cores
        }
        
        # Tracking
        self.total_agents = 0
        self.active_agents: Set[str] = set()
        self.resource_violations: List[Dict[str, Any]] = []
        
        logger.info(f"TenantAgentManager initialized with limits: {self.global_limits}")
    
    def create_tenant(self, tenant_id: str, resource_limits: Optional[Dict[str, float]] = None) -> TenantContext:
        """Create a new tenant context."""
        if tenant_id in self.tenants:
            logger.warning(f"Tenant {tenant_id} already exists")
            return self.tenants[tenant_id]
        
        # Apply default limits if not specified
        limits = resource_limits or {}
        for key, default_value in self.global_limits.items():
            if key not in limits:
                limits[key] = default_value
        
        tenant = TenantContext(
            tenant_id=tenant_id,
            resource_limits=limits
        )
        
        self.tenants[tenant_id] = tenant
        logger.info(f"Created tenant {tenant_id} with limits: {limits}")
        return tenant
    
    def create_agent(self, tenant_id: str, agent_config: Optional[Dict[str, Any]] = None) -> AgentInstance:
        """Create a new agent instance for a tenant."""
        if tenant_id not in self.tenants:
            self.create_tenant(tenant_id)
        
        tenant = self.tenants[tenant_id]
        
        # Check tenant limits
        if len(tenant.agents) >= tenant.resource_limits.get("max_agents_per_tenant", 10):
            raise RuntimeError(f"Tenant {tenant_id} has reached maximum agent limit")
        
        # Create agent instance
        agent_id = str(uuid4())
        agent = AgentInstance(
            id=agent_id,
            tenant_id=tenant_id,
            status="created",
            metadata=agent_config or {}
        )
        
        # Initialize resource tracking
        agent.resources_used = {
            "memory_mb": 0.0,
            "cpu_usage": 0.0,
            "execution_time": 0.0,
            "requests_count": 0
        }
        
        # Add to tenant
        tenant.agents[agent_id] = agent
        self.active_agents.add(agent_id)
        self.total_agents += 1
        
        logger.info(f"Created agent {agent_id} for tenant {tenant_id}")
        return agent
    
    def start_agent(self, tenant_id: str, agent_id: str) -> bool:
        """Start an agent instance."""
        if tenant_id not in self.tenants:
            logger.error(f"Tenant {tenant_id} not found")
            return False
        
        tenant = self.tenants[tenant_id]
        if agent_id not in tenant.agents:
            logger.error(f"Agent {agent_id} not found in tenant {tenant_id}")
            return False
        
        agent = tenant.agents[agent_id]
        agent.status = "running"
        agent.last_activity = time.time()
        
        logger.info(f"Started agent {agent_id} for tenant {tenant_id}")
        return True
    
    def stop_agent(self, tenant_id: str, agent_id: str) -> bool:
        """Stop an agent instance."""
        if tenant_id not in self.tenants:
            logger.error(f"Tenant {tenant_id} not found")
            return False
        
        tenant = self.tenants[tenant_id]
        if agent_id not in tenant.agents:
            logger.error(f"Agent {agent_id} not found in tenant {tenant_id}")
            return False
        
        agent = tenant.agents[agent_id]
        agent.status = "stopped"
        agent.last_activity = time.time()
        
        if agent_id in self.active_agents:
            self.active_agents.remove(agent_id)
        
        logger.info(f"Stopped agent {agent_id} for tenant {tenant_id}")
        return True
    
    def update_agent_resources(self, tenant_id: str, agent_id: str, resources: Dict[str, float]) -> bool:
        """Update resource usage for an agent."""
        if tenant_id not in self.tenants:
            return False
        
        tenant = self.tenants[tenant_id]
        if agent_id not in tenant.agents:
            return False
        
        agent = tenant.agents[agent_id]
        agent.resources_used.update(resources)
        agent.last_activity = time.time()
        
        # Update tenant totals
        for resource, value in resources.items():
            if resource in tenant.current_usage:
                tenant.current_usage[resource] += value - agent.resources_used.get(resource, 0)
            else:
                tenant.current_usage[resource] = value
        
        # Check for resource violations
        self._check_resource_violations(tenant_id)
        
        return True
    
    def get_tenant_stats(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a tenant."""
        if tenant_id not in self.tenants:
            return None
        
        tenant = self.tenants[tenant_id]
        
        return {
            "tenant_id": tenant_id,
            "total_agents": len(tenant.agents),
            "active_agents": len([a for a in tenant.agents.values() if a.status == "running"]),
            "resource_usage": tenant.current_usage.copy(),
            "resource_limits": tenant.resource_limits.copy(),
            "created_at": tenant.created_at,
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics across all tenants."""
        return {
            "total_tenants": len(self.tenants),
            "total_agents": self.total_agents,
            "active_agents": len(self.active_agents),
            "resource_violations": len(self.resource_violations),
            "tenants": {tid: self.get_tenant_stats(tid) for tid in self.tenants.keys()}
        }
    
    def cleanup_tenant(self, tenant_id: str) -> bool:
        """Clean up all resources for a tenant."""
        if tenant_id not in self.tenants:
            return False
        
        tenant = self.tenants[tenant_id]
        
        # Stop all agents
        for agent_id in list(tenant.agents.keys()):
            self.stop_agent(tenant_id, agent_id)
        
        # Remove tenant
        del self.tenants[tenant_id]
        
        logger.info(f"Cleaned up tenant {tenant_id}")
        return True
    
    def cleanup_all(self):
        """Clean up all tenants and agents."""
        for tenant_id in list(self.tenants.keys()):
            self.cleanup_tenant(tenant_id)
        
        self.active_agents.clear()
        self.resource_violations.clear()
        self.total_agents = 0
        
        logger.info("Cleaned up all tenants and agents")
    
    def _check_resource_violations(self, tenant_id: str):
        """Check for resource limit violations."""
        tenant = self.tenants[tenant_id]
        
        for resource, usage in tenant.current_usage.items():
            limit_key = f"max_{resource}"
            if limit_key in tenant.resource_limits:
                limit = tenant.resource_limits[limit_key]
                if usage > limit:
                    violation = {
                        "tenant_id": tenant_id,
                        "resource": resource,
                        "usage": usage,
                        "limit": limit,
                        "timestamp": time.time(),
                        "severity": "warning" if usage < limit * 1.2 else "error"
                    }
                    self.resource_violations.append(violation)
                    logger.warning(f"Resource violation detected: {violation}")
    
    async def simulate_workload(self, tenant_id: str, agent_count: int, duration_seconds: float = 60.0) -> Dict[str, Any]:
        """Simulate a workload for testing purposes."""
        results = {
            "tenant_id": tenant_id,
            "agents_created": 0,
            "agents_started": 0,
            "simulation_duration": duration_seconds,
            "start_time": time.time(),
            "errors": []
        }
        
        try:
            # Create tenant if it doesn't exist
            if tenant_id not in self.tenants:
                self.create_tenant(tenant_id)
            
            # Create agents
            agents = []
            for i in range(agent_count):
                try:
                    agent = self.create_agent(tenant_id, {"workload_index": i})
                    agents.append(agent)
                    results["agents_created"] += 1
                except Exception as e:
                    results["errors"].append(f"Failed to create agent {i}: {str(e)}")
            
            # Start agents
            for agent in agents:
                try:
                    if self.start_agent(tenant_id, agent.id):
                        results["agents_started"] += 1
                except Exception as e:
                    results["errors"].append(f"Failed to start agent {agent.id}: {str(e)}")
            
            # Simulate activity
            end_time = time.time() + duration_seconds
            while time.time() < end_time:
                for agent in agents:
                    # Simulate resource usage
                    if agent.status == "running":
                        simulated_resources = {
                            "memory_mb": agent.resources_used.get("memory_mb", 0) + 0.1,
                            "cpu_usage": min(1.0, agent.resources_used.get("cpu_usage", 0) + 0.01),
                            "requests_count": agent.resources_used.get("requests_count", 0) + 1
                        }
                        self.update_agent_resources(tenant_id, agent.id, simulated_resources)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
            
            # Stop agents
            for agent in agents:
                self.stop_agent(tenant_id, agent.id)
            
        except Exception as e:
            results["errors"].append(f"Simulation error: {str(e)}")
        
        results["end_time"] = time.time()
        results["actual_duration"] = results["end_time"] - results["start_time"]
        
        return results
    
    async def create_tenant_agents(self, count: int) -> List[TenantAgent]:
        """
        Create tenant agents for resource isolation testing.
        
        Creates the specified number of TenantAgent instances, with each agent
        assigned to a unique tenant for isolation testing purposes.
        
        Args:
            count: Number of agents to create (1-50)
            
        Returns:
            List[TenantAgent]: List of created tenant agent instances, each with unique tenant_id
            
        Raises:
            ValueError: If count is invalid (< 0 or > 50)
            TypeError: If count is not an integer
        """
        # Input validation
        if count is None:
            raise TypeError("Count cannot be None")
        if not isinstance(count, int):
            raise TypeError(f"Count must be an integer, got {type(count).__name__}")
        if count < 0:
            raise ValueError(f"Count must be non-negative, got {count}")
        if count > 50:
            raise ValueError(f"Count must be <= 50 for performance reasons, got {count}")
        
        if count == 0:
            logger.info("Creating 0 tenant agents - returning empty list")
            return []
        
        logger.info(f"Creating {count} tenant agents with unique tenant IDs for isolation testing")
        
        agents = []
        
        try:
            for i in range(count):
                # Create unique tenant ID for each agent (for isolation testing)
                tenant_num = i + 1
                tenant_id = f"tenant_{tenant_num}_{uuid4().hex[:8]}"
                
                # Generate unique user ID
                user_id = f"user_{i + 1}_{uuid4().hex[:8]}"
                
                # Get WebSocket URI
                websocket_uri = self._get_websocket_base_url()
                
                # Generate test JWT token
                jwt_token = self._generate_test_jwt_token(user_id, tenant_id)
                
                # Create TenantAgent instance
                agent = TenantAgent(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    websocket_uri=websocket_uri,
                    jwt_token=jwt_token,
                    connection=None,  # Will be established later
                    process_info=None
                )
                
                agents.append(agent)
                logger.debug(f"Created agent {i+1}/{count}: tenant={tenant_id}, user={user_id}")
            
            logger.info(f"Successfully created {len(agents)} tenant agents, each with unique tenant ID")
            return agents
            
        except Exception as e:
            logger.error(f"Failed to create tenant agents: {str(e)}")
            raise RuntimeError(f"Failed to create tenant agents: {str(e)}") from e
    
    async def establish_agent_connections(self, agents: List[TenantAgent]) -> List[TenantAgent]:
        """
        Establish WebSocket connections for tenant agents.
        
        Attempts to establish WebSocket connections for all provided agents
        with concurrent connection handling, retry logic, and authentication.
        
        Args:
            agents: List of TenantAgent instances to connect
            
        Returns:
            List[TenantAgent]: List of successfully connected agents
            
        Raises:
            TypeError: If agents is not a list
        """
        # Input validation
        if agents is None or not isinstance(agents, list):
            raise TypeError(f"agents must be a list, got {type(agents).__name__}")
        
        if not agents:
            logger.info("No agents provided - returning empty list")
            return []
        
        logger.info(f"Establishing WebSocket connections for {len(agents)} agents")
        
        # Use semaphore to limit concurrent connections
        connection_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent connections
        connected_agents = []
        
        async def connect_single_agent(agent: TenantAgent) -> Optional[TenantAgent]:
            """Helper to connect a single agent with semaphore control."""
            async with connection_semaphore:
                return await self._establish_single_agent_connection(agent)
        
        try:
            # Create connection tasks for all agents
            connection_tasks = []
            for agent in agents:
                task = asyncio.create_task(connect_single_agent(agent))
                connection_tasks.append(task)
            
            # Wait for all connections to complete
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Connection failed for agent {i}: {result}")
                    continue
                    
                if result is not None:
                    connected_agents.append(result)
                    logger.debug(f"Successfully connected agent: {result.user_id}")
            
            success_rate = len(connected_agents) / len(agents) * 100 if agents else 0
            logger.info(f"Connection results: {len(connected_agents)}/{len(agents)} successful ({success_rate:.1f}%)")
            
            return connected_agents
            
        except Exception as e:
            logger.error(f"Failed to establish agent connections: {str(e)}")
            # Clean up any partial connections
            await self._close_websocket_connections(connected_agents)
            raise RuntimeError(f"Failed to establish agent connections: {str(e)}") from e
    
    async def cleanup_all_agents(self) -> None:
        """
        Clean up all agents and their resources.
        
        Performs comprehensive cleanup of:
        - WebSocket connections
        - Internal agent instances
        - Tenant contexts
        - Active agent tracking
        
        This method is idempotent and can be called multiple times safely.
        """
        logger.info("Starting cleanup of all agents and resources")
        
        try:
            # Count resources before cleanup
            total_tenants = len(self.tenants)
            total_agents = len(self.active_agents)
            
            # Close any WebSocket connections first
            if hasattr(self, '_websocket_connections'):
                await self._close_websocket_connections(list(self._websocket_connections.values()))
                delattr(self, '_websocket_connections')
            
            # Stop all internal agents using existing cleanup method
            self.cleanup_all()
            
            # Clear any additional tracking that might exist
            if hasattr(self, '_connection_tasks'):
                # Cancel any pending connection tasks
                for task in getattr(self, '_connection_tasks', []):
                    if not task.done():
                        task.cancel()
                delattr(self, '_connection_tasks')
            
            # Clear any tenant agent references
            if hasattr(self, '_tenant_agents'):
                delattr(self, '_tenant_agents')
            
            logger.info(f"Cleanup complete: removed {total_tenants} tenants and {total_agents} agents")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            # Continue cleanup even if some steps fail - this method should be idempotent
            try:
                # Fallback: clear core state regardless of errors
                self.tenants.clear()
                self.active_agents.clear()
                self.resource_violations.clear()
                self.total_agents = 0
                logger.info("Fallback cleanup completed")
            except Exception as fallback_error:
                logger.error(f"Fallback cleanup failed: {str(fallback_error)}")
    
    def _get_websocket_base_url(self) -> str:
        """
        Get the base WebSocket URL for agent connections.
        
        Returns:
            str: WebSocket URL for connecting agents
        """
        # Try to get from config first
        if 'websocket_url' in self.config:
            return self.config['websocket_url']
        
        # Try environment variable
        websocket_url = self.env.get('WEBSOCKET_URL', None)
        if websocket_url:
            return websocket_url
        
        # Default fallback
        backend_url = self.config.get('backend_url', 'http://localhost:8000')
        # Convert HTTP to WebSocket URL
        websocket_url = backend_url.replace('http://', 'ws://').replace('https://', 'wss://')
        return f"{websocket_url}/ws"
    
    def _generate_test_jwt_token(self, user_id: str, tenant_id: str) -> str:
        """
        Generate a test JWT token for authentication.
        
        Args:
            user_id: Unique user identifier
            tenant_id: Tenant identifier
            
        Returns:
            str: JWT token for testing
        """
        try:
            # Test payload with standard claims
            payload = {
                'sub': user_id,
                'tenant_id': tenant_id,
                'iat': int(time.time()),
                'exp': int(time.time()) + 3600,  # 1 hour expiry
                'iss': 'netra-test',
                'aud': 'netra-api',
                'scope': 'test:agent'
            }
            
            # Use test secret - in real implementation this would come from config
            test_secret = self.env.get('JWT_SECRET_KEY', 'test-secret-key-for-resource-isolation-testing')
            
            # Generate JWT token
            token = jwt.encode(payload, test_secret, algorithm='HS256')
            
            logger.debug(f"Generated JWT token for user {user_id}, tenant {tenant_id}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate JWT token: {str(e)}")
            # Return a minimal test token as fallback
            return f"test-token-{user_id}-{tenant_id}-{int(time.time())}"
    
    async def _establish_single_agent_connection(self, agent: TenantAgent) -> Optional[TenantAgent]:
        """
        Establish WebSocket connection for a single agent.
        
        Args:
            agent: TenantAgent to connect
            
        Returns:
            Optional[TenantAgent]: Agent with established connection, or None if failed
        """
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Prepare connection headers with authentication
                headers = {
                    'Authorization': f'Bearer {agent.jwt_token}',
                    'X-Tenant-ID': agent.tenant_id,
                    'X-User-ID': agent.user_id
                }
                
                # Attempt WebSocket connection with timeout
                logger.debug(f"Connecting to {agent.websocket_uri} (attempt {attempt + 1}/{max_retries})")
                
                connection = await asyncio.wait_for(
                    websockets.connect(
                        agent.websocket_uri,
                        extra_headers=headers,
                        ping_interval=30,
                        ping_timeout=10
                    ),
                    timeout=10.0
                )
                
                # Perform authentication handshake
                auth_message = {
                    'type': 'auth',
                    'token': agent.jwt_token,
                    'tenant_id': agent.tenant_id,
                    'user_id': agent.user_id
                }
                
                await connection.send(json.dumps(auth_message))
                
                # Wait for auth confirmation (with timeout)
                try:
                    response = await asyncio.wait_for(connection.recv(), timeout=5.0)
                    auth_result = json.loads(response)
                    
                    if auth_result.get('type') != 'auth_success':
                        logger.warning(f"Authentication failed for {agent.user_id}: {auth_result}")
                        await connection.close()
                        continue
                        
                except (asyncio.TimeoutError, json.JSONDecodeError) as e:
                    logger.warning(f"Auth handshake failed for {agent.user_id}: {e}")
                    await connection.close()
                    continue
                
                # Connection successful
                agent.connection = connection
                
                # Store connection for cleanup tracking
                if not hasattr(self, '_websocket_connections'):
                    self._websocket_connections = {}
                self._websocket_connections[agent.user_id] = agent
                
                logger.debug(f"Successfully connected agent {agent.user_id}")
                return agent
                
            except (websockets.exceptions.WebSocketException, 
                   asyncio.TimeoutError, 
                   ConnectionRefusedError, 
                   OSError) as e:
                logger.warning(f"Connection attempt {attempt + 1} failed for {agent.user_id}: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                    
            except Exception as e:
                logger.error(f"Unexpected error connecting {agent.user_id}: {e}")
                break
        
        logger.error(f"Failed to establish connection for agent {agent.user_id} after {max_retries} attempts")
        return None
    
    async def _close_websocket_connections(self, agents: List[TenantAgent]) -> None:
        """
        Close WebSocket connections for a list of agents.
        
        Args:
            agents: List of TenantAgent instances with connections to close
        """
        if not agents:
            return
            
        logger.debug(f"Closing {len(agents)} WebSocket connections")
        
        close_tasks = []
        for agent in agents:
            if agent.connection and not agent.connection.closed:
                task = asyncio.create_task(self._close_single_connection(agent))
                close_tasks.append(task)
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        logger.debug("WebSocket connection cleanup complete")
    
    async def _close_single_connection(self, agent: TenantAgent) -> None:
        """
        Close a single WebSocket connection gracefully.
        
        Args:
            agent: TenantAgent with connection to close
        """
        try:
            if agent.connection and not agent.connection.closed:
                await asyncio.wait_for(agent.connection.close(), timeout=5.0)
                logger.debug(f"Closed connection for agent {agent.user_id}")
        except Exception as e:
            logger.warning(f"Error closing connection for {agent.user_id}: {e}")
        finally:
            agent.connection = None