"""
Agent Monitoring and Observability Testing (Iterations 36-40).

Tests comprehensive monitoring, metrics collection, alerting,
and observability features for the agent system.
"""

import asyncio
import pytest
from typing import Dict, Any, List
import time
import json
from datetime import datetime, timezone
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import RedisTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent


@pytest.mark.monitoring
class TestAgentMetricsCollection:
    """Test comprehensive agent metrics collection."""
    
    @pytest.mark.asyncio
    async def test_agent_performance_metrics(self):
        """Test agent performance metrics collection."""
        # Mock metrics collector
        collected_metrics = []
        
        def mock_collect_metric(metric_name, value, labels=None, metric_type="gauge"):
            metric_entry = {
                "name": metric_name,
                "value": value,
                "labels": labels or {},
                "type": metric_type,
                "timestamp": time.time()
            }
            collected_metrics.append(metric_entry)
        
        with patch('netra_backend.app.monitoring.metrics_collector.collect_metric', side_effect=mock_collect_metric):
            
            agent_state = DeepAgentState(
                agent_id="metrics_agent",
                session_id="metrics_session",
                thread_id="metrics_thread",
                context={"metrics_collection": True, "detailed_monitoring": True}
            )
            
            agent = SupervisorAgent(
                agent_id="metrics_test",
                initial_state=agent_state
            )
            
            # Execute various operations to generate metrics
            operations = [
                {"type": "database_query", "duration": 0.05, "success": True},
                {"type": "llm_request", "duration": 1.2, "success": True},
                {"type": "data_processing", "duration": 0.3, "success": False},
                {"type": "websocket_broadcast", "duration": 0.01, "success": True}
            ]
            
            for operation in operations:
                await agent._execute_monitored_operation(operation)
            
            # Verify comprehensive metrics were collected
            assert len(collected_metrics) >= 12  # Multiple metrics per operation
            
            # Check for key performance metrics
            metric_names = [m["name"] for m in collected_metrics]
            
            expected_metrics = [
                "agent_operation_duration_seconds",
                "agent_operation_count_total", 
                "agent_success_rate",
                "agent_error_count_total",
                "agent_memory_usage_bytes",
                "agent_active_tasks",
                "agent_queue_size"
            ]
            
            for expected_metric in expected_metrics:
                assert any(expected_metric in name for name in metric_names)
            
            # Verify metric labels contain agent context
            labeled_metrics = [m for m in collected_metrics if m["labels"]]
            assert len(labeled_metrics) > 0
            
            for metric in labeled_metrics:
                assert "agent_id" in metric["labels"]
                assert "session_id" in metric["labels"]
                assert metric["labels"]["agent_id"] == "metrics_agent"
            
            # Check operation-specific metrics
            database_metrics = [m for m in collected_metrics if "database" in m["name"]]
            llm_metrics = [m for m in collected_metrics if "llm" in m["name"]]
            
            assert len(database_metrics) >= 2  # Duration and count metrics
            assert len(llm_metrics) >= 2
    
    @pytest.mark.asyncio
    async def test_agent_error_metrics_and_alerting(self):
        """Test agent error metrics and alerting thresholds."""
        # Mock metrics and alerting systems
        collected_metrics = []
        triggered_alerts = []
        
        def mock_collect_metric(metric_name, value, labels=None, metric_type="gauge"):
            metric_entry = {
                "name": metric_name,
                "value": value,
                "labels": labels or {},
                "type": metric_type,
                "timestamp": time.time()
            }
            collected_metrics.append(metric_entry)
        
        def mock_trigger_alert(alert_name, severity, details):
            alert_entry = {
                "alert_name": alert_name,
                "severity": severity,
                "details": details,
                "timestamp": time.time()
            }
            triggered_alerts.append(alert_entry)
        
        with patch('netra_backend.app.monitoring.metrics_collector.collect_metric', side_effect=mock_collect_metric):
            with patch('netra_backend.app.monitoring.alerting.trigger_alert', side_effect=mock_trigger_alert):
                
                agent_state = DeepAgentState(
                    agent_id="error_monitoring_agent",
                    session_id="error_session",
                    thread_id="error_thread", 
                    context={
                        "error_monitoring": True,
                        "alert_thresholds": {
                            "error_rate": 0.2,  # 20% error rate threshold
                            "consecutive_errors": 5,
                            "response_time_p95": 2.0  # 2 second response time
                        }
                    }
                )
                
                agent = SupervisorAgent(
                    agent_id="error_monitoring_test",
                    initial_state=agent_state
                )
                
                # Simulate operations with varying error rates
                operation_results = [
                    {"success": True, "duration": 0.1},   # Success
                    {"success": True, "duration": 0.15},  # Success
                    {"success": False, "duration": 0.8, "error": "Database timeout"},  # Error
                    {"success": False, "duration": 1.2, "error": "Service unavailable"},  # Error
                    {"success": True, "duration": 0.2},   # Success
                    {"success": False, "duration": 0.9, "error": "Connection failed"},  # Error
                    {"success": False, "duration": 2.5, "error": "Slow response"},  # Error + slow
                    {"success": False, "duration": 0.3, "error": "Validation failed"},  # Error
                ]
                
                for i, result in enumerate(operation_results):
                    await agent._execute_operation_with_monitoring({
                        "operation_id": i,
                        "simulate_result": result
                    })
                
                # Verify error metrics were collected
                error_metrics = [m for m in collected_metrics if "error" in m["name"]]
                assert len(error_metrics) >= 3  # Error count, rate, consecutive errors
                
                # Check for error rate calculation
                error_rate_metrics = [m for m in collected_metrics if "error_rate" in m["name"]]
                assert len(error_rate_metrics) > 0
                
                # Error rate should be calculated correctly (5 errors out of 8 operations = 62.5%)
                latest_error_rate = max(error_rate_metrics, key=lambda x: x["timestamp"])
                assert latest_error_rate["value"] > 0.6  # Should be around 62.5%
                
                # Verify alerts were triggered
                assert len(triggered_alerts) >= 1
                
                # Check for high error rate alert
                error_rate_alerts = [a for a in triggered_alerts if "error_rate" in a["alert_name"]]
                assert len(error_rate_alerts) >= 1
                
                # Check for high response time alert
                response_time_alerts = [a for a in triggered_alerts if "response_time" in a["alert_name"]]
                assert len(response_time_alerts) >= 1  # 2.5s operation should trigger alert
                
                # Verify alert details
                high_error_alert = error_rate_alerts[0]
                assert high_error_alert["severity"] in ["warning", "critical"]
                assert "error_rate" in high_error_alert["details"]
    
    @pytest.mark.asyncio
    async def test_agent_resource_utilization_monitoring(self):
        """Test agent resource utilization monitoring."""
        # Mock resource monitoring
        resource_snapshots = []
        
        def mock_capture_resource_snapshot(agent_id):
            snapshot = {
                "agent_id": agent_id,
                "timestamp": time.time(),
                "cpu_percent": 25.5,
                "memory_mb": 128.7,
                "active_tasks": 3,
                "queue_depth": 5,
                "database_connections": 2,
                "websocket_connections": 10,
                "cache_hit_rate": 0.85
            }
            resource_snapshots.append(snapshot)
            return snapshot
        
        with patch('netra_backend.app.monitoring.resource_monitor.capture_snapshot', side_effect=mock_capture_resource_snapshot):
            
            agent_state = DeepAgentState(
                agent_id="resource_monitored_agent",
                session_id="resource_session",
                thread_id="resource_thread",
                context={"resource_monitoring": True, "monitoring_interval": 0.1}
            )
            
            agent = SupervisorAgent(
                agent_id="resource_monitoring_test",
                initial_state=agent_state
            )
            
            # Execute resource-intensive operations
            resource_operations = [
                {"type": "memory_intensive", "expected_memory_increase": 50},
                {"type": "cpu_intensive", "expected_cpu_increase": 20},
                {"type": "io_intensive", "expected_connections": 5},
                {"type": "concurrent_tasks", "task_count": 8}
            ]
            
            for operation in resource_operations:
                await agent._execute_resource_monitored_operation(operation)
                await asyncio.sleep(0.12)  # Allow monitoring interval
            
            # Verify resource snapshots were captured
            assert len(resource_snapshots) >= 4  # One per operation + baseline
            
            # Verify snapshot data completeness
            for snapshot in resource_snapshots:
                required_fields = ["cpu_percent", "memory_mb", "active_tasks", "queue_depth"]
                for field in required_fields:
                    assert field in snapshot
                    assert isinstance(snapshot[field], (int, float))
                    assert snapshot[field] >= 0
            
            # Check for resource utilization trends
            memory_values = [s["memory_mb"] for s in resource_snapshots]
            cpu_values = [s["cpu_percent"] for s in resource_snapshots]
            
            # Memory and CPU should show some variation during operations
            assert max(memory_values) > min(memory_values)  # Memory usage varied
            assert max(cpu_values) >= min(cpu_values)  # CPU usage tracked
            
            # Check for reasonable resource bounds
            assert all(cpu < 100 for cpu in cpu_values)  # CPU within bounds
            assert all(mem < 1000 for mem in memory_values)  # Memory within reasonable bounds


