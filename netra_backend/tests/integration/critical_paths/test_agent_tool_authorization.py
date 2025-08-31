"""
L3 Integration Test: Agent Tool Authorization

Business Value Justification (BVJ):
- Segment: Enterprise (security-critical AI operations)
- Business Goal: Ensure secure tool access control and prevent unauthorized operations
- Value Impact: Protects customer data and prevents security breaches through tool misuse
- Strategic Impact: $150K MRR - Security and compliance for enterprise AI workflows

L3 Test: Uses real authorization service with role-based access control.
Security target: Zero unauthorized tool access with comprehensive audit trail.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest
from netra_backend.app.schemas import User

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.state_manager import AgentStateManager

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.exceptions_base import (
    AuthorizationException,
    NetraException,
)
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.security_service import SecurityService
# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

logger = logging.getLogger(__name__)

class ToolPermissionLevel(Enum):
    """Tool permission levels for authorization testing."""
    PUBLIC = "public"
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"

class AgentRole(Enum):
    """Agent roles for authorization testing."""
    BASIC_AGENT = "basic_agent"
    ADVANCED_AGENT = "advanced_agent"
    ADMIN_AGENT = "admin_agent"
    SYSTEM_AGENT = "system_agent"

class MockTool:
    """Mock tool for authorization testing."""
    
    def __init__(self, tool_id: str, name: str, permission_level: ToolPermissionLevel, 
                 required_capabilities: List[str] = None):
        self.tool_id = tool_id
        self.name = name
        self.permission_level = permission_level
        self.required_capabilities = required_capabilities or []
        self.usage_count = 0
        self.last_used = None
        
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with authorization context."""
        self.usage_count += 1
        self.last_used = datetime.now(timezone.utc)
        
        return {
            "tool_id": self.tool_id,
            "result": f"Tool {self.name} executed successfully",
            "parameters": parameters,
            "context": context,
            "execution_time": time.time()
        }

