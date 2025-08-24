"""
RED TEAM TEST 18: File Upload and Storage

CRITICAL: This test is DESIGNED TO FAIL initially to expose real integration issues.
Tests document upload for corpus creation and file storage management.

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise (corpus creation features)
- Business Goal: Content Management, AI Training Data, User Productivity
- Value Impact: Failed uploads break corpus creation and AI model training workflows
- Strategic Impact: Core content foundation for AI optimization capabilities

Testing Level: L3 (Real services, real file system, minimal mocking)
Expected Initial Result: FAILURE (exposes real file handling gaps)
"""

import asyncio
import hashlib
import io
import os
import secrets
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, BinaryIO

import pytest
from fastapi.testclient import TestClient
from fastapi import UploadFile
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
# Fix imports with error handling
try:
    from netra_backend.app.core.network_constants import DatabaseConstants, ServicePorts
except ImportError:
    class DatabaseConstants:
        pass
    class ServicePorts:
        pass

# CorpusService exists
from netra_backend.app.services.corpus_service import CorpusService

# FileStorageService exists  
from netra_backend.app.services.file_storage_service import FileStorageService

try:
    from netra_backend.app.db.models_content import Corpus, Document
except ImportError:
    # Try alternative import
    try:
        from netra_backend.app.db.models import Corpus, Document
    except ImportError:
        from unittest.mock import Mock, AsyncMock, MagicMock
        Corpus = Mock()
        Document = Mock()

try:
    from netra_backend.app.schemas.corpus import CorpusCreate, DocumentCreate
except ImportError:
    from dataclasses import dataclass
    from typing import Optional
    
    @dataclass
    class CorpusCreate:
        name: str
        description: Optional[str] = None
    
    @dataclass
    class DocumentCreate:
        title: str
        content: str
        corpus_id: str


class TestFileUploadAndStorage:
    """
    RED TEAM TEST 18: File Upload and Storage
    
    Tests critical file upload and storage functionality for corpus creation.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        try:
            database_url = DatabaseConstants.build_postgres_url(
                user="test", password="test",
                port=ServicePorts.POSTGRES_DEFAULT,
                database="netra_test"
            )
            
            engine = create_async_engine(database_url, echo=False)
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            
            # Test real connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            if 'engine' in locals():
                await engine.dispose()

    @pytest.fixture
    def real_test_client(self):
        """Real FastAPI test client - no mocking of the application."""
        return TestClient(app)

    @pytest.fixture
    def temp_upload_directory(self):
        """Create temporary directory for file upload testing."""
        with tempfile.TemporaryDirectory(prefix="netra_upload_test_") as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.asyncio
    async def test_01_basic_file_upload_fails(
        self, real_database_session, temp_upload_directory, real_test_client
    ):
        """
        Test 18A: Basic File Upload (EXPECTED TO FAIL)
        
        Tests basic file upload functionality for document creation.
        Will likely FAIL because:
        1. File upload endpoints may not be implemented
        2. File validation may be missing
        3. Storage path configuration may be incorrect
        """
        try:
            # Create test file content
            test_content = b"""
This is a test document for corpus creation.
It contains multiple paragraphs and should be processed correctly.

The document includes various text elements:
- Bullet points
- Technical terms
- Structured content

