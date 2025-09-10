#!/usr/bin/env python3
"""Debug script to understand Redis configuration validation issue."""

import sys
import os
sys.path.insert(0, '.')

from shared.isolated_environment import get_env
from netra_backend.app.core.backend_environment import BackendEnvironment

def main():
    print("=== DEBUGGING REDIS CONFIGURATION VALIDATION ===")
    
    # Set up test environment like the failing test
    env = get_env()
    env.enable_isolation(backup_original=True)
    
    # Invalid configuration from test
    invalid_config = {
        "ENVIRONMENT": "staging",
        "REDIS_HOST": "",  # Invalid empty host
        "REDIS_PORT": "invalid_port",
        "POSTGRES_HOST": "localhost",  # Invalid for staging
        "JWT_SECRET_KEY": "short",     # Too short
        "SECRET_KEY": ""               # Missing
    }
    
    print("Setting invalid configuration:")
    for key, value in invalid_config.items():
        env.set(key, value, "debug_test")
        print(f"  {key} = '{value}'")
    
    print("\n=== CREATING BACKEND ENVIRONMENT ===")
    backend_env = BackendEnvironment()
    
    print(f"Environment detected: {backend_env.get_environment()}")
    print(f"Is staging: {backend_env.is_staging()}")
    
    print("\n=== CHECKING INDIVIDUAL COMPONENTS ===")
    
    # Check JWT Secret Key
    try:
        jwt_secret = backend_env.get_jwt_secret_key()
        print(f"JWT_SECRET_KEY: '{jwt_secret}' (length: {len(jwt_secret) if jwt_secret else 0})")
    except Exception as e:
        print(f"JWT_SECRET_KEY error: {e}")
    
    # Check Secret Key
    try:
        secret_key = backend_env.get_secret_key()
        print(f"SECRET_KEY: '{secret_key}' (length: {len(secret_key) if secret_key else 0})")
    except Exception as e:
        print(f"SECRET_KEY error: {e}")
    
    # Check Redis configuration
    try:
        redis_host = backend_env.get_redis_host()
        print(f"REDIS_HOST: '{redis_host}'")
    except Exception as e:
        print(f"REDIS_HOST error: {e}")
    
    try:
        redis_port = backend_env.get_redis_port()
        print(f"REDIS_PORT: {redis_port}")
    except Exception as e:
        print(f"REDIS_PORT error: {e}")
    
    try:
        redis_url = backend_env.get_redis_url()
        print(f"REDIS_URL: '{redis_url}'")
    except Exception as e:
        print(f"REDIS_URL error: {e}")
    
    # Check database configuration
    try:
        db_url = backend_env.get_database_url()
        print(f"DATABASE_URL: '{db_url}'")
    except Exception as e:
        print(f"DATABASE_URL error: {e}")
    
    print("\n=== VALIDATION RESULTS ===")
    validation_result = backend_env.validate()
    print(f"Valid: {validation_result['valid']}")
    print(f"Issues: {validation_result['issues']}")
    print(f"Warnings: {validation_result['warnings']}")
    print(f"Environment: {validation_result['environment']}")
    
    # Test the assertion that's failing
    print(f"\n=== TEST ASSERTION ANALYSIS ===")
    print(f"validation_result['valid'] is False: {validation_result['valid'] is False}")
    print(f"validation_result['valid'] == False: {validation_result['valid'] == False}")
    print(f"len(validation_result['issues']) > 0: {len(validation_result['issues']) > 0}")
    
    # Clean up
    env.reset_to_original()

if __name__ == "__main__":
    main()