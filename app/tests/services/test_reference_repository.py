"""Test reference repository specific functionality.

MODULE PURPOSE:
Tests the reference repository layer with comprehensive mocking to ensure
reference-specific data access patterns work correctly.
"""

import pytest
from app.tests.helpers.database_repository_helpers import (
    create_test_message, create_test_reference, assert_reference_created_correctly
)


# Import fixtures from helpers
pytest_plugins = ["app.tests.helpers.database_repository_fixtures"]


@pytest.mark.asyncio
class TestReferenceRepository:
    """Test reference repository specific functionality."""

    async def test_create_reference_with_metadata(self, unit_of_work):
        """Test creating a reference with metadata."""
        async with unit_of_work as uow:
            message = await create_test_message(uow, "test_thread", "Test message", "user")
            
            reference = await uow.references.create({
                "message_id": message.id,
                "type": "document",
                "source": "knowledge_base",
                "content": "Referenced content",
                "metadata": {
                    "document_id": "doc123",
                    "page": 5,
                    "relevance_score": 0.95
                }
            })
            
            assert_reference_created_correctly(reference, message.id, "document", "knowledge_base")
            assert reference.metadata["relevance_score"] == 0.95

    async def test_get_references_by_message(self, unit_of_work):
        """Test getting references by message ID."""
        async with unit_of_work as uow:
            message = await create_test_message(uow, "test_thread", "Test message", "user")
            
            # Create references
            for i in range(3):
                await create_test_reference(uow, message.id, "document", f"source_{i}")
            
            references = await uow.references.get_by_message(message.id)
            
            assert len(references) == 3
            assert all(r.message_id == message.id for r in references)

    async def test_search_references(self, unit_of_work):
        """Test searching references."""
        async with unit_of_work as uow:
            # Create references with searchable content
            for i in range(5):
                await uow.references.create({
                    "message_id": f"msg_{i}",
                    "type": "document",
                    "source": "knowledge_base",
                    "content": f"Python programming reference {i}"
                })
            
            results = await uow.references.search(query="Python", limit=10)
            
            assert len(results) == 5
            assert all("Python" in r.content for r in results)