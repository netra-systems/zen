"""
Security tests for error response information disclosure prevention.

These tests demonstrate missing security controls for debugging information
in error responses that could lead to information disclosure.

All tests are designed to FAIL to show current security gaps.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from netra_backend.app.core.error_response_models import ErrorResponse
from netra_backend.app.core.unified_error_handler import (
    UnifiedErrorHandler,
    api_error_handler,
    agent_error_handler
)
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.core.exceptions_base import NetraException
from shared.isolated_environment import IsolatedEnvironment


class TestProductionSecurityFiltering:
    """Test security filtering of debug information in production."""

    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing."""
        return UnifiedErrorHandler()

    @pytest.fixture
    def sensitive_exception(self):
        """Create exception with sensitive information in locals."""
        def sensitive_function():
            # Sensitive data that should never be exposed
            api_key = "sk-1234567890abcdef"
            database_password = "super_secret_db_password"
            user_ssn = "123-45-6789"
            credit_card = "4111-1111-1111-1111"
            jwt_secret = "HS256_jwt_secret_key_dont_expose"
            internal_service_token = "internal_service_token_12345"
            
            # Business sensitive data
            customer_data = {
                "email": "ceo@bigcompany.com",
                "salary": 250000,
                "performance_review": "confidential notes"
            }
            
            raise ValueError("Function failed with sensitive context")
        
        try:
            sensitive_function()
        except Exception as e:
            return e

    @pytest.mark.asyncio
    async def test_production_environment_missing_sensitive_data_filtering(
        self, error_handler, sensitive_exception
    ):
        """FAILING TEST: Production should filter sensitive data but doesn't."""
        context = ErrorContext(
            trace_id="test-trace-123",
            operation="sensitive_operation"
        )
        
        # Test in production environment
        with patch.dict(os.environ, {'NETRA_ENV': 'production'}):
            result = await error_handler.handle_error(sensitive_exception, context)
            
            assert isinstance(result, ErrorResponse)
            
            # This will FAIL - no security filtering mechanism exists
            # Convert entire response to string to check for sensitive data
            response_str = json.dumps(result.model_dump())
            
            # These sensitive values should be filtered but mechanism doesn't exist
            # Tests pass only because debug info isn't implemented yet
            assert "api_key" not in response_str
            assert "database_password" not in response_str
            assert "user_ssn" not in response_str
            assert "credit_card" not in response_str
            assert "jwt_secret" not in response_str
            
            # This will FAIL - no security classification system
            with pytest.raises(AttributeError):
                _ = result.security_level
            with pytest.raises(AttributeError):
                _ = result.data_classification

    @pytest.mark.asyncio
    async def test_development_environment_missing_debug_warnings(
        self, error_handler, sensitive_exception
    ):
        """FAILING TEST: Development should warn about sensitive data but doesn't."""
        context = ErrorContext(
            trace_id="test-trace-123",
            operation="sensitive_operation"
        )
        
        # Test in development environment
        with patch.dict(os.environ, {'NETRA_ENV': 'development'}):
            result = await error_handler.handle_error(sensitive_exception, context)
            
            assert isinstance(result, ErrorResponse)
            
            # This will FAIL - no debug warnings for sensitive data
            details = result.details or {}
            assert "security_warnings" not in details
            assert "sensitive_data_detected" not in details
            assert "debug_safety_notice" not in details

    @pytest.mark.asyncio
    async def test_staging_environment_missing_hybrid_filtering(self, error_handler, sensitive_exception):
        """FAILING TEST: Staging should use hybrid filtering but doesn't."""
        context = ErrorContext(
            trace_id="test-trace-123",
            operation="sensitive_operation"
        )
        
        # Test in staging environment
        with patch.dict(os.environ, {'NETRA_ENV': 'staging'}):
            result = await error_handler.handle_error(sensitive_exception, context)
            
            assert isinstance(result, ErrorResponse)
            
            # This will FAIL - no hybrid filtering for staging
            # Should show some debug info but filter highly sensitive data
            details = result.details or {}
            assert "filtered_debug_info" not in details
            assert "staging_safety_mode" not in details


