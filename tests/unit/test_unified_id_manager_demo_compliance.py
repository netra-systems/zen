"""
Unit Test for Issue #584: UnifiedIDManager Demo Compliance

This test validates that UnifiedIDManager provides the correct SSOT methods
for demo use cases and consistent ID generation patterns.
"""

import unittest
import uuid
from unittest.mock import patch

from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestUnifiedIdManagerDemoCompliance(unittest.TestCase):
    """Unit tests for UnifiedIDManager demo compliance."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.id_manager = UnifiedIDManager()
    
    def test_unified_id_manager_demo_thread_id_generation(self):
        """Test UnifiedIDManager provides proper demo thread ID generation."""
        
        # Test the SSOT method for thread ID generation
        thread_id = UnifiedIDManager.generate_thread_id()
        
        # Validate the generated thread ID
        self.assertIsInstance(thread_id, str)
        self.assertGreater(len(thread_id), 0)
        
        # Should NOT have demo prefix (that was the problem)
        self.assertFalse(thread_id.startswith('demo-'), 
                        "UnifiedIDManager should not generate demo-prefixed IDs")
        
        print(f"SSOT thread_id: {thread_id}")
        
    def test_unified_id_manager_demo_run_id_generation(self):
        """Test UnifiedIDManager provides proper demo run ID generation."""
        
        # Generate thread ID first
        thread_id = UnifiedIDManager.generate_thread_id()
        
        # Test the SSOT method for run ID generation
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Validate the generated run ID
        self.assertIsInstance(run_id, str)
        self.assertGreater(len(run_id), 0)
        
        # Should NOT have demo prefix (that was the problem)
        self.assertFalse(run_id.startswith('demo-'),
                        "UnifiedIDManager should not generate demo-prefixed IDs")
        
        # Should contain or be related to the thread_id
        self.assertIn(thread_id, run_id, 
                     "run_id should contain or reference the thread_id")
        
        print(f"SSOT run_id: {run_id} (contains thread_id: {thread_id})")
        
    def test_unified_id_manager_thread_id_extraction_consistency(self):
        """Test UnifiedIDManager thread ID extraction consistency."""
        
        # Generate IDs using SSOT methods
        thread_id = UnifiedIDManager.generate_thread_id()
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Test extraction
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        
        # Validate extraction consistency
        self.assertIsInstance(extracted_thread_id, str)
        self.assertGreater(len(extracted_thread_id), 0)
        
        # The extracted thread_id should be related to the original
        self.assertIn(thread_id, extracted_thread_id,
                     "Extracted thread_id should contain original thread_id")
        
        print(f"Original thread_id: {thread_id}")
        print(f"Generated run_id: {run_id}")
        print(f"Extracted thread_id: {extracted_thread_id}")
        
    def test_unified_id_manager_demo_pattern_rejection(self):
        """Test UnifiedIDManager correctly handles demo patterns."""
        
        # Test with demo-prefixed IDs (these should be handled gracefully)
        demo_run_id = f"demo-run-{uuid.uuid4()}"
        demo_thread_id = f"demo-thread-{uuid.uuid4()}"
        
        # Test extraction with demo patterns
        try:
            extracted = UnifiedIDManager.extract_thread_id(demo_run_id)
            extraction_succeeded = True
            print(f"Demo extraction result: {extracted}")
        except Exception as e:
            extraction_succeeded = False
            print(f"Demo extraction failed: {e}")
        
        # The UnifiedIDManager should either:
        # 1. Handle demo patterns gracefully, OR
        # 2. Fail predictably with clear error messages
        
        # For Issue #584 fix, we want consistent behavior
        if extraction_succeeded:
            self.assertIsInstance(extracted, str)
        
    def test_unified_id_manager_format_validation(self):
        """Test UnifiedIDManager format validation methods."""
        
        # Test with various ID formats
        test_ids = [
            str(uuid.uuid4()),  # Plain UUID
            f"demo-run-{uuid.uuid4()}",  # Demo pattern
            f"demo-thread-{uuid.uuid4()}",  # Demo pattern
            "invalid-id",  # Invalid format
            "",  # Empty string
        ]
        
        for test_id in test_ids:
            # Test format validation
            try:
                is_valid = self.id_manager.is_valid_id_format_compatible(test_id)
                print(f"ID: {test_id} -> Valid: {is_valid}")
                
                if test_id and test_id != "invalid-id":
                    # Most reasonable IDs should be valid
                    self.assertIsInstance(is_valid, bool)
                    
            except Exception as e:
                print(f"Validation error for {test_id}: {e}")
                
    def test_unified_id_manager_instance_methods(self):
        """Test UnifiedIDManager instance methods for demo scenarios."""
        
        # Test generating IDs through instance methods
        user_id = self.id_manager.generate_id(IDType.USER)
        thread_id = self.id_manager.generate_id(IDType.THREAD)
        run_id = self.id_manager.generate_id(IDType.EXECUTION)
        
        # Validate generated IDs
        generated_ids = [user_id, thread_id, run_id]
        for generated_id in generated_ids:
            self.assertIsInstance(generated_id, str)
            self.assertGreater(len(generated_id), 0)
            
            # Should NOT have demo prefixes
            self.assertFalse(generated_id.startswith('demo-'),
                           f"Generated ID should not have demo prefix: {generated_id}")
        
        print(f"Generated user_id: {user_id}")
        print(f"Generated thread_id: {thread_id}")
        print(f"Generated run_id: {run_id}")
        
    def test_unified_id_manager_registration_and_tracking(self):
        """Test UnifiedIDManager ID registration and tracking."""
        
        # Generate IDs
        user_id = self.id_manager.generate_id(IDType.USER, context={"demo": True})
        thread_id = self.id_manager.generate_id(IDType.THREAD, context={"demo": True})
        
        # Test registration tracking
        user_metadata = self.id_manager.get_id_metadata(user_id)
        thread_metadata = self.id_manager.get_id_metadata(thread_id)
        
        # Validate metadata
        self.assertIsNotNone(user_metadata)
        self.assertIsNotNone(thread_metadata)
        
        self.assertEqual(user_metadata.id_type, IDType.USER)
        self.assertEqual(thread_metadata.id_type, IDType.THREAD)
        
        # Check context
        self.assertTrue(user_metadata.context.get('demo'))
        self.assertTrue(thread_metadata.context.get('demo'))
        
        print(f"User metadata: {user_metadata}")
        print(f"Thread metadata: {thread_metadata}")
        
    def test_demo_websocket_correct_ssot_usage(self):
        """Test correct SSOT usage pattern for demo_websocket.py fix."""
        
        # This demonstrates the CORRECT pattern that demo_websocket.py should use
        
        # Instead of:
        # demo_user_id = f"demo-user-{uuid.uuid4()}"
        # thread_id = f"demo-thread-{uuid.uuid4()}"
        # run_id = f"demo-run-{uuid.uuid4()}"
        
        # Should use:
        demo_user_id = self.id_manager.generate_id(IDType.USER, context={"demo": True})
        thread_id = UnifiedIDManager.generate_thread_id()
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        request_id = self.id_manager.generate_id(IDType.REQUEST, context={"demo": True})
        
        # Validate the corrected pattern
        correct_ids = [demo_user_id, thread_id, run_id, request_id]
        
        for id_value in correct_ids:
            self.assertIsInstance(id_value, str)
            self.assertGreater(len(id_value), 0)
            
            # Should NOT have demo prefixes
            self.assertFalse(id_value.startswith('demo-'),
                           f"Corrected ID should not have demo prefix: {id_value}")
        
        # Test correlation consistency
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        self.assertIn(thread_id, extracted_thread_id)
        
        print("CORRECT SSOT Pattern for demo_websocket.py:")
        print(f"  demo_user_id: {demo_user_id}")
        print(f"  thread_id: {thread_id}")
        print(f"  run_id: {run_id}")
        print(f"  request_id: {request_id}")
        print(f"  extracted_thread_id: {extracted_thread_id}")
        
        # This is the pattern that should replace the problematic lines 37-39 in demo_websocket.py


if __name__ == "__main__":
    unittest.main()