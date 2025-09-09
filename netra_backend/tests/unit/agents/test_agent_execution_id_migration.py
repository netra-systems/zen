"""
Agent Execution ID Migration Test Suite
=======================================

FOCUSED test suite for migrating the single uuid.uuid4() call in agent_execution_tracker.py
to UnifiedIDManager. This is a targeted migration for business compliance audit trails.

CRITICAL: This test will FAIL initially (exposing uuid.uuid4() dependency), 
then PASS after UnifiedIDManager migration is complete.

Business Value: Agent execution tracking is core to audit trails and compliance requirements.
"""

import pytest
import time
import uuid
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Import the target module
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionTracker, 
    ExecutionRecord, 
    ExecutionState,
    get_execution_tracker
)
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class TestAgentExecutionIDMigration:
    """
    Test suite focused on migrating agent execution ID generation 
    from uuid.uuid4() to UnifiedIDManager.
    """
    
    def setup_method(self):
        """Setup for each test method"""
        self.tracker = AgentExecutionTracker()
        self.unified_id_manager = UnifiedIDManager()
        
        # Test data
        self.test_agent_name = "TestDataAgent"
        self.test_thread_id = "thread_12345"
        self.test_user_id = "user_67890"
        
    def teardown_method(self):
        """Cleanup after each test method"""
        # Reset global tracker instance
        import netra_backend.app.core.agent_execution_tracker as tracker_module
        tracker_module._tracker_instance = None

    @pytest.mark.unit
    def test_current_uuid4_dependency_detection(self):
        """
        CRITICAL: Test that exposes the current uuid.uuid4() dependency.
        This test will FAIL after migration to prove the dependency is removed.
        """
        # Patch uuid.uuid4 to detect when it's called
        with patch('uuid.uuid4') as mock_uuid4:
            mock_uuid4.return_value = MagicMock(hex="abcdef123456789")
            
            execution_id = self.tracker.create_execution(
                agent_name=self.test_agent_name,
                thread_id=self.test_thread_id,
                user_id=self.test_user_id
            )
            
            # ASSERTION: This will fail after migration (which is good!)
            mock_uuid4.assert_called_once()
            
            # Validate current format: exec_{uuid_hex[:12]}_{timestamp}
            assert execution_id.startswith("exec_")
            parts = execution_id.split("_")
            assert len(parts) >= 3
            assert parts[0] == "exec"
            # parts[1] should be uuid hex (12 chars)
            assert len(parts[1]) == 12
            # parts[2] should be timestamp
            assert parts[2].isdigit()

    @pytest.mark.unit 
    def test_execution_id_format_validation(self):
        """
        Test current execution ID format before migration.
        Validates business requirements for audit trail metadata.
        """
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Current format: exec_{uuid_hex[:12]}_{timestamp}
        assert execution_id.startswith("exec_")
        
        # Split and validate components
        parts = execution_id.split("_")
        assert len(parts) >= 3
        
        exec_prefix = parts[0]
        uuid_component = parts[1]
        timestamp_component = parts[2]
        
        assert exec_prefix == "exec"
        assert len(uuid_component) == 12
        assert all(c in '0123456789abcdef' for c in uuid_component)
        assert timestamp_component.isdigit()
        
        # Timestamp should be recent (within last 10 seconds)
        timestamp = int(timestamp_component)
        current_time = int(time.time())
        assert abs(current_time - timestamp) < 10

    @pytest.mark.unit
    def test_execution_id_uniqueness_collision_prevention(self):
        """
        Test execution ID uniqueness - critical for audit trails.
        Business requirement: Each agent execution must have unique ID.
        """
        # Generate multiple execution IDs rapidly
        execution_ids = []
        for i in range(100):
            execution_id = self.tracker.create_execution(
                agent_name=f"{self.test_agent_name}_{i}",
                thread_id=f"{self.test_thread_id}_{i}",
                user_id=self.test_user_id
            )
            execution_ids.append(execution_id)
        
        # Verify all IDs are unique
        assert len(execution_ids) == len(set(execution_ids))
        
        # Verify format consistency
        for exec_id in execution_ids:
            assert exec_id.startswith("exec_")
            parts = exec_id.split("_")
            assert len(parts) >= 3

    @pytest.mark.unit
    def test_execution_record_audit_trail_metadata(self):
        """
        Test that execution records contain proper audit trail metadata.
        Business Value: Compliance and debugging require complete execution history.
        """
        metadata = {
            "compliance_context": "SOC2_audit",
            "business_unit": "ai_optimization",
            "risk_level": "medium"
        }
        
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            timeout_seconds=30,
            metadata=metadata
        )
        
        # Retrieve and validate execution record
        record = self.tracker.get_execution(execution_id)
        assert record is not None
        assert record.execution_id == execution_id
        assert record.agent_name == self.test_agent_name
        assert record.thread_id == self.test_thread_id
        assert record.user_id == self.test_user_id
        assert record.state == ExecutionState.PENDING
        
        # Validate audit trail metadata
        assert record.metadata == metadata
        assert record.started_at is not None
        assert record.last_heartbeat is not None
        assert record.timeout_seconds == 30

    @pytest.mark.unit
    def test_execution_id_performance_benchmark(self):
        """
        Performance test for execution ID generation.
        Business requirement: ID generation should not be a bottleneck.
        """
        import time
        
        # Benchmark current uuid.uuid4() approach
        start_time = time.perf_counter()
        
        for i in range(1000):
            execution_id = self.tracker.create_execution(
                agent_name=f"PerfTest_{i}",
                thread_id=f"thread_{i}",
                user_id="perf_user"
            )
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should generate 1000 IDs in under 1 second
        assert total_time < 1.0
        
        # Average generation time per ID
        avg_time_per_id = total_time / 1000
        assert avg_time_per_id < 0.001  # Less than 1ms per ID

    @pytest.mark.unit
    def test_unified_id_manager_integration_preparation(self):
        """
        Test to prepare for UnifiedIDManager integration.
        This test shows how the migration should work.
        """
        # Create a UnifiedIDManager instance
        id_manager = UnifiedIDManager()
        
        # Test generating execution IDs using UnifiedIDManager
        execution_id_1 = id_manager.generate_id(
            id_type=IDType.EXECUTION,
            prefix="exec",
            context={
                "agent_name": self.test_agent_name,
                "thread_id": self.test_thread_id,
                "user_id": self.test_user_id
            }
        )
        
        execution_id_2 = id_manager.generate_id(
            id_type=IDType.EXECUTION,
            prefix="exec",
            context={
                "agent_name": "AnotherAgent",
                "thread_id": "thread_999",
                "user_id": "user_888"
            }
        )
        
        # Validate UnifiedIDManager format
        assert execution_id_1.startswith("exec_")
        assert execution_id_2.startswith("exec_")
        assert execution_id_1 != execution_id_2
        
        # UnifiedIDManager IDs should contain execution type
        assert "execution" in execution_id_1
        assert "execution" in execution_id_2

    @pytest.mark.unit
    async def test_execution_lifecycle_with_id_tracking(self):
        """
        Test complete execution lifecycle while tracking ID usage.
        Business Value: Ensures agent execution tracking works end-to-end.
        """
        # Create execution
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            timeout_seconds=10
        )
        
        # Validate initial state
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.PENDING
        assert record.execution_id == execution_id
        
        # Start execution
        success = self.tracker.start_execution(execution_id)
        assert success is True
        
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.STARTING
        
        # Send heartbeat (should transition to RUNNING)
        success = self.tracker.heartbeat(execution_id)
        assert success is True
        
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.RUNNING
        assert record.heartbeat_count == 1
        
        # Complete execution
        success = self.tracker.update_execution_state(
            execution_id,
            ExecutionState.COMPLETED,
            result={"status": "success", "data": "test_result"}
        )
        assert success is True
        
        record = self.tracker.get_execution(execution_id)
        assert record.state == ExecutionState.COMPLETED
        assert record.result == {"status": "success", "data": "test_result"}
        assert record.completed_at is not None

    @pytest.mark.unit
    def test_global_tracker_singleton_id_consistency(self):
        """
        Test that the global tracker singleton maintains ID consistency.
        Business requirement: Single source of truth for execution tracking.
        """
        # Get global tracker instances
        tracker1 = get_execution_tracker()
        tracker2 = get_execution_tracker()
        
        # Should be the same instance (singleton)
        assert tracker1 is tracker2
        
        # Create execution through first instance
        execution_id_1 = tracker1.create_execution(
            agent_name="Agent1",
            thread_id="thread_1",
            user_id="user_1"
        )
        
        # Should be accessible through second instance
        record = tracker2.get_execution(execution_id_1)
        assert record is not None
        assert record.execution_id == execution_id_1

    @pytest.mark.unit
    def test_execution_id_migration_compatibility(self):
        """
        Test that migration to UnifiedIDManager maintains backward compatibility.
        Critical: Existing systems expecting current format should still work.
        """
        # Current format validation
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id
        )
        
        # Test systems that might parse the current format
        def parse_execution_id(exec_id: str) -> dict:
            """Simulate system that parses current execution ID format"""
            if not exec_id.startswith("exec_"):
                raise ValueError("Invalid execution ID format")
            
            parts = exec_id.split("_")
            if len(parts) < 3:
                raise ValueError("Insufficient ID components")
            
            return {
                "prefix": parts[0],
                "uuid_component": parts[1],
                "timestamp": int(parts[2]) if parts[2].isdigit() else None
            }
        
        # Should be parseable by existing systems
        parsed = parse_execution_id(execution_id)
        assert parsed["prefix"] == "exec"
        assert len(parsed["uuid_component"]) == 12
        assert parsed["timestamp"] is not None
        assert isinstance(parsed["timestamp"], int)

    @pytest.mark.unit
    def test_execution_id_context_preservation(self):
        """
        Test that execution context is preserved in generated IDs.
        Business Value: Context enables better debugging and audit trails.
        """
        complex_metadata = {
            "business_context": {
                "customer_tier": "enterprise",
                "compliance_level": "SOC2",
                "data_classification": "confidential"
            },
            "technical_context": {
                "execution_environment": "production",
                "resource_pool": "high_priority",
                "retry_count": 0
            }
        }
        
        execution_id = self.tracker.create_execution(
            agent_name=self.test_agent_name,
            thread_id=self.test_thread_id,
            user_id=self.test_user_id,
            metadata=complex_metadata
        )
        
        # Retrieve and validate context preservation
        record = self.tracker.get_execution(execution_id)
        assert record.metadata == complex_metadata
        
        # Business context should be accessible
        business_ctx = record.metadata.get("business_context", {})
        assert business_ctx.get("customer_tier") == "enterprise"
        assert business_ctx.get("compliance_level") == "SOC2"
        
        # Technical context should be accessible  
        technical_ctx = record.metadata.get("technical_context", {})
        assert technical_ctx.get("execution_environment") == "production"
        assert technical_ctx.get("resource_pool") == "high_priority"


