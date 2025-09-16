"""
AgentWebSocketBridge Factory Methods Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (Mission Critical Infrastructure)
- Business Goal: Protect $500K+ ARR by ensuring reliable factory pattern implementations
- Value Impact: Validates factory methods preventing WebSocket emitter creation failures
- Strategic Impact: Core factory testing for Golden Path user emitter isolation

This test suite validates the factory method patterns of AgentWebSocketBridge,
ensuring proper user emitter creation, scoped emitter management, and resource
cleanup that are critical for maintaining user isolation and preventing memory leaks.

FACTORY METHODS TESTED:
- create_user_emitter(): Creates isolated WebSocket event emitters per user
- create_user_emitter_from_ids(): Convenience method for emitter creation from IDs
- create_scoped_emitter(): Context manager for automatic emitter cleanup
- create_agent_websocket_bridge(): Main bridge factory function

@compliance CLAUDE.md - SSOT patterns, factory method requirements
@compliance SPEC/websocket_agent_integration_critical.xml - Factory patterns
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch, call
from contextlib import AsyncExitStack

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture

# Bridge Components
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    create_agent_websocket_bridge
)

# User Context Components
from netra_backend.app.services.user_execution_context import UserExecutionContext

# WebSocket Dependencies
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# Shared utilities
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestAgentWebSocketBridgeFactoryMethods(SSotAsyncTestCase):
    """
    Test AgentWebSocketBridge factory methods and user emitter creation.
    
    BUSINESS CRITICAL: Factory methods ensure proper user isolation and
    prevent resource leaks in WebSocket event emission.
    """
    
    def setup_method(self, method):
        """Set up test environment with user contexts and mock dependencies."""
        super().setup_method(method)
        
        # Create test user context
        self.test_user_id = str(uuid.uuid4())
        self.test_thread_id = f"thread_{uuid.uuid4()}"
        self.test_request_id = f"req_{uuid.uuid4()}"
        self.test_run_id = f"run_{uuid.uuid4()}"
        self.test_connection_id = f"conn_{uuid.uuid4()}"
        
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            agent_context={
                "test": "factory_methods",
                "test_run_ref": self.test_run_id
            },
            audit_metadata={"test_suite": "factory_methods"}
        )
        
        # Create bridge for testing
        self.bridge = AgentWebSocketBridge(user_context=self.user_context)
        
        # Create mock WebSocket manager
        self.mock_websocket_manager = MagicMock()
        self.mock_websocket_manager.send_to_thread = AsyncMock(return_value=True)
        self.mock_websocket_manager.send_to_user = AsyncMock(return_value=True)
        self.mock_websocket_manager.is_connected = MagicMock(return_value=True)
    
    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
    
    @pytest.mark.unit
    @pytest.mark.factory_patterns
    def test_main_bridge_factory_function(self):
        """
        Test main create_agent_websocket_bridge factory function.
        
        BUSINESS VALUE: Main factory ensures consistent bridge creation
        across all components with proper initialization.
        """
        # Test factory without parameters
        bridge1 = create_agent_websocket_bridge()
        assert bridge1 is not None, "Factory should create bridge"
        assert isinstance(bridge1, AgentWebSocketBridge), "Factory should create AgentWebSocketBridge instance"
        assert bridge1.user_context is None, "Bridge should have no user context by default"
        assert bridge1.state == IntegrationState.UNINITIALIZED, "Bridge should be in UNINITIALIZED state"
        
        # Test factory with user context
        bridge2 = create_agent_websocket_bridge(user_context=self.user_context)
        assert bridge2 is not None, "Factory should create bridge with user context"
        assert bridge2.user_context is self.user_context, "Bridge should have correct user context"
        assert bridge2.user_id == self.test_user_id, "Bridge should have correct user ID"
        
        # Test factory with WebSocket manager
        bridge3 = create_agent_websocket_bridge(
            user_context=self.user_context,
            websocket_manager=self.mock_websocket_manager
        )
        assert bridge3 is not None, "Factory should create bridge with WebSocket manager"
        assert bridge3.user_context is self.user_context, "Bridge should have correct user context"
        assert bridge3.websocket_manager is self.mock_websocket_manager, "Bridge should have correct WebSocket manager"
        
        # Verify all factory-created bridges are independent
        assert bridge1 is not bridge2, "Factory bridges should be independent instances"
        assert bridge1 is not bridge3, "Factory bridges should be independent instances"
        assert bridge2 is not bridge3, "Factory bridges should be independent instances"
    
    @pytest.mark.unit
    @pytest.mark.user_emitter_creation
    async def test_create_user_emitter_with_user_context(self):
        """
        Test create_user_emitter with UserExecutionContext.
        
        SECURITY CRITICAL: User emitter creation must properly isolate
        users and prevent cross-user event delivery.
        """
        # Mock the import and factory to simulate successful emitter creation
        with patch('netra_backend.app.services.agent_websocket_bridge.get_config') as mock_get_config, \
             patch('netra_backend.app.websocket_core.unified_emitter.WebSocketEmitterFactory') as mock_factory_class:
            
            # Configure mocks
            mock_config = MagicMock()
            mock_config.use_ssot_websocket_emitter = True
            mock_get_config.return_value = mock_config
            
            mock_factory = MagicMock()
            mock_emitter = MagicMock()
            mock_factory.create_user_emitter = AsyncMock(return_value=mock_emitter)
            mock_factory_class.return_value = mock_factory
            
            # Set WebSocket manager on bridge
            self.bridge.websocket_manager = self.mock_websocket_manager
            
            # Create user emitter
            emitter = await self.bridge.create_user_emitter(user_context=self.user_context)
            
            # Verify emitter was created
            assert emitter is not None, "User emitter should be created"
            assert emitter is mock_emitter, "Should return the mocked emitter"
            
            # Verify factory was called with correct parameters
            mock_factory.create_user_emitter.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.user_emitter_creation
    async def test_create_user_emitter_with_individual_parameters(self):
        """
        Test create_user_emitter with individual user/thread/connection parameters.
        
        BUSINESS VALUE: Flexible parameter handling enables different
        calling patterns for emitter creation.
        """
        # Mock the import and factory
        with patch('netra_backend.app.services.agent_websocket_bridge.get_config') as mock_get_config, \
             patch('netra_backend.app.websocket_core.unified_emitter.WebSocketEmitterFactory') as mock_factory_class:
            
            # Configure mocks
            mock_config = MagicMock()
            mock_config.use_ssot_websocket_emitter = True
            mock_get_config.return_value = mock_config
            
            mock_factory = MagicMock()
            mock_emitter = MagicMock()
            mock_factory.create_user_emitter = AsyncMock(return_value=mock_emitter)
            mock_factory_class.return_value = mock_factory
            
            # Set WebSocket manager on bridge
            self.bridge.websocket_manager = self.mock_websocket_manager
            
            # Create user emitter with individual parameters
            emitter = await self.bridge.create_user_emitter(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                connection_id=self.test_connection_id
            )
            
            # Verify emitter was created
            assert emitter is not None, "User emitter should be created"
            assert emitter is mock_emitter, "Should return the mocked emitter"
    
    @pytest.mark.unit
    @pytest.mark.user_emitter_creation
    async def test_create_user_emitter_from_ids(self):
        """
        Test create_user_emitter_from_ids convenience method.
        
        BUSINESS VALUE: Convenience method simplifies emitter creation
        when only IDs are available.
        """
        # Mock the dependencies
        with patch('netra_backend.app.services.user_execution_context.UserExecutionContext') as mock_context_class, \
             patch('netra_backend.app.services.agent_websocket_bridge.get_config') as mock_get_config, \
             patch('netra_backend.app.websocket_core.unified_emitter.WebSocketEmitterFactory') as mock_factory_class:
            
            # Configure mocks
            mock_config = MagicMock()
            mock_config.use_ssot_websocket_emitter = True
            mock_get_config.return_value = mock_config
            
            mock_user_context = MagicMock()
            mock_user_context.user_id = self.test_user_id
            mock_context_class.return_value = mock_user_context
            
            mock_factory = MagicMock()
            mock_emitter = MagicMock()
            mock_factory.create_user_emitter = AsyncMock(return_value=mock_emitter)
            mock_factory_class.return_value = mock_factory
            
            # Create user emitter from IDs
            emitter = await AgentWebSocketBridge.create_user_emitter_from_ids(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id,
                websocket_client_id=self.test_connection_id
            )
            
            # Verify emitter was created
            assert emitter is not None, "User emitter should be created from IDs"
            assert emitter is mock_emitter, "Should return the mocked emitter"
            
            # Verify UserExecutionContext was created with correct parameters
            mock_context_class.assert_called_once_with(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                request_id=self.test_run_id,
                websocket_client_id=self.test_connection_id
            )
    
    @pytest.mark.unit
    @pytest.mark.scoped_emitter
    async def test_create_scoped_emitter_context_manager(self):
        """
        Test create_scoped_emitter context manager for automatic cleanup.
        
        BUSINESS VALUE: Automatic cleanup prevents resource leaks and
        ensures proper WebSocket emitter lifecycle management.
        """
        # Mock the dependencies
        with patch('netra_backend.app.services.agent_websocket_bridge.get_config') as mock_get_config, \
             patch('netra_backend.app.websocket_core.unified_emitter.WebSocketEmitterFactory') as mock_factory_class:
            
            # Configure mocks
            mock_config = MagicMock()
            mock_config.use_ssot_websocket_emitter = True
            mock_get_config.return_value = mock_config
            
            mock_factory = MagicMock()
            mock_emitter = MagicMock()
            mock_emitter.cleanup = AsyncMock()  # Mock cleanup method
            mock_factory.create_user_emitter = AsyncMock(return_value=mock_emitter)
            mock_factory_class.return_value = mock_factory
            
            # Test scoped emitter context manager
            async with AgentWebSocketBridge.create_scoped_emitter(self.user_context) as scoped_emitter:
                # Verify emitter is available within context
                assert scoped_emitter is not None, "Scoped emitter should be available"
                
                # Verify it's the mocked emitter
                assert scoped_emitter is mock_emitter, "Should return the mocked emitter"
            
            # After exiting context, cleanup should have been called
            if hasattr(mock_emitter, 'cleanup') and callable(mock_emitter.cleanup):
                mock_emitter.cleanup.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.error_handling
    async def test_create_user_emitter_with_invalid_parameters(self):
        """
        Test create_user_emitter error handling with invalid parameters.
        
        BUSINESS VALUE: Proper error handling prevents system crashes
        and provides clear feedback for debugging.
        """
        # Test with no WebSocket manager
        self.bridge.websocket_manager = None
        
        with pytest.raises(ValueError, match="WebSocket manager.*not available"):
            await self.bridge.create_user_emitter(user_context=self.user_context)
        
        # Test with empty user ID
        with pytest.raises(ValueError):
            await self.bridge.create_user_emitter(
                user_id="",
                thread_id=self.test_thread_id
            )
        
        # Test with None user context and no individual parameters
        with pytest.raises(ValueError):
            await self.bridge.create_user_emitter()
    
    @pytest.mark.unit
    @pytest.mark.error_handling
    async def test_create_user_emitter_from_ids_with_invalid_ids(self):
        """
        Test create_user_emitter_from_ids with invalid ID parameters.
        
        BUSINESS VALUE: Input validation prevents creation of invalid
        emitters that could cause WebSocket delivery failures.
        """
        # Test with empty user_id
        with pytest.raises(ValueError):
            await AgentWebSocketBridge.create_user_emitter_from_ids(
                user_id="",
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
        
        # Test with None thread_id
        with pytest.raises(ValueError):
            await AgentWebSocketBridge.create_user_emitter_from_ids(
                user_id=self.test_user_id,
                thread_id=None,
                run_id=self.test_run_id
            )
        
        # Test with empty run_id
        with pytest.raises(ValueError):
            await AgentWebSocketBridge.create_user_emitter_from_ids(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=""
            )
    
    @pytest.mark.unit
    @pytest.mark.concurrent_factory_usage
    async def test_concurrent_user_emitter_creation(self):
        """
        Test concurrent user emitter creation to validate thread safety.
        
        BUSINESS CRITICAL: Concurrent emitter creation must be thread-safe
        to prevent race conditions in multi-user scenarios.
        """
        # Mock the dependencies
        with patch('netra_backend.app.services.agent_websocket_bridge.get_config') as mock_get_config, \
             patch('netra_backend.app.websocket_core.unified_emitter.WebSocketEmitterFactory') as mock_factory_class:
            
            # Configure mocks
            mock_config = MagicMock()
            mock_config.use_ssot_websocket_emitter = True
            mock_get_config.return_value = mock_config
            
            mock_factory = MagicMock()
            # Create different mock emitters for each call
            mock_emitters = [MagicMock() for _ in range(5)]
            mock_factory.create_user_emitter = AsyncMock(side_effect=mock_emitters)
            mock_factory_class.return_value = mock_factory
            
            # Set WebSocket manager on bridge
            self.bridge.websocket_manager = self.mock_websocket_manager
            
            # Create multiple user contexts for concurrent testing
            user_contexts = []
            for i in range(5):
                context = UserExecutionContext(
                    user_id=f"user_{i}_{uuid.uuid4()}",
                    thread_id=f"thread_{i}_{uuid.uuid4()}",
                    run_id=f"run_{i}_{uuid.uuid4()}",
                    request_id=f"req_{i}_{uuid.uuid4()}",
                    agent_context={"concurrent_test": i},
                    audit_metadata={"test": "concurrent_factory"}
                )
                user_contexts.append(context)
            
            # Create emitters concurrently
            async def create_emitter_async(user_context):
                """Create emitter with small delay to increase concurrency."""
                await asyncio.sleep(0.001)  # Small delay to increase race condition chances
                return await self.bridge.create_user_emitter(user_context=user_context)
            
            # Create emitters concurrently
            emitters = await asyncio.gather(
                *[create_emitter_async(ctx) for ctx in user_contexts]
            )
            
            # Verify all emitters were created successfully
            assert len(emitters) == 5, "All emitters should be created"
            for i, emitter in enumerate(emitters):
                assert emitter is not None, f"Emitter {i} should not be None"
                assert emitter is mock_emitters[i], f"Emitter {i} should be correct mock instance"
            
            # Verify all emitters are independent
            for i in range(len(emitters)):
                for j in range(i + 1, len(emitters)):
                    assert emitters[i] is not emitters[j], f"Emitter {i} and {j} should be different instances"
    
    @pytest.mark.unit
    @pytest.mark.resource_management
    async def test_scoped_emitter_cleanup_on_exception(self):
        """
        Test that scoped emitter cleanup occurs even when exceptions happen.
        
        BUSINESS VALUE: Proper cleanup on exceptions prevents resource
        leaks and ensures system stability during error conditions.
        """
        # Mock the dependencies
        with patch('netra_backend.app.services.agent_websocket_bridge.get_config') as mock_get_config, \
             patch('netra_backend.app.websocket_core.unified_emitter.WebSocketEmitterFactory') as mock_factory_class:
            
            # Configure mocks
            mock_config = MagicMock()
            mock_config.use_ssot_websocket_emitter = True
            mock_get_config.return_value = mock_config
            
            mock_factory = MagicMock()
            mock_emitter = MagicMock()
            mock_emitter.cleanup = AsyncMock()
            mock_factory.create_user_emitter = AsyncMock(return_value=mock_emitter)
            mock_factory_class.return_value = mock_factory
            
            # Test that cleanup occurs even when exception is raised
            with pytest.raises(ValueError, match="Test exception"):
                async with AgentWebSocketBridge.create_scoped_emitter(self.user_context) as scoped_emitter:
                    # Verify emitter is available
                    assert scoped_emitter is not None, "Scoped emitter should be available"
                    
                    # Raise exception to test cleanup
                    raise ValueError("Test exception")
            
            # Verify cleanup was called despite exception
            if hasattr(mock_emitter, 'cleanup') and callable(mock_emitter.cleanup):
                mock_emitter.cleanup.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.factory_isolation
    def test_factory_bridge_independence(self):
        """
        Test that factory-created bridges are independent and properly isolated.
        
        SECURITY CRITICAL: Bridge independence prevents shared state
        that could lead to cross-user contamination.
        """
        # Create multiple bridges using factory
        bridges = []
        user_contexts = []
        
        for i in range(3):
            user_context = UserExecutionContext(
                user_id=f"factory_user_{i}_{uuid.uuid4()}",
                thread_id=f"factory_thread_{i}_{uuid.uuid4()}",
                run_id=f"factory_run_{i}_{uuid.uuid4()}",
                request_id=f"factory_req_{i}_{uuid.uuid4()}",
                agent_context={"factory_index": i},
                audit_metadata={"test": "factory_isolation"}
            )
            user_contexts.append(user_context)
            
            bridge = create_agent_websocket_bridge(user_context=user_context)
            bridges.append(bridge)
        
        # Verify all bridges are independent instances
        for i in range(len(bridges)):
            for j in range(i + 1, len(bridges)):
                assert bridges[i] is not bridges[j], f"Factory bridge {i} and {j} should be different instances"
        
        # Verify each bridge has correct user context
        for i, bridge in enumerate(bridges):
            assert bridge.user_context is user_contexts[i], f"Factory bridge {i} should have correct user context"
            assert bridge.user_id == user_contexts[i].user_id, f"Factory bridge {i} should have correct user ID"
        
        # Verify internal state is independent
        for i, bridge in enumerate(bridges):
            # Modify one bridge's state
            bridge.is_connected = False
            
            # Verify other bridges are unaffected
            for j in range(len(bridges)):
                if i != j:
                    assert bridges[j].is_connected is True, f"Bridge {j} should remain unaffected by bridge {i} changes"
            
            # Reset state for next iteration
            bridge.is_connected = True
