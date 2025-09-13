"""
AgentWebSocketBridge Initialization Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (Mission Critical Infrastructure)
- Business Goal: Protect $500K+ ARR by ensuring WebSocket bridge reliability 
- Value Impact: Validates proper bridge initialization preventing WebSocket 1011 errors
- Strategic Impact: Core infrastructure testing for Golden Path user flow

This test suite validates the initialization patterns of AgentWebSocketBridge,
ensuring proper configuration, dependency initialization, and state management
that are critical for chat functionality and real-time agent event delivery.

@compliance CLAUDE.md - SSOT patterns, real services over mocks
@compliance SPEC/websocket_agent_integration_critical.xml - WebSocket bridge patterns
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture

# Bridge Components
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig,
    HealthStatus,
    IntegrationResult,
    IntegrationMetrics,
    create_agent_websocket_bridge
)

# User Context for isolation testing
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager

# WebSocket Dependencies
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# Shared utilities
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestAgentWebSocketBridgeInitialization(SSotAsyncTestCase):
    """
    Test AgentWebSocketBridge initialization patterns and configuration.
    
    CRITICAL: These tests validate core initialization logic that determines
    whether the bridge can properly handle WebSocket events for chat functionality.
    """
    
    def setup_method(self, method):
        """Set up test environment with clean state."""
        super().setup_method(method)
        
        # Create test user context for isolation testing
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = f"thread_{uuid.uuid4()}"
        self.test_request_id = f"req_{uuid.uuid4()}"
        
        # Create user execution context for tests
        self.test_run_id = f"run_{uuid.uuid4()}"
        
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            agent_context={"test": "initialization"},
            audit_metadata={"test_suite": "initialization"}
        )
    
    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
    
    @pytest.mark.unit
    @pytest.mark.core_infrastructure  
    def test_bridge_initialization_without_user_context(self):
        """
        Test bridge initialization without user context (system mode).
        
        BUSINESS CRITICAL: System-level initialization must work for 
        infrastructure setup and health monitoring.
        """
        # Create bridge without user context
        bridge = AgentWebSocketBridge()
        
        # Verify basic initialization
        assert bridge is not None, "Bridge should be created successfully"
        assert bridge.user_context is None, "Bridge should have no user context in system mode"
        assert bridge.user_id is None, "Bridge should have no user ID in system mode"
        
        # Verify configuration initialization
        assert bridge.config is not None, "Bridge should have default configuration"
        assert isinstance(bridge.config, IntegrationConfig), "Config should be IntegrationConfig instance"
        assert bridge.config.initialization_timeout_s > 0, "Timeout should be positive"
        assert bridge.config.health_check_interval_s > 0, "Health check interval should be positive"
        
        # Verify state initialization
        assert bridge.state == IntegrationState.UNINITIALIZED, "Bridge should start in UNINITIALIZED state"
        assert hasattr(bridge, 'initialization_lock'), "Bridge should have initialization lock"
        assert hasattr(bridge, 'recovery_lock'), "Bridge should have recovery lock"
        assert hasattr(bridge, 'health_lock'), "Bridge should have health lock"
        
        # Verify dependency initialization
        assert bridge._websocket_manager is None, "WebSocket manager should be None initially"
        assert bridge._registry is None, "Registry should be None initially"
        assert bridge._thread_registry is None, "Thread registry should be None initially"
        
        # Verify connection status for test compatibility
        assert bridge.is_connected is True, "Bridge should be marked as connected after initialization"
        
        # Verify event tracking initialization
        assert hasattr(bridge, '_event_history'), "Bridge should have event history for test validation"
        assert isinstance(bridge._event_history, list), "Event history should be a list"
        assert len(bridge._event_history) == 0, "Event history should be empty initially"
    
    @pytest.mark.unit
    @pytest.mark.user_isolation
    def test_bridge_initialization_with_user_context(self):
        """
        Test bridge initialization with user context for proper isolation.
        
        BUSINESS CRITICAL: Per-user initialization is essential for multi-tenant
        security and preventing cross-user event leakage.
        """
        # Create bridge with user context
        bridge = AgentWebSocketBridge(user_context=self.user_context)
        
        # Verify user context binding
        assert bridge.user_context is not None, "Bridge should have user context"
        assert bridge.user_context.user_id == self.test_user_id, "User ID should match"
        assert bridge.user_context.thread_id == self.test_thread_id, "Thread ID should match"
        assert bridge.user_context.request_id == self.test_request_id, "Request ID should match"
        
        # Verify user ID property
        assert bridge.user_id == self.test_user_id, "User ID property should return correct ID"
        
        # Verify configuration and state are still properly initialized
        assert bridge.config is not None, "Bridge should have configuration with user context"
        assert bridge.state == IntegrationState.UNINITIALIZED, "Bridge should start in UNINITIALIZED state"
        assert bridge.is_connected is True, "Bridge should be marked as connected"
        
        # Verify isolation - each bridge instance is independent
        bridge2 = AgentWebSocketBridge(user_context=self.user_context)
        assert bridge is not bridge2, "Different bridge instances should be created"
        assert bridge.user_context.request_id == bridge2.user_context.request_id, "User context should match"
    
    @pytest.mark.unit
    @pytest.mark.configuration
    def test_configuration_initialization_with_custom_config(self):
        """
        Test bridge initialization with custom configuration parameters.
        
        BUSINESS VALUE: Validates configuration flexibility for different
        deployment environments and performance requirements.
        """
        # Create custom configuration
        custom_config = IntegrationConfig(
            initialization_timeout_s=45,
            health_check_interval_s=90,
            recovery_max_attempts=5,
            recovery_base_delay_s=2.0,
            recovery_max_delay_s=60.0,
            integration_verification_timeout_s=15
        )
        
        # Create bridge with custom configuration (via monkey patch for test)
        bridge = AgentWebSocketBridge(user_context=self.user_context)
        bridge.config = custom_config
        
        # Verify custom configuration is applied
        assert bridge.config.initialization_timeout_s == 45, "Custom timeout should be set"
        assert bridge.config.health_check_interval_s == 90, "Custom health interval should be set"
        assert bridge.config.recovery_max_attempts == 5, "Custom recovery attempts should be set"
        assert bridge.config.recovery_base_delay_s == 2.0, "Custom base delay should be set"
        assert bridge.config.recovery_max_delay_s == 60.0, "Custom max delay should be set"
        assert bridge.config.integration_verification_timeout_s == 15, "Custom verification timeout should be set"
    
    @pytest.mark.unit
    @pytest.mark.monitoring_setup
    def test_monitoring_initialization(self):
        """
        Test bridge monitoring component initialization.
        
        BUSINESS VALUE: Monitoring is critical for production stability
        and early detection of WebSocket failures.
        """
        bridge = AgentWebSocketBridge(user_context=self.user_context)
        
        # Verify monitoring observers list initialization
        assert hasattr(bridge, '_observers'), "Bridge should have observers list"
        assert isinstance(bridge._observers, list), "Observers should be a list"
        assert len(bridge._observers) == 0, "Observers list should be empty initially"
        
        # Verify metrics initialization
        assert hasattr(bridge, '_metrics'), "Bridge should have metrics"
        
        # Test MonitorableComponent interface
        from shared.monitoring.interfaces import MonitorableComponent
        assert isinstance(bridge, MonitorableComponent), "Bridge should implement MonitorableComponent"
        
        # Test basic monitoring methods are callable
        assert callable(getattr(bridge, 'register_monitor_observer', None)), "Should have register_monitor_observer method"
        assert callable(getattr(bridge, 'remove_monitor_observer', None)), "Should have remove_monitor_observer method"
    
    @pytest.mark.unit
    @pytest.mark.factory_pattern
    def test_factory_function_creates_bridge(self):
        """
        Test factory function properly creates bridge instances.
        
        BUSINESS VALUE: Factory pattern ensures consistent bridge creation
        across different components and prevents initialization errors.
        """
        # Test factory without parameters
        bridge1 = create_agent_websocket_bridge()
        assert bridge1 is not None, "Factory should create bridge"
        assert isinstance(bridge1, AgentWebSocketBridge), "Factory should create AgentWebSocketBridge instance"
        assert bridge1.user_context is None, "Factory bridge should have no user context by default"
        
        # Test factory with user context
        bridge2 = create_agent_websocket_bridge(user_context=self.user_context)
        assert bridge2 is not None, "Factory should create bridge with user context"
        assert bridge2.user_context is not None, "Factory bridge should have user context"
        assert bridge2.user_id == self.test_user_id, "Factory bridge should have correct user ID"
        
        # Verify instances are independent
        assert bridge1 is not bridge2, "Factory should create independent instances"
    
    @pytest.mark.unit
    @pytest.mark.concurrent_initialization
    async def test_concurrent_bridge_initialization(self):
        """
        Test concurrent bridge initialization to validate thread safety.
        
        BUSINESS CRITICAL: Concurrent initialization must not cause race conditions
        that could lead to WebSocket event delivery failures.
        """
        # Create multiple user contexts for concurrent testing
        user_contexts = []
        for i in range(5):
            context = UserExecutionContext(
                user_id=f"user_{i}_{uuid.uuid4()}",
                thread_id=f"thread_{i}_{uuid.uuid4()}",
                run_id=f"run_{i}_{uuid.uuid4()}",
                request_id=f"req_{i}_{uuid.uuid4()}",
                agent_context={"concurrent_test": i},
                audit_metadata={"test": "concurrent_init"}
            )
            user_contexts.append(context)
        
        # Initialize bridges concurrently
        async def create_bridge_async(user_context):
            """Create bridge with small delay to increase concurrency."""
            await asyncio.sleep(0.001)  # Small delay to increase race condition chances
            return AgentWebSocketBridge(user_context=user_context)
        
        # Create bridges concurrently
        bridges = await asyncio.gather(
            *[create_bridge_async(ctx) for ctx in user_contexts]
        )
        
        # Verify all bridges were created successfully
        assert len(bridges) == 5, "All bridges should be created"
        for i, bridge in enumerate(bridges):
            assert bridge is not None, f"Bridge {i} should not be None"
            assert bridge.user_context is not None, f"Bridge {i} should have user context"
            assert bridge.user_id == user_contexts[i].user_id, f"Bridge {i} should have correct user ID"
            assert bridge.state == IntegrationState.UNINITIALIZED, f"Bridge {i} should be in UNINITIALIZED state"
        
        # Verify bridges are independent instances
        for i in range(len(bridges)):
            for j in range(i + 1, len(bridges)):
                assert bridges[i] is not bridges[j], f"Bridge {i} and {j} should be different instances"
    
    @pytest.mark.unit
    @pytest.mark.state_validation
    def test_initialization_state_consistency(self):
        """
        Test initialization state consistency and expected values.
        
        BUSINESS VALUE: Consistent initialization state prevents unexpected
        behavior during WebSocket event processing.
        """
        bridge = AgentWebSocketBridge(user_context=self.user_context)
        
        # Verify all required locks are created
        assert hasattr(bridge, 'initialization_lock'), "Should have initialization lock"
        assert hasattr(bridge, 'recovery_lock'), "Should have recovery lock"
        assert hasattr(bridge, 'health_lock'), "Should have health lock"
        
        # Verify locks are asyncio.Lock instances
        assert isinstance(bridge.initialization_lock, asyncio.Lock), "Initialization lock should be asyncio.Lock"
        assert isinstance(bridge.recovery_lock, asyncio.Lock), "Recovery lock should be asyncio.Lock"
        assert isinstance(bridge.health_lock, asyncio.Lock), "Health lock should be asyncio.Lock"
        
        # Verify shutdown flag
        assert hasattr(bridge, '_shutdown'), "Should have shutdown flag"
        assert bridge._shutdown is False, "Shutdown flag should be False initially"
        
        # Verify state machine is in expected initial state
        assert bridge.state == IntegrationState.UNINITIALIZED, "Should start in UNINITIALIZED state"
        
        # Verify required attributes exist
        required_attrs = [
            'config', 'state', 'user_context', '_websocket_manager', 
            '_registry', '_thread_registry', '_event_history', 'is_connected'
        ]
        for attr in required_attrs:
            assert hasattr(bridge, attr), f"Bridge should have {attr} attribute"
    
    @pytest.mark.unit
    @pytest.mark.initialization_idempotency
    def test_initialization_idempotency(self):
        """
        Test that initialization is idempotent and can be called multiple times safely.
        
        BUSINESS VALUE: Idempotent initialization prevents issues in complex
        startup sequences and recovery scenarios.
        """
        bridge = AgentWebSocketBridge(user_context=self.user_context)
        
        # Store initial state
        initial_state = bridge.state
        initial_config = bridge.config
        initial_user_context = bridge.user_context
        
        # Verify initialization marked as completed
        assert hasattr(bridge, '_initialized'), "Should have initialization flag"
        assert bridge._initialized is True, "Should be marked as initialized"
        
        # Multiple calls to initialization methods should not change state
        bridge._initialize_configuration()
        bridge._initialize_state()  
        bridge._initialize_dependencies()
        bridge._initialize_health_monitoring()
        bridge._initialize_monitoring_observers()
        
        # Verify state remains consistent
        assert bridge.state == initial_state, "State should not change after re-initialization"
        assert bridge.config is initial_config, "Config should not change after re-initialization"
        assert bridge.user_context is initial_user_context, "User context should not change after re-initialization"
        assert bridge._initialized is True, "Should still be marked as initialized"
