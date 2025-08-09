"""Test corpus service for managing document and content collections."""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from app.services.corpus_service import (
    CorpusService,
    Document,
    DocumentChunk,
    EmbeddingModel,
    SearchResult,
    CorpusMetadata
)


@pytest.fixture
async def corpus_service():
    """Create a test corpus service instance."""
    service = CorpusService(
        embedding_model="text-embedding-ada-002",
        chunk_size=512,
        chunk_overlap=50
    )
    await service.initialize()
    yield service
    await service.cleanup()


@pytest.mark.asyncio
class TestDocumentManagement:
    """Test document management operations."""

    async def test_add_document(self, corpus_service):
        """Test adding a document to the corpus."""
        document = Document(
            id="doc1",
            content="This is a test document with sample content.",
            metadata={"source": "test", "category": "sample"},
            created_at=datetime.now()
        )
        
        result = await corpus_service.add_document(document)
        
        assert result["document_id"] == "doc1"
        assert result["chunks_created"] > 0
        assert result["success"] is True

    async def test_document_chunking(self, corpus_service):
        """Test document chunking strategy."""
        long_content = " ".join([f"Sentence {i}." for i in range(100)])
        document = Document(
            id="doc2",
            content=long_content,
            metadata={"type": "long_document"}
        )
        
        chunks = await corpus_service.chunk_document(document)
        
        assert len(chunks) > 1
        assert all(len(chunk.content) <= corpus_service.chunk_size for chunk in chunks)
        
        # Test overlap
        for i in range(len(chunks) - 1):
            overlap = corpus_service.get_chunk_overlap(chunks[i], chunks[i + 1])
            assert overlap >= corpus_service.chunk_overlap

    async def test_batch_document_ingestion(self, corpus_service):
        """Test batch document ingestion."""
        documents = [
            Document(
                id=f"doc_{i}",
                content=f"Document {i} content with unique information.",
                metadata={"batch": 1, "index": i}
            )
            for i in range(50)
        ]
        
        result = await corpus_service.batch_ingest(documents, batch_size=10)
        
        assert result["total_documents"] == 50
        assert result["total_chunks"] > 50
        assert result["failed_documents"] == 0

    async def test_document_update(self, corpus_service):
        """Test updating an existing document."""
        # Add initial document
        original = Document(
            id="update_test",
            content="Original content",
            metadata={"version": 1}
        )
        await corpus_service.add_document(original)
        
        # Update document
        updated = Document(
            id="update_test",
            content="Updated content with new information",
            metadata={"version": 2}
        )
        result = await corpus_service.update_document(updated)
        
        assert result["document_id"] == "update_test"
        assert result["chunks_updated"] > 0
        assert result["old_chunks_removed"] > 0

    async def test_document_deletion(self, corpus_service):
        """Test document deletion from corpus."""
        # Add document
        document = Document(
            id="delete_test",
            content="Document to be deleted",
            metadata={}
        )
        await corpus_service.add_document(document)
        
        # Delete document
        result = await corpus_service.delete_document("delete_test")
        
        assert result["document_id"] == "delete_test"
        assert result["chunks_removed"] > 0
        assert result["success"] is True
        
        # Verify document is deleted
        search_result = await corpus_service.get_document("delete_test")
        assert search_result is None


@pytest.mark.asyncio
class TestEmbeddingOperations:
    """Test embedding generation and management."""

    async def test_embedding_generation(self, corpus_service):
        """Test generating embeddings for text."""
        text = "This is a sample text for embedding generation."
        
        embedding = await corpus_service.generate_embedding(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] > 0
        assert -1 <= embedding.min() <= embedding.max() <= 1

    async def test_batch_embedding_generation(self, corpus_service):
        """Test batch embedding generation."""
        texts = [f"Text sample {i}" for i in range(20)]
        
        embeddings = await corpus_service.batch_generate_embeddings(texts)
        
        assert len(embeddings) == 20
        assert all(isinstance(emb, np.ndarray) for emb in embeddings)

    async def test_embedding_caching(self, corpus_service):
        """Test embedding caching mechanism."""
        text = "Cacheable text content"
        
        # First generation
        embedding1 = await corpus_service.generate_embedding(text)
        
        # Second generation (should use cache)
        with patch.object(corpus_service.embedding_model, 'encode', wraps=corpus_service.embedding_model.encode) as mock_encode:
            embedding2 = await corpus_service.generate_embedding(text)
            mock_encode.assert_not_called()
        
        assert np.array_equal(embedding1, embedding2)

    async def test_embedding_similarity_calculation(self, corpus_service):
        """Test similarity calculation between embeddings."""
        text1 = "Machine learning is a subset of artificial intelligence"
        text2 = "AI includes techniques like machine learning"
        text3 = "The weather is nice today"
        
        emb1 = await corpus_service.generate_embedding(text1)
        emb2 = await corpus_service.generate_embedding(text2)
        emb3 = await corpus_service.generate_embedding(text3)
        
        # Similar texts should have higher similarity
        sim_12 = corpus_service.calculate_similarity(emb1, emb2)
        sim_13 = corpus_service.calculate_similarity(emb1, emb3)
        
        assert sim_12 > sim_13
        assert 0 <= sim_12 <= 1
        assert 0 <= sim_13 <= 1


