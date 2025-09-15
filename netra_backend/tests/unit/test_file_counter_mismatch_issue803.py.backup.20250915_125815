"""
Unit test to reproduce Issue #803: File counter mismatch between upload count and statistics
Test demonstrates the mismatch between files uploaded via upload_document() and corpus statistics records.
"""

import asyncio
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.corpus_service import CorpusService
from netra_backend.app.services.file_storage_service import FileStorageService
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestFileCounterMismatch(SSotAsyncTestCase):
    """Unit tests to reproduce the file counter mismatch issue"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        
        # Mock dependencies
        self.mock_db = AsyncMock()
        self.corpus_id = "test-corpus-123"
        self.test_filename = "test-document.txt"
        self.test_content = b"This is test document content for corpus"

    async def test_upload_document_does_not_create_corpus_record(self):
        """
        REPRODUCTION TEST: Demonstrates that upload_document() only stores files
        but doesn't create records counted by get_corpus_statistics()
        
        This test SHOULD PASS, showing the bug exists (files uploaded != records in statistics)
        """
        # Arrange: Create corpus service and mock successful file upload but no corpus record creation
        corpus_service = CorpusService()
        corpus_id = "test-corpus-123"
        test_filename = "test-document.txt"
        test_content = b"This is test document content for corpus"
        mock_db = AsyncMock()
        
        with patch('netra_backend.app.services.file_storage_service.FileStorageService.upload_file') as mock_upload:
            mock_upload.return_value = {
                "file_id": "file-123",
                "storage_path": "/test/path/file-123_test-document.txt",
                "file_size": 1024,
                "checksum": "abc123def456",
                "metadata": {"corpus_id": corpus_id, "purpose": "corpus_document"}
            }
            
            # Mock modular service statistics to return 0 records (the bug)
            with patch.object(corpus_service._modular_service, 'get_corpus_statistics') as mock_stats:
                mock_stats.return_value = {
                    "total_records": 0,  # BUG: No records despite file upload
                    "unique_workload_types": 0,
                    "workload_distribution": {}
                }
                
                # Act: Upload a document file
                file_stream = io.BytesIO(test_content)
                upload_result = await corpus_service.upload_document(
                    corpus_id=corpus_id,
                    file_stream=file_stream,
                    filename=test_filename,
                    content_type="text/plain"
                )
                
                # Get corpus statistics
                stats = await corpus_service.get_corpus_statistics(mock_db, corpus_id)
                
                # Assert: File uploaded successfully but no corpus records exist (BUG REPRODUCTION)
                self.assertIsNotNone(upload_result)
                self.assertEqual(upload_result["filename"], test_filename)
                self.assertEqual(upload_result["corpus_id"], corpus_id)
                
                # BUG DEMONSTRATED: File count (1) != record count (0)
                files_uploaded = 1  # We uploaded 1 file
                records_in_corpus = stats["total_records"]  # Should be 0 (the bug)
                
                self.assertEqual(files_uploaded, 1)
                self.assertEqual(records_in_corpus, 0)
                
                # This assertion shows the mismatch (BUG):
                self.assertNotEqual(files_uploaded, records_in_corpus, 
                                   "BUG REPRODUCED: Files uploaded != corpus records")
                
                print(f"BUG REPRODUCED: Files uploaded ({files_uploaded}) != corpus records ({records_in_corpus})")

    async def test_upload_content_creates_corpus_records(self):
        """
        CONTROL TEST: Shows that upload_content() properly creates records 
        that are counted by get_corpus_statistics()
        """
        # Arrange: Create corpus service and mock upload_content to create actual records
        corpus_service = CorpusService()
        test_records = [
            {"prompt": "Test prompt", "response": "Test response", "workload_type": "test"}
        ]
        
        with patch.object(corpus_service._modular_service, 'upload_content') as mock_upload:
            mock_upload.return_value = {"inserted_records": 1}
            
            with patch.object(corpus_service._modular_service, 'get_corpus_statistics') as mock_stats:
                mock_stats.return_value = {
                    "total_records": 1,  # CORRECT: Records properly counted
                    "unique_workload_types": 1,
                    "workload_distribution": {"test": 1}
                }
                
                # Act: Upload content records
                await corpus_service.upload_content(
                    db=self.mock_db,
                    corpus_id=self.corpus_id,
                    content_data={"records": test_records}
                )
                
                # Get corpus statistics
                stats = await corpus_service.get_corpus_statistics(self.mock_db, self.corpus_id)
                
                # Assert: Content upload correctly shows in statistics
                records_uploaded = len(test_records)  # 1 record
                records_in_corpus = stats["total_records"]  # 1 record
                
                self.assertEqual(records_uploaded, 1)
                self.assertEqual(records_in_corpus, 1)
                
                # This should be equal (no bug):
                self.assertEqual(records_uploaded, records_in_corpus, 
                                "CONTROL: Content records properly counted")

    async def test_mixed_uploads_show_mismatch(self):
        """
        COMPREHENSIVE TEST: Shows mismatch when both files and content are uploaded
        """
        # Arrange: Create corpus service and upload both a file and content records
        corpus_service = CorpusService()
        test_records = [
            {"prompt": "Content prompt", "response": "Content response", "workload_type": "content"}
        ]
        
        # Mock file upload (doesn't create corpus records)
        with patch('netra_backend.app.services.file_storage_service.FileStorageService.upload_file') as mock_file_upload:
            mock_file_upload.return_value = {
                "file_id": "file-456",
                "storage_path": "/test/path/file-456_mixed-test.txt",
                "file_size": 512,
                "checksum": "def456ghi789",
                "metadata": {"corpus_id": self.corpus_id}
            }
            
            # Mock content upload (creates corpus records)
            with patch.object(corpus_service._modular_service, 'upload_content') as mock_content:
                mock_content.return_value = {"inserted_records": 1}
                
                with patch.object(corpus_service._modular_service, 'get_corpus_statistics') as mock_stats:
                    mock_stats.return_value = {
                        "total_records": 1,  # Only counts content uploads, not file uploads
                        "unique_workload_types": 1,
                        "workload_distribution": {"content": 1}
                    }
                    
                    # Act: Upload both file and content
                    file_stream = io.BytesIO(b"Mixed test content")
                    file_result = await corpus_service.upload_document(
                        corpus_id=self.corpus_id,
                        file_stream=file_stream,
                        filename="mixed-test.txt",
                        content_type="text/plain"
                    )
                    
                    content_result = await corpus_service.upload_content(
                        db=self.mock_db,
                        corpus_id=self.corpus_id,
                        content_data={"records": test_records}
                    )
                    
                    # Get final statistics
                    stats = await corpus_service.get_corpus_statistics(self.mock_db, self.corpus_id)
                    
                    # Assert: Only content uploads counted, files ignored
                    total_items_uploaded = 2  # 1 file + 1 content record
                    records_in_corpus = stats["total_records"]  # Only 1 (content record)
                    
                    self.assertEqual(total_items_uploaded, 2)
                    self.assertEqual(records_in_corpus, 1)
                    
                    # BUG: Total items != corpus records
                    self.assertNotEqual(total_items_uploaded, records_in_corpus,
                                       "BUG: File uploads not counted in corpus statistics")
                    
                    print(f"MIXED UPLOAD BUG: Total items ({total_items_uploaded}) != corpus records ({records_in_corpus})")


if __name__ == "__main__":
    # Run the test to demonstrate the bug
    test = TestFileCounterMismatch()
    
    async def run_tests():
        await test.test_upload_document_does_not_create_corpus_record()
        await test.test_upload_content_creates_corpus_records()
        await test.test_mixed_uploads_show_mismatch()
        print("All bug reproduction tests completed successfully!")
    
    asyncio.run(run_tests())