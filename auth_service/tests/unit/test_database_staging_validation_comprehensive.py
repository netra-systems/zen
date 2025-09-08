"""
Comprehensive unit tests for Auth Service Staging Database Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent staging deployment failures due to database configuration issues
- Value Impact: Reduces deployment downtime and debugging time for staging environment
- Strategic Impact: Ensures reliable auth service availability during development cycle

Tests database URL validation, credential validation, SSL compatibility,
staging deployment validation, and pre-deployment checks.
Focuses on configuration validation rather than real database connections.
"""

import pytest
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse

from auth_service.auth_core.database.staging_validation import (
    StagingDatabaseValidator,
    validate_staging_deployment
)
from shared.isolated_environment import get_env


class TestStagingDatabaseValidatorURLFormat:
    """Test database URL format validation"""
    
    @pytest.mark.unit
    def test_validate_empty_url(self):
        """Test validation of empty database URL"""
        result = StagingDatabaseValidator.validate_database_url_format("")
        
        assert result["valid"] is False
        assert "Database URL is empty" in result["error"]
        assert "Set POSTGRES_* environment variables" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_none_url(self):
        """Test validation of None database URL"""
        result = StagingDatabaseValidator.validate_database_url_format(None)
        
        assert result["valid"] is False
        assert "Database URL is empty" in result["error"]
    
    @pytest.mark.unit
    def test_validate_invalid_scheme(self):
        """Test validation of invalid URL scheme"""
        invalid_url = "mysql://user:pass@host:5432/db"
        result = StagingDatabaseValidator.validate_database_url_format(invalid_url)
        
        assert result["valid"] is False
        assert "Invalid scheme: mysql" in result["error"]
        assert "Use postgresql:// or postgres:// scheme" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_postgresql_scheme(self):
        """Test validation of postgresql:// scheme"""
        valid_url = "postgresql://user:pass@host:5432/db"
        result = StagingDatabaseValidator.validate_database_url_format(valid_url)
        
        assert result["valid"] is True
        assert result["url_type"] == "tcp"
    
    @pytest.mark.unit
    def test_validate_postgres_scheme(self):
        """Test validation of postgres:// scheme"""
        valid_url = "postgres://user:pass@host:5432/db"
        result = StagingDatabaseValidator.validate_database_url_format(valid_url)
        
        assert result["valid"] is True
        assert result["url_type"] == "tcp"
    
    @pytest.mark.unit
    def test_validate_cloud_sql_url(self):
        """Test validation of Cloud SQL URL format"""
        cloud_sql_url = "postgresql://user:pass@/cloudsql/project:region:instance/db"
        result = StagingDatabaseValidator.validate_database_url_format(cloud_sql_url)
        
        assert result["valid"] is True
        assert result["url_type"] == "cloud_sql"
        assert result["ssl_handling"] == "none_needed"
    
    @pytest.mark.unit
    def test_validate_cloud_sql_url_with_ssl_params(self):
        """Test Cloud SQL URL with SSL parameters (should warn)"""
        cloud_sql_url = "postgresql://user:pass@/cloudsql/project:region:instance/db?sslmode=require"
        result = StagingDatabaseValidator.validate_database_url_format(cloud_sql_url)
        
        assert result["valid"] is True
        assert result["url_type"] == "cloud_sql"
        assert result["ssl_handling"] == "auto_remove"
        assert "SSL parameters found in Cloud SQL URL" in result["warnings"]
        assert "SSL parameters will be automatically removed" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_tcp_url_with_sslmode(self):
        """Test TCP URL with sslmode parameter"""
        tcp_url = "postgresql://user:pass@host:5432/db?sslmode=require"
        result = StagingDatabaseValidator.validate_database_url_format(tcp_url)
        
        assert result["valid"] is True
        assert result["url_type"] == "tcp"
        assert result["ssl_handling"] == "convert_to_ssl"
        assert "sslmode will be converted to ssl" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_tcp_url_with_ssl_param(self):
        """Test TCP URL with ssl parameter"""
        tcp_url = "postgresql://user:pass@host:5432/db?ssl=require"
        result = StagingDatabaseValidator.validate_database_url_format(tcp_url)
        
        assert result["valid"] is True
        assert result["url_type"] == "tcp"
        assert result["ssl_handling"] == "compatible"
    
    @pytest.mark.unit
    def test_validate_tcp_url_no_ssl(self):
        """Test TCP URL without SSL parameters"""
        tcp_url = "postgresql://user:pass@host:5432/db"
        result = StagingDatabaseValidator.validate_database_url_format(tcp_url)
        
        assert result["valid"] is True
        assert result["url_type"] == "tcp"
        assert result["ssl_handling"] == "none_specified"
        assert "No SSL parameters specified" in result["warnings"]
        assert "Consider adding ssl=require" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_localhost_warning(self):
        """Test warning for localhost in staging"""
        localhost_url = "postgresql://user:pass@localhost:5432/db"
        result = StagingDatabaseValidator.validate_database_url_format(localhost_url)
        
        assert result["valid"] is True
        assert "Using localhost in staging URL" in result["warnings"]
        assert "Use actual staging database hostname" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_no_port_warning(self):
        """Test warning for missing port"""
        no_port_url = "postgresql://user:pass@host/db"
        result = StagingDatabaseValidator.validate_database_url_format(no_port_url)
        
        assert result["valid"] is True
        assert "Port not specified" in result["warnings"]
        assert "Explicitly specify port" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_no_hostname(self):
        """Test validation failure for no hostname"""
        no_host_url = "postgresql://user:pass@:5432/db"
        result = StagingDatabaseValidator.validate_database_url_format(no_host_url)
        
        assert result["valid"] is False
        assert "No hostname or Cloud SQL path found" in result["error"]
    
    @pytest.mark.unit
    def test_validate_malformed_cloud_sql_path(self):
        """Test warning for malformed Cloud SQL path"""
        malformed_url = "postgresql://user:pass@/cloudsql/invalid-path/db"
        result = StagingDatabaseValidator.validate_database_url_format(malformed_url)
        
        assert result["valid"] is True
        assert "Cloud SQL path format may be incorrect" in result["warnings"]
        assert "Expected format: /cloudsql/project:region:instance" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_cloud_sql_missing_db_name(self):
        """Test warning for missing database name in Cloud SQL URL"""
        missing_db_url = "postgresql://user:pass@/cloudsql/project:region:instance/?param=value"
        result = StagingDatabaseValidator.validate_database_url_format(missing_db_url)
        
        assert result["valid"] is True
        assert "Database name not specified" in result["warnings"]
        assert "Specify database name after @/" in result["recommendations"]


