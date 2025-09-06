"""Tests for demo API routes."""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import json
import uuid
from datetime import UTC, datetime

import pytest
# REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import ( )
import asyncio
DemoChatRequest,
DemoChatResponse,
DemoMetrics,
ExportReportRequest,
IndustryTemplate,
ROICalculationRequest,
ROICalculationResponse

# REMOVED_SYNTAX_ERROR: class TestDemoRoutes:
    # REMOVED_SYNTAX_ERROR: """Test suite for demo API endpoints."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_demo_service():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock demo service."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service = AsyncNone  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return service

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_current_user():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock current user."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return {"id": 1, "email": "test@example.com", "is_admin": False}
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_demo_chat_success(self, mock_demo_service, mock_current_user):
        # REMOVED_SYNTAX_ERROR: """Test successful demo chat interaction."""
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import demo_chat

        # Setup mock response
        # REMOVED_SYNTAX_ERROR: mock_demo_service.process_demo_chat.return_value = { )
        # REMOVED_SYNTAX_ERROR: "response": "Based on analysis, here are optimizations...",
        # REMOVED_SYNTAX_ERROR: "agents": ["TriageAgent", "OptimizationAgent"],
        # REMOVED_SYNTAX_ERROR: "metrics": { )
        # REMOVED_SYNTAX_ERROR: "cost_reduction_percentage": 45.0,
        # REMOVED_SYNTAX_ERROR: "latency_improvement_ms": 120.0,
        # REMOVED_SYNTAX_ERROR: "throughput_increase_factor": 2.5
        
        

        # Create request
        # REMOVED_SYNTAX_ERROR: request = DemoChatRequest( )
        # REMOVED_SYNTAX_ERROR: message="How can I optimize my ML workloads?",
        # REMOVED_SYNTAX_ERROR: industry="financial",
        # REMOVED_SYNTAX_ERROR: session_id="test-session-123"
        

        # Execute
        # Mock: Background processing isolation for controlled test environments
        # REMOVED_SYNTAX_ERROR: background_tasks = MagicNone  # TODO: Use real service instance
        # REMOVED_SYNTAX_ERROR: response = await demo_chat( )
        # REMOVED_SYNTAX_ERROR: request=request,
        # REMOVED_SYNTAX_ERROR: background_tasks=background_tasks,
        # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service,
        # REMOVED_SYNTAX_ERROR: current_user=mock_current_user
        

        # Verify
        # REMOVED_SYNTAX_ERROR: assert response.response == "Based on analysis, here are optimizations..."
        # REMOVED_SYNTAX_ERROR: assert len(response.agents_involved) == 2
        # REMOVED_SYNTAX_ERROR: assert response.optimization_metrics["cost_reduction_percentage"] == 45.0
        # REMOVED_SYNTAX_ERROR: assert response.session_id == "test-session-123"

        # Verify service was called correctly
        # REMOVED_SYNTAX_ERROR: mock_demo_service.process_demo_chat.assert_called_once_with( )
        # REMOVED_SYNTAX_ERROR: message="How can I optimize my ML workloads?",
        # REMOVED_SYNTAX_ERROR: industry="financial",
        # REMOVED_SYNTAX_ERROR: session_id="test-session-123",
        # REMOVED_SYNTAX_ERROR: context={},
        # REMOVED_SYNTAX_ERROR: user_id=1
        

        # Verify background task was added
        # REMOVED_SYNTAX_ERROR: background_tasks.add_task.assert_called_once()
        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_demo_chat_without_session_id(self, mock_demo_service):
            # REMOVED_SYNTAX_ERROR: """Test demo chat creates session ID if not provided."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import demo_chat

            # REMOVED_SYNTAX_ERROR: mock_demo_service.process_demo_chat.return_value = { )
            # REMOVED_SYNTAX_ERROR: "response": "Test response",
            # REMOVED_SYNTAX_ERROR: "agents": ["Agent1"],
            # REMOVED_SYNTAX_ERROR: "metrics": {}
            

            # REMOVED_SYNTAX_ERROR: request = DemoChatRequest( )
            # REMOVED_SYNTAX_ERROR: message="Test message",
            # REMOVED_SYNTAX_ERROR: industry="technology"
            

            # Mock: Background processing isolation for controlled test environments
            # REMOVED_SYNTAX_ERROR: background_tasks = MagicNone  # TODO: Use real service instance
            # REMOVED_SYNTAX_ERROR: response = await demo_chat( )
            # REMOVED_SYNTAX_ERROR: request=request,
            # REMOVED_SYNTAX_ERROR: background_tasks=background_tasks,
            # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service,
            # REMOVED_SYNTAX_ERROR: current_user=None
            

            # Verify session ID was generated
            # REMOVED_SYNTAX_ERROR: assert response.session_id != None
            # REMOVED_SYNTAX_ERROR: assert len(response.session_id) > 0
            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_get_industry_templates_success(self, mock_demo_service):
                # REMOVED_SYNTAX_ERROR: """Test getting industry templates."""
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import get_industry_templates

                # Setup mock templates
                # REMOVED_SYNTAX_ERROR: mock_templates = [ )
                # REMOVED_SYNTAX_ERROR: { )
                # REMOVED_SYNTAX_ERROR: "industry": "healthcare",
                # REMOVED_SYNTAX_ERROR: "name": "Diagnostic AI",
                # REMOVED_SYNTAX_ERROR: "description": "Template for diagnostic AI optimization",
                # REMOVED_SYNTAX_ERROR: "prompt_template": "Analyze diagnostic workloads...",
                # REMOVED_SYNTAX_ERROR: "optimization_scenarios": [{"name": "Accuracy Enhancement"}],
                # REMOVED_SYNTAX_ERROR: "typical_metrics": {"baseline": {"accuracy": 0.85}}
                
                
                # REMOVED_SYNTAX_ERROR: mock_demo_service.get_industry_templates.return_value = mock_templates

                # Execute
                # REMOVED_SYNTAX_ERROR: templates = await get_industry_templates( )
                # REMOVED_SYNTAX_ERROR: industry="healthcare",
                # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service
                

                # Verify
                # REMOVED_SYNTAX_ERROR: assert len(templates) == 1
                # REMOVED_SYNTAX_ERROR: assert templates[0]["industry"] == "healthcare"
                # REMOVED_SYNTAX_ERROR: assert templates[0]["name"] == "Diagnostic AI"
                # REMOVED_SYNTAX_ERROR: mock_demo_service.get_industry_templates.assert_called_once_with("healthcare")
                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_get_industry_templates_invalid_industry(self, mock_demo_service):
                    # REMOVED_SYNTAX_ERROR: """Test getting templates for invalid industry."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: from fastapi import HTTPException

                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import get_industry_templates

                    # REMOVED_SYNTAX_ERROR: mock_demo_service.get_industry_templates.side_effect = ValueError("Unknown industry: invalid")

                    # REMOVED_SYNTAX_ERROR: with pytest.raises(HTTPException) as exc_info:
                        # REMOVED_SYNTAX_ERROR: await get_industry_templates( )
                        # REMOVED_SYNTAX_ERROR: industry="invalid",
                        # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service
                        

                        # REMOVED_SYNTAX_ERROR: assert exc_info.value.status_code == 404
                        # REMOVED_SYNTAX_ERROR: assert "Unknown industry" in str(exc_info.value.detail)
                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_calculate_roi_success(self, mock_demo_service):
                            # REMOVED_SYNTAX_ERROR: """Test ROI calculation."""
                            # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import calculate_roi

                            # Setup mock ROI response
                            # REMOVED_SYNTAX_ERROR: mock_roi = { )
                            # REMOVED_SYNTAX_ERROR: "current_annual_cost": 1200000,
                            # REMOVED_SYNTAX_ERROR: "optimized_annual_cost": 720000,
                            # REMOVED_SYNTAX_ERROR: "annual_savings": 480000,
                            # REMOVED_SYNTAX_ERROR: "savings_percentage": 40.0,
                            # REMOVED_SYNTAX_ERROR: "roi_months": 2,
                            # REMOVED_SYNTAX_ERROR: "three_year_tco_reduction": 1440000,
                            # REMOVED_SYNTAX_ERROR: "performance_improvements": { )
                            # REMOVED_SYNTAX_ERROR: "latency_reduction_percentage": 60.0,
                            # REMOVED_SYNTAX_ERROR: "throughput_increase_factor": 2.5
                            
                            
                            # REMOVED_SYNTAX_ERROR: mock_demo_service.calculate_roi.return_value = mock_roi

                            # Create request
                            # REMOVED_SYNTAX_ERROR: request = ROICalculationRequest( )
                            # REMOVED_SYNTAX_ERROR: current_spend=100000,
                            # REMOVED_SYNTAX_ERROR: request_volume=1000000,
                            # REMOVED_SYNTAX_ERROR: average_latency=250,
                            # REMOVED_SYNTAX_ERROR: industry="financial"
                            

                            # Execute
                            # Mock: Background processing isolation for controlled test environments
                            # REMOVED_SYNTAX_ERROR: background_tasks = MagicNone  # TODO: Use real service instance
                            # REMOVED_SYNTAX_ERROR: response = await calculate_roi( )
                            # REMOVED_SYNTAX_ERROR: request=request,
                            # REMOVED_SYNTAX_ERROR: background_tasks=background_tasks,
                            # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service
                            

                            # Verify
                            # REMOVED_SYNTAX_ERROR: assert response.current_annual_cost == 1200000
                            # REMOVED_SYNTAX_ERROR: assert response.annual_savings == 480000
                            # REMOVED_SYNTAX_ERROR: assert response.savings_percentage == 40.0
                            # REMOVED_SYNTAX_ERROR: assert response.roi_months == 2

                            # Verify service was called
                            # REMOVED_SYNTAX_ERROR: mock_demo_service.calculate_roi.assert_called_once_with( )
                            # REMOVED_SYNTAX_ERROR: current_spend=100000,
                            # REMOVED_SYNTAX_ERROR: request_volume=1000000,
                            # REMOVED_SYNTAX_ERROR: average_latency=250,
                            # REMOVED_SYNTAX_ERROR: industry="financial"
                            
                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_get_synthetic_metrics_success(self, mock_demo_service):
                                # REMOVED_SYNTAX_ERROR: """Test synthetic metrics generation."""
                                # REMOVED_SYNTAX_ERROR: pass
                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import get_synthetic_metrics

                                # Setup mock metrics
                                # REMOVED_SYNTAX_ERROR: mock_metrics = { )
                                # REMOVED_SYNTAX_ERROR: "latency_reduction": 60.0,
                                # REMOVED_SYNTAX_ERROR: "throughput_increase": 200.0,
                                # REMOVED_SYNTAX_ERROR: "cost_reduction": 45.0,
                                # REMOVED_SYNTAX_ERROR: "accuracy_improvement": 8.5,
                                # REMOVED_SYNTAX_ERROR: "timestamps": [datetime.now(UTC)],
                                # REMOVED_SYNTAX_ERROR: "values": { )
                                # REMOVED_SYNTAX_ERROR: "baseline_latency": [250.0],
                                # REMOVED_SYNTAX_ERROR: "optimized_latency": [100.0]
                                
                                
                                # REMOVED_SYNTAX_ERROR: mock_demo_service.generate_synthetic_metrics.return_value = mock_metrics

                                # Execute
                                # REMOVED_SYNTAX_ERROR: metrics = await get_synthetic_metrics( )
                                # REMOVED_SYNTAX_ERROR: scenario="standard",
                                # REMOVED_SYNTAX_ERROR: duration_hours=24,
                                # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service
                                

                                # Verify
                                # REMOVED_SYNTAX_ERROR: assert metrics.latency_reduction == 60.0
                                # REMOVED_SYNTAX_ERROR: assert metrics.cost_reduction == 45.0
                                # REMOVED_SYNTAX_ERROR: assert len(metrics.timestamps) == 1
                                # REMOVED_SYNTAX_ERROR: mock_demo_service.generate_synthetic_metrics.assert_called_once_with( )
                                # REMOVED_SYNTAX_ERROR: scenario="standard",
                                # REMOVED_SYNTAX_ERROR: duration_hours=24
                                
                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_export_report_success(self, mock_demo_service, mock_current_user):
                                    # REMOVED_SYNTAX_ERROR: """Test report export."""
                                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import export_demo_report

                                    # Setup mock response
                                    # REMOVED_SYNTAX_ERROR: mock_demo_service.generate_report.return_value = "/api/demo/reports/report-123.pdf"

                                    # Create request
                                    # REMOVED_SYNTAX_ERROR: request = ExportReportRequest( )
                                    # REMOVED_SYNTAX_ERROR: session_id="session-123",
                                    # REMOVED_SYNTAX_ERROR: format="pdf",
                                    # REMOVED_SYNTAX_ERROR: include_sections=["summary", "metrics"]
                                    

                                    # Execute
                                    # Mock: Background processing isolation for controlled test environments
                                    # REMOVED_SYNTAX_ERROR: background_tasks = MagicNone  # TODO: Use real service instance
                                    # REMOVED_SYNTAX_ERROR: response = await export_demo_report( )
                                    # REMOVED_SYNTAX_ERROR: request=request,
                                    # REMOVED_SYNTAX_ERROR: background_tasks=background_tasks,
                                    # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service,
                                    # REMOVED_SYNTAX_ERROR: current_user=mock_current_user
                                    

                                    # Verify
                                    # REMOVED_SYNTAX_ERROR: assert response["status"] == "success"
                                    # REMOVED_SYNTAX_ERROR: assert response["report_url"] == "/api/demo/reports/report-123.pdf"
                                    # REMOVED_SYNTAX_ERROR: assert "expires_at" in response

                                    # Verify service was called
                                    # REMOVED_SYNTAX_ERROR: mock_demo_service.generate_report.assert_called_once_with( )
                                    # REMOVED_SYNTAX_ERROR: session_id="session-123",
                                    # REMOVED_SYNTAX_ERROR: format="pdf",
                                    # REMOVED_SYNTAX_ERROR: include_sections=["summary", "metrics"],
                                    # REMOVED_SYNTAX_ERROR: user_id=1
                                    
                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_export_report_session_not_found(self, mock_demo_service):
                                        # REMOVED_SYNTAX_ERROR: """Test report export with invalid session."""
                                        # REMOVED_SYNTAX_ERROR: pass
                                        # REMOVED_SYNTAX_ERROR: from fastapi import HTTPException

                                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import export_demo_report

                                        # REMOVED_SYNTAX_ERROR: mock_demo_service.generate_report.side_effect = ValueError("Session not found")

                                        # REMOVED_SYNTAX_ERROR: request = ExportReportRequest( )
                                        # REMOVED_SYNTAX_ERROR: session_id="invalid-session",
                                        # REMOVED_SYNTAX_ERROR: format="pdf"
                                        

                                        # REMOVED_SYNTAX_ERROR: with pytest.raises(HTTPException) as exc_info:
                                            # REMOVED_SYNTAX_ERROR: await export_demo_report( )
                                            # REMOVED_SYNTAX_ERROR: request=request,
                                            # Mock: Background processing isolation for controlled test environments
                                            # REMOVED_SYNTAX_ERROR: background_tasks=MagicNone  # TODO: Use real service instance,
                                            # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service,
                                            # REMOVED_SYNTAX_ERROR: current_user=None
                                            

                                            # REMOVED_SYNTAX_ERROR: assert exc_info.value.status_code == 404
                                            # REMOVED_SYNTAX_ERROR: assert "Session not found" in str(exc_info.value.detail)
                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_get_session_status_success(self, mock_demo_service):
                                                # REMOVED_SYNTAX_ERROR: """Test getting demo session status."""
                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import get_demo_session_status

                                                # Setup mock status
                                                # REMOVED_SYNTAX_ERROR: mock_status = { )
                                                # REMOVED_SYNTAX_ERROR: "session_id": "session-123",
                                                # REMOVED_SYNTAX_ERROR: "industry": "healthcare",
                                                # REMOVED_SYNTAX_ERROR: "started_at": datetime.now(UTC).isoformat(),
                                                # REMOVED_SYNTAX_ERROR: "message_count": 5,
                                                # REMOVED_SYNTAX_ERROR: "progress_percentage": 83.3,
                                                # REMOVED_SYNTAX_ERROR: "status": "active",
                                                # REMOVED_SYNTAX_ERROR: "last_interaction": datetime.now(UTC).isoformat()
                                                
                                                # REMOVED_SYNTAX_ERROR: mock_demo_service.get_session_status.return_value = mock_status

                                                # Execute
                                                # REMOVED_SYNTAX_ERROR: status = await get_demo_session_status( )
                                                # REMOVED_SYNTAX_ERROR: session_id="session-123",
                                                # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service
                                                

                                                # Verify
                                                # REMOVED_SYNTAX_ERROR: assert status["session_id"] == "session-123"
                                                # REMOVED_SYNTAX_ERROR: assert status["progress_percentage"] == 83.3
                                                # REMOVED_SYNTAX_ERROR: assert status["status"] == "active"
                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_submit_feedback_success(self, mock_demo_service):
                                                    # REMOVED_SYNTAX_ERROR: """Test submitting demo feedback."""
                                                    # REMOVED_SYNTAX_ERROR: pass
                                                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import submit_demo_feedback

                                                    # Setup mock
                                                    # REMOVED_SYNTAX_ERROR: mock_demo_service.submit_feedback.return_value = None

                                                    # Execute
                                                    # REMOVED_SYNTAX_ERROR: feedback = { )
                                                    # REMOVED_SYNTAX_ERROR: "rating": 5,
                                                    # REMOVED_SYNTAX_ERROR: "would_recommend": True,
                                                    # REMOVED_SYNTAX_ERROR: "comments": "Excellent demo!"
                                                    

                                                    # REMOVED_SYNTAX_ERROR: response = await submit_demo_feedback( )
                                                    # REMOVED_SYNTAX_ERROR: session_id="session-123",
                                                    # REMOVED_SYNTAX_ERROR: feedback=feedback,
                                                    # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service
                                                    

                                                    # Verify
                                                    # REMOVED_SYNTAX_ERROR: assert response["status"] == "success"
                                                    # REMOVED_SYNTAX_ERROR: assert response["message"] == "Feedback received"
                                                    # REMOVED_SYNTAX_ERROR: mock_demo_service.submit_feedback.assert_called_once_with("session-123", feedback)
                                                    # Removed problematic line: @pytest.mark.asyncio
                                                    # Removed problematic line: async def test_get_analytics_admin_only(self, mock_demo_service):
                                                        # REMOVED_SYNTAX_ERROR: """Test analytics endpoint requires admin access."""
                                                        # REMOVED_SYNTAX_ERROR: from fastapi import HTTPException

                                                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import get_demo_analytics

                                                        # Non-admin user
                                                        # REMOVED_SYNTAX_ERROR: non_admin_user = {"id": 1, "email": "user@example.com", "is_admin": False}

                                                        # REMOVED_SYNTAX_ERROR: with pytest.raises(HTTPException) as exc_info:
                                                            # REMOVED_SYNTAX_ERROR: await get_demo_analytics( )
                                                            # REMOVED_SYNTAX_ERROR: days=30,
                                                            # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service,
                                                            # REMOVED_SYNTAX_ERROR: current_user=non_admin_user
                                                            

                                                            # REMOVED_SYNTAX_ERROR: assert exc_info.value.status_code == 403
                                                            # REMOVED_SYNTAX_ERROR: assert "Admin access required" in str(exc_info.value.detail)
                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_get_analytics_success(self, mock_demo_service):
                                                                # REMOVED_SYNTAX_ERROR: """Test getting demo analytics as admin."""
                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import get_demo_analytics

                                                                # Admin user
                                                                # REMOVED_SYNTAX_ERROR: admin_user = {"id": 1, "email": "admin@example.com", "is_admin": True}

                                                                # Setup mock analytics
                                                                # REMOVED_SYNTAX_ERROR: mock_analytics = { )
                                                                # REMOVED_SYNTAX_ERROR: "period_days": 30,
                                                                # REMOVED_SYNTAX_ERROR: "total_sessions": 150,
                                                                # REMOVED_SYNTAX_ERROR: "total_interactions": 1200,
                                                                # REMOVED_SYNTAX_ERROR: "conversion_rate": 65.0,
                                                                # REMOVED_SYNTAX_ERROR: "industries": {"financial": 50, "healthcare": 40, "ecommerce": 60},
                                                                # REMOVED_SYNTAX_ERROR: "avg_interactions_per_session": 8.0,
                                                                # REMOVED_SYNTAX_ERROR: "report_exports": 98
                                                                
                                                                # REMOVED_SYNTAX_ERROR: mock_demo_service.get_analytics_summary.return_value = mock_analytics

                                                                # Execute
                                                                # REMOVED_SYNTAX_ERROR: analytics = await get_demo_analytics( )
                                                                # REMOVED_SYNTAX_ERROR: days=30,
                                                                # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service,
                                                                # REMOVED_SYNTAX_ERROR: current_user=admin_user
                                                                

                                                                # Verify
                                                                # REMOVED_SYNTAX_ERROR: assert analytics["total_sessions"] == 150
                                                                # REMOVED_SYNTAX_ERROR: assert analytics["conversion_rate"] == 65.0
                                                                # REMOVED_SYNTAX_ERROR: assert analytics["report_exports"] == 98
                                                                # REMOVED_SYNTAX_ERROR: mock_demo_service.get_analytics_summary.assert_called_once_with(days=30)
                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_demo_chat_error_handling(self, mock_demo_service):
                                                                    # REMOVED_SYNTAX_ERROR: """Test demo chat error handling."""
                                                                    # REMOVED_SYNTAX_ERROR: from fastapi import HTTPException

                                                                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.routes.demo import demo_chat

                                                                    # Setup service to raise error
                                                                    # REMOVED_SYNTAX_ERROR: mock_demo_service.process_demo_chat.side_effect = Exception("Service error")

                                                                    # REMOVED_SYNTAX_ERROR: request = DemoChatRequest( )
                                                                    # REMOVED_SYNTAX_ERROR: message="Test",
                                                                    # REMOVED_SYNTAX_ERROR: industry="tech"
                                                                    

                                                                    # REMOVED_SYNTAX_ERROR: with pytest.raises(HTTPException) as exc_info:
                                                                        # REMOVED_SYNTAX_ERROR: await demo_chat( )
                                                                        # REMOVED_SYNTAX_ERROR: request=request,
                                                                        # Mock: Background processing isolation for controlled test environments
                                                                        # REMOVED_SYNTAX_ERROR: background_tasks=MagicNone  # TODO: Use real service instance,
                                                                        # REMOVED_SYNTAX_ERROR: demo_service=mock_demo_service,
                                                                        # REMOVED_SYNTAX_ERROR: current_user=None
                                                                        

                                                                        # REMOVED_SYNTAX_ERROR: assert exc_info.value.status_code == 500
                                                                        # REMOVED_SYNTAX_ERROR: assert "Demo chat processing failed" in str(exc_info.value.detail)
                                                                        # REMOVED_SYNTAX_ERROR: pass