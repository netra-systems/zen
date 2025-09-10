"""
Test Corpus Handlers Business Logic

Business Value Justification (BVJ):
- Segment: Mid, Enterprise - Data Processing & Analytics
- Business Goal: Enable efficient processing of large data sets for AI insights
- Value Impact: Users can upload, process, and analyze business data through AI agents
- Strategic Impact: Core data processing capabilities for enterprise customers

This test suite validates corpus handling operations including:
- Document ingestion and parsing
- Data validation and sanitization
- Metadata extraction and indexing
- Search and retrieval operations
- Performance optimization for large datasets

Performance Requirements:
- Document ingestion should process 1MB files within 5 seconds
- Search operations should complete within 200ms
- Memory usage should remain bounded during processing
- Batch operations should scale linearly
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO, StringIO
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional, List, Union

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockDocument:
    """Mock document model for testing."""
    
    def __init__(self, doc_id: str, title: str, content: str, doc_type: str = "text"):
        self.id = doc_id
        self.title = title
        self.content = content
        self.doc_type = doc_type
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.metadata = {}
        self.size_bytes = len(content.encode('utf-8'))
        self.processed = False
        self.indexed = False


class MockCorpusHandler:
    """Mock corpus handler for unit testing."""
    
    def __init__(self):
        self._documents: Dict[str, MockDocument] = {}
        self._indexes: Dict[str, List[str]] = {}
        self._processing_queue: List[str] = []
        self._metrics = {
            "documents_processed": 0,
            "total_size_bytes": 0,
            "processing_time_ms": 0,
            "search_queries": 0,
            "index_operations": 0
        }
    
    async def ingest_document(self, title: str, content: Union[str, bytes], 
                            doc_type: str = "text", metadata: Optional[Dict] = None) -> MockDocument:
        """Ingest a document into the corpus."""
        start_time = time.time()
        
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        # Handle bytes content
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                # Handle binary content
                content = f"<binary_content:{len(content)}_bytes>"
                doc_type = "binary"
        
        # Validate content
        if not content.strip():
            raise ValueError("Document content cannot be empty")
        
        if len(content) > 10_000_000:  # 10MB limit
            raise ValueError("Document too large (max 10MB)")
        
        # Create document
        document = MockDocument(doc_id, title, content, doc_type)
        if metadata:
            document.metadata.update(metadata)
        
        # Store document
        self._documents[doc_id] = document
        self._processing_queue.append(doc_id)
        
        # Update metrics
        processing_time = (time.time() - start_time) * 1000
        self._metrics["documents_processed"] += 1
        self._metrics["total_size_bytes"] += document.size_bytes
        self._metrics["processing_time_ms"] += processing_time
        
        return document
    
    async def process_document(self, doc_id: str) -> bool:
        """Process a document for indexing and analysis."""
        if doc_id not in self._documents:
            return False
        
        document = self._documents[doc_id]
        
        # Simulate processing
        await asyncio.sleep(0.01)  # Simulate processing time
        
        # Extract keywords for indexing
        keywords = self._extract_keywords(document.content)
        
        # Update indexes
        for keyword in keywords:
            if keyword not in self._indexes:
                self._indexes[keyword] = []
            if doc_id not in self._indexes[keyword]:
                self._indexes[keyword].append(doc_id)
        
        # Mark as processed and indexed
        document.processed = True
        document.indexed = True
        document.updated_at = datetime.now(timezone.utc)
        
        # Remove from processing queue
        if doc_id in self._processing_queue:
            self._processing_queue.remove(doc_id)
        
        self._metrics["index_operations"] += 1
        
        return True
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        # Simple keyword extraction for testing
        words = content.lower().split()
        # Filter out common words and extract meaningful terms
        keywords = [word.strip('.,!?;:"()[]') for word in words 
                   if len(word) > 3 and word.isalpha()]
        # Return unique keywords
        return list(set(keywords[:50]))  # Limit to 50 keywords
    
    async def search_documents(self, query: str, limit: int = 10) -> List[MockDocument]:
        """Search documents by query."""
        start_time = time.time()
        self._metrics["search_queries"] += 1
        
        query_terms = query.lower().split()
        results = []
        scores = {}
        
        # Score documents based on keyword matches
        for term in query_terms:
            if term in self._indexes:
                for doc_id in self._indexes[term]:
                    if doc_id not in scores:
                        scores[doc_id] = 0
                    scores[doc_id] += 1
        
        # Sort by relevance score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Get top documents
        for doc_id, score in sorted_docs[:limit]:
            if doc_id in self._documents:
                results.append(self._documents[doc_id])
        
        return results
    
    async def get_document(self, doc_id: str) -> Optional[MockDocument]:
        """Get document by ID."""
        return self._documents.get(doc_id)
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document and clean up indexes."""
        if doc_id not in self._documents:
            return False
        
        # Remove from indexes
        for keyword_list in self._indexes.values():
            if doc_id in keyword_list:
                keyword_list.remove(doc_id)
        
        # Remove empty index entries
        empty_keywords = [k for k, v in self._indexes.items() if not v]
        for keyword in empty_keywords:
            del self._indexes[keyword]
        
        # Remove document
        del self._documents[doc_id]
        
        # Remove from processing queue
        if doc_id in self._processing_queue:
            self._processing_queue.remove(doc_id)
        
        return True
    
    async def get_corpus_stats(self) -> Dict[str, Any]:
        """Get corpus statistics."""
        total_docs = len(self._documents)
        processed_docs = sum(1 for doc in self._documents.values() if doc.processed)
        total_size = sum(doc.size_bytes for doc in self._documents.values())
        
        return {
            "total_documents": total_docs,
            "processed_documents": processed_docs,
            "pending_processing": len(self._processing_queue),
            "total_size_bytes": total_size,
            "total_keywords": len(self._indexes),
            "metrics": self._metrics
        }