class TestStagingDatabaseValidatorCredentials:
    """Test credential validation functionality"""
    
    @pytest.mark.unit
    def test_validate_credentials_no_username(self):
        """Test validation with no username"""
        url = "postgresql://:password@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "No username specified" in result["credential_issues"]
        assert "Specify username in URL" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_no_password(self):
        """Test validation with no password"""
        url = "postgresql://user@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "No password specified" in result["credential_issues"]
        assert "Specify password in URL" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_problematic_username_pattern(self):
        """Test validation with problematic username pattern"""
        url = "postgresql://user_pr-4:password@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "Invalid username pattern 'user_pr-4'" in result["credential_issues"]
        assert "Use correct username - should be 'postgres'" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_pr_pattern_username(self):
        """Test validation with PR-pattern username"""
        url = "postgresql://user_pr-123:password@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "appears to be misconfigured PR-specific user" in result["credential_issues"]
    
    @pytest.mark.unit
    def test_validate_credentials_postgres_username(self):
        """Test validation with postgres username (acceptable)"""
        url = "postgresql://postgres:securepassword@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is True
        assert "Using common username 'postgres'" in result["warnings"]
        assert "Username 'postgres' is acceptable for Cloud SQL" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_root_username(self):
        """Test validation with root username (warning)"""
        url = "postgresql://root:password@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is True
        assert "Using common username 'root'" in result["warnings"]
        assert "Consider using service-specific username" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_insecure_password(self):
        """Test validation with insecure password"""
        url = "postgresql://user:password@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "Using insecure default password" in result["credential_issues"]
        assert "Use secure password" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_short_password(self):
        """Test validation with short password"""
        url = "postgresql://user:pass123@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "Password is shorter than 8 characters" in result["credential_issues"]
        assert "Use password with at least 8 characters" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_numeric_password(self):
        """Test validation with numeric-only password"""
        url = "postgresql://user:123456@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "Password contains only numbers" in result["credential_issues"]
        assert "Use complex password with letters, numbers, and symbols" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_test_password(self):
        """Test validation with test password"""
        url = "postgresql://user:test_password@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "appears to be a test/development password" in result["credential_issues"]
        assert "Use secure production password for staging" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_placeholder_password(self):
        """Test validation with placeholder password"""
        url = "postgresql://user:REPLACE_WITH_SECURE_PASSWORD@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "Password contains placeholder text" in result["credential_issues"]
        assert "Replace placeholder with actual secure password" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_variable_placeholder(self):
        """Test validation with variable placeholder"""
        url = "postgresql://user:${DATABASE_PASSWORD}@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is False
        assert "Password contains placeholder text" in result["credential_issues"]
    
    @pytest.mark.unit
    def test_validate_credentials_staging_specific_checks(self):
        """Test staging-specific credential validation"""
        url = "postgresql://dev_user:devpassword@staging-host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert "Username appears to be development-specific" in result["warnings"]
        assert "Password contains 'dev' which may indicate development" in result["warnings"]
        assert "Verify username is correct for staging" in result["recommendations"]
        assert "Ensure password is staging-appropriate" in result["recommendations"]
    
    @pytest.mark.unit
    def test_validate_credentials_secure_example(self):
        """Test validation with secure credentials"""
        url = "postgresql://staging_user:SecureP@ssw0rd123!@host:5432/db"
        result = StagingDatabaseValidator.validate_credentials_format(url)
        
        assert result["valid"] is True
        # Should have minimal or no warnings for secure credentials
    
    @pytest.mark.unit
    def test_validate_credentials_parsing_error(self):
        """Test credential validation with malformed URL"""
        malformed_url = "not-a-valid-url"
        result = StagingDatabaseValidator.validate_credentials_format(malformed_url)
        
        assert result["valid"] is False
        assert "Credential validation failed" in result["error"]


