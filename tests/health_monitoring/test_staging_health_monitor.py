"""
Comprehensive Test Suite for Staging Health Monitor

Tests all health monitoring components including WebSocket, database,
service monitoring, performance metrics, and business impact analysis.
"""

import asyncio
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from netra_backend.app.monitoring.staging_health_monitor import (
    StagingHealthMonitor,
    WebSocketHealthChecker,
    ResourceHealthChecker,
    ConfigurationHealthChecker,
    PerformanceMetricsChecker
)
from netra_backend.app.core.health_types import HealthCheckResult


class TestWebSocketHealthChecker:
    """Test WebSocket health monitoring functionality."""
    
    @pytest.fixture
    def websocket_checker(self):
        """Create WebSocket health checker instance."""
        return WebSocketHealthChecker()
    
    @pytest.mark.asyncio
    async def test_websocket_health_check_success(self, websocket_checker):
        """Test successful WebSocket health check."""
        # Mock successful WebSocket checks
        with patch.object(websocket_checker, '_check_websocket_server', return_value=True), \
             patch.object(websocket_checker, '_check_event_transmission', return_value=True), \
             patch.object(websocket_checker, '_check_event_pipeline', return_value=True):
            
            result = await websocket_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is True
            assert result.health_score == 1.0
            assert result.status == "healthy"
            assert "websocket_server_available" in result.details
            assert result.details["websocket_server_available"] is True
    
    @pytest.mark.asyncio
    async def test_websocket_health_check_partial_failure(self, websocket_checker):
        """Test WebSocket health check with partial failures."""
        # Mock partial WebSocket failure
        with patch.object(websocket_checker, '_check_websocket_server', return_value=True), \
             patch.object(websocket_checker, '_check_event_transmission', return_value=False), \
             patch.object(websocket_checker, '_check_event_pipeline', return_value=True):
            
            result = await websocket_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is False
            assert result.health_score == 2/3  # 2 out of 3 components working
            assert result.status == "unhealthy"
            assert result.details["event_transmission_working"] is False
    
    @pytest.mark.asyncio
    async def test_websocket_health_check_complete_failure(self, websocket_checker):
        """Test WebSocket health check with complete failure."""
        # Mock complete WebSocket failure
        with patch.object(websocket_checker, '_check_websocket_server', return_value=False), \
             patch.object(websocket_checker, '_check_event_transmission', return_value=False), \
             patch.object(websocket_checker, '_check_event_pipeline', return_value=False):
            
            result = await websocket_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is False
            assert result.health_score == 0.0
            assert result.status == "unhealthy"
            assert all(not result.details[key] for key in [
                "websocket_server_available",
                "event_transmission_working", 
                "event_pipeline_functional"
            ])
    
    @pytest.mark.asyncio
    async def test_websocket_health_check_exception_handling(self, websocket_checker):
        """Test WebSocket health check exception handling."""
        # Mock exception in WebSocket check
        with patch.object(websocket_checker, '_check_websocket_server', side_effect=Exception("Connection failed")):
            
            result = await websocket_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is False
            assert result.health_score == 0.0
            assert result.status == "unhealthy"
            assert "Connection failed" in result.details["error_message"]
    
    def test_websocket_health_score_calculation(self, websocket_checker):
        """Test WebSocket health score calculation."""
        # Test all components working
        score = websocket_checker._calculate_websocket_health_score(True, True, True)
        assert score == 1.0
        
        # Test partial working
        score = websocket_checker._calculate_websocket_health_score(True, False, True)
        assert score == 2/3
        
        # Test none working
        score = websocket_checker._calculate_websocket_health_score(False, False, False)
        assert score == 0.0


