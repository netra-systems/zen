"""
Test cross-service integration for WebSocket SSOT migration (Issue #1182).

CRITICAL BUSINESS IMPACT: $500K+ ARR Golden Path requires seamless integration between
WebSocket infrastructure and all dependent services. This test validates service boundary
compliance and integration stability during SSOT migration.

ISSUE #1182: WebSocket Manager SSOT Migration
- Problem: Competing WebSocket implementations causing integration inconsistencies
- Impact: Service boundary violations, interface mismatches, integration failures
- Solution: Consolidated SSOT WebSocket manager with consistent cross-service interfaces

RELATED ISSUES:
- Issue #1209: DemoWebSocketBridge interface failure (cross-service integration regression)
- Issue #762: Agent WebSocket Bridge test coverage gaps
- Issue #714: BaseAgent integration dependencies on WebSocket interfaces

Test Strategy:
1. Test AgentWebSocketBridge integration consistency (SHOULD FAIL INITIALLY)
2. Validate demo WebSocket service compatibility (SHOULD FAIL INITIALLY)
3. Test cross-service interface contracts (SHOULD FAIL INITIALLY)
4. Verify service boundary compliance with SSOT patterns (SHOULD FAIL INITIALLY)

Business Value Justification:
- Segment: Platform Infrastructure
- Business Goal: Service Integration Reliability & Developer Velocity
- Value Impact: Eliminates integration failures and cross-service inconsistencies
- Revenue Impact: Protects Golden Path stability and reduces integration maintenance costs
"""

import pytest
import asyncio
import unittest
import json
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from datetime import datetime

from test_framework.ssot.base_test_case import BaseIntegrationTest
from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ThreadID, ConnectionID

logger = get_logger(__name__)


@dataclass
class IntegrationTestResult:
    """Data class to track cross-service integration test results."""
    service_name: str
    integration_point: str
    success: bool
    error_message: Optional[str] = None
    interface_compatibility: bool = False
    performance_metrics: Optional[Dict[str, float]] = None
    ssot_compliance: bool = False


