"""
Test Golden Path Business Value Protection E2E

Focus: Complete business value validation in staging environment
Uses staging GCP deployment with real LLM.

Business Value Justification:
- Segment: Platform Infrastructure
- Business Goal: Revenue Protection ($500K+ ARR)
- Value Impact: Validate complete end-to-end chat experience delivers business value
- Strategic Impact: Protect mission-critical user workflows and revenue streams

Purpose: This test file validates complete Golden Path business value in staging.
Tests should FAIL initially due to routing conflicts, then PASS after consolidation.

Issue #1067: MessageRouter SSOT Consolidation Test Suite
"""

import pytest
import asyncio
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from unittest.mock import AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, AuthenticatedUser
from test_framework.ssot.real_websocket_connection_manager import RealWebSocketConnectionManager
from shared.isolated_environment import get_env


class GoldenPathBusinessValueProtectionE2ETests(SSotAsyncTestCase):
    """Test complete Golden Path business value in staging environment."""

    @pytest.fixture(scope="class")
    async def staging_environment(self):
        """Staging environment configuration."""
        return {
            "auth_url": get_env("STAGING_AUTH_URL", "https://auth.staging.netrasystems.ai"),
            "backend_url": get_env("STAGING_BACKEND_URL", "https://api.staging.netrasystems.ai"),
            "websocket_url": get_env("STAGING_WS_URL", "wss://api.staging.netrasystems.ai/ws"),
            "frontend_url": get_env("STAGING_FRONTEND_URL", "https://staging.netrasystems.ai")
        }

    @pytest.mark.e2e
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    @pytest.mark.asyncio
    async def test_complete_chat_experience_reliability(self, staging_environment):
        """CRITICAL TEST: End-to-end chat must deliver business value.

        This test validates the complete user experience and should initially
        FAIL due to routing conflicts, then PASS after SSOT consolidation.
        """
        business_value_metrics = {
            "chat_completion_success": False,
            "websocket_events_received": [],
            "agent_response_quality": False,
            "user_experience_smooth": False,
            "revenue_protecting_functionality": False
        }

        test_errors = []

        try:
            # Create E2E auth helper
            auth_helper = E2EAuthHelper(staging_environment["auth_url"])

            # Create real user for testing
            test_user_email = f"e2e-test-{uuid.uuid4()}@netrasystems.ai"

            try:
                # Create authenticated user
                test_user = await auth_helper.create_authenticated_user(
                    email=test_user_email,
                    subscription_tier="enterprise",
                    additional_claims={"test_type": "golden_path_business_value"}
                )

                auth_token = await auth_helper.get_auth_token(test_user)

                # Create WebSocket connection manager
                ws_manager = RealWebSocketConnectionManager(
                    base_url=staging_environment["backend_url"],
                    websocket_url=staging_environment["websocket_url"]
                )

                # Test complete chat experience
                async with ws_manager.create_authenticated_connection(auth_token) as websocket:

                    # Send business-critical message that represents real user value
                    business_message = {
                        "type": "agent_request",
                        "agent": "cost_optimizer",
                        "message": "Analyze my cloud costs and provide optimization recommendations",
                        "context": {
                            "monthly_budget": 50000,
                            "current_spend": 65000,
                            "priority": "cost_reduction",
                            "user_segment": "enterprise"
                        },
                        "user_id": test_user.user_id,
                        "session_id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat()
                    }

                    # Send the message
                    await websocket.send_json(business_message)

                    # Collect all WebSocket events
                    events = []
                    timeout_seconds = 60

                    try:
                        async with asyncio.timeout(timeout_seconds):
                            while True:
                                try:
                                    event = await websocket.receive_json()
                                    events.append(event)
                                    event_type = event.get("type")

                                    if event_type:
                                        business_value_metrics["websocket_events_received"].append(event_type)

                                    # Stop on completion event
                                    if event_type == "agent_completed":
                                        business_value_metrics["chat_completion_success"] = True
                                        break

                                except Exception as e:
                                    test_errors.append(f"Event reception error: {str(e)}")
                                    break

                    except asyncio.TimeoutError:
                        test_errors.append(f"Chat completion timeout after {timeout_seconds}s")

                    # Analyze business value delivery
                    required_events = ["agent_started", "agent_thinking", "tool_executing",
                                     "tool_completed", "agent_completed"]
                    events_received = business_value_metrics["websocket_events_received"]

                    # Check if all critical events were received
                    missing_events = set(required_events) - set(events_received)
                    if len(missing_events) == 0:
                        business_value_metrics["user_experience_smooth"] = True
                    else:
                        test_errors.append(f"Missing critical events: {missing_events}")

                    # Validate agent response quality
                    if events and business_value_metrics["chat_completion_success"]:
                        final_event = events[-1]
                        if final_event.get("type") == "agent_completed":
                            response_data = final_event.get("data", {})
                            result = response_data.get("result", {})

                            # Business value checks for cost optimization
                            has_recommendations = bool(result.get("recommendations"))
                            has_cost_savings = bool(result.get("cost_savings") or result.get("savings"))
                            has_actionable_insights = len(result.get("recommendations", [])) > 0

                            business_value_metrics["agent_response_quality"] = (
                                has_recommendations and (has_cost_savings or has_actionable_insights)
                            )

                            if business_value_metrics["agent_response_quality"]:
                                business_value_metrics["revenue_protecting_functionality"] = True

            except Exception as e:
                test_errors.append(f"Authentication or WebSocket setup failed: {str(e)}")

        except Exception as e:
            test_errors.append(f"Test infrastructure setup failed: {str(e)}")

        # Calculate overall business value score
        successful_metrics = sum([
            business_value_metrics["chat_completion_success"],
            business_value_metrics["user_experience_smooth"],
            business_value_metrics["agent_response_quality"],
            business_value_metrics["revenue_protecting_functionality"]
        ])

        business_value_score = successful_metrics / 4.0
        minimum_acceptable_score = 1.0  # 100% - business critical

        # This assertion protects $500K+ ARR functionality
        assert business_value_score >= minimum_acceptable_score, (
            f"BUSINESS VALUE FAILURE: Golden Path score {business_value_score:.2%} "
            f"below minimum {minimum_acceptable_score:.2%}. "
            f"Metrics: {business_value_metrics}. "
            f"Errors: {test_errors}. "
            f"This failure impacts $500K+ ARR chat functionality and demonstrates "
            f"SSOT violations that break revenue-generating user workflows."
        )

    @pytest.mark.e2e
    @pytest.mark.real_llm
    @pytest.mark.user_isolation
    @pytest.mark.asyncio
    async def test_multi_user_chat_scalability(self, staging_environment):
        """FAILING TEST: Multiple users should have isolated, reliable chat.

        This test should initially FAIL due to routing conflicts.
        """
        user_count = 3
        concurrent_chat_results = []
        isolation_violations = []

        async def single_user_chat_test(user_index: int) -> Dict[str, any]:
            """Test chat functionality for a single user."""
            user_result = {
                "user_index": user_index,
                "success": False,
                "errors": [],
                "events_received": [],
                "response_data": None
            }

            try:
                auth_helper = E2EAuthHelper(staging_environment["auth_url"])

                # Create unique user
                test_user = await auth_helper.create_authenticated_user(
                    email=f"concurrent-user-{user_index}-{uuid.uuid4()}@netrasystems.ai",
                    subscription_tier="enterprise",
                    additional_claims={"user_index": user_index}
                )
                auth_token = await auth_helper.get_auth_token(test_user)

                # Test chat functionality
                ws_manager = RealWebSocketConnectionManager(
                    base_url=staging_environment["backend_url"],
                    websocket_url=staging_environment["websocket_url"]
                )

                async with ws_manager.create_authenticated_connection(auth_token) as websocket:
                    message = {
                        "type": "agent_request",
                        "message": f"User {user_index} unique optimization request - confidential data {user_index}",
                        "agent": "triage_agent",
                        "user_id": test_user.user_id,
                        "confidential_marker": f"SECRET_USER_{user_index}_DATA"
                    }

                    await websocket.send_json(message)

                    # Wait for completion with timeout
                    try:
                        async with asyncio.timeout(30):
                            while True:
                                event = await websocket.receive_json()
                                event_type = event.get("type")
                                user_result["events_received"].append(event_type)

                                # Check for isolation violations
                                event_content = str(event)
                                for other_user in range(user_count):
                                    if other_user != user_index:
                                        secret_marker = f"SECRET_USER_{other_user}_DATA"
                                        if secret_marker in event_content:
                                            isolation_violations.append(
                                                f"User {user_index} received User {other_user}'s confidential data"
                                            )

                                if event_type == "agent_completed":
                                    user_result["success"] = True
                                    user_result["response_data"] = event.get("data")
                                    break

                    except asyncio.TimeoutError:
                        user_result["errors"].append("Timeout waiting for completion")

            except Exception as e:
                user_result["errors"].append(f"User {user_index} test failed: {str(e)}")

            return user_result

        # Run concurrent chat tests
        results = await asyncio.gather(
            *[single_user_chat_test(i) for i in range(user_count)],
            return_exceptions=True
        )

        # Analyze results
        successful_chats = sum(1 for result in results if isinstance(result, dict) and result.get("success"))
        failed_results = [result for result in results if not (isinstance(result, dict) and result.get("success"))]

        success_rate = successful_chats / user_count
        minimum_success_rate = 0.95  # 95%

        # Check for cross-user data contamination
        all_errors = []
        if isolation_violations:
            all_errors.extend(isolation_violations)

        for result in results:
            if isinstance(result, dict) and result.get("errors"):
                all_errors.extend(result["errors"])

        # This assertion should FAIL initially due to routing conflicts
        assert success_rate >= minimum_success_rate and len(isolation_violations) == 0, (
            f"MULTI-USER SCALABILITY FAILURE: Success rate {success_rate:.2%} "
            f"below minimum {minimum_success_rate:.2%}. "
            f"Successful: {successful_chats}/{user_count}. "
            f"Isolation violations: {len(isolation_violations)}. "
            f"Failed results: {failed_results}. "
            f"All errors: {all_errors}. "
            f"This demonstrates critical SSOT violations that break multi-user chat reliability."
        )

    @pytest.mark.e2e
    @pytest.mark.real_llm
    @pytest.mark.websocket_events
    @pytest.mark.asyncio
    async def test_websocket_event_delivery_reliability(self, staging_environment):
        """FAILING TEST: All WebSocket events should be delivered reliably.

        This test should FAIL initially due to event routing fragmentation.
        """
        event_reliability_metrics = {
            "total_events_expected": 0,
            "total_events_received": 0,
            "event_delivery_rate": 0.0,
            "missing_event_types": [],
            "duplicate_events": [],
            "out_of_order_events": []
        }

        try:
            auth_helper = E2EAuthHelper(staging_environment["auth_url"])
            test_user = await auth_helper.create_authenticated_user(
                email=f"event-reliability-test-{uuid.uuid4()}@netrasystems.ai",
                subscription_tier="enterprise"
            )
            auth_token = await auth_helper.get_auth_token(test_user)

            ws_manager = RealWebSocketConnectionManager(
                base_url=staging_environment["backend_url"],
                websocket_url=staging_environment["websocket_url"]
            )

            async with ws_manager.create_authenticated_connection(auth_token) as websocket:
                # Send a message that should generate all 5 events
                test_message = {
                    "type": "agent_request",
                    "message": "Generate all WebSocket events for reliability test",
                    "agent": "data_helper_agent",
                    "user_id": test_user.user_id
                }

                await websocket.send_json(test_message)

                # Track event sequence
                events_received = []
                expected_sequence = ["agent_started", "agent_thinking", "tool_executing",
                                   "tool_completed", "agent_completed"]
                event_reliability_metrics["total_events_expected"] = len(expected_sequence)

                try:
                    async with asyncio.timeout(45):
                        while True:
                            event = await websocket.receive_json()
                            event_type = event.get("type")

                            if event_type in expected_sequence:
                                events_received.append(event_type)

                            if event_type == "agent_completed":
                                break

                except asyncio.TimeoutError:
                    pass  # Continue with analysis

                event_reliability_metrics["total_events_received"] = len(events_received)
                event_reliability_metrics["event_delivery_rate"] = len(events_received) / len(expected_sequence)

                # Check for missing events
                missing_events = set(expected_sequence) - set(events_received)
                event_reliability_metrics["missing_event_types"] = list(missing_events)

                # Check for duplicates
                seen_events = set()
                for event in events_received:
                    if event in seen_events:
                        event_reliability_metrics["duplicate_events"].append(event)
                    seen_events.add(event)

                # Check sequence order
                if events_received != expected_sequence[:len(events_received)]:
                    event_reliability_metrics["out_of_order_events"] = events_received

        except Exception as e:
            # Test setup failure indicates severe routing issues
            event_reliability_metrics["setup_error"] = str(e)

        # Reliability thresholds
        minimum_delivery_rate = 1.0  # 100%
        max_missing_events = 0
        max_duplicate_events = 0

        actual_delivery_rate = event_reliability_metrics["event_delivery_rate"]
        missing_count = len(event_reliability_metrics["missing_event_types"])
        duplicate_count = len(event_reliability_metrics["duplicate_events"])

        # This assertion should FAIL initially due to event delivery fragmentation
        assert (actual_delivery_rate >= minimum_delivery_rate and
                missing_count <= max_missing_events and
                duplicate_count <= max_duplicate_events), (
            f"WEBSOCKET EVENT RELIABILITY FAILURE: "
            f"Delivery rate: {actual_delivery_rate:.2%} (minimum: {minimum_delivery_rate:.2%}), "
            f"Missing events: {missing_count} (max: {max_missing_events}), "
            f"Duplicate events: {duplicate_count} (max: {max_duplicate_events}). "
            f"Metrics: {event_reliability_metrics}. "
            f"This demonstrates WebSocket event routing SSOT violations that break user experience."
        )