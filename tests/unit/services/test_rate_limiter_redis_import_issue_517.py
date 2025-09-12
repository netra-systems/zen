"""
Unit Tests for Issue #517 - Redis Import Error in Rate Limiter Service

BUSINESS VALUE: Platform/Internal - System Stability & Critical Infrastructure
Prevents staging service outages that block $500K+ ARR chat functionality.

ROOT CAUSE: NameError in rate_limiter.py line 23 - missing proper redis import
FIX: Added explicit redis import to resolve NameError: name 'redis' is not defined

These tests reproduce the exact import error that caused the staging backend
HTTP 503 service outage and validate the fix prevents regression.

CRITICAL: These tests MUST FAIL initially to demonstrate the problem exists.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import importlib.util

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Simple debug test
def test_basic():
    print("Basic test works")
    return True


class TestRateLimiterRedisImportIssue517(unittest.TestCase):
    """
    Test suite for Issue #517 - Redis Import Error in Rate Limiter Service
    
    These tests reproduce the exact staging outage scenario where missing
    redis import caused NameError and HTTP 503 service unavailability.
    """
    
    def setUp(self):
        self.rate_limiter_path = project_root / "netra_backend" / "app" / "services" / "tool_permissions" / "rate_limiter.py"
        print(f"Testing rate limiter at: {self.rate_limiter_path}")
        
    def test_redis_import_error_reproduction(self):
        """
        CRITICAL TEST: Reproduce the exact NameError that caused staging outage.
        
        This test reproduces the original problem by temporarily removing
        the redis import and showing the NameError occurs.
        
        Expected: FAILURE when imports are broken (demonstrates the original issue)
        """
        print("Testing redis import error reproduction...")
        
        # Read the current (fixed) rate limiter file
        with open(self.rate_limiter_path, 'r') as f:
            original_content = f.read()
            
        # Create broken version (simulate the original problem)
        broken_content = original_content.replace(
            "import redis\nimport redis.asyncio as redis_asyncio", 
            "# import redis  # BROKEN: Missing redis import"
        )
        
        # Write the broken version to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(broken_content)
            temp_file_path = temp_file.name
            
        try:
            # Try to import the broken module
            spec = importlib.util.spec_from_file_location("broken_rate_limiter", temp_file_path)
            broken_module = importlib.util.module_from_spec(spec)
            
            # This should raise NameError: name 'redis' is not defined
            with self.assertRaises(NameError) as context:
                spec.loader.exec_module(broken_module)
                # Try to instantiate the class that uses redis type annotation
                broken_module.ToolPermissionRateLimiter(redis_client=None)
                
            # Verify it's the exact error we expect
            self.assertIn("redis", str(context.exception).lower())
            print(f"✓ Successfully reproduced the original NameError: {context.exception}")
            
        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)
    
    def test_fixed_import_works_correctly(self):
        """
        VALIDATION TEST: Confirm the current fix resolves the import error.
        
        This test validates that the current rate_limiter.py file imports
        successfully and can be instantiated without NameError.
        
        Expected: SUCCESS (demonstrates the fix works)
        """
        # Import should work without error
        try:
            from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter
            # Should be able to instantiate without NameError
            rate_limiter = ToolPermissionRateLimiter(redis_client=None)
            self.assertIsNotNone(rate_limiter)
            
        except NameError as e:
            self.fail(f"Fixed rate limiter still has import error: {e}")
            
    def test_redis_type_annotation_validation(self):
        """
        REGRESSION TEST: Validate redis type annotations work correctly.
        
        This test ensures the type annotations that use redis.Redis work
        correctly with the proper imports in place.
        
        Expected: SUCCESS (validates type system works)
        """
        from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter
        import redis
        
        # Mock Redis client for type validation
        mock_redis = MagicMock(spec=redis.Redis)
        
        # Should accept redis.Redis type without error
        try:
            rate_limiter = ToolPermissionRateLimiter(redis_client=mock_redis)
            self.assertEqual(rate_limiter.redis, mock_redis)
            print("✓ Type annotation validation successful")
            
        except Exception as e:
            self.fail(f"Type annotation validation failed: {e}")
    
    def test_application_startup_integration(self):
        """
        INTEGRATION TEST: Validate rate limiter doesn't break app startup.
        
        This test ensures the rate limiter import is compatible with
        application startup and doesn't cause server startup failures.
        
        Expected: SUCCESS (validates startup compatibility)
        """
        # Test import chain that caused startup failure
        try:
            # This import chain should work without NameError
            from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter
            from netra_backend.app.services.tool_permission_service import ToolPermissionService
            
            # Should be able to create instances
            rate_limiter = ToolPermissionRateLimiter()
            self.assertIsNotNone(rate_limiter)
            
        except (NameError, ImportError) as e:
            self.fail(f"Application startup import chain broken: {e}")
    
    def test_redis_client_dependency_handling(self):
        """
        DEPENDENCY TEST: Validate proper Redis client dependency handling.
        
        This test ensures the rate limiter handles Redis client dependencies
        correctly without causing import errors during initialization.
        
        Expected: SUCCESS (validates dependency management)
        """
        from netra_backend.app.services.tool_permissions.rate_limiter import ToolPermissionRateLimiter
        
        # Test with None redis client (should not cause NameError)
        try:
            rate_limiter = ToolPermissionRateLimiter(redis_client=None)
            self.assertIsNone(rate_limiter.redis)
            
        except NameError as e:
            self.fail(f"Redis dependency handling broken: {e}")
            
        # Test with mock redis client
        mock_redis = MagicMock()
        try:
            rate_limiter = ToolPermissionRateLimiter(redis_client=mock_redis)
            self.assertEqual(rate_limiter.redis, mock_redis)
            print("✓ Mock redis client handled correctly")
            
        except NameError as e:
            self.fail(f"Redis client assignment broken: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)