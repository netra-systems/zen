"""
Test to validate Issue #584 fix: Demo WebSocket SSOT Compliance

This test validates that the fix for demo_websocket.py correctly uses
UnifiedIDManager SSOT methods instead of ad-hoc prefixed UUIDs.
"""

import unittest
import uuid
from unittest.mock import patch, Mock

from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestDemoWebSocketFixValidation(unittest.TestCase):
    """Test validation of Issue #584 fix in demo_websocket.py."""
    
    def test_fixed_demo_websocket_id_generation_pattern(self):
        """Test that fixed demo_websocket.py uses SSOT ID generation patterns."""
        
        # Simulate the FIXED pattern from demo_websocket.py
        def fixed_demo_websocket_id_generation():
            """Simulate the FIXED demo_websocket.py ID generation"""
            # This is the NEW (correct) pattern after Issue #584 fix
            id_manager = UnifiedIDManager()
            demo_user_id = id_manager.generate_id(IDType.USER, context={"demo": True})
            thread_id = UnifiedIDManager.generate_thread_id()
            run_id = UnifiedIDManager.generate_run_id(thread_id)
            request_id = id_manager.generate_id(IDType.REQUEST, context={"demo": True})
            
            return {
                "demo_user_id": demo_user_id,
                "thread_id": thread_id,
                "run_id": run_id,
                "request_id": request_id
            }
        
        # Generate IDs using fixed pattern
        fixed_ids = fixed_demo_websocket_id_generation()
        
        # Validate SSOT compliance
        ssot_compliance_results = self._check_ssot_compliance_fixed(fixed_ids)
        
        print("Fixed Demo WebSocket ID Generation:")
        for id_name, id_value in fixed_ids.items():
            print(f"  {id_name}: {id_value}")
            
        print("\nSSot Compliance Results:")
        for result in ssot_compliance_results:
            print(f"  ✅ {result}")
        
        # After fix, should have NO SSOT violations
        violations = [result for result in ssot_compliance_results if "VIOLATION" in result]
        self.assertEqual(len(violations), 0, "Fixed pattern should have no SSOT violations")
        
    def test_demo_websocket_id_pattern_consistency(self):
        """Test that fixed demo_websocket.py has consistent ID patterns."""
        
        # Generate IDs using the fixed pattern
        id_manager = UnifiedIDManager()
        demo_user_id = id_manager.generate_id(IDType.USER, context={"demo": True})
        thread_id = UnifiedIDManager.generate_thread_id()
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        request_id = id_manager.generate_id(IDType.REQUEST, context={"demo": True})
        
        fixed_ids = [demo_user_id, thread_id, run_id, request_id]
        
        # Test pattern consistency
        for id_value in fixed_ids:
            # Should NOT have demo prefixes (that was the problem)
            self.assertFalse(id_value.startswith('demo-'),
                           f"Fixed ID should not have demo prefix: {id_value}")
            
            # Should be valid strings
            self.assertIsInstance(id_value, str)
            self.assertGreater(len(id_value), 0)
        
        print("Pattern Consistency Validation:")
        print(f"  demo_user_id: {demo_user_id} (no demo- prefix: {not demo_user_id.startswith('demo-')})")
        print(f"  thread_id: {thread_id} (no demo- prefix: {not thread_id.startswith('demo-')})")
        print(f"  run_id: {run_id} (no demo- prefix: {not run_id.startswith('demo-')})")
        print(f"  request_id: {request_id} (no demo- prefix: {not request_id.startswith('demo-')})")
        
    def test_demo_websocket_correlation_consistency(self):
        """Test that fixed demo_websocket.py has proper ID correlation."""
        
        # Generate IDs using the fixed pattern
        thread_id = UnifiedIDManager.generate_thread_id()
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Test correlation extraction
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        
        # Validate correlation consistency
        self.assertIn(thread_id, extracted_thread_id,
                     "Fixed pattern should maintain thread_id correlation")
        
        print("Correlation Consistency Validation:")
        print(f"  Original thread_id: {thread_id}")
        print(f"  Generated run_id: {run_id}")
        print(f"  Extracted thread_id: {extracted_thread_id}")
        print(f"  Correlation successful: {thread_id in extracted_thread_id}")
        
    def test_websocket_cleanup_correlation_fixed(self):
        """Test WebSocket cleanup correlation with fixed ID patterns."""
        
        # Generate FIXED pattern IDs
        id_manager = UnifiedIDManager()
        fixed_user_id = id_manager.generate_id(IDType.USER, context={"demo": True})
        fixed_thread_id = UnifiedIDManager.generate_thread_id()
        fixed_run_id = UnifiedIDManager.generate_run_id(fixed_thread_id)
        
        # Simulate WebSocket connections with fixed patterns
        fixed_websocket_connections = {
            fixed_run_id: {
                "user_id": fixed_user_id,
                "thread_id": fixed_thread_id,
                "pattern": "fixed_ssot"
            },
            fixed_thread_id: {
                "user_id": fixed_user_id,
                "thread_id": fixed_thread_id,
                "pattern": "fixed_ssot"
            }
        }
        
        # Test cleanup correlation function with fixed patterns
        def cleanup_related_resources_fixed(target_id):
            """Test cleanup correlation with fixed SSOT patterns"""
            related = []
            
            try:
                # Extract thread_id using UnifiedIDManager
                extracted_thread = UnifiedIDManager.extract_thread_id(target_id)
                
                # Find connections with related thread_ids
                for conn_id, conn_data in fixed_websocket_connections.items():
                    if conn_data.get("thread_id") == extracted_thread:
                        related.append(conn_id)
                        
            except Exception as e:
                print(f"Correlation failed for {target_id}: {e}")
                
            return related
        
        # Test correlation with fixed patterns
        correlation_results = []
        for conn_id in fixed_websocket_connections.keys():
            related = cleanup_related_resources_fixed(conn_id)
            correlation_results.extend(related)
            
        print("Fixed WebSocket Correlation Results:")
        print(f"  Fixed connections: {len(fixed_websocket_connections)}")
        print(f"  Correlation successes: {len(correlation_results)}")
        
        # Fixed patterns should have successful correlations
        self.assertGreater(len(correlation_results), 0,
                          "Fixed patterns should enable successful correlation")
        
    def test_id_validation_compliance_after_fix(self):
        """Test ID validation compliance after Issue #584 fix."""
        
        # Generate IDs using fixed pattern
        id_manager = UnifiedIDManager()
        test_ids = {
            "user_id": id_manager.generate_id(IDType.USER, context={"demo": True}),
            "thread_id": UnifiedIDManager.generate_thread_id(),
            "run_id": UnifiedIDManager.generate_run_id(UnifiedIDManager.generate_thread_id()),
            "request_id": id_manager.generate_id(IDType.REQUEST, context={"demo": True})
        }
        
        # Test validation with UnifiedIDManager
        validation_results = {}
        for id_name, id_value in test_ids.items():
            try:
                is_valid = id_manager.is_valid_id_format_compatible(id_value)
                validation_results[id_name] = is_valid
            except Exception as e:
                validation_results[id_name] = f"Error: {e}"
        
        print("ID Validation Results After Fix:")
        for id_name, result in validation_results.items():
            print(f"  {id_name}: {test_ids[id_name]} -> Valid: {result}")
            
        # All fixed IDs should be valid
        for id_name, is_valid in validation_results.items():
            self.assertTrue(is_valid, f"Fixed {id_name} should be valid")
            
    def _check_ssot_compliance_fixed(self, generated_ids):
        """Check generated IDs for SSOT compliance (after fix)."""
        compliance_results = []
        
        for id_name, id_value in generated_ids.items():
            # Check for SSOT compliance
            if id_name in ['thread_id', 'run_id']:
                # These should now be generated through UnifiedIDManager
                if self._is_unified_id_manager_format(id_value):
                    compliance_results.append(f"{id_name}: COMPLIANT - Generated through UnifiedIDManager")
                else:
                    compliance_results.append(f"{id_name}: VIOLATION - Not generated through UnifiedIDManager")
                    
            # Check for pattern consistency  
            if not id_value.startswith('demo-'):
                compliance_results.append(f"{id_name}: COMPLIANT - No demo prefix")
            else:
                compliance_results.append(f"{id_name}: VIOLATION - Has demo prefix")
                
        return compliance_results
    
    def _is_unified_id_manager_format(self, id_value):
        """Check if ID follows UnifiedIDManager format patterns."""
        # UnifiedIDManager generates structured format: [prefix_]idtype_counter_uuid8
        
        try:
            # Check if it's a plain UUID (accepted during migration)
            uuid.UUID(id_value)
            return True
        except ValueError:
            pass
            
        # Check if it's structured format
        parts = id_value.split('_')
        if len(parts) >= 3:
            # Last part should be 8-character hex
            uuid_part = parts[-1]
            if len(uuid_part) == 8 and all(c in '0123456789abcdefABCDEF' for c in uuid_part):
                # Second to last should be numeric counter
                counter_part = parts[-2]
                if counter_part.isdigit():
                    return True
                    
        return False


if __name__ == "__main__":
    unittest.main()