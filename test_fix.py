#!/usr/bin/env python3
"""Quick test script to verify the hardcoded stub fix"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.synthetic_data.advanced_generation_methods import AdvancedGenerationMethods
from app.core.exceptions_base import ValidationError

def test_empty_corpus_handling():
    """Test that empty corpus content raises ValidationError instead of returning test data"""
    
    # Create a mock patterns_helper and tool_helper
    class MockHelper:
        pass
    
    patterns_helper = MockHelper()
    tool_helper = MockHelper()
    
    # Create the AdvancedGenerationMethods instance
    adv_gen = AdvancedGenerationMethods(patterns_helper, tool_helper)
    
    # Test with empty list
    try:
        result = adv_gen._select_corpus_record([])
        print("FAIL: Expected ValidationError but got:", result)
        return False
    except ValidationError as e:
        print("PASS: Empty list correctly raises ValidationError")
        print(f"   Message: {e.error_details.message}")
        print(f"   Details: {e.error_details.details}")
    except Exception as e:
        print(f"FAIL: Unexpected exception type: {type(e).__name__}: {e}")
        return False
    
    # Test with None
    try:
        result = adv_gen._select_corpus_record(None)
        print("FAIL: Expected ValidationError but got:", result)
        return False
    except ValidationError as e:
        print("PASS: None correctly raises ValidationError")
        print(f"   Message: {e.error_details.message}")
        print(f"   Details: {e.error_details.details}")
    except Exception as e:
        print(f"FAIL: Unexpected exception type: {type(e).__name__}: {e}")
        return False
    
    # Test with valid data
    try:
        test_corpus = [{"prompt": "real_prompt", "response": "real_response"}]
        result = adv_gen._select_corpus_record(test_corpus)
        print("PASS: Valid corpus correctly returns data")
        print(f"   Result: {result}")
        
        # Verify it's not the old hardcoded test data
        if result == {"prompt": "test", "response": "test"}:
            print("FAIL: Still returning hardcoded test data!")
            return False
        else:
            print("PASS: No hardcoded test data returned")
    except Exception as e:
        print(f"FAIL: Valid corpus should not raise exception: {type(e).__name__}: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing hardcoded stub fix...")
    success = test_empty_corpus_handling()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)