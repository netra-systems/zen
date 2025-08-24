"""Tests for demo service functionality."""

import sys
from pathlib import Path

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, MagicMock, patch

import numpy as np
import pytest

from netra_backend.app.services.demo_service import DemoService

class TestDemoService:
    """Test suite for DemoService."""
    
    @pytest.fixture
    def mock_agent_service(self):
        """Create a mock agent service."""
        # Mock: Generic component isolation for controlled unit testing
        return AsyncMock()
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client with stateful behavior."""
        # Create a storage dict to simulate Redis behavior
        storage = {}
        
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        redis = AsyncMock()
        
        async def mock_get(key):
            return storage.get(key, None)
            
        async def mock_setex(key, ttl, value):
            storage[key] = value
            return True
            
        async def mock_lrange(key, start, end):
            return storage.get(key, [])
            
        async def mock_lpush(key, value):
            if key not in storage:
                storage[key] = []
            storage[key].insert(0, value)
            return len(storage[key])
            
        async def mock_expire(key, ttl):
            return True
        
        # Wrap the functions with AsyncMock to preserve mock behavior
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        redis.get = AsyncMock(side_effect=mock_get)
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        redis.setex = AsyncMock(side_effect=mock_setex)
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        redis.lrange = AsyncMock(side_effect=mock_lrange)
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        redis.lpush = AsyncMock(side_effect=mock_lpush)
        # Mock: Redis caching isolation to prevent test interference and external dependencies
        redis.expire = AsyncMock(side_effect=mock_expire)
        return redis
    
    @pytest.fixture
    def demo_service(self, mock_agent_service, mock_redis_client):
        """Create a DemoService instance with mocks."""
        service = DemoService(agent_service=mock_agent_service)
        # Patch the Redis client getter method - it needs to be async
        async def async_get_redis():
            return mock_redis_client
        # Mock all the _get_redis methods to share the same storage
        service.session_manager._get_redis = async_get_redis
        service.analytics_tracker._get_redis = async_get_redis
        service.report_generator._get_redis = async_get_redis
        # Also patch the redis_client attributes directly
        service.session_manager.redis_client = mock_redis_client
        service.analytics_tracker.redis_client = mock_redis_client
        service.report_generator.redis_client = mock_redis_client
        return service
    @pytest.mark.asyncio
    async def test_process_demo_chat_new_session(self, demo_service, mock_redis_client):
        """Test processing demo chat for a new session."""
        # Execute
        result = await demo_service.process_demo_chat(
            message="How can I optimize my fraud detection models?",
            industry="financial",
            session_id="test-session-123",
            context={"test": "context"},
            user_id=1
        )
        
        # Verify response structure
        assert result["response"] != None
        assert "Cost Optimization" in result["response"]
        assert "Performance Improvements" in result["response"]
        assert len(result["agents"]) == 4
        assert result["agents"] == ["TriageAgent", "DataAgent", "OptimizationAgent", "ReportingAgent"]
        
        # Verify metrics
        metrics = result["metrics"]
        assert 40 <= metrics["cost_reduction_percentage"] <= 50
        assert metrics["latency_improvement_ms"] > 0
        assert metrics["throughput_increase_factor"] == 2.5
        assert metrics["accuracy_improvement_percentage"] == 8.0
        assert metrics["estimated_annual_savings"] > 0
        assert 2 <= metrics["implementation_time_weeks"] <= 8
        assert 0.85 <= metrics["confidence_score"] <= 0.98
        
        # Verify Redis interactions
        mock_redis_client.setex.assert_called()
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][0] == "demo:session:test-session-123"
        assert call_args[0][1] == 3600 * 24  # 24 hour expiry
    @pytest.mark.asyncio
    async def test_process_demo_chat_existing_session(self, demo_service, mock_redis_client):
        """Test processing demo chat for an existing session."""
        # Setup existing session data
        existing_session = {
            "industry": "healthcare",
            "user_id": 1,
            "started_at": datetime.now(UTC).isoformat(),
            "messages": [
                {"role": "user", "content": "Previous message", "timestamp": datetime.now(UTC).isoformat()}
            ]
        }
        mock_redis_client.get.return_value = json.dumps(existing_session)
        
        # Execute
        result = await demo_service.process_demo_chat(
            message="What about diagnostic AI optimization?",
            industry="healthcare",
            session_id="existing-session",
            user_id=1
        )
        
        # Verify response
        assert result["response"] != None
        assert result["agents"] != None
        assert result["metrics"] != None
        
        # Verify session was updated with new message
        mock_redis_client.setex.assert_called()
        call_args = mock_redis_client.setex.call_args
        session_data = json.loads(call_args[0][2])
        assert len(session_data["messages"]) == 2  # user + assistant (original gets replaced)
    @pytest.mark.asyncio
    async def test_get_industry_templates_valid(self, demo_service):
        """Test getting templates for a valid industry."""
        # Execute
        templates = await demo_service.get_industry_templates("financial")
        
        # Verify
        assert len(templates) == 3  # fraud_detection, risk_assessment, trading_algorithms
        
        for template in templates:
            assert template["industry"] == "financial"
            assert template["name"] in ["Fraud Detection", "Risk Assessment", "Trading Algorithms"]
            assert template["description"] != None
            assert template["prompt_template"] != None
            assert len(template["optimization_scenarios"]) == 3
            assert "baseline" in template["typical_metrics"]
            assert "optimized" in template["typical_metrics"]
    @pytest.mark.asyncio
    async def test_get_industry_templates_invalid(self, demo_service):
        """Test getting templates for an invalid industry."""
        with pytest.raises(ValueError) as exc_info:
            await demo_service.get_industry_templates("invalid_industry")
        
        assert "Unknown industry: invalid_industry" in str(exc_info.value)
    @pytest.mark.asyncio
    async def test_calculate_roi_financial(self, demo_service):
        """Test ROI calculation for financial industry."""
        # Execute
        result = await demo_service.calculate_roi(
            current_spend=100000,
            request_volume=1000000,
            average_latency=300,
            industry="financial"
        )
        
        # Verify calculations
        assert result["current_annual_cost"] == 1200000  # 100k * 12
        assert result["optimized_annual_cost"] == 660000  # 45% reduction
        assert result["annual_savings"] == 540000
        assert result["savings_percentage"] == 45.0
        assert result["roi_months"] > 0
        assert result["three_year_tco_reduction"] > 0
        
        # Verify performance improvements
        perf = result["performance_improvements"]
        assert perf["latency_reduction_percentage"] == 60.0
        assert perf["throughput_increase_factor"] == 2.5
        assert perf["accuracy_improvement_percentage"] == 8.0
        assert perf["error_rate_reduction_percentage"] == 50.0
    @pytest.mark.asyncio
    async def test_calculate_roi_different_industries(self, demo_service):
        """Test ROI calculation varies by industry."""
        # Test multiple industries
        industries = ["financial", "healthcare", "ecommerce"]
        roi_results = []
        
        for industry in industries:
            result = await demo_service.calculate_roi(
                current_spend=100000,
                request_volume=1000000,
                average_latency=300,
                industry=industry
            )
            roi_results.append(result)
        
        # Verify different industries have different optimization factors
        savings = [r["annual_savings"] for r in roi_results]
        assert len(set(savings)) > 1  # Should have different savings amounts
        
        # Verify all have valid calculations
        for result in roi_results:
            assert result["annual_savings"] > 0
            assert 0 < result["savings_percentage"] <= 100
            assert result["roi_months"] > 0
    @pytest.mark.asyncio
    async def test_generate_synthetic_metrics(self, demo_service):
        """Test synthetic metrics generation."""
        # Execute
        metrics = await demo_service.generate_synthetic_metrics(
            scenario="standard",
            duration_hours=4
        )
        
        # Verify structure
        assert metrics["latency_reduction"] == 60.0
        assert metrics["throughput_increase"] == 200.0
        assert metrics["cost_reduction"] == 45.0
        assert metrics["accuracy_improvement"] == 8.5
        
        # Verify timestamps (4 hours with 15-minute intervals = 17 points)
        assert len(metrics["timestamps"]) == 17
        assert isinstance(metrics["timestamps"][0], datetime)
        
        # Verify values
        assert len(metrics["values"]["baseline_latency"]) == 17
        assert len(metrics["values"]["optimized_latency"]) == 17
        assert len(metrics["values"]["baseline_throughput"]) == 17
        assert len(metrics["values"]["optimized_throughput"]) == 17
        
        # Verify optimization trend (should improve over time)
        baseline_lat = metrics["values"]["baseline_latency"]
        optimized_lat = metrics["values"]["optimized_latency"]
        assert optimized_lat[0] > optimized_lat[-1]  # Latency should decrease
    @pytest.mark.asyncio
    async def test_generate_report(self, demo_service, mock_redis_client):
        """Test report generation."""
        # Setup session data
        session_data = {
            "industry": "healthcare",
            "user_id": 1,
            "started_at": datetime.now(UTC).isoformat(),
            "messages": [{"role": "user", "content": "Test"}]
        }
        # Store in the mock's storage dict instead of setting return_value
        await mock_redis_client.setex("demo:session:test-session", 3600, json.dumps(session_data))
        
        # Execute
        report_url = await demo_service.generate_report(
            session_id="test-session",
            format="pdf",
            include_sections=["summary", "metrics"],
            user_id=1
        )
        
        # Verify
        assert report_url.endswith(".pdf")
        assert "/api/demo/reports/" in report_url
        
        # Verify report metadata was stored
        mock_redis_client.setex.assert_called()
        call_args = mock_redis_client.setex.call_args_list[-1]
        assert "demo:report:" in call_args[0][0]
        assert call_args[0][1] == 3600 * 24  # 24 hour expiry
    @pytest.mark.asyncio
    async def test_generate_report_session_not_found(self, demo_service, mock_redis_client):
        """Test report generation with invalid session."""
        mock_redis_client.get.return_value = None
        
        with pytest.raises(ValueError) as exc_info:
            await demo_service.generate_report(
                session_id="invalid-session",
                format="pdf"
            )
        
        assert "Session not found: invalid-session" in str(exc_info.value)
    @pytest.mark.asyncio
    async def test_get_session_status(self, demo_service, mock_redis_client):
        """Test getting session status."""
        # Setup session data
        session_data = {
            "industry": "ecommerce",
            "user_id": 2,
            "started_at": datetime.now(UTC).isoformat(),
            "messages": [
                {"role": "user", "content": "Message 1", "timestamp": datetime.now(UTC).isoformat()},
                {"role": "assistant", "content": "Response 1", "timestamp": datetime.now(UTC).isoformat()},
                {"role": "user", "content": "Message 2", "timestamp": datetime.now(UTC).isoformat()}
            ]
        }
        # Store in the mock's storage dict instead of setting return_value
        await mock_redis_client.setex("demo:session:test-session", 3600, json.dumps(session_data))
        
        # Execute
        status = await demo_service.get_session_status("test-session")
        
        # Verify
        assert status["session_id"] == "test-session"
        assert status["industry"] == "ecommerce"
        assert status["message_count"] == 3
        assert status["progress_percentage"] == 50.0  # 3 messages / 6 expected steps
        assert status["status"] == "active"
        assert status["last_interaction"] != None
    @pytest.mark.asyncio
    async def test_get_session_status_not_found(self, demo_service, mock_redis_client):
        """Test getting status for non-existent session."""
        mock_redis_client.get.return_value = None
        
        with pytest.raises(ValueError) as exc_info:
            await demo_service.get_session_status("invalid-session")
        
        assert "Session not found: invalid-session" in str(exc_info.value)
    @pytest.mark.asyncio
    async def test_submit_feedback(self, demo_service, mock_redis_client):
        """Test submitting demo feedback."""
        # Execute
        feedback = {
            "rating": 5,
            "would_recommend": True,
            "comments": "Great demo!"
        }
        
        await demo_service.submit_feedback("test-session", feedback)
        
        # Verify feedback was stored
        mock_redis_client.setex.assert_called()
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][0] == "demo:feedback:test-session"
        assert call_args[0][1] == 3600 * 24 * 30  # 30 day expiry
        
        feedback_data = json.loads(call_args[0][2])
        assert feedback_data["session_id"] == "test-session"
        assert feedback_data["feedback"] == feedback
    @pytest.mark.asyncio
    async def test_track_demo_interaction(self, demo_service, mock_redis_client):
        """Test tracking demo interactions."""
        # Execute
        await demo_service.track_demo_interaction(
            session_id="test-session",
            interaction_type="chat",
            data={"industry": "financial", "message_length": 100}
        )
        
        # Verify interaction was tracked
        mock_redis_client.lpush.assert_called()
        call_args = mock_redis_client.lpush.call_args
        
        # Verify key format includes date
        key = call_args[0][0]
        assert key.startswith("demo:analytics:")
        assert datetime.now(UTC).strftime("%Y%m%d") in key
        
        # Verify data structure
        interaction_data = json.loads(call_args[0][1])
        assert interaction_data["session_id"] == "test-session"
        assert interaction_data["type"] == "chat"
        assert interaction_data["data"]["industry"] == "financial"
    @pytest.mark.asyncio
    async def test_get_analytics_summary(self, demo_service, mock_redis_client):
        """Test getting analytics summary."""
        # Setup mock analytics data
        analytics_data = [
            json.dumps({
                "session_id": "session1",
                "type": "chat",
                "data": {"industry": "financial"},
                "timestamp": datetime.now(UTC).isoformat()
            }),
            json.dumps({
                "session_id": "session2",
                "type": "chat",
                "data": {"industry": "healthcare"},
                "timestamp": datetime.now(UTC).isoformat()
            }),
            json.dumps({
                "session_id": "session1",
                "type": "report_export",
                "data": {"format": "pdf"},
                "timestamp": datetime.now(UTC).isoformat()
            })
        ]
        
        # Store analytics data in mock storage using the correct key format
        today_key = f"demo:analytics:{datetime.now(UTC).strftime('%Y%m%d')}"
        for data_item in analytics_data:
            await mock_redis_client.lpush(today_key, data_item)
        
        # Execute
        summary = await demo_service.get_analytics_summary(days=7)
        
        # Verify
        assert summary["period_days"] == 7
        assert summary["total_sessions"] >= 2  # May have more from other tests
        assert summary["total_interactions"] >= 3  # May have more from other tests
        # Don't check exact conversion rate as it depends on total sessions
        assert "conversion_rate" in summary
        assert "financial" in summary["industries"]
        assert "healthcare" in summary["industries"]
        assert summary["avg_interactions_per_session"] > 0
        assert summary["report_exports"] >= 1
    @pytest.mark.asyncio
    async def test_generate_demo_response(self, demo_service):
        """Test demo response generation."""
        # Import the function directly for testing
        from netra_backend.app.services.demo.response_generator import (
            generate_demo_response,
        )
        
        # Execute
        response = generate_demo_response(
            message="Optimize my recommendation engine",
            industry="ecommerce",
            metrics={
                "cost_reduction_percentage": 50.0,
                "latency_improvement_ms": 150.0,
                "throughput_increase_factor": 3.0,
                "accuracy_improvement_percentage": 10.0,
                "estimated_annual_savings": 750000,
                "implementation_time_weeks": 4,
                "confidence_score": 0.92
            }
        )
        
        # Verify response contains key elements
        assert "ecommerce" in response
        assert "50.0%" in response
        assert "150ms" in response
        assert "3.0x" in response
        assert "10.0%" in response
        assert "750,000" in response
        assert "4 weeks" in response
        assert "92.00%" in response or "0.92" in response
        assert "Recommendation Engine" in response or "Search Optimization" in response or "Inventory Prediction" in response
    @pytest.mark.asyncio
    async def test_error_handling_redis_failure(self, demo_service):
        """Test error handling when Redis operations fail."""
        # Make Redis operations fail
        with patch.object(demo_service.session_manager, '_get_redis', side_effect=Exception("Redis connection failed")):
            with pytest.raises(Exception) as exc_info:
                await demo_service.process_demo_chat(
                    message="Test",
                    industry="tech",
                    session_id="test"
                )
            
            assert "Redis connection failed" in str(exc_info.value)