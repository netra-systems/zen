#!/usr/bin/env python3
"""
Basic test to verify UnifiedTestHarness functionality
"""
import asyncio
import sys
import os
sys.path.append('.')

# Set test environment
os.environ["TESTING"] = "1"

async def test_harness():
    """Test the unified test harness."""
    print("Testing UnifiedTestHarness...")
    
    try:
        from tests.unified.harness_complete import UnifiedTestHarnessComplete
        
        print("Creating harness...")
        harness = UnifiedTestHarnessComplete("basic_test")
        
        print("Starting services...")
        await harness.start_services()
        
        print("Services started successfully!")
        
        # Test basic functionality
        health = await harness.check_system_health()
        print(f"System health: {health}")
        
        print("Stopping services...")
        await harness.stop_all_services()
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_harness())