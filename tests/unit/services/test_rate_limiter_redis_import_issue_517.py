"""
Unit Tests for Issue #517 - Redis Import Error in Rate Limiter Service

BUSINESS VALUE: Platform/Internal - System Stability & Critical Infrastructure
Prevents staging service outages that block $500K+ ARR chat functionality.

ROOT CAUSE: NameError in rate_limiter.py line 23 - missing proper redis import
The original issue was:
- Line 5: import redis  
- Line 23: def __init__(self, redis_client: Optional[redis.Redis] = None):
- But the type annotation 'redis.Redis' failed because only the module was imported

FIX: Added explicit redis import to resolve NameError: name 'redis' is not defined
- Line 5: import redis
- Line 6: import redis.asyncio as redis_asyncio

These tests reproduce the exact import error that caused the staging backend
HTTP 503 service outage and validate the fix prevents regression.

CRITICAL: These tests MUST FAIL initially to demonstrate the problem exists.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import importlib.util

# SSOT Test Infrastructure Imports
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Simple debug test
@pytest.mark.unit
def test_basic():
    print("Basic test works")
    return True


@pytest.mark.unit
class RateLimiterRedisImportIssue517Tests(SSotBaseTestCase):
    """
    Test suite for Issue #517 - Redis Import Error in Rate Limiter Service
    
    These tests reproduce the exact staging outage scenario where missing
    redis import caused NameError and HTTP 503 service unavailability.
    """
    
    def setup_method(self, method):
        """SSOT test setup using pytest-style method."""
        super().setup_method(method)
        self.rate_limiter_path = project_root / "netra_backend" / "app" / "services" / "tool_permissions" / "rate_limiter.py"
        print(f"Testing rate limiter at: {self.rate_limiter_path}")

        # Record test category for SSOT metrics
        self.record_metric("test_category", "unit")
        self.record_metric("issue_number", "517")
        self.record_metric("business_value", "platform_stability")

        # Add cleanup for temporary files (SSOT pattern)
        self.add_cleanup(self._cleanup_temp_files)
        self._temp_files = []

    def _cleanup_temp_files(self):
        """SSOT cleanup method for temporary files."""
        for temp_file_path in getattr(self, '_temp_files', []):
            try:
                Path(temp_file_path).unlink(missing_ok=True)
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp file {temp_file_path}: {e}")
        
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
        
        # Write the broken version to a temporary file (SSOT cleanup pattern)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(broken_content)
            temp_file_path = temp_file.name

        # Register for SSOT cleanup
        self._temp_files.append(temp_file_path)

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
            print(f"CHECK Successfully reproduced the original NameError: {context.exception}")

            # Record success metric (SSOT pattern)
            self.record_metric("redis_import_error_reproduced", True)

        except Exception as e:
            # SSOT error handling: Record failure and continue
            self.record_metric("redis_import_error_reproduced", False)
            self.record_metric("error_details", str(e))
            raise
    
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

            # Record success metric (SSOT pattern)
            self.record_metric("fixed_import_validation", True)

        except NameError as e:
            # SSOT error recording
            self.record_metric("fixed_import_validation", False)
            self.record_metric("import_error", str(e))
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
            print("CHECK Type annotation validation successful")

            # Record success metric (SSOT pattern)
            self.record_metric("type_annotation_validation", True)

        except Exception as e:
            # SSOT error recording
            self.record_metric("type_annotation_validation", False)
            self.record_metric("type_error", str(e))
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

            # Record success metric (SSOT pattern)
            self.record_metric("startup_integration_test", True)

        except (NameError, ImportError) as e:
            # SSOT error recording
            self.record_metric("startup_integration_test", False)
            self.record_metric("startup_error", str(e))
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

            # Record success metric (SSOT pattern)
            self.record_metric("redis_none_handling", True)

        except NameError as e:
            # SSOT error recording
            self.record_metric("redis_none_handling", False)
            self.record_metric("none_handling_error", str(e))
            self.fail(f"Redis dependency handling broken: {e}")

        # Test with mock redis client
        mock_redis = MagicMock()
        try:
            rate_limiter = ToolPermissionRateLimiter(redis_client=mock_redis)
            self.assertEqual(rate_limiter.redis, mock_redis)
            print("CHECK Mock redis client handled correctly")

            # Record success metric (SSOT pattern)
            self.record_metric("redis_mock_handling", True)

        except NameError as e:
            # SSOT error recording
            self.record_metric("redis_mock_handling", False)
            self.record_metric("mock_handling_error", str(e))
            self.fail(f"Redis client assignment broken: {e}")


if __name__ == '__main__':
    # SSOT Test Execution: Use unified test runner instead of direct unittest
    # For SSOT compliance, run via: python tests/unified_test_runner.py
    print("SSOT Migration Complete: Use 'python tests/unified_test_runner.py --pattern test_rate_limiter_redis_import_issue_517.py' for execution")
    import unittest
    unittest.main(verbosity=2)  # Fallback for direct execution
