#!/usr/bin/env python3
"""
Test script to verify Cloud SQL proxy URL construction.
This validates that DatabaseURLBuilder correctly handles Cloud SQL connections.
"""

import sys
import os
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database_url_builder import DatabaseURLBuilder


def test_cloud_sql_url_construction():
    """Test that Cloud SQL proxy URLs are constructed correctly."""
    print("Testing Cloud SQL Proxy URL Construction")
    print("=" * 50)
    
    # Test case 1: Cloud SQL with Unix socket
    cloud_sql_env = {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:staging-shared-postgres",
        "POSTGRES_USER": "netra_user",
        "POSTGRES_PASSWORD": "test_password",
        "POSTGRES_DB": "netra_staging",
        "POSTGRES_PORT": "5432"
    }
    
    builder = DatabaseURLBuilder(cloud_sql_env)
    
    # Check detection
    is_cloud_sql = builder.cloud_sql.is_cloud_sql
    print(f"✓ Cloud SQL detected: {is_cloud_sql}")
    assert is_cloud_sql, "Failed to detect Cloud SQL configuration"
    
    # Get async URL
    async_url = builder.cloud_sql.async_url
    print(f"✓ Async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
    assert async_url, "Failed to generate async URL"
    assert "postgresql+asyncpg://" in async_url, "Wrong protocol for async URL"
    assert "@/" in async_url, "Wrong format for Unix socket connection"
    assert "?host=/cloudsql/" in async_url, "Missing host parameter for Unix socket"
    
    # Get sync URL
    sync_url = builder.cloud_sql.sync_url
    print(f"✓ Sync URL: {DatabaseURLBuilder.mask_url_for_logging(sync_url)}")
    assert sync_url, "Failed to generate sync URL"
    assert sync_url.startswith("postgresql://"), "Wrong protocol for sync URL"
    assert "@/" in sync_url, "Wrong format for Unix socket connection"
    assert "?host=/cloudsql/" in sync_url, "Missing host parameter for Unix socket"
    
    # Test environment-specific URL retrieval
    staging_url = builder.get_url_for_environment(sync=False)
    print(f"✓ Staging environment URL: {DatabaseURLBuilder.mask_url_for_logging(staging_url)}")
    assert staging_url == async_url, "Environment URL doesn't match expected async URL"
    
    staging_sync_url = builder.get_url_for_environment(sync=True)
    print(f"✓ Staging sync URL: {DatabaseURLBuilder.mask_url_for_logging(staging_sync_url)}")
    assert staging_sync_url == sync_url, "Environment sync URL doesn't match expected sync URL"
    
    print("\n" + "=" * 50)
    print("✅ All Cloud SQL proxy URL tests passed!")
    
    # Test case 2: Regular TCP connection (for comparison)
    print("\nTesting regular TCP connection for comparison:")
    tcp_env = {
        "ENVIRONMENT": "development",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres",
        "POSTGRES_DB": "netra_dev",
        "POSTGRES_PORT": "5432"
    }
    
    tcp_builder = DatabaseURLBuilder(tcp_env)
    
    # Check detection
    is_cloud_sql_tcp = tcp_builder.cloud_sql.is_cloud_sql
    print(f"✓ Cloud SQL detected (should be False): {is_cloud_sql_tcp}")
    assert not is_cloud_sql_tcp, "Incorrectly detected TCP as Cloud SQL"
    
    tcp_url = tcp_builder.tcp.async_url
    print(f"✓ TCP URL: {DatabaseURLBuilder.mask_url_for_logging(tcp_url)}")
    assert tcp_url, "Failed to generate TCP URL"
    assert "@localhost:" in tcp_url or "@postgres:" in tcp_url, "Wrong host in TCP URL"
    assert "?host=" not in tcp_url, "Unexpected host parameter in TCP URL"
    
    print("\n✅ All tests passed successfully!")
    return True


def test_deployment_script_compliance():
    """Verify deployment script doesn't set DATABASE_URL."""
    print("\nVerifying deployment script compliance:")
    print("=" * 50)
    
    deploy_script_path = project_root / "scripts" / "deploy_to_gcp.py"
    with open(deploy_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that we're not constructing DATABASE_URL
    checks = [
        ("DATABASE_URL construction removed", 'env_vars["DATABASE_URL"]' not in content),
        ("No DATABASE_URL in environment", 'env_vars.append(f"DATABASE_URL=' not in content),
        ("DatabaseURLBuilder comment present", "DatabaseURLBuilder" in content),
        ("SSOT comment present", "SSOT" in content)
    ]
    
    all_passed = True
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n✅ Deployment script compliance verified!")
    else:
        print("\n❌ Deployment script compliance issues found!")
    
    return all_passed


if __name__ == "__main__":
    try:
        test_passed = test_cloud_sql_url_construction()
        compliance_passed = test_deployment_script_compliance()
        
        if test_passed and compliance_passed:
            print("\n" + "=" * 50)
            print("🎉 All Cloud SQL proxy tests passed!")
            print("The fix has been successfully applied and verified.")
            sys.exit(0)
        else:
            print("\n⚠️ Some tests failed. Please review the output above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)