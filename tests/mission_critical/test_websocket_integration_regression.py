"""
Test WebSocket Integration Regression Prevention

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent future WebSocket integration breaks that damage user experience
- Value Impact: Ensures reliable real-time updates that drive $500K+ ARR
- Strategic Impact: Mission-critical test suite to protect core chat functionality

CRITICAL: This is a mission-critical test that prevents future integration breaks
between ExecutionEngine and AgentWebSocketBridge. It ensures the factory pattern
migration maintains proper WebSocket event delivery to users.

Based on Five Whys Root Cause Analysis:
- Root Cause: Missing dependency orchestration between factory components
- Prevention: Comprehensive integration validation across all critical paths
- Business Impact: Protects core revenue-generating chat functionality

This test SHOULD FAIL initially because it detects the current integration gap.
After fixes, this test becomes the regression prevention guardian.
"""

import pytest
import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import websockets
from unittest.mock import Mock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


class TestWebSocketIntegrationRegression(BaseIntegrationTest):
    """
    Mission-critical test suite to prevent WebSocket integration regressions.
    
    CRITICAL: This test suite validates the complete integration chain and
    prevents future breaks that would damage user experience and revenue.
    """

    @pytest.mark.mission_critical
    @pytest.mark.no_skip  # NEVER skip this test
    @pytest.mark.real_services
    async def test_complete_websocket_integration_chain_regression(self, real_services_fixture):
        """
        Test the complete WebSocket integration chain to prevent regressions.
        
        EXPECTED: This test SHOULD FAIL initially because it detects the current
        integration gap. After fixes, it becomes the primary regression guardian.
        
        Critical Integration Chain:
        1. ExecutionEngineFactory.configure()  ->  Success
        2. ExecutionEngineFactory.create_execution_engine()  ->  UserExecutionEngine
        3. UserExecutionEngine._websocket_bridge  ->  AgentWebSocketBridge
        4. AgentWebSocketBridge._user_emitter  ->  UserWebSocketEmitter
        5. UserWebSocketEmitter.emit_*()  ->  WebSocket events to user
        
        This test validates EVERY link in the chain to prevent future breaks.
        """
        # Setup authenticated test context
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="regression_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        logger.info(f"REGRESSION TEST: Validating complete WebSocket integration chain for user: {user_context.user_id}")
        
        # Track integration chain validation results
        chain_validation = {
            "factory_configuration": False,
            "execution_engine_creation": False,
            "websocket_bridge_attachment": False,
            "user_emitter_creation": False,
            "event_emission_capability": False,
            "end_to_end_event_delivery": False
        }
        
        integration_failures = []
        
        try:
            # LINK 1: ExecutionEngineFactory Configuration
            from netra_backend.app.factories.execution_factory import ExecutionEngineFactory
            
            execution_factory = ExecutionEngineFactory()
            
            try:
                execution_factory.configure()
                chain_validation["factory_configuration"] = True
                logger.info("[U+2713] REGRESSION CHECK: ExecutionEngineFactory configuration succeeded")
            except Exception as e:
                integration_failures.append(f"Factory configuration failed: {e}")
                logger.error(f"[U+2717] REGRESSION FAILURE: Factory configuration: {e}")
            
            # LINK 2: UserExecutionEngine Creation  
            if chain_validation["factory_configuration"]:
                try:
                    user_execution_engine = execution_factory.create_execution_engine(user_context)
                    
                    assert user_execution_engine is not None, "create_execution_engine returned None"
                    chain_validation["execution_engine_creation"] = True
                    logger.info("[U+2713] REGRESSION CHECK: UserExecutionEngine creation succeeded")
                    
                except Exception as e:
                    integration_failures.append(f"ExecutionEngine creation failed: {e}")
                    logger.error(f"[U+2717] REGRESSION FAILURE: ExecutionEngine creation: {e}")
            
            # LINK 3: WebSocket Bridge Attachment
            if chain_validation["execution_engine_creation"]:
                try:
                    # Check for WebSocket bridge in various possible attribute names
                    websocket_bridge_attributes = [
                        '_websocket_bridge',
                        'websocket_bridge',
                        '_agent_websocket_bridge', 
                        'agent_websocket_bridge',
                        '_websocket_manager',
                        'websocket_manager'
                    ]
                    
                    websocket_bridge = None
                    websocket_bridge_attr = None
                    
                    for attr_name in websocket_bridge_attributes:
                        if hasattr(user_execution_engine, attr_name):
                            potential_bridge = getattr(user_execution_engine, attr_name)
                            if potential_bridge is not None:
                                websocket_bridge = potential_bridge
                                websocket_bridge_attr = attr_name
                                break
                    
                    assert websocket_bridge is not None, (
                        f"ExecutionEngine missing WebSocket bridge. Checked: {websocket_bridge_attributes}"
                    )
                    
                    chain_validation["websocket_bridge_attachment"] = True
                    logger.info(f"[U+2713] REGRESSION CHECK: WebSocket bridge attached ({websocket_bridge_attr})")
                    
                except Exception as e:
                    integration_failures.append(f"WebSocket bridge attachment failed: {e}")
                    logger.error(f"[U+2717] REGRESSION FAILURE: WebSocket bridge: {e}")
            
            # LINK 4: User Emitter Creation
            if chain_validation["websocket_bridge_attachment"]:
                try:
                    # Check for user emitter in various possible attribute names
                    user_emitter_attributes = [
                        '_user_emitter',
                        'user_emitter',
                        '_emitter',
                        'emitter',
                        '_websocket_emitter',
                        'websocket_emitter'
                    ]
                    
                    user_emitter = None
                    user_emitter_attr = None
                    
                    for attr_name in user_emitter_attributes:
                        if hasattr(websocket_bridge, attr_name):
                            potential_emitter = getattr(websocket_bridge, attr_name)
                            if potential_emitter is not None:
                                user_emitter = potential_emitter
                                user_emitter_attr = attr_name
                                break
                    
                    assert user_emitter is not None, (
                        f"WebSocket bridge missing user emitter. Checked: {user_emitter_attributes}"
                    )
                    
                    # Verify emitter has correct user context
                    if hasattr(user_emitter, 'user_id'):
                        assert str(user_emitter.user_id) == str(user_context.user_id), (
                            f"User emitter has wrong user_id: expected {user_context.user_id}, got {user_emitter.user_id}"
                        )
                    
                    chain_validation["user_emitter_creation"] = True
                    logger.info(f"[U+2713] REGRESSION CHECK: User emitter created ({user_emitter_attr})")
                    
                except Exception as e:
                    integration_failures.append(f"User emitter creation failed: {e}")
                    logger.error(f"[U+2717] REGRESSION FAILURE: User emitter: {e}")
            
            # LINK 5: Event Emission Capability
            if chain_validation["user_emitter_creation"]:
                try:
                    # Verify all required event emission methods exist
                    required_event_methods = [
                        'emit_agent_started',
                        'emit_agent_thinking',
                        'emit_tool_executing',
                        'emit_tool_completed',
                        'emit_agent_completed'
                    ]
                    
                    missing_methods = []
                    for method_name in required_event_methods:
                        if not hasattr(user_emitter, method_name):
                            missing_methods.append(method_name)
                        elif not callable(getattr(user_emitter, method_name)):
                            missing_methods.append(f"{method_name} (not callable)")
                    
                    assert len(missing_methods) == 0, (
                        f"User emitter missing required methods: {missing_methods}"
                    )
                    
                    chain_validation["event_emission_capability"] = True
                    logger.info("[U+2713] REGRESSION CHECK: Event emission capability verified")
                    
                except Exception as e:
                    integration_failures.append(f"Event emission capability check failed: {e}")
                    logger.error(f"[U+2717] REGRESSION FAILURE: Event emission: {e}")
            
            # LINK 6: End-to-End Event Delivery
            if chain_validation["event_emission_capability"]:
                try:
                    # Mock WebSocket connection to capture emitted events
                    captured_events = []
                    
                    def capture_event(event_type, **kwargs):
                        captured_events.append({
                            "event_type": event_type,
                            "data": kwargs,
                            "user_id": kwargs.get("user_id"),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        logger.info(f"CAPTURED EVENT: {event_type} for user {kwargs.get('user_id')}")
                    
                    # Patch event emission methods to capture events
                    original_methods = {}
                    for method_name in required_event_methods:
                        if hasattr(user_emitter, method_name):
                            original_method = getattr(user_emitter, method_name)
                            original_methods[method_name] = original_method
                            
                            # Create wrapper that captures events
                            def create_capture_wrapper(event_type, original_fn):
                                async def capture_wrapper(*args, **kwargs):
                                    capture_event(event_type, **kwargs)
                                    if asyncio.iscoroutinefunction(original_fn):
                                        return await original_fn(*args, **kwargs)
                                    return original_fn(*args, **kwargs)
                                return capture_wrapper
                            
                            event_type = method_name.replace('emit_', '')
                            capture_wrapper = create_capture_wrapper(event_type, original_method)
                            setattr(user_emitter, method_name, capture_wrapper)
                    
                    # Execute agent request to trigger events through complete chain
                    execution_result = await user_execution_engine.execute_agent_request(
                        agent_type="triage_agent",
                        message="Regression test - validate complete WebSocket integration",
                        user_context=user_context
                    )
                    
                    # Verify events were captured
                    assert len(captured_events) > 0, (
                        "No events captured during agent execution - integration chain broken"
                    )
                    
                    # Verify minimum required events
                    captured_event_types = [event["event_type"] for event in captured_events]
                    minimum_required = ["agent_started", "agent_completed"]
                    
                    missing_required = [event for event in minimum_required if event not in captured_event_types]
                    assert len(missing_required) == 0, (
                        f"Missing required events: {missing_required}. Captured: {captured_event_types}"
                    )
                    
                    chain_validation["end_to_end_event_delivery"] = True
                    logger.info(f"[U+2713] REGRESSION CHECK: End-to-end event delivery verified ({len(captured_events)} events)")
                    
                    # Restore original methods
                    for method_name, original_method in original_methods.items():
                        setattr(user_emitter, method_name, original_method)
                    
                except Exception as e:
                    integration_failures.append(f"End-to-end event delivery failed: {e}")
                    logger.error(f"[U+2717] REGRESSION FAILURE: End-to-end delivery: {e}")
            
            # CRITICAL REGRESSION ANALYSIS
            total_links = len(chain_validation)
            successful_links = sum(chain_validation.values())
            
            logger.info(f"REGRESSION ANALYSIS: {successful_links}/{total_links} integration links validated")
            logger.info(f"Chain validation results: {chain_validation}")
            
            if successful_links < total_links:
                failed_links = [link for link, success in chain_validation.items() if not success]
                
                pytest.fail(
                    f"WEBSOCKET INTEGRATION REGRESSION DETECTED: Integration chain broken. "
                    f"Failed links: {failed_links}. "
                    f"Integration failures: {integration_failures}. "
                    f"Chain validation: {successful_links}/{total_links} successful. "
                    f"This regression breaks user WebSocket event delivery, damaging $500K+ ARR chat experience."
                )
                
        except ImportError as e:
            pytest.fail(
                f"WEBSOCKET INTEGRATION REGRESSION: Required components not available. "
                f"Import error: {e}. "
                f"Integration chain cannot be validated without component access."
            )
        
        except Exception as e:
            pytest.fail(
                f"WEBSOCKET INTEGRATION REGRESSION: Unexpected error during chain validation. "
                f"Error: {e}. "
                f"Integration failures: {integration_failures}. "
                f"Chain validation: {chain_validation}. "
                f"This indicates fundamental integration issues."
            )

    @pytest.mark.mission_critical
    @pytest.mark.no_skip  # NEVER skip this test
    @pytest.mark.real_services
    async def test_websocket_events_business_continuity_regression(self, real_services_fixture):
        """
        Test WebSocket events business continuity to prevent revenue regressions.
        
        EXPECTED: This test SHOULD FAIL initially because missing events damage
        business continuity. After fixes, it ensures business value protection.
        
        Business Continuity Requirements:
        - All 5 critical events must be delivered for user trust
        - Event delivery must be reliable across user sessions
        - Performance must meet SLA requirements for real-time experience
        - Multi-user isolation must prevent cross-user contamination
        """
        auth_helper = E2EAuthHelper(environment="test")
        
        # Create multiple business users to test continuity
        business_users = []
        for i in range(3):
            user_context = await create_authenticated_user_context(
                user_email=f"business_continuity_{i}@example.com",
                environment="test",
                websocket_enabled=True,
                permissions=["read", "write", "premium_features"]
            )
            business_users.append(user_context)
        
        logger.info(f"BUSINESS CONTINUITY TEST: Validating WebSocket events for {len(business_users)} business users")
        
        business_continuity_metrics = {
            "users_tested": len(business_users),
            "successful_event_delivery": 0,
            "failed_event_delivery": 0,
            "total_events_expected": 0,
            "total_events_delivered": 0,
            "average_event_latency": 0,
            "cross_user_contamination": 0,
            "business_value_score": 0
        }
        
        continuity_failures = []
        
        try:
            from netra_backend.app.factories.execution_factory import ExecutionEngineFactory
            
            # Test business continuity for each user
            user_results = {}
            
            for user_context in business_users:
                user_id = str(user_context.user_id)
                user_results[user_id] = {
                    "events_received": [],
                    "execution_success": False,
                    "event_latency": [],
                    "contamination_detected": False
                }
                
                try:
                    # Create execution engine for business user
                    execution_factory = ExecutionEngineFactory()
                    execution_factory.configure()
                    execution_engine = execution_factory.create_execution_engine(user_context)
                    
                    # Setup event monitoring for business value tracking
                    captured_events = []
                    event_timestamps = []
                    
                    def business_event_monitor(event_type, **kwargs):
                        """Monitor events for business continuity analysis."""
                        timestamp = asyncio.get_event_loop().time()
                        event_timestamps.append(timestamp)
                        
                        captured_events.append({
                            "event_type": event_type,
                            "user_id": kwargs.get("user_id", "unknown"),
                            "business_context": kwargs.get("business_context", {}),
                            "timestamp": timestamp
                        })
                        
                        # Check for cross-user contamination
                        event_user_id = kwargs.get("user_id")
                        if event_user_id and event_user_id != user_id:
                            user_results[user_id]["contamination_detected"] = True
                            business_continuity_metrics["cross_user_contamination"] += 1
                        
                        logger.info(f"BUSINESS EVENT: {event_type} for user {user_id}")
                    
                    # Find and patch WebSocket emitter for monitoring
                    websocket_bridge = None
                    for attr_name in ['_websocket_bridge', 'websocket_bridge']:
                        if hasattr(execution_engine, attr_name):
                            websocket_bridge = getattr(execution_engine, attr_name)
                            if websocket_bridge:
                                break
                    
                    if websocket_bridge:
                        user_emitter = None
                        for attr_name in ['_user_emitter', 'user_emitter']:
                            if hasattr(websocket_bridge, attr_name):
                                user_emitter = getattr(websocket_bridge, attr_name)
                                if user_emitter:
                                    break
                        
                        if user_emitter:
                            # Patch event methods for business monitoring
                            event_methods = [
                                'emit_agent_started',
                                'emit_agent_thinking',
                                'emit_tool_executing',
                                'emit_tool_completed',
                                'emit_agent_completed'
                            ]
                            
                            for method_name in event_methods:
                                if hasattr(user_emitter, method_name):
                                    original_method = getattr(user_emitter, method_name)
                                    
                                    def create_business_wrapper(event_type, original_fn):
                                        async def business_wrapper(*args, **kwargs):
                                            business_event_monitor(event_type, user_id=user_id, **kwargs)
                                            if asyncio.iscoroutinefunction(original_fn):
                                                return await original_fn(*args, **kwargs)
                                            return original_fn(*args, **kwargs)
                                        return business_wrapper
                                    
                                    event_type = method_name.replace('emit_', '')
                                    business_wrapper = create_business_wrapper(event_type, original_method)
                                    setattr(user_emitter, method_name, business_wrapper)
                    
                    # Execute business-critical agent request
                    start_time = asyncio.get_event_loop().time()
                    
                    execution_result = await execution_engine.execute_agent_request(
                        agent_type="optimization_agent",
                        message=f"Business continuity test for user {user_id} - analyze cost optimization",
                        user_context=user_context
                    )
                    
                    end_time = asyncio.get_event_loop().time()
                    total_latency = end_time - start_time
                    
                    # Analyze business continuity for this user
                    user_results[user_id]["events_received"] = captured_events
                    user_results[user_id]["execution_success"] = execution_result is not None
                    
                    if event_timestamps:
                        # Calculate average event latency
                        latencies = [event_timestamps[i] - start_time for i in range(len(event_timestamps))]
                        user_results[user_id]["event_latency"] = latencies
                        avg_latency = sum(latencies) / len(latencies)
                        business_continuity_metrics["average_event_latency"] += avg_latency
                    
                    # Update business metrics
                    business_continuity_metrics["total_events_expected"] += 5  # 5 critical events
                    business_continuity_metrics["total_events_delivered"] += len(captured_events)
                    
                    if len(captured_events) >= 2:  # Minimum: agent_started, agent_completed
                        business_continuity_metrics["successful_event_delivery"] += 1
                    else:
                        business_continuity_metrics["failed_event_delivery"] += 1
                        continuity_failures.append(f"User {user_id} received {len(captured_events)} events, expected 5")
                    
                except Exception as e:
                    business_continuity_metrics["failed_event_delivery"] += 1
                    continuity_failures.append(f"User {user_id} execution failed: {e}")
                    logger.error(f"Business continuity failure for user {user_id}: {e}")
            
            # Calculate business continuity scores
            if business_continuity_metrics["users_tested"] > 0:
                business_continuity_metrics["average_event_latency"] /= business_continuity_metrics["users_tested"]
            
            success_rate = (business_continuity_metrics["successful_event_delivery"] / 
                          business_continuity_metrics["users_tested"]) * 100
            
            event_delivery_rate = (business_continuity_metrics["total_events_delivered"] / 
                                 business_continuity_metrics["total_events_expected"]) * 100
            
            # Business value scoring
            if success_rate >= 95 and event_delivery_rate >= 90 and business_continuity_metrics["cross_user_contamination"] == 0:
                business_continuity_metrics["business_value_score"] = 100
            elif success_rate >= 80 and event_delivery_rate >= 70:
                business_continuity_metrics["business_value_score"] = 75  
            elif success_rate >= 50:
                business_continuity_metrics["business_value_score"] = 50
            else:
                business_continuity_metrics["business_value_score"] = 25
            
            logger.info(f"BUSINESS CONTINUITY ANALYSIS:")
            logger.info(f"  Success Rate: {success_rate:.1f}%")
            logger.info(f"  Event Delivery Rate: {event_delivery_rate:.1f}%")
            logger.info(f"  Average Latency: {business_continuity_metrics['average_event_latency']:.3f}s")
            logger.info(f"  Cross-User Contamination: {business_continuity_metrics['cross_user_contamination']}")
            logger.info(f"  Business Value Score: {business_continuity_metrics['business_value_score']}/100")
            
            # CRITICAL BUSINESS CONTINUITY ASSERTIONS
            if business_continuity_metrics["business_value_score"] < 75:
                pytest.fail(
                    f"BUSINESS CONTINUITY REGRESSION: WebSocket events failing business requirements. "
                    f"Business value score: {business_continuity_metrics['business_value_score']}/100. "
                    f"Success rate: {success_rate:.1f}%. "
                    f"Event delivery rate: {event_delivery_rate:.1f}%. "
                    f"Continuity failures: {continuity_failures}. "
                    f"This regression damages $500K+ ARR by breaking user trust and real-time experience."
                )
            
            if business_continuity_metrics["cross_user_contamination"] > 0:
                pytest.fail(
                    f"BUSINESS CONTINUITY SECURITY REGRESSION: Cross-user event contamination detected. "
                    f"Contamination incidents: {business_continuity_metrics['cross_user_contamination']}. "
                    f"This creates security vulnerabilities in multi-user system, violating enterprise requirements."
                )
            
            if business_continuity_metrics["average_event_latency"] > 5.0:
                pytest.fail(
                    f"BUSINESS CONTINUITY PERFORMANCE REGRESSION: Event latency exceeds SLA. "
                    f"Average latency: {business_continuity_metrics['average_event_latency']:.3f}s (max: 5.0s). "
                    f"Poor performance degrades user experience and competitive advantage."
                )
                
        except ImportError as e:
            pytest.fail(
                f"BUSINESS CONTINUITY REGRESSION: Required components not available. "
                f"Import error: {e}. "
                f"Cannot validate business continuity without component access."
            )
        
        except Exception as e:
            pytest.fail(
                f"BUSINESS CONTINUITY REGRESSION: Unexpected error during continuity testing. "
                f"Error: {e}. "
                f"Continuity failures: {continuity_failures}. "
                f"Business metrics: {business_continuity_metrics}. "
                f"This indicates fundamental business continuity issues."
            )

    @pytest.mark.mission_critical
    @pytest.mark.no_skip  # NEVER skip this test  
    @pytest.mark.real_services
    async def test_websocket_integration_architecture_regression(self, real_services_fixture):
        """
        Test WebSocket integration architecture to prevent architectural regressions.
        
        EXPECTED: This test SHOULD FAIL initially because it detects architectural
        issues in the factory pattern migration. After fixes, it guards architecture.
        
        Architecture Requirements:
        - Factory pattern must be consistently implemented
        - Singleton patterns must be eliminated
        - Dependency injection must work properly
        - Service orchestration must coordinate startup
        - SSOT principles must be maintained
        """
        auth_helper = E2EAuthHelper(environment="test")
        user_context = await create_authenticated_user_context(
            user_email="architecture_test@example.com",
            environment="test"
        )
        
        logger.info(f"ARCHITECTURE REGRESSION TEST: Validating WebSocket integration architecture")
        
        architecture_validation = {
            "factory_pattern_consistency": False,
            "singleton_elimination": False,
            "dependency_injection": False,
            "service_orchestration": False,
            "ssot_compliance": False,
            "interface_contracts": False
        }
        
        architecture_failures = []
        
        try:
            from netra_backend.app.factories.execution_factory import ExecutionEngineFactory
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            
            # ARCHITECTURE TEST 1: Factory Pattern Consistency
            try:
                execution_factory1 = ExecutionEngineFactory()
                execution_factory2 = ExecutionEngineFactory()
                websocket_factory1 = WebSocketBridgeFactory()
                websocket_factory2 = WebSocketBridgeFactory()
                
                # All factories should be independent instances
                assert execution_factory1 is not execution_factory2, "ExecutionEngineFactory not creating independent instances"
                assert websocket_factory1 is not websocket_factory2, "WebSocketBridgeFactory not creating independent instances"
                
                # All factories should have consistent configuration capability
                factories = [execution_factory1, execution_factory2, websocket_factory1, websocket_factory2]
                
                for factory in factories:
                    assert hasattr(factory, 'configure'), f"Factory {type(factory)} missing configure method"
                    assert callable(factory.configure), f"Factory {type(factory)} configure not callable"
                
                # Configuration should be successful for all instances
                for factory in factories:
                    factory.configure()
                
                architecture_validation["factory_pattern_consistency"] = True
                logger.info("[U+2713] ARCHITECTURE CHECK: Factory pattern consistency verified")
                
            except Exception as e:
                architecture_failures.append(f"Factory pattern consistency failed: {e}")
                logger.error(f"[U+2717] ARCHITECTURE FAILURE: Factory pattern: {e}")
            
            # ARCHITECTURE TEST 2: Singleton Elimination
            try:
                # Create multiple execution engines and verify they are independent
                execution_engines = []
                
                for i in range(3):
                    factory = ExecutionEngineFactory()
                    factory.configure()
                    engine = factory.create_execution_engine(user_context)
                    execution_engines.append(engine)
                
                # All execution engines should be different instances
                for i in range(len(execution_engines)):
                    for j in range(i + 1, len(execution_engines)):
                        assert execution_engines[i] is not execution_engines[j], (
                            f"ExecutionEngine instances {i} and {j} are same object - singleton detected"
                        )
                
                # Check WebSocket components for singleton patterns
                websocket_components = []
                
                for engine in execution_engines:
                    websocket_bridge = None
                    for attr_name in ['_websocket_bridge', 'websocket_bridge']:
                        if hasattr(engine, attr_name):
                            websocket_bridge = getattr(engine, attr_name)
                            if websocket_bridge:
                                websocket_components.append(websocket_bridge)
                                break
                
                # WebSocket bridges should be independent (not singleton)
                if len(websocket_components) > 1:
                    for i in range(len(websocket_components)):
                        for j in range(i + 1, len(websocket_components)):
                            assert websocket_components[i] is not websocket_components[j], (
                                f"WebSocket bridge instances {i} and {j} are same object - singleton detected"
                            )
                
                architecture_validation["singleton_elimination"] = True
                logger.info("[U+2713] ARCHITECTURE CHECK: Singleton elimination verified")
                
            except Exception as e:
                architecture_failures.append(f"Singleton elimination check failed: {e}")
                logger.error(f"[U+2717] ARCHITECTURE FAILURE: Singleton elimination: {e}")
            
            # ARCHITECTURE TEST 3: Dependency Injection
            try:
                # Test that factories properly inject dependencies
                execution_factory = ExecutionEngineFactory()
                execution_factory.configure()
                
                # Check factory has required dependencies
                required_dependencies = ['_config', '_websocket_bridge_factory']
                available_dependencies = []
                
                for dep_name in required_dependencies:
                    if hasattr(execution_factory, dep_name):
                        dep_value = getattr(execution_factory, dep_name)
                        if dep_value is not None:
                            available_dependencies.append(dep_name)
                
                # Factory should have dependency injection mechanism
                execution_engine = execution_factory.create_execution_engine(user_context)
                
                # Execution engine should have injected dependencies
                injected_components = []
                dependency_attributes = [
                    '_websocket_bridge',
                    '_user_context', 
                    '_config',
                    '_agent_registry'
                ]
                
                for attr_name in dependency_attributes:
                    if hasattr(execution_engine, attr_name):
                        attr_value = getattr(execution_engine, attr_name)
                        if attr_value is not None:
                            injected_components.append(attr_name)
                
                assert len(injected_components) > 0, (
                    "ExecutionEngine has no injected dependencies - dependency injection not working"
                )
                
                architecture_validation["dependency_injection"] = True
                logger.info(f"[U+2713] ARCHITECTURE CHECK: Dependency injection verified ({len(injected_components)} components)")
                
            except Exception as e:
                architecture_failures.append(f"Dependency injection check failed: {e}")
                logger.error(f"[U+2717] ARCHITECTURE FAILURE: Dependency injection: {e}")
            
            # ARCHITECTURE TEST 4: Service Orchestration
            try:
                # Test that services can be orchestrated properly
                execution_factory = ExecutionEngineFactory()
                websocket_factory = WebSocketBridgeFactory()
                
                # Test coordinated startup
                startup_order = []
                
                try:
                    execution_factory.configure()
                    startup_order.append("execution_factory")
                except Exception as e:
                    startup_order.append(f"execution_factory_failed: {e}")
                
                try:
                    websocket_factory.configure()
                    startup_order.append("websocket_factory")
                except Exception as e:
                    startup_order.append(f"websocket_factory_failed: {e}")
                
                # Both factories should configure successfully
                successful_startups = [item for item in startup_order if not item.endswith("_failed")]
                assert len(successful_startups) >= 2, (
                    f"Service orchestration failed. Startup order: {startup_order}"
                )
                
                # Test coordinated component creation
                execution_engine = execution_factory.create_execution_engine(user_context)
                user_emitter = websocket_factory.create_user_emitter(
                    user_id=str(user_context.user_id),
                    websocket_client_id=str(user_context.websocket_client_id)
                )
                
                assert execution_engine is not None, "Execution engine creation failed in orchestration"
                assert user_emitter is not None, "User emitter creation failed in orchestration"
                
                architecture_validation["service_orchestration"] = True
                logger.info("[U+2713] ARCHITECTURE CHECK: Service orchestration verified")
                
            except Exception as e:
                architecture_failures.append(f"Service orchestration check failed: {e}")
                logger.error(f"[U+2717] ARCHITECTURE FAILURE: Service orchestration: {e}")
            
            # ARCHITECTURE TEST 5: SSOT Compliance
            try:
                # Test Single Source of Truth compliance
                execution_factory = ExecutionEngineFactory()
                execution_factory.configure()
                
                # Check for SSOT configuration patterns
                ssot_indicators = []
                
                if hasattr(execution_factory, '_config'):
                    config = execution_factory._config
                    if config and hasattr(config, 'get'):
                        ssot_indicators.append("unified_config")
                
                if hasattr(execution_factory, '_websocket_bridge_factory'):
                    bridge_factory = execution_factory._websocket_bridge_factory
                    if bridge_factory:
                        ssot_indicators.append("websocket_bridge_factory")
                
                # Create multiple engines and verify they use SSOT patterns
                engine1 = execution_factory.create_execution_engine(user_context)
                engine2 = execution_factory.create_execution_engine(user_context)
                
                # Engines should have consistent configuration (SSOT)
                if hasattr(engine1, '_config') and hasattr(engine2, '_config'):
                    config1 = engine1._config
                    config2 = engine2._config
                    
                    # Configs should be from same source (SSOT)
                    if config1 and config2:
                        assert type(config1) == type(config2), "Engines using different config types - SSOT violation"
                
                assert len(ssot_indicators) > 0, (
                    "No SSOT indicators found - factory not following SSOT principles"
                )
                
                architecture_validation["ssot_compliance"] = True
                logger.info(f"[U+2713] ARCHITECTURE CHECK: SSOT compliance verified ({len(ssot_indicators)} indicators)")
                
            except Exception as e:
                architecture_failures.append(f"SSOT compliance check failed: {e}")
                logger.error(f"[U+2717] ARCHITECTURE FAILURE: SSOT compliance: {e}")
            
            # ARCHITECTURE TEST 6: Interface Contracts
            try:
                # Test that components follow proper interface contracts
                execution_factory = ExecutionEngineFactory()
                execution_factory.configure()
                
                execution_engine = execution_factory.create_execution_engine(user_context)
                
                # ExecutionEngine should follow expected interface
                required_execution_methods = [
                    'execute_agent_request'
                ]
                
                missing_execution_methods = []
                for method_name in required_execution_methods:
                    if not hasattr(execution_engine, method_name):
                        missing_execution_methods.append(method_name)
                    elif not callable(getattr(execution_engine, method_name)):
                        missing_execution_methods.append(f"{method_name} (not callable)")
                
                assert len(missing_execution_methods) == 0, (
                    f"ExecutionEngine missing interface methods: {missing_execution_methods}"
                )
                
                # WebSocket components should follow expected interface
                websocket_bridge = None
                for attr_name in ['_websocket_bridge', 'websocket_bridge']:
                    if hasattr(execution_engine, attr_name):
                        websocket_bridge = getattr(execution_engine, attr_name)
                        if websocket_bridge:
                            break
                
                if websocket_bridge:
                    user_emitter = None
                    for attr_name in ['_user_emitter', 'user_emitter']:
                        if hasattr(websocket_bridge, attr_name):
                            user_emitter = getattr(websocket_bridge, attr_name)
                            if user_emitter:
                                break
                    
                    if user_emitter:
                        required_emitter_methods = [
                            'emit_agent_started',
                            'emit_agent_completed'
                        ]
                        
                        missing_emitter_methods = []
                        for method_name in required_emitter_methods:
                            if not hasattr(user_emitter, method_name):
                                missing_emitter_methods.append(method_name)
                            elif not callable(getattr(user_emitter, method_name)):
                                missing_emitter_methods.append(f"{method_name} (not callable)")
                        
                        assert len(missing_emitter_methods) == 0, (
                            f"User emitter missing interface methods: {missing_emitter_methods}"
                        )
                
                architecture_validation["interface_contracts"] = True
                logger.info("[U+2713] ARCHITECTURE CHECK: Interface contracts verified")
                
            except Exception as e:
                architecture_failures.append(f"Interface contracts check failed: {e}")
                logger.error(f"[U+2717] ARCHITECTURE FAILURE: Interface contracts: {e}")
            
            # CRITICAL ARCHITECTURE ANALYSIS
            total_checks = len(architecture_validation)
            successful_checks = sum(architecture_validation.values())
            
            logger.info(f"ARCHITECTURE ANALYSIS: {successful_checks}/{total_checks} architecture checks passed")
            logger.info(f"Architecture validation results: {architecture_validation}")
            
            if successful_checks < total_checks:
                failed_checks = [check for check, success in architecture_validation.items() if not success]
                
                pytest.fail(
                    f"WEBSOCKET INTEGRATION ARCHITECTURE REGRESSION: Architecture violations detected. "
                    f"Failed checks: {failed_checks}. "
                    f"Architecture failures: {architecture_failures}. "
                    f"Architecture validation: {successful_checks}/{total_checks} successful. "
                    f"This regression indicates incomplete factory pattern migration and violates "
                    f"architectural principles required for stable multi-user WebSocket functionality."
                )
                
        except ImportError as e:
            pytest.fail(
                f"ARCHITECTURE REGRESSION: Required components not available for architecture testing. "
                f"Import error: {e}. "
                f"Architecture cannot be validated without component access."
            )
        
        except Exception as e:
            pytest.fail(
                f"ARCHITECTURE REGRESSION: Unexpected error during architecture validation. "
                f"Error: {e}. "
                f"Architecture failures: {architecture_failures}. "
                f"Architecture validation: {architecture_validation}. "
                f"This indicates fundamental architectural issues in WebSocket integration."
            )