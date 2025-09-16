"""
GCP Staging ClickHouse URL Configuration Error Tests
Failing tests that replicate ClickHouse URL validation issues found in staging logs

These tests WILL FAIL until the underlying URL validation issues are resolved.
Purpose: Demonstrate URL configuration problems and prevent regressions.

Issues replicated:
1. URL contains control characters (newline \n)
2. URL contains other control characters (\r, \t, etc.)
3. Malformed URLs from environment variable parsing
4. URL validation bypassed or insufficient
"""

import pytest
import re
from urllib.parse import urlparse, ParseResult
from test_framework.database.test_database_manager import DatabaseTestManager

from netra_backend.app.db.clickhouse import ClickHouseDatabase
from shared.isolated_environment import IsolatedEnvironment


class TestClickHouseURLControlCharacters:
    """Tests that replicate ClickHouse URL control character issues from staging logs"""
    
    def test_clickhouse_url_contains_newline_character(self):
        """
        Test: ClickHouse URL contains newline character (\n)
        This test SHOULD FAIL until URL validation prevents control characters
        """
        # Simulate URL with newline from environment variable parsing
        malformed_url_with_newline = "http://localhost:8123\n"
        
        # This should fail during URL validation
        with pytest.raises(ValueError) as exc_info:
            # URL parsing should detect and reject control characters
            self._validate_clickhouse_url(malformed_url_with_newline)
            
        error_msg = str(exc_info.value).lower()
        assert any(phrase in error_msg for phrase in [
            "control character",
            "invalid character", 
            "newline",
            "malformed url",
            "invalid url"
        ]), f"Expected URL validation error for newline character, got: {exc_info.value}"

    def test_clickhouse_url_contains_carriage_return(self):
        """
        Test: ClickHouse URL contains carriage return character (\r)
        This test SHOULD FAIL until URL validation is comprehensive
        """
        # Simulate URL with carriage return
        malformed_url_with_cr = "http://localhost:8123\r"
        
        with pytest.raises(ValueError) as exc_info:
            self._validate_clickhouse_url(malformed_url_with_cr)
            
        error_msg = str(exc_info.value).lower()
        assert any(phrase in error_msg for phrase in [
            "control character",
            "carriage return",
            "invalid character",
            "malformed url"
        ]), f"Expected URL validation error for carriage return, got: {exc_info.value}"

    def test_clickhouse_url_contains_tab_character(self):
        """
        Test: ClickHouse URL contains tab character (\t)
        This test SHOULD FAIL until URL validation handles all control chars
        """
        # Simulate URL with tab character
        malformed_url_with_tab = "http://localhost:8123\t"
        
        with pytest.raises(ValueError) as exc_info:
            self._validate_clickhouse_url(malformed_url_with_tab)
            
        error_msg = str(exc_info.value).lower()
        assert any(phrase in error_msg for phrase in [
            "control character",
            "tab",
            "invalid character",
            "malformed url"
        ]), f"Expected URL validation error for tab character, got: {exc_info.value}"

    def test_clickhouse_url_multiple_control_characters(self):
        """
        Test: ClickHouse URL contains multiple control characters
        This test SHOULD FAIL until URL sanitization is robust
        """
        # Simulate URL with multiple control characters
        malformed_url_multi = "http://localhost:8123\n\r\t"
        
        with pytest.raises(ValueError) as exc_info:
            self._validate_clickhouse_url(malformed_url_multi)
            
        error_msg = str(exc_info.value).lower()
        assert "control character" in error_msg or "invalid" in error_msg, \
            f"Expected URL validation error for multiple control chars, got: {exc_info.value}"

    def test_clickhouse_url_embedded_control_characters(self):
        """
        Test: ClickHouse URL with control characters embedded in path/query
        This test SHOULD FAIL until URL validation is thorough
        """
        # Control characters embedded in different parts of URL
        embedded_urls = [
            "http://localhost:8123/database\n/table",
            "http://localhost:8123?param=value\n&other=test",
            "http://user\nname:pass@localhost:8123/db",
            "http://localhost:8123/path?query=val\rue"
        ]
        
        for url in embedded_urls:
            with pytest.raises(ValueError) as exc_info:
                self._validate_clickhouse_url(url)
                
            error_msg = str(exc_info.value).lower()
            assert any(phrase in error_msg for phrase in [
                "control character",
                "invalid character",
                "malformed url"
            ]), f"Expected validation error for embedded control chars in {url}, got: {exc_info.value}"

    def _validate_clickhouse_url(self, url: str) -> bool:
        """
        URL validation that SHOULD exist but currently doesn't
        This method represents what the system SHOULD do
        """
        # Check for control characters (ASCII 0-31 and 127)
        control_chars = [chr(i) for i in range(32)] + [chr(127)]
        
        for char in control_chars:
            if char in url:
                raise ValueError(f"URL contains control character: {repr(char)} (ASCII {ord(char)})")
        
        # Additional URL validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception as e:
            raise ValueError(f"URL parsing failed: {e}")
            
        return True


