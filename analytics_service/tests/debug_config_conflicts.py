#!/usr/bin/env python3
"""
Debug script to reproduce and analyze Issue #1062 Analytics Configuration conflicts.

This script demonstrates the specific conflicts between SSOT Configuration migration
and analytics service test expectations.

Run with: python analytics_service/tests/debug_config_conflicts.py
"""

import sys
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def analyze_environment_detection():
    """Analyze environment detection logic conflicts."""
    print("\n" + "="*60)
    print("ENVIRONMENT DETECTION ANALYSIS")
    print("="*60)

    from shared.isolated_environment import get_env
    from analytics_service.analytics_core.config import AnalyticsConfig

    env = get_env()
    env.enable_isolation()
    env.clear_cache()

    # Test default environment detection
    print("\n1. Default Environment Detection:")
    config = AnalyticsConfig()
    print(f"   Expected: development")
    print(f"   Actual:   {config.environment}")
    print(f"   Match:    {config.environment == 'development'}")

    # Test pytest detection
    print(f"\n2. Pytest Detection:")
    print(f"   pytest in sys.modules: {'pytest' in sys.modules}")
    print(f"   _is_development_environment(): {config._is_development_environment()}")

    # Test environment variable override
    print(f"\n3. Environment Variable Test:")
    env.set("ENVIRONMENT", "development")

    # Reset config to test new environment
    import analytics_service.analytics_core.config as config_module
    config_module._config = None

    config = AnalyticsConfig()
    print(f"   ENVIRONMENT set to: development")
    print(f"   config.environment: {config.environment}")
    print(f"   is_development: {config.is_development}")

    env.disable_isolation()

def analyze_port_configuration():
    """Analyze port configuration conflicts."""
    print("\n" + "="*60)
    print("PORT CONFIGURATION ANALYSIS")
    print("="*60)

    from shared.isolated_environment import get_env
    from analytics_service.analytics_core.config import AnalyticsConfig

    env = get_env()
    env.enable_isolation()
    env.clear_cache()

    # Reset config
    import analytics_service.analytics_core.config as config_module
    config_module._config = None

    print("\n1. Default Port Configuration:")
    config = AnalyticsConfig()
    print(f"   Expected service_port: 8090")
    print(f"   Actual service_port:   {config.service_port}")
    print(f"   Expected ClickHouse:   8123 (test expects this)")
    print(f"   Actual ClickHouse:     {config.clickhouse_port}")

    # Test with environment variable
    print(f"\n2. Environment Variable Override:")
    env.set("ANALYTICS_SERVICE_PORT", "8091")
    config_module._config = None
    config = AnalyticsConfig()
    print(f"   ANALYTICS_SERVICE_PORT=8091")
    print(f"   Actual service_port: {config.service_port}")
    print(f"   Expected: 8091, Match: {config.service_port == 8091}")

    env.disable_isolation()

def analyze_database_configuration():
    """Analyze database configuration conflicts."""
    print("\n" + "="*60)
    print("DATABASE CONFIGURATION ANALYSIS")
    print("="*60)

    from shared.isolated_environment import get_env
    from analytics_service.analytics_core.config import AnalyticsConfig

    env = get_env()
    env.enable_isolation()
    env.clear_cache()

    # Reset config
    import analytics_service.analytics_core.config as config_module
    config_module._config = None

    print("\n1. ClickHouse Connection Parameters:")
    # Set test values like the failing test does
    env.set("CLICKHOUSE_HOST", "test-clickhouse")
    env.set("CLICKHOUSE_PORT", "9000")
    env.set("CLICKHOUSE_DATABASE", "test_analytics")
    env.set("CLICKHOUSE_USERNAME", "test_user")
    env.set("CLICKHOUSE_PASSWORD", "test_password")

    config = AnalyticsConfig()
    params = config.get_clickhouse_connection_params()

    expected_params = {
        "host": "test-clickhouse",
        "port": 9000,
        "database": "test_analytics",
        "user": "test_user",
        "password": "test_password",
    }

    print(f"   Expected: {expected_params}")
    print(f"   Actual:   {params}")
    print(f"   Match:    {params == expected_params}")

    if params != expected_params:
        print(f"   Differences:")
        for key in expected_params:
            if key not in params:
                print(f"     Missing key: {key}")
            elif params[key] != expected_params[key]:
                print(f"     {key}: expected={expected_params[key]}, actual={params[key]}")
        for key in params:
            if key not in expected_params:
                print(f"     Extra key: {key} = {params[key]}")

    print("\n2. Redis Connection Parameters:")
    env.set("REDIS_HOST", "test-redis")
    env.set("REDIS_PORT", "6380")
    env.set("REDIS_ANALYTICS_DB", "5")
    env.set("REDIS_PASSWORD", "test_redis_password")

    config_module._config = None
    config = AnalyticsConfig()
    params = config.get_redis_connection_params()

    expected_params = {
        "host": "test-redis",
        "port": 6380,
        "db": 5,
        "password": "test_redis_password",
    }

    print(f"   Expected: {expected_params}")
    print(f"   Actual:   {params}")
    print(f"   Match:    {params == expected_params}")

    if params != expected_params:
        print(f"   Differences:")
        for key in expected_params:
            if key not in params:
                print(f"     Missing key: {key}")
            elif params[key] != expected_params[key]:
                print(f"     {key}: expected={expected_params[key]}, actual={params[key]}")
        for key in params:
            if key not in expected_params:
                print(f"     Extra key: {key} = {params[key]}")

    env.disable_isolation()

