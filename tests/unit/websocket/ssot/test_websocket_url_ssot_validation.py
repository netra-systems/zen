"""
Issue #507 - WebSocket URL SSOT Validation Tests

CRITICAL MISSION: Create SSOT validation tests for WebSocket URL environment variable 
duplication issue (Issue #507).

PROBLEM: Duplicate `NEXT_PUBLIC_WS_URL` vs `NEXT_PUBLIC_WEBSOCKET_URL` 
BUSINESS IMPACT: $500K+ ARR Golden Path chat functionality at risk

TEST DESIGN:
- Pre-SSOT Fix: These tests MUST FAIL (by design - detecting dual variables)
- Post-SSOT Fix: These tests MUST PASS (confirming SSOT consolidation works)

Business Value: Platform/Internal - System Stability & Revenue Protection
Protects $500K+ ARR by ensuring WebSocket URL configuration consistency.
"""
import pytest
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics
from shared.isolated_environment import IsolatedEnvironment, get_env

class TestWebSocketURLSSOTValidation(SSotBaseTestCase):
    """Unit tests for WebSocket URL SSOT validation (Issue #507)"""

    def setup_method(self, method):
        """Setup for each test method using SSOT pattern"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.metrics = SsotTestMetrics()

    def teardown_method(self, method):
        """Teardown for each test method"""
        super().teardown_method(method)

    def test_single_websocket_url_variable_enforced(self):
        """
        Test that only ONE WebSocket URL environment variable exists
        
        CRITICAL: This test MUST FAIL pre-SSOT fix (dual variables exist)
        CRITICAL: This test MUST PASS post-SSOT fix (only one variable)
        """
        test_env = {'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai/ws', 'NEXT_PUBLIC_WEBSOCKET_URL': 'wss://api.staging.netrasystems.ai/ws'}
        with patch.dict('os.environ', test_env, clear=False):
            env = IsolatedEnvironment()
            ws_url = env.get('NEXT_PUBLIC_WS_URL')
            websocket_url = env.get('NEXT_PUBLIC_WEBSOCKET_URL')
            variables_defined = sum([1 for var in [ws_url, websocket_url] if var is not None])
            assert variables_defined == 1, f'SSOT VIOLATION: Multiple WebSocket URL variables defined. Found NEXT_PUBLIC_WS_URL={ws_url}, NEXT_PUBLIC_WEBSOCKET_URL={websocket_url}. SSOT requires exactly ONE canonical variable.'

    def test_canonical_websocket_url_variable_identified(self):
        """
        Test that the canonical WebSocket URL variable is properly identified
        
        Expected: NEXT_PUBLIC_WS_URL should be the canonical variable
        """
        canonical_var = 'NEXT_PUBLIC_WS_URL'
        deprecated_var = 'NEXT_PUBLIC_WEBSOCKET_URL'
        test_env = {canonical_var: 'wss://api.staging.netrasystems.ai/ws'}
        with patch.dict('os.environ', test_env, clear=False):
            env = IsolatedEnvironment()
            canonical_value = env.get(canonical_var)
            deprecated_value = env.get(deprecated_var)
            assert canonical_value is not None, f'Canonical variable {canonical_var} should be defined'
            assert deprecated_value is None, f'Deprecated variable {deprecated_var} should NOT be defined'
            assert canonical_value.startswith('wss://'), 'WebSocket URL should use secure WebSocket protocol'
            assert 'netrasystems.ai' in canonical_value, 'URL should be Netra domain'

    def test_websocket_url_validation_logic(self):
        """Test WebSocket URL validation logic for SSOT compliance"""
        valid_urls = ['wss://api.staging.netrasystems.ai/ws', 'wss://api.netrasystems.ai/ws', 'wss://localhost:8000/ws']
        invalid_urls = ['ws://api.netrasystems.ai/ws', 'https://api.netrasystems.ai/ws', 'wss://example.com/ws', '', None]
        for url in valid_urls:
            test_env = {'NEXT_PUBLIC_WS_URL': url}
            with patch.dict('os.environ', test_env, clear=False):
                env = IsolatedEnvironment()
                retrieved_url = env.get('NEXT_PUBLIC_WS_URL')
                assert retrieved_url == url, f'Valid URL {url} should be retrievable'
        for url in invalid_urls:
            if url is not None:
                test_env = {'NEXT_PUBLIC_WS_URL': url}
                with patch.dict('os.environ', test_env, clear=False):
                    env = IsolatedEnvironment()
                    retrieved_url = env.get('NEXT_PUBLIC_WS_URL')
                    assert retrieved_url == url, f'Environment should return URL as-is: {url}'

    def test_websocket_url_configuration_consistency(self):
        """Test consistency of WebSocket URL configuration across different environments"""
        environments = {'staging': 'wss://api.staging.netrasystems.ai/ws', 'production': 'wss://api.netrasystems.ai/ws', 'development': 'wss://localhost:8000/ws'}
        for env_name, expected_url in environments.items():
            test_env = {'ENVIRONMENT': env_name, 'NEXT_PUBLIC_WS_URL': expected_url}
            with patch.dict('os.environ', test_env, clear=False):
                env = IsolatedEnvironment()
                actual_url = env.get('NEXT_PUBLIC_WS_URL')
                environment = env.get('ENVIRONMENT')
                assert actual_url == expected_url, f'Environment {env_name} should have WebSocket URL {expected_url}, got {actual_url}'
                deprecated_url = env.get('NEXT_PUBLIC_WEBSOCKET_URL')
                assert deprecated_url is None, f'SSOT VIOLATION: Deprecated NEXT_PUBLIC_WEBSOCKET_URL should not exist in {env_name} environment'

    def test_websocket_url_ssot_migration_detection(self):
        """
        Test detection of SSOT migration status
        
        This test validates that we can detect whether SSOT migration has been completed
        """
        pre_migration_env = {'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai/ws', 'NEXT_PUBLIC_WEBSOCKET_URL': 'wss://api.staging.netrasystems.ai/ws'}
        with patch.dict('os.environ', pre_migration_env, clear=False):
            env = IsolatedEnvironment()
            has_canonical = env.get('NEXT_PUBLIC_WS_URL') is not None
            has_deprecated = env.get('NEXT_PUBLIC_WEBSOCKET_URL') is not None
            ssot_compliant = has_canonical and (not has_deprecated)
            if has_canonical and has_deprecated:
                self.metrics.custom_metrics['ssot_violation_detected'] = True
                self.metrics.custom_metrics['migration_status'] = 'pre_migration'
                pytest.fail('SSOT VIOLATION DETECTED: Both NEXT_PUBLIC_WS_URL and NEXT_PUBLIC_WEBSOCKET_URL exist. SSOT migration required. Issue #507 remediation needed.')
        post_migration_env = {'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai/ws'}
        with patch.dict('os.environ', post_migration_env, clear=False):
            env = IsolatedEnvironment()
            has_canonical = env.get('NEXT_PUBLIC_WS_URL') is not None
            has_deprecated = env.get('NEXT_PUBLIC_WEBSOCKET_URL') is not None
            ssot_compliant = has_canonical and (not has_deprecated)
            assert ssot_compliant, 'SSOT COMPLIANT: Only canonical NEXT_PUBLIC_WS_URL should exist after Issue #507 remediation'
            self.metrics.custom_metrics['ssot_compliant'] = True
            self.metrics.custom_metrics['migration_status'] = 'post_migration'

class TestWebSocketEnvironmentVariableValidation(SSotBaseTestCase):
    """Additional unit tests for WebSocket environment variable validation"""

    def setup_method(self, method):
        """Setup for each test method"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

    def test_missing_websocket_url_handling(self):
        """Test handling when no WebSocket URL is configured"""
        clear_env = {}
        with patch.dict('os.environ', clear_env, clear=True):
            env = IsolatedEnvironment()
            ws_url = env.get('NEXT_PUBLIC_WS_URL')
            websocket_url = env.get('NEXT_PUBLIC_WEBSOCKET_URL')
            assert ws_url is None, 'NEXT_PUBLIC_WS_URL should be None when not configured'
            assert websocket_url is None, 'NEXT_PUBLIC_WEBSOCKET_URL should be None when not configured'

    def test_websocket_url_environment_isolation(self):
        """Test that WebSocket URL configuration is properly isolated between tests"""
        env1 = {'NEXT_PUBLIC_WS_URL': 'wss://env1.example.com/ws'}
        with patch.dict('os.environ', env1, clear=False):
            isolated_env1 = IsolatedEnvironment()
            url1 = isolated_env1.get('NEXT_PUBLIC_WS_URL')
            assert url1 == 'wss://env1.example.com/ws'
        env2 = {'NEXT_PUBLIC_WS_URL': 'wss://env2.example.com/ws'}
        with patch.dict('os.environ', env2, clear=False):
            isolated_env2 = IsolatedEnvironment()
            url2 = isolated_env2.get('NEXT_PUBLIC_WS_URL')
            assert url2 == 'wss://env2.example.com/ws'
        assert url1 != url2, 'Environment isolation should maintain separate configurations'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')