class TestStagingDatabaseValidatorSSLCompatibility:
    """Test SSL compatibility validation"""
    
    @pytest.mark.unit
    def test_ssl_compatibility_cloud_sql_with_ssl_params(self):
        """Test SSL compatibility for Cloud SQL with SSL parameters"""
        cloud_sql_url = "postgresql://user:pass@/cloudsql/project:region:instance/db?sslmode=require&ssl=true"
        result = StagingDatabaseValidator._validate_ssl_compatibility(cloud_sql_url)
        
        assert result["valid"] is True
        assert "SSL parameters correctly handled for Cloud SQL" in result["recommendations"]
    
    @pytest.mark.unit
    def test_ssl_compatibility_cloud_sql_ssl_not_removed(self):
        """Test SSL compatibility when SSL parameters not properly removed for Cloud SQL"""
        # Mock the conversion to simulate improper removal
        with patch('re.sub', side_effect=lambda pattern, repl, string: string):
            cloud_sql_url = "postgresql://user:pass@/cloudsql/project:region:instance/db?sslmode=require"
            result = StagingDatabaseValidator._validate_ssl_compatibility(cloud_sql_url)
            
            assert result["valid"] is False
            assert "SSL parameters not properly removed for Cloud SQL" in result["error"]
    
    @pytest.mark.unit
    def test_ssl_compatibility_tcp_sslmode_conversion(self):
        """Test SSL compatibility for TCP connections with sslmode parameter"""
        tcp_url = "postgresql://user:pass@host:5432/db?sslmode=require"
        result = StagingDatabaseValidator._validate_ssl_compatibility(tcp_url)
        
        assert result["valid"] is True
        assert "SSL parameters compatible with asyncpg" in result["recommendations"]
    
    @pytest.mark.unit
    def test_ssl_compatibility_tcp_sslmode_not_converted(self):
        """Test SSL compatibility when sslmode not properly converted"""
        # Test case where conversion fails
        tcp_url = "postgresql://user:pass@host:5432/db?sslmode=require"
        
        # Mock replace to simulate failed conversion
        with patch('str.replace', return_value=tcp_url):
            result = StagingDatabaseValidator._validate_ssl_compatibility(tcp_url)
            
            assert result["valid"] is False
            assert "sslmode parameter not converted to ssl for asyncpg" in result["error"]
    
    @pytest.mark.unit
    def test_ssl_compatibility_tcp_with_ssl_param(self):
        """Test SSL compatibility for TCP connections with ssl parameter"""
        tcp_url = "postgresql://user:pass@host:5432/db?ssl=require"
        result = StagingDatabaseValidator._validate_ssl_compatibility(tcp_url)
        
        assert result["valid"] is True
        assert "SSL parameters compatible with asyncpg" in result["recommendations"]
    
    @pytest.mark.unit
    def test_ssl_compatibility_error_handling(self):
        """Test SSL compatibility error handling"""
        with patch('re.sub', side_effect=Exception("Regex error")):
            url = "postgresql://user:pass@host:5432/db"
            result = StagingDatabaseValidator._validate_ssl_compatibility(url)
            
            assert result["valid"] is False
            assert "SSL compatibility check failed: Regex error" in result["error"]


