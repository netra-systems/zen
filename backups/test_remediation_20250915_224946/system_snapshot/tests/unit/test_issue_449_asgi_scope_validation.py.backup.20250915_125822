"""
Issue #449 - ASGI Scope Validation Tests for GCP Cloud Run Environment

PURPOSE: Test enhanced ASGI scope validation and repair functionality that prevents
         uvicorn websockets_impl.py:244 failures in GCP Cloud Run environments.

BUSINESS IMPACT: $500K+ ARR WebSocket functionality protection through comprehensive
                ASGI scope validation and automatic repair mechanisms.

TEST FOCUS:
- UvicornProtocolValidator ASGI scope validation
- Scope corruption detection and repair
- GCP Cloud Run environment compatibility
- Protocol transition failure prevention
- Enhanced error recovery patterns

TEST STRATEGY:
These tests validate the enhanced uvicorn protocol handling components work correctly
to prevent the websockets_impl.py:244 failures identified in Issue #449.
"""
import pytest
import json
import time
from typing import Dict, Any, List, Tuple
from unittest.mock import Mock, AsyncMock, patch
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.middleware.uvicorn_protocol_enhancement import UvicornProtocolValidator, UvicornWebSocketExclusionMiddleware

@pytest.mark.unit
class TestIssue449ASGIScopeValidation(SSotBaseTestCase):
    """
    Unit tests for Issue #449 ASGI scope validation and repair.

    EXPECTED BEHAVIOR: These tests should PASS, demonstrating the enhanced
    uvicorn protocol handling correctly validates and repairs ASGI scopes.
    """

    def setup_method(self, method=None):
        super().setup_method(method)
        self.validator = UvicornProtocolValidator()

    def test_valid_websocket_scope_validation_passes(self):
        """
        Test that valid WebSocket ASGI scopes pass validation.

        EXPECTED: This test should PASS, demonstrating proper validation
        of correct WebSocket ASGI scopes for uvicorn compatibility.
        """
        valid_websocket_scope = {'type': 'websocket', 'path': '/ws', 'query_string': b'', 'headers': [(b'host', b'netra-backend-staging.a.run.app'), (b'upgrade', b'websocket'), (b'connection', b'upgrade'), (b'sec-websocket-version', b'13'), (b'sec-websocket-key', b'dGhlIHNhbXBsZSBub25jZQ==')], 'asgi': {'version': '3.0'}}
        is_valid, error_message = self.validator.validate_websocket_scope(valid_websocket_scope)
        self.assertTrue(is_valid, f'Valid WebSocket scope should pass validation: {error_message}')
        self.assertIsNone(error_message, 'Valid scope should not have error message')
        self.assertEqual(len(self.validator.validation_failures), 0, 'Valid scope should not record validation failures')

    def test_invalid_websocket_scope_missing_headers_fails_validation(self):
        """
        Test that WebSocket scopes missing required headers fail validation.

        EXPECTED: This test should PASS, demonstrating proper detection
        of invalid WebSocket scopes that would cause uvicorn failures.
        """
        invalid_scope = {'type': 'websocket', 'path': '/ws', 'query_string': b''}
        is_valid, error_message = self.validator.validate_websocket_scope(invalid_scope)
        self.assertFalse(is_valid, 'WebSocket scope missing headers should fail validation')
        self.assertIsNotNone(error_message, 'Invalid scope should have error message')
        self.assertIn('missing required fields', error_message.lower(), 'Error should mention missing fields')
        self.assertIn('headers', error_message, 'Error should specifically mention headers')
        self.assertEqual(len(self.validator.validation_failures), 1, 'Invalid scope should record validation failure')
        failure = self.validator.validation_failures[0]
        self.assertEqual(failure['error'], 'missing_websocket_fields')
        self.assertIn('headers', failure['missing_fields'])

    def test_protocol_transition_corruption_detection(self):
        """
        Test detection of protocol transition corruption in ASGI scopes.

        EXPECTED: This test should PASS, demonstrating proper detection of
        uvicorn protocol transition corruption patterns.
        """
        corrupted_websocket_scope = {'type': 'websocket', 'path': '/ws', 'method': 'GET', 'query_string': b'', 'headers': []}
        corruption = self.validator.detect_protocol_transition_corruption(corrupted_websocket_scope)
        self.assertIsNotNone(corruption, 'Protocol transition corruption should be detected')
        self.assertEqual(corruption['pattern'], 'websocket_with_http_method', 'Should detect WebSocket scope with HTTP method pattern')
        self.assertEqual(corruption['uvicorn_failure'], 'protocol_transition_incomplete', 'Should identify as uvicorn protocol transition failure')
        self.assertIn('method', corruption['corrupted_fields'], 'Should identify method as corrupted field')
        self.assertEqual(len(self.validator.scope_corruptions), 1, 'Corruption should be recorded')

    def test_scope_repair_removes_invalid_http_fields(self):
        """
        Test that scope repair correctly removes invalid HTTP fields from WebSocket scopes.

        EXPECTED: This test should PASS, demonstrating proper repair of corrupted
        WebSocket scopes to prevent uvicorn websockets_impl.py:244 failures.
        """
        corrupted_scope = {'type': 'websocket', 'path': '/ws', 'method': 'GET', 'query_params': {'test': 'value'}, 'query_string': b'test=value', 'headers': []}
        repaired_scope, repair_actions = self.validator.repair_corrupted_scope(corrupted_scope)
        self.assertNotIn('method', repaired_scope, 'HTTP method should be removed from WebSocket scope')
        self.assertNotIn('query_params', repaired_scope, 'HTTP query_params should be removed')
        self.assertIn('removed_http_method_from_websocket', repair_actions, 'Should record HTTP method removal')
        self.assertIn('removed_query_params_from_websocket', repair_actions, 'Should record query_params removal')
        self.assertEqual(repaired_scope['type'], 'websocket', 'WebSocket type should remain')
        self.assertEqual(repaired_scope['path'], '/ws', 'Path should remain')
        self.assertEqual(repaired_scope['query_string'], b'test=value', 'query_string should remain')
        self.assertEqual(repaired_scope['headers'], [], 'Headers should remain')

    def test_scope_repair_adds_missing_required_fields(self):
        """
        Test that scope repair adds missing required fields for WebSocket scopes.

        EXPECTED: This test should PASS, demonstrating automatic addition of
        required fields to prevent uvicorn validation failures.
        """
        incomplete_scope = {'type': 'websocket', 'path': '/ws'}
        repaired_scope, repair_actions = self.validator.repair_corrupted_scope(incomplete_scope)
        self.assertIn('query_string', repaired_scope, 'query_string should be added')
        self.assertEqual(repaired_scope['query_string'], b'', 'query_string should default to empty bytes')
        self.assertIn('headers', repaired_scope, 'headers should be added')
        self.assertEqual(repaired_scope['headers'], [], 'headers should default to empty list')
        self.assertIn('asgi', repaired_scope, 'asgi info should be added')
        self.assertEqual(repaired_scope['asgi']['version'], '3.0', 'asgi version should default to 3.0')
        expected_actions = ['added_missing_query_string', 'added_missing_headers', 'added_asgi_version_info']
        for action in expected_actions:
            self.assertIn(action, repair_actions, f'Should record repair action: {action}')

    def test_asgi_version_compatibility_validation(self):
        """
        Test ASGI version compatibility validation for different versions.

        EXPECTED: This test should PASS, demonstrating proper handling of
        different ASGI versions that might cause uvicorn compatibility issues.
        """
        test_versions = [('2.0', True), ('3.0', True), ('3.1', True), ('1.0', False), ('4.0', False), ('invalid', False)]
        for version, should_be_standard in test_versions:
            with self.subTest(version=version):
                websocket_scope = {'type': 'websocket', 'path': '/ws', 'query_string': b'', 'headers': [], 'asgi': {'version': version}}
                is_valid, error_message = self.validator.validate_websocket_scope(websocket_scope)
                self.assertTrue(is_valid, f'ASGI version {version} should pass validation: {error_message}')
                self.assertIsNone(error_message, f'ASGI version {version} should not have error')

    def test_headers_format_validation(self):
        """
        Test that headers format validation correctly handles different header formats.

        EXPECTED: This test should PASS, demonstrating proper validation of
        header formats required for uvicorn WebSocket handling.
        """
        valid_headers_scope = {'type': 'websocket', 'path': '/ws', 'query_string': b'', 'headers': [(b'host', b'localhost'), (b'upgrade', b'websocket')]}
        is_valid, error_message = self.validator.validate_websocket_scope(valid_headers_scope)
        self.assertTrue(is_valid, f'Valid headers format should pass: {error_message}')
        invalid_headers_scope = {'type': 'websocket', 'path': '/ws', 'query_string': b'', 'headers': [('host', 'localhost'), (b'upgrade', b'websocket')]}
        is_valid, error_message = self.validator.validate_websocket_scope(invalid_headers_scope)
        self.assertFalse(is_valid, 'Invalid headers format should fail validation')
        self.assertIn('bytes', error_message, 'Error should mention bytes requirement')

    def test_non_websocket_scope_passthrough(self):
        """
        Test that non-WebSocket scopes are passed through without validation.

        EXPECTED: This test should PASS, demonstrating that HTTP and other
        scope types are not affected by WebSocket validation.
        """
        http_scope = {'type': 'http', 'method': 'GET', 'path': '/api/test', 'query_string': b'', 'headers': []}
        is_valid, error_message = self.validator.validate_websocket_scope(http_scope)
        self.assertTrue(is_valid, 'HTTP scope should pass through validation')
        self.assertIsNone(error_message, 'HTTP scope should not have error')
        lifespan_scope = {'type': 'lifespan'}
        is_valid, error_message = self.validator.validate_websocket_scope(lifespan_scope)
        self.assertTrue(is_valid, 'Lifespan scope should pass through validation')
        self.assertIsNone(error_message, 'Lifespan scope should not have error')

    def test_scope_validation_exception_handling(self):
        """
        Test that scope validation handles exceptions gracefully.

        EXPECTED: This test should PASS, demonstrating proper exception handling
        during scope validation to prevent uvicorn middleware crashes.
        """
        malformed_scope = {'type': 'websocket', 'headers': 'not_a_list'}
        is_valid, error_message = self.validator.validate_websocket_scope(malformed_scope)
        self.assertFalse(is_valid, 'Malformed scope should fail validation')
        self.assertIsNotNone(error_message, 'Should have error message')
        self.assertIn('exception', error_message.lower(), 'Error should indicate exception occurred')
        self.assertEqual(len(self.validator.validation_failures), 1, 'Exception should be recorded')
        failure = self.validator.validation_failures[0]
        self.assertEqual(failure['error'], 'validation_exception')

    def test_gcp_cloud_run_specific_scope_patterns(self):
        """
        Test validation of ASGI scope patterns specific to GCP Cloud Run.

        EXPECTED: This test should PASS, demonstrating proper handling of
        GCP Cloud Run WebSocket scope characteristics.
        """
        gcp_websocket_scope = {'type': 'websocket', 'path': '/ws', 'raw_path': b'/ws', 'query_string': b'', 'root_path': '', 'scheme': 'wss', 'server': ('10.0.0.1', 8080), 'client': ('172.16.0.1', 45678), 'headers': [(b'host', b'netra-backend-staging-00498-ssn.a.run.app'), (b'x-forwarded-for', b'203.0.113.195'), (b'x-forwarded-proto', b'https'), (b'x-cloud-trace-context', b'105445aa7843bc8bf206b120001000/1'), (b'upgrade', b'websocket'), (b'connection', b'upgrade'), (b'sec-websocket-version', b'13'), (b'sec-websocket-key', b'x3JJHMbDL1EzLkh9GBhXDw==')], 'asgi': {'version': '3.0'}, 'extensions': {'websocket.http.response': {}}}
        is_valid, error_message = self.validator.validate_websocket_scope(gcp_websocket_scope)
        self.assertTrue(is_valid, f'GCP Cloud Run WebSocket scope should be valid: {error_message}')
        self.assertIsNone(error_message, 'GCP scope should not have validation errors')
        corruption = self.validator.detect_protocol_transition_corruption(gcp_websocket_scope)
        self.assertIsNone(corruption, 'GCP Cloud Run scope should not be detected as corrupted')

