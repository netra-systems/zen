"""
Verification script for database connectivity fix.
This script proves that the database URL validation and health check fixes work correctly.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys

async def test_none_database_url_handling():
    """Test that None database_url is handled gracefully."""
    from netra_backend.app.routes.health import _check_postgres_connection
    
    test_results = []
    
    # Test 1: None database_url in testing environment (should not raise)
    mock_db = AsyncMock()
    mock_config = MagicMock()
    mock_config.database_url = None
    
    with patch('netra_backend.app.routes.health.unified_config_manager.get_config', return_value=mock_config):
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.return_value = 'testing'
            
            try:
                await _check_postgres_connection(mock_db)
                test_results.append(("Test 1: None in testing env", "PASS"))
            except Exception as e:
                test_results.append(("Test 1: None in testing env", f"FAIL: {e}"))
    
    # Test 2: None database_url in staging environment (should raise)
    with patch('netra_backend.app.routes.health.unified_config_manager.get_config', return_value=mock_config):
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.return_value = 'staging'
            
            try:
                await _check_postgres_connection(mock_db)
                test_results.append(("Test 2: None in staging env", "FAIL: Should have raised"))
            except ValueError as e:
                if "DATABASE_URL is not configured" in str(e):
                    test_results.append(("Test 2: None in staging env", "PASS"))
                else:
                    test_results.append(("Test 2: None in staging env", f"FAIL: Wrong error: {e}"))
            except Exception as e:
                test_results.append(("Test 2: None in staging env", f"FAIL: Unexpected error: {e}"))
    
    # Test 3: Valid database_url executes query
    mock_config.database_url = 'postgresql://user:pass@localhost/testdb'
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 1
    mock_db.execute.return_value = mock_result
    
    with patch('netra_backend.app.routes.health.unified_config_manager.get_config', return_value=mock_config):
        try:
            await _check_postgres_connection(mock_db)
            if mock_db.execute.called:
                test_results.append(("Test 3: Valid URL executes query", "PASS"))
            else:
                test_results.append(("Test 3: Valid URL executes query", "FAIL: Query not executed"))
        except Exception as e:
            test_results.append(("Test 3: Valid URL executes query", f"FAIL: {e}"))
    
    # Test 4: Mock database URL is skipped
    mock_config.database_url = 'postgresql+mock://mockuser:mockpass@mockhost/mockdb'
    mock_db.execute.reset_mock()
    
    with patch('netra_backend.app.routes.health.unified_config_manager.get_config', return_value=mock_config):
        try:
            await _check_postgres_connection(mock_db)
            if not mock_db.execute.called:
                test_results.append(("Test 4: Mock URL skipped", "PASS"))
            else:
                test_results.append(("Test 4: Mock URL skipped", "FAIL: Query was executed"))
        except Exception as e:
            test_results.append(("Test 4: Mock URL skipped", f"FAIL: {e}"))
    
    return test_results

def test_config_loading():
    """Test that configs load database URLs properly."""
    test_results = []
    
    # Test 5: StagingConfig calls database URL loader
    try:
        from netra_backend.app.schemas.config import StagingConfig
        
        # Check if the method exists
        if hasattr(StagingConfig, '_load_database_url_from_unified_config_staging'):
            test_results.append(("Test 5: StagingConfig has URL loader", "PASS"))
        else:
            test_results.append(("Test 5: StagingConfig has URL loader", "FAIL: Method missing"))
    except Exception as e:
        test_results.append(("Test 5: StagingConfig has URL loader", f"FAIL: {e}"))
    
    # Test 6: ProductionConfig has database URL loader
    try:
        from netra_backend.app.schemas.config import ProductionConfig
        
        # Check if the method exists
        if hasattr(ProductionConfig, '_load_database_url_from_unified_config_production'):
            test_results.append(("Test 6: ProductionConfig has URL loader", "PASS"))
        else:
            test_results.append(("Test 6: ProductionConfig has URL loader", "FAIL: Method missing"))
    except Exception as e:
        test_results.append(("Test 6: ProductionConfig has URL loader", f"FAIL: {e}"))
    
    return test_results

def main():
    print("=" * 60)
    print("DATABASE CONNECTIVITY FIX VERIFICATION")
    print("=" * 60)
    print()
    
    # Run async tests
    async_results = asyncio.run(test_none_database_url_handling())
    
    # Run sync tests
    sync_results = test_config_loading()
    
    # Combine results
    all_results = async_results + sync_results
    
    # Display results
    passed = 0
    failed = 0
    
    for test_name, result in all_results:
        status_symbol = "[PASS]" if result == "PASS" else "[FAIL]"
        print(f"{status_symbol} {test_name}")
        if result != "PASS":
            print(f"       {result}")
        if result == "PASS":
            passed += 1
        else:
            failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    # Return appropriate exit code
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())