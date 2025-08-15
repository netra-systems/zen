"""Test anomaly detection type conversion to prevent regression.

This test ensures that LLM response format is correctly converted to
AnomalyDetectionResponse model format.
"""

import pytest
from datetime import datetime
from app.agents.data_sub_agent.agent import DataSubAgent
from app.schemas.shared_types import AnomalyDetail, AnomalySeverity, AnomalyDetectionResponse
from unittest.mock import MagicMock, AsyncMock


class TestAnomalyDetectionTypeConversion:
    """Test suite for anomaly detection type conversion."""
    
    def test_convert_llm_anomaly_to_detail(self):
        """Test conversion of LLM anomaly format to AnomalyDetail."""
        # Create a mock agent with minimal dependencies
        agent = DataSubAgent(
            llm_manager=MagicMock(),
            tool_dispatcher=MagicMock()
        )
        
        # LLM response format (as per data_prompts.py)
        llm_anomaly = {
            "type": "latency_spike",
            "timestamp": "2025-08-15T12:00:00Z",
            "severity": "high",
            "affected_models": ["model1", "model2"],
            "description": "Latency spike detected"
        }
        
        # Convert to AnomalyDetail
        detail = agent._create_anomaly_detail(llm_anomaly)
        
        # Verify conversion
        assert isinstance(detail, AnomalyDetail)
        assert detail.metric_name == "latency_spike"
        assert detail.severity == AnomalySeverity.HIGH
        assert detail.description == "Latency spike detected"
        assert isinstance(detail.timestamp, datetime)
        assert detail.actual_value == 0.0  # Default value
        assert detail.expected_value == 0.0  # Default value
        assert detail.deviation_percentage == 0.0  # Default value
        assert detail.z_score == 0.0  # Default value
    
    def test_convert_anomaly_details_list(self):
        """Test conversion of multiple anomaly details."""
        agent = DataSubAgent(
            llm_manager=MagicMock(),
            tool_dispatcher=MagicMock()
        )
        
        # Multiple LLM anomalies
        llm_anomalies = [
            {
                "type": "error_surge",
                "severity": "critical",
                "description": "Error rate increased"
            },
            {
                "type": "cost_anomaly",
                "severity": "medium",
                "description": "Unexpected cost increase"
            }
        ]
        
        # Convert list
        converted = agent._convert_anomaly_details(llm_anomalies)
        
        # Verify
        assert len(converted) == 2
        assert all(isinstance(item, dict) for item in converted)
        assert converted[0]['metric_name'] == "error_surge"
        assert converted[1]['metric_name'] == "cost_anomaly"
    
    def test_anomaly_response_creation_with_conversion(self):
        """Test creating AnomalyDetectionResponse with LLM format."""
        agent = DataSubAgent(
            llm_manager=MagicMock(),
            tool_dispatcher=MagicMock()
        )
        
        # LLM response with wrong format
        result_dict = {
            "anomalies_detected": True,
            "anomaly_count": 1,
            "anomaly_details": [
                {
                    "type": "latency_spike",
                    "timestamp": "2025-08-15T12:00:00Z",
                    "severity": "high",
                    "description": "High latency detected"
                }
            ],
            "confidence_score": 0.9,
            "recommended_actions": ["Investigate model performance"]
        }
        
        # Try conversion
        response = agent._try_anomaly_detection_conversion(result_dict)
        
        # Verify successful conversion
        assert isinstance(response, AnomalyDetectionResponse)
        assert response.anomalies_detected is True
        assert response.anomaly_count == 1
        assert len(response.anomaly_details) == 1
        # anomaly_details contains AnomalyDetail objects, not dicts
        first_detail = response.anomaly_details[0]
        if isinstance(first_detail, dict):
            assert first_detail['metric_name'] == "latency_spike"
        else:
            assert first_detail.metric_name == "latency_spike"
        assert response.confidence_score == 0.9
    
    def test_fallback_for_invalid_anomaly_format(self):
        """Test fallback when anomaly format is completely invalid."""
        agent = DataSubAgent(
            llm_manager=MagicMock(),
            tool_dispatcher=MagicMock()
        )
        
        # Invalid format
        result_dict = {
            "anomalies_detected": "not_a_boolean",  # Wrong type
            "anomaly_details": "not_a_list",  # Wrong type
        }
        
        # Should return fallback
        response = agent._try_anomaly_detection_conversion(result_dict)
        
        # Verify fallback DataAnalysisResponse
        from app.schemas.shared_types import DataAnalysisResponse
        assert isinstance(response, DataAnalysisResponse)
        assert response.query == "unknown"
        assert response.error is not None
    
    def test_severity_mapping(self):
        """Test severity string to enum mapping."""
        agent = DataSubAgent(
            llm_manager=MagicMock(),
            tool_dispatcher=MagicMock()
        )
        
        # Test all severity levels
        severities = [
            ("low", AnomalySeverity.LOW),
            ("medium", AnomalySeverity.MEDIUM),
            ("high", AnomalySeverity.HIGH),
            ("critical", AnomalySeverity.CRITICAL),
            ("unknown", AnomalySeverity.LOW),  # Default
            ("", AnomalySeverity.LOW),  # Default
        ]
        
        for input_severity, expected_enum in severities:
            llm_anomaly = {
                "type": "test",
                "severity": input_severity
            }
            detail = agent._create_anomaly_detail(llm_anomaly)
            assert detail.severity == expected_enum
    
    def test_timestamp_parsing(self):
        """Test various timestamp formats."""
        agent = DataSubAgent(
            llm_manager=MagicMock(),
            tool_dispatcher=MagicMock()
        )
        
        # Valid ISO format
        llm_anomaly = {
            "type": "test",
            "timestamp": "2025-08-15T12:00:00Z"
        }
        detail = agent._create_anomaly_detail(llm_anomaly)
        assert isinstance(detail.timestamp, datetime)
        
        # Invalid timestamp - should use current time
        llm_anomaly = {
            "type": "test",
            "timestamp": "invalid"
        }
        detail = agent._create_anomaly_detail(llm_anomaly)
        assert isinstance(detail.timestamp, datetime)
        
        # Missing timestamp - should use current time
        llm_anomaly = {"type": "test"}
        detail = agent._create_anomaly_detail(llm_anomaly)
        assert isinstance(detail.timestamp, datetime)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])