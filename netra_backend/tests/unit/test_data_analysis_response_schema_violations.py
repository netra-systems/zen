"""Test DataAnalysisResponse Schema Violations - Failing Tests to Reproduce Bug

This test file contains INTENTIONALLY FAILING tests that reproduce the current
Pydantic validation errors in DataAnalysisResponse usage across the codebase.

These tests demonstrate the mismatch between:
1. What tests expect (query, insights, recommendations fields)  
2. What the actual schema provides (analysis_id, status, results, metrics fields)

The tests are DESIGNED TO FAIL to document the current broken state.
Once the schema is fixed, these tests should be updated to pass.
"""

import pytest
from pydantic import ValidationError
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the ACTUAL schemas that are causing the problem
from netra_backend.app.schemas.shared_types import DataAnalysisResponse
from netra_backend.app.agents.state import OptimizationsResult
from netra_backend.app.schemas.agent_models import DeepAgentState


class TestDataAnalysisResponseSchemaViolations(SSotBaseTestCase):
    """Test suite documenting DataAnalysisResponse schema violations."""
    
    def test_data_analysis_response_missing_query_field(self):
        """FAILING TEST: DataAnalysisResponse does not have 'query' field.
        
        Current ActionsAgent tests expect DataAnalysisResponse to have a 'query' field,
        but the actual schema in shared_types.py does not include this field.
        """
        # This will FAIL because DataAnalysisResponse doesn't have 'query' field
        with self.expect_exception(ValidationError):
            DataAnalysisResponse(
                query="test query",  # Field does not exist in actual schema
                results=[{"test": "data"}],
                insights={"insight": "test insight"},
                recommendations=["test recommendation"]
            )
    
    def test_data_analysis_response_missing_insights_field(self):
        """FAILING TEST: DataAnalysisResponse does not have 'insights' field.
        
        Current ActionsAgent tests expect DataAnalysisResponse to have an 'insights' field,
        but the actual schema in shared_types.py does not include this field.
        """
        # This will FAIL because DataAnalysisResponse doesn't have 'insights' field  
        with self.expect_exception(ValidationError):
            DataAnalysisResponse(
                analysis_id="test_123",
                status="completed", 
                results={"test": "data"},
                metrics={},  # This should be PerformanceMetrics, not dict
                created_at=1234567890.0,
                insights={"insight": "test insight"}  # Field does not exist
            )
    
    def test_data_analysis_response_missing_recommendations_field(self):
        """FAILING TEST: DataAnalysisResponse does not have 'recommendations' field.
        
        Current ActionsAgent tests expect DataAnalysisResponse to have a 'recommendations' field,
        but the actual schema in shared_types.py does not include this field.
        """
        # This will FAIL because DataAnalysisResponse doesn't have 'recommendations' field
        with self.expect_exception(ValidationError):
            DataAnalysisResponse(
                analysis_id="test_123",
                status="completed",
                results={"test": "data"}, 
                metrics={},  # This should be PerformanceMetrics, not dict
                created_at=1234567890.0,
                recommendations=["test recommendation"]  # Field does not exist
            )
    
    def test_data_analysis_response_wrong_metrics_type(self):
        """FAILING TEST: DataAnalysisResponse.metrics expects PerformanceMetrics, not dict.
        
        Current ActionsAgent tests pass a dict for metrics, but the actual schema
        expects a PerformanceMetrics object.
        """
        # This will FAIL because metrics should be PerformanceMetrics, not dict
        with self.expect_exception(ValidationError):
            DataAnalysisResponse(
                analysis_id="test_123", 
                status="completed",
                results={"test": "data"},
                metrics={"duration": 100},  # Should be PerformanceMetrics object
                created_at=1234567890.0
            )
    
    def test_data_analysis_response_missing_required_fields(self):
        """FAILING TEST: DataAnalysisResponse requires analysis_id, status, results, metrics, created_at.
        
        Current ActionsAgent tests try to create DataAnalysisResponse with fields
        that don't exist, while missing the fields that are actually required.
        """
        # This will FAIL because required fields are missing
        with self.expect_exception(ValidationError):
            DataAnalysisResponse(
                query="test query",  # Field doesn't exist
                results=[{"test": "data"}],  # Wrong type (list vs dict)
                insights={"insight": "test insight"},  # Field doesn't exist
                recommendations=["test recommendation"]  # Field doesn't exist
                # Missing: analysis_id, status, metrics (PerformanceMetrics), created_at
            )
    
    def test_deep_agent_state_with_invalid_data_result(self):
        """FAILING TEST: DeepAgentState.data_result creation fails with wrong schema.
        
        This reproduces the exact pattern used in ActionsAgent tests that is currently failing.
        """
        # This will FAIL because we're trying to create DataAnalysisResponse with wrong fields
        with self.expect_exception(ValidationError):
            state = DeepAgentState(
                user_request="Test request",
                data_result=DataAnalysisResponse(
                    query="test query",  # Field doesn't exist in schema
                    results=[{"test": "data"}],  # Wrong type (should be dict not list)
                    insights={"insight": "test insight"},  # Field doesn't exist
                    recommendations=["test recommendation"]  # Field doesn't exist
                ),
                optimizations_result=OptimizationsResult(
                    optimization_type="performance",
                    recommendations=["test recommendation"],
                    confidence_score=0.9
                )
            )
    
    def test_actual_schema_fields_work(self):
        """PASSING TEST: Verify the ACTUAL schema fields work correctly.
        
        This test should pass and shows what the correct schema usage looks like.
        """
        from netra_backend.app.schemas.shared_types import PerformanceMetrics
        
        # Create a valid DataAnalysisResponse using the ACTUAL schema
        valid_response = DataAnalysisResponse(
            analysis_id="test_analysis_123",
            status="completed", 
            results={"data": "test_result", "count": 42},  # Dict, not list
            metrics=PerformanceMetrics(duration_ms=150.0),  # PerformanceMetrics object
            created_at=1234567890.0
        )
        
        # Verify the object was created successfully
        self.assertIsNotNone(valid_response)
        self.assertEqual(valid_response.analysis_id, "test_analysis_123") 
        self.assertEqual(valid_response.status, "completed")
        self.assertIn("data", valid_response.results)
        self.assertEqual(valid_response.metrics.duration_ms, 150.0)
        self.assertEqual(valid_response.created_at, 1234567890.0)
    
    def test_demonstrate_schema_mismatch_root_cause(self):
        """FAILING TEST: Demonstrate the root cause of the schema mismatch.
        
        This test clearly shows the disconnect between what tests expect vs actual schema.
        """
        # What the tests EXPECT to work (but will FAIL):
        expected_fields = {
            "query": "SELECT * FROM metrics",
            "results": [{"metric": "cpu", "value": 80}],  # List format
            "insights": {"performance": "high CPU usage detected"},
            "recommendations": ["Optimize query", "Add caching"]
        }
        
        # What the ACTUAL schema requires:
        actual_schema_fields = {
            "analysis_id": "analysis_123",
            "status": "completed", 
            "results": {"cpu_metric": 80, "memory_metric": 65},  # Dict format
            "metrics": {"duration_ms": 150.0},  # Should be PerformanceMetrics object
            "created_at": 1234567890.0
        }
        
        # Attempting to use expected fields will FAIL
        with self.expect_exception(ValidationError):
            DataAnalysisResponse(**expected_fields)
        
        # Using actual schema fields will also FAIL due to metrics type mismatch
        with self.expect_exception(ValidationError):
            DataAnalysisResponse(**actual_schema_fields)
        
        # This documents that BOTH approaches currently fail, showing the need for schema alignment