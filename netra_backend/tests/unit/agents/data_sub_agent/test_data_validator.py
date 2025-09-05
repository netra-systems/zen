"""
Comprehensive Unit Tests for DataValidator

Tests all data validation operations including request validation,
raw data quality checks, analysis result validation, and quality scoring.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Data quality assurance and reliable analytics
- Value Impact: Prevents incorrect insights that could impact revenue
- Strategic Impact: Critical for data integrity and trustworthy analysis
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from netra_backend.app.agents.data_sub_agent.data_validator import DataValidator
from test_framework.decorators import mock_justified

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
        
        # Check valid metrics are defined
        assert "latency_ms" in validator.valid_metrics
        assert "cost_cents" in validator.valid_metrics
        assert "throughput" in validator.valid_metrics
        
        # Check metric configurations
        latency_config = validator.valid_metrics["latency_ms"]
        assert latency_config["min"] == 0
        assert latency_config["max"] == 30000
        assert latency_config["type"] == "float"
        
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
    
    def test_validate_request_missing_timeframe(self, validator):
        """Test validation fails when timeframe is missing."""
        request = {
            "type": "performance"
        }
        
        valid, errors = validator.validate_analysis_request(request)
        
        assert valid is False
        assert "Timeframe is required" in errors
    
    def test_validate_request_invalid_type(self, validator):
        """Test validation fails with invalid analysis type."""
        request = {
            "type": "invalid_type",
            "timeframe": "24h"
        }
        
        valid, errors = validator.validate_analysis_request(request)
        
        assert valid is False
        assert any("Invalid analysis type" in error for error in errors)
    
    @pytest.mark.parametrize("timeframe,should_be_valid", [
        ("24h", True),
        ("7d", True),
        ("2w", True),
        ("30d", True),
        ("1h", True),
        ("invalid", False),
        ("24", False),
        ("h", False),
        ("24hours", False),
        ("", False),
    ])
    def test_validate_timeframe_format(self, validator, timeframe, should_be_valid):
        """Test timeframe format validation with various inputs."""
        result = validator._validate_timeframe_format(timeframe)
        assert result == should_be_valid
    
    def test_validate_request_invalid_metrics(self, validator):
        """Test validation fails with invalid metrics."""
        request = {
            "type": "performance",
            "timeframe": "24h",
            "metrics": ["latency_ms", "invalid_metric", "cost_cents"]
        }
        
        valid, errors = validator.validate_analysis_request(request)
        
        assert valid is False
        assert any("Invalid metrics: ['invalid_metric']" in error for error in errors)
    
    def test_validate_request_all_valid_analysis_types(self, validator):
        """Test all valid analysis types are accepted."""
        valid_types = ["performance", "cost_optimization", "trend_analysis"]
        
        for analysis_type in valid_types:
            request = {
                "type": analysis_type,
                "timeframe": "24h"
            }
            
            valid, errors = validator.validate_analysis_request(request)
            assert valid is True, f"Analysis type '{analysis_type}' should be valid"


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
            for i in range(15)  # More than min_data_points threshold
        ]
    
    def test_validate_valid_raw_data(self, validator, sample_valid_data):
        """Test validation of good quality raw data."""
        metrics = ["latency_ms", "cost_cents", "throughput"]
        
        valid, result = validator.validate_raw_data(sample_valid_data, metrics)
        
        assert valid is True
        assert result["valid"] is True
        assert result["data_points"] == 15
        assert result["quality_score"] > 0.8  # Should be high quality
        assert len(result["errors"]) == 0
    
    def test_validate_empty_data(self, validator):
        """Test validation fails with empty data."""
        valid, result = validator.validate_raw_data([], [])
        
        assert valid is False
        assert result["valid"] is False
        assert "No data provided for validation" in result["errors"]
        assert result["data_points"] == 0
    
    def test_validate_insufficient_data_points(self, validator):
        """Test validation warns with insufficient data points."""
        minimal_data = [
            {
                "timestamp": datetime.now().isoformat(),
                "user_id": "user_1",
                "latency_ms": 100.0
            }
        ]
        
        valid, result = validator.validate_raw_data(minimal_data, ["latency_ms"])
        
        # Should be valid (no errors) but have warnings
        assert result["valid"] is True  # No errors, just warnings
        assert len(result["warnings"]) > 0
        assert any("Low data point count" in warning for warning in result["warnings"])
    
    def test_validate_data_with_missing_required_fields(self, validator):
        """Test validation identifies missing required fields."""
        data_missing_fields = [
            {"latency_ms": 100.0},  # Missing timestamp
            {"user_id": "user_1"},  # Missing timestamp
        ]
        
        valid, result = validator.validate_raw_data(data_missing_fields, [])
        
        # The validator should identify missing 'timestamp' fields
        assert not valid
        assert not result["valid"]
        assert len(result["errors"]) > 0
        # Check that at least one error mentions missing timestamp
        error_messages = " ".join(result["errors"])
        assert "timestamp" in error_messages.lower()
    
    def test_validate_data_with_high_null_percentage(self, validator):
        """Test validation identifies high null percentages."""
        data_with_nulls = []
        for i in range(15):
            row = {
                "timestamp": datetime.now().isoformat(),
                "user_id": f"user_{i}",
                "latency_ms": 100.0 if i < 5 else None  # 10/15 = 66.7% null
            }
            data_with_nulls.append(row)
        
        valid, result = validator.validate_raw_data(data_with_nulls, ["latency_ms"])
        
        # The validator should identify high null percentage in errors
        assert not valid
        assert not result["valid"]
        assert len(result["errors"]) > 0
        # Check that at least one error mentions high null percentage for latency_ms
        error_messages = " ".join(result["errors"])
        assert "latency_ms" in error_messages and ("null" in error_messages.lower() or "percentage" in error_messages.lower())
    
    def test_validate_metric_values_out_of_range(self, validator):
        """Test validation identifies out-of-range metric values."""
        data_with_outliers = [
            {
                "timestamp": datetime.now().isoformat(),
                "user_id": "user_1",
                "latency_ms": 50000.0,  # Way above max of 30000
                "cost_cents": -5.0      # Below min of 0
            }
            for _ in range(12)
        ]
        
        valid, result = validator.validate_raw_data(data_with_outliers, ["latency_ms", "cost_cents"])
        
        metrics_result = result["quality_metrics"]["metrics"]
        assert "outliers" in metrics_result
        assert "latency_ms" in metrics_result["outliers"]
        assert "cost_cents" in metrics_result["outliers"]
    
    def test_validate_invalid_metric_value_types(self, validator):
        """Test validation identifies invalid metric value types."""
        data_with_invalid_types = [
            {
                "timestamp": datetime.now().isoformat(),
                "user_id": "user_1",
                "latency_ms": "not_a_number",
                "tokens_input": "also_not_a_number"
            }
            for _ in range(12)
        ]
        
        valid, result = validator.validate_raw_data(data_with_invalid_types, ["latency_ms", "tokens_input"])
        
        assert not result["valid"]  # Should have errors
        metrics_result = result["quality_metrics"]["metrics"]
        assert len(metrics_result["errors"]) > 0
        assert any("Invalid latency_ms value" in error for error in metrics_result["errors"])
    
    def test_validate_time_span_too_short(self, validator):
        """Test validation warns about short time spans."""
        now = datetime.now()
        short_span_data = [
            {
                "timestamp": (now + timedelta(minutes=i)).isoformat(),
                "user_id": f"user_{i}",
                "latency_ms": 100.0
            }
            for i in range(12)  # Only 11 minutes span
        ]
        
        valid, result = validator.validate_raw_data(short_span_data, [])
        
        time_result = result["quality_metrics"]["time_span"]
        assert "warning" in time_result
        assert "Short time span" in time_result["warning"]


class TestAnalysisResultValidation:
    """Test analysis result validation."""
    
    @pytest.fixture
    def validator(self):
        """Create DataValidator instance for testing."""
        return DataValidator()
    
    @pytest.fixture
    def valid_analysis_result(self):
        """Create valid analysis result for testing."""
        return {
            "summary": "Performance analysis completed",
            "findings": [
                "Average latency increased by 15%",
                "Cost optimization opportunities identified"
            ],
            "recommendations": [
                "Consider optimizing slow queries",
                "Implement caching for frequent requests"
            ],
            "cost_savings": {
                "savings_percentage": 12.5,
                "total_potential_savings_cents": 150.0
            }
        }
    
    def test_validate_valid_analysis_result(self, validator, valid_analysis_result):
        """Test validation of a valid analysis result."""
        valid, errors = validator.validate_analysis_result(valid_analysis_result)
        
        assert valid is True
        assert len(errors) == 0
    
    def test_validate_result_missing_required_fields(self, validator):
        """Test validation fails when required fields are missing."""
        incomplete_result = {
            "summary": "Analysis completed"
            # Missing findings and recommendations
        }
        
        valid, errors = validator.validate_analysis_result(incomplete_result)
        
        assert valid is False
        assert "Missing required field: findings" in errors
        assert "Missing required field: recommendations" in errors
    
    def test_validate_result_invalid_findings_format(self, validator):
        """Test validation fails with invalid findings format."""
        result_invalid_findings = {
            "summary": "Analysis completed",
            "findings": "Not a list",  # Should be a list
            "recommendations": []
        }
        
        valid, errors = validator.validate_analysis_result(result_invalid_findings)
        
        assert valid is False
        assert "Findings must be a list" in errors
    
    def test_validate_result_empty_findings(self, validator):
        """Test validation fails with empty findings."""
        result_empty_findings = {
            "summary": "Analysis completed",
            "findings": [],  # Empty findings
            "recommendations": ["Some recommendation"]
        }
        
        valid, errors = validator.validate_analysis_result(result_empty_findings)
        
        assert valid is False
        assert "Analysis should produce at least one finding" in errors
    
    def test_validate_result_invalid_recommendations_format(self, validator):
        """Test validation fails with invalid recommendations format."""
        result_invalid_recommendations = {
            "summary": "Analysis completed",
            "findings": ["Some finding"],
            "recommendations": "Not a list"  # Should be a list
        }
        
        valid, errors = validator.validate_analysis_result(result_invalid_recommendations)
        
        assert valid is False
        assert "Recommendations must be a list" in errors
    
    def test_validate_cost_savings_invalid_percentage(self, validator):
        """Test validation fails with invalid savings percentage."""
        result_invalid_savings = {
            "summary": "Analysis completed",
            "findings": ["Some finding"],
            "recommendations": ["Some recommendation"],
            "cost_savings": {
                "savings_percentage": 60.0,  # Above 50% limit
                "total_potential_savings_cents": 100.0
            }
        }
        
        valid, errors = validator.validate_analysis_result(result_invalid_savings)
        
        assert valid is False
        assert "Savings percentage must be between 0-50%" in errors
    
    def test_validate_cost_savings_negative_total(self, validator):
        """Test validation fails with negative total savings."""
        result_negative_savings = {
            "summary": "Analysis completed",
            "findings": ["Some finding"],
            "recommendations": ["Some recommendation"],
            "cost_savings": {
                "savings_percentage": 10.0,
                "total_potential_savings_cents": -50.0  # Negative savings
            }
        }
        
        valid, errors = validator.validate_analysis_result(result_negative_savings)
        
        assert valid is False
        assert "Total savings must be non-negative" in errors


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
    
    def test_calculate_quality_score_with_errors(self, validator):
        """Test quality score calculation with errors."""
        validation_result = {
            "errors": ["Error 1", "Error 2"],
            "warnings": [],
            "data_points": 20
        }
        
        score = validator._calculate_quality_score(validation_result)
        
        assert score < 1.0  # Should be penalized for errors
        assert score > 0.0  # But not zero
    
    def test_calculate_quality_score_with_warnings(self, validator):
        """Test quality score calculation with warnings."""
        validation_result = {
            "errors": [],
            "warnings": ["Warning 1", "Warning 2", "Warning 3"],
            "data_points": 15
        }
        
        score = validator._calculate_quality_score(validation_result)
        
        assert score < 1.0  # Should be penalized for warnings
        assert score > 0.7  # But not severely
    
    def test_calculate_quality_score_bonus_for_large_dataset(self, validator):
        """Test quality score gets bonus for large dataset."""
        validation_result = {
            "errors": [],
            "warnings": [],
            "data_points": 100  # Well above bonus threshold
        }
        
        score = validator._calculate_quality_score(validation_result)
        
        assert score >= 1.0  # Should be high quality score
        assert score <= 1.1  # But capped at reasonable maximum


class TestValidMetricsConfiguration:
    """Test valid metrics configuration and validation."""
    
    @pytest.fixture
    def validator(self):
        """Create DataValidator instance for testing."""
        return DataValidator()
    
    def test_all_valid_metrics_have_required_config(self, validator):
        """Test all valid metrics have required configuration."""
        for metric_name, config in validator.valid_metrics.items():
            assert "min" in config
            assert "max" in config
            assert "type" in config
            assert config["type"] in ["float", "int"]
            assert isinstance(config["min"], (int, float))
            assert isinstance(config["max"], (int, float))
            assert config["min"] <= config["max"]
    
    def test_metric_validation_respects_type_constraints(self, validator):
        """Test metric validation respects type constraints."""
        # Test float metric
        float_data = [{"latency_ms": 150.5}]
        validation = validator._validate_metric_values(float_data, ["latency_ms"])
        assert len(validation["errors"]) == 0
        
        # Test int metric
        int_data = [{"tokens_input": 1000}]
        validation = validator._validate_metric_values(int_data, ["tokens_input"])
        assert len(validation["errors"]) == 0
    
    @pytest.mark.parametrize("metric,valid_value,invalid_value", [
        ("latency_ms", 150.0, -10.0),
        ("cost_cents", 5.0, -1.0),
        ("throughput", 100.0, 20000.0),  # Above max
        ("success_rate", 0.95, 1.5),     # Above max of 1.0
        ("tokens_input", 5000, -100),    # Below min of 0
    ])
    def test_metric_range_validation(self, validator, metric, valid_value, invalid_value):
        """Test metric range validation for various metrics."""
        # Test valid value
        valid_data = [{metric: valid_value}]
        validation = validator._validate_metric_values(valid_data, [metric])
        assert metric not in validation.get("outliers", {})
        
        # Test invalid value
        invalid_data = [{metric: invalid_value}]
        validation = validator._validate_metric_values(invalid_data, [metric])
        assert metric in validation.get("outliers", {})


class TestTimeSpanValidation:
    """Test time span validation functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create DataValidator instance for testing."""
        return DataValidator()
    
    def test_validate_time_span_sufficient_duration(self, validator):
        """Test time span validation with sufficient duration."""
        now = datetime.now()
        data = [
            {"timestamp": (now - timedelta(hours=2)).isoformat()},
            {"timestamp": now.isoformat()}
        ]
        
        result = validator._validate_time_span(data)
        
        assert result["valid"] is True
        assert result["time_span_hours"] == 2.0
        assert "warning" not in result
    
    def test_validate_time_span_insufficient_duration(self, validator):
        """Test time span validation with insufficient duration."""
        now = datetime.now()
        data = [
            {"timestamp": (now - timedelta(minutes=30)).isoformat()},
            {"timestamp": now.isoformat()}
        ]
        
        result = validator._validate_time_span(data)
        
        assert result["valid"] is True  # Still valid, just with warning
        assert "warning" in result
        assert "Short time span" in result["warning"]
    
    def test_validate_time_span_insufficient_timestamps(self, validator):
        """Test time span validation with insufficient timestamps."""
        data = [{"timestamp": datetime.now().isoformat()}]
        
        result = validator._validate_time_span(data)
        
        assert result["valid"] is False
        assert "warning" in result
        assert "Insufficient timestamps" in result["warning"]
    
    def test_validate_time_span_mixed_timestamp_formats(self, validator):
        """Test time span validation handles mixed timestamp formats."""
        now = datetime.now()
        data = [
            {"timestamp": (now - timedelta(hours=1)).isoformat()},  # ISO string
            {"timestamp": now},  # datetime object
            {"timestamp": "invalid_timestamp"},  # Invalid format
        ]
        
        result = validator._validate_time_span(data)
        
        # Should still work with valid timestamps and ignore invalid ones
        assert result["valid"] is True
        assert result["time_span_hours"] == 1.0


class TestDataValidatorEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.fixture
    def validator(self):
        """Create DataValidator instance."""
        return DataValidator()
    
    def test_validate_extremely_large_dataset(self, validator):
        """Test validation with very large dataset."""
        # Generate large dataset
        now = datetime.now()
        data = []
        for i in range(1000):  # Large dataset
            data.append({
                "timestamp": now - timedelta(minutes=i),
                "user_id": f"user_{i % 100}",
                "workload_id": f"workload_{i % 50}",
                "latency_ms": 100.0 + (i % 50),
                "cost_cents": 2.0 + (i % 10) * 0.1,
                "throughput": 95.0 + (i % 20)
            })
        
        metrics = ["latency_ms", "cost_cents", "throughput"]
        is_valid, result = validator.validate_raw_data(data, metrics)
        
        # Should handle large datasets efficiently
        assert is_valid  # Performance shouldn't cause validation errors
        
    def test_validate_unicode_and_special_characters(self, validator):
        """Test validation with unicode and special characters."""
        now = datetime.now()
        data = [
            {
                "timestamp": now - timedelta(minutes=10),
                "user_id": "用户_测试_123",  # Chinese characters
                "workload_id": "wörk-löad_ñoñé",  # Accented characters
                "latency_ms": 150.0,
                "cost_cents": 2.3,
                "throughput": 100.0
            }
        ] * 15  # Ensure minimum data points
        
        metrics = ["latency_ms", "cost_cents", "throughput"]
        is_valid, result = validator.validate_raw_data(data, metrics)
        
        # Should handle unicode characters without issues
        assert is_valid
        assert len(result.get("errors", [])) == 0
        
    def test_validate_boundary_metric_values(self, validator):
        """Test validation with boundary metric values."""
        now = datetime.now()
        data = []
        
        # Test boundary values for each metric type
        boundary_cases = [
            {"latency_ms": 0.1},     # Small but positive
            {"latency_ms": 999.9},   # Large but within range
            {"cost_cents": 0.01},    # Small cost
            {"cost_cents": 99.99},   # Large cost
            {"throughput": 1.0},     # Low throughput
            {"throughput": 1999.9},  # High throughput
        ]
        
        for i, metrics in enumerate(boundary_cases * 3):  # Ensure minimum data points
            record = {
                "timestamp": now - timedelta(minutes=i * 10),
                "user_id": f"user_{i}",
                "workload_id": f"workload_{i}",
                "latency_ms": metrics.get("latency_ms", 150.0),
                "cost_cents": metrics.get("cost_cents", 2.3),
                "throughput": metrics.get("throughput", 100.0)
            }
            data.append(record)
        
        metrics = ["latency_ms", "cost_cents", "throughput"]
        is_valid, result = validator.validate_raw_data(data, metrics)
        
        # Boundary values within ranges should be valid
        assert is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])