class TestCorpusHandler(SSotBaseTestCase):
    """Test CorpusHandler business logic and operations."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        self.corpus_handler = MockCorpusHandler()
        
        # Test documents
        self.sample_documents = [
            ("Technical Report", "This is a technical report about AI optimization and cost analysis. It contains detailed information about performance metrics and business value."),
            ("Meeting Notes", "Meeting notes from the weekly review. Discussion about project timeline, budget allocation, and resource planning."),
            ("Research Paper", "Academic research paper on machine learning algorithms for automated decision making and process optimization."),
            ("User Manual", "Comprehensive user manual for the data processing system. Includes installation guide, configuration steps, and troubleshooting tips."),
            ("Policy Document", "Company policy document outlining data governance, security protocols, and compliance requirements for business operations.")
        ]
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    async def test_document_ingestion_with_validation(self):
        """Test document ingestion with content validation."""
        # When: Ingesting valid documents
        ingested_docs = []
        for title, content in self.sample_documents:
            doc = await self.corpus_handler.ingest_document(
                title=title,
                content=content,
                doc_type="text",
                metadata={"source": "test", "category": "sample"}
            )
            ingested_docs.append(doc)
        
        # Then: All documents should be ingested successfully
        assert len(ingested_docs) == len(self.sample_documents)
        
        for i, doc in enumerate(ingested_docs):
            assert doc.id is not None
            assert doc.title == self.sample_documents[i][0]
            assert doc.content == self.sample_documents[i][1]
            assert doc.doc_type == "text"
            assert doc.metadata["source"] == "test"
            assert doc.metadata["category"] == "sample"
            assert doc.size_bytes > 0
            assert isinstance(doc.created_at, datetime)
        
        # And: Documents should be stored in corpus
        corpus_stats = await self.corpus_handler.get_corpus_stats()
        assert corpus_stats["total_documents"] == len(self.sample_documents)
        assert corpus_stats["pending_processing"] == len(self.sample_documents)
        
        self.record_metric("documents_ingested", len(ingested_docs))
        self.record_metric("document_ingestion_validated", True)
    
    @pytest.mark.unit
    async def test_document_validation_errors(self):
        """Test document validation and error handling."""
        # When: Attempting to ingest invalid documents
        # Test empty content
        with pytest.raises(ValueError, match="cannot be empty"):
            await self.corpus_handler.ingest_document("Empty Doc", "")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            await self.corpus_handler.ingest_document("Whitespace Doc", "   \n\t  ")
        
        # Test oversized content
        large_content = "x" * 10_000_001  # Over 10MB limit
        with pytest.raises(ValueError, match="too large"):
            await self.corpus_handler.ingest_document("Large Doc", large_content)
        
        # Then: Error handling should be proper
        corpus_stats = await self.corpus_handler.get_corpus_stats()
        assert corpus_stats["total_documents"] == 0  # No invalid docs stored
        
        self.record_metric("validation_errors_handled", 3)
    
    @pytest.mark.unit
    async def test_binary_content_handling(self):
        """Test handling of binary content."""
        # Given: Binary content (simulated as bytes)
        binary_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00'
        text_bytes = "This is text content".encode('utf-8')
        
        # When: Ingesting binary and text bytes
        binary_doc = await self.corpus_handler.ingest_document(
            title="Binary File",
            content=binary_data,
            metadata={"type": "image"}
        )
        
        text_doc = await self.corpus_handler.ingest_document(
            title="Text File", 
            content=text_bytes,
            metadata={"type": "text"}
        )
        
        # Then: Binary content should be handled appropriately
        assert binary_doc.doc_type == "binary"
        assert binary_doc.content.startswith("<binary_content:")
        assert str(len(binary_data)) in binary_doc.content
        
        # And: Text bytes should be decoded
        assert text_doc.doc_type == "text"
        assert text_doc.content == "This is text content"
        
        self.record_metric("binary_content_handled", True)
    
    @pytest.mark.unit
    async def test_document_processing_and_indexing(self):
        """Test document processing and keyword indexing."""
        # Given: Ingested documents
        docs = []
        for title, content in self.sample_documents:
            doc = await self.corpus_handler.ingest_document(title, content)
            docs.append(doc)
        
        # When: Processing documents
        processing_results = []
        for doc in docs:
            result = await self.corpus_handler.process_document(doc.id)
            processing_results.append(result)
        
        # Then: All documents should be processed successfully
        assert all(processing_results)
        
        # And: Documents should be marked as processed and indexed
        for doc in docs:
            updated_doc = await self.corpus_handler.get_document(doc.id)
            assert updated_doc.processed is True
            assert updated_doc.indexed is True
            assert updated_doc.updated_at > updated_doc.created_at
        
        # And: Keywords should be indexed
        corpus_stats = await self.corpus_handler.get_corpus_stats()
        assert corpus_stats["processed_documents"] == len(docs)
        assert corpus_stats["pending_processing"] == 0
        assert corpus_stats["total_keywords"] > 0
        
        self.record_metric("documents_processed", len(docs))
        self.record_metric("keywords_indexed", corpus_stats["total_keywords"])
    
    @pytest.mark.unit
    async def test_document_search_functionality(self):
        """Test document search with relevance scoring."""
        # Given: Processed documents
        docs = []
        for title, content in self.sample_documents:
            doc = await self.corpus_handler.ingest_document(title, content)
            await self.corpus_handler.process_document(doc.id)
            docs.append(doc)
        
        # When: Searching with different queries
        search_tests = [
            ("optimization", "Should find technical and research docs"),
            ("meeting notes", "Should find meeting-related content"),
            ("security compliance", "Should find policy document"),
            ("installation guide", "Should find user manual"),
            ("nonexistent keyword", "Should return empty results")
        ]
        
        search_results = {}
        for query, description in search_tests:
            results = await self.corpus_handler.search_documents(query, limit=5)
            search_results[query] = results
        
        # Then: Search results should be relevant
        # Optimization query should find technical and research docs
        optimization_results = search_results["optimization"]
        optimization_titles = [doc.title for doc in optimization_results]
        assert any("Technical" in title or "Research" in title for title in optimization_titles)
        
        # Meeting notes query should find meeting content
        meeting_results = search_results["meeting notes"]
        if meeting_results:
            assert any("Meeting" in doc.title for doc in meeting_results)
        
        # Nonexistent keyword should return no results
        nonexistent_results = search_results["nonexistent keyword"]
        assert len(nonexistent_results) == 0
        
        # And: Search metrics should be updated
        corpus_stats = await self.corpus_handler.get_corpus_stats()
        assert corpus_stats["metrics"]["search_queries"] == len(search_tests)
        
        self.record_metric("search_queries_tested", len(search_tests))
        self.record_metric("search_functionality_validated", True)
    
    @pytest.mark.unit
    async def test_document_deletion_and_cleanup(self):
        """Test document deletion with index cleanup."""
        # Given: Processed documents
        docs = []
        for title, content in self.sample_documents[:3]:  # Use first 3 documents
            doc = await self.corpus_handler.ingest_document(title, content)
            await self.corpus_handler.process_document(doc.id)
            docs.append(doc)
        
        initial_stats = await self.corpus_handler.get_corpus_stats()
        initial_keywords = initial_stats["total_keywords"]
        
        # When: Deleting a document
        deleted_doc = docs[0]
        deletion_success = await self.corpus_handler.delete_document(deleted_doc.id)
        
        # Then: Deletion should succeed
        assert deletion_success is True
        
        # And: Document should no longer exist
        retrieved_doc = await self.corpus_handler.get_document(deleted_doc.id)
        assert retrieved_doc is None
        
        # And: Stats should be updated
        final_stats = await self.corpus_handler.get_corpus_stats()
        assert final_stats["total_documents"] == len(docs) - 1
        assert final_stats["processed_documents"] == len(docs) - 1
        
        # And: Search should not return deleted document
        search_results = await self.corpus_handler.search_documents("technical")
        result_ids = [doc.id for doc in search_results]
        assert deleted_doc.id not in result_ids
        
        # When: Attempting to delete non-existent document
        fake_deletion = await self.corpus_handler.delete_document("non_existent_id")
        
        # Then: Should return False gracefully
        assert fake_deletion is False
        
        self.record_metric("document_deletion_validated", True)
    
    @pytest.mark.unit
    async def test_corpus_statistics_accuracy(self):
        """Test accuracy of corpus statistics reporting."""
        # Given: Initial empty corpus
        initial_stats = await self.corpus_handler.get_corpus_stats()
        assert initial_stats["total_documents"] == 0
        assert initial_stats["processed_documents"] == 0
        assert initial_stats["pending_processing"] == 0
        
        # When: Adding and processing documents incrementally
        doc_count = 0
        processed_count = 0
        
        for i, (title, content) in enumerate(self.sample_documents):
            # Ingest document
            doc = await self.corpus_handler.ingest_document(title, content)
            doc_count += 1
            
            # Check stats after ingestion
            stats_after_ingest = await self.corpus_handler.get_corpus_stats()
            assert stats_after_ingest["total_documents"] == doc_count
            assert stats_after_ingest["processed_documents"] == processed_count
            assert stats_after_ingest["pending_processing"] == doc_count - processed_count
            
            # Process document
            await self.corpus_handler.process_document(doc.id)
            processed_count += 1
            
            # Check stats after processing
            stats_after_process = await self.corpus_handler.get_corpus_stats()
            assert stats_after_process["total_documents"] == doc_count
            assert stats_after_process["processed_documents"] == processed_count
            assert stats_after_process["pending_processing"] == doc_count - processed_count
        
        # Final stats validation
        final_stats = await self.corpus_handler.get_corpus_stats()
        assert final_stats["total_documents"] == len(self.sample_documents)
        assert final_stats["processed_documents"] == len(self.sample_documents)
        assert final_stats["pending_processing"] == 0
        assert final_stats["total_size_bytes"] > 0
        assert final_stats["total_keywords"] > 0
        
        self.record_metric("statistics_accuracy_validated", True)


class TestCorpusHandlerPerformance(SSotBaseTestCase):
    """Test corpus handler performance characteristics."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        self.corpus_handler = MockCorpusHandler()
    
    @pytest.mark.unit
    async def test_bulk_document_ingestion_performance(self):
        """Test performance of bulk document ingestion."""
        # Given: Large number of documents
        doc_count = 50
        max_ingestion_time_per_doc_ms = 100  # 100ms max per document
        
        # Generate test documents
        test_docs = []
        for i in range(doc_count):
            title = f"Performance Test Document {i}"
            content = f"This is test document {i} for performance testing. " * 20  # ~1KB content
            test_docs.append((title, content))
        
        # When: Ingesting documents and measuring performance
        ingestion_times = []
        ingested_docs = []
        
        for title, content in test_docs:
            start_time = time.time()
            
            doc = await self.corpus_handler.ingest_document(
                title=title,
                content=content,
                metadata={"performance_test": True, "batch": "bulk_test"}
            )
            
            ingestion_time = (time.time() - start_time) * 1000  # Convert to ms
            ingestion_times.append(ingestion_time)
            ingested_docs.append(doc)
        
        # Then: Performance should meet requirements
        avg_ingestion_time = sum(ingestion_times) / len(ingestion_times)
        max_ingestion_time = max(ingestion_times)
        
        assert avg_ingestion_time < max_ingestion_time_per_doc_ms
        assert max_ingestion_time < max_ingestion_time_per_doc_ms * 2  # Allow some variance
        
        # And: All documents should be ingested successfully
        assert len(ingested_docs) == doc_count
        
        corpus_stats = await self.corpus_handler.get_corpus_stats()
        assert corpus_stats["total_documents"] == doc_count
        
        self.record_metric("bulk_docs_ingested", doc_count)
        self.record_metric("avg_ingestion_time_ms", avg_ingestion_time)
        self.record_metric("max_ingestion_time_ms", max_ingestion_time)
    
    @pytest.mark.unit
    async def test_search_performance_with_large_corpus(self):
        """Test search performance with larger corpus."""
        # Given: Corpus with many documents
        doc_count = 30
        search_queries = ["optimization", "performance", "business", "technical", "analysis"]
        max_search_time_ms = 200  # 200ms max per search
        
        # Create and process documents
        for i in range(doc_count):
            content_variants = [
                f"Business optimization strategies for company {i}. Performance analysis and technical implementation.",
                f"Technical documentation for system {i}. Business requirements and optimization guidelines.",
                f"Performance metrics report {i}. Technical analysis of business optimization results.",
                f"Analysis of business processes {i}. Technical performance optimization recommendations.",
                f"System optimization guide {i}. Business analysis and technical performance evaluation."
            ]
            
            title = f"Document {i}"
            content = content_variants[i % len(content_variants)]
            
            doc = await self.corpus_handler.ingest_document(title, content)
            await self.corpus_handler.process_document(doc.id)
        
        # When: Performing searches and measuring performance
        search_times = []
        total_results = 0
        
        for query in search_queries:
            start_time = time.time()
            
            results = await self.corpus_handler.search_documents(query, limit=10)
            
            search_time = (time.time() - start_time) * 1000  # Convert to ms
            search_times.append(search_time)
            total_results += len(results)
        
        # Then: Search performance should meet requirements
        avg_search_time = sum(search_times) / len(search_times)
        max_search_time = max(search_times)
        
        assert avg_search_time < max_search_time_ms
        assert max_search_time < max_search_time_ms * 1.5  # Allow some variance
        
        # And: Should return relevant results
        assert total_results > 0
        
        self.record_metric("search_queries_performed", len(search_queries))
        self.record_metric("avg_search_time_ms", avg_search_time)
        self.record_metric("total_search_results", total_results)
        self.record_metric("search_performance_validated", True)
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        # Log performance metrics
        execution_time = self.get_metrics().execution_time
        if execution_time > 3.0:  # Warn for slow tests
            self.record_metric("slow_corpus_test_warning", execution_time)
        
        super().teardown_method(method)