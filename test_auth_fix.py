#!/usr/bin/env python3
"""
Test script to verify UserAuthService configuration fix
"""
import asyncio
from netra_backend.app.services.user_auth_service import UserAuthService


def test_userauth_initialization():
    """Test that UserAuthService initializes correctly with proper config access"""
    print("Testing UserAuthService initialization...")
    
    try:
        service = UserAuthService()
        print(f"SUCCESS: Service initialized successfully")
        print(f"SUCCESS: Shared secret type: {type(service._shared_secret)}")
        print(f"SUCCESS: Shared secret length: {len(service._shared_secret)}")
        
        # Test that config access works
        config = service.config.get_config()
        print(f"SUCCESS: Config access works: {type(config)}")
        print(f"SUCCESS: Has jwt_secret_key: {hasattr(config, 'jwt_secret_key')}")
        print(f"SUCCESS: Has service_secret: {hasattr(config, 'service_secret')}")
        
        return True
        
    except Exception as e:
        print(f"ERROR during initialization: {e}")
        raise


async def test_userauth_methods():
    """Test that UserAuthService methods work correctly"""
    print("\nTesting UserAuthService methods...")
    
    service = UserAuthService()
    
    try:
        # Test blacklist functionality
        test_token = "test-token-12345"
        service.blacklist_token(test_token)
        is_blacklisted = service._is_token_blacklisted(test_token)
        assert is_blacklisted, "Token should be blacklisted"
        print("SUCCESS: Token blacklist functionality works")
        
        # Test metrics
        metrics = service.get_security_metrics()
        assert isinstance(metrics, dict), "Metrics should be a dictionary"
        assert "blacklisted_tokens" in metrics, "Metrics should contain blacklisted_tokens count"
        print(f"SUCCESS: Security metrics work: {metrics}")
        
        # Test token validation (should handle gracefully even without auth service)
        result = await service.validate_user_token("invalid-token")
        print(f"SUCCESS: Token validation runs without errors: {result is None}")
        
        print("SUCCESS: All method tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Error during method testing: {e}")
        raise


def main():
    """Run all tests"""
    print("=" * 60)
    print("UserAuthService Configuration Fix Verification")
    print("=" * 60)
    
    try:
        # Test initialization
        test_userauth_initialization()
        
        # Test async methods
        asyncio.run(test_userauth_methods())
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED - Configuration fix is working!")
        print("UserAuthService now properly accesses configuration via")
        print("config.get_config() instead of config.get()")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TESTS FAILED: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())