This content will be used to test the file upload and storage pipeline.
"""
            
            test_filename = f"test_document_{secrets.token_urlsafe(8)}.txt"
            test_file_path = temp_upload_directory / test_filename
            
            # Write test file
            with open(test_file_path, 'wb') as f:
                f.write(test_content)
            
            # Create file storage service
            file_storage_service = FileStorageService()
            
            # FAILURE EXPECTED HERE - file upload may not be implemented
            with open(test_file_path, 'rb') as file_stream:
                upload_result = await file_storage_service.upload_file(
                    file_stream=file_stream,
                    filename=test_filename,
                    content_type="text/plain",
                    metadata={
                        "purpose": "corpus_document",
                        "uploaded_by": "red_team_test",
                        "test_id": "basic_upload"
                    }
                )
            
            assert upload_result is not None, "File upload returned None"
            assert "file_id" in upload_result, "Upload result should contain file_id"
            assert "storage_path" in upload_result, "Upload result should contain storage_path"
            assert "file_size" in upload_result, "Upload result should contain file_size"
            
            file_id = upload_result["file_id"]
            storage_path = upload_result["storage_path"]
            
            # Verify file size is correct
            expected_size = len(test_content)
            actual_size = upload_result["file_size"]
            assert actual_size == expected_size, \
                f"File size mismatch: expected {expected_size}, got {actual_size}"
            
            # Verify file was actually stored
            stored_file_path = Path(storage_path)
            assert stored_file_path.exists(), f"Uploaded file not found at {storage_path}"
            assert stored_file_path.is_file(), f"Storage path is not a file: {storage_path}"
            
            # Verify file content integrity
            with open(stored_file_path, 'rb') as stored_file:
                stored_content = stored_file.read()
            
            assert stored_content == test_content, \
                "Stored file content does not match original content"
            
            # Verify file metadata
            if hasattr(file_storage_service, 'get_file_metadata'):
                metadata = await file_storage_service.get_file_metadata(file_id)
                
                assert metadata is not None, "File metadata should be available"
                assert metadata.get("filename") == test_filename, \
                    f"Filename mismatch in metadata: expected {test_filename}, got {metadata.get('filename')}"
                assert metadata.get("content_type") == "text/plain", \
                    f"Content type mismatch: expected text/plain, got {metadata.get('content_type')}"
                    
        except ImportError as e:
            pytest.fail(f"File storage service not available: {e}")
        except Exception as e:
            pytest.fail(f"Basic file upload test failed: {e}")

    @pytest.mark.asyncio
    async def test_02_corpus_document_creation_fails(
        self, real_database_session, temp_upload_directory
    ):
        """
        Test 18B: Corpus Document Creation (EXPECTED TO FAIL)
        
        Tests document creation for corpus through file upload.
        Will likely FAIL because:
        1. Corpus service integration may not work
        2. Document processing pipeline may be incomplete
        3. Metadata extraction may fail
        """
        try:
            # Create test corpus first
            corpus_service = CorpusService()
            
            corpus_data = CorpusCreate(
                name=f"Test Corpus {secrets.token_urlsafe(8)}",
                description="Test corpus for file upload testing",
                metadata={"created_by": "red_team_test", "test_purpose": "file_upload"}
            )
            
            # FAILURE EXPECTED HERE - corpus creation may not work
            created_corpus = await corpus_service.create_corpus(corpus_data)
            
            assert created_corpus is not None, "Corpus creation failed"
            assert hasattr(created_corpus, 'id'), "Corpus should have an ID"
            
            corpus_id = created_corpus.id
            
            # Create multiple test documents with different formats
            test_documents = [
                {
                    "filename": "document1.txt",
                    "content": b"First test document with plain text content.",
                    "content_type": "text/plain"
                },
                {
                    "filename": "document2.md",
                    "content": b"# Markdown Document\n\nThis is a **markdown** document with *formatting*.",
                    "content_type": "text/markdown"
                },
                {
                    "filename": "document3.json",
                    "content": b'{"type": "structured", "content": "JSON document", "metadata": {"version": 1}}',
                    "content_type": "application/json"
                }
            ]
            
            uploaded_documents = []
            
            for doc_info in test_documents:
                # Write test file
                test_file_path = temp_upload_directory / doc_info["filename"]
                with open(test_file_path, 'wb') as f:
                    f.write(doc_info["content"])
                
                # Upload document to corpus
                with open(test_file_path, 'rb') as file_stream:
                    # FAILURE EXPECTED HERE - document upload to corpus may fail
                    document_result = await corpus_service.upload_document(
                        corpus_id=corpus_id,
                        file_stream=file_stream,
                        filename=doc_info["filename"],
                        content_type=doc_info["content_type"],
                        metadata={
                            "upload_source": "red_team_test",
                            "document_type": "test_document"
                        }
                    )
                
                assert document_result is not None, f"Document upload failed for {doc_info['filename']}"
                assert "document_id" in document_result, \
                    f"Document result should contain document_id for {doc_info['filename']}"
                
                uploaded_documents.append(document_result)
            
            # Verify documents were created in database
            for i, doc_result in enumerate(uploaded_documents):
                document_id = doc_result["document_id"]
                
                doc_query = await real_database_session.execute(
                    select(Document).where(Document.id == document_id)
                )
                stored_document = doc_query.scalar_one_or_none()
                
                assert stored_document is not None, \
                    f"Document {document_id} not found in database"
                assert str(stored_document.corpus_id) == str(corpus_id), \
                    f"Document corpus_id mismatch: expected {corpus_id}, got {stored_document.corpus_id}"
                assert stored_document.filename == test_documents[i]["filename"], \
                    f"Filename mismatch: expected {test_documents[i]['filename']}, got {stored_document.filename}"
            
            # Verify corpus document count
            corpus_query = await real_database_session.execute(
                select(Corpus).where(Corpus.id == corpus_id)
            )
            updated_corpus = corpus_query.scalar_one()
            
            if hasattr(updated_corpus, 'document_count'):
                expected_count = len(test_documents)
                actual_count = updated_corpus.document_count
                assert actual_count == expected_count, \
                    f"Corpus document count mismatch: expected {expected_count}, got {actual_count}"
                    
        except Exception as e:
            pytest.fail(f"Corpus document creation test failed: {e}")

    @pytest.mark.asyncio
    async def test_03_large_file_handling_fails(self, temp_upload_directory):
        """
        Test 18C: Large File Handling (EXPECTED TO FAIL)
        
        Tests handling of large file uploads and storage.
        Will likely FAIL because:
        1. File size limits may not be configured
        2. Streaming upload may not be implemented
        3. Progress tracking may be missing
        """
        try:
            # Create large test file (10MB)
            large_file_size = 10 * 1024 * 1024  # 10MB
            large_filename = f"large_test_file_{secrets.token_urlsafe(8)}.dat"
            large_file_path = temp_upload_directory / large_filename
            
            # Generate large file with pseudo-random content
            chunk_size = 1024 * 1024  # 1MB chunks
            written_size = 0
            
            with open(large_file_path, 'wb') as f:
                while written_size < large_file_size:
                    remaining = min(chunk_size, large_file_size - written_size)
                    chunk_data = secrets.token_bytes(remaining)
                    f.write(chunk_data)
                    written_size += remaining
            
            # Calculate file checksum for integrity verification
            file_hash = hashlib.sha256()
            with open(large_file_path, 'rb') as f:
                while chunk := f.read(8192):
                    file_hash.update(chunk)
            expected_checksum = file_hash.hexdigest()
            
            # Test large file upload
            file_storage_service = FileStorageService()
            
            # FAILURE EXPECTED HERE - large file upload may fail or timeout
            with open(large_file_path, 'rb') as file_stream:
                upload_start_time = asyncio.get_event_loop().time()
                
                upload_result = await file_storage_service.upload_large_file(
                    file_stream=file_stream,
                    filename=large_filename,
                    content_type="application/octet-stream",
                    file_size=large_file_size,
                    chunk_size=chunk_size,
                    metadata={
                        "purpose": "large_file_test",
                        "expected_checksum": expected_checksum
                    }
                )
                
                upload_duration = asyncio.get_event_loop().time() - upload_start_time
            
            assert upload_result is not None, "Large file upload returned None"
            assert "file_id" in upload_result, "Upload result should contain file_id"
            assert upload_result["file_size"] == large_file_size, \
                f"File size mismatch: expected {large_file_size}, got {upload_result['file_size']}"
            
            # Verify upload performance
            max_upload_time = 60  # 60 seconds for 10MB
            assert upload_duration < max_upload_time, \
                f"Large file upload too slow: {upload_duration:.2f}s (max: {max_upload_time}s)"
            
            upload_throughput = large_file_size / upload_duration / (1024 * 1024)  # MB/s
            min_throughput = 0.5  # 0.5 MB/s minimum
            assert upload_throughput >= min_throughput, \
                f"Upload throughput too low: {upload_throughput:.2f} MB/s (min: {min_throughput})"
            
            # Verify file integrity
            storage_path = upload_result["storage_path"]
            stored_file_path = Path(storage_path)
            
            assert stored_file_path.exists(), "Large file not found in storage"
            assert stored_file_path.stat().st_size == large_file_size, \
                f"Stored file size mismatch: expected {large_file_size}, got {stored_file_path.stat().st_size}"
            
            # Verify checksum
            stored_hash = hashlib.sha256()
            with open(stored_file_path, 'rb') as f:
                while chunk := f.read(8192):
                    stored_hash.update(chunk)
            stored_checksum = stored_hash.hexdigest()
            
            assert stored_checksum == expected_checksum, \
                f"File integrity check failed: checksums don't match"
                
        except Exception as e:
            pytest.fail(f"Large file handling test failed: {e}")

    @pytest.mark.asyncio
    async def test_04_concurrent_uploads_fails(self, temp_upload_directory):
        """
        Test 18D: Concurrent File Uploads (EXPECTED TO FAIL)
        
        Tests handling of multiple simultaneous file uploads.
        Will likely FAIL because:
        1. Concurrency controls may not be implemented
        2. Resource contention may occur
        3. File locking may cause issues
        """
        try:
            # Create multiple test files for concurrent upload
            num_files = 5
            test_files = []
            
            for i in range(num_files):
                filename = f"concurrent_test_{i}_{secrets.token_urlsafe(8)}.txt"
                content = f"Concurrent upload test file {i}\n" * 100  # Create some content
                file_path = temp_upload_directory / filename
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                test_files.append({
                    "path": file_path,
                    "filename": filename,
                    "content": content.encode(),
                    "size": len(content.encode())
                })
            
            # Define concurrent upload function
            async def upload_file_async(file_info: Dict[str, Any]) -> Dict[str, Any]:
                """Upload a single file and return result."""
                try:
                    file_storage_service = FileStorageService()
                    
                    with open(file_info["path"], 'rb') as file_stream:
                        result = await file_storage_service.upload_file(
                            file_stream=file_stream,
                            filename=file_info["filename"],
                            content_type="text/plain",
                            metadata={
                                "upload_type": "concurrent_test",
                                "file_index": file_info.get("index", 0)
                            }
                        )
                    
                    return {
                        "filename": file_info["filename"],
                        "status": "success",
                        "result": result
                    }
                    
                except Exception as e:
                    return {
                        "filename": file_info["filename"],
                        "status": "error",
                        "error": str(e)
                    }
            
            # Add index to file info
            for i, file_info in enumerate(test_files):
                file_info["index"] = i
            
            # Execute concurrent uploads
            upload_start_time = asyncio.get_event_loop().time()
            
            # FAILURE EXPECTED HERE - concurrent uploads may fail
            upload_tasks = [upload_file_async(file_info) for file_info in test_files]
            upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            
            upload_duration = asyncio.get_event_loop().time() - upload_start_time
            
            # Analyze results
            successful_uploads = 0
            failed_uploads = 0
            exceptions = []
            
            for result in upload_results:
                if isinstance(result, Exception):
                    exceptions.append(str(result))
                    failed_uploads += 1
                elif result["status"] == "success":
                    successful_uploads += 1
                else:
                    failed_uploads += 1
            
            # At least 80% should succeed for basic concurrency
            success_rate = successful_uploads / num_files
            assert success_rate >= 0.8, \
                f"Concurrent upload failed: {success_rate*100:.1f}% success rate. " \
                f"Exceptions: {exceptions[:2]}"
            
            # Verify upload performance
            max_concurrent_time = 30  # 30 seconds for 5 small files
            assert upload_duration < max_concurrent_time, \
                f"Concurrent uploads too slow: {upload_duration:.2f}s (max: {max_concurrent_time}s)"
            
            # Verify all successful uploads
            for i, result in enumerate(upload_results):
                if not isinstance(result, Exception) and result["status"] == "success":
                    upload_result = result["result"]
                    
                    # Verify file was stored
                    storage_path = upload_result["storage_path"]
                    assert Path(storage_path).exists(), \
                        f"Concurrent upload file {i} not found in storage"
                    
                    # Verify file size
                    expected_size = test_files[i]["size"]
                    actual_size = upload_result["file_size"]
                    assert actual_size == expected_size, \
                        f"File {i} size mismatch: expected {expected_size}, got {actual_size}"
                        
        except Exception as e:
            pytest.fail(f"Concurrent uploads test failed: {e}")

    @pytest.mark.asyncio
    async def test_05_file_cleanup_and_deletion_fails(self, temp_upload_directory):
        """
        Test 18E: File Cleanup and Deletion (EXPECTED TO FAIL)
        
        Tests file deletion and cleanup functionality.
        Will likely FAIL because:
        1. File deletion may not be implemented
        2. Cleanup processes may not work
        3. Orphaned file detection may be missing
        """
        try:
            # Upload test files for deletion testing
            file_storage_service = FileStorageService()
            uploaded_files = []
            
            for i in range(3):
                filename = f"deletion_test_{i}_{secrets.token_urlsafe(8)}.txt"
                content = f"File for deletion test {i}"
                file_path = temp_upload_directory / filename
                
                with open(file_path, 'w') as f:
                    f.write(content)
                
                with open(file_path, 'rb') as file_stream:
                    upload_result = await file_storage_service.upload_file(
                        file_stream=file_stream,
                        filename=filename,
                        content_type="text/plain",
                        metadata={"purpose": "deletion_test"}
                    )
                
                uploaded_files.append(upload_result)
            
            # Verify files were uploaded successfully
            for upload_result in uploaded_files:
                storage_path = upload_result["storage_path"]
                assert Path(storage_path).exists(), \
                    f"Uploaded file not found: {storage_path}"
            
            # Test individual file deletion
            first_file = uploaded_files[0]
            file_id = first_file["file_id"]
            storage_path = first_file["storage_path"]
            
            # FAILURE EXPECTED HERE - file deletion may not be implemented
            deletion_result = await file_storage_service.delete_file(file_id)
            
            assert deletion_result is not None, "File deletion returned None"
            assert "status" in deletion_result, "Deletion result should include status"
            assert deletion_result["status"] == "success", \
                f"File deletion failed: {deletion_result.get('error', 'Unknown error')}"
            
            # Verify file was actually deleted
            assert not Path(storage_path).exists(), \
                f"Deleted file still exists: {storage_path}"
            
            # Test batch deletion
            remaining_files = uploaded_files[1:]
            remaining_file_ids = [f["file_id"] for f in remaining_files]
            
            if hasattr(file_storage_service, 'delete_files_batch'):
                batch_deletion_result = await file_storage_service.delete_files_batch(
                    remaining_file_ids
                )
                
                assert batch_deletion_result is not None, "Batch deletion returned None"
                assert "deleted_count" in batch_deletion_result, \
                    "Batch deletion should include deleted count"
                assert batch_deletion_result["deleted_count"] == len(remaining_files), \
                    f"Expected {len(remaining_files)} files deleted, got {batch_deletion_result['deleted_count']}"
                
                # Verify all files were deleted
                for file_info in remaining_files:
                    storage_path = file_info["storage_path"]
                    assert not Path(storage_path).exists(), \
                        f"Batch deleted file still exists: {storage_path}"
            
            else:
                # Individual deletion fallback
                for file_info in remaining_files:
                    await file_storage_service.delete_file(file_info["file_id"])
            
            # Test cleanup orphaned files
            if hasattr(file_storage_service, 'cleanup_orphaned_files'):
                cleanup_result = await file_storage_service.cleanup_orphaned_files()
                
                assert "status" in cleanup_result, "Cleanup should return status"
                assert cleanup_result["status"] == "success", \
                    f"Orphaned file cleanup failed: {cleanup_result.get('error', 'Unknown error')}"
                    
        except Exception as e:
            pytest.fail(f"File cleanup and deletion test failed: {e}")


# Utility class for file upload testing
class RedTeamFileUploadTestUtils:
    """Utility methods for file upload and storage testing."""
    
    @staticmethod
    def create_test_file(
        content: str = "Test file content",
        filename: str = "test_file.txt",
        directory: Path = None
    ) -> Path:
        """Create a test file with specified content."""
        if directory is None:
            directory = Path(tempfile.gettempdir())
        
        file_path = directory / filename
        with open(file_path, 'w') as f:
            f.write(content)
        
        return file_path
    
    @staticmethod
    def calculate_file_checksum(file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        hash_obj = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def get_file_info(file_path: Path) -> Dict[str, Any]:
        """Get comprehensive file information."""
        stat = file_path.stat()
        
        return {
            "path": str(file_path),
            "name": file_path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            "checksum": RedTeamFileUploadTestUtils.calculate_file_checksum(file_path)
        }
    
    @staticmethod
    async def verify_file_integrity(
        original_path: Path,
        storage_path: Path
    ) -> Dict[str, Any]:
        """Verify integrity between original and stored file."""
        
        original_info = RedTeamFileUploadTestUtils.get_file_info(original_path)
        stored_info = RedTeamFileUploadTestUtils.get_file_info(storage_path)
        
        integrity_report = {
            "size_match": original_info["size"] == stored_info["size"],
            "checksum_match": original_info["checksum"] == stored_info["checksum"],
            "original_size": original_info["size"],
            "stored_size": stored_info["size"],
            "original_checksum": original_info["checksum"],
            "stored_checksum": stored_info["checksum"]
        }
        
        integrity_report["integrity_verified"] = (
            integrity_report["size_match"] and 
            integrity_report["checksum_match"]
        )
        
        return integrity_report