class TestResourceHealthChecker:
    """Test system resource monitoring functionality."""
    
    @pytest.fixture
    def resource_checker(self):
        """Create resource health checker instance."""
        return ResourceHealthChecker()
    
    @pytest.mark.asyncio
    async def test_resource_health_check_success(self, resource_checker):
        """Test successful resource health check."""
        # Mock healthy resource usage
        with patch.object(resource_checker, '_get_cpu_usage', return_value=50.0), \
             patch.object(resource_checker, '_get_memory_usage', return_value=60.0), \
             patch.object(resource_checker, '_get_disk_usage', return_value=70.0), \
             patch.object(resource_checker, '_get_connection_count', return_value=100):
            
            result = await resource_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is True
            assert result.status == "healthy"
            assert result.details["cpu_usage_percent"] == 50.0
            assert result.details["memory_usage_percent"] == 60.0
            assert result.details["disk_usage_percent"] == 70.0
            assert result.details["active_connections"] == 100
    
    @pytest.mark.asyncio
    async def test_resource_health_check_high_usage(self, resource_checker):
        """Test resource health check with high usage."""
        # Mock high resource usage
        with patch.object(resource_checker, '_get_cpu_usage', return_value=90.0), \
             patch.object(resource_checker, '_get_memory_usage', return_value=95.0), \
             patch.object(resource_checker, '_get_disk_usage', return_value=88.0), \
             patch.object(resource_checker, '_get_connection_count', return_value=1200):
            
            result = await resource_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is False
            assert result.status == "degraded"
            assert result.details["status_details"]["cpu_healthy"] is False
            assert result.details["status_details"]["memory_healthy"] is False
    
    def test_resource_health_score_calculation(self, resource_checker):
        """Test resource health score calculation."""
        # Test healthy resources
        score = resource_checker._calculate_resource_health_score(30, 40, 50, 100)
        assert score > 0.8  # Should be high score for low usage
        
        # Test unhealthy resources
        score = resource_checker._calculate_resource_health_score(95, 90, 95, 1200)
        assert score < 0.2  # Should be low score for high usage


class TestConfigurationHealthChecker:
    """Test configuration consistency monitoring."""
    
    @pytest.fixture
    def config_checker(self):
        """Create configuration health checker instance."""
        return ConfigurationHealthChecker()
    
    @pytest.mark.asyncio
    async def test_configuration_health_check_success(self, config_checker):
        """Test successful configuration health check."""
        # Mock valid configuration checks
        with patch.object(config_checker, '_check_database_configuration', return_value=True), \
             patch.object(config_checker, '_check_auth_configuration', return_value=True), \
             patch.object(config_checker, '_check_websocket_configuration', return_value=True), \
             patch.object(config_checker, '_check_environment_configuration', return_value=True):
            
            result = await config_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is True
            assert result.health_score == 1.0
            assert result.status == "healthy"
            assert all(result.details["configuration_status"].values())
    
    @pytest.mark.asyncio
    async def test_configuration_health_check_partial_failure(self, config_checker):
        """Test configuration health check with partial failure."""
        # Mock partial configuration failure
        with patch.object(config_checker, '_check_database_configuration', return_value=True), \
             patch.object(config_checker, '_check_auth_configuration', return_value=False), \
             patch.object(config_checker, '_check_websocket_configuration', return_value=True), \
             patch.object(config_checker, '_check_environment_configuration', return_value=True):
            
            result = await config_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is False
            assert result.health_score == 0.75  # 3 out of 4 configs valid
            assert result.status == "degraded"
            assert result.details["configuration_status"]["auth_config_valid"] is False
    
    @pytest.mark.asyncio
    async def test_database_configuration_check(self, config_checker):
        """Test database configuration validation."""
        # Test valid database configuration
        with patch('netra_backend.app.monitoring.staging_health_monitor.get_env') as mock_env:
            mock_env.return_value.get.return_value = "postgresql://user:pass@host:5432/db"
            
            result = await config_checker._check_database_configuration()
            assert result is True
        
        # Test missing database configuration
        with patch('netra_backend.app.monitoring.staging_health_monitor.get_env') as mock_env:
            mock_env.return_value.get.return_value = None
            
            result = await config_checker._check_database_configuration()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_auth_configuration_check(self, config_checker):
        """Test authentication configuration validation."""
        # Test valid auth configuration
        with patch('netra_backend.app.monitoring.staging_health_monitor.get_env') as mock_env:
            mock_env.return_value.get.return_value = "valid-secret-key-that-is-long-enough"
            
            result = await config_checker._check_auth_configuration()
            assert result is True
        
        # Test missing auth configuration
        with patch('netra_backend.app.monitoring.staging_health_monitor.get_env') as mock_env:
            mock_env.return_value.get.return_value = ""
            
            result = await config_checker._check_auth_configuration()
            assert result is False


