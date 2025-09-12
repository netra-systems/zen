from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
env = get_env()
Debug script to test SecretManagerBuilder implementation and identify issues.
"""

import os
import sys
import json
from typing import Dict, Any

# Set encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Set test environment
env.set('ENVIRONMENT', 'development', "test")
env.set('JWT_SECRET_KEY', 'test-jwt-secret-key', "test")
env.set('POSTGRES_PASSWORD', 'test-postgres-password', "test")
env.set('REDIS_PASSWORD', 'test-redis-password', "test")
env.set('FERNET_KEY', 'test-fernet-key-32-chars-exactly', "test")
env.set('ANTHROPIC_API_KEY', 'sk-ant-test-key', "test")

def test_secret_manager_builder():
    """Test the SecretManagerBuilder implementation."""
    print("=" * 80)
    print("SECRET MANAGER BUILDER DEBUG TEST")
    print("=" * 80)
    
    try:
        # Import the SecretManagerBuilder
        from shared.secret_manager_builder import SecretManagerBuilder
        print(" PASS:  SecretManagerBuilder imported successfully")
        
        # Create builder instance
        builder = SecretManagerBuilder(service="shared")
        print(f" PASS:  Builder created for service: {builder.service}")
        print(f"   Environment detected: {builder._environment}")
        
        # Test loading all secrets
        print("\n[U+1F4E6] Testing load_all_secrets()...")
        try:
            secrets = builder.load_all_secrets()
            print(f"   Loaded {len(secrets)} secrets")
            
            # Check critical secrets
            critical_secrets = ['JWT_SECRET_KEY', 'POSTGRES_PASSWORD', 'REDIS_PASSWORD', 'FERNET_KEY']
            for secret_name in critical_secrets:
                if secret_name in secrets:
                    print(f"    PASS:  {secret_name}: Found (value length: {len(str(secrets[secret_name]))})")
                else:
                    print(f"    FAIL:  {secret_name}: Missing")
                    
            # Check new business secret
            if 'ANTHROPIC_API_KEY' in secrets:
                print(f"    PASS:  ANTHROPIC_API_KEY: Found")
            else:
                print(f"    FAIL:  ANTHROPIC_API_KEY: Missing")
                
        except Exception as e:
            print(f"    FAIL:  Failed to load secrets: {e}")
            
        # Test validation
        print("\n[U+1F510] Testing validate_configuration()...")
        try:
            validation_result = builder.validate_configuration()
            print(f"   Validation valid: {validation_result.is_valid}")
            print(f"   Errors: {len(validation_result.errors)}")
            print(f"   Warnings: {len(validation_result.warnings)}")
            print(f"   Placeholder count: {validation_result.placeholder_count}")
            
            if validation_result.errors:
                print("   Errors found:")
                for error in validation_result.errors[:3]:
                    print(f"     - {error}")
                    
        except Exception as e:
            print(f"    FAIL:  Validation failed: {e}")
            
        # Test sub-builders
        print("\n[U+1F3D7][U+FE0F] Testing sub-builders...")
        
        # Test GCP builder
        try:
            print("   Testing GCP builder...")
            project_id = builder.gcp._project_id
            print(f"     Project ID: {project_id}")
            
            # Test connectivity (will fail in dev but should not crash)
            is_valid, error = builder.gcp.validate_gcp_connectivity()
            if is_valid:
                print(f"      PASS:  GCP connectivity valid")
            else:
                print(f"      WARNING: [U+FE0F] GCP connectivity not available (expected in dev)")
                
        except Exception as e:
            print(f"      FAIL:  GCP builder error: {e}")
            
        # Test auth builder
        try:
            print("   Testing Auth builder...")
            jwt_secret = builder.auth.get_jwt_secret()
            print(f"      PASS:  JWT secret retrieved (length: {len(jwt_secret)})")
        except Exception as e:
            print(f"      FAIL:  Auth builder error: {e}")
            
        # Test cache builder
        try:
            print("   Testing Cache builder...")
            builder.cache.cache_secret("TEST_SECRET", "test_value", ttl_minutes=5)
            cached_value = builder.cache.get_cached_secret("TEST_SECRET")
            if cached_value == "test_value":
                print(f"      PASS:  Cache working correctly")
            else:
                print(f"      FAIL:  Cache not working: got {cached_value}")
        except Exception as e:
            print(f"      FAIL:  Cache builder error: {e}")
            
        # Test debug info
        print("\n CHART:  Getting debug info...")
        try:
            debug_info = builder.get_debug_info()
            print(json.dumps(debug_info, indent=2))
        except Exception as e:
            print(f"    FAIL:  Debug info failed: {e}")
            
        # Test backward compatibility functions
        print("\n[U+1F527] Testing backward compatibility...")
        try:
            from shared.secret_manager_builder import (
                get_secret_manager,
                load_secrets_for_service,
                get_jwt_secret,
                get_database_password,
                get_redis_password
            )
            
            # Test get_secret_manager
            manager = get_secret_manager("shared")
            print(f"    PASS:  get_secret_manager() works")
            
            # Test load_secrets_for_service
            service_secrets = load_secrets_for_service("shared")
            print(f"    PASS:  load_secrets_for_service() returned {len(service_secrets)} secrets")
            
            # Test get_jwt_secret
            jwt = get_jwt_secret("shared")
            print(f"    PASS:  get_jwt_secret() works")
            
            # Test get_database_password
            db_pass = get_database_password("shared")
            if db_pass:
                print(f"    PASS:  get_database_password() returned value")
            else:
                print(f"    WARNING: [U+FE0F] get_database_password() returned None (expected in dev)")
                
            # Test get_redis_password
            redis_pass = get_redis_password("shared")
            if redis_pass:
                print(f"    PASS:  get_redis_password() returned value")
            else:
                print(f"    WARNING: [U+FE0F] get_redis_password() returned None (expected in dev)")
                
        except Exception as e:
            print(f"    FAIL:  Backward compatibility error: {e}")
            
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        
    except ImportError as e:
        print(f" FAIL:  Failed to import SecretManagerBuilder: {e}")
        return False
    except Exception as e:
        print(f" FAIL:  Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return True

if __name__ == "__main__":
    success = test_secret_manager_builder()
    sys.exit(0 if success else 1)