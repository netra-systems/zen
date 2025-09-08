#!/usr/bin/env python3
"""Test script to verify the SSOT-compliant config validation."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_ssot_config_validation():
    """Test that config validation uses the central SSOT validator."""
    
    # Set up staging environment
    os.environ['ENVIRONMENT'] = 'staging'
    
    # Set up required staging configs with secure values
    staging_configs = {
        'POSTGRES_HOST': 'db.staging.example.com',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'netra_staging',
        'POSTGRES_USER': 'postgres',
        'POSTGRES_PASSWORD': 'xK9mN2pQ8vL3fR6tY5wA7zE4jH1uG0sD',
        'DATABASE_HOST': 'db.staging.example.com',  # Central validator expects these
        'DATABASE_PORT': '5432',
        'DATABASE_NAME': 'netra_staging',
        'DATABASE_USER': 'postgres',
        'DATABASE_PASSWORD': 'xK9mN2pQ8vL3fR6tY5wA7zE4jH1uG0sD',
        'JWT_SECRET_KEY': 'xK9mN2pQ8vL3fR6tY5wA7zE4jH1uG0sDqW3eR5tY6uI8oP',
        'JWT_SECRET_STAGING': 'xK9mN2pQ8vL3fR6tY5wA7zE4jH1uG0sDqW3eR5tY6uI8oP',
        'SECRET_KEY': 'aB3cD5eF7gH9jK2mN4pQ6rS8tU0vW2xY4zA6bC8dE0fG2hJ',
        'SERVICE_SECRET': 'qW3eR5tY6uI8oP0aS2dF4gH6jK8lZ0xC2vB4nM6qW8eR0t',
        'REDIS_HOST': 'redis.staging.example.com',
        'REDIS_PORT': '6379',
        'REDIS_PASSWORD': 'redis_password_secure_12345',
        'FRONTEND_URL': 'https://staging.netra.example.com',
        'BACKEND_URL': 'https://api.staging.netra.example.com',
        'AUTH_SERVICE_URL': 'https://auth.staging.netra.example.com',
        'GEMINI_API_KEY': 'test_gemini_key_for_staging_environment',
        'CLICKHOUSE_HOST': 'clickhouse.staging.example.com',
        'CLICKHOUSE_PASSWORD': 'clickhouse_secure_password',
    }
    
    for key, value in staging_configs.items():
        os.environ[key] = value
    
    print("Testing SSOT-compliant config validation...")
    
    try:
        # Test 1: Test ConfigDependencyMap using central validator
        print("\n1. Testing ConfigDependencyMap with central validator...")
        from netra_backend.app.core.config_dependencies import ConfigDependencyMap
        
        # This should now use the central validator
        issues = ConfigDependencyMap.check_config_consistency({})
        
        # Filter to see what issues remain
        critical_issues = [i for i in issues if 'CRITICAL' in i]
        warnings = [i for i in issues if 'WARNING' in i]
        
        print(f"   Critical issues: {len(critical_issues)}")
        print(f"   Warnings: {len(warnings)}")
        
        if critical_issues:
            print("   Sample critical issues:")
            for issue in critical_issues[:3]:
                print(f"      - {issue}")
        
        # Test 2: Test central validator directly
        print("\n2. Testing CentralConfigurationValidator directly...")
        from shared.configuration.central_config_validator import CentralConfigurationValidator
        from shared.isolated_environment import get_env
        
        env = get_env()
        validator = CentralConfigurationValidator(
            env_getter_func=lambda key, default=None: env.get(key, default)
        )
        
        try:
            validator.validate_all_requirements()
            print("   OK Central validator passed!")
        except ValueError as e:
            error_msg = str(e)
            print(f"   Central validator found issues:")
            # Parse and display first few issues
            if "Configuration validation failed" in error_msg:
                lines = error_msg.split('\n')
                for line in lines[:5]:
                    if line.strip():
                        print(f"      {line}")
        
        # Test 3: Verify delegation is working
        print("\n3. Verifying delegation from ConfigDependencyMap to central validator...")
        
        # Check that the method exists
        has_central_validator_method = hasattr(ConfigDependencyMap, '_validate_with_central_validator')
        print(f"   Has _validate_with_central_validator method: {has_central_validator_method}")
        
        # Check that check_config_consistency uses it
        import inspect
        source = inspect.getsource(ConfigDependencyMap.check_config_consistency)
        uses_central = '_validate_with_central_validator' in source
        print(f"   check_config_consistency delegates to central: {uses_central}")
        
        # Test 4: Check that ENV_TO_CONFIG_MAPPING was removed
        print("\n4. Verifying ENV_TO_CONFIG_MAPPING was removed...")
        has_mapping = hasattr(ConfigDependencyMap, 'ENV_TO_CONFIG_MAPPING')
        print(f"   ENV_TO_CONFIG_MAPPING exists: {has_mapping}")
        
        if has_mapping:
            print("   X SSOT VIOLATION: ENV_TO_CONFIG_MAPPING still exists!")
        else:
            print("   OK ENV_TO_CONFIG_MAPPING successfully removed")
        
        print("\n=== SSOT Compliance Summary ===")
        print(f"Delegation to central validator: {'YES' if uses_central else 'NO'}")
        print(f"Duplicate mapping removed: {'YES' if not has_mapping else 'NO'}")
        print(f"SSOT Compliant: {'YES' if uses_central and not has_mapping else 'NO'}")
        
        return uses_central and not has_mapping
        
    except Exception as e:
        print(f"\nX Error during SSOT validation test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up environment
        for key in staging_configs:
            os.environ.pop(key, None)
        os.environ.pop('ENVIRONMENT', None)


if __name__ == "__main__":
    success = test_ssot_config_validation()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)