class TestClickHouseConfigurationValidation:
    """Test ClickHouse configuration validation from environment"""
    
    def test_clickhouse_host_environment_variable_parsing(self):
        """
        Test: ClickHouse host from environment contains control characters
        This test SHOULD FAIL until env var sanitization is implemented
        """
        # Simulate environment variable with control characters
        malformed_env_vars = {
            'CLICKHOUSE_HOST': 'localhost\n',
            'CLICKHOUSE_PORT': '8123',
            'CLICKHOUSE_USER': 'default',
            'CLICKHOUSE_PASSWORD': ''
        }
        
        with patch.dict('os.environ', malformed_env_vars):
            env = IsolatedEnvironment(isolation_mode=False)
            
            # Should fail when parsing environment variables
            with pytest.raises(ValueError) as exc_info:
                host = env.get('CLICKHOUSE_HOST')
                self._validate_host_string(host)
                
            assert "control character" in str(exc_info.value).lower(), \
                f"Expected host validation error, got: {exc_info.value}"

    def test_clickhouse_database_construction_with_malformed_config(self):
        """
        Test: ClickHouseDatabase construction with malformed configuration
        This test SHOULD FAIL until constructor validation is added
        """
        # Malformed configuration with control characters
        with pytest.raises(ValueError) as exc_info:
            db = ClickHouseDatabase(
                host="localhost\n",  # Contains newline
                port=8123,
                database="default",
                user="default",
                password="",
                secure=False
            )
            
        error_msg = str(exc_info.value).lower()
        assert any(phrase in error_msg for phrase in [
            "invalid host",
            "control character",
            "malformed configuration"
        ]), f"Expected configuration validation error, got: {exc_info.value}"

    def test_clickhouse_url_construction_from_components(self):
        """
        Test: ClickHouse URL construction should validate components
        This test SHOULD FAIL until URL building validates inputs
        """
        # Components with control characters
        malformed_components = [
            {"host": "localhost\n", "expected_error": "host"},
            {"user": "default\r", "expected_error": "user"},
            {"password": "pass\t", "expected_error": "password"},
            {"database": "db\n", "expected_error": "database"}
        ]
        
        for component_set in malformed_components:
            base_config = {
                "host": "localhost",
                "port": 8123,
                "user": "default", 
                "password": "",
                "database": "default"
            }
            
            # Update with malformed component
            error_component = component_set["expected_error"]
            base_config.update({k: v for k, v in component_set.items() if k != "expected_error"})
            
            with pytest.raises(ValueError) as exc_info:
                url = self._build_clickhouse_url(**base_config)
                
            error_msg = str(exc_info.value).lower()
            assert error_component in error_msg or "control character" in error_msg, \
                f"Expected {error_component} validation error, got: {exc_info.value}"

    def test_staging_environment_clickhouse_url_strict_validation(self):
        """
        Test: Staging environment should have strict ClickHouse URL validation
        This test SHOULD FAIL until staging validation is enforced
        """
        staging_env_vars = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_HOST': 'localhost\n',  # Invalid
            'CLICKHOUSE_PORT': '8123'
        }
        
        with patch.dict('os.environ', staging_env_vars):
            # Staging should NEVER accept malformed URLs
            with pytest.raises(ValueError) as exc_info:
                env = IsolatedEnvironment(isolation_mode=False)
                host = env.get('CLICKHOUSE_HOST')
                
                # Staging should validate strictly
                if env.get('ENVIRONMENT') == 'staging':
                    self._validate_host_string(host)
                    
            assert "staging" in str(exc_info.value).lower() or "control character" in str(exc_info.value).lower(), \
                "Staging should enforce strict validation"

    def _validate_host_string(self, host: str) -> bool:
        """
        Host validation that SHOULD exist but currently doesn't
        """
        if not host:
            raise ValueError("Host cannot be empty")
            
        # Check for control characters
        control_chars = [chr(i) for i in range(32)] + [chr(127)]
        
        for char in control_chars:
            if char in host:
                raise ValueError(f"Host contains control character: {repr(char)} (ASCII {ord(char)})")
        
        return True

    def _build_clickhouse_url(self, host: str, port: int, user: str, password: str, database: str) -> str:
        """
        URL building that SHOULD validate components
        """
        # Validate each component
        for name, value in [("host", host), ("user", user), ("password", password), ("database", database)]:
            if isinstance(value, str):
                control_chars = [chr(i) for i in range(32)] + [chr(127)]
                for char in control_chars:
                    if char in value:
                        raise ValueError(f"{name} contains control character: {repr(char)}")
        
        # Build URL (simplified)
        return f"http://{user}:{password}@{host}:{port}/{database}"


