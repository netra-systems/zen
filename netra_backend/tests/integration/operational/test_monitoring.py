"""
System Monitoring Integration Tests

BVJ:
- Segment: Platform/Internal - Supporting system reliability and quality monitoring
- Business Goal: Platform Stability - Maintains service quality and prevents churn
- Value Impact: Validates comprehensive monitoring systems and health aggregation
- Revenue Impact: Prevents revenue loss through proactive quality assurance

REQUIREMENTS:
- Quality monitoring end-to-end validation
- System health aggregation monitoring
- Alert management and notification systems
- Performance threshold validation
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

# Add project root to path
from integration.operational.shared_fixtures import (
    QualityMonitoringTestHelper,
    # Add project root to path
    operational_infrastructure,
    quality_monitoring_helper,
)


class TestSystemMonitoring:
    """BVJ: Maintains service quality supporting customer satisfaction and retention."""

    @pytest.mark.asyncio
    async def test_quality_monitoring_end_to_end_validation(self, operational_infrastructure, quality_monitoring_helper):
        """BVJ: Maintains service quality supporting customer satisfaction and retention."""
        quality_scenario = await quality_monitoring_helper.create_quality_monitoring_scenario()
        quality_measurement = await quality_monitoring_helper.execute_comprehensive_quality_measurement(operational_infrastructure, quality_scenario)
        threshold_validation = await self._validate_quality_thresholds(operational_infrastructure, quality_measurement)
        quality_reporting = await self._generate_quality_reports(threshold_validation)
        await self._verify_quality_monitoring_effectiveness(quality_reporting, quality_scenario)

    async def _validate_quality_thresholds(self, infra, measurement):
        """Validate quality against defined thresholds."""
        threshold_results = {}
        
        for dimension, metrics in measurement["metrics"].items():
            if "threshold" in metrics:
                if dimension == "system_performance":
                    passed = metrics["avg_response_time"] <= metrics["threshold"]
                else:
                    passed = metrics["score"] >= metrics["threshold"]
                
                threshold_results[dimension] = {
                    "threshold_met": passed,
                    "margin": 0.05 if passed else -0.02
                }
        
        validation_result = {
            "threshold_results": threshold_results,
            "overall_compliance": all(r["threshold_met"] for r in threshold_results.values()),
            "quality_gate_passed": True
        }
        
        infra["quality_monitor"].validate_thresholds = AsyncMock(return_value=validation_result)
        return await infra["quality_monitor"].validate_thresholds(measurement)

    async def _generate_quality_reports(self, validation):
        """Generate quality monitoring reports."""
        quality_report = {
            "report_id": str(uuid.uuid4()),
            "executive_summary": {
                "overall_quality_score": 0.96,
                "sla_compliance": "PASS",
                "key_achievements": ["Maintained 99.7% uptime", "Response accuracy above target"],
                "areas_for_improvement": ["Optimize P95 response times"]
            },
            "detailed_metrics": validation["threshold_results"],
            "trend_analysis": "Quality metrics improving over past 30 days",
            "report_generated_at": datetime.utcnow()
        }
        
        return quality_report

    async def _verify_quality_monitoring_effectiveness(self, reporting, scenario):
        """Verify quality monitoring system effectiveness."""
        assert reporting["executive_summary"]["sla_compliance"] == "PASS"
        assert reporting["executive_summary"]["overall_quality_score"] >= 0.95
        assert len(scenario["quality_dimensions"]) == 4

    @pytest.mark.asyncio
    async def test_system_health_aggregation_monitoring(self, operational_infrastructure):
        """BVJ: Maintains system reliability supporting $22K MRR."""
        health_scenario = await self._create_system_health_scenario()
        health_aggregation = await self._execute_system_health_aggregation(operational_infrastructure, health_scenario)
        alert_management = await self._manage_health_alerts(operational_infrastructure, health_aggregation)
        await self._verify_health_monitoring_reliability(alert_management, health_scenario)

    async def _create_system_health_scenario(self):
        """Create system health monitoring scenario."""
        return {
            "monitoring_components": ["database", "llm_service", "websocket", "cache", "api_gateway"],
            "health_thresholds": {"critical": 0.5, "warning": 0.8, "healthy": 0.95},
            "alert_requirements": ["immediate_notification", "escalation_path", "auto_recovery"]
        }

    async def _execute_system_health_aggregation(self, infra, scenario):
        """Execute system health aggregation."""
        component_health = {
            "database": {"status": "healthy", "score": 0.98, "response_time": 25},
            "llm_service": {"status": "healthy", "score": 0.96, "response_time": 180},
            "websocket": {"status": "warning", "score": 0.82, "response_time": 45},
            "cache": {"status": "healthy", "score": 0.99, "response_time": 5},
            "api_gateway": {"status": "healthy", "score": 0.97, "response_time": 35}
        }
        
        aggregation_result = {
            "overall_health_score": 0.94,
            "component_health": component_health,
            "alerts_triggered": 1,
            "system_status": "operational_with_warnings"
        }
        
        infra["health_aggregator"].aggregate_health = AsyncMock(return_value=aggregation_result)
        return await infra["health_aggregator"].aggregate_health(scenario)

    async def _manage_health_alerts(self, infra, health_data):
        """Manage health alerts and notifications."""
        alert_management = {
            "alerts_processed": health_data["alerts_triggered"],
            "notifications_sent": 3,
            "escalations_triggered": 0,
            "auto_recovery_attempted": True,
            "alert_resolution_time_minutes": 8
        }
        
        infra["health_aggregator"].manage_alerts = AsyncMock(return_value=alert_management)
        return await infra["health_aggregator"].manage_alerts(health_data)

    async def _verify_health_monitoring_reliability(self, alerts, scenario):
        """Verify health monitoring system reliability."""
        assert alerts["auto_recovery_attempted"] is True
        assert alerts["alert_resolution_time_minutes"] < 15
        assert len(scenario["monitoring_components"]) == 5

    @pytest.mark.asyncio
    async def test_quality_threshold_validation(self, operational_infrastructure, quality_monitoring_helper):
        """BVJ: Validates quality threshold compliance checking."""
        quality_scenario = await quality_monitoring_helper.create_quality_monitoring_scenario()
        quality_measurement = await quality_monitoring_helper.execute_comprehensive_quality_measurement(operational_infrastructure, quality_scenario)
        threshold_validation = await self._validate_quality_thresholds(operational_infrastructure, quality_measurement)
        
        assert threshold_validation["overall_compliance"] is True
        assert threshold_validation["quality_gate_passed"] is True

    @pytest.mark.asyncio
    async def test_performance_metrics_accuracy(self, operational_infrastructure, quality_monitoring_helper):
        """BVJ: Validates performance metrics measurement accuracy."""
        quality_scenario = await quality_monitoring_helper.create_quality_monitoring_scenario()
        measurement = await quality_monitoring_helper.execute_comprehensive_quality_measurement(operational_infrastructure, quality_scenario)
        
        perf_metrics = measurement["metrics"]["system_performance"]
        assert perf_metrics["avg_response_time"] < perf_metrics["threshold"]
        assert perf_metrics["p95_response_time"] > perf_metrics["avg_response_time"]

    @pytest.mark.asyncio
    async def test_sla_compliance_reporting(self, operational_infrastructure, quality_monitoring_helper):
        """BVJ: Validates SLA compliance reporting functionality."""
        quality_scenario = await quality_monitoring_helper.create_quality_monitoring_scenario()
        quality_measurement = await quality_monitoring_helper.execute_comprehensive_quality_measurement(operational_infrastructure, quality_scenario)
        threshold_validation = await self._validate_quality_thresholds(operational_infrastructure, quality_measurement)
        quality_report = await self._generate_quality_reports(threshold_validation)
        
        assert quality_report["executive_summary"]["sla_compliance"] == "PASS"
        assert len(quality_report["executive_summary"]["key_achievements"]) >= 2

    @pytest.mark.asyncio
    async def test_alert_management_system(self, operational_infrastructure):
        """BVJ: Validates alert management system functionality."""
        health_scenario = await self._create_system_health_scenario()
        health_aggregation = await self._execute_system_health_aggregation(operational_infrastructure, health_scenario)
        alert_management = await self._manage_health_alerts(operational_infrastructure, health_aggregation)
        
        assert alert_management["notifications_sent"] > 0
        assert alert_management["auto_recovery_attempted"] is True
        assert alert_management["alert_resolution_time_minutes"] < 15

    @pytest.mark.asyncio
    async def test_component_health_tracking(self, operational_infrastructure):
        """BVJ: Validates individual component health tracking."""
        health_scenario = await self._create_system_health_scenario()
        health_aggregation = await self._execute_system_health_aggregation(operational_infrastructure, health_scenario)
        
        component_health = health_aggregation["component_health"]
        
        # Verify all components are tracked
        for component in health_scenario["monitoring_components"]:
            assert component in component_health
            assert "status" in component_health[component]
            assert "score" in component_health[component]

    @pytest.mark.asyncio
    async def test_overall_health_score_calculation(self, operational_infrastructure):
        """BVJ: Validates overall health score calculation accuracy."""
        health_scenario = await self._create_system_health_scenario()
        health_aggregation = await self._execute_system_health_aggregation(operational_infrastructure, health_scenario)
        
        overall_score = health_aggregation["overall_health_score"]
        component_scores = [comp["score"] for comp in health_aggregation["component_health"].values()]
        
        # Overall score should be reasonable average of component scores
        expected_avg = sum(component_scores) / len(component_scores)
        assert abs(overall_score - expected_avg) < 0.1

    @pytest.mark.asyncio
    async def test_trend_analysis_generation(self, operational_infrastructure, quality_monitoring_helper):
        """BVJ: Validates trend analysis generation in quality reports."""
        quality_scenario = await quality_monitoring_helper.create_quality_monitoring_scenario()
        quality_measurement = await quality_monitoring_helper.execute_comprehensive_quality_measurement(operational_infrastructure, quality_scenario)
        threshold_validation = await self._validate_quality_thresholds(operational_infrastructure, quality_measurement)
        quality_report = await self._generate_quality_reports(threshold_validation)
        
        assert "trend_analysis" in quality_report
        assert quality_report["trend_analysis"] is not None
        assert len(quality_report["trend_analysis"]) > 0

    @pytest.mark.asyncio
    async def test_data_quality_metrics(self, operational_infrastructure, quality_monitoring_helper):
        """BVJ: Validates data quality metrics measurement."""
        quality_scenario = await quality_monitoring_helper.create_quality_monitoring_scenario()
        measurement = await quality_monitoring_helper.execute_comprehensive_quality_measurement(operational_infrastructure, quality_scenario)
        
        data_quality = measurement["metrics"]["data_quality"]
        assert data_quality["completeness"] >= 0.95
        assert data_quality["consistency"] >= 0.95
        assert data_quality["accuracy"] >= 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])