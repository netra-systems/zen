"""
E2E Tests - Golden Path Chat Functionality for Issue #1099

Test Purpose: Validate complete user journey with migrated handlers on GCP staging
Expected Initial State: FAIL - Handler conflicts break Golden Path

Environment: GCP Staging (https://auth.staging.netrasystems.ai)
Dependencies: Real WebSocket connections, JWT authentication, LLM API integration

Business Value Justification:
- Segment: Platform/Enterprise (Customer-facing functionality)
- Business Goal: Ensure Golden Path chat functionality works end-to-end
- Value Impact: Validate complete user journey from login to agent completion
- Revenue Impact: Protect $500K+ ARR by ensuring customer-facing features work

🔍 These tests are designed to INITIALLY FAIL to demonstrate Golden Path breaking
"""

import asyncio
import json
import time
import pytest
import websockets
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import uuid

# HTTP client for staging API calls
try:
    import httpx
    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False

# WebSocket client
try:
    import websockets
    WEBSOCKET_CLIENT_AVAILABLE = True
except ImportError:
    WEBSOCKET_CLIENT_AVAILABLE = False

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# GCP Staging configuration
STAGING_CONFIG = {
    "auth_url": "https://auth.staging.netrasystems.ai",
    "api_url": "https://api.staging.netrasystems.ai",
    "websocket_url": "wss://api.staging.netrasystems.ai/ws",
    "timeout": 30.0
}

# Test user configurations for staging
TEST_USERS = [
    {
        "username": "test_user_1099_legacy",
        "password": "test_password_secure_123",
        "email": "test1099legacy@example.com"
    },
    {
        "username": "test_user_1099_ssot",
        "password": "test_password_secure_456",
        "email": "test1099ssot@example.com"
    }
]


