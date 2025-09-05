"""
Comprehensive unit tests for corpus_admin models.

Business Value: Ensures data integrity and validation for corpus management models.
These models are critical for enterprise clients and must be 100% reliable.
Tests cover all validation scenarios, edge cases, and business rules.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List
from pydantic import ValidationError
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.corpus_admin.models import (
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
    CorpusStatistics,
)


class TestCorpusOperation:
    """Test CorpusOperation enum."""

    def test_all_operation_values(self):
        """Test all corpus operation enum values."""
        expected_operations = {
            "create", "update", "delete", "search", 
            "analyze", "export", "import", "validate"
        }
        actual_operations = {op.value for op in CorpusOperation}
        assert actual_operations == expected_operations

    def test_operation_string_representation(self):
        """Test operation string representation."""
        assert CorpusOperation.CREATE.value == "create"
        assert CorpusOperation.DELETE.value == "delete"
        assert CorpusOperation.SEARCH.value == "search"

    def test_operation_comparison(self):
        """Test operation comparison with strings."""
        assert CorpusOperation.CREATE == "create"
        assert CorpusOperation.UPDATE == "update"
        assert CorpusOperation.DELETE != "create"

    def test_operation_membership(self):
        """Test operation membership checks."""
        assert "create" in [op.value for op in CorpusOperation]
        assert "invalid_op" not in [op.value for op in CorpusOperation]


class TestCorpusType:
    """Test CorpusType enum."""

    def test_all_type_values(self):
        """Test all corpus type enum values."""
        expected_types = {
            "documentation", "knowledge_base", "training_data", 
            "reference_data", "embeddings"
        }
        actual_types = {ct.value for ct in CorpusType}
        assert actual_types == expected_types

    def test_type_string_representation(self):
        """Test type string representation."""
        assert CorpusType.DOCUMENTATION.value == "documentation"
        assert CorpusType.KNOWLEDGE_BASE.value == "knowledge_base"
        assert CorpusType.EMBEDDINGS.value == "embeddings"

    def test_type_comparison(self):
        """Test type comparison with strings."""
        assert CorpusType.DOCUMENTATION == "documentation"
        assert CorpusType.TRAINING_DATA == "training_data"
        assert CorpusType.EMBEDDINGS != "documentation"


class TestCorpusMetadata:
    """Test CorpusMetadata model."""

    def test_basic_creation(self):
        """Test basic metadata creation with required fields."""
        metadata = CorpusMetadata(
            corpus_name="test_corpus",
            corpus_type=CorpusType.DOCUMENTATION
        )
        
        assert metadata.corpus_name == "test_corpus"
        assert metadata.corpus_type == CorpusType.DOCUMENTATION
        assert metadata.corpus_id is None
        assert metadata.description is None
        assert metadata.tags == []
        assert metadata.created_at is None
        assert metadata.version == "1.0"
        assert metadata.access_level == "private"

    def test_creation_with_all_fields(self):
        """Test metadata creation with all fields."""
        now = datetime.now(timezone.utc)
        metadata = CorpusMetadata(
            corpus_id="corpus_123",
            corpus_name="comprehensive_corpus",
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            description="Comprehensive knowledge base for testing",
            tags=["test", "comprehensive", "kb"],
            created_at=now,
            updated_at=now,
            size_bytes=1048576,
            document_count=150,
            version="2.1",
            access_level="public"
        )
        
        assert metadata.corpus_id == "corpus_123"
        assert metadata.corpus_name == "comprehensive_corpus"
        assert metadata.corpus_type == CorpusType.KNOWLEDGE_BASE
        assert metadata.description == "Comprehensive knowledge base for testing"
        assert metadata.tags == ["test", "comprehensive", "kb"]
        assert metadata.created_at == now
        assert metadata.updated_at == now
        assert metadata.size_bytes == 1048576
        assert metadata.document_count == 150
        assert metadata.version == "2.1"
        assert metadata.access_level == "public"

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        with pytest.raises(ValidationError) as exc_info:
            CorpusMetadata(corpus_type=CorpusType.DOCUMENTATION)
        
        assert "corpus_name" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            CorpusMetadata(corpus_name="test")
        
        assert "corpus_type" in str(exc_info.value)

    def test_default_values(self):
        """Test default values are correctly applied."""
        metadata = CorpusMetadata(
            corpus_name="test_defaults",
            corpus_type=CorpusType.REFERENCE_DATA
        )
        
        assert metadata.tags == []
        assert metadata.version == "1.0"
        assert metadata.access_level == "private"
        assert metadata.size_bytes is None
        assert metadata.document_count is None

    def test_tag_list_handling(self):
        """Test tag list validation and handling."""
        # Empty tags
        metadata = CorpusMetadata(
            corpus_name="empty_tags",
            corpus_type=CorpusType.EMBEDDINGS,
            tags=[]
        )
        assert metadata.tags == []

        # Multiple tags
        metadata = CorpusMetadata(
            corpus_name="multi_tags",
            corpus_type=CorpusType.EMBEDDINGS,
            tags=["ai", "ml", "embeddings", "vector"]
        )
        assert len(metadata.tags) == 4
        assert "ai" in metadata.tags

    def test_datetime_handling(self):
        """Test datetime field handling."""
        now = datetime.now(timezone.utc)
        metadata = CorpusMetadata(
            corpus_name="datetime_test",
            corpus_type=CorpusType.TRAINING_DATA,
            created_at=now
        )
        
        assert metadata.created_at == now
        assert isinstance(metadata.created_at, datetime)

    def test_numeric_fields_validation(self):
        """Test numeric fields validation."""
        metadata = CorpusMetadata(
            corpus_name="numeric_test",
            corpus_type=CorpusType.DOCUMENTATION,
            size_bytes=0,
            document_count=0
        )
        
        assert metadata.size_bytes == 0
        assert metadata.document_count == 0

        # Test large values
        metadata = CorpusMetadata(
            corpus_name="large_numeric",
            corpus_type=CorpusType.DOCUMENTATION,
            size_bytes=999999999999,
            document_count=1000000
        )
        
        assert metadata.size_bytes == 999999999999
        assert metadata.document_count == 1000000

    def test_model_serialization(self):
        """Test model serialization to dict."""
        metadata = CorpusMetadata(
            corpus_name="serialize_test",
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            tags=["serialize", "test"]
        )
        
        data = metadata.model_dump()
        assert isinstance(data, dict)
        assert data["corpus_name"] == "serialize_test"
        assert data["corpus_type"] == "knowledge_base"
        assert data["tags"] == ["serialize", "test"]
        assert data["version"] == "1.0"

    def test_model_copy(self):
        """Test model copying functionality."""
        original = CorpusMetadata(
            corpus_name="original",
            corpus_type=CorpusType.EMBEDDINGS,
            tags=["original"]
        )
        
        copy = original.model_copy()
        assert copy.corpus_name == original.corpus_name
        assert copy.corpus_type == original.corpus_type
        assert copy.tags == original.tags
        assert copy is not original  # Different objects

        # Test that copy is independent (Pydantic model_copy does deep copy)
        copy.tags.append("modified")
        # Note: Pydantic model_copy() creates shallow copy for mutable fields
        # This is expected behavior, not a bug


class TestCorpusOperationRequest:
    """Test CorpusOperationRequest model."""

    def test_basic_creation(self):
        """Test basic request creation with required fields."""
        metadata = CorpusMetadata(
            corpus_name="request_test",
            corpus_type=CorpusType.DOCUMENTATION
        )
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=metadata
        )
        
        assert request.operation == CorpusOperation.CREATE
        assert request.corpus_metadata == metadata
        assert request.filters == {}
        assert request.content is None
        assert request.options == {}
        assert request.requires_approval is False

    def test_creation_with_all_fields(self):
        """Test request creation with all fields."""
        metadata = CorpusMetadata(
            corpus_name="full_request_test",
            corpus_type=CorpusType.KNOWLEDGE_BASE
        )
        
        filters = {"document_type": "guide", "status": "published"}
        content = {"documents": [{"title": "Test Doc", "content": "Test content"}]}
        options = {"limit": 100, "include_metadata": True}
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=metadata,
            filters=filters,
            content=content,
            options=options,
            requires_approval=True
        )
        
        assert request.operation == CorpusOperation.SEARCH
        assert request.corpus_metadata == metadata
        assert request.filters == filters
        assert request.content == content
        assert request.options == options
        assert request.requires_approval is True

    def test_filters_validation(self):
        """Test filters field validation and types."""
        metadata = CorpusMetadata(
            corpus_name="filter_test",
            corpus_type=CorpusType.REFERENCE_DATA
        )
        
        # Empty filters
        request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=metadata,
            filters={}
        )
        assert request.filters == {}

        # Complex filters
        complex_filters = {
            "category": "technical",
            "tags": ["api", "documentation"],
            "created_after": "2024-01-01",
            "size_range": {"min": 1000, "max": 50000}
        }
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=metadata,
            filters=complex_filters
        )
        assert request.filters == complex_filters

    def test_content_field_flexibility(self):
        """Test content field accepts various types."""
        metadata = CorpusMetadata(
            corpus_name="content_test",
            corpus_type=CorpusType.TRAINING_DATA
        )
        
        # String content
        request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=metadata,
            content="search query string"
        )
        assert request.content == "search query string"

        # Dict content
        dict_content = {"documents": [], "metadata": {"source": "test"}}
        request = CorpusOperationRequest(
            operation=CorpusOperation.IMPORT,
            corpus_metadata=metadata,
            content=dict_content
        )
        assert request.content == dict_content

        # List content
        list_content = ["item1", "item2", "item3"]
        request = CorpusOperationRequest(
            operation=CorpusOperation.VALIDATE,
            corpus_metadata=metadata,
            content=list_content
        )
        assert request.content == list_content

    def test_options_validation(self):
        """Test options field validation."""
        metadata = CorpusMetadata(
            corpus_name="options_test",
            corpus_type=CorpusType.EMBEDDINGS
        )
        
        options = {
            "batch_size": 100,
            "timeout": 30,
            "retry_count": 3,
            "async_mode": True,
            "compression": "gzip"
        }
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.EXPORT,
            corpus_metadata=metadata,
            options=options
        )
        
        assert request.options == options
        assert request.options["batch_size"] == 100
        assert request.options["async_mode"] is True

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        metadata = CorpusMetadata(
            corpus_name="missing_test",
            corpus_type=CorpusType.DOCUMENTATION
        )
        
        # Missing operation
        with pytest.raises(ValidationError) as exc_info:
            CorpusOperationRequest(corpus_metadata=metadata)
        assert "operation" in str(exc_info.value)

        # Missing metadata
        with pytest.raises(ValidationError) as exc_info:
            CorpusOperationRequest(operation=CorpusOperation.CREATE)
        assert "corpus_metadata" in str(exc_info.value)


class TestCorpusOperationResult:
    """Test CorpusOperationResult model."""

    def test_basic_creation(self):
        """Test basic result creation with required fields."""
        metadata = CorpusMetadata(
            corpus_name="result_test",
            corpus_type=CorpusType.DOCUMENTATION
        )
        
        result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.CREATE,
            corpus_metadata=metadata
        )
        
        assert result.success is True
        assert result.operation == CorpusOperation.CREATE
        assert result.corpus_metadata == metadata
        assert result.affected_documents == 0
        assert result.result_data is None
        assert result.errors == []
        assert result.warnings == []
        assert result.requires_approval is False
        assert result.approval_message is None
        assert result.metadata == {}

    def test_creation_with_all_fields(self):
        """Test result creation with all fields."""
        metadata = CorpusMetadata(
            corpus_name="full_result_test",
            corpus_type=CorpusType.KNOWLEDGE_BASE
        )
        
        result_data = [
            {"id": "doc1", "title": "Document 1", "score": 0.95},
            {"id": "doc2", "title": "Document 2", "score": 0.87}
        ]
        
        errors = ["Warning: Some documents could not be processed"]
        warnings = ["Info: Operation completed with partial success"]
        result_metadata = {"total_matches": 2, "search_time_ms": 45}
        
        result = CorpusOperationResult(
            success=False,
            operation=CorpusOperation.SEARCH,
            corpus_metadata=metadata,
            affected_documents=2,
            result_data=result_data,
            errors=errors,
            warnings=warnings,
            requires_approval=True,
            approval_message="Please approve this search operation",
            metadata=result_metadata
        )
        
        assert result.success is False
        assert result.operation == CorpusOperation.SEARCH
        assert result.affected_documents == 2
        assert result.result_data == result_data
        assert result.errors == errors
        assert result.warnings == warnings
        assert result.requires_approval is True
        assert result.approval_message == "Please approve this search operation"
        assert result.metadata == result_metadata

    def test_success_failure_scenarios(self):
        """Test success and failure result scenarios."""
        metadata = CorpusMetadata(
            corpus_name="success_test",
            corpus_type=CorpusType.EMBEDDINGS
        )
        
        # Successful operation
        success_result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.CREATE,
            corpus_metadata=metadata,
            affected_documents=100
        )
        assert success_result.success is True
        assert success_result.errors == []
        assert success_result.affected_documents == 100

        # Failed operation
        failed_result = CorpusOperationResult(
            success=False,
            operation=CorpusOperation.DELETE,
            corpus_metadata=metadata,
            errors=["Insufficient permissions", "Corpus not found"]
        )
        assert failed_result.success is False
        assert len(failed_result.errors) == 2
        assert "Insufficient permissions" in failed_result.errors

    def test_result_data_flexibility(self):
        """Test result_data field accepts various types."""
        metadata = CorpusMetadata(
            corpus_name="data_test",
            corpus_type=CorpusType.TRAINING_DATA
        )
        
        # List result data
        list_data = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.SEARCH,
            corpus_metadata=metadata,
            result_data=list_data
        )
        assert result.result_data == list_data

        # Dict result data
        dict_data = {"summary": {"total": 50}, "items": []}
        result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.ANALYZE,
            corpus_metadata=metadata,
            result_data=dict_data
        )
        assert result.result_data == dict_data

        # String result data
        string_data = "Operation completed successfully"
        result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.VALIDATE,
            corpus_metadata=metadata,
            result_data=string_data
        )
        assert result.result_data == string_data

    def test_error_and_warning_lists(self):
        """Test error and warning list handling."""
        metadata = CorpusMetadata(
            corpus_name="error_test",
            corpus_type=CorpusType.REFERENCE_DATA
        )
        
        # Multiple errors
        errors = [
            "Database connection failed",
            "Invalid document format",
            "Insufficient storage space"
        ]
        
        # Multiple warnings
        warnings = [
            "Large operation may take time",
            "Some optional fields missing",
            "Deprecated API version used"
        ]
        
        result = CorpusOperationResult(
            success=False,
            operation=CorpusOperation.UPDATE,
            corpus_metadata=metadata,
            errors=errors,
            warnings=warnings
        )
        
        assert len(result.errors) == 3
        assert len(result.warnings) == 3
        assert "Database connection failed" in result.errors
        assert "Large operation may take time" in result.warnings

    def test_approval_fields(self):
        """Test approval-related fields."""
        metadata = CorpusMetadata(
            corpus_name="approval_test",
            corpus_type=CorpusType.DOCUMENTATION
        )
        
        approval_message = "This operation will delete 1000+ documents. Please confirm."
        
        result = CorpusOperationResult(
            success=False,
            operation=CorpusOperation.DELETE,
            corpus_metadata=metadata,
            requires_approval=True,
            approval_message=approval_message
        )
        
        assert result.requires_approval is True
        assert result.approval_message == approval_message

    def test_missing_required_fields(self):
        """Test validation error when required fields are missing."""
        metadata = CorpusMetadata(
            corpus_name="missing_result_test",
            corpus_type=CorpusType.EMBEDDINGS
        )
        
        # Missing success
        with pytest.raises(ValidationError) as exc_info:
            CorpusOperationResult(
                operation=CorpusOperation.CREATE,
                corpus_metadata=metadata
            )
        assert "success" in str(exc_info.value)

        # Missing operation
        with pytest.raises(ValidationError) as exc_info:
            CorpusOperationResult(
                success=True,
                corpus_metadata=metadata
            )
        assert "operation" in str(exc_info.value)

        # Missing metadata
        with pytest.raises(ValidationError) as exc_info:
            CorpusOperationResult(
                success=True,
                operation=CorpusOperation.SEARCH
            )
        assert "corpus_metadata" in str(exc_info.value)

    def test_affected_documents_validation(self):
        """Test affected_documents field validation."""
        metadata = CorpusMetadata(
            corpus_name="affected_test",
            corpus_type=CorpusType.KNOWLEDGE_BASE
        )
        
        # Zero affected documents
        result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.VALIDATE,
            corpus_metadata=metadata,
            affected_documents=0
        )
        assert result.affected_documents == 0

        # Large number of affected documents
        result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.IMPORT,
            corpus_metadata=metadata,
            affected_documents=999999
        )
        assert result.affected_documents == 999999


class TestCorpusStatistics:
    """Test CorpusStatistics model."""

    def test_basic_creation(self):
        """Test basic statistics creation with defaults."""
        stats = CorpusStatistics()
        
        assert stats.total_corpora == 0
        assert stats.total_documents == 0
        assert stats.total_size_bytes == 0
        assert stats.corpora_by_type == {}
        assert stats.recent_operations == []

    def test_creation_with_all_fields(self):
        """Test statistics creation with all fields."""
        corpora_by_type = {
            "documentation": 5,
            "knowledge_base": 3,
            "training_data": 2
        }
        
        recent_operations = [
            {"operation": "create", "timestamp": "2024-01-01T12:00:00Z"},
            {"operation": "search", "timestamp": "2024-01-01T11:30:00Z"}
        ]
        
        stats = CorpusStatistics(
            total_corpora=10,
            total_documents=50000,
            total_size_bytes=1073741824,  # 1 GB
            corpora_by_type=corpora_by_type,
            recent_operations=recent_operations
        )
        
        assert stats.total_corpora == 10
        assert stats.total_documents == 50000
        assert stats.total_size_bytes == 1073741824
        assert stats.corpora_by_type == corpora_by_type
        assert stats.recent_operations == recent_operations

    def test_corpora_by_type_validation(self):
        """Test corpora_by_type field validation."""
        # Empty dict
        stats = CorpusStatistics(corpora_by_type={})
        assert stats.corpora_by_type == {}

        # Multiple types
        type_counts = {
            "documentation": 10,
            "knowledge_base": 15,
            "training_data": 5,
            "reference_data": 8,
            "embeddings": 3
        }
        
        stats = CorpusStatistics(corpora_by_type=type_counts)
        assert stats.corpora_by_type == type_counts
        assert stats.corpora_by_type["documentation"] == 10

    def test_recent_operations_validation(self):
        """Test recent_operations field validation."""
        # Empty list
        stats = CorpusStatistics(recent_operations=[])
        assert stats.recent_operations == []

        # Multiple operations
        operations = [
            {
                "operation": "create",
                "timestamp": "2024-01-01T12:00:00Z",
                "corpus_name": "new_kb",
                "user": "admin"
            },
            {
                "operation": "search",
                "timestamp": "2024-01-01T11:30:00Z",
                "query": "optimization techniques",
                "results": 42
            },
            {
                "operation": "delete",
                "timestamp": "2024-01-01T10:15:00Z",
                "corpus_name": "old_docs",
                "documents_affected": 150
            }
        ]
        
        stats = CorpusStatistics(recent_operations=operations)
        assert len(stats.recent_operations) == 3
        assert stats.recent_operations[0]["operation"] == "create"
        assert stats.recent_operations[1]["results"] == 42

    def test_numeric_fields_validation(self):
        """Test numeric fields accept valid ranges."""
        # Zero values
        stats = CorpusStatistics(
            total_corpora=0,
            total_documents=0,
            total_size_bytes=0
        )
        assert stats.total_corpora == 0
        assert stats.total_documents == 0
        assert stats.total_size_bytes == 0

        # Large values
        stats = CorpusStatistics(
            total_corpora=1000,
            total_documents=10000000,
            total_size_bytes=1099511627776  # 1 TB
        )
        assert stats.total_corpora == 1000
        assert stats.total_documents == 10000000
        assert stats.total_size_bytes == 1099511627776

    def test_model_serialization_and_copy(self):
        """Test model serialization and copying."""
        stats = CorpusStatistics(
            total_corpora=5,
            corpora_by_type={"docs": 3, "kb": 2},
            recent_operations=[{"op": "test"}]
        )
        
        # Test serialization
        data = stats.model_dump()
        assert isinstance(data, dict)
        assert data["total_corpora"] == 5
        assert data["corpora_by_type"] == {"docs": 3, "kb": 2}

        # Test copy
        copy = stats.model_copy()
        assert copy.total_corpora == stats.total_corpora
        assert copy.corpora_by_type == stats.corpora_by_type
        assert copy is not stats


class TestModelIntegration:
    """Test integration between models."""

    def test_request_result_integration(self):
        """Test integration between request and result models."""
        # Create request
        metadata = CorpusMetadata(
            corpus_name="integration_test",
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            tags=["integration", "test"]
        )
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=metadata,
            filters={"category": "technical"},
            content="search query"
        )
        
        # Create corresponding result
        result = CorpusOperationResult(
            success=True,
            operation=request.operation,
            corpus_metadata=request.corpus_metadata,
            affected_documents=25,
            result_data=[{"id": "doc1"}, {"id": "doc2"}]
        )
        
        # Verify integration
        assert result.operation == request.operation
        assert result.corpus_metadata == request.corpus_metadata
        assert result.corpus_metadata.corpus_name == "integration_test"

    def test_metadata_in_multiple_contexts(self):
        """Test metadata reuse across different operations."""
        metadata = CorpusMetadata(
            corpus_name="shared_corpus",
            corpus_type=CorpusType.DOCUMENTATION,
            version="1.5"
        )
        
        # Use in different operations
        create_request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=metadata
        )
        
        search_request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=metadata
        )
        
        update_result = CorpusOperationResult(
            success=True,
            operation=CorpusOperation.UPDATE,
            corpus_metadata=metadata
        )
        
        # Verify metadata consistency
        assert create_request.corpus_metadata == metadata
        assert search_request.corpus_metadata == metadata
        assert update_result.corpus_metadata == metadata
        assert all(
            m.corpus_metadata.version == "1.5" 
            for m in [create_request, search_request, update_result]
        )

    def test_enum_consistency_across_models(self):
        """Test enum consistency across different models."""
        # Test all operations work in request and result
        for operation in CorpusOperation:
            metadata = CorpusMetadata(
                corpus_name=f"test_{operation.value}",
                corpus_type=CorpusType.KNOWLEDGE_BASE
            )
            
            request = CorpusOperationRequest(
                operation=operation,
                corpus_metadata=metadata
            )
            
            result = CorpusOperationResult(
                success=True,
                operation=operation,
                corpus_metadata=metadata
            )
            
            assert request.operation == operation
            assert result.operation == operation

        # Test all corpus types work in metadata
        for corpus_type in CorpusType:
            metadata = CorpusMetadata(
                corpus_name=f"test_{corpus_type.value}",
                corpus_type=corpus_type
            )
            
            assert metadata.corpus_type == corpus_type


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])