class TestAgentExecutionIDMigrationIntegration:
    """
    Integration tests for UnifiedIDManager migration.
    These tests validate the complete migration path.
    """
    
    @pytest.mark.integration
    def test_unified_id_manager_execution_id_generation(self):
        """
        Integration test for UnifiedIDManager execution ID generation.
        This test shows the target state after migration.
        """
        id_manager = UnifiedIDManager()
        
        # Generate execution ID using UnifiedIDManager
        execution_id = id_manager.generate_id(
            id_type=IDType.EXECUTION,
            prefix="exec",
            context={
                "agent_name": "TestAgent",
                "thread_id": "thread_123",
                "user_id": "user_456",
                "business_unit": "ai_optimization"
            }
        )
        
        # Validate format meets business requirements
        assert execution_id.startswith("exec_")
        assert "execution" in execution_id
        
        # Should be unique
        execution_id_2 = id_manager.generate_id(
            id_type=IDType.EXECUTION,
            prefix="exec",
            context={
                "agent_name": "AnotherAgent",
                "thread_id": "thread_789",
                "user_id": "user_999"
            }
        )
        
        assert execution_id != execution_id_2

    @pytest.mark.integration
    def test_migration_performance_comparison(self):
        """
        Performance comparison between uuid.uuid4() and UnifiedIDManager.
        Business requirement: Migration should not degrade performance.
        """
        import time
        
        # Test current uuid.uuid4() approach
        start_time = time.perf_counter()
        uuid_ids = []
        for i in range(100):
            uuid_id = f"exec_{uuid.uuid4().hex[:12]}_{int(time.time())}"
            uuid_ids.append(uuid_id)
        uuid_time = time.perf_counter() - start_time
        
        # Test UnifiedIDManager approach
        id_manager = UnifiedIDManager()
        start_time = time.perf_counter()
        unified_ids = []
        for i in range(100):
            unified_id = id_manager.generate_id(
                id_type=IDType.EXECUTION,
                prefix="exec"
            )
            unified_ids.append(unified_id)
        unified_time = time.perf_counter() - start_time
        
        # Performance should be acceptable (within 5x for added functionality)
        # UnifiedIDManager provides additional metadata tracking which adds overhead
        assert unified_time < (uuid_time * 5)
        
        # All IDs should be unique
        assert len(uuid_ids) == len(set(uuid_ids))
        assert len(unified_ids) == len(set(unified_ids))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])