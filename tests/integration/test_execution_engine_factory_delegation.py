"""
Test ExecutionEngine Factory Delegation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure ExecutionEngine properly delegates to factory pattern
- Value Impact: Factory delegation enables per-user isolation and WebSocket event delivery
- Strategic Impact: Core architecture pattern for multi-user system security and functionality

CRITICAL: This test reproduces the ExecutionEngine factory delegation failure identified
in the Five Whys Root Cause Analysis. ExecutionEngine was not updated when the factory
pattern was implemented, breaking the handoff to UserExecutionEngine.

Based on Five Whys Analysis:
- Root Cause: ExecutionEngine factory delegation to UserExecutionEngine is broken
- Impact: Per-request WebSocket emitter creation fails
- Evidence: Factory initialization failures cause cascade errors

This test SHOULD FAIL initially because ExecutionEngine doesn't use the new factory pattern.
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


class TestExecutionEngineFactoryDelegation(BaseIntegrationTest):
    """
    Test ExecutionEngine factory delegation to UserExecutionEngine.
    
    CRITICAL: This test reproduces the handoff failure where ExecutionEngine
    should delegate to the factory pattern but doesn't properly integrate.
    """

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_factory_delegation_handoff(self, real_services_fixture):
        """
        Test ExecutionEngine factory delegation to UserExecutionEngine.
        
        EXPECTED: This test SHOULD FAIL because ExecutionEngine doesn't properly
        delegate to the factory pattern for user-specific execution engines.
        
        Five Whys Root Cause:
        - ExecutionEngine was not updated when AgentWebSocketBridge migrated
        - Factory delegation is broken at the handoff point
        - Per-request execution engine creation fails
        """
        # Setup authenticated user context for factory testing
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="factory_delegation@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        logger.info(f"Testing ExecutionEngine factory delegation for user: {user_context.user_id}")
        
        delegation_failures = []
        
        try:
            from netra_backend.app.factories.execution_factory import ExecutionEngineFactory
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            
            # CRITICAL TEST: Factory should create ExecutionEngine instances
            execution_factory = ExecutionEngineFactory()
            
            # Step 1: Test factory configuration
            try:
                execution_factory.configure()
                logger.info("[U+2713] ExecutionEngineFactory configuration succeeded")
            except Exception as e:
                delegation_failures.append(f"Factory configuration failed: {e}")
                pytest.fail(
                    f"FACTORY DELEGATION FAILURE: ExecutionEngineFactory configuration failed. "
                    f"Error: {e}. "
                    f"Factory pattern not properly implemented for execution engines."
                )
            
            # Step 2: Test factory delegation - create user-specific execution engine
            try:
                user_execution_engine = execution_factory.create_execution_engine(user_context)
                
                assert user_execution_engine is not None, (
                    "Factory delegation failure: create_execution_engine returned None"
                )
                
                logger.info("[U+2713] User-specific ExecutionEngine created via factory")
                
            except Exception as e:
                delegation_failures.append(f"create_execution_engine failed: {e}")
                pytest.fail(
                    f"FACTORY DELEGATION FAILURE: create_execution_engine failed. "
                    f"Error: {e}. "
                    f"ExecutionEngineFactory not properly creating user-specific instances. "
                    f"This confirms the factory delegation is broken at the handoff point."
                )
            
            # CRITICAL TEST: Verify ExecutionEngine has WebSocket integration
            # This is the key integration point that's broken
            try:
                # Check if ExecutionEngine was configured with WebSocket bridge
                websocket_integration_attributes = [
                    '_websocket_bridge',
                    'websocket_bridge', 
                    '_websocket_manager',
                    'websocket_manager',
                    '_agent_websocket_bridge',
                    'agent_websocket_bridge'
                ]
                
                websocket_integration_found = False
                websocket_attribute = None
                
                for attr_name in websocket_integration_attributes:
                    if hasattr(user_execution_engine, attr_name):
                        websocket_attribute = attr_name
                        websocket_integration = getattr(user_execution_engine, attr_name)
                        if websocket_integration is not None:
                            websocket_integration_found = True
                            logger.info(f"[U+2713] WebSocket integration found: {attr_name}")
                            break
                
                if not websocket_integration_found:
                    delegation_failures.append("ExecutionEngine missing WebSocket integration")
                    pytest.fail(
                        f"FACTORY DELEGATION FAILURE: ExecutionEngine lacks WebSocket integration. "
                        f"Checked attributes: {websocket_integration_attributes}. "
                        f"Factory delegation not establishing proper WebSocket connections. "
                        f"This confirms the Five Whys analysis: ExecutionEngine not updated for factory pattern."
                    )
                
                # Verify WebSocket integration is properly configured
                websocket_integration = getattr(user_execution_engine, websocket_attribute)
                
                # Check if WebSocket bridge has user emitter
                user_emitter_attributes = [
                    '_user_emitter',
                    'user_emitter',
                    '_emitter',
                    'emitter'
                ]
                
                user_emitter_found = False
                for attr_name in user_emitter_attributes:
                    if hasattr(websocket_integration, attr_name):
                        user_emitter = getattr(websocket_integration, attr_name)
                        if user_emitter is not None:
                            user_emitter_found = True
                            logger.info(f"[U+2713] User emitter found: {attr_name}")
                            break
                
                if not user_emitter_found:
                    delegation_failures.append("WebSocket integration missing user emitter")
                    pytest.fail(
                        f"FACTORY DELEGATION FAILURE: WebSocket integration missing user emitter. "
                        f"WebSocket integration: {type(websocket_integration)}. "
                        f"Per-request factory pattern not creating user-specific emitters. "
                        f"This confirms emitter creation fails as identified in Five Whys analysis."
                    )
                
            except Exception as e:
                delegation_failures.append(f"WebSocket integration verification failed: {e}")
                pytest.fail(
                    f"FACTORY DELEGATION FAILURE: WebSocket integration verification failed. "
                    f"Error: {e}. "
                    f"This indicates the ExecutionEngine-WebSocket bridge integration is broken."
                )
            
            # CRITICAL TEST: Verify ExecutionEngine can execute agent requests
            # This tests the complete factory delegation chain
            try:
                # Mock WebSocket emitter to track event emissions
                emitted_events = []
                
                def mock_emit_event(event_type, **kwargs):
                    emitted_events.append({
                        "event_type": event_type,
                        "kwargs": kwargs,
                        "user_id": kwargs.get("user_id", "unknown")
                    })
                    logger.info(f"Mock event emitted: {event_type} for user {kwargs.get('user_id')}")
                
                # Find and patch the WebSocket emitter methods
                websocket_integration = getattr(user_execution_engine, websocket_attribute)
                
                for emitter_attr in user_emitter_attributes:
                    if hasattr(websocket_integration, emitter_attr):
                        user_emitter = getattr(websocket_integration, emitter_attr)
                        if user_emitter is not None:
                            # Patch event emission methods
                            event_methods = [
                                'emit_agent_started',
                                'emit_agent_thinking',
                                'emit_tool_executing',
                                'emit_tool_completed', 
                                'emit_agent_completed'
                            ]
                            
                            for method_name in event_methods:
                                if hasattr(user_emitter, method_name):
                                    setattr(user_emitter, method_name, 
                                           lambda event=method_name.replace('emit_', ''), **kw: mock_emit_event(event, **kw))
                            break
                
                # Test agent execution through factory-created ExecutionEngine
                execution_result = await user_execution_engine.execute_agent_request(
                    agent_type="triage_agent",
                    message="Test factory delegation handoff",
                    user_context=user_context
                )
                
                # Verify execution was successful
                assert execution_result is not None, (
                    "Agent execution returned None - factory delegation chain broken"
                )
                
                # Verify WebSocket events were emitted
                if len(emitted_events) == 0:
                    delegation_failures.append("No WebSocket events emitted during agent execution")
                    pytest.fail(
                        f"FACTORY DELEGATION FAILURE: No WebSocket events emitted. "
                        f"ExecutionEngine -> WebSocket bridge integration broken. "
                        f"Users will not receive real-time updates during agent execution."
                    )
                
                # Check for required events
                event_types = [event["event_type"] for event in emitted_events]
                required_events = ["agent_started", "agent_completed"]
                
                missing_events = [event for event in required_events if event not in event_types]
                if missing_events:
                    delegation_failures.append(f"Missing required events: {missing_events}")
                
                logger.info(f"[U+2713] Agent execution successful, events: {event_types}")
                
            except Exception as e:
                delegation_failures.append(f"Agent execution through factory failed: {e}")
                pytest.fail(
                    f"FACTORY DELEGATION FAILURE: Agent execution failed through factory-created ExecutionEngine. "
                    f"Error: {e}. "
                    f"This confirms the complete factory delegation chain is broken. "
                    f"Factory pattern not enabling agent execution with WebSocket events."
                )
                
        except ImportError as e:
            pytest.fail(
                f"FACTORY DELEGATION FAILURE: Required factory components not available. "
                f"Import error: {e}. "
                f"Factory pattern migration incomplete."
            )
        
        except Exception as e:
            pytest.fail(
                f"FACTORY DELEGATION FAILURE: Unexpected error during delegation testing. "
                f"Error: {e}. "
                f"Delegation failures: {delegation_failures}. "
                f"This indicates broader factory pattern implementation issues."
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_direct_vs_factory_inconsistency(self, real_services_fixture):
        """
        Test inconsistency between direct ExecutionEngine creation and factory creation.
        
        EXPECTED: This test SHOULD FAIL because direct creation and factory creation
        produce different ExecutionEngine instances with different capabilities.
        
        Based on Five Whys Analysis:
        - Architecture evolved from singleton to factory patterns without updating ExecutionEngine
        - Direct creation vs factory creation should be consistent
        - Inconsistency indicates incomplete migration
        """
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="consistency_test@example.com",
            environment="test"
        )
        
        logger.info(f"Testing ExecutionEngine creation consistency for user: {user_context.user_id}")
        
        consistency_failures = []
        
        try:
            from netra_backend.app.factories.execution_factory import ExecutionEngineFactory
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            
            # CRITICAL TEST: Compare direct creation vs factory creation
            
            # Method 1: Direct ExecutionEngine creation (legacy pattern)
            try:
                direct_execution_engine = ExecutionEngine()
                logger.info("[U+2713] Direct ExecutionEngine creation succeeded")
                direct_creation_success = True
            except Exception as e:
                logger.error(f"Direct ExecutionEngine creation failed: {e}")
                direct_execution_engine = None
                direct_creation_success = False
                consistency_failures.append(f"Direct creation failed: {e}")
            
            # Method 2: Factory ExecutionEngine creation (new pattern)
            try:
                execution_factory = ExecutionEngineFactory()
                execution_factory.configure()
                factory_execution_engine = execution_factory.create_execution_engine(user_context)
                logger.info("[U+2713] Factory ExecutionEngine creation succeeded")
                factory_creation_success = True
            except Exception as e:
                logger.error(f"Factory ExecutionEngine creation failed: {e}")
                factory_execution_engine = None
                factory_creation_success = False
                consistency_failures.append(f"Factory creation failed: {e}")
            
            # CRITICAL ANALYSIS: Creation method consistency
            if not direct_creation_success and not factory_creation_success:
                pytest.fail(
                    f"CREATION CONSISTENCY FAILURE: Both direct and factory creation failed. "
                    f"Consistency failures: {consistency_failures}. "
                    f"ExecutionEngine completely broken - no working creation method."
                )
            
            if direct_creation_success != factory_creation_success:
                pytest.fail(
                    f"CREATION CONSISTENCY FAILURE: Inconsistent creation success. "
                    f"Direct creation: {direct_creation_success}, Factory creation: {factory_creation_success}. "
                    f"This indicates incomplete migration from direct to factory pattern."
                )
            
            # If both succeeded, compare their capabilities
            if direct_creation_success and factory_creation_success:
                
                # CRITICAL TEST: Compare ExecutionEngine types and capabilities
                direct_type = type(direct_execution_engine)
                factory_type = type(factory_execution_engine)
                
                if direct_type != factory_type:
                    consistency_failures.append(
                        f"Different types: direct={direct_type}, factory={factory_type}"
                    )
                
                # Compare WebSocket integration capabilities
                websocket_attributes = [
                    '_websocket_bridge',
                    'websocket_bridge',
                    '_websocket_manager', 
                    'websocket_manager'
                ]
                
                direct_websocket_attrs = []
                factory_websocket_attrs = []
                
                for attr in websocket_attributes:
                    if hasattr(direct_execution_engine, attr):
                        direct_websocket_attrs.append(attr)
                    if hasattr(factory_execution_engine, attr):
                        factory_websocket_attrs.append(attr)
                
                if set(direct_websocket_attrs) != set(factory_websocket_attrs):
                    consistency_failures.append(
                        f"Different WebSocket attributes: direct={direct_websocket_attrs}, factory={factory_websocket_attrs}"
                    )
                
                # Compare user context capabilities
                user_context_attributes = [
                    '_user_context',
                    'user_context',
                    '_user_id',
                    'user_id'
                ]
                
                direct_context_attrs = []
                factory_context_attrs = []
                
                for attr in user_context_attributes:
                    if hasattr(direct_execution_engine, attr):
                        direct_context_attrs.append(attr)
                    if hasattr(factory_execution_engine, attr):
                        factory_context_attrs.append(attr)
                
                if set(direct_context_attrs) != set(factory_context_attrs):
                    consistency_failures.append(
                        f"Different user context attributes: direct={direct_context_attrs}, factory={factory_context_attrs}"
                    )
                
                # CRITICAL TEST: Compare execution capabilities
                try:
                    # Test if both can execute agent requests
                    direct_execution_capable = hasattr(direct_execution_engine, 'execute_agent_request')
                    factory_execution_capable = hasattr(factory_execution_engine, 'execute_agent_request')
                    
                    if direct_execution_capable != factory_execution_capable:
                        consistency_failures.append(
                            f"Different execution capabilities: direct={direct_execution_capable}, factory={factory_execution_capable}"
                        )
                    
                    # If both have execution capability, test actual execution
                    if direct_execution_capable and factory_execution_capable:
                        
                        # Test direct execution
                        try:
                            direct_result = await direct_execution_engine.execute_agent_request(
                                agent_type="triage_agent",
                                message="Direct execution test",
                                user_context=user_context
                            )
                            direct_execution_works = True
                        except Exception as e:
                            direct_execution_works = False
                            consistency_failures.append(f"Direct execution failed: {e}")
                        
                        # Test factory execution  
                        try:
                            factory_result = await factory_execution_engine.execute_agent_request(
                                agent_type="triage_agent",
                                message="Factory execution test",
                                user_context=user_context
                            )
                            factory_execution_works = True
                        except Exception as e:
                            factory_execution_works = False
                            consistency_failures.append(f"Factory execution failed: {e}")
                        
                        # Compare execution success
                        if direct_execution_works != factory_execution_works:
                            consistency_failures.append(
                                f"Execution success inconsistent: direct={direct_execution_works}, factory={factory_execution_works}"
                            )
                        
                except Exception as e:
                    consistency_failures.append(f"Execution capability testing failed: {e}")
            
            # CRITICAL ANALYSIS: Overall consistency
            if consistency_failures:
                pytest.fail(
                    f"EXECUTION ENGINE CONSISTENCY FAILURE: Direct and factory creation produce inconsistent results. "
                    f"Consistency failures: {consistency_failures}. "
                    f"This confirms incomplete migration from singleton to factory patterns. "
                    f"Different code paths produce different ExecutionEngine capabilities, "
                    f"indicating the architecture evolution was not properly completed."
                )
                
        except ImportError as e:
            pytest.fail(
                f"CONSISTENCY TEST FAILURE: Required components not available for consistency testing. "
                f"Import error: {e}. "
                f"Cannot compare creation methods without component access."
            )
        
        except Exception as e:
            pytest.fail(
                f"CONSISTENCY TEST FAILURE: Unexpected error during consistency testing. "
                f"Error: {e}. "
                f"Consistency failures: {consistency_failures}. "
                f"This indicates broader ExecutionEngine implementation issues."
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_factory_configuration_cascade(self, real_services_fixture):
        """
        Test cascade failures in ExecutionEngine factory configuration.
        
        EXPECTED: This test SHOULD FAIL because factory configuration has multiple
        failure points that can cause cascade errors throughout the system.
        
        Based on Five Whys Analysis:
        - Factory initialization failures cause cascade errors
        - Each factory manages its own lifecycle without coordination
        - State consistency challenges during factory configuration
        """
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="cascade_test@example.com",
            environment="test"
        )
        
        logger.info(f"Testing ExecutionEngine factory configuration cascade for user: {user_context.user_id}")
        
        cascade_failures = []
        
        try:
            from netra_backend.app.factories.execution_factory import ExecutionEngineFactory
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            
            # CRITICAL TEST: Test configuration cascade across multiple factories
            
            # Step 1: Create multiple factory instances
            execution_factory1 = ExecutionEngineFactory()
            execution_factory2 = ExecutionEngineFactory()
            websocket_factory = WebSocketBridgeFactory()
            
            factories = [
                ("execution_factory1", execution_factory1),
                ("execution_factory2", execution_factory2), 
                ("websocket_factory", websocket_factory)
            ]
            
            # Step 2: Test individual factory configuration
            configuration_results = {}
            
            for factory_name, factory in factories:
                try:
                    factory.configure()
                    configuration_results[factory_name] = True
                    logger.info(f"[U+2713] {factory_name} configuration succeeded")
                except Exception as e:
                    configuration_results[factory_name] = False
                    cascade_failures.append(f"{factory_name} configuration failed: {e}")
                    logger.error(f"[U+2717] {factory_name} configuration failed: {e}")
            
            successful_configs = sum(configuration_results.values())
            total_configs = len(configuration_results)
            
            if successful_configs == 0:
                pytest.fail(
                    f"FACTORY CONFIGURATION CASCADE FAILURE: All factory configurations failed. "
                    f"Cascade failures: {cascade_failures}. "
                    f"Complete system failure - no factories can be configured."
                )
            
            if successful_configs < total_configs:
                pytest.fail(
                    f"FACTORY CONFIGURATION PARTIAL FAILURE: {successful_configs}/{total_configs} factories configured. "
                    f"Cascade failures: {cascade_failures}. "
                    f"Inconsistent factory configuration causes unpredictable system behavior."
                )
            
            # Step 3: Test cross-factory coordination
            try:
                # Create ExecutionEngine from execution factory
                if configuration_results["execution_factory1"]:
                    execution_engine = execution_factory1.create_execution_engine(user_context)
                    assert execution_engine is not None, "ExecutionEngine creation returned None"
                    logger.info("[U+2713] ExecutionEngine created from factory")
                
                # Create WebSocket emitter from websocket factory
                if configuration_results["websocket_factory"]:
                    user_emitter = websocket_factory.create_user_emitter(
                        user_id=str(user_context.user_id),
                        websocket_client_id=str(user_context.websocket_client_id)
                    )
                    assert user_emitter is not None, "User emitter creation returned None"
                    logger.info("[U+2713] User emitter created from factory")
                
                # CRITICAL TEST: Verify cross-factory integration
                # ExecutionEngine should be able to use WebSocket emitter from different factory
                if configuration_results["execution_factory1"] and configuration_results["websocket_factory"]:
                    
                    # Check if ExecutionEngine can integrate with separately created WebSocket emitter
                    # This tests cross-factory coordination
                    try:
                        # Try to inject WebSocket emitter into ExecutionEngine
                        if hasattr(execution_engine, 'set_websocket_emitter'):
                            execution_engine.set_websocket_emitter(user_emitter)
                            logger.info("[U+2713] Cross-factory WebSocket integration succeeded")
                        elif hasattr(execution_engine, '_websocket_bridge'):
                            # Try to set emitter on WebSocket bridge
                            websocket_bridge = execution_engine._websocket_bridge
                            if websocket_bridge and hasattr(websocket_bridge, 'set_user_emitter'):
                                websocket_bridge.set_user_emitter(user_emitter)
                                logger.info("[U+2713] Cross-factory bridge integration succeeded")
                            else:
                                cascade_failures.append("ExecutionEngine WebSocket bridge not compatible with external emitter")
                        else:
                            cascade_failures.append("ExecutionEngine not designed for cross-factory integration")
                    
                    except Exception as e:
                        cascade_failures.append(f"Cross-factory integration failed: {e}")
                
            except Exception as e:
                cascade_failures.append(f"Cross-factory coordination testing failed: {e}")
            
            # Step 4: Test factory instance isolation
            try:
                # Create multiple execution engines from different factory instances
                if configuration_results["execution_factory1"] and configuration_results["execution_factory2"]:
                    
                    engine1 = execution_factory1.create_execution_engine(user_context)
                    engine2 = execution_factory2.create_execution_engine(user_context)
                    
                    # Engines should be different instances but have consistent capabilities
                    assert engine1 is not engine2, "Factory instances creating same ExecutionEngine instance"
                    
                    # Both should have same type and capabilities
                    assert type(engine1) == type(engine2), f"Factory instances creating different types: {type(engine1)} vs {type(engine2)}"
                    
                    # Both should have same attributes
                    engine1_attrs = set(dir(engine1))
                    engine2_attrs = set(dir(engine2))
                    
                    missing_attrs = engine1_attrs.symmetric_difference(engine2_attrs)
                    if missing_attrs:
                        cascade_failures.append(f"Factory instances creating engines with different attributes: {missing_attrs}")
                    
                    logger.info("[U+2713] Factory instance isolation verified")
                
            except Exception as e:
                cascade_failures.append(f"Factory instance isolation testing failed: {e}")
            
            # Step 5: Test configuration state persistence
            try:
                # Verify factory configuration persists across multiple operations
                for factory_name, factory in factories:
                    if configuration_results[factory_name]:
                        
                        # Test multiple operations on same factory
                        for i in range(3):
                            try:
                                if factory_name.startswith("execution"):
                                    test_engine = factory.create_execution_engine(user_context)
                                    assert test_engine is not None, f"Factory operation {i} failed for {factory_name}"
                                elif factory_name == "websocket_factory":
                                    test_emitter = factory.create_user_emitter(
                                        user_id=str(user_context.user_id),
                                        websocket_client_id=str(user_context.websocket_client_id)
                                    )
                                    assert test_emitter is not None, f"Factory operation {i} failed for {factory_name}"
                            
                            except Exception as e:
                                cascade_failures.append(f"{factory_name} operation {i} failed: {e}")
                
                logger.info("[U+2713] Factory configuration persistence verified")
                
            except Exception as e:
                cascade_failures.append(f"Configuration persistence testing failed: {e}")
            
            # CRITICAL ANALYSIS: Cascade failure impact
            if cascade_failures:
                pytest.fail(
                    f"FACTORY CONFIGURATION CASCADE FAILURE: Multiple factory configuration issues detected. "
                    f"Cascade failures: {cascade_failures}. "
                    f"Successful configurations: {successful_configs}/{total_configs}. "
                    f"This confirms the Five Whys analysis: factory initialization failures cause cascade errors "
                    f"because each factory manages its own lifecycle without coordination. State consistency "
                    f"challenges occur when multiple factories are involved in creating a complete system."
                )
                
        except ImportError as e:
            pytest.fail(
                f"CASCADE TEST FAILURE: Required factory components not available. "
                f"Import error: {e}. "
                f"Cannot test cascade behavior without factory access."
            )
        
        except Exception as e:
            pytest.fail(
                f"CASCADE TEST FAILURE: Unexpected error during cascade testing. "
                f"Error: {e}. "
                f"Cascade failures: {cascade_failures}. "
                f"This indicates fundamental factory coordination issues."
            )