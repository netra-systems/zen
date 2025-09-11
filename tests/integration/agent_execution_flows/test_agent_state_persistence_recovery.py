"""
Test Agent State Persistence and Recovery Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent state survives system restarts and network interruptions
- Value Impact: Prevents loss of work progress and maintains user experience continuity
- Strategic Impact: Enables reliable long-running AI workflows that build customer trust

Tests the agent state persistence and recovery system including state snapshots,
recovery after failures, cross-session continuity, and data integrity.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import time
import json

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.agent_state_tracker import AgentStateTracker
from netra_backend.app.services.state_persistence import StatePersistenceService


class TestAgentStatePersistenceRecovery(BaseIntegrationTest):
    """Integration tests for agent state persistence and recovery."""

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_comprehensive_state_persistence_workflow(self, real_services_fixture):
        """Test comprehensive state persistence across complex agent workflows."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="persistent_user_1100",
            thread_id="thread_1400",
            session_id="session_1700",
            workspace_id="persistent_workspace_1000"
        )
        
        persistence_service = StatePersistenceService()
        # The service is already configured with Redis, PostgreSQL, and ClickHouse via dependency injection
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            persistence_service=persistence_service
        )
        
        # Create complex agent state
        agent_state = DeepAgentState(
            agent_id="complex_persistent_agent",
            user_context=user_context,
            initial_state="initializing"
        )
        
        # Build complex state over multiple phases
        workflow_phases = [
            {
                "state": "data_collection",
                "data": {
                    "collected_sources": ["aws_api", "azure_api", "gcp_api"],
                    "collection_progress": 0.33,
                    "raw_data_size_mb": 125,
                    "collection_metadata": {
                        "start_time": "2024-01-15T10:00:00Z",
                        "collection_strategy": "parallel",
                        "api_calls_made": 450
                    }
                }
            },
            {
                "state": "data_analysis", 
                "data": {
                    "analysis_algorithms": ["cost_trend", "anomaly_detection", "usage_pattern"],
                    "analysis_progress": 0.67,
                    "preliminary_findings": {
                        "cost_trend": "increasing_15_percent", 
                        "anomalies_detected": 3,
                        "usage_patterns": ["peak_morning", "idle_weekend"]
                    },
                    "intermediate_results": {"confidence_scores": [0.87, 0.92, 0.78]}
                }
            },
            {
                "state": "optimization_planning",
                "data": {
                    "optimization_opportunities": [
                        {"type": "rightsizing", "potential_savings": 8500, "complexity": "medium"},
                        {"type": "reserved_instances", "potential_savings": 12000, "complexity": "low"},
                        {"type": "storage_optimization", "potential_savings": 3500, "complexity": "high"}
                    ],
                    "implementation_plan": {
                        "phase_1": ["rightsizing"],
                        "phase_2": ["reserved_instances"],
                        "phase_3": ["storage_optimization"]
                    },
                    "risk_assessment": {"overall_risk": "low", "mitigation_strategies": 5}
                }
            }
        ]
        
        # Execute workflow with persistence at each phase
        persistence_snapshots = []
        for i, phase in enumerate(workflow_phases):
            # Transition state
            await state_tracker.transition_agent_state(
                agent_state=agent_state,
                from_state=agent_state.current_state,
                to_state=phase["state"]
            )
            
            # Update with complex state data
            await state_tracker.update_agent_state_data(
                agent_state=agent_state,
                data_update=phase["data"]
            )
            
            # Create persistence snapshot
            snapshot_id = await persistence_service.create_state_snapshot(
                agent_state=agent_state,
                snapshot_type="phase_complete",
                tier_preference="redis" if i == 0 else "postgres" if i == 1 else "clickhouse"
            )
            persistence_snapshots.append({
                "snapshot_id": snapshot_id,
                "phase": phase["state"],
                "tier": "redis" if i == 0 else "postgres" if i == 1 else "clickhouse"
            })
        
        # Act - Simulate system restart and recovery
        original_state_summary = {
            "agent_id": agent_state.agent_id,
            "current_state": agent_state.current_state,
            "total_data_keys": len(agent_state.get_all_state_data()),
            "optimization_opportunities_count": len(agent_state.get_state_data("optimization_opportunities", []))
        }
        
        # Create new state tracker (simulates restart)
        new_state_tracker = AgentStateTracker(
            user_context=user_context,
            persistence_service=persistence_service
        )
        
        # Recover state
        recovered_state = await new_state_tracker.recover_agent_state(
            agent_id="complex_persistent_agent",
            user_context=user_context,
            recovery_strategy="latest_snapshot"
        )
        
        # Assert - Verify comprehensive recovery
        assert recovered_state is not None
        assert recovered_state.agent_id == original_state_summary["agent_id"]
        assert recovered_state.current_state == original_state_summary["current_state"]
        
        # Verify complex data recovery
        recovered_data = recovered_state.get_all_state_data()
        assert "optimization_opportunities" in recovered_data
        assert len(recovered_data["optimization_opportunities"]) == 3
        assert recovered_data["optimization_opportunities"][0]["type"] == "rightsizing"
        
        # Verify metadata preservation
        assert "collection_metadata" in recovered_data
        assert recovered_data["collection_metadata"]["api_calls_made"] == 450
        
        # Verify analysis results preservation
        assert "preliminary_findings" in recovered_data
        assert recovered_data["preliminary_findings"]["anomalies_detected"] == 3
        
        # Verify can continue workflow from recovered state
        continue_result = await new_state_tracker.transition_agent_state(
            agent_state=recovered_state,
            from_state=recovered_state.current_state,
            to_state="optimization_execution"
        )
        
        assert continue_result.success is True

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_cross_session_state_continuity(self, real_services_fixture):
        """Test state continuity across different user sessions."""
        # Arrange - First session
        session_1_context = UserExecutionContext(
            user_id="continuity_user_1101",
            thread_id="persistent_thread_001", 
            session_id="session_1701",  # First session
            workspace_id="continuity_workspace_1001"
        )
        
        persistence_service = StatePersistenceService(
            redis_client=real_services_fixture.get("redis", MagicMock()),
            postgres_client=real_services_fixture.get("postgres", MagicMock()),
            cross_session_enabled=True
        )
        
        state_tracker_session_1 = AgentStateTracker(
            user_context=session_1_context,
            persistence_service=persistence_service
        )
        
        # Start long-running analysis in first session
        agent_state_session_1 = DeepAgentState(
            agent_id="cross_session_agent",
            user_context=session_1_context,
            initial_state="started"
        )
        
        # Perform partial work
        partial_work_data = {
            "analysis_started": True,
            "data_processed": 0.6,
            "partial_results": {
                "cost_analysis": {"current_spend": 25000, "trend": "increasing"},
                "resource_analysis": {"utilization": 0.45, "waste_detected": True}
            },
            "next_steps": ["complete_optimization_analysis", "generate_recommendations"],
            "session_metadata": {
                "session_id": session_1_context.session_id,
                "work_duration_minutes": 15,
                "interruption_point": "mid_analysis"
            }
        }
        
        await state_tracker_session_1.update_agent_state_data(
            agent_state=agent_state_session_1,
            data_update=partial_work_data
        )
        
        await state_tracker_session_1.transition_agent_state(
            agent_state=agent_state_session_1,
            from_state="started",
            to_state="analysis_in_progress"
        )
        
        # Persist state before "session ends"
        await persistence_service.persist_cross_session_state(
            agent_state=agent_state_session_1,
            session_end_type="user_disconnect",
            resumable=True
        )
        
        # Arrange - Second session (different session ID, same user/thread)
        session_2_context = UserExecutionContext(
            user_id="continuity_user_1101",  # Same user
            thread_id="persistent_thread_001",  # Same thread 
            session_id="session_1702",  # Different session
            workspace_id="continuity_workspace_1001"  # Same workspace
        )
        
        state_tracker_session_2 = AgentStateTracker(
            user_context=session_2_context,
            persistence_service=persistence_service
        )
        
        # Act - Resume work in second session
        resumable_work = await persistence_service.find_resumable_work(
            user_id=session_2_context.user_id,
            thread_id=session_2_context.thread_id
        )
        
        assert len(resumable_work) > 0
        assert resumable_work[0]["agent_id"] == "cross_session_agent"
        
        # Resume the agent state
        resumed_state = await state_tracker_session_2.resume_cross_session_agent(
            agent_id="cross_session_agent",
            original_session_id="session_1701",
            current_session_context=session_2_context
        )
        
        # Continue work from where it left off
        await state_tracker_session_2.update_agent_state_data(
            agent_state=resumed_state,
            data_update={
                "analysis_completed": True,
                "data_processed": 1.0,
                "final_results": {
                    "optimization_recommendations": [
                        {"type": "rightsizing", "savings": 7500},
                        {"type": "scheduling", "savings": 3000}
                    ]
                },
                "resumed_in_session": session_2_context.session_id,
                "completion_time": "2024-01-15T11:30:00Z"
            }
        )
        
        await state_tracker_session_2.transition_agent_state(
            agent_state=resumed_state,
            from_state="analysis_in_progress",
            to_state="completed"
        )
        
        # Assert - Verify cross-session continuity
        assert resumed_state.current_state == "completed"
        
        # Verify original work was preserved
        state_data = resumed_state.get_all_state_data()
        assert state_data["analysis_started"] is True
        assert state_data["partial_results"]["cost_analysis"]["current_spend"] == 25000
        
        # Verify new work was added
        assert state_data["analysis_completed"] is True
        assert "final_results" in state_data
        assert len(state_data["final_results"]["optimization_recommendations"]) == 2
        
        # Verify session tracking
        assert state_data["session_metadata"]["session_id"] == "session_1701"  # Original
        assert state_data["resumed_in_session"] == "session_1702"  # Current

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_state_integrity_validation_and_repair(self, real_services_fixture):
        """Test state integrity validation and automatic repair mechanisms."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="integrity_user_1102",
            thread_id="thread_1402", 
            session_id="session_1703",
            workspace_id="integrity_workspace_1002"
        )
        
        persistence_service = StatePersistenceService(
            redis_client=real_services_fixture.get("redis", MagicMock()),
            postgres_client=real_services_fixture.get("postgres", MagicMock()),
            integrity_checking=True,
            auto_repair=True
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            persistence_service=persistence_service
        )
        
        # Create agent state with checksums
        agent_state = DeepAgentState(
            agent_id="integrity_test_agent",
            user_context=user_context,
            initial_state="processing"
        )
        
        # Add critical state data
        critical_data = {
            "financial_analysis": {
                "total_cost": 45000.00,
                "cost_breakdown": {
                    "compute": 25000.00,
                    "storage": 15000.00,
                    "network": 5000.00
                }
            },
            "optimization_results": {
                "identified_savings": 12500.00,
                "confidence_level": 0.92,
                "recommendations": [
                    {"id": "rec_001", "type": "rightsizing", "impact": 8000.00},
                    {"id": "rec_002", "type": "storage_optimization", "impact": 4500.00}
                ]
            }
        }
        
        await state_tracker.update_agent_state_data(
            agent_state=agent_state,
            data_update=critical_data
        )
        
        # Create persistence snapshot with integrity checks
        snapshot_with_checksum = await persistence_service.create_integrity_checked_snapshot(
            agent_state=agent_state,
            checksum_algorithm="sha256",
            backup_redundancy=2
        )
        
        # Act - Simulate data corruption and recovery
        # Intentionally corrupt some data (simulating storage issues)
        corrupted_agent_state = DeepAgentState(
            agent_id="integrity_test_agent",
            user_context=user_context,
            initial_state="processing"
        )
        
        # Corrupt the financial data
        corrupted_data = critical_data.copy()
        corrupted_data["financial_analysis"]["total_cost"] = 999999.99  # Corrupted
        corrupted_data["optimization_results"]["confidence_level"] = "invalid"  # Type corruption
        del corrupted_data["optimization_results"]["recommendations"][0]  # Missing data
        
        corrupted_agent_state.update_state_data(corrupted_data)
        
        # Run integrity validation
        integrity_report = await persistence_service.validate_state_integrity(
            agent_state=corrupted_agent_state,
            reference_checksum=snapshot_with_checksum["checksum"]
        )
        
        assert integrity_report["integrity_valid"] is False
        assert integrity_report["corruption_detected"] is True
        assert len(integrity_report["integrity_violations"]) > 0
        
        # Attempt automatic repair
        repair_result = await persistence_service.repair_corrupted_state(
            corrupted_agent_state=corrupted_agent_state,
            integrity_snapshot=snapshot_with_checksum,
            repair_strategy="restore_from_backup"
        )
        
        # Assert - Verify integrity validation and repair
        assert repair_result["repair_successful"] is True
        assert repair_result["data_restored"] is True
        
        # Verify repaired data matches original
        repaired_data = repair_result["repaired_state"].get_all_state_data()
        assert repaired_data["financial_analysis"]["total_cost"] == 45000.00  # Restored
        assert repaired_data["optimization_results"]["confidence_level"] == 0.92  # Fixed type
        assert len(repaired_data["optimization_results"]["recommendations"]) == 2  # Restored missing data
        
        # Verify integrity after repair
        post_repair_validation = await persistence_service.validate_state_integrity(
            agent_state=repair_result["repaired_state"],
            reference_checksum=snapshot_with_checksum["checksum"]
        )
        
        assert post_repair_validation["integrity_valid"] is True
        assert post_repair_validation["corruption_detected"] is False

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_disaster_recovery_and_backup_strategies(self, real_services_fixture):
        """Test disaster recovery scenarios and backup strategies."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="disaster_user_1103",
            thread_id="thread_1403",
            session_id="session_1704", 
            workspace_id="disaster_workspace_1003"
        )
        
        # Multi-tier backup configuration
        backup_config = {
            "primary_storage": "redis",
            "secondary_storage": "postgres", 
            "disaster_recovery_storage": "clickhouse",
            "geo_replication": True,
            "backup_frequency": "real_time",
            "retention_policy": "30_days"
        }
        
        persistence_service = StatePersistenceService(
            redis_client=real_services_fixture.get("redis", MagicMock()),
            postgres_client=real_services_fixture.get("postgres", MagicMock()), 
            clickhouse_client=real_services_fixture.get("clickhouse", MagicMock()),
            backup_config=backup_config,
            disaster_recovery_enabled=True
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            persistence_service=persistence_service
        )
        
        # Create critical business state
        agent_state = DeepAgentState(
            agent_id="disaster_recovery_agent",
            user_context=user_context,
            initial_state="critical_analysis"
        )
        
        # Business-critical state that must survive disasters
        critical_business_data = {
            "customer_cost_analysis": {
                "customer_id": "enterprise_customer_001",
                "analysis_type": "annual_optimization_review", 
                "current_annual_spend": 2400000.00,
                "optimization_potential": 480000.00,
                "roi_timeline_months": 8
            },
            "regulatory_compliance": {
                "compliance_frameworks": ["SOX", "PCI-DSS", "GDPR"],
                "audit_trail": [
                    {"timestamp": "2024-01-15T10:00:00Z", "action": "analysis_started", "user": user_context.user_id},
                    {"timestamp": "2024-01-15T10:15:00Z", "action": "data_validated", "compliance_check": "passed"}
                ]
            },
            "executive_deliverables": {
                "board_presentation_due": "2024-01-20",
                "stakeholders": ["CEO", "CFO", "CTO"],
                "commitment_savings": 450000.00,
                "presentation_status": "in_progress"
            }
        }
        
        await state_tracker.update_agent_state_data(
            agent_state=agent_state,
            data_update=critical_business_data
        )
        
        # Create multi-tier backups
        backup_results = await persistence_service.create_disaster_recovery_backup(
            agent_state=agent_state,
            backup_tiers=["primary", "secondary", "disaster_recovery"],
            priority="critical_business_data"
        )
        
        # Act - Simulate various disaster scenarios
        disaster_scenarios = [
            {
                "name": "primary_storage_failure",
                "failed_tiers": ["primary"],
                "recovery_tier": "secondary"
            },
            {
                "name": "dual_storage_failure", 
                "failed_tiers": ["primary", "secondary"],
                "recovery_tier": "disaster_recovery"
            },
            {
                "name": "regional_outage",
                "failed_tiers": ["primary", "secondary"],
                "recovery_tier": "disaster_recovery",
                "geo_recovery": True
            }
        ]
        
        recovery_results = {}
        
        for scenario in disaster_scenarios:
            # Simulate disaster
            await persistence_service.simulate_storage_failure(
                failed_tiers=scenario["failed_tiers"]
            )
            
            # Attempt recovery
            recovery_start_time = time.time()
            
            recovered_state = await persistence_service.execute_disaster_recovery(
                agent_id="disaster_recovery_agent",
                user_context=user_context,
                recovery_tier=scenario["recovery_tier"],
                geo_recovery=scenario.get("geo_recovery", False)
            )
            
            recovery_end_time = time.time()
            recovery_time = recovery_end_time - recovery_start_time
            
            recovery_results[scenario["name"]] = {
                "recovery_successful": recovered_state is not None,
                "recovery_time_seconds": recovery_time,
                "data_integrity_maintained": False,
                "business_continuity": False
            }
            
            if recovered_state:
                # Verify data integrity
                recovered_data = recovered_state.get_all_state_data()
                
                # Check critical business data preservation
                if "customer_cost_analysis" in recovered_data:
                    original_spend = critical_business_data["customer_cost_analysis"]["current_annual_spend"]
                    recovered_spend = recovered_data["customer_cost_analysis"]["current_annual_spend"]
                    recovery_results[scenario["name"]]["data_integrity_maintained"] = (original_spend == recovered_spend)
                
                # Check business continuity capability
                if "executive_deliverables" in recovered_data:
                    recovery_results[scenario["name"]]["business_continuity"] = (
                        recovered_data["executive_deliverables"]["presentation_status"] == "in_progress"
                    )
            
            # Reset for next scenario
            await persistence_service.reset_storage_simulation()
        
        # Assert - Verify disaster recovery capabilities
        for scenario_name, result in recovery_results.items():
            assert result["recovery_successful"] is True, f"Recovery failed for {scenario_name}"
            assert result["recovery_time_seconds"] < 30.0, f"Recovery took too long for {scenario_name}"
            assert result["data_integrity_maintained"] is True, f"Data integrity lost in {scenario_name}"
            assert result["business_continuity"] is True, f"Business continuity broken in {scenario_name}"
        
        # Verify all scenarios could be recovered
        assert len(recovery_results) == 3
        assert all(result["recovery_successful"] for result in recovery_results.values())
        
        # Verify disaster recovery backup strategy worked
        assert backup_results["backup_tiers_created"] >= 3
        assert backup_results["geo_replication_enabled"] is True