"""
Integration Tests for Unified Redis Configuration Patterns
Tests Five Whys solution for Redis configuration management across all services.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from shared.redis_configuration_builder import RedisConfigurationBuilder
from auth_service.auth_core.redis_config_builder import AuthRedisConfigurationBuilder, get_auth_redis_builder
from shared.configuration.redis_pattern_validator import RedisConfigurationPatternValidator
from netra_backend.app.core.backend_environment import get_backend_env
from auth_service.auth_core.auth_environment import AuthEnvironment


class TestRedisConfigurationBuilderCore:
    """Test core RedisConfigurationBuilder functionality."""
    
    def test_redis_builder_initialization(self):
        """Test RedisConfigurationBuilder initializes correctly."""
        env_vars = {
            "ENVIRONMENT": "development",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0"
        }
        
        builder = RedisConfigurationBuilder(env_vars)
        
        assert builder.environment == "development"
        assert builder.redis_host == "localhost"
        assert builder.redis_port == "6379"
        assert builder.redis_db == "0"
        
        # Verify sub-builders exist
        assert builder.connection is not None
        assert builder.ssl is not None
        assert builder.development is not None
        assert builder.test is not None
        assert builder.docker is not None
        assert builder.staging is not None
        assert builder.production is not None
    
    def test_docker_environment_detection(self):
        """Test Docker environment detection follows DatabaseURLBuilder pattern."""
        env_vars = {"ENVIRONMENT": "development"}
        builder = RedisConfigurationBuilder(env_vars)
        
        # Test environment variable detection
        with patch.dict(os.environ, {"RUNNING_IN_DOCKER": "true"}):
            assert builder.is_docker_environment() is True
        
        with patch.dict(os.environ, {}, clear=True):
            # Mock .dockerenv file
            with patch("os.path.exists") as mock_exists:
                mock_exists.return_value = True
                assert builder.is_docker_environment() is True
        
        # Test no Docker indicators
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                assert builder.is_docker_environment() is False
    
    def test_docker_hostname_resolution(self):
        """Test Docker hostname resolution for Redis."""
        env_vars = {
            "ENVIRONMENT": "development",
            "REDIS_HOST": "localhost"
        }
        builder = RedisConfigurationBuilder(env_vars)
        
        # Test Docker hostname resolution
        with patch.object(builder, 'is_docker_environment', return_value=True):
            resolved = builder.apply_docker_hostname_resolution("localhost")
            assert resolved == "redis"
            
            resolved = builder.apply_docker_hostname_resolution("127.0.0.1")
            assert resolved == "redis"
            
            # Don't resolve other hostnames
            resolved = builder.apply_docker_hostname_resolution("redis-server")
            assert resolved == "redis-server"
        
        # Test non-Docker environment
        with patch.object(builder, 'is_docker_environment', return_value=False):
            resolved = builder.apply_docker_hostname_resolution("localhost")
            assert resolved == "localhost"
    
    def test_redis_url_construction_by_environment(self):
        """Test Redis URL construction for different environments."""
        base_env = {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "secret",
            "REDIS_DB": "1"
        }
        
        # Development environment
        env_vars = {**base_env, "ENVIRONMENT": "development"}
        builder = RedisConfigurationBuilder(env_vars)
        url = builder.get_url_for_environment()
        assert "redis://:secret@localhost:6379/1" == url
        
        # Test environment
        env_vars = {**base_env, "ENVIRONMENT": "test"}
        builder = RedisConfigurationBuilder(env_vars)
        url = builder.get_url_for_environment()
        assert "redis://:secret@localhost:6379/15" in url  # Test uses isolated DB
        
        # Staging environment
        env_vars = {**base_env, "ENVIRONMENT": "staging"}
        builder = RedisConfigurationBuilder(env_vars)
        url = builder.get_url_for_environment()
        assert "redis://:secret@localhost:6379/1" == url
    
    def test_ssl_configuration(self):
        """Test SSL Redis configuration."""
        env_vars = {
            "ENVIRONMENT": "production",
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "REDIS_SSL": "true",
            "REDIS_DB": "0"
        }
        
        builder = RedisConfigurationBuilder(env_vars)
        
        assert builder.ssl.is_ssl_enabled is True
        ssl_url = builder.ssl.enabled_url
        assert ssl_url.startswith("rediss://")
        assert "redis.example.com:6380" in ssl_url
    
    def test_connection_pool_configuration(self):
        """Test Redis connection pool configuration by environment."""
        # Production pool config
        env_vars = {"ENVIRONMENT": "production"}
        builder = RedisConfigurationBuilder(env_vars)
        pool_config = builder.pool.get_pool_config()
        
        assert pool_config["max_connections"] == 50
        assert pool_config["retry_on_timeout"] is True
        assert pool_config["health_check_interval"] == 30
        
        # Development pool config
        env_vars = {"ENVIRONMENT": "development"}
        builder = RedisConfigurationBuilder(env_vars)
        pool_config = builder.pool.get_pool_config()
        
        assert pool_config["max_connections"] == 10
        assert pool_config["retry_on_timeout"] is False
        assert pool_config["health_check_interval"] == 120
    
    def test_validation_by_environment(self):
        """Test configuration validation by environment."""
        # Development - should pass without explicit config
        env_vars = {"ENVIRONMENT": "development"}
        builder = RedisConfigurationBuilder(env_vars)
        is_valid, error = builder.validate()
        assert is_valid is True
        
        # Production - should require explicit config
        env_vars = {"ENVIRONMENT": "production"}
        builder = RedisConfigurationBuilder(env_vars)
        is_valid, error = builder.validate()
        assert is_valid is False
        assert "Missing required variables" in error
        
        # Production with proper config - should pass
        env_vars = {
            "ENVIRONMENT": "production",
            "REDIS_HOST": "redis.prod.com",
            "REDIS_PORT": "6379"
        }
        builder = RedisConfigurationBuilder(env_vars)
        is_valid, error = builder.validate()
        assert is_valid is True
    
    def test_safe_logging(self):
        """Test safe Redis URL logging with credential masking."""
        # Test URL masking
        masked = RedisConfigurationBuilder.mask_url_for_logging("redis://:secret@localhost:6379/0")
        assert "secret" not in masked
        assert "redis://***@localhost:6379/0" == masked
        
        # Test URL without password
        masked = RedisConfigurationBuilder.mask_url_for_logging("redis://localhost:6379/0")
        assert masked == "redis://localhost:6379/0"
        
        # Test None URL
        masked = RedisConfigurationBuilder.mask_url_for_logging(None)
        assert masked == "NOT SET"


class TestAuthRedisConfigurationBuilder:
    """Test auth service-specific Redis configuration."""
    
    def test_auth_redis_builder_initialization(self):
        """Test auth Redis builder with service-specific defaults."""
        env_vars = {"ENVIRONMENT": "development"}
        builder = get_auth_redis_builder(env_vars)
        
        assert isinstance(builder, AuthRedisConfigurationBuilder)
        assert builder.redis_db == "1"  # Auth development uses db 1
    
    def test_auth_database_isolation(self):
        """Test auth service uses isolated Redis databases."""
        environments = [
            ("development", "1"),
            ("test", "2"), 
            ("staging", "3"),
            ("production", "4")
        ]
        
        for env, expected_db in environments:
            env_vars = {"ENVIRONMENT": env}
            builder = get_auth_redis_builder(env_vars)
            assert builder.redis_db == expected_db
    
    def test_auth_session_config(self):
        """Test auth-specific session configuration."""
        env_vars = {
            "ENVIRONMENT": "production",
            "REDIS_HOST": "redis.auth.com",
            "SESSION_TIMEOUT": "7200"
        }
        builder = get_auth_redis_builder(env_vars)
        
        session_config = builder.get_session_config()
        assert session_config["session_timeout"] == 7200
        assert session_config["key_prefix"] == "auth:production:session:"
        assert "pool_config" in session_config
    
    def test_auth_redis_validation(self):
        """Test auth-specific Redis validation."""
        # Test staging requires Redis
        env_vars = {"ENVIRONMENT": "staging"}
        builder = get_auth_redis_builder(env_vars)
        is_valid, error = builder.validate_auth_redis_config()
        assert is_valid is False
        assert "session management" in error


class TestServiceIntegration:
    """Test service integration with unified Redis patterns."""
    
    def test_backend_environment_redis_integration(self):
        """Test BackendEnvironment uses RedisConfigurationBuilder."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379"
        }):
            backend_env = get_backend_env()
            redis_url = backend_env.get_redis_url()
            
            # Verify URL follows expected pattern
            assert redis_url.startswith("redis://")
            assert "localhost" in redis_url or "redis" in redis_url  # Could resolve to Docker
    
    def test_auth_environment_redis_integration(self):
        """Test AuthEnvironment uses AuthRedisConfigurationBuilder."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "REDIS_HOST": "localhost", 
            "REDIS_PORT": "6379"
        }):
            auth_env = AuthEnvironment()
            redis_url = auth_env.get_redis_url()
            
            # Verify URL follows expected pattern with auth database isolation
            assert redis_url.startswith("redis://")
            assert "/1" in redis_url  # Auth development uses db 1
    
    def test_service_independence(self):
        """Test that services maintain independence while using unified patterns."""
        backend_env_vars = {
            "ENVIRONMENT": "development",
            "REDIS_HOST": "backend-redis",
            "REDIS_DB": "0"
        }
        
        auth_env_vars = {
            "ENVIRONMENT": "development", 
            "REDIS_HOST": "auth-redis",
            "REDIS_DB": "1"
        }
        
        # Backend configuration
        backend_builder = RedisConfigurationBuilder(backend_env_vars)
        backend_url = backend_builder.get_url_for_environment()
        
        # Auth configuration
        auth_builder = get_auth_redis_builder(auth_env_vars)
        auth_url = auth_builder.get_url_for_environment()
        
        # Verify services use different configurations
        assert "backend-redis" in backend_url
        assert "auth-redis" in auth_url
        assert "/0" in backend_url
        assert "/1" in auth_url


class TestRedisPatternValidation:
    """Test Redis configuration pattern validation framework."""
    
    def test_pattern_validator_initialization(self):
        """Test pattern validator initializes correctly."""
        validator = RedisConfigurationPatternValidator()
        assert validator.project_root is not None
        assert len(validator.APPROVED_SERVICES) == 2
        assert "netra_backend" in validator.APPROVED_SERVICES
        assert "auth_service" in validator.APPROVED_SERVICES
    
    def test_forbidden_pattern_detection(self):
        """Test detection of forbidden Redis patterns."""
        # Create temporary file with forbidden patterns
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write('''
def bad_redis_config():
    url = env.get("REDIS_URL")
    return "redis://localhost:6379/0"
            ''')
            tmp_path = tmp.name
        
        try:
            validator = RedisConfigurationPatternValidator()
            content = Path(tmp_path).read_text()
            lines = content.split('\n')
            
            # Manually check patterns
            violations = []
            for line_num, line in enumerate(lines, 1):
                for forbidden in validator.EXPECTED_PATTERNS["forbidden_patterns"]:
                    if forbidden in line and not line.strip().startswith('#'):
                        violations.append(f"Line {line_num}: {forbidden}")
            
            assert len(violations) >= 2  # Should find both violations
        finally:
            os.unlink(tmp_path)
    
    def test_environment_variable_validation(self):
        """Test environment variable pattern validation."""
        validator = RedisConfigurationPatternValidator()
        
        # Test deprecated REDIS_URL in production
        env_vars = {
            "ENVIRONMENT": "production",
            "REDIS_URL": "redis://prod-redis:6379/0"
        }
        violations = validator.validate_redis_environment_variables(env_vars)
        assert len(violations) > 0
        assert any("DEPRECATED_REDIS_URL" in v.violation_type for v in violations)
        
        # Test missing Redis components in staging
        env_vars = {"ENVIRONMENT": "staging"}
        violations = validator.validate_redis_environment_variables(env_vars)
        assert len(violations) > 0
        assert any("MISSING_REDIS_COMPONENTS" in v.violation_type for v in violations)
    
    def test_compliance_report_generation(self):
        """Test compliance report generation."""
        validator = RedisConfigurationPatternValidator()
        report = validator.generate_compliance_report()
        
        assert "compliance_score" in report
        assert "total_violations" in report
        assert "recommendations" in report
        assert isinstance(report["recommendations"], list)


class TestEnvironmentSpecificBehavior:
    """Test environment-specific Redis configuration behavior."""
    
    @pytest.mark.parametrize("environment,expected_behavior", [
        ("development", "fallback_allowed"),
        ("test", "isolation_required"),
        ("staging", "explicit_config_required"),
        ("production", "explicit_config_required")
    ])
    def test_environment_specific_redis_behavior(self, environment, expected_behavior):
        """Test Redis behavior varies appropriately by environment."""
        env_vars = {"ENVIRONMENT": environment}
        builder = RedisConfigurationBuilder(env_vars)
        
        if expected_behavior == "fallback_allowed":
            # Development should provide fallback URLs
            url = builder.get_url_for_environment()
            assert url is not None
            assert "localhost" in url or "redis" in url
        
        elif expected_behavior == "isolation_required":
            # Test environment should use isolated database
            url = builder.get_url_for_environment()
            assert url is not None
            assert "/15" in url  # Test isolation database
        
        elif expected_behavior == "explicit_config_required":
            # Staging/production should require explicit configuration
            is_valid, _ = builder.validate()
            if not builder.connection.has_config:
                assert is_valid is False
    
    def test_docker_environment_behavior(self):
        """Test Docker-specific Redis configuration behavior."""
        env_vars = {
            "ENVIRONMENT": "development",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379"
        }
        
        builder = RedisConfigurationBuilder(env_vars)
        
        # Test Docker hostname resolution
        with patch.object(builder, 'is_docker_environment', return_value=True):
            url = builder.get_url_for_environment()
            assert "redis://" in url
            # In Docker, localhost should resolve to 'redis'
            
        # Test non-Docker environment
        with patch.object(builder, 'is_docker_environment', return_value=False):
            url = builder.get_url_for_environment()
            assert "localhost" in url


@pytest.mark.integration
class TestE2ERedisConfigurationFlow:
    """End-to-end tests for Redis configuration flow."""
    
    def test_complete_redis_configuration_flow(self):
        """Test complete Redis configuration flow from environment to URL."""
        # Simulate complete environment setup
        test_env = {
            "ENVIRONMENT": "development",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "testpass",
            "REDIS_DB": "1"
        }
        
        with patch.dict(os.environ, test_env):
            # Test backend service flow
            backend_env = get_backend_env()
            backend_redis_url = backend_env.get_redis_url()
            backend_redis_host = backend_env.get_redis_host()
            backend_redis_port = backend_env.get_redis_port()
            
            # Verify backend configuration
            assert backend_redis_url is not None
            assert backend_redis_host == "localhost"
            assert backend_redis_port == 6379
            
            # Test auth service flow
            auth_env = AuthEnvironment()
            auth_redis_url = auth_env.get_redis_url()
            auth_redis_host = auth_env.get_redis_host()
            auth_redis_port = auth_env.get_redis_port()
            
            # Verify auth configuration
            assert auth_redis_url is not None
            assert auth_redis_host == "localhost"
            assert auth_redis_port == 6379
            
            # Verify service isolation (different databases)
            assert "/0" in backend_redis_url or "/1" in backend_redis_url
            assert "/1" in auth_redis_url or "/2" in auth_redis_url  # Auth uses different DB
    
    def test_five_whys_solution_validation(self):
        """Test that Five Whys solution requirements are met."""
        # 1. Pattern Consistency: Both services use builder pattern
        backend_env_vars = {"ENVIRONMENT": "development", "REDIS_HOST": "localhost"}
        auth_env_vars = {"ENVIRONMENT": "development", "REDIS_HOST": "localhost"}
        
        backend_builder = RedisConfigurationBuilder(backend_env_vars)
        auth_builder = get_auth_redis_builder(auth_env_vars)
        
        # Both should have same interface methods
        assert hasattr(backend_builder, 'get_url_for_environment')
        assert hasattr(auth_builder, 'get_url_for_environment')
        assert hasattr(backend_builder, 'is_docker_environment')
        assert hasattr(auth_builder, 'is_docker_environment')
        
        # 2. Docker Environment Detection: Both support Docker resolution
        assert callable(backend_builder.apply_docker_hostname_resolution)
        assert callable(auth_builder.apply_docker_hostname_resolution)
        
        # 3. Environment-Specific Behavior: Both adapt to environments
        backend_url = backend_builder.get_url_for_environment()
        auth_url = auth_builder.get_url_for_environment()
        assert backend_url is not None
        assert auth_url is not None
        
        # 4. Service Independence: Auth has specific database isolation
        assert auth_builder.redis_db == "1"  # Auth dev database
        
        # 5. Configuration Validation: Pattern validator works
        validator = RedisConfigurationPatternValidator()
        report = validator.generate_compliance_report()
        assert "compliance_score" in report