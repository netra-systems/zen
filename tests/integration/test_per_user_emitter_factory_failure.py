"""
Test Per-User Emitter Factory Failure

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure user isolation in multi-user system
- Value Impact: Per-user WebSocket emitters prevent cross-user data leaks
- Strategic Impact: Security and privacy foundation for enterprise customers

CRITICAL: This test reproduces the per-user factory pattern failure identified
in the Five Whys Root Cause Analysis. The create_user_emitter() factory pattern
is broken, leading to shared state and security vulnerabilities.

Based on Five Whys Analysis:
- Root Cause: Per-user factory pattern not creating isolated WebSocket emitters  
- Impact: Cross-user event contamination and security violations
- Evidence: create_user_emitter() factory method has multiple failure points

This test SHOULD FAIL initially because the factory pattern migration is incomplete.
"""

import pytest
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


class TestPerUserEmitterFactoryFailure(BaseIntegrationTest):
    """
    Test the per-user WebSocket emitter factory pattern failures.
    
    CRITICAL: This test reproduces the factory pattern issues that prevent
    proper user isolation in WebSocket event delivery.
    """

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_create_user_emitter_factory_pattern_failure(self, real_services_fixture):
        """
        Test create_user_emitter() factory pattern failure.
        
        EXPECTED: This test SHOULD FAIL because the factory pattern is not
        properly creating isolated user-specific WebSocket emitters.
        
        Five Whys Root Cause:
        - WebSocket emitter creation depends on factory initialization 
        - Factory configuration requirements can cause emitter creation to fail
        - Multiple failure points in complex creation process
        """
        # Setup multiple authenticated users for isolation testing
        auth_helper = E2EAuthHelper(environment="test")
        
        user1_context = await create_authenticated_user_context(
            user_email="factory_user1@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        user2_context = await create_authenticated_user_context(
            user_email="factory_user2@example.com", 
            environment="test",
            websocket_enabled=True
        )
        
        user3_context = await create_authenticated_user_context(
            user_email="factory_user3@example.com",
            environment="test", 
            websocket_enabled=True
        )
        
        logger.info(f"Testing factory pattern with users: {user1_context.user_id}, {user2_context.user_id}, {user3_context.user_id}")
        
        factory_failures = []
        created_emitters = {}
        
        try:
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            
            # CRITICAL TEST: Factory should create isolated user emitters
            websocket_factory = WebSocketBridgeFactory()
            
            # Configure factory - this can fail due to SSOT validation
            try:
                websocket_factory.configure()
                logger.info("[U+2713] WebSocket factory configuration succeeded")
            except Exception as e:
                factory_failures.append(f"Factory configuration failed: {e}")
                pytest.fail(
                    f"FACTORY PATTERN FAILURE: WebSocket factory configuration failed. "
                    f"Error: {e}. "
                    f"This confirms SSOT validation failures identified in Five Whys analysis."
                )
            
            # CRITICAL TEST: Create user emitters for multiple users
            test_users = [user1_context, user2_context, user3_context]
            
            for user_context in test_users:
                user_id = str(user_context.user_id)
                websocket_client_id = str(user_context.websocket_client_id)
                
                try:
                    # This is the critical factory method that should work
                    user_emitter = websocket_factory.create_user_emitter(
                        user_id=user_id,
                        websocket_client_id=websocket_client_id
                    )
                    
                    if user_emitter is None:
                        factory_failures.append(f"create_user_emitter returned None for user {user_id}")
                        continue
                    
                    created_emitters[user_id] = user_emitter
                    logger.info(f"[U+2713] Created emitter for user {user_id}")
                    
                    # CRITICAL VALIDATION: Each emitter should be unique and isolated
                    assert hasattr(user_emitter, 'user_id'), (
                        f"User emitter missing user_id attribute for user {user_id}"
                    )
                    
                    assert user_emitter.user_id == user_id, (
                        f"User emitter has wrong user_id: expected {user_id}, got {user_emitter.user_id}"
                    )
                    
                    # Verify emitter has required WebSocket event methods
                    required_methods = [
                        'emit_agent_started',
                        'emit_agent_thinking',
                        'emit_tool_executing', 
                        'emit_tool_completed',
                        'emit_agent_completed'
                    ]
                    
                    for method_name in required_methods:
                        assert hasattr(user_emitter, method_name), (
                            f"User emitter missing required method {method_name} for user {user_id}"
                        )
                    
                except Exception as e:
                    factory_failures.append(f"create_user_emitter failed for user {user_id}: {e}")
                    logger.error(f"Failed to create emitter for user {user_id}: {e}")
            
            # CRITICAL ANALYSIS: Check factory pattern success/failure
            successful_emitters = len(created_emitters)
            expected_emitters = len(test_users)
            
            if successful_emitters == 0:
                pytest.fail(
                    f"FACTORY PATTERN COMPLETE FAILURE: No user emitters created successfully. "
                    f"Factory failures: {factory_failures}. "
                    f"This confirms the create_user_emitter() factory method is completely broken. "
                    f"All users will experience missing WebSocket events."
                )
            
            if successful_emitters < expected_emitters:
                pytest.fail(
                    f"FACTORY PATTERN PARTIAL FAILURE: Only {successful_emitters}/{expected_emitters} emitters created. "
                    f"Factory failures: {factory_failures}. "
                    f"This indicates inconsistent factory behavior. "
                    f"Some users will have missing WebSocket events while others work correctly."
                )
            
            # CRITICAL ISOLATION TEST: Verify emitters are truly isolated
            # Check that emitters don't share state or references
            emitter_instances = list(created_emitters.values())
            
            for i, emitter1 in enumerate(emitter_instances):
                for j, emitter2 in enumerate(emitter_instances):
                    if i != j:
                        # Emitters should be different instances
                        assert emitter1 is not emitter2, (
                            f"ISOLATION FAILURE: Emitters for different users are same instance. "
                            f"Users {list(created_emitters.keys())[i]} and {list(created_emitters.keys())[j]} share emitter."
                        )
                        
                        # Emitters should have different user IDs
                        assert emitter1.user_id != emitter2.user_id, (
                            f"ISOLATION FAILURE: Different emitter instances have same user_id: {emitter1.user_id}"
                        )
            
            # CRITICAL TEST: Verify emitters work independently
            # Test that events from one emitter don't affect others
            event_tracking = {user_id: [] for user_id in created_emitters.keys()}
            
            def create_event_tracker(tracked_user_id):
                def track_event(event_type, **kwargs):
                    event_tracking[tracked_user_id].append({
                        "event_type": event_type,
                        "user_id": tracked_user_id,
                        "kwargs": kwargs
                    })
                return track_event
            
            # Patch each emitter's methods to track events
            patches = []
            for user_id, emitter in created_emitters.items():
                tracker = create_event_tracker(user_id)
                
                # Patch event emission methods
                for method_name in ['emit_agent_started', 'emit_agent_thinking', 'emit_agent_completed']:
                    if hasattr(emitter, method_name):
                        original_method = getattr(emitter, method_name)
                        
                        def create_tracked_method(event_type, original_fn, user_tracker):
                            async def tracked_method(*args, **kwargs):
                                user_tracker(event_type)
                                if asyncio.iscoroutinefunction(original_fn):
                                    return await original_fn(*args, **kwargs)
                                return original_fn(*args, **kwargs)
                            return tracked_method
                        
                        event_type = method_name.replace('emit_', '')
                        tracked_method = create_tracked_method(event_type, original_method, tracker)
                        setattr(emitter, method_name, tracked_method)
            
            # Trigger events from each emitter
            for user_id, emitter in created_emitters.items():
                try:
                    # Simulate agent events
                    if hasattr(emitter, 'emit_agent_started'):
                        await emitter.emit_agent_started(message=f"Test from {user_id}")
                    
                    if hasattr(emitter, 'emit_agent_thinking'):
                        await emitter.emit_agent_thinking(thought=f"Thinking for {user_id}")
                    
                    if hasattr(emitter, 'emit_agent_completed'):
                        await emitter.emit_agent_completed(result=f"Complete for {user_id}")
                    
                except Exception as e:
                    factory_failures.append(f"Event emission failed for user {user_id}: {e}")
            
            # CRITICAL ANALYSIS: Verify event isolation
            for user_id, events in event_tracking.items():
                expected_events = 3  # agent_started, agent_thinking, agent_completed
                
                if len(events) < expected_events:
                    factory_failures.append(f"User {user_id} missing events: got {len(events)}, expected {expected_events}")
            
            # Check for cross-user event contamination
            for user_id, events in event_tracking.items():
                for event in events:
                    if event["user_id"] != user_id:
                        factory_failures.append(f"Cross-user contamination: User {user_id} has event for {event['user_id']}")
            
            if factory_failures:
                pytest.fail(
                    f"FACTORY PATTERN ISOLATION FAILURE: User emitters not properly isolated. "
                    f"Isolation failures: {factory_failures}. "
                    f"Event tracking results: {event_tracking}. "
                    f"This confirms the per-user factory pattern creates security vulnerabilities."
                )
                
        except ImportError as e:
            pytest.fail(
                f"FACTORY PATTERN FAILURE: Required factory components not available. "
                f"Import error: {e}. "
                f"Factory pattern migration incomplete or broken."
            )
        
        except Exception as e:
            pytest.fail(
                f"FACTORY PATTERN FAILURE: Unexpected error during factory testing. "
                f"Error: {e}. "
                f"Factory failures: {factory_failures}. "
                f"Created emitters: {len(created_emitters)}. "
                f"This indicates broader factory pattern implementation issues."
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_dependency_chain_failure(self, real_services_fixture):
        """
        Test the dependency chain failures in factory initialization.
        
        EXPECTED: This test SHOULD FAIL because factory components have
        inconsistent initialization and dependency management.
        
        Based on Five Whys Analysis:
        - Factory configuration requires all components to be properly initialized
        - Multiple required dependencies for proper emitter creation
        - No dependency orchestration ensures component availability
        """
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="dependency_test@example.com",
            environment="test"
        )
        
        logger.info(f"Testing factory dependency chain for user: {user_context.user_id}")
        
        dependency_failures = []
        
        try:
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            
            # CRITICAL TEST: Each dependency in the chain
            websocket_factory = WebSocketBridgeFactory()
            
            # Step 1: Test factory configuration dependencies
            try:
                # Before configuration - dependencies should not be available
                assert not hasattr(websocket_factory, '_connection_pool') or websocket_factory._connection_pool is None, (
                    "Connection pool should not be initialized before configure()"
                )
                
                assert not hasattr(websocket_factory, '_agent_registry') or websocket_factory._agent_registry is None, (
                    "Agent registry should not be initialized before configure()"
                )
                
                logger.info("[U+2713] Pre-configuration state correct")
                
            except Exception as e:
                dependency_failures.append(f"Pre-configuration validation failed: {e}")
            
            # Step 2: Test configuration process
            try:
                websocket_factory.configure()
                logger.info("[U+2713] Factory configuration completed")
            except Exception as e:
                dependency_failures.append(f"Factory configuration failed: {e}")
                pytest.fail(
                    f"DEPENDENCY CHAIN FAILURE: Factory configuration failed. "
                    f"Error: {e}. "
                    f"This confirms dependency initialization issues in factory pattern."
                )
            
            # Step 3: Test post-configuration dependencies
            required_dependencies = [
                ('_connection_pool', 'WebSocket connection pool'),
                ('_agent_registry', 'Agent registry'),
                ('_health_monitor', 'Health monitor'),
                ('_config', 'Configuration object')
            ]
            
            for attr_name, description in required_dependencies:
                try:
                    assert hasattr(websocket_factory, attr_name), (
                        f"Missing required dependency: {description} ({attr_name})"
                    )
                    
                    dependency = getattr(websocket_factory, attr_name)
                    assert dependency is not None, (
                        f"Dependency is None: {description} ({attr_name})"
                    )
                    
                    logger.info(f"[U+2713] {description} available")
                    
                except Exception as e:
                    dependency_failures.append(f"{description} dependency failed: {e}")
            
            # Step 4: Test dependency chain for user emitter creation
            try:
                # This requires all dependencies to work together
                user_emitter = websocket_factory.create_user_emitter(
                    user_id=str(user_context.user_id),
                    websocket_client_id=str(user_context.websocket_client_id)
                )
                
                if user_emitter is None:
                    dependency_failures.append("create_user_emitter returned None despite available dependencies")
                else:
                    logger.info("[U+2713] User emitter created with full dependency chain")
                    
            except Exception as e:
                dependency_failures.append(f"User emitter creation failed with dependencies: {e}")
            
            # Step 5: Test dependency coordination under load
            try:
                # Create multiple emitters simultaneously to test coordination
                concurrent_users = []
                for i in range(5):
                    user_ctx = await create_authenticated_user_context(
                        user_email=f"concurrent_user_{i}@example.com",
                        environment="test"
                    )
                    concurrent_users.append(user_ctx)
                
                async def create_emitter_concurrent(user_ctx):
                    """Create emitter concurrently to test dependency coordination."""
                    try:
                        emitter = websocket_factory.create_user_emitter(
                            user_id=str(user_ctx.user_id),
                            websocket_client_id=str(user_ctx.websocket_client_id)
                        )
                        return emitter is not None
                    except Exception as e:
                        logger.error(f"Concurrent emitter creation failed: {e}")
                        return False
                
                # Create emitters concurrently
                results = await asyncio.gather(
                    *[create_emitter_concurrent(user_ctx) for user_ctx in concurrent_users],
                    return_exceptions=True
                )
                
                successful_creations = sum(1 for result in results if result is True)
                failed_creations = len(results) - successful_creations
                
                if failed_creations > 0:
                    dependency_failures.append(
                        f"Concurrent emitter creation failed: {failed_creations}/{len(results)} failures"
                    )
                
                logger.info(f"Concurrent creation results: {successful_creations}/{len(results)} successful")
                
            except Exception as e:
                dependency_failures.append(f"Concurrent dependency testing failed: {e}")
            
            # CRITICAL ANALYSIS: Dependency chain integrity
            if dependency_failures:
                pytest.fail(
                    f"DEPENDENCY CHAIN FAILURE: Factory dependency management broken. "
                    f"Dependency failures: {dependency_failures}. "
                    f"This confirms the Five Whys analysis: factory components don't coordinate properly. "
                    f"No dependency orchestration ensures component availability for user emitter creation."
                )
                
        except ImportError as e:
            pytest.fail(
                f"DEPENDENCY CHAIN FAILURE: Factory dependencies not available. "
                f"Import error: {e}. "
                f"Dependency chain broken at import level."
            )
        
        except Exception as e:
            pytest.fail(
                f"DEPENDENCY CHAIN FAILURE: Unexpected error in dependency testing. "
                f"Error: {e}. "
                f"Dependency failures: {dependency_failures}. "
                f"This indicates fundamental dependency management issues in factory pattern."
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_state_consistency_failure(self, real_services_fixture):
        """
        Test factory state consistency failures during concurrent operations.
        
        EXPECTED: This test SHOULD FAIL because factory state is not consistently
        managed across concurrent user operations.
        
        Based on Five Whys Analysis:
        - Factory components initialize independently without coordination
        - SSOT validation depends on consistent state across multiple components
        - State consistency challenges between old and new patterns
        """
        auth_helper = E2EAuthHelper(environment="test")
        
        logger.info("Testing factory state consistency under concurrent operations")
        
        state_consistency_failures = []
        
        try:
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            
            # CRITICAL TEST: Create multiple factory instances to test state consistency
            factory1 = WebSocketBridgeFactory()
            factory2 = WebSocketBridgeFactory()
            factory3 = WebSocketBridgeFactory()
            
            factories = [factory1, factory2, factory3]
            
            # Test state consistency during configuration
            async def configure_factory_async(factory, factory_id):
                """Configure factory asynchronously to test state consistency."""
                try:
                    await asyncio.sleep(0.1 * factory_id)  # Stagger configuration
                    factory.configure()
                    return True
                except Exception as e:
                    logger.error(f"Factory {factory_id} configuration failed: {e}")
                    return False
            
            # Configure all factories concurrently
            configuration_results = await asyncio.gather(
                *[configure_factory_async(factory, i) for i, factory in enumerate(factories)],
                return_exceptions=True
            )
            
            successful_configs = sum(1 for result in configuration_results if result is True)
            
            if successful_configs < len(factories):
                state_consistency_failures.append(
                    f"Concurrent factory configuration failed: {successful_configs}/{len(factories)} successful"
                )
            
            # CRITICAL TEST: Verify state consistency across configured factories
            configured_factories = [f for i, f in enumerate(factories) if configuration_results[i] is True]
            
            if len(configured_factories) < 2:
                pytest.fail(
                    f"STATE CONSISTENCY FAILURE: Insufficient factories configured for state testing. "
                    f"Configured: {len(configured_factories)}/{len(factories)}. "
                    f"Cannot test state consistency with fewer than 2 factories."
                )
            
            # Test state consistency by comparing factory internal state
            reference_factory = configured_factories[0]
            
            for i, factory in enumerate(configured_factories[1:], 1):
                try:
                    # Compare critical state attributes
                    state_attributes = ['_config', '_connection_pool', '_agent_registry', '_health_monitor']
                    
                    for attr_name in state_attributes:
                        if hasattr(reference_factory, attr_name) and hasattr(factory, attr_name):
                            ref_attr = getattr(reference_factory, attr_name)
                            test_attr = getattr(factory, attr_name)
                            
                            # State should be consistent (similar type/configuration, not necessarily same instance)
                            if type(ref_attr) != type(test_attr):
                                state_consistency_failures.append(
                                    f"Factory {i} has different {attr_name} type: {type(ref_attr)} vs {type(test_attr)}"
                                )
                            
                            # Both should be either None or not None
                            if (ref_attr is None) != (test_attr is None):
                                state_consistency_failures.append(
                                    f"Factory {i} has inconsistent {attr_name} initialization"
                                )
                        else:
                            state_consistency_failures.append(
                                f"Factory {i} missing attribute {attr_name} for state consistency"
                            )
                            
                except Exception as e:
                    state_consistency_failures.append(f"State comparison failed for factory {i}: {e}")
            
            # CRITICAL TEST: Verify emitter creation consistency across factories
            test_user_contexts = []
            for i in range(3):
                user_ctx = await create_authenticated_user_context(
                    user_email=f"consistency_user_{i}@example.com",
                    environment="test"
                )
                test_user_contexts.append(user_ctx)
            
            # Create emitters from different factories for same users
            emitter_results = {}
            
            for factory_idx, factory in enumerate(configured_factories):
                emitter_results[factory_idx] = {}
                
                for user_ctx in test_user_contexts:
                    try:
                        emitter = factory.create_user_emitter(
                            user_id=str(user_ctx.user_id),
                            websocket_client_id=str(user_ctx.websocket_client_id)
                        )
                        emitter_results[factory_idx][str(user_ctx.user_id)] = emitter is not None
                    except Exception as e:
                        emitter_results[factory_idx][str(user_ctx.user_id)] = False
                        state_consistency_failures.append(
                            f"Factory {factory_idx} failed to create emitter for user {user_ctx.user_id}: {e}"
                        )
            
            # Analyze emitter creation consistency
            for user_ctx in test_user_contexts:
                user_id = str(user_ctx.user_id)
                user_results = [emitter_results[factory_idx].get(user_id, False) for factory_idx in emitter_results]
                
                # All factories should have consistent behavior for same user
                if not all(user_results) and any(user_results):
                    state_consistency_failures.append(
                        f"Inconsistent emitter creation for user {user_id}: {user_results}"
                    )
            
            # CRITICAL ANALYSIS: State consistency failures
            if state_consistency_failures:
                pytest.fail(
                    f"STATE CONSISTENCY FAILURE: Factory state not consistent across instances. "
                    f"Consistency failures: {state_consistency_failures}. "
                    f"Configured factories: {len(configured_factories)}/{len(factories)}. "
                    f"This confirms the Five Whys analysis: factory components initialize independently "
                    f"without coordinated state synchronization. SSOT validation depends on consistent "
                    f"state but components may be in different initialization phases."
                )
                
        except ImportError as e:
            pytest.fail(
                f"STATE CONSISTENCY FAILURE: Factory components not available for state testing. "
                f"Import error: {e}. "
                f"Cannot test state consistency without factory access."
            )
        
        except Exception as e:
            pytest.fail(
                f"STATE CONSISTENCY FAILURE: Unexpected error during state consistency testing. "
                f"Error: {e}. "
                f"State failures: {state_consistency_failures}. "
                f"This indicates fundamental state management issues in factory pattern."
            )