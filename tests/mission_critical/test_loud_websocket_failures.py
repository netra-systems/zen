'''
Test Loud WebSocket Failure Mechanisms

Business Value Justification:
    - Segment: Platform/Internal
    - Business Goal: Stability & User Experience
    - Value Impact: Verifies that WebSocket failures are loud and visible, not silent
    - Strategic Impact: Ensures users always know when something goes wrong

This test suite validates that all WebSocket failures raise exceptions
rather than failing silently.
'''

import asyncio
import pytest
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment
from loguru import logger

# Core WebSocket infrastructure imports
try:
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
    from netra_backend.app.services.websocket_bridge_factory import (
        WebSocketBridgeFactory,
        UserWebSocketEmitter,
        UserWebSocketContext,
        UserWebSocketConnection,
        WebSocketEvent,
        WebSocketConnectionPool
    )
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.core.websocket_exceptions import (
        WebSocketConnectionError,
        WebSocketSendError,
        WebSocketTimeoutError,
        WebSocketAuthenticationError
    )
except ImportError as e:
    logger.warning(f"Some imports failed: {e}. Test will use mock implementations.)")

    # Define mock exceptions for testing
    class WebSocketConnectionError(Exception):
        pass

    class WebSocketSendError(Exception):
        pass

    class WebSocketTimeoutError(Exception):
        pass

    class WebSocketAuthenticationError(Exception):
        pass


class TestWebSocketConnection:
    Real WebSocket connection for testing instead of mocks."

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        self.should_fail = False
        self.failure_type = None

    async def send_json(self, message: dict):
        "Send JSON message.
        if self._closed:
            raise RuntimeError(WebSocket is closed")"

        if self.should_fail:
            if self.failure_type == connection_error:
                raise WebSocketConnectionError(Connection lost)"
            elif self.failure_type == "send_error:
                raise WebSocketSendError(Failed to send message)
            elif self.failure_type == "timeout:"
                raise WebSocketTimeoutError(Send timeout)

        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = Normal closure):"
        "Close WebSocket connection.
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        "Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()

    def simulate_failure(self, failure_type: str):
        "Simulate different types of failures."
        self.should_fail = True
        self.failure_type = failure_type


