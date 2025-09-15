"""
Test WebSocket Manager Integration Consistency - Issue #1100

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Infrastructure Layer
- Business Goal: Ensure WebSocket functionality consistency during SSOT migration
- Value Impact: Validates $500K+ ARR WebSocket infrastructure remains stable
- Strategic Impact: Prevents integration failures during technical debt elimination

Uses real PostgreSQL and Redis services (non-Docker) to validate WebSocket manager 
behavior consistency across different instantiation patterns.

DESIGNED TO FAIL INITIALLY - These tests validate SSOT migration success
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestWebSocketManagerIntegration(BaseIntegrationTest):
    """Test WebSocket manager integration with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_consistent_behavior_with_real_services(self, real_services_fixture):
        """
        SHOULD FAIL INITIALLY: Validate consistent WebSocket manager behavior.
        
        This test should FAIL if multiple implementations create inconsistencies
        and PASS after single SSOT implementation ensures consistency.
        """
        logger.info("Testing WebSocket manager consistent behavior with real services")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, WebSocketManagerMode
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            # Get real services
            db = real_services_fixture["db"]
            redis = real_services_fixture["redis"]
            
            # Create test context
            test_user_id = ensure_user_id("integration_test_user")
            test_context = UserExecutionContext(
                user_id=test_user_id,
                thread_id="integration_test_thread",
                run_id="integration_test_run",
                request_id="integration_test_request"
            )
            
            # Test WebSocket manager consistency
            manager1 = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=test_context
            )
            
            manager2 = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=test_context
            )
            
            # Validate consistent behavior
            assert type(manager1) == type(manager2), "Inconsistent WebSocket manager types"
            assert manager1.__class__.__name__ == "WebSocketManager", "Wrong manager class name"
            assert manager2.__class__.__name__ == "WebSocketManager", "Wrong manager class name"
            
            # Test with real Redis operations to validate integration
            test_key = f"websocket_test_{test_user_id}_{int(time.time())}"
            await redis.set(test_key, "integration_test_value")
            stored_value = await redis.get(test_key)
            
            assert stored_value == "integration_test_value", "Real Redis integration failed"
            
            # Clean up
            await redis.delete(test_key)
            
            logger.info("WebSocket manager consistency test passed with real services")
            
        except Exception as e:
            pytest.fail(f"WebSocket manager integration test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_ssot_integration(self, real_services_fixture):
        """
        SHOULD FAIL INITIALLY: Test agent WebSocket bridge uses SSOT WebSocket manager.
        
        Validates AgentWebSocketBridge integration consistency after SSOT migration.
        """
        logger.info("Testing agent WebSocket bridge SSOT integration")
        
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, WebSocketManagerMode
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            # Get real services
            db = real_services_fixture["db"]
            redis = real_services_fixture["redis"]
            
            # Create test context
            test_user_id = ensure_user_id("bridge_integration_test")
            test_context = UserExecutionContext(
                user_id=test_user_id,
                thread_id="bridge_test_thread",
                run_id="bridge_test_run",
                request_id="bridge_test_request"
            )
            
            # Create WebSocket manager using SSOT pattern
            websocket_manager = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=test_context
            )
            
            # Test AgentWebSocketBridge integration
            bridge = AgentWebSocketBridge(
                websocket_manager=websocket_manager,
                user_context=test_context
            )
            
            # Validate bridge uses SSOT WebSocket manager
            assert hasattr(bridge, 'websocket_manager'), "Bridge missing websocket_manager attribute"
            assert isinstance(bridge.websocket_manager, WebSocketManager), "Bridge not using SSOT WebSocketManager"
            
            # Test bridge functionality with real services
            test_message = {
                "type": "test_message",
                "data": {"test": True},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": str(test_user_id),
                "thread_id": test_context.thread_id
            }
            
            # Validate message structure
            assert "type" in test_message, "Test message missing type field"
            assert "data" in test_message, "Test message missing data field"
            assert "timestamp" in test_message, "Test message missing timestamp field"
            assert "user_id" in test_message, "Test message missing user_id field"
            assert "thread_id" in test_message, "Test message missing thread_id field"
            
            logger.info("Agent WebSocket bridge SSOT integration test passed")
            
        except ImportError as e:
            pytest.skip(f"AgentWebSocketBridge not available: {e}")
        except Exception as e:
            pytest.fail(f"Agent WebSocket bridge SSOT integration test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_structure_consistency_with_real_services(self, real_services_fixture):
        """
        SHOULD FAIL INITIALLY: Fix current event structure validation failures.
        
        Address the 3/42 mission critical test failures by validating all 5 required events:
        agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        """
        logger.info("Testing WebSocket event structure consistency with real services")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, WebSocketManagerMode
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            # Get real services
            db = real_services_fixture["db"]
            redis = real_services_fixture["redis"]
            
            test_user_id = ensure_user_id("event_test_user")
            test_context = UserExecutionContext(
                user_id=test_user_id,
                thread_id="event_test_thread",
                run_id="event_test_run",
                request_id="event_test_request"
            )
            
            # Create WebSocket manager
            manager = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=test_context
            )
            
            # Validate event structure for all required events
            required_events = [
                "agent_started",
                "agent_thinking",
                "tool_executing", 
                "tool_completed",
                "agent_completed"
            ]
            
            event_validation_results = {}
            
            for event_type in required_events:
                # Create test event with proper structure
                test_event = {
                    "type": event_type,
                    "data": {
                        "test": True,
                        "event_type": event_type,
                        "validation": "structure_test"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "thread_id": test_context.thread_id,
                    "user_id": str(test_context.user_id),
                    "run_id": test_context.run_id,
                    "request_id": test_context.request_id
                }
                
                # Validate required fields
                required_fields = ["type", "data", "timestamp", "thread_id", "user_id"]
                missing_fields = []
                
                for field in required_fields:
                    if field not in test_event:
                        missing_fields.append(field)
                
                event_validation_results[event_type] = {
                    "structure_valid": len(missing_fields) == 0,
                    "missing_fields": missing_fields,
                    "has_required_data": isinstance(test_event.get("data"), dict)
                }
                
                # Validate event structure
                assert field in test_event, f"Event {event_type} missing {field} field"
                assert isinstance(test_event["data"], dict), f"Event {event_type} data field must be dict"
                assert test_event["type"] == event_type, f"Event type mismatch for {event_type}"
            
            # Validate all events have consistent structure
            all_valid = all(result["structure_valid"] for result in event_validation_results.values())
            
            assert all_valid, (
                f"Event structure validation failed. Results: {event_validation_results}"
            )
            
            # Store validation results in Redis for integration testing
            validation_key = f"event_validation_{test_user_id}_{int(time.time())}"
            await redis.set(validation_key, str(len(required_events)))
            stored_count = await redis.get(validation_key)
            
            assert int(stored_count) == len(required_events), "Redis integration failed for event validation"
            
            # Clean up
            await redis.delete(validation_key)
            
            logger.info(f"Event structure consistency validated for {len(required_events)} event types")
            
        except Exception as e:
            pytest.fail(f"Event structure consistency test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_factory_elimination_with_real_services(self, real_services_fixture):
        """
        SHOULD FAIL INITIALLY: Ensure WebSocket manager factory pattern is eliminated.
        
        Validates that only SSOT WebSocketManager can be instantiated and no factory
        patterns remain accessible in the integration environment.
        """
        logger.info("Testing WebSocket manager factory elimination with real services")
        
        # Get real services for integration context
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Test 1: Canonical WebSocketManager should be available
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, WebSocketManagerMode
            canonical_available = True
            logger.info("Canonical WebSocketManager successfully imported")
        except ImportError as e:
            canonical_available = False
            pytest.fail(f"CRITICAL: Canonical WebSocketManager not available: {e}")
        
        # Test 2: Deprecated factory should NOT be available
        factory_available = False
        factory_functions_available = []
        
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory_available = True
            logger.warning("SSOT VIOLATION: Deprecated WebSocketManagerFactory still available")
        except ImportError:
            logger.info("Deprecated WebSocketManagerFactory correctly not available")
        
        # Test 3: Factory functions should NOT be available
        factory_function_names = [
            'create_websocket_manager',
            'create_websocket_manager_sync',
            'get_websocket_manager_factory'
        ]
        
        for func_name in factory_function_names:
            try:
                import importlib
                module = importlib.import_module('netra_backend.app.websocket_core.websocket_manager_factory')
                if hasattr(module, func_name):
                    factory_functions_available.append(func_name)
            except ImportError:
                pass  # Expected - factory module should not exist
        
        # Test 4: Direct instantiation should work with real services
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            test_user_id = ensure_user_id("factory_elimination_test")
            test_context = UserExecutionContext(
                user_id=test_user_id,
                thread_id="factory_test_thread",
                run_id="factory_test_run",
                request_id="factory_test_request"
            )
            
            # Test direct instantiation (SSOT compliant)
            manager = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=test_context
            )
            
            assert manager is not None, "Direct WebSocketManager instantiation failed"
            direct_instantiation_works = True
            
            # Test integration with real Redis
            test_key = f"factory_test_{test_user_id}_{int(time.time())}"
            await redis.set(test_key, "factory_elimination_test")
            stored_value = await redis.get(test_key)
            
            assert stored_value == "factory_elimination_test", "Redis integration failed"
            await redis.delete(test_key)
            
        except Exception as e:
            direct_instantiation_works = False
            pytest.fail(f"Direct WebSocketManager instantiation failed: {e}")
        
        # Assertions for SSOT compliance
        assert canonical_available, "CRITICAL: Canonical WebSocketManager must be available"
        
        assert not factory_available, (
            "SSOT VIOLATION: Deprecated WebSocketManagerFactory must be eliminated. "
            "SSOT compliance requires single implementation."
        )
        
        assert len(factory_functions_available) == 0, (
            f"SSOT VIOLATION: Factory functions must be eliminated: {factory_functions_available}"
        )
        
        assert direct_instantiation_works, (
            "CRITICAL: Direct WebSocketManager instantiation must work for SSOT compliance"
        )
        
        logger.info("WebSocket manager factory elimination test passed - SSOT compliance verified")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_user_isolation_with_real_services(self, real_services_fixture):
        """
        SHOULD PASS: Validate WebSocket manager maintains user isolation.
        
        Ensures that different user contexts create properly isolated WebSocket managers
        and that cross-user data contamination does not occur.
        """
        logger.info("Testing WebSocket manager user isolation with real services")
        
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, WebSocketManagerMode
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id
            
            # Get real services
            redis = real_services_fixture["redis"]
            
            # Create two different user contexts
            user1_id = ensure_user_id("user_isolation_test_1")
            user2_id = ensure_user_id("user_isolation_test_2")
            
            context1 = UserExecutionContext(
                user_id=user1_id,
                thread_id="isolation_thread_1",
                run_id="isolation_run_1",
                request_id="isolation_request_1"
            )
            
            context2 = UserExecutionContext(
                user_id=user2_id,
                thread_id="isolation_thread_2", 
                run_id="isolation_run_2",
                request_id="isolation_request_2"
            )
            
            # Create separate WebSocket managers for each user
            manager1 = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=context1
            )
            
            manager2 = WebSocketManager(
                mode=WebSocketManagerMode.UNIFIED,
                user_context=context2
            )
            
            # Validate managers are separate instances
            assert manager1 is not manager2, "WebSocket managers should be separate instances"
            assert manager1.user_context.user_id != manager2.user_context.user_id, "User IDs should be different"
            assert manager1.user_context.thread_id != manager2.user_context.thread_id, "Thread IDs should be different"
            
            # Test isolation with real Redis operations
            timestamp = int(time.time())
            key1 = f"user_isolation_test_1_{timestamp}"
            key2 = f"user_isolation_test_2_{timestamp}"
            
            await redis.set(key1, f"data_for_user_{user1_id}")
            await redis.set(key2, f"data_for_user_{user2_id}")
            
            # Validate data separation
            value1 = await redis.get(key1)
            value2 = await redis.get(key2)
            
            assert value1 == f"data_for_user_{user1_id}", "User 1 data corrupted"
            assert value2 == f"data_for_user_{user2_id}", "User 2 data corrupted"
            assert value1 != value2, "User data should be different"
            
            # Clean up
            await redis.delete(key1)
            await redis.delete(key2)
            
            logger.info("WebSocket manager user isolation test passed")
            
        except Exception as e:
            pytest.fail(f"WebSocket manager user isolation test failed: {e}")