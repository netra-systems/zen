"""Simple validation of critical imports"""
try:
    from test_framework.ssot.base_test_case import SSotAsyncTestCase
    print("✅ SSOT base test case import - SUCCESS")
except Exception as e:
    print(f"❌ SSOT base test case import - FAILED: {e}")

try:
    from tests.e2e.staging.staging_test_config import get_staging_config
    print("✅ Staging config import - SUCCESS")
except Exception as e:
    print(f"❌ Staging config import - FAILED: {e}")

try:
    from shared.isolated_environment import IsolatedEnvironment
    print("✅ Isolated environment import - SUCCESS")
except Exception as e:
    print(f"❌ Isolated environment import - FAILED: {e}")