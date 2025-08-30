"""
Unit tests for operations
Coverage Target: 90%
Business Value: Revenue-critical component
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from netra_backend.app.agents.corpus_admin.operations import CorpusOperationHandler

class TestOperations:
    """Test suite for CorpusOperationHandler"""
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher"""
        return Mock()
    
    @pytest.fixture
    def instance(self, mock_tool_dispatcher):
        """Create test instance"""
        return CorpusOperationHandler(mock_tool_dispatcher)
    
    def test_initialization(self, instance):
        """Test proper initialization"""
        assert instance is not None
        assert instance.tool_dispatcher is not None
        assert instance.crud_ops is not None
        assert instance.analysis_ops is not None
    
    def test_get_corpus_statistics(self, instance):
        """Test core statistics functionality"""
        # Test happy path
        result = instance.get_corpus_statistics()
        assert result is not None
        assert "total_corpora" in result
        assert "total_documents" in result
        assert "total_size_gb" in result
    
    def test_crud_operation_detection(self, instance):
        """Test CRUD operation detection"""
        assert instance._is_crud_operation("create") == True
        assert instance._is_crud_operation("search") == True
        assert instance._is_crud_operation("update") == True
        assert instance._is_crud_operation("delete") == True
        assert instance._is_crud_operation("analyze") == False
    
    def test_analysis_operation_detection(self, instance):
        """Test analysis operation detection"""
        assert instance._is_analysis_operation("analyze") == True
        assert instance._is_analysis_operation("export") == True
        assert instance._is_analysis_operation("import") == True
        assert instance._is_analysis_operation("validate") == True
        assert instance._is_analysis_operation("create") == False
    
    def test_base_statistics_structure(self, instance):
        """Test that statistics have correct structure"""
        stats = instance._get_base_statistics()
        assert "total_corpora" in stats
        assert "total_documents" in stats
        assert "total_size_gb" in stats
        assert isinstance(stats["total_corpora"], int)
        assert isinstance(stats["total_documents"], int)
        assert isinstance(stats["total_size_gb"], float)
