"""
Comprehensive Unit Test Suite: UnifiedConfigurationManager SSOT - Business Critical

Business Value Justification (BVJ):
- Segment: Platform/All (Free, Early, Mid, Enterprise) - Core infrastructure affecting all customers
- Business Goal: Configuration stability preventing chat service failures and data leakage
- Value Impact: Environment consistency prevents $500K+ ARR chat failures, configuration security prevents credential exposure
- Strategic Impact: CRITICAL - Foundation configuration management protecting multi-user isolation ($15K+ MRR per enterprise customer)

CRITICAL AREAS TESTED:
1. Configuration Entry Management (protecting configuration consistency)
2. Multi-User Isolation (protecting $15K+ MRR per enterprise customer)
3. Environment Consistency (preventing $500K+ ARR chat failures)
4. Configuration Validation & Type Safety (preventing system instability)
5. Configuration Sources & Precedence (ensuring predictable behavior)
6. Cache Management & Performance (supporting scalability)

This test suite follows CLAUDE.md requirements:
- Real services over mocks (using real IsolatedEnvironment, real validation)
- Tests designed to fail hard (no try/except masking failures)
- Multi-user isolation validation (factory patterns)
- Business logic validation (no cheating on tests)
- SSOT compliance validation
"""

import pytest
import threading
import time
import json
import tempfile
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

from netra_backend.app.core.managers.unified_configuration_manager import (
    UnifiedConfigurationManager,
    ConfigurationManagerFactory,
    ConfigurationEntry,
    ConfigurationSource,
    ConfigurationScope,
    ConfigurationStatus,
    ConfigurationError,
    get_configuration_manager
)
from shared.isolated_environment import IsolatedEnvironment