@pytest.mark.asyncio
class TestSearchOperations:
    """Test search and retrieval operations."""

    async def test_semantic_search(self, corpus_service):
        """Test semantic search functionality."""
        # Add test documents
        documents = [
            Document(id="1", content="Python is a programming language"),
            Document(id="2", content="Machine learning with Python"),
            Document(id="3", content="Data science and analytics"),
            Document(id="4", content="Web development with JavaScript")
        ]
        
        for doc in documents:
            await corpus_service.add_document(doc)
        
        # Search
        results = await corpus_service.semantic_search(
            query="Python programming",
            top_k=2
        )
        
        assert len(results) == 2
        assert results[0].document_id in ["1", "2"]
        assert results[0].score > results[1].score

    async def test_hybrid_search(self, corpus_service):
        """Test hybrid search combining semantic and keyword search."""
        results = await corpus_service.hybrid_search(
            query="Python machine learning",
            semantic_weight=0.7,
            keyword_weight=0.3,
            top_k=5
        )
        
        assert len(results) <= 5
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(0 <= r.score <= 1 for r in results)

    async def test_filtered_search(self, corpus_service):
        """Test search with metadata filters."""
        # Add documents with metadata
        documents = [
            Document(id="1", content="Technical documentation", metadata={"type": "docs", "language": "en"}),
            Document(id="2", content="Code examples", metadata={"type": "code", "language": "python"}),
            Document(id="3", content="API reference", metadata={"type": "docs", "language": "en"}),
            Document(id="4", content="Tutorial content", metadata={"type": "tutorial", "language": "es"})
        ]
        
        for doc in documents:
            await corpus_service.add_document(doc)
        
        # Search with filters
        results = await corpus_service.search_with_filters(
            query="documentation",
            filters={"type": "docs", "language": "en"},
            top_k=10
        )
        
        assert all(r.metadata["type"] == "docs" for r in results)
        assert all(r.metadata["language"] == "en" for r in results)

    async def test_reranking(self, corpus_service):
        """Test result reranking."""
        initial_results = [
            SearchResult(document_id="1", content="Result 1", score=0.8, metadata={}),
            SearchResult(document_id="2", content="Result 2", score=0.75, metadata={}),
            SearchResult(document_id="3", content="Result 3", score=0.7, metadata={})
        ]
        
        reranked = await corpus_service.rerank_results(
            query="specific query",
            results=initial_results,
            reranker_model="cross-encoder"
        )
        
        assert len(reranked) == len(initial_results)
        # Scores may change after reranking
        assert all(isinstance(r, SearchResult) for r in reranked)

    async def test_query_expansion(self, corpus_service):
        """Test query expansion for better recall."""
        original_query = "ML algorithms"
        
        expanded_queries = await corpus_service.expand_query(original_query)
        
        assert len(expanded_queries) > 1
        assert original_query in expanded_queries
        assert any("machine learning" in q.lower() for q in expanded_queries)


