"""
Unit test for Issue #271: UnifiedIDManager.generate_run_id() signature incompatibility

This test creates a FAILING test that exposes the signature issue preventing
emergency security validation from running.

Issue: UnifiedIDManager.generate_run_id() requires thread_id parameter,
but emergency validation system calls it without arguments.
"""

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager


class TestUnifiedIdManagerIssue271(SSotBaseTestCase):
    """
    Test class to expose Issue #271: UnifiedIDManager signature incompatibility
    
    This test should FAIL initially to prove the issue exists, then PASS
    after the fix is implemented.
    """
    
    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.id_manager = UnifiedIDManager()
    
    def test_generate_run_id_without_thread_id_now_works(self):
        """
        FIXED TEST: This test verifies the signature issue has been resolved.
        
        The emergency security validation system calls generate_run_id() without
        arguments, and this should now work with the optional thread_id parameter.
        
        This test should PASS with the fix that makes thread_id optional.
        """
        # This call should now WORK with the fixed implementation
        # Simulating how the emergency validation system calls this method
        run_id = UnifiedIDManager.generate_run_id()
        
        # Verify the generated run_id is valid
        self.assertIsNotNone(run_id)
        self.assertIsInstance(run_id, str)
        self.assertGreater(len(run_id), 0)
        self.assertTrue(run_id.startswith("run_"))
        
        # Should contain a default thread ID when none provided
        self.assertIn("default_", run_id)
    
    def test_generate_run_id_with_thread_id_works(self):
        """
        This test should PASS: generate_run_id() works when thread_id is provided
        """
        thread_id = "test_thread_123"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        self.assertIsNotNone(run_id)
        self.assertIsInstance(run_id, str)
        self.assertIn(thread_id, run_id)
        self.assertTrue(run_id.startswith("run_"))
    
    def test_emergency_validation_pattern_works(self):
        """
        FIXED TEST: This test demonstrates the emergency validation pattern now works.
        
        Emergency validation system expects to call generate_run_id() without
        arguments as a class method, similar to how UnifiedIdGenerator works.
        """
        # This is the exact pattern that emergency validation uses
        # Emergency validation expects this to work without arguments
        run_id = UnifiedIDManager.generate_run_id()
        
        # Emergency validation can now proceed
        self.assertIsNotNone(run_id)
        self.assertIsInstance(run_id, str)
        self.assertGreater(len(run_id), 0)
        self.assertTrue(run_id.startswith("run_"))
    
    def test_comparison_with_unified_id_generator_pattern(self):
        """
        Test that shows the expected pattern that emergency validation expects.
        
        This test demonstrates what the emergency validation system expects
        to work - a parameterless class method for generating run IDs.
        """
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        
        # UnifiedIdGenerator has methods like generate_base_id() that work without parameters
        generator_base_id = UnifiedIdGenerator.generate_base_id()
        self.assertIsNotNone(generator_base_id)
        self.assertIsInstance(generator_base_id, str)
        
        # Emergency validation expects UnifiedIDManager to work similarly
        # This should now work with the fixed implementation
        manager_run_id = UnifiedIDManager.generate_run_id()
        # Should have similar interface for emergency validation
        self.assertIsNotNone(manager_run_id)
        self.assertIsInstance(manager_run_id, str)
        
        # Both should work without arguments for emergency validation compatibility
        self.assertGreater(len(generator_base_id), 0)
        self.assertGreater(len(manager_run_id), 0)
    
    def test_backward_compatibility_with_thread_id_parameter(self):
        """
        Test that the fix maintains backward compatibility.
        
        Existing code that passes thread_id should continue to work exactly as before.
        """
        thread_id = "custom_thread_12345"
        
        # This should work exactly as before the fix
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Verify it contains the provided thread_id
        self.assertIsNotNone(run_id)
        self.assertIsInstance(run_id, str)
        self.assertIn(thread_id, run_id)
        self.assertTrue(run_id.startswith("run_"))
        
        # Should NOT contain "default_" when explicit thread_id is provided
        self.assertNotIn("default_", run_id)
    
    def test_both_usage_patterns_produce_different_results(self):
        """
        Test that calling with and without thread_id produces different but valid results.
        """
        # Call without thread_id (uses default)
        run_id_default = UnifiedIDManager.generate_run_id()
        
        # Call with explicit thread_id
        run_id_custom = UnifiedIDManager.generate_run_id("explicit_thread")
        
        # Both should be valid but different
        self.assertIsNotNone(run_id_default)
        self.assertIsNotNone(run_id_custom)
        self.assertNotEqual(run_id_default, run_id_custom)
        
        # Default should contain "default_", custom should not
        self.assertIn("default_", run_id_default)
        self.assertNotIn("default_", run_id_custom)
        self.assertIn("explicit_thread", run_id_custom)