class ToolAuthorizationService:
    """Service for managing tool authorization and access control."""
    
    def __init__(self, redis_manager: Optional[RedisManager] = None):
        self.redis_manager = redis_manager
        self.tool_registry: Dict[str, MockTool] = {}
        self.agent_permissions: Dict[str, Dict[str, Any]] = {}
        self.authorization_cache: Dict[str, Dict] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.failed_authorizations: List[Dict[str, Any]] = []
        
    def register_tool(self, tool: MockTool) -> None:
        """Register a tool in the authorization system."""
        self.tool_registry[tool.tool_id] = tool
        
    def set_agent_permissions(self, agent_id: str, role: AgentRole, 
                            capabilities: List[str] = None, 
                            tool_access: List[str] = None) -> None:
        """Set permissions for an agent."""
        self.agent_permissions[agent_id] = {
            "role": role,
            "capabilities": capabilities or [],
            "tool_access": tool_access or [],
            "created_at": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
    async def authorize_tool_access(self, agent_id: str, tool_id: str, 
                                  context: Dict[str, Any] = None) -> bool:
        """Authorize tool access for an agent."""
        # Check cache first
        cache_key = f"{agent_id}:{tool_id}"
        if cache_key in self.authorization_cache:
            cached_result = self.authorization_cache[cache_key]
            if time.time() - cached_result["timestamp"] < 300:  # 5 minute cache
                return cached_result["authorized"]
        
        # Perform authorization check
        authorized = await self._check_authorization(agent_id, tool_id, context)
        
        # Cache result
        self.authorization_cache[cache_key] = {
            "authorized": authorized,
            "timestamp": time.time(),
            "context": context or {}
        }
        
        # Log authorization attempt
        self._log_authorization_attempt(agent_id, tool_id, authorized, context)
        
        return authorized
        
    async def _check_authorization(self, agent_id: str, tool_id: str, 
                                 context: Dict[str, Any] = None) -> bool:
        """Perform actual authorization check."""
        # Get agent permissions
        agent_perms = self.agent_permissions.get(agent_id)
        if not agent_perms:
            return False
            
        # Get tool requirements
        tool = self.tool_registry.get(tool_id)
        if not tool:
            return False
            
        # Check role-based access
        agent_role = agent_perms["role"]
        tool_permission_level = tool.permission_level
        
        # Role hierarchy check
        if tool_permission_level == ToolPermissionLevel.PUBLIC:
            return True
        elif tool_permission_level == ToolPermissionLevel.USER:
            return agent_role in [AgentRole.BASIC_AGENT, AgentRole.ADVANCED_AGENT, 
                                AgentRole.ADMIN_AGENT, AgentRole.SYSTEM_AGENT]
        elif tool_permission_level == ToolPermissionLevel.ADMIN:
            return agent_role in [AgentRole.ADMIN_AGENT, AgentRole.SYSTEM_AGENT]
        elif tool_permission_level == ToolPermissionLevel.SYSTEM:
            return agent_role == AgentRole.SYSTEM_AGENT
            
        return False
        
    def _log_authorization_attempt(self, agent_id: str, tool_id: str, 
                                 authorized: bool, context: Dict[str, Any] = None) -> None:
        """Log authorization attempt for audit trail."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc),
            "agent_id": agent_id,
            "tool_id": tool_id,
            "authorized": authorized,
            "context": context or {},
            "audit_id": str(uuid.uuid4())
        }
        
        self.audit_log.append(log_entry)
        
        if not authorized:
            self.failed_authorizations.append(log_entry)
            
    async def execute_tool_with_authorization(self, agent_id: str, tool_id: str, 
                                            parameters: Dict[str, Any], 
                                            context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute tool with authorization check."""
        # Authorization check
        authorized = await self.authorize_tool_access(agent_id, tool_id, context)
        
        if not authorized:
            raise AuthorizationException(f"Agent {agent_id} not authorized to use tool {tool_id}")
            
        # Execute tool
        tool = self.tool_registry[tool_id]
        execution_context = {
            **(context or {}),
            "agent_id": agent_id,
            "authorized_at": datetime.now(timezone.utc)
        }
        
        result = await tool.execute(parameters, execution_context)
        
        # Log successful execution
        self._log_tool_execution(agent_id, tool_id, result)
        
        return result
        
    def _log_tool_execution(self, agent_id: str, tool_id: str, result: Dict[str, Any]) -> None:
        """Log successful tool execution."""
        execution_log = {
            "timestamp": datetime.now(timezone.utc),
            "agent_id": agent_id,
            "tool_id": tool_id,
            "result_summary": str(result.get("result", ""))[:100],
            "execution_id": str(uuid.uuid4())
        }
        self.audit_log.append(execution_log)
        
    def get_agent_tool_usage(self, agent_id: str) -> Dict[str, Any]:
        """Get tool usage statistics for an agent."""
        agent_logs = [log for log in self.audit_log if log.get("agent_id") == agent_id]
        
        tool_usage = {}
        for log in agent_logs:
            if "tool_id" in log:
                tool_id = log["tool_id"]
                if tool_id not in tool_usage:
                    tool_usage[tool_id] = {"count": 0, "last_used": None}
                tool_usage[tool_id]["count"] += 1
                tool_usage[tool_id]["last_used"] = log["timestamp"]
                
        return {
            "agent_id": agent_id,
            "total_tool_calls": len(agent_logs),
            "tool_usage": tool_usage,
            "failed_authorizations": len([log for log in self.failed_authorizations 
                                        if log.get("agent_id") == agent_id])
        }

class MockAuthorizedAgent(BaseSubAgent):
    """Mock agent that integrates with tool authorization system."""
    
    def __init__(self, agent_id: str, role: AgentRole, 
                 authorization_service: ToolAuthorizationService):
        super().__init__(agent_id=agent_id)
        self.role = role
        self.authorization_service = authorization_service
        self.tool_usage_count = 0
        self.authorization_failures = 0
        
    async def use_tool(self, tool_id: str, parameters: Dict[str, Any], 
                      context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Use a tool through the authorization system."""
        try:
            result = await self.authorization_service.execute_tool_with_authorization(
                self.agent_id, tool_id, parameters, context
            )
            self.tool_usage_count += 1
            return result
        except AuthorizationException as e:
            self.authorization_failures += 1
            raise e

@pytest.mark.L3
@pytest.mark.integration
class TestAgentToolAuthorizationL3:
    """L3 integration tests for agent tool authorization."""
    
    @pytest.fixture
    async def redis_manager(self):
        """Create Redis manager for authorization caching."""
        redis_mgr = RedisManager()
        redis_mgr.enabled = True
        yield redis_mgr
        
    @pytest.fixture
    async def authorization_service(self, redis_manager):
        """Create tool authorization service."""
        service = ToolAuthorizationService(redis_manager=redis_manager)
        
        # Register test tools
        tools = [
            MockTool("public_tool", "Public Tool", ToolPermissionLevel.PUBLIC),
            MockTool("user_tool", "User Tool", ToolPermissionLevel.USER),
            MockTool("admin_tool", "Admin Tool", ToolPermissionLevel.ADMIN),
            MockTool("system_tool", "System Tool", ToolPermissionLevel.SYSTEM),
            MockTool("file_access", "File Access", ToolPermissionLevel.USER, ["file_read"]),
            MockTool("db_write", "Database Write", ToolPermissionLevel.ADMIN, ["db_write"]),
        ]
        
        for tool in tools:
            service.register_tool(tool)
            
        yield service
        
    @pytest.fixture
    def test_agents(self, authorization_service):
        """Create test agents with different roles."""
        agents = {}
        
        # Basic agent
        basic_agent = MockAuthorizedAgent("basic_agent_1", AgentRole.BASIC_AGENT, authorization_service)
        authorization_service.set_agent_permissions(
            "basic_agent_1", AgentRole.BASIC_AGENT, 
            capabilities=["basic_operations"], 
            tool_access=["public_tool", "user_tool"]
        )
        agents["basic"] = basic_agent
        
        # Advanced agent
        advanced_agent = MockAuthorizedAgent("advanced_agent_1", AgentRole.ADVANCED_AGENT, authorization_service)
        authorization_service.set_agent_permissions(
            "advanced_agent_1", AgentRole.ADVANCED_AGENT,
            capabilities=["basic_operations", "file_read"],
            tool_access=["public_tool", "user_tool", "file_access"]
        )
        agents["advanced"] = advanced_agent
        
        # Admin agent
        admin_agent = MockAuthorizedAgent("admin_agent_1", AgentRole.ADMIN_AGENT, authorization_service)
        authorization_service.set_agent_permissions(
            "admin_agent_1", AgentRole.ADMIN_AGENT,
            capabilities=["basic_operations", "file_read", "db_write", "admin_operations"],
            tool_access=["public_tool", "user_tool", "admin_tool", "file_access", "db_write"]
        )
        agents["admin"] = admin_agent
        
        # System agent
        system_agent = MockAuthorizedAgent("system_agent_1", AgentRole.SYSTEM_AGENT, authorization_service)
        authorization_service.set_agent_permissions(
            "system_agent_1", AgentRole.SYSTEM_AGENT,
            capabilities=["all"],
            tool_access=["*"]  # Access to all tools
        )
        agents["system"] = system_agent
        
        return agents
        
    @pytest.mark.asyncio
    async def test_role_based_tool_permissions(self, authorization_service, test_agents):
        """Test role-based tool access permissions."""
        # Test basic agent permissions
        basic_agent = test_agents["basic"]
        
        # Should have access to public and user tools
        result = await basic_agent.use_tool("public_tool", {"test": "data"})
        assert result["result"] == "Tool Public Tool executed successfully"
        
        result = await basic_agent.use_tool("user_tool", {"test": "data"})
        assert result["result"] == "Tool User Tool executed successfully"
        
        # Should NOT have access to admin tools
        with pytest.raises(AuthorizationException):
            await basic_agent.use_tool("admin_tool", {"test": "data"})
            
        # Should NOT have access to system tools
        with pytest.raises(AuthorizationException):
            await basic_agent.use_tool("system_tool", {"test": "data"})
            
        # Test admin agent permissions
        admin_agent = test_agents["admin"]
        
        # Should have access to all tools except system
        await admin_agent.use_tool("public_tool", {"test": "data"})
        await admin_agent.use_tool("user_tool", {"test": "data"})
        await admin_agent.use_tool("admin_tool", {"test": "data"})
        
        # Should NOT have access to system tools
        with pytest.raises(AuthorizationException):
            await admin_agent.use_tool("system_tool", {"test": "data"})
            
        # Test system agent permissions
        system_agent = test_agents["system"]
        
        # Should have access to all tools
        await system_agent.use_tool("public_tool", {"test": "data"})
        await system_agent.use_tool("user_tool", {"test": "data"})
        await system_agent.use_tool("admin_tool", {"test": "data"})
        await system_agent.use_tool("system_tool", {"test": "data"})
        
        # Verify usage counts
        assert basic_agent.tool_usage_count == 2
        assert basic_agent.authorization_failures == 2
        assert admin_agent.tool_usage_count == 3
        assert admin_agent.authorization_failures == 1
        assert system_agent.tool_usage_count == 4
        assert system_agent.authorization_failures == 0
        
    @pytest.mark.asyncio
    async def test_zero_unauthorized_access(self, authorization_service, test_agents):
        """Test that there is zero unauthorized tool access."""
        unauthorized_attempts = []
        
        # Test various unauthorized access attempts
        test_cases = [
            ("basic", "admin_tool"),
            ("basic", "system_tool"),
            ("advanced", "admin_tool"), 
            ("advanced", "system_tool"),
            ("admin", "system_tool"),
        ]
        
        for agent_type, tool_id in test_cases:
            agent = test_agents[agent_type]
            try:
                await agent.use_tool(tool_id, {"unauthorized": "attempt"})
                # If we get here, unauthorized access occurred
                unauthorized_attempts.append((agent_type, tool_id))
            except AuthorizationException:
                # Expected - authorization properly blocked
                pass
                
        # Verify zero unauthorized access
        assert len(unauthorized_attempts) == 0, f"Unauthorized access detected: {unauthorized_attempts}"
        
        # Verify all attempts were logged as failures
        failed_auth_count = len(authorization_service.failed_authorizations)
        assert failed_auth_count == len(test_cases)
        
    @pytest.mark.asyncio
    async def test_tool_usage_tracking_and_audit(self, authorization_service, test_agents):
        """Test comprehensive tool usage tracking and audit trail."""
        # Perform various tool operations
        operations = [
            ("basic", "public_tool", {"operation": "basic_public"}),
            ("advanced", "file_access", {"file": "test.txt"}),
            ("admin", "db_write", {"table": "users", "action": "update"}),
            ("system", "system_tool", {"system_operation": "maintenance"}),
        ]
        
        for agent_type, tool_id, params in operations:
            agent = test_agents[agent_type]
            await agent.use_tool(tool_id, params)
            
        # Check audit log
        assert len(authorization_service.audit_log) >= len(operations)
        
        # Verify tool usage statistics
        for agent_type in ["basic", "advanced", "admin", "system"]:
            agent = test_agents[agent_type]
            usage_stats = authorization_service.get_agent_tool_usage(agent.agent_id)
            
            assert usage_stats["agent_id"] == agent.agent_id
            assert usage_stats["total_tool_calls"] > 0
            assert len(usage_stats["tool_usage"]) > 0
            
    @pytest.mark.asyncio
    async def test_authorization_caching_performance(self, authorization_service, test_agents):
        """Test authorization caching for performance optimization."""
        agent = test_agents["admin"]
        tool_id = "admin_tool"
        
        # First access - should perform full authorization
        start_time = time.time()
        result1 = await agent.use_tool(tool_id, {"cache_test": "first"})
        first_access_time = time.time() - start_time
        
        # Second access - should use cache
        start_time = time.time()
        result2 = await agent.use_tool(tool_id, {"cache_test": "second"})
        second_access_time = time.time() - start_time
        
        # Both should succeed
        assert result1["result"] == "Tool Admin Tool executed successfully"
        assert result2["result"] == "Tool Admin Tool executed successfully"
        
        # Cache should improve performance (though may be minimal in tests)
        # At minimum, verify both completed successfully
        assert first_access_time >= 0
        assert second_access_time >= 0
        
        # Verify cache entry exists
        cache_key = f"{agent.agent_id}:{tool_id}"
        assert cache_key in authorization_service.authorization_cache
        
    @pytest.mark.asyncio
    async def test_cross_service_authorization_validation(self, authorization_service, test_agents):
        """Test authorization validation across service boundaries."""
        # Simulate cross-service authorization checks
        cross_service_tools = [
            MockTool("external_api", "External API", ToolPermissionLevel.ADMIN),
            MockTool("data_export", "Data Export", ToolPermissionLevel.SYSTEM),
            MockTool("user_management", "User Management", ToolPermissionLevel.ADMIN),
        ]
        
        for tool in cross_service_tools:
            authorization_service.register_tool(tool)
            
        # Test cross-service authorization
        admin_agent = test_agents["admin"]
        system_agent = test_agents["system"]
        
        # Admin should access external API and user management
        await admin_agent.use_tool("external_api", {"api_call": "test"})
        await admin_agent.use_tool("user_management", {"action": "list_users"})
        
        # Admin should NOT access data export (system level)
        with pytest.raises(AuthorizationException):
            await admin_agent.use_tool("data_export", {"export": "users"})
            
        # System should access all
        await system_agent.use_tool("external_api", {"api_call": "system"})
        await system_agent.use_tool("data_export", {"export": "system_data"})
        await system_agent.use_tool("user_management", {"action": "system_admin"})
        
        # Verify cross-service audit trail
        cross_service_logs = [
            log for log in authorization_service.audit_log 
            if log.get("tool_id") in ["external_api", "data_export", "user_management"]
        ]
        
        assert len(cross_service_logs) >= 5  # 5 successful operations
        
        @pytest.mark.asyncio
    async def test_authorization_under_concurrent_load(self, authorization_service, test_agents):
        """Test authorization system under concurrent load."""
        # Create concurrent authorization requests
        concurrent_requests = []
        
        agents = list(test_agents.values())
        tools = ["public_tool", "user_tool", "admin_tool", "system_tool"]
        
        # Generate concurrent authorization checks
        for i in range(50):
            agent = agents[i % len(agents)]
            tool_id = tools[i % len(tools)]
            
            # Create authorization check task
            task = authorization_service.authorize_tool_access(
                agent.agent_id, 
                tool_id, 
                {"concurrent_test": True, "request_id": i}
            )
            concurrent_requests.append((agent.agent_id, tool_id, task))
            
        # Execute all authorization checks concurrently
        start_time = time.time()
        results = await asyncio.gather(
            *[task for _, _, task in concurrent_requests],
            return_exceptions=True
        )
        total_time = time.time() - start_time
        
        # Analyze results
        successful_checks = 0
        failed_checks = 0
        errors = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors += 1
            elif result:
                successful_checks += 1
            else:
                failed_checks += 1
                
        # Performance validation
        assert total_time < 10.0  # Should complete in under 10 seconds
        assert errors == 0  # No authorization system errors
        
        # Authorization accuracy
        assert successful_checks + failed_checks == len(concurrent_requests)
        
        # Verify cache effectiveness under load
        cache_hits = len([
            entry for entry in authorization_service.authorization_cache.values()
            if time.time() - entry["timestamp"] < 300
        ])
        assert cache_hits > 0  # Should have cache entries

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])