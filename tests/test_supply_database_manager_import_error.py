"""Test to reproduce SupplyDatabaseManager import error.

This test reproduces the P1 critical bug where SupplyDatabaseManager
cannot be imported from netra_backend.app.db.database_manager.
"""

import pytest
import sys
import importlib
from shared.isolated_environment import IsolatedEnvironment


def test_supply_database_manager_import_error():
    """Test that reproduces the SupplyDatabaseManager import error."""
    
    # This should fail with ImportError: cannot import name 'SupplyDatabaseManager'
    with pytest.raises(ImportError) as exc_info:
        from netra_backend.app.db.database_manager import SupplyDatabaseManager
    
    # Verify the error message
    assert "cannot import name 'SupplyDatabaseManager'" in str(exc_info.value)


def test_supply_researcher_agent_import_fails():
    """Test that supply_researcher agent fails to import due to missing SupplyDatabaseManager."""
    
    # Clear any cached imports
    if 'netra_backend.app.agents.supply_researcher' in sys.modules:
        del sys.modules['netra_backend.app.agents.supply_researcher']
    if 'netra_backend.app.agents.supply_researcher.agent' in sys.modules:
        del sys.modules['netra_backend.app.agents.supply_researcher.agent']
    
    # This should fail when trying to import the agent
    with pytest.raises(ImportError) as exc_info:
        import netra_backend.app.agents.supply_researcher
    
    # Verify it's the SupplyDatabaseManager import that's failing
    assert "SupplyDatabaseManager" in str(exc_info.value)


def test_database_manager_only_has_base_class():
    """Verify that database_manager.py only contains DatabaseManager, not SupplyDatabaseManager."""
    
    # Import the module
    from netra_backend.app.db import database_manager
    
    # Check what's available
    available_classes = [name for name in dir(database_manager) if not name.startswith('_')]
    
    # DatabaseManager should exist
    assert 'DatabaseManager' in available_classes
    
    # SupplyDatabaseManager should NOT exist
    assert 'SupplyDatabaseManager' not in available_classes
    
    # Verify we can instantiate DatabaseManager
    assert hasattr(database_manager, 'DatabaseManager')
    
    # Verify SupplyDatabaseManager doesn't exist
    assert not hasattr(database_manager, 'SupplyDatabaseManager')


if __name__ == "__main__":
    # Run the tests to demonstrate the error
    print("Running test to reproduce SupplyDatabaseManager import error...")
    
    try:
        test_supply_database_manager_import_error()
        print("✗ Test should have caught ImportError but didn't!")
    except AssertionError:
        print("✓ Test correctly identified missing SupplyDatabaseManager import")
    
    try:
        test_database_manager_only_has_base_class()
        print("✓ Confirmed database_manager.py only has DatabaseManager class")
    except AssertionError as e:
        print(f"✗ Unexpected state in database_manager.py: {e}")
    
    try:
        test_supply_researcher_agent_import_fails()
        print("✓ Confirmed supply_researcher agent fails to import")
    except AssertionError:
        print("✗ Supply researcher agent import didn't fail as expected")
    
    print("
Conclusion: SupplyDatabaseManager class is missing and needs to be implemented.")
    pass