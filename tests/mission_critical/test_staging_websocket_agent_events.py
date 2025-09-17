#!/usr/bin/env python
"
MISSION CRITICAL TEST SUITE: Staging WebSocket Agent Events

THIS SUITE VALIDATES WEBSOCKET FUNCTIONALITY IN STAGING ENVIRONMENT.
Business Value: $500K+ ARR - Core chat functionality must work in production-like environment

This test suite:
1. Connects to real staging WebSocket endpoint (wss://api.staging.netrasystems.ai/ws)
2. Uses real authentication via staging auth service
3. Tests all critical WebSocket event flows with real services
4. Validates agent event tracking works correctly
5. Ensures SSL/TLS handling is correct for wss:// connections

ANY FAILURE HERE INDICATES STAGING WEBSOCKET ISSUES THAT WILL AFFECT PRODUCTION.
""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
import logging
from shared.isolated_environment import IsolatedEnvironment

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import staging test utilities
from test_framework.staging_websocket_test_helper import StagingWebSocketTestHelper, WebSocketEventRecord
from tests.e2e.staging_config import get_staging_config
from tests.e2e.staging_auth_client import StagingAuthClient

# Set up logging
logging.basicConfig(level=logging.INFO)


class StagingWebSocketEventValidator:
    ""Validates WebSocket events in staging environment with production requirements."

    REQUIRED_EVENTS = {
        "agent_started,
        agent_thinking",
        "tool_executing,
        tool_completed",
        "agent_completed
    }

    # Additional events that may be sent in real scenarios
    OPTIONAL_EVENTS = {
        agent_fallback",
        "final_report,
        partial_result",
        "tool_error
    }

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[WebSocketEventRecord] = []
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()

    def record_event(self, event: WebSocketEventRecord) -> None:
        ""Record an event for validation."
        self.events.append(event)
        self.event_counts[event.event_type] = self.event_counts.get(event.event_type, 0) + 1

    def validate_staging_requirements(self) -> tuple[bool, List[str]]:
        "Validate that all staging requirements are met.""
        failures = []

        # 1. Check for required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(fCRITICAL: Missing required events in staging: {missing}")

        # 2. Validate event ordering
        if not self._validate_event_order():
            failures.append("CRITICAL: Invalid event order in staging)

        # 3. Check for paired events
        if not self._validate_paired_events():
            failures.append(CRITICAL: Unpaired tool events in staging")

        # 4. Validate timing constraints (more lenient for staging due to cold starts)
        if not self._validate_staging_timing():
            failures.append("CRITICAL: Event timing violations in staging)

        # 5. Check for data completeness
        if not self._validate_event_data():
            failures.append(CRITICAL: Incomplete event data in staging")

        return len(failures) == 0, failures

    def _validate_event_order(self) -> bool:
        "Ensure events follow logical order.""
        if not self.events:
            return False

        # First event must be agent_started
        if self.events[0].event_type != agent_started":
            self.errors.append(f"First event was {self.events[0].event_type}, not agent_started)
            return False

        # Last event should be completion
        last_event = self.events[-1].event_type
        if last_event not in [agent_completed", "final_report, agent_error"]:
            self.errors.append(f"Last event was {last_event}, not a completion event)
            return False

        return True

    def _validate_paired_events(self) -> bool:
        ""Ensure tool events are properly paired."
        tool_starts = self.event_counts.get("tool_executing, 0)
        tool_ends = self.event_counts.get(tool_completed", 0)

        if tool_starts != tool_ends:
            self.errors.append(f"Tool event mismatch: {tool_starts} starts, {tool_ends} completions)
            return False

        return True

    def _validate_staging_timing(self) -> bool:
        ""Validate event timing constraints (lenient for staging cold starts)."
        if not self.events:
            return True

        duration = self.events[-1].timestamp - self.events[0].timestamp
        # More lenient timing for staging due to cold starts and network latency
        if duration > 120:  # 2 minute timeout for staging
            self.errors.append(f"Agent flow took too long in staging: {duration:.2f}s)
            return False

        return True

    def _validate_event_data(self) -> bool:
        ""Ensure events contain required data fields."
        for event in self.events:
            if not event.event_type:
                self.errors.append("Event missing event_type)
                return False
            if not event.data:
                self.errors.append(fEvent {event.event_type} missing data")
                return False

        return True

    def generate_staging_report(self) -> str:
        "Generate staging validation report.""
        is_valid, failures = self.validate_staging_requirements()

        report = [
            \n" + "= * 80,
            STAGING WEBSOCKET VALIDATION REPORT",
            "= * 80,
            fStatus: {'PASS - STAGING READY' if is_valid else 'FAIL - STAGING ISSUES'}",
            f"Total Events: {len(self.events)},
            fUnique Types: {len(self.event_counts)}",
            f"Duration: {(self.events[-1].timestamp - self.events[0].timestamp) if len(self.events) > 1 else 0:.2f}s,
            ",
            "Event Coverage:
        ]

        for event in self.REQUIRED_EVENTS:
            count = self.event_counts.get(event, 0)
            status = PASS" if count > 0 else "FAIL
            report.append(f  {status}: {event}: {count}")

        if failures:
            report.extend([", STAGING FAILURES:"] + [f"  - {f} for f in failures]

        if self.errors:
            report.extend([", "ERRORS:] + [f  - {e}" for e in self.errors]

        if self.warnings:
            report.extend([", WARNINGS:"] + [f"  - {w} for w in self.warnings]

        report.append(=" * 80)
        return "\n.join(report)


# ============================================================================
# STAGING WEBSOCKET TESTS
# ============================================================================

class StagingWebSocketFlowTests:
    ""Test WebSocket functionality against real staging environment."

    @pytest.fixture(autouse=True)
    async def setup_staging_websocket(self):
        "Setup staging WebSocket helper for tests.""
        self.config = get_staging_config()
        self.helper = StagingWebSocketTestHelper()

        # Verify staging configuration
        if not self.config.validate_configuration():
            pytest.skip(Staging configuration not valid")

        yield

        # Cleanup
        if self.helper:
            await self.helper.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.critical
    @pytest.mark.timeout(120)  # Longer timeout for staging cold starts
    async def test_staging_websocket_connection_with_auth(self):
        "Test that we can connect to staging WebSocket with proper authentication.""
        logger.info(Testing staging WebSocket connection with authentication")

        # Test connection
        connected = await self.helper.connect_with_auth(
            email="e2e-test@staging.netrasystems.ai,
            name=E2E Test User"
        )

        assert connected, "Failed to connect to staging WebSocket with authentication
        assert self.helper.is_connected, Helper should report connected state"
        assert self.helper.current_token is not None, "Should have authentication token

        logger.info(PASS: Successfully connected to staging WebSocket with authentication")

    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.critical
    @pytest.mark.timeout(180)  # Extra time for staging agent processing
    async def test_staging_agent_websocket_flow(self):
        "Test complete agent flow through staging WebSocket.""
        logger.info(Testing complete agent flow in staging environment")

        # Connect with authentication
        connected = await self.helper.connect_with_auth()
        assert connected, "Failed to connect to staging WebSocket

        # Setup event validator
        validator = StagingWebSocketEventValidator()

        # Register event handler
        def record_event(data):
            event = WebSocketEventRecord(
                event_type=data.get(type"),
                data=data,
                timestamp=time.time(),
                thread_id=data.get("thread_id, unknown")
            )
            validator.record_event(event)
            logger.info(f"Staging event: {event.event_type})

        # Register handlers for all critical events
        for event_type in validator.REQUIRED_EVENTS:
            self.helper.on_event(event_type, record_event)

        # Send agent request
        thread_id = fstaging-test-{int(time.time())}"
        query = "What is the current system status? Please provide a brief summary.

        success = await self.helper.send_agent_request(
            query=query,
            agent_type=supervisor",
            thread_id=thread_id
        )
        assert success, "Failed to send agent request to staging

        # Wait for complete agent flow
        flow_result = await self.helper.wait_for_agent_flow(
            thread_id=thread_id,
            timeout=120.0  # Generous timeout for staging
        )

        # Validate flow completed
        assert flow_result[success"], f"Agent flow failed in staging: {flow_result}

        # Validate events
        is_valid, failures = validator.validate_staging_requirements()

        if not is_valid:
            logger.error(validator.generate_staging_report())

        assert is_valid, fStaging WebSocket validation failed: {failures}"

        logger.info(f"PASS: Agent flow completed successfully in staging:)
        logger.info(f  - Duration: {flow_result['duration']:.2f}s")
        logger.info(f"  - Events: {flow_result['total_events']})
        logger.info(f  - Types: {flow_result['event_types']}")

    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_staging_websocket_ssl_tls_security(self):
        "Test that staging WebSocket uses proper SSL/TLS security.""
        logger.info(Testing staging WebSocket SSL/TLS security")

        # Verify we're using wss:// protocol
        ws_url = self.config.urls.websocket_url
        assert ws_url.startswith('wss://'), f"Staging should use secure WebSocket (wss://), got: {ws_url}

        # Test connection with SSL validation
        connected = await self.helper.connect_with_auth()
        assert connected, Failed to connect to staging WebSocket with SSL/TLS"

        # Send a test message to verify the connection works
        success = await self.helper.send_message(
            message_type="ping,
            data={test": "ssl_verification},
            thread_id=ssl-test"
        )
        assert success, "Failed to send message over secure WebSocket connection

        logger.info(PASS: Staging WebSocket SSL/TLS security validated")

    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_staging_websocket_reconnection(self):
        "Test WebSocket reconnection handling in staging.""
        logger.info(Testing staging WebSocket reconnection")

        # Initial connection
        connected = await self.helper.connect_with_auth()
        assert connected, "Failed initial connection to staging WebSocket

        original_connection = self.helper.websocket

        # Simulate connection loss by closing WebSocket
        await original_connection.close()

        # Give time for connection to be detected as closed
        await asyncio.sleep(2)

        # Attempt reconnection
        reconnected = await self.helper.connect_with_auth(force_refresh=False)
        assert reconnected, Failed to reconnect to staging WebSocket"
        assert self.helper.websocket != original_connection, "Should have new WebSocket connection

        # Test that reconnected connection works
        success = await self.helper.send_message(
            message_type=reconnection_test",
            data={"test: after_reconnection"},
            thread_id="reconnect-test
        )
        assert success, Reconnected WebSocket should work"

        logger.info("PASS: Staging WebSocket reconnection working)

    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.performance
    @pytest.mark.timeout(120)
    async def test_staging_websocket_performance(self):
        ""Test WebSocket performance in staging environment."
        logger.info("Testing staging WebSocket performance)

        # Connect to staging
        connected = await self.helper.connect_with_auth()
        assert connected, Failed to connect for performance test"

        # Send multiple messages to test throughput
        message_count = 50
        start_time = time.time()
        successful_sends = 0

        for i in range(message_count):
            success = await self.helper.send_message(
                message_type="performance_test,
                data={sequence": i, "timestamp: time.time()},
                thread_id=fperf-test-{i}"
            )
            if success:
                successful_sends += 1

        duration = time.time() - start_time
        messages_per_second = successful_sends / duration

        logger.info(f"Staging WebSocket performance: {successful_sends}/{message_count} messages in {duration:.2f}s)
        logger.info(fThroughput: {messages_per_second:.1f} messages/second")

        # Performance assertions (lenient for staging)
        assert successful_sends >= message_count * 0.9, f"Too many failed sends: {successful_sends}/{message_count}
        assert messages_per_second > 10, fThroughput too low: {messages_per_second:.1f} msg/s"

        logger.info("PASS: Staging WebSocket performance acceptable)


# ============================================================================
# STAGING REGRESSION PREVENTION TESTS
# ============================================================================

class StagingRegressionPreventionTests:
    ""Tests to prevent regression of staging-specific WebSocket issues."

    @pytest.fixture(autouse=True)
    async def setup_staging_regression_tests(self):
        "Setup for regression tests.""
        self.config = get_staging_config()
        self.helper = StagingWebSocketTestHelper()

        if not self.config.validate_configuration():
            pytest.skip(Staging configuration not valid")

        yield

        if self.helper:
            await self.helper.disconnect()

    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.critical
    async def test_staging_websocket_auth_headers_correct(self):
        "REGRESSION TEST: Ensure staging WebSocket uses correct auth headers.""
        logger.info(Testing staging WebSocket authentication headers")

        # Get auth token
        auth_client = StagingAuthClient()
        tokens = await auth_client.get_auth_token()
        token = tokens["access_token]

        # Check that helper creates correct headers
        headers = self.config.get_websocket_headers(token)

        assert Authorization" in headers, "Missing Authorization header
        assert headers[Authorization"].startswith("Bearer ), Authorization header should use Bearer token"
        assert headers["Authorization].endswith(token), Authorization header should contain correct token"

        # Test connection works with these headers
        connected = await self.helper.connect_with_auth()
        assert connected, "Connection should work with correct auth headers

        logger.info(PASS: Staging WebSocket authentication headers correct")

    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.critical
    async def test_staging_websocket_error_handling(self):
        "REGRESSION TEST: Ensure staging WebSocket handles errors gracefully.""
        logger.info(Testing staging WebSocket error handling")

        # Connect to staging
        connected = await self.helper.connect_with_auth()
        assert connected, "Failed to connect for error handling test

        # Send invalid message to trigger error handling
        success = await self.helper.send_message(
            message_type=invalid_test_message",
            data={"invalid: data", "should_cause: graceful_handling"},
            thread_id="error-test
        )

        # Message should be sent (server handles validation)
        assert success, Should be able to send message even if server will reject it"

        # Connection should remain stable
        await asyncio.sleep(2)  # Give time for any error response
        assert self.helper.is_connected, "Connection should remain stable after error

        # Should still be able to send valid messages
        valid_success = await self.helper.send_message(
            message_type=ping",
            data={"test: after_error"},
            thread_id="after-error-test
        )
        assert valid_success, Should be able to send valid messages after error"

        logger.info("PASS: Staging WebSocket error handling working)


# ============================================================================
# TEST SUITE RUNNER
# ============================================================================

@pytest.mark.staging
@pytest.mark.mission_critical
class StagingMissionCriticalSuiteTests:
    ""Main test suite for staging WebSocket validation."

    @pytest.mark.asyncio
    async def test_run_staging_websocket_suite(self):
        "Run staging WebSocket validation suite.""
        logger.info(\n" + "= * 80)
        logger.info(RUNNING STAGING WEBSOCKET VALIDATION SUITE")
        logger.info("= * 80)

        # Validate staging configuration
        config = get_staging_config()
        if not config.validate_configuration():
            pytest.fail(Staging configuration validation failed - cannot run WebSocket tests")

        logger.info(f"PASS: Staging configuration validated:)
        logger.info(f  - WebSocket URL: {config.urls.websocket_url}")
        logger.info(f"  - Backend URL: {config.urls.backend_url})
        logger.info(f  - Auth URL: {config.urls.auth_url}")

        # This test validates the suite itself is operational
        logger.info("PASS: Staging WebSocket test suite is operational)
        logger.info(Run individual tests with: pytest tests/mission_critical/test_staging_websocket_agent_events.py -v")


if __name__ == "__main__:
    # MIGRATED: Use SSOT unified test runner instead of direct pytest execution
    # Issue #1024: Unauthorized test runners blocking Golden Path
    print(MIGRATION NOTICE: This file previously used direct pytest execution.")
    print("Please use: python tests/unified_test_runner.py --category <appropriate_category>)
    print(For more info: reports/TEST_EXECUTION_GUIDE.md")

    # Uncomment and customize the following for SSOT execution:
    # result = run_tests_via_ssot_runner()
    # sys.exit(result)
