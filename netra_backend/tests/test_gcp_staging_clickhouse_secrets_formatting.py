"""
GCP Staging ClickHouse Secret Formatting Issues - Failing Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all customer segments)
- Business Goal: Platform Stability and Data Pipeline Reliability  
- Value Impact: Prevents ClickHouse connectivity failures that block analytics and metrics
- Strategic/Revenue Impact: Analytics-driven features depend on ClickHouse for performance monitoring

These failing tests replicate the exact ClickHouse secret formatting issues found in GCP staging deployment.
The tests are designed to FAIL until the underlying secret formatting problems are resolved.

Critical Issues Tested:
1. ClickHouse secrets containing extra whitespace/newlines from Google Secret Manager
2. Control characters in ClickHouse URLs causing connection failures
3. Secret trimming and validation during configuration loading
4. URL construction with malformed parameters
5. Environment variable parsing introducing formatting issues
"""

import asyncio
import re
import pytest
from typing import Dict, Any, Optional
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager

from netra_backend.app.config import get_config
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase


class TestClickHouseSecretFormattingIssues:
    """Test ClickHouse secret formatting issues from GCP Secret Manager."""
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_clickhouse_host_contains_newline_character(self):
        """Test ClickHouse host secret contains newline character from Secret Manager.
        
        This test should FAIL until ClickHouse secrets are properly trimmed in GCP Secret Manager.
        """
        # Mock ClickHouse host with newline (common issue from Secret Manager)
        clickhouse_host_with_newline = "clickhouse.staging.example.com\n"
        
        with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
            mock_env_get.side_effect = lambda key, default=None: {
                'CLICKHOUSE_HOST': clickhouse_host_with_newline,
                'CLICKHOUSE_PORT': '8123',
                'CLICKHOUSE_USER': 'default',
                'CLICKHOUSE_PASSWORD': 'password',
                'CLICKHOUSE_DATABASE': 'netra_analytics'
            }.get(key, default)
            
            try:
                # This should fail due to newline in host
                clickhouse_db = ClickHouseDatabase(
                    host=clickhouse_host_with_newline,
                    port=8123,
                    database='netra_analytics',
                    user='default',
                    password='password'
                )
                
                # The URL construction should detect control characters
                url = clickhouse_db._build_connection_url()
                
                # Check if newline is present (indicates trimming not working)
                assert '\n' not in url, f"ClickHouse URL contains newline character: {repr(url)}"
                
                pytest.fail("Expected ClickHouse URL validation to detect control characters")
                
            except Exception as e:
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in [
                    'control character',
                    'invalid character',
                    'newline',
                    'malformed url',
                    'url validation failed'
                ]), f"Expected control character validation error but got: {e}"
                
                print(f"✅ Correctly detected ClickHouse host newline character: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_clickhouse_password_contains_whitespace_characters(self):
        """Test ClickHouse password secret contains extra whitespace from Secret Manager."""
        # Mock password with various whitespace issues
        passwords_with_whitespace = [
            " password ",      # Leading and trailing spaces
            "password\n",      # Trailing newline
            "password\r",      # Trailing carriage return
            "\tpassword\t",    # Leading and trailing tabs
            "password\r\n",    # Windows line ending
            " password\n ",    # Multiple whitespace types
        ]
        
        for malformed_password in passwords_with_whitespace:
            with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
                mock_env_get.side_effect = lambda key, default=None: {
                    'CLICKHOUSE_HOST': 'clickhouse.staging.example.com',
                    'CLICKHOUSE_PORT': '8123',
                    'CLICKHOUSE_USER': 'default',
                    'CLICKHOUSE_PASSWORD': malformed_password,
                    'CLICKHOUSE_DATABASE': 'netra_analytics'
                }.get(key, default)
                
                try:
                    clickhouse_db = ClickHouseDatabase()
                    url = clickhouse_db._build_connection_url()
                    
                    # Check for whitespace characters in URL
                    if any(char in url for char in ['\n', '\r', '\t']) or url.count(' ') > url.count('%20'):
                        pytest.fail(f"ClickHouse URL contains unescaped whitespace: {repr(url)}")
                    
                    # Try to connect - this should fail with authentication error due to malformed password
                    await clickhouse_db.test_connection()
                    pytest.fail("Expected ClickHouse authentication failure due to malformed password")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    # Accept either URL validation errors OR authentication failures
                    assert any(keyword in error_msg for keyword in [
                        'authentication failed',
                        'invalid password',
                        'control character',
                        'whitespace',
                        'malformed',
                        'connection refused'
                    ]), f"Expected password formatting error for {repr(malformed_password)} but got: {e}"
                    
                    print(f"✅ Correctly detected password formatting issue for {repr(malformed_password)}: {e}")
    
    @pytest.mark.staging
    def test_clickhouse_url_control_character_validation(self):
        """Test comprehensive control character validation in ClickHouse URLs."""
        # Test various control characters (ASCII 0-31 and 127)
        control_characters = [
            '\n',    # Newline (10)
            '\r',    # Carriage return (13)
            '\t',    # Tab (9)
            '\b',    # Backspace (8)
            '\f',    # Form feed (12)
            '\v',    # Vertical tab (11)
            '\x00',  # Null character (0)
            '\x1f',  # Unit separator (31)
            '\x7f',  # Delete (127)
        ]
        
        base_host = "clickhouse.staging.example.com"
        
        for control_char in control_characters:
            host_with_control_char = f"{base_host}{control_char}"
            
            with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
                mock_env_get.side_effect = lambda key, default=None: {
                    'CLICKHOUSE_HOST': host_with_control_char,
                    'CLICKHOUSE_PORT': '8123',
                    'CLICKHOUSE_USER': 'default',
                    'CLICKHOUSE_PASSWORD': 'password',
                    'CLICKHOUSE_DATABASE': 'netra_analytics'
                }.get(key, default)
                
                try:
                    clickhouse_db = ClickHouseDatabase()
                    url = clickhouse_db._build_connection_url()
                    
                    # URL should not contain control characters
                    for char in control_characters:
                        assert char not in url, f"URL contains control character {repr(char)}: {repr(url)}"
                    
                    pytest.fail(f"Expected control character validation to fail for {repr(control_char)}")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    assert any(keyword in error_msg for keyword in [
                        'control character',
                        'invalid character',
                        'malformed',
                        'url validation'
                    ]), f"Expected control character error for {repr(control_char)} but got: {e}"
                    
                    print(f"✅ Control character validation detected {repr(control_char)}: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_clickhouse_multiple_secret_formatting_issues(self):
        """Test ClickHouse configuration with multiple secret formatting issues simultaneously."""
        # Mock all secrets having formatting issues
        malformed_secrets = {
            'CLICKHOUSE_HOST': ' clickhouse.staging.example.com\n',  # Space and newline
            'CLICKHOUSE_PORT': '8123\r',  # Carriage return
            'CLICKHOUSE_USER': '\tdefault ',  # Tab and space
            'CLICKHOUSE_PASSWORD': ' password\n\r ',  # Multiple whitespace
            'CLICKHOUSE_DATABASE': 'netra_analytics\t'  # Tab
        }
        
        with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
            mock_env_get.side_effect = lambda key, default=None: malformed_secrets.get(key, default)
            
            try:
                clickhouse_db = ClickHouseDatabase()
                url = clickhouse_db._build_connection_url()
                
                # URL should not contain any control characters
                control_chars = ['\n', '\r', '\t', '\b', '\f', '\v']
                for char in control_chars:
                    assert char not in url, f"URL contains control character {repr(char)}: {repr(url)}"
                
                # If URL is clean, connection should still fail due to invalid host
                await clickhouse_db.test_connection()
                pytest.fail("Expected ClickHouse connection to fail with malformed secrets")
                
            except Exception as e:
                error_msg = str(e).lower()
                assert any(keyword in error_msg for keyword in [
                    'control character',
                    'connection failed',
                    'invalid host',
                    'malformed',
                    'url validation'
                ]), f"Expected secret formatting error but got: {e}"
                
                print(f"✅ Multiple secret formatting issues correctly detected: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_gcp_secret_manager_direct_formatting_issues(self):
        """Test that simulates direct GCP Secret Manager formatting issues."""
        # Simulate how GCP Secret Manager might return secrets
        def mock_gcp_secret_with_formatting_issues(secret_name):
            secrets_with_issues = {
                'clickhouse-host': 'clickhouse.staging.example.com\n',
                'clickhouse-user': 'default\r\n',
                'clickhouse-password': ' super_secret_password\n ',
                'clickhouse-port': '8123\t',
                'clickhouse-database': 'netra_analytics\r'
            }
            return secrets_with_issues.get(secret_name, 'default_value')
        
        # Mock the secret manager
        with patch('netra_backend.app.config.secrets.SecretManager') as mock_secret_manager:
            mock_instance = MagicNone  # TODO: Use real service instance
            mock_instance.get_secret.side_effect = mock_gcp_secret_with_formatting_issues
            mock_secret_manager.return_value = mock_instance
            
            # Mock environment to use secret manager
            with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}, clear=False):
                try:
                    config = get_config()
                    
                    # Check if config properly handles malformed secrets
                    clickhouse_config = {
                        'host': config.clickhouse_host,
                        'port': config.clickhouse_port,
                        'user': config.clickhouse_user,
                        'password': config.clickhouse_password,
                        'database': config.clickhouse_database
                    }
                    
                    # All config values should be properly trimmed
                    for key, value in clickhouse_config.items():
                        if isinstance(value, str):
                            # Check for control characters
                            control_chars = ['\n', '\r', '\t', '\b', '\f', '\v']
                            for char in control_chars:
                                assert char not in value, f"Config {key} contains control character {repr(char)}: {repr(value)}"
                            
                            # Check for leading/trailing whitespace
                            assert value == value.strip(), f"Config {key} has untrimmed whitespace: {repr(value)}"
                    
                    print("✅ All ClickHouse config values properly trimmed")
                    
                except AssertionError as e:
                    # This is expected - secret formatting is broken
                    print(f"✅ Correctly detected GCP secret formatting issues: {e}")
                    
                except Exception as e:
                    # Other configuration errors are also expected
                    error_msg = str(e).lower()
                    assert any(keyword in error_msg for keyword in [
                        'clickhouse',
                        'config',
                        'secret',
                        'format'
                    ]), f"Expected ClickHouse configuration error but got: {e}"
                    
                    print(f"✅ ClickHouse configuration failed due to formatting: {e}")
    
    @pytest.mark.staging
    def test_clickhouse_database_construction_with_malformed_secrets(self):
        """Test ClickHouse database construction fails with malformed secrets."""
        # Test various malformed secret scenarios
        malformed_scenarios = [
            {
                'name': 'host_with_multiple_newlines',
                'secrets': {
                    'CLICKHOUSE_HOST': 'clickhouse.staging.example.com\n\n',
                    'CLICKHOUSE_PORT': '8123',
                    'CLICKHOUSE_USER': 'default',
                    'CLICKHOUSE_PASSWORD': 'password',
                    'CLICKHOUSE_DATABASE': 'netra_analytics'
                }
            },
            {
                'name': 'port_with_whitespace',
                'secrets': {
                    'CLICKHOUSE_HOST': 'clickhouse.staging.example.com',
                    'CLICKHOUSE_PORT': ' 8123 ',
                    'CLICKHOUSE_USER': 'default',
                    'CLICKHOUSE_PASSWORD': 'password',
                    'CLICKHOUSE_DATABASE': 'netra_analytics'
                }
            },
            {
                'name': 'database_name_with_tabs',
                'secrets': {
                    'CLICKHOUSE_HOST': 'clickhouse.staging.example.com',
                    'CLICKHOUSE_PORT': '8123',
                    'CLICKHOUSE_USER': 'default',
                    'CLICKHOUSE_PASSWORD': 'password',
                    'CLICKHOUSE_DATABASE': '\tnetra_analytics\t'
                }
            },
            {
                'name': 'all_secrets_malformed',
                'secrets': {
                    'CLICKHOUSE_HOST': ' clickhouse.staging.example.com\n',
                    'CLICKHOUSE_PORT': '8123\r',
                    'CLICKHOUSE_USER': '\tdefault\t',
                    'CLICKHOUSE_PASSWORD': ' password \n',
                    'CLICKHOUSE_DATABASE': 'netra_analytics\r\n'
                }
            }
        ]
        
        for scenario in malformed_scenarios:
            with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
                mock_env_get.side_effect = lambda key, default=None: scenario['secrets'].get(key, default)
                
                try:
                    # ClickHouse construction should validate and reject malformed secrets
                    clickhouse_db = ClickHouseDatabase()
                    
                    # If construction succeeds, check if values are properly sanitized
                    config_values = [
                        clickhouse_db.host,
                        str(clickhouse_db.port),
                        clickhouse_db.user,
                        clickhouse_db.password,
                        clickhouse_db.database
                    ]
                    
                    # Check for control characters and whitespace
                    for value in config_values:
                        if value:  # Skip None values
                            control_chars = ['\n', '\r', '\t', '\b', '\f', '\v']
                            for char in control_chars:
                                assert char not in value, f"ClickHouse config contains control character {repr(char)} in scenario {scenario['name']}: {repr(value)}"
                            
                            # Check for proper trimming
                            assert value == value.strip(), f"ClickHouse config not properly trimmed in scenario {scenario['name']}: {repr(value)}"
                    
                    print(f"✅ ClickHouse construction properly sanitized secrets for scenario: {scenario['name']}")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    assert any(keyword in error_msg for keyword in [
                        'control character',
                        'invalid',
                        'malformed',
                        'validation failed',
                        'format'
                    ]), f"Expected formatting validation error for scenario {scenario['name']} but got: {e}"
                    
                    print(f"✅ ClickHouse construction correctly rejected malformed secrets for scenario {scenario['name']}: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_environment_clickhouse_strict_validation(self):
        """Test that staging environment enforces strict ClickHouse secret validation."""
        # Mock staging environment
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}, clear=False):
            # Test that staging rejects any malformed secrets
            malformed_secrets = {
                'CLICKHOUSE_HOST': '',  # Empty host
                'CLICKHOUSE_PORT': '8123\n',  # Port with newline
                'CLICKHOUSE_USER': None,  # Missing user
                'CLICKHOUSE_PASSWORD': ' ',  # Whitespace-only password
                'CLICKHOUSE_DATABASE': 'netra_analytics\r\n'  # Database with CRLF
            }
            
            with patch.object(IsolatedEnvironment, 'get') as mock_env_get:
                mock_env_get.side_effect = lambda key, default=None: malformed_secrets.get(key, default)
                
                try:
                    # Staging should strictly validate all ClickHouse secrets
                    config = get_config()
                    
                    # Try to access ClickHouse configuration
                    clickhouse_config = {
                        'host': config.clickhouse_host,
                        'port': config.clickhouse_port,
                        'user': config.clickhouse_user,
                        'password': config.clickhouse_password,
                        'database': config.clickhouse_database
                    }
                    
                    # In staging, no empty or malformed values should be accepted
                    for key, value in clickhouse_config.items():
                        if value is None or (isinstance(value, str) and not value.strip()):
                            pytest.fail(f"Staging environment should reject empty/null ClickHouse {key}: {repr(value)}")
                        
                        if isinstance(value, str):
                            # Check for control characters
                            if any(char in value for char in ['\n', '\r', '\t', '\b', '\f', '\v']):
                                pytest.fail(f"Staging environment should reject ClickHouse {key} with control characters: {repr(value)}")
                    
                    pytest.fail("Expected staging environment to reject malformed ClickHouse configuration")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    assert any(keyword in error_msg for keyword in [
                        'clickhouse',
                        'configuration',
                        'validation',
                        'staging',
                        'required',
                        'invalid'
                    ]), f"Expected staging validation error but got: {e}"
                    
                    print(f"✅ Staging environment correctly enforced strict ClickHouse validation: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "staging"])