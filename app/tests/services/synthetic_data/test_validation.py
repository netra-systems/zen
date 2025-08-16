"""
Tests for data validation, quality metrics, and anomaly detection
"""

import pytest
import uuid
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock

from app.services.synthetic_data_service import SyntheticDataService
from app.services.synthetic_data.validators import validate_schema, validate_distribution, validate_referential_integrity, validate_temporal_consistency, validate_completeness


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()
class TestValidationMethods:
    """Test data validation methods"""
    
    def test_validate_schema_valid(self, service):
        """Test schema validation with valid record"""
        record = {
            "trace_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "workload_type": "test",
            "latency_ms": 100
        }
        
        assert validate_schema(record) == True
    
    def test_validate_schema_missing_fields(self, service):
        """Test schema validation with missing required fields"""
        record = {"data": "incomplete"}
        
        assert validate_schema(record) == False
    
    def test_validate_schema_invalid_uuid(self, service):
        """Test schema validation with invalid UUID"""
        record = {
            "trace_id": "not-a-uuid",
            "timestamp": datetime.now(UTC).isoformat(),
            "workload_type": "test"
        }
        
        assert validate_schema(record) == False
    
    def test_validate_schema_invalid_timestamp(self, service):
        """Test schema validation with invalid timestamp"""
        record = {
            "trace_id": str(uuid.uuid4()),
            "timestamp": "not-a-timestamp",
            "workload_type": "test"
        }
        
        assert validate_schema(record) == False
    
    async def test_validate_distribution(self, service):
        """Test statistical distribution validation"""
        records = [{"latency_ms": i} for i in range(100)]
        
        result = await validate_distribution(records)
        
        assert hasattr(result, 'chi_square_p_value')
        assert hasattr(result, 'ks_test_p_value')
        assert hasattr(result, 'distribution_match')
    
    async def test_validate_referential_integrity(self, service):
        """Test referential integrity validation"""
        traces = [
            {
                "spans": [
                    {"span_id": "1", "parent_span_id": None, "start_time": datetime.now(UTC), "end_time": datetime.now(UTC) + timedelta(seconds=1)},
                    {"span_id": "2", "parent_span_id": "1", "start_time": datetime.now(UTC), "end_time": datetime.now(UTC) + timedelta(seconds=1)}
                ]
            }
        ]
        
        result = await validate_referential_integrity(traces)
        
        assert hasattr(result, 'valid_parent_child_relationships')
        assert hasattr(result, 'temporal_ordering_valid')
        assert hasattr(result, 'orphaned_spans')
    
    async def test_validate_temporal_consistency(self, service):
        """Test temporal consistency validation"""
        records = [
            {"timestamp_utc": datetime.now(UTC) - timedelta(hours=1)},
            {"timestamp_utc": datetime.now(UTC)}
        ]
        
        result = await validate_temporal_consistency(records)
        
        assert hasattr(result, 'all_within_window')
        assert hasattr(result, 'chronological_order')
        assert hasattr(result, 'no_future_timestamps')
    
    async def test_validate_completeness(self, service):
        """Test data completeness validation"""
        records = [
            {"field1": "value1", "field2": "value2"},
            {"field1": "value1", "field2": None},
            {"field1": None, "field2": "value2"}
        ]
        required_fields = ["field1", "field2"]
        
        result = await validate_completeness(records, required_fields)
        
        assert hasattr(result, 'all_required_fields_present')
        assert hasattr(result, 'null_value_percentage')
        assert result.null_value_percentage == 2/6  # 2 null values out of 6 total field checks
class TestQualityAndDiversityMetrics:
    """Test quality and diversity metrics calculation"""
    
    @pytest.mark.skip(reason="calculate_quality_metrics method not implemented in SyntheticDataService")
    async def test_calculate_quality_metrics(self, service):
        """Test quality metrics calculation"""
        records = [
            {"trace_id": str(uuid.uuid4()), "timestamp": datetime.now(UTC).isoformat(), "workload_type": "test"},
            {"trace_id": "invalid", "timestamp": "invalid", "workload_type": "test"}  # Invalid record
        ]
        
        metrics = await service.calculate_quality_metrics(records)
        
        assert hasattr(metrics, 'validation_pass_rate')
        assert hasattr(metrics, 'distribution_divergence')
        assert hasattr(metrics, 'temporal_consistency')
        assert hasattr(metrics, 'corpus_coverage')
        assert 0 <= metrics.validation_pass_rate <= 1
    
    @pytest.mark.skip(reason="calculate_diversity method not implemented in SyntheticDataService")
    async def test_calculate_diversity(self, service):
        """Test diversity metrics calculation"""
        records = [
            {"trace_id": "trace1", "workload_type": "type1", "tool_invocations": ["tool1", "tool2"]},
            {"trace_id": "trace2", "workload_type": "type2", "tool_invocations": ["tool2", "tool3"]},
            {"trace_id": "trace1", "workload_type": "type1", "tool_invocations": ["tool1"]}  # Duplicate trace
        ]
        
        metrics = await service.calculate_diversity(records)
        
        assert hasattr(metrics, 'unique_traces')
        assert hasattr(metrics, 'workload_type_entropy')
        assert hasattr(metrics, 'tool_usage_variety')
        assert metrics.unique_traces == 2  # Only 2 unique trace IDs
        assert metrics.tool_usage_variety == 3  # 3 unique tools
    
    @pytest.mark.skip(reason="generate_validation_report method not implemented in SyntheticDataService")
    async def test_generate_validation_report(self, service):
        """Test comprehensive validation report generation"""
        records = [
            {"trace_id": str(uuid.uuid4()), "timestamp": datetime.now(UTC).isoformat(), "workload_type": "test"}
        ]
        
        report = await service.generate_validation_report(records)
        
        assert "schema_validation" in report
        assert "statistical_validation" in report
        assert "quality_metrics" in report
        assert "overall_quality_score" in report
        assert 0 <= report["overall_quality_score"] <= 1