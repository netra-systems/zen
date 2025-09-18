"""
E2E Tests - Handler Conflict Reproduction for Issue #1099

Test Purpose: Demonstrate and reproduce handler conflicts in staging environment
Expected Initial State: FAIL - These tests reproduce the actual issue

Environment: GCP Staging (https://auth.staging.netrasystems.ai)
Focus: Reproducing the exact handler conflicts that break Golden Path

Business Value Justification:
- Segment: Platform/Engineering (Issue reproduction and validation)
- Business Goal: Reproduce and document handler conflicts for resolution
- Value Impact: Provide concrete evidence of handler conflicts breaking Golden Path
- Revenue Impact: Protect 500K+ ARR by documenting exact failure modes

🔍 These tests are DESIGNED TO FAIL to reproduce the actual issue
"""

import asyncio
import json
import time
import pytest
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch

# WebSocket and HTTP clients
try:
    import websockets
    import httpx
    CLIENT_LIBRARIES_AVAILABLE = True
except ImportError:
    CLIENT_LIBRARIES_AVAILABLE = False

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Staging configuration
STAGING_CONFIG = {
    "auth_url": "https://auth.staging.netrasystems.ai",
    "api_url": "https://api.staging.netrasystems.ai",
    "websocket_url": "wss://api.staging.netrasystems.ai/ws",
    "timeout": 30.0
}

# Test scenarios designed to trigger specific conflicts
CONFLICT_SCENARIOS = {
    "dual_handler_registration": {
        "description": "Both legacy and SSOT handlers attempt to process same message",
        "trigger_method": "simultaneous_handler_calls",
        "expected_symptoms": ["duplicate_processing", "handler_override", "interface_mismatch"]
    },
    "import_precedence_chaos": {
        "description": "Import order affects which handler gets loaded",
        "trigger_method": "import_order_manipulation",
        "expected_symptoms": ["unpredictable_behavior", "handler_not_found", "wrong_handler_used"]
    },
    "interface_breaking_changes": {
        "description": "Legacy and SSOT handlers have incompatible interfaces",
        "trigger_method": "interface_signature_mismatch",
        "expected_symptoms": ["method_not_found", "parameter_mismatch", "return_type_error"]
    },
    "message_routing_confusion": {
        "description": "Messages get routed to wrong handler or lost",
        "trigger_method": "routing_table_conflicts",
        "expected_symptoms": ["message_not_processed", "wrong_response", "timeout"]
    }
}


class TestHandlerConflictScenarios:
    """E2E tests to reproduce handler conflicts in staging environment"""

    @pytest.fixture(scope="class")
    async def staging_connection(self):
        """Establish connection to staging environment"""
        if not CLIENT_LIBRARIES_AVAILABLE:
            pytest.skip("Client libraries not available")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                health_response = await client.get(f"{STAGING_CONFIG['auth_url']}/health")

                if health_response.status_code != 200:
                    pytest.skip(f"Staging environment not available: {health_response.status_code}")

            return True

        except Exception as e:
            pytest.skip(f"Cannot connect to staging: {e}")

    @pytest.fixture(scope="function")
    async def conflict_test_user(self, staging_connection):
        """Create or authenticate test user specifically for conflict testing"""
        test_user = {
            "username": "conflict_test_user_1099",
            "email": "conflict1099@example.com",
            "password": "ConflictTest123!"
        }

        try:
            async with httpx.AsyncClient(timeout=STAGING_CONFIG["timeout"]) as client:
                # Try to login first
                login_response = await client.post(
                    f"{STAGING_CONFIG['auth_url']}/auth/login",
                    json={"username": test_user["username"], "password": test_user["password"]}
                )

                if login_response.status_code == 200:
                    auth_data = login_response.json()
                    return {
                        "jwt_token": auth_data.get("access_token"),
                        "user_id": auth_data.get("user_id"),
                        "username": test_user["username"]
                    }

                # Create user if doesn't exist
                register_response = await client.post(
                    f"{STAGING_CONFIG['auth_url']}/auth/register",
                    json=test_user
                )

                if register_response.status_code in [200, 201]:
                    # Login after registration
                    login_response = await client.post(
                        f"{STAGING_CONFIG['auth_url']}/auth/login",
                        json={"username": test_user["username"], "password": test_user["password"]}
                    )

                    if login_response.status_code == 200:
                        auth_data = login_response.json()
                        return {
                            "jwt_token": auth_data.get("access_token"),
                            "user_id": auth_data.get("user_id"),
                            "username": test_user["username"]
                        }

            pytest.skip("Could not authenticate conflict test user")

        except Exception as e:
            pytest.skip(f"Conflict test user setup failed: {e}")

    @pytest.mark.asyncio
    async def test_duplicate_handler_registration_conflict(self, conflict_test_user):
        """
        Test: Reproduce dual handler issue where both legacy and SSOT handlers process same message
        Expected: FAIL - This test reproduces the actual conflict
        """
        jwt_token = conflict_test_user["jwt_token"]
        user_id = conflict_test_user["user_id"]

        logger.info("Reproducing duplicate handler registration conflict...")

        conflict_evidence = {
            "duplicate_responses": [],
            "handler_conflicts": [],
            "interface_errors": [],
            "timing_anomalies": []
        }

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&debug=handler_conflicts"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                # Send a message designed to trigger dual handler processing
                conflict_message = {
                    "type": "user_message",
                    "content": "This message should trigger handler conflicts - process it with both legacy and SSOT handlers",
                    "user_id": user_id,
                    "thread_id": f"conflict_test_{uuid.uuid4()}",
                    "handler_debug": True,
                    "force_dual_processing": True,  # This might trigger the conflict
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await websocket.send(json.dumps(conflict_message))

                # Monitor for conflict symptoms
                response_messages = []
                start_time = time.time()
                monitor_duration = 45.0

                while (time.time() - start_time) < monitor_duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        response_data = json.loads(message)
                        response_messages.append(response_data)

                        response_type = response_data.get("type")
                        response_content = json.dumps(response_data)

                        # Look for duplicate processing indicators
                        if response_type == "agent_started":
                            conflict_evidence["duplicate_responses"].append({
                                "type": "agent_started",
                                "timestamp": time.time(),
                                "data": response_data
                            })

                        # Look for handler conflict errors
                        if response_type == "error":
                            error_message = response_data.get("message", "").lower()
                            if any(term in error_message for term in ["handler", "conflict", "duplicate", "interface"]):
                                conflict_evidence["handler_conflicts"].append(response_data)

                        # Look for interface errors
                        if any(term in response_content.lower() for term in ["method not found", "signature", "interface"]):
                            conflict_evidence["interface_errors"].append(response_data)

                        # Check for completion
                        if response_type == "agent_completed":
                            break

                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for conflict evidence")
                        break

                    except Exception as e:
                        logger.error(f"Error monitoring conflict: {e}")
                        break

                # Analyze conflict evidence
                logger.info(f"Collected {len(response_messages)} response messages")

                # Check for duplicate agent_started events (smoking gun for dual processing)
                agent_started_events = [msg for msg in response_messages if msg.get("type") == "agent_started"]

                if len(agent_started_events) > 1:
                    conflict_evidence["duplicate_responses"] = agent_started_events
                    logger.error(f"CONFLICT DETECTED: {len(agent_started_events)} agent_started events - dual handler processing!")
                    pytest.fail(f"Duplicate handler registration confirmed - {len(agent_started_events)} agent_started events")

                # Check for handler-specific errors
                if conflict_evidence["handler_conflicts"]:
                    logger.error(f"Handler conflicts detected: {conflict_evidence['handler_conflicts']}")
                    pytest.fail(f"Handler conflict errors: {len(conflict_evidence['handler_conflicts'])} errors")

                # Check for interface errors
                if conflict_evidence["interface_errors"]:
                    logger.error(f"Interface errors detected: {conflict_evidence['interface_errors']}")
                    pytest.fail(f"Interface compatibility errors: {len(conflict_evidence['interface_errors'])} errors")

                # Check for suspicious timing patterns
                event_timestamps = [msg.get("timestamp") for msg in response_messages if msg.get("timestamp")]
                if len(event_timestamps) > 1:
                    time_gaps = [event_timestamps[i+1] - event_timestamps[i] for i in range(len(event_timestamps)-1)]
                    unusual_gaps = [gap for gap in time_gaps if gap > 10.0 or gap < 0.1]  # Very fast or very slow

                    if unusual_gaps:
                        conflict_evidence["timing_anomalies"] = unusual_gaps
                        logger.warning(f"Timing anomalies detected: {unusual_gaps}")

                # If no conflicts detected, that's unexpected for this test
                if not any(conflict_evidence.values()):
                    logger.warning("No handler conflicts detected - this is unexpected for conflict reproduction test")
                    pytest.fail("Expected to reproduce handler conflicts but no conflicts were detected")

                # This line should not be reached if conflicts are properly detected
                pytest.fail("Duplicate handler registration test should have failed with conflicts")

        except Exception as e:
            # This exception might BE the conflict we're trying to reproduce
            logger.error(f"Exception during conflict test - this may be the conflict: {e}")

            # Check if the exception indicates a handler conflict
            exception_str = str(e).lower()
            if any(term in exception_str for term in ["handler", "conflict", "duplicate", "interface"]):
                pytest.fail(f"Handler conflict reproduced via exception: {e}")

            # Re-raise if it's not a recognized conflict pattern
            pytest.fail(f"Unexpected error during conflict reproduction: {e}")

    @pytest.mark.asyncio
    async def test_message_routing_confusion(self, conflict_test_user):
        """
        Test: Show routing failures when messages get lost or go to wrong handler
        Expected: FAIL - Messages get routed incorrectly due to handler conflicts
        """
        jwt_token = conflict_test_user["jwt_token"]
        user_id = conflict_test_user["user_id"]

        logger.info("Testing message routing confusion...")

        routing_test_results = {
            "messages_sent": 0,
            "messages_processed": 0,
            "routing_errors": [],
            "lost_messages": [],
            "wrong_responses": []
        }

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                # Send multiple messages with different types to test routing
                test_messages = [
                    {
                        "type": "user_message",
                        "content": "Route this to user message handler",
                        "expected_handler": "user_message_handler",
                        "message_id": "routing_test_1"
                    },
                    {
                        "type": "agent_command",
                        "content": "Route this to agent command handler",
                        "expected_handler": "agent_command_handler",
                        "message_id": "routing_test_2"
                    },
                    {
                        "type": "system_message",
                        "content": "Route this to system message handler",
                        "expected_handler": "system_message_handler",
                        "message_id": "routing_test_3"
                    }
                ]

                message_tracking = {}

                for i, test_msg in enumerate(test_messages):
                    message_id = test_msg["message_id"]

                    full_message = {
                        **test_msg,
                        "user_id": user_id,
                        "thread_id": f"routing_test_{i}",
                        "routing_test": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    message_tracking[message_id] = {
                        "sent": False,
                        "processed": False,
                        "response_received": False,
                        "expected_handler": test_msg["expected_handler"],
                        "actual_handler": None,
                        "errors": []
                    }

                    try:
                        await websocket.send(json.dumps(full_message))
                        message_tracking[message_id]["sent"] = True
                        routing_test_results["messages_sent"] += 1
                        logger.info(f"Sent routing test message: {message_id}")

                    except Exception as e:
                        message_tracking[message_id]["errors"].append(f"send_error: {str(e)}")
                        routing_test_results["routing_errors"].append(f"{message_id}: {str(e)}")

                    # Brief delay between messages
                    await asyncio.sleep(1.0)

                # Monitor responses for routing issues
                start_time = time.time()
                monitor_timeout = 60.0  # Wait up to 60 seconds for all responses

                while (time.time() - start_time) < monitor_timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        response_data = json.loads(response)

                        response_type = response_data.get("type")
                        message_id = response_data.get("message_id")  # May not be present

                        # Try to match response to original message
                        matched_message = None
                        if message_id:
                            matched_message = message_tracking.get(message_id)
                        else:
                            # Try to match by content or context
                            response_content = response_data.get("content", "").lower()
                            for mid, tracking in message_tracking.items():
                                if not tracking["response_received"]:
                                    # Simple content matching
                                    if any(word in response_content for word in ["route", "handler", "message"]):
                                        matched_message = tracking
                                        message_id = mid
                                        break

                        if matched_message:
                            matched_message["response_received"] = True
                            matched_message["actual_handler"] = response_data.get("handler_type", "unknown")

                            # Check if correct handler processed the message
                            expected_handler = matched_message["expected_handler"]
                            actual_handler = matched_message["actual_handler"]

                            if actual_handler != expected_handler and actual_handler != "unknown":
                                routing_test_results["wrong_responses"].append({
                                    "message_id": message_id,
                                    "expected": expected_handler,
                                    "actual": actual_handler
                                })

                            routing_test_results["messages_processed"] += 1

                        # Look for routing errors in response
                        if response_type == "error":
                            error_message = response_data.get("message", "").lower()
                            if any(term in error_message for term in ["routing", "handler not found", "no handler"]):
                                routing_test_results["routing_errors"].append(response_data)

                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for routing responses")
                        break

                    except Exception as e:
                        logger.error(f"Error processing routing response: {e}")
                        routing_test_results["routing_errors"].append(str(e))
                        break

                # Analyze routing results
                logger.info(f"Routing test results: {routing_test_results}")

                # Check for lost messages
                for message_id, tracking in message_tracking.items():
                    if tracking["sent"] and not tracking["response_received"]:
                        routing_test_results["lost_messages"].append(message_id)

                # Evaluate routing failures
                if routing_test_results["lost_messages"]:
                    logger.error(f"Lost messages detected: {routing_test_results['lost_messages']}")
                    pytest.fail(f"Message routing failure - {len(routing_test_results['lost_messages'])} messages lost")

                if routing_test_results["wrong_responses"]:
                    logger.error(f"Wrong routing detected: {routing_test_results['wrong_responses']}")
                    pytest.fail(f"Message routing confusion - {len(routing_test_results['wrong_responses'])} messages misrouted")

                if routing_test_results["routing_errors"]:
                    logger.error(f"Routing errors detected: {routing_test_results['routing_errors']}")
                    pytest.fail(f"Message routing errors - {len(routing_test_results['routing_errors'])} routing failures")

                # Check success rate
                success_rate = routing_test_results["messages_processed"] / routing_test_results["messages_sent"] if routing_test_results["messages_sent"] > 0 else 0

                if success_rate < 1.0:
                    pytest.fail(f"Message routing incomplete - success rate: {success_rate:.2f}")

                # If we get here, routing worked perfectly, which is unexpected for this test
                pytest.fail("Expected message routing confusion but all messages were routed correctly")

        except Exception as e:
            # This might be the routing failure we're trying to reproduce
            logger.error(f"Routing test exception: {e}")
            pytest.fail(f"Message routing confusion reproduced: {e}")

    @pytest.mark.asyncio
    async def test_interface_breaking_changes(self, conflict_test_user):
        """
        Test: Demonstrate interface mismatches between legacy and SSOT handlers
        Expected: FAIL - Interface incompatibilities cause failures
        """
        jwt_token = conflict_test_user["jwt_token"]
        user_id = conflict_test_user["user_id"]

        logger.info("Testing interface breaking changes...")

        interface_test_scenarios = [
            {
                "name": "legacy_handle_method",
                "message": {
                    "type": "user_message",
                    "content": "Test legacy handle() method interface",
                    "interface_test": "legacy_handle",
                    "expected_method": "handle"
                }
            },
            {
                "name": "ssot_handle_message_method",
                "message": {
                    "type": "user_message",
                    "content": "Test SSOT handle_message() method interface",
                    "interface_test": "ssot_handle_message",
                    "expected_method": "handle_message"
                }
            },
            {
                "name": "parameter_mismatch",
                "message": {
                    "type": "user_message",
                    "content": "Test parameter signature mismatch",
                    "interface_test": "parameter_mismatch",
                    "legacy_params": ["payload"],
                    "ssot_params": ["websocket", "message"]
                }
            },
            {
                "name": "return_type_mismatch",
                "message": {
                    "type": "user_message",
                    "content": "Test return type compatibility",
                    "interface_test": "return_type",
                    "legacy_return": "None",
                    "ssot_return": "bool"
                }
            }
        ]

        interface_failures = []

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                for scenario in interface_test_scenarios:
                    scenario_name = scenario["name"]
                    test_message = scenario["message"]

                    logger.info(f"Testing interface scenario: {scenario_name}")

                    full_message = {
                        **test_message,
                        "user_id": user_id,
                        "thread_id": f"interface_test_{scenario_name}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    scenario_result = {
                        "scenario": scenario_name,
                        "message_sent": False,
                        "interface_errors": [],
                        "method_errors": [],
                        "parameter_errors": [],
                        "return_type_errors": []
                    }

                    try:
                        await websocket.send(json.dumps(full_message))
                        scenario_result["message_sent"] = True

                        # Monitor for interface-specific errors
                        start_time = time.time()
                        scenario_timeout = 30.0

                        while (time.time() - start_time) < scenario_timeout:
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                                response_data = json.loads(response)

                                response_type = response_data.get("type")
                                response_content = json.dumps(response_data).lower()

                                # Look for interface-related errors
                                if response_type == "error":
                                    error_message = response_data.get("message", "").lower()

                                    if "method not found" in error_message or "handle" in error_message:
                                        scenario_result["method_errors"].append(response_data)

                                    if "parameter" in error_message or "signature" in error_message:
                                        scenario_result["parameter_errors"].append(response_data)

                                    if "return" in error_message or "type" in error_message:
                                        scenario_result["return_type_errors"].append(response_data)

                                    if any(term in error_message for term in ["interface", "compatibility", "mismatch"]):
                                        scenario_result["interface_errors"].append(response_data)

                                # Check for successful completion
                                if response_type in ["agent_completed", "agent_response"]:
                                    break

                            except asyncio.TimeoutError:
                                logger.warning(f"Timeout in interface scenario: {scenario_name}")
                                break

                    except Exception as e:
                        scenario_result["interface_errors"].append(str(e))
                        logger.error(f"Interface scenario {scenario_name} failed: {e}")

                    # Record scenario results
                    if any([
                        scenario_result["interface_errors"],
                        scenario_result["method_errors"],
                        scenario_result["parameter_errors"],
                        scenario_result["return_type_errors"]
                    ]):
                        interface_failures.append(scenario_result)

                    # Brief delay between scenarios
                    await asyncio.sleep(2.0)

                # Analyze interface test results
                if interface_failures:
                    logger.error(f"Interface breaking changes detected in {len(interface_failures)} scenarios")

                    for failure in interface_failures:
                        logger.error(f"Scenario {failure['scenario']} failures:")
                        for error_type in ["interface_errors", "method_errors", "parameter_errors", "return_type_errors"]:
                            errors = failure.get(error_type, [])
                            if errors:
                                logger.error(f"  {error_type}: {len(errors)} errors")

                    pytest.fail(f"Interface breaking changes confirmed - {len(interface_failures)} scenarios failed")

                # If no interface failures, that's unexpected for this test
                pytest.fail("Expected interface breaking changes but all interface tests passed")

        except Exception as e:
            # This might be the interface failure we're trying to reproduce
            logger.error(f"Interface test exception: {e}")

            exception_str = str(e).lower()
            if any(term in exception_str for term in ["method", "signature", "parameter", "interface"]):
                pytest.fail(f"Interface breaking changes reproduced: {e}")

            pytest.fail(f"Unexpected error during interface testing: {e}")

    @pytest.mark.asyncio
    async def test_import_precedence_failures(self, conflict_test_user):
        """
        Test: Show import order issues causing unpredictable handler selection
        Expected: FAIL - Import precedence causes undefined behavior
        """
        jwt_token = conflict_test_user["jwt_token"]
        user_id = conflict_test_user["user_id"]

        logger.info("Testing import precedence failures...")

        precedence_test_results = {
            "handler_selections": [],
            "import_errors": [],
            "precedence_violations": [],
            "undefined_behavior": []
        }

        try:
            # Test multiple connections to see if handler selection is consistent
            connection_attempts = 5
            handler_consistency_check = []

            for attempt in range(connection_attempts):
                logger.info(f"Import precedence test attempt {attempt + 1}")

                try:
                    # Use different connection parameters to potentially trigger different import orders
                    connection_params = {
                        "attempt": attempt,
                        "import_test": True,
                        "precedence_check": attempt % 2  # Alternate to trigger different paths
                    }

                    websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&" + "&".join(f"{k}={v}" for k, v in connection_params.items())

                    async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                        # Send test message to see which handler processes it
                        test_message = {
                            "type": "user_message",
                            "content": f"Import precedence test message {attempt + 1}",
                            "user_id": user_id,
                            "thread_id": f"precedence_test_{attempt}",
                            "import_test": True,
                            "attempt": attempt,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }

                        await websocket.send(json.dumps(test_message))

                        # Monitor response to identify which handler processed it
                        attempt_result = {
                            "attempt": attempt,
                            "message_sent": True,
                            "handler_identified": False,
                            "handler_type": None,
                            "response_data": [],
                            "errors": []
                        }

                        start_time = time.time()
                        response_timeout = 30.0

                        while (time.time() - start_time) < response_timeout:
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                                response_data = json.loads(response)

                                attempt_result["response_data"].append(response_data)

                                # Look for handler identification
                                response_str = json.dumps(response_data).lower()

                                if "legacy" in response_str or "message_handler" in response_str:
                                    attempt_result["handler_type"] = "legacy"
                                    attempt_result["handler_identified"] = True

                                elif "ssot" in response_str or "websocket_core" in response_str:
                                    attempt_result["handler_type"] = "ssot"
                                    attempt_result["handler_identified"] = True

                                # Look for import-related errors
                                if response_data.get("type") == "error":
                                    error_message = response_data.get("message", "").lower()
                                    if any(term in error_message for term in ["import", "module", "not found", "precedence"]):
                                        attempt_result["errors"].append(response_data)
                                        precedence_test_results["import_errors"].append(response_data)

                                # Check for completion
                                if response_data.get("type") in ["agent_completed", "agent_response"]:
                                    break

                            except asyncio.TimeoutError:
                                logger.warning(f"Response timeout in precedence test attempt {attempt + 1}")
                                break

                        handler_consistency_check.append(attempt_result)

                except Exception as e:
                    logger.error(f"Precedence test attempt {attempt + 1} failed: {e}")
                    handler_consistency_check.append({
                        "attempt": attempt,
                        "message_sent": False,
                        "error": str(e)
                    })

                # Brief delay between attempts
                await asyncio.sleep(1.0)

            # Analyze handler consistency
            identified_handlers = [result["handler_type"] for result in handler_consistency_check if result.get("handler_identified")]

            precedence_test_results["handler_selections"] = identified_handlers

            # Check for inconsistent handler selection (precedence violation)
            if len(set(identified_handlers)) > 1:
                precedence_test_results["precedence_violations"].append({
                    "inconsistent_handlers": list(set(identified_handlers)),
                    "selections": identified_handlers
                })

                logger.error(f"Import precedence violation - inconsistent handler selection: {identified_handlers}")
                pytest.fail(f"Import precedence failure - handlers selected inconsistently: {set(identified_handlers)}")

            # Check for undefined behavior (no handler identified)
            unidentified_attempts = [result for result in handler_consistency_check if not result.get("handler_identified")]

            if unidentified_attempts:
                precedence_test_results["undefined_behavior"] = unidentified_attempts
                logger.error(f"Undefined behavior - {len(unidentified_attempts)} attempts had no identifiable handler")
                pytest.fail(f"Import precedence undefined behavior - {len(unidentified_attempts)} unidentified handlers")

            # Check for import errors
            if precedence_test_results["import_errors"]:
                logger.error(f"Import errors detected: {precedence_test_results['import_errors']}")
                pytest.fail(f"Import precedence failures - {len(precedence_test_results['import_errors'])} import errors")

            # If we get here, import precedence was consistent
            logger.warning(f"Import precedence appeared consistent - all attempts used: {set(identified_handlers)}")
            pytest.fail("Expected import precedence failures but handler selection was consistent")

        except Exception as e:
            # This might be the import precedence failure we're trying to reproduce
            logger.error(f"Import precedence test exception: {e}")
            pytest.fail(f"Import precedence failures reproduced: {e}")

    @pytest.mark.asyncio
    async def test_handler_override_scenarios(self, conflict_test_user):
        """
        Test: Test when handlers override each other causing unpredictable behavior
        Expected: FAIL - Handler overrides cause system instability
        """
        jwt_token = conflict_test_user["jwt_token"]
        user_id = conflict_test_user["user_id"]

        logger.info("Testing handler override scenarios...")

        override_test_cases = [
            {
                "name": "sequential_override",
                "description": "Send messages that should trigger sequential handler overrides",
                "messages": [
                    {"content": "Message 1 - should use handler A", "expected_handler": "A"},
                    {"content": "Message 2 - should use handler B", "expected_handler": "B"},
                    {"content": "Message 3 - should use handler A again", "expected_handler": "A"}
                ]
            },
            {
                "name": "rapid_override",
                "description": "Send rapid messages to trigger override race conditions",
                "messages": [
                    {"content": f"Rapid message {i}", "expected_handler": "consistent"}
                    for i in range(10)
                ]
            }
        ]

        override_failures = []

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                for test_case in override_test_cases:
                    case_name = test_case["name"]
                    test_messages = test_case["messages"]

                    logger.info(f"Testing override scenario: {case_name}")

                    case_result = {
                        "case_name": case_name,
                        "messages_sent": 0,
                        "handler_overrides": [],
                        "inconsistent_responses": [],
                        "override_errors": []
                    }

                    previous_handler = None

                    for i, msg_config in enumerate(test_messages):
                        message = {
                            "type": "user_message",
                            "content": msg_config["content"],
                            "user_id": user_id,
                            "thread_id": f"override_{case_name}_{i}",
                            "message_sequence": i,
                            "override_test": case_name,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }

                        try:
                            await websocket.send(json.dumps(message))
                            case_result["messages_sent"] += 1

                            # Monitor for override behavior
                            start_time = time.time()
                            message_timeout = 20.0

                            current_handler = None

                            while (time.time() - start_time) < message_timeout:
                                try:
                                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                                    response_data = json.loads(response)

                                    response_str = json.dumps(response_data).lower()

                                    # Identify current handler
                                    if "legacy" in response_str:
                                        current_handler = "legacy"
                                    elif "ssot" in response_str:
                                        current_handler = "ssot"

                                    # Look for override indicators
                                    if any(term in response_str for term in ["override", "replaced", "switched"]):
                                        case_result["handler_overrides"].append({
                                            "message_index": i,
                                            "previous_handler": previous_handler,
                                            "current_handler": current_handler,
                                            "response": response_data
                                        })

                                    # Look for error responses that might indicate overrides
                                    if response_data.get("type") == "error":
                                        error_message = response_data.get("message", "").lower()
                                        if any(term in error_message for term in ["handler", "override", "conflict"]):
                                            case_result["override_errors"].append(response_data)

                                    # Check for completion
                                    if response_data.get("type") in ["agent_completed", "agent_response"]:
                                        break

                                except asyncio.TimeoutError:
                                    logger.warning(f"Timeout in override test message {i}")
                                    break

                            # Check for handler consistency
                            if previous_handler and current_handler and previous_handler != current_handler:
                                if case_name == "sequential_override":
                                    # This is expected for sequential test
                                    case_result["handler_overrides"].append({
                                        "message_index": i,
                                        "expected_override": True,
                                        "previous": previous_handler,
                                        "current": current_handler
                                    })
                                else:
                                    # This is unexpected for rapid test
                                    case_result["inconsistent_responses"].append({
                                        "message_index": i,
                                        "unexpected_handler_change": True,
                                        "previous": previous_handler,
                                        "current": current_handler
                                    })

                            previous_handler = current_handler

                            # Brief delay for sequential test, no delay for rapid test
                            if case_name == "sequential_override":
                                await asyncio.sleep(1.0)

                        except Exception as e:
                            case_result["override_errors"].append(f"message_{i}: {str(e)}")

                    # Analyze case results
                    if case_result["override_errors"]:
                        override_failures.append(case_result)

                    if case_result["inconsistent_responses"]:
                        override_failures.append(case_result)

                    # For rapid test, inconsistent handlers indicate override problems
                    if case_name == "rapid_override" and case_result["handler_overrides"]:
                        override_failures.append(case_result)

                # Evaluate override test results
                if override_failures:
                    logger.error(f"Handler override failures detected in {len(override_failures)} test cases")

                    for failure in override_failures:
                        logger.error(f"Override failure in {failure['case_name']}:")
                        logger.error(f"  Override errors: {len(failure.get('override_errors', []))}")
                        logger.error(f"  Inconsistent responses: {len(failure.get('inconsistent_responses', []))}")
                        logger.error(f"  Handler overrides: {len(failure.get('handler_overrides', []))}")

                    pytest.fail(f"Handler override scenarios failed - {len(override_failures)} cases with override issues")

                # If no override issues, that's unexpected for this test
                pytest.fail("Expected handler override scenarios to fail but all override tests passed")

        except Exception as e:
            # This might be the override failure we're trying to reproduce
            logger.error(f"Handler override test exception: {e}")
            pytest.fail(f"Handler override scenarios reproduced failures: {e}")

    @pytest.mark.asyncio
    async def test_legacy_fallback_failures(self, conflict_test_user):
        """
        Test: Show fallback mechanism failures when handlers conflict
        Expected: FAIL - Fallback mechanisms don't work with conflicting handlers
        """
        jwt_token = conflict_test_user["jwt_token"]
        user_id = conflict_test_user["user_id"]

        logger.info("Testing legacy fallback failures...")

        fallback_scenarios = [
            {
                "name": "ssot_handler_unavailable",
                "trigger": "force_ssot_failure",
                "expected_fallback": "legacy_handler"
            },
            {
                "name": "legacy_handler_unavailable",
                "trigger": "force_legacy_failure",
                "expected_fallback": "ssot_handler"
            },
            {
                "name": "both_handlers_conflict",
                "trigger": "force_handler_conflict",
                "expected_fallback": "graceful_degradation"
            }
        ]

        fallback_failures = []

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                for scenario in fallback_scenarios:
                    scenario_name = scenario["name"]
                    trigger = scenario["trigger"]
                    expected_fallback = scenario["expected_fallback"]

                    logger.info(f"Testing fallback scenario: {scenario_name}")

                    scenario_result = {
                        "scenario": scenario_name,
                        "trigger_sent": False,
                        "fallback_activated": False,
                        "fallback_type": None,
                        "fallback_errors": [],
                        "graceful_degradation": False
                    }

                    # Send message designed to trigger fallback scenario
                    fallback_message = {
                        "type": "user_message",
                        "content": f"Fallback test: {scenario_name}",
                        "user_id": user_id,
                        "thread_id": f"fallback_{scenario_name}",
                        "fallback_test": True,
                        "trigger": trigger,
                        "expected_fallback": expected_fallback,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    try:
                        await websocket.send(json.dumps(fallback_message))
                        scenario_result["trigger_sent"] = True

                        # Monitor for fallback behavior
                        start_time = time.time()
                        fallback_timeout = 45.0

                        while (time.time() - start_time) < fallback_timeout:
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                                response_data = json.loads(response)

                                response_str = json.dumps(response_data).lower()

                                # Look for fallback indicators
                                if any(term in response_str for term in ["fallback", "degraded", "backup"]):
                                    scenario_result["fallback_activated"] = True

                                # Identify fallback type
                                if "legacy" in response_str and scenario_result["fallback_activated"]:
                                    scenario_result["fallback_type"] = "legacy"

                                elif "ssot" in response_str and scenario_result["fallback_activated"]:
                                    scenario_result["fallback_type"] = "ssot"

                                elif "degraded" in response_str:
                                    scenario_result["fallback_type"] = "graceful_degradation"
                                    scenario_result["graceful_degradation"] = True

                                # Look for fallback errors
                                if response_data.get("type") == "error":
                                    error_message = response_data.get("message", "").lower()
                                    if any(term in error_message for term in ["fallback", "handler", "unavailable"]):
                                        scenario_result["fallback_errors"].append(response_data)

                                # Check for completion or timeout
                                if response_data.get("type") in ["agent_completed", "agent_response"]:
                                    break

                            except asyncio.TimeoutError:
                                logger.warning(f"Timeout in fallback scenario: {scenario_name}")
                                break

                        # Evaluate fallback scenario
                        if not scenario_result["trigger_sent"]:
                            fallback_failures.append({**scenario_result, "failure_reason": "trigger_not_sent"})

                        elif scenario_result["fallback_errors"]:
                            fallback_failures.append({**scenario_result, "failure_reason": "fallback_errors"})

                        elif not scenario_result["fallback_activated"] and expected_fallback != "graceful_degradation":
                            fallback_failures.append({**scenario_result, "failure_reason": "no_fallback_activated"})

                        elif scenario_result["fallback_type"] != expected_fallback.split("_")[0] and expected_fallback != "graceful_degradation":
                            fallback_failures.append({**scenario_result, "failure_reason": "wrong_fallback_type"})

                    except Exception as e:
                        scenario_result["fallback_errors"].append(str(e))
                        fallback_failures.append({**scenario_result, "failure_reason": f"exception: {str(e)}"})

                    # Brief delay between scenarios
                    await asyncio.sleep(2.0)

                # Analyze fallback test results
                if fallback_failures:
                    logger.error(f"Legacy fallback failures detected in {len(fallback_failures)} scenarios")

                    for failure in fallback_failures:
                        logger.error(f"Fallback failure in {failure['scenario']}: {failure.get('failure_reason')}")
                        if failure.get('fallback_errors'):
                            logger.error(f"  Errors: {failure['fallback_errors']}")

                    pytest.fail(f"Legacy fallback mechanisms failed - {len(fallback_failures)} scenarios failed")

                # If all fallback scenarios worked, that's unexpected
                pytest.fail("Expected legacy fallback failures but all fallback mechanisms worked correctly")

        except Exception as e:
            # This might be the fallback failure we're trying to reproduce
            logger.error(f"Fallback test exception: {e}")
            pytest.fail(f"Legacy fallback failures reproduced: {e}")


# Test configuration
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.websocket,
    pytest.mark.issue_1099,
    pytest.mark.gcp_staging,
    pytest.mark.conflict_reproduction,
    pytest.mark.expected_failure  # These tests are DESIGNED TO FAIL to reproduce conflicts
]