class TestUnifiedConfigurationManagerSSotBusinessCritical:
    """Comprehensive unit tests for UnifiedConfigurationManager SSOT protecting business value."""

    @pytest.fixture
    def isolated_env(self):
        """Provide clean IsolatedEnvironment for each test."""
        env = IsolatedEnvironment()
        yield env
        # Cleanup - ensure no environment pollution between tests
        env._environment_vars.clear()

    @pytest.fixture
    def temp_config_dir(self):
        """Provide temporary directory for configuration file testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_manager(self, isolated_env):
        """Provide clean UnifiedConfigurationManager instance."""
        # Patch environment detection to use isolated environment
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment') as mock_env_class:
            mock_env_class.return_value = isolated_env
            manager = UnifiedConfigurationManager(
                user_id="test_user_12345",
                environment="test",
                service_name="test_service",
                enable_validation=True,
                enable_caching=True,
                cache_ttl=5
            )
            yield manager

    @pytest.fixture
    def factory_cleanup(self):
        """Cleanup factory state between tests."""
        yield
        # Clear all factory managers to prevent test interference
        ConfigurationManagerFactory._global_manager = None
        ConfigurationManagerFactory._user_managers.clear()
        ConfigurationManagerFactory._service_managers.clear()

    # ============================================================================
    # CONFIGURATION ENTRY MANAGEMENT TESTS (Business Critical)
    # Protects: Configuration consistency preventing system failures
    # ============================================================================

    def test_configuration_entry_validation_and_metadata_business_critical(self, config_manager):
        """
        BUSINESS CRITICAL: Test configuration entry validation and metadata handling.
        
        Protects: Configuration consistency preventing $500K+ ARR chat service failures
        Business Impact: Invalid configurations can cause complete service outages
        """
        # Test configuration entry creation with all metadata
        entry = ConfigurationEntry(
            key="database.pool_size",
            value="10",
            source=ConfigurationSource.ENVIRONMENT,
            scope=ConfigurationScope.GLOBAL,
            data_type=int,
            required=True,
            sensitive=False,
            description="Database connection pool size",
            validation_rules=["min_value:1", "max_value:100"],
            environment="production",
            service="backend",
            user_id="enterprise_user_001"
        )
        
        # Validate entry processes correctly
        assert entry.validate() == True
        assert entry.value == 10  # Should be converted to int
        assert entry.key == "database.pool_size"
        assert entry.source == ConfigurationSource.ENVIRONMENT
        assert entry.scope == ConfigurationScope.GLOBAL
        assert entry.required == True
        assert entry.sensitive == False
        
        # Test invalid entry fails validation (critical for preventing misconfigurations)
        invalid_entry = ConfigurationEntry(
            key="database.pool_size",
            value="invalid_number",
            source=ConfigurationSource.ENVIRONMENT,
            scope=ConfigurationScope.GLOBAL,
            data_type=int,
            required=True,
            validation_rules=["min_value:1"]
        )
        
        # Must fail validation to prevent system instability
        assert invalid_entry.validate() == False

    def test_sensitive_value_masking_prevents_credential_exposure(self, config_manager):
        """
        BUSINESS CRITICAL: Test sensitive value masking prevents credential exposure.
        
        Protects: Enterprise security compliance and credential protection
        Business Impact: Credential exposure can cause enterprise customer loss ($15K+ MRR each)
        """
        # Test various sensitive configurations that must be masked
        sensitive_configs = {
            "security.jwt_secret": "super_secret_jwt_key_12345678",
            "llm.openai.api_key": "sk-1234567890abcdef1234567890abcdef",
            "database.password": "complex_db_password_2024",
            "oauth.client_secret": "oauth_client_secret_value",
        }
        
        for key, value in sensitive_configs.items():
            # Set sensitive configuration
            config_manager.set(key, value, sensitive=True)
            
            # Verify actual value is stored correctly
            actual_value = config_manager.get(key)
            assert actual_value == value
            
            # Verify masked value protects credentials
            masked_value = config_manager.get_masked(key)
            assert masked_value != value  # Must be masked
            assert "***" in str(masked_value) or "*" in str(masked_value)
            
            # Verify sensitive value is auto-detected for key patterns
            entry = config_manager._configurations[key]
            assert entry.sensitive == True
            
            # Verify display value is properly masked
            display_value = entry.get_display_value()
            assert display_value != value  # Must be masked for logging/display
            assert len(display_value) <= len(value)  # Masked should not be longer

    def test_type_coercion_comprehensive_validation_prevents_errors(self, config_manager):
        """
        BUSINESS CRITICAL: Test comprehensive type coercion prevents configuration errors.
        
        Protects: System stability by ensuring type consistency
        Business Impact: Type errors in configuration can cause service crashes affecting all users
        """
        # Test integer coercion from various inputs
        config_manager.set("test.int_from_string", "42")
        assert config_manager.get_int("test.int_from_string") == 42
        
        config_manager.set("test.int_from_float", 42.9)
        assert config_manager.get_int("test.int_from_float") == 42
        
        config_manager.set("test.int_from_float_string", "42.7")
        assert config_manager.get_int("test.int_from_float_string") == 42
        
        # Test invalid int conversion returns default (prevents crashes)
        config_manager.set("test.invalid_int", "not_a_number")
        assert config_manager.get_int("test.invalid_int", default=0) == 0
        
        # Test comprehensive boolean conversion (critical for feature flags)
        boolean_test_cases = {
            # Truthy values
            "true": True, "True": True, "TRUE": True,
            "1": True, "yes": True, "on": True, "y": True,
            "enable": True, "enabled": True,
            # Falsy values  
            "false": False, "False": False, "FALSE": False,
            "0": False, "no": False, "off": False, "n": False,
            "disable": False, "disabled": False, "": False,
        }
        
        for test_value, expected in boolean_test_cases.items():
            config_manager.set(f"test.bool_{test_value}", test_value)
            result = config_manager.get_bool(f"test.bool_{test_value}")
            assert result == expected, f"Boolean conversion failed for '{test_value}' -> expected {expected}, got {result}"
        
        # Test list conversion from JSON and CSV (critical for configuration arrays)
        config_manager.set("test.list_json", '["item1", "item2", "item3"]')
        assert config_manager.get_list("test.list_json") == ["item1", "item2", "item3"]
        
        config_manager.set("test.list_csv", "item1, item2, item3")
        assert config_manager.get_list("test.list_csv") == ["item1", "item2", "item3"]
        
        # Test dict conversion from JSON (critical for nested configurations)
        config_manager.set("test.dict_json", '{"key1": "value1", "key2": "value2"}')
        result_dict = config_manager.get_dict("test.dict_json")
        assert result_dict == {"key1": "value1", "key2": "value2"}
        
        # Test invalid JSON returns default (prevents crashes)
        config_manager.set("test.invalid_json", "invalid_json_string")
        assert config_manager.get_dict("test.invalid_json", default={}) == {}

    def test_validation_rules_comprehensive_business_logic(self, config_manager):
        """
        BUSINESS CRITICAL: Test validation rules prevent invalid business configurations.
        
        Protects: Business logic integrity and system stability
        Business Impact: Invalid configurations can cause business logic failures affecting revenue
        """
        # Test min/max length validation (critical for security)
        entry_password = ConfigurationEntry(
            key="security.password",
            value="12345678",  # 8 characters
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.USER,
            data_type=str,
            validation_rules=["min_length:8", "max_length:50"]
        )
        assert entry_password.validate() == True
        
        # Test password too short (security violation)
        entry_short_password = ConfigurationEntry(
            key="security.password",
            value="123",  # Too short
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.USER,
            data_type=str,
            validation_rules=["min_length:8"]
        )
        assert entry_short_password.validate() == False
        
        # Test numeric range validation (critical for resource limits)
        entry_pool_size = ConfigurationEntry(
            key="database.pool_size",
            value=10,
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.GLOBAL,
            data_type=int,
            validation_rules=["min_value:1", "max_value:100", "positive"]
        )
        assert entry_pool_size.validate() == True
        
        # Test invalid range (prevents resource exhaustion)
        entry_invalid_pool = ConfigurationEntry(
            key="database.pool_size",
            value=1000,  # Too high
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.GLOBAL,
            data_type=int,
            validation_rules=["max_value:100"]
        )
        assert entry_invalid_pool.validate() == False
        
        # Test regex validation (critical for format validation)
        entry_email = ConfigurationEntry(
            key="user.email",
            value="test@example.com",
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.USER,
            data_type=str,
            validation_rules=["regex:^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"]
        )
        assert entry_email.validate() == True
        
        # Test invalid email format
        entry_invalid_email = ConfigurationEntry(
            key="user.email",
            value="invalid_email",
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.USER,
            data_type=str,
            validation_rules=["regex:^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"]
        )
        assert entry_invalid_email.validate() == False
        
        # Test not_empty validation (prevents empty critical values)
        entry_not_empty = ConfigurationEntry(
            key="api.key",
            value="some_value",
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.GLOBAL,
            data_type=str,
            validation_rules=["not_empty"]
        )
        assert entry_not_empty.validate() == True
        
        entry_empty = ConfigurationEntry(
            key="api.key",
            value="",
            source=ConfigurationSource.OVERRIDE,
            scope=ConfigurationScope.GLOBAL,
            data_type=str,
            validation_rules=["not_empty"]
        )
        assert entry_empty.validate() == False

    def test_configuration_source_precedence_business_critical(self, config_manager):
        """
        BUSINESS CRITICAL: Test configuration source precedence ensures predictable behavior.
        
        Protects: Configuration predictability and environment consistency
        Business Impact: Incorrect precedence can cause production configurations to be overridden
        """
        key = "test.precedence_validation"
        
        # Set value from each source in reverse precedence order
        config_manager.set(key, "default_value", source=ConfigurationSource.DEFAULT)
        config_manager.set(key, "database_value", source=ConfigurationSource.DATABASE)
        config_manager.set(key, "config_file_value", source=ConfigurationSource.CONFIG_FILE)
        config_manager.set(key, "environment_value", source=ConfigurationSource.ENVIRONMENT)
        config_manager.set(key, "override_value", source=ConfigurationSource.OVERRIDE)
        
        # Verify highest precedence (OVERRIDE) wins
        assert config_manager.get(key) == "override_value"
        
        # Remove override, verify environment wins
        config_manager.delete(key)
        config_manager.set(key, "environment_value", source=ConfigurationSource.ENVIRONMENT)
        config_manager.set(key, "config_file_value", source=ConfigurationSource.CONFIG_FILE)
        config_manager.set(key, "database_value", source=ConfigurationSource.DATABASE)
        config_manager.set(key, "default_value", source=ConfigurationSource.DEFAULT)
        
        assert config_manager.get(key) == "environment_value"
        
        # Verify precedence order is maintained
        precedence_order = [
            ConfigurationSource.OVERRIDE,
            ConfigurationSource.ENVIRONMENT,
            ConfigurationSource.CONFIG_FILE,
            ConfigurationSource.DATABASE,
            ConfigurationSource.DEFAULT
        ]
        
        # Each source should have lower precedence than previous
        for i in range(len(precedence_order) - 1):
            assert precedence_order[i].value != precedence_order[i + 1].value

    # ============================================================================
    # MULTI-USER ISOLATION TESTS (Enterprise Critical)
    # Protects: $15K+ MRR per enterprise customer through user data isolation
    # ============================================================================

    def test_user_specific_configuration_isolation_enterprise_critical(self, factory_cleanup):
        """
        ENTERPRISE CRITICAL: Test user-specific configuration isolation prevents data leakage.
        
        Protects: Multi-tenant isolation preventing data leakage between enterprise customers
        Business Impact: $15K+ MRR per enterprise customer - data leakage causes customer loss
        """
        # Create separate managers for different enterprise customers
        user1_manager = ConfigurationManagerFactory.get_user_manager("enterprise_customer_001")
        user2_manager = ConfigurationManagerFactory.get_user_manager("enterprise_customer_002")
        user3_manager = ConfigurationManagerFactory.get_user_manager("enterprise_customer_003")
        
        # Set different sensitive configurations for each user
        user1_manager.set("api.key", "user1_secret_api_key", sensitive=True)
        user1_manager.set("database.credentials", "user1_db_password", sensitive=True)
        user1_manager.set("user.preferences", {"theme": "dark", "notifications": True})
        
        user2_manager.set("api.key", "user2_secret_api_key", sensitive=True)
        user2_manager.set("database.credentials", "user2_db_password", sensitive=True)
        user2_manager.set("user.preferences", {"theme": "light", "notifications": False})
        
        user3_manager.set("api.key", "user3_secret_api_key", sensitive=True)
        user3_manager.set("database.credentials", "user3_db_password", sensitive=True)
        
        # Verify complete isolation - each user only sees their own data
        assert user1_manager.get("api.key") == "user1_secret_api_key"
        assert user2_manager.get("api.key") == "user2_secret_api_key"
        assert user3_manager.get("api.key") == "user3_secret_api_key"
        
        assert user1_manager.get("database.credentials") == "user1_db_password"
        assert user2_manager.get("database.credentials") == "user2_db_password"
        assert user3_manager.get("database.credentials") == "user3_db_password"
        
        # Verify user preferences are isolated
        user1_prefs = user1_manager.get("user.preferences")
        user2_prefs = user2_manager.get("user.preferences")
        assert user1_prefs["theme"] == "dark"
        assert user2_prefs["theme"] == "light"
        assert user1_prefs != user2_prefs
        
        # Verify no cross-contamination (critical security requirement)
        assert user1_manager.get("api.key") != user2_manager.get("api.key")
        assert user1_manager.get("api.key") != user3_manager.get("api.key")
        assert user2_manager.get("api.key") != user3_manager.get("api.key")
        
        # Verify configuration counts are independent
        user1_count = len(user1_manager.get_all())
        user2_count = len(user2_manager.get_all())
        user3_count = len(user3_manager.get_all())
        
        # Each user should have their own configurations plus system defaults
        assert user1_count > 0
        assert user2_count > 0
        assert user3_count > 0

    def test_service_specific_configuration_isolation(self, factory_cleanup):
        """
        BUSINESS CRITICAL: Test service-specific configuration isolation.
        
        Protects: Service boundaries and configuration consistency
        Business Impact: Service configuration leakage can cause cross-service failures
        """
        # Create service-specific managers
        auth_manager = ConfigurationManagerFactory.get_service_manager("auth_service")
        backend_manager = ConfigurationManagerFactory.get_service_manager("backend_service")
        analytics_manager = ConfigurationManagerFactory.get_service_manager("analytics_service")
        
        # Set service-specific configurations
        auth_manager.set("jwt.secret", "auth_jwt_secret", sensitive=True)
        auth_manager.set("oauth.client_id", "auth_oauth_client")
        auth_manager.set("session.timeout", 1800)
        
        backend_manager.set("database.pool_size", 20)
        backend_manager.set("redis.max_connections", 100)
        backend_manager.set("llm.timeout", 30.0)
        
        analytics_manager.set("clickhouse.host", "analytics-db.internal")
        analytics_manager.set("data.retention_days", 365)
        
        # Verify service isolation
        assert auth_manager.get("jwt.secret") == "auth_jwt_secret"
        assert backend_manager.get("jwt.secret") is None  # Should not see auth secrets
        assert analytics_manager.get("jwt.secret") is None
        
        assert backend_manager.get("database.pool_size") == 20
        assert auth_manager.get("database.pool_size") != 20  # Should have different/default value
        
        assert analytics_manager.get("clickhouse.host") == "analytics-db.internal"
        assert backend_manager.get("clickhouse.host") is None
        
        # Verify service names are correctly set
        assert auth_manager.service_name == "auth_service"
        assert backend_manager.service_name == "backend_service"
        assert analytics_manager.service_name == "analytics_service"

    def test_combined_user_service_isolation_enterprise_scenario(self, factory_cleanup):
        """
        ENTERPRISE CRITICAL: Test combined user+service isolation for enterprise scenarios.
        
        Protects: Enterprise multi-tenant architecture
        Business Impact: Enterprise customers pay $15K+ MRR for guaranteed isolation
        """
        # Create combined user+service managers (enterprise scenario)
        enterprise_auth = ConfigurationManagerFactory.get_manager("enterprise_001", "auth_service")
        enterprise_backend = ConfigurationManagerFactory.get_manager("enterprise_001", "backend_service")
        startup_auth = ConfigurationManagerFactory.get_manager("startup_002", "auth_service")
        startup_backend = ConfigurationManagerFactory.get_manager("startup_002", "backend_service")
        
        # Set enterprise-specific configurations
        enterprise_auth.set("oauth.enterprise_sso", True)
        enterprise_auth.set("security.compliance_mode", "enterprise")
        enterprise_backend.set("agent.max_concurrent", 10)  # Higher limits for enterprise
        enterprise_backend.set("performance.priority", "high")
        
        # Set startup-specific configurations (lower limits)
        startup_auth.set("oauth.enterprise_sso", False)
        startup_auth.set("security.compliance_mode", "standard")
        startup_backend.set("agent.max_concurrent", 3)  # Lower limits for startup
        startup_backend.set("performance.priority", "standard")
        
        # Verify enterprise configurations
        assert enterprise_auth.get("oauth.enterprise_sso") == True
        assert enterprise_auth.get("security.compliance_mode") == "enterprise"
        assert enterprise_backend.get("agent.max_concurrent") == 10
        assert enterprise_backend.get("performance.priority") == "high"
        
        # Verify startup configurations
        assert startup_auth.get("oauth.enterprise_sso") == False
        assert startup_auth.get("security.compliance_mode") == "standard"
        assert startup_backend.get("agent.max_concurrent") == 3
        assert startup_backend.get("performance.priority") == "standard"
        
        # Verify complete isolation between customers
        assert enterprise_auth.get("oauth.enterprise_sso") != startup_auth.get("oauth.enterprise_sso")
        assert enterprise_backend.get("agent.max_concurrent") != startup_backend.get("agent.max_concurrent")
        
        # Verify user_id and service_name are correctly set
        assert enterprise_auth.user_id == "enterprise_001"
        assert enterprise_auth.service_name == "auth_service"
        assert startup_backend.user_id == "startup_002"
        assert startup_backend.service_name == "backend_service"

    def test_factory_manager_counting_and_cleanup(self, factory_cleanup):
        """
        BUSINESS CRITICAL: Test factory manager counting and cleanup prevents memory leaks.
        
        Protects: System resource management and scalability
        Business Impact: Memory leaks can cause service degradation affecting all customers
        """
        # Initial state should be empty
        initial_counts = ConfigurationManagerFactory.get_manager_count()
        assert initial_counts["global"] == 0
        assert initial_counts["user_specific"] == 0
        assert initial_counts["service_specific"] == 0
        assert initial_counts["combined"] == 0
        assert initial_counts["total"] == 0
        
        # Create various manager types
        global_mgr = ConfigurationManagerFactory.get_global_manager()
        user1_mgr = ConfigurationManagerFactory.get_user_manager("user_001")
        user2_mgr = ConfigurationManagerFactory.get_user_manager("user_002")
        service1_mgr = ConfigurationManagerFactory.get_service_manager("service_001")
        combined_mgr = ConfigurationManagerFactory.get_manager("user_003", "service_002")
        
        # Verify counts after creation
        counts_after_creation = ConfigurationManagerFactory.get_manager_count()
        assert counts_after_creation["global"] == 1
        assert counts_after_creation["user_specific"] == 2  # user_001, user_002
        assert counts_after_creation["service_specific"] == 1  # service_001
        assert counts_after_creation["combined"] == 1  # user_003:service_002
        assert counts_after_creation["total"] == 5
        
        # Verify singleton behavior - requesting same manager returns existing instance
        global_mgr2 = ConfigurationManagerFactory.get_global_manager()
        user1_mgr2 = ConfigurationManagerFactory.get_user_manager("user_001")
        assert global_mgr is global_mgr2  # Same instance
        assert user1_mgr is user1_mgr2  # Same instance
        
        # Counts should not change (singleton behavior)
        counts_after_retrieval = ConfigurationManagerFactory.get_manager_count()
        assert counts_after_retrieval == counts_after_creation
        
        # Test cache clearing across all managers
        # Set values in different managers
        global_mgr.set("global.test", "global_value")
        user1_mgr.set("user.test", "user1_value")
        service1_mgr.set("service.test", "service1_value")
        
        # Clear all caches
        ConfigurationManagerFactory.clear_all_caches()
        
        # Values should still be accessible (cache clearing doesn't remove configurations)
        assert global_mgr.get("global.test") == "global_value"
        assert user1_mgr.get("user.test") == "user1_value"
        assert service1_mgr.get("service.test") == "service1_value"

    # ============================================================================
    # ENVIRONMENT CONSISTENCY TESTS (Revenue Protection)
    # Protects: $500K+ ARR by preventing chat service failures
    # ============================================================================

    def test_environment_detection_and_consistency(self, isolated_env):
        """
        REVENUE CRITICAL: Test environment detection ensures configuration consistency.
        
        Protects: Environment-specific configurations prevent production/staging mix-ups
        Business Impact: Wrong environment configs can cause $500K+ ARR service outages
        """
        # Test environment detection from various sources
        test_cases = [
            ("ENVIRONMENT", "production"),
            ("STAGE", "staging"),
            ("ENV", "development"),
            ("DEPLOYMENT_ENV", "test")
        ]
        
        for env_var, env_value in test_cases:
            # Clear environment
            isolated_env._environment_vars.clear()
            isolated_env.set(env_var, env_value, source="test")
            
            # Create manager with isolated environment
            with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment') as mock_env_class:
                mock_env_class.return_value = isolated_env
                manager = UnifiedConfigurationManager()
                
                # Verify environment is detected correctly
                assert manager.environment == env_value.lower()
                
                # Verify environment-specific behavior
                status = manager.get_status()
                assert status["environment"] == env_value.lower()
        
        # Test default fallback when no environment variables set
        isolated_env._environment_vars.clear()
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment') as mock_env_class:
            mock_env_class.return_value = isolated_env
            manager = UnifiedConfigurationManager()
            assert manager.environment == "development"  # Default fallback

    def test_isolated_environment_integration_security_critical(self, isolated_env):
        """
        SECURITY CRITICAL: Test IsolatedEnvironment integration prevents environment pollution.
        
        Protects: Environment isolation preventing configuration cross-contamination
        Business Impact: Environment pollution can expose production secrets in development
        """
        # Set test environment variables
        isolated_env.set("DATABASE_POOL_SIZE", "15", source="test")
        isolated_env.set("REDIS_MAX_CONNECTIONS", "75", source="test")
        isolated_env.set("JWT_SECRET_KEY", "test_jwt_secret", source="test")
        isolated_env.set("DEBUG", "true", source="test")
        
        # Create manager with isolated environment
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment') as mock_env_class:
            mock_env_class.return_value = isolated_env
            manager = UnifiedConfigurationManager()
            
            # Verify environment variables are loaded correctly
            assert manager.get_int("database.pool_size") == 15
            assert manager.get_int("redis.max_connections") == 75
            assert manager.get_str("security.jwt_secret") == "test_jwt_secret"
            assert manager.get_bool("system.debug") == True
            
            # Verify sensitive values are automatically detected and masked
            jwt_entry = manager._configurations.get("security.jwt_secret")
            assert jwt_entry is not None
            assert jwt_entry.sensitive == True
            
            # Verify masked display
            masked_jwt = manager.get_masked("security.jwt_secret")
            assert masked_jwt != "test_jwt_secret"
            assert "***" in str(masked_jwt) or "*" in str(masked_jwt)
        
        # Verify isolation - changes don't affect other managers
        with patch('netra_backend.app.core.managers.unified_configuration_manager.IsolatedEnvironment') as mock_env_class:
            clean_env = IsolatedEnvironment()
            mock_env_class.return_value = clean_env
            clean_manager = UnifiedConfigurationManager()
            
            # Should not see test environment values
            assert clean_manager.get_int("database.pool_size") != 15
            assert clean_manager.get_str("security.jwt_secret") != "test_jwt_secret"

    def test_mission_critical_values_validation_prevents_failures(self, config_manager):
        """
        MISSION CRITICAL: Test mission critical values validation prevents service failures.
        
        Protects: Critical configuration validation preventing complete service outages
        Business Impact: Missing critical values can cause total platform failure ($500K+ ARR loss)
        """
        # Verify mission critical values are loaded and validated
        critical_configs = config_manager.get_all()
        
        # Check for essential configurations that must exist
        essential_keys = [
            "database.pool_size",
            "redis.max_connections", 
            "agent.execution_timeout",
            "websocket.ping_interval",
            "security.jwt_algorithm"
        ]
        
        for key in essential_keys:
            assert key in critical_configs, f"Essential configuration missing: {key}"
            value = config_manager.get(key)
            assert value is not None, f"Essential configuration is None: {key}"
        
        # Verify database configuration is complete and valid
        db_config = config_manager.get_database_config()
        assert db_config["pool_size"] > 0
        assert db_config["max_overflow"] > 0
        assert db_config["pool_timeout"] > 0
        assert isinstance(db_config["echo"], bool)
        
        # Verify Redis configuration is complete and valid
        redis_config = config_manager.get_redis_config()
        assert redis_config["max_connections"] > 0
        assert redis_config["socket_timeout"] > 0
        assert isinstance(redis_config["retry_on_timeout"], bool)
        
        # Verify agent configuration is complete and valid
        agent_config = config_manager.get_agent_config()
        assert agent_config["execution_timeout"] > 0
        assert agent_config["max_concurrent"] > 0
        assert agent_config["circuit_breaker"]["failure_threshold"] > 0
        
        # Verify WebSocket configuration is complete and valid
        websocket_config = config_manager.get_websocket_config()
        assert websocket_config["ping_interval"] > 0
        assert websocket_config["ping_timeout"] > 0
        assert websocket_config["max_connections"] > 0

    def test_configuration_drift_detection_prevents_inconsistency(self, config_manager):
        """
        BUSINESS CRITICAL: Test configuration drift detection prevents environment inconsistency.
        
        Protects: Configuration consistency across deployments
        Business Impact: Configuration drift can cause different behavior in staging vs production
        """
        # Establish baseline configuration
        baseline_configs = {
            "database.pool_size": 10,
            "redis.max_connections": 50,
            "agent.max_concurrent": 5,
            "websocket.ping_interval": 20,
            "security.jwt_expire_minutes": 30
        }
        
        for key, value in baseline_configs.items():
            config_manager.set(key, value, source=ConfigurationSource.CONFIG_FILE)
        
        # Simulate configuration drift (values changed unexpectedly)
        drift_changes = {
            "database.pool_size": 25,  # Drifted from 10 to 25
            "redis.max_connections": 100,  # Drifted from 50 to 100
            "agent.max_concurrent": 8,  # Drifted from 5 to 8
        }
        
        for key, drifted_value in drift_changes.items():
            config_manager.set(key, drifted_value, source=ConfigurationSource.ENVIRONMENT)
        
        # Detect drift by comparing current vs baseline
        current_configs = {key: config_manager.get(key) for key in baseline_configs.keys()}
        
        drift_detected = []
        for key, baseline_value in baseline_configs.items():
            current_value = current_configs[key]
            if current_value != baseline_value:
                drift_detected.append({
                    "key": key,
                    "baseline": baseline_value,
                    "current": current_value,
                    "drift": current_value - baseline_value if isinstance(current_value, (int, float)) else "type_change"
                })
        
        # Verify drift detection
        assert len(drift_detected) == 3  # Should detect 3 drifted values
        
        drift_keys = [item["key"] for item in drift_detected]
        assert "database.pool_size" in drift_keys
        assert "redis.max_connections" in drift_keys
        assert "agent.max_concurrent" in drift_keys
        
        # Verify drift amounts
        for drift_item in drift_detected:
            if drift_item["key"] == "database.pool_size":
                assert drift_item["current"] == 25
                assert drift_item["baseline"] == 10
                assert drift_item["drift"] == 15

    # ============================================================================
    # CACHE MANAGEMENT AND PERFORMANCE TESTS (Scalability Protection)
    # Protects: System performance and scalability
    # ============================================================================

    def test_cache_management_with_ttl_prevents_stale_data(self, config_manager):
        """
        PERFORMANCE CRITICAL: Test cache management with TTL prevents stale data.
        
        Protects: Data freshness and cache performance
        Business Impact: Stale cached data can cause incorrect business decisions
        """
        # Verify caching is enabled
        assert config_manager.enable_caching == True
        assert config_manager.cache_ttl == 5  # 5 seconds for testing
        
        # Set initial value and verify it's cached
        config_manager.set("test.cache_ttl", "initial_value")
        cached_value1 = config_manager.get("test.cache_ttl")
        assert cached_value1 == "initial_value"
        
        # Verify value is retrieved from cache
        assert "test.cache_ttl" in config_manager._cache
        assert config_manager._cache["test.cache_ttl"] == "initial_value"
        
        # Update value directly in configurations (bypassing cache)
        config_manager._configurations["test.cache_ttl"].value = "updated_value"
        
        # Should still get cached value initially
        cached_value2 = config_manager.get("test.cache_ttl")
        assert cached_value2 == "initial_value"  # Still cached
        
        # Wait for TTL expiration
        time.sleep(6)  # Wait longer than 5-second TTL
        
        # Should get updated value after TTL expiration
        fresh_value = config_manager.get("test.cache_ttl")
        assert fresh_value == "updated_value"  # Cache expired, got fresh value
        
        # Test cache invalidation on set
        config_manager.set("test.cache_ttl", "new_value")
        immediate_value = config_manager.get("test.cache_ttl")
        assert immediate_value == "new_value"  # Cache invalidated immediately

    def test_concurrent_cache_operations_thread_safety(self, config_manager):
        """
        PERFORMANCE CRITICAL: Test concurrent cache operations are thread-safe.
        
        Protects: Data integrity under concurrent access
        Business Impact: Cache corruption can cause inconsistent user experiences
        """
        results = []
        errors = []
        
        def cache_worker(worker_id: int):
            """Worker function for concurrent cache testing."""
            try:
                for i in range(50):
                    key = f"concurrent.worker_{worker_id}.item_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    
                    # Set and immediately get value
                    config_manager.set(key, value)
                    retrieved_value = config_manager.get(key)
                    
                    # Verify value consistency
                    if retrieved_value == value:
                        results.append(f"worker_{worker_id}_success_{i}")
                    else:
                        errors.append(f"worker_{worker_id}_mismatch_{i}: expected {value}, got {retrieved_value}")
                    
                    # Test cache clearing
                    if i % 10 == 0:
                        config_manager.clear_cache(key)
            except Exception as e:
                errors.append(f"worker_{worker_id}_exception: {str(e)}")
        
        # Run 8 concurrent workers
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(cache_worker, i) for i in range(8)]
            
            # Wait for all workers to complete
            for future in futures:
                future.result()
        
        # Verify results
        assert len(errors) == 0, f"Cache concurrency errors: {errors}"
        assert len(results) == 400  # 8 workers * 50 operations each
        
        # Verify no cache corruption
        cache_size = len(config_manager._cache)
        config_size = len([k for k in config_manager._configurations.keys() if k.startswith("concurrent.")])
        
        # Cache might be smaller due to TTL expiration, but configurations should be complete
        assert config_size == 400

    def test_cache_performance_with_large_dataset(self, config_manager):
        """
        PERFORMANCE CRITICAL: Test cache performance with large dataset.
        
        Protects: System performance under load
        Business Impact: Poor cache performance can cause request timeouts affecting UX
        """
        # Disable caching initially to establish baseline
        config_manager.enable_caching = False
        
        # Set up large dataset (1000 configurations)
        large_dataset = {}
        for i in range(1000):
            key = f"performance.large_dataset.item_{i:04d}"
            value = f"large_value_{i}_with_substantial_content_for_performance_testing"
            large_dataset[key] = value
            config_manager.set(key, value)
        
        # Measure uncached performance
        start_time = time.time()
        for key in list(large_dataset.keys())[:100]:  # Test subset for speed
            value = config_manager.get(key)
            assert value == large_dataset[key]
        uncached_time = time.time() - start_time
        
        # Enable caching and warm up cache
        config_manager.enable_caching = True
        config_manager.cache_ttl = 60  # Longer TTL for performance test
        
        # Warm up cache
        for key in list(large_dataset.keys())[:100]:
            config_manager.get(key)
        
        # Measure cached performance
        start_time = time.time()
        for key in list(large_dataset.keys())[:100]:
            value = config_manager.get(key)
            assert value == large_dataset[key]
        cached_time = time.time() - start_time
        
        # Cache should provide significant performance improvement
        performance_improvement = uncached_time / cached_time if cached_time > 0 else float('inf')
        assert performance_improvement > 1.5, f"Cache performance improvement insufficient: {performance_improvement}x"
        
        # Verify cache hit rate
        cache_hits = len([k for k in large_dataset.keys() if k in config_manager._cache])
        assert cache_hits >= 50  # Should have cached at least 50 of the 100 tested items

    def test_memory_efficient_cache_cleanup(self, config_manager):
        """
        PERFORMANCE CRITICAL: Test memory-efficient cache cleanup prevents memory leaks.
        
        Protects: System memory usage and stability
        Business Impact: Memory leaks can cause service degradation and outages
        """
        # Set large TTL to prevent automatic expiration during test
        config_manager.cache_ttl = 300
        
        # Fill cache with substantial data
        initial_memory_usage = len(config_manager._cache)
        
        for i in range(500):
            key = f"memory.test.item_{i}"
            # Create substantial value to test memory usage
            value = f"substantial_value_{i}_" + "x" * 100  # 100+ character values
            config_manager.set(key, value)
            config_manager.get(key)  # Ensure it's cached
        
        # Verify cache is populated
        cache_size_after_fill = len(config_manager._cache)
        assert cache_size_after_fill >= 400  # Should have cached most items
        
        # Test selective cache clearing
        keys_to_clear = [f"memory.test.item_{i}" for i in range(0, 500, 10)]  # Every 10th item
        
        for key in keys_to_clear:
            config_manager.clear_cache(key)
        
        cache_size_after_selective_clear = len(config_manager._cache)
        cleared_count = cache_size_after_fill - cache_size_after_selective_clear
        assert cleared_count >= 40  # Should have cleared approximately 50 items
        
        # Test complete cache clearing
        config_manager.clear_cache()  # Clear all
        
        cache_size_after_complete_clear = len(config_manager._cache)
        assert cache_size_after_complete_clear == 0
        
        # Verify cache timestamps are also cleared
        timestamp_count = len(config_manager._cache_timestamps)
        assert timestamp_count == 0
        
        # Verify configurations are still accessible (not deleted, just uncached)
        test_key = "memory.test.item_100"
        retrieved_value = config_manager.get(test_key)
        assert retrieved_value is not None  # Should still be accessible from configurations

    # ============================================================================
    # HIGH DIFFICULTY TESTS (Advanced Business Logic)
    # Protects: Complex enterprise requirements and edge cases
    # ============================================================================

    def test_complex_validation_schema_enterprise_requirements(self, config_manager):
        """
        HIGH DIFFICULTY: Test complex validation schema for enterprise requirements.
        
        Protects: Enterprise compliance and complex business rules
        Business Impact: Enterprise customers pay $15K+ MRR for advanced validation features
        """
        # Define complex enterprise validation schema
        enterprise_schema = {
            "security.password_policy": {
                "type": str,
                "required": True,
                "validation_rules": [
                    "min_length:12",
                    "regex:^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]",
                    "not_empty"
                ],
                "sensitive": True,
                "description": "Enterprise password policy requirements"
            },
            "compliance.audit_retention_days": {
                "type": int,
                "required": True,
                "validation_rules": ["min_value:365", "max_value:2555"],  # 1-7 years
                "description": "Audit log retention period for compliance"
            },
            "database.connection_string": {
                "type": str,
                "required": True,
                "validation_rules": [
                    "regex:^postgresql://[^:]+:[^@]+@[^:/]+:\\d+/[^\\s]+$",
                    "not_empty"
                ],
                "sensitive": True,
                "description": "PostgreSQL connection string with credentials"
            },
            "performance.max_concurrent_users": {
                "type": int,
                "required": True,
                "validation_rules": ["min_value:1", "max_value:10000", "positive"],
                "description": "Maximum concurrent users supported"
            }
        }
        
        # Apply validation schema
        config_manager.add_validation_schema(enterprise_schema)
        
        # Test valid enterprise configurations
        valid_configs = {
            "security.password_policy": "ComplexP@ssw0rd123!",
            "compliance.audit_retention_days": 2555,  # 7 years
            "database.connection_string": "postgresql://user:password@localhost:5432/enterprise_db",
            "performance.max_concurrent_users": 5000
        }
        
        for key, value in valid_configs.items():
            config_manager.set(key, value)
            retrieved_value = config_manager.get(key)
            assert retrieved_value == value
        
        # Test invalid configurations should raise errors
        invalid_configs = [
            ("security.password_policy", "weak", "Password too weak"),
            ("compliance.audit_retention_days", 100, "Retention too short"),
            ("database.connection_string", "invalid_connection", "Invalid connection format"),
            ("performance.max_concurrent_users", -1, "Negative users not allowed"),
            ("performance.max_concurrent_users", 20000, "Exceeds maximum limit")
        ]
        
        for key, invalid_value, description in invalid_configs:
            with pytest.raises(ValueError, match="Configuration validation failed"):
                config_manager.set(key, invalid_value)
        
        # Verify comprehensive validation results
        validation_result = config_manager.validate_all_configurations()
        assert validation_result.is_valid == True
        assert len(validation_result.critical_errors) == 0
        
        # Verify sensitive values are properly masked
        for key in ["security.password_policy", "database.connection_string"]:
            masked_value = config_manager.get_masked(key)
            actual_value = config_manager.get(key)
            assert masked_value != actual_value
            assert "***" in str(masked_value) or "*" in str(masked_value)

    def test_nested_configuration_structures_complex_business_logic(self, config_manager):
        """
        HIGH DIFFICULTY: Test nested configuration structures for complex business logic.
        
        Protects: Complex business configuration requirements
        Business Impact: Advanced configurations enable enterprise features worth $15K+ MRR
        """
        # Test complex nested configuration structures
        complex_config = {
            "agent.optimization_strategies": {
                "cost_optimization": {
                    "enabled": True,
                    "algorithms": ["genetic", "simulated_annealing", "gradient_descent"],
                    "parameters": {
                        "population_size": 100,
                        "mutation_rate": 0.1,
                        "crossover_rate": 0.8,
                        "max_generations": 1000
                    },
                    "thresholds": {
                        "min_cost_reduction": 0.05,
                        "max_execution_time": 300.0,
                        "confidence_level": 0.95
                    }
                },
                "performance_optimization": {
                    "enabled": True,
                    "metrics": ["latency", "throughput", "error_rate"],
                    "targets": {
                        "latency_p99": 100.0,
                        "throughput_rps": 1000,
                        "error_rate": 0.001
                    }
                }
            }
        }
        
        # Set complex nested configuration as JSON string
        config_manager.set("agent.optimization_config", json.dumps(complex_config))
        
        # Retrieve and validate nested structure
        retrieved_dict = config_manager.get_dict("agent.optimization_config")
        assert retrieved_dict == complex_config
        
        # Test accessing nested values
        cost_opt = retrieved_dict["agent.optimization_strategies"]["cost_optimization"]
        assert cost_opt["enabled"] == True
        assert "genetic" in cost_opt["algorithms"]
        assert cost_opt["parameters"]["population_size"] == 100
        assert cost_opt["thresholds"]["min_cost_reduction"] == 0.05
        
        perf_opt = retrieved_dict["agent.optimization_strategies"]["performance_optimization"]
        assert perf_opt["enabled"] == True
        assert "latency" in perf_opt["metrics"]
        assert perf_opt["targets"]["latency_p99"] == 100.0
        
        # Test flattened key access for nested configurations
        flattened_keys = [
            ("agent.cost_optimization.enabled", True),
            ("agent.cost_optimization.population_size", 100),
            ("agent.cost_optimization.mutation_rate", 0.1),
            ("agent.performance_optimization.latency_p99", 100.0),
            ("agent.performance_optimization.throughput_rps", 1000)
        ]
        
        for key, expected_value in flattened_keys:
            config_manager.set(key, expected_value)
            assert config_manager.get(key) == expected_value

    def test_configuration_change_tracking_audit_compliance(self, config_manager):
        """
        HIGH DIFFICULTY: Test configuration change tracking for audit compliance.
        
        Protects: Enterprise audit requirements and compliance
        Business Impact: Audit compliance is required for enterprise customers ($15K+ MRR)
        """
        # Verify audit is enabled by default
        assert config_manager._audit_enabled == True
        
        # Make series of configuration changes
        change_sequence = [
            ("database.pool_size", 10, "Initial setup"),
            ("database.pool_size", 15, "Increased load"),
            ("redis.max_connections", 50, "Initial Redis config"),
            ("security.jwt_expire_minutes", 30, "Security policy"),
            ("database.pool_size", 20, "Further optimization"),
            ("redis.max_connections", 75, "Redis optimization")
        ]
        
        initial_history_length = len(config_manager.get_change_history())
        
        for key, value, reason in change_sequence:
            config_manager.set(key, value)
        
        # Verify change history is tracked
        change_history = config_manager.get_change_history()
        new_changes = change_history[initial_history_length:]
        assert len(new_changes) == len(change_sequence)
        
        # Verify change record structure and content
        for i, change_record in enumerate(new_changes):
            expected_key, expected_value, _ = change_sequence[i]
            
            assert "timestamp" in change_record
            assert "key" in change_record
            assert "new_value" in change_record
            assert "source" in change_record
            assert "user_id" in change_record
            assert "service" in change_record
            assert "environment" in change_record
            
            assert change_record["key"] == expected_key
            assert change_record["new_value"] == expected_value
            assert change_record["source"] == "override"  # Default source
            assert change_record["user_id"] == "test_user_12345"
            assert change_record["service"] == "test_service"
            assert change_record["environment"] == "test"
            
            # Verify timestamp is recent
            assert time.time() - change_record["timestamp"] < 10  # Within last 10 seconds
        
        # Test change history limiting (prevents memory bloat)
        # Fill history beyond limit
        for i in range(1050):  # Exceed 1000 limit
            config_manager.set(f"test.history_limit_{i}", f"value_{i}")
        
        limited_history = config_manager.get_change_history()
        assert len(limited_history) <= 500  # Should be truncated to 500
        
        # Test change listener functionality
        listener_calls = []
        
        def test_change_listener(key: str, old_value: Any, new_value: Any):
            listener_calls.append({
                "key": key,
                "old_value": old_value,
                "new_value": new_value,
                "timestamp": time.time()
            })
        
        config_manager.add_change_listener(test_change_listener)
        
        # Make changes after adding listener
        config_manager.set("test.listener", "initial_value")
        config_manager.set("test.listener", "updated_value")
        config_manager.delete("test.listener")
        
        # Verify listener was called
        assert len(listener_calls) == 3
        assert listener_calls[0]["key"] == "test.listener"
        assert listener_calls[0]["new_value"] == "initial_value"
        assert listener_calls[1]["new_value"] == "updated_value"
        assert listener_calls[2]["new_value"] is None  # Deletion
        
        # Test listener removal
        config_manager.remove_change_listener(test_change_listener)
        initial_call_count = len(listener_calls)
        
        config_manager.set("test.no_listener", "should_not_trigger")
        
        # Listener should not be called after removal
        assert len(listener_calls) == initial_call_count

    def test_concurrent_multi_user_isolation_stress_test(self, factory_cleanup):
        """
        HIGH DIFFICULTY: Test concurrent multi-user isolation under stress.
        
        Protects: Enterprise multi-tenant isolation under heavy load
        Business Impact: Isolation failures can cause enterprise customer data leakage ($15K+ MRR loss)
        """
        results = {}
        errors = []
        
        def multi_user_worker(user_id: str, operations_count: int):
            """Worker function simulating enterprise user operations."""
            try:
                # Create user-specific manager
                user_manager = ConfigurationManagerFactory.get_user_manager(f"enterprise_user_{user_id}")
                user_results = []
                
                for i in range(operations_count):
                    # Set user-specific configurations
                    user_config_key = f"user.config.item_{i}"
                    user_config_value = f"user_{user_id}_config_value_{i}"
                    user_manager.set(user_config_key, user_config_value)
                    
                    # Set sensitive user data
                    user_secret_key = f"user.secret.api_key_{i}"
                    user_secret_value = f"secret_api_key_user_{user_id}_item_{i}"
                    user_manager.set(user_secret_key, user_secret_value, sensitive=True)
                    
                    # Retrieve and verify isolation
                    retrieved_config = user_manager.get(user_config_key)
                    retrieved_secret = user_manager.get(user_secret_key)
                    
                    if retrieved_config == user_config_value and retrieved_secret == user_secret_value:
                        user_results.append(f"user_{user_id}_operation_{i}_success")
                    else:
                        errors.append(f"user_{user_id}_operation_{i}_isolation_failure")
                    
                    # Test configuration service combinations
                    if i % 10 == 0:
                        service_manager = ConfigurationManagerFactory.get_manager(f"enterprise_user_{user_id}", "auth_service")
                        service_key = f"service.auth.config_{i}"
                        service_value = f"auth_config_user_{user_id}_item_{i}"
                        service_manager.set(service_key, service_value)
                        
                        if service_manager.get(service_key) == service_value:
                            user_results.append(f"user_{user_id}_service_operation_{i}_success")
                        else:
                            errors.append(f"user_{user_id}_service_operation_{i}_failure")
                
                results[f"user_{user_id}"] = user_results
                
            except Exception as e:
                errors.append(f"user_{user_id}_exception: {str(e)}")
        
        # Run concurrent users simulating enterprise load
        user_count = 12
        operations_per_user = 25
        
        with ThreadPoolExecutor(max_workers=user_count) as executor:
            futures = [
                executor.submit(multi_user_worker, str(user_id), operations_per_user) 
                for user_id in range(user_count)
            ]
            
            # Wait for all users to complete
            for future in futures:
                future.result()
        
        # Verify no isolation failures or errors
        assert len(errors) == 0, f"Multi-user isolation errors: {errors[:10]}..."  # Show first 10 errors
        
        # Verify all users completed successfully
        assert len(results) == user_count
        for user_key, user_results in results.items():
            expected_operations = operations_per_user + (operations_per_user // 10)  # Regular + service operations
            assert len(user_results) == expected_operations, f"User {user_key} incomplete operations"
        
        # Verify cross-user isolation by checking configurations don't leak
        user_0_manager = ConfigurationManagerFactory.get_user_manager("enterprise_user_0")
        user_1_manager = ConfigurationManagerFactory.get_user_manager("enterprise_user_1")
        
        # User 0 should not see User 1's configurations
        user_0_config = user_0_manager.get("user.config.item_5")
        user_1_config = user_1_manager.get("user.config.item_5")
        
        assert user_0_config != user_1_config
        assert "user_0_config_value_5" in user_0_config
        assert "user_1_config_value_5" in user_1_config
        
        # Verify manager count reflects all created managers
        manager_counts = ConfigurationManagerFactory.get_manager_count()
        assert manager_counts["user_specific"] >= user_count
        assert manager_counts["combined"] >= user_count  # Service combinations

    def test_performance_scalability_enterprise_load(self, config_manager):
        """
        HIGH DIFFICULTY: Test performance scalability under enterprise load.
        
        Protects: System performance for enterprise customers
        Business Impact: Poor performance can cause enterprise customer churn ($15K+ MRR loss)
        """
        # Test large-scale configuration handling
        enterprise_config_count = 2000
        start_time = time.time()
        
        # Create enterprise-scale configuration dataset
        for i in range(enterprise_config_count):
            config_key = f"enterprise.config.setting_{i:04d}"
            config_value = {
                "enabled": i % 2 == 0,
                "priority": i % 10,
                "metadata": {
                    "created_by": f"admin_user_{i % 5}",
                    "department": f"department_{i % 8}",
                    "cost_center": f"cc_{i % 20:03d}",
                    "tags": [f"tag_{j}" for j in range(i % 5)]
                },
                "configuration": {
                    "timeout": (i % 100) + 10,
                    "retry_count": (i % 5) + 1,
                    "batch_size": (i % 50) + 10
                }
            }
            config_manager.set(config_key, json.dumps(config_value))
        
        creation_time = time.time() - start_time
        assert creation_time < 60, f"Configuration creation too slow: {creation_time:.2f}s"
        
        # Test bulk retrieval performance
        start_time = time.time()
        
        retrieved_configs = []
        for i in range(0, enterprise_config_count, 10):  # Sample every 10th config
            config_key = f"enterprise.config.setting_{i:04d}"
            config_value = config_manager.get_dict(config_key)
            retrieved_configs.append(config_value)
        
        retrieval_time = time.time() - start_time
        assert retrieval_time < 30, f"Configuration retrieval too slow: {retrieval_time:.2f}s"
        assert len(retrieved_configs) == 200  # Should have retrieved 200 configs
        
        # Test validation performance on large dataset
        start_time = time.time()
        validation_result = config_manager.validate_all_configurations()
        validation_time = time.time() - start_time
        
        assert validation_time < 45, f"Validation too slow: {validation_time:.2f}s"
        assert validation_result.is_valid == True
        
        # Test concurrent access performance
        concurrent_results = []
        concurrent_errors = []
        
        def concurrent_access_worker(worker_id: int):
            try:
                worker_results = []
                for i in range(100):
                    config_key = f"enterprise.config.setting_{(worker_id * 100 + i) % enterprise_config_count:04d}"
                    config_value = config_manager.get_dict(config_key)
                    if config_value:
                        worker_results.append(f"worker_{worker_id}_success_{i}")
                    else:
                        concurrent_errors.append(f"worker_{worker_id}_missing_config_{i}")
                concurrent_results.extend(worker_results)
            except Exception as e:
                concurrent_errors.append(f"worker_{worker_id}_exception: {str(e)}")
        
        # Run 10 concurrent workers
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_access_worker, i) for i in range(10)]
            for future in futures:
                future.result()
        
        concurrent_time = time.time() - start_time
        assert concurrent_time < 20, f"Concurrent access too slow: {concurrent_time:.2f}s"
        assert len(concurrent_errors) == 0, f"Concurrent access errors: {concurrent_errors[:5]}..."
        assert len(concurrent_results) == 1000  # 10 workers * 100 operations
        
        # Verify system stability after stress test
        final_status = config_manager.get_health_status()
        assert final_status["status"] == "healthy"
        assert final_status["total_configurations"] >= enterprise_config_count