@pytest.mark.monitoring
class TestAgentTracing:
    """Test distributed tracing for agent operations."""
    
    @pytest.mark.asyncio
    async def test_agent_distributed_tracing(self):
        """Test distributed tracing across agent operations."""
        # Mock distributed tracing
        trace_spans = []
        
        def mock_start_span(span_name, parent_span_id=None, tags=None):
            span_id = f"span_{len(trace_spans) + 1}"
            span = {
                "span_id": span_id,
                "span_name": span_name,
                "parent_span_id": parent_span_id,
                "tags": tags or {},
                "start_time": time.time(),
                "end_time": None,
                "status": "active",
                "events": []
            }
            trace_spans.append(span)
            return span
        
        def mock_finish_span(span, status="success", error=None):
            span["end_time"] = time.time()
            span["status"] = status
            if error:
                span["error"] = str(error)
        
        def mock_add_span_event(span, event_name, attributes=None):
            event = {
                "event_name": event_name,
                "attributes": attributes or {},
                "timestamp": time.time()
            }
            span["events"].append(event)
        
        with patch('netra_backend.app.monitoring.tracing.start_span', side_effect=mock_start_span):
            with patch('netra_backend.app.monitoring.tracing.finish_span', side_effect=mock_finish_span):
                with patch('netra_backend.app.monitoring.tracing.add_span_event', side_effect=mock_add_span_event):
                    
                    agent_state = DeepAgentState(
                        agent_id="traced_agent",
                        session_id="traced_session",
                        thread_id="traced_thread",
                        context={"distributed_tracing": True, "trace_sampling": 1.0}
                    )
                    
                    agent = SupervisorAgent(
                        agent_id="tracing_test",
                        initial_state=agent_state
                    )
                    
                    # Execute traced workflow
                    workflow_config = {
                        "workflow_name": "data_analysis_workflow",
                        "steps": [
                            {"name": "fetch_data", "service": "database"},
                            {"name": "process_data", "service": "agent"},
                            {"name": "generate_insights", "service": "llm"},
                            {"name": "store_results", "service": "database"}
                        ]
                    }
                    
                    result = await agent._execute_traced_workflow(workflow_config)
                    
                    # Verify trace structure
                    assert len(trace_spans) >= 5  # Root span + step spans
                    
                    # Find root span
                    root_spans = [s for s in trace_spans if s["parent_span_id"] is None]
                    assert len(root_spans) == 1
                    root_span = root_spans[0]
                    
                    # Verify root span details
                    assert root_span["span_name"] == "data_analysis_workflow"
                    assert "agent_id" in root_span["tags"]
                    assert "session_id" in root_span["tags"]
                    assert root_span["status"] in ["success", "error"]
                    
                    # Find child spans
                    child_spans = [s for s in trace_spans if s["parent_span_id"] == root_span["span_id"]]
                    assert len(child_spans) >= 4  # One per workflow step
                    
                    # Verify span hierarchy and timing
                    step_names = [s["span_name"] for s in child_spans]
                    expected_steps = ["fetch_data", "process_data", "generate_insights", "store_results"]
                    for expected_step in expected_steps:
                        assert expected_step in step_names
                    
                    # Verify span timing relationships
                    for span in trace_spans:
                        if span["end_time"]:
                            assert span["end_time"] > span["start_time"]
                    
                    # Check for span events
                    spans_with_events = [s for s in trace_spans if s["events"]]
                    assert len(spans_with_events) > 0
                    
                    # Verify service tags
                    database_spans = [s for s in child_spans if s["tags"].get("service") == "database"]
                    assert len(database_spans) >= 2  # fetch_data and store_results
    
    @pytest.mark.asyncio
    async def test_agent_error_tracing(self):
        """Test error tracking and tracing in agent operations."""
        # Mock error tracing
        error_traces = []
        
        def mock_capture_error_trace(error, span_context=None, additional_context=None):
            error_trace = {
                "error_id": f"error_{len(error_traces) + 1}",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "span_context": span_context or {},
                "additional_context": additional_context or {},
                "timestamp": time.time(),
                "stack_trace": ["mock_stack_frame_1", "mock_stack_frame_2"]
            }
            error_traces.append(error_trace)
            return error_trace
        
        with patch('netra_backend.app.monitoring.error_tracking.capture_error', side_effect=mock_capture_error_trace):
            
            agent_state = DeepAgentState(
                agent_id="error_traced_agent",
                session_id="error_traced_session",
                thread_id="error_traced_thread",
                context={"error_tracing": True, "trace_errors": True}
            )
            
            agent = SupervisorAgent(
                agent_id="error_tracing_test",
                initial_state=agent_state
            )
            
            # Execute operations with various error scenarios
            error_scenarios = [
                {"operation": "database_query", "error_type": "ConnectionError", "error_msg": "Database unavailable"},
                {"operation": "llm_request", "error_type": "TimeoutError", "error_msg": "LLM service timeout"},
                {"operation": "data_validation", "error_type": "ValueError", "error_msg": "Invalid input data"},
                {"operation": "file_processing", "error_type": "FileNotFoundError", "error_msg": "File not found"}
            ]
            
            for scenario in error_scenarios:
                try:
                    await agent._execute_operation_with_error_tracing(scenario)
                except Exception:
                    pass  # Expected to fail
            
            # Verify error traces were captured
            assert len(error_traces) == len(error_scenarios)
            
            # Check error trace details
            for i, error_trace in enumerate(error_traces):
                expected_scenario = error_scenarios[i]
                
                assert error_trace["error_type"] == expected_scenario["error_type"]
                assert expected_scenario["error_msg"] in error_trace["error_message"]
                assert "agent_id" in error_trace["additional_context"]
                assert error_trace["additional_context"]["agent_id"] == "error_traced_agent"
            
            # Verify error correlation
            database_errors = [e for e in error_traces if "database" in e["additional_context"].get("operation", "")]
            llm_errors = [e for e in error_traces if "llm" in e["additional_context"].get("operation", "")]
            
            assert len(database_errors) >= 1
            assert len(llm_errors) >= 1
            
            # Check for error context preservation
            for error_trace in error_traces:
                assert "timestamp" in error_trace
                assert "stack_trace" in error_trace
                assert isinstance(error_trace["stack_trace"], list)
    
    @pytest.mark.asyncio
    async def test_agent_custom_metrics_and_dashboards(self):
        """Test custom metrics collection for agent dashboards."""
        # Mock custom metrics
        custom_metrics = {}
        
        def mock_record_custom_metric(metric_name, value, metric_type="gauge", labels=None):
            if metric_name not in custom_metrics:
                custom_metrics[metric_name] = []
            
            metric_entry = {
                "value": value,
                "type": metric_type,
                "labels": labels or {},
                "timestamp": time.time()
            }
            custom_metrics[metric_name].append(metric_entry)
        
        with patch('netra_backend.app.monitoring.custom_metrics.record_metric', side_effect=mock_record_custom_metric):
            
            agent_state = DeepAgentState(
                agent_id="dashboard_agent",
                session_id="dashboard_session", 
                thread_id="dashboard_thread",
                context={"custom_metrics": True, "dashboard_mode": "detailed"}
            )
            
            agent = SupervisorAgent(
                agent_id="dashboard_metrics_test",
                initial_state=agent_state
            )
            
            # Execute operations that generate business metrics
            business_operations = [
                {"type": "user_analysis", "users_processed": 150, "insights_generated": 12},
                {"type": "cost_optimization", "cost_saved_dollars": 247.50, "recommendations": 5},
                {"type": "performance_analysis", "queries_optimized": 8, "latency_improvement_ms": 125},
                {"type": "security_scan", "vulnerabilities_found": 3, "issues_resolved": 2}
            ]
            
            for operation in business_operations:
                await agent._execute_business_metrics_operation(operation)
            
            # Verify custom business metrics were recorded
            expected_metrics = [
                "agent_users_processed_total",
                "agent_insights_generated_total", 
                "agent_cost_saved_dollars_total",
                "agent_recommendations_count",
                "agent_queries_optimized_total",
                "agent_latency_improvement_ms",
                "agent_vulnerabilities_found_total",
                "agent_issues_resolved_total"
            ]
            
            for expected_metric in expected_metrics:
                assert expected_metric in custom_metrics
                assert len(custom_metrics[expected_metric]) > 0
            
            # Check metric values and types
            users_processed = custom_metrics["agent_users_processed_total"]
            assert sum(entry["value"] for entry in users_processed) == 150
            
            cost_saved = custom_metrics["agent_cost_saved_dollars_total"]
            assert any(entry["value"] == 247.50 for entry in cost_saved)
            
            # Verify metric labels for dashboard grouping
            labeled_metrics = []
            for metric_name, entries in custom_metrics.items():
                for entry in entries:
                    if entry["labels"]:
                        labeled_metrics.append((metric_name, entry))
            
            assert len(labeled_metrics) > 0
            
            # Check for dashboard-relevant labels
            dashboard_labels = ["agent_id", "operation_type", "session_id"]
            for metric_name, entry in labeled_metrics:
                labels = entry["labels"]
                assert any(label in labels for label in dashboard_labels)


