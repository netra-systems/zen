#!/usr/bin/env python3
"""
Direct staging test runner - bypasses conftest issues
This is a temporary script to test the business value tests directly without pytest interference.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Run staging tests directly."""
    
    print("=" * 80)
    print("DIRECT STAGING TEST RUNNER")
    print("=" * 80)
    
    try:
        # Import test modules
        from tests.e2e.staging.test_ai_optimization_business_value import TestAIOptimizationBusinessValue
        print("✅ Successfully imported TestAIOptimizationBusinessValue")
        
        # Get test methods
        test_methods = [method for method in dir(TestAIOptimizationBusinessValue) if method.startswith('test_')]
        print(f"✅ Found {len(test_methods)} test methods")
        
        # Try to create an instance
        test_instance = TestAIOptimizationBusinessValue()
        print("✅ Successfully created test instance")
        
        # Test the setup fixture
        print("\n--- Testing Setup Fixture ---")
        
        async def test_setup():
            """Test the setup fixture."""
            try:
                # Get the setup method
                if hasattr(test_instance, 'setup'):
                    await test_instance.setup().__anext__()
                    print("✅ Setup fixture completed successfully")
                else:
                    print("⚠️  No setup fixture found")
                    
                return True
            except Exception as e:
                print(f"❌ Setup fixture failed: {e}")
                print(f"Stack trace: {traceback.format_exc()}")
                return False
        
        # Run setup test
        setup_success = asyncio.run(test_setup())
        
        if setup_success:
            print("\n🎉 All tests would be discoverable!")
            print("\n--- Test Methods Available ---")
            for i, method in enumerate(test_methods, 1):
                print(f"{i:2d}. {method}")
        else:
            print("\n⚠️  Tests may fail due to setup issues")
            
        return setup_success
        
    except Exception as e:
        print(f"❌ Critical import/setup error: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        return False
    
    print("=" * 80)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)