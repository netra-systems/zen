from shared.isolated_environment import IsolatedEnvironment
"""Minimal test to verify clickhouse_connect imports work"""

def test_clickhouse_import():
    """Test that clickhouse_connect can be imported correctly"""
    import clickhouse_connect
    from clickhouse_connect.driver.client import Client
    
    # If we get here, imports worked
    assert True
    print("Clickhouse imports successful!")

if __name__ == "__main__":
    test_clickhouse_import()
    print("Test passed!")