def analyze_validation_logic():
    """Analyze configuration validation logic."""
    print("\n" + "="*60)
    print("VALIDATION LOGIC ANALYSIS")
    print("="*60)

    from shared.isolated_environment import get_env
    from analytics_service.analytics_core.config import AnalyticsConfig

    env = get_env()
    env.enable_isolation()
    env.clear_cache()

    # Reset config
    import analytics_service.analytics_core.config as config_module
    config_module._config = None

    print("\n1. Invalid Port Validation Test:")
    env.set("ANALYTICS_SERVICE_PORT", "80")  # Below minimum
    env.set("ENVIRONMENT", "production")

    try:
        config = AnalyticsConfig()
        print(f"   ERROR: Expected ValueError but config was created successfully")
        print(f"   Environment: {config.environment}")
        print(f"   Port: {config.service_port}")
    except ValueError as e:
        print(f"   SUCCESS: ValueError raised as expected: {e}")
    except Exception as e:
        print(f"   ERROR: Unexpected exception: {type(e).__name__}: {e}")

    print(f"\n2. Invalid Batch Size Validation Test:")
    config_module._config = None
    env.set("EVENT_BATCH_SIZE", "0")  # Invalid
    env.set("ENVIRONMENT", "production")

    try:
        config = AnalyticsConfig()
        print(f"   ERROR: Expected ValueError but config was created successfully")
        print(f"   Batch size: {config.event_batch_size}")
    except ValueError as e:
        print(f"   SUCCESS: ValueError raised as expected: {e}")
    except Exception as e:
        print(f"   ERROR: Unexpected exception: {type(e).__name__}: {e}")

    env.disable_isolation()

def analyze_masking_logic():
    """Analyze sensitive value masking logic."""
    print("\n" + "="*60)
    print("MASKING LOGIC ANALYSIS")
    print("="*60)

    from shared.isolated_environment import get_env
    from analytics_service.analytics_core.config import AnalyticsConfig

    env = get_env()
    env.enable_isolation()
    env.clear_cache()

    # Reset config
    import analytics_service.analytics_core.config as config_module
    config_module._config = None

    print("\n1. Sensitive Value Masking Test:")
    env.set("CLICKHOUSE_PASSWORD", "secret_password")
    env.set("REDIS_PASSWORD", "secret_redis_password")
    env.set("ANALYTICS_API_KEY", "secret_api_key")
    env.set("GRAFANA_API_KEY", "secret_grafana_key")

    config = AnalyticsConfig()
    masked_config = config.mask_sensitive_config()

    print(f"   Expected keys with masking:")
    expected_keys = ["clickhouse_password", "redis_password", "api_key", "grafana_api_key"]
    for key in expected_keys:
        if key in masked_config:
            print(f"     {key}: {masked_config[key]} ✓")
        else:
            print(f"     {key}: MISSING ✗")

    print(f"\n   All masked config keys:")
    for key, value in masked_config.items():
        if "password" in key or "key" in key:
            print(f"     {key}: {value}")

    env.disable_isolation()

def main():
    """Run comprehensive conflict analysis."""
    print("ISSUE #1062 ANALYTICS CONFIGURATION CONFLICT ANALYSIS")
    print("Analyzing conflicts between SSOT Configuration migration and analytics service tests")

    try:
        analyze_environment_detection()
        analyze_port_configuration()
        analyze_database_configuration()
        analyze_validation_logic()
        analyze_masking_logic()

        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        print("See TEST_REMEDIATION_PLAN_ISSUE_1062.md for detailed remediation plan")

    except Exception as e:
        logger.error(f"Analysis failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())