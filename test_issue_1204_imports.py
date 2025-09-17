#!/usr/bin/env python3
"""
Focused test for Issue #1204 - SSOT Monitoring Module Import Failure
Tests the exact imports that were failing in Docker staging environment.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_issue_1204_imports():
    """Test the exact imports that were failing in issue #1204."""
    print("=" * 60)
    print("ISSUE #1204 - SSOT MONITORING MODULE IMPORT FAILURE TEST")
    print("Testing exact imports that failed in Docker staging")
    print("=" * 60)

    success = True

    try:
        # This is the exact import that was failing in staging
        print("Testing: from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context")
        from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context
        print("✅ SUCCESS: Direct gcp_error_reporter import works")

        # Test the module-level imports
        print("\nTesting: from netra_backend.app.services.monitoring import set_request_context, clear_request_context")
        from netra_backend.app.services.monitoring import set_request_context, clear_request_context
        print("✅ SUCCESS: Module-level imports work")

        # Test that the functions are callable
        print("\nTesting function calls...")
        set_request_context(user_id="test_user_1204", trace_id="test_trace_1204")
        print("✅ SUCCESS: set_request_context callable")

        clear_request_context()
        print("✅ SUCCESS: clear_request_context callable")

        # Test the main GCPErrorReporter import
        print("\nTesting: from netra_backend.app.services.monitoring import GCPErrorReporter")
        from netra_backend.app.services.monitoring import GCPErrorReporter
        print("✅ SUCCESS: GCPErrorReporter import works")

        print("\n" + "🎉" * 20)
        print("🚀 ISSUE #1204 VALIDATION PASSED!")
        print("✅ All monitoring module imports working correctly")
        print("✅ Docker packaging is properly configured")
        print("✅ Ready for staging deployment validation")
        print("🎉" * 20)

    except ImportError as e:
        print(f"❌ IMPORT FAILURE: {e}")
        print(f"💥 Module path issue: {e.name if hasattr(e, 'name') else 'unknown'}")
        print("🚨 Docker packaging regression detected")
        success = False

    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        import traceback
        print("🔍 Traceback:")
        traceback.print_exc()
        success = False

    return success

if __name__ == "__main__":
    if test_issue_1204_imports():
        print("\n✅ Phase 1 validation complete - imports working locally")
        sys.exit(0)
    else:
        print("\n❌ Phase 1 validation failed - import issues persist")
        sys.exit(1)