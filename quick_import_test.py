import sys

# Test 1: Direct import from gcp_error_reporter
print("Test 1: Direct import from gcp_error_reporter")
try:
    from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context
    print("✅ SUCCESS")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 2: Import from monitoring module __init__
print("Test 2: Import from monitoring module __init__")
try:
    from netra_backend.app.services.monitoring import set_request_context, clear_request_context
    print("✅ SUCCESS")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 3: Test function calls
print("Test 3: Test function calls")
try:
    set_request_context("test-user", "test-trace")
    clear_request_context()
    print("✅ SUCCESS")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

print("🎉 ALL BASIC TESTS PASSED!")