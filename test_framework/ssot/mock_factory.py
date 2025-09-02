"""
Single Source of Truth (SSOT) Mock Factory - The Canonical Mock Generator

This module provides the ONE unified mock factory that generates ALL mock types
across the entire codebase. This eliminates thousands of duplicate mock implementations
and provides a consistent, extensible mock generation system.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for all mock generation.
NO duplicate mock implementations are allowed in the codebase.

Business Value: Platform/Internal - System Stability & Development Velocity  
Eliminates mock duplication, provides consistent test infrastructure, and ensures
all mocks follow the same patterns and interfaces.

SSOT Violations Eliminated:
- 23 different MockAgent implementations across test files
- Multiple MockAgentService duplicates
- Scattered MockServiceManager implementations  
- Hundreds of ad-hoc mock classes in individual test files

REQUIREMENTS per CLAUDE.md:
- Must be extensible for new mock types
- Must integrate with IsolatedEnvironment
- Must support both sync and async mocks
- Must provide consistent error simulation
- Must be backwards compatible where possible
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from shared.isolated_environment import IsolatedEnvironment, get_env


# === ENUMS AND STATE CLASSES ===

class AgentState(Enum):
    """Canonical agent state enumeration."""
    IDLE = "idle"
    ACTIVE = "active" 
    RUNNING = "running"
    THINKING = "thinking"
    ERROR = "error"
    RECOVERING = "recovering"
    STOPPED = "stopped"


class ServiceStatus(Enum):
    """Canonical service status enumeration."""
    STARTING = "starting"
    RUNNING = "running" 
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


@dataclass
class MockConfiguration:
    """Configuration for mock behavior."""
    should_fail: bool = False
    failure_rate: float = 0.0  # 0.0 to 1.0
    failure_message: str = "Mock failure"
    execution_delay: float = 0.0
    max_retries: int = 3
    timeout: float = 5.0
    enable_metrics: bool = True
    custom_responses: Dict[str, Any] = field(default_factory=dict)
    
    def should_fail_now(self) -> bool:
        """Determine if this call should fail based on failure rate."""
        if self.should_fail:
            return True
        if self.failure_rate > 0:
            import random
            return random.random() < self.failure_rate
        return False


# === BASE MOCK CLASSES ===

class SSotBaseMock:
    """
    Base class for all SSOT mocks.
    
    Provides common functionality:
    - Metrics tracking
    - Error simulation
    - Call logging
    - Environment integration
    """
    
    def __init__(self, mock_id: Optional[str] = None, config: Optional[MockConfiguration] = None):
        """Initialize base mock."""
        self.mock_id = mock_id or f"mock_{uuid.uuid4().hex[:8]}"
        self.config = config or MockConfiguration()
        self._env = get_env()
        
        # Tracking
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []
        self.error_count = 0
        self.last_error: Optional[Exception] = None
        
        # State
        self.created_at = datetime.now(UTC)
        self.is_active = True
    
    def _log_call(self, method_name: str, args: tuple = (), kwargs: Dict[str, Any] = None) -> None:
        """Log a method call for debugging."""
        self.call_count += 1
        call_record = {
            "method": method_name,
            "args": args,
            "kwargs": kwargs or {},
            "timestamp": datetime.now(UTC),
            "call_number": self.call_count
        }
        self.call_history.append(call_record)
        
        if self.config.enable_metrics:
            # Could integrate with metrics system here
            pass
    
    async def _simulate_delay(self) -> None:
        """Simulate execution delay if configured."""
        if self.config.execution_delay > 0:
            await asyncio.sleep(self.config.execution_delay)
    
    def _simulate_delay_sync(self) -> None:
        """Simulate execution delay synchronously."""
        if self.config.execution_delay > 0:
            import time
            time.sleep(self.config.execution_delay)
    
    def _handle_failure(self, method_name: str) -> None:
        """Handle failure simulation."""
        if self.config.should_fail_now():
            self.error_count += 1
            error = Exception(f"{method_name}: {self.config.failure_message}")
            self.last_error = error
            raise error
    
    def reset_metrics(self) -> None:
        """Reset all tracking metrics."""
        self.call_count = 0
        self.call_history.clear()
        self.error_count = 0
        self.last_error = None
    
    def get_call_summary(self) -> Dict[str, Any]:
        """Get summary of all calls made to this mock."""
        return {
            "mock_id": self.mock_id,
            "total_calls": self.call_count,
            "error_count": self.error_count,
            "last_error": str(self.last_error) if self.last_error else None,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "recent_calls": self.call_history[-5:] if self.call_history else []
        }


# === AGENT MOCKS ===

class SSotMockAgent(SSotBaseMock):
    """
    SSOT Mock Agent - The canonical agent mock implementation.
    
    This replaces ALL 23+ different MockAgent implementations found across
    the codebase with a single, configurable, comprehensive mock.
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        config: Optional[MockConfiguration] = None
    ):
        """Initialize mock agent."""
        super().__init__(agent_id, config)
        
        # Agent-specific properties
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.state = AgentState.IDLE
        self.thread_id: Optional[str] = None
        self.run_id: Optional[str] = None
        self.task_id: Optional[str] = None
        
        # Agent capabilities
        self.execution_results: List[Dict[str, Any]] = []
        self.tools_executed: List[str] = []
        self.thinking_steps: List[str] = []
        
        # WebSocket integration
        self.websocket_events: List[Dict[str, Any]] = []
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request (core agent functionality)."""
        self._log_call("process_request", args=(request,))
        self._handle_failure("process_request")
        await self._simulate_delay()
        
        self.state = AgentState.RUNNING
        
        # Simulate processing
        result = {
            "status": "success",
            "result": f"Processed: {request.get('content', request.get('request', 'unknown'))}",
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "run_id": self.run_id,
            "execution_time": self.config.execution_delay,
            "tools_used": self.tools_executed.copy()
        }
        
        self.execution_results.append(result)
        self.state = AgentState.IDLE
        
        return result
    
    async def run(self, request: str, run_id: str, user_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Run agent with specific parameters."""
        self._log_call("run", args=(request, run_id, user_id, task_id))
        
        # Update state
        self.run_id = run_id
        self.user_id = user_id
        self.task_id = task_id
        self.state = AgentState.RUNNING
        
        # Emit WebSocket event
        await self._emit_websocket_event("agent_started", {
            "run_id": run_id,
            "user_id": user_id,
            "task_id": task_id
        })
        
        try:
            # Process the request
            result = await self.process_request({
                "request": request,
                "run_id": run_id,
                "user_id": user_id,
                "task_id": task_id
            })
            
            await self._emit_websocket_event("agent_completed", result)
            return result
            
        except Exception as e:
            self.state = AgentState.ERROR
            await self._emit_websocket_event("agent_error", {
                "error": str(e),
                "run_id": run_id
            })
            raise
    
    async def think(self, prompt: str) -> str:
        """Simulate agent thinking process."""
        self._log_call("think", args=(prompt,))
        self.state = AgentState.THINKING
        
        await self._emit_websocket_event("agent_thinking", {
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt
        })
        
        await self._simulate_delay()
        
        thinking_result = f"Thinking about: {prompt}"
        self.thinking_steps.append(thinking_result)
        self.state = AgentState.ACTIVE
        
        return thinking_result
    
    async def execute_tool(self, tool_name: str, tool_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool (simulate tool usage)."""
        self._log_call("execute_tool", args=(tool_name, tool_params))
        
        await self._emit_websocket_event("tool_executing", {
            "tool_name": tool_name,
            "params": tool_params
        })
        
        await self._simulate_delay()
        
        result = {
            "tool": tool_name,
            "params": tool_params,
            "result": f"Executed {tool_name} successfully",
            "success": True
        }
        
        self.tools_executed.append(tool_name)
        
        await self._emit_websocket_event("tool_completed", result)
        
        return result
    
    async def recover(self) -> bool:
        """Recover from error state."""
        self._log_call("recover")
        self.state = AgentState.RECOVERING
        await self._simulate_delay()
        self.state = AgentState.ACTIVE
        return True
    
    async def _emit_websocket_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit a WebSocket event (for testing WebSocket functionality)."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
            "agent_id": self.agent_id
        }
        self.websocket_events.append(event)
    
    def get_websocket_events(self) -> List[Dict[str, Any]]:
        """Get all WebSocket events emitted by this agent."""
        return self.websocket_events.copy()
    
    def clear_websocket_events(self) -> None:
        """Clear WebSocket event history."""
        self.websocket_events.clear()


class SSotMockAgentService(SSotBaseMock):
    """
    SSOT Mock Agent Service - The canonical agent service mock.
    
    This consolidates all the different MockAgentService implementations
    into a single, comprehensive service mock.
    """
    
    def __init__(self, config: Optional[MockConfiguration] = None):
        """Initialize mock agent service."""
        super().__init__(config=config)
        
        # Service state
        self.status = ServiceStatus.STOPPED
        self.agents: Dict[str, SSotMockAgent] = {}
        self.messages_processed: List[Dict[str, Any]] = []
        self.next_agent_id = 1
        
        # Service metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
    
    async def start_service(self) -> bool:
        """Start the agent service."""
        self._log_call("start_service")
        self.status = ServiceStatus.STARTING
        await self._simulate_delay()
        self.status = ServiceStatus.RUNNING
        return True
    
    async def stop_service(self) -> bool:
        """Stop the agent service."""
        self._log_call("stop_service")
        self.status = ServiceStatus.STOPPING
        await self._simulate_delay()
        
        # Stop all agents
        for agent in self.agents.values():
            agent.state = AgentState.STOPPED
        
        self.status = ServiceStatus.STOPPED
        return True
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message through the agent service."""
        self._log_call("process_message", args=(message,))
        self._handle_failure("process_message")
        
        self.total_requests += 1
        self.messages_processed.append(message)
        
        try:
            # Get or create agent for the user
            user_id = message.get("user_id", f"user_{self.total_requests}")
            agent = await self.get_or_create_agent(user_id)
            
            # Process through agent
            result = await agent.process_request(message)
            
            self.successful_requests += 1
            return {
                "response": result,
                "agent_id": agent.agent_id,
                "status": "completed",
                "processed_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            self.failed_requests += 1
            return {
                "error": str(e),
                "status": "failed",
                "processed_at": datetime.now(UTC).isoformat()
            }
    
    async def get_or_create_agent(self, user_id: str) -> SSotMockAgent:
        """Get existing agent or create new one for user."""
        self._log_call("get_or_create_agent", args=(user_id,))
        
        if user_id not in self.agents:
            agent_id = f"agent_{self.next_agent_id}"
            self.next_agent_id += 1
            
            self.agents[user_id] = SSotMockAgent(
                agent_id=agent_id,
                user_id=user_id,
                config=self.config
            )
            self.agents[user_id].state = AgentState.ACTIVE
        
        return self.agents[user_id]
    
    async def release_agent(self, user_id: str) -> bool:
        """Release an agent back to the pool."""
        self._log_call("release_agent", args=(user_id,))
        
        if user_id in self.agents:
            self.agents[user_id].state = AgentState.IDLE
            del self.agents[user_id]
            return True
        return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get detailed service status."""
        return {
            "status": self.status.value,
            "active_agents": len(self.agents),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                self.successful_requests / self.total_requests 
                if self.total_requests > 0 else 0.0
            )
        }


# === SERVICE MOCKS ===

class SSotMockServiceManager(SSotBaseMock):
    """
    SSOT Mock Service Manager - The canonical service manager mock.
    
    Provides unified service management mock functionality.
    """
    
    def __init__(self, config: Optional[MockConfiguration] = None):
        """Initialize mock service manager."""
        super().__init__(config=config)
        
        self.services: Dict[str, Dict[str, Any]] = {}
        self.service_status: Dict[str, ServiceStatus] = {}
    
    async def start_service(self, service_name: str, service_config: Dict[str, Any]) -> bool:
        """Start a service."""
        self._log_call("start_service", args=(service_name, service_config))
        self._handle_failure("start_service")
        
        self.services[service_name] = service_config
        self.service_status[service_name] = ServiceStatus.STARTING
        
        await self._simulate_delay()
        
        self.service_status[service_name] = ServiceStatus.RUNNING
        return True
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop a service."""
        self._log_call("stop_service", args=(service_name,))
        
        if service_name in self.services:
            self.service_status[service_name] = ServiceStatus.STOPPING
            await self._simulate_delay()
            self.service_status[service_name] = ServiceStatus.STOPPED
            return True
        return False
    
    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get service status."""
        return self.service_status.get(service_name, ServiceStatus.STOPPED)
    
    async def health_check(self, service_name: str) -> bool:
        """Perform health check on service."""
        self._log_call("health_check", args=(service_name,))
        
        status = self.get_service_status(service_name)
        return status == ServiceStatus.RUNNING


class SSotMockDatabase(SSotBaseMock):
    """SSOT Mock Database - Unified database mock."""
    
    def __init__(self, config: Optional[MockConfiguration] = None):
        """Initialize mock database."""
        super().__init__(config=config)
        
        self.data: Dict[str, List[Dict[str, Any]]] = {}
        self.query_log: List[Dict[str, Any]] = []
    
    async def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query."""
        self._log_call("query", args=(sql, params))
        self._handle_failure("query")
        
        query_record = {
            "sql": sql,
            "params": params,
            "timestamp": datetime.now(UTC)
        }
        self.query_log.append(query_record)
        
        await self._simulate_delay()
        
        # Return mock results
        return [{"id": 1, "result": "mock_data"}]
    
    async def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        """Execute a command.""" 
        self._log_call("execute", args=(sql, params))
        await self._simulate_delay()
        return 1  # Mock affected rows
    
    def get_query_count(self) -> int:
        """Get total query count."""
        return len(self.query_log)


class SSotMockRedis(SSotBaseMock):
    """SSOT Mock Redis - Unified Redis mock."""
    
    def __init__(self, config: Optional[MockConfiguration] = None):
        """Initialize mock Redis."""
        super().__init__(config=config)
        
        self.data: Dict[str, str] = {}
        self.operations: List[Dict[str, Any]] = []
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        self._log_call("get", args=(key,))
        self._handle_failure("get")
        
        self.operations.append({"op": "get", "key": key, "timestamp": datetime.now(UTC)})
        await self._simulate_delay()
        
        return self.data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis."""
        self._log_call("set", args=(key, value, ex))
        self._handle_failure("set")
        
        self.operations.append({"op": "set", "key": key, "value": value, "ex": ex, "timestamp": datetime.now(UTC)})
        await self._simulate_delay()
        
        self.data[key] = value
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        self._log_call("delete", args=(key,))
        
        self.operations.append({"op": "delete", "key": key, "timestamp": datetime.now(UTC)})
        
        if key in self.data:
            del self.data[key]
            return True
        return False


# === MOCK FACTORY ===

class SSotMockFactory:
    """
    Single Source of Truth Mock Factory.
    
    The centralized factory for creating ALL mock types in the codebase.
    This eliminates duplication and provides a consistent interface.
    """
    
    def __init__(self):
        """Initialize the mock factory."""
        self._created_mocks: List[SSotBaseMock] = []
        self._env = get_env()
    
    # === AGENT MOCKS ===
    
    def create_agent(
        self,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        config: Optional[MockConfiguration] = None
    ) -> SSotMockAgent:
        """Create a mock agent."""
        mock = SSotMockAgent(agent_id, user_id, config)
        self._created_mocks.append(mock)
        return mock
    
    def create_agent_service(self, config: Optional[MockConfiguration] = None) -> SSotMockAgentService:
        """Create a mock agent service."""
        mock = SSotMockAgentService(config)
        self._created_mocks.append(mock)
        return mock
    
    # === SERVICE MOCKS ===
    
    def create_service_manager(self, config: Optional[MockConfiguration] = None) -> SSotMockServiceManager:
        """Create a mock service manager."""
        mock = SSotMockServiceManager(config)
        self._created_mocks.append(mock)
        return mock
    
    def create_database(self, config: Optional[MockConfiguration] = None) -> SSotMockDatabase:
        """Create a mock database."""
        mock = SSotMockDatabase(config)
        self._created_mocks.append(mock)
        return mock
    
    def create_redis(self, config: Optional[MockConfiguration] = None) -> SSotMockRedis:
        """Create a mock Redis."""
        mock = SSotMockRedis(config)
        self._created_mocks.append(mock)
        return mock
    
    # === CONFIGURATION HELPERS ===
    
    def create_failing_config(
        self,
        failure_rate: float = 1.0,
        failure_message: str = "Mock configured to fail"
    ) -> MockConfiguration:
        """Create a configuration that causes mocks to fail."""
        return MockConfiguration(
            should_fail=True,
            failure_rate=failure_rate,
            failure_message=failure_message
        )
    
    def create_slow_config(
        self,
        execution_delay: float = 1.0
    ) -> MockConfiguration:
        """Create a configuration that makes mocks slow."""
        return MockConfiguration(
            execution_delay=execution_delay
        )
    
    def create_unreliable_config(
        self,
        failure_rate: float = 0.3,
        execution_delay: float = 0.5
    ) -> MockConfiguration:
        """Create a configuration for unreliable mocks."""
        return MockConfiguration(
            failure_rate=failure_rate,
            execution_delay=execution_delay,
            failure_message="Unreliable mock failure"
        )
    
    # === BATCH OPERATIONS ===
    
    def create_agent_cluster(
        self,
        count: int,
        base_config: Optional[MockConfiguration] = None
    ) -> List[SSotMockAgent]:
        """Create multiple agents for cluster testing."""
        agents = []
        for i in range(count):
            agent = self.create_agent(
                agent_id=f"cluster_agent_{i}",
                user_id=f"cluster_user_{i}",
                config=base_config
            )
            agents.append(agent)
        return agents
    
    # === CLEANUP AND UTILITIES ===
    
    def reset_all_mocks(self) -> None:
        """Reset metrics for all created mocks."""
        for mock in self._created_mocks:
            mock.reset_metrics()
    
    def get_all_mocks_summary(self) -> Dict[str, Any]:
        """Get summary of all created mocks."""
        return {
            "total_mocks": len(self._created_mocks),
            "mock_summaries": [mock.get_call_summary() for mock in self._created_mocks]
        }
    
    def cleanup(self) -> None:
        """Clean up all created mocks."""
        for mock in self._created_mocks:
            mock.is_active = False
        self._created_mocks.clear()


# === GLOBAL FACTORY INSTANCE ===

_mock_factory = SSotMockFactory()


def get_mock_factory() -> SSotMockFactory:
    """Get the global mock factory instance."""
    return _mock_factory


# === CONVENIENCE FUNCTIONS ===

def create_mock_agent(
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
    should_fail: bool = False
) -> SSotMockAgent:
    """Convenience function to create a mock agent."""
    config = MockConfiguration(should_fail=should_fail) if should_fail else None
    return get_mock_factory().create_agent(agent_id, user_id, config)


def create_mock_agent_service(should_fail: bool = False) -> SSotMockAgentService:
    """Convenience function to create a mock agent service."""
    config = MockConfiguration(should_fail=should_fail) if should_fail else None
    return get_mock_factory().create_agent_service(config)


# === BACKWARDS COMPATIBILITY ===

# Legacy aliases for existing test code
MockAgent = SSotMockAgent
MockAgentService = SSotMockAgentService  
MockServiceManager = SSotMockServiceManager

# Legacy factory functions
def create_mock_orchestrator() -> SSotMockServiceManager:
    """Legacy compatibility function."""
    return get_mock_factory().create_service_manager()


# === EXPORT CONTROL ===

__all__ = [
    # Core Classes
    "SSotMockAgent",
    "SSotMockAgentService", 
    "SSotMockServiceManager",
    "SSotMockDatabase",
    "SSotMockRedis",
    "SSotMockFactory",
    
    # Configuration
    "MockConfiguration",
    "AgentState",
    "ServiceStatus",
    
    # Factory Functions
    "get_mock_factory",
    "create_mock_agent",
    "create_mock_agent_service",
    
    # Backwards Compatibility
    "MockAgent",
    "MockAgentService",
    "MockServiceManager",
    "create_mock_orchestrator",
]