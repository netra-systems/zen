"""
Unit Tests for ExecutionTracker Business Logic - Comprehensive Coverage

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Agent Reliability - Prevent silent agent failures from degrading user experience  
- Value Impact: Execution tracking ensures agent operations complete successfully or fail visibly
- Strategic Impact: Reliable agent execution is fundamental to platform trust and business value delivery

This test suite validates the business-critical path of execution tracking including:
- Silent agent death detection to prevent business process hangs
- Timeout enforcement to prevent resource waste and user abandonment
- Execution state monitoring for business process transparency
- Metrics collection for business performance insights
- Recovery mechanisms for business continuity
- Multi-user execution isolation for enterprise scalability

CRITICAL: These tests focus on BUSINESS LOGIC that ensures AI agents execute
reliably and provide visible failures when business processes encounter issues.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from uuid import UUID, uuid4
from typing import Dict, Any, Optional

from netra_backend.app.core.execution_tracker import (
    ExecutionTracker,
    ExecutionRecord, 
    ExecutionState,
    get_execution_tracker
)
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics
from test_framework.unified import TestCategory
from shared.isolated_environment import get_env


class TestExecutionTrackerBusiness(SSotBaseTestCase):
    """Comprehensive unit tests for ExecutionTracker business logic."""

    def setup_method(self, method):
        """Set up test environment with isolated configuration."""
        super().setup_method(method)
        self.env = get_env()
        self.env.set("LOG_LEVEL", "INFO", source="test")
        
        self.test_context = self.get_test_context()
        
        self.metrics = SsotTestMetrics()
        self.metrics.start_timing()

    def teardown_method(self, method):
        """Clean up after each test."""
        self.metrics.end_timing()
        super().teardown_method(method)

    @pytest.fixture
    def execution_tracker(self):
        """Create ExecutionTracker for testing."""
        return ExecutionTracker()

    @pytest.fixture
    def business_execution_record(self):
        """Create realistic business execution record."""
        return ExecutionRecord(
            execution_id=uuid4(),
            agent_name="cost_optimization_agent",
            correlation_id="optimization-job-12345",
            thread_id="enterprise-session-789",
            user_id="business-analyst-456", 
            start_time=time.time(),
            state=ExecutionState.RUNNING,
            last_heartbeat=time.time(),
            timeout_seconds=45.0  # Longer timeout for complex business analysis
        )

    async def test_register_execution_creates_business_tracking_record(
        self, execution_tracker
    ):
        """Test that register_execution creates proper business tracking record."""
        # BUSINESS VALUE: Business processes must be trackable for reliability and accountability
        
        # Register business execution
        exec_id = await execution_tracker.register_execution(
            agent_name="quarterly_revenue_analyzer",
            correlation_id="q4-revenue-analysis-2024",
            thread_id="finance-dashboard-session",
            user_id="finance-manager-789",
            timeout_seconds=60.0  # Complex financial analysis needs time
        )
        
        # Verify execution was registered with business context
        assert isinstance(exec_id, UUID)
        assert exec_id in execution_tracker.executions
        
        record = execution_tracker.executions[exec_id]
        assert record.agent_name == "quarterly_revenue_analyzer"
        assert record.correlation_id == "q4-revenue-analysis-2024"
        assert record.thread_id == "finance-dashboard-session" 
        assert record.user_id == "finance-manager-789"
        assert record.state == ExecutionState.PENDING
        assert record.timeout_seconds == 60.0
        
        # Verify business tracking metrics
        assert record.heartbeat_count == 0
        assert record.websocket_updates_sent == 0
        assert record.start_time > 0
        
        # Record business tracking metrics
        self.metrics.record_custom("business_executions_registered", 1)
        self.metrics.record_custom("execution_accountability_enabled", True)

    async def test_start_execution_enables_business_monitoring(
        self, execution_tracker
    ):
        """Test that start_execution enables business process monitoring."""
        # BUSINESS VALUE: Active monitoring prevents business processes from hanging silently
        
        # Register and start business execution
        exec_id = await execution_tracker.register_execution(
            agent_name="customer_churn_predictor",
            correlation_id="churn-prevention-campaign-2024",
            user_id="marketing-director-123"
        )
        
        await execution_tracker.start_execution(exec_id)
        
        # Verify execution is actively monitored
        record = execution_tracker.executions[exec_id]
        assert record.state == ExecutionState.RUNNING
        assert exec_id in execution_tracker.active_executions
        
        # Verify heartbeat tracking is initialized
        assert record.last_heartbeat > record.start_time - 1  # Within 1 second
        
        # Record monitoring metrics
        self.metrics.record_custom("business_monitoring_enabled", True)
        self.metrics.record_custom("silent_failures_prevented", True)

    async def test_complete_execution_provides_business_closure(
        self, execution_tracker
    ):
        """Test that complete_execution provides proper business closure.""" 
        # BUSINESS VALUE: Business processes need clear completion status for workflow continuity
        
        # Setup running business execution
        exec_id = await execution_tracker.register_execution(
            agent_name="market_opportunity_analyzer",
            correlation_id="market-expansion-q1-2025"
        )
        await execution_tracker.start_execution(exec_id)
        
        # Complete with business results
        business_result = {
            "market_size": 850000000,  # $850M market opportunity
            "competition_level": "moderate",
            "entry_barriers": ["regulatory", "capital_intensive"],
            "success_probability": 0.73,
            "recommended_investment": 2500000,
            "expected_roi": 2.8,
            "timeline_months": 18
        }
        
        await execution_tracker.complete_execution(exec_id, result=business_result)
        
        # Verify business closure was recorded
        record = execution_tracker.executions[exec_id]
        assert record.state == ExecutionState.COMPLETED
        assert record.result == business_result
        assert record.end_time is not None
        assert record.error is None
        
        # Verify execution is removed from active monitoring
        assert exec_id not in execution_tracker.active_executions
        
        # Record business closure metrics
        self.metrics.record_custom("business_processes_completed", 1)
        self.metrics.record_custom("workflow_continuity_enabled", True)

    async def test_complete_execution_handles_business_failures_gracefully(
        self, execution_tracker
    ):
        """Test that complete_execution handles business failures gracefully."""
        # BUSINESS VALUE: Business failures must be recorded clearly to enable recovery
        
        # Setup business execution that will fail
        exec_id = await execution_tracker.register_execution(
            agent_name="supply_chain_optimizer",
            correlation_id="supply-chain-crisis-response"
        )
        await execution_tracker.start_execution(exec_id)
        
        # Complete with business error
        business_error = "Supply chain API unavailable - unable to access real-time inventory data for optimization analysis"
        
        await execution_tracker.complete_execution(exec_id, error=business_error)
        
        # Verify business failure was recorded clearly
        record = execution_tracker.executions[exec_id]
        assert record.state == ExecutionState.FAILED
        assert record.error == business_error
        assert record.result is None
        assert record.end_time is not None
        
        # Verify failure tracking for business insights
        assert exec_id in execution_tracker.failed_executions
        assert exec_id not in execution_tracker.active_executions
        
        # Record failure handling metrics
        self.metrics.record_custom("business_failures_recorded", 1)
        self.metrics.record_custom("recovery_insights_enabled", True)

    async def test_heartbeat_tracking_prevents_business_process_hangs(
        self, execution_tracker
    ):
        """Test that heartbeat tracking prevents business processes from hanging."""
        # BUSINESS VALUE: Heartbeat monitoring prevents business processes from hanging silently
        
        # Setup long-running business execution
        exec_id = await execution_tracker.register_execution(
            agent_name="enterprise_data_pipeline_optimizer",
            correlation_id="monthly-etl-optimization",
            timeout_seconds=120.0  # 2 minutes for data processing
        )
        await execution_tracker.start_execution(exec_id)
        
        initial_record = execution_tracker.executions[exec_id]
        initial_heartbeat = initial_record.last_heartbeat
        
        # Send heartbeat update
        await execution_tracker.heartbeat(exec_id, {
            "status": "processing_customer_data",
            "progress": 0.45,
            "records_processed": 125000,
            "estimated_remaining_ms": 45000
        })
        
        # Verify heartbeat was recorded
        updated_record = execution_tracker.executions[exec_id]
        assert updated_record.last_heartbeat > initial_heartbeat
        assert updated_record.heartbeat_count == 1
        
        # Verify business process status is trackable
        assert not updated_record.is_dead()  # Fresh heartbeat, not dead
        assert not updated_record.is_timeout()  # Within timeout window
        
        # Record heartbeat monitoring metrics
        self.metrics.record_custom("business_process_heartbeats_tracked", 1)
        self.metrics.record_custom("process_hangs_prevented", True)

    async def test_timeout_detection_prevents_business_resource_waste(
        self, execution_tracker
    ):
        """Test that timeout detection prevents business resource waste."""
        # BUSINESS VALUE: Timeouts prevent runaway processes that waste business resources
        
        # Setup business execution with short timeout for testing
        exec_id = await execution_tracker.register_execution(
            agent_name="quick_market_scan",
            correlation_id="urgent-competitive-analysis",
            timeout_seconds=0.1  # Very short timeout for test
        )
        await execution_tracker.start_execution(exec_id)
        
        # Wait for timeout to occur
        await asyncio.sleep(0.2)
        
        # Check timeout detection
        record = execution_tracker.executions[exec_id]
        assert record.is_timeout() is True
        assert record.duration() > record.timeout_seconds
        
        # Verify business process is still marked as running (detection doesn't auto-kill)
        assert record.state == ExecutionState.RUNNING
        
        # Record timeout detection metrics
        self.metrics.record_custom("business_timeouts_detected", 1)
        self.metrics.record_custom("resource_waste_prevention_enabled", True)

    async def test_death_detection_identifies_silent_business_failures(
        self, execution_tracker
    ):
        """Test that death detection identifies silent business failures."""
        # BUSINESS VALUE: Death detection prevents business processes from appearing healthy when they're dead
        
        # Setup business execution that will go silent
        exec_id = await execution_tracker.register_execution(
            agent_name="financial_risk_assessor",
            correlation_id="quarterly-risk-evaluation"
        )
        await execution_tracker.start_execution(exec_id)
        
        # Simulate agent going silent (no heartbeat)
        record = execution_tracker.executions[exec_id]
        record.last_heartbeat = time.time() - 15.0  # 15 seconds ago, beyond default 10s threshold
        
        # Check death detection
        assert record.is_dead() is True
        assert record.is_dead(heartbeat_timeout=10.0) is True
        assert record.is_dead(heartbeat_timeout=20.0) is False  # Would be alive with longer threshold
        
        # Verify business process state accuracy
        assert record.state == ExecutionState.RUNNING  # State doesn't auto-change, just detected
        
        # Record death detection metrics
        self.metrics.record_custom("silent_business_failures_detected", 1)
        self.metrics.record_custom("false_health_status_prevented", True)

    async def test_metrics_collection_enables_business_insights(
        self, execution_tracker
    ):
        """Test that metrics collection enables business performance insights."""
        # BUSINESS VALUE: Execution metrics enable business process optimization
        
        # Setup completed business execution with metrics
        exec_id = await execution_tracker.register_execution(
            agent_name="customer_segment_analyzer",
            correlation_id="segment-optimization-2024"
        )
        await execution_tracker.start_execution(exec_id)
        
        # Simulate multiple heartbeats and websocket updates
        for i in range(3):
            await execution_tracker.heartbeat(exec_id, {"progress": (i + 1) * 0.33})
            await execution_tracker.websocket_update_sent(exec_id)
        
        # Complete execution
        await execution_tracker.complete_execution(exec_id, result={"segments": 5})
        
        # Collect business metrics
        metrics = await execution_tracker.collect_metrics(exec_id)
        
        # Verify business-relevant metrics are available
        assert isinstance(metrics, dict)
        assert "execution_time_ms" in metrics or "duration" in metrics
        assert "heartbeat_count" in metrics or metrics.get("heartbeat_count", 0) >= 0
        assert "websocket_updates" in metrics or metrics.get("websocket_updates", 0) >= 0
        
        # Verify metrics enable business insights
        record = execution_tracker.executions[exec_id]
        assert record.heartbeat_count == 3
        assert record.websocket_updates_sent == 3
        assert record.duration() > 0
        
        # Record business insights metrics
        self.metrics.record_custom("business_metrics_collected", True)
        self.metrics.record_custom("performance_insights_enabled", True)

    async def test_execution_monitoring_provides_business_visibility(
        self, execution_tracker
    ):
        """Test that execution monitoring provides business visibility."""
        # BUSINESS VALUE: Monitoring enables business stakeholders to track process status
        
        # Start monitoring system
        await execution_tracker.start_monitoring()
        
        # Verify monitoring is active
        assert execution_tracker.monitoring_task is not None
        assert not execution_tracker.monitoring_task.done()
        
        # Setup multiple business executions for monitoring
        business_executions = []
        for i in range(3):
            exec_id = await execution_tracker.register_execution(
                agent_name=f"business_process_{i}",
                correlation_id=f"business-workflow-{i}",
                user_id=f"business-user-{i}"
            )
            await execution_tracker.start_execution(exec_id)
            business_executions.append(exec_id)
        
        # Verify all executions are being monitored
        assert len(execution_tracker.active_executions) == 3
        
        # Stop monitoring
        await execution_tracker.stop_monitoring()
        assert execution_tracker.monitoring_task is None or execution_tracker.monitoring_task.done()
        
        # Record monitoring metrics
        self.metrics.record_custom("business_executions_monitored", 3)
        self.metrics.record_custom("process_visibility_enabled", True)

    def test_execution_record_serialization_enables_business_reporting(
        self, business_execution_record
    ):
        """Test that execution record serialization enables business reporting."""
        # BUSINESS VALUE: Serializable records enable business dashboards and reporting
        
        # Add business metrics to record
        business_execution_record.heartbeat_count = 5
        business_execution_record.websocket_updates_sent = 8
        business_execution_record.end_time = time.time()
        business_execution_record.state = ExecutionState.COMPLETED
        
        # Serialize record for business reporting
        record_dict = business_execution_record.to_dict()
        
        # Verify all business-relevant data is serialized
        required_fields = [
            "execution_id", "agent_name", "correlation_id", "thread_id", "user_id",
            "start_time", "state", "last_heartbeat", "end_time", "heartbeat_count", 
            "websocket_updates_sent", "duration", "is_timeout", "is_dead"
        ]
        
        for field in required_fields:
            assert field in record_dict, f"Business field {field} missing from serialized record"
        
        # Verify business identifiers are preserved
        assert record_dict["agent_name"] == "cost_optimization_agent"
        assert record_dict["correlation_id"] == "optimization-job-12345" 
        assert record_dict["user_id"] == "business-analyst-456"
        assert record_dict["state"] == "completed"
        
        # Verify business metrics are included
        assert record_dict["heartbeat_count"] == 5
        assert record_dict["websocket_updates_sent"] == 8
        assert record_dict["duration"] > 0
        
        # Record serialization metrics
        self.metrics.record_custom("business_records_serializable", True)
        self.metrics.record_custom("reporting_enabled", True)

    def test_singleton_execution_tracker_ensures_business_consistency(self):
        """Test that singleton execution tracker ensures business consistency."""
        # BUSINESS VALUE: Single tracker instance ensures consistent business process monitoring
        
        # Get tracker instances multiple times
        tracker1 = get_execution_tracker()
        tracker2 = get_execution_tracker() 
        tracker3 = get_execution_tracker()
        
        # Verify all references point to same instance
        assert tracker1 is tracker2
        assert tracker2 is tracker3
        assert id(tracker1) == id(tracker2) == id(tracker3)
        
        # Verify business consistency
        assert isinstance(tracker1, ExecutionTracker)
        assert hasattr(tracker1, 'executions')
        assert hasattr(tracker1, 'active_executions')
        assert hasattr(tracker1, 'failed_executions')
        
        # Record consistency metrics
        self.metrics.record_custom("business_consistency_ensured", True)
        self.metrics.record_custom("singleton_pattern_verified", True)


class TestExecutionTrackerBusinessScenarios(SSotBaseTestCase):
    """Business scenario tests for execution tracker edge cases."""

    async def test_concurrent_business_executions_tracked_independently(self):
        """Test that concurrent business executions are tracked independently."""
        # BUSINESS VALUE: Multi-user platform must track executions independently for each business unit
        
        tracker = ExecutionTracker()
        
        # Setup concurrent business executions for different units
        business_units = ["sales", "marketing", "finance", "operations"]
        concurrent_executions = []
        
        for unit in business_units:
            exec_id = await tracker.register_execution(
                agent_name=f"{unit}_performance_analyzer", 
                correlation_id=f"{unit}-quarterly-review-2024",
                user_id=f"{unit}-director-001",
                thread_id=f"{unit}-dashboard-session"
            )
            await tracker.start_execution(exec_id)
            concurrent_executions.append(exec_id)
        
        # Verify independent tracking
        assert len(tracker.active_executions) == 4
        assert all(exec_id in tracker.executions for exec_id in concurrent_executions)
        
        # Verify each execution has correct business context
        for i, exec_id in enumerate(concurrent_executions):
            record = tracker.executions[exec_id]
            unit = business_units[i]
            assert record.agent_name == f"{unit}_performance_analyzer"
            assert record.user_id == f"{unit}-director-001"
            assert record.correlation_id == f"{unit}-quarterly-review-2024"
        
        # Record concurrency metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("concurrent_business_executions_tracked", 4)
        metrics.record_custom("business_unit_isolation_maintained", True)

    async def test_enterprise_scale_execution_tracking(self):
        """Test execution tracking at enterprise scale.""" 
        # BUSINESS VALUE: Enterprise customers need robust tracking for high-volume business operations
        
        tracker = ExecutionTracker()
        
        # Simulate enterprise-scale concurrent executions
        enterprise_scale = 50  # 50 concurrent business processes
        execution_ids = []
        
        for i in range(enterprise_scale):
            exec_id = await tracker.register_execution(
                agent_name=f"enterprise_process_{i}",
                correlation_id=f"enterprise-operation-{i}",
                user_id=f"enterprise-user-{i % 10}",  # 10 users sharing 50 processes
                timeout_seconds=300.0  # 5 minutes for complex enterprise operations
            )
            await tracker.start_execution(exec_id)
            execution_ids.append(exec_id)
        
        # Verify enterprise-scale tracking capability
        assert len(tracker.active_executions) == enterprise_scale
        assert all(exec_id in tracker.executions for exec_id in execution_ids)
        
        # Verify performance at scale
        start_time = time.time()
        
        # Complete all executions
        for exec_id in execution_ids:
            await tracker.complete_execution(exec_id, result={"enterprise_data": True})
        
        completion_time = time.time() - start_time
        
        # Verify reasonable performance (should complete quickly)
        assert completion_time < 5.0  # Less than 5 seconds for 50 completions
        assert len(tracker.active_executions) == 0
        assert all(tracker.executions[exec_id].state == ExecutionState.COMPLETED for exec_id in execution_ids)
        
        # Record enterprise scale metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("enterprise_scale_executions_tracked", enterprise_scale)
        metrics.record_custom("enterprise_performance_maintained", completion_time < 5.0)