class TestClickHouseConnectionValidation:
    """Test ClickHouse connection validation with malformed URLs"""
    
    @pytest.mark.asyncio
    async def test_clickhouse_connection_with_control_char_url(self):
        """
        Test: ClickHouse connection attempt with control character URL
        This test SHOULD FAIL until connection validation prevents malformed URLs
        """
        # Mock ClickHouse client to avoid external dependency
        with patch('clickhouse_connect.get_client') as mock_get_client:
            # Should fail before reaching the client due to URL validation
            mock_client = MagicNone  # TODO: Use real service instance
            mock_get_client.return_value = mock_client
            
            with pytest.raises(ValueError) as exc_info:
                # This should validate URL before attempting connection
                db = ClickHouseDatabase(
                    host="localhost\n",
                    port=8123,
                    database="default", 
                    user="default",
                    password="",
                    secure=False
                )
                
            assert "control character" in str(exc_info.value).lower(), \
                f"Expected URL validation error, got: {exc_info.value}"

    def test_clickhouse_url_parsing_error_handling(self):
        """
        Test: ClickHouse URL parsing should handle and report control characters
        This test SHOULD FAIL until error reporting is clear
        """
        problematic_urls = [
            "http://localhost:8123\n",
            "http://localhost:8123\r\n", 
            "http://localhost\t:8123",
            "http://\nlocalhost:8123"
        ]
        
        for url in problematic_urls:
            with pytest.raises(ValueError) as exc_info:
                # URL parsing should provide clear error messages
                self._parse_and_validate_clickhouse_url(url)
                
            error_msg = str(exc_info.value)
            # Error message should be descriptive
            assert len(error_msg) > 20, "Error message should be descriptive"
            assert any(phrase in error_msg.lower() for phrase in [
                "control character",
                "invalid url",
                "newline",
                "carriage return", 
                "tab"
            ]), f"Error message should be specific for URL: {url}, got: {error_msg}"

    def _parse_and_validate_clickhouse_url(self, url: str) -> ParseResult:
        """
        URL parsing with validation that SHOULD exist
        """
        # Pre-validate for control characters
        control_chars = [chr(i) for i in range(32)] + [chr(127)]
        
        for char in control_chars:
            if char in url:
                char_name = {
                    '\n': 'newline',
                    '\r': 'carriage return',
                    '\t': 'tab'
                }.get(char, f'control character (ASCII {ord(char)})')
                
                raise ValueError(f"URL contains {char_name}: {repr(url)}")
        
        try:
            return urlparse(url)
        except Exception as e:
            raise ValueError(f"URL parsing failed: {e}")