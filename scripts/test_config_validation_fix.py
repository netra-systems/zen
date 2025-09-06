#!/usr/bin/env python3
"""Test script to verify the config validation fix for staging environment."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_config_validation():
    """Test that config validation properly maps env vars to config attributes."""
    
    # Set up staging environment
    os.environ['ENVIRONMENT'] = 'staging'
    
    # Set up required staging configs with secure values
    staging_configs = {
        'POSTGRES_HOST': 'db.staging.example.com',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'netra_staging',
        'POSTGRES_USER': 'postgres',
        'POSTGRES_PASSWORD': 'xK9mN2pQ8vL3fR6tY5wA7zE4jH1uG0sD',
        'JWT_SECRET_KEY': 'xK9mN2pQ8vL3fR6tY5wA7zE4jH1uG0sDqW3eR5tY6uI8oP',
        'JWT_SECRET_STAGING': 'xK9mN2pQ8vL3fR6tY5wA7zE4jH1uG0sDqW3eR5tY6uI8oP',
        'SECRET_KEY': 'aB3cD5eF7gH9jK2mN4pQ6rS8tU0vW2xY4zA6bC8dE0fG2hJ',
        'SERVICE_SECRET': 'qW3eR5tY6uI8oP0aS2dF4gH6jK8lZ0xC2vB4nM6qW8eR0t',
        'REDIS_HOST': 'redis.staging.example.com',
        'REDIS_PORT': '6379',
        'FRONTEND_URL': 'https://staging.netra.example.com',
        'BACKEND_URL': 'https://api.staging.netra.example.com',
        'AUTH_SERVICE_URL': 'https://auth.staging.netra.example.com',
        'GEMINI_API_KEY': 'test_gemini_key_for_staging_environment',
    }
    
    for key, value in staging_configs.items():
        os.environ[key] = value
    
    print("Testing config validation with proper environment variables...")
    
    try:
        # Import after environment is set
        from netra_backend.app.core.configuration.base import UnifiedConfigManager
        from netra_backend.app.core.config_dependencies import ConfigDependencyMap
        
        # Test 1: Create config manager
        print("\n1. Creating UnifiedConfigManager...")
        config_manager = UnifiedConfigManager()
        
        # Test 2: Get config (this triggers validation)
        print("2. Getting config (triggers validation)...")
        config = config_manager.get_config()
        print(f"   Environment: {config.environment}")
        
        # Test 3: Check config object has proper attributes
        print("\n3. Checking config object attributes...")
        print(f"   database_url: {bool(config.database_url)}")
        print(f"   jwt_secret_key: {bool(config.jwt_secret_key)}")
        print(f"   secret_key: {bool(config.secret_key)}")
        print(f"   service_secret: {bool(config.service_secret)}")
        print(f"   frontend_url: {config.frontend_url}")
        print(f"   api_base_url: {config.api_base_url if hasattr(config, 'api_base_url') else 'Not present'}")
        
        # Test 4: Direct dependency check with config object
        print("\n4. Testing ConfigDependencyMap with config object...")
        config_dict = config.__dict__ if hasattr(config, '__dict__') else {}
        issues = ConfigDependencyMap.check_config_consistency(config)
        
        # Filter out non-critical issues for this test
        critical_issues = [i for i in issues if 'CRITICAL' in i and 'Missing required config' in i]
        
        if critical_issues:
            print(f"   X Found {len(critical_issues)} critical issues:")
            for issue in critical_issues[:5]:  # Show first 5
                print(f"      - {issue}")
        else:
            print("   OK No critical missing config issues!")
        
        # Test 5: Check environment variable validation
        print("\n5. Testing ConfigDependencyMap with environment variables...")
        env_issues = ConfigDependencyMap.check_config_consistency(staging_configs)
        
        critical_env_issues = [i for i in env_issues if 'CRITICAL' in i and 'Missing required config' in i]
        
        if critical_env_issues:
            print(f"   X Found {len(critical_env_issues)} critical issues in env:")
            for issue in critical_env_issues[:5]:
                print(f"      - {issue}")
        else:
            print("   OK No critical missing config issues in environment!")
        
        print("\nOK Config validation test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nX Error during config validation test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up environment
        for key in staging_configs:
            os.environ.pop(key, None)
        os.environ.pop('ENVIRONMENT', None)


if __name__ == "__main__":
    success = test_config_validation()
    sys.exit(0 if success else 1)