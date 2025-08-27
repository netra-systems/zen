"""Additional test for DataValidator - Iteration 81

Tests malformed data structure handling for data integrity validation.
"""

import pytest
from datetime import datetime, timedelta

from netra_backend.app.agents.data_sub_agent.data_validator import DataValidator


class TestDataValidatorIteration81:
    """Test DataValidator for malformed data structure handling."""

    @pytest.fixture
    def validator(self):
        """Create a DataValidator instance for testing."""
        return DataValidator()

    def test_validate_malformed_data_structures_iteration_81(self, validator):
        """Test validation of malformed data structures - Iteration 81."""
        now = datetime.now()
        
        # Test malformed data with type mismatches
        malformed_data = [
            {"timestamp": now, "user_id": "user_1", "latency_ms": 150.0, "cost_cents": 2.5},
            {"timestamp": now - timedelta(minutes=10), "user_id": "user_2", "latency_ms": "invalid", "cost_cents": 3.0},
            {"timestamp": now - timedelta(minutes=20), "user_id": "user_3", "latency_ms": True, "cost_cents": False},
        ] * 5

        metrics = ["latency_ms", "cost_cents"]
        is_valid, result = validator.validate_raw_data(malformed_data, metrics)
        
        # Should flag malformed data
        assert not is_valid
        assert len(result.get("errors", [])) > 0
        assert result.get("quality_score", 1.0) < 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