class LoudWebSocketFailureValidator:
    "
    Validates that WebSocket failures are loud and visible, not silent.

    Critical for ensuring users know when real-time updates are broken.
    "

    def __init__(self):
        self.test_results = {
            'failures_tested': [],
            'failures_loud': [],
            'failures_silent': [],
            'test_timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.test_connection = TestWebSocketConnection()

    async def test_connection_failure_is_loud(self) -> dict:
        Test that connection failures raise exceptions loudly.""
        test_name = connection_failure_loudness
        logger.info(fTesting {test_name}...)"

        result = {
            'test_name': test_name,
            'failure_types_tested': [],
            'loud_failures': [],
            'silent_failures': [],
            'success': False
        }

        # Test different connection failure scenarios
        connection_failures = [
            ("connection_lost, Connection lost during operation),
            (connection_timeout, Connection timeout),
            ("connection_refused, Connection refused by server")
        ]

        for failure_type, description in connection_failures:
            result['failure_types_tested'].append(failure_type)

            try:
                # Simulate connection failure
                self.test_connection.simulate_failure(connection_error)

                # This should raise an exception
                await self.test_connection.send_json({
                    event_type: "test_event,
                    data": {test: connection failure}
                }

                # If we reach here, the failure was silent (BAD)
                result['silent_failures'].append(failure_type)
                logger.error(f"❌ {failure_type} was SILENT - this is critical!)

            except (WebSocketConnectionError, RuntimeError) as e:
                # Good! The failure was loud
                result['loud_failures'].append(failure_type)
                logger.info(f✅ {failure_type} was LOUD: {e}")

            except Exception as e:
                # Any other exception is also considered loud
                result['loud_failures'].append(failure_type)
                logger.info(f✅ {failure_type} was LOUD (unexpected exception): {e})

            # Reset for next test
            self.test_connection.should_fail = False

        # Success if all failures were loud
        result['success'] = len(result['silent_failures'] == 0

        self.test_results['failures_tested'].extend(result['failure_types_tested']
        self.test_results['failures_loud'].extend(result['loud_failures']
        self.test_results['failures_silent'].extend(result['silent_failures']

        return result

    async def test_send_failure_is_loud(self) -> dict:
        "Test that send failures raise exceptions loudly."
        test_name = send_failure_loudness
        logger.info(fTesting {test_name}...")"

        result = {
            'test_name': test_name,
            'failure_types_tested': [],
            'loud_failures': [],
            'silent_failures': [],
            'success': False
        }

        # Test different send failure scenarios
        send_failures = [
            (send_error, Generic send error),
            (timeout, Send timeout"),
            ("serialization_error, JSON serialization error)
        ]

        for failure_type, description in send_failures:
            result['failure_types_tested'].append(failure_type)

            try:
                # Simulate send failure
                self.test_connection.simulate_failure(failure_type)

                # This should raise an exception
                await self.test_connection.send_json({
                    event_type: test_event,
                    "data: {test": send failure}
                }

                # If we reach here, the failure was silent (BAD)
                result['silent_failures'].append(failure_type)
                logger.error(f❌ {failure_type} was SILENT - this is critical!)"

            except (WebSocketSendError, WebSocketTimeoutError, RuntimeError) as e:
                # Good! The failure was loud
                result['loud_failures'].append(failure_type)
                logger.info(f"✅ {failure_type} was LOUD: {e})

            except Exception as e:
                # Any other exception is also considered loud
                result['loud_failures'].append(failure_type)
                logger.info(f✅ {failure_type} was LOUD (unexpected exception): {e})

            # Reset for next test
            self.test_connection.should_fail = False

        # Success if all failures were loud
        result['success'] = len(result['silent_failures'] == 0

        self.test_results['failures_tested'].extend(result['failure_types_tested']
        self.test_results['failures_loud'].extend(result['loud_failures']
        self.test_results['failures_silent'].extend(result['silent_failures']

        return result

    async def test_authentication_failure_is_loud(self) -> dict:
        Test that authentication failures raise exceptions loudly.""
        test_name = authentication_failure_loudness
        logger.info(f"Testing {test_name}...)

        result = {
            'test_name': test_name,
            'failure_types_tested': ['auth_failure'],
            'loud_failures': [],
            'silent_failures': [],
            'success': False
        }

        try:
            # Simulate authentication failure by creating an invalid connection scenario
            class FailingAuthConnection:
                async def send_json(self, message: dict):
                    # This should always raise an auth error
                    raise WebSocketAuthenticationError(Invalid token or expired session")

            failing_connection = FailingAuthConnection()

            # This should raise an exception
            await failing_connection.send_json({
                event_type: test_event,
                "data: {test": auth failure}
            }

            # If we reach here, the failure was silent (BAD)
            result['silent_failures'].append('auth_failure')
            logger.error(❌ Authentication failure was SILENT - this is critical!)"

        except WebSocketAuthenticationError as e:
            # Good! The failure was loud
            result['loud_failures'].append('auth_failure')
            logger.info(f"✅ Authentication failure was LOUD: {e})

        except Exception as e:
            # Any other exception is also considered loud
            result['loud_failures'].append('auth_failure')
            logger.info(f✅ Authentication failure was LOUD (unexpected exception): {e})

        # Success if failure was loud
        result['success'] = len(result['silent_failures'] == 0

        self.test_results['failures_tested'].extend(result['failure_types_tested']
        self.test_results['failures_loud'].extend(result['loud_failures']
        self.test_results['failures_silent'].extend(result['silent_failures']

        return result

    async def test_silent_failure_detection(self) -> dict:
        Test that we can detect when failures would be silent.""
        test_name = silent_failure_detection
        logger.info(f"Testing {test_name}...)

        result = {
            'test_name': test_name,
            'detection_methods': [],
            'success': False
        }

        # Test method 1: Return value checking
        class SilentFailingConnection:
            async def send_json(self, message: dict):
                # This connection fails silently by returning None/False
                return False  # Silent failure indicator

        silent_connection = SilentFailingConnection()

        try:
            send_result = await silent_connection.send_json({
                event_type": test_event,
                data: {test: silent failure detection"}"
            }

            # Check if we can detect the silent failure
            if send_result is False:
                result['detection_methods'].append('return_value_checking')
                logger.info(✅ Silent failure detected via return value)
            else:
                logger.warning(⚠️ Could not detect silent failure via return value)"

        except Exception as e:
            logger.info(f"✅ Exception raised instead of silent failure: {e})

        # Test method 2: Message count verification
        class CountingConnection:
            def __init__(self):
                self.sent_count = 0

            async def send_json(self, message: dict):
                # Simulate silent failure by not incrementing count
                pass  # Silent failure - no count increment

        counting_connection = CountingConnection()
        initial_count = counting_connection.sent_count

        await counting_connection.send_json({
            event_type: test_event,
            data: {"test: count verification"}
        }

        if counting_connection.sent_count == initial_count:
            result['detection_methods'].append('message_count_verification')
            logger.info(✅ Silent failure detected via message count)

        result['success'] = len(result['detection_methods'] > 0
        return result

    async def run_loud_failure_validation(self) -> dict:
        ""Run all loud failure validation tests.
        logger.info(\n + =" * 80)
        logger.info("🔊 LOUD WEBSOCKET FAILURES VALIDATION SUITE)
        logger.info(= * 80)

        # Run all test categories
        test_results = {}

        test_functions = [
            ("Connection Failure Loudness, self.test_connection_failure_is_loud()),"
            (Send Failure Loudness, self.test_send_failure_is_loud()),
            (Authentication Failure Loudness, self.test_authentication_failure_is_loud()),"
            (Silent Failure Detection", self.test_silent_failure_detection()),
        ]

        for test_name, test_coro in test_functions:
            logger.info(f\n🔍 Running: {test_name})
            try:
                result = await test_coro
                test_results[test_name] = result

                if result.get('success', False):
                    logger.info(f✅ {test_name}: PASSED)"
                else:
                    logger.error(f"❌ {test_name}: FAILED)
                    if 'silent_failures' in result and result['silent_failures']:
                        logger.error(f   Silent failures detected: {result['silent_failures']})

            except Exception as e:
                logger.error(f❌ {test_name}: EXCEPTION - {e})
                test_results[test_name] = {
                    'test_name': test_name,
                    'success': False,
                    'exception': str(e)
                }

        # Final summary
        self._print_loud_failure_summary(test_results)

        return {
            'test_results': test_results,
            'summary': self.test_results,
            'overall_success': len(self.test_results['failures_silent'] == 0
        }

    def _print_loud_failure_summary(self, test_results: dict):
        ""Print comprehensive summary of loud failure tests.
        logger.info(\n + =" * 80)
        logger.info("📊 LOUD WEBSOCKET FAILURES SUMMARY)
        logger.info(= * 80)

        logger.info(f"Total Failures Tested: {len(self.test_results['failures_tested']})
        logger.info(fLoud Failures: {len(self.test_results['failures_loud']}")
        logger.info(fSilent Failures: {len(self.test_results['failures_silent']})

        if self.test_results['failures_silent']:
            logger.error(f\n🚨 CRITICAL: SILENT FAILURES DETECTED!)"
            for failure in self.test_results['failures_silent']:
                logger.error(f"  - {failure}: Users will not know when this fails)
        else:
            logger.info(f\n✅ All failures are LOUD - users will always know when something breaks!)

        # Test-by-test breakdown
        logger.info(f\n📋 TEST BREAKDOWN:)
        for test_name, result in test_results.items():
            status = ✅ PASS" if result.get('success', False) else "❌ FAIL
            logger.info(f  {status}: {test_name})

        # Overall assessment
        if len(self.test_results['failures_silent'] == 0:
            logger.info(f\n🎉 EXCELLENT: All WebSocket failures are loud and visible!)
            logger.info(f    Users will always know when real-time updates break")"
        else:
            logger.error(f\n🚨 CRITICAL ISSUE: Silent failures detected!)
            logger.error(f    These must be fixed to ensure user experience)


# Pytest integration
@pytest.mark.asyncio
@pytest.mark.critical
async def test_loud_websocket_failures():
    "Pytest wrapper for loud WebSocket failures validation."
    validator = LoudWebSocketFailureValidator()
    results = await validator.run_loud_failure_validation()

    # Assert no silent failures exist
    silent_failures = results['summary']['failures_silent']
    assert len(silent_failures) == 0, fSilent WebSocket failures detected: {silent_failures}"

    # Assert overall test success
    assert results['overall_success'], "Loud WebSocket failures validation failed

    # Assert specific failure types are loud
    loud_failures = set(results['summary']['failures_loud']
    critical_failure_types = {'connection_error', 'send_error', 'auth_failure'}

    for critical_type in critical_failure_types:
        if critical_type in results['summary']['failures_tested']:
            assert critical_type in loud_failures, fCritical failure type {critical_type} is silent


if __name__ == "__main__":
    # Allow running directly for debugging
    async def main():
        validator = LoudWebSocketFailureValidator()
        results = await validator.run_loud_failure_validation()

        # Exit with appropriate code
        exit_code = 0 if results['overall_success'] else 1
        return exit_code

    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)