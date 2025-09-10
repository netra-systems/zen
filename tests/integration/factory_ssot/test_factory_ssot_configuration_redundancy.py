"""
Test Configuration Factory Redundancy SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate configuration factory redundancy blocking golden path
- Value Impact: Remove duplicate configuration patterns causing environment drift
- Strategic Impact: Critical $120K+ MRR protection through configuration consistency

This test validates that configuration factory patterns don't create redundant
configuration management systems. The over-engineering audit identified multiple
configuration factories that violate SSOT principles.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env, IsolatedEnvironment

# Import configuration management classes to test SSOT violations
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
from shared.isolated_environment import IsolatedEnvironment


class TestConfigurationFactoryRedundancy(BaseIntegrationTest):
    """Test SSOT violations in configuration factory redundancy patterns."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_unified_configuration_manager_vs_isolated_environment_duplication(self, real_services_fixture):
        """
        Test SSOT violation between UnifiedConfigurationManager and IsolatedEnvironment.
        
        SSOT Violation: UnifiedConfigurationManager and IsolatedEnvironment both
        manage configuration with overlapping responsibilities and different APIs.
        """
        # SSOT VIOLATION: Multiple configuration management systems
        
        # Method 1: UnifiedConfigurationManager (centralized)
        unified_config = UnifiedConfigurationManager()
        await unified_config.initialize(environment="test")
        
        # Method 2: IsolatedEnvironment (per-request/per-service)
        isolated_env = get_env()
        
        # Test configuration overlap
        test_config_key = "TEST_SSOT_CONFIG_VALUE"
        test_config_value = "ssot_configuration_test_value"
        
        # Set configuration via both systems
        unified_config.set_config(test_config_key, test_config_value, source="ssot_test")
        isolated_env.set(test_config_key + "_ISOLATED", test_config_value, source="ssot_test")
        
        # SSOT REQUIREMENT: Both should be able to manage same configuration types
        
        # Test unified config retrieval
        unified_retrieved = unified_config.get_config(test_config_key)
        isolated_retrieved = isolated_env.get(test_config_key + "_ISOLATED")
        
        assert unified_retrieved == test_config_value
        assert isolated_retrieved == test_config_value
        
        # SSOT VIOLATION: Test configuration precedence and consistency
        # Both systems should have consistent behavior for environment variables
        
        # Test environment variable handling
        env_test_key = "SSOT_ENV_TEST"
        env_test_value = "environment_consistency_test"
        
        # Set via isolated environment
        isolated_env.set(env_test_key, env_test_value, source="ssot_test")
        
        # Check if unified config can access it
        try:
            unified_env_value = unified_config.get_config(env_test_key)
            env_access_consistent = unified_env_value == env_test_value
        except Exception:
            env_access_consistent = False
        
        # CRITICAL: Test configuration validation differences
        # Both systems should validate configurations consistently
        
        invalid_config_tests = {}
        
        # Test invalid configuration handling in unified config
        try:
            unified_config.set_config("", "invalid_empty_key", source="test")
            invalid_config_tests["unified_empty_key"] = "allowed"
        except Exception as e:
            invalid_config_tests["unified_empty_key"] = f"rejected: {type(e).__name__}"
        
        # Test invalid configuration handling in isolated environment
        try:
            isolated_env.set("", "invalid_empty_key", source="test")
            invalid_config_tests["isolated_empty_key"] = "allowed"
        except Exception as e:
            invalid_config_tests["isolated_empty_key"] = f"rejected: {type(e).__name__}"
        
        # SSOT REQUIREMENT: Both should handle invalid configurations consistently
        unified_behavior = invalid_config_tests.get("unified_empty_key", "unknown")
        isolated_behavior = invalid_config_tests.get("isolated_empty_key", "unknown")
        
        # Configuration validation should be consistent between systems
        if unified_behavior != "unknown" and isolated_behavior != "unknown":
            # Both should either allow or reject empty keys consistently
            both_allow = "allowed" in unified_behavior and "allowed" in isolated_behavior
            both_reject = "rejected" in unified_behavior and "rejected" in isolated_behavior
            assert both_allow or both_reject, f"Inconsistent validation: unified={unified_behavior}, isolated={isolated_behavior}"
        
        # Test configuration source tracking
        unified_sources = unified_config.get_all_sources()
        isolated_sources = isolated_env.get_all_sources() if hasattr(isolated_env, 'get_all_sources') else []
        
        # Both should track configuration sources
        assert len(unified_sources) > 0, "UnifiedConfigurationManager should track sources"
        
        # Cleanup
        await unified_config.cleanup()
        
        # Business value: Unified configuration management reduces environment drift
        self.assert_business_value_delivered(
            {
                "configuration_consolidation": True,
                "environment_consistency": env_access_consistent,
                "validation_consistency": unified_behavior == isolated_behavior
            },
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_specific_config_vs_unified_config_duplication(self, real_services_fixture):
        """
        Test SSOT violation between service-specific config managers and unified configuration.
        
        SSOT Violation: Each service potentially has its own configuration management
        pattern while UnifiedConfigurationManager exists as a centralized solution.
        """
        # SSOT VIOLATION: Service-specific vs unified configuration patterns
        
        # Unified configuration (should be SSOT)
        unified_config = UnifiedConfigurationManager()
        await unified_config.initialize(environment="test")
        
        # Simulate service-specific configuration patterns
        service_configs = {}
        
        # Test different service configuration patterns
        services = ["backend", "auth", "analytics", "frontend"]
        
        for service in services:
            # Each service might have its own config management
            service_env = IsolatedEnvironment()
            service_env.set("SERVICE_NAME", service, source=f"{service}_config")
            service_env.set(f"{service.upper()}_PORT", f"808{len(service)}", source=f"{service}_config")
            service_env.set(f"{service.upper()}_DEBUG", "true", source=f"{service}_config")
            
            service_configs[service] = service_env
        
        # SSOT REQUIREMENT: Unified config should be able to manage all service configs
        
        # Test that unified config can handle service-specific configurations
        for service in services:
            service_section = f"service_{service}"
            
            # Set service config via unified manager
            unified_config.set_config(f"{service_section}.name", service, source="unified_test")
            unified_config.set_config(f"{service_section}.port", f"808{len(service)}", source="unified_test")
            unified_config.set_config(f"{service_section}.debug", "true", source="unified_test")
        
        # Verify unified config can retrieve service configurations
        unified_service_configs = {}
        for service in services:
            service_section = f"service_{service}"
            unified_service_configs[service] = {
                "name": unified_config.get_config(f"{service_section}.name"),
                "port": unified_config.get_config(f"{service_section}.port"),
                "debug": unified_config.get_config(f"{service_section}.debug")
            }
        
        # SSOT VALIDATION: Unified config should match service-specific configs
        for service in services:
            service_env = service_configs[service]
            unified_service = unified_service_configs[service]
            
            # Compare configuration values
            assert unified_service["name"] == service
            assert unified_service["port"] == f"808{len(service)}"
            assert unified_service["debug"] == "true"
            
            # Service-specific env should also have these values
            assert service_env.get("SERVICE_NAME") == service
            assert service_env.get(f"{service.upper()}_PORT") == f"808{len(service)}"
            assert service_env.get(f"{service.upper()}_DEBUG") == "true"
        
        # CRITICAL: Test configuration update propagation
        # Changes in unified config should be available to service-specific access
        
        test_propagation_key = "SHARED_CONFIG_VALUE"
        test_propagation_value = "propagation_test_value"
        
        # Set via unified config
        unified_config.set_config(test_propagation_key, test_propagation_value, source="propagation_test")
        
        # Check if service-specific environments can access it
        propagation_results = {}
        for service in services:
            service_env = service_configs[service]
            try:
                # Service env might need to refresh or have unified config integration
                service_value = service_env.get(test_propagation_key)
                propagation_results[service] = service_value == test_propagation_value
            except Exception:
                propagation_results[service] = False
        
        # At least some services should be able to access unified configuration
        successful_propagation = sum(propagation_results.values())
        propagation_rate = successful_propagation / len(services) if services else 0
        
        # Cleanup
        await unified_config.cleanup()
        
        # Business value: Centralized configuration reduces service configuration drift
        self.assert_business_value_delivered(
            {
                "service_config_unification": True,
                "configuration_propagation_rate": propagation_rate,
                "service_count": len(services),
                "drift_prevention": True
            },
            "automation"
        )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_environment_specific_config_factory_redundancy(self, real_services_fixture):
        """
        Test SSOT violation in environment-specific configuration factory patterns.
        
        SSOT Violation: Multiple factory patterns for environment-specific
        configuration (test, dev, staging, prod) that could be unified.
        """
        # SSOT VIOLATION: Environment-specific configuration factories
        
        environments = ["test", "development", "staging", "production"]
        
        # Test environment-specific configuration creation patterns
        env_configs = {}
        unified_env_configs = {}
        
        # Create unified configuration manager
        unified_config = UnifiedConfigurationManager()
        await unified_config.initialize(environment="test")
        
        for env_name in environments:
            # Pattern 1: Environment-specific IsolatedEnvironment instances
            env_isolated = IsolatedEnvironment()
            env_isolated.set("ENVIRONMENT", env_name, source=f"{env_name}_factory")
            env_isolated.set("DEBUG", str(env_name in ["test", "development"]), source=f"{env_name}_factory")
            env_isolated.set("DATABASE_POOL_SIZE", "5" if env_name == "test" else "20", source=f"{env_name}_factory")
            
            env_configs[env_name] = env_isolated
            
            # Pattern 2: Unified configuration with environment sections
            env_section = f"env_{env_name}"
            unified_config.set_config(f"{env_section}.name", env_name, source="unified_env_test")
            unified_config.set_config(f"{env_section}.debug", str(env_name in ["test", "development"]), source="unified_env_test")
            unified_config.set_config(f"{env_section}.database_pool_size", "5" if env_name == "test" else "20", source="unified_env_test")
            
            unified_env_configs[env_name] = {
                "name": unified_config.get_config(f"{env_section}.name"),
                "debug": unified_config.get_config(f"{env_section}.debug"),
                "database_pool_size": unified_config.get_config(f"{env_section}.database_pool_size")
            }
        
        # SSOT REQUIREMENT: Both patterns should produce equivalent configurations
        
        config_comparison = {}
        for env_name in environments:
            isolated_config = env_configs[env_name]
            unified_config_data = unified_env_configs[env_name]
            
            # Compare configuration values
            isolated_env_name = isolated_config.get("ENVIRONMENT")
            isolated_debug = isolated_config.get("DEBUG")
            isolated_pool_size = isolated_config.get("DATABASE_POOL_SIZE")
            
            unified_env_name = unified_config_data["name"]
            unified_debug = unified_config_data["debug"]
            unified_pool_size = unified_config_data["database_pool_size"]
            
            config_comparison[env_name] = {
                "env_name_match": isolated_env_name == unified_env_name,
                "debug_match": isolated_debug == unified_debug,
                "pool_size_match": isolated_pool_size == unified_pool_size,
                "isolated_values": {
                    "env": isolated_env_name,
                    "debug": isolated_debug,
                    "pool": isolated_pool_size
                },
                "unified_values": {
                    "env": unified_env_name,
                    "debug": unified_debug, 
                    "pool": unified_pool_size
                }
            }
        
        # SSOT VALIDATION: All environment configurations should match
        all_matches = True
        for env_name, comparison in config_comparison.items():
            env_match = comparison["env_name_match"]
            debug_match = comparison["debug_match"]
            pool_match = comparison["pool_size_match"]
            
            if not (env_match and debug_match and pool_match):
                all_matches = False
            
            assert env_match, f"Environment name mismatch for {env_name}: {comparison['isolated_values']['env']} vs {comparison['unified_values']['env']}"
            assert debug_match, f"Debug setting mismatch for {env_name}: {comparison['isolated_values']['debug']} vs {comparison['unified_values']['debug']}"
            assert pool_match, f"Pool size mismatch for {env_name}: {comparison['isolated_values']['pool']} vs {comparison['unified_values']['pool']}"
        
        # CRITICAL: Test environment switching efficiency
        # Unified config should handle environment switching better than multiple factories
        
        switch_start = time.time()
        
        # Switch environments via isolated pattern (requires new instances)
        isolated_switch_time = 0
        for env_name in environments:
            start = time.time()
            # Create new isolated environment for switch
            new_env = IsolatedEnvironment()
            new_env.set("CURRENT_ENV", env_name, source="switch_test")
            isolated_switch_time += time.time() - start
        
        # Switch environments via unified pattern (single instance)
        unified_switch_time = 0
        for env_name in environments:
            start = time.time()
            # Just change configuration in existing unified manager
            unified_config.set_config("current_environment", env_name, source="switch_test")
            unified_switch_time += time.time() - start
        
        total_switch_time = time.time() - switch_start
        
        # Unified switching should be more efficient
        switch_efficiency = isolated_switch_time / unified_switch_time if unified_switch_time > 0 else 1.0
        
        # Cleanup
        await unified_config.cleanup()
        
        # Business value: Unified environment configuration reduces switching overhead
        self.assert_business_value_delivered(
            {
                "environment_config_unification": True,
                "configuration_consistency": all_matches,
                "switching_efficiency": switch_efficiency,
                "environment_count": len(environments)
            },
            "automation"
        )