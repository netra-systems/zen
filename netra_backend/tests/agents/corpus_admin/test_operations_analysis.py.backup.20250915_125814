from unittest.mock import Mock

"""
Unit tests for operations_analysis
Coverage Target: 90%
Business Value: Revenue-critical component
Tests actual corpus analysis operations that exist in the implementation.
"""

import pytest
from netra_backend.app.agents.corpus_admin.operations_analysis import CorpusAnalysisOperations
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher


class TestOperationsAnalysis:
    """Test suite for CorpusAnalysisOperations - tests actual implementation"""

    @pytest.fixture
    def tool_dispatcher(self):
        """Create mock tool dispatcher for testing"""
        return Mock(spec=UnifiedToolDispatcher)

    @pytest.fixture 
    def instance(self, tool_dispatcher):
        """Create test instance with actual implementation"""
        return CorpusAnalysisOperations(tool_dispatcher)

    def test_initialization(self, instance, tool_dispatcher):
        """Test proper initialization with actual attributes"""
        assert instance is not None
        assert instance.tool_dispatcher is not None
        assert instance.tool_dispatcher == tool_dispatcher

    def test_analyze_corpus_metrics(self, instance):
        """Test corpus metrics analysis - actual business logic"""
        corpus_id = "test_corpus_123"
        
        result = instance.analyze_corpus_metrics(corpus_id)
        
        # Verify actual return structure
        assert result["corpus_id"] == corpus_id
        assert "total_documents" in result
        assert "average_size" in result
        assert "performance_score" in result
        assert isinstance(result["total_documents"], int)
        assert isinstance(result["average_size"], (int, float))
        assert isinstance(result["performance_score"], (int, float))

    def test_generate_corpus_report(self, instance):
        """Test corpus report generation - actual business logic"""
        corpus_id = "test_corpus_456"
        
        result = instance.generate_corpus_report(corpus_id)
        
        # Verify actual return structure
        assert result["corpus_id"] == corpus_id
        assert result["report_type"] == "corpus_analysis"
        assert "generated_at" in result
        assert "summary" in result

    def test_compare_corpus_performance(self, instance):
        """Test corpus performance comparison - actual business logic"""
        # Test with multiple corpus IDs
        corpus_ids = ["corpus_1", "corpus_2", "corpus_3"]
        
        result = instance.compare_corpus_performance(corpus_ids)
        
        # Verify actual return structure
        assert result["comparison_type"] == "performance"
        assert result["corpus_count"] == len(corpus_ids)
        assert result["best_performer"] == corpus_ids[0]
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_compare_corpus_performance_empty_list(self, instance):
        """Test corpus performance comparison with empty list"""
        corpus_ids = []
        
        result = instance.compare_corpus_performance(corpus_ids)
        
        # Verify handling of edge case
        assert result["corpus_count"] == 0
        assert result["best_performer"] is None
        assert isinstance(result["results"], list)

    def test_compare_corpus_performance_single_corpus(self, instance):
        """Test corpus performance comparison with single corpus"""
        corpus_ids = ["single_corpus"]
        
        result = instance.compare_corpus_performance(corpus_ids)
        
        # Verify single corpus handling
        assert result["corpus_count"] == 1
        assert result["best_performer"] == "single_corpus"