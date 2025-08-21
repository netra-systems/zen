"""Unit tests for ProductionTool specific operations."""

import pytest
from unittest.mock import AsyncMock, patch, Mock

from netra_backend.app.agents.production_tool import ProductionTool
from netra_backend.tests.helpers.tool_dispatcher_assertions import (
    assert_tool_execute_response_success,
    assert_tool_execute_response_error,
    assert_batch_execution_success,
    assert_corpus_creation_success,
    assert_corpus_search_success,
    assert_validation_success,
    assert_storage_success,
    assert_missing_parameter_error,
    assert_not_implemented_error
)


class TestProductionToolSpecificOperations:
    """Test specific tool operations."""
    async def test_execute_synthetic_data_batch_success(self):
        """Test synthetic data batch generation success."""
        tool = ProductionTool("generate_synthetic_data_batch")
        result = await self._execute_with_batch_service_mock(tool)
        assert_batch_execution_success(result, 2)
    async def test_execute_synthetic_data_batch_failure(self):
        """Test synthetic data batch generation failure."""
        tool = ProductionTool("generate_synthetic_data_batch")
        result = await self._execute_with_batch_service_failure(tool)
        assert_tool_execute_response_error(result, "Failed to generate synthetic data")
    async def test_execute_create_corpus_success(self):
        """Test corpus creation success."""
        tool = ProductionTool("create_corpus")
        result = await self._execute_with_corpus_service_mock(tool)
        assert_corpus_creation_success(result, "corpus_123", "test_corpus")
    async def test_execute_create_corpus_failure(self):
        """Test corpus creation failure."""
        tool = ProductionTool("create_corpus")
        result = await self._execute_with_corpus_service_failure(tool)
        assert_tool_execute_response_error(result, "Failed to create corpus")
    async def test_execute_search_corpus_success(self):
        """Test corpus search success."""
        tool = ProductionTool("search_corpus")
        result = await self._execute_with_search_service_mock(tool)
        assert_corpus_search_success(result, 2)
    async def test_execute_search_corpus_missing_id(self):
        """Test corpus search with missing corpus_id."""
        tool = ProductionTool("search_corpus")
        result = await tool._execute_search_corpus({"query": "test"})
        assert_missing_parameter_error(result, "corpus_id")
    async def test_execute_validate_synthetic_data(self):
        """Test synthetic data validation."""
        tool = ProductionTool("validate_synthetic_data")
        result = await self._execute_with_validation_mock(tool)
        assert_validation_success(result, True)
    async def test_execute_store_synthetic_data(self):
        """Test synthetic data storage."""
        tool = ProductionTool("store_synthetic_data")
        result = await self._execute_with_storage_mock(tool)
        assert_storage_success(result, 10)
    async def test_execute_default(self):
        """Test default execution method."""
        tool = ProductionTool("unknown_tool")
        result = await tool._execute_default()
        assert_not_implemented_error(result, "unknown_tool")
    
    async def _execute_with_batch_service_mock(self, tool: ProductionTool) -> dict:
        """Execute with batch service mock."""
        with patch('app.services.synthetic_data.synthetic_data_service') as mock_service:
            mock_service.generate_batch = AsyncMock(return_value=["data1", "data2"])
            return await tool._execute_synthetic_data_batch({"batch_size": 2})
    
    async def _execute_with_batch_service_failure(self, tool: ProductionTool) -> dict:
        """Execute with batch service failure."""
        with patch('app.services.synthetic_data.synthetic_data_service') as mock_service:
            mock_service.generate_batch = AsyncMock(side_effect=Exception("Service error"))
            return await tool._execute_synthetic_data_batch({"batch_size": 2})
    
    async def _execute_with_corpus_service_mock(self, tool: ProductionTool) -> dict:
        """Execute with corpus service mock."""
        with patch('app.services.corpus.corpus_service') as mock_service:
            mock_corpus = self._create_mock_corpus()
            mock_service.create_corpus = AsyncMock(return_value=mock_corpus)
            return await tool._execute_create_corpus({"corpus_name": "test_corpus", "description": "Test description"})
    
    async def _execute_with_corpus_service_failure(self, tool: ProductionTool) -> dict:
        """Execute with corpus service failure."""
        with patch('app.services.corpus.corpus_service') as mock_service:
            mock_service.create_corpus = AsyncMock(side_effect=Exception("Database error"))
            return await tool._execute_create_corpus({"corpus_name": "test"})
    
    async def _execute_with_search_service_mock(self, tool: ProductionTool) -> dict:
        """Execute with search service mock."""
        with patch('app.services.corpus.corpus_service') as mock_service:
            mock_results = {"results": ["doc1", "doc2"], "total": 2}
            mock_service.search_corpus_content = AsyncMock(return_value=mock_results)
            return await tool._execute_search_corpus({"corpus_id": "123", "query": "test", "limit": 10})
    
    async def _execute_with_validation_mock(self, tool: ProductionTool) -> dict:
        """Execute with validation mock."""
        with patch('app.services.synthetic_data.validate_data') as mock_validate:
            mock_validate.return_value = {"valid": True, "errors": []}
            return await tool._execute_validate_synthetic_data({"data": ["item1", "item2"]})
    
    async def _execute_with_storage_mock(self, tool: ProductionTool) -> dict:
        """Execute with storage mock."""
        with patch('app.services.synthetic_data.synthetic_data_service') as mock_service:
            mock_service.ingest_batch = AsyncMock(return_value={"stored": 10})
            return await tool._execute_store_synthetic_data({"data": ["item1", "item2"], "table_name": "test_table"})
    
    def _create_mock_corpus(self) -> Mock:
        """Create mock corpus object."""
        mock_corpus = Mock()
        mock_corpus.id = "corpus_123"
        mock_corpus.name = "test_corpus"
        return mock_corpus