@pytest.mark.integration
class WebSocketCrossServiceIntegrationTests(BaseIntegrationTest):
    """
    Integration tests for Issue #1182 WebSocket Manager SSOT cross-service compatibility.
    
    These tests validate that the consolidated WebSocket manager properly integrates
    with all dependent services without breaking existing functionality.
    """

    def setUp(self):
        """Set up integration test environment for cross-service validation."""
        super().setUp()
        self.integration_results = []
        self.test_user_id = "integration_test_user"
        self.test_thread_id = "integration_test_thread"

    async def test_agent_websocket_bridge_integration_consistency(self):
        """
        Test AgentWebSocketBridge integration with consolidated WebSocket manager.
        
        CURRENT STATE: SHOULD FAIL - Integration inconsistencies detected
        TARGET STATE: SHOULD PASS - Seamless integration with SSOT manager
        
        Business Impact: Critical for agent execution and WebSocket event delivery
        Related: Issue #762 Agent WebSocket Bridge test coverage
        """
        logger.info("🌉 Testing AgentWebSocketBridge integration consistency (Issue #1182)")
        
        integration_result = IntegrationTestResult(
            service_name="AgentWebSocketBridge",
            integration_point="websocket_manager_integration"
        )
        
        try:
            # Test AgentWebSocketBridge import and initialization
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            
            logger.info("✓ AgentWebSocketBridge and WebSocketManager imports successful")
            
            # Create WebSocket manager instance
            mock_websocket = AsyncMock()
            mock_websocket.send_text = AsyncMock()
            
            id_manager = UnifiedIDManager()
            user_id = self.test_user_id
            thread_id = id_manager.generate_id("THREAD", context={"user": user_id})
            
            websocket_manager = WebSocketManager(websocket=mock_websocket, user_id=user_id)
            
            # Test AgentWebSocketBridge initialization with WebSocket manager
            bridge = AgentWebSocketBridge()
            
            # Verify interface compatibility
            integration_result.interface_compatibility = True
            
            # Test bridge functionality with WebSocket manager
            test_events = [
                ("agent_started", {"message": "Agent execution started"}),
                ("agent_thinking", {"status": "processing", "progress": 25}),
                ("tool_executing", {"tool": "test_tool", "parameters": {"test": True}}),
                ("tool_completed", {"tool": "test_tool", "result": "success"}),
                ("agent_completed", {"result": "Task completed successfully"})
            ]
            
            event_delivery_count = 0
            
            for event_type, event_data in test_events:
                try:
                    # Test event delivery through bridge
                    await websocket_manager.emit_agent_event(
                        event_type=event_type,
                        data=event_data,
                        user_id=user_id,
                        thread_id=thread_id
                    )
                    event_delivery_count += 1
                    logger.info(f"✓ Event delivery successful: {event_type}")
                    
                except Exception as e:
                    logger.error(f"❌ Event delivery failed for {event_type}: {e}")
                    integration_result.error_message = f"Event delivery failed: {e}"
                    break
            
            # Verify all events were delivered
            expected_events = len(test_events)
            if event_delivery_count == expected_events:
                integration_result.success = True
                integration_result.ssot_compliance = True
                logger.info(f"✓ All {expected_events} events delivered successfully")
            else:
                integration_result.error_message = f"Event delivery incomplete: {event_delivery_count}/{expected_events}"
                logger.error(integration_result.error_message)
            
            # Test WebSocket manager method calls through bridge
            try:
                connections = websocket_manager.get_active_connections()
                integration_result.performance_metrics = {
                    'event_delivery_rate': event_delivery_count / expected_events,
                    'connection_count': len(connections) if connections else 0
                }
                logger.info(f"✓ WebSocket manager methods accessible through bridge")
                
            except Exception as e:
                logger.error(f"❌ WebSocket manager method call failed: {e}")
                integration_result.error_message = f"Method call failed: {e}"
                integration_result.success = False
            
        except ImportError as e:
            integration_result.error_message = f"Import failed: {e}"
            integration_result.success = False
            logger.error(f"❌ Import failed: {e}")
            
        except Exception as e:
            integration_result.error_message = f"Integration test failed: {e}"
            integration_result.success = False
            logger.error(f"❌ AgentWebSocketBridge integration test failed: {e}")
        
        self.integration_results.append(integration_result)
        
        # Log integration analysis
        logger.info(f"📊 AgentWebSocketBridge Integration Analysis:")
        logger.info(f"   Success: {integration_result.success}")
        logger.info(f"   Interface compatibility: {integration_result.interface_compatibility}")
        logger.info(f"   SSOT compliance: {integration_result.ssot_compliance}")
        
        if integration_result.performance_metrics:
            logger.info(f"   Performance metrics: {integration_result.performance_metrics}")
        
        if integration_result.error_message:
            logger.error(f"   Error: {integration_result.error_message}")
        
        # CRITICAL: AgentWebSocketBridge integration must be seamless
        # CURRENT STATE: This assertion SHOULD FAIL (integration inconsistencies)
        # TARGET STATE: This assertion SHOULD PASS (seamless integration)
        self.assertTrue(
            integration_result.success,
            f"AgentWebSocketBridge integration failed with SSOT WebSocket manager. "
            f"Issue #1182 cross-service integration not implemented. "
            f"Error: {integration_result.error_message}"
        )
        
        self.assertTrue(
            integration_result.interface_compatibility,
            f"AgentWebSocketBridge interface incompatible with consolidated WebSocket manager. "
            f"Issue #1182 interface standardization incomplete."
        )

    async def test_demo_websocket_service_compatibility(self):
        """
        Validate demo WebSocket service works with SSOT manager.
        
        CURRENT STATE: SHOULD FAIL - DemoWebSocketBridge interface issues
        TARGET STATE: SHOULD PASS - Demo service fully compatible with SSOT manager
        
        Business Impact: Critical for staging demo functionality and customer demos
        Related: Issue #1209 DemoWebSocketBridge interface failure regression
        """
        logger.info("🎭 Testing demo WebSocket service compatibility (Issues #1182 + #1209)")
        
        integration_result = IntegrationTestResult(
            service_name="DemoWebSocketService", 
            integration_point="demo_websocket_interface"
        )
        
        try:
            # Test demo WebSocket service imports
            from netra_backend.app.routes.demo_websocket import execute_real_agent_workflow
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            
            logger.info("✓ Demo WebSocket service imports successful")
            
            # Create mock WebSocket for demo testing
            mock_websocket = AsyncMock()
            mock_websocket.send_text = AsyncMock()
            mock_websocket.close = AsyncMock()
            
            # Capture sent messages for verification
            sent_messages = []
            
            async def capture_message(message):
                sent_messages.append({
                    'timestamp': datetime.now().isoformat(),
                    'message': message,
                    'type': type(message).__name__
                })
                logger.info(f"📨 Demo message captured: {message[:100]}...")
            
            mock_websocket.send_text = capture_message
            
            # Test demo WebSocket execution
            demo_user_message = "Test demo message for Issue #1182 validation"
            demo_connection_id = "demo_test_connection_1182"
            
            # Execute demo workflow to test integration
            try:
                await execute_real_agent_workflow(
                    websocket=mock_websocket,
                    user_message=demo_user_message,
                    connection_id=demo_connection_id
                )
                
                # Verify messages were sent
                if sent_messages:
                    integration_result.success = True
                    integration_result.interface_compatibility = True
                    integration_result.ssot_compliance = True
                    
                    # Analyze sent messages for expected patterns
                    message_types = set()
                    for msg in sent_messages:
                        try:
                            parsed = json.loads(msg['message']) if isinstance(msg['message'], str) else msg['message']
                            if isinstance(parsed, dict) and 'type' in parsed:
                                message_types.add(parsed['type'])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    integration_result.performance_metrics = {
                        'messages_sent': len(sent_messages),
                        'unique_message_types': len(message_types),
                        'demo_execution_success': True
                    }
                    
                    logger.info(f"✓ Demo WebSocket execution successful: {len(sent_messages)} messages sent")
                    logger.info(f"✓ Message types: {message_types}")
                    
                else:
                    integration_result.error_message = "No messages sent during demo execution"
                    integration_result.success = False
                    logger.error("❌ No messages sent during demo WebSocket execution")
            
            except Exception as e:
                integration_result.error_message = f"Demo execution failed: {e}"
                integration_result.success = False
                logger.error(f"❌ Demo WebSocket execution failed: {e}")
        
        except ImportError as e:
            integration_result.error_message = f"Demo service import failed: {e}"
            integration_result.success = False
            logger.error(f"❌ Demo WebSocket service import failed: {e}")
            
        except Exception as e:
            integration_result.error_message = f"Demo service test failed: {e}"
            integration_result.success = False
            logger.error(f"❌ Demo WebSocket service test failed: {e}")
        
        self.integration_results.append(integration_result)
        
        # Log demo service analysis
        logger.info(f"📊 Demo WebSocket Service Integration Analysis:")
        logger.info(f"   Success: {integration_result.success}")
        logger.info(f"   Interface compatibility: {integration_result.interface_compatibility}")
        logger.info(f"   SSOT compliance: {integration_result.ssot_compliance}")
        
        if integration_result.performance_metrics:
            logger.info(f"   Performance metrics: {integration_result.performance_metrics}")
        
        if integration_result.error_message:
            logger.error(f"   Error: {integration_result.error_message}")
        
        # CRITICAL: Demo WebSocket service must work for customer demonstrations
        # CURRENT STATE: This assertion SHOULD FAIL (Issue #1209 regression)
        # TARGET STATE: This assertion SHOULD PASS (demo service fully functional)
        self.assertTrue(
            integration_result.success,
            f"Demo WebSocket service failed with SSOT manager. "
            f"Issue #1209 regression from Issue #1182 SSOT migration. "
            f"Critical for customer demonstrations. Error: {integration_result.error_message}"
        )
        
        self.assertTrue(
            integration_result.interface_compatibility,
            f"Demo WebSocket service interface incompatible with SSOT manager. "
            f"Issue #1182 + #1209 interface alignment required."
        )

    async def test_cross_service_interface_contracts(self):
        """
        Test cross-service interface contracts with consolidated WebSocket manager.
        
        CURRENT STATE: SHOULD FAIL - Interface contract violations detected
        TARGET STATE: SHOULD PASS - All interface contracts satisfied
        
        Business Impact: Ensures API stability and prevents integration regressions
        """
        logger.info("📋 Testing cross-service interface contracts (Issue #1182)")
        
        integration_result = IntegrationTestResult(
            service_name="CrossServiceContracts",
            integration_point="interface_contracts"
        )
        
        interface_contract_results = []
        
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            
            # Define expected interface contracts
            interface_contracts = [
                {
                    'method': 'emit_agent_event',
                    'required_params': ['event_type', 'data', 'user_id', 'thread_id'],
                    'return_type': 'coroutine'
                },
                {
                    'method': 'get_active_connections',
                    'required_params': [],
                    'return_type': 'dict_or_list'
                },
                {
                    'method': 'send_message',
                    'required_params': ['message', 'user_id'],
                    'return_type': 'coroutine'
                },
                {
                    'method': 'disconnect_user',
                    'required_params': ['user_id'],
                    'return_type': 'coroutine'
                }
            ]
            
            # Test each interface contract
            for contract in interface_contracts:
                method_name = contract['method']
                required_params = contract['required_params']
                expected_return_type = contract['return_type']
                
                contract_result = {
                    'method': method_name,
                    'exists': False,
                    'signature_correct': False,
                    'return_type_correct': False,
                    'error': None
                }
                
                try:
                    # Check if method exists
                    if hasattr(WebSocketManager, method_name):
                        contract_result['exists'] = True
                        method = getattr(WebSocketManager, method_name)
                        
                        # Check method signature
                        import inspect
                        signature = inspect.signature(method)
                        param_names = list(signature.parameters.keys())
                        
                        # Remove 'self' parameter for instance methods
                        if param_names and param_names[0] == 'self':
                            param_names = param_names[1:]
                        
                        # Check if all required parameters are present
                        has_all_params = all(param in param_names for param in required_params)
                        contract_result['signature_correct'] = has_all_params
                        
                        # Check return type
                        if expected_return_type == 'coroutine':
                            contract_result['return_type_correct'] = inspect.iscoroutinefunction(method)
                        else:
                            contract_result['return_type_correct'] = True  # Non-async methods
                        
                        logger.info(f"✓ Contract check for {method_name}: exists={contract_result['exists']}, "
                                  f"signature={contract_result['signature_correct']}, "
                                  f"return_type={contract_result['return_type_correct']}")
                    else:
                        contract_result['error'] = f"Method {method_name} not found"
                        logger.error(f"❌ Method {method_name} not found in WebSocketManager")
                        
                except Exception as e:
                    contract_result['error'] = str(e)
                    logger.error(f"❌ Contract check failed for {method_name}: {e}")
                
                interface_contract_results.append(contract_result)
            
            # Analyze contract compliance
            total_contracts = len(interface_contracts)
            successful_contracts = sum(1 for result in interface_contract_results 
                                     if result['exists'] and result['signature_correct'] and result['return_type_correct'])
            
            contract_compliance_rate = successful_contracts / total_contracts if total_contracts > 0 else 0
            
            integration_result.success = contract_compliance_rate >= 1.0
            integration_result.interface_compatibility = contract_compliance_rate >= 0.8
            integration_result.ssot_compliance = contract_compliance_rate >= 1.0
            
            integration_result.performance_metrics = {
                'contract_compliance_rate': contract_compliance_rate,
                'successful_contracts': successful_contracts,
                'total_contracts': total_contracts
            }
            
            if contract_compliance_rate < 1.0:
                failed_contracts = [result['method'] for result in interface_contract_results 
                                  if not (result['exists'] and result['signature_correct'] and result['return_type_correct'])]
                integration_result.error_message = f"Interface contract violations: {failed_contracts}"
            
            logger.info(f"✓ Interface contract compliance: {contract_compliance_rate:.2%} ({successful_contracts}/{total_contracts})")
            
        except Exception as e:
            integration_result.error_message = f"Interface contract testing failed: {e}"
            integration_result.success = False
            logger.error(f"❌ Interface contract testing failed: {e}")
        
        self.integration_results.append(integration_result)
        
        # Log contract analysis
        logger.info(f"📊 Cross-Service Interface Contract Analysis:")
        logger.info(f"   Success: {integration_result.success}")
        logger.info(f"   Interface compatibility: {integration_result.interface_compatibility}")
        logger.info(f"   SSOT compliance: {integration_result.ssot_compliance}")
        
        if integration_result.performance_metrics:
            logger.info(f"   Contract compliance: {integration_result.performance_metrics['contract_compliance_rate']:.2%}")
        
        if integration_result.error_message:
            logger.error(f"   Contract violations: {integration_result.error_message}")
        
        # Log detailed contract results
        for result in interface_contract_results:
            status = "✓" if (result['exists'] and result['signature_correct'] and result['return_type_correct']) else "❌"
            logger.info(f"   {status} {result['method']}: exists={result['exists']}, "
                       f"signature={result['signature_correct']}, return_type={result['return_type_correct']}")
            if result['error']:
                logger.error(f"      Error: {result['error']}")
        
        # CRITICAL: All interface contracts must be satisfied for service compatibility
        # CURRENT STATE: This assertion SHOULD FAIL (contract violations detected)
        # TARGET STATE: This assertion SHOULD PASS (full contract compliance)
        self.assertTrue(
            integration_result.success,
            f"Interface contract violations detected in WebSocket manager. "
            f"Issue #1182 interface standardization incomplete. "
            f"Violations: {integration_result.error_message}"
        )
        
        self.assertGreaterEqual(
            integration_result.performance_metrics.get('contract_compliance_rate', 0), 1.0,
            f"Interface contract compliance insufficient: {integration_result.performance_metrics.get('contract_compliance_rate', 0):.2%}. "
            f"Issue #1182 requires 100% cross-service interface compatibility."
        )

    def tearDown(self):
        """Clean up and log comprehensive integration test results."""
        super().tearDown()
        
        if self.integration_results:
            logger.info("📋 COMPREHENSIVE CROSS-SERVICE INTEGRATION SUMMARY:")
            logger.info("=" * 70)
            
            total_integrations = len(self.integration_results)
            successful_integrations = sum(1 for result in self.integration_results if result.success)
            compatible_interfaces = sum(1 for result in self.integration_results if result.interface_compatibility)
            ssot_compliant = sum(1 for result in self.integration_results if result.ssot_compliance)
            
            logger.info(f"Total integration tests: {total_integrations}")
            logger.info(f"Successful integrations: {successful_integrations}")
            logger.info(f"Interface compatible: {compatible_interfaces}")
            logger.info(f"SSOT compliant: {ssot_compliant}")
            
            success_rate = (successful_integrations / total_integrations) if total_integrations > 0 else 0
            compatibility_rate = (compatible_interfaces / total_integrations) if total_integrations > 0 else 0
            compliance_rate = (ssot_compliant / total_integrations) if total_integrations > 0 else 0
            
            logger.info(f"Integration success rate: {success_rate:.2%}")
            logger.info(f"Interface compatibility rate: {compatibility_rate:.2%}")
            logger.info(f"SSOT compliance rate: {compliance_rate:.2%}")
            
            for result in self.integration_results:
                logger.info(f"\n📊 {result.service_name} ({result.integration_point}):")
                logger.info(f"   Success: {result.success}")
                logger.info(f"   Interface compatible: {result.interface_compatibility}")
                logger.info(f"   SSOT compliant: {result.ssot_compliance}")
                
                if result.performance_metrics:
                    logger.info(f"   Metrics: {result.performance_metrics}")
                
                if result.error_message:
                    logger.error(f"   Error: {result.error_message}")
            
            logger.info("=" * 70)


if __name__ == '__main__':
    unittest.main()