class TestStagingDatabaseValidatorPreDeployment:
    """Test pre-deployment validation functionality"""
    
    @pytest.mark.unit
    def test_pre_deployment_validation_with_url(self):
        """Test pre-deployment validation with provided URL"""
        test_url = "postgresql://user:SecurePassword123@host:5432/db"
        report = StagingDatabaseValidator.pre_deployment_validation(test_url)
        
        assert "overall_status" in report
        assert "database_url" in report
        assert "validations" in report
        assert "critical_issues" in report
        assert "warnings" in report
        assert "recommendations" in report
        
        # Should contain all validation categories
        assert "url_format" in report["validations"]
        assert "credentials" in report["validations"]
        assert "ssl_compatibility" in report["validations"]
    
    @pytest.mark.unit
    def test_pre_deployment_validation_without_url(self):
        """Test pre-deployment validation without provided URL (builds from env)"""
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.get_url_for_environment.return_value = "postgresql://env_user:env_pass@env_host:5432/env_db"
            mock_builder_class.return_value = mock_builder
            
            with patch.object(get_env(), 'as_dict', return_value={}):
                report = StagingDatabaseValidator.pre_deployment_validation()
                
                assert report is not None
                assert "overall_status" in report
                assert report["database_url"] == "postgresql://env_user:env_pass@env_host:5432/env_db"
    
    @pytest.mark.unit
    def test_pre_deployment_validation_url_format_failure(self):
        """Test pre-deployment validation with URL format failure"""
        invalid_url = "mysql://user:pass@host:3306/db"
        report = StagingDatabaseValidator.pre_deployment_validation(invalid_url)
        
        assert report["overall_status"] == "failed"
        assert len(report["critical_issues"]) > 0
        assert any("URL format" in issue for issue in report["critical_issues"])
    
    @pytest.mark.unit
    def test_pre_deployment_validation_credential_failure(self):
        """Test pre-deployment validation with credential failure"""
        insecure_url = "postgresql://user:password@host:5432/db"
        report = StagingDatabaseValidator.pre_deployment_validation(insecure_url)
        
        assert report["overall_status"] == "failed"
        assert len(report["critical_issues"]) > 0
        assert any("insecure default password" in issue for issue in report["critical_issues"])
    
    @pytest.mark.unit
    def test_pre_deployment_validation_ssl_failure(self):
        """Test pre-deployment validation with SSL compatibility failure"""
        # Mock SSL validation to return failure
        with patch.object(StagingDatabaseValidator, '_validate_ssl_compatibility') as mock_ssl:
            mock_ssl.return_value = {
                "valid": False,
                "error": "SSL compatibility issue"
            }
            
            test_url = "postgresql://user:SecurePassword123@host:5432/db"
            report = StagingDatabaseValidator.pre_deployment_validation(test_url)
            
            assert report["overall_status"] == "failed"
            assert len(report["critical_issues"]) > 0
            assert any("SSL compatibility issue" in issue for issue in report["critical_issues"])
    
    @pytest.mark.unit
    def test_pre_deployment_validation_warnings_only(self):
        """Test pre-deployment validation with warnings but no critical issues"""
        warning_url = "postgresql://postgres:SecurePassword123@localhost:5432/db"
        report = StagingDatabaseValidator.pre_deployment_validation(warning_url)
        
        # Should have warnings status (not failed) due to localhost
        assert report["overall_status"] == "warning"
        assert len(report["warnings"]) > 0
        assert len(report["critical_issues"]) == 0
    
    @pytest.mark.unit
    def test_pre_deployment_validation_success(self):
        """Test pre-deployment validation with no issues"""
        secure_url = "postgresql://staging_user:SecureP@ssw0rd123!@staging-host:5432/staging_db?ssl=require"
        report = StagingDatabaseValidator.pre_deployment_validation(secure_url)
        
        # Should pass or have minimal warnings
        assert report["overall_status"] in ["passed", "warning"]
        assert len(report["critical_issues"]) == 0
    
    @pytest.mark.unit
    def test_pre_deployment_validation_long_url_truncation(self):
        """Test that long URLs are properly truncated in report"""
        very_long_password = "a" * 100
        long_url = f"postgresql://user:{very_long_password}@host:5432/db"
        report = StagingDatabaseValidator.pre_deployment_validation(long_url)
        
        # URL should be truncated in report
        assert len(report["database_url"]) <= 53  # 50 + "..."


