"""Tests for demo API routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
import json
import uuid

from routes.demo import (
    DemoChatRequest,
    DemoChatResponse,
    ROICalculationRequest,
    ROICalculationResponse,
    ExportReportRequest,
    IndustryTemplate,
    DemoMetrics
)
class TestDemoRoutes:
    """Test suite for demo API endpoints."""
    
    @pytest.fixture
    def mock_demo_service(self):
        """Create a mock demo service."""
        service = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_current_user(self):
        """Create a mock current user."""
        return {"id": 1, "email": "test@example.com", "is_admin": False}
    async def test_demo_chat_success(self, mock_demo_service, mock_current_user):
        """Test successful demo chat interaction."""
        from app.routes.demo import demo_chat
        
        # Setup mock response
        mock_demo_service.process_demo_chat.return_value = {
            "response": "Based on analysis, here are optimizations...",
            "agents": ["TriageAgent", "OptimizationAgent"],
            "metrics": {
                "cost_reduction_percentage": 45.0,
                "latency_improvement_ms": 120.0,
                "throughput_increase_factor": 2.5
            }
        }
        
        # Create request
        request = DemoChatRequest(
            message="How can I optimize my ML workloads?",
            industry="financial",
            session_id="test-session-123"
        )
        
        # Execute
        background_tasks = MagicMock()
        response = await demo_chat(
            request=request,
            background_tasks=background_tasks,
            demo_service=mock_demo_service,
            current_user=mock_current_user
        )
        
        # Verify
        assert response.response == "Based on analysis, here are optimizations..."
        assert len(response.agents_involved) == 2
        assert response.optimization_metrics["cost_reduction_percentage"] == 45.0
        assert response.session_id == "test-session-123"
        
        # Verify service was called correctly
        mock_demo_service.process_demo_chat.assert_called_once_with(
            message="How can I optimize my ML workloads?",
            industry="financial",
            session_id="test-session-123",
            context={},
            user_id=1
        )
        
        # Verify background task was added
        background_tasks.add_task.assert_called_once()
    async def test_demo_chat_without_session_id(self, mock_demo_service):
        """Test demo chat creates session ID if not provided."""
        from app.routes.demo import demo_chat
        
        mock_demo_service.process_demo_chat.return_value = {
            "response": "Test response",
            "agents": ["Agent1"],
            "metrics": {}
        }
        
        request = DemoChatRequest(
            message="Test message",
            industry="technology"
        )
        
        background_tasks = MagicMock()
        response = await demo_chat(
            request=request,
            background_tasks=background_tasks,
            demo_service=mock_demo_service,
            current_user=None
        )
        
        # Verify session ID was generated
        assert response.session_id != None
        assert len(response.session_id) > 0
    async def test_get_industry_templates_success(self, mock_demo_service):
        """Test getting industry templates."""
        from app.routes.demo import get_industry_templates
        
        # Setup mock templates
        mock_templates = [
            {
                "industry": "healthcare",
                "name": "Diagnostic AI",
                "description": "Template for diagnostic AI optimization",
                "prompt_template": "Analyze diagnostic workloads...",
                "optimization_scenarios": [{"name": "Accuracy Enhancement"}],
                "typical_metrics": {"baseline": {"accuracy": 0.85}}
            }
        ]
        mock_demo_service.get_industry_templates.return_value = mock_templates
        
        # Execute
        templates = await get_industry_templates(
            industry="healthcare",
            demo_service=mock_demo_service
        )
        
        # Verify
        assert len(templates) == 1
        assert templates[0]["industry"] == "healthcare"
        assert templates[0]["name"] == "Diagnostic AI"
        mock_demo_service.get_industry_templates.assert_called_once_with("healthcare")
    async def test_get_industry_templates_invalid_industry(self, mock_demo_service):
        """Test getting templates for invalid industry."""
        from app.routes.demo import get_industry_templates
        from fastapi import HTTPException
        
        mock_demo_service.get_industry_templates.side_effect = ValueError("Unknown industry: invalid")
        
        with pytest.raises(HTTPException) as exc_info:
            await get_industry_templates(
                industry="invalid",
                demo_service=mock_demo_service
            )
        
        assert exc_info.value.status_code == 404
        assert "Unknown industry" in str(exc_info.value.detail)
    async def test_calculate_roi_success(self, mock_demo_service):
        """Test ROI calculation."""
        from app.routes.demo import calculate_roi
        
        # Setup mock ROI response
        mock_roi = {
            "current_annual_cost": 1200000,
            "optimized_annual_cost": 720000,
            "annual_savings": 480000,
            "savings_percentage": 40.0,
            "roi_months": 2,
            "three_year_tco_reduction": 1440000,
            "performance_improvements": {
                "latency_reduction_percentage": 60.0,
                "throughput_increase_factor": 2.5
            }
        }
        mock_demo_service.calculate_roi.return_value = mock_roi
        
        # Create request
        request = ROICalculationRequest(
            current_spend=100000,
            request_volume=1000000,
            average_latency=250,
            industry="financial"
        )
        
        # Execute
        background_tasks = MagicMock()
        response = await calculate_roi(
            request=request,
            background_tasks=background_tasks,
            demo_service=mock_demo_service
        )
        
        # Verify
        assert response.current_annual_cost == 1200000
        assert response.annual_savings == 480000
        assert response.savings_percentage == 40.0
        assert response.roi_months == 2
        
        # Verify service was called
        mock_demo_service.calculate_roi.assert_called_once_with(
            current_spend=100000,
            request_volume=1000000,
            average_latency=250,
            industry="financial"
        )
    async def test_get_synthetic_metrics_success(self, mock_demo_service):
        """Test synthetic metrics generation."""
        from app.routes.demo import get_synthetic_metrics
        
        # Setup mock metrics
        mock_metrics = {
            "latency_reduction": 60.0,
            "throughput_increase": 200.0,
            "cost_reduction": 45.0,
            "accuracy_improvement": 8.5,
            "timestamps": [datetime.now(UTC)],
            "values": {
                "baseline_latency": [250.0],
                "optimized_latency": [100.0]
            }
        }
        mock_demo_service.generate_synthetic_metrics.return_value = mock_metrics
        
        # Execute
        metrics = await get_synthetic_metrics(
            scenario="standard",
            duration_hours=24,
            demo_service=mock_demo_service
        )
        
        # Verify
        assert metrics.latency_reduction == 60.0
        assert metrics.cost_reduction == 45.0
        assert len(metrics.timestamps) == 1
        mock_demo_service.generate_synthetic_metrics.assert_called_once_with(
            scenario="standard",
            duration_hours=24
        )
    async def test_export_report_success(self, mock_demo_service, mock_current_user):
        """Test report export."""
        from app.routes.demo import export_demo_report
        
        # Setup mock response
        mock_demo_service.generate_report.return_value = "/api/demo/reports/report-123.pdf"
        
        # Create request
        request = ExportReportRequest(
            session_id="session-123",
            format="pdf",
            include_sections=["summary", "metrics"]
        )
        
        # Execute
        background_tasks = MagicMock()
        response = await export_demo_report(
            request=request,
            background_tasks=background_tasks,
            demo_service=mock_demo_service,
            current_user=mock_current_user
        )
        
        # Verify
        assert response["status"] == "success"
        assert response["report_url"] == "/api/demo/reports/report-123.pdf"
        assert "expires_at" in response
        
        # Verify service was called
        mock_demo_service.generate_report.assert_called_once_with(
            session_id="session-123",
            format="pdf",
            include_sections=["summary", "metrics"],
            user_id=1
        )
    async def test_export_report_session_not_found(self, mock_demo_service):
        """Test report export with invalid session."""
        from app.routes.demo import export_demo_report
        from fastapi import HTTPException
        
        mock_demo_service.generate_report.side_effect = ValueError("Session not found")
        
        request = ExportReportRequest(
            session_id="invalid-session",
            format="pdf"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await export_demo_report(
                request=request,
                background_tasks=MagicMock(),
                demo_service=mock_demo_service,
                current_user=None
            )
        
        assert exc_info.value.status_code == 404
        assert "Session not found" in str(exc_info.value.detail)
    async def test_get_session_status_success(self, mock_demo_service):
        """Test getting demo session status."""
        from app.routes.demo import get_demo_session_status
        
        # Setup mock status
        mock_status = {
            "session_id": "session-123",
            "industry": "healthcare",
            "started_at": datetime.now(UTC).isoformat(),
            "message_count": 5,
            "progress_percentage": 83.3,
            "status": "active",
            "last_interaction": datetime.now(UTC).isoformat()
        }
        mock_demo_service.get_session_status.return_value = mock_status
        
        # Execute
        status = await get_demo_session_status(
            session_id="session-123",
            demo_service=mock_demo_service
        )
        
        # Verify
        assert status["session_id"] == "session-123"
        assert status["progress_percentage"] == 83.3
        assert status["status"] == "active"
    async def test_submit_feedback_success(self, mock_demo_service):
        """Test submitting demo feedback."""
        from app.routes.demo import submit_demo_feedback
        
        # Setup mock
        mock_demo_service.submit_feedback.return_value = None
        
        # Execute
        feedback = {
            "rating": 5,
            "would_recommend": True,
            "comments": "Excellent demo!"
        }
        
        response = await submit_demo_feedback(
            session_id="session-123",
            feedback=feedback,
            demo_service=mock_demo_service
        )
        
        # Verify
        assert response["status"] == "success"
        assert response["message"] == "Feedback received"
        mock_demo_service.submit_feedback.assert_called_once_with("session-123", feedback)
    async def test_get_analytics_admin_only(self, mock_demo_service):
        """Test analytics endpoint requires admin access."""
        from app.routes.demo import get_demo_analytics
        from fastapi import HTTPException
        
        # Non-admin user
        non_admin_user = {"id": 1, "email": "user@example.com", "is_admin": False}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_demo_analytics(
                days=30,
                demo_service=mock_demo_service,
                current_user=non_admin_user
            )
        
        assert exc_info.value.status_code == 403
        assert "Admin access required" in str(exc_info.value.detail)
    async def test_get_analytics_success(self, mock_demo_service):
        """Test getting demo analytics as admin."""
        from app.routes.demo import get_demo_analytics
        
        # Admin user
        admin_user = {"id": 1, "email": "admin@example.com", "is_admin": True}
        
        # Setup mock analytics
        mock_analytics = {
            "period_days": 30,
            "total_sessions": 150,
            "total_interactions": 1200,
            "conversion_rate": 65.0,
            "industries": {"financial": 50, "healthcare": 40, "ecommerce": 60},
            "avg_interactions_per_session": 8.0,
            "report_exports": 98
        }
        mock_demo_service.get_analytics_summary.return_value = mock_analytics
        
        # Execute
        analytics = await get_demo_analytics(
            days=30,
            demo_service=mock_demo_service,
            current_user=admin_user
        )
        
        # Verify
        assert analytics["total_sessions"] == 150
        assert analytics["conversion_rate"] == 65.0
        assert analytics["report_exports"] == 98
        mock_demo_service.get_analytics_summary.assert_called_once_with(days=30)
    async def test_demo_chat_error_handling(self, mock_demo_service):
        """Test demo chat error handling."""
        from app.routes.demo import demo_chat
        from fastapi import HTTPException
        
        # Setup service to raise error
        mock_demo_service.process_demo_chat.side_effect = Exception("Service error")
        
        request = DemoChatRequest(
            message="Test",
            industry="tech"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await demo_chat(
                request=request,
                background_tasks=MagicMock(),
                demo_service=mock_demo_service,
                current_user=None
            )
        
        assert exc_info.value.status_code == 500
        assert "Demo chat processing failed" in str(exc_info.value.detail)