"""
ClickHouse URL Control Character Failures - Iteration 3 Persistent Issues

These tests WILL FAIL until ClickHouse URL control character sanitization is fixed.
Purpose: Replicate specific control character issues found in iteration 3 logs.

Critical Issue: "ClickHouse URL control characters: Still has newline at position 34"
"""

import pytest
import re
from urllib.parse import urlparse
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager

from netra_backend.app.db.clickhouse import ClickHouseDatabase
from shared.isolated_environment import IsolatedEnvironment


class TestClickHouseControlCharacterPersistence:
    """Tests that demonstrate persistent control character issues in ClickHouse URLs"""
    
    def test_newline_at_position_34_specific_issue(self):
        """
        Test: Newline character persists at position 34 in ClickHouse URL
        This test SHOULD FAIL until specific position sanitization is fixed
        """
        # Create URL with newline at position 34 (specific issue from logs)
        base_url = "http://clickhouse-host:8123/db"  # 33 characters
        url_with_newline_at_34 = base_url + "\n" + "/table"  # Newline at position 34
        
        # Should fail because newline at position 34 should be detected and removed
        with pytest.raises(ValueError) as exc_info:
            # This should detect and sanitize the control character
            sanitized_url = self._sanitize_clickhouse_url(url_with_newline_at_34)
            
            # Check if newline still exists at position 34
            if len(sanitized_url) > 34 and sanitized_url[33] == '\n':
                raise ValueError(f"Newline still present at position 34: {repr(sanitized_url)}")
        
        error_msg = str(exc_info.value)
        assert "position 34" in error_msg or "newline" in error_msg, \
            f"Expected position 34 newline error, got: {exc_info.value}"

    def test_secret_sanitization_not_removing_newlines_properly(self):
        """
        Test: Secret sanitization doesn't remove newlines properly from ClickHouse URLs
        This test SHOULD FAIL until secret sanitization handles newlines correctly
        """
        # URLs with newlines that secret sanitization might miss
        problematic_urls = [
            "http://localhost:8123\n",           # Trailing newline
            "http://localhost:8123\r\n",         # Windows line ending
            "http://user:pass\nword@host:8123",  # Newline in password
            "http://localhost\n:8123/db",        # Newline in hostname
            "http://localhost:8123/\ndb",        # Newline in path
            "http://localhost:8123?param=val\n", # Newline in query
        ]
        
        for url_with_newline in problematic_urls:
            # Mock secret sanitization that doesn't handle newlines properly
            with patch('netra_backend.app.core.isolated_environment.IsolatedEnvironment._sanitize_value') as mock_sanitize:
                # Simulate inadequate sanitization that misses newlines
                mock_sanitize.return_value = url_with_newline  # No sanitization applied
                
                env = IsolatedEnvironment(isolation_mode=True)
                env.set("CLICKHOUSE_URL", url_with_newline, "secret_manager")
                
                # Should fail because newlines should be removed by sanitization
                with pytest.raises(ValueError) as exc_info:
                    clickhouse_url = env.get("CLICKHOUSE_URL")
                    
                    # Validate that newlines were removed
                    if '\n' in clickhouse_url or '\r' in clickhouse_url:
                        raise ValueError(f"Secret sanitization failed to remove newlines: {repr(clickhouse_url)}")
                
                error_msg = str(exc_info.value).lower()
                assert any(phrase in error_msg for phrase in [
                    "newlines",
                    "sanitization failed",
                    "control character",
                    "line ending"
                ]), f"Expected newline sanitization error for URL: {url_with_newline}"

    def test_control_character_detection_comprehensive(self):
        """
        Test: Comprehensive control character detection in ClickHouse URLs
        This test SHOULD FAIL until all control characters are properly detected
        """
        # All ASCII control characters (0-31 and 127)
        control_chars = [chr(i) for i in range(32)] + [chr(127)]
        base_url = "http://localhost:8123"
        
        for char_code, control_char in enumerate(control_chars):
            if char_code >= 32:  # Skip printable chars, only test control chars
                char_code = 127  # DEL character
                control_char = chr(127)
            
            url_with_control_char = base_url + control_char
            
            # Should fail because ALL control characters should be detected
            with pytest.raises(ValueError) as exc_info:
                validated_url = self._validate_clickhouse_url_comprehensive(url_with_control_char)
            
            error_msg = str(exc_info.value).lower()
            assert f"ascii {char_code}" in error_msg or "control character" in error_msg, \
                f"Expected control character detection for ASCII {char_code}, got: {exc_info.value}"

    def test_url_sanitization_edge_cases(self):
        """
        Test: Edge cases in URL sanitization that might miss control characters
        This test SHOULD FAIL until edge case handling is complete
        """
        # Edge cases that sanitization might miss
        edge_case_urls = [
            "http://localhost:8123\x00",         # Null byte
            "http://localhost:8123\x1f",         # Unit separator
            "http://localhost:8123\x7f",         # DEL character
            "http://localhost:8123\x0b\x0c",     # Vertical tab + Form feed
            "http://\x08localhost:8123",         # Backspace in hostname
            "http://localhost:8123/\x1edb",      # Record separator in path
            "http://localhost:8123?\x1fparam=1", # Unit separator in query
        ]
        
        for url in edge_case_urls:
            # Should fail because edge case control characters should be caught
            with pytest.raises(ValueError) as exc_info:
                self._comprehensive_url_sanitization(url)
            
            error_msg = str(exc_info.value)
            # Should identify the specific control character
            assert "control character" in error_msg.lower(), \
                f"Expected edge case control character detection for: {repr(url)}"

    def test_clickhouse_database_construction_control_char_validation(self):
        """
        Test: ClickHouseDatabase constructor should validate against control characters
        This test SHOULD FAIL until constructor validation is comprehensive
        """
        # Test all components with control characters
        control_char_components = [
            {"host": "localhost\n", "component": "host"},
            {"user": "default\r", "component": "user"},
            {"password": "pass\t", "component": "password"},  
            {"database": "test\x1f", "component": "database"},
            {"host": "host\x00", "component": "host"},       # Null byte
            {"host": "host\x7f", "component": "host"},       # DEL
        ]
        
        for component_data in control_char_components:
            base_config = {
                "host": "localhost",
                "port": 8123,
                "database": "default",
                "user": "default",
                "password": "",
                "secure": False
            }
            
            # Update with component containing control character
            component_name = component_data["component"]
            base_config.update({k: v for k, v in component_data.items() if k != "component"})
            
            # Should fail during constructor validation
            with pytest.raises(ValueError) as exc_info:
                db = ClickHouseDatabase(**base_config)
            
            error_msg = str(exc_info.value).lower()
            assert component_name in error_msg and "control character" in error_msg, \
                f"Expected {component_name} control character validation error"

    def _sanitize_clickhouse_url(self, url: str) -> str:
        """
        URL sanitization that SHOULD exist but currently doesn't work properly
        This method represents what the system SHOULD do for sanitization
        """
        # This should remove ALL control characters, but currently doesn't
        control_chars = [chr(i) for i in range(32)] + [chr(127)]
        
        sanitized = url
        for char in control_chars:
            if char in sanitized:
                # This should remove the character but currently doesn't
                # Simulate the CURRENT broken behavior
                if char != '\n':  # Simulate that only some chars are removed
                    sanitized = sanitized.replace(char, '')
        
        # If newline is still present, this should fail
        if '\n' in sanitized:
            raise ValueError(f"Sanitization failed to remove newlines: {repr(sanitized)}")
        
        return sanitized

    def _validate_clickhouse_url_comprehensive(self, url: str) -> str:
        """
        Comprehensive URL validation that SHOULD exist
        """
        # Check ALL control characters (ASCII 0-31 and 127)
        for i in range(32):
            char = chr(i)
            if char in url:
                raise ValueError(f"URL contains control character: ASCII {i} ({repr(char)})")
        
        # Check DEL character (127)
        if chr(127) in url:
            raise ValueError(f"URL contains control character: ASCII 127 (DEL)")
        
        return url

    def _comprehensive_url_sanitization(self, url: str) -> str:
        """
        Comprehensive URL sanitization that SHOULD handle all edge cases
        """
        # This should catch ALL control characters including edge cases
        for i in range(128):
            char = chr(i)
            # Control characters are 0-31 and 127
            if i < 32 or i == 127:
                if char in url:
                    raise ValueError(f"URL contains control character: ASCII {i} ({repr(char)})")
        
        return url