class TestStagingDatabaseValidatorReporting:
    """Test validation report printing and formatting"""
    
    @pytest.mark.unit
    def test_print_validation_report_passed(self, capsys):
        """Test printing validation report for passed validation"""
        report = {
            "overall_status": "passed",
            "database_url": "postgresql://user:***@host:5432/db",
            "critical_issues": [],
            "warnings": [],
            "recommendations": ["Use secure connection"]
        }
        
        StagingDatabaseValidator.print_validation_report(report)
        
        captured = capsys.readouterr()
        assert "PASS PASSED" in captured.out
        assert "Recommendations (1):" in captured.out
        assert "Use secure connection" in captured.out
    
    @pytest.mark.unit
    def test_print_validation_report_failed(self, capsys):
        """Test printing validation report for failed validation"""
        report = {
            "overall_status": "failed",
            "database_url": "postgresql://user:***@host:5432/db",
            "critical_issues": ["Invalid credentials", "SSL configuration error"],
            "warnings": ["Minor warning"],
            "recommendations": ["Fix credentials", "Configure SSL"]
        }
        
        StagingDatabaseValidator.print_validation_report(report)
        
        captured = capsys.readouterr()
        assert "FAIL FAILED" in captured.out
        assert "Critical Issues (2):" in captured.out
        assert "Invalid credentials" in captured.out
        assert "SSL configuration error" in captured.out
        assert "Warnings (1):" in captured.out
        assert "Minor warning" in captured.out
        assert "Recommendations (2):" in captured.out
    
    @pytest.mark.unit
    def test_print_validation_report_warning(self, capsys):
        """Test printing validation report for warning status"""
        report = {
            "overall_status": "warning",
            "database_url": "postgresql://user:***@localhost:5432/db",
            "critical_issues": [],
            "warnings": ["Using localhost in staging"],
            "recommendations": ["Use staging hostname"]
        }
        
        StagingDatabaseValidator.print_validation_report(report)
        
        captured = capsys.readouterr()
        assert "WARN WARNING" in captured.out
        assert "Warnings (1):" in captured.out
        assert "Using localhost in staging" in captured.out
    
    @pytest.mark.unit
    def test_print_validation_report_unknown_status(self, capsys):
        """Test printing validation report for unknown status"""
        report = {
            "overall_status": "unknown",
            "database_url": "postgresql://user:***@host:5432/db",
            "critical_issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        StagingDatabaseValidator.print_validation_report(report)
        
        captured = capsys.readouterr()
        assert "UNKNOWN UNKNOWN" in captured.out


class TestValidateStagingDeploymentFunction:
    """Test the main validate_staging_deployment function"""
    
    @pytest.mark.unit
    def test_validate_staging_deployment_success(self, capsys):
        """Test validate_staging_deployment with successful validation"""
        with patch.object(StagingDatabaseValidator, 'pre_deployment_validation') as mock_validation:
            mock_validation.return_value = {
                "overall_status": "passed",
                "database_url": "postgresql://secure_url",
                "critical_issues": [],
                "warnings": [],
                "recommendations": []
            }
            
            result = validate_staging_deployment()
            
            assert result is True
            captured = capsys.readouterr()
            assert "Validating Auth Service for Staging Deployment" in captured.out
            assert "Validation passed" in captured.out
    
    @pytest.mark.unit
    def test_validate_staging_deployment_warning(self, capsys):
        """Test validate_staging_deployment with warnings (should still pass)"""
        with patch.object(StagingDatabaseValidator, 'pre_deployment_validation') as mock_validation:
            mock_validation.return_value = {
                "overall_status": "warning",
                "database_url": "postgresql://localhost_url",
                "critical_issues": [],
                "warnings": ["Using localhost"],
                "recommendations": []
            }
            
            result = validate_staging_deployment()
            
            assert result is True
            captured = capsys.readouterr()
            assert "Validation passed" in captured.out
    
    @pytest.mark.unit
    def test_validate_staging_deployment_failure(self, capsys):
        """Test validate_staging_deployment with failure"""
        with patch.object(StagingDatabaseValidator, 'pre_deployment_validation') as mock_validation:
            mock_validation.return_value = {
                "overall_status": "failed",
                "database_url": "invalid_url",
                "critical_issues": ["Invalid configuration"],
                "warnings": [],
                "recommendations": []
            }
            
            result = validate_staging_deployment()
            
            assert result is False
            # Note: The function prints but doesn't capture in this test context


class TestStagingDatabaseValidatorEdgeCases:
    """Test edge cases and error scenarios"""
    
    @pytest.mark.unit
    def test_url_format_validation_exception(self):
        """Test URL format validation with exception"""
        with patch('urllib.parse.urlparse', side_effect=Exception("Parse error")):
            result = StagingDatabaseValidator.validate_database_url_format("test_url")
            
            assert result["valid"] is False
            assert "URL parsing failed: Parse error" in result["error"]
    
    @pytest.mark.unit
    def test_credential_validation_exception(self):
        """Test credential validation with exception"""
        with patch('urllib.parse.urlparse', side_effect=Exception("Parse error")):
            result = StagingDatabaseValidator.validate_credentials_format("test_url")
            
            assert result["valid"] is False
            assert "Credential validation failed: Parse error" in result["error"]
    
    @pytest.mark.unit
    def test_cloud_sql_database_name_extraction_edge_cases(self):
        """Test Cloud SQL database name extraction edge cases"""
        # URL without query parameters
        url1 = "postgresql://user:pass@/cloudsql/project:region:instance/database"
        result1 = StagingDatabaseValidator.validate_database_url_format(url1)
        assert result1["valid"] is True
        
        # URL with empty database name but query params
        url2 = "postgresql://user:pass@/cloudsql/project:region:instance/?param=value"
        result2 = StagingDatabaseValidator.validate_database_url_format(url2)
        assert "Database name not specified" in result2["warnings"]
        
        # URL with database name and query params
        url3 = "postgresql://user:pass@/cloudsql/project:region:instance/database?param=value"
        result3 = StagingDatabaseValidator.validate_database_url_format(url3)
        assert result3["valid"] is True
    
    @pytest.mark.unit
    def test_regex_patterns_comprehensive(self):
        """Test various regex patterns used in validation"""
        # Test placeholder patterns
        placeholder_passwords = [
            "$(DATABASE_PASSWORD)",
            "${DB_PASS}",
            "REPLACE_WITH_SECRET",
            "your-secure-password",
            "CHANGE_ME_NOW",
            "TODO_SET_PASSWORD",
            "PLACEHOLDER_PASSWORD",
            "EXAMPLE_PASSWORD"
        ]
        
        for placeholder in placeholder_passwords:
            url = f"postgresql://user:{placeholder}@host:5432/db"
            result = StagingDatabaseValidator.validate_credentials_format(url)
            assert result["valid"] is False
            assert "Password contains placeholder text" in result["credential_issues"]
    
    @pytest.mark.unit
    def test_environment_specific_validation_branches(self):
        """Test environment-specific validation logic branches"""
        # Test non-staging URL (should skip staging-specific checks)
        dev_url = "postgresql://dev_user:devpass@dev-host:5432/dev_db"
        result = StagingDatabaseValidator.validate_credentials_format(dev_url)
        
        # Should not have staging-specific warnings since "staging" not in URL
        staging_warnings = [w for w in result.get("warnings", []) if "staging" in w.lower()]
        assert len(staging_warnings) == 0
    
    @pytest.mark.unit
    def test_password_security_checks_comprehensive(self):
        """Test comprehensive password security validation"""
        test_cases = [
            ("admin123", False, "insecure default"),
            ("test", False, "insecure default"),
            ("12345678", False, "only numbers"),  # 8 chars but all numeric
            ("123456789012", True, None),  # 12 chars numeric - should pass
            ("Short7!", False, "shorter than 8"),
            ("SecurePassword123!", True, None),  # Should pass
            ("contains_wrong_password", False, "test/development password"),
        ]
        
        for password, should_pass, expected_issue in test_cases:
            url = f"postgresql://user:{password}@host:5432/db"
            result = StagingDatabaseValidator.validate_credentials_format(url)
            
            if should_pass:
                assert result["valid"] is True, f"Password '{password}' should pass but failed"
            else:
                assert result["valid"] is False, f"Password '{password}' should fail but passed"
                assert any(expected_issue in issue.lower() for issue in result["credential_issues"]), \
                    f"Expected issue '{expected_issue}' not found for password '{password}'"


class TestMainModuleBehavior:
    """Test behavior when module is run as main"""
    
    @pytest.mark.unit
    def test_main_module_success(self):
        """Test main module behavior with successful validation"""
        with patch('auth_service.auth_core.database.staging_validation.validate_staging_deployment') as mock_validate:
            mock_validate.return_value = True
            
            with patch('sys.exit') as mock_exit:
                # Simulate running as main module
                exec(open('auth_service/auth_core/database/staging_validation.py').read().split('if __name__ == "__main__":')[1])
                
                mock_exit.assert_called_with(0)
    
    @pytest.mark.unit
    def test_main_module_failure(self):
        """Test main module behavior with failed validation"""
        with patch('auth_service.auth_core.database.staging_validation.validate_staging_deployment') as mock_validate:
            mock_validate.return_value = False
            
            with patch('sys.exit') as mock_exit:
                # Simulate running as main module
                try:
                    exec(open('auth_service/auth_core/database/staging_validation.py').read().split('if __name__ == "__main__":')[1])
                except SystemExit:
                    pass
                
                mock_exit.assert_called_with(1)