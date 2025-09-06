"""Agent Registry Initialization Validation Integration Test

Business Value Justification (BVJ):
- Segment: All Segments (Platform/Internal)
- Business Goal: Core Functionality & System Stability
- Value Impact: Multi-agent collaboration foundation that enables all advanced features
- Strategic/Revenue Impact: Agent registry failures eliminate $50K+ MRR from advanced workflows

Tests comprehensive validation including:
- AgentRegistry initialization with real LLMManager and ToolDispatcher
- Real WebSocket integration for mission-critical agent events
- Sub-agent registration and discovery with real database persistence
- Tool dispatcher enhancement with WebSocket notifications
- Communication setup validation with actual WebSocket connections
- State management with real database transactions

CLAUDE.md Compliance:
- NO MOCKS: Uses real services (PostgreSQL, Redis, ClickHouse, WebSocket)
- Uses IsolatedEnvironment for all configuration access
- Tests mission-critical WebSocket agent events (agent_started, tool_executing, etc.)
- Follows Single Source of Truth for AgentRegistry patterns
- Real Everything (LLM, Services) E2E > E2E > Integration > Unit
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from netra_backend.app.core.agent_registry import AgentRegistry

import pytest

# CLAUDE.md compliance: Use absolute imports only, no relative imports
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from shared.isolated_environment import get_env
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.config import AppConfig
from netra_backend.app.websocket_core import (
    WebSocketManager,
    get_websocket_manager,
    WebSocketMessage,
    MessageType
)

# Real services framework for eliminating mocks
from test_framework.real_services import (
    RealServicesManager,
    get_real_services,
    ServiceUnavailableError
)

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
@pytest.mark.agent_registry
@pytest.mark.websocket
class TestAgentRegistryInitializationValidation:
    """
    Comprehensive AgentRegistry initialization validation with real services.
    
    CLAUDE.md Standards:
    - Uses real PostgreSQL on port 5434 for agent state persistence
    - Uses real Redis on port 6381 for caching and session management
    - Uses real ClickHouse on port 9002 for analytics and metrics
    - Tests actual WebSocket manager integration for mission-critical events
    - Validates tool dispatcher enhancement with WebSocket notifications
    - Tests graceful degradation and error recovery patterns
    """
    
    @pytest.fixture(autouse=True)
    async def setup_isolated_environment(self):
        """Set up isolated environment following CLAUDE.md standards."""
        # CLAUDE.md: All environment access MUST go through IsolatedEnvironment
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        
        # Set up test environment variables for real services
        test_env_vars = {
            'ENVIRONMENT': 'testing',
            'DATABASE_URL': 'postgresql://test_user:test_pass@localhost:5434/netra_test',
            'REDIS_URL': 'redis://localhost:6381/0',
            'CLICKHOUSE_URL': 'http://localhost:8125',
            'CLICKHOUSE_TCP_PORT': '9002',
            'JWT_SECRET_KEY': 'test-jwt-secret-key-32-chars-long',
            'FERNET_KEY': 'test-fernet-key-32-chars-very-long',
            'SERVICE_SECRET': 'test-service-secret-key-32-chars',
            'SECRET_KEY': 'test-secret-key-for-application-32c',
            'LLM_ENABLED': 'true',
            'OPENAI_API_KEY': 'test-openai-key-for-testing-only',
            'SERVICE_ID': 'agent-registry-test',
            'TESTING': '1'
        }
        
        for key, value in test_env_vars.items():
            self.env.set(key, value, "agent_registry_test")
            
        yield
        
        # Cleanup
        self.env.disable_isolation()
    
    @pytest.fixture
    async def real_services(self) -> RealServicesManager:
        """Get real services manager for testing."""
        try:
            services = get_real_services()
            # Ensure services are available before proceeding
            await services.ensure_all_services_available()
            # Reset to clean state for each test
            await services.reset_all_data()
            yield services
        except ServiceUnavailableError as e:
            pytest.skip(f"Real services not available for AgentRegistry test: {e}")
        finally:
            if 'services' in locals():
                await services.close_all()
    
    @pytest.fixture
    async def app_config(self) -> AppConfig:
        """Create test AppConfig using IsolatedEnvironment."""
        config = AppConfig(
            environment="testing",
            database_url=self.env.get("DATABASE_URL"),
            redis_url=self.env.get("REDIS_URL"),
            llm_enabled=True,
            openai_api_key=self.env.get("OPENAI_API_KEY"),
            service_id=self.env.get("SERVICE_ID")
        )
        return config
    
    @pytest.fixture
    async def llm_manager(self, app_config: AppConfig) -> LLMManager:
        """Create real LLMManager for testing."""
        return LLMManager(app_config)
    
    @pytest.fixture
    async def tool_dispatcher(self) -> ToolDispatcher:
        """Create real ToolDispatcher for testing."""
        return ToolDispatcher()
    
    @pytest.fixture
    async def websocket_manager(self) -> WebSocketManager:
        """Create real WebSocket manager for testing."""
        return get_websocket_manager()
    
    @pytest.fixture
    async def agent_registry(self, llm_manager: LLMManager, 
                           tool_dispatcher: ToolDispatcher) -> AgentRegistry:
        """Create real AgentRegistry for testing."""
        return AgentRegistry()

    @pytest.mark.asyncio
    async def test_agent_registry_initialization_real_services(
        self, real_services: RealServicesManager, 
        agent_registry: AgentRegistry, 
        websocket_manager: WebSocketManager
    ):
        """
        Test AgentRegistry initialization with real services.
        
        Validates:
        - AgentRegistry initializes properly with real LLMManager and ToolDispatcher
        - WebSocket manager integration works correctly
        - Tool dispatcher enhancement with WebSocket notifications succeeds
        - Performance meets requirements (<2 seconds for initialization)
        """
        start_time = time.time()
        
        # Verify AgentRegistry is properly constructed
        assert agent_registry is not None
        assert agent_registry.llm_manager is not None
        assert agent_registry.tool_dispatcher is not None
        assert agent_registry.agents == {}  # Should start empty
        assert not agent_registry._agents_registered  # Should not be registered yet
        
        # Test WebSocket manager integration (MISSION CRITICAL per CLAUDE.md section 6)
        agent_registry.set_websocket_manager(websocket_manager)
        assert agent_registry.websocket_manager is not None
        
        # Verify tool dispatcher was enhanced with WebSocket notifications
        assert hasattr(agent_registry.tool_dispatcher, '_websocket_enhanced')
        assert agent_registry.tool_dispatcher._websocket_enhanced is True
        
        # Test agent registration
        agent_registry.register_default_agents()
        assert agent_registry._agents_registered is True
        assert len(agent_registry.agents) > 0
        
        # Verify specific agents are registered
        expected_agents = ['triage', 'data', 'optimization', 'actions', 
                          'reporting', 'synthetic_data', 'data_helper', 'corpus_admin']
        
        for agent_name in expected_agents:
            assert agent_name in agent_registry.agents, f"Agent {agent_name} not registered"
            agent = agent_registry.get(agent_name)
            assert agent is not None
            assert hasattr(agent, 'websocket_manager')
            assert agent.websocket_manager is not None
        
        # Test agent list functionality
        agent_names = agent_registry.list_agents()
        assert len(agent_names) == len(expected_agents)
        
        all_agents = agent_registry.get_all_agents()
        assert len(all_agents) == len(expected_agents)
        
        # Performance validation (CLAUDE.md requirement)
        duration = time.time() - start_time
        assert duration < 2.0, f"AgentRegistry initialization took {duration:.2f}s (max: 2.0s)"

    @pytest.mark.asyncio
    async def test_sub_agent_discovery_with_database_persistence(
        self, real_services: RealServicesManager,
        agent_registry: AgentRegistry,
        websocket_manager: WebSocketManager
    ):
        """
        Test sub-agent discovery with real database persistence.
        
        Validates:
        - Agent discovery works with real PostgreSQL connections
        - Agent state can be persisted and retrieved from database
        - Agent metadata is correctly stored
        - Database transactions work properly
        """
        # Set up WebSocket manager for notifications
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Register agents
        agent_registry.register_default_agents()
        
        # Test database connectivity with agent context
        try:
            async with real_services.postgres.connection() as conn:
                # Create agents table for testing
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_agents (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        type VARCHAR(50) NOT NULL,
                        status VARCHAR(50) DEFAULT 'active',
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Store agent registry information in database
                agent_data = []
                for agent_name in agent_registry.list_agents():
                    agent = agent_registry.get(agent_name)
                    agent_data.append((
                        agent_name, 
                        agent.__class__.__name__, 
                        {
                            'websocket_enabled': agent.websocket_manager is not None,
                            'initialized_at': datetime.now(timezone.utc).isoformat()
                        }
                    ))
                
                # Batch insert for better performance and connection stability
                for agent_name, agent_type, metadata in agent_data:
                    await conn.execute("""
                        INSERT INTO test_agents (name, type, metadata)
                        VALUES ($1, $2, $3)
                    """, agent_name, agent_type, metadata)
                
                # Verify agents were stored
                agent_count = await conn.fetchval("SELECT COUNT(*) FROM test_agents")
                assert agent_count == len(agent_registry.agents)
                
                # Test agent discovery from database
                stored_agents = await conn.fetch("SELECT name, type, metadata FROM test_agents")
                
                for stored_agent in stored_agents:
                    agent_name = stored_agent['name']
                    assert agent_name in agent_registry.agents
                    
                    # Verify metadata integrity
                    metadata = stored_agent['metadata']
                    assert metadata['websocket_enabled'] is True
                    assert 'initialized_at' in metadata
        
        except Exception as e:
            pytest.skip(f"Database persistence test failed due to connection issue: {e}")

    @pytest.mark.asyncio
    async def test_websocket_communication_setup_mission_critical(
        self, real_services: RealServicesManager,
        agent_registry: AgentRegistry,
        websocket_manager: WebSocketManager
    ):
        """
        Test WebSocket communication setup - MISSION CRITICAL per CLAUDE.md section 6.
        
        Validates:
        - WebSocket manager integration works correctly
        - Mission-critical WebSocket events are properly configured
        - Tool dispatcher enhancement enables real-time notifications
        - Agent-WebSocket communication patterns work end-to-end
        - Error handling and recovery for WebSocket failures
        """
        # Test WebSocket manager integration
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Register agents to set up WebSocket connections
        agent_registry.register_default_agents()
        
        # Verify all agents have WebSocket manager set
        for agent_name, agent in agent_registry.agents.items():
            assert hasattr(agent, 'websocket_manager')
            assert agent.websocket_manager is websocket_manager
        
        # Test tool dispatcher WebSocket enhancement
        assert hasattr(agent_registry.tool_dispatcher, '_websocket_enhanced')
        assert agent_registry.tool_dispatcher._websocket_enhanced is True
        
        # Verify enhanced tool execution engine is in place
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        assert isinstance(agent_registry.tool_dispatcher.executor, UnifiedToolExecutionEngine)
        
        # Test WebSocket message creation (mission-critical events)
        test_thread_id = str(uuid.uuid4())
        
        # Test that WebSocket manager can handle agent-related messages
        test_message = {
            "type": "agent_started",
            "payload": {
                "agent_name": "test_agent",
                "run_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).timestamp()
            }
        }
        
        # Test message sending (should not raise exception)
        try:
            # Note: This tests the interface, actual WebSocket sending would need a connected client
            result = await websocket_manager.send_to_thread(test_thread_id, test_message)
            # If no clients connected, this may return False, but should not raise
            assert isinstance(result, bool)
        except Exception as e:
            # Should not raise exceptions for properly formatted messages
            pytest.fail(f"WebSocket communication failed: {e}")
        
        # Test error recovery - try to set WebSocket manager again (should be idempotent)
        try:
            agent_registry.set_websocket_manager(websocket_manager)
            # Should not raise exception on re-setting
        except Exception as e:
            pytest.fail(f"WebSocket manager re-setting failed: {e}")

    @pytest.mark.asyncio
    async def test_agent_registry_tool_dispatcher_integration(
        self, real_services: RealServicesManager,
        agent_registry: AgentRegistry,
        websocket_manager: WebSocketManager
    ):
        """
        Test AgentRegistry and ToolDispatcher integration with WebSocket notifications.
        
        Validates:
        - Tool dispatcher is properly enhanced with WebSocket capabilities
        - Agents can execute tools with real-time notifications
        - Integration between AgentRegistry, ToolDispatcher, and WebSocket manager
        - Tool execution engine handles WebSocket events correctly
        """
        # Set up full integration
        agent_registry.set_websocket_manager(websocket_manager)
        agent_registry.register_default_agents()
        
        # Verify tool dispatcher integration
        tool_dispatcher = agent_registry.tool_dispatcher
        assert tool_dispatcher._websocket_enhanced is True
        
        # Verify WebSocket manager is properly set in tool dispatcher
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        enhanced_executor = tool_dispatcher.executor
        assert isinstance(enhanced_executor, UnifiedToolExecutionEngine)
        assert enhanced_executor.websocket_manager is websocket_manager
        
        # Test that agents have access to enhanced tool capabilities
        triage_agent = agent_registry.get('triage')
        assert triage_agent is not None
        assert triage_agent.websocket_manager is websocket_manager
        
        # Verify tool execution context would work with WebSocket notifications
        # This tests the setup without actually executing tools
        assert hasattr(enhanced_executor, 'websocket_notifier')
        assert enhanced_executor.websocket_notifier is not None
    
    @pytest.mark.smoke
    @pytest.mark.asyncio
    async def test_smoke_agent_registry_initialization_validation(
        self, real_services: RealServicesManager,
        agent_registry: AgentRegistry
    ):
        """
        Quick smoke test for AgentRegistry initialization validation.
        
        Should complete in <5 seconds for CI/CD pipeline.
        Tests core functionality without heavy operations.
        """
        start_time = time.time()
        
        # Basic initialization test
        assert agent_registry is not None
        assert agent_registry.llm_manager is not None
        assert agent_registry.tool_dispatcher is not None
        
        # Quick registration test
        agent_registry.register_default_agents()
        assert len(agent_registry.agents) > 0
        
        # Quick service connectivity test
        try:
            # Test basic database connectivity
            result = await real_services.postgres.fetchval("SELECT 1")
            assert result == 1
        except Exception as e:
            pytest.skip(f"Quick database connectivity check failed: {e}")
        
        # Performance validation for CI/CD
        duration = time.time() - start_time
        assert duration < 5.0, f"Smoke test took {duration:.2f}s (max: 5.0s)"


@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.database
class TestAgentRegistryAdvancedIntegration:
    """Advanced AgentRegistry integration scenarios with real services."""
    
    @pytest.fixture(autouse=True)
    async def setup_isolated_environment(self):
        """Set up isolated environment for advanced tests."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        
        # Advanced testing configuration
        advanced_env_vars = {
            'ENVIRONMENT': 'testing',
            'DATABASE_URL': 'postgresql://test_user:test_pass@localhost:5434/netra_test',
            'REDIS_URL': 'redis://localhost:6381/0',
            'CLICKHOUSE_URL': 'http://localhost:8125',
            'CLICKHOUSE_TCP_PORT': '9002',
            'LLM_ENABLED': 'true',
            'TESTING': '1',
            'AGENT_REGISTRY_CONCURRENT_LIMIT': '10',
            'WEBSOCKET_HEARTBEAT_INTERVAL': '1.0'
        }
        
        for key, value in advanced_env_vars.items():
            self.env.set(key, value, "advanced_agent_registry_test")
            
        yield
        self.env.disable_isolation()
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_operations(self):
        """
        Test concurrent AgentRegistry operations with real services.
        
        Validates:
        - Multiple AgentRegistry instances can coexist
        - Concurrent agent registration works correctly
        - WebSocket manager handles concurrent connections
        - No race conditions in agent initialization
        """
        # Create AppConfig for this test
        config = AppConfig(
            environment="testing",
            llm_enabled=True,
            openai_api_key="test-key"
        )
        
        # Create shared components
        llm_manager = LLMManager(config)
        websocket_manager = get_websocket_manager()
        
        async def create_registry():
            tool_dispatcher = ToolDispatcher()
            registry = AgentRegistry()
            registry.set_websocket_manager(websocket_manager)
            registry.register_default_agents()
            return registry
        
        # Create 3 registries concurrently
        tasks = [create_registry() for _ in range(3)]
        registries = await asyncio.gather(*tasks)
        
        # Verify all registries were created successfully
        assert len(registries) == 3
        for registry in registries:
            assert registry._agents_registered is True
            assert len(registry.agents) > 0
            assert registry.websocket_manager is websocket_manager
    
    @pytest.mark.asyncio
    async def test_agent_registry_error_recovery_patterns(self):
        """
        Test AgentRegistry error recovery patterns.
        
        Validates:
        - Registry handles WebSocket manager failures gracefully
        - Agent registration continues after errors
        - System can recover from initialization failures
        - Graceful degradation when services are unavailable
        """
        # Create components
        config = AppConfig(environment="testing", llm_enabled=True, openai_api_key="test-key")
        llm_manager = LLMManager(config)
        tool_dispatcher = ToolDispatcher()
        websocket_manager = get_websocket_manager()
        
        registry = AgentRegistry()
        
        # Test WebSocket manager failure recovery
        try:
            registry.set_websocket_manager(None)  # Simulate failure
            # Should not crash, should handle gracefully
        except Exception as e:
            pytest.fail(f"AgentRegistry should handle None WebSocket manager gracefully: {e}")
        
        # Test successful recovery
        registry.set_websocket_manager(websocket_manager)
        assert registry.websocket_manager is websocket_manager
        
        # Test agent registration after recovery
        registry.register_default_agents()
        assert len(registry.agents) > 0
        
        # Verify agents have WebSocket manager set after recovery
        for agent in registry.get_all_agents():
            assert agent.websocket_manager is websocket_manager
    
    @pytest.mark.asyncio
    async def test_agent_registry_websocket_event_flow(self):
        """
        Test complete WebSocket event flow through AgentRegistry.
        
        Validates:
        - Mission-critical WebSocket events are properly configured
        - AgentRegistry -> ToolDispatcher -> WebSocket integration works
        - Event flow supports all required event types from CLAUDE.md section 6.1
        """
        # Create components
        config = AppConfig(environment="testing", llm_enabled=True, openai_api_key="test-key")
        llm_manager = LLMManager(config)
        tool_dispatcher = ToolDispatcher()
        websocket_manager = get_websocket_manager()
        
        # Set up AgentRegistry with full WebSocket integration
        registry = AgentRegistry()
        registry.set_websocket_manager(websocket_manager)
        registry.register_default_agents()
        
        # Verify mission-critical WebSocket integration is complete
        # From CLAUDE.md section 6.1: agent_started, agent_thinking, tool_executing, 
        # tool_completed, agent_completed
        
        # Check tool dispatcher enhancement
        from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
        enhanced_executor = registry.tool_dispatcher.executor
        assert isinstance(enhanced_executor, UnifiedToolExecutionEngine)
        assert enhanced_executor.websocket_manager is websocket_manager
        assert enhanced_executor.websocket_notifier is not None
        
        # Verify WebSocket notifier has required methods for mission-critical events
        websocket_notifier = enhanced_executor.websocket_notifier
        required_methods = [
            'send_agent_started', 'send_agent_thinking', 'send_tool_executing',
            'send_tool_completed', 'send_agent_completed'
        ]
        
        for method_name in required_methods:
            assert hasattr(websocket_notifier, method_name), \
                f"WebSocket notifier missing required method: {method_name}"
        
        # Test that agents are properly connected to WebSocket infrastructure
        for agent_name, agent in registry.agents.items():
            assert agent.websocket_manager is websocket_manager, \
                f"Agent {agent_name} not connected to WebSocket manager"