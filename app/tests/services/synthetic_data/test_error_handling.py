"""
Tests for error handling, circuit breaker, and anomaly scenarios
"""

import pytest
from unittest.mock import MagicMock

from app.services.synthetic_data_service import SyntheticDataService


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()


@pytest.mark.asyncio
class TestCircuitBreakerAndErrorHandling:
    """Test circuit breaker and error handling functionality"""
    
    @pytest.mark.skip(reason="Circuit breaker not yet implemented in SyntheticDataService")
    def test_get_circuit_breaker(self, service):
        """Test circuit breaker creation"""
        cb = service.get_circuit_breaker(failure_threshold=2, timeout_seconds=1)
        
        assert hasattr(cb, 'failure_threshold')
        assert hasattr(cb, 'timeout')
        assert hasattr(cb, 'call')
        assert hasattr(cb, 'is_open')
        assert cb.failure_threshold == 2
        assert cb.timeout == 1
    
    @pytest.mark.skip(reason="Circuit breaker not yet implemented in SyntheticDataService")
    async def test_circuit_breaker_functionality(self, service):
        """Test circuit breaker operation"""
        cb = service.get_circuit_breaker(failure_threshold=2)
        
        # Test successful call
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        assert result == "success"
        assert not cb.is_open()
        
        # Test failing calls
        async def fail_func():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception):
            await cb.call(fail_func)
        
        # Second failure - should open circuit
        with pytest.raises(Exception):
            await cb.call(fail_func)
        
        # Circuit should now be open
        assert cb.is_open()


@pytest.mark.asyncio
class TestErrorScenarios:
    """Test various error scenarios and edge cases"""
    
    async def test_generate_with_anomalies_method(self, service):
        """Test anomaly generation method through generate_batch"""
        from app.services.synthetic_data.generation_patterns import generate_with_anomalies
        
        config = MagicMock()
        config.num_traces = 10
        config.anomaly_injection_rate = 1.0  # 100% anomalies
        
        # Use the pattern function directly with a mock generate function
        async def mock_generate_single(config, corpus_id, index):
            return {
                "event_id": f"event_{index}",
                "latency_ms": 100,
                "status": "success"
            }
        
        records = await generate_with_anomalies(config, mock_generate_single)
        
        assert len(records) == 10
        anomaly_count = sum(1 for r in records if r.get('anomaly', False))
        assert anomaly_count > 0  # Should have some anomalies
    
    async def test_detect_anomalies(self, service):
        """Test anomaly detection"""
        from app.services.synthetic_data.metrics import detect_anomalies
        
        records = [
            {"event_id": "1", "anomaly": True, "anomaly_type": "spike"},
            {"event_id": "2", "anomaly": False},
            {"event_id": "3", "anomaly": True, "anomaly_type": "failure"}
        ]
        
        anomalies = await detect_anomalies(records)
        
        assert len(anomalies) == 2
        for anomaly in anomalies:
            assert "record_id" in anomaly
            assert "anomaly_type" in anomaly
            assert "severity" in anomaly
    
    async def test_calculate_correlation(self, service):
        """Test correlation calculation between fields"""
        from app.services.synthetic_data.metrics import calculate_correlation
        
        records = [
            {"field1": 1, "field2": 2},
            {"field1": 2, "field2": 4},
            {"field1": 3, "field2": 6}
        ]
        
        correlation = await calculate_correlation(records, "field1", "field2")
        
        assert isinstance(correlation, float)
        assert -1 <= correlation <= 1
        assert correlation == pytest.approx(1.0, rel=0.01)  # Perfect positive correlation
    
    async def test_calculate_correlation_no_data(self, service):
        """Test correlation calculation with insufficient data"""
        from app.services.synthetic_data.metrics import calculate_correlation
        
        records = [{"field1": 1}]  # Only one record
        
        correlation = await calculate_correlation(records, "field1", "field2")
        
        assert correlation == 0.0
    
    async def test_calculate_correlation_invalid_data(self, service):
        """Test correlation calculation with invalid data"""
        from app.services.synthetic_data.metrics import calculate_correlation
        
        records = [
            {"field1": "not_a_number", "field2": "also_not_a_number"},
            {"field1": 2, "field2": 4}
        ]
        
        correlation = await calculate_correlation(records, "field1", "field2")
        
        # Should handle invalid data gracefully
        assert isinstance(correlation, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])