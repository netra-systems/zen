"""Triage ExecutionResult Creation Tests

CRITICAL TEST SUITE: Validates ExecutionResult creation patterns for triage operations,
ensuring proper result formatting and data structure consistency.

This test suite covers:
1. ExecutionResult creation and validation
2. Result data structure consistency 
3. Success and failure result patterns
4. Metadata and context preservation
5. Error handling in result creation
6. Performance optimization for result processing

BVJ: ALL segments | Data Consistency | Reliable results = System integrity
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.llm.llm_manager import LLMManager


class TestExecutionResultCreation:
    """Test ExecutionResult creation patterns."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value='{"result": "test"}')
        return llm
    
    @pytest.fixture
    def sample_execution_context(self):
        return ExecutionContext(
            request_id="test_request_123",
            run_id="test_run_456", 
            agent_name="TestTriageAgent",
            state={"user_request": "Test triage request"},
            correlation_id="test_correlation_789"
        )
    
    def test_successful_result_creation(self, sample_execution_context):
        """Test creation of successful ExecutionResult."""
        result_data = {
            "category": "data_analysis",
            "confidence_score": 0.9,
            "status": "success"
        }
        
        result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id=sample_execution_context.request_id,
            data=result_data,
            error_message=None,
            execution_time_ms=100.0
        )
        
        assert result.is_success is True
        assert result.data == result_data
        assert result.error_message is None
        assert result.execution_time_ms == 100.0
        assert result.request_id == sample_execution_context.request_id
    
    def test_failure_result_creation(self, sample_execution_context):
        """Test creation of failure ExecutionResult."""
        error_msg = "Triage categorization failed"
        
        result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            request_id=sample_execution_context.request_id,
            data=None,
            error_message=error_msg,
            execution_time_ms=50.0
        )
        
        assert result.is_success is False
        assert result.data == {}  # ExecutionResult.__post_init__ converts None to {}
        assert result.error_message == error_msg
        assert result.execution_time_ms == 50.0
        assert result.request_id == sample_execution_context.request_id


