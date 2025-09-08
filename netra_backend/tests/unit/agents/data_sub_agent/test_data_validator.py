"""
Unit Tests for Data Validator

Tests the data validation functionality including request validation,
raw data quality checks, analysis result validation, and quality scoring.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Data quality assurance and reliable analytics
- Value Impact: Prevents incorrect insights that could impact revenue
- Strategic Impact: Critical for data integrity and trustworthy analysis
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.agents.data_sub_agent.data_validator import DataValidator

# Test markers for unified test runner
pytestmark = [
    pytest.mark.env_test,    # For test environment compatibility
    pytest.mark.unit,        # Unit test marker
    pytest.mark.agents       # Agents category marker
]


class TestDataValidatorInitialization:
    """Test DataValidator initialization and configuration."""
    
    def test_data_validator_initialization(self):
        """Test DataValidator initialization with default thresholds."""
        validator = DataValidator()
        
        # Check thresholds are set
        assert validator.thresholds["min_data_points"] == 10
        assert validator.thresholds["max_null_percentage"] == 20.0
        assert validator.thresholds["min_time_span_hours"] == 1.0
        assert validator.thresholds["max_outlier_percentage"] == 10.0
        
        # Check valid analysis types
        assert "performance" in validator.valid_analysis_types
        assert "cost_optimization" in validator.valid_analysis_types
        assert "trend_analysis" in validator.valid_analysis_types
        
        # Check valid metrics configuration
        assert "latency_ms" in validator.valid_metrics
        assert "cost_cents" in validator.valid_metrics
        assert "throughput" in validator.valid_metrics
        
        # Check logger is initialized
        assert validator.logger is not None


class TestAnalysisRequestValidation:
    """Test analysis request validation."""
    
    @pytest.fixture
    def validator(self):
        """Create DataValidator instance for testing."""
        return DataValidator()
    
    def test_validate_valid_analysis_request(self, validator):
        """Test validation of a valid analysis request."""
        request = {
            "type": "performance",
            "timeframe": "24h",
            "metrics": ["latency_ms", "cost_cents"]
        }
        
        valid, errors = validator.validate_analysis_request(request)
        
        assert valid is True
        assert len(errors) == 0
    
    def test_validate_request_missing_type(self, validator):
        """Test validation fails when type is missing."""
        request = {
            "timeframe": "24h"
        }
        
        valid, errors = validator.validate_analysis_request(request)
        
        assert valid is False
        assert "Analysis type is required" in errors


class TestRawDataValidation:
    """Test raw data quality validation."""
    
    @pytest.fixture
    def validator(self):
        """Create DataValidator instance for testing."""
        return DataValidator()
    
    @pytest.fixture
    def sample_valid_data(self):
        """Create sample valid data for testing."""
        base_time = datetime.now()
        return [
            {
                "timestamp": (base_time - timedelta(hours=i)).isoformat(),
                "user_id": f"user_{i}",
                "workload_id": f"workload_{i}",
                "latency_ms": 100.0 + i * 10,
                "cost_cents": 2.0 + i * 0.5,
                "throughput": 50.0 + i * 5
            }
            for i in range(15)
        ]
    
    def test_validate_empty_data(self, validator):
        """Test validation fails with empty data."""
        valid, result = validator.validate_raw_data([], [])
        
        assert valid is False
        assert result["valid"] is False
        assert "No data provided for validation" in result["errors"]
        assert result["data_points"] == 0


class TestQualityScoring:
    """Test quality score calculation."""
    
    @pytest.fixture
    def validator(self):
        """Create DataValidator instance for testing."""
        return DataValidator()
    
    def test_calculate_quality_score_perfect_data(self, validator):
        """Test quality score calculation for perfect data."""
        validation_result = {
            "errors": [],
            "warnings": [],
            "data_points": 50  # Well above minimum threshold
        }
        
        score = validator._calculate_quality_score(validation_result)
        
        assert score >= 1.0  # Perfect score, may have bonus
        assert score <= 1.1  # Capped at maximum


if __name__ == "__main__":
    pytest.main([__file__, "-v"])