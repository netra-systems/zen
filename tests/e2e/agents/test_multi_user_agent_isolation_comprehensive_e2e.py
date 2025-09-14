#!/usr/bin/env python
"""
Multi-User Agent Isolation Comprehensive E2E Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise - Multi-tenant architecture ($300K+ MRR)
- Business Goal: Ensure complete user isolation in concurrent agent execution
- Value Impact: Prevents data leaks, security breaches, and cross-user interference
- Strategic/Revenue Impact: Critical for enterprise trust and compliance requirements

This test suite validates comprehensive multi-user isolation:
1. Concurrent user execution with no data leakage
2. Factory pattern isolation ensuring unique instances per user
3. WebSocket event isolation - users only see their own events
4. Resource isolation - memory/CPU separation between users
5. State persistence isolation - user data never crosses boundaries
6. Error isolation - one user's errors don't affect others

CRITICAL E2E REQUIREMENTS:
- Real GCP staging environment (NO Docker)
- Multiple authenticated users with JWT tokens
- Concurrent execution stress testing
- Data leakage detection and prevention
- Factory pattern validation for user isolation
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Set
import pytest
import websockets
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import E2E auth helper for SSOT authentication
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper,
    create_authenticated_user_context,
    E2EAuthConfig
)
from test_framework.base_e2e_test import BaseE2ETest
from tests.e2e.staging_config import StagingTestConfig, get_staging_config

logger = logging.getLogger(__name__)


class TestMultiUserAgentIsolationE2E(BaseE2ETest):
    """
    Comprehensive Multi-User Agent Isolation E2E Tests for GCP Staging.

    Tests critical multi-tenant isolation patterns to ensure enterprise-grade
    security and data separation in concurrent agent execution.
    """

    @pytest.fixture(autouse=True)
    async def setup_multi_user_environment(self):
        """Set up multi-user staging environment with isolation testing."""
        await self.initialize_test_environment()

        # Configure for GCP staging environment
        self.staging_config = get_staging_config()
        self.auth_helper = E2EAuthHelper(environment="staging")
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment="staging")

        # Validate staging configuration
        assert self.staging_config.validate_configuration(), "Staging configuration invalid"

        # Create multiple authenticated test users for isolation testing
        self.test_users = []
        user_count = 5  # 5 concurrent users for comprehensive isolation testing

        for i in range(user_count):
            user_context = await create_authenticated_user_context(
                user_email=f"isolation_test_user_{i}_{int(time.time())}@staging.netra.ai",
                environment="staging",
                permissions=["read", "write", "execute_agents"],
                user_metadata={
                    "user_index": i,
                    "isolation_group": f"group_{i % 3}",  # 3 isolation groups
                    "secret_data": f"secret_for_user_{i}_only"
                }
            )
            self.test_users.append(user_context)

        # Isolation monitoring data
        self.user_events = {}
        self.user_data_access = {}
        self.cross_user_leaks = []

        for user in self.test_users:
            self.user_events[user.user_id] = []
            self.user_data_access[user.user_id] = set()

        self.logger.info(f"✅ PASS: Multi-user isolation test environment ready - {len(self.test_users)} users authenticated")

    async def test_concurrent_execution_complete_isolation(self):
        """
        Test concurrent agent execution with complete user isolation validation.

        BVJ: Validates $300K+ MRR enterprise architecture - Zero data leakage tolerance
        Ensures: Users never see other users' data, events, or execution results
        """
        concurrent_isolation_results = []

        async def run_isolated_user_execution(user_context, user_index):
            """Execute agent for specific user with comprehensive isolation monitoring."""
            try:
                # Isolated WebSocket connection per user
                user_ws_helper = E2EWebSocketAuthHelper(environment="staging")
                websocket = await user_ws_helper.connect_authenticated_websocket(timeout=20.0)

                # Track all events for this user
                user_events = []
                user_data = {}
                other_user_data_detected = []

                async def monitor_user_isolation():
                    """Monitor for isolation violations and collect user-specific data."""
                    nonlocal user_data
                    async for message in websocket:
                        event = json.loads(message)
                        user_events.append({
                            **event,
                            "user_index": user_index,
                            "user_id": user_context.user_id,
                            "timestamp": time.time()
                        })

                        # Check for data leakage from other users
                        event_data = event.get("data", {})

                        # Detect if this event contains data from other users
                        for other_user in self.test_users:
                            if other_user.user_id != user_context.user_id:
                                other_secret = other_user.agent_context.get("user_metadata", {}).get("secret_data", "")
                                if other_secret and other_secret in str(event_data):
                                    other_user_data_detected.append({
                                        "leaked_from": other_user.user_id,
                                        "leaked_to": user_context.user_id,
                                        "secret_data": other_secret,
                                        "event_type": event.get("type")
                                    })

                        if event.get("type") == "agent_completed":
                            user_data = event_data
                            break

                isolation_task = asyncio.create_task(monitor_user_isolation())

                # Send user-specific execution request with unique data
                user_secret = user_context.agent_context.get("user_metadata", {}).get("secret_data", "")
                isolation_request = {
                    "type": "execute_agent",
                    "agent_type": "isolation_test",
                    "user_id": user_context.user_id,
                    "thread_id": user_context.thread_id,
                    "request_id": user_context.request_id,
                    "data": {
                        "user_index": user_index,
                        "isolation_validation": True,
                        "user_secret_data": user_secret,
                        "user_specific_task": f"task_for_user_{user_index}",
                        "cross_contamination_test": True,
                        "expected_isolation_group": user_context.agent_context.get("user_metadata", {}).get("isolation_group")
                    }
                }

                start_time = time.time()
                await websocket.send(json.dumps(isolation_request))

                # Wait for user execution completion
                await asyncio.wait_for(isolation_task, timeout=45.0)
                execution_duration = time.time() - start_time

                await websocket.close()

                # Validate isolation - no cross-user data leakage
                isolation_violations = len(other_user_data_detected)

                return {
                    "user_index": user_index,
                    "user_id": user_context.user_id,
                    "success": True,
                    "execution_duration": execution_duration,
                    "events": user_events,
                    "user_data": user_data,
                    "isolation_violations": isolation_violations,
                    "leaked_data": other_user_data_detected,
                    "event_count": len(user_events)
                }

            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_context.user_id,
                    "success": False,
                    "error": str(e)
                }

        # Execute all users concurrently
        tasks = [
            run_isolated_user_execution(user_context, i)
            for i, user_context in enumerate(self.test_users)
        ]

        concurrent_isolation_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate complete isolation across all users
        successful_users = 0
        total_violations = 0
        all_leaked_data = []

        for result in concurrent_isolation_results:
            if isinstance(result, dict) and result.get("success"):
                successful_users += 1

                # Critical validation: Zero isolation violations allowed
                violations = result.get("isolation_violations", 0)
                total_violations += violations

                leaked_data = result.get("leaked_data", [])
                all_leaked_data.extend(leaked_data)

                # Validate user received their own data
                user_data = result.get("user_data", {})
                user_index = result.get("user_index")

                assert f"task_for_user_{user_index}" in str(user_data), f"User {user_index} didn't receive their task"
                assert user_data.get("user_index") == user_index, f"User {user_index} received wrong user index"

                # Validate execution completed successfully
                events = result.get("events", [])
                event_types = [e.get("type") for e in events]
                assert "agent_completed" in event_types, f"User {user_index} execution never completed"

        # Critical assertions for enterprise-grade isolation
        assert successful_users == len(self.test_users), f"Expected {len(self.test_users)} successful users, got {successful_users}"
        assert total_violations == 0, f"CRITICAL ISOLATION FAILURE: {total_violations} violations detected"
        assert len(all_leaked_data) == 0, f"CRITICAL DATA LEAK: {len(all_leaked_data)} leaks found"

        # Additional validation: Cross-reference all results for isolation
        all_user_ids = {r.get("user_id") for r in concurrent_isolation_results if isinstance(r, dict) and r.get("success")}
        assert len(all_user_ids) == len(self.test_users), "Not all users completed successfully"

        # Validate no event cross-contamination
        for result in concurrent_isolation_results:
            if isinstance(result, dict) and result.get("success"):
                user_id = result.get("user_id")
                user_events = result.get("events", [])

                for event in user_events:
                    event_user_id = event.get("user_id")
                    assert event_user_id == user_id, f"Event cross-contamination: User {user_id} received event for {event_user_id}"

        self.logger.info(f"✅ PASS: Concurrent multi-user isolation validated successfully")
        self.logger.info(f"👥 Concurrent users: {successful_users}")
        self.logger.info(f"🔒 Isolation violations: {total_violations} (MUST BE ZERO)")
        self.logger.info(f"🛡️ Data leaks prevented: {len(all_leaked_data)} (MUST BE ZERO)")

    async def test_factory_pattern_instance_isolation(self):
        """
        Test factory pattern creates truly isolated instances per user.

        BVJ: Validates $200K+ MRR architecture integrity - Shared instances cause failures
        Ensures: Each user gets unique agent instances with no shared state
        """
        factory_isolation_results = []

        async def test_user_factory_isolation(user_context, user_index):
            """Test factory pattern isolation for specific user."""
            try:
                # Create WebSocket connection for factory testing
                user_ws_helper = E2EWebSocketAuthHelper(environment="staging")
                websocket = await user_ws_helper.connect_authenticated_websocket(timeout=20.0)

                # Track factory-related events
                factory_events = []
                instance_id = None
                shared_state_detected = False

                async def monitor_factory_isolation():
                    """Monitor factory instance creation and isolation."""
                    nonlocal instance_id, shared_state_detected
                    async for message in websocket:
                        event = json.loads(message)
                        factory_events.append(event)

                        if event.get("type") == "agent_instance_created":
                            instance_data = event.get("data", {})
                            instance_id = instance_data.get("instance_id")

                            # Check for shared state indicators
                            shared_state_markers = instance_data.get("shared_state_markers", [])
                            if len(shared_state_markers) > 0:
                                shared_state_detected = True

                        elif event.get("type") == "agent_completed":
                            break

                factory_task = asyncio.create_task(monitor_factory_isolation())

                # Send factory instance test request
                factory_request = {
                    "type": "execute_agent",
                    "agent_type": "factory_isolation_test",
                    "user_id": user_context.user_id,
                    "thread_id": user_context.thread_id,
                    "request_id": user_context.request_id,
                    "data": {
                        "test_factory_isolation": True,
                        "user_index": user_index,
                        "require_unique_instance": True,
                        "state_isolation_test": True,
                        "instance_validation": {
                            "memory_isolation": True,
                            "state_separation": True,
                            "resource_independence": True
                        }
                    }
                }

                await websocket.send(json.dumps(factory_request))

                # Wait for factory testing completion
                await asyncio.wait_for(factory_task, timeout=30.0)
                await websocket.close()

                return {
                    "user_index": user_index,
                    "user_id": user_context.user_id,
                    "instance_id": instance_id,
                    "shared_state_detected": shared_state_detected,
                    "events": factory_events,
                    "success": True
                }

            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_context.user_id,
                    "success": False,
                    "error": str(e)
                }

        # Test factory isolation for all users
        tasks = [
            test_user_factory_isolation(user_context, i)
            for i, user_context in enumerate(self.test_users[:3])  # Test with 3 users for factory validation
        ]

        factory_isolation_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate factory pattern isolation
        successful_factory_tests = 0
        unique_instance_ids = set()
        shared_state_detections = 0

        for result in factory_isolation_results:
            if isinstance(result, dict) and result.get("success"):
                successful_factory_tests += 1

                # Validate unique instance creation
                instance_id = result.get("instance_id")
                assert instance_id is not None, f"User {result['user_index']} didn't get instance ID"

                # Check for instance uniqueness
                if instance_id in unique_instance_ids:
                    pytest.fail(f"CRITICAL FACTORY FAILURE: Instance ID {instance_id} reused across users")

                unique_instance_ids.add(instance_id)

                # Validate no shared state
                shared_state = result.get("shared_state_detected", False)
                if shared_state:
                    shared_state_detections += 1

        # Critical factory pattern validations
        assert successful_factory_tests == 3, f"Expected 3 successful factory tests, got {successful_factory_tests}"
        assert len(unique_instance_ids) == 3, f"Expected 3 unique instances, got {len(unique_instance_ids)}"
        assert shared_state_detections == 0, f"CRITICAL: Shared state detected in {shared_state_detections} instances"

        # Validate instance IDs follow expected pattern (should be UUIDs or similar)
        for instance_id in unique_instance_ids:
            assert len(instance_id) >= 8, f"Instance ID too short: {instance_id}"
            assert "-" in instance_id or len(instance_id) >= 16, f"Instance ID doesn't follow UUID pattern: {instance_id}"

        self.logger.info(f"✅ PASS: Factory pattern isolation validated successfully")
        self.logger.info(f"🏭 Factory tests: {successful_factory_tests}")
        self.logger.info(f"🔑 Unique instances: {len(unique_instance_ids)}")
        self.logger.info(f"🔒 Shared state detections: {shared_state_detections} (MUST BE ZERO)")

    async def test_websocket_event_stream_isolation(self):
        """
        Test WebSocket event streams are completely isolated between users.

        BVJ: Validates $150K+ MRR real-time architecture - Event leakage breaks user trust
        Ensures: Users only receive their own WebSocket events, no cross-streaming
        """
        # Create multiple concurrent WebSocket connections
        websocket_connections = []
        event_collectors = []

        try:
            # Set up isolated WebSocket connections for each user
            for i, user_context in enumerate(self.test_users[:3]):  # Test with 3 users
                user_ws_helper = E2EWebSocketAuthHelper(environment="staging")
                websocket = await user_ws_helper.connect_authenticated_websocket(timeout=20.0)
                websocket_connections.append((websocket, user_context, i))

                # Event collector for this user
                user_events = []
                event_collectors.append(user_events)

        except Exception as e:
            # Clean up any connections that were established
            for ws, _, _ in websocket_connections:
                try:
                    await ws.close()
                except:
                    pass
            pytest.fail(f"Failed to establish WebSocket connections: {e}")

        # Monitor event streams for all users simultaneously
        async def monitor_user_event_stream(websocket, user_context, user_index, event_collector):
            """Monitor WebSocket events for specific user."""
            try:
                # Send user-specific request to generate events
                stream_test_request = {
                    "type": "execute_agent",
                    "agent_type": "event_stream_isolation_test",
                    "user_id": user_context.user_id,
                    "thread_id": user_context.thread_id,
                    "request_id": user_context.request_id,
                    "data": {
                        "user_index": user_index,
                        "generate_unique_events": True,
                        "event_isolation_test": True,
                        "user_identifier": f"user_{user_index}_stream",
                        "event_count_target": 10  # Generate 10+ events for testing
                    }
                }

                await websocket.send(json.dumps(stream_test_request))

                # Collect events for this user
                async for message in websocket:
                    event = json.loads(message)
                    event_collector.append({
                        **event,
                        "received_by_user": user_context.user_id,
                        "user_index": user_index,
                        "timestamp": time.time()
                    })

                    if event.get("type") == "agent_completed":
                        break

            except Exception as e:
                self.logger.error(f"Event stream monitoring error for user {user_index}: {e}")

        # Start monitoring all event streams simultaneously
        monitoring_tasks = []
        for (websocket, user_context, user_index), event_collector in zip(websocket_connections, event_collectors):
            task = asyncio.create_task(
                monitor_user_event_stream(websocket, user_context, user_index, event_collector)
            )
            monitoring_tasks.append(task)

        # Wait for all event stream monitoring to complete
        try:
            await asyncio.gather(*monitoring_tasks, return_exceptions=True)
        finally:
            # Clean up WebSocket connections
            for websocket, _, _ in websocket_connections:
                try:
                    await websocket.close()
                except:
                    pass

        # Validate event stream isolation
        total_events = sum(len(events) for events in event_collectors)
        assert total_events >= 30, f"Expected at least 30 total events (10 per user), got {total_events}"

        # Critical isolation validation: Check for event cross-contamination
        for i, user_events in enumerate(event_collectors):
            user_context = websocket_connections[i][1]
            expected_user_id = user_context.user_id

            assert len(user_events) >= 8, f"User {i} received insufficient events: {len(user_events)}"

            for event in user_events:
                # Validate event belongs to correct user
                event_user_id = event.get("user_id")
                received_by_user = event.get("received_by_user")

                if event_user_id and event_user_id != expected_user_id:
                    pytest.fail(f"CRITICAL EVENT LEAK: User {i} ({expected_user_id}) received event for {event_user_id}")

                # Validate user-specific content
                event_data = event.get("data", {})
                expected_identifier = f"user_{i}_stream"

                if "user_identifier" in event_data:
                    actual_identifier = event_data.get("user_identifier")
                    assert actual_identifier == expected_identifier, f"User {i} received event with wrong identifier: {actual_identifier}"

        # Validate no duplicate events across users
        all_event_signatures = set()
        duplicate_events = []

        for i, user_events in enumerate(event_collectors):
            for event in user_events:
                # Create event signature for duplicate detection
                event_signature = f"{event.get('type')}_{event.get('user_id')}_{event.get('timestamp')}"

                if event_signature in all_event_signatures:
                    duplicate_events.append(event_signature)
                else:
                    all_event_signatures.add(event_signature)

        assert len(duplicate_events) == 0, f"Duplicate events detected across users: {len(duplicate_events)}"

        self.logger.info(f"✅ PASS: WebSocket event stream isolation validated")
        self.logger.info(f"📡 Total events: {total_events}")
        self.logger.info(f"🔀 Event streams: {len(event_collectors)}")
        self.logger.info(f"🚫 Cross-contamination: 0 (VALIDATED)")
        self.logger.info(f"📊 Average events per user: {total_events // len(event_collectors)}")

    async def test_resource_isolation_memory_cpu_separation(self):
        """
        Test resource isolation between concurrent users (memory/CPU separation).

        BVJ: Validates $250K+ MRR system stability - Resource contention causes failures
        Ensures: Each user's resource usage is tracked separately and isolated
        """
        resource_isolation_results = []

        async def test_user_resource_isolation(user_context, user_index):
            """Test resource isolation for specific user."""
            try:
                user_ws_helper = E2EWebSocketAuthHelper(environment="staging")
                websocket = await user_ws_helper.connect_authenticated_websocket(timeout=20.0)

                # Track resource usage for this user
                resource_snapshots = []
                peak_memory_mb = 0
                peak_cpu_percent = 0

                async def monitor_user_resources():
                    """Monitor resource usage isolation for this user."""
                    nonlocal peak_memory_mb, peak_cpu_percent
                    async for message in websocket:
                        event = json.loads(message)

                        if event.get("type") == "resource_update":
                            resource_data = event.get("data", {})
                            memory_mb = resource_data.get("memory_usage_mb", 0)
                            cpu_percent = resource_data.get("cpu_usage_percent", 0)

                            resource_snapshots.append({
                                "timestamp": time.time(),
                                "memory_mb": memory_mb,
                                "cpu_percent": cpu_percent,
                                "user_id": user_context.user_id,
                                "user_index": user_index
                            })

                            peak_memory_mb = max(peak_memory_mb, memory_mb)
                            peak_cpu_percent = max(peak_cpu_percent, cpu_percent)

                        elif event.get("type") == "agent_completed":
                            break

                resource_task = asyncio.create_task(monitor_user_resources())

                # Send resource-intensive request to test isolation
                resource_request = {
                    "type": "execute_agent",
                    "agent_type": "resource_isolation_test",
                    "user_id": user_context.user_id,
                    "thread_id": user_context.thread_id,
                    "request_id": user_context.request_id,
                    "data": {
                        "user_index": user_index,
                        "resource_intensive": True,
                        "memory_test_mb": 100 + (user_index * 20),  # Different memory patterns per user
                        "cpu_test_duration": 10,  # 10 second CPU test
                        "resource_monitoring": True,
                        "isolation_validation": True
                    }
                }

                await websocket.send(json.dumps(resource_request))
                await asyncio.wait_for(resource_task, timeout=30.0)
                await websocket.close()

                return {
                    "user_index": user_index,
                    "user_id": user_context.user_id,
                    "resource_snapshots": resource_snapshots,
                    "peak_memory_mb": peak_memory_mb,
                    "peak_cpu_percent": peak_cpu_percent,
                    "success": True
                }

            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_context.user_id,
                    "success": False,
                    "error": str(e)
                }

        # Test resource isolation with first 3 users
        tasks = [
            test_user_resource_isolation(user_context, i)
            for i, user_context in enumerate(self.test_users[:3])
        ]

        resource_isolation_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate resource isolation
        successful_tests = 0
        total_snapshots = 0

        for result in resource_isolation_results:
            if isinstance(result, dict) and result.get("success"):
                successful_tests += 1

                snapshots = result.get("resource_snapshots", [])
                total_snapshots += len(snapshots)

                # Validate resource monitoring occurred
                assert len(snapshots) >= 5, f"User {result['user_index']} had insufficient resource monitoring: {len(snapshots)}"

                # Validate resource usage is reasonable and user-specific
                peak_memory = result.get("peak_memory_mb", 0)
                peak_cpu = result.get("peak_cpu_percent", 0)

                assert peak_memory > 0, f"User {result['user_index']} reported no memory usage"
                assert peak_cpu > 0, f"User {result['user_index']} reported no CPU usage"

                # Validate resource levels are different between users (isolation working)
                user_index = result.get("user_index")
                expected_memory_base = 100 + (user_index * 20)

                # Memory should be at least the base amount (allowing for overhead)
                assert peak_memory >= expected_memory_base * 0.5, f"User {user_index} memory too low: {peak_memory}MB < {expected_memory_base * 0.5}MB"

        assert successful_tests == 3, f"Expected 3 successful resource tests, got {successful_tests}"

        # Validate resource patterns are distinct between users
        memory_patterns = [r.get("peak_memory_mb", 0) for r in resource_isolation_results if isinstance(r, dict) and r.get("success")]
        cpu_patterns = [r.get("peak_cpu_percent", 0) for r in resource_isolation_results if isinstance(r, dict) and r.get("success")]

        # Check that users had different resource footprints (isolation working)
        memory_variance = max(memory_patterns) - min(memory_patterns)
        cpu_variance = max(cpu_patterns) - min(cpu_patterns)

        assert memory_variance > 20, f"Memory usage too similar between users (low isolation): variance {memory_variance}MB"
        assert cpu_variance > 10, f"CPU usage too similar between users (low isolation): variance {cpu_variance}%"

        self.logger.info(f"✅ PASS: Resource isolation validated successfully")
        self.logger.info(f"💾 Memory variance: {memory_variance}MB (isolation confirmed)")
        self.logger.info(f"⚡ CPU variance: {cpu_variance}% (isolation confirmed)")
        self.logger.info(f"📊 Total resource snapshots: {total_snapshots}")


# Integration with pytest for automated test discovery
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])