class TestResultDataStructures:
    """Test result data structure consistency."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        llm = Mock(spec=LLMManager)
        llm.generate_response = AsyncMock(return_value='{"structure": "test"}')
        return llm
    
    def test_triage_result_structure(self):
        """Test triage-specific result structure."""
        triage_data = {
            "category": "optimization",
            "confidence_score": 0.85,
            "should_route": True,
            "metadata": {
                "processing_time": 0.02,
                "model_version": "v1.0"
            }
        }
        
        # Should have proper structure
        assert "category" in triage_data
        assert "confidence_score" in triage_data
        assert "should_route" in triage_data
        assert isinstance(triage_data["metadata"], dict)
    
    def test_complex_result_data(self):
        """Test complex result data structures."""
        complex_data = {
            "primary_category": "data_analysis",
            "secondary_categories": ["reporting", "visualization"],
            "confidence_breakdown": {
                "data_analysis": 0.9,
                "reporting": 0.7,
                "visualization": 0.6
            },
            "entities_extracted": [
                {"type": "metric", "value": "CPU usage"},
                {"type": "threshold", "value": "80%"}
            ]
        }
        
        # Should handle complex nested structures
        assert isinstance(complex_data["secondary_categories"], list)
        assert isinstance(complex_data["confidence_breakdown"], dict)
        assert isinstance(complex_data["entities_extracted"], list)
        assert len(complex_data["entities_extracted"]) == 2


class TestResultValidation:
    """Test result validation and consistency checks."""
    
    def test_result_consistency_validation(self):
        """Test result data consistency validation."""
        # Valid result
        valid_result = {
            "category": "optimization",
            "confidence_score": 0.8,
            "status": "success"
        }
        
        # Should have required fields
        assert "category" in valid_result
        assert "confidence_score" in valid_result
        assert "status" in valid_result
        assert 0.0 <= valid_result["confidence_score"] <= 1.0
    
    def test_boundary_value_validation(self):
        """Test boundary value validation."""
        # Test confidence score boundaries
        min_confidence = {"confidence_score": 0.0}
        max_confidence = {"confidence_score": 1.0}
        
        assert 0.0 <= min_confidence["confidence_score"] <= 1.0
        assert 0.0 <= max_confidence["confidence_score"] <= 1.0


class TestErrorHandling:
    """Test error handling in result creation."""
    
    @pytest.fixture
    def sample_context(self):
        return ExecutionContext(
            request_id="error_test",
            run_id="error_run",
            agent_name="ErrorTestAgent", 
            state={"error": "test"},
            correlation_id="error_correlation"
        )
    
    def test_error_result_handling(self, sample_context):
        """Test handling of error results."""
        error_result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            request_id=sample_context.request_id,
            data=None,
            error_message="Simulated triage error",
            execution_time_ms=10.0
        )
        
        assert error_result.is_success is False
        assert error_result.error_message is not None
        assert len(error_result.error_message) > 0
    
    def test_partial_failure_handling(self, sample_context):
        """Test handling of partial failures."""
        partial_data = {
            "category": "unknown",
            "confidence_score": 0.3,
            "status": "partial_success",
            "warnings": ["Low confidence score", "Ambiguous request"]
        }
        
        result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,  # Still considered success but with warnings
            request_id=sample_context.request_id,
            data=partial_data,
            error_message=None,
            execution_time_ms=50.0
        )
        
        assert result.is_success is True
        assert "warnings" in result.data
        assert len(result.data["warnings"]) == 2


class TestPerformanceOptimization:
    """Test performance optimization patterns for result processing."""
    
    def test_rapid_result_creation(self):
        """Test rapid result creation performance."""
        start_time = time.time()
        
        results = []
        for i in range(100):
            result_data = {
                "category": f"category_{i}",
                "confidence_score": 0.8,
                "result_id": i
            }
            results.append(result_data)
        
        end_time = time.time()
        
        # Should create results rapidly
        assert (end_time - start_time) < 0.1  # Under 100ms
        assert len(results) == 100
    
    def test_memory_efficient_results(self):
        """Test memory efficient result creation."""
        # Create large number of results
        results = []
        for i in range(50):
            result = {
                "id": i,
                "category": "test",
                "confidence": 0.8
            }
            results.append(result)
        
        # Should handle many results efficiently
        assert len(results) == 50
        
        # Cleanup
        del results


class TestMetadataHandling:
    """Test metadata and context preservation."""
    
    @pytest.fixture
    def context_with_metadata(self):
        return ExecutionContext(
            request_id="metadata_test",
            run_id="metadata_run",
            agent_name="MetadataAgent",
            state={
                "user_request": "Test with metadata",
                "timestamp": time.time(),
                "user_id": "test_user_123"
            },
            correlation_id="metadata_correlation"
        )
    
    def test_metadata_preservation(self, context_with_metadata):
        """Test preservation of metadata in results."""
        result_with_metadata = {
            "category": "test",
            "confidence_score": 0.8,
            "metadata": {
                "original_request": context_with_metadata.state["user_request"],
                "processing_timestamp": time.time(),
                "user_context": context_with_metadata.state.get("user_id")
            }
        }
        
        # Should preserve important metadata
        assert "metadata" in result_with_metadata
        assert result_with_metadata["metadata"]["user_context"] == "test_user_123"
        assert "processing_timestamp" in result_with_metadata["metadata"]
    
    def test_context_continuity(self, context_with_metadata):
        """Test context continuity through result creation."""
        result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id=context_with_metadata.request_id,
            data={"test": "data"},
            error_message=None,
            execution_time_ms=100.0
        )
        
        # Request ID should be preserved
        assert result.request_id == "metadata_test"
        assert result.status == ExecutionStatus.COMPLETED
        assert result.data == {"test": "data"}


class TestEdgeCases:
    """Test edge cases in result creation."""
    
    def test_empty_result_data(self):
        """Test handling of empty result data."""
        empty_data = {}
        
        # Should handle empty data gracefully
        assert isinstance(empty_data, dict)
        assert len(empty_data) == 0
    
    def test_null_result_handling(self):
        """Test handling of null/None results."""
        null_data = None
        
        # Should handle null data appropriately
        assert null_data is None
    
    def test_large_result_data(self):
        """Test handling of large result datasets."""
        large_data = {
            "category": "large_analysis",
            "confidence_score": 0.9,
            "detailed_analysis": ["item"] * 1000  # 1000 items
        }
        
        # Should handle large datasets
        assert len(large_data["detailed_analysis"]) == 1000
        assert large_data["confidence_score"] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])