class TestGoldenPathMessageHandlerMigration:
    """E2E tests for complete Golden Path functionality on GCP staging"""

    @pytest.fixture(scope="class")
    async def staging_available(self):
        """Check if GCP staging environment is accessible"""
        if not HTTP_CLIENT_AVAILABLE:
            pytest.skip("HTTP client not available for staging tests")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{STAGING_CONFIG['auth_url']}/health")

                if response.status_code != 200:
                    pytest.skip(f"GCP staging not accessible: {response.status_code}")

            return True

        except Exception as e:
            pytest.skip(f"GCP staging environment not accessible: {e}")

    @pytest.fixture(scope="function")
    async def staging_authentication(self, staging_available):
        """Authenticate test users on staging"""
        if not HTTP_CLIENT_AVAILABLE:
            pytest.skip("HTTP client not available")

        authenticated_users = {}

        async with httpx.AsyncClient(timeout=STAGING_CONFIG["timeout"]) as client:
            for user_config in TEST_USERS:
                try:
                    # Attempt login
                    login_data = {
                        "username": user_config["username"],
                        "password": user_config["password"]
                    }

                    login_response = await client.post(
                        f"{STAGING_CONFIG['auth_url']}/auth/login",
                        json=login_data
                    )

                    if login_response.status_code == 200:
                        auth_data = login_response.json()
                        authenticated_users[user_config["username"]] = {
                            "jwt_token": auth_data.get("access_token"),
                            "user_id": auth_data.get("user_id"),
                            "config": user_config
                        }

                    elif login_response.status_code == 404:
                        # User doesn't exist, try to create
                        register_data = {
                            "username": user_config["username"],
                            "email": user_config["email"],
                            "password": user_config["password"]
                        }

                        register_response = await client.post(
                            f"{STAGING_CONFIG['auth_url']}/auth/register",
                            json=register_data
                        )

                        if register_response.status_code == 201:
                            # Now login
                            login_response = await client.post(
                                f"{STAGING_CONFIG['auth_url']}/auth/login",
                                json=login_data
                            )

                            if login_response.status_code == 200:
                                auth_data = login_response.json()
                                authenticated_users[user_config["username"]] = {
                                    "jwt_token": auth_data.get("access_token"),
                                    "user_id": auth_data.get("user_id"),
                                    "config": user_config
                                }

                except Exception as e:
                    logger.warning(f"Authentication failed for {user_config['username']}: {e}")

        if not authenticated_users:
            pytest.skip("No users could be authenticated on staging")

        return authenticated_users

    @pytest.mark.asyncio
    async def test_complete_chat_flow_legacy_baseline(self, staging_authentication):
        """
        Test: Establish baseline with legacy handler patterns
        Expected: FAIL - Legacy patterns may not work on staging due to conflicts
        """
        if not WEBSOCKET_CLIENT_AVAILABLE:
            pytest.skip("WebSocket client not available")

        # Use first authenticated user for legacy baseline test
        user_data = next(iter(staging_authentication.values()))
        jwt_token = user_data["jwt_token"]
        user_id = user_data["user_id"]

        logger.info(f"Testing legacy baseline for user: {user_id}")

        golden_path_steps = []
        websocket_events = []

        try:
            # Step 1: Establish WebSocket connection
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}"

            golden_path_steps.append("connecting_websocket")

            async with websockets.connect(
                websocket_url,
                timeout=STAGING_CONFIG["timeout"]
            ) as websocket:

                golden_path_steps.append("websocket_connected")

                # Step 2: Send initial user message
                user_message = {
                    "type": "user_message",
                    "content": "Hello, I need help with analyzing my data. Can you help me create a simple report?",
                    "user_id": user_id,
                    "thread_id": f"legacy_test_{uuid.uuid4()}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_marker": "legacy_baseline"
                }

                golden_path_steps.append("sending_user_message")

                await websocket.send(json.dumps(user_message))

                golden_path_steps.append("user_message_sent")

                # Step 3: Wait for and collect WebSocket events
                expected_events = [
                    "agent_started",
                    "agent_thinking",
                    "agent_progress",
                    "agent_response",
                    "agent_completed"
                ]

                collected_events = []
                start_time = time.time()
                timeout = 60.0  # 60 seconds for full Golden Path

                while len(collected_events) < len(expected_events) and (time.time() - start_time) < timeout:
                    try:
                        # Wait for WebSocket message
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event_data = json.loads(message)

                        websocket_events.append(event_data)

                        event_type = event_data.get("type")
                        if event_type in expected_events:
                            collected_events.append(event_type)
                            golden_path_steps.append(f"received_{event_type}")

                        logger.info(f"Received event: {event_type}")

                    except asyncio.TimeoutError:
                        logger.warning("WebSocket message timeout")
                        break

                    except Exception as e:
                        logger.error(f"WebSocket event processing error: {e}")
                        break

                # Step 4: Analyze Golden Path completion
                golden_path_steps.append("analyzing_results")

                missing_events = set(expected_events) - set(collected_events)

                if missing_events:
                    pytest.fail(f"Legacy baseline Golden Path incomplete - missing events: {missing_events}")

                # Check event order
                event_order_correct = True
                for i, expected_event in enumerate(expected_events):
                    if i < len(collected_events) and collected_events[i] != expected_event:
                        event_order_correct = False
                        break

                if not event_order_correct:
                    pytest.fail(f"Legacy baseline event order incorrect: expected {expected_events}, got {collected_events}")

                # Check for handler-specific indicators
                legacy_indicators = []
                for event in websocket_events:
                    event_str = json.dumps(event)
                    if any(indicator in event_str.lower() for indicator in ["legacy", "message_handler", "create_handler_safely"]):
                        legacy_indicators.append(event.get("type", "unknown"))

                if not legacy_indicators:
                    logger.warning("No legacy handler indicators found - may be using SSOT handlers")

                golden_path_steps.append("baseline_complete")

                # If we get here, legacy baseline worked, but test plan expects failure
                pytest.fail("Expected legacy baseline failures but Golden Path completed successfully")

        except Exception as e:
            # Expected failure due to handler conflicts
            logger.error(f"Golden Path steps completed: {golden_path_steps}")
            logger.error(f"WebSocket events received: {len(websocket_events)}")
            pytest.fail(f"Legacy baseline Golden Path failed: {e}")

    @pytest.mark.asyncio
    async def test_complete_chat_flow_ssot_migration(self, staging_authentication):
        """
        Test: Test with SSOT handlers after migration
        Expected: FAIL - SSOT migration may have interface conflicts
        """
        if not WEBSOCKET_CLIENT_AVAILABLE:
            pytest.skip("WebSocket client not available")

        # Use second authenticated user for SSOT test
        if len(staging_authentication) < 2:
            pytest.skip("Need at least 2 authenticated users for comparison")

        user_data = list(staging_authentication.values())[1]
        jwt_token = user_data["jwt_token"]
        user_id = user_data["user_id"]

        logger.info(f"Testing SSOT migration for user: {user_id}")

        ssot_path_steps = []
        websocket_events = []

        try:
            # Step 1: Establish WebSocket connection with SSOT handler expectation
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&handler=ssot"

            ssot_path_steps.append("connecting_websocket_ssot")

            async with websockets.connect(
                websocket_url,
                timeout=STAGING_CONFIG["timeout"]
            ) as websocket:

                ssot_path_steps.append("websocket_connected_ssot")

                # Step 2: Send user message designed to test SSOT patterns
                user_message = {
                    "type": "user_message",
                    "content": "I need to process a complex data analysis task with multiple steps. Please help me create a comprehensive report with charts and insights.",
                    "user_id": user_id,
                    "thread_id": f"ssot_test_{uuid.uuid4()}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "test_marker": "ssot_migration",
                    "handler_preference": "ssot"
                }

                ssot_path_steps.append("sending_ssot_message")

                await websocket.send(json.dumps(user_message))

                ssot_path_steps.append("ssot_message_sent")

                # Step 3: Monitor for SSOT-specific event patterns
                expected_ssot_events = [
                    "agent_started",
                    "agent_thinking",
                    "agent_progress",
                    "agent_response",
                    "agent_completed"
                ]

                collected_events = []
                ssot_indicators = []
                start_time = time.time()
                timeout = 60.0

                while len(collected_events) < len(expected_ssot_events) and (time.time() - start_time) < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event_data = json.loads(message)

                        websocket_events.append(event_data)

                        event_type = event_data.get("type")
                        if event_type in expected_ssot_events:
                            collected_events.append(event_type)
                            ssot_path_steps.append(f"received_ssot_{event_type}")

                        # Look for SSOT handler indicators
                        event_str = json.dumps(event_data)
                        if any(indicator in event_str.lower() for indicator in ["ssot", "websocket_core", "handle_message"]):
                            ssot_indicators.append(event_type)

                        logger.info(f"SSOT event: {event_type}")

                    except asyncio.TimeoutError:
                        logger.warning("SSOT WebSocket message timeout")
                        break

                    except Exception as e:
                        logger.error(f"SSOT WebSocket event processing error: {e}")
                        break

                # Step 4: Validate SSOT migration success
                ssot_path_steps.append("analyzing_ssot_results")

                missing_events = set(expected_ssot_events) - set(collected_events)

                if missing_events:
                    pytest.fail(f"SSOT migration Golden Path incomplete - missing events: {missing_events}")

                # Check for proper SSOT handler usage
                if not ssot_indicators:
                    logger.warning("No SSOT handler indicators found - may still be using legacy handlers")

                # Check for interface compatibility issues
                interface_errors = []
                for event in websocket_events:
                    if event.get("type") == "error":
                        error_message = event.get("message", "")
                        if any(term in error_message.lower() for term in ["interface", "signature", "handle_message"]):
                            interface_errors.append(error_message)

                if interface_errors:
                    pytest.fail(f"SSOT interface compatibility errors: {interface_errors}")

                # Compare with legacy baseline
                # This would require both tests to run and compare results
                ssot_path_steps.append("ssot_migration_complete")

                # If we get here, SSOT migration worked
                pytest.fail("Expected SSOT migration failures but Golden Path completed successfully")

        except Exception as e:
            # Expected failure due to migration issues
            logger.error(f"SSOT path steps completed: {ssot_path_steps}")
            logger.error(f"WebSocket events received: {len(websocket_events)}")
            pytest.fail(f"SSOT migration Golden Path failed: {e}")

    @pytest.mark.asyncio
    async def test_agent_execution_message_flow(self, staging_authentication):
        """
        Test: Full agent request to completion flow
        Expected: FAIL - Agent execution conflicts with dual handlers
        """
        if not WEBSOCKET_CLIENT_AVAILABLE:
            pytest.skip("WebSocket client not available")

        user_data = next(iter(staging_authentication.values()))
        jwt_token = user_data["jwt_token"]
        user_id = user_data["user_id"]

        logger.info(f"Testing agent execution flow for user: {user_id}")

        execution_steps = []
        agent_events = []

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                execution_steps.append("websocket_connected")

                # Send agent execution request
                agent_request = {
                    "type": "agent_execute",
                    "content": "Please analyze the latest sales data and create a summary report with key insights and recommendations.",
                    "user_id": user_id,
                    "thread_id": f"agent_exec_{uuid.uuid4()}",
                    "agent_type": "data_analyst",
                    "execution_mode": "comprehensive",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                execution_steps.append("sending_agent_request")

                await websocket.send(json.dumps(agent_request))

                execution_steps.append("agent_request_sent")

                # Monitor complete agent execution cycle
                agent_lifecycle_events = [
                    "agent_started",
                    "agent_initialized",
                    "agent_thinking",
                    "agent_processing",
                    "agent_progress",
                    "agent_response",
                    "agent_finalizing",
                    "agent_completed"
                ]

                collected_lifecycle = []
                execution_errors = []
                start_time = time.time()
                timeout = 120.0  # 2 minutes for complex agent execution

                while (time.time() - start_time) < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        event_data = json.loads(message)

                        agent_events.append(event_data)

                        event_type = event_data.get("type")

                        if event_type in agent_lifecycle_events:
                            collected_lifecycle.append(event_type)
                            execution_steps.append(f"agent_{event_type}")

                        # Check for execution errors
                        if event_type == "error":
                            error_message = event_data.get("message", "")
                            execution_errors.append(error_message)

                        # Check for agent completion
                        if event_type == "agent_completed":
                            execution_steps.append("agent_execution_complete")
                            break

                        logger.info(f"Agent execution event: {event_type}")

                    except asyncio.TimeoutError:
                        logger.warning("Agent execution timeout waiting for events")
                        break

                    except Exception as e:
                        logger.error(f"Agent execution event error: {e}")
                        execution_errors.append(str(e))
                        break

                # Analyze agent execution results
                execution_steps.append("analyzing_execution")

                if execution_errors:
                    pytest.fail(f"Agent execution errors: {execution_errors}")

                # Check for complete lifecycle
                if "agent_completed" not in collected_lifecycle:
                    pytest.fail("Agent execution did not complete - missing agent_completed event")

                # Check for proper event sequence
                critical_events = ["agent_started", "agent_thinking", "agent_response", "agent_completed"]
                missing_critical = [event for event in critical_events if event not in collected_lifecycle]

                if missing_critical:
                    pytest.fail(f"Critical agent execution events missing: {missing_critical}")

                # Check for handler conflicts during execution
                handler_conflicts = []
                for event in agent_events:
                    event_str = json.dumps(event)
                    # Look for signs of handler conflicts
                    if any(conflict in event_str.lower() for conflict in ["handler conflict", "duplicate handler", "interface mismatch"]):
                        handler_conflicts.append(event.get("type", "unknown"))

                if handler_conflicts:
                    pytest.fail(f"Handler conflicts detected during agent execution: {handler_conflicts}")

                execution_steps.append("execution_validation_complete")

                # If we get here, agent execution worked
                pytest.fail("Expected agent execution failures but execution completed successfully")

        except Exception as e:
            # Expected failure due to execution issues
            logger.error(f"Execution steps completed: {execution_steps}")
            logger.error(f"Agent events received: {len(agent_events)}")
            pytest.fail(f"Agent execution message flow failed: {e}")

    @pytest.mark.asyncio
    async def test_conversation_continuity(self, staging_authentication):
        """
        Test: Multi-message conversation context preservation
        Expected: FAIL - Conversation context lost due to handler conflicts
        """
        if not WEBSOCKET_CLIENT_AVAILABLE:
            pytest.skip("WebSocket client not available")

        user_data = next(iter(staging_authentication.values()))
        jwt_token = user_data["jwt_token"]
        user_id = user_data["user_id"]

        logger.info(f"Testing conversation continuity for user: {user_id}")

        conversation_thread_id = f"continuity_test_{uuid.uuid4()}"
        conversation_messages = [
            "Hi, I'm working on a quarterly sales analysis project.",
            "Can you help me identify the key metrics I should focus on?",
            "Great! Now, based on those metrics, what visualization would you recommend?",
            "Perfect. Can you also suggest how to present this data to executive leadership?",
            "Thank you! One final question - how should I validate these insights?"
        ]

        conversation_log = []
        context_preservation_checks = []

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                conversation_log.append("conversation_started")

                for i, message_content in enumerate(conversation_messages):
                    message_num = i + 1
                    logger.info(f"Sending conversation message {message_num}")

                    user_message = {
                        "type": "user_message",
                        "content": message_content,
                        "user_id": user_id,
                        "thread_id": conversation_thread_id,
                        "message_sequence": message_num,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    conversation_log.append(f"sending_message_{message_num}")

                    await websocket.send(json.dumps(user_message))

                    # Wait for agent response
                    agent_response_received = False
                    response_content = ""
                    start_time = time.time()
                    message_timeout = 45.0

                    while not agent_response_received and (time.time() - start_time) < message_timeout:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            response_data = json.loads(response)

                            if response_data.get("type") == "agent_response":
                                response_content = response_data.get("content", "")
                                agent_response_received = True
                                conversation_log.append(f"received_response_{message_num}")

                        except asyncio.TimeoutError:
                            logger.warning(f"Timeout waiting for response to message {message_num}")
                            break

                        except Exception as e:
                            logger.error(f"Error receiving response to message {message_num}: {e}")
                            break

                    if not agent_response_received:
                        pytest.fail(f"No agent response received for message {message_num}")

                    # Check context preservation
                    context_check = {
                        "message_num": message_num,
                        "user_message": message_content,
                        "agent_response": response_content,
                        "context_preserved": False,
                        "context_indicators": []
                    }

                    # Look for context indicators in response
                    if message_num > 1:
                        # Check if response references previous context
                        previous_keywords = []
                        if message_num == 2:
                            previous_keywords = ["sales", "analysis", "project"]
                        elif message_num == 3:
                            previous_keywords = ["metrics", "focus", "quarterly"]
                        elif message_num == 4:
                            previous_keywords = ["visualization", "data", "recommend"]
                        elif message_num == 5:
                            previous_keywords = ["executive", "leadership", "present"]

                        found_context = []
                        for keyword in previous_keywords:
                            if keyword.lower() in response_content.lower():
                                found_context.append(keyword)

                        if found_context:
                            context_check["context_preserved"] = True
                            context_check["context_indicators"] = found_context

                    else:
                        # First message always has "context"
                        context_check["context_preserved"] = True

                    context_preservation_checks.append(context_check)

                    # Brief delay between messages
                    await asyncio.sleep(2.0)

                conversation_log.append("conversation_complete")

                # Analyze conversation continuity
                failed_context_checks = [
                    check for check in context_preservation_checks
                    if not check["context_preserved"]
                ]

                if failed_context_checks:
                    pytest.fail(f"Conversation context lost in {len(failed_context_checks)} messages: {[c['message_num'] for c in failed_context_checks]}")

                # Check for context degradation over time
                context_quality = [
                    len(check["context_indicators"]) for check in context_preservation_checks[1:]  # Skip first message
                ]

                if context_quality and max(context_quality) == 0:
                    pytest.fail("No context preservation detected throughout conversation")

                # Check for handler consistency throughout conversation
                # This would require inspecting WebSocket events for handler indicators
                conversation_log.append("continuity_validation_complete")

                # If we get here, conversation continuity worked
                pytest.fail("Expected conversation continuity failures but conversation context was preserved")

        except Exception as e:
            # Expected failure due to context issues
            logger.error(f"Conversation log: {conversation_log}")
            logger.error(f"Context checks: {len(context_preservation_checks)} completed")
            pytest.fail(f"Conversation continuity test failed: {e}")

    @pytest.mark.asyncio
    async def test_real_llm_agent_responses(self, staging_authentication):
        """
        Test: Integration with actual LLM responses
        Expected: FAIL - LLM integration conflicts with handler issues
        """
        if not WEBSOCKET_CLIENT_AVAILABLE:
            pytest.skip("WebSocket client not available")

        user_data = next(iter(staging_authentication.values()))
        jwt_token = user_data["jwt_token"]
        user_id = user_data["user_id"]

        logger.info(f"Testing real LLM integration for user: {user_id}")

        llm_test_queries = [
            {
                "query": "What are the key principles of effective data visualization?",
                "expected_topics": ["clarity", "accuracy", "relevance", "design"],
                "complexity": "simple"
            },
            {
                "query": "Can you create a Python script to analyze CSV sales data and generate insights?",
                "expected_topics": ["python", "pandas", "csv", "analysis"],
                "complexity": "complex"
            },
            {
                "query": "Explain the difference between correlation and causation with business examples.",
                "expected_topics": ["correlation", "causation", "business", "examples"],
                "complexity": "medium"
            }
        ]

        llm_response_results = []

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                for i, test_query in enumerate(llm_test_queries):
                    query_num = i + 1
                    logger.info(f"Testing LLM query {query_num}: {test_query['complexity']}")

                    user_message = {
                        "type": "user_message",
                        "content": test_query["query"],
                        "user_id": user_id,
                        "thread_id": f"llm_test_{query_num}_{uuid.uuid4()}",
                        "llm_test": True,
                        "expected_complexity": test_query["complexity"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await websocket.send(json.dumps(user_message))

                    # Collect LLM response events
                    llm_events = []
                    llm_response_content = ""
                    start_time = time.time()
                    query_timeout = 90.0  # 90 seconds for LLM processing

                    while (time.time() - start_time) < query_timeout:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                            event_data = json.loads(message)

                            llm_events.append(event_data)

                            event_type = event_data.get("type")

                            if event_type == "agent_response":
                                llm_response_content = event_data.get("content", "")

                            elif event_type == "agent_completed":
                                break

                        except asyncio.TimeoutError:
                            logger.warning(f"LLM query {query_num} timeout")
                            break

                        except Exception as e:
                            logger.error(f"LLM query {query_num} event error: {e}")
                            break

                    # Analyze LLM response quality
                    query_result = {
                        "query_num": query_num,
                        "query": test_query["query"],
                        "response": llm_response_content,
                        "response_received": bool(llm_response_content),
                        "topic_coverage": [],
                        "quality_issues": []
                    }

                    if llm_response_content:
                        # Check topic coverage
                        response_lower = llm_response_content.lower()
                        for topic in test_query["expected_topics"]:
                            if topic.lower() in response_lower:
                                query_result["topic_coverage"].append(topic)

                        # Quality checks
                        if len(llm_response_content) < 50:
                            query_result["quality_issues"].append("response_too_short")

                        if "error" in response_lower or "sorry" in response_lower:
                            query_result["quality_issues"].append("error_response")

                        # Check for handler-related errors in response
                        if any(term in response_lower for term in ["handler error", "interface", "migration"]):
                            query_result["quality_issues"].append("handler_conflict_in_response")

                    else:
                        query_result["quality_issues"].append("no_response_received")

                    llm_response_results.append(query_result)

                    # Brief delay between queries
                    await asyncio.sleep(3.0)

                # Analyze overall LLM integration
                failed_queries = [result for result in llm_response_results if not result["response_received"]]

                if failed_queries:
                    pytest.fail(f"LLM integration failed for {len(failed_queries)} queries")

                # Check response quality
                quality_issues = []
                for result in llm_response_results:
                    quality_issues.extend(result["quality_issues"])

                if quality_issues:
                    pytest.fail(f"LLM response quality issues: {quality_issues}")

                # Check topic coverage
                poor_coverage = [
                    result for result in llm_response_results
                    if len(result["topic_coverage"]) < len(test_query["expected_topics"]) // 2
                ]

                if poor_coverage:
                    pytest.fail(f"Poor LLM topic coverage in {len(poor_coverage)} responses")

                # If we get here, LLM integration worked
                pytest.fail("Expected LLM integration failures but LLM responses were successful")

        except Exception as e:
            # Expected failure due to LLM integration issues
            logger.error(f"LLM response results: {len(llm_response_results)} completed")
            for result in llm_response_results:
                logger.error(f"Query {result['query_num']}: {result['response_received']}, issues: {result.get('quality_issues', [])}")
            pytest.fail(f"Real LLM agent responses test failed: {e}")

    @pytest.mark.asyncio
    async def test_websocket_reconnection_handling(self, staging_authentication):
        """
        Test: Connection resilience during handler conflicts
        Expected: FAIL - Reconnection issues due to handler state conflicts
        """
        if not WEBSOCKET_CLIENT_AVAILABLE:
            pytest.skip("WebSocket client not available")

        user_data = next(iter(staging_authentication.values()))
        jwt_token = user_data["jwt_token"]
        user_id = user_data["user_id"]

        logger.info(f"Testing WebSocket reconnection for user: {user_id}")

        reconnection_attempts = 3
        reconnection_results = []

        try:
            for attempt in range(reconnection_attempts):
                attempt_num = attempt + 1
                logger.info(f"Reconnection attempt {attempt_num}")

                attempt_result = {
                    "attempt": attempt_num,
                    "connected": False,
                    "message_sent": False,
                    "response_received": False,
                    "reconnection_time": 0.0,
                    "errors": []
                }

                try:
                    start_time = time.time()

                    websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&reconnect={attempt_num}"

                    async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                        connect_time = time.time() - start_time
                        attempt_result["connected"] = True
                        attempt_result["reconnection_time"] = connect_time

                        # Send test message
                        test_message = {
                            "type": "user_message",
                            "content": f"Reconnection test message {attempt_num}",
                            "user_id": user_id,
                            "thread_id": f"reconnect_test_{attempt_num}",
                            "reconnection_test": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }

                        await websocket.send(json.dumps(test_message))
                        attempt_result["message_sent"] = True

                        # Wait for response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                            response_data = json.loads(response)

                            if response_data.get("type") in ["agent_started", "agent_response"]:
                                attempt_result["response_received"] = True

                        except asyncio.TimeoutError:
                            attempt_result["errors"].append("response_timeout")

                        # Deliberately close connection to test reconnection
                        await websocket.close()

                except Exception as e:
                    attempt_result["errors"].append(str(e))

                reconnection_results.append(attempt_result)

                # Brief delay between reconnection attempts
                await asyncio.sleep(2.0)

            # Analyze reconnection results
            successful_connections = [result for result in reconnection_results if result["connected"]]
            successful_messaging = [result for result in reconnection_results if result["message_sent"]]
            successful_responses = [result for result in reconnection_results if result["response_received"]]

            if len(successful_connections) < reconnection_attempts:
                pytest.fail(f"Reconnection failures: only {len(successful_connections)}/{reconnection_attempts} connections successful")

            if len(successful_messaging) < len(successful_connections):
                pytest.fail(f"Message sending failures after reconnection: {len(successful_messaging)}/{len(successful_connections)}")

            if len(successful_responses) < len(successful_messaging):
                pytest.fail(f"Response failures after reconnection: {len(successful_responses)}/{len(successful_messaging)}")

            # Check reconnection timing
            reconnection_times = [result["reconnection_time"] for result in successful_connections]
            avg_reconnection_time = sum(reconnection_times) / len(reconnection_times)

            if avg_reconnection_time > 10.0:  # 10 seconds is too slow
                pytest.fail(f"Reconnection too slow: average {avg_reconnection_time:.2f}s")

            # Check for handler state persistence issues
            handler_errors = []
            for result in reconnection_results:
                for error in result.get("errors", []):
                    if any(term in error.lower() for term in ["handler", "state", "context"]):
                        handler_errors.append(error)

            if handler_errors:
                pytest.fail(f"Handler state issues during reconnection: {handler_errors}")

            # If we get here, reconnection worked
            pytest.fail("Expected WebSocket reconnection failures but reconnection handling was successful")

        except Exception as e:
            # Expected failure due to reconnection issues
            logger.error(f"Reconnection results: {reconnection_results}")
            pytest.fail(f"WebSocket reconnection handling test failed: {e}")

    @pytest.mark.asyncio
    async def test_performance_regression_detection(self, staging_authentication):
        """
        Test: Ensure no performance slowdown from handler conflicts
        Expected: FAIL - Performance degradation due to handler conflicts
        """
        if not WEBSOCKET_CLIENT_AVAILABLE:
            pytest.skip("WebSocket client not available")

        user_data = next(iter(staging_authentication.values()))
        jwt_token = user_data["jwt_token"]
        user_id = user_data["user_id"]

        logger.info(f"Testing performance regression for user: {user_id}")

        performance_benchmarks = {
            "connection_time": 5.0,  # Max 5 seconds to connect
            "first_response_time": 10.0,  # Max 10 seconds for first response
            "message_processing_time": 5.0,  # Max 5 seconds per message
            "concurrent_message_handling": 3  # Should handle 3 concurrent messages
        }

        performance_results = {
            "connection_times": [],
            "response_times": [],
            "processing_times": [],
            "concurrent_performance": {},
            "performance_issues": []
        }

        try:
            # Test 1: Connection performance
            for i in range(5):
                start_time = time.time()

                try:
                    websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&perf_test={i}"

                    async with websockets.connect(websocket_url, timeout=performance_benchmarks["connection_time"]) as websocket:
                        connect_time = time.time() - start_time
                        performance_results["connection_times"].append(connect_time)

                        await websocket.close()

                except Exception as e:
                    performance_results["performance_issues"].append(f"connection_{i}: {str(e)}")

                await asyncio.sleep(1.0)

            # Test 2: Response time performance
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                for i in range(3):
                    start_time = time.time()

                    test_message = {
                        "type": "user_message",
                        "content": f"Performance test message {i}: simple query for response time testing",
                        "user_id": user_id,
                        "thread_id": f"perf_test_{i}",
                        "performance_test": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await websocket.send(json.dumps(test_message))

                    # Wait for first response
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=performance_benchmarks["first_response_time"]
                        )

                        response_time = time.time() - start_time
                        performance_results["response_times"].append(response_time)

                    except asyncio.TimeoutError:
                        performance_results["performance_issues"].append(f"response_timeout_{i}")

                    await asyncio.sleep(2.0)

                # Test 3: Concurrent message handling
                concurrent_messages = []
                for i in range(performance_benchmarks["concurrent_message_handling"]):
                    message = {
                        "type": "user_message",
                        "content": f"Concurrent message {i}",
                        "user_id": user_id,
                        "thread_id": f"concurrent_{i}",
                        "concurrent_test": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    concurrent_messages.append(message)

                # Send all messages rapidly
                start_time = time.time()

                for message in concurrent_messages:
                    await websocket.send(json.dumps(message))

                # Count responses received
                responses_received = 0
                timeout_start = time.time()

                while responses_received < len(concurrent_messages) and (time.time() - timeout_start) < 30.0:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)

                        if response_data.get("type") in ["agent_started", "agent_response"]:
                            responses_received += 1

                    except asyncio.TimeoutError:
                        break

                concurrent_time = time.time() - start_time
                performance_results["concurrent_performance"] = {
                    "messages_sent": len(concurrent_messages),
                    "responses_received": responses_received,
                    "total_time": concurrent_time,
                    "success_rate": responses_received / len(concurrent_messages)
                }

            # Analyze performance results
            # Connection performance
            if performance_results["connection_times"]:
                avg_connection_time = sum(performance_results["connection_times"]) / len(performance_results["connection_times"])
                max_connection_time = max(performance_results["connection_times"])

                if avg_connection_time > performance_benchmarks["connection_time"]:
                    performance_results["performance_issues"].append(f"slow_average_connection: {avg_connection_time:.2f}s")

                if max_connection_time > performance_benchmarks["connection_time"] * 1.5:
                    performance_results["performance_issues"].append(f"very_slow_connection: {max_connection_time:.2f}s")

            # Response time performance
            if performance_results["response_times"]:
                avg_response_time = sum(performance_results["response_times"]) / len(performance_results["response_times"])
                max_response_time = max(performance_results["response_times"])

                if avg_response_time > performance_benchmarks["first_response_time"]:
                    performance_results["performance_issues"].append(f"slow_average_response: {avg_response_time:.2f}s")

                if max_response_time > performance_benchmarks["first_response_time"] * 1.5:
                    performance_results["performance_issues"].append(f"very_slow_response: {max_response_time:.2f}s")

            # Concurrent performance
            concurrent_perf = performance_results["concurrent_performance"]
            if concurrent_perf.get("success_rate", 0) < 0.8:  # Less than 80% success
                performance_results["performance_issues"].append(f"poor_concurrent_success: {concurrent_perf['success_rate']:.2f}")

            if performance_results["performance_issues"]:
                pytest.fail(f"Performance regression detected: {performance_results['performance_issues']}")

            # If we get here, performance was acceptable
            pytest.fail("Expected performance regression but performance was within acceptable limits")

        except Exception as e:
            # Expected failure due to performance issues
            logger.error(f"Performance results: {performance_results}")
            pytest.fail(f"Performance regression detection test failed: {e}")


# Test configuration
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.websocket,
    pytest.mark.issue_1099,
    pytest.mark.gcp_staging,
    pytest.mark.golden_path,
    pytest.mark.expected_failure  # These tests are designed to fail initially
]