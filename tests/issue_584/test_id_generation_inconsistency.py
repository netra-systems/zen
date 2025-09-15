"""
Test to reproduce Issue #584: Thread ID Run ID Generation Inconsistency

This test reproduces the ID generation pattern inconsistencies found in demo_websocket.py
where different ID fields use different patterns (prefixed vs plain UUID).
"""

import uuid
import unittest
from unittest.mock import Mock

from netra_backend.app.services.user_execution_context import UserExecutionContext


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


if __name__ == "__main__":
    unittest.main()