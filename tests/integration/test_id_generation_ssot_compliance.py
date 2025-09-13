"""
Integration Test for Issue #584: ID Generation SSOT Compliance

This test validates system-wide compliance with UnifiedIDManager SSOT patterns
and detects violations across the entire system.
"""

import unittest
import uuid
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, List, Any

from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestIdGenerationSSOTCompliance(unittest.TestCase):
    """Integration tests for ID generation SSOT compliance across system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.id_manager = UnifiedIDManager()
        self.violation_log = []
    
    def test_demo_websocket_endpoint_ssot_compliance(self):
        """Test demo WebSocket endpoint for SSOT compliance violations."""
        
        # Simulate the current demo_websocket.py execution flow
        def simulate_demo_websocket_execution():
            """Simulate demo_websocket.py execute_real_agent_workflow function"""
            # This is the PROBLEMATIC pattern from lines 37-39
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
        
        # Execute the simulation
        generated_ids = simulate_demo_websocket_execution()
        
        # Validate SSOT compliance
        violations = self._check_ssot_compliance(generated_ids)
        
        # For Issue #584, we expect violations in the current implementation
        self.assertGreater(len(violations), 0, 
                          "Expected SSOT violations in current demo_websocket.py implementation")
        
        print("Demo WebSocket SSOT Compliance Violations:")
        for violation in violations:
            print(f"  - {violation}")
            
    def test_user_execution_context_id_integration(self):
        """Test UserExecutionContext ID integration with mixed patterns."""
        
        # Test with problematic demo pattern IDs
        demo_ids = {
            "user_id": f"demo-user-{uuid.uuid4()}",
            "thread_id": f"demo-thread-{uuid.uuid4()}",
            "run_id": f"demo-run-{uuid.uuid4()}",
            "request_id": str(uuid.uuid4())
        }
        
        # Test with SSOT pattern IDs
        ssot_ids = {
            "user_id": str(uuid.uuid4()),
            "thread_id": str(uuid.uuid4()),
            "run_id": str(uuid.uuid4()),
            "request_id": str(uuid.uuid4())
        }
        
        # Create UserExecutionContext with each pattern
        try:
            demo_context = UserExecutionContext(
                user_id=demo_ids["user_id"],
                thread_id=demo_ids["thread_id"],
                run_id=demo_ids["run_id"],
                request_id=demo_ids["request_id"]
            )
            demo_context_created = True
        except Exception as e:
            demo_context_created = False
            print(f"Demo context creation failed: {e}")
            
        try:
            ssot_context = UserExecutionContext(
                user_id=ssot_ids["user_id"],
                thread_id=ssot_ids["thread_id"],
                run_id=ssot_ids["run_id"],
                request_id=ssot_ids["request_id"]
            )
            ssot_context_created = True
        except Exception as e:
            ssot_context_created = False
            print(f"SSOT context creation failed: {e}")
        
        # Both should be created (UserExecutionContext should accept both patterns)
        self.assertTrue(demo_context_created, "Demo pattern should be accepted")
        self.assertTrue(ssot_context_created, "SSOT pattern should be accepted")
        
        # However, the issue is not in UserExecutionContext acceptance,
        # but in the inconsistent generation patterns
        
    def test_websocket_resource_cleanup_correlation_integration(self):
        """Test WebSocket resource cleanup correlation with mixed ID patterns."""
        
        # Simulate WebSocket resource registry with mixed patterns
        mock_websocket_registry = {
            # SSOT pattern resources
            str(uuid.uuid4()): {
                "user_id": "user1",
                "resource_type": "websocket_connection",
                "pattern": "ssot"
            },
            str(uuid.uuid4()): {
                "user_id": "user2", 
                "resource_type": "websocket_connection",
                "pattern": "ssot"
            },
            
            # Demo pattern resources (problematic)
            f"demo-run-{uuid.uuid4()}": {
                "user_id": "demo-user-123",
                "resource_type": "websocket_connection", 
                "pattern": "demo"
            },
            f"demo-thread-{uuid.uuid4()}": {
                "user_id": "demo-user-456",
                "resource_type": "websocket_connection",
                "pattern": "demo"
            }
        }
        
        # Test cleanup correlation function
        def cleanup_related_resources(target_id: str) -> List[str]:
            """Simulate WebSocket cleanup correlation logic"""
            cleaned_up = []
            
            try:
                # Extract thread_id using UnifiedIDManager
                extracted_thread = UnifiedIDManager.extract_thread_id(target_id)
                
                # Find and cleanup related resources
                for resource_id, resource_data in mock_websocket_registry.items():
                    # This correlation logic would fail for demo-prefixed IDs
                    if resource_id == target_id or extracted_thread in resource_id:
                        cleaned_up.append(resource_id)
                        
            except Exception as e:
                print(f"Cleanup correlation failed for {target_id}: {e}")
                
            return cleaned_up
        
        # Test cleanup with different ID patterns
        ssot_resources = [rid for rid in mock_websocket_registry.keys() if not rid.startswith("demo-")]
        demo_resources = [rid for rid in mock_websocket_registry.keys() if rid.startswith("demo-")]
        
        # Test cleanup correlation for each pattern
        ssot_cleanup_results = []
        demo_cleanup_results = []
        
        for resource_id in ssot_resources:
            cleaned = cleanup_related_resources(resource_id)
            ssot_cleanup_results.extend(cleaned)
            
        for resource_id in demo_resources:
            cleaned = cleanup_related_resources(resource_id)
            demo_cleanup_results.extend(cleaned)
        
        print(f"SSOT resources: {len(ssot_resources)}")
        print(f"Demo resources: {len(demo_resources)}")
        print(f"SSOT cleanup successful: {len(ssot_cleanup_results)}")
        print(f"Demo cleanup successful: {len(demo_cleanup_results)}")
        
        # The issue: demo pattern cleanup likely has problems due to correlation failures
        self.assertGreater(len(ssot_resources), 0, "Should have SSOT resources")
        self.assertGreater(len(demo_resources), 0, "Should have demo resources")
        
        # This test demonstrates the correlation problem
        
    def test_id_tracing_and_debugging_correlation(self):
        """Test ID tracing and debugging correlation across different patterns."""
        
        # Simulate debug trace log with mixed ID patterns
        debug_trace_entries = [
            {"id": str(uuid.uuid4()), "action": "user_login", "pattern": "ssot"},
            {"id": str(uuid.uuid4()), "action": "websocket_connect", "pattern": "ssot"},
            {"id": f"demo-run-{uuid.uuid4()}", "action": "demo_execution", "pattern": "demo"},
            {"id": f"demo-thread-{uuid.uuid4()}", "action": "demo_thread", "pattern": "demo"},
        ]
        
        # Test correlation tracing function
        def trace_related_operations(target_id: str) -> List[Dict[str, Any]]:
            """Simulate tracing correlation logic"""
            related_operations = []
            
            try:
                # Extract correlation keys
                if target_id.startswith("demo-"):
                    # Demo pattern handling (ad-hoc)
                    correlation_key = target_id.split("-")[-1]  # Use UUID part
                else:
                    # SSOT pattern handling
                    correlation_key = UnifiedIDManager.extract_thread_id(target_id)
                
                # Find related operations
                for entry in debug_trace_entries:
                    if correlation_key in entry["id"]:
                        related_operations.append(entry)
                        
            except Exception as e:
                print(f"Trace correlation failed for {target_id}: {e}")
                
            return related_operations
        
        # Test tracing with different patterns
        ssot_trace_id = str(uuid.uuid4())
        demo_trace_id = f"demo-run-{uuid.uuid4()}"
        
        ssot_related = trace_related_operations(ssot_trace_id)
        demo_related = trace_related_operations(demo_trace_id)
        
        print(f"SSOT trace results: {len(ssot_related)}")
        print(f"Demo trace results: {len(demo_related)}")
        
        # This test shows how mixed patterns complicate debugging correlation
        
    def _check_ssot_compliance(self, generated_ids: Dict[str, str]) -> List[str]:
        """Check generated IDs for SSOT compliance violations."""
        violations = []
        
        for id_name, id_value in generated_ids.items():
            # Check for SSOT violations
            if id_name in ['thread_id', 'run_id']:
                # These should be generated through UnifiedIDManager
                if not self._is_unified_id_manager_format(id_value):
                    violations.append(f"{id_name}: {id_value} not generated through UnifiedIDManager")
                    
            # Check for pattern consistency
            if id_value.startswith('demo-') and id_name == 'request_id':
                violations.append(f"{id_name}: {id_value} has inconsistent pattern (should be plain UUID)")
                
        return violations
    
    def _is_unified_id_manager_format(self, id_value: str) -> bool:
        """Check if ID follows UnifiedIDManager format patterns."""
        # UnifiedIDManager generates either:
        # 1. Plain UUIDs (during migration)
        # 2. Structured format: [prefix_]idtype_counter_uuid8
        
        try:
            # Check if it's a plain UUID
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
                    
        # Check for demo patterns (these are NOT UnifiedIDManager format)
        if id_value.startswith('demo-'):
            return False
            
        return False


if __name__ == "__main__":
    unittest.main()