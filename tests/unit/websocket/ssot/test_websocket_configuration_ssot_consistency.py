"""
Issue #507 - WebSocket Configuration SSOT Consistency Tests

CRITICAL MISSION: Create SSOT validation tests for WebSocket configuration consistency
to prevent environment variable duplication issues.

PROBLEM: WebSocket URL configuration inconsistencies across services and environments
BUSINESS IMPACT: $500K+ ARR Golden Path chat functionality at risk from config drift

TEST DESIGN:
- Validate configuration consistency across all services
- Test service startup with proper WebSocket URL configuration  
- Ensure no configuration drift between frontend/backend

Business Value: Platform/Internal - System Stability & Configuration Management
Prevents configuration drift that could impact revenue-generating chat functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics
from shared.isolated_environment import IsolatedEnvironment, get_env

@pytest.mark.unit
class TestWebSocketConfigurationSSOTConsistency(SSotBaseTestCase):
    """Unit tests for WebSocket configuration SSOT consistency (Issue #507)"""

    def setup_method(self, method):
        """Setup for each test method using SSOT pattern"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.metrics = SsotTestMetrics()

    def teardown_method(self, method):
        """Teardown for each test method"""
        super().teardown_method(method)

    def test_frontend_backend_websocket_url_consistency(self):
        """
        Test that frontend and backend use consistent WebSocket URL configuration
        
        CRITICAL: Prevents frontend/backend WebSocket URL mismatches
        """
        staging_config = {'ENVIRONMENT': 'staging', 'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai/ws', 'WEBSOCKET_URL': 'wss://api.staging.netrasystems.ai/ws'}
        with patch.dict('os.environ', staging_config, clear=False):
            env = IsolatedEnvironment()
            frontend_url = env.get('NEXT_PUBLIC_WS_URL')
            backend_url = env.get('WEBSOCKET_URL')
            if frontend_url and backend_url:
                assert frontend_url == backend_url, f'SSOT VIOLATION: Frontend WebSocket URL ({frontend_url}) != Backend WebSocket URL ({backend_url}). Configuration drift detected.'
            assert frontend_url is not None, 'Frontend WebSocket URL must be configured'
            if frontend_url:
                assert frontend_url.startswith('wss://'), 'WebSocket URL must use secure protocol'
                assert '/ws' in frontend_url, 'WebSocket URL must include /ws path'

    def test_environment_specific_websocket_configuration(self):
        """Test WebSocket configuration for different deployment environments"""
        environment_configs = {'development': {'ENVIRONMENT': 'development', 'NEXT_PUBLIC_WS_URL': 'wss://localhost:8000/ws', 'expected_domain': 'localhost'}, 'staging': {'ENVIRONMENT': 'staging', 'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai/ws', 'expected_domain': 'api.staging.netrasystems.ai'}, 'production': {'ENVIRONMENT': 'production', 'NEXT_PUBLIC_WS_URL': 'wss://api.netrasystems.ai/ws', 'expected_domain': 'api.netrasystems.ai'}}
        for env_name, config in environment_configs.items():
            test_env = {'ENVIRONMENT': config['ENVIRONMENT'], 'NEXT_PUBLIC_WS_URL': config['NEXT_PUBLIC_WS_URL']}
            with patch.dict('os.environ', test_env, clear=False):
                env = IsolatedEnvironment()
                ws_url = env.get('NEXT_PUBLIC_WS_URL')
                environment = env.get('ENVIRONMENT')
                assert ws_url == config['NEXT_PUBLIC_WS_URL'], f'Environment {env_name} WebSocket URL mismatch'
                assert config['expected_domain'] in ws_url, f"Environment {env_name} should use domain {config['expected_domain']}"
                deprecated_url = env.get('NEXT_PUBLIC_WEBSOCKET_URL')
                assert deprecated_url is None, f'SSOT VIOLATION: Deprecated NEXT_PUBLIC_WEBSOCKET_URL found in {env_name}'

    def test_websocket_url_protocol_enforcement(self):
        """Test enforcement of secure WebSocket protocol (wss://) in all environments"""
        protocol_tests = [{'url': 'wss://api.netrasystems.ai/ws', 'should_be_secure': True, 'description': 'Production secure WebSocket'}, {'url': 'ws://localhost:8000/ws', 'should_be_secure': False, 'description': 'Development insecure WebSocket (acceptable for localhost)'}, {'url': 'wss://api.staging.netrasystems.ai/ws', 'should_be_secure': True, 'description': 'Staging secure WebSocket'}]
        for test_case in protocol_tests:
            test_env = {'NEXT_PUBLIC_WS_URL': test_case['url']}
            with patch.dict('os.environ', test_env, clear=False):
                env = IsolatedEnvironment()
                ws_url = env.get('NEXT_PUBLIC_WS_URL')
                if test_case['should_be_secure']:
                    assert ws_url.startswith('wss://'), f"URL should use secure protocol: {test_case['description']}"
                else:
                    assert ws_url.startswith('ws://') or ws_url.startswith('wss://'), f"URL should use WebSocket protocol: {test_case['description']}"

    def test_websocket_url_path_consistency(self):
        """Test that WebSocket URLs use consistent path structure"""
        valid_paths = ['/ws', '/websocket', '/api/ws']
        base_urls = ['wss://api.netrasystems.ai', 'wss://api.staging.netrasystems.ai', 'wss://localhost:8000']
        for base_url in base_urls:
            for path in valid_paths:
                full_url = f'{base_url}{path}'
                test_env = {'NEXT_PUBLIC_WS_URL': full_url}
                with patch.dict('os.environ', test_env, clear=False):
                    env = IsolatedEnvironment()
                    ws_url = env.get('NEXT_PUBLIC_WS_URL')
                    assert ws_url == full_url, f'URL should match expected: {full_url}'
                    assert any((p in ws_url for p in valid_paths)), f'URL should contain valid WebSocket path: {ws_url}'

    def test_websocket_configuration_validation_logic(self):
        """Test WebSocket configuration validation logic for SSOT compliance"""

        def validate_websocket_config(ws_url):
            """Validation logic that should be used in application"""
            if not ws_url:
                return (False, 'WebSocket URL is required')
            if not (ws_url.startswith('ws://') or ws_url.startswith('wss://')):
                return (False, 'WebSocket URL must use ws:// or wss:// protocol')
            if not any((path in ws_url for path in ['/ws', '/websocket', '/api/ws'])):
                return (False, 'WebSocket URL must include valid path')
            if 'netrasystems.ai' in ws_url and (not ws_url.startswith('wss://')):
                return (False, 'Production/staging URLs must use secure WebSocket protocol')
            return (True, 'Valid WebSocket configuration')
        valid_configs = ['wss://api.netrasystems.ai/ws', 'wss://api.staging.netrasystems.ai/ws', 'ws://localhost:8000/ws', 'wss://localhost:8000/websocket']
        for config in valid_configs:
            test_env = {'NEXT_PUBLIC_WS_URL': config}
            with patch.dict('os.environ', test_env, clear=False):
                env = IsolatedEnvironment()
                ws_url = env.get('NEXT_PUBLIC_WS_URL')
                is_valid, message = validate_websocket_config(ws_url)
                assert is_valid, f'Valid config should pass validation: {config} - {message}'
        invalid_configs = ['', 'https://api.netrasystems.ai/ws', 'wss://api.netrasystems.ai', 'ws://api.netrasystems.ai/ws']
        for config in invalid_configs:
            if config:
                test_env = {'NEXT_PUBLIC_WS_URL': config}
                with patch.dict('os.environ', test_env, clear=False):
                    env = IsolatedEnvironment()
                    ws_url = env.get('NEXT_PUBLIC_WS_URL')
                    is_valid, message = validate_websocket_config(ws_url)
                    assert not is_valid, f'Invalid config should fail validation: {config}'

    def test_websocket_configuration_backwards_compatibility(self):
        """
        Test backwards compatibility during SSOT migration
        
        CRITICAL: Ensures system continues working during migration period
        """
        canonical_only = {'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai/ws'}
        with patch.dict('os.environ', canonical_only, clear=False):
            env = IsolatedEnvironment()
            canonical_url = env.get('NEXT_PUBLIC_WS_URL')
            deprecated_url = env.get('NEXT_PUBLIC_WEBSOCKET_URL')
            assert canonical_url is not None, 'Canonical variable should be accessible'
            assert deprecated_url is None, 'Deprecated variable should not exist'
            self.metrics.custom_metrics['migration_state'] = 'post_migration'
            self.metrics.custom_metrics['canonical_only'] = True
        dual_variables = {'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai/ws', 'NEXT_PUBLIC_WEBSOCKET_URL': 'wss://api.staging.netrasystems.ai/ws'}
        with patch.dict('os.environ', dual_variables, clear=False):
            env = IsolatedEnvironment()
            canonical_url = env.get('NEXT_PUBLIC_WS_URL')
            deprecated_url = env.get('NEXT_PUBLIC_WEBSOCKET_URL')
            if canonical_url and deprecated_url:
                self.metrics.custom_metrics['migration_state'] = 'pre_migration'
                self.metrics.custom_metrics['ssot_violation'] = True
                pytest.fail(f'SSOT VIOLATION: Both variables exist - NEXT_PUBLIC_WS_URL={canonical_url}, NEXT_PUBLIC_WEBSOCKET_URL={deprecated_url}. Issue #507 SSOT migration required.')

@pytest.mark.unit
class TestWebSocketServiceConfigurationIntegration(SSotBaseTestCase):
    """Unit tests for WebSocket service configuration integration"""

    def setup_method(self, method):
        """Setup for each test method"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

    def test_websocket_configuration_service_startup_compatibility(self):
        """Test that WebSocket configuration works correctly during service startup"""
        startup_config = {'ENVIRONMENT': 'staging', 'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai/ws', 'DEBUG': 'false'}
        with patch.dict('os.environ', startup_config, clear=False):
            env = IsolatedEnvironment()
            environment = env.get('ENVIRONMENT')
            ws_url = env.get('NEXT_PUBLIC_WS_URL')
            debug_mode = env.get('DEBUG', 'false').lower() == 'true'
            assert environment == 'staging', 'Environment should be loaded correctly'
            assert ws_url is not None, 'WebSocket URL should be loaded'
            assert ws_url.startswith('wss://'), 'URL should be secure in staging'
            deprecated_url = env.get('NEXT_PUBLIC_WEBSOCKET_URL')
            assert deprecated_url is None, 'Deprecated variable should not interfere'

    def test_websocket_url_configuration_error_handling(self):
        """Test error handling for WebSocket URL configuration issues"""
        empty_config = {}
        with patch.dict('os.environ', empty_config, clear=True):
            env = IsolatedEnvironment()
            ws_url = env.get('NEXT_PUBLIC_WS_URL')
            assert ws_url is None, 'Missing WebSocket URL should return None'
        malformed_config = {'NEXT_PUBLIC_WS_URL': 'not-a-url'}
        with patch.dict('os.environ', malformed_config, clear=False):
            env = IsolatedEnvironment()
            ws_url = env.get('NEXT_PUBLIC_WS_URL')
            assert ws_url == 'not-a-url', 'Environment should return URL as provided'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')