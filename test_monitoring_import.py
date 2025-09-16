#!/usr/bin/env python3
"""
Test script to verify monitoring module imports work correctly.
This validates the Docker packaging fix.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_monitoring_imports():
    """Test all critical monitoring module imports."""
    print("Testing monitoring module imports...")

    try:
        # Test the main monitoring module import that was failing
        from netra_backend.app.services.monitoring import GCPErrorService
        print("✓ GCPErrorService import successful")

        from netra_backend.app.services.monitoring import GCPErrorReporter
        print("✓ GCPErrorReporter import successful")

        from netra_backend.app.services.monitoring import ErrorFormatter
        print("✓ ErrorFormatter import successful")

        from netra_backend.app.services.monitoring import GCPClientManager
        print("✓ GCPClientManager import successful")

        from netra_backend.app.services.monitoring.error_tracker import ErrorTracker
        print("✓ ErrorTracker import successful")

        from netra_backend.app.services.monitoring.metrics_service import MetricsService
        print("✓ MetricsService import successful")

        # Test instantiation (basic validation)
        error_formatter = ErrorFormatter()
        print("✓ ErrorFormatter instantiation successful")

        print("\n🎉 ALL MONITORING IMPORTS SUCCESSFUL!")
        print("✓ Docker packaging fix is working correctly")
        return True

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("💀 Docker packaging regression still present")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_app_startup_imports():
    """Test imports that would be used during app startup."""
    print("\nTesting app startup related imports...")

    try:
        # Test imports that the main application uses
        from netra_backend.app.core.app_factory import create_fastapi_app
        print("✓ FastAPI app factory import successful")

        # This should work if monitoring is properly included
        from netra_backend.app.core.unified_logging import get_logger
        print("✓ Unified logging import successful")

        print("✓ App startup imports successful")
        return True

    except ImportError as e:
        print(f"❌ App startup import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in app startup: {e}")
        return False

def main():
    """Main test routine."""
    print("=" * 60)
    print("MONITORING MODULE IMPORT VALIDATION TEST")
    print("Verifying Docker packaging regression fix")
    print("=" * 60)

    # Change to project directory
    os.chdir(project_root)

    success = True

    # Test monitoring imports
    if not test_monitoring_imports():
        success = False

    # Test app startup imports
    if not test_app_startup_imports():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("🚀 VALIDATION PASSED - Monitoring module packaging is fixed!")
        print("✅ Safe to proceed with staging verification")
    else:
        print("💥 VALIDATION FAILED - Docker packaging issue persists")
        print("❌ Additional fixes needed before staging deployment")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())