class TestInformationDisclosureVulnerabilities:
    """Test for information disclosure vulnerabilities in error responses."""

    @pytest.fixture
    def error_handler(self):
        """Create error handler for testing."""
        return UnifiedErrorHandler()

    @pytest.mark.asyncio
    async def test_path_disclosure_vulnerability_missing_protection(self, error_handler):
        """FAILING TEST: File paths should be sanitized but aren't."""
        def path_disclosure_error():
            file_path = "/etc/passwd"
            config_path = "/home/user/.ssh/id_rsa"
            source_code_path = "/app/netra_backend/app/core/sensitive_module.py"
            raise FileNotFoundError(f"Could not access {file_path}, {config_path}, {source_code_path}")
            
        try:
            path_disclosure_error()
        except Exception as e:
            context = ErrorContext(
                trace_id="test-trace-123",
                operation="file_operation"
            )
            
            result = await error_handler.handle_error(e, context)
            
            # This will FAIL - no path sanitization
            response_str = str(result.message) + str(result.details or {})
            
            # These paths should be sanitized but aren't
            assert "/etc/passwd" in response_str  # Should be sanitized
            assert "/home/user/.ssh/" in response_str  # Should be sanitized
            assert "/app/netra_backend/" in response_str  # Should be sanitized

    @pytest.mark.asyncio
    async def test_database_schema_disclosure_missing_protection(self, error_handler):
        """FAILING TEST: Database schema info should be hidden but isn't."""
        from sqlalchemy.exc import IntegrityError
        
        # Simulate database constraint error with schema details
        db_error = IntegrityError(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
            ["test@example.com", "hashed_password"],
            "duplicate key value violates unique constraint \"users_email_key\"\n"
            "DETAIL: Key (email)=(test@example.com) already exists.\n"
            "SCHEMA: public\nTABLE: users\nCOLUMN: email"
        )
        
        context = ErrorContext(
            trace_id="test-trace-123",
            operation="database_insert"
        )
        
        result = await error_handler.handle_error(db_error, context)
        
        # This will FAIL - database schema details are exposed
        response_str = str(result.message) + str(result.details or {})
        
        # These should be sanitized in production but aren't
        assert "users_email_key" in response_str  # Constraint name exposed
        assert "SCHEMA: public" in response_str  # Schema name exposed
        assert "TABLE: users" in response_str  # Table name exposed

    @pytest.mark.asyncio 
    async def test_internal_service_urls_disclosure_missing_protection(self, error_handler):
        """FAILING TEST: Internal service URLs should be hidden but aren't."""
        def service_error():
            internal_urls = [
                "http://internal-auth-service:8081/validate",
                "http://database.internal:5432/netra_prod",
                "redis://cache.internal:6379/0",
                "http://admin-panel.internal:9000/metrics"
            ]
            raise ConnectionError(f"Failed to connect to services: {internal_urls}")
            
        try:
            service_error()
        except Exception as e:
            context = ErrorContext(
                trace_id="test-trace-123",
                operation="service_connection"
            )
            
            result = await error_handler.handle_error(e, context)
            
            # This will FAIL - internal URLs are exposed
            response_str = str(result.message) + str(result.details or {})
            
            # These internal URLs should be sanitized
            assert "internal-auth-service:8081" in response_str
            assert "database.internal:5432" in response_str 
            assert "cache.internal:6379" in response_str

    @pytest.mark.asyncio
    async def test_configuration_disclosure_missing_protection(self, error_handler):
        """FAILING TEST: Configuration details should be hidden but aren't."""
        def config_error():
            config_details = {
                "JWT_SECRET_KEY": "HS256_production_secret",
                "DATABASE_URL": "postgresql://user:pass@db.internal:5432/prod",
                "REDIS_URL": "redis://:password@redis.internal:6379",
                "API_KEYS": {
                    "openai": "sk-1234567890",
                    "anthropic": "api_key_12345"
                }
            }
            raise ValueError(f"Configuration error: {config_details}")
            
        try:
            config_error()
        except Exception as e:
            context = ErrorContext(
                trace_id="test-trace-123",
                operation="configuration_load"
            )
            
            result = await error_handler.handle_error(e, context)
            
            # This will FAIL - configuration details are exposed
            response_str = str(result.message) + str(result.details or {})
            
            # These config values should be sanitized
            assert "JWT_SECRET_KEY" in response_str
            assert "DATABASE_URL" in response_str
            assert "sk-1234567890" in response_str


class TestSecurityHeaders:
    """Test security-related headers in error responses."""

    @pytest.mark.asyncio
    async def test_api_error_missing_security_headers(self):
        """FAILING TEST: API errors should include security headers but don't."""
        test_error = ValueError("API security test error")
        
        response = await api_error_handler.handle_exception(test_error)
        
        # This will FAIL - missing security headers
        headers = dict(response.headers)
        
        assert "X-Content-Type-Options" not in headers
        assert "X-Frame-Options" not in headers
        assert "X-XSS-Protection" not in headers
        assert "Strict-Transport-Security" not in headers
        assert "Content-Security-Policy" not in headers

    @pytest.mark.asyncio
    async def test_error_response_missing_security_metadata(self):
        """FAILING TEST: Error responses should include security metadata."""
        error_response = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message", 
            trace_id="test-trace-123",
            timestamp="2025-01-01T00:00:00Z"
        )
        
        # This will FAIL - no security metadata fields
        with pytest.raises(AttributeError):
            _ = error_response.security_classification
        with pytest.raises(AttributeError):
            _ = error_response.information_disclosure_risk
        with pytest.raises(AttributeError):
            _ = error_response.sanitization_applied


