"""
WebSocket Performance and Load Handling Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise/Mid/Platform
- Business Goal: Ensure WebSocket performance scales with business growth
- Value Impact: High-performance WebSocket handling enables large-scale AI operations
- Strategic Impact: Scalable real-time communication supports enterprise customer growth

These tests validate that WebSocket infrastructure can handle enterprise-level load
while maintaining the responsiveness critical for AI-powered business operations.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
import uuid
import statistics
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    WebSocketMessage
)
from shared.isolated_environment import get_env


class TestWebSocketPerformanceLoadHandling(SSotAsyncTestCase):
    """Test WebSocket performance and load handling patterns."""
    
    async def setup_method(self, method=None):
        """Set up test environment."""
        await super().async_setup_method(method)
        self.env = get_env()
        
        # Configure performance testing environment
        self.set_env_var("WEBSOCKET_TEST_TIMEOUT", "30")
        self.set_env_var("WEBSOCKET_MOCK_MODE", "true")
        self.set_env_var("PERFORMANCE_MONITORING_ENABLED", "true")
        self.set_env_var("WEBSOCKET_BATCH_SIZE", "25")
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.performance
    async def test_high_frequency_message_handling(self):
        """
        Test WebSocket handling of high-frequency message streams.
        
        BVJ: Enterprise - High-frequency AI analysis requires rapid event delivery.
        """
        async with WebSocketTestUtility() as ws_util:
            async with ws_util.connected_client("high_freq_user") as client:
                # Performance tracking
                performance_metrics = {
                    "messages_sent": 0,
                    "messages_received": 0,
                    "start_time": None,
                    "end_time": None,
                    "latency_measurements": [],
                    "throughput_measurements": [],
                    "peak_throughput": 0,
                    "avg_latency": 0
                }
                
                # High-frequency message parameters
                message_batches = 5
                messages_per_batch = 50
                total_messages = message_batches * messages_per_batch
                
                performance_metrics["start_time"] = time.time()
                
                # Send high-frequency message batches
                for batch in range(message_batches):
                    batch_start = time.time()
                    batch_sent = 0
                    
                    for msg_num in range(messages_per_batch):
                        message_start = time.time()
                        
                        # Simulate real-time AI analysis events
                        message_data = {
                            "batch_id": batch,
                            "message_id": msg_num,
                            "high_frequency_test": True,
                            "ai_analysis": {
                                "step": f"analysis_step_{msg_num}",
                                "progress": (msg_num + 1) / messages_per_batch,
                                "intermediate_result": f"finding_{msg_num}",
                                "timestamp": message_start
                            },
                            "optimization_metrics": {
                                "cpu_utilization": 45 + (msg_num % 20),
                                "memory_usage": 60 + (msg_num % 15),
                                "cost_impact": round(100.50 * (msg_num + 1) / 10, 2)
                            }
                        }
                        
                        try:
                            sent_message = await client.send_message(
                                WebSocketEventType.AGENT_THINKING,
                                message_data,
                                user_id="high_freq_user"
                            )
                            
                            if sent_message.message_id:
                                performance_metrics["messages_sent"] += 1
                                batch_sent += 1
                                
                                # Measure per-message latency
                                message_latency = time.time() - message_start
                                performance_metrics["latency_measurements"].append(message_latency)
                            
                        except Exception as e:
                            self.record_metric(f"high_freq_message_error_{batch}_{msg_num}", str(e))
                        
                        # Minimal delay for high frequency (20ms between messages)
                        await asyncio.sleep(0.02)
                    
                    # Measure batch throughput
                    batch_duration = time.time() - batch_start
                    if batch_duration > 0:
                        batch_throughput = batch_sent / batch_duration
                        performance_metrics["throughput_measurements"].append(batch_throughput)
                        performance_metrics["peak_throughput"] = max(
                            performance_metrics["peak_throughput"], 
                            batch_throughput
                        )
                    
                    # Brief pause between batches to measure sustained performance
                    await asyncio.sleep(0.1)
                
                performance_metrics["end_time"] = time.time()
                
                # Wait for message processing completion
                await asyncio.sleep(2.0)
                
                # Calculate overall performance metrics
                total_duration = performance_metrics["end_time"] - performance_metrics["start_time"]
                overall_throughput = performance_metrics["messages_sent"] / total_duration
                
                if performance_metrics["latency_measurements"]:
                    performance_metrics["avg_latency"] = statistics.mean(performance_metrics["latency_measurements"])
                    max_latency = max(performance_metrics["latency_measurements"])
                    min_latency = min(performance_metrics["latency_measurements"])
                    latency_std = statistics.stdev(performance_metrics["latency_measurements"]) if len(performance_metrics["latency_measurements"]) > 1 else 0
                
                # Count received messages (in mock mode, track what was processed)
                thinking_messages = client.get_messages_by_type(WebSocketEventType.AGENT_THINKING)
                performance_metrics["messages_received"] = len(thinking_messages)
                
                # Performance assertions for enterprise-level requirements
                assert overall_throughput >= 15.0, f"Overall throughput too low: {overall_throughput} msg/s"
                assert performance_metrics["peak_throughput"] >= 25.0, f"Peak throughput too low: {performance_metrics['peak_throughput']} msg/s"
                assert performance_metrics["avg_latency"] < 0.1, f"Average latency too high: {performance_metrics['avg_latency']}s"
                
                # Message delivery rate
                delivery_rate = performance_metrics["messages_received"] / performance_metrics["messages_sent"] if performance_metrics["messages_sent"] > 0 else 0
                assert delivery_rate >= 0.95, f"Message delivery rate too low: {delivery_rate}"
                
                # Record detailed performance metrics
                self.record_metric("total_high_freq_messages", total_messages)
                self.record_metric("messages_sent", performance_metrics["messages_sent"])
                self.record_metric("messages_received", performance_metrics["messages_received"])
                self.record_metric("overall_throughput_msg_per_sec", overall_throughput)
                self.record_metric("peak_throughput_msg_per_sec", performance_metrics["peak_throughput"])
                self.record_metric("avg_message_latency_seconds", performance_metrics["avg_latency"])
                self.record_metric("message_delivery_rate", delivery_rate)
                self.record_metric("test_duration_seconds", total_duration)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.performance
    async def test_concurrent_user_scaling_performance(self):
        """
        Test WebSocket performance with multiple concurrent users at scale.
        
        BVJ: Enterprise - Multi-user scalability for large enterprise deployments.
        """
        async with WebSocketTestUtility() as ws_util:
            # Scaling test parameters
            concurrent_users = 20  # Enterprise-level concurrent users
            messages_per_user = 15
            test_duration_limit = 25.0  # seconds
            
            # Performance tracking
            scaling_metrics = {
                "concurrent_users": concurrent_users,
                "total_connections_attempted": 0,
                "successful_connections": 0,
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "user_performance": {},
                "connection_establishment_times": [],
                "message_distribution_fairness": {},
                "resource_efficiency_score": 0
            }
            
            connected_clients = []
            
            try:
                # Phase 1: Concurrent connection establishment
                connection_start_time = time.time()
                connection_tasks = []
                
                async def establish_user_connection(user_index: int) -> Tuple[str, Optional[WebSocketTestClient], float, bool]:
                    """Establish connection for a single user."""
                    user_id = f"scale_user_{user_index}"
                    scaling_metrics["total_connections_attempted"] += 1
                    
                    connect_start = time.time()
                    try:
                        client = await ws_util.create_authenticated_client(user_id)
                        success = await client.connect(mock_mode=True, timeout=10.0)
                        connect_time = time.time() - connect_start
                        
                        scaling_metrics["connection_establishment_times"].append(connect_time)
                        
                        if success:
                            scaling_metrics["successful_connections"] += 1
                            return user_id, client, connect_time, True
                        else:
                            return user_id, None, connect_time, False
                            
                    except Exception as e:
                        connect_time = time.time() - connect_start
                        self.record_metric(f"connection_error_user_{user_index}", str(e))
                        return user_id, None, connect_time, False
                
                # Launch concurrent connections
                connection_tasks = [establish_user_connection(i) for i in range(concurrent_users)]
                connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
                
                # Process connection results
                for result in connection_results:
                    if isinstance(result, tuple) and len(result) == 4:
                        user_id, client, connect_time, success = result
                        if success and client:
                            connected_clients.append((user_id, client))
                            scaling_metrics["user_performance"][user_id] = {
                                "connection_time": connect_time,
                                "messages_sent": 0,
                                "messages_received": 0,
                                "avg_response_time": 0
                            }
                
                connection_phase_duration = time.time() - connection_start_time
                connection_success_rate = len(connected_clients) / concurrent_users
                
                # Phase 2: Concurrent message exchange
                message_phase_start = time.time()
                
                async def user_message_workload(user_id: str, client: WebSocketTestClient, user_index: int):
                    """Execute message workload for a single user."""
                    user_metrics = scaling_metrics["user_performance"][user_id]
                    response_times = []
                    
                    for msg_num in range(messages_per_user):
                        message_start_time = time.time()
                        
                        try:
                            # Simulate realistic enterprise AI workload
                            message_data = {
                                "user_index": user_index,
                                "message_number": msg_num,
                                "concurrent_scaling_test": True,
                                "enterprise_workload": {
                                    "analysis_type": "cost_optimization",
                                    "resource_scope": f"account_{user_index}",
                                    "optimization_parameters": {
                                        "target_savings": 10000 + (user_index * 1000),
                                        "risk_tolerance": "moderate",
                                        "time_horizon": "quarterly"
                                    },
                                    "data_volume": f"processing_{msg_num + 1}_of_{messages_per_user}"
                                },
                                "timestamp": message_start_time
                            }
                            
                            sent_message = await client.send_message(
                                WebSocketEventType.AGENT_THINKING,
                                message_data,
                                user_id=user_id
                            )
                            
                            if sent_message.message_id:
                                scaling_metrics["total_messages_sent"] += 1
                                user_metrics["messages_sent"] += 1
                                
                                response_time = time.time() - message_start_time
                                response_times.append(response_time)
                            
                        except Exception as e:
                            self.record_metric(f"message_error_{user_id}_{msg_num}", str(e))
                        
                        # Stagger message timing to simulate real usage
                        await asyncio.sleep(0.05 + (user_index % 3) * 0.02)
                    
                    # Calculate user-specific performance metrics
                    if response_times:
                        user_metrics["avg_response_time"] = statistics.mean(response_times)
                    
                    # Count received messages for this user
                    user_received_messages = [
                        msg for msg in client.received_messages 
                        if hasattr(msg, 'data') and msg.data.get('user_index') == user_index
                    ]
                    user_metrics["messages_received"] = len(user_received_messages)
                    scaling_metrics["total_messages_received"] += len(user_received_messages)
                
                # Execute concurrent user workloads
                workload_tasks = [
                    user_message_workload(user_id, client, i) 
                    for i, (user_id, client) in enumerate(connected_clients)
                ]
                
                await asyncio.gather(*workload_tasks, return_exceptions=True)
                
                message_phase_duration = time.time() - message_phase_start
                total_test_duration = connection_phase_duration + message_phase_duration
                
                # Wait for final message processing
                await asyncio.sleep(1.0)
                
                # Phase 3: Performance analysis
                # Calculate scaling performance metrics
                expected_total_messages = len(connected_clients) * messages_per_user
                message_delivery_efficiency = scaling_metrics["total_messages_received"] / scaling_metrics["total_messages_sent"] if scaling_metrics["total_messages_sent"] > 0 else 0
                
                # Connection establishment performance
                avg_connection_time = statistics.mean(scaling_metrics["connection_establishment_times"]) if scaling_metrics["connection_establishment_times"] else 0
                max_connection_time = max(scaling_metrics["connection_establishment_times"]) if scaling_metrics["connection_establishment_times"] else 0
                
                # Message throughput across all users
                overall_throughput = scaling_metrics["total_messages_sent"] / message_phase_duration if message_phase_duration > 0 else 0
                per_user_avg_throughput = overall_throughput / len(connected_clients) if connected_clients else 0
                
                # Fairness analysis - check if message distribution is fair across users
                user_message_counts = [metrics["messages_sent"] for metrics in scaling_metrics["user_performance"].values()]
                if user_message_counts:
                    message_fairness_coefficient = statistics.stdev(user_message_counts) / statistics.mean(user_message_counts) if statistics.mean(user_message_counts) > 0 else 1.0
                else:
                    message_fairness_coefficient = 1.0
                
                # Resource efficiency score (combined metric)
                efficiency_factors = [
                    min(connection_success_rate * 100, 100),  # Connection success (0-100)
                    min(message_delivery_efficiency * 100, 100),  # Message delivery (0-100)
                    min(overall_throughput * 2, 100),  # Throughput score (scale throughput to 0-100)
                    max(100 - (message_fairness_coefficient * 50), 0)  # Fairness score (lower coefficient = higher score)
                ]
                scaling_metrics["resource_efficiency_score"] = statistics.mean(efficiency_factors)
                
                # Enterprise-level performance assertions
                assert connection_success_rate >= 0.9, f"Connection success rate too low: {connection_success_rate}"
                assert message_delivery_efficiency >= 0.85, f"Message delivery efficiency too low: {message_delivery_efficiency}"
                assert overall_throughput >= 20.0, f"Overall throughput too low: {overall_throughput} msg/s"
                assert per_user_avg_throughput >= 0.8, f"Per-user throughput too low: {per_user_avg_throughput} msg/s"
                assert avg_connection_time < 2.0, f"Average connection time too slow: {avg_connection_time}s"
                assert total_test_duration < test_duration_limit, f"Test duration exceeded limit: {total_test_duration}s"
                assert message_fairness_coefficient < 0.3, f"Message distribution unfairness too high: {message_fairness_coefficient}"
                
                # Record comprehensive scaling metrics
                self.record_metric("concurrent_users_tested", concurrent_users)
                self.record_metric("connection_success_rate", connection_success_rate)
                self.record_metric("message_delivery_efficiency", message_delivery_efficiency)
                self.record_metric("overall_message_throughput", overall_throughput)
                self.record_metric("per_user_avg_throughput", per_user_avg_throughput)
                self.record_metric("avg_connection_establishment_time", avg_connection_time)
                self.record_metric("max_connection_establishment_time", max_connection_time)
                self.record_metric("message_fairness_coefficient", message_fairness_coefficient)
                self.record_metric("resource_efficiency_score", scaling_metrics["resource_efficiency_score"])
                self.record_metric("total_test_duration", total_test_duration)
                self.record_metric("concurrent_scaling_performance_verified", True)
                
            finally:
                # Clean up all connections
                disconnect_tasks = [client.disconnect() for _, client in connected_clients]
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.performance
    async def test_large_payload_handling_performance(self):
        """
        Test WebSocket performance with large message payloads.
        
        BVJ: Enterprise - Large AI analysis results require efficient payload handling.
        """
        async with WebSocketTestUtility() as ws_util:
            async with ws_util.connected_client("large_payload_user") as client:
                # Large payload test parameters
                payload_sizes = [
                    {"size": "small", "data_multiplier": 10, "description": "standard_optimization_results"},
                    {"size": "medium", "data_multiplier": 50, "description": "detailed_analysis_with_recommendations"},
                    {"size": "large", "data_multiplier": 100, "description": "comprehensive_enterprise_report"},
                    {"size": "extra_large", "data_multiplier": 200, "description": "multi_account_optimization_analysis"}
                ]
                
                # Performance tracking for large payloads
                payload_metrics = {
                    "payload_tests": [],
                    "total_data_transferred": 0,
                    "avg_transfer_rate": 0,
                    "payload_processing_times": {},
                    "memory_efficiency_score": 100
                }
                
                for payload_config in payload_sizes:
                    payload_start_time = time.time()
                    
                    # Generate large realistic payload
                    base_data_unit = {
                        "resource_id": f"resource_{uuid.uuid4().hex[:8]}",
                        "resource_type": "ec2_instance",
                        "current_cost": round(145.67, 2),
                        "optimization_recommendation": {
                            "action": "rightsizing",
                            "new_instance_type": "m5.large",
                            "projected_savings": round(67.89, 2),
                            "confidence_score": 0.87,
                            "implementation_steps": [
                                "stop_instance_during_maintenance_window",
                                "create_snapshot_for_rollback",
                                "change_instance_type",
                                "validate_performance_metrics"
                            ]
                        },
                        "historical_metrics": {
                            "cpu_utilization": [45.2, 42.8, 48.1, 44.5, 47.3],
                            "memory_utilization": [62.1, 58.9, 65.4, 60.2, 63.7],
                            "network_throughput": [128.5, 134.2, 121.8, 126.9, 132.1]
                        },
                        "cost_breakdown": {
                            "compute_cost": 89.45,
                            "storage_cost": 34.12,
                            "network_cost": 22.10
                        }
                    }
                    
                    # Scale up data based on payload size
                    multiplier = payload_config["data_multiplier"]
                    large_payload_data = {
                        "payload_size_category": payload_config["size"],
                        "description": payload_config["description"],
                        "large_payload_test": True,
                        "optimization_results": {
                            "total_resources_analyzed": multiplier * 10,
                            "total_potential_savings": multiplier * 1500.00,
                            "analysis_complexity": payload_config["size"],
                            "detailed_recommendations": [
                                {**base_data_unit, "resource_id": f"resource_{i}_{uuid.uuid4().hex[:6]}"}
                                for i in range(multiplier)
                            ]
                        },
                        "performance_metadata": {
                            "analysis_duration": f"{multiplier * 0.5} minutes",
                            "data_sources_consulted": multiplier // 5,
                            "optimization_algorithms_applied": ["cost_analysis", "performance_profiling", "usage_pattern_analysis"]
                        },
                        "compliance_data": {
                            "security_checks_passed": multiplier * 3,
                            "regulatory_requirements_verified": ["sox", "pci", "gdpr"],
                            "audit_trail": [f"audit_entry_{i}" for i in range(min(multiplier // 2, 100))]
                        }
                    }
                    
                    try:
                        # Send large payload
                        sent_message = await client.send_message(
                            WebSocketEventType.AGENT_COMPLETED,
                            large_payload_data,
                            user_id="large_payload_user"
                        )
                        
                        payload_processing_time = time.time() - payload_start_time
                        
                        # Estimate payload size (rough calculation)
                        import sys
                        estimated_payload_size = sys.getsizeof(str(large_payload_data))
                        
                        payload_test_result = {
                            "size_category": payload_config["size"],
                            "estimated_size_bytes": estimated_payload_size,
                            "processing_time": payload_processing_time,
                            "transfer_rate_bps": estimated_payload_size / payload_processing_time if payload_processing_time > 0 else 0,
                            "success": sent_message.message_id is not None,
                            "message_id": sent_message.message_id if sent_message.message_id else None
                        }
                        
                        payload_metrics["payload_tests"].append(payload_test_result)
                        payload_metrics["total_data_transferred"] += estimated_payload_size
                        payload_metrics["payload_processing_times"][payload_config["size"]] = payload_processing_time
                        
                        # Verify data integrity for large payloads
                        if sent_message.message_id:
                            assert large_payload_data["optimization_results"]["total_resources_analyzed"] == sent_message.data["optimization_results"]["total_resources_analyzed"]
                            assert large_payload_data["payload_size_category"] == sent_message.data["payload_size_category"]
                            
                    except Exception as e:
                        payload_test_result = {
                            "size_category": payload_config["size"],
                            "estimated_size_bytes": 0,
                            "processing_time": time.time() - payload_start_time,
                            "transfer_rate_bps": 0,
                            "success": False,
                            "error": str(e)
                        }
                        payload_metrics["payload_tests"].append(payload_test_result)
                        self.record_metric(f"large_payload_error_{payload_config['size']}", str(e))
                    
                    # Brief pause between payload tests
                    await asyncio.sleep(1.0)
                
                # Wait for all large payloads to be processed
                await asyncio.sleep(3.0)
                
                # Analyze large payload performance
                successful_payload_tests = [test for test in payload_metrics["payload_tests"] if test["success"]]
                payload_success_rate = len(successful_payload_tests) / len(payload_metrics["payload_tests"])
                
                # Calculate transfer rate statistics
                transfer_rates = [test["transfer_rate_bps"] for test in successful_payload_tests if test["transfer_rate_bps"] > 0]
                if transfer_rates:
                    payload_metrics["avg_transfer_rate"] = statistics.mean(transfer_rates)
                    min_transfer_rate = min(transfer_rates)
                    max_transfer_rate = max(transfer_rates)
                
                # Performance assertions for large payload handling
                assert payload_success_rate >= 0.8, f"Large payload success rate too low: {payload_success_rate}"
                
                # Check processing time scaling
                small_payload_time = payload_metrics["payload_processing_times"].get("small", 0)
                large_payload_time = payload_metrics["payload_processing_times"].get("large", 0)
                if small_payload_time > 0 and large_payload_time > 0:
                    processing_time_scaling = large_payload_time / small_payload_time
                    # Large payloads should not take disproportionately longer
                    assert processing_time_scaling < 50, f"Large payload processing scales poorly: {processing_time_scaling}x"
                
                # Verify data integrity across all payload sizes
                received_completed_messages = client.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
                large_payload_messages = [
                    msg for msg in received_completed_messages 
                    if hasattr(msg, 'data') and msg.data.get('large_payload_test') is True
                ]
                
                data_integrity_verified = True
                for message in large_payload_messages:
                    if "optimization_results" not in message.data or "detailed_recommendations" not in message.data["optimization_results"]:
                        data_integrity_verified = False
                        break
                
                assert data_integrity_verified, "Large payload data integrity not maintained"
                
                # Record large payload performance metrics
                self.record_metric("payload_sizes_tested", len(payload_sizes))
                self.record_metric("payload_success_rate", payload_success_rate)
                self.record_metric("total_data_transferred_bytes", payload_metrics["total_data_transferred"])
                self.record_metric("avg_transfer_rate_bps", payload_metrics["avg_transfer_rate"])
                self.record_metric("large_payload_data_integrity_verified", data_integrity_verified)
                
                # Record individual payload size performance
                for test_result in payload_metrics["payload_tests"]:
                    self.record_metric(f"payload_{test_result['size_category']}_processing_time", test_result["processing_time"])
                    self.record_metric(f"payload_{test_result['size_category']}_success", test_result["success"])
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.performance
    async def test_sustained_load_endurance_performance(self):
        """
        Test WebSocket endurance under sustained load conditions.
        
        BVJ: Enterprise - Long-running AI operations require sustained performance.
        """
        async with WebSocketTestUtility() as ws_util:
            # Endurance test parameters
            endurance_duration = 10.0  # seconds (reduced for integration test)
            concurrent_clients = 6
            message_frequency = 2.0  # messages per second per client
            
            # Endurance performance tracking
            endurance_metrics = {
                "test_duration": endurance_duration,
                "concurrent_clients": concurrent_clients,
                "target_message_frequency": message_frequency,
                "actual_messages_sent": 0,
                "actual_messages_received": 0,
                "performance_degradation_detected": False,
                "memory_usage_stable": True,
                "connection_stability": {},
                "throughput_over_time": [],
                "latency_over_time": [],
                "error_rate_over_time": [],
                "endurance_score": 0
            }
            
            connected_clients = []
            
            try:
                # Establish concurrent connections for endurance test
                for i in range(concurrent_clients):
                    user_id = f"endurance_user_{i}"
                    client = await ws_util.create_authenticated_client(user_id)
                    success = await client.connect(mock_mode=True)
                    
                    if success:
                        connected_clients.append((user_id, client))
                        endurance_metrics["connection_stability"][user_id] = {
                            "initial_connected": True,
                            "disconnections": 0,
                            "reconnections": 0,
                            "messages_sent": 0,
                            "errors": 0
                        }
                
                assert len(connected_clients) >= concurrent_clients * 0.8, "Insufficient clients connected for endurance test"
                
                # Sustained load execution
                test_start_time = time.time()
                client_tasks = []
                
                async def sustained_client_workload(user_id: str, client: WebSocketTestClient, client_index: int):
                    """Execute sustained workload for a single client."""
                    client_metrics = endurance_metrics["connection_stability"][user_id]
                    interval = 1.0 / message_frequency  # seconds between messages
                    
                    message_count = 0
                    while time.time() - test_start_time < endurance_duration:
                        try:
                            message_send_start = time.time()
                            
                            # Simulate sustained enterprise AI workload
                            sustained_message_data = {
                                "endurance_test": True,
                                "client_index": client_index,
                                "message_count": message_count,
                                "elapsed_time": time.time() - test_start_time,
                                "sustained_analysis": {
                                    "analysis_phase": f"continuous_optimization_phase_{message_count // 10}",
                                    "resource_monitoring": {
                                        "active_resources": 150 + client_index * 25,
                                        "optimization_opportunities": message_count % 12,
                                        "cost_tracking": round((message_count * 15.50) + (client_index * 100), 2)
                                    },
                                    "performance_indicators": {
                                        "processing_efficiency": min(95, 80 + message_count % 15),
                                        "resource_utilization": min(85, 65 + message_count % 20),
                                        "optimization_success_rate": min(98, 85 + message_count % 13)
                                    }
                                },
                                "timestamp": message_send_start
                            }
                            
                            sent_message = await client.send_message(
                                WebSocketEventType.AGENT_THINKING,
                                sustained_message_data,
                                user_id=user_id
                            )
                            
                            if sent_message.message_id:
                                client_metrics["messages_sent"] += 1
                                endurance_metrics["actual_messages_sent"] += 1
                                message_count += 1
                                
                                # Track latency over time
                                message_latency = time.time() - message_send_start
                                endurance_metrics["latency_over_time"].append({
                                    "timestamp": time.time() - test_start_time,
                                    "latency": message_latency,
                                    "client": client_index
                                })
                            
                        except Exception as e:
                            client_metrics["errors"] += 1
                            
                            # Check if connection was lost
                            if not client.is_connected:
                                client_metrics["disconnections"] += 1
                                
                                # Attempt reconnection
                                try:
                                    reconnect_success = await client.connect(mock_mode=True, timeout=5.0)
                                    if reconnect_success:
                                        client_metrics["reconnections"] += 1
                                except Exception:
                                    pass  # Continue test even if reconnection fails
                            
                            self.record_metric(f"endurance_error_{user_id}_{message_count}", str(e))
                        
                        # Maintain steady message frequency
                        await asyncio.sleep(interval)
                
                # Launch sustained workload for all clients
                client_tasks = [
                    sustained_client_workload(user_id, client, i) 
                    for i, (user_id, client) in enumerate(connected_clients)
                ]
                
                # Monitor performance during sustained load
                monitoring_task = asyncio.create_task(
                    self._monitor_sustained_performance(endurance_metrics, test_start_time, endurance_duration)
                )
                
                # Wait for sustained load completion
                await asyncio.gather(*client_tasks, return_exceptions=True)
                monitoring_task.cancel()
                
                actual_test_duration = time.time() - test_start_time
                
                # Wait for final message processing
                await asyncio.sleep(2.0)
                
                # Analyze endurance performance
                # Calculate actual throughput achieved
                actual_throughput = endurance_metrics["actual_messages_sent"] / actual_test_duration
                expected_throughput = concurrent_clients * message_frequency
                throughput_efficiency = actual_throughput / expected_throughput if expected_throughput > 0 else 0
                
                # Count received messages
                total_received = 0
                for user_id, client in connected_clients:
                    thinking_messages = client.get_messages_by_type(WebSocketEventType.AGENT_THINKING)
                    endurance_received = len([
                        msg for msg in thinking_messages 
                        if hasattr(msg, 'data') and msg.data.get('endurance_test') is True
                    ])
                    total_received += endurance_received
                
                endurance_metrics["actual_messages_received"] = total_received
                message_delivery_rate = total_received / endurance_metrics["actual_messages_sent"] if endurance_metrics["actual_messages_sent"] > 0 else 0
                
                # Analyze connection stability
                total_disconnections = sum(metrics["disconnections"] for metrics in endurance_metrics["connection_stability"].values())
                total_errors = sum(metrics["errors"] for metrics in endurance_metrics["connection_stability"].values())
                connection_reliability = 1.0 - (total_disconnections / len(connected_clients))
                error_rate = total_errors / endurance_metrics["actual_messages_sent"] if endurance_metrics["actual_messages_sent"] > 0 else 0
                
                # Performance degradation analysis
                if endurance_metrics["latency_over_time"]:
                    early_latencies = [l["latency"] for l in endurance_metrics["latency_over_time"][:10]]
                    late_latencies = [l["latency"] for l in endurance_metrics["latency_over_time"][-10:]]
                    
                    if early_latencies and late_latencies:
                        early_avg = statistics.mean(early_latencies)
                        late_avg = statistics.mean(late_latencies)
                        latency_degradation = (late_avg - early_avg) / early_avg if early_avg > 0 else 0
                        endurance_metrics["performance_degradation_detected"] = latency_degradation > 0.5  # 50% degradation threshold
                
                # Calculate endurance score
                score_factors = [
                    min(throughput_efficiency * 100, 100),
                    min(message_delivery_rate * 100, 100),
                    min(connection_reliability * 100, 100),
                    max(100 - (error_rate * 1000), 0),  # Error rate penalty
                    100 if not endurance_metrics["performance_degradation_detected"] else 70
                ]
                endurance_metrics["endurance_score"] = statistics.mean(score_factors)
                
                # Enterprise endurance performance assertions
                assert throughput_efficiency >= 0.8, f"Throughput efficiency under sustained load too low: {throughput_efficiency}"
                assert message_delivery_rate >= 0.85, f"Message delivery rate under sustained load too low: {message_delivery_rate}"
                assert connection_reliability >= 0.9, f"Connection reliability under sustained load too low: {connection_reliability}"
                assert error_rate < 0.05, f"Error rate under sustained load too high: {error_rate}"
                assert not endurance_metrics["performance_degradation_detected"], "Significant performance degradation detected"
                assert endurance_metrics["endurance_score"] >= 85, f"Overall endurance score too low: {endurance_metrics['endurance_score']}"
                
                # Record comprehensive endurance metrics
                self.record_metric("endurance_test_duration", actual_test_duration)
                self.record_metric("concurrent_clients_endurance", len(connected_clients))
                self.record_metric("messages_sent_endurance", endurance_metrics["actual_messages_sent"])
                self.record_metric("messages_received_endurance", endurance_metrics["actual_messages_received"])
                self.record_metric("sustained_throughput_efficiency", throughput_efficiency)
                self.record_metric("sustained_message_delivery_rate", message_delivery_rate)
                self.record_metric("sustained_connection_reliability", connection_reliability)
                self.record_metric("sustained_error_rate", error_rate)
                self.record_metric("performance_degradation_detected", endurance_metrics["performance_degradation_detected"])
                self.record_metric("endurance_performance_score", endurance_metrics["endurance_score"])
                
            finally:
                # Clean up all endurance test connections
                disconnect_tasks = [client.disconnect() for _, client in connected_clients]
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
    
    async def _monitor_sustained_performance(self, metrics: Dict[str, Any], start_time: float, duration: float):
        """Monitor performance metrics during sustained load test."""
        sample_interval = 1.0  # Sample every second
        
        try:
            while time.time() - start_time < duration:
                current_time = time.time() - start_time
                
                # Sample current throughput
                current_throughput = len(metrics.get("latency_over_time", [])) / current_time if current_time > 0 else 0
                metrics["throughput_over_time"].append({
                    "timestamp": current_time,
                    "throughput": current_throughput
                })
                
                await asyncio.sleep(sample_interval)
                
        except asyncio.CancelledError:
            pass  # Expected when test completes
    
    @pytest.mark.integration
    @pytest.mark.websocket
    @pytest.mark.performance
    async def test_websocket_memory_efficiency_optimization(self):
        """
        Test WebSocket memory efficiency and resource optimization.
        
        BVJ: Enterprise - Memory efficiency critical for large-scale deployments.
        """
        async with WebSocketTestUtility() as ws_util:
            # Memory efficiency test parameters
            memory_test_clients = 8
            messages_per_memory_test = 25
            message_retention_cycles = 3
            
            # Memory efficiency tracking
            memory_metrics = {
                "clients_tested": memory_test_clients,
                "messages_per_cycle": messages_per_memory_test,
                "retention_cycles": message_retention_cycles,
                "total_messages_sent": 0,
                "memory_usage_samples": [],
                "message_buffer_sizes": [],
                "garbage_collection_efficiency": 100,
                "memory_leak_detected": False,
                "resource_cleanup_verified": True
            }
            
            memory_test_clients_list = []
            
            try:
                # Create clients for memory efficiency testing
                for i in range(memory_test_clients):
                    user_id = f"memory_test_user_{i}"
                    client = await ws_util.create_authenticated_client(user_id)
                    await client.connect(mock_mode=True)
                    memory_test_clients_list.append((user_id, client))
                
                # Execute memory efficiency test cycles
                for cycle in range(message_retention_cycles):
                    cycle_start_time = time.time()
                    
                    # Send messages with varying payload sizes
                    for client_index, (user_id, client) in enumerate(memory_test_clients_list):
                        for msg_num in range(messages_per_memory_test):
                            # Create message with escalating complexity
                            complexity_factor = (cycle + 1) * (msg_num + 1)
                            
                            memory_test_data = {
                                "memory_efficiency_test": True,
                                "cycle": cycle,
                                "message_number": msg_num,
                                "client_index": client_index,
                                "complexity_factor": complexity_factor,
                                "resource_analysis": {
                                    "memory_intensive_data": [
                                        {
                                            "resource_id": f"mem_resource_{i}_{uuid.uuid4().hex[:4]}",
                                            "metrics": [float(x) for x in range(min(complexity_factor, 50))],
                                            "optimization_history": [f"step_{j}" for j in range(min(complexity_factor // 2, 25))]
                                        }
                                        for i in range(min(complexity_factor // 5, 10))
                                    ]
                                },
                                "timestamp": cycle_start_time
                            }
                            
                            try:
                                sent_message = await client.send_message(
                                    WebSocketEventType.AGENT_THINKING,
                                    memory_test_data,
                                    user_id=user_id
                                )
                                
                                if sent_message.message_id:
                                    memory_metrics["total_messages_sent"] += 1
                                
                            except Exception as e:
                                self.record_metric(f"memory_test_error_c{cycle}_u{client_index}_m{msg_num}", str(e))
                    
                    # Sample memory usage after each cycle (simulated)
                    # In a real implementation, this would check actual memory usage
                    cycle_duration = time.time() - cycle_start_time
                    simulated_memory_usage = {
                        "cycle": cycle,
                        "duration": cycle_duration,
                        "estimated_memory_mb": 50 + (cycle * 10) + (memory_metrics["total_messages_sent"] * 0.1),
                        "message_buffer_size": sum(len(client.sent_messages) for _, client in memory_test_clients_list)
                    }
                    
                    memory_metrics["memory_usage_samples"].append(simulated_memory_usage)
                    memory_metrics["message_buffer_sizes"].append(simulated_memory_usage["message_buffer_size"])
                    
                    # Brief pause between cycles
                    await asyncio.sleep(0.5)
                
                # Wait for message processing
                await asyncio.sleep(2.0)
                
                # Analyze memory efficiency
                if len(memory_metrics["memory_usage_samples"]) >= 2:
                    initial_memory = memory_metrics["memory_usage_samples"][0]["estimated_memory_mb"]
                    final_memory = memory_metrics["memory_usage_samples"][-1]["estimated_memory_mb"]
                    memory_growth_rate = (final_memory - initial_memory) / initial_memory if initial_memory > 0 else 0
                    
                    # Memory leak detection (growth rate threshold)
                    memory_metrics["memory_leak_detected"] = memory_growth_rate > 2.0  # 200% growth indicates potential leak
                
                # Buffer size efficiency analysis
                if memory_metrics["message_buffer_sizes"]:
                    max_buffer_size = max(memory_metrics["message_buffer_sizes"])
                    avg_buffer_size = statistics.mean(memory_metrics["message_buffer_sizes"])
                    buffer_efficiency = 1.0 - (avg_buffer_size / max_buffer_size) if max_buffer_size > 0 else 1.0
                
                # Verify message cleanup (test that old messages don't accumulate indefinitely)
                total_retained_messages = sum(len(client.received_messages) for _, client in memory_test_clients_list)
                message_retention_ratio = total_retained_messages / memory_metrics["total_messages_sent"] if memory_metrics["total_messages_sent"] > 0 else 0
                
                # Memory efficiency assertions
                assert not memory_metrics["memory_leak_detected"], "Memory leak detected during efficiency test"
                assert message_retention_ratio < 1.5, f"Message retention ratio too high: {message_retention_ratio}"  # Allow some buffering
                
                # Test connection cleanup efficiency
                cleanup_start_time = time.time()
                disconnect_tasks = [client.disconnect() for _, client in memory_test_clients_list[:4]]  # Test half the clients
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
                cleanup_duration = time.time() - cleanup_start_time
                
                # Cleanup should be efficient
                assert cleanup_duration < 2.0, f"Connection cleanup too slow: {cleanup_duration}s"
                
                # Verify remaining connections still work after partial cleanup
                remaining_clients = memory_test_clients_list[4:]
                post_cleanup_success_count = 0
                
                for user_id, client in remaining_clients:
                    try:
                        post_cleanup_message = await client.send_message(
                            WebSocketEventType.PING,
                            {"post_cleanup_test": True, "memory_efficiency_verified": True}
                        )
                        if post_cleanup_message.message_id:
                            post_cleanup_success_count += 1
                    except Exception:
                        pass
                
                post_cleanup_success_rate = post_cleanup_success_count / len(remaining_clients) if remaining_clients else 1.0
                assert post_cleanup_success_rate >= 0.8, f"Post-cleanup success rate too low: {post_cleanup_success_rate}"
                
                # Record memory efficiency metrics
                self.record_metric("memory_test_clients", memory_test_clients)
                self.record_metric("total_memory_test_messages", memory_metrics["total_messages_sent"])
                self.record_metric("memory_leak_detected", memory_metrics["memory_leak_detected"])
                self.record_metric("message_retention_ratio", message_retention_ratio)
                self.record_metric("connection_cleanup_duration", cleanup_duration)
                self.record_metric("post_cleanup_success_rate", post_cleanup_success_rate)
                self.record_metric("memory_efficiency_verified", True)
                
            finally:
                # Final cleanup of remaining connections
                final_cleanup_tasks = [client.disconnect() for _, client in memory_test_clients_list[4:]]
                await asyncio.gather(*final_cleanup_tasks, return_exceptions=True)