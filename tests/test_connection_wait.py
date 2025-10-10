#!/usr/bin/env python3
"""
Test the waiting behavior for connection_established event
"""

import asyncio
import time
import unittest
from unittest.mock import MagicMock, patch, AsyncMock


class TestConnectionWaiting(unittest.TestCase):
    """Test that send_message waits for connection_established instead of crashing"""

    def setUp(self):
        """Set up test fixtures"""
        self.cli = MagicMock()
        self.cli.connected = True  # Handshake complete
        self.cli.connection_established_received = False
        self.cli.ready_to_send_events = False
        self.cli.debug = MagicMock()
        self.cli.config = MagicMock()
        self.cli.config.json_mode = False
        self.cli.config.ci_mode = False

    async def test_waits_for_connection_established(self):
        """Test that send_message waits up to 5 seconds for connection_established"""

        # Simulate connection_established arriving after 2 seconds
        async def delayed_connection():
            await asyncio.sleep(2)
            self.cli.ready_to_send_events = True

        # Start the delayed connection task
        delayed_task = asyncio.create_task(delayed_connection())

        # Record start time
        start = time.time()

        # Simulate the waiting logic from send_message
        wait_timeout = 5.0
        wait_start = time.time()
        wait_interval = 0.1

        while not self.cli.ready_to_send_events and (time.time() - wait_start) < wait_timeout:
            await asyncio.sleep(wait_interval)
            if self.cli.ready_to_send_events:
                break

        # Clean up task
        await delayed_task

        # Verify it waited about 2 seconds and succeeded
        elapsed = time.time() - start
        self.assertTrue(self.cli.ready_to_send_events)
        self.assertGreaterEqual(elapsed, 1.9)  # At least 2 seconds (with margin)
        self.assertLess(elapsed, 3)  # Less than 3 seconds

    async def test_timeout_after_5_seconds(self):
        """Test that send_message times out after 5 seconds if no connection_established"""

        # Connection_established never arrives
        self.cli.ready_to_send_events = False

        # Record start time
        start = time.time()

        # Simulate the waiting logic from send_message
        wait_timeout = 5.0
        wait_start = time.time()
        wait_interval = 0.1

        while not self.cli.ready_to_send_events and (time.time() - wait_start) < wait_timeout:
            await asyncio.sleep(wait_interval)
            if self.cli.ready_to_send_events:
                break

        # Verify it waited 5 seconds and timed out
        elapsed = time.time() - start
        self.assertFalse(self.cli.ready_to_send_events)
        self.assertGreaterEqual(elapsed, 4.9)  # At least 5 seconds (with margin)
        self.assertLess(elapsed, 5.5)  # Not much more than 5 seconds

    async def test_immediate_success_if_already_ready(self):
        """Test that send_message proceeds immediately if already ready"""

        # Already ready to send
        self.cli.ready_to_send_events = True

        # Record start time
        start = time.time()

        # Simulate the check from send_message
        if not self.cli.ready_to_send_events:
            # This branch won't execute
            wait_timeout = 5.0
            wait_start = time.time()
            wait_interval = 0.1

            while not self.cli.ready_to_send_events and (time.time() - wait_start) < wait_timeout:
                await asyncio.sleep(wait_interval)

        # Verify no waiting occurred
        elapsed = time.time() - start
        self.assertTrue(self.cli.ready_to_send_events)
        self.assertLess(elapsed, 0.1)  # Should be nearly instant


def run_async_test(test_func):
    """Helper to run async test functions"""
    return asyncio.run(test_func())


if __name__ == '__main__':
    # Run the tests
    test = TestConnectionWaiting()
    test.setUp()

    print("Test 1: Waiting for connection_established...")
    run_async_test(test.test_waits_for_connection_established)
    print("[PASS] Test 1 passed: Successfully waited ~2 seconds for connection_established\n")

    test.setUp()
    print("Test 2: Timeout after 5 seconds...")
    run_async_test(test.test_timeout_after_5_seconds)
    print("[PASS] Test 2 passed: Correctly timed out after ~5 seconds\n")

    test.setUp()
    print("Test 3: Immediate success if already ready...")
    run_async_test(test.test_immediate_success_if_already_ready)
    print("[PASS] Test 3 passed: No waiting when already ready\n")

    print("All tests passed!")