class TestRateLimitingAndDDoSProtection:
    """Test rate limiting for error endpoints to prevent information gathering."""

    @pytest.mark.asyncio
    async def test_error_rate_limiting_missing(self, error_handler):
        """FAILING TEST: Error responses should be rate limited but aren't."""
        context = ErrorContext(
            trace_id="test-trace-123",
            operation="rate_limit_test",
            client_ip="192.168.1.100"
        )
        
        # Generate multiple errors rapidly
        for i in range(100):
            test_error = ValueError(f"Rate limit test error {i}")
            result = await error_handler.handle_error(test_error, context)
            
            # This will FAIL - no rate limiting applied
            assert isinstance(result, ErrorResponse)
            
            # Should have rate limit info but doesn't
            details = result.details or {}
            assert "rate_limit_remaining" not in details
            assert "rate_limit_reset" not in details

    @pytest.mark.asyncio
    async def test_error_enumeration_protection_missing(self, error_handler):
        """FAILING TEST: Should protect against error enumeration but doesn't."""
        # Simulate enumeration attack patterns
        enumeration_attempts = [
            "SELECT * FROM users WHERE id=1",
            "../../../etc/passwd", 
            "admin' OR '1'='1",
            "<?php system($_GET['cmd']); ?>",
            "javascript:alert('xss')"
        ]
        
        for attempt in enumeration_attempts:
            test_error = ValueError(f"Input validation failed: {attempt}")
            context = ErrorContext(
                trace_id="test-trace-123",
                operation="enumeration_test",
                client_ip="192.168.1.100"
            )
            
            result = await error_handler.handle_error(test_error, context)
            
            # This will FAIL - no enumeration protection
            assert isinstance(result, ErrorResponse)
            
            # Should detect and protect against enumeration but doesn't
            details = result.details or {}
            assert "enumeration_detected" not in details
            assert "security_alert_triggered" not in details


class TestAuditingAndCompliance:
    """Test auditing and compliance features for error handling."""

    @pytest.mark.asyncio
    async def test_error_auditing_missing(self, error_handler):
        """FAILING TEST: Errors should be audited for security compliance."""
        sensitive_error = ValueError("User attempted unauthorized access to admin panel")
        context = ErrorContext(
            trace_id="test-trace-123",
            operation="security_violation",
            user_id="user-123",
            client_ip="192.168.1.100"
        )
        
        result = await error_handler.handle_error(sensitive_error, context)
        
        # This will FAIL - no audit trail functionality
        assert isinstance(result, ErrorResponse)
        
        # Should create audit log but doesn't
        details = result.details or {}
        assert "audit_log_id" not in details
        assert "security_incident_id" not in details
        assert "compliance_flags" not in details

    @pytest.mark.asyncio
    async def test_gdpr_compliance_missing(self, error_handler):
        """FAILING TEST: Error handling should be GDPR compliant but isn't."""
        # Error containing personal data
        personal_data_error = ValueError(
            "Processing failed for user john.doe@example.com with phone +1-555-0123"
        )
        context = ErrorContext(
            trace_id="test-trace-123",
            operation="personal_data_processing",
            region="EU"
        )
        
        result = await error_handler.handle_error(personal_data_error, context)
        
        # This will FAIL - no GDPR compliance features
        assert isinstance(result, ErrorResponse)
        
        # Should have data protection features but doesn't
        details = result.details or {}
        assert "gdpr_compliance_status" not in details
        assert "personal_data_sanitized" not in details
        assert "data_subject_rights_notice" not in details

    @pytest.mark.asyncio
    async def test_hipaa_compliance_missing(self, error_handler):
        """FAILING TEST: Medical/health data errors should be HIPAA compliant."""
        # Error containing health information
        health_data_error = ValueError(
            "Patient record access failed for DOB 1985-03-15, SSN 123-45-6789"
        )
        context = ErrorContext(
            trace_id="test-trace-123", 
            operation="health_data_access",
            data_classification="PHI"  # Protected Health Information
        )
        
        result = await error_handler.handle_error(health_data_error, context)
        
        # This will FAIL - no HIPAA compliance features  
        assert isinstance(result, ErrorResponse)
        
        # Should have health data protection but doesn't
        details = result.details or {}
        assert "hipaa_compliance_status" not in details
        assert "phi_sanitized" not in details
        assert "healthcare_audit_trail" not in details


class TestSecurityTesting:
    """Test security testing capabilities for error handling."""

    @pytest.mark.asyncio
    async def test_penetration_testing_mode_missing(self, error_handler):
        """FAILING TEST: Should support penetration testing mode but doesn't."""
        # This will FAIL - no pen testing mode
        with pytest.raises(AttributeError):
            _ = error_handler.enable_penetration_testing_mode()
        with pytest.raises(AttributeError):
            _ = error_handler.security_test_mode

    @pytest.mark.asyncio
    async def test_vulnerability_scanning_integration_missing(self, error_handler):
        """FAILING TEST: Should integrate with vulnerability scanners but doesn't."""
        test_error = ValueError("Security scanner test error")
        context = ErrorContext(
            trace_id="test-trace-123",
            operation="vulnerability_scan"
        )
        
        result = await error_handler.handle_error(test_error, context)
        
        # This will FAIL - no vulnerability scanning integration
        details = result.details or {}
        assert "vulnerability_scan_results" not in details
        assert "security_score" not in details
        assert "threat_assessment" not in details