@pytest.mark.unit
class TestIssue449UvicornMiddlewareIntegration(SSotBaseTestCase):
    """
    Integration tests for uvicorn middleware with enhanced protocol validation.

    EXPECTED BEHAVIOR: These tests should PASS, demonstrating the enhanced
    middleware correctly integrates with uvicorn protocol validation.
    """

    def setup_method(self, method=None):
        super().setup_method(method)
        self.mock_app = AsyncMock()
        self.middleware = UvicornWebSocketExclusionMiddleware(self.mock_app)

    @pytest.mark.asyncio
    async def test_websocket_scope_protection_with_validation(self):
        """
        Test WebSocket scope protection with enhanced validation.

        EXPECTED: This test should PASS, demonstrating proper WebSocket scope
        protection using the enhanced uvicorn protocol validation.
        """
        websocket_scope = {'type': 'websocket', 'path': '/ws', 'query_string': b'', 'headers': [(b'upgrade', b'websocket'), (b'connection', b'upgrade')], 'asgi': {'version': '3.0'}}
        mock_receive = AsyncMock()
        mock_send = AsyncMock()
        await self.middleware._handle_websocket_scope_protection(websocket_scope, mock_receive, mock_send)
        self.mock_app.assert_called_once_with(websocket_scope, mock_receive, mock_send)
        mock_send.assert_not_called()
        self.assertEqual(len(self.middleware.protocol_validator.validation_failures), 0, 'Valid WebSocket scope should not record validation failures')

    @pytest.mark.asyncio
    async def test_corrupted_websocket_scope_repair_and_recovery(self):
        """
        Test automatic repair of corrupted WebSocket scopes.

        EXPECTED: This test should PASS, demonstrating automatic repair of
        corrupted scopes to prevent uvicorn websockets_impl.py:244 failures.
        """
        corrupted_scope = {'type': 'websocket', 'path': '/ws', 'method': 'GET', 'query_string': b'', 'headers': []}
        mock_receive = AsyncMock()
        mock_send = AsyncMock()
        await self.middleware._handle_websocket_scope_protection(corrupted_scope, mock_receive, mock_send)
        self.mock_app.assert_called_once()
        called_scope = self.mock_app.call_args[0][0]
        self.assertNotIn('method', called_scope, 'HTTP method should be removed from repaired scope')
        self.assertEqual(called_scope['type'], 'websocket', 'Scope type should remain websocket')
        self.assertEqual(len(self.middleware.protocol_recoveries), 1, 'Protocol recovery should be recorded')
        recovery = self.middleware.protocol_recoveries[0]
        self.assertIn('removed_http_method_from_websocket', recovery['repair_actions'], 'Should record HTTP method removal action')

    @pytest.mark.asyncio
    async def test_websocket_upgrade_in_http_scope_conversion(self):
        """
        Test conversion of WebSocket upgrade detected in HTTP scope.

        EXPECTED: This test should PASS, demonstrating proper handling of
        uvicorn protocol confusion where WebSocket upgrades appear in HTTP scopes.
        """
        http_scope_with_upgrade = {'type': 'http', 'method': 'GET', 'path': '/ws', 'query_string': b'', 'headers': [(b'upgrade', b'websocket'), (b'connection', b'upgrade'), (b'sec-websocket-version', b'13'), (b'sec-websocket-key', b'dGhlIHNhbXBsZSBub25jZQ==')]}
        mock_receive = AsyncMock()
        mock_send = AsyncMock()
        await self.middleware._handle_websocket_upgrade_in_http_scope(http_scope_with_upgrade, mock_receive, mock_send)
        self.mock_app.assert_called_once()
        called_scope = self.mock_app.call_args[0][0]
        self.assertEqual(called_scope['type'], 'websocket', 'Scope should be converted to websocket')
        self.assertNotIn('method', called_scope, 'HTTP method should be removed')
        self.assertEqual(called_scope['path'], '/ws', 'Path should be preserved')
        self.assertIn('query_string', called_scope, 'query_string should be ensured')

    def test_diagnostic_info_collection(self):
        """
        Test collection of diagnostic information for troubleshooting.

        EXPECTED: This test should PASS, demonstrating proper diagnostic
        information collection for Issue #449 troubleshooting.
        """
        self.middleware.protocol_validator.validation_failures.append({'error': 'test_failure', 'details': 'Test validation failure'})
        self.middleware.middleware_conflicts.append({'type': 'test_conflict', 'timestamp': time.time()})
        diagnostic_info = self.middleware.get_diagnostic_info()
        self.assertEqual(diagnostic_info['middleware'], 'uvicorn_websocket_exclusion')
        self.assertEqual(diagnostic_info['issue_reference'], '#449')
        self.assertEqual(diagnostic_info['validation_failures'], 1)
        self.assertEqual(diagnostic_info['middleware_conflicts'], 1)
        self.assertEqual(len(diagnostic_info['recent_failures']), 1)
        self.assertEqual(len(diagnostic_info['recent_conflicts']), 1)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')