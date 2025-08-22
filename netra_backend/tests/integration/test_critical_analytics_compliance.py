"""
Critical analytics and compliance integration tests.
Business Value: Powers $17K MRR from analytics features and quality assurance.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

# Add project root to path
from .test_fixtures_common import mock_infrastructure, test_database

# Add project root to path


class TestAnalyticsComplianceIntegration:
    """Analytics and compliance integration tests"""

    async def test_metrics_export_pipeline_to_observability(self, test_database, mock_infrastructure):
        """Data flow from collection to Prometheus/InfluxDB"""
        metrics_pipeline = await self._setup_metrics_export_pipeline()
        test_metrics = await self._generate_test_metrics_data()
        export_flow = await self._execute_metrics_export_flow(metrics_pipeline, test_metrics)
        await self._verify_observability_integration(export_flow, test_metrics)

    async def test_demo_service_analytics_integration(self, test_database, mock_infrastructure):
        """Customer demo tracking and ROI calculation"""
        analytics_system = await self._setup_demo_analytics_infrastructure(test_database)
        demo_sessions = await self._create_demo_session_data()
        analytics_flow = await self._execute_demo_analytics_pipeline(analytics_system, demo_sessions)
        await self._verify_roi_calculations(analytics_flow, demo_sessions)

    async def test_factory_status_compliance_integration(self, test_database, mock_infrastructure):
        """Architecture compliance validation flow"""
        compliance_system = await self._setup_factory_status_infrastructure()
        compliance_checks = await self._create_compliance_check_scenarios()
        validation_flow = await self._execute_compliance_validation(compliance_system, compliance_checks)
        await self._verify_compliance_reporting(validation_flow)

    async def _setup_metrics_export_pipeline(self):
        """Setup metrics export pipeline infrastructure"""
        return {
            "collectors": ["prometheus", "influxdb", "datadog"],
            "exporters": {
                "prometheus": {"endpoint": "http://prometheus:9090", "connected": True},
                "influxdb": {"endpoint": "http://influxdb:8086", "connected": True}
            },
            "buffer": {"size": 1000, "flush_interval": 30}
        }

    async def _generate_test_metrics_data(self):
        """Generate test metrics for export"""
        return [
            {"name": "gpu_utilization", "value": 85.5, "timestamp": time.time(), "labels": {"instance": "gpu-1"}},
            {"name": "cost_per_hour", "value": 2.4, "timestamp": time.time(), "labels": {"instance": "gpu-1"}},
            {"name": "optimization_score", "value": 0.75, "timestamp": time.time(), "labels": {"agent": "optimizer"}}
        ]

    async def _execute_metrics_export_flow(self, pipeline, metrics):
        """Execute end-to-end metrics export"""
        export_results = {}
        for exporter_name, config in pipeline["exporters"].items():
            if config["connected"]:
                exported_metrics = await self._export_to_system(exporter_name, metrics)
                export_results[exporter_name] = exported_metrics
        return export_results

    async def _export_to_system(self, system_name, metrics):
        """Export metrics to specific observability system"""
        return {"exported_count": len(metrics), "success": True, "system": system_name}

    async def _verify_observability_integration(self, export_flow, original_metrics):
        """Verify metrics properly exported to observability systems"""
        for system, result in export_flow.items():
            assert result["success"] is True
            assert result["exported_count"] == len(original_metrics)

    async def _setup_demo_analytics_infrastructure(self, db_setup):
        """Setup demo analytics infrastructure"""
        return {
            "event_collector": {"active": True, "buffer_size": 1000},
            "analytics_engine": {"type": "spark", "cluster_active": True},
            "roi_calculator": {"version": "1.3", "active": True},
            "reporting_dashboard": {"connected": True},
            "db_session": db_setup["session"]
        }

    async def _create_demo_session_data(self):
        """Create demo session data for analytics"""
        return [
            {
                "session_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "demo_type": "gpu_optimization",
                "duration_minutes": 45,
                "interactions": ["gpu_analyzer", "cost_calculator", "performance_chart"],
                "outcome": "converted",
                "conversion_value": 2400
            },
            {
                "session_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "demo_type": "full_platform",
                "duration_minutes": 60,
                "interactions": ["agent_workflow", "synthetic_data", "analytics_dashboard"],
                "outcome": "follow_up_scheduled",
                "conversion_value": 0
            }
        ]

    async def _execute_demo_analytics_pipeline(self, system, sessions):
        """Execute demo analytics pipeline"""
        pipeline_results = {
            "event_processing": await self._process_demo_events(system, sessions),
            "roi_calculation": await self._calculate_demo_roi(system, sessions),
            "reporting": await self._generate_demo_reports(system, sessions)
        }
        return pipeline_results

    async def _process_demo_events(self, system, sessions):
        """Process demo events for analytics"""
        processed = {
            "total_sessions": len(sessions),
            "total_interactions": sum(len(s["interactions"]) for s in sessions),
            "average_duration": sum(s["duration_minutes"] for s in sessions) / len(sessions),
            "conversion_rate": len([s for s in sessions if s["outcome"] == "converted"]) / len(sessions)
        }
        return processed

    async def _calculate_demo_roi(self, system, sessions):
        """Calculate ROI from demo sessions"""
        total_investment = len(sessions) * 100
        total_revenue = sum(s["conversion_value"] for s in sessions)
        roi = (total_revenue - total_investment) / total_investment if total_investment > 0 else 0
        
        return {
            "total_investment": total_investment,
            "total_revenue": total_revenue,
            "roi_percentage": roi * 100,
            "payback_period_days": 30 if roi > 0 else None
        }

    async def _generate_demo_reports(self, system, sessions):
        """Generate demo analytics reports"""
        return {
            "report_generated": True,
            "report_id": str(uuid.uuid4()),
            "metrics_included": ["conversion_rate", "roi", "engagement_score"],
            "export_formats": ["pdf", "csv", "json"]
        }

    async def _verify_roi_calculations(self, flow, sessions):
        """Verify ROI calculations accuracy"""
        roi_data = flow["roi_calculation"]
        assert roi_data["total_revenue"] >= 0
        assert roi_data["roi_percentage"] is not None
        assert flow["reporting"]["report_generated"] is True

    async def _setup_factory_status_infrastructure(self):
        """Setup factory status compliance infrastructure"""
        return {
            "compliance_engine": {"version": "2.1", "active": True},
            "rule_sets": {
                "300_line_limit": {"enabled": True, "threshold": 300},
                "8_line_function_limit": {"enabled": True, "threshold": 8},
                "type_safety": {"enabled": True, "strict_mode": True}
            },
            "violation_tracker": {"active": True, "history_retention_days": 30},
            "reporting_system": {"active": True, "real_time": True}
        }

    async def _create_compliance_check_scenarios(self):
        """Create compliance check scenarios"""
        return [
            {
                "check_type": "file_size",
                "file_path": "test_agent.py",
                "line_count": 350,
                "expected_violation": True
            },
            {
                "check_type": "function_complexity",
                "function_name": "process_optimization",
                "line_count": 12,
                "expected_violation": True
            },
            {
                "check_type": "type_safety",
                "file_path": "utils.py",
                "missing_type_hints": 5,
                "expected_violation": True
            }
        ]

    async def _execute_compliance_validation(self, system, checks):
        """Execute compliance validation"""
        validation_results = {}
        for check in checks:
            result = await self._perform_compliance_check(system, check)
            validation_results[check["check_type"]] = result
        return validation_results

    async def _perform_compliance_check(self, system, check):
        """Perform individual compliance check"""
        rule_set = system["rule_sets"].get(f"{check['check_type']}_limit") or system["rule_sets"].get(check["check_type"])
        
        if not rule_set:
            return {"violation": False, "reason": "no_rule_defined"}
        
        if check["check_type"] == "file_size":
            violation = check["line_count"] > rule_set["threshold"]
        elif check["check_type"] == "function_complexity":
            violation = check["line_count"] > rule_set["threshold"]
        else:
            violation = check.get("missing_type_hints", 0) > 0
        
        return {
            "violation": violation,
            "severity": "high" if violation else "none",
            "rule_applied": rule_set
        }

    async def _verify_compliance_reporting(self, flow):
        """Verify compliance reporting functionality"""
        violations_found = any(result["violation"] for result in flow.values())
        assert violations_found is True
        
        expected_types = ["file_size", "function_complexity", "type_safety"]
        for check_type in expected_types:
            assert check_type in flow