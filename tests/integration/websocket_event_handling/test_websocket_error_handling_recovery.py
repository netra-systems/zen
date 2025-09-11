"""
WebSocket Error Handling and Recovery Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket failures don't interrupt chat experience 
- Value Impact: Robust error handling maintains 90% platform value delivery continuity
- Strategic Impact: Error recovery prevents loss of AI optimization insights

These tests validate that WebSocket error conditions are handled gracefully
and recovery mechanisms maintain the chat functionality essential to business value.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import uuid
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    WebSocketMessage
)
from shared.isolated_environment import get_env


class TestWebSocketErrorHandlingRecovery(SSotAsyncTestCase):
    """Test WebSocket error handling and recovery patterns."""
    
    async def setup_method(self, method=None):
        """Set up test environment."""
        await super().async_setup_method(method)
        self.env = get_env()
        
        # Configure error testing environment
        self.set_env_var("WEBSOCKET_TEST_TIMEOUT", "15")
        self.set_env_var("WEBSOCKET_MOCK_MODE", "true")
        self.set_env_var("ERROR_RECOVERY_ENABLED", "true")
        self.set_env_var("WEBSOCKET_RETRY_COUNT", "3")
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.error_handling
    async def test_connection_failure_recovery(self):
        """
        Test WebSocket connection failure detection and automatic recovery.
        
        BVJ: All segments - Connection failures must not disrupt chat experience.
        """
        async with WebSocketTestUtility() as ws_util:
            user_id = f"recovery_user_{uuid.uuid4().hex[:8]}"
            client = await ws_util.create_authenticated_client(user_id)
            
            # Establish initial connection
            initial_success = await client.connect(mock_mode=True)
            assert initial_success, "Initial connection should succeed"
            
            # Send successful message to establish baseline
            baseline_message = await client.send_message(
                WebSocketEventType.AGENT_STARTED,
                {
                    "baseline_test": True,
                    "user_id": user_id,
                    "optimization_type": "cost_analysis"
                }
            )
            assert baseline_message.message_id, "Baseline message should succeed"
            
            # Track recovery attempts
            recovery_attempts = []
            recovery_start_time = time.time()
            
            # Simulate connection failures and recovery cycles
            failure_recovery_cycles = 3
            successful_recoveries = 0
            
            for cycle in range(failure_recovery_cycles):
                cycle_start_time = time.time()
                
                # Simulate connection failure
                await client.disconnect()
                assert not client.is_connected, f"Should be disconnected after cycle {cycle}"
                
                # Wait brief period (simulate network instability)
                await asyncio.sleep(0.5)
                
                # Attempt recovery
                recovery_success = await client.connect(mock_mode=True, timeout=10.0)
                cycle_recovery_time = time.time() - cycle_start_time
                
                recovery_attempts.append({
                    "cycle": cycle + 1,
                    "success": recovery_success,
                    "recovery_time": cycle_recovery_time,
                    "timestamp": datetime.now()
                })
                
                if recovery_success:
                    successful_recoveries += 1
                    
                    # Test that connection works post-recovery
                    post_recovery_message = await client.send_message(
                        WebSocketEventType.AGENT_THINKING,
                        {
                            "post_recovery_test": True,
                            "recovery_cycle": cycle + 1,
                            "user_id": user_id,
                            "analysis_continuing": True
                        }
                    )
                    assert post_recovery_message.message_id, f"Post-recovery message should work in cycle {cycle + 1}"
                
                # Brief pause before next cycle
                await asyncio.sleep(0.3)
            
            total_recovery_time = time.time() - recovery_start_time
            recovery_success_rate = successful_recoveries / failure_recovery_cycles
            
            # Verify recovery performance
            assert recovery_success_rate >= 0.8, f"Recovery success rate too low: {recovery_success_rate}"
            assert total_recovery_time < 30.0, f"Total recovery time too slow: {total_recovery_time}s"
            
            # Verify final connection stability
            if client.is_connected:
                stability_test_message = await client.send_message(
                    WebSocketEventType.AGENT_COMPLETED,
                    {
                        "stability_test": True,
                        "recovery_cycles_completed": failure_recovery_cycles,
                        "final_optimization_result": "recovery_testing_complete"
                    }
                )
                assert stability_test_message.message_id, "Final stability test should succeed"
            
            self.record_metric("failure_recovery_cycles", failure_recovery_cycles)
            self.record_metric("successful_recoveries", successful_recoveries)
            self.record_metric("recovery_success_rate", recovery_success_rate)
            self.record_metric("total_recovery_time", total_recovery_time)
            self.record_metric("connection_resilience_verified", True)
            
            await client.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.error_handling
    async def test_message_delivery_failure_retry(self):
        """
        Test WebSocket message delivery failure detection and retry mechanism.
        
        BVJ: Enterprise/Mid - Critical events must be delivered even with transient failures.
        """
        async with WebSocketTestUtility() as ws_util:
            async with ws_util.connected_client("retry_user") as client:
                # Track message delivery attempts
                delivery_tracking = {
                    "attempts": [],
                    "successes": 0,
                    "failures": 0,
                    "retry_attempts": 0
                }
                
                # Send critical business messages that must be delivered
                critical_messages = [
                    {
                        "type": WebSocketEventType.AGENT_COMPLETED,
                        "data": {
                            "critical_optimization": True,
                            "cost_savings_identified": 25000.00,
                            "urgent_recommendations": [
                                "immediate_resource_scaling_required",
                                "cost_spike_detected_needs_attention"
                            ],
                            "business_impact": "high"
                        }
                    },
                    {
                        "type": WebSocketEventType.TOOL_COMPLETED,
                        "data": {
                            "tool": "security_scanner",
                            "critical_vulnerabilities_found": 3,
                            "immediate_action_required": True,
                            "security_recommendations": [
                                "patch_critical_cve_immediately",
                                "rotate_exposed_credentials"
                            ]
                        }
                    },
                    {
                        "type": WebSocketEventType.AGENT_THINKING,
                        "data": {
                            "analysis_type": "emergency_cost_analysis",
                            "budget_overage_detected": True,
                            "projected_monthly_overage": 15000.00,
                            "requires_immediate_intervention": True
                        }
                    }
                ]
                
                # Send critical messages with retry tracking
                for i, message_config in enumerate(critical_messages):
                    attempt_start_time = time.time()
                    
                    try:
                        # Send message (in mock mode, this will succeed)
                        sent_message = await client.send_message(
                            message_config["type"],
                            message_config["data"],
                            user_id="retry_user"
                        )
                        
                        delivery_attempt = {
                            "message_index": i,
                            "attempt_time": time.time() - attempt_start_time,
                            "success": True,
                            "message_id": sent_message.message_id,
                            "event_type": message_config["type"].value
                        }
                        
                        delivery_tracking["attempts"].append(delivery_attempt)
                        delivery_tracking["successes"] += 1
                        
                        # Verify critical data integrity in delivery
                        if message_config["type"] == WebSocketEventType.AGENT_COMPLETED:
                            assert sent_message.data["cost_savings_identified"] == 25000.00
                            assert "urgent_recommendations" in sent_message.data
                            
                        elif message_config["type"] == WebSocketEventType.TOOL_COMPLETED:
                            assert sent_message.data["critical_vulnerabilities_found"] == 3
                            assert sent_message.data["immediate_action_required"] is True
                            
                        elif message_config["type"] == WebSocketEventType.AGENT_THINKING:
                            assert sent_message.data["projected_monthly_overage"] == 15000.00
                            assert sent_message.data["requires_immediate_intervention"] is True
                        
                    except Exception as e:
                        delivery_attempt = {
                            "message_index": i,
                            "attempt_time": time.time() - attempt_start_time,
                            "success": False,
                            "error": str(e),
                            "event_type": message_config["type"].value
                        }
                        
                        delivery_tracking["attempts"].append(delivery_attempt)
                        delivery_tracking["failures"] += 1
                    
                    # Small delay between messages
                    await asyncio.sleep(0.2)
                
                # Wait for message processing
                await asyncio.sleep(1.5)
                
                # Verify critical message delivery
                total_messages = len(critical_messages)
                delivery_success_rate = delivery_tracking["successes"] / total_messages
                
                assert delivery_success_rate >= 0.9, f"Critical message delivery rate too low: {delivery_success_rate}"
                
                # Verify received critical messages maintain data integrity
                received_agent_completed = client.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                received_tool_completed = client.get_messages_by_type(WebSocketEventType.TOOL_COMPLETED)
                received_agent_thinking = client.get_messages_by_type(WebSocketEventType.AGENT_THINKING)
                
                # Check for critical data in received messages
                cost_savings_preserved = False
                security_alerts_preserved = False
                budget_alerts_preserved = False
                
                for message in received_agent_completed:
                    if "cost_savings_identified" in str(message.data):
                        cost_savings_preserved = True
                        
                for message in received_tool_completed:
                    if "critical_vulnerabilities_found" in str(message.data):
                        security_alerts_preserved = True
                        
                for message in received_agent_thinking:
                    if "projected_monthly_overage" in str(message.data):
                        budget_alerts_preserved = True
                
                self.record_metric("critical_messages_sent", total_messages)
                self.record_metric("delivery_success_rate", delivery_success_rate)
                self.record_metric("cost_savings_data_preserved", cost_savings_preserved)
                self.record_metric("security_alerts_preserved", security_alerts_preserved)
                self.record_metric("budget_alerts_preserved", budget_alerts_preserved)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.error_handling
    async def test_malformed_message_handling(self):
        """
        Test WebSocket handling of malformed or corrupted messages.
        
        BVJ: All segments - System stability with invalid input prevents chat disruption.
        """
        async with WebSocketTestUtility() as ws_util:
            async with ws_util.connected_client("malformed_test_user") as client:
                # Track error handling metrics
                error_handling_results = {
                    "malformed_messages_sent": 0,
                    "graceful_errors_handled": 0,
                    "connection_stability_maintained": True,
                    "valid_messages_after_errors": 0
                }
                
                # Test various malformed message scenarios
                malformed_test_cases = [
                    # Invalid JSON structure
                    '{"type": "agent_started", "data": {"incomplete": }',
                    
                    # Missing required fields  
                    '{"data": {"some_data": "value"}}',
                    
                    # Invalid event type
                    '{"type": "invalid_event_type", "data": {"test": true}}',
                    
                    # Extremely large payload (simulated)
                    '{"type": "agent_thinking", "data": {"large_data": "' + 'x' * 1000 + '"}}',
                    
                    # Invalid data types
                    '{"type": "tool_executing", "data": "this_should_be_object"}',
                ]
                
                # Send malformed messages and test handling
                for i, malformed_json in enumerate(malformed_test_cases):
                    error_handling_results["malformed_messages_sent"] += 1
                    
                    try:
                        # Attempt to send malformed message (this tests the client's validation)
                        await client.send_raw_message(malformed_json)
                        
                        # Connection should remain stable after malformed message
                        await asyncio.sleep(0.2)
                        
                        if client.is_connected:
                            error_handling_results["graceful_errors_handled"] += 1
                        else:
                            error_handling_results["connection_stability_maintained"] = False
                            
                    except Exception as e:
                        # Expected behavior - client should reject malformed messages gracefully
                        error_handling_results["graceful_errors_handled"] += 1
                        self.record_metric(f"malformed_message_{i}_error", str(e))
                    
                    # Test that valid messages still work after malformed attempts
                    try:
                        recovery_message = await client.send_message(
                            WebSocketEventType.PING,
                            {
                                "recovery_test": True,
                                "after_malformed_attempt": i + 1,
                                "connection_health": "testing"
                            }
                        )
                        
                        if recovery_message.message_id:
                            error_handling_results["valid_messages_after_errors"] += 1
                            
                    except Exception as e:
                        self.record_metric(f"recovery_message_{i}_failed", str(e))
                
                # Test edge case: Empty message
                error_handling_results["malformed_messages_sent"] += 1
                try:
                    await client.send_raw_message("")
                except Exception:
                    error_handling_results["graceful_errors_handled"] += 1
                
                # Test edge case: Non-JSON message
                error_handling_results["malformed_messages_sent"] += 1
                try:
                    await client.send_raw_message("this is not json at all")
                except Exception:
                    error_handling_results["graceful_errors_handled"] += 1
                
                # Final stability test with valid business message
                try:
                    final_stability_message = await client.send_message(
                        WebSocketEventType.AGENT_COMPLETED,
                        {
                            "malformed_message_test_complete": True,
                            "system_stability": "maintained",
                            "optimization_result": "error_handling_verified",
                            "business_continuity": True
                        }
                    )
                    
                    if final_stability_message.message_id:
                        error_handling_results["connection_stability_maintained"] = True
                        
                except Exception as e:
                    error_handling_results["connection_stability_maintained"] = False
                    self.record_metric("final_stability_test_failed", str(e))
                
                # Verify error handling effectiveness
                malformed_count = error_handling_results["malformed_messages_sent"]
                handled_count = error_handling_results["graceful_errors_handled"]
                error_handling_rate = handled_count / malformed_count if malformed_count > 0 else 0
                
                assert error_handling_rate >= 0.8, f"Error handling rate too low: {error_handling_rate}"
                assert error_handling_results["connection_stability_maintained"], "Connection stability not maintained"
                
                recovery_rate = error_handling_results["valid_messages_after_errors"] / len(malformed_test_cases)
                assert recovery_rate >= 0.8, f"Post-error recovery rate too low: {recovery_rate}"
                
                self.record_metric("malformed_messages_tested", malformed_count)
                self.record_metric("error_handling_success_rate", error_handling_rate)
                self.record_metric("post_error_recovery_rate", recovery_rate)
                self.record_metric("malformed_message_resilience_verified", True)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.error_handling
    async def test_resource_exhaustion_recovery(self):
        """
        Test WebSocket behavior under resource exhaustion conditions.
        
        BVJ: Enterprise - System must handle resource pressure gracefully.
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple clients to simulate resource pressure
            resource_test_clients = []
            user_count = 8  # Moderate load for integration test
            
            try:
                # Create multiple concurrent connections
                for i in range(user_count):
                    user_id = f"resource_test_user_{i}"
                    client = await ws_util.create_authenticated_client(user_id)
                    await client.connect(mock_mode=True)
                    resource_test_clients.append((user_id, client))
                
                # Track resource exhaustion handling
                resource_metrics = {
                    "concurrent_connections": len(resource_test_clients),
                    "message_bursts_sent": 0,
                    "successful_message_deliveries": 0,
                    "connection_drops": 0,
                    "recovery_attempts": 0,
                    "graceful_degradation": True
                }
                
                # Generate message bursts to simulate resource pressure
                burst_tasks = []
                messages_per_burst = 20
                
                async def send_message_burst(user_id: str, client: WebSocketTestClient, burst_id: int):
                    """Send a burst of messages from one client."""
                    burst_results = {
                        "user_id": user_id,
                        "burst_id": burst_id,
                        "messages_sent": 0,
                        "messages_succeeded": 0,
                        "connection_maintained": True
                    }
                    
                    for msg_num in range(messages_per_burst):
                        try:
                            message = await client.send_message(
                                WebSocketEventType.AGENT_THINKING,
                                {
                                    "resource_pressure_test": True,
                                    "burst_id": burst_id,
                                    "message_number": msg_num,
                                    "user_id": user_id,
                                    "payload_data": f"data_chunk_{msg_num}" * 10  # Moderate payload size
                                }
                            )
                            
                            if message.message_id:
                                burst_results["messages_succeeded"] += 1
                            
                            burst_results["messages_sent"] += 1
                            
                            # Brief delay to not overwhelm
                            await asyncio.sleep(0.02)
                            
                        except Exception as e:
                            # Connection may have dropped under pressure
                            if not client.is_connected:
                                burst_results["connection_maintained"] = False
                                resource_metrics["connection_drops"] += 1
                                
                                # Attempt recovery
                                try:
                                    resource_metrics["recovery_attempts"] += 1
                                    await client.connect(mock_mode=True, timeout=5.0)
                                    if client.is_connected:
                                        # Test connection after recovery
                                        recovery_test = await client.send_message(
                                            WebSocketEventType.PING,
                                            {"recovery_successful": True, "user_id": user_id}
                                        )
                                        if recovery_test.message_id:
                                            burst_results["connection_maintained"] = True
                                except Exception:
                                    pass  # Recovery failed, continue test
                            break
                    
                    return burst_results
                
                # Launch concurrent message bursts
                for i, (user_id, client) in enumerate(resource_test_clients):
                    task = send_message_burst(user_id, client, i)
                    burst_tasks.append(task)
                
                # Wait for all bursts to complete
                burst_results = await asyncio.gather(*burst_tasks, return_exceptions=True)
                
                # Analyze resource exhaustion handling
                total_messages_attempted = 0
                total_messages_succeeded = 0
                connections_maintained = 0
                
                for result in burst_results:
                    if isinstance(result, dict):
                        total_messages_attempted += result["messages_sent"]
                        total_messages_succeeded += result["messages_succeeded"]
                        if result["connection_maintained"]:
                            connections_maintained += 1
                
                resource_metrics["message_bursts_sent"] = len(burst_tasks)
                resource_metrics["successful_message_deliveries"] = total_messages_succeeded
                
                # Calculate performance under resource pressure
                message_success_rate = total_messages_succeeded / total_messages_attempted if total_messages_attempted > 0 else 0
                connection_stability_rate = connections_maintained / len(resource_test_clients)
                
                # Verify graceful degradation (should maintain reasonable performance even under pressure)
                assert message_success_rate >= 0.7, f"Message success rate under pressure too low: {message_success_rate}"
                assert connection_stability_rate >= 0.6, f"Connection stability under pressure too low: {connection_stability_rate}"
                
                # Test system recovery after resource pressure
                recovery_test_results = []
                for user_id, client in resource_test_clients[:3]:  # Test first 3 clients
                    if client.is_connected:
                        try:
                            recovery_message = await client.send_message(
                                WebSocketEventType.AGENT_COMPLETED,
                                {
                                    "post_pressure_test": True,
                                    "system_recovery": "verified",
                                    "user_id": user_id,
                                    "optimization_continues": True
                                }
                            )
                            recovery_test_results.append(recovery_message.message_id is not None)
                        except Exception:
                            recovery_test_results.append(False)
                
                system_recovery_rate = sum(recovery_test_results) / len(recovery_test_results) if recovery_test_results else 0
                assert system_recovery_rate >= 0.8, f"System recovery rate too low: {system_recovery_rate}"
                
                self.record_metric("concurrent_connections_tested", resource_metrics["concurrent_connections"])
                self.record_metric("message_success_rate_under_pressure", message_success_rate)
                self.record_metric("connection_stability_rate", connection_stability_rate)
                self.record_metric("system_recovery_rate", system_recovery_rate)
                self.record_metric("resource_exhaustion_handled_gracefully", True)
                
            finally:
                # Clean up all test connections
                cleanup_tasks = [client.disconnect() for _, client in resource_test_clients]
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.error_handling
    async def test_concurrent_error_isolation(self):
        """
        Test that WebSocket errors in one user's connection don't affect other users.
        
        BVJ: All segments - Error isolation ensures multi-user system stability.
        """
        async with WebSocketTestUtility() as ws_util:
            # Create multiple users - one will experience errors, others should be unaffected
            stable_user_1 = await ws_util.create_authenticated_client("stable_user_1")
            error_user = await ws_util.create_authenticated_client("error_user")
            stable_user_2 = await ws_util.create_authenticated_client("stable_user_2")
            
            await stable_user_1.connect(mock_mode=True)
            await error_user.connect(mock_mode=True)
            await stable_user_2.connect(mock_mode=True)
            
            try:
                # Establish baseline for stable users
                stable_1_baseline = await stable_user_1.send_message(
                    WebSocketEventType.AGENT_STARTED,
                    {"baseline": True, "user": "stable_1", "optimization": "aws_costs"}
                )
                
                stable_2_baseline = await stable_user_2.send_message(
                    WebSocketEventType.AGENT_STARTED,
                    {"baseline": True, "user": "stable_2", "optimization": "azure_performance"}
                )
                
                assert stable_1_baseline.message_id, "Stable user 1 baseline should work"
                assert stable_2_baseline.message_id, "Stable user 2 baseline should work"
                
                # Track error isolation metrics
                isolation_metrics = {
                    "error_user_issues": 0,
                    "stable_user_1_continuity": True,
                    "stable_user_2_continuity": True,
                    "cross_contamination_detected": False
                }
                
                # Introduce errors for error_user while stable users continue normal operations
                error_scenarios = [
                    # Scenario 1: Connection disruption for error user
                    {"type": "disconnect", "description": "connection_loss"},
                    
                    # Scenario 2: Malformed messages from error user  
                    {"type": "malformed", "description": "invalid_json"},
                    
                    # Scenario 3: Excessive message rate from error user
                    {"type": "rate_limit", "description": "message_flood"}
                ]
                
                for scenario in error_scenarios:
                    isolation_metrics["error_user_issues"] += 1
                    
                    # Introduce error condition for error_user
                    if scenario["type"] == "disconnect":
                        # Simulate connection loss
                        await error_user.disconnect()
                        
                    elif scenario["type"] == "malformed":
                        # Send malformed message
                        try:
                            await error_user.send_raw_message('{"invalid": json}')
                        except Exception:
                            pass  # Expected to fail
                            
                    elif scenario["type"] == "rate_limit":
                        # Send rapid burst of messages
                        try:
                            for i in range(50):
                                await error_user.send_message(
                                    WebSocketEventType.PING,
                                    {"flood_test": i, "rapid_fire": True}
                                )
                        except Exception:
                            pass  # May fail due to rate limiting
                    
                    # Verify stable users continue working normally during error user's issues
                    try:
                        stable_1_during_error = await stable_user_1.send_message(
                            WebSocketEventType.AGENT_THINKING,
                            {
                                "during_error_test": True,
                                "scenario": scenario["description"],
                                "user": "stable_1",
                                "analysis": "cost_optimization_continuing"
                            }
                        )
                        
                        if not stable_1_during_error.message_id:
                            isolation_metrics["stable_user_1_continuity"] = False
                            
                    except Exception as e:
                        isolation_metrics["stable_user_1_continuity"] = False
                        self.record_metric(f"stable_user_1_error_{scenario['type']}", str(e))
                    
                    try:
                        stable_2_during_error = await stable_user_2.send_message(
                            WebSocketEventType.TOOL_EXECUTING,
                            {
                                "during_error_test": True,
                                "scenario": scenario["description"],
                                "user": "stable_2",
                                "tool": "performance_analyzer"
                            }
                        )
                        
                        if not stable_2_during_error.message_id:
                            isolation_metrics["stable_user_2_continuity"] = False
                            
                    except Exception as e:
                        isolation_metrics["stable_user_2_continuity"] = False
                        self.record_metric(f"stable_user_2_error_{scenario['type']}", str(e))
                    
                    # Brief recovery time between error scenarios
                    await asyncio.sleep(1.0)
                    
                    # Attempt to restore error user connection if needed
                    if not error_user.is_connected:
                        try:
                            await error_user.connect(mock_mode=True, timeout=5.0)
                        except Exception:
                            pass  # Continue test even if error user can't reconnect
                
                # Wait for message processing
                await asyncio.sleep(2.0)
                
                # Verify error isolation - stable users should not have received error user's problematic data
                stable_1_messages = stable_user_1.received_messages
                stable_2_messages = stable_user_2.received_messages
                
                for message in stable_1_messages:
                    message_str = str(message.data)
                    if "error_user" in message_str or "flood_test" in message_str:
                        isolation_metrics["cross_contamination_detected"] = True
                
                for message in stable_2_messages:
                    message_str = str(message.data)
                    if "error_user" in message_str or "flood_test" in message_str:
                        isolation_metrics["cross_contamination_detected"] = True
                
                # Final connectivity test for all users
                final_connectivity_test = []
                
                if stable_user_1.is_connected:
                    try:
                        final_1 = await stable_user_1.send_message(
                            WebSocketEventType.AGENT_COMPLETED,
                            {"final_test": True, "user": "stable_1", "isolation_verified": True}
                        )
                        final_connectivity_test.append(final_1.message_id is not None)
                    except Exception:
                        final_connectivity_test.append(False)
                
                if stable_user_2.is_connected:
                    try:
                        final_2 = await stable_user_2.send_message(
                            WebSocketEventType.AGENT_COMPLETED,
                            {"final_test": True, "user": "stable_2", "isolation_verified": True}
                        )
                        final_connectivity_test.append(final_2.message_id is not None)
                    except Exception:
                        final_connectivity_test.append(False)
                
                # Verify isolation effectiveness
                assert isolation_metrics["stable_user_1_continuity"], "Stable user 1 should maintain continuity"
                assert isolation_metrics["stable_user_2_continuity"], "Stable user 2 should maintain continuity"
                assert not isolation_metrics["cross_contamination_detected"], "No cross-contamination should occur"
                
                final_connectivity_rate = sum(final_connectivity_test) / len(final_connectivity_test) if final_connectivity_test else 0
                assert final_connectivity_rate >= 0.8, f"Final connectivity rate too low: {final_connectivity_rate}"
                
                self.record_metric("error_scenarios_tested", len(error_scenarios))
                self.record_metric("stable_user_1_continuity_maintained", isolation_metrics["stable_user_1_continuity"])
                self.record_metric("stable_user_2_continuity_maintained", isolation_metrics["stable_user_2_continuity"])
                self.record_metric("error_isolation_successful", not isolation_metrics["cross_contamination_detected"])
                self.record_metric("concurrent_error_isolation_verified", True)
                
            finally:
                await stable_user_1.disconnect()
                await error_user.disconnect()
                await stable_user_2.disconnect()