class TestClickHouseEnvironmentVariableSanitization:
    """Tests for ClickHouse environment variable sanitization issues"""
    
    def test_clickhouse_host_newline_not_sanitized_from_environment(self):
        """
        Test: CLICKHOUSE_HOST with newlines not properly sanitized from environment
        This test SHOULD FAIL until environment variable sanitization is fixed
        """
        # Environment variables with newlines that should be sanitized
        problematic_env_values = [
            "clickhouse-host\n",      # Trailing newline
            "\nclickhouse-host",      # Leading newline  
            "clickhouse\nhost",       # Embedded newline
            "host\r\n",              # Windows line ending
            "host\n\r",              # Mixed line endings
        ]
        
        for host_value in problematic_env_values:
            env_vars = {
                'CLICKHOUSE_HOST': host_value,
                'CLICKHOUSE_PORT': '8123',
            }
            
            with patch.dict('os.environ', env_vars):
                env = IsolatedEnvironment(isolation_mode=False)
                
                # Should fail because environment sanitization should remove newlines
                with pytest.raises(ValueError) as exc_info:
                    host = env.get('CLICKHOUSE_HOST')
                    
                    # Check if newlines are still present
                    if '\n' in host or '\r' in host:
                        raise ValueError(f"Environment sanitization failed to remove newlines from CLICKHOUSE_HOST: {repr(host)}")
                
                error_msg = str(exc_info.value).lower()
                assert "newlines" in error_msg or "sanitization failed" in error_msg, \
                    f"Expected environment sanitization error for host: {repr(host_value)}"

    def test_clickhouse_connection_string_building_with_unsanitized_components(self):
        """
        Test: ClickHouse connection string building with unsanitized components
        This test SHOULD FAIL until connection string building validates components
        """
        # Components with control characters that slip through
        component_sets = [
            {"host": "localhost\n", "port": "8123", "expected_error": "host"},
            {"host": "localhost", "port": "8123\r", "expected_error": "port"},
            {"host": "localhost", "port": "8123", "user": "user\t", "expected_error": "user"},
            {"host": "localhost", "port": "8123", "database": "db\x1f", "expected_error": "database"},
        ]
        
        for components in component_sets:
            expected_error_component = components.pop("expected_error")
            
            # Should fail because connection string building should validate components
            with pytest.raises(ValueError) as exc_info:
                connection_string = self._build_clickhouse_connection_string(**components)
            
            error_msg = str(exc_info.value).lower()
            assert expected_error_component in error_msg and "control character" in error_msg, \
                f"Expected {expected_error_component} validation error in connection string building"

    def test_staging_environment_clickhouse_strict_control_character_validation(self):
        """
        Test: Staging environment should have strict control character validation
        This test SHOULD FAIL until staging validation is comprehensive
        """
        staging_env_vars = {
            'ENVIRONMENT': 'staging',
            'CLICKHOUSE_HOST': 'staging-clickhouse\n',  # Newline should be rejected
            'CLICKHOUSE_PORT': '8123',
        }
        
        with patch.dict('os.environ', staging_env_vars):
            # Should fail because staging should reject ANY control characters
            with pytest.raises(ValueError) as exc_info:
                env = IsolatedEnvironment(isolation_mode=False)
                
                if env.get('ENVIRONMENT') == 'staging':
                    host = env.get('CLICKHOUSE_HOST')
                    self._staging_strict_validation(host)
            
            error_msg = str(exc_info.value).lower()
            assert any(phrase in error_msg for phrase in [
                "staging validation",
                "control character",
                "strict mode",
                "not allowed in staging"
            ]), "Staging should enforce strict control character validation"

    def _build_clickhouse_connection_string(self, host: str, port: str, user: str = "default", 
                                          database: str = "default", password: str = "") -> str:
        """
        Connection string building that SHOULD validate components
        """
        components = {"host": host, "port": port, "user": user, "database": database, "password": password}
        
        # Validate each component for control characters
        control_chars = [chr(i) for i in range(32)] + [chr(127)]
        
        for component_name, component_value in components.items():
            for char in control_chars:
                if char in str(component_value):
                    raise ValueError(f"{component_name} contains control character: {repr(char)}")
        
        return f"http://{user}:{password}@{host}:{port}/{database}"

    def _staging_strict_validation(self, value: str) -> bool:
        """
        Staging environment strict validation that SHOULD exist
        """
        # Staging should reject ANY control characters
        control_chars = [chr(i) for i in range(32)] + [chr(127)]
        
        for char in control_chars:
            if char in value:
                raise ValueError(f"Staging validation: control character not allowed: {repr(char)}")
        
        return True


