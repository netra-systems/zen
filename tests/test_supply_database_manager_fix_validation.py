"""
Validation test for SupplyResearcherAgent import paths.

This test validates that the SupplyResearcherAgent can be imported correctly
using the fixed import paths.
"""

import pytest

def test_supply_researcher_agent_import_from_module():
    """Test that SupplyResearcherAgent can be imported from module level."""
    # Should import without error
    from netra_backend.app.agents.supply_researcher import SupplyResearcherAgent
    
    # Verify it's a class
    assert isinstance(SupplyResearcherAgent, type)
    
    # Verify it has expected methods
    assert hasattr(SupplyResearcherAgent, 'execute')

def test_supply_researcher_agent_import_from_agent():
    """Test that SupplyResearcherAgent can be imported from agent.py directly.""" 
    # Should import without error
    from netra_backend.app.agents.supply_researcher.agent import SupplyResearcherAgent
    
    # Verify it's a class
    assert isinstance(SupplyResearcherAgent, type)
    
    # Verify it has expected methods
    assert hasattr(SupplyResearcherAgent, 'execute')

def test_supply_database_manager_import():
    """Test that SupplyDatabaseManager can be imported from correct location."""
    # Should import without error
    from netra_backend.app.agents.supply_researcher.supply_database_manager import SupplyDatabaseManager
    
    # Verify it's a class
    assert isinstance(SupplyDatabaseManager, type)
    
    # Verify it has the expected method
    assert hasattr(SupplyDatabaseManager, 'update_database')

if __name__ == "__main__":
    print("Running validation tests for SupplyResearcherAgent import paths...")
    
    test_supply_researcher_agent_import_from_module()
    print("✅ SupplyResearcherAgent imports correctly from module level")
    
    test_supply_researcher_agent_import_from_agent() 
    print("✅ SupplyResearcherAgent imports correctly from agent.py")
    
    test_supply_database_manager_import()
    print("✅ SupplyDatabaseManager imports correctly")
    
    print("\n🎉 All validation tests passed! The import paths are working correctly.")