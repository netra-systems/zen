"""Simple test to verify agent initialization fixes work."""

import asyncio
import sys
import os

# Add to path for imports
sys.path.insert(0, os.getcwd())

async def test_imports():
    """Test that our new modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test initialization manager import
        from app.agents.initialization_manager import AgentInitializationManager
        print("+ AgentInitializationManager imported")
        
        # Test enhanced registry import  
        from app.agents.supervisor.agent_registry_enhanced import EnhancedAgentRegistry
        print("+ EnhancedAgentRegistry imported")
        
        # Test data processing operations import
        from app.agents.data_sub_agent.data_processing_operations import DataProcessingOperations
        print("+ DataProcessingOperations imported")
        
        # Test agent core import
        from app.agents.data_sub_agent.agent_core import DataSubAgent as CoreDataSubAgent
        print("+ CoreDataSubAgent imported")
        
        return True
        
    except Exception as e:
        print(f"- Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_basic_functionality():
    """Test basic functionality of new components."""
    print("\nTesting basic functionality...")
    
    try:
        from unittest.mock import Mock
        from app.agents.initialization_manager import AgentInitializationManager
        
        # Test initialization manager creation
        init_manager = AgentInitializationManager(max_retries=2, timeout_seconds=5)
        print("+ AgentInitializationManager created")
        
        # Test stats retrieval
        stats = init_manager.get_initialization_stats()
        print(f"+ Initial stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"- Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_file_compliance():
    """Test that files comply with 300-line limit."""
    print("\nTesting file compliance...")
    
    files_to_check = [
        "app/agents/initialization_manager.py",
        "app/agents/supervisor/agent_registry_enhanced.py", 
        "app/agents/data_sub_agent/agent_core.py",
        "app/agents/data_sub_agent/data_processing_operations.py",
        "app/agents/data_sub_agent/agent_modernized.py"
    ]
    
    compliant_files = 0
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                line_count = len(lines)
                
            if line_count <= 300:
                print(f"+ {file_path}: {line_count} lines (compliant)")
                compliant_files += 1
            else:
                print(f"- {file_path}: {line_count} lines (exceeds 300)")
                
        except FileNotFoundError:
            print(f"- {file_path}: File not found")
        except Exception as e:
            print(f"- {file_path}: Error checking - {e}")
    
    print(f"\nCompliance: {compliant_files}/{len(files_to_check)} files comply with 300-line limit")
    return compliant_files == len(files_to_check)

async def main():
    """Run all tests."""
    print("=== Agent Initialization Fix Tests ===\n")
    
    tests = [
        ("Imports", test_imports),
        ("Basic Functionality", test_basic_functionality),
        ("File Compliance", test_file_compliance)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"- {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print(f"\n=== Test Summary ===")
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    return passed == len(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\nTest result: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1)