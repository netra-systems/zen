"""Golden Datasets for Agent Persistence Testing

This module provides standardized test data representing common business flows
for comprehensive agent persistence testing across the 3-tier architecture.

Business Value Justification (BVJ):
- Segment: Enterprise, Mid
- Business Goal: Platform Stability, Customer Retention
- Value Impact: Ensures data integrity for $25K+ MRR agent workloads
- Strategic Impact: Validates persistence for 24/7 enterprise operations
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.triage.models import TriageResult, TriageMetadata, Priority, Complexity
from netra_backend.app.schemas.agent_state import (
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.schemas.shared_types import (
    AnomalyDetectionResponse,
    AnomalyDetail,
    AnomalySeverity,
    DataAnalysisResponse,
    PerformanceMetrics,
)


class GoldenDatasets:
    """Provides golden datasets for critical business flow testing."""
    
    @staticmethod
    def get_simple_agent_flow() -> Dict[str, Any]:
        """Simple single-agent execution flow (Free/Early tier).
        
        Represents: Basic user query  ->  triage  ->  response flow
        Business Impact: 80% of Free tier usage, conversion path
        """
        run_id = str(uuid.uuid4())
        user_id = "test_user_free_001"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        return {
            "run_id": run_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "initial_state": DeepAgentState(
                user_request="Analyze my API response times",
                chat_thread_id=thread_id,
                user_id=user_id,
                run_id=run_id,
                step_count=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            "triage_result": TriageResult(
                category="data_analysis",
                confidence_score=0.95,
                priority=Priority.MEDIUM,
                complexity=Complexity.LOW,
                metadata=TriageMetadata(
                    triage_duration_ms=150,
                    cache_hit=False
                )
            ),
            "data_result": DataAnalysisResponse(
                analysis_id=f"analysis_{uuid.uuid4().hex[:8]}",
                status="completed",
                results={
                    "query": "SELECT avg(response_time), p95(response_time), p99(response_time) FROM api_metrics",
                    "data": [
                        {"metric": "avg_response_time", "value": 250},
                        {"metric": "p95_response_time", "value": 450},
                        {"metric": "p99_response_time", "value": 800}
                    ],
                    "insights": {
                        "performance_summary": "API response times analyzed", 
                        "average_response": "250ms",
                        "p95_response": "450ms", 
                        "p99_response": "800ms"
                    },
                    "recommendations": ["Consider caching for slow endpoints"],
                    "affected_rows": 10000
                },
                metrics=PerformanceMetrics(
                    duration_ms=2500.0,
                    latency_p95=450.0,
                    latency_p99=800.0
                ),
                created_at=datetime.now(timezone.utc).timestamp()
            ),
            "expected_metrics": {
                "total_steps": 3,
                "duration_seconds": 5.0,
                "tokens_used": 1500,
                "cache_hits": 1
            }
        }
    
    @staticmethod
    def get_multi_agent_collaboration_flow() -> Dict[str, Any]:
        """Multi-agent collaboration flow (Mid/Enterprise tier).
        
        Represents: Complex query  ->  supervisor  ->  multiple sub-agents  ->  aggregation
        Business Impact: Core Enterprise value prop, $10K+ MRR workloads
        """
        run_id = str(uuid.uuid4())
        user_id = "test_user_enterprise_001"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        return {
            "run_id": run_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "supervisor_state": DeepAgentState(
                user_request="Optimize our entire data pipeline for cost and performance",
                chat_thread_id=thread_id,
                user_id=user_id,
                run_id=run_id,
                step_count=0,
                agent_type="supervisor",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            "sub_agent_states": [
                {
                    "agent_type": "data_analyst",
                    "run_id": f"{run_id}_data",
                    "result": DataAnalysisResponse(
                        analysis_id=f"analysis_{uuid.uuid4().hex[:8]}",
                        status="completed",
                        results={
                            "query": "SELECT stage, resource_usage, data_skew FROM pipeline_metrics WHERE pipeline_id = ?",
                            "data": [
                                {"stage": "etl_stage_3", "resource_usage": 0.60, "data_skew": True},
                                {"stage": "etl_stage_1", "resource_usage": 0.25, "data_skew": False}
                            ],
                            "insights": {
                                "summary": "Pipeline bottlenecks identified",
                                "main_issue": "ETL stage 3 using 60% resources",
                                "secondary_issue": "Data skew detected"
                            },
                            "recommendations": ["Partition rebalancing", "Add parallel processing"],
                            "affected_rows": 50000
                        },
                        metrics=PerformanceMetrics(
                            duration_ms=15300.0
                        ),
                        created_at=datetime.now(timezone.utc).timestamp()
                    )
                },
                {
                    "agent_type": "anomaly_detector",
                    "run_id": f"{run_id}_anomaly",
                    "result": AnomalyDetectionResponse(
                        anomalies_detected=[
                            AnomalyDetail(
                                metric_name="cost_spike",
                                value=150.0,
                                expected_value=100.0,
                                deviation=50.0,
                                severity=AnomalySeverity.HIGH,
                                timestamp=datetime.now(timezone.utc).timestamp()
                            ),
                            AnomalyDetail(
                                metric_name="performance_degradation",
                                value=0.75,
                                expected_value=0.95,
                                deviation=-0.20,
                                severity=AnomalySeverity.MEDIUM,
                                timestamp=datetime.now(timezone.utc).timestamp()
                            ),
                            AnomalyDetail(
                                metric_name="data_quality",
                                value=0.88,
                                expected_value=0.95,
                                deviation=-0.07,
                                severity=AnomalySeverity.LOW,
                                timestamp=datetime.now(timezone.utc).timestamp()
                            )
                        ],
                        total_anomalies=3,
                        detection_time_ms=450.0,
                        model_version="anomaly_v2.1",
                        confidence_threshold=0.85
                    )
                },
                {
                    "agent_type": "optimization_agent",
                    "run_id": f"{run_id}_optimize",
                    "result": {
                        "optimizations": [
                            {"type": "resource_allocation", "estimated_savings": "$2,500/month"},
                            {"type": "query_optimization", "performance_gain": "35%"},
                            {"type": "caching_strategy", "latency_reduction": "60%"}
                        ],
                        "implementation_plan": ["Phase 1: Quick wins", "Phase 2: Infrastructure", "Phase 3: Monitoring"],
                        "risk_assessment": "low",
                        "metadata": {"simulation_runs": 100}
                    }
                }
            ],
            "expected_metrics": {
                "total_agents": 4,  # supervisor + 3 sub-agents
                "total_steps": 15,
                "duration_seconds": 45.0,
                "tokens_used": 8500,
                "parallel_executions": 3,
                "checkpoint_count": 5
            }
        }
    
    @staticmethod
    def get_long_running_agent_flow() -> Dict[str, Any]:
        """24-hour long-running agent flow (Enterprise tier).
        
        Represents: Continuous monitoring/optimization agent
        Business Impact: Enterprise SLA compliance, $25K+ MRR
        """
        run_id = str(uuid.uuid4())
        user_id = "test_user_enterprise_002"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now(timezone.utc) - timedelta(hours=23)
        
        checkpoints = []
        for hour in range(24):
            checkpoint_time = start_time + timedelta(hours=hour)
            checkpoints.append({
                "hour": hour,
                "timestamp": checkpoint_time,
                "metrics": {
                    "systems_monitored": 15,
                    "anomalies_detected": hour % 5,  # Some variation
                    "optimizations_applied": hour // 6,  # Every 6 hours
                    "cost_saved": hour * 125.50,  # Accumulating savings
                    "alerts_sent": max(0, (hour % 8) - 6)  # Spike every 8 hours
                },
                "state_size_kb": 50 + (hour * 2),  # Growing state
                "checkpoint_type": CheckpointType.FULL if hour % 6 == 0 else CheckpointType.AUTO
            })
        
        return {
            "run_id": run_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "start_time": start_time,
            "checkpoints": checkpoints,
            "final_state": DeepAgentState(
                user_request="Monitor and optimize our infrastructure 24/7",
                chat_thread_id=thread_id,
                user_id=user_id,
                run_id=run_id,
                step_count=1440,  # One step per minute for 24 hours
                agent_type="monitoring_supervisor",
                created_at=start_time,
                updated_at=datetime.now(timezone.utc),
                metadata={
                    "total_runtime_hours": 24,
                    "total_cost_saved": 3012.00,
                    "systems_monitored": 15,
                    "total_anomalies": 28,
                    "total_optimizations": 4
                }
            ),
            "expected_metrics": {
                "total_checkpoints": 24,
                "critical_checkpoints": 4,
                "total_state_size_mb": 2.5,
                "redis_operations": 2880,  # Read/write every 30 seconds
                "postgres_checkpoints": 4,
                "clickhouse_migrations": 1  # After completion
            }
        }
    
    @staticmethod
    def get_failure_recovery_flow() -> Dict[str, Any]:
        """Agent failure and recovery flow (All tiers).
        
        Represents: Agent crash  ->  state recovery  ->  resume execution
        Business Impact: Platform reliability, customer trust
        """
        run_id = str(uuid.uuid4())
        user_id = "test_user_recovery_001"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        return {
            "run_id": run_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "pre_failure_state": DeepAgentState(
                user_request="Complex multi-step analysis",
                chat_thread_id=thread_id,
                user_id=user_id,
                run_id=run_id,
                step_count=7,
                agent_type="data_analyst",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                updated_at=datetime.now(timezone.utc) - timedelta(seconds=30),
                metadata={
                    "progress_percentage": 70,
                    "partial_results": {"analyzed_records": 50000, "findings": 12}
                }
            ),
            "failure_point": {
                "step": 8,
                "error_type": "NetworkTimeout",
                "timestamp": datetime.now(timezone.utc) - timedelta(seconds=25),
                "state_corrupted": False,
                "recovery_possible": True
            },
            "recovery_state": DeepAgentState(
                user_request="Complex multi-step analysis",
                chat_thread_id=thread_id,
                user_id=user_id,
                run_id=run_id,
                step_count=7,  # Resume from last checkpoint
                agent_type="data_analyst",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                updated_at=datetime.now(timezone.utc),
                metadata={
                    "progress_percentage": 70,
                    "partial_results": {"analyzed_records": 50000, "findings": 12},
                    "recovery_metadata": {
                        "recovered_from": "redis_primary",
                        "recovery_time_ms": 150,
                        "data_loss": False
                    }
                }
            ),
            "expected_recovery_metrics": {
                "recovery_time_ms": 150,
                "data_loss": False,
                "recovery_source": "redis",
                "fallback_attempts": 0,
                "state_integrity": True
            }
        }
    
    @staticmethod
    def get_high_concurrency_flow() -> Dict[str, Any]:
        """High concurrency agent flow (Enterprise tier).
        
        Represents: 100+ concurrent agents for same user
        Business Impact: Enterprise scalability, $50K+ MRR potential
        """
        user_id = "test_user_enterprise_003"
        base_thread = f"thread_{uuid.uuid4().hex[:8]}"
        
        concurrent_agents = []
        for i in range(100):
            run_id = str(uuid.uuid4())
            agent_type = ["data_analyst", "anomaly_detector", "optimizer", "monitor"][i % 4]
            
            concurrent_agents.append({
                "run_id": run_id,
                "thread_id": f"{base_thread}_{i}",
                "agent_type": agent_type,
                "start_time": datetime.now(timezone.utc) - timedelta(seconds=i * 0.5),
                "state": DeepAgentState(
                    user_request=f"Concurrent task {i}",
                    chat_thread_id=f"{base_thread}_{i}",
                    user_id=user_id,
                    run_id=run_id,
                    step_count=i % 10,
                    agent_type=agent_type,
                    created_at=datetime.now(timezone.utc) - timedelta(seconds=i * 0.5),
                    updated_at=datetime.now(timezone.utc),
                    metadata={"task_index": i, "batch_id": i // 10}
                )
            })
        
        return {
            "user_id": user_id,
            "concurrent_agents": concurrent_agents,
            "expected_metrics": {
                "total_agents": 100,
                "concurrent_peak": 100,
                "redis_connections": 20,  # Connection pooling
                "postgres_connections": 5,  # Limited pool
                "total_memory_mb": 500,
                "avg_latency_ms": 50,
                "p99_latency_ms": 200,
                "failed_saves": 0,
                "race_conditions": 0
            }
        }
    
    @staticmethod
    def validate_persistence_result(flow_type: str, actual_result: Any, 
                                   expected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate persistence results against golden dataset expectations.
        
        Args:
            flow_type: Type of flow being validated
            actual_result: Actual persistence/recovery result
            expected_data: Expected data from golden dataset
            
        Returns:
            Validation report with pass/fail and discrepancies
        """
        validation_report = {
            "flow_type": flow_type,
            "passed": True,
            "discrepancies": [],
            "metrics_comparison": {}
        }
        
        # Compare expected metrics
        if "expected_metrics" in expected_data and hasattr(actual_result, "metrics"):
            for metric_key, expected_value in expected_data["expected_metrics"].items():
                actual_value = getattr(actual_result.metrics, metric_key, None)
                if actual_value is None:
                    validation_report["discrepancies"].append(f"Missing metric: {metric_key}")
                    validation_report["passed"] = False
                elif isinstance(expected_value, (int, float)):
                    # Allow 10% variance for numeric metrics
                    if abs(actual_value - expected_value) > expected_value * 0.1:
                        validation_report["discrepancies"].append(
                            f"Metric {metric_key}: expected {expected_value}, got {actual_value}"
                        )
                        validation_report["passed"] = False
                validation_report["metrics_comparison"][metric_key] = {
                    "expected": expected_value,
                    "actual": actual_value
                }
        
        # Validate state integrity
        if hasattr(actual_result, "state") and "initial_state" in expected_data:
            expected_state = expected_data["initial_state"]
            actual_state = actual_result.state
            
            # Check critical fields
            critical_fields = ["user_id", "run_id", "chat_thread_id", "user_request"]
            for field in critical_fields:
                expected_val = getattr(expected_state, field, None)
                actual_val = getattr(actual_state, field, None)
                if expected_val != actual_val:
                    validation_report["discrepancies"].append(
                        f"State field {field}: expected {expected_val}, got {actual_val}"
                    )
                    validation_report["passed"] = False
        
        return validation_report


# Export golden datasets for easy access
GOLDEN_SIMPLE_FLOW = GoldenDatasets.get_simple_agent_flow()
GOLDEN_MULTI_AGENT_FLOW = GoldenDatasets.get_multi_agent_collaboration_flow()
GOLDEN_LONG_RUNNING_FLOW = GoldenDatasets.get_long_running_agent_flow()
GOLDEN_RECOVERY_FLOW = GoldenDatasets.get_failure_recovery_flow()
GOLDEN_HIGH_CONCURRENCY_FLOW = GoldenDatasets.get_high_concurrency_flow()