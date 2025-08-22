"""
Test script to verify environment detection is working correctly.
Run this to ensure all environment detection logic defaults to staging, not production.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_auth_client_environment_detection():
    """Test auth client environment detection."""
    print("\n=== Testing Auth Client Environment Detection ===")
    
    # Test with no environment variables
    os.environ.pop("ENVIRONMENT", None)
    os.environ.pop("K_SERVICE", None)
    os.environ.pop("K_REVISION", None)
    os.environ.pop("TESTING", None)
    
    from netra_backend.app.clients.auth_client_config import (
        Environment,
        EnvironmentDetector,
    )
    
    detector = EnvironmentDetector()
    env = detector.detect_environment()
    
    print(f"No env vars set: {env.value}")
    assert env == Environment.STAGING, f"Expected STAGING, got {env.value}"
    print("[PASS] Correctly defaults to STAGING when no env vars")
    
    # Test with ENVIRONMENT=staging
    os.environ["ENVIRONMENT"] = "staging"
    env = detector.detect_environment()
    print(f"ENVIRONMENT=staging: {env.value}")
    assert env == Environment.STAGING
    print("[PASS] Correctly detects staging from ENVIRONMENT var")
    
    # Test with K_SERVICE containing staging
    os.environ.pop("ENVIRONMENT", None)
    os.environ["K_SERVICE"] = "netra-staging-backend"
    env = detector.detect_environment()
    print(f"K_SERVICE=netra-staging-backend: {env.value}")
    assert env == Environment.STAGING
    print("[PASS] Correctly detects staging from K_SERVICE")
    
    # Test with K_SERVICE containing just backend (should NOT be production)
    os.environ["K_SERVICE"] = "netra-backend"
    env = detector.detect_environment()
    print(f"K_SERVICE=netra-backend: {env.value}")
    assert env == Environment.STAGING, f"Backend alone should not trigger production, got {env.value}"
    print("[PASS] Correctly defaults to staging for ambiguous service name")
    
    # Test with explicit production
    os.environ["K_SERVICE"] = "netra-prod-backend"
    env = detector.detect_environment()
    print(f"K_SERVICE=netra-prod-backend: {env.value}")
    assert env == Environment.PRODUCTION
    print("[PASS] Correctly detects production when explicitly specified")
    
    print("\n[PASS] All auth client environment detection tests passed!")


def test_middleware_environment_defaults():
    """Test that middleware defaults to staging."""
    print("\n=== Testing Middleware Environment Defaults ===")
    
    os.environ.pop("ENVIRONMENT", None)
    
    # Test by directly checking the environment default values in the code
    # without importing the full modules (to avoid circular imports)
    
    # Read and verify the defaults are set to "staging"
    script_dir = Path(__file__).parent.parent
    
    # Check tool_permission_middleware
    middleware_file = script_dir / "app/middleware/tool_permission_middleware.py"
    with open(middleware_file, 'r') as f:
        content = f.read()
        if 'os.getenv("ENVIRONMENT", "staging")' in content:
            print("[PASS] ToolPermissionMiddleware defaults to staging")
        else:
            raise AssertionError("ToolPermissionMiddleware does not default to staging")
    
    # Check factory_compliance
    compliance_file = script_dir / "app/routes/factory_compliance.py"
    with open(compliance_file, 'r') as f:
        content = f.read()
        if 'os.getenv("ENVIRONMENT", "staging")' in content:
            print("[PASS] Factory compliance defaults to staging")
        else:
            raise AssertionError("Factory compliance does not default to staging")
    
    # Check factory_status_integration
    status_file = script_dir / "app/services/factory_status/factory_status_integration.py"
    with open(status_file, 'r') as f:
        content = f.read()
        if 'os.getenv("ENVIRONMENT", "staging")' in content:
            print("[PASS] Factory status integration defaults to staging")
        else:
            raise AssertionError("Factory status integration does not default to staging")
    
    print("\n[PASS] All middleware environment default tests passed!")


def test_schema_defaults():
    """Test that schemas default to staging."""
    print("\n=== Testing Schema Defaults ===")
    
    # Check schema file directly to avoid circular imports
    script_dir = Path(__file__).parent.parent
    schema_file = script_dir / "app/schemas/ToolPermission.py"
    
    with open(schema_file, 'r') as f:
        content = f.read()
        if 'Field(default="staging"' in content:
            print("[PASS] PermissionRequest schema defaults to staging")
        else:
            raise AssertionError("PermissionRequest schema does not default to staging")
    
    print("\n[PASS] All schema default tests passed!")


def test_oauth_config_fallback():
    """Test OAuth configuration fallback."""
    print("\n=== Testing OAuth Config Fallback ===")
    
    os.environ.pop("ENVIRONMENT", None)
    from netra_backend.app.clients.auth_client_config import (
        Environment,
        EnvironmentDetector,
        OAuthConfigGenerator,
    )
    
    detector = EnvironmentDetector()
    env = detector.detect_environment()
    
    generator = OAuthConfigGenerator()
    config = generator.get_oauth_config(env)
    
    print(f"OAuth config for {env.value}:")
    print(f"  - Allow dev login: {config.allow_dev_login}")
    print(f"  - Allow mock auth: {config.allow_mock_auth}")
    
    # Staging should not allow dev login or mock auth
    assert not config.allow_dev_login, "Staging should not allow dev login"
    assert not config.allow_mock_auth, "Staging should not allow mock auth"
    print("[PASS] OAuth config correctly configured for staging")
    
    print("\n[PASS] All OAuth config tests passed!")


def main():
    """Run all environment detection tests."""
    print("=" * 60)
    print("ENVIRONMENT DETECTION TEST SUITE")
    print("=" * 60)
    
    try:
        test_auth_client_environment_detection()
        test_middleware_environment_defaults()
        test_schema_defaults()
        test_oauth_config_fallback()
        
        print("\n" + "=" * 60)
        print("[PASS] ALL ENVIRONMENT DETECTION TESTS PASSED!")
        print("=" * 60)
        print("\nSUMMARY:")
        print("- All services correctly default to STAGING (not production)")
        print("- Environment detection logic works as expected")
        print("- OAuth configuration appropriate for each environment")
        print("\n[SUCCESS] Environment detection is properly configured!")
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()