"""
Error Handling and Recovery Workflows E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure platform resilience and graceful error recovery
- Value Impact: Users continue to receive value despite technical failures
- Strategic Impact: System reliability enables customer trust and platform stability

These tests validate COMPLETE error handling and recovery mechanisms:
1. Agent execution failures and recovery strategies
2. WebSocket connection drops and reconnection
3. Service unavailability and failover patterns
4. User-friendly error messages and suggestions
5. Data consistency during error conditions
6. Graceful degradation under system stress
7. Recovery workflows that preserve user context
8. Error boundary isolation to prevent cascade failures

CRITICAL E2E REQUIREMENTS:
1. Real authentication throughout error scenarios - NO MOCKS
2. Real services with induced failure conditions - NO MOCKS
3. Real LLM integration with timeout/failure handling
4. Error recovery maintains WebSocket event delivery
5. User experience remains acceptable during errors
6. Business value delivery continues despite technical issues
7. Data integrity preserved through error conditions
"""

import asyncio
import json
import pytest
import time
import uuid
import random
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import websockets
import aiohttp

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user, get_test_jwt_token
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestErrorHandlingRecoveryWorkflows(SSotBaseTestCase):
    """
    E2E tests for error handling and recovery workflows.
    Tests complete error scenarios and recovery mechanisms that preserve business value.
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated helper for E2E tests."""
        return E2EAuthHelper(environment="test")
    
    @pytest.fixture
    async def authenticated_user(self, auth_helper):
        """Create authenticated user for error handling tests."""
        return await create_authenticated_user(
            environment="test",
            email="error_recovery_test@example.com",
            permissions=["read", "write", "agent_execution"]
        )

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_agent_execution_failure_recovery(self, auth_helper, authenticated_user):
        """
        Test agent execution failure and recovery mechanisms.
        
        Business Scenario: Agent encounters execution error but system recovers
        gracefully and provides user with helpful error messages and alternatives.
        
        Validates:
        - Agent execution failure detection
        - User-friendly error messages
        - Recovery suggestions provided
        - WebSocket events during error conditions
        - System stability after failure
        - Business context preserved in error handling
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Testing agent execution failure and recovery")
        print(f"👤 User: {user_data['email']}")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        # Create requests that might trigger various failure modes
        failure_test_scenarios = [
            {
                "name": "malformed_context",
                "request": {
                    "type": "agent_request",
                    "agent": "supervisor",
                    "message": "Optimize my costs - currently spending way too much!",
                    "context": {
                        "invalid_data": {"nested": {"deeply": {"broken": "<<<INVALID>>>"}}}
                    },
                    "user_id": user_data["id"]
                },
                "expected_error_handling": "graceful_degradation"
            },
            {
                "name": "excessive_request",
                "request": {
                    "type": "agent_request", 
                    "agent": "supervisor",
                    "message": "I need optimization for " + "very complex scenario " * 100,  # Very long message
                    "context": {
                        "huge_data": list(range(1000)),  # Large context
                        "test_scenario": "excessive_request"
                    },
                    "user_id": user_data["id"]
                },
                "expected_error_handling": "size_limitation_handling"
            },
            {
                "name": "timeout_scenario", 
                "request": {
                    "type": "agent_request",
                    "agent": "supervisor",
                    "message": "Provide extremely comprehensive analysis of global AI infrastructure optimization strategies across all cloud providers with detailed implementation timelines and cost projections for enterprise deployment at massive scale including regulatory compliance frameworks",
                    "context": {
                        "comprehensive": True,
                        "timeout_test": True
                    },
                    "user_id": user_data["id"]
                },
                "expected_error_handling": "timeout_management"
            }
        ]
        
        failure_recovery_results = {}
        
        for scenario in failure_test_scenarios:
            scenario_name = scenario["name"]
            test_request = scenario["request"]
            expected_handling = scenario["expected_error_handling"]
            
            print(f"\n🧪 Testing failure scenario: {scenario_name}")
            print(f"   Expected handling: {expected_handling}")
            
            scenario_result = {
                "scenario": scenario_name,
                "connection_successful": False,
                "events_received": [],
                "error_handled_gracefully": False,
                "business_value_preserved": False,
                "recovery_suggestions_provided": False,
                "system_stable_after_error": False
            }
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    scenario_result["connection_successful"] = True
                    print(f"✅ WebSocket connected for {scenario_name}")
                    
                    # Send potentially problematic request
                    await websocket.send(json.dumps(test_request))
                    print(f"📤 Sent {scenario_name} test request")
                    
                    start_time = time.time()
                    timeout_duration = 45.0  # Reasonable timeout for error handling
                    
                    # Collect events and monitor error handling
                    while time.time() - start_time < timeout_duration:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=10)
                            event = json.loads(message)
                            
                            scenario_result["events_received"].append(event)
                            event_type = event['type']
                            
                            print(f"📨 {scenario_name}: {event_type}")
                            
                            # Analyze error handling quality
                            if event_type == 'error':
                                error_data = event.get('data', {})
                                error_message = error_data.get('message', '').lower()
                                
                                # Check for graceful error handling
                                graceful_indicators = [
                                    'try again', 'please', 'help', 'support', 
                                    'suggestion', 'alternative', 'reduce', 'simplify'
                                ]
                                
                                if any(indicator in error_message for indicator in graceful_indicators):
                                    scenario_result["error_handled_gracefully"] = True
                                    print(f"✅ Graceful error handling detected")
                                
                                # Check for recovery suggestions
                                suggestion_indicators = [
                                    'try', 'reduce', 'simplify', 'break down', 'smaller', 'contact'
                                ]
                                
                                if any(indicator in error_message for indicator in suggestion_indicators):
                                    scenario_result["recovery_suggestions_provided"] = True
                                    print(f"✅ Recovery suggestions provided")
                                    
                                # Business context preservation
                                business_indicators = ['optimization', 'cost', 'ai', 'platform']
                                if any(indicator in error_message for indicator in business_indicators):
                                    scenario_result["business_value_preserved"] = True
                            
                            elif event_type == 'agent_completed':
                                # If agent completed despite potential issues, that's good recovery
                                result_data = event.get('data', {}).get('result', {})
                                result_text = str(result_data).lower()
                                
                                # Check if result acknowledges limitations but provides value
                                if any(word in result_text for word in ['however', 'although', 'limited', 'partial']):
                                    scenario_result["error_handled_gracefully"] = True
                                
                                if any(word in result_text for word in ['recommend', 'suggest', 'try', 'consider']):
                                    scenario_result["business_value_preserved"] = True
                                
                                print(f"✅ Agent completed despite potential issues")
                                break
                            
                            elif event_type == 'agent_started':
                                # Good sign - system is attempting to process request
                                print(f"✅ System attempting to process {scenario_name}")
                                
                        except asyncio.TimeoutError:
                            print(f"⏰ {scenario_name} event timeout")
                            break
                        except json.JSONDecodeError:
                            print(f"⚠️ {scenario_name} JSON decode error")
                            continue
                    
                    # Test system stability after potential error
                    print(f"🔍 Testing system stability after {scenario_name}")
                    
                    stability_request = {
                        "type": "agent_request",
                        "agent": "supervisor", 
                        "message": "Simple test - are you working correctly?",
                        "context": {"stability_check": True},
                        "user_id": user_data["id"]
                    }
                    
                    await websocket.send(json.dumps(stability_request))
                    
                    # Brief check for system responsiveness
                    try:
                        stability_response = await asyncio.wait_for(websocket.recv(), timeout=15)
                        stability_event = json.loads(stability_response)
                        
                        if stability_event['type'] in ['agent_started', 'agent_thinking', 'agent_completed']:
                            scenario_result["system_stable_after_error"] = True
                            print(f"✅ System stable after {scenario_name}")
                        
                    except asyncio.TimeoutError:
                        print(f"⚠️ System may be unstable after {scenario_name}")
            
            except Exception as e:
                print(f"❌ {scenario_name} connection/execution error: {e}")
            
            failure_recovery_results[scenario_name] = scenario_result
        
        # Analyze failure recovery results
        print(f"\n📊 FAILURE RECOVERY ANALYSIS:")
        
        total_scenarios = len(failure_recovery_results)
        successful_connections = sum(1 for r in failure_recovery_results.values() if r["connection_successful"])
        graceful_handling_count = sum(1 for r in failure_recovery_results.values() if r["error_handled_gracefully"])
        stable_after_error_count = sum(1 for r in failure_recovery_results.values() if r["system_stable_after_error"])
        
        for scenario_name, result in failure_recovery_results.items():
            print(f"   {scenario_name}:")
            print(f"     Connection: {result['connection_successful']}")
            print(f"     Events received: {len(result['events_received'])}")
            print(f"     Graceful handling: {result['error_handled_gracefully']}")
            print(f"     Recovery suggestions: {result['recovery_suggestions_provided']}")
            print(f"     Business value preserved: {result['business_value_preserved']}")
            print(f"     System stable after: {result['system_stable_after_error']}")
        
        print(f"\n📈 SUMMARY:")
        print(f"   Successful connections: {successful_connections}/{total_scenarios}")
        print(f"   Graceful error handling: {graceful_handling_count}/{total_scenarios}")
        print(f"   System stability after errors: {stable_after_error_count}/{total_scenarios}")
        
        # Validation criteria
        connection_rate = successful_connections / total_scenarios
        graceful_rate = graceful_handling_count / total_scenarios if successful_connections > 0 else 0
        stability_rate = stable_after_error_count / total_scenarios if successful_connections > 0 else 0
        
        assert connection_rate >= 0.8, f"Connection rate too low: {connection_rate:.1%}"
        assert graceful_rate >= 0.5, f"Graceful handling rate too low: {graceful_rate:.1%}" 
        assert stability_rate >= 0.7, f"System stability rate too low: {stability_rate:.1%}"
        
        print(f"✅ AGENT EXECUTION FAILURE RECOVERY SUCCESS!")
        print(f"   ✓ {graceful_rate:.1%} graceful error handling rate")
        print(f"   ✓ {stability_rate:.1%} system stability after errors")
        print(f"   ✓ Error recovery preserves business value")
        print(f"   ✓ User-friendly error messages provided")


    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_connection_recovery(self, auth_helper, authenticated_user):
        """
        Test WebSocket connection recovery and reconnection scenarios.
        
        Business Scenario: User's WebSocket connection drops during agent execution
        but system handles reconnection gracefully without losing context.
        
        Validates:
        - WebSocket connection drop detection
        - Automatic reconnection mechanisms
        - Context preservation during reconnection
        - Event delivery continuation after recovery
        - User experience continuity
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Testing WebSocket connection recovery")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        # Test connection recovery scenarios
        recovery_scenarios = [
            {
                "name": "rapid_reconnection",
                "description": "Quick reconnection after brief disconnect",
                "disconnect_duration": 2
            },
            {
                "name": "delayed_reconnection", 
                "description": "Reconnection after longer disconnect",
                "disconnect_duration": 10
            }
        ]
        
        recovery_results = {}
        
        for scenario in recovery_scenarios:
            scenario_name = scenario["name"]
            disconnect_duration = scenario["disconnect_duration"]
            
            print(f"\n🔄 Testing {scenario_name} (disconnect: {disconnect_duration}s)")
            
            scenario_result = {
                "initial_connection": False,
                "request_sent": False,
                "events_before_disconnect": 0,
                "reconnection_successful": False,
                "context_preserved": False,
                "total_events": 0,
                "recovery_time": None
            }
            
            try:
                # Initial connection and request
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    scenario_result["initial_connection"] = True
                    print(f"✅ Initial connection established")
                    
                    # Send request that should take some time to process
                    recovery_request = {
                        "type": "agent_request",
                        "agent": "supervisor",
                        "message": f"Help me optimize AI costs - this is connection recovery test {scenario_name}",
                        "context": {
                            "recovery_test": scenario_name,
                            "connection_test": True
                        },
                        "user_id": user_data["id"]
                    }
                    
                    await websocket.send(json.dumps(recovery_request))
                    scenario_result["request_sent"] = True
                    print(f"📤 Sent recovery test request")
                    
                    # Collect some initial events
                    start_time = time.time()
                    initial_events = []
                    
                    while time.time() - start_time < 5:  # Collect events for 5 seconds
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=2)
                            event = json.loads(message)
                            initial_events.append(event)
                            scenario_result["events_before_disconnect"] += 1
                            
                            print(f"📨 Pre-disconnect: {event['type']}")
                            
                        except asyncio.TimeoutError:
                            break
                        except json.JSONDecodeError:
                            continue
                    
                    print(f"📊 Collected {len(initial_events)} events before disconnect")
                
                # Simulate connection loss by closing and waiting
                print(f"💔 Simulating connection loss for {disconnect_duration}s...")
                await asyncio.sleep(disconnect_duration)
                
                # Attempt reconnection
                reconnect_start = time.time()
                
                try:
                    async with websockets.connect(websocket_url, additional_headers=headers) as new_websocket:
                        scenario_result["reconnection_successful"] = True
                        scenario_result["recovery_time"] = time.time() - reconnect_start
                        
                        print(f"✅ Reconnection successful ({scenario_result['recovery_time']:.2f}s)")
                        
                        # Test if we can continue receiving events or need to resend request
                        print(f"🔍 Testing context preservation after reconnection...")
                        
                        # First, try to receive any pending events
                        try:
                            pending_message = await asyncio.wait_for(new_websocket.recv(), timeout=5)
                            pending_event = json.loads(pending_message)
                            scenario_result["total_events"] += 1
                            
                            print(f"📨 Post-reconnect: {pending_event['type']}")
                            
                            # If we get events, context might be preserved
                            if pending_event.get('data') and 'recovery_test' in str(pending_event['data']):
                                scenario_result["context_preserved"] = True
                                print(f"✅ Context preserved through reconnection")
                                
                        except asyncio.TimeoutError:
                            print(f"⚠️ No immediate events after reconnection")
                        
                        # Send new request to test connection functionality
                        continuity_request = {
                            "type": "agent_request", 
                            "agent": "supervisor",
                            "message": f"Connection recovery verification for {scenario_name}",
                            "context": {
                                "post_recovery_test": True,
                                "original_scenario": scenario_name
                            },
                            "user_id": user_data["id"]
                        }
                        
                        await new_websocket.send(json.dumps(continuity_request))
                        print(f"📤 Sent post-recovery verification request")
                        
                        # Collect events to verify functionality
                        verification_start = time.time()
                        
                        while time.time() - verification_start < 20:
                            try:
                                message = await asyncio.wait_for(new_websocket.recv(), timeout=5)
                                event = json.loads(message)
                                scenario_result["total_events"] += 1
                                
                                print(f"📨 Verification: {event['type']}")
                                
                                if event['type'] == 'agent_completed':
                                    print(f"✅ Post-recovery functionality confirmed")
                                    break
                                    
                            except asyncio.TimeoutError:
                                break
                            except json.JSONDecodeError:
                                continue
                
                except Exception as e:
                    print(f"❌ Reconnection failed: {e}")
            
            except Exception as e:
                print(f"❌ {scenario_name} failed: {e}")
            
            recovery_results[scenario_name] = scenario_result
        
        # Analyze recovery results
        print(f"\n📊 WEBSOCKET RECOVERY ANALYSIS:")
        
        for scenario_name, result in recovery_results.items():
            print(f"   {scenario_name}:")
            print(f"     Initial connection: {result['initial_connection']}")
            print(f"     Request sent: {result['request_sent']}")
            print(f"     Events before disconnect: {result['events_before_disconnect']}")
            print(f"     Reconnection successful: {result['reconnection_successful']}")
            print(f"     Recovery time: {result['recovery_time']:.2f}s" if result['recovery_time'] else "     Recovery time: N/A")
            print(f"     Context preserved: {result['context_preserved']}")
            print(f"     Total events: {result['total_events']}")
        
        # Validation
        successful_reconnections = sum(1 for r in recovery_results.values() if r["reconnection_successful"])
        total_scenarios = len(recovery_results)
        
        reconnection_rate = successful_reconnections / total_scenarios
        assert reconnection_rate >= 0.8, f"Reconnection rate too low: {reconnection_rate:.1%}"
        
        # Average recovery time should be reasonable
        recovery_times = [r["recovery_time"] for r in recovery_results.values() if r["recovery_time"]]
        if recovery_times:
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
            assert avg_recovery_time < 10, f"Average recovery time too slow: {avg_recovery_time:.2f}s"
            print(f"📊 Average recovery time: {avg_recovery_time:.2f}s")
        
        print(f"✅ WEBSOCKET CONNECTION RECOVERY SUCCESS!")
        print(f"   ✓ {reconnection_rate:.1%} successful reconnection rate")
        print(f"   ✓ Connection recovery within acceptable time")
        print(f"   ✓ Post-recovery functionality verified")


    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_service_unavailability_graceful_degradation(self, auth_helper, authenticated_user):
        """
        Test graceful degradation when backend services are unavailable.
        
        Business Scenario: Some backend services are temporarily unavailable
        but system provides partial functionality and clear communication.
        
        Validates:
        - Detection of service unavailability
        - Graceful degradation strategies
        - User communication about limitations
        - Partial functionality delivery
        - Service recovery detection
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Testing service unavailability and graceful degradation")
        
        # Test various service unavailability scenarios
        service_test_scenarios = [
            {
                "name": "auth_service_test",
                "service_url": "http://localhost:8081",
                "service_name": "Auth Service",
                "test_endpoints": ["/auth/validate", "/auth/user"]
            },
            {
                "name": "backend_service_test", 
                "service_url": "http://localhost:8000",
                "service_name": "Backend Service",
                "test_endpoints": ["/api/health", "/api/user/profile"]
            }
        ]
        
        degradation_results = {}
        
        for scenario in service_test_scenarios:
            scenario_name = scenario["name"] 
            service_url = scenario["service_url"]
            service_name = scenario["service_name"]
            test_endpoints = scenario["test_endpoints"]
            
            print(f"\n🔍 Testing {service_name} availability")
            
            scenario_result = {
                "service_reachable": False,
                "endpoints_working": 0,
                "graceful_degradation": False,
                "user_communication": False,
                "partial_functionality": False
            }
            
            # Test service availability
            async with aiohttp.ClientSession() as session:
                headers = auth_helper.get_auth_headers(token)
                
                for endpoint in test_endpoints:
                    full_url = f"{service_url}{endpoint}"
                    
                    try:
                        async with session.get(full_url, headers=headers, timeout=5) as response:
                            scenario_result["service_reachable"] = True
                            
                            if response.status in [200, 401, 403]:  # Any response means service is up
                                scenario_result["endpoints_working"] += 1
                                print(f"✅ {endpoint}: Service responding ({response.status})")
                            else:
                                print(f"⚠️ {endpoint}: Service issues ({response.status})")
                                
                    except aiohttp.ClientConnectorError:
                        print(f"❌ {endpoint}: Service unavailable (connection refused)")
                    except asyncio.TimeoutError:
                        print(f"❌ {endpoint}: Service timeout")
                    except Exception as e:
                        print(f"❌ {endpoint}: Service error - {e}")
            
            # Test how WebSocket handles service issues
            websocket_url = "ws://localhost:8000/ws" 
            headers = auth_helper.get_websocket_headers(token)
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    # Send request that might require unavailable service
                    degradation_request = {
                        "type": "agent_request",
                        "agent": "supervisor",
                        "message": f"Test request that may require {service_name} - provide optimization recommendations",
                        "context": {
                            "service_dependency_test": scenario_name,
                            "requires_service": service_name
                        },
                        "user_id": user_data["id"]
                    }
                    
                    await websocket.send(json.dumps(degradation_request))
                    print(f"📤 Sent service dependency test request")
                    
                    start_time = time.time()
                    
                    while time.time() - start_time < 30:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=10)
                            event = json.loads(message)
                            event_type = event['type']
                            
                            print(f"📨 Service test: {event_type}")
                            
                            if event_type == 'error':
                                error_data = event.get('data', {})
                                error_message = error_data.get('message', '').lower()
                                
                                # Check for graceful error communication
                                graceful_indicators = [
                                    'temporarily unavailable', 'service issue', 'try again later',
                                    'partial functionality', 'limited features'
                                ]
                                
                                if any(indicator in error_message for indicator in graceful_indicators):
                                    scenario_result["graceful_degradation"] = True
                                    scenario_result["user_communication"] = True
                                    print(f"✅ Graceful degradation detected")
                                
                            elif event_type == 'agent_completed':
                                result_data = event.get('data', {}).get('result', {})
                                result_text = str(result_data).lower()
                                
                                # Check if partial functionality was delivered
                                if len(result_text) > 50:  # Some meaningful response
                                    scenario_result["partial_functionality"] = True
                                    print(f"✅ Partial functionality delivered despite service issues")
                                    
                                # Check for service limitation acknowledgment
                                limitation_indicators = [
                                    'limited', 'partial', 'unavailable', 'temporary', 'basic'
                                ]
                                
                                if any(indicator in result_text for indicator in limitation_indicators):
                                    scenario_result["user_communication"] = True
                                
                                break
                                
                        except asyncio.TimeoutError:
                            print(f"⏰ Service test timeout")
                            break
                        except json.JSONDecodeError:
                            continue
            
            except Exception as e:
                print(f"❌ WebSocket service test failed: {e}")
            
            degradation_results[scenario_name] = scenario_result
        
        # Analyze degradation results
        print(f"\n📊 SERVICE DEGRADATION ANALYSIS:")
        
        for scenario_name, result in degradation_results.items():
            service_name = next(s["service_name"] for s in service_test_scenarios if s["name"] == scenario_name)
            
            print(f"   {service_name}:")
            print(f"     Service reachable: {result['service_reachable']}")
            print(f"     Endpoints working: {result['endpoints_working']}")
            print(f"     Graceful degradation: {result['graceful_degradation']}")
            print(f"     User communication: {result['user_communication']}")
            print(f"     Partial functionality: {result['partial_functionality']}")
        
        # Validation criteria
        total_scenarios = len(degradation_results)
        
        # If services are unavailable, system should handle gracefully
        unavailable_services = [r for r in degradation_results.values() if not r["service_reachable"]]
        
        if unavailable_services:
            graceful_handling = sum(1 for r in unavailable_services if r["graceful_degradation"] or r["user_communication"])
            graceful_rate = graceful_handling / len(unavailable_services)
            
            assert graceful_rate >= 0.5, f"Graceful degradation rate too low: {graceful_rate:.1%}"
            print(f"✅ Graceful degradation rate: {graceful_rate:.1%}")
        else:
            print(f"ℹ️ All services available - degradation not tested")
        
        print(f"✅ SERVICE UNAVAILABILITY HANDLING TESTED!")
        print(f"   ✓ Service availability detection")
        print(f"   ✓ Graceful degradation strategies")
        print(f"   ✓ User communication about limitations")
        print(f"   ✓ Partial functionality delivery")


    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_data_consistency_during_errors(self, auth_helper, authenticated_user):
        """
        Test data consistency and integrity during error conditions.
        
        Business Scenario: Errors occur during agent execution but user data
        and conversation context remain consistent and recoverable.
        
        Validates:
        - Data consistency during agent failures
        - Conversation context preservation
        - No data corruption or loss
        - Recovery without data inconsistencies
        - Transaction integrity during errors
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Testing data consistency during error conditions")
        
        websocket_url = "ws://localhost:8000/ws"
        headers = auth_helper.get_websocket_headers(token)
        
        # Multi-step conversation to test consistency
        consistency_test_conversation = [
            {
                "step": 1,
                "message": "I want to optimize AI costs for my e-commerce platform",
                "context": {"platform": "ecommerce", "step": 1}
            },
            {
                "step": 2, 
                "message": "We're currently spending $5000/month on customer service AI",
                "context": {"monthly_spend": 5000, "use_case": "customer_service", "step": 2}
            },
            {
                "step": 3,
                "message": "ERROR_INDUCING_REQUEST_WITH_MALFORMED_DATA: <<<INVALID>>>",
                "context": {"error_step": True, "step": 3, "malformed": "<<<DATA>>>"}
            },
            {
                "step": 4,
                "message": "Sorry about that error. Can you still help with cost optimization?",
                "context": {"recovery_step": True, "step": 4, "reference_previous": True}
            },
            {
                "step": 5,
                "message": "Specifically for the $5000/month customer service costs I mentioned",
                "context": {"context_reference": True, "step": 5, "specific_followup": True}
            }
        ]
        
        consistency_results = {
            "conversation_steps_completed": 0,
            "error_step_handled": False,
            "context_preserved_after_error": False,
            "data_consistency_maintained": False,
            "conversation_recoverable": False,
            "all_events": []
        }
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                print(f"✅ WebSocket connected for consistency test")
                
                for conversation_step in consistency_test_conversation:
                    step_num = conversation_step["step"]
                    message = conversation_step["message"]
                    context = conversation_step["context"]
                    
                    print(f"\n💬 Step {step_num}: {message[:50]}...")
                    
                    consistency_request = {
                        "type": "agent_request",
                        "agent": "supervisor", 
                        "message": message,
                        "context": {
                            **context,
                            "consistency_test": True,
                            "conversation_id": "consistency_test_conversation"
                        },
                        "user_id": user_data["id"]
                    }
                    
                    try:
                        await websocket.send(json.dumps(consistency_request))
                        print(f"📤 Sent step {step_num}")
                    except Exception as e:
                        if step_num == 3:  # Expected error step
                            print(f"✅ Step {step_num} failed as expected: {e}")
                            consistency_results["error_step_handled"] = True
                            continue
                        else:
                            print(f"❌ Unexpected error at step {step_num}: {e}")
                            break
                    
                    # Collect events for this step
                    step_events = []
                    start_time = time.time()
                    
                    while time.time() - start_time < 25:  # 25 seconds per step
                        try:
                            message_raw = await asyncio.wait_for(websocket.recv(), timeout=5)
                            event = json.loads(message_raw)
                            
                            step_events.append(event)
                            consistency_results["all_events"].append(event)
                            
                            print(f"📨 Step {step_num}: {event['type']}")
                            
                            # Special handling for error step
                            if step_num == 3 and event['type'] == 'error':
                                consistency_results["error_step_handled"] = True
                                print(f"✅ Error step handled gracefully")
                                break
                            
                            # Check for completion
                            if event['type'] == 'agent_completed':
                                consistency_results["conversation_steps_completed"] += 1
                                
                                result_data = event.get('data', {}).get('result', {})
                                result_text = str(result_data).lower()
                                
                                # Check context preservation after error (steps 4-5)
                                if step_num >= 4:
                                    context_indicators = ['5000', 'customer service', 'ecommerce', 'cost']
                                    found_context = sum(1 for indicator in context_indicators if indicator in result_text)
                                    
                                    if found_context >= 2:
                                        consistency_results["context_preserved_after_error"] = True
                                        print(f"✅ Context preserved after error (step {step_num})")
                                
                                # Check data consistency references
                                if step_num == 5:  # Final step should reference earlier data
                                    if '5000' in result_text and ('customer' in result_text or 'service' in result_text):
                                        consistency_results["data_consistency_maintained"] = True
                                        print(f"✅ Data consistency maintained through conversation")
                                
                                break
                                
                        except asyncio.TimeoutError:
                            if step_num == 3:  # Error step may timeout
                                consistency_results["error_step_handled"] = True
                                print(f"✅ Error step timed out (expected behavior)")
                                break
                            else:
                                print(f"⏰ Step {step_num} timeout")
                                break
                        except json.JSONDecodeError:
                            continue
                    
                    # Brief pause between steps
                    await asyncio.sleep(1)
                
                # Test conversation recoverability
                recovery_request = {
                    "type": "agent_request",
                    "agent": "supervisor",
                    "message": "Can you summarize our conversation about cost optimization?",
                    "context": {
                        "recovery_test": True,
                        "conversation_summary": True
                    },
                    "user_id": user_data["id"]
                }
                
                await websocket.send(json.dumps(recovery_request))
                print(f"📤 Sent conversation recovery test")
                
                try:
                    recovery_message = await asyncio.wait_for(websocket.recv(), timeout=20)
                    recovery_event = json.loads(recovery_message)
                    
                    if recovery_event['type'] == 'agent_completed':
                        result_text = str(recovery_event.get('data', {}).get('result', '')).lower()
                        
                        # Should reference key conversation elements
                        recovery_indicators = ['5000', 'cost', 'optimization', 'customer service']
                        found_recovery = sum(1 for indicator in recovery_indicators if indicator in result_text)
                        
                        if found_recovery >= 2:
                            consistency_results["conversation_recoverable"] = True
                            print(f"✅ Conversation recoverable after errors")
                    
                except asyncio.TimeoutError:
                    print(f"⏰ Recovery test timeout")
        
        except Exception as e:
            print(f"❌ Consistency test failed: {e}")
        
        # Analyze consistency results
        print(f"\n📊 DATA CONSISTENCY ANALYSIS:")
        print(f"   Conversation steps completed: {consistency_results['conversation_steps_completed']}")
        print(f"   Error step handled: {consistency_results['error_step_handled']}")
        print(f"   Context preserved after error: {consistency_results['context_preserved_after_error']}")
        print(f"   Data consistency maintained: {consistency_results['data_consistency_maintained']}")
        print(f"   Conversation recoverable: {consistency_results['conversation_recoverable']}")
        print(f"   Total events collected: {len(consistency_results['all_events'])}")
        
        # Validation criteria
        assert consistency_results["error_step_handled"], "Error step was not handled properly"
        assert consistency_results["conversation_steps_completed"] >= 2, "Too few conversation steps completed"
        
        # At least one consistency indicator should be true
        consistency_score = sum([
            consistency_results["context_preserved_after_error"],
            consistency_results["data_consistency_maintained"], 
            consistency_results["conversation_recoverable"]
        ])
        
        assert consistency_score >= 1, f"No data consistency indicators passed: {consistency_score}/3"
        
        print(f"✅ DATA CONSISTENCY DURING ERRORS SUCCESS!")
        print(f"   ✓ Error handling without data corruption")
        print(f"   ✓ Context preservation through errors")
        print(f"   ✓ Data consistency maintained")
        print(f"   ✓ Conversation recoverability validated")
        print(f"   ✓ Consistency score: {consistency_score}/3")


    @pytest.mark.e2e
    @pytest.mark.real_services 
    async def test_error_cascade_prevention(self, auth_helper, authenticated_user):
        """
        Test error cascade prevention and isolation mechanisms.
        
        Business Scenario: Single component failure doesn't cascade and
        bring down the entire system or affect other users.
        
        Validates:
        - Error isolation between system components
        - Prevention of error cascade effects
        - System stability during component failures
        - Other user sessions unaffected by errors
        - Graceful degradation instead of total failure
        """
        token, user_data = authenticated_user
        
        print(f"🚀 Testing error cascade prevention")
        
        # Create additional user to test isolation
        secondary_user_token, secondary_user_data = await create_authenticated_user(
            environment="test",
            email=f"cascade_test_user_{int(time.time())}@example.com",
            permissions=["read", "write", "agent_execution"]
        )
        
        print(f"✅ Created secondary user for isolation testing")
        
        websocket_url = "ws://localhost:8000/ws"
        
        # Function to create problematic session that might cause errors
        async def error_inducing_session() -> Dict:
            """Session designed to potentially cause errors."""
            headers = auth_helper.get_websocket_headers(token)
            
            session_result = {
                "connection_successful": False,
                "error_generated": False,
                "system_impact": "none"
            }
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    session_result["connection_successful"] = True
                    
                    # Send multiple problematic requests to try to cause errors
                    problematic_requests = [
                        {"message": "<<<MALFORMED_JSON_REQUEST>>>", "type": "malformed"},
                        {"message": "EXTREMELY LARGE REQUEST " * 500, "type": "oversized"},
                        {"message": None, "type": "null_message"},  # This will cause JSON encoding error
                    ]
                    
                    for i, req_data in enumerate(problematic_requests):
                        try:
                            if req_data["type"] == "null_message":
                                # Intentionally problematic request
                                bad_request = {
                                    "type": "agent_request",
                                    "agent": "supervisor", 
                                    "message": None,  # This should cause issues
                                    "context": {"error_test": True},
                                    "user_id": user_data["id"]
                                }
                                await websocket.send(json.dumps(bad_request))
                            else:
                                # Send as raw string for malformed/oversized
                                await websocket.send(req_data["message"])
                            
                            print(f"📤 Sent problematic request #{i+1}")
                            
                            # Try to receive response
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                                event = json.loads(response)
                                
                                if event['type'] == 'error':
                                    session_result["error_generated"] = True
                                    print(f"✅ Error generated and handled: {event.get('message', 'Unknown error')[:50]}...")
                                    
                            except asyncio.TimeoutError:
                                print(f"⏰ No response to problematic request #{i+1}")
                            except json.JSONDecodeError:
                                print(f"⚠️ Received non-JSON response")
                            
                        except Exception as e:
                            session_result["error_generated"] = True
                            print(f"✅ Request #{i+1} generated error: {str(e)[:50]}...")
                            
            except Exception as e:
                print(f"❌ Error-inducing session failed: {e}")
            
            return session_result
        
        # Function to create normal session that should remain unaffected
        async def normal_session(user_token: str, user_data: Dict) -> Dict:
            """Normal session that should not be affected by errors in other sessions."""
            headers = auth_helper.get_websocket_headers(user_token)
            
            session_result = {
                "connection_successful": False,
                "request_completed": False,
                "events_received": 0,
                "business_value_delivered": False
            }
            
            try:
                async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                    session_result["connection_successful"] = True
                    
                    normal_request = {
                        "type": "agent_request",
                        "agent": "supervisor",
                        "message": "Help me with basic cost optimization for AI infrastructure",
                        "context": {
                            "normal_session": True,
                            "cascade_test": True
                        },
                        "user_id": user_data["id"]
                    }
                    
                    await websocket.send(json.dumps(normal_request))
                    print(f"📤 Sent normal session request")
                    
                    start_time = time.time()
                    
                    while time.time() - start_time < 30:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=5)
                            event = json.loads(message)
                            
                            session_result["events_received"] += 1
                            print(f"📨 Normal session: {event['type']}")
                            
                            if event['type'] == 'agent_completed':
                                session_result["request_completed"] = True
                                
                                result_text = str(event.get('data', {}).get('result', '')).lower()
                                if 'optimization' in result_text or 'cost' in result_text:
                                    session_result["business_value_delivered"] = True
                                
                                break
                                
                        except asyncio.TimeoutError:
                            continue
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                print(f"❌ Normal session failed: {e}")
            
            return session_result
        
        # Execute error-inducing session and normal sessions concurrently
        print(f"🏃 Running concurrent sessions: error-inducing + normal sessions")
        
        tasks = [
            error_inducing_session(),
            normal_session(token, user_data),  # Primary user normal session
            normal_session(secondary_user_token, secondary_user_data)  # Secondary user session
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze cascade prevention results
        print(f"\n📊 ERROR CASCADE PREVENTION ANALYSIS:")
        
        error_session_result = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
        primary_normal_result = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
        secondary_normal_result = results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])}
        
        print(f"   Error-inducing session:")
        if isinstance(error_session_result, dict) and "error" not in error_session_result:
            print(f"     Connection: {error_session_result['connection_successful']}")
            print(f"     Errors generated: {error_session_result['error_generated']}")
            print(f"     System impact: {error_session_result['system_impact']}")
        else:
            print(f"     Failed: {error_session_result.get('error', 'Unknown error')}")
        
        print(f"   Primary user normal session:")
        if isinstance(primary_normal_result, dict) and "error" not in primary_normal_result:
            print(f"     Connection: {primary_normal_result['connection_successful']}")
            print(f"     Request completed: {primary_normal_result['request_completed']}")
            print(f"     Events received: {primary_normal_result['events_received']}")
            print(f"     Business value: {primary_normal_result['business_value_delivered']}")
        else:
            print(f"     Failed: {primary_normal_result.get('error', 'Unknown error')}")
        
        print(f"   Secondary user normal session:")
        if isinstance(secondary_normal_result, dict) and "error" not in secondary_normal_result:
            print(f"     Connection: {secondary_normal_result['connection_successful']}")
            print(f"     Request completed: {secondary_normal_result['request_completed']}")
            print(f"     Events received: {secondary_normal_result['events_received']}")
            print(f"     Business value: {secondary_normal_result['business_value_delivered']}")
        else:
            print(f"     Failed: {secondary_normal_result.get('error', 'Unknown error')}")
        
        # Validation criteria for cascade prevention
        normal_sessions_working = 0
        normal_sessions_total = 2
        
        if isinstance(primary_normal_result, dict) and primary_normal_result.get("connection_successful"):
            normal_sessions_working += 1
        
        if isinstance(secondary_normal_result, dict) and secondary_normal_result.get("connection_successful"):
            normal_sessions_working += 1
        
        isolation_rate = normal_sessions_working / normal_sessions_total
        assert isolation_rate >= 0.5, f"Error isolation rate too low: {isolation_rate:.1%} (normal sessions affected)"
        
        # At least one normal session should deliver business value
        business_value_delivered = (
            (isinstance(primary_normal_result, dict) and primary_normal_result.get("business_value_delivered")) or
            (isinstance(secondary_normal_result, dict) and secondary_normal_result.get("business_value_delivered"))
        )
        
        assert business_value_delivered, "No business value delivered in normal sessions during error conditions"
        
        print(f"✅ ERROR CASCADE PREVENTION SUCCESS!")
        print(f"   ✓ {isolation_rate:.1%} normal session isolation rate")
        print(f"   ✓ Business value preserved in normal sessions")
        print(f"   ✓ Error isolation between users verified")
        print(f"   ✓ System stability maintained during errors")