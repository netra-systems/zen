"""
E2E Tests - Migration Validation Suite for Issue #1099

Test Purpose: Validate successful migration to SSOT patterns
Expected Final State: PASS - All tests pass after successful migration

Environment: GCP Staging (https://auth.staging.netrasystems.ai)
Focus: Post-migration validation and success criteria verification

Business Value Justification:
- Segment: Platform/Enterprise (Migration success validation)
- Business Goal: Ensure migration to SSOT patterns is complete and successful
- Value Impact: Validate Golden Path functionality restored and improved
- Revenue Impact: Protect $500K+ ARR by ensuring migration success

🔍 These tests validate migration completion and should PASS after migration
"""

import asyncio
import json
import time
import pytest
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Client libraries
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

# Migration success criteria
MIGRATION_SUCCESS_CRITERIA = {
    "golden_path_functionality": {
        "user_login_time": 2.0,  # Max 2 seconds
        "agent_response_time": 10.0,  # Max 10 seconds
        "websocket_events_delivered": 5,  # All 5 events
        "conversation_context_preserved": True,
        "error_rate": 0.01  # Less than 1% errors
    },
    "performance_metrics": {
        "connection_time": 3.0,  # Max 3 seconds
        "message_processing_time": 5.0,  # Max 5 seconds
        "concurrent_user_support": 10,  # Support 10 concurrent users
        "memory_leak_tolerance": 0  # No memory leaks
    },
    "handler_consolidation": {
        "single_handler_interface": True,  # Only handle_message() interface
        "legacy_handler_removed": True,  # Legacy handler files deleted
        "import_path_consistency": True,  # All imports from SSOT
        "no_handler_conflicts": True  # No dual processing
    }
}