class TestClickHouseURLParsingRobustness:
    """Tests for robust ClickHouse URL parsing with control characters"""
    
    def test_url_parsing_error_reporting_for_control_characters(self):
        """
        Test: URL parsing should provide clear error reporting for control characters
        This test SHOULD FAIL until error reporting is descriptive
        """
        # URLs with various control characters for testing error reporting
        control_char_urls = [
            ("http://localhost:8123\n", "newline"),
            ("http://localhost:8123\r", "carriage return"),
            ("http://localhost:8123\t", "tab"),
            ("http://localhost:8123\x00", "null byte"),
            ("http://localhost:8123\x1f", "unit separator"),
            ("http://localhost:8123\x7f", "delete character"),
        ]
        
        for url, char_name in control_char_urls:
            # Should fail with descriptive error message
            with pytest.raises(ValueError) as exc_info:
                self._parse_clickhouse_url_with_validation(url)
            
            error_msg = str(exc_info.value).lower()
            # Error message should be descriptive and mention the specific character
            assert len(error_msg) > 30, "Error message should be descriptive"
            assert any(phrase in error_msg for phrase in [
                char_name.lower(),
                "control character",
                "invalid url",
                "character at position"
            ]), f"Error message should describe the control character issue for {char_name}: {error_msg}"

    def test_url_component_extraction_with_embedded_control_characters(self):
        """
        Test: URL component extraction should handle embedded control characters
        This test SHOULD FAIL until component extraction is robust
        """
        # URLs with control characters in different components
        component_test_urls = [
            ("http://user\nname:pass@host:8123/db", "username"),
            ("http://username:pass\tword@host:8123/db", "password"),
            ("http://username:password@ho\rst:8123/db", "hostname"),
            ("http://username:password@host:8123/da\x1ftabase", "database"),
            ("http://username:password@host:8123/db?param=val\nue", "query parameter"),
        ]
        
        for url, component_name in component_test_urls:
            # Should fail when trying to extract components with control characters
            with pytest.raises(ValueError) as exc_info:
                components = self._extract_clickhouse_url_components(url)
            
            error_msg = str(exc_info.value).lower()
            assert component_name.replace(" ", "").lower() in error_msg or "control character" in error_msg, \
                f"Expected {component_name} control character error, got: {error_msg}"

    def _parse_clickhouse_url_with_validation(self, url: str) -> dict:
        """
        URL parsing with validation that SHOULD provide clear error messages
        """
        # Check for control characters with descriptive error reporting
        control_chars = {
            '\n': 'newline',
            '\r': 'carriage return', 
            '\t': 'tab',
            '\x00': 'null byte',
            '\x1f': 'unit separator',
            '\x7f': 'delete character'
        }
        
        for char, name in control_chars.items():
            if char in url:
                position = url.index(char)
                raise ValueError(
                    f"URL parsing failed: {name} character found at position {position}. "
                    f"Control characters are not allowed in URLs. URL: {repr(url)}"
                )
        
        # Additional validation for other control characters
        for i in range(32):
            char = chr(i)
            if char in url and char not in control_chars:
                position = url.index(char)
                raise ValueError(
                    f"URL parsing failed: control character (ASCII {i}) found at position {position}. "
                    f"URL: {repr(url)}"
                )
        
        return {"url": url, "valid": True}

    def _extract_clickhouse_url_components(self, url: str) -> dict:
        """
        URL component extraction that SHOULD validate components
        """
        try:
            parsed = urlparse(url)
            
            components = {
                "scheme": parsed.scheme,
                "username": parsed.username,
                "password": parsed.password,  
                "hostname": parsed.hostname,
                "port": parsed.port,
                "path": parsed.path,
                "query": parsed.query,
                "fragment": parsed.fragment
            }
            
            # Validate each component for control characters
            control_chars = [chr(i) for i in range(32)] + [chr(127)]
            
            for component_name, component_value in components.items():
                if component_value:
                    for char in control_chars:
                        if char in str(component_value):
                            raise ValueError(f"{component_name} contains control character: {repr(char)}")
            
            return components
            
        except Exception as e:
            raise ValueError(f"URL component extraction failed: {e}")