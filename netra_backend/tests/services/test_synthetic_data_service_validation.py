"""
Data Quality Validation Test Suite for Synthetic Data Service
Testing data quality and validation mechanisms
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.services.synthetic_data.generation_patterns import (
    generate_with_anomalies,
)
from netra_backend.app.services.synthetic_data.metrics import (
    calculate_correlation,
    detect_anomalies,
)

# Add project root to path
from netra_backend.app.services.synthetic_data_service import SyntheticDataService
from .test_synthetic_data_service_basic import (
    GenerationConfig,
    ValidationResult,
)

# Add project root to path


@pytest.fixture
def validation_service():
    return SyntheticDataService()


# ==================== Test Suite: Data Quality Validation ====================

class TestDataQualityValidation:
    """Test data quality and validation mechanisms"""
    async def test_schema_validation(self, validation_service):
        """Test schema validation of generated records"""
        valid_record = {
            "trace_id": str(uuid.uuid4()),
            "span_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "workload_type": "simple_chat",
            "latency_ms": 150,
            "status": "success"
        }
        
        invalid_record = {
            "trace_id": "invalid-uuid",
            "timestamp": "not-a-timestamp",
            "latency_ms": "not-a-number"
        }
        
        assert validation_service.validate_schema(valid_record) == True
        assert validation_service.validate_schema(invalid_record) == False
    async def test_statistical_distribution_validation(self, validation_service):
        """Test validation of statistical distributions"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        validation_result = await validation_service.validate_distribution(
            records,
            expected_distribution="normal",
            tolerance=0.05
        )
        
        assert validation_result.chi_square_p_value > 0.05
        assert validation_result.ks_test_p_value > 0.05
        assert validation_result.distribution_match == True
    async def test_referential_integrity_validation(self, validation_service):
        """Test referential integrity in trace hierarchies"""
        traces = await validation_service.generate_trace_hierarchies(num_traces=10)
        
        validation_result = await validation_service.validate_referential_integrity(traces)
        
        assert validation_result.valid_parent_child_relationships == True
        assert validation_result.temporal_ordering_valid == True
        assert validation_result.orphaned_spans == 0
    async def test_temporal_consistency_validation(self, validation_service):
        """Test temporal consistency of generated data"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(
                num_traces=1000,
                time_window_hours=24
            )
        )
        
        validation_result = await validation_service.validate_temporal_consistency(records)
        
        assert validation_result.all_within_window == True
        assert validation_result.chronological_order == True
        assert validation_result.no_future_timestamps == True
    async def test_data_completeness_validation(self, validation_service):
        """Test data completeness and required fields"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=100)
        )
        
        required_fields = ["trace_id", "span_id", "timestamp", "workload_type"]
        
        validation_result = await validation_service.validate_completeness(
            records,
            required_fields=required_fields
        )
        
        assert validation_result.all_required_fields_present == True
        assert validation_result.null_value_percentage < 0.01
    async def test_anomaly_detection_in_generated_data(self, validation_service):
        """Test anomaly detection in generated data"""
        config = GenerationConfig(
            num_traces=1000,
            anomaly_injection_rate=0.05
        )
        
        # Mock generate function
        async def mock_generate_fn(config, corpus, idx):
            return {
                'trace_id': f'trace_{idx}',
                'latency_ms': 100,
                'status': 'success'
            }
        
        records = await generate_with_anomalies(config, mock_generate_fn)
        
        detected_anomalies = await detect_anomalies(records)
        
        # Should detect approximately 5% anomalies
        anomaly_rate = len(detected_anomalies) / len(records)
        assert 0.04 <= anomaly_rate <= 0.06
    async def test_correlation_preservation(self, validation_service):
        """Test preservation of correlations in generated data"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        # Test correlation between complexity and latency
        correlation = await calculate_correlation(
            records,
            field1="tool_count",
            field2="latency_ms"
        )
        
        assert correlation > 0.5  # Positive correlation expected
    async def test_quality_metrics_calculation(self, validation_service):
        """Test calculation of quality metrics"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        metrics = await validation_service.calculate_quality_metrics(records)
        
        assert metrics.validation_pass_rate > 0.95
        assert metrics.distribution_divergence < 0.1
        assert metrics.temporal_consistency > 0.98
        assert metrics.corpus_coverage > 0.5
    async def test_data_diversity_validation(self, validation_service):
        """Test diversity of generated data"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        diversity_metrics = await validation_service.calculate_diversity(records)
        
        assert diversity_metrics.unique_traces == 1000
        assert diversity_metrics.workload_type_entropy > 1.0
        assert diversity_metrics.tool_usage_variety > 10
    async def test_validation_report_generation(self, validation_service):
        """Test comprehensive validation report generation"""
        records = await validation_service.generate_synthetic_data(
            GenerationConfig(num_traces=1000)
        )
        
        report = await validation_service.generate_validation_report(records)
        
        assert "schema_validation" in report
        assert "statistical_validation" in report
        assert "quality_metrics" in report
        assert report["overall_quality_score"] > 0.9


# ==================== Test Runner ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])