class TestPerformanceMetricsChecker:
    """Test performance metrics monitoring."""
    
    @pytest.fixture
    def performance_checker(self):
        """Create performance metrics checker instance."""
        return PerformanceMetricsChecker()
    
    @pytest.mark.asyncio
    async def test_performance_metrics_check_success(self, performance_checker):
        """Test successful performance metrics check."""
        # Mock good performance metrics
        with patch.object(performance_checker, '_measure_api_response_time', return_value=200.0), \
             patch.object(performance_checker, '_measure_websocket_latency', return_value=50.0), \
             patch.object(performance_checker, '_measure_database_query_time', return_value=30.0):
            
            result = await performance_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is True
            assert result.status == "healthy"
            assert result.details["performance_metrics"]["api_response_time_ms"] == 200.0
            assert result.details["performance_status"]["api_performance_good"] is True
    
    @pytest.mark.asyncio
    async def test_performance_metrics_check_degraded(self, performance_checker):
        """Test performance metrics check with degraded performance."""
        # Mock degraded performance metrics
        with patch.object(performance_checker, '_measure_api_response_time', return_value=800.0), \
             patch.object(performance_checker, '_measure_websocket_latency', return_value=150.0), \
             patch.object(performance_checker, '_measure_database_query_time', return_value=80.0):
            
            result = await performance_checker.check_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.success is False
            assert result.status == "degraded"
            assert result.details["performance_status"]["api_performance_good"] is False
            assert result.details["performance_status"]["websocket_performance_good"] is False
    
    def test_performance_score_calculation(self, performance_checker):
        """Test performance score calculation."""
        # Test good performance
        score = performance_checker._calculate_performance_score(200, 50, 30)
        assert score > 0.8
        
        # Test poor performance
        score = performance_checker._calculate_performance_score(1000, 200, 100)
        assert score < 0.2
    
    def test_performance_trend_analysis(self, performance_checker):
        """Test performance trend analysis functionality."""
        # Add some sample metrics to history
        sample_metrics = [
            {"api_response_time": 200, "websocket_latency": 50, "database_query_time": 30, "timestamp": time.time() - 300},
            {"api_response_time": 220, "websocket_latency": 55, "database_query_time": 32, "timestamp": time.time() - 240},
            {"api_response_time": 250, "websocket_latency": 60, "database_query_time": 35, "timestamp": time.time() - 180},
            {"api_response_time": 280, "websocket_latency": 65, "database_query_time": 38, "timestamp": time.time() - 120},
            {"api_response_time": 300, "websocket_latency": 70, "database_query_time": 40, "timestamp": time.time() - 60}
        ]
        
        for metric in sample_metrics:
            performance_checker._update_metrics_history(metric)
        
        # Analyze trends
        trend_analysis = performance_checker._analyze_performance_trends()
        
        assert trend_analysis["status"] == "trend_analysis_available"
        assert "recent_averages" in trend_analysis
        assert "historical_averages" in trend_analysis


