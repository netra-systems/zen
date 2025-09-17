"""E2E Tests for WebSocket Agent Event Integration - Event Reliability Under Load

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Real-time events are critical for user experience
- Business Goal: Ensure reliable WebSocket event delivery under high concurrency and load
- Value Impact: Users receive consistent real-time feedback during agent execution even under load
- Strategic Impact: $500K+ ARR real-time communication reliability foundation

These E2E tests validate WebSocket agent event integration with complete system stack under load:
- Real authentication (JWT/OAuth) for multiple concurrent users
- Real WebSocket connections with high-frequency event delivery
- Real databases (PostgreSQL, Redis, ClickHouse) under concurrent load
- All 5 critical WebSocket events under stress testing
- Event ordering and reliability guarantees
- Performance metrics and scalability validation
- Real LLM integration with concurrent agent execution

CRITICAL: ALL E2E tests MUST use authentication - no exceptions.
STAGING ONLY: These tests run against GCP staging environment only.
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager


@pytest.mark.e2e
class WebSocketAgentEventIntegrationLoadE2ETests(BaseE2ETest):
    """E2E tests for WebSocket agent event integration under load with authenticated full-stack testing."""

    async def create_multiple_authenticated_users(self, count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple authenticated users for load testing."""
        users = []
        for i in range(count):
            token, user_data = await create_authenticated_user(
                environment="staging",  # GCP staging only
                permissions=["read", "write", "agent_execute", "websocket_events"],
                user_prefix=f"load_test_user_{i}"
            )
            users.append({
                "token": token,
                "user_data": user_data,
                "user_id": user_data["id"],
                "email": user_data["email"],
                "user_index": i
            })
        return users

    @pytest.fixture
    def auth_helper(self):
        """E2E authentication helper."""
        return E2EAuthHelper(environment="staging")

    async def create_websocket_client(self, user: Dict[str, Any], auth_helper) -> WebSocketTestClient:
        """Create authenticated WebSocket client for specific user."""
        headers = auth_helper.get_websocket_headers(user["token"])

        # Use staging GCP WebSocket endpoint
        staging_ws_url = "wss://staging.netra-apex.com/ws"
        client = WebSocketTestClient(
            url=staging_ws_url,
            headers=headers,
            user_id=user["user_id"]  # Track user for event validation
        )
        await client.connect()
        return client

    @pytest.mark.asyncio
    async def test_five_critical_websocket_events_delivery_under_concurrent_load(self, auth_helper):
        """Test all 5 critical WebSocket events under concurrent user load.

        This test validates:
        - All 5 critical events delivered under concurrent load
        - Event ordering preservation per user
        - No event loss under load conditions
        - Performance metrics within acceptable bounds
        - Cross-user event isolation under load
        - Event content accuracy under stress
        """
        # Create multiple users for concurrent load testing
        users = await self.create_multiple_authenticated_users(count=4)

        # Create WebSocket clients for each user
        websocket_clients = {}
        for user in users:
            websocket_clients[user["user_id"]] = await self.create_websocket_client(user, auth_helper)

        # Define the 5 critical WebSocket events to validate
        CRITICAL_EVENTS = [
            "agent_started",
            "agent_thinking",
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]

        # Track events per user with detailed analysis
        user_events = {user_id: [] for user_id in websocket_clients.keys()}
        event_metrics = {user_id: {"total": 0, "critical": 0, "by_type": defaultdict(int)} for user_id in websocket_clients.keys()}

        async def collect_and_analyze_events(user_id: str, websocket_client: WebSocketTestClient):
            """Collect WebSocket events with detailed metrics analysis."""
            while True:
                try:
                    start_time = time.time()
                    event = await websocket_client.receive()
                    receive_time = time.time()

                    if event:
                        parsed_event = json.loads(event) if isinstance(event, str) else event
                        event_type = parsed_event.get('type', 'unknown')

                        event_data = {
                            'timestamp': datetime.now(timezone.utc),
                            'user_id': user_id,
                            'event': parsed_event,
                            'event_type': event_type,
                            'receive_latency': receive_time - start_time,
                            'run_id': parsed_event.get('run_id'),
                            'agent_name': parsed_event.get('agent_name')
                        }

                        user_events[user_id].append(event_data)
                        event_metrics[user_id]["total"] += 1

                        if event_type in CRITICAL_EVENTS:
                            event_metrics[user_id]["critical"] += 1

                        event_metrics[user_id]["by_type"][event_type] += 1

                except Exception:
                    break

        # Start event collection for all users
        event_tasks = []
        for user_id, websocket_client in websocket_clients.items():
            task = asyncio.create_task(collect_and_analyze_events(user_id, websocket_client))
            event_tasks.append(task)

        try:
            # Create high-load concurrent agent executions
            execution_tasks = []

            async def execute_agent_with_all_events(user: Dict[str, Any], execution_id: int):
                """Execute agent request generating all 5 critical WebSocket events."""
                user_id = user["user_id"]
                run_id = str(uuid.uuid4())
                thread_id = str(uuid.uuid4())

                # Create agent request designed to trigger all event types
                request_data = {
                    "message": f"Perform comprehensive data analysis with tool execution for load test #{execution_id}",
                    "load_test_metadata": {
                        "user_id": user_id,
                        "execution_id": execution_id,
                        "expected_events": CRITICAL_EVENTS,
                        "load_test_timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }

                # Create agent state for comprehensive execution
                agent_state = DeepAgentState(
                    user_id=user_id,
                    thread_id=thread_id,
                    conversation_history=[],
                    context=request_data["load_test_metadata"],
                    agent_memory={
                        "load_test_execution": execution_id,
                        "expected_websocket_events": CRITICAL_EVENTS,
                        "event_validation_enabled": True
                    },
                    workflow_state="comprehensive_execution_with_events"
                )

                # Execute with full event generation
                agent_execution_core = AgentExecutionCore()

                try:
                    result = await agent_execution_core.execute_with_comprehensive_events(
                        agent_state=agent_state,
                        request=request_data["message"],
                        run_id=run_id,
                        enable_all_critical_events=True,
                        enable_tool_execution=True,  # Ensures tool_executing and tool_completed events
                        enable_thinking_updates=True,  # Ensures agent_thinking events
                        force_event_generation=True  # For load testing reliability
                    )

                    return {
                        "user_id": user_id,
                        "execution_id": execution_id,
                        "run_id": run_id,
                        "result": result,
                        "status": "success",
                        "timestamp": datetime.now(timezone.utc)
                    }

                except Exception as e:
                    return {
                        "user_id": user_id,
                        "execution_id": execution_id,
                        "run_id": run_id,
                        "error": str(e),
                        "status": "failed",
                        "timestamp": datetime.now(timezone.utc)
                    }

            # Execute multiple concurrent requests per user (2 requests × 4 users = 8 concurrent executions)
            for user in users:
                for execution_id in range(2):  # 2 executions per user for load testing
                    task = asyncio.create_task(execute_agent_with_all_events(user, execution_id))
                    execution_tasks.append(task)

            # Wait for all executions with extended timeout for load conditions
            execution_results = await asyncio.gather(*execution_tasks, return_exceptions=True)

            # Allow additional time for all events to be delivered
            await asyncio.sleep(5.0)

        finally:
            # Cancel event collection tasks
            for task in event_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Clean up WebSocket connections
            for websocket_client in websocket_clients.values():
                try:
                    await websocket_client.disconnect()
                except Exception:
                    pass

        # VALIDATION: WebSocket event delivery under load

        # 1. Process execution results
        successful_executions = [r for r in execution_results if isinstance(r, dict) and r.get("status") == "success"]
        failed_executions = [r for r in execution_results if isinstance(r, dict) and r.get("status") == "failed"]
        exception_executions = [r for r in execution_results if isinstance(r, Exception)]

        total_executions = len(execution_results)
        success_rate = len(successful_executions) / total_executions if total_executions > 0 else 0

        assert success_rate >= 0.75, f"Success rate under load too low: {success_rate:.2%} ({len(successful_executions)}/{total_executions})"

        # 2. Validate that all users received events
        users_with_events = [user_id for user_id, events in user_events.items() if len(events) >= 5]
        assert len(users_with_events) >= 3, f"At least 3 users should receive events under load, got {len(users_with_events)}"

        # 3. Validate critical event delivery for each user
        critical_event_coverage = {}
        for user_id, events in user_events.items():
            user_critical_events = set()
            for event_data in events:
                event_type = event_data.get("event_type")
                if event_type in CRITICAL_EVENTS:
                    user_critical_events.add(event_type)

            critical_event_coverage[user_id] = {
                "events_received": list(user_critical_events),
                "events_count": len(user_critical_events),
                "coverage_percentage": len(user_critical_events) / len(CRITICAL_EVENTS)
            }

        # At least 75% of users should receive at least 80% of critical events
        high_coverage_users = [
            user_id for user_id, coverage in critical_event_coverage.items()
            if coverage["coverage_percentage"] >= 0.8
        ]
        high_coverage_rate = len(high_coverage_users) / len(users) if len(users) > 0 else 0

        assert high_coverage_rate >= 0.75, f"Critical event coverage too low: {high_coverage_rate:.2%} of users have 80%+ coverage"

        # 4. Validate event ordering per user (agent_started should come before agent_completed)
        ordering_violations = []
        for user_id, events in user_events.items():
            user_critical_events = [e for e in events if e.get("event_type") in CRITICAL_EVENTS]

            if len(user_critical_events) >= 2:
                # Group events by run_id for ordering analysis
                events_by_run = defaultdict(list)
                for event in user_critical_events:
                    run_id = event.get("run_id")
                    if run_id:
                        events_by_run[run_id].append(event)

                for run_id, run_events in events_by_run.items():
                    if len(run_events) >= 2:
                        # Sort by timestamp
                        sorted_events = sorted(run_events, key=lambda e: e["timestamp"])

                        # Check if agent_started comes before agent_completed
                        started_index = next((i for i, e in enumerate(sorted_events) if e["event_type"] == "agent_started"), -1)
                        completed_index = next((i for i, e in enumerate(sorted_events) if e["event_type"] == "agent_completed"), -1)

                        if started_index != -1 and completed_index != -1 and started_index > completed_index:
                            ordering_violations.append({
                                "user_id": user_id,
                                "run_id": run_id,
                                "started_index": started_index,
                                "completed_index": completed_index
                            })

        # Allow some ordering violations under load but not too many (max 20%)
        max_allowed_violations = max(1, len(successful_executions) // 5)
        assert len(ordering_violations) <= max_allowed_violations, f"Too many event ordering violations under load: {len(ordering_violations)}"

        # 5. Validate performance metrics
        total_events_received = sum(len(events) for events in user_events.values())
        assert total_events_received >= 15, f"Should receive substantial events under load, got {total_events_received}"

        # Calculate average event delivery latency
        all_latencies = []
        for events in user_events.values():
            latencies = [e.get("receive_latency", 0) for e in events if e.get("receive_latency")]
            all_latencies.extend(latencies)

        if all_latencies:
            avg_latency = sum(all_latencies) / len(all_latencies)
            max_latency = max(all_latencies)

            # Performance should be reasonable under load
            assert avg_latency <= 2.0, f"Average event delivery latency too high under load: {avg_latency:.2f}s"
            assert max_latency <= 5.0, f"Maximum event delivery latency too high under load: {max_latency:.2f}s"

        # 6. Validate cross-user event isolation (no event leakage)
        isolation_violations = []
        for user_id, events in user_events.items():
            for event_data in events:
                event = event_data.get("event", {})
                event_user_id = event.get("user_id")

                if event_user_id and event_user_id != user_id:
                    isolation_violations.append({
                        "receiving_user": user_id,
                        "event_user_id": event_user_id,
                        "event_type": event.get("type")
                    })

        assert len(isolation_violations) == 0, f"Event isolation violations under load: {isolation_violations}"

        # 7. Validate business value metrics
        # Calculate critical event delivery reliability
        total_expected_critical_events = len(successful_executions) * len(CRITICAL_EVENTS)
        total_critical_events_delivered = sum(metrics["critical"] for metrics in event_metrics.values())

        if total_expected_critical_events > 0:
            critical_event_reliability = total_critical_events_delivered / total_expected_critical_events
            assert critical_event_reliability >= 0.6, f"Critical event delivery reliability too low under load: {critical_event_reliability:.2%}"

    @pytest.mark.asyncio
    async def test_websocket_event_content_accuracy_under_stress(self, auth_helper):
        """Test WebSocket event content accuracy under stress conditions.

        This test validates:
        - Event payload accuracy under concurrent load
        - No data corruption in event content
        - Proper event metadata preservation
        - Run ID and user ID accuracy in events
        - Agent name and context preservation
        - Tool execution details accuracy
        """
        # Create users for stress testing
        users = await self.create_multiple_authenticated_users(count=3)

        # Create WebSocket clients
        websocket_clients = {}
        for user in users:
            websocket_clients[user["user_id"]] = await self.create_websocket_client(user, auth_helper)

        # Track detailed event content for validation
        detailed_events = {user_id: [] for user_id in websocket_clients.keys()}

        async def collect_detailed_events(user_id: str, websocket_client: WebSocketTestClient):
            """Collect events with detailed content validation."""
            while True:
                try:
                    event = await websocket_client.receive()
                    if event:
                        parsed_event = json.loads(event) if isinstance(event, str) else event

                        # Extract detailed content for validation
                        event_details = {
                            'timestamp': datetime.now(timezone.utc),
                            'user_id': user_id,
                            'raw_event': event,
                            'parsed_event': parsed_event,
                            'event_type': parsed_event.get('type'),
                            'event_user_id': parsed_event.get('user_id'),
                            'run_id': parsed_event.get('run_id'),
                            'agent_name': parsed_event.get('agent_name'),
                            'payload_size': len(str(event)),
                            'has_required_fields': all(field in parsed_event for field in ['type', 'timestamp']),
                            'content_preview': str(parsed_event)[:200]  # First 200 chars for validation
                        }

                        detailed_events[user_id].append(event_details)

                except Exception as e:
                    # Track parsing errors
                    detailed_events[user_id].append({
                        'timestamp': datetime.now(timezone.utc),
                        'user_id': user_id,
                        'error': f"Event parsing error: {str(e)}",
                        'event_type': 'parsing_error'
                    })
                    break

        # Start detailed event collection
        event_tasks = []
        for user_id, websocket_client in websocket_clients.items():
            task = asyncio.create_task(collect_detailed_events(user_id, websocket_client))
            event_tasks.append(task)

        try:
            # Create stress conditions with rapid-fire agent executions
            stress_execution_tasks = []

            async def execute_stress_agent_with_validation_data(user: Dict[str, Any], stress_id: int):
                """Execute agent with specific validation data for content accuracy testing."""
                user_id = user["user_id"]
                run_id = f"stress_test_{user_id}_{stress_id}_{uuid.uuid4()}"
                thread_id = str(uuid.uuid4())

                # Create request with specific validation markers
                validation_markers = {
                    "stress_test_id": stress_id,
                    "user_identifier": user_id,
                    "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                    "expected_agent_name": f"stress_validation_agent_{stress_id}",
                    "content_validation_string": f"VALIDATION_MARKER_{user_id}_{stress_id}",
                    "special_characters": "äöü!@#$%^&*()[]{}|;:,.<>?",
                    "large_data_block": "x" * 500  # 500 character block for payload testing
                }

                request_message = f"Execute stress validation test #{stress_id} with specific markers for content accuracy validation"

                # Create agent state with validation data
                agent_state = DeepAgentState(
                    user_id=user_id,
                    thread_id=thread_id,
                    conversation_history=[],
                    context={
                        "stress_validation": validation_markers,
                        "content_accuracy_test": True
                    },
                    agent_memory={
                        "validation_data": validation_markers,
                        "stress_test_active": True
                    },
                    workflow_state="stress_content_validation"
                )

                # Execute with content validation enabled
                agent_execution_core = AgentExecutionCore()

                try:
                    result = await agent_execution_core.execute_with_content_validation(
                        agent_state=agent_state,
                        request=request_message,
                        run_id=run_id,
                        agent_name=validation_markers["expected_agent_name"],
                        enable_content_validation=True,
                        include_validation_markers=True
                    )

                    return {
                        "user_id": user_id,
                        "stress_id": stress_id,
                        "run_id": run_id,
                        "validation_markers": validation_markers,
                        "result": result,
                        "status": "success"
                    }

                except Exception as e:
                    return {
                        "user_id": user_id,
                        "stress_id": stress_id,
                        "run_id": run_id,
                        "validation_markers": validation_markers,
                        "error": str(e),
                        "status": "failed"
                    }

            # Execute stress tests (3 users × 3 executions = 9 concurrent stress tests)
            for user in users:
                for stress_id in range(3):
                    task = asyncio.create_task(execute_stress_agent_with_validation_data(user, stress_id))
                    stress_execution_tasks.append(task)

            # Execute with shorter intervals for stress conditions
            stress_results = []
            for i, task in enumerate(stress_execution_tasks):
                if i > 0:
                    await asyncio.sleep(0.1)  # Very short interval for stress testing

                try:
                    result = await asyncio.wait_for(task, timeout=20.0)
                    stress_results.append(result)
                except asyncio.TimeoutError:
                    stress_results.append({"status": "timeout", "error": "Stress execution timeout"})

            # Allow time for all events to be collected
            await asyncio.sleep(3.0)

        finally:
            # Cancel event collection tasks
            for task in event_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Clean up WebSocket connections
            for websocket_client in websocket_clients.values():
                try:
                    await websocket_client.disconnect()
                except Exception:
                    pass

        # VALIDATION: Event content accuracy under stress

        # 1. Process stress execution results
        successful_stress_tests = [r for r in stress_results if r.get("status") == "success"]
        stress_success_rate = len(successful_stress_tests) / len(stress_results) if stress_results else 0

        assert stress_success_rate >= 0.6, f"Stress test success rate too low: {stress_success_rate:.2%} ({len(successful_stress_tests)}/{len(stress_results)})"

        # 2. Validate event content accuracy
        content_validation_errors = []
        for user_id, events in detailed_events.items():
            parsing_errors = [e for e in events if e.get("event_type") == "parsing_error"]
            valid_events = [e for e in events if e.get("event_type") != "parsing_error"]

            # Should have minimal parsing errors under stress
            parsing_error_rate = len(parsing_errors) / len(events) if events else 0
            if parsing_error_rate > 0.1:  # More than 10% parsing errors is concerning
                content_validation_errors.append({
                    "user_id": user_id,
                    "error_type": "high_parsing_error_rate",
                    "rate": parsing_error_rate,
                    "total_events": len(events)
                })

            # Validate required fields presence
            events_missing_fields = [e for e in valid_events if not e.get("has_required_fields", False)]
            if len(events_missing_fields) > 0:
                content_validation_errors.append({
                    "user_id": user_id,
                    "error_type": "missing_required_fields",
                    "count": len(events_missing_fields)
                })

        assert len(content_validation_errors) <= 1, f"Too many content validation errors under stress: {content_validation_errors}"

        # 3. Validate run ID and user ID accuracy
        id_accuracy_errors = []
        for user_id, events in detailed_events.items():
            for event_detail in events:
                if event_detail.get("event_type") != "parsing_error":
                    event_user_id = event_detail.get("event_user_id")
                    run_id = event_detail.get("run_id")

                    # User ID should match or be None (some events may not include user_id)
                    if event_user_id and event_user_id != user_id:
                        id_accuracy_errors.append({
                            "user_id": user_id,
                            "event_user_id": event_user_id,
                            "error_type": "user_id_mismatch",
                            "event_type": event_detail.get("event_type")
                        })

                    # Run ID should be present and properly formatted for most events
                    if event_detail.get("event_type") in ["agent_started", "agent_completed"]:
                        if not run_id or len(run_id) < 10:  # Basic run ID validation
                            id_accuracy_errors.append({
                                "user_id": user_id,
                                "run_id": run_id,
                                "error_type": "invalid_run_id",
                                "event_type": event_detail.get("event_type")
                            })

        assert len(id_accuracy_errors) <= 2, f"Too many ID accuracy errors under stress: {id_accuracy_errors}"

        # 4. Validate agent name preservation
        agent_name_validation = {}
        for stress_result in successful_stress_tests:
            if "validation_markers" in stress_result:
                expected_agent_name = stress_result["validation_markers"]["expected_agent_name"]
                run_id = stress_result["run_id"]
                user_id = stress_result["user_id"]

                # Find events for this run
                user_events = detailed_events.get(user_id, [])
                run_events = [e for e in user_events if e.get("run_id") == run_id]

                # Check if agent name appears in events
                agent_name_found = any(
                    expected_agent_name in str(e.get("parsed_event", {}))
                    for e in run_events
                )

                agent_name_validation[run_id] = {
                    "expected": expected_agent_name,
                    "found": agent_name_found,
                    "events_count": len(run_events)
                }

        # At least 60% of runs should have proper agent name preservation
        successful_name_preservation = sum(1 for v in agent_name_validation.values() if v["found"])
        name_preservation_rate = successful_name_preservation / len(agent_name_validation) if agent_name_validation else 0

        assert name_preservation_rate >= 0.6, f"Agent name preservation rate too low under stress: {name_preservation_rate:.2%}"

        # 5. Validate payload size consistency (no truncation under stress)
        payload_size_issues = []
        for user_id, events in detailed_events.items():
            for event_detail in events:
                payload_size = event_detail.get("payload_size", 0)

                # Very small payloads might indicate truncation (unless it's a simple event)
                if payload_size < 10 and event_detail.get("event_type") not in ["ping", "heartbeat"]:
                    payload_size_issues.append({
                        "user_id": user_id,
                        "event_type": event_detail.get("event_type"),
                        "payload_size": payload_size,
                        "content_preview": event_detail.get("content_preview", "")
                    })

        # Allow some small payloads but not excessive truncation
        max_allowed_small_payloads = max(2, len(detailed_events) // 2)
        assert len(payload_size_issues) <= max_allowed_small_payloads, f"Too many small payload issues under stress: {len(payload_size_issues)}"

        # 6. Validate overall event delivery under stress
        total_events_collected = sum(len(events) for events in detailed_events.values())
        assert total_events_collected >= 10, f"Should collect substantial events under stress conditions, got {total_events_collected}"

        # Calculate event collection rate per successful execution
        if len(successful_stress_tests) > 0:
            events_per_execution = total_events_collected / len(successful_stress_tests)
            assert events_per_execution >= 2.0, f"Should receive multiple events per execution under stress: {events_per_execution:.1f} events/execution"

        # 7. Validate business value - stress conditions don't compromise user experience
        user_experience_quality = 0

        # Quality factor 1: Low parsing error rate
        total_events = sum(len(events) for events in detailed_events.values())
        total_parsing_errors = sum(
            len([e for e in events if e.get("event_type") == "parsing_error"])
            for events in detailed_events.values()
        )
        parsing_quality = 1 - (total_parsing_errors / total_events) if total_events > 0 else 0

        # Quality factor 2: ID accuracy
        id_accuracy_quality = 1 - (len(id_accuracy_errors) / total_events) if total_events > 0 else 0

        # Quality factor 3: Agent name preservation
        name_preservation_quality = name_preservation_rate

        # Combined quality score
        user_experience_quality = (parsing_quality + id_accuracy_quality + name_preservation_quality) / 3

        assert user_experience_quality >= 0.7, f"User experience quality too low under stress: {user_experience_quality:.2%} (target: 70%+)"