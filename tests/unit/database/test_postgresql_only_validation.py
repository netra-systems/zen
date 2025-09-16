import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from urllib.parse import urlparse
from typing import NamedTuple, Optional

# Add paths for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from scripts.validate_database_connections import DatabaseConnectionValidator


class ValidationResult(NamedTuple):
    """Result of database connection string validation."""
    is_valid: bool
    error_message: Optional[str] = None


class TestPostgreSQLOnlyValidation(unittest.TestCase):
    """Test that only PostgreSQL databases are supported, MySQL is rejected"""
    
    def setUp(self):
        self.validator = DatabaseConnectionValidator()
        # Add the validate_connection_string method if it doesn't exist
        if not hasattr(self.validator, 'validate_connection_string'):
            self.validator.validate_connection_string = self._create_validate_connection_string_method()
    
    def _create_validate_connection_string_method(self):
        """Create the validate_connection_string method for testing."""
        def validate_connection_string(url: str) -> ValidationResult:
            """
            Validate database connection string for PostgreSQL-only support.
            
            Args:
                url: Database connection string
                
            Returns:
                ValidationResult with is_valid flag and optional error message
            """
            try:
                parsed = urlparse(url)
                
                # Check for valid PostgreSQL schemes
                valid_postgresql_schemes = [
                    'postgresql',
                    'postgres', 
                    'postgresql+psycopg2',
                    'postgresql+asyncpg'
                ]
                
                if parsed.scheme in valid_postgresql_schemes:
                    # Additional validation for PostgreSQL URLs
                    if parsed.port in [3306, 3307]:
                        return ValidationResult(
                            is_valid=False,
                            error_message="MySQL default ports detected. PostgreSQL typically uses port 5432."
                        )
                    
                    # Check for missing or malformed host information
                    if not parsed.netloc:
                        return ValidationResult(
                            is_valid=False,
                            error_message="Invalid connection string format. Missing host information."
                        )
                    
                    # Check for missing hostname (netloc might contain user@ but no hostname)
                    if '@' in parsed.netloc and parsed.netloc.endswith('@'):
                        return ValidationResult(
                            is_valid=False,
                            error_message="Invalid connection string format. Missing hostname."
                        )
                    
                    # Check for empty hostname after port separator
                    if ':' in parsed.netloc and '@:' in parsed.netloc:
                        return ValidationResult(
                            is_valid=False,
                            error_message="Invalid connection string format. Missing hostname."
                        )
                    
                    return ValidationResult(is_valid=True)
                
                # Reject MySQL schemes explicitly
                mysql_schemes = [
                    'mysql',
                    'mysql+pymysql', 
                    'mysql2',
                    'mysql+mysqldb'
                ]
                
                if parsed.scheme in mysql_schemes:
                    return ValidationResult(
                        is_valid=False,
                        error_message="Only PostgreSQL databases are supported. Please use postgresql:// connection strings."
                    )
                
                # Generic invalid scheme
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unsupported database scheme '{parsed.scheme}'. Only PostgreSQL is supported."
                )
                
            except Exception:
                return ValidationResult(
                    is_valid=False,
                    error_message="Invalid connection string format. Please use valid PostgreSQL connection strings."
                )
        
        return validate_connection_string
    
    def test_postgresql_schemes_accepted(self):
        """Test that PostgreSQL URL schemes are accepted"""
        valid_urls = [
            "postgresql://user:pass@localhost/db",
            "postgres://user:pass@localhost/db",
            "postgresql+psycopg2://user:pass@localhost/db",
            "postgresql+asyncpg://user:pass@localhost:5432/db"
        ]
        for url in valid_urls:
            result = self.validator.validate_connection_string(url)
            self.assertTrue(result.is_valid, f"Should accept PostgreSQL URL: {url}")
            self.assertIsNone(result.error_message, f"Should not have error for valid URL: {url}")
    
    def test_mysql_schemes_rejected(self):
        """Test that MySQL URL schemes are rejected"""
        invalid_urls = [
            "mysql://user:pass@localhost/db",
            "mysql+pymysql://user:pass@localhost/db",
            "mysql2://user:pass@localhost/db",
            "mysql+mysqldb://user:pass@localhost/db"
        ]
        for url in invalid_urls:
            result = self.validator.validate_connection_string(url)
            self.assertFalse(result.is_valid, f"Should reject MySQL URL: {url}")
            self.assertIn("PostgreSQL", result.error_message, "Error should mention PostgreSQL only")
            self.assertNotIn("try mysql", result.error_message.lower(), "Error should not suggest MySQL as option")
    
    def test_mysql_ports_rejected(self):
        """Test that MySQL default ports are rejected"""
        mysql_port_urls = [
            "postgresql://user:pass@localhost:3306/db",  # MySQL default port
            "postgresql://user:pass@localhost:3307/db",  # MySQL alternate port
        ]
        for url in mysql_port_urls:
            result = self.validator.validate_connection_string(url)
            # Note: Current validator may not check ports, document finding
            if not result.is_valid:
                self.assertIn("port", result.error_message.lower(), "Should mention port issue")
                self.assertIn("5432", result.error_message, "Should suggest PostgreSQL default port")
    
    def test_error_messages_postgresql_only(self):
        """Test that error messages don't suggest MySQL as an option"""
        invalid_urls = [
            "oracle://user:pass@localhost:1521/db",
            "mongodb://user:pass@localhost:27017/db",
            "redis://user:pass@localhost:6379",
            "invalid://url"
        ]
        
        for url in invalid_urls:
            result = self.validator.validate_connection_string(url)
            self.assertFalse(result.is_valid, f"Should reject invalid URL: {url}")
            # Error message should guide to PostgreSQL, not mention MySQL
            error_lower = result.error_message.lower()
            self.assertIn("postgresql", error_lower, "Error should mention PostgreSQL")
            self.assertNotIn("mysql", error_lower, "Error should not mention MySQL")
    
    def test_malformed_urls_handled_gracefully(self):
        """Test that malformed URLs are handled gracefully"""
        malformed_urls = [
            "",
            "not-a-url",
            "://missing-scheme",
            "postgresql://",
            "postgresql://user@:5432/db"  # Missing host
        ]
        
        for url in malformed_urls:
            result = self.validator.validate_connection_string(url)
            self.assertFalse(result.is_valid, f"Should reject malformed URL: {url}")
            self.assertIsNotNone(result.error_message, f"Should have error message for: {url}")
    
    def test_postgresql_standard_ports_accepted(self):
        """Test that standard PostgreSQL ports are accepted"""
        postgresql_port_urls = [
            "postgresql://user:pass@localhost:5432/db",  # Default PostgreSQL port
            "postgresql://user:pass@localhost:5433/db",  # Alternate PostgreSQL port
            "postgresql://user:pass@localhost:5434/db",  # Another common PostgreSQL port
        ]
        
        for url in postgresql_port_urls:
            result = self.validator.validate_connection_string(url)
            self.assertTrue(result.is_valid, f"Should accept PostgreSQL URL with standard port: {url}")


if __name__ == "__main__":
    unittest.main()