class TestStagingHealthMonitor:
    """Test the comprehensive staging health monitor."""
    
    @pytest.fixture
    def health_monitor(self):
        """Create staging health monitor instance."""
        return StagingHealthMonitor()
    
    @pytest.mark.asyncio
    async def test_comprehensive_health_check(self, health_monitor):
        """Test comprehensive health status retrieval."""
        # Mock the health interface
        mock_health_status = {
            "status": "healthy",
            "service": "staging_environment",
            "version": "1.0.0",
            "timestamp": time.time(),
            "checks": {
                "staging_websocket": {
                    "success": True,
                    "health_score": 1.0,
                    "response_time_ms": 50.0
                },
                "database_postgres": {
                    "success": True,
                    "health_score": 0.95,
                    "response_time_ms": 25.0
                }
            }
        }
        
        with patch.object(health_monitor.health_interface, 'get_health_status', return_value=mock_health_status):
            result = await health_monitor.get_comprehensive_health()
            
            assert result["status"] == "healthy"
            assert "staging_analysis" in result
            assert "alert_status" in result
            assert result["service"] == "staging_environment"
    
    @pytest.mark.asyncio
    async def test_critical_health_check(self, health_monitor):
        """Test critical components health check."""
        mock_critical_status = {
            "status": "degraded",
            "service": "staging_environment_critical",
            "timestamp": time.time(),
            "checks": {
                "staging_websocket": {
                    "success": True,
                    "health_score": 1.0
                },
                "database_postgres": {
                    "success": False,
                    "health_score": 0.3
                }
            }
        }
        
        with patch.object(health_monitor.health_interface, 'get_health_status', return_value=mock_critical_status):
            result = await health_monitor.get_critical_health()
            
            assert result["status"] == "degraded"
            assert result["focus"] == "critical_components_only"
    
    def test_business_impact_analysis(self, health_monitor):
        """Test business impact analysis."""
        # Test no impact scenario
        checks = {
            "staging_websocket": {"success": True},
            "service_auth_service": {"success": True},
            "database_postgres": {"success": True}
        }
        
        chat_impact = health_monitor._is_chat_functionality_impacted(checks)
        auth_impact = health_monitor._is_auth_functionality_impacted(checks)
        data_impact = health_monitor._is_data_persistence_impacted(checks)
        
        assert chat_impact is False
        assert auth_impact is False  
        assert data_impact is False
        
        # Test critical impact scenario
        checks_critical = {
            "staging_websocket": {"success": False},
            "service_auth_service": {"success": False},
            "database_postgres": {"success": False}
        }
        
        chat_impact = health_monitor._is_chat_functionality_impacted(checks_critical)
        auth_impact = health_monitor._is_auth_functionality_impacted(checks_critical)
        data_impact = health_monitor._is_data_persistence_impacted(checks_critical)
        
        assert chat_impact is True
        assert auth_impact is True
        assert data_impact is True
    
    def test_user_impact_estimation(self, health_monitor):
        """Test user impact percentage estimation."""
        # No impact
        impact = health_monitor._estimate_user_impact_percentage(False, False, False)
        assert impact == 0
        
        # Auth impact (all users affected)
        impact = health_monitor._estimate_user_impact_percentage(False, True, False)
        assert impact == 100
        
        # Chat impact (most users affected)
        impact = health_monitor._estimate_user_impact_percentage(True, False, False)
        assert impact == 90
        
        # Data impact (some users affected)
        impact = health_monitor._estimate_user_impact_percentage(False, False, True)
        assert impact == 30
    
    def test_failure_prediction(self, health_monitor):
        """Test failure prediction functionality."""
        health_status = {
            "checks": {
                "component_1": {"health_score": 0.9, "success": True},
                "component_2": {"health_score": 0.4, "success": False},
                "component_3": {"health_score": 0.3, "success": False}
            }
        }
        
        prediction = health_monitor._predict_potential_failures(health_status)
        
        assert prediction["failure_prediction_available"] is True
        assert len(prediction["potential_failures"]) == 2  # Two components below 0.8
        assert prediction["overall_risk_level"] == "high"  # Multiple high risk components
    
    def test_remediation_suggestions(self, health_monitor):
        """Test automated remediation suggestions."""
        # Test WebSocket component failure
        suggestions = health_monitor._get_component_remediation_suggestions(
            "staging_websocket", {"success": False, "error": "Connection failed"}
        )
        
        assert len(suggestions) > 0
        assert any("websocket" in s["action"].lower() for s in suggestions)
        assert any(s["urgency"] == "high" for s in suggestions)
        
        # Test database component failure
        suggestions = health_monitor._get_component_remediation_suggestions(
            "database_postgres", {"success": False, "error": "Connection timeout"}
        )
        
        assert len(suggestions) > 0
        assert any("database" in s["action"].lower() for s in suggestions)
        assert any(s["urgency"] == "critical" for s in suggestions)
    
    def test_alert_conditions_checking(self, health_monitor):
        """Test alert conditions checking."""
        # Test overall health degradation
        health_status = {
            "status": "degraded",
            "checks": {
                "component_1": {"success": False, "health_score": 0.4},
                "component_2": {"success": False, "health_score": 0.3},
                "component_3": {"success": True, "health_score": 0.9}
            }
        }
        
        alert_status = health_monitor._check_alert_conditions(health_status)
        
        assert alert_status["alerts_active"] is True
        assert alert_status["alert_count"] > 0
        assert alert_status["alert_severity"] in ["warning", "critical"]
    
    def test_health_trends_analysis(self, health_monitor):
        """Test health trends analysis."""
        # Add sample health history
        sample_history = [
            {"overall_health_score": 0.9, "failed_components": 0, "timestamp": time.time() - 600},
            {"overall_health_score": 0.85, "failed_components": 1, "timestamp": time.time() - 480},
            {"overall_health_score": 0.8, "failed_components": 1, "timestamp": time.time() - 360},
            {"overall_health_score": 0.75, "failed_components": 2, "timestamp": time.time() - 240},
            {"overall_health_score": 0.7, "failed_components": 2, "timestamp": time.time() - 120}
        ]
        
        health_monitor.health_history.extend(sample_history)
        
        trend_analysis = health_monitor._analyze_health_trends()
        
        assert trend_analysis["status"] == "trend_analysis_available"
        assert trend_analysis["overall_trend"] == "degrading"  # Health is declining
        assert "stability_score" in trend_analysis
    
    def test_stability_score_calculation(self, health_monitor):
        """Test stability score calculation."""
        # Test stable system (low variance)
        stable_checks = [
            {"overall_health_score": 0.9},
            {"overall_health_score": 0.91},
            {"overall_health_score": 0.89},
            {"overall_health_score": 0.9},
            {"overall_health_score": 0.9}
        ]
        
        stability = health_monitor._calculate_stability_score(stable_checks)
        assert stability > 0.8  # High stability
        
        # Test unstable system (high variance)
        unstable_checks = [
            {"overall_health_score": 0.9},
            {"overall_health_score": 0.3},
            {"overall_health_score": 0.8},
            {"overall_health_score": 0.2},
            {"overall_health_score": 0.7}
        ]
        
        stability = health_monitor._calculate_stability_score(unstable_checks)
        assert stability < 0.5  # Low stability


