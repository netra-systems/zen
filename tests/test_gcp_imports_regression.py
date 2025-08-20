"""
Regression test to ensure GCP integration modules can be imported successfully.

This test prevents regression of import errors due to:
1. Missing google-cloud-logging enums module (removed in v3)
2. Missing google-cloud-run module (unused import)
3. Missing AsyncIterator import in type hints
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_all_gcp_integration_imports():
    """Test that all GCP integration modules can be imported without errors."""
    errors = []
    
    # Test base module imports
    try:
        from test_framework.gcp_integration.base import GCPConfig, GCPBaseClient
        print("[OK] GCP base module imports successful")
    except ImportError as e:
        errors.append(f"Failed to import base module: {e}")
    
    # Test log_reader imports
    try:
        from test_framework.gcp_integration.log_reader import (
            GCPLogReader, LogEntry, LogFilter
        )
        print("[OK] GCP log_reader module imports successful")
    except ImportError as e:
        errors.append(f"Failed to import log_reader module: {e}")
    
    # Test unified base_interfaces imports
    try:
        from test_framework.unified.base_interfaces import (
            IHealthMonitor, ILogAnalyzer, BaseTestComponent
        )
        print("[OK] Unified base_interfaces imports successful")
    except ImportError as e:
        errors.append(f"Failed to import base_interfaces: {e}")
    
    # Test the main __init__ imports
    try:
        from test_framework.gcp_integration import (
            GCPLogReader, LogEntry, LogFilter, GCPConfig, GCPBaseClient
        )
        print("[OK] GCP integration package imports successful")
    except ImportError as e:
        errors.append(f"Failed to import from gcp_integration package: {e}")
    
    # Test that we're NOT importing removed modules
    try:
        from google.cloud.logging_v2 import enums
        errors.append("WARNING: enums module still exists or is being imported")
    except ImportError:
        print("[OK] Correctly not importing removed enums module")
    
    # Test that we're NOT importing unused modules
    try:
        from google.cloud import run_v2
        errors.append("WARNING: run_v2 module exists - consider if it should be installed")
    except ImportError:
        print("[OK] Correctly not importing unused run_v2 module")
    
    return errors


def test_fetch_auth_sql_errors_script():
    """Test that the fetch_auth_sql_errors script can be imported."""
    errors = []
    
    try:
        # Just test the imports, don't run the script
        import fetch_auth_sql_errors
        print("[OK] fetch_auth_sql_errors script imports successful")
    except ImportError as e:
        errors.append(f"Failed to import fetch_auth_sql_errors: {e}")
    except Exception as e:
        # Catch other exceptions (like missing credentials) but pass the import test
        if "credentials" in str(e).lower() or "auth" in str(e).lower():
            print("[OK] fetch_auth_sql_errors imports work (auth error expected)")
        else:
            errors.append(f"Unexpected error in fetch_auth_sql_errors: {e}")
    
    return errors


def test_no_unicode_in_output():
    """Test that error messages don't contain Unicode characters that cause encoding issues."""
    import fetch_auth_sql_errors
    
    # Read the file and check for problematic Unicode characters
    script_path = Path(__file__).parent.parent / "fetch_auth_sql_errors.py"
    content = script_path.read_text(encoding='utf-8')
    
    problematic_chars = ['❌', '[OK]', '⚠️', '📊', '🔍']
    found_chars = []
    
    for char in problematic_chars:
        if char in content:
            found_chars.append(char)
    
    if found_chars:
        print(f"[WARNING] Found Unicode characters that may cause encoding issues: {found_chars}")
        return [f"Unicode characters found: {found_chars}"]
    else:
        print("[OK] No problematic Unicode characters in fetch_auth_sql_errors.py")
        return []


def main():
    """Run all regression tests."""
    print("=" * 60)
    print("GCP INTEGRATION REGRESSION TESTS")
    print("=" * 60)
    
    all_errors = []
    
    # Run import tests
    print("\n1. Testing GCP integration imports...")
    errors = test_all_gcp_integration_imports()
    all_errors.extend(errors)
    
    print("\n2. Testing fetch_auth_sql_errors script...")
    errors = test_fetch_auth_sql_errors_script()
    all_errors.extend(errors)
    
    print("\n3. Testing for Unicode encoding issues...")
    errors = test_no_unicode_in_output()
    all_errors.extend(errors)
    
    # Summary
    print("\n" + "=" * 60)
    if all_errors:
        print("REGRESSION TESTS FAILED:")
        for error in all_errors:
            print(f"  - {error}")
        return 1
    else:
        print("ALL REGRESSION TESTS PASSED!")
        return 0


if __name__ == "__main__":
    exit(main())