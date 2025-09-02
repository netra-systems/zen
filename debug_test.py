#!/usr/bin/env python3
"""Debug the UserExecutionContext test failure."""

import traceback
from netra_backend.app.services.user_execution_context import UserExecutionContext

def test_metadata_deep_copy():
    """Reproduction of the failing test."""
    print("Testing metadata deep copy...")
    
    try:
        # This is the exact code from the failing test
        nested_context = {
            "level1": {
                "level2": {
                    "value": "original"
                }
            }
        }
        
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            agent_context=nested_context
        )
        
        print("[OK] Context created successfully")
        
        # Modify nested structure
        context.agent_context["level1"]["level2"]["value"] = "modified"
        print("[OK] Modified nested structure")
        
        # Create child context
        child = context.create_child_context("test_operation")
        print("[OK] Child context created successfully")
        
        # Child should have snapshot, not reference
        expected_child_value = "modified"  # Should be the snapshot at creation time
        actual_child_value = child.agent_context["level1"]["level2"]["value"]
        print(f"Child value: {actual_child_value}, Expected: {expected_child_value}")
        
        assert actual_child_value == expected_child_value, f"Expected {expected_child_value}, got {actual_child_value}"
        
        # Further modifications to child should not affect parent
        child.agent_context["level1"]["level2"]["value"] = "child_modified"
        parent_value = context.agent_context["level1"]["level2"]["value"]
        print(f"Parent value after child modification: {parent_value}")
        
        assert parent_value == "modified", f"Expected parent to still be 'modified', got {parent_value}"
        
        print("✅ All assertions passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Exception type:", type(e).__name__)
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_metadata_deep_copy()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")