@pytest.mark.asyncio
class TestIndexManagement:
    """Test vector index management."""

    async def test_index_creation(self, corpus_service):
        """Test creating vector indexes."""
        result = await corpus_service.create_index(
            index_name="test_index",
            dimension=768,
            metric="cosine",
            index_type="hnsw"
        )
        
        assert result["index_name"] == "test_index"
        assert result["success"] is True

    async def test_index_optimization(self, corpus_service):
        """Test index optimization for performance."""
        # Add many documents
        documents = [
            Document(id=f"doc_{i}", content=f"Content {i}")
            for i in range(1000)
        ]
        await corpus_service.batch_ingest(documents)
        
        # Optimize index
        result = await corpus_service.optimize_index("test_index")
        
        assert result["optimized"] is True
        assert result["performance_improvement"] > 0

    async def test_index_statistics(self, corpus_service):
        """Test getting index statistics."""
        stats = await corpus_service.get_index_stats("test_index")
        
        assert "total_vectors" in stats
        assert "index_size_mb" in stats
        assert "avg_search_time_ms" in stats
        assert "last_optimized" in stats


@pytest.mark.asyncio
class TestCorpusAnalytics:
    """Test corpus analytics and insights."""

    async def test_corpus_statistics(self, corpus_service):
        """Test getting corpus statistics."""
        stats = await corpus_service.get_corpus_statistics()
        
        assert "total_documents" in stats
        assert "total_chunks" in stats
        assert "avg_document_length" in stats
        assert "vocabulary_size" in stats
        assert "storage_size_mb" in stats

    async def test_topic_extraction(self, corpus_service):
        """Test extracting topics from corpus."""
        topics = await corpus_service.extract_topics(
            num_topics=5,
            words_per_topic=10
        )
        
        assert len(topics) <= 5
        for topic in topics:
            assert "topic_id" in topic
            assert "words" in topic
            assert "weight" in topic
            assert len(topic["words"]) <= 10

    async def test_document_clustering(self, corpus_service):
        """Test clustering documents."""
        clusters = await corpus_service.cluster_documents(
            num_clusters=3,
            min_cluster_size=5
        )
        
        assert len(clusters) <= 3
        for cluster in clusters:
            assert "cluster_id" in cluster
            assert "document_ids" in cluster
            assert "centroid" in cluster
            assert len(cluster["document_ids"]) >= 5

    async def test_duplicate_detection(self, corpus_service):
        """Test detecting duplicate or near-duplicate documents."""
        # Add similar documents
        documents = [
            Document(id="dup1", content="This is a test document with some content"),
            Document(id="dup2", content="This is a test document with some content"),  # Exact duplicate
            Document(id="dup3", content="This is a test doc with some content"),  # Near duplicate
            Document(id="unique", content="Completely different content here")
        ]
        
        for doc in documents:
            await corpus_service.add_document(doc)
        
        duplicates = await corpus_service.find_duplicates(similarity_threshold=0.9)
        
        assert len(duplicates) > 0
        assert any("dup1" in group and "dup2" in group for group in duplicates)


@pytest.mark.asyncio
class TestCorpusMaintenanceAndBackup:
    """Test corpus maintenance and backup operations."""

    async def test_corpus_validation(self, corpus_service):
        """Test corpus integrity validation."""
        validation_result = await corpus_service.validate_corpus()
        
        assert validation_result["is_valid"] is True
        assert "orphaned_chunks" in validation_result
        assert "missing_embeddings" in validation_result
        assert "corrupted_documents" in validation_result

    async def test_corpus_cleanup(self, corpus_service):
        """Test corpus cleanup operations."""
        cleanup_result = await corpus_service.cleanup_corpus(
            remove_orphaned_chunks=True,
            rebuild_missing_embeddings=True
        )
        
        assert "chunks_removed" in cleanup_result
        assert "embeddings_rebuilt" in cleanup_result
        assert "space_freed_mb" in cleanup_result

    async def test_corpus_backup(self, corpus_service):
        """Test corpus backup functionality."""
        backup_result = await corpus_service.backup_corpus(
            backup_path="/tmp/corpus_backup",
            include_embeddings=True
        )
        
        assert backup_result["success"] is True
        assert "backup_size_mb" in backup_result
        assert "documents_backed_up" in backup_result
        assert "backup_location" in backup_result

    async def test_corpus_restore(self, corpus_service):
        """Test corpus restoration from backup."""
        restore_result = await corpus_service.restore_corpus(
            backup_path="/tmp/corpus_backup",
            overwrite_existing=False
        )
        
        assert restore_result["success"] is True
        assert "documents_restored" in restore_result
        assert "chunks_restored" in restore_result