class TestHealthMonitoringIntegration:
    """Integration tests for the complete health monitoring system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_health_monitoring(self):
        """Test end-to-end health monitoring workflow."""
        health_monitor = StagingHealthMonitor()
        
        # Mock all components as healthy
        with patch.object(health_monitor.health_interface, 'get_health_status') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "service": "staging_environment",
                "version": "1.0.0",
                "timestamp": time.time(),
                "checks": {
                    "staging_websocket": {
                        "success": True,
                        "health_score": 1.0,
                        "response_time_ms": 50.0
                    },
                    "database_postgres": {
                        "success": True,
                        "health_score": 0.95,
                        "response_time_ms": 25.0
                    },
                    "service_auth_service": {
                        "success": True,
                        "health_score": 0.98,
                        "response_time_ms": 100.0
                    }
                }
            }
            
            # Run comprehensive health check
            result = await health_monitor.get_comprehensive_health()
            
            # Verify comprehensive analysis
            assert result["status"] == "healthy"
            assert "staging_analysis" in result
            assert "business_impact" in result["staging_analysis"]
            assert "failure_prediction" in result["staging_analysis"]
            assert "remediation_suggestions" in result["staging_analysis"]
            assert "trend_analysis" in result["staging_analysis"]
            
            # Verify business impact analysis
            business_impact = result["staging_analysis"]["business_impact"]
            assert business_impact["impact_level"] == "none"
            assert business_impact["chat_functionality_impacted"] is False
            assert business_impact["user_authentication_impacted"] is False
            assert business_impact["data_persistence_impacted"] is False
            
            # Verify alert status
            alert_status = result["alert_status"]
            assert alert_status["alerts_active"] is False
            assert alert_status["alert_count"] == 0
    
    @pytest.mark.asyncio
    async def test_critical_failure_scenario(self):
        """Test health monitoring during critical failure scenario."""
        health_monitor = StagingHealthMonitor()
        
        # Mock critical failures
        with patch.object(health_monitor.health_interface, 'get_health_status') as mock_health:
            mock_health.return_value = {
                "status": "unhealthy",
                "service": "staging_environment",
                "version": "1.0.0",
                "timestamp": time.time(),
                "checks": {
                    "staging_websocket": {
                        "success": False,
                        "health_score": 0.0,
                        "response_time_ms": 999.0
                    },
                    "database_postgres": {
                        "success": False,
                        "health_score": 0.0,
                        "response_time_ms": 999.0
                    },
                    "service_auth_service": {
                        "success": False,
                        "health_score": 0.0,
                        "response_time_ms": 999.0
                    }
                }
            }
            
            # Run comprehensive health check
            result = await health_monitor.get_comprehensive_health()
            
            # Verify critical failure analysis
            assert result["status"] == "unhealthy"
            
            # Verify business impact analysis
            business_impact = result["staging_analysis"]["business_impact"]
            assert business_impact["impact_level"] == "critical"
            assert business_impact["estimated_user_impact_percent"] == 100
            
            # Verify failure prediction
            failure_prediction = result["staging_analysis"]["failure_prediction"]
            assert failure_prediction["failure_prediction_available"] is True
            assert failure_prediction["overall_risk_level"] == "high"
            
            # Verify remediation suggestions
            remediation = result["staging_analysis"]["remediation_suggestions"]
            assert len(remediation) > 0
            
            # Verify alert status
            alert_status = result["alert_status"]
            assert alert_status["alerts_active"] is True
            assert alert_status["alert_severity"] == "critical"
    
    def test_health_monitoring_performance(self):
        """Test health monitoring system performance."""
        health_monitor = StagingHealthMonitor()
        
        # Measure health check execution time
        start_time = time.time()
        
        # Simulate multiple health checks
        for _ in range(10):
            asyncio.run(self._mock_health_check(health_monitor))
        
        execution_time = time.time() - start_time
        
        # Verify performance is acceptable (should complete in reasonable time)
        assert execution_time < 5.0  # Should complete within 5 seconds
        
        # Verify memory efficiency (health history should be bounded)
        assert len(health_monitor.health_history) <= 1000
    
    async def _mock_health_check(self, health_monitor):
        """Mock health check for performance testing."""
        mock_result = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {"test_component": {"success": True, "health_score": 1.0}}
        }
        
        with patch.object(health_monitor.health_interface, 'get_health_status', return_value=mock_result):
            await health_monitor.get_comprehensive_health()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])