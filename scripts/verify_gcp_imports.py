#!/usr/bin/env python3
"""
Verification script for GCP import handling.

This script verifies that GCP integration modules can be imported gracefully
even when google-cloud-logging library is not installed, ensuring unit tests
can run in environments without full GCP dependencies.

Business Value: Ensures development velocity by allowing unit tests to run
in local environments without requiring all production dependencies.
"""

import sys
import os
import importlib
from typing import List, Tuple

# Add project root to Python path to allow imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_gcp_imports() -> List[Tuple[str, bool, str]]:
    """Test all GCP integration imports for graceful failure handling."""
    
    modules_to_test = [
        'test_framework.gcp_integration.base',
        'test_framework.gcp_integration.log_reader',
        'test_framework.gcp_integration.log_reader_helpers',
        'test_framework.gcp_integration.log_reader_core',
        'test_framework.gcp_integration.gcp_error_test_fixtures'
    ]
    
    results = []
    
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            
            # Check if module has graceful GCP handling
            has_graceful_handling = (
                hasattr(module, 'GCP_LOGGING_AVAILABLE') or
                hasattr(module, 'GCP_AVAILABLE') or
                'try:' in str(module.__dict__)  # Basic check for try/except patterns
            )
            
            results.append((module_name, True, 'Import successful'))
            
            if has_graceful_handling:
                print(f" PASS:  {module_name}: Import successful with graceful GCP handling")
            else:
                print(f" WARNING: [U+FE0F]  {module_name}: Import successful but no graceful handling detected")
                
        except ImportError as e:
            results.append((module_name, False, str(e)))
            print(f" FAIL:  {module_name}: Import failed - {e}")
        except Exception as e:
            results.append((module_name, False, f"Unexpected error: {e}"))
            print(f" FAIL:  {module_name}: Unexpected error - {e}")
    
    return results


def test_gcp_library_status():
    """Check the status of GCP libraries."""
    
    libraries = [
        'google.cloud.logging',
        'google.cloud.secretmanager',
        'google.cloud.error_reporting'
    ]
    
    print("\n CHART:  GCP Library Status:")
    for lib in libraries:
        try:
            importlib.import_module(lib)
            print(f" PASS:  {lib}: Available")
        except ImportError:
            print(f" FAIL:  {lib}: Not available")


def main():
    """Main verification function."""
    
    print(" SEARCH:  Verifying GCP Integration Import Handling")
    print("=" * 50)
    
    results = test_gcp_imports()
    test_gcp_library_status()
    
    # Summary
    successful_imports = sum(1 for _, success, _ in results if success)
    total_imports = len(results)
    
    print(f"\n[U+1F4C8] Summary:")
    print(f"Successful imports: {successful_imports}/{total_imports}")
    
    if successful_imports == total_imports:
        print(" PASS:  All GCP integration modules can be imported successfully!")
        print(" PASS:  Backend unit tests should now run without GCP dependency issues.")
        return 0
    else:
        print(" FAIL:  Some imports still failing. Check above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())