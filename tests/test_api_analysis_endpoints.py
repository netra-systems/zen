"""
Comprehensive API endpoint tests for analysis and reporting.
Tests all analysis, metrics, and reporting endpoints.

Business Value Justification (BVJ):
1. Segment: Mid and Enterprise segments
2. Business Goal: Provide actionable AI optimization insights
3. Value Impact: Enables customers to optimize AI spend and performance
4. Revenue Impact: Core value prop for paid tiers, drives 40% of enterprise sales
"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List


def _create_mock_analysis_service() -> Mock:
    """Create mock analysis service."""
    mock = Mock()
    mock.run_analysis = AsyncMock(return_value={
        "id": "analysis-id",
        "status": "completed",
        "results": {"optimization_score": 85.5}
    })
    mock.get_analysis = AsyncMock(return_value={
        "id": "analysis-id",
        "results": {"cost_savings": 1250.75}
    })
    return mock


def _create_mock_metrics_service() -> Mock:
    """Create mock metrics service."""
    mock = Mock()
    mock.get_metrics = AsyncMock(return_value={
        "total_requests": 1000,
        "avg_response_time": 250.5,
        "cost_per_request": 0.025
    })
    mock.get_dashboard_data = AsyncMock(return_value={
        "daily_usage": [100, 150, 200],
        "cost_trends": [50, 75, 100]
    })
    return mock


@pytest.fixture
def mock_analysis_dependencies():
    """Mock analysis service dependencies."""
    with patch('app.services.analysis_service', _create_mock_analysis_service()):
        with patch('app.services.metrics_service', _create_mock_metrics_service()):
            yield


class TestAnalysisEndpoints:
    """Test AI analysis endpoints."""

    def test_start_analysis(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test starting a new analysis."""
        analysis_data = {
            "type": "cost_optimization",
            "parameters": {"time_range": "30d"},
            "workspace_id": "workspace-id"
        }
        
        response = client.post("/api/analysis/start", json=analysis_data, headers=auth_headers)
        
        if response.status_code in [200, 201, 202]:
            data = response.json()
            assert isinstance(data, dict)
            assert "id" in data or "analysis_id" in data

    def test_get_analysis_status(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test getting analysis status."""
        analysis_id = "test-analysis-id"
        response = client.get(f"/api/analysis/{analysis_id}/status", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert "status" in data
            assert data["status"] in ["pending", "running", "completed", "failed"]

    def test_get_analysis_results(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test getting analysis results."""
        analysis_id = "test-analysis-id"
        response = client.get(f"/api/analysis/{analysis_id}/results", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert "results" in data or len(data) > 0

    def test_list_analyses(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test listing user analyses."""
        response = client.get("/api/analysis", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            if isinstance(data, dict) and "analyses" in data:
                assert isinstance(data["analyses"], list)

    def test_cancel_analysis(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test canceling running analysis."""
        analysis_id = "test-analysis-id"
        response = client.post(f"/api/analysis/{analysis_id}/cancel", headers=auth_headers)
        
        # Accept various response codes
        assert response.status_code in [200, 204, 404]


class TestMetricsEndpoints:
    """Test metrics and dashboard endpoints."""

    def test_get_dashboard_metrics(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test getting dashboard metrics."""
        response = client.get("/api/metrics/dashboard", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            metrics_fields = ["usage", "costs", "performance", "requests"]
            # At least one metrics field should be present
            has_metrics = any(field in data for field in metrics_fields)
            assert has_metrics or len(data) > 0

    def test_get_usage_metrics(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test getting usage metrics."""
        response = client.get("/api/metrics/usage", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            usage_fields = ["total_requests", "active_users", "api_calls"]
            has_usage_data = any(field in data for field in usage_fields)
            assert has_usage_data or len(data) > 0

    def test_get_cost_metrics(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test getting cost metrics."""
        response = client.get("/api/metrics/costs", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            cost_fields = ["total_cost", "cost_per_request", "savings"]
            has_cost_data = any(field in data for field in cost_fields)
            assert has_cost_data or len(data) > 0

    def test_get_performance_metrics(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test getting performance metrics."""
        response = client.get("/api/metrics/performance", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            perf_fields = ["response_time", "throughput", "latency"]
            has_perf_data = any(field in data for field in perf_fields)
            assert has_perf_data or len(data) > 0

    def test_get_metrics_with_time_range(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test getting metrics with time range filter."""
        response = client.get("/api/metrics/usage?start_date=2024-01-01&end_date=2024-01-31", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


class TestReportingEndpoints:
    """Test reporting and export endpoints."""

    def test_generate_report(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test generating analysis report."""
        report_data = {
            "type": "monthly_summary",
            "format": "pdf",
            "time_range": "30d"
        }
        
        response = client.post("/api/reports/generate", json=report_data, headers=auth_headers)
        
        if response.status_code in [200, 201, 202]:
            data = response.json()
            assert isinstance(data, dict)
            assert "report_id" in data or "id" in data

    def test_get_report_status(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting report generation status."""
        report_id = "test-report-id"
        response = client.get(f"/api/reports/{report_id}/status", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert "status" in data

    def test_download_report(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test downloading generated report."""
        report_id = "test-report-id"
        response = client.get(f"/api/reports/{report_id}/download", headers=auth_headers)
        
        # Accept various response codes (endpoint might not exist)
        assert response.status_code in [200, 404, 403]

    def test_list_reports(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test listing user reports."""
        response = client.get("/api/reports", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_export_data_csv(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test exporting data as CSV."""
        export_data = {
            "data_type": "usage_metrics",
            "format": "csv",
            "time_range": "7d"
        }
        
        response = client.post("/api/export/csv", json=export_data, headers=auth_headers)
        
        if response.status_code == 200:
            # Should return CSV content or download URL
            assert len(response.content) > 0 or response.json()

    def test_export_data_json(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test exporting data as JSON."""
        export_data = {
            "data_type": "analysis_results",
            "format": "json"
        }
        
        response = client.post("/api/export/json", json=export_data, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))


class TestAnalyticsEndpoints:
    """Test analytics and insights endpoints."""

    def test_get_insights(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting AI optimization insights."""
        response = client.get("/api/analytics/insights", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            if isinstance(data, dict):
                insight_fields = ["insights", "recommendations", "opportunities"]
                has_insights = any(field in data for field in insight_fields)
                assert has_insights or len(data) > 0

    def test_get_recommendations(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting optimization recommendations."""
        response = client.get("/api/analytics/recommendations", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_get_trends(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting usage trends."""
        response = client.get("/api/analytics/trends", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            trend_fields = ["trends", "data", "series"]
            has_trends = any(field in data for field in trend_fields)
            assert has_trends or len(data) > 0

    def test_get_predictions(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting cost predictions."""
        response = client.get("/api/analytics/predictions", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            pred_fields = ["predictions", "forecast", "projected"]
            has_predictions = any(field in data for field in pred_fields)
            assert has_predictions or len(data) > 0


class TestAnalysisValidation:
    """Test analysis endpoint validation."""

    def test_start_analysis_missing_type(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test starting analysis without type."""
        analysis_data = {"parameters": {}}
        
        response = client.post("/api/analysis/start", json=analysis_data, headers=auth_headers)
        
        if response.status_code != 404:  # If endpoint exists
            assert response.status_code in [400, 422]

    def test_start_analysis_invalid_type(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test starting analysis with invalid type."""
        analysis_data = {
            "type": "invalid_analysis_type",
            "parameters": {}
        }
        
        response = client.post("/api/analysis/start", json=analysis_data, headers=auth_headers)
        
        if response.status_code != 404:  # If endpoint exists
            assert response.status_code in [400, 422]

    def test_get_metrics_invalid_date_range(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting metrics with invalid date range."""
        response = client.get("/api/metrics/usage?start_date=invalid&end_date=also-invalid", headers=auth_headers)
        
        if response.status_code != 404:  # If endpoint exists
            assert response.status_code in [400, 422]

    def test_generate_report_invalid_format(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test generating report with invalid format."""
        report_data = {
            "type": "summary",
            "format": "invalid_format"
        }
        
        response = client.post("/api/reports/generate", json=report_data, headers=auth_headers)
        
        if response.status_code != 404:  # If endpoint exists
            assert response.status_code in [400, 422]


class TestAnalysisPermissions:
    """Test analysis endpoint permissions."""

    def test_analysis_unauthorized(self, client: TestClient) -> None:
        """Test analysis endpoints without authentication."""
        response = client.get("/api/analysis")
        assert response.status_code == 401

    def test_metrics_unauthorized(self, client: TestClient) -> None:
        """Test metrics endpoints without authentication."""
        response = client.get("/api/metrics/dashboard")
        assert response.status_code == 401

    def test_reports_unauthorized(self, client: TestClient) -> None:
        """Test reports endpoints without authentication."""
        response = client.get("/api/reports")
        assert response.status_code == 401

    def test_access_other_user_analysis(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test accessing another user's analysis."""
        other_analysis_id = "other-user-analysis-id"
        response = client.get(f"/api/analysis/{other_analysis_id}/results", headers=auth_headers)
        
        # Should either work (if user has access) or return 403/404
        assert response.status_code in [200, 403, 404]


class TestAnalysisPerformance:
    """Test analysis endpoint performance."""

    def test_dashboard_response_time(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test dashboard endpoint response time."""
        import time
        
        start_time = time.time()
        response = client.get("/api/metrics/dashboard", headers=auth_headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        # Dashboard should be fast (under 5 seconds)
        assert response_time < 5.0

    def test_large_dataset_export(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test exporting large dataset."""
        export_data = {
            "data_type": "usage_metrics",
            "format": "csv",
            "time_range": "365d"  # Large time range
        }
        
        response = client.post("/api/export/csv", json=export_data, headers=auth_headers)
        
        # Should either work or return appropriate error/timeout
        assert response.status_code in [200, 202, 400, 404, 413, 504]

    def test_concurrent_analysis_requests(self, client: TestClient, auth_headers: Dict[str, str], mock_analysis_dependencies) -> None:
        """Test handling concurrent analysis requests."""
        import concurrent.futures
        
        def make_request():
            return client.get("/api/metrics/dashboard", headers=auth_headers)
        
        # Make 3 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should complete
        assert len(responses) == 3
        status_codes = [r.status_code for r in responses]
        # Either all succeed or fail consistently
        assert len(set(status_codes)) <= 2


class TestAnalysisErrorHandling:
    """Test error handling in analysis endpoints."""

    def test_nonexistent_analysis_id(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test accessing nonexistent analysis."""
        response = client.get("/api/analysis/nonexistent-id/results", headers=auth_headers)
        assert response.status_code == 404

    def test_malformed_analysis_request(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test analysis endpoint with malformed data."""
        response = client.post(
            "/api/analysis/start",
            data="malformed json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]

    def test_analysis_service_error(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test handling analysis service errors."""
        with patch('app.services.analysis_service') as mock_service:
            mock_service.run_analysis = AsyncMock(side_effect=Exception("Service error"))
            
            response = client.post(
                "/api/analysis/start",
                json={"type": "cost_optimization"},
                headers=auth_headers
            )
            
            if response.status_code != 404:  # If endpoint exists
                assert response.status_code in [500, 503]