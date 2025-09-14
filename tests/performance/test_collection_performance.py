
"""
Test Collection Performance Validation
=====================================
Validates that test collection meets performance targets
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import unittest
import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class TestCollectionPerformanceTest(SSotBaseTestCase):
    """Validates test collection performance"""
    
    def test_agent_collection_performance(self):
        """Test that agent test collection takes <30 seconds"""
        from tests.unified_test_runner import UnifiedTestRunner
        
        start_time = time.time()
        runner = UnifiedTestRunner()
        
        # Simulate agent test collection
        try:
            tests = runner._collect_tests_for_pattern("*agent*")
            collection_time = time.time() - start_time
            
            # Performance assertion
            self.assertLess(
                collection_time, 30.0,
                f"Agent test collection took {collection_time:.2f}s (target: <30s)"
            )
            
            # Ensure we collected some tests
            self.assertGreater(
                len(tests) if tests else 0, 0,
                "No agent tests were collected"
            )
            
            print(f"✅ Agent test collection: {collection_time:.2f}s ({len(tests or [])} tests)")
            
        except Exception as e:
            self.fail(f"Test collection failed: {e}")
    
    def test_overall_collection_performance(self):
        """Test that overall collection is within acceptable limits"""
        from tests.unified_test_runner import UnifiedTestRunner
        
        start_time = time.time()
        runner = UnifiedTestRunner()
        
        # Test multiple common patterns
        patterns = ["*unit*", "*integration*", "*agent*"]
        total_tests = 0
        
        for pattern in patterns:
            try:
                tests = runner._collect_tests_for_pattern(pattern)
                total_tests += len(tests) if tests else 0
            except Exception:
                pass  # Continue with other patterns
        
        collection_time = time.time() - start_time
        
        # Performance assertion - should be reasonable for multiple patterns
        self.assertLess(
            collection_time, 60.0,
            f"Multi-pattern collection took {collection_time:.2f}s (target: <60s)"
        )
        
        print(f"✅ Multi-pattern collection: {collection_time:.2f}s ({total_tests} tests)")

if __name__ == '__main__':
    unittest.main()
