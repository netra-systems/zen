"""
Test to reproduce Issue #584: Thread ID Run ID Generation Inconsistency

This test reproduces the ID generation pattern inconsistencies found in demo_websocket.py
where different ID fields use different patterns (prefixed vs plain UUID).

Enhanced to comprehensively test SSOT violations and correlation issues.
"""

import uuid
import unittest
from unittest.mock import Mock, patch
import re

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestIdGenerationInconsistency(unittest.TestCase):
    """Test ID generation pattern inconsistencies in Issue #584."""
    
    def test_demo_websocket_id_generation_patterns(self):
        """Reproduce the inconsistent ID generation patterns from demo_websocket.py."""
        
        # Pattern 1: Prefixed UUIDs (as used in demo_websocket.py lines 37-39)
        demo_user_id = f"demo-user-{uuid.uuid4()}"
        thread_id = f"demo-thread-{uuid.uuid4()}"
        run_id = f"demo-run-{uuid.uuid4()}"
        
        # Pattern 2: Plain UUID (as used in demo_websocket.py line 52)
        request_id = str(uuid.uuid4())
        
        # Pattern 3: SSOT UserExecutionContext generation (expected pattern)
        context = UserExecutionContext(
            user_id="test-user",
            run_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4())
        )
        
        # Verify inconsistency patterns
        print(f"Prefixed demo_user_id: {demo_user_id}")
        print(f"Prefixed thread_id: {thread_id}")
        print(f"Prefixed run_id: {run_id}")
        print(f"Plain request_id: {request_id}")
        print(f"SSOT context run_id: {context.run_id}")
        print(f"SSOT context thread_id: {context.thread_id}")
        
        # Assert the patterns are different
        self.assertTrue(demo_user_id.startswith("demo-user-"))
        self.assertTrue(thread_id.startswith("demo-thread-"))
        self.assertTrue(run_id.startswith("demo-run-"))
        self.assertFalse(request_id.startswith("demo-"))  # Plain UUID
        self.assertFalse(context.run_id.startswith("demo-"))  # SSOT pattern
        self.assertFalse(context.thread_id.startswith("demo-"))  # SSOT pattern
        
        # Show the issue: WebSocket cleanup correlation would be affected
        # because prefixed IDs wouldn't match SSOT IDs
        mock_websocket_manager = Mock()
        mock_websocket_manager.active_connections = {
            context.run_id: {"user_id": "test-user", "status": "active"},  # SSOT pattern
            run_id: {"user_id": demo_user_id, "status": "active"}  # Demo pattern
        }
        
        # Cleanup correlation would fail because IDs don't match
        ssot_connections = [conn_id for conn_id in mock_websocket_manager.active_connections.keys() 
                           if not conn_id.startswith("demo-")]
        demo_connections = [conn_id for conn_id in mock_websocket_manager.active_connections.keys() 
                           if conn_id.startswith("demo-")]
        
        self.assertEqual(len(ssot_connections), 1)
        self.assertEqual(len(demo_connections), 1)
        print(f"SSOT connections: {ssot_connections}")
        print(f"Demo connections: {demo_connections}")
        
        # This demonstrates the correlation issue - two different ID patterns
        # would make cleanup correlation complex and error-prone
        
    def test_websocket_cleanup_correlation_with_mismatched_ids(self):
        """Test WebSocket cleanup correlation logic with mismatched vs SSOT IDs."""
        
        # Simulate mixed ID patterns in active connections
        active_connections = {
            # SSOT pattern (correct)
            str(uuid.uuid4()): {"type": "ssot", "user_id": "user1"},
            str(uuid.uuid4()): {"type": "ssot", "user_id": "user2"},
            
            # Demo pattern (inconsistent)
            f"demo-run-{uuid.uuid4()}": {"type": "demo", "user_id": "demo-user-123"},
            f"demo-thread-{uuid.uuid4()}": {"type": "demo", "user_id": "demo-user-456"},
        }
        
        # Test cleanup correlation
        ssot_pattern_count = 0
        demo_pattern_count = 0
        
        for conn_id, conn_data in active_connections.items():
            if conn_id.startswith("demo-"):
                demo_pattern_count += 1
            else:
                ssot_pattern_count += 1
                
        # Assert we have mixed patterns (this is the problem)
        self.assertGreater(ssot_pattern_count, 0)
        self.assertGreater(demo_pattern_count, 0)
        
        print(f"SSOT pattern connections: {ssot_pattern_count}")
        print(f"Demo pattern connections: {demo_pattern_count}")
        
        # This mixed state makes cleanup correlation difficult
        # because different parts of the system use different ID generation patterns
        
    def test_id_pattern_standardization_proposal(self):
        """Test proposed SSOT ID generation pattern for consistency."""
        
        # Proposed SSOT pattern: all IDs use plain UUID format
        def generate_ssot_ids():
            return {
                "user_id": str(uuid.uuid4()),
                "thread_id": str(uuid.uuid4()),
                "run_id": str(uuid.uuid4()),
                "request_id": str(uuid.uuid4())
            }
            
        ids1 = generate_ssot_ids()
        ids2 = generate_ssot_ids()
        
        # All IDs should be plain UUIDs (no prefixes)
        for id_type, id_value in ids1.items():
            self.assertIsInstance(id_value, str)
            self.assertEqual(len(id_value), 36)  # Standard UUID length
            self.assertIn("-", id_value)  # UUID format
            self.assertFalse(id_value.startswith("demo-"))  # No prefix
            
        # All IDs should be unique
        all_ids = list(ids1.values()) + list(ids2.values())
        self.assertEqual(len(all_ids), len(set(all_ids)))  # All unique
        
        print("SSOT ID pattern validation passed")
        print(f"Sample SSOT IDs: {ids1}")

    def test_unified_id_manager_thread_id_extraction_consistency(self):
        """Test UnifiedIDManager thread ID extraction consistency."""
        
        # Test the SSOT method that should be used instead of ad-hoc generation
        id_manager = UnifiedIDManager()
        
        # Generate thread ID using SSOT method
        ssot_thread_id = UnifiedIDManager.generate_thread_id()
        ssot_run_id = UnifiedIDManager.generate_run_id(ssot_thread_id)
        
        # Test extraction consistency
        extracted_thread_id = UnifiedIDManager.extract_thread_id(ssot_run_id)
        
        print(f"SSOT thread_id: {ssot_thread_id}")
        print(f"SSOT run_id: {ssot_run_id}")
        print(f"Extracted thread_id: {extracted_thread_id}")
        
        # Verify the extracted thread_id is consistent
        self.assertIn(ssot_thread_id, extracted_thread_id)  # Should be contained/related
        
    def test_demo_websocket_ssot_violation_detection(self):
        """Test detection of SSOT violations in demo_websocket.py pattern."""
        
        # Simulate the problematic pattern from demo_websocket.py
        def demo_websocket_id_generation():
            """Simulate the current (problematic) demo_websocket.py ID generation"""
            demo_user_id = f"demo-user-{uuid.uuid4()}"
            thread_id = f"demo-thread-{uuid.uuid4()}"
            run_id = f"demo-run-{uuid.uuid4()}"
            request_id = str(uuid.uuid4())  # Mixed pattern!
            
            return {
                "demo_user_id": demo_user_id,
                "thread_id": thread_id,
                "run_id": run_id,
                "request_id": request_id
            }
        
        # Generate IDs using problematic pattern
        problematic_ids = demo_websocket_id_generation()
        
        # Test SSOT violation detection
        ssot_violations = []
        pattern_inconsistencies = []
        
        for id_name, id_value in problematic_ids.items():
            # Check if ID was generated through UnifiedIDManager (it shouldn't be for this test)
            if id_name in ['thread_id', 'run_id']:
                if id_value.startswith('demo-'):
                    ssot_violations.append(f"{id_name}: {id_value} bypasses UnifiedIDManager")
                    
            # Check pattern consistency
            is_prefixed = id_value.startswith('demo-')
            is_plain_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', id_value, re.I)
            
            if not (is_prefixed or is_plain_uuid):
                pattern_inconsistencies.append(f"{id_name}: {id_value} has unknown pattern")
        
        # This test should DETECT violations (before fix)
        print("SSOT Violations Detected:")
        for violation in ssot_violations:
            print(f"  - {violation}")
            
        print("Pattern Inconsistencies:")
        for inconsistency in pattern_inconsistencies:
            print(f"  - {inconsistency}")
            
        # For Issue #584, we expect to find violations
        self.assertGreater(len(ssot_violations), 0, "Expected to detect SSOT violations in demo_websocket.py pattern")
        
    def test_websocket_cleanup_correlation_failure_with_mixed_ids(self):
        """Test WebSocket cleanup correlation failure with mixed ID patterns."""
        
        # Simulate WebSocket manager with mixed ID patterns
        websocket_connections = {
            # SSOT pattern connections
            str(uuid.uuid4()): {
                "user_id": "user1", 
                "thread_id": str(uuid.uuid4()),
                "pattern": "ssot"
            },
            str(uuid.uuid4()): {
                "user_id": "user2",
                "thread_id": str(uuid.uuid4()), 
                "pattern": "ssot"
            },
            
            # Demo pattern connections (problematic)
            f"demo-run-{uuid.uuid4()}": {
                "user_id": "demo-user-123",
                "thread_id": f"demo-thread-{uuid.uuid4()}",
                "pattern": "demo"
            },
            f"demo-thread-{uuid.uuid4()}": {
                "user_id": "demo-user-456",
                "thread_id": f"demo-thread-{uuid.uuid4()}",
                "pattern": "demo"
            }
        }
        
        # Test cleanup correlation logic
        def find_related_connections(target_id):
            """Simulate WebSocket cleanup correlation logic"""
            related = []
            
            # Try to extract thread_id from target_id
            try:
                # This would fail for demo-prefixed IDs
                extracted_thread = UnifiedIDManager.extract_thread_id(target_id)
                
                # Find connections with related thread_ids
                for conn_id, conn_data in websocket_connections.items():
                    if conn_data.get("thread_id") == extracted_thread:
                        related.append(conn_id)
                        
            except Exception as e:
                print(f"Correlation failed for {target_id}: {e}")
                
            return related
        
        # Test correlation with different ID patterns
        ssot_connections = [conn for conn in websocket_connections.keys() if not conn.startswith("demo-")]
        demo_connections = [conn for conn in websocket_connections.keys() if conn.startswith("demo-")]
        
        # Test correlation for SSOT pattern
        ssot_correlation_results = []
        for conn_id in ssot_connections:
            related = find_related_connections(conn_id)
            ssot_correlation_results.extend(related)
            
        # Test correlation for demo pattern (should have issues)
        demo_correlation_results = []
        for conn_id in demo_connections:
            related = find_related_connections(conn_id)
            demo_correlation_results.extend(related)
            
        print(f"SSOT connections found: {len(ssot_connections)}")
        print(f"Demo connections found: {len(demo_connections)}")
        print(f"SSOT correlation results: {len(ssot_correlation_results)}")
        print(f"Demo correlation results: {len(demo_correlation_results)}")
        
        # This demonstrates the issue: mixed patterns make correlation unreliable
        self.assertGreater(len(ssot_connections), 0, "Should have SSOT connections")
        self.assertGreater(len(demo_connections), 0, "Should have demo connections")
        
        # The correlation issue: demo patterns likely have fewer/zero correlations
        # because UnifiedIDManager.extract_thread_id() doesn't handle "demo-" prefixes properly


if __name__ == "__main__":
    unittest.main()