@pytest.mark.monitoring
class TestAgentConfigurationMonitoring:
    """Test agent configuration monitoring and management."""
    
    @pytest.mark.asyncio
    async def test_agent_config_change_tracking(self):
        """Test tracking of agent configuration changes."""
        # Mock configuration tracking
        config_changes = []
        
        def mock_track_config_change(agent_id, config_key, old_value, new_value, change_reason):
            change_entry = {
                "agent_id": agent_id,
                "config_key": config_key,
                "old_value": old_value,
                "new_value": new_value,
                "change_reason": change_reason,
                "timestamp": time.time(),
                "change_id": f"change_{len(config_changes) + 1}"
            }
            config_changes.append(change_entry)
        
        with patch('netra_backend.app.monitoring.config_tracker.track_change', side_effect=mock_track_config_change):
            
            agent_state = DeepAgentState(
                agent_id="config_monitored_agent",
                session_id="config_session",
                thread_id="config_thread",
                context={"config_monitoring": True, "track_changes": True}
            )
            
            agent = SupervisorAgent(
                agent_id="config_monitoring_test",
                initial_state=agent_state
            )
            
            # Simulate configuration changes
            config_updates = [
                {"key": "max_retries", "old": 3, "new": 5, "reason": "increased_reliability"},
                {"key": "timeout_seconds", "old": 30, "new": 45, "reason": "slow_operations"},
                {"key": "batch_size", "old": 100, "new": 50, "reason": "memory_optimization"},
                {"key": "enable_caching", "old": True, "new": False, "reason": "debugging"}
            ]
            
            for update in config_updates:
                await agent._update_configuration(update["key"], update["new"], update["reason"])
            
            # Verify configuration changes were tracked
            assert len(config_changes) == len(config_updates)
            
            # Check change tracking details
            for i, change in enumerate(config_changes):
                expected_update = config_updates[i]
                
                assert change["agent_id"] == "config_monitored_agent"
                assert change["config_key"] == expected_update["key"]
                assert change["old_value"] == expected_update["old"]
                assert change["new_value"] == expected_update["new"]
                assert change["change_reason"] == expected_update["reason"]
                assert "timestamp" in change
                assert "change_id" in change
            
            # Verify configuration audit trail
            audit_trail = await agent._get_configuration_audit_trail()
            
            assert len(audit_trail["changes"]) == 4
            assert audit_trail["agent_id"] == "config_monitored_agent"
            assert all("timestamp" in change for change in audit_trail["changes"])
    
    @pytest.mark.asyncio
    async def test_agent_health_monitoring_integration(self):
        """Test integration with system health monitoring."""
        # Mock health monitoring integration
        health_reports = []
        
        def mock_report_agent_health(agent_id, health_status, metrics):
            health_report = {
                "agent_id": agent_id,
                "health_status": health_status,
                "metrics": metrics,
                "timestamp": time.time(),
                "report_id": f"health_{len(health_reports) + 1}"
            }
            health_reports.append(health_report)
        
        with patch('netra_backend.app.monitoring.health_reporter.report_health', side_effect=mock_report_agent_health):
            
            agent_state = DeepAgentState(
                agent_id="health_monitored_agent",
                session_id="health_session",
                thread_id="health_thread",
                context={"health_monitoring": True, "health_reporting_interval": 0.1}
            )
            
            agent = SupervisorAgent(
                agent_id="health_monitoring_test",
                initial_state=agent_state
            )
            
            # Simulate agent operations with health monitoring
            operation_sequence = [
                {"type": "normal_operation", "expected_health": "healthy"},
                {"type": "heavy_operation", "expected_health": "stressed"},
                {"type": "failing_operation", "expected_health": "unhealthy"},
                {"type": "recovery_operation", "expected_health": "recovering"},
                {"type": "normal_operation", "expected_health": "healthy"}
            ]
            
            for operation in operation_sequence:
                await agent._execute_health_monitored_operation(operation)
                await asyncio.sleep(0.12)  # Allow health reporting interval
            
            # Verify health reports were generated
            assert len(health_reports) >= len(operation_sequence)
            
            # Check health status progression
            health_statuses = [report["health_status"] for report in health_reports]
            assert "healthy" in health_statuses
            assert "stressed" in health_statuses or "unhealthy" in health_statuses
            
            # Verify health metrics completeness
            for report in health_reports:
                assert "metrics" in report
                metrics = report["metrics"]
                
                # Check for key health metrics
                expected_health_metrics = ["response_time", "error_rate", "resource_usage", "queue_depth"]
                for metric in expected_health_metrics:
                    assert metric in metrics
                    assert isinstance(metrics[metric], (int, float))
            
            # Check health trend analysis
            latest_report = health_reports[-1]
            assert latest_report["health_status"] in ["healthy", "recovering"]  # Should recover
            assert latest_report["agent_id"] == "health_monitored_agent"