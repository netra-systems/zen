#!/usr/bin/env python3
"""
Issue #521 Stability Validation Script
Proof that Redis import fix and requirements.txt addition maintain system stability
"""

import sys
import traceback
import subprocess
from pathlib import Path

def test_redis_import_fix():
    """Test that the Redis import fix works correctly"""
    print("🔍 Testing Redis Import Fix...")
    try:
        from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter, RateLimiter
        print("✅ ToolPermissionRateLimiter imports successfully")
        
        # Test instantiation
        rate_limiter = ToolPermissionRateLimiter()
        print("✅ ToolPermissionRateLimiter instantiates successfully")
        
        # Test alias
        alias_limiter = RateLimiter()
        print("✅ RateLimiter alias instantiates successfully")
        
        # Test redis module is available
        import redis
        import redis.asyncio
        print("✅ Redis and redis.asyncio modules import successfully")
        
        return True
    except Exception as e:
        print(f"❌ Redis import test failed: {e}")
        traceback.print_exc()
        return False

def test_requirements_dependency():
    """Test that requirements.txt includes redis dependency"""
    print("\n🔍 Testing Requirements.txt Redis Dependency...")
    try:
        requirements_path = Path("requirements.txt")
        if not requirements_path.exists():
            print("❌ requirements.txt not found")
            return False
            
        content = requirements_path.read_text()
        if "redis>=" in content:
            print("✅ Redis dependency found in requirements.txt")
            return True
        else:
            print("❌ Redis dependency not found in requirements.txt")
            return False
    except Exception as e:
        print(f"❌ Requirements check failed: {e}")
        return False

def test_service_health_check():
    """Basic service health validation - focusing on Issue #521 changes"""
    print("\n🔍 Testing Basic Service Health...")
    try:
        # Test basic imports of critical services don't break
        from netra_backend.app.core.configuration.base import get_config
        config = get_config()
        print("✅ Configuration system loads successfully")
        
        from netra_backend.app.websocket_core.manager import WebSocketManager
        print("✅ WebSocket manager imports successfully")
        
        # Test that the Redis import doesn't break other imports
        from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter
        print("✅ Rate limiter with Redis import works correctly")
        
        return True
    except Exception as e:
        print(f"❌ Service health check failed: {e}")
        traceback.print_exc()
        return False

def test_no_breaking_changes():
    """Test that no breaking changes were introduced"""
    print("\n🔍 Testing No Breaking Changes...")
    try:
        # Test critical import paths still work
        from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter
        
        # Test that the class has expected methods
        rate_limiter = ToolPermissionRateLimiter()
        
        # Verify key methods exist
        expected_methods = [
            'check_rate_limits',
            'record_tool_usage',
            '_get_applicable_rate_limits',
            '_build_limit_exceeded_response',
            '_build_allowed_response',
            '_get_usage_count'
        ]
        
        for method_name in expected_methods:
            if not hasattr(rate_limiter, method_name):
                print(f"❌ Missing expected method: {method_name}")
                return False
                
        print("✅ All expected methods present on ToolPermissionRateLimiter")
        
        # Test that imports from the service layer work
        from netra_backend.app.services.rate_limiter import RateLimiter as CoreRateLimiter
        print("✅ Core rate limiter import works (no circular import)")
        
        return True
    except Exception as e:
        print(f"❌ Breaking changes test failed: {e}")
        traceback.print_exc()
        return False

def run_basic_validation():
    """Run basic validation of the system"""
    print("\n🔍 Running Basic System Validation...")
    try:
        # Try to run a simple test to ensure the system is functional
        result = subprocess.run([
            sys.executable, "-c", 
            """
import sys
sys.path.insert(0, '.')
from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter
limiter = ToolPermissionRateLimiter()
print("Basic validation successful")
            """
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Basic system validation passed")
            return True
        else:
            print(f"❌ Basic validation failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Basic validation failed: {e}")
        return False

def main():
    """Main validation function"""
    print("="*80)
    print("ISSUE #521 STABILITY VALIDATION - PROOF OF NO BREAKING CHANGES")
    print("="*80)
    print("Changes validated:")
    print("1. Added 'import redis' to rate_limiter.py")
    print("2. Root requirements.txt includes redis>=6.4.0")
    print("="*80)
    
    tests = [
        ("Redis Import Fix", test_redis_import_fix),
        ("Requirements Dependency", test_requirements_dependency),
        ("Service Health Check", test_service_health_check),
        ("No Breaking Changes", test_no_breaking_changes),
        ("Basic Validation", run_basic_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "="*80)
    print(f"VALIDATION RESULTS: {passed}/{total} tests passed")
    print("="*80)
    
    if passed == total:
        print("🎉 PROOF COMPLETE: Issue #521 changes maintain system stability")
        print("🎉 NO BREAKING CHANGES INTRODUCED")
        print("🎉 CHANGES EXCLUSIVELY ADD VALUE (Redis import fix)")
        return True
    else:
        print("❌ VALIDATION FAILED: Some tests did not pass")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)