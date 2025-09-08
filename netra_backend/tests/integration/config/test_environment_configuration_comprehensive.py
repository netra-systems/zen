"""
Test Environment Configuration Comprehensive - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Configuration reliability and environment stability
- Value Impact: Prevents configuration-related outages and security breaches
- Strategic Impact: Foundation for reliable multi-environment deployments

CRITICAL REQUIREMENTS:
- Tests real environment configuration loading
- Validates configuration isolation between environments
- Ensures sensitive data protection
- No mocks - uses real IsolatedEnvironment system
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
from contextlib import contextmanager

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from test_framework.ssot.configuration_validator import ConfigurationValidator
from shared.isolated_environment import IsolatedEnvironment, get_env
from shared.database_url_builder import DatabaseURLBuilder
from shared.jwt_secret_manager import get_unified_jwt_secret
from shared.config_change_tracker import ConfigChangeTracker


class TestEnvironmentConfigurationComprehensive(SSotBaseTestCase):
    """
    Comprehensive environment configuration tests.
    
    Tests critical configuration management that ensures business continuity:
    - Environment isolation and variable loading
    - Configuration validation and consistency
    - Sensitive data handling and security
    - Multi-environment deployment scenarios
    - Configuration drift detection
    """
    
    def __init__(self):
        """Initialize environment configuration test suite."""
        super().__init__()
        self.isolated_helper = IsolatedTestHelper()
        self.config_validator = ConfigurationValidator()
        
        # Test configuration
        self.test_env_prefix = f"test_{uuid.uuid4().hex[:8]}"
        self.original_env_vars = {}
        
    def setup_test_isolation(self):
        """Set up isolated environment for testing."""
        # Store original environment variables
        self.original_env_vars = dict(os.environ)
        
        # Create isolated test environment
        test_env = IsolatedEnvironment()
        test_env.set("TEST_MODE", "true", source="test_setup")
        test_env.set("ENVIRONMENT", "test", source="test_setup")
        
        return test_env
    
    def teardown_test_isolation(self):
        """Clean up environment isolation."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env_vars)
    
    @contextmanager
    def temporary_env_file(self, env_vars: Dict[str, str]):
        """Create temporary environment file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
            temp_path = f.name
        
        try:
            yield temp_path
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_environment_variable_loading_and_isolation(self):
        """
        Test environment variable loading with proper isolation.
        
        BUSINESS CRITICAL: Environment misconfiguration causes service outages.
        Must ensure each environment loads correct configuration.
        """
        # Test environment isolation
        test_env1 = self.setup_test_isolation()
        
        try:
            # Test basic environment variable loading
            test_env1.set("DATABASE_URL", "postgresql://test1:password@localhost:5432/test1", source="test")
            test_env1.set("REDIS_URL", "redis://localhost:6379/1", source="test")
            test_env1.set("SERVICE_SECRET", "test_secret_123", source="test")
            test_env1.set("DEBUG_MODE", "true", source="test")
            
            # Validate variables are loaded correctly
            assert test_env1.get("DATABASE_URL") == "postgresql://test1:password@localhost:5432/test1"
            assert test_env1.get("REDIS_URL") == "redis://localhost:6379/1"
            assert test_env1.get("SERVICE_SECRET") == "test_secret_123"
            assert test_env1.get("DEBUG_MODE") == "true"
            
            # Test environment isolation with second environment
            test_env2 = IsolatedEnvironment()
            test_env2.set("DATABASE_URL", "postgresql://test2:password@localhost:5432/test2", source="test")
            test_env2.set("REDIS_URL", "redis://localhost:6379/2", source="test")
            test_env2.set("SERVICE_SECRET", "different_secret_456", source="test")
            test_env2.set("DEBUG_MODE", "false", source="test")
            
            # Validate isolation - each environment has different values
            assert test_env1.get("DATABASE_URL") != test_env2.get("DATABASE_URL")
            assert test_env1.get("REDIS_URL") != test_env2.get("REDIS_URL")
            assert test_env1.get("SERVICE_SECRET") != test_env2.get("SERVICE_SECRET")
            assert test_env1.get("DEBUG_MODE") != test_env2.get("DEBUG_MODE")
            
            # Test environment hierarchy and precedence
            test_env1.set("OVERRIDE_TEST", "base_value", source="env_file")
            test_env1.set("OVERRIDE_TEST", "override_value", source="environment")
            
            # Environment variables should take precedence
            assert test_env1.get("OVERRIDE_TEST") == "override_value"
            
            # Test required variable validation
            required_vars = ["DATABASE_URL", "SERVICE_SECRET"]
            validation_result = test_env1.validate_required_variables(required_vars)
            
            assert validation_result.is_valid, f"Required variable validation failed: {validation_result.missing_variables}"
            assert len(validation_result.missing_variables) == 0
            
            # Test missing required variable detection
            test_env3 = IsolatedEnvironment()
            test_env3.set("DATABASE_URL", "postgresql://test3:password@localhost:5432/test3", source="test")
            # Missing SERVICE_SECRET
            
            missing_validation = test_env3.validate_required_variables(required_vars)
            assert not missing_validation.is_valid
            assert "SERVICE_SECRET" in missing_validation.missing_variables
            
            # Test sensitive variable masking
            env_dict = test_env1.as_dict(mask_sensitive=True)
            assert "SERVICE_SECRET" in env_dict
            assert env_dict["SERVICE_SECRET"] == "***MASKED***"
            assert "DATABASE_URL" in env_dict
            assert "password" not in env_dict["DATABASE_URL"]  # Should be masked
            
        finally:
            self.teardown_test_isolation()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_database_url_configuration_validation(self):
        """
        Test database URL configuration and validation.
        
        BUSINESS CRITICAL: Database connection failures cause complete service outage.
        Must validate database URLs for all supported environments.
        """
        test_env = self.setup_test_isolation()
        
        try:
            # Test local development configuration
            test_env.set("POSTGRES_HOST", "localhost", source="test")
            test_env.set("POSTGRES_PORT", "5432", source="test")
            test_env.set("POSTGRES_USER", "dev_user", source="test")
            test_env.set("POSTGRES_PASSWORD", "dev_password", source="test")
            test_env.set("POSTGRES_DB", "dev_database", source="test")
            
            url_builder = DatabaseURLBuilder(test_env.as_dict())
            
            # Validate local configuration builds correctly
            local_url = url_builder.build_database_url()
            expected_local = "postgresql://dev_user:dev_password@localhost:5432/dev_database"
            assert local_url == expected_local, f"Local URL incorrect: {local_url}"
            
            # Test Cloud SQL configuration (staging/production)
            test_env.set("CLOUD_SQL_CONNECTION_NAME", "project:region:instance", source="test")
            test_env.set("CLOUD_SQL_USER", "cloud_user", source="test")
            test_env.set("CLOUD_SQL_PASSWORD", "cloud_password", source="test")  
            test_env.set("CLOUD_SQL_DATABASE", "cloud_database", source="test")
            
            # Rebuild with Cloud SQL config
            cloud_builder = DatabaseURLBuilder(test_env.as_dict())
            cloud_url = cloud_builder.build_database_url()
            
            # Cloud SQL URL should be different format
            assert "cloud_user" in cloud_url
            assert "cloud_database" in cloud_url
            assert cloud_url != local_url
            
            # Test TCP configuration validation
            test_env.set("POSTGRES_HOST", "staging-postgres.example.com", source="test")
            test_env.set("POSTGRES_PORT", "5432", source="test")
            test_env.set("POSTGRES_SSL_MODE", "require", source="test")
            
            tcp_builder = DatabaseURLBuilder(test_env.as_dict())
            tcp_url = tcp_builder.build_database_url()
            
            assert "staging-postgres.example.com" in tcp_url
            assert "sslmode=require" in tcp_url
            
            # Test configuration validation
            validation_result = tcp_builder.validate()
            assert validation_result[0], f"Configuration validation failed: {validation_result[1]}"
            
            # Test invalid configuration detection
            invalid_env = IsolatedEnvironment()
            invalid_env.set("POSTGRES_HOST", "", source="test")  # Empty host
            invalid_env.set("POSTGRES_PORT", "invalid_port", source="test")  # Invalid port
            
            invalid_builder = DatabaseURLBuilder(invalid_env.as_dict())
            invalid_validation = invalid_builder.validate()
            
            assert not invalid_validation[0], "Invalid configuration should fail validation"
            assert "host" in invalid_validation[1].lower() or "port" in invalid_validation[1].lower()
            
        finally:
            self.teardown_test_isolation()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_jwt_secret_configuration_consistency(self):
        """
        Test JWT secret configuration consistency across services.
        
        BUSINESS CRITICAL: JWT secret inconsistency causes authentication failures.
        All services must use the same JWT secret for user authentication.
        """
        test_env = self.setup_test_isolation()
        
        try:
            # Test unified JWT secret management
            test_env.set("JWT_SECRET_KEY", "test_jwt_secret_key_32_characters_long", source="test")
            test_env.set("ENVIRONMENT", "test", source="test")
            
            # Test JWT secret retrieval consistency
            secret1 = test_env.get("JWT_SECRET_KEY")
            assert secret1 == "test_jwt_secret_key_32_characters_long"
            
            # Test different environment secret isolation
            staging_env = IsolatedEnvironment()
            staging_env.set("JWT_SECRET_KEY", "staging_jwt_secret_different_key", source="staging")
            staging_env.set("ENVIRONMENT", "staging", source="staging")
            
            staging_secret = staging_env.get("JWT_SECRET_KEY")
            assert staging_secret == "staging_jwt_secret_different_key"
            assert staging_secret != secret1  # Environments should have different secrets
            
            # Test JWT secret validation
            from shared.jwt_secret_validator import JWTSecretValidator
            
            validator = JWTSecretValidator()
            
            # Test valid secret
            valid_result = validator.validate_secret(secret1)
            assert valid_result.is_valid, f"Valid JWT secret rejected: {valid_result.error_message}"
            
            # Test invalid secrets
            invalid_secrets = [
                "",  # Empty
                "short",  # Too short
                "a" * 10,  # Too short
            ]
            
            for invalid_secret in invalid_secrets:
                invalid_result = validator.validate_secret(invalid_secret)
                assert not invalid_result.is_valid, f"Invalid secret accepted: '{invalid_secret}'"
            
            # Test JWT secret consistency check
            from shared.jwt_secret_consistency_validator import JWTSecretConsistencyValidator
            
            consistency_validator = JWTSecretConsistencyValidator()
            
            # Mock service configuration for consistency check
            service_configs = {
                "backend": {"JWT_SECRET_KEY": secret1},
                "auth_service": {"JWT_SECRET_KEY": secret1}, 
                "frontend": {"JWT_SECRET_KEY": secret1}
            }
            
            consistency_result = consistency_validator.validate_consistency(service_configs)
            assert consistency_result.is_consistent, \
                f"Consistent secrets marked as inconsistent: {consistency_result.inconsistencies}"
            
            # Test inconsistent secrets detection
            inconsistent_configs = {
                "backend": {"JWT_SECRET_KEY": secret1},
                "auth_service": {"JWT_SECRET_KEY": "different_secret_causing_auth_failures"},
                "frontend": {"JWT_SECRET_KEY": secret1}
            }
            
            inconsistent_result = consistency_validator.validate_consistency(inconsistent_configs)
            assert not inconsistent_result.is_consistent, "Inconsistent secrets not detected"
            assert "auth_service" in str(inconsistent_result.inconsistencies)
            
        finally:
            self.teardown_test_isolation()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_configuration_change_tracking_and_drift_detection(self):
        """
        Test configuration change tracking and drift detection.
        
        BUSINESS CRITICAL: Configuration drift causes unexpected behavior.
        Must track changes and detect dangerous configuration drift.
        """
        test_env = self.setup_test_isolation()
        
        try:
            # Set up initial configuration state
            initial_config = {
                "DATABASE_URL": "postgresql://localhost:5432/initial_db",
                "REDIS_URL": "redis://localhost:6379/0",
                "JWT_SECRET_KEY": "initial_secret_key_32_chars_long",
                "DEBUG_MODE": "false",
                "SERVICE_TIMEOUT": "30"
            }
            
            for key, value in initial_config.items():
                test_env.set(key, value, source="initial")
            
            # Initialize change tracker
            change_tracker = ConfigChangeTracker()
            baseline = change_tracker.create_baseline(test_env.as_dict())
            
            # Test normal configuration changes
            test_env.set("SERVICE_TIMEOUT", "60", source="update")  # Acceptable change
            test_env.set("DEBUG_MODE", "true", source="update")     # Acceptable change
            
            current_state = test_env.as_dict()
            change_analysis = change_tracker.analyze_changes(baseline, current_state)
            
            assert len(change_analysis.changed_variables) == 2
            assert "SERVICE_TIMEOUT" in change_analysis.changed_variables
            assert "DEBUG_MODE" in change_analysis.changed_variables
            assert not change_analysis.has_critical_changes  # These are safe changes
            
            # Test critical configuration changes (dangerous drift)
            test_env.set("DATABASE_URL", "postgresql://malicious:host@evil.com:5432/hacked", source="drift")
            test_env.set("JWT_SECRET_KEY", "compromised_secret", source="drift")
            
            drifted_state = test_env.as_dict()
            drift_analysis = change_tracker.analyze_changes(baseline, drifted_state)
            
            assert drift_analysis.has_critical_changes, "Critical changes not detected"
            assert "DATABASE_URL" in drift_analysis.critical_changes
            assert "JWT_SECRET_KEY" in drift_analysis.critical_changes
            
            # Test configuration rollback capability
            rollback_result = change_tracker.generate_rollback_config(baseline, drifted_state)
            assert rollback_result.can_rollback
            
            # Apply rollback
            for var_name, original_value in rollback_result.rollback_commands.items():
                test_env.set(var_name, original_value, source="rollback")
            
            # Verify rollback restored original state
            rolled_back_state = test_env.as_dict()
            post_rollback_analysis = change_tracker.analyze_changes(baseline, rolled_back_state)
            
            # Should only have the safe changes we made earlier
            critical_changes_after_rollback = [
                var for var in post_rollback_analysis.changed_variables
                if var in ["DATABASE_URL", "JWT_SECRET_KEY"]
            ]
            assert len(critical_changes_after_rollback) == 0, \
                f"Critical changes not rolled back: {critical_changes_after_rollback}"
            
            # Test environment-specific drift detection
            production_baseline = {
                "ENVIRONMENT": "production",
                "DATABASE_URL": "postgresql://prod-db:5432/prod",
                "DEBUG_MODE": "false",
                "LOG_LEVEL": "INFO"
            }
            
            # Simulate production drift (debug accidentally enabled)
            production_current = production_baseline.copy()
            production_current["DEBUG_MODE"] = "true"
            production_current["LOG_LEVEL"] = "DEBUG"
            
            prod_drift = change_tracker.analyze_environment_drift(
                production_baseline,
                production_current,
                environment="production"
            )
            
            assert prod_drift.has_environment_violations
            assert "DEBUG_MODE" in prod_drift.environment_violations
            assert prod_drift.severity == "HIGH"  # Debug in production is high severity
            
        finally:
            self.teardown_test_isolation()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_multi_environment_configuration_scenarios(self):
        """
        Test multi-environment configuration scenarios.
        
        BUSINESS CRITICAL: Multi-environment deployments require different configs.
        Must validate configuration loading for dev/staging/production.
        """
        try:
            # Test development environment configuration
            dev_env = IsolatedEnvironment()
            dev_config = {
                "ENVIRONMENT": "development",
                "DATABASE_URL": "postgresql://dev:dev@localhost:5432/dev_db",
                "REDIS_URL": "redis://localhost:6379/0",
                "DEBUG_MODE": "true",
                "LOG_LEVEL": "DEBUG",
                "CORS_ORIGINS": "http://localhost:3000,http://localhost:8080",
                "JWT_SECRET_KEY": "dev_secret_key_for_local_testing_only",
                "RATE_LIMITING": "false"
            }
            
            for key, value in dev_config.items():
                dev_env.set(key, value, source="development")
            
            # Test staging environment configuration
            staging_env = IsolatedEnvironment()
            staging_config = {
                "ENVIRONMENT": "staging", 
                "DATABASE_URL": "postgresql://staging:secret@staging-db:5432/staging_db",
                "REDIS_URL": "redis://staging-redis:6379/0",
                "DEBUG_MODE": "false",
                "LOG_LEVEL": "INFO", 
                "CORS_ORIGINS": "https://staging.netra.ai",
                "JWT_SECRET_KEY": "staging_jwt_secret_secure_32_chars",
                "RATE_LIMITING": "true"
            }
            
            for key, value in staging_config.items():
                staging_env.set(key, value, source="staging")
            
            # Test production environment configuration
            prod_env = IsolatedEnvironment()
            prod_config = {
                "ENVIRONMENT": "production",
                "DATABASE_URL": "postgresql://prod:secure@prod-db:5432/prod_db",
                "REDIS_URL": "redis://prod-redis:6379/0", 
                "DEBUG_MODE": "false",
                "LOG_LEVEL": "WARNING",
                "CORS_ORIGINS": "https://app.netra.ai",
                "JWT_SECRET_KEY": "production_jwt_secret_highly_secure",
                "RATE_LIMITING": "true"
            }
            
            for key, value in prod_config.items():
                prod_env.set(key, value, source="production")
            
            # Validate environment-specific behaviors
            environments = {
                "development": dev_env,
                "staging": staging_env, 
                "production": prod_env
            }
            
            for env_name, env_instance in environments.items():
                # Validate required variables
                required_vars = ["DATABASE_URL", "JWT_SECRET_KEY", "ENVIRONMENT"]
                validation = env_instance.validate_required_variables(required_vars)
                assert validation.is_valid, \
                    f"Environment {env_name} missing required variables: {validation.missing_variables}"
                
                # Validate environment-specific security settings
                if env_name in ["staging", "production"]:
                    assert env_instance.get("DEBUG_MODE") == "false", \
                        f"Debug mode enabled in {env_name} - security risk"
                    assert env_instance.get("RATE_LIMITING") == "true", \
                        f"Rate limiting disabled in {env_name} - security risk"
                
                # Validate CORS origins are environment appropriate
                cors_origins = env_instance.get("CORS_ORIGINS", "")
                if env_name == "development":
                    assert "localhost" in cors_origins, f"Development CORS should include localhost"
                elif env_name == "production":
                    assert "localhost" not in cors_origins, f"Production CORS should not include localhost"
                    assert "netra.ai" in cors_origins, f"Production CORS should include production domains"
            
            # Test configuration inheritance and overrides
            base_config = {
                "SERVICE_NAME": "netra-backend",
                "SERVICE_VERSION": "1.0.0", 
                "DEFAULT_TIMEOUT": "30",
                "MAX_CONNECTIONS": "100"
            }
            
            # Each environment inherits base and adds specific overrides
            for env_name, env_instance in environments.items():
                # Add base configuration
                for key, value in base_config.items():
                    env_instance.set(key, value, source="base")
                
                # Add environment-specific overrides
                if env_name == "development":
                    env_instance.set("MAX_CONNECTIONS", "10", source="dev_override")  # Lower for dev
                elif env_name == "production":
                    env_instance.set("MAX_CONNECTIONS", "500", source="prod_override")  # Higher for prod
                    env_instance.set("DEFAULT_TIMEOUT", "60", source="prod_override")  # Longer timeout
                
                # Validate overrides applied correctly
                max_conn = env_instance.get("MAX_CONNECTIONS")
                if env_name == "development":
                    assert max_conn == "10", f"Dev override failed: {max_conn}"
                elif env_name == "production":
                    assert max_conn == "500", f"Prod override failed: {max_conn}"
                    assert env_instance.get("DEFAULT_TIMEOUT") == "60", "Prod timeout override failed"
                else:
                    assert max_conn == "100", f"Base value not preserved in {env_name}: {max_conn}"
            
            # Test cross-environment configuration consistency checks
            consistency_issues = []
            
            # JWT secrets should be different across environments
            jwt_secrets = {env_name: env.get("JWT_SECRET_KEY") for env_name, env in environments.items()}
            
            if len(set(jwt_secrets.values())) != len(jwt_secrets):
                consistency_issues.append("JWT secrets not unique across environments")
            
            # Database URLs should be different
            db_urls = {env_name: env.get("DATABASE_URL") for env_name, env in environments.items()}
            
            if len(set(db_urls.values())) != len(db_urls):
                consistency_issues.append("Database URLs not unique across environments")
            
            assert len(consistency_issues) == 0, f"Configuration consistency issues: {consistency_issues}"
            
        finally:
            # No cleanup needed for isolated environments
            pass
    
    @pytest.mark.integration
    @pytest.mark.real_services
    def test_configuration_security_and_sensitive_data_handling(self):
        """
        Test configuration security and sensitive data protection.
        
        BUSINESS CRITICAL: Exposed secrets cause security breaches.
        Must ensure sensitive configuration data is properly protected.
        """
        test_env = self.setup_test_isolation()
        
        try:
            # Set up configuration with sensitive data
            sensitive_config = {
                "DATABASE_PASSWORD": "super_secret_db_password_123",
                "JWT_SECRET_KEY": "jwt_secret_key_must_be_protected",
                "API_KEY": "sk-1234567890abcdef", 
                "OAUTH_CLIENT_SECRET": "oauth_secret_never_expose",
                "ENCRYPTION_KEY": "encryption_key_for_user_data",
                "REDIS_PASSWORD": "redis_secret_password"
            }
            
            non_sensitive_config = {
                "SERVICE_NAME": "netra-backend",
                "PORT": "8000",
                "ENVIRONMENT": "test",
                "LOG_LEVEL": "INFO",
                "CORS_ORIGINS": "https://app.netra.ai"
            }
            
            # Add all configuration
            for key, value in sensitive_config.items():
                test_env.set(key, value, source="test")
                
            for key, value in non_sensitive_config.items():
                test_env.set(key, value, source="test")
            
            # Test sensitive data masking in logs/output
            masked_dict = test_env.as_dict(mask_sensitive=True)
            
            # Sensitive values should be masked
            for key in sensitive_config.keys():
                assert key in masked_dict, f"Sensitive key {key} missing from output"
                assert masked_dict[key] == "***MASKED***", \
                    f"Sensitive value not masked: {key}={masked_dict[key]}"
            
            # Non-sensitive values should remain visible
            for key, expected_value in non_sensitive_config.items():
                assert masked_dict[key] == expected_value, \
                    f"Non-sensitive value incorrectly masked: {key}"
            
            # Test access control for sensitive variables
            from shared.config_access_control import ConfigAccessControl
            
            access_control = ConfigAccessControl()
            
            # Test authorized access
            authorized_result = access_control.get_sensitive_value(
                test_env,
                "DATABASE_PASSWORD", 
                requester="netra_backend.database_manager",
                authorization_token="valid_service_token"
            )
            assert authorized_result.success
            assert authorized_result.value == "super_secret_db_password_123"
            
            # Test unauthorized access
            unauthorized_result = access_control.get_sensitive_value(
                test_env,
                "DATABASE_PASSWORD",
                requester="unknown_service",
                authorization_token="invalid_token"
            )
            assert not unauthorized_result.success
            assert unauthorized_result.error_code == "ACCESS_DENIED"
            
            # Test configuration encryption at rest
            from shared.config_encryption import ConfigEncryption
            
            encryptor = ConfigEncryption()
            
            # Encrypt sensitive configuration for storage
            encrypted_config = encryptor.encrypt_sensitive_values(sensitive_config)
            
            for key, encrypted_value in encrypted_config.items():
                # Encrypted values should not contain original values
                assert sensitive_config[key] not in encrypted_value, \
                    f"Original value visible in encrypted config: {key}"
                # Should be properly encrypted format
                assert encrypted_value.startswith("ENC[") and encrypted_value.endswith("]"), \
                    f"Invalid encryption format: {key}={encrypted_value}"
            
            # Decrypt and verify integrity
            decrypted_config = encryptor.decrypt_sensitive_values(encrypted_config)
            
            for key, original_value in sensitive_config.items():
                assert decrypted_config[key] == original_value, \
                    f"Decryption failed for {key}: expected {original_value}, got {decrypted_config[key]}"
            
            # Test configuration audit logging
            from shared.config_audit_logger import ConfigAuditLogger
            
            audit_logger = ConfigAuditLogger()
            
            # Log configuration access
            audit_logger.log_config_access(
                user_id="system",
                config_key="JWT_SECRET_KEY",
                access_type="READ",
                source_ip="127.0.0.1",
                result="SUCCESS"
            )
            
            audit_logger.log_config_change(
                user_id="admin",
                config_key="DATABASE_PASSWORD", 
                old_value="***MASKED***",
                new_value="***MASKED***",
                change_reason="Security rotation",
                source_ip="10.0.0.1"
            )
            
            # Verify audit logs are properly created
            audit_logs = audit_logger.get_recent_logs(hours=1)
            assert len(audit_logs) >= 2, f"Audit logs not created: {len(audit_logs)}"
            
            config_access_logs = [log for log in audit_logs if log.action == "CONFIG_ACCESS"]
            config_change_logs = [log for log in audit_logs if log.action == "CONFIG_CHANGE"]
            
            assert len(config_access_logs) >= 1, "Configuration access not logged"
            assert len(config_change_logs) >= 1, "Configuration change not logged"
            
            # Verify sensitive values are not in audit logs
            for log in audit_logs:
                log_text = log.to_json()
                for sensitive_value in sensitive_config.values():
                    assert sensitive_value not in log_text, \
                        f"Sensitive value leaked in audit log: {sensitive_value[:10]}..."
                        
        finally:
            self.teardown_test_isolation()


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])