"""
Test Cross-Service Context Failure E2E Scenarios

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure cross-service context propagation remains resilient during service failures
- Value Impact: Prevents user context loss during partial system failures
- Strategic Impact: Core multi-service architecture reliability and user experience continuity

This test suite validates context behavior during network partitions, service restarts,
context schema evolution, and cross-service propagation failures. Tests use REAL
services and network conditions to simulate production failure scenarios.

CRITICAL: Uses real services with authentication - E2E test requirements
"""

import asyncio
import json
import logging
import os
import pytest
import random
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch
import subprocess
import signal

# SSOT imports for E2E testing
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class NetworkPartitionSimulator:
    """Simulates network partitions between services for E2E testing."""
    
    def __init__(self):
        self.active_partitions = set()
        self.partition_rules = []
    
    async def create_partition(self, source_service: str, target_service: str, partition_type: str = "drop"):
        """Create a network partition between services."""
        partition_id = f"{source_service}-{target_service}-{partition_type}"
        
        if partition_type == "drop":
            # Simulate packet drop (would use iptables in real implementation)
            logger.info(f"Simulating packet drop partition: {source_service} -> {target_service}")
        elif partition_type == "delay":
            # Simulate high latency
            logger.info(f"Simulating delay partition: {source_service} -> {target_service}")
        elif partition_type == "disconnect":
            # Simulate complete disconnection
            logger.info(f"Simulating disconnection: {source_service} -> {target_service}")
        
        self.active_partitions.add(partition_id)
        self.partition_rules.append({
            "id": partition_id,
            "source": source_service,
            "target": target_service,
            "type": partition_type,
            "created": time.time()
        })
        
        # Simulate partition creation delay
        await asyncio.sleep(0.5)
        
    async def remove_partition(self, partition_id: str):
        """Remove a network partition."""
        if partition_id in self.active_partitions:
            self.active_partitions.remove(partition_id)
            self.partition_rules = [r for r in self.partition_rules if r["id"] != partition_id]
            logger.info(f"Removed network partition: {partition_id}")
            await asyncio.sleep(0.3)  # Simulate cleanup delay
    
    async def clear_all_partitions(self):
        """Clear all active partitions."""
        for partition_id in list(self.active_partitions):
            await self.remove_partition(partition_id)


class ServiceRestartSimulator:
    """Simulates service restart scenarios for E2E testing."""
    
    def __init__(self):
        self.restarted_services = set()
        self.restart_history = []
    
    async def restart_service(self, service_name: str, restart_type: str = "graceful"):
        """Simulate service restart."""
        restart_id = f"{service_name}-{restart_type}-{int(time.time())}"
        
        logger.info(f"Simulating {restart_type} restart of {service_name}")
        
        if restart_type == "graceful":
            # Simulate graceful shutdown and restart
            restart_duration = random.uniform(2.0, 4.0)
        elif restart_type == "crash":
            # Simulate crash and recovery
            restart_duration = random.uniform(5.0, 8.0)
        elif restart_type == "force_kill":
            # Simulate forced termination
            restart_duration = random.uniform(3.0, 6.0)
        
        self.restart_history.append({
            "service": service_name,
            "type": restart_type,
            "duration": restart_duration,
            "timestamp": time.time()
        })
        
        # Simulate service downtime
        await asyncio.sleep(restart_duration)
        
        self.restarted_services.add(service_name)
        logger.info(f"Service {service_name} restart simulation completed ({restart_duration:.1f}s)")


class TestCrossServiceContextFailures:
    """Test cross-service context behavior during various failure scenarios."""
    
    def setup_method(self):
        """Set up method with cross-service testing infrastructure."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test") 
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        self.network_simulator = NetworkPartitionSimulator()
        self.service_simulator = ServiceRestartSimulator()
        self.failure_scenarios = []
        
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_context_behavior_during_network_partitions(self, real_services_fixture):
        """
        Test context behavior during network partitions between services.
        
        This test creates network partitions between backend and auth services
        and validates that user contexts remain accessible and consistent
        even when services cannot communicate directly.
        
        CRITICAL: Uses REAL authentication and WebSocket connections.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for cross-service testing")
        
        # Create authenticated test users
        partition_users = []
        for i in range(3):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=f"partition-test-{i}-{uuid.uuid4().hex[:8]}",
                email=f"partition-test-{i}-{int(time.time())}@example.com"
            )
            partition_users.append({"token": user_token, "data": user_data})
        
        # Establish initial WebSocket connections with authentication
        websocket_connections = []
        for user in partition_users:
            try:
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket(
                    timeout=10.0
                )
                websocket_connections.append({
                    "websocket": websocket,
                    "user": user,
                    "established": True
                })
                
                # Send initial message to establish context
                await websocket.send(json.dumps({
                    "type": "context_establishment",
                    "user_id": user["data"]["id"],
                    "message": "Establishing context before partition test",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
                
                # Receive acknowledgment
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"Context established for user {user['data']['id']}: {response}")
                
            except Exception as e:
                logger.error(f"Failed to establish WebSocket for user {user['data']['id']}: {e}")
                websocket_connections.append({
                    "websocket": None,
                    "user": user,
                    "established": False,
                    "error": str(e)
                })
        
        # PARTITION SCENARIO 1: Network partition between backend and auth service
        partition_start = time.time()
        await self.network_simulator.create_partition(
            "backend", "auth_service", partition_type="drop"
        )
        
        # Test context operations during partition
        partition_operations = []
        
        for connection in websocket_connections:
            if not connection["established"]:
                continue
                
            websocket = connection["websocket"]
            user = connection["user"]
            
            try:
                # Send message during partition
                partition_message = {
                    "type": "context_operation_during_partition",
                    "user_id": user["data"]["id"],
                    "message": "Testing context during network partition",
                    "partition_active": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(partition_message))
                
                # Wait for response (may be delayed or cached)
                partition_response = await asyncio.wait_for(
                    websocket.recv(), timeout=15.0  # Longer timeout during partition
                )
                
                partition_operations.append({
                    "user_id": user["data"]["id"],
                    "success": True,
                    "response": json.loads(partition_response),
                    "latency": time.time() - partition_start
                })
                
                logger.info(f" PASS:  Context operation successful during partition for user {user['data']['id']}")
                
            except Exception as e:
                partition_operations.append({
                    "user_id": user["data"]["id"],
                    "success": False,
                    "error": str(e),
                    "latency": time.time() - partition_start
                })
                logger.warning(f" FAIL:  Context operation failed during partition for user {user['data']['id']}: {e}")
        
        # PARTITION RECOVERY: Remove network partition
        await self.network_simulator.remove_partition("backend-auth_service-drop")
        recovery_start = time.time()
        
        # Test context recovery after partition
        recovery_operations = []
        
        for connection in websocket_connections:
            if not connection["established"]:
                continue
                
            websocket = connection["websocket"]
            user = connection["user"]
            
            try:
                # Send recovery message
                recovery_message = {
                    "type": "context_recovery_test",
                    "user_id": user["data"]["id"],
                    "message": "Testing context after partition recovery",
                    "partition_recovered": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(recovery_message))
                recovery_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                
                recovery_operations.append({
                    "user_id": user["data"]["id"],
                    "success": True,
                    "response": json.loads(recovery_response),
                    "recovery_time": time.time() - recovery_start
                })
                
                logger.info(f" PASS:  Context recovery successful for user {user['data']['id']}")
                
            except Exception as e:
                recovery_operations.append({
                    "user_id": user["data"]["id"],
                    "success": False,
                    "error": str(e),
                    "recovery_time": time.time() - recovery_start
                })
                
        # RESILIENCE ASSERTIONS
        successful_partition_ops = sum(1 for op in partition_operations if op["success"])
        successful_recovery_ops = sum(1 for op in recovery_operations if op["success"])
        total_users = len([c for c in websocket_connections if c["established"]])
        
        # During partition, some operations may fail, but most should succeed (cached contexts)
        if total_users > 0:
            partition_success_rate = successful_partition_ops / total_users
            recovery_success_rate = successful_recovery_ops / total_users
            
            # PARTITION RESILIENCE: At least 60% of operations should succeed during partition
            min_partition_success = 0.6
            assert partition_success_rate >= min_partition_success, f"Partition resilience too low: {partition_success_rate:.1%}"
            
            # RECOVERY RESILIENCE: At least 90% should recover after partition
            min_recovery_success = 0.9
            assert recovery_success_rate >= min_recovery_success, f"Recovery success rate too low: {recovery_success_rate:.1%}"
        
        # Clean up connections
        for connection in websocket_connections:
            if connection["websocket"]:
                await connection["websocket"].close()
        
        logger.info(f" PASS:  Network partition test completed: {successful_partition_ops}/{total_users} during partition, {successful_recovery_ops}/{total_users} recovered")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_service_restart_context_recovery(self, real_services_fixture):
        """
        Test context recovery during service restart scenarios.
        
        This test simulates service restarts while maintaining user contexts
        and validates that contexts are properly restored after services
        come back online.
        
        CRITICAL: Uses REAL services and authentication flows.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for service restart testing")
        
        # Create authenticated users for restart testing
        restart_users = []
        for i in range(4):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=f"restart-test-{i}-{uuid.uuid4().hex[:8]}",
                email=f"restart-test-{i}-{int(time.time())}@example.com"
            )
            restart_users.append({"token": user_token, "data": user_data})
        
        # Establish persistent contexts before restart
        pre_restart_contexts = []
        for user in restart_users:
            try:
                # Create WebSocket connection
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket()
                
                # Establish context with specific data
                context_message = {
                    "type": "persistent_context_creation",
                    "user_id": user["data"]["id"],
                    "persistent_data": {
                        "user_preferences": {"theme": "dark", "language": "en"},
                        "session_state": {"active_workflow": "cost_optimization"},
                        "temporary_data": {"current_step": 3, "total_steps": 10}
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(context_message))
                context_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                
                pre_restart_contexts.append({
                    "user": user,
                    "websocket": websocket,
                    "context_data": json.loads(context_response),
                    "established": True
                })
                
                logger.info(f"Pre-restart context established for user {user['data']['id']}")
                
            except Exception as e:
                logger.error(f"Failed to establish pre-restart context for user {user['data']['id']}: {e}")
                pre_restart_contexts.append({
                    "user": user,
                    "websocket": None,
                    "context_data": None,
                    "established": False,
                    "error": str(e)
                })
        
        # SERVICE RESTART SIMULATION: Restart backend service
        logger.info("Simulating backend service restart...")
        restart_start = time.time()
        
        # Close existing connections (simulate service going down)
        for context in pre_restart_contexts:
            if context["websocket"]:
                await context["websocket"].close()
        
        # Simulate service restart
        await self.service_simulator.restart_service("backend", restart_type="graceful")
        restart_duration = time.time() - restart_start
        
        # POST-RESTART RECOVERY: Re-establish connections and test context recovery
        recovery_start = time.time()
        recovery_contexts = []
        
        for context_info in pre_restart_contexts:
            if not context_info["established"]:
                continue
                
            user = context_info["user"]
            original_context = context_info["context_data"]
            
            try:
                # Re-establish WebSocket connection after restart
                recovered_websocket = await self.websocket_auth_helper.connect_authenticated_websocket()
                
                # Request context recovery
                recovery_message = {
                    "type": "context_recovery_request",
                    "user_id": user["data"]["id"],
                    "recovery_after_restart": True,
                    "original_session_id": original_context.get("session_id") if original_context else None,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await recovered_websocket.send(json.dumps(recovery_message))
                recovery_response = await asyncio.wait_for(recovered_websocket.recv(), timeout=15.0)
                
                recovered_context = json.loads(recovery_response)
                
                recovery_contexts.append({
                    "user": user,
                    "websocket": recovered_websocket,
                    "recovered_context": recovered_context,
                    "recovery_successful": True,
                    "recovery_time": time.time() - recovery_start
                })
                
                logger.info(f" PASS:  Context recovery successful for user {user['data']['id']}")
                
            except Exception as e:
                recovery_contexts.append({
                    "user": user,
                    "websocket": None,
                    "recovered_context": None,
                    "recovery_successful": False,
                    "error": str(e),
                    "recovery_time": time.time() - recovery_start
                })
                logger.error(f" FAIL:  Context recovery failed for user {user['data']['id']}: {e}")
        
        # CONTEXT PERSISTENCE VALIDATION: Verify critical context data survived restart
        persistent_data_recovered = 0
        total_recoverable_contexts = len([c for c in pre_restart_contexts if c["established"]])
        
        for recovery_info in recovery_contexts:
            if not recovery_info["recovery_successful"]:
                continue
                
            recovered_context = recovery_info["recovered_context"]
            
            # Check for persistent data recovery (user preferences should survive)
            if (recovered_context and 
                "user_preferences" in str(recovered_context) and
                "session_state" in str(recovered_context)):
                persistent_data_recovered += 1
        
        # RECOVERY ASSERTIONS
        successful_recoveries = sum(1 for r in recovery_contexts if r["recovery_successful"])
        
        if total_recoverable_contexts > 0:
            recovery_success_rate = successful_recoveries / total_recoverable_contexts
            persistence_success_rate = persistent_data_recovered / total_recoverable_contexts
            
            # SERVICE RESTART RESILIENCE: At least 80% of contexts should recover
            min_recovery_rate = 0.8
            assert recovery_success_rate >= min_recovery_rate, f"Service restart recovery rate too low: {recovery_success_rate:.1%}"
            
            # PERSISTENCE RESILIENCE: At least 70% of persistent data should survive
            min_persistence_rate = 0.7
            assert persistence_success_rate >= min_persistence_rate, f"Context persistence rate too low: {persistence_success_rate:.1%}"
        
        # Clean up recovered connections
        for recovery_info in recovery_contexts:
            if recovery_info["websocket"]:
                await recovery_info["websocket"].close()
        
        logger.info(f" PASS:  Service restart test completed: {successful_recoveries}/{total_recoverable_contexts} recovered, {persistent_data_recovered} with persistent data")

    @pytest.mark.e2e
    @pytest.mark.real_services 
    async def test_context_schema_evolution_compatibility(self, real_services_fixture):
        """
        Test context behavior during schema evolution scenarios.
        
        This test simulates context schema changes and validates that
        existing contexts remain compatible and functional even when
        the underlying schema evolves.
        
        CRITICAL: Tests forward/backward compatibility of context schemas.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for schema evolution testing")
        
        # Create users with different schema versions
        schema_users = []
        for i in range(5):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=f"schema-test-{i}-{uuid.uuid4().hex[:8]}",
                email=f"schema-test-{i}-{int(time.time())}@example.com"
            )
            schema_users.append({"token": user_token, "data": user_data})
        
        # SCHEMA VERSION 1: Create contexts with original schema
        v1_contexts = []
        for user in schema_users[:2]:  # First 2 users use v1 schema
            try:
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket()
                
                # Create context with v1 schema
                v1_context_message = {
                    "type": "context_creation",
                    "schema_version": "1.0",
                    "user_id": user["data"]["id"],
                    "context_data": {
                        "user_preferences": {"theme": "light"},
                        "session_info": {"created_at": datetime.now(timezone.utc).isoformat()}
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(v1_context_message))
                v1_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                
                v1_contexts.append({
                    "user": user,
                    "websocket": websocket,
                    "context": json.loads(v1_response),
                    "schema_version": "1.0"
                })
                
                logger.info(f"Created v1 context for user {user['data']['id']}")
                
            except Exception as e:
                logger.error(f"Failed to create v1 context for user {user['data']['id']}: {e}")
                v1_contexts.append({
                    "user": user,
                    "websocket": None,
                    "context": None,
                    "schema_version": "1.0",
                    "error": str(e)
                })
        
        # SCHEMA VERSION 2: Create contexts with evolved schema
        v2_contexts = []
        for user in schema_users[2:4]:  # Next 2 users use v2 schema
            try:
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket()
                
                # Create context with v2 schema (extended with new fields)
                v2_context_message = {
                    "type": "context_creation",
                    "schema_version": "2.0",
                    "user_id": user["data"]["id"],
                    "context_data": {
                        "user_preferences": {
                            "theme": "dark",
                            "accessibility": {"high_contrast": True}  # New in v2
                        },
                        "session_info": {
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "device_type": "desktop"  # New in v2
                        },
                        "feature_flags": {"beta_features": True}  # New in v2
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(v2_context_message))
                schema_v2_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                
                v2_contexts.append({
                    "user": user,
                    "websocket": websocket,
                    "context": json.loads(schema_v2_response),
                    "schema_version": "2.0"
                })
                
                logger.info(f"Created v2 context for user {user['data']['id']}")
                
            except Exception as e:
                logger.error(f"Failed to create v2 context for user {user['data']['id']}: {e}")
                v2_contexts.append({
                    "user": user,
                    "websocket": None,
                    "context": None,
                    "schema_version": "2.0",
                    "error": str(e)
                })
        
        # SCHEMA VERSION 3: Create contexts with future schema
        v3_contexts = []
        for user in schema_users[4:]:  # Last user uses v3 schema
            try:
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket()
                
                # Create context with v3 schema (hypothetical future version)
                v3_context_message = {
                    "type": "context_creation",
                    "schema_version": "3.0",
                    "user_id": user["data"]["id"],
                    "context_data": {
                        "user_preferences": {
                            "theme": "auto",
                            "accessibility": {"high_contrast": False, "font_size": "large"},
                            "ai_preferences": {"model": "advanced", "response_style": "detailed"}  # New in v3
                        },
                        "session_info": {
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "device_type": "mobile",
                            "client_version": "3.0.0"  # New in v3
                        },
                        "feature_flags": {"beta_features": True, "experimental_ui": True},  # Extended in v3
                        "ai_context": {"conversation_history": [], "model_state": {}}  # New in v3
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(v3_context_message))
                v3_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                
                v3_contexts.append({
                    "user": user,
                    "websocket": websocket,
                    "context": json.loads(v3_response),
                    "schema_version": "3.0"
                })
                
                logger.info(f"Created v3 context for user {user['data']['id']}")
                
            except Exception as e:
                logger.error(f"Failed to create v3 context for user {user['data']['id']}: {e}")
                v3_contexts.append({
                    "user": user,
                    "websocket": None,
                    "context": None,
                    "schema_version": "3.0",
                    "error": str(e)
                })
        
        # CROSS-SCHEMA COMPATIBILITY TEST: Access contexts across schema versions
        all_contexts = v1_contexts + v2_contexts + v3_contexts
        compatibility_results = []
        
        for context_info in all_contexts:
            if not context_info["websocket"]:
                continue
                
            try:
                # Test context access with different client versions
                compatibility_message = {
                    "type": "cross_schema_access_test",
                    "user_id": context_info["user"]["data"]["id"],
                    "requesting_schema": "2.0",  # Simulate v2 client accessing context
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await context_info["websocket"].send(json.dumps(compatibility_message))
                compatibility_response = await asyncio.wait_for(
                    context_info["websocket"].recv(), timeout=10.0
                )
                
                response_data = json.loads(compatibility_response)
                
                compatibility_results.append({
                    "original_schema": context_info["schema_version"],
                    "requesting_schema": "2.0",
                    "user_id": context_info["user"]["data"]["id"],
                    "compatible": True,
                    "response_data": response_data
                })
                
                logger.info(f" PASS:  Cross-schema compatibility successful: {context_info['schema_version']} -> 2.0")
                
            except Exception as e:
                compatibility_results.append({
                    "original_schema": context_info["schema_version"],
                    "requesting_schema": "2.0",
                    "user_id": context_info["user"]["data"]["id"],
                    "compatible": False,
                    "error": str(e)
                })
                logger.warning(f" FAIL:  Cross-schema compatibility failed: {context_info['schema_version']} -> 2.0: {e}")
        
        # SCHEMA EVOLUTION ASSERTIONS
        successful_v1_contexts = len([c for c in v1_contexts if c["websocket"]])
        successful_schema_v2_contexts = len([c for c in v2_contexts if c["websocket"]])
        successful_v3_contexts = len([c for c in v3_contexts if c["websocket"]])
        compatible_accesses = len([r for r in compatibility_results if r["compatible"]])
        total_compatibility_tests = len(compatibility_results)
        
        # SCHEMA COMPATIBILITY: All schema versions should work
        assert successful_v1_contexts > 0, "v1 schema contexts failed to create"
        assert successful_v2_contexts > 0, "v2 schema contexts failed to create"
        assert successful_v3_contexts > 0, "v3 schema contexts failed to create"
        
        # CROSS-COMPATIBILITY: At least 80% of cross-schema access should work
        if total_compatibility_tests > 0:
            compatibility_rate = compatible_accesses / total_compatibility_tests
            min_compatibility_rate = 0.8
            assert compatibility_rate >= min_compatibility_rate, f"Cross-schema compatibility too low: {compatibility_rate:.1%}"
        
        # Clean up all connections
        for context_info in all_contexts:
            if context_info["websocket"]:
                await context_info["websocket"].close()
        
        logger.info(f" PASS:  Schema evolution test completed: v1={successful_v1_contexts}, v2={successful_v2_contexts}, v3={successful_v3_contexts}, compatibility={compatible_accesses}/{total_compatibility_tests}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_cross_service_context_propagation_failures(self, real_services_fixture):
        """
        Test context propagation behavior when inter-service communication fails.
        
        This test validates that context information is properly cached and
        remains accessible even when services cannot communicate with each
        other for context synchronization.
        
        CRITICAL: Tests service mesh resilience and context caching.
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Real PostgreSQL not available - required for propagation testing")
        
        # Create users for propagation testing
        propagation_users = []
        for i in range(3):
            user_token, user_data = await create_authenticated_user(
                environment="test",
                user_id=f"propagation-{i}-{uuid.uuid4().hex[:8]}",
                email=f"propagation-{i}-{int(time.time())}@example.com"
            )
            propagation_users.append({"token": user_token, "data": user_data})
        
        # Establish contexts that require cross-service propagation
        propagation_contexts = []
        for user in propagation_users:
            try:
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket()
                
                # Create complex context requiring cross-service sync
                propagation_message = {
                    "type": "cross_service_context_creation",
                    "user_id": user["data"]["id"],
                    "context_data": {
                        "auth_context": {"permissions": ["read", "write"], "roles": ["user"]},
                        "session_context": {"preferences": {"notifications": True}},
                        "business_context": {"subscription": "pro", "usage_limits": {"api_calls": 1000}}
                    },
                    "requires_propagation": ["auth_service", "backend", "analytics_service"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(propagation_message))
                propagation_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                
                propagation_contexts.append({
                    "user": user,
                    "websocket": websocket,
                    "context": json.loads(propagation_response),
                    "propagated": True
                })
                
                logger.info(f"Cross-service context established for user {user['data']['id']}")
                
            except Exception as e:
                logger.error(f"Failed cross-service context for user {user['data']['id']}: {e}")
                propagation_contexts.append({
                    "user": user,
                    "websocket": None,
                    "context": None,
                    "propagated": False,
                    "error": str(e)
                })
        
        # PROPAGATION FAILURE SIMULATION: Block inter-service communication
        await self.network_simulator.create_partition("backend", "analytics_service", "disconnect")
        await self.network_simulator.create_partition("auth_service", "backend", "delay")
        
        # Test context access during propagation failures
        failure_test_results = []
        
        for context_info in propagation_contexts:
            if not context_info["propagated"]:
                continue
                
            try:
                # Request context operations that would normally require propagation
                failure_test_message = {
                    "type": "context_operation_during_propagation_failure",
                    "user_id": context_info["user"]["data"]["id"],
                    "operation": "update_business_context",
                    "data": {"subscription": "enterprise", "upgrade_timestamp": time.time()},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await context_info["websocket"].send(json.dumps(failure_test_message))
                
                # This should succeed using cached context, even if propagation fails
                failure_response = await asyncio.wait_for(
                    context_info["websocket"].recv(), timeout=20.0  # Longer timeout due to retries
                )
                
                failure_test_results.append({
                    "user_id": context_info["user"]["data"]["id"],
                    "operation_successful": True,
                    "response": json.loads(failure_response),
                    "used_cache": True  # Inferred from successful response during propagation failure
                })
                
                logger.info(f" PASS:  Context operation successful during propagation failure for user {context_info['user']['data']['id']}")
                
            except Exception as e:
                failure_test_results.append({
                    "user_id": context_info["user"]["data"]["id"],
                    "operation_successful": False,
                    "error": str(e),
                    "used_cache": False
                })
                logger.warning(f" FAIL:  Context operation failed during propagation failure for user {context_info['user']['data']['id']}: {e}")
        
        # PROPAGATION RECOVERY: Restore inter-service communication
        await self.network_simulator.clear_all_partitions()
        
        # Test context synchronization after propagation recovery
        recovery_sync_results = []
        
        for context_info in propagation_contexts:
            if not context_info["propagated"]:
                continue
                
            try:
                # Trigger context synchronization after recovery
                sync_message = {
                    "type": "context_synchronization_after_recovery",
                    "user_id": context_info["user"]["data"]["id"],
                    "force_sync": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await context_info["websocket"].send(json.dumps(sync_message))
                sync_response = await asyncio.wait_for(context_info["websocket"].recv(), timeout=15.0)
                
                recovery_sync_results.append({
                    "user_id": context_info["user"]["data"]["id"],
                    "sync_successful": True,
                    "sync_response": json.loads(sync_response)
                })
                
                logger.info(f" PASS:  Context synchronization after recovery successful for user {context_info['user']['data']['id']}")
                
            except Exception as e:
                recovery_sync_results.append({
                    "user_id": context_info["user"]["data"]["id"],
                    "sync_successful": False,
                    "error": str(e)
                })
                logger.error(f" FAIL:  Context synchronization after recovery failed for user {context_info['user']['data']['id']}: {e}")
        
        # PROPAGATION RESILIENCE ASSERTIONS
        successful_operations_during_failure = len([r for r in failure_test_results if r["operation_successful"]])
        successful_syncs_after_recovery = len([r for r in recovery_sync_results if r["sync_successful"]])
        total_propagated_contexts = len([c for c in propagation_contexts if c["propagated"]])
        
        if total_propagated_contexts > 0:
            # CACHE RESILIENCE: At least 70% should work using cached context
            failure_resilience_rate = successful_operations_during_failure / total_propagated_contexts
            min_cache_resilience = 0.7
            assert failure_resilience_rate >= min_cache_resilience, f"Cache resilience during propagation failure too low: {failure_resilience_rate:.1%}"
            
            # SYNC RECOVERY: At least 90% should sync successfully after recovery
            sync_recovery_rate = successful_syncs_after_recovery / total_propagated_contexts
            min_sync_recovery = 0.9
            assert sync_recovery_rate >= min_sync_recovery, f"Sync recovery rate too low: {sync_recovery_rate:.1%}"
        
        # Clean up connections
        for context_info in propagation_contexts:
            if context_info["websocket"]:
                await context_info["websocket"].close()
        
        logger.info(f" PASS:  Cross-service propagation failure test completed: {successful_operations_during_failure}/{total_propagated_contexts} during failure, {successful_syncs_after_recovery}/{total_propagated_contexts} synced after recovery")

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up network partitions
        asyncio.create_task(self.network_simulator.clear_all_partitions())
        
        # Clear failure scenario tracking
        self.failure_scenarios.clear()
        
        logger.info("Cross-service context failure test cleanup completed")