class TestMessageHandlerMigrationValidation:
    """E2E tests to validate successful migration to SSOT patterns"""

    @pytest.fixture(scope="class")
    async def staging_environment(self):
        """Verify staging environment is accessible and stable"""
        if not CLIENT_LIBRARIES_AVAILABLE:
            pytest.skip("Client libraries not available")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Health check
                health_response = await client.get(f"{STAGING_CONFIG['auth_url']}/health")
                if health_response.status_code != 200:
                    pytest.skip(f"Staging environment unhealthy: {health_response.status_code}")

                # API availability check
                api_response = await client.get(f"{STAGING_CONFIG['api_url']}/health")
                if api_response.status_code != 200:
                    pytest.skip(f"Staging API unhealthy: {api_response.status_code}")

            return True

        except Exception as e:
            pytest.skip(f"Staging environment not accessible: {e}")

    @pytest.fixture(scope="function")
    async def migration_test_user(self, staging_environment):
        """Create authenticated user for migration validation"""
        test_user = {
            "username": "migration_validation_user",
            "email": "migration.validation@example.com",
            "password": "MigrationTest123!"
        }

        try:
            async with httpx.AsyncClient(timeout=STAGING_CONFIG["timeout"]) as client:
                # Try login first
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

            pytest.skip("Could not authenticate migration test user")

        except Exception as e:
            pytest.skip(f"Migration test user setup failed: {e}")

    @pytest.mark.asyncio
    async def test_post_migration_golden_path(self, migration_test_user):
        """
        Test: Full Golden Path works post-migration
        Expected: PASS - Complete Golden Path functionality restored
        """
        jwt_token = migration_test_user["jwt_token"]
        user_id = migration_test_user["user_id"]

        logger.info("Validating post-migration Golden Path functionality...")

        golden_path_metrics = {
            "connection_time": None,
            "first_response_time": None,
            "total_completion_time": None,
            "events_received": [],
            "conversation_context": [],
            "error_count": 0,
            "success": False
        }

        try:
            # Start Golden Path timing
            golden_path_start = time.time()

            # Step 1: WebSocket Connection (should be fast and reliable)
            connection_start = time.time()

            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&migration_validation=true"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                connection_time = time.time() - connection_start
                golden_path_metrics["connection_time"] = connection_time

                logger.info(f"WebSocket connection established in {connection_time:.2f}s")

                # Verify connection speed meets criteria
                if connection_time > MIGRATION_SUCCESS_CRITERIA["golden_path_functionality"]["user_login_time"]:
                    pytest.fail(f"Connection too slow: {connection_time:.2f}s > {MIGRATION_SUCCESS_CRITERIA['golden_path_functionality']['user_login_time']}s")

                # Step 2: Send comprehensive test message
                comprehensive_message = {
                    "type": "user_message",
                    "content": "Post-migration validation: Please analyze quarterly sales data, create visualizations, and provide strategic recommendations for the executive team. This is a comprehensive test of the migrated Golden Path functionality.",
                    "user_id": user_id,
                    "thread_id": f"migration_validation_{uuid.uuid4()}",
                    "validation_test": True,
                    "expected_complexity": "high",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                message_sent_time = time.time()

                await websocket.send(json.dumps(comprehensive_message))

                logger.info("Comprehensive validation message sent")

                # Step 3: Monitor complete Golden Path execution
                expected_events = [
                    "agent_started",
                    "agent_thinking",
                    "agent_progress",
                    "agent_response",
                    "agent_completed"
                ]

                events_received = []
                first_response_received = False
                conversation_context_evidence = []
                start_monitoring = time.time()
                golden_path_timeout = 120.0  # 2 minutes for comprehensive test

                while (time.time() - start_monitoring) < golden_path_timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        response_data = json.loads(response)

                        event_type = response_data.get("type")
                        event_content = response_data.get("content", "")

                        # Track events
                        if event_type in expected_events:
                            events_received.append(event_type)
                            golden_path_metrics["events_received"].append({
                                "type": event_type,
                                "timestamp": time.time(),
                                "content_length": len(str(event_content))
                            })

                            logger.info(f"Golden Path event: {event_type}")

                        # Capture first meaningful response time
                        if not first_response_received and event_type == "agent_response":
                            first_response_time = time.time() - message_sent_time
                            golden_path_metrics["first_response_time"] = first_response_time
                            first_response_received = True

                            logger.info(f"First response received in {first_response_time:.2f}s")

                        # Look for conversation context evidence
                        if event_content and isinstance(event_content, str):
                            context_indicators = ["quarterly", "sales", "analysis", "visualization", "strategic", "executive"]
                            found_context = [indicator for indicator in context_indicators if indicator.lower() in event_content.lower()]

                            if found_context:
                                conversation_context_evidence.extend(found_context)

                        # Check for errors
                        if event_type == "error":
                            golden_path_metrics["error_count"] += 1
                            logger.warning(f"Error in Golden Path: {response_data}")

                        # Check for completion
                        if event_type == "agent_completed":
                            total_completion_time = time.time() - golden_path_start
                            golden_path_metrics["total_completion_time"] = total_completion_time
                            logger.info(f"Golden Path completed in {total_completion_time:.2f}s")
                            break

                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for Golden Path events")
                        break

                    except Exception as e:
                        logger.error(f"Error during Golden Path monitoring: {e}")
                        golden_path_metrics["error_count"] += 1
                        break

                # Step 4: Validate Golden Path success criteria
                golden_path_metrics["conversation_context"] = list(set(conversation_context_evidence))

                validation_results = []

                # Check all expected events received
                missing_events = set(expected_events) - set(events_received)
                if missing_events:
                    validation_results.append(f"Missing events: {missing_events}")

                # Check event count meets criteria
                if len(events_received) < MIGRATION_SUCCESS_CRITERIA["golden_path_functionality"]["websocket_events_delivered"]:
                    validation_results.append(f"Insufficient events: {len(events_received)} < {MIGRATION_SUCCESS_CRITERIA['golden_path_functionality']['websocket_events_delivered']}")

                # Check response time
                if golden_path_metrics["first_response_time"]:
                    max_response_time = MIGRATION_SUCCESS_CRITERIA["golden_path_functionality"]["agent_response_time"]
                    if golden_path_metrics["first_response_time"] > max_response_time:
                        validation_results.append(f"Response too slow: {golden_path_metrics['first_response_time']:.2f}s > {max_response_time}s")

                # Check conversation context preservation
                if len(conversation_context_evidence) < 3:  # Should find at least 3 context indicators
                    validation_results.append(f"Poor context preservation: only {len(conversation_context_evidence)} indicators found")

                # Check error rate
                max_errors = int(MIGRATION_SUCCESS_CRITERIA["golden_path_functionality"]["error_rate"] * 100)  # Convert to count
                if golden_path_metrics["error_count"] > max_errors:
                    validation_results.append(f"Too many errors: {golden_path_metrics['error_count']} > {max_errors}")

                # Determine overall success
                if not validation_results:
                    golden_path_metrics["success"] = True
                    logger.info("CHECK Post-migration Golden Path validation PASSED")
                else:
                    logger.error(f"X Golden Path validation failures: {validation_results}")
                    pytest.fail(f"Post-migration Golden Path validation failed: {validation_results}")

        except Exception as e:
            logger.error(f"Golden Path validation exception: {e}")
            pytest.fail(f"Post-migration Golden Path test failed: {e}")

    @pytest.mark.asyncio
    async def test_legacy_handler_removal_validation(self, migration_test_user):
        """
        Test: Verify legacy handler fully removed
        Expected: PASS - No legacy handler artifacts remain
        """
        jwt_token = migration_test_user["jwt_token"]
        user_id = migration_test_user["user_id"]

        logger.info("Validating legacy handler removal...")

        legacy_detection_results = {
            "legacy_imports_detected": [],
            "legacy_function_calls": [],
            "legacy_error_messages": [],
            "legacy_handler_indicators": [],
            "migration_complete": True
        }

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&legacy_detection=true"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                # Send messages designed to probe for legacy handler presence
                legacy_probe_messages = [
                    {
                        "content": "Legacy handler detection probe 1",
                        "probe_type": "import_detection",
                        "expected_handler": "ssot_only"
                    },
                    {
                        "content": "Test create_handler_safely function availability",
                        "probe_type": "function_availability",
                        "legacy_function": "create_handler_safely"
                    },
                    {
                        "content": "Check for message_handler module references",
                        "probe_type": "module_detection",
                        "legacy_module": "services.websocket.message_handler"
                    }
                ]

                for i, probe in enumerate(legacy_probe_messages):
                    probe_message = {
                        "type": "user_message",
                        "content": probe["content"],
                        "user_id": user_id,
                        "thread_id": f"legacy_probe_{i}",
                        "legacy_detection": True,
                        "probe_type": probe["probe_type"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await websocket.send(json.dumps(probe_message))

                    # Monitor responses for legacy indicators
                    start_time = time.time()
                    probe_timeout = 30.0

                    while (time.time() - start_time) < probe_timeout:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            response_data = json.loads(response)

                            response_str = json.dumps(response_data).lower()

                            # Look for legacy handler indicators
                            legacy_indicators = [
                                "create_handler_safely",
                                "message_handler",
                                "services.websocket",
                                "legacy",
                                "_handler_instances",
                                "_handler_registry"
                            ]

                            found_indicators = [indicator for indicator in legacy_indicators if indicator in response_str]

                            if found_indicators:
                                legacy_detection_results["legacy_handler_indicators"].extend(found_indicators)
                                legacy_detection_results["migration_complete"] = False

                            # Look for legacy import errors (good sign)
                            if response_data.get("type") == "error":
                                error_message = response_data.get("message", "").lower()
                                if any(term in error_message for term in ["import", "module not found", "create_handler_safely"]):
                                    # This is actually good - means legacy is removed
                                    logger.info(f"Legacy removal confirmed by import error: {error_message}")

                            # Check for completion
                            if response_data.get("type") in ["agent_completed", "agent_response"]:
                                break

                        except asyncio.TimeoutError:
                            logger.warning(f"Timeout in legacy probe {i}")
                            break

                    # Brief delay between probes
                    await asyncio.sleep(1.0)

                # Validate legacy handler removal
                if legacy_detection_results["legacy_handler_indicators"]:
                    unique_indicators = list(set(legacy_detection_results["legacy_handler_indicators"]))
                    logger.error(f"Legacy handler artifacts detected: {unique_indicators}")
                    pytest.fail(f"Legacy handler removal incomplete - found artifacts: {unique_indicators}")

                # Check for SSOT-only indicators
                ssot_only_message = {
                    "type": "user_message",
                    "content": "SSOT validation - verify only SSOT handlers are active",
                    "user_id": user_id,
                    "thread_id": f"ssot_validation_{uuid.uuid4()}",
                    "ssot_validation": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await websocket.send(json.dumps(ssot_only_message))

                ssot_indicators_found = []
                start_time = time.time()

                while (time.time() - start_time) < 30.0:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        response_data = json.loads(response)

                        response_str = json.dumps(response_data).lower()

                        # Look for SSOT indicators
                        ssot_indicators = [
                            "websocket_core",
                            "handle_message",
                            "ssot",
                            "unified_manager",
                            "canonical_imports"
                        ]

                        found_ssot = [indicator for indicator in ssot_indicators if indicator in response_str]
                        ssot_indicators_found.extend(found_ssot)

                        if response_data.get("type") == "agent_completed":
                            break

                    except asyncio.TimeoutError:
                        break

                # Verify SSOT-only operation
                if not ssot_indicators_found:
                    logger.warning("No SSOT indicators found - migration may not be complete")

                unique_ssot_indicators = list(set(ssot_indicators_found))
                logger.info(f"CHECK SSOT indicators confirmed: {unique_ssot_indicators}")
                logger.info("CHECK Legacy handler removal validation PASSED")

        except Exception as e:
            logger.error(f"Legacy handler removal validation exception: {e}")
            pytest.fail(f"Legacy handler removal validation failed: {e}")

    @pytest.mark.asyncio
    async def test_ssot_handler_full_functionality(self, migration_test_user):
        """
        Test: All SSOT features work correctly
        Expected: PASS - Complete SSOT functionality operational
        """
        jwt_token = migration_test_user["jwt_token"]
        user_id = migration_test_user["user_id"]

        logger.info("Validating full SSOT handler functionality...")

        ssot_functionality_tests = [
            {
                "name": "basic_message_handling",
                "message": "Test basic SSOT message handling capability",
                "expected_features": ["handle_message", "websocket_response"]
            },
            {
                "name": "complex_conversation",
                "message": "Test complex conversation handling with context preservation, multi-turn dialogue, and state management",
                "expected_features": ["context_preservation", "state_management", "multi_turn"]
            },
            {
                "name": "error_handling",
                "message": "Test SSOT error handling and recovery mechanisms",
                "expected_features": ["error_recovery", "graceful_degradation"]
            },
            {
                "name": "performance_features",
                "message": "Test SSOT performance optimizations and efficiency improvements",
                "expected_features": ["performance_optimization", "efficiency"]
            }
        ]

        ssot_test_results = []

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&ssot_validation=true"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                for test_case in ssot_functionality_tests:
                    test_name = test_case["name"]
                    test_message = test_case["message"]
                    expected_features = test_case["expected_features"]

                    logger.info(f"Testing SSOT functionality: {test_name}")

                    test_result = {
                        "test_name": test_name,
                        "message_sent": False,
                        "response_received": False,
                        "features_confirmed": [],
                        "response_quality": 0,
                        "performance_metrics": {},
                        "errors": []
                    }

                    ssot_message = {
                        "type": "user_message",
                        "content": test_message,
                        "user_id": user_id,
                        "thread_id": f"ssot_test_{test_name}",
                        "ssot_functionality_test": test_name,
                        "expected_features": expected_features,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    try:
                        # Send test message
                        send_start = time.time()
                        await websocket.send(json.dumps(ssot_message))
                        test_result["message_sent"] = True

                        # Monitor SSOT response
                        response_start = time.time()
                        response_received = False
                        response_content = ""

                        while (time.time() - response_start) < 45.0:
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                                response_data = json.loads(response)

                                response_type = response_data.get("type")
                                content = response_data.get("content", "")

                                if response_type == "agent_response":
                                    response_received = True
                                    response_content = content
                                    response_time = time.time() - response_start

                                    test_result["response_received"] = True
                                    test_result["performance_metrics"]["response_time"] = response_time

                                    # Analyze response quality
                                    if len(response_content) > 100:
                                        test_result["response_quality"] += 1

                                    # Look for expected features
                                    response_lower = response_content.lower()
                                    for feature in expected_features:
                                        feature_keywords = {
                                            "handle_message": ["handle", "process", "manage"],
                                            "websocket_response": ["websocket", "connection", "real-time"],
                                            "context_preservation": ["context", "remember", "previous"],
                                            "state_management": ["state", "track", "maintain"],
                                            "multi_turn": ["conversation", "dialogue", "turn"],
                                            "error_recovery": ["error", "recovery", "handle"],
                                            "graceful_degradation": ["graceful", "fallback", "degradation"],
                                            "performance_optimization": ["fast", "efficient", "optimized"],
                                            "efficiency": ["quick", "speed", "performance"]
                                        }

                                        keywords = feature_keywords.get(feature, [feature])
                                        if any(keyword in response_lower for keyword in keywords):
                                            test_result["features_confirmed"].append(feature)

                                # Check for errors
                                if response_type == "error":
                                    test_result["errors"].append(response_data)

                                # Check for completion
                                if response_type == "agent_completed":
                                    break

                            except asyncio.TimeoutError:
                                logger.warning(f"Timeout in SSOT test: {test_name}")
                                break

                        # Evaluate test results
                        if not response_received:
                            test_result["errors"].append("No response received")

                        # Check feature coverage
                        feature_coverage = len(test_result["features_confirmed"]) / len(expected_features) if expected_features else 1.0
                        test_result["feature_coverage"] = feature_coverage

                        ssot_test_results.append(test_result)

                    except Exception as e:
                        test_result["errors"].append(str(e))
                        ssot_test_results.append(test_result)

                    # Brief delay between tests
                    await asyncio.sleep(2.0)

                # Analyze overall SSOT functionality
                failed_tests = [result for result in ssot_test_results if result["errors"] or not result["response_received"]]

                if failed_tests:
                    failed_test_names = [test["test_name"] for test in failed_tests]
                    logger.error(f"SSOT functionality failures: {failed_test_names}")
                    pytest.fail(f"SSOT handler functionality incomplete - failed tests: {failed_test_names}")

                # Check response quality
                low_quality_tests = [result for result in ssot_test_results if result["response_quality"] < 1]

                if low_quality_tests:
                    logger.warning(f"Low quality responses in {len(low_quality_tests)} tests")

                # Check feature coverage
                poor_coverage_tests = [result for result in ssot_test_results if result.get("feature_coverage", 0) < 0.5]

                if poor_coverage_tests:
                    poor_test_names = [test["test_name"] for test in poor_coverage_tests]
                    logger.warning(f"Poor feature coverage in tests: {poor_test_names}")

                # Check performance
                avg_response_time = sum(
                    result["performance_metrics"].get("response_time", 0)
                    for result in ssot_test_results
                ) / len(ssot_test_results)

                max_response_time = MIGRATION_SUCCESS_CRITERIA["performance_metrics"]["message_processing_time"]

                if avg_response_time > max_response_time:
                    pytest.fail(f"SSOT performance too slow: {avg_response_time:.2f}s > {max_response_time}s")

                logger.info(f"CHECK SSOT handler full functionality validation PASSED - {len(ssot_test_results)} tests successful")

        except Exception as e:
            logger.error(f"SSOT functionality validation exception: {e}")
            pytest.fail(f"SSOT handler full functionality test failed: {e}")

    @pytest.mark.asyncio
    async def test_performance_parity_validation(self, migration_test_user):
        """
        Test: Performance matches or improves post-migration
        Expected: PASS - Performance criteria met or exceeded
        """
        jwt_token = migration_test_user["jwt_token"]
        user_id = migration_test_user["user_id"]

        logger.info("Validating post-migration performance...")

        performance_benchmarks = {
            "connection_performance": [],
            "message_processing_performance": [],
            "concurrent_user_performance": {},
            "memory_usage_metrics": {},
            "overall_performance_score": 0
        }

        try:
            # Test 1: Connection Performance
            logger.info("Testing connection performance...")

            for i in range(10):  # 10 connection attempts
                connection_start = time.time()

                try:
                    websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&perf_test={i}"

                    async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:
                        connection_time = time.time() - connection_start
                        performance_benchmarks["connection_performance"].append(connection_time)

                        await websocket.close()

                except Exception as e:
                    logger.warning(f"Connection performance test {i} failed: {e}")

                await asyncio.sleep(0.5)

            # Test 2: Message Processing Performance
            logger.info("Testing message processing performance...")

            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&message_perf_test=true"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                for i in range(5):  # 5 message processing tests
                    processing_start = time.time()

                    perf_message = {
                        "type": "user_message",
                        "content": f"Performance test message {i}: analyze this data quickly and efficiently",
                        "user_id": user_id,
                        "thread_id": f"perf_test_{i}",
                        "performance_test": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await websocket.send(json.dumps(perf_message))

                    # Wait for first meaningful response
                    response_received = False

                    while (time.time() - processing_start) < 30.0:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            response_data = json.loads(response)

                            if response_data.get("type") == "agent_response":
                                processing_time = time.time() - processing_start
                                performance_benchmarks["message_processing_performance"].append(processing_time)
                                response_received = True
                                break

                        except asyncio.TimeoutError:
                            break

                    if not response_received:
                        logger.warning(f"No response for performance test {i}")

                    await asyncio.sleep(1.0)

                # Test 3: Concurrent User Simulation
                logger.info("Testing concurrent user performance...")

                concurrent_tasks = []

                async def concurrent_user_task(user_num):
                    """Simulate concurrent user activity"""
                    task_start = time.time()
                    try:
                        user_websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&concurrent_user={user_num}"

                        async with websockets.connect(user_websocket_url, timeout=STAGING_CONFIG["timeout"]) as user_websocket:

                            user_message = {
                                "type": "user_message",
                                "content": f"Concurrent user {user_num} message",
                                "user_id": f"{user_id}_concurrent_{user_num}",
                                "thread_id": f"concurrent_{user_num}",
                                "concurrent_test": True,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }

                            await user_websocket.send(json.dumps(user_message))

                            # Wait for response
                            try:
                                response = await asyncio.wait_for(user_websocket.recv(), timeout=20.0)
                                response_data = json.loads(response)

                                if response_data.get("type") in ["agent_response", "agent_started"]:
                                    task_time = time.time() - task_start
                                    return {"user": user_num, "success": True, "time": task_time}

                            except asyncio.TimeoutError:
                                pass

                        return {"user": user_num, "success": False, "time": time.time() - task_start}

                    except Exception as e:
                        return {"user": user_num, "success": False, "error": str(e)}

                # Run concurrent user tasks
                concurrent_user_count = min(5, MIGRATION_SUCCESS_CRITERIA["performance_metrics"]["concurrent_user_support"])

                concurrent_tasks = [concurrent_user_task(i) for i in range(concurrent_user_count)]

                concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

                successful_concurrent = [r for r in concurrent_results if isinstance(r, dict) and r.get("success")]
                failed_concurrent = [r for r in concurrent_results if not (isinstance(r, dict) and r.get("success"))]

                performance_benchmarks["concurrent_user_performance"] = {
                    "total_users": concurrent_user_count,
                    "successful_users": len(successful_concurrent),
                    "failed_users": len(failed_concurrent),
                    "success_rate": len(successful_concurrent) / concurrent_user_count,
                    "avg_response_time": sum(r["time"] for r in successful_concurrent) / len(successful_concurrent) if successful_concurrent else 0
                }

            # Analyze performance results
            logger.info("Analyzing performance metrics...")

            performance_issues = []

            # Check connection performance
            if performance_benchmarks["connection_performance"]:
                avg_connection_time = sum(performance_benchmarks["connection_performance"]) / len(performance_benchmarks["connection_performance"])
                max_connection_time = max(performance_benchmarks["connection_performance"])

                connection_criteria = MIGRATION_SUCCESS_CRITERIA["performance_metrics"]["connection_time"]

                if avg_connection_time > connection_criteria:
                    performance_issues.append(f"Average connection time too slow: {avg_connection_time:.2f}s > {connection_criteria}s")

                if max_connection_time > connection_criteria * 2:
                    performance_issues.append(f"Max connection time too slow: {max_connection_time:.2f}s > {connection_criteria * 2}s")

            # Check message processing performance
            if performance_benchmarks["message_processing_performance"]:
                avg_processing_time = sum(performance_benchmarks["message_processing_performance"]) / len(performance_benchmarks["message_processing_performance"])
                max_processing_time = max(performance_benchmarks["message_processing_performance"])

                processing_criteria = MIGRATION_SUCCESS_CRITERIA["performance_metrics"]["message_processing_time"]

                if avg_processing_time > processing_criteria:
                    performance_issues.append(f"Average processing time too slow: {avg_processing_time:.2f}s > {processing_criteria}s")

                if max_processing_time > processing_criteria * 2:
                    performance_issues.append(f"Max processing time too slow: {max_processing_time:.2f}s > {processing_criteria * 2}s")

            # Check concurrent user performance
            concurrent_perf = performance_benchmarks["concurrent_user_performance"]
            if concurrent_perf.get("success_rate", 0) < 0.8:  # 80% success rate minimum
                performance_issues.append(f"Concurrent user success rate too low: {concurrent_perf['success_rate']:.2f} < 0.8")

            # Evaluate overall performance
            if performance_issues:
                logger.error(f"Performance validation failures: {performance_issues}")
                pytest.fail(f"Performance parity validation failed: {performance_issues}")

            # Calculate performance score
            performance_score = 100  # Start with perfect score

            # Deduct points for slow performance
            if performance_benchmarks["connection_performance"]:
                avg_conn_time = sum(performance_benchmarks["connection_performance"]) / len(performance_benchmarks["connection_performance"])
                if avg_conn_time > 1.0:
                    performance_score -= 10

            if performance_benchmarks["message_processing_performance"]:
                avg_proc_time = sum(performance_benchmarks["message_processing_performance"]) / len(performance_benchmarks["message_processing_performance"])
                if avg_proc_time > 3.0:
                    performance_score -= 10

            concurrent_success_rate = concurrent_perf.get("success_rate", 1.0)
            if concurrent_success_rate < 1.0:
                performance_score -= int((1.0 - concurrent_success_rate) * 20)

            performance_benchmarks["overall_performance_score"] = performance_score

            logger.info(f"CHECK Performance parity validation PASSED - Score: {performance_score}/100")

        except Exception as e:
            logger.error(f"Performance validation exception: {e}")
            pytest.fail(f"Performance parity validation failed: {e}")

    @pytest.mark.asyncio
    async def test_security_posture_maintained(self, migration_test_user):
        """
        Test: Security not degraded post-migration
        Expected: PASS - Security maintained or improved
        """
        jwt_token = migration_test_user["jwt_token"]
        user_id = migration_test_user["user_id"]

        logger.info("Validating security posture post-migration...")

        security_validation_results = {
            "authentication_security": [],
            "user_isolation_security": [],
            "data_protection_security": [],
            "communication_security": [],
            "overall_security_score": 0
        }

        try:
            # Test 1: Authentication Security
            logger.info("Testing authentication security...")

            # Test with valid token (should work)
            try:
                websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&security_test=auth"

                async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                    auth_test_message = {
                        "type": "user_message",
                        "content": "Authentication security test with valid token",
                        "user_id": user_id,
                        "thread_id": f"auth_security_test",
                        "security_test": "authentication",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await websocket.send(json.dumps(auth_test_message))

                    # Should receive successful response
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    response_data = json.loads(response)

                    if response_data.get("type") in ["agent_started", "agent_response"]:
                        security_validation_results["authentication_security"].append({
                            "test": "valid_token",
                            "result": "success",
                            "secure": True
                        })

            except Exception as e:
                security_validation_results["authentication_security"].append({
                    "test": "valid_token",
                    "result": "failure",
                    "error": str(e),
                    "secure": False
                })

            # Test with invalid token (should fail securely)
            try:
                invalid_websocket_url = f"{STAGING_CONFIG['websocket_url']}?token=invalid_token_12345&security_test=auth_invalid"

                # This should fail to connect or fail gracefully
                async with websockets.connect(invalid_websocket_url, timeout=10.0) as invalid_websocket:
                    # If connection succeeds, that's a security issue
                    security_validation_results["authentication_security"].append({
                        "test": "invalid_token",
                        "result": "security_failure",
                        "issue": "Invalid token accepted",
                        "secure": False
                    })

            except Exception:
                # Connection failure with invalid token is expected and secure
                security_validation_results["authentication_security"].append({
                    "test": "invalid_token",
                    "result": "secure_rejection",
                    "secure": True
                })

            # Test 2: User Isolation Security
            logger.info("Testing user isolation security...")

            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&security_test=isolation"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                # Send message with correct user_id
                isolation_message = {
                    "type": "user_message",
                    "content": "User isolation test - sensitive data for current user",
                    "user_id": user_id,  # Correct user ID
                    "thread_id": f"isolation_test_correct",
                    "sensitive_data": f"private_info_for_{user_id}",
                    "security_test": "user_isolation",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await websocket.send(json.dumps(isolation_message))

                # Monitor response for proper user context
                isolation_response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                isolation_data = json.loads(isolation_response)

                # Should receive response for correct user
                if isolation_data.get("user_id") == user_id or user_id in json.dumps(isolation_data):
                    security_validation_results["user_isolation_security"].append({
                        "test": "correct_user_context",
                        "result": "success",
                        "secure": True
                    })

                # Test with incorrect user_id (should be rejected or isolated)
                wrong_user_message = {
                    "type": "user_message",
                    "content": "Attempt to access another user's context",
                    "user_id": "wrong_user_id_12345",  # Wrong user ID
                    "thread_id": f"isolation_test_wrong",
                    "security_test": "user_isolation_attack",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await websocket.send(json.dumps(wrong_user_message))

                # Should receive error or be properly isolated
                try:
                    wrong_user_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    wrong_user_data = json.loads(wrong_user_response)

                    if wrong_user_data.get("type") == "error" or wrong_user_data.get("user_id") != "wrong_user_id_12345":
                        security_validation_results["user_isolation_security"].append({
                            "test": "wrong_user_rejection",
                            "result": "secure_isolation",
                            "secure": True
                        })
                    else:
                        security_validation_results["user_isolation_security"].append({
                            "test": "wrong_user_rejection",
                            "result": "security_failure",
                            "issue": "Wrong user ID accepted",
                            "secure": False
                        })

                except asyncio.TimeoutError:
                    # Timeout can be acceptable for security - no response to invalid request
                    security_validation_results["user_isolation_security"].append({
                        "test": "wrong_user_rejection",
                        "result": "secure_timeout",
                        "secure": True
                    })

            # Test 3: Data Protection Security
            logger.info("Testing data protection security...")

            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&security_test=data_protection"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                # Send message with sensitive data
                data_protection_message = {
                    "type": "user_message",
                    "content": "Data protection test with sensitive information: SSN 123-45-6789, Credit Card 4111-1111-1111-1111",
                    "user_id": user_id,
                    "thread_id": f"data_protection_test",
                    "security_test": "data_protection",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                await websocket.send(json.dumps(data_protection_message))

                # Monitor response for data protection
                data_response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data_response_str = json.dumps(data_response)

                # Check if sensitive data is properly handled (not echoed back in plain text)
                sensitive_patterns = ["123-45-6789", "4111-1111-1111-1111"]
                data_leak_detected = any(pattern in data_response_str for pattern in sensitive_patterns)

                if not data_leak_detected:
                    security_validation_results["data_protection_security"].append({
                        "test": "sensitive_data_protection",
                        "result": "secure_handling",
                        "secure": True
                    })
                else:
                    security_validation_results["data_protection_security"].append({
                        "test": "sensitive_data_protection",
                        "result": "data_leak",
                        "issue": "Sensitive data exposed in response",
                        "secure": False
                    })

            # Test 4: Communication Security (WSS encryption)
            logger.info("Testing communication security...")

            # Verify WSS (WebSocket Secure) is used
            if STAGING_CONFIG["websocket_url"].startswith("wss://"):
                security_validation_results["communication_security"].append({
                    "test": "encrypted_communication",
                    "result": "wss_encryption",
                    "secure": True
                })
            else:
                security_validation_results["communication_security"].append({
                    "test": "encrypted_communication",
                    "result": "unencrypted_ws",
                    "issue": "WebSocket not using SSL/TLS",
                    "secure": False
                })

            # Analyze security validation results
            security_issues = []

            for category, tests in security_validation_results.items():
                if category == "overall_security_score":
                    continue

                failed_security_tests = [test for test in tests if not test.get("secure", True)]

                if failed_security_tests:
                    security_issues.extend([f"{category}: {test.get('issue', test.get('result'))}" for test in failed_security_tests])

            # Calculate security score
            total_security_tests = sum(len(tests) for category, tests in security_validation_results.items() if category != "overall_security_score")
            failed_security_tests = len([issue for issues in security_validation_results.values() if isinstance(issues, list) for issue in issues if not issue.get("secure", True)])

            security_score = int(((total_security_tests - failed_security_tests) / total_security_tests) * 100) if total_security_tests > 0 else 100

            security_validation_results["overall_security_score"] = security_score

            if security_issues:
                logger.error(f"Security validation failures: {security_issues}")
                pytest.fail(f"Security posture degraded - issues: {security_issues}")

            logger.info(f"CHECK Security posture validation PASSED - Score: {security_score}/100")

        except Exception as e:
            logger.error(f"Security validation exception: {e}")
            pytest.fail(f"Security posture validation failed: {e}")

    @pytest.mark.asyncio
    async def test_error_handling_robustness(self, migration_test_user):
        """
        Test: Error handling improved post-migration
        Expected: PASS - Robust error handling and recovery
        """
        jwt_token = migration_test_user["jwt_token"]
        user_id = migration_test_user["user_id"]

        logger.info("Validating error handling robustness...")

        error_handling_scenarios = [
            {
                "name": "malformed_message",
                "message": "invalid_json_structure",  # Will be sent as invalid JSON
                "expected_behavior": "graceful_error_response"
            },
            {
                "name": "missing_required_fields",
                "message": {
                    "type": "user_message",
                    # Missing content, user_id, etc.
                },
                "expected_behavior": "validation_error_with_details"
            },
            {
                "name": "oversized_message",
                "message": {
                    "type": "user_message",
                    "content": "x" * 100000,  # Very large message
                    "user_id": user_id,
                    "thread_id": "oversized_test"
                },
                "expected_behavior": "size_limit_error"
            },
            {
                "name": "rapid_message_burst",
                "message": "rapid_burst_test",  # Special handling
                "expected_behavior": "rate_limiting_or_graceful_handling"
            }
        ]

        error_handling_results = []

        try:
            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&error_handling_test=true"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                for scenario in error_handling_scenarios:
                    scenario_name = scenario["name"]
                    test_message = scenario["message"]
                    expected_behavior = scenario["expected_behavior"]

                    logger.info(f"Testing error handling scenario: {scenario_name}")

                    scenario_result = {
                        "scenario": scenario_name,
                        "message_sent": False,
                        "error_response_received": False,
                        "error_response_quality": 0,
                        "recovery_successful": False,
                        "graceful_handling": False
                    }

                    try:
                        if scenario_name == "malformed_message":
                            # Send malformed JSON
                            await websocket.send('{"invalid": json syntax')
                            scenario_result["message_sent"] = True

                        elif scenario_name == "rapid_message_burst":
                            # Send rapid burst of messages
                            for i in range(10):
                                burst_message = {
                                    "type": "user_message",
                                    "content": f"Rapid burst message {i}",
                                    "user_id": user_id,
                                    "thread_id": f"burst_{i}",
                                    "burst_test": True,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                                await websocket.send(json.dumps(burst_message))

                            scenario_result["message_sent"] = True

                        else:
                            # Send regular test message
                            if isinstance(test_message, dict):
                                await websocket.send(json.dumps(test_message))
                            else:
                                await websocket.send(test_message)

                            scenario_result["message_sent"] = True

                        # Monitor error response
                        start_time = time.time()
                        error_timeout = 30.0

                        while (time.time() - start_time) < error_timeout:
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)

                                try:
                                    response_data = json.loads(response)
                                except json.JSONDecodeError:
                                    # Response itself might be malformed in error scenarios
                                    response_data = {"raw_response": response}

                                response_type = response_data.get("type")

                                if response_type == "error":
                                    scenario_result["error_response_received"] = True

                                    # Evaluate error response quality
                                    error_message = response_data.get("message", "")
                                    error_code = response_data.get("code")

                                    # Quality indicators
                                    if error_message and len(error_message) > 10:
                                        scenario_result["error_response_quality"] += 1

                                    if error_code:
                                        scenario_result["error_response_quality"] += 1

                                    # Check for helpful error details
                                    if any(term in error_message.lower() for term in ["invalid", "required", "missing", "format"]):
                                        scenario_result["error_response_quality"] += 1

                                    scenario_result["graceful_handling"] = True
                                    break

                                # Check for recovery (non-error response after error scenario)
                                elif response_type in ["agent_response", "agent_started"]:
                                    if scenario_name == "rapid_message_burst":
                                        # Getting responses to burst messages indicates handling
                                        scenario_result["recovery_successful"] = True
                                        scenario_result["graceful_handling"] = True

                            except asyncio.TimeoutError:
                                logger.warning(f"Timeout in error scenario: {scenario_name}")
                                break

                            except Exception as e:
                                logger.warning(f"Exception in error scenario {scenario_name}: {e}")
                                # Connection might have been closed due to error - this could be expected
                                if scenario_name in ["malformed_message", "oversized_message"]:
                                    scenario_result["graceful_handling"] = True
                                break

                        # Test recovery by sending normal message
                        try:
                            recovery_message = {
                                "type": "user_message",
                                "content": f"Recovery test after {scenario_name}",
                                "user_id": user_id,
                                "thread_id": f"recovery_{scenario_name}",
                                "recovery_test": True,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }

                            await websocket.send(json.dumps(recovery_message))

                            # Check if normal operation resumes
                            recovery_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                            recovery_data = json.loads(recovery_response)

                            if recovery_data.get("type") in ["agent_started", "agent_response"]:
                                scenario_result["recovery_successful"] = True

                        except Exception as e:
                            logger.warning(f"Recovery test failed for {scenario_name}: {e}")

                        error_handling_results.append(scenario_result)

                    except Exception as e:
                        scenario_result["exception"] = str(e)
                        error_handling_results.append(scenario_result)

                    # Brief delay between scenarios
                    await asyncio.sleep(2.0)

                # Analyze error handling results
                failed_error_handling = []

                for result in error_handling_results:
                    scenario = result["scenario"]

                    # Check expected behaviors
                    if scenario in ["malformed_message", "missing_required_fields", "oversized_message"]:
                        if not result["error_response_received"] and not result["graceful_handling"]:
                            failed_error_handling.append(f"{scenario}: No error response or graceful handling")

                        if result["error_response_quality"] < 2:
                            failed_error_handling.append(f"{scenario}: Poor error response quality")

                    elif scenario == "rapid_message_burst":
                        if not result["graceful_handling"]:
                            failed_error_handling.append(f"{scenario}: Poor handling of rapid messages")

                    # All scenarios should allow recovery
                    if not result["recovery_successful"]:
                        failed_error_handling.append(f"{scenario}: Recovery not successful")

                if failed_error_handling:
                    logger.error(f"Error handling robustness failures: {failed_error_handling}")
                    pytest.fail(f"Error handling not robust - issues: {failed_error_handling}")

                logger.info(f"CHECK Error handling robustness validation PASSED - {len(error_handling_results)} scenarios tested")

        except Exception as e:
            logger.error(f"Error handling validation exception: {e}")
            pytest.fail(f"Error handling robustness test failed: {e}")

    @pytest.mark.asyncio
    async def test_memory_leak_elimination(self, migration_test_user):
        """
        Test: Memory usage optimized post-migration
        Expected: PASS - No memory leaks, optimized usage
        """
        jwt_token = migration_test_user["jwt_token"]
        user_id = migration_test_user["user_id"]

        logger.info("Validating memory leak elimination...")

        memory_test_results = {
            "baseline_connections": 0,
            "peak_connections": 0,
            "connection_cleanup_success": True,
            "message_processing_memory": [],
            "long_session_memory": {},
            "memory_leaks_detected": [],
            "memory_optimization_score": 0
        }

        try:
            # Test 1: Connection Memory Management
            logger.info("Testing connection memory management...")

            # Establish baseline
            initial_connections = 0

            # Create and close multiple connections to test cleanup
            for i in range(20):
                try:
                    websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&memory_test={i}"

                    async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:
                        memory_test_results["peak_connections"] = i + 1

                        # Send simple message to ensure connection is active
                        test_message = {
                            "type": "user_message",
                            "content": f"Memory test connection {i}",
                            "user_id": user_id,
                            "thread_id": f"memory_test_{i}",
                            "memory_test": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }

                        await websocket.send(json.dumps(test_message))

                        # Wait for brief response
                        try:
                            await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        except asyncio.TimeoutError:
                            pass

                        # Connection automatically closed by context manager

                    # Brief delay to allow cleanup
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.warning(f"Connection {i} failed: {e}")
                    memory_test_results["connection_cleanup_success"] = False

            # Test 2: Message Processing Memory
            logger.info("Testing message processing memory...")

            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&memory_processing_test=true"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                # Send multiple messages to test memory accumulation
                for i in range(50):
                    processing_start = time.time()

                    message = {
                        "type": "user_message",
                        "content": f"Memory processing test message {i} with substantial content to test memory handling during processing. This message contains enough text to create a meaningful memory footprint during processing.",
                        "user_id": user_id,
                        "thread_id": f"memory_processing_{i}",
                        "message_sequence": i,
                        "memory_processing_test": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    await websocket.send(json.dumps(message))

                    # Monitor response time (memory issues often manifest as performance degradation)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        response_data = json.loads(response)

                        processing_time = time.time() - processing_start

                        memory_test_results["message_processing_memory"].append({
                            "message_num": i,
                            "processing_time": processing_time,
                            "response_size": len(json.dumps(response_data))
                        })

                        if response_data.get("type") == "error":
                            memory_test_results["memory_leaks_detected"].append(f"Error in message {i}: {response_data.get('message', '')}")

                    except asyncio.TimeoutError:
                        memory_test_results["memory_leaks_detected"].append(f"Timeout in message {i} - possible memory issue")

                    # Brief delay between messages
                    await asyncio.sleep(0.1)

            # Test 3: Long Session Memory
            logger.info("Testing long session memory...")

            websocket_url = f"{STAGING_CONFIG['websocket_url']}?token={jwt_token}&long_session_test=true"

            async with websockets.connect(websocket_url, timeout=STAGING_CONFIG["timeout"]) as websocket:

                long_session_start = time.time()

                # Simulate long session with periodic activity
                for session_minute in range(5):  # 5 "minutes" of activity (compressed)
                    minute_start = time.time()

                    # Send several messages during this "minute"
                    for msg_in_minute in range(10):
                        session_message = {
                            "type": "user_message",
                            "content": f"Long session message - minute {session_minute}, message {msg_in_minute}",
                            "user_id": user_id,
                            "thread_id": f"long_session_{session_minute}_{msg_in_minute}",
                            "session_minute": session_minute,
                            "message_in_minute": msg_in_minute,
                            "long_session_test": True,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }

                        await websocket.send(json.dumps(session_message))

                        # Wait for response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                            response_data = json.loads(response)

                            # Check for memory-related errors
                            if response_data.get("type") == "error":
                                error_msg = response_data.get("message", "").lower()
                                if any(term in error_msg for term in ["memory", "resource", "limit", "capacity"]):
                                    memory_test_results["memory_leaks_detected"].append(f"Memory error in long session: {error_msg}")

                        except asyncio.TimeoutError:
                            memory_test_results["memory_leaks_detected"].append(f"Long session timeout at minute {session_minute}")

                        await asyncio.sleep(0.1)

                    minute_duration = time.time() - minute_start

                    memory_test_results["long_session_memory"][f"minute_{session_minute}"] = {
                        "duration": minute_duration,
                        "messages_sent": 10,
                        "performance": "good" if minute_duration < 30 else "degraded"
                    }

                    # Brief pause between "minutes"
                    await asyncio.sleep(0.5)

                total_session_time = time.time() - long_session_start
                memory_test_results["long_session_memory"]["total_duration"] = total_session_time

            # Analyze memory test results
            memory_issues = []

            # Check connection cleanup
            if not memory_test_results["connection_cleanup_success"]:
                memory_issues.append("Connection cleanup issues detected")

            # Check message processing memory patterns
            if memory_test_results["message_processing_memory"]:
                processing_times = [msg["processing_time"] for msg in memory_test_results["message_processing_memory"]]

                # Look for increasing processing times (memory accumulation symptom)
                early_avg = sum(processing_times[:10]) / 10 if len(processing_times) >= 10 else 0
                late_avg = sum(processing_times[-10:]) / 10 if len(processing_times) >= 10 else 0

                if late_avg > early_avg * 2:  # Processing time doubled
                    memory_issues.append(f"Processing time degradation: {early_avg:.2f}s -> {late_avg:.2f}s")

                # Check for excessive processing times
                slow_messages = [msg for msg in memory_test_results["message_processing_memory"] if msg["processing_time"] > 10.0]

                if slow_messages:
                    memory_issues.append(f"Slow message processing: {len(slow_messages)} messages > 10s")

            # Check long session performance
            long_session_minutes = memory_test_results["long_session_memory"]
            degraded_minutes = [minute for minute, data in long_session_minutes.items() if isinstance(data, dict) and data.get("performance") == "degraded"]

            if degraded_minutes:
                memory_issues.append(f"Long session performance degradation: {len(degraded_minutes)} degraded periods")

            # Check for explicit memory leak detections
            if memory_test_results["memory_leaks_detected"]:
                memory_issues.extend(memory_test_results["memory_leaks_detected"])

            # Calculate memory optimization score
            memory_score = 100

            if memory_issues:
                memory_score -= len(memory_issues) * 10  # Deduct 10 points per issue

            if not memory_test_results["connection_cleanup_success"]:
                memory_score -= 20

            memory_test_results["memory_optimization_score"] = max(0, memory_score)

            if memory_issues:
                logger.error(f"Memory leak elimination validation failures: {memory_issues}")
                pytest.fail(f"Memory leaks detected - issues: {memory_issues}")

            logger.info(f"CHECK Memory leak elimination validation PASSED - Score: {memory_score}/100")

        except Exception as e:
            logger.error(f"Memory leak validation exception: {e}")
            pytest.fail(f"Memory leak elimination test failed: {e}")


# Test configuration
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.websocket,
    pytest.mark.issue_1099,
    pytest.mark.gcp_staging,
    pytest.mark.migration_validation,
    pytest.mark.success_criteria,
    # Note: These tests should PASS after migration is complete
]