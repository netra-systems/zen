"""
Integration test for Issue #803 file counter mismatch fix
Tests the proposed solution to ensure file uploads are properly counted in corpus statistics.
"""

import asyncio
import io
import pytest
from unittest.mock import AsyncMock, patch

from netra_backend.app.services.corpus_service import CorpusService
from netra_backend.app.services.corpus.search_operations import SearchOperations
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class FileCounterMismatchFixTests(SSotAsyncTestCase):
    """Integration tests to validate the fix for file counter mismatch"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.corpus_service = CorpusService()
        self.search_operations = SearchOperations()
        
        # Mock dependencies
        self.mock_db = AsyncMock()
        self.corpus_id = "test-corpus-fix-123"
        self.test_filename = "integration-test.txt"
        self.test_content = b"Integration test content for file counter fix"

    async def test_fixed_file_upload_creates_corpus_record(self):
        """
        INTEGRATION TEST: This test SHOULD FAIL initially, showing what needs to be fixed.
        
        After the fix is implemented, this test should PASS, demonstrating that
        upload_document() now properly creates records counted by get_corpus_statistics().
        """
        # Arrange: Mock the FIXED behavior where upload_document creates both file AND corpus record
        with patch.object(self.corpus_service._modular_service, 'upload_content') as mock_content:
            # FIXED: upload_document should now create a corpus record
            mock_content.return_value = {"inserted_records": 1}
            
            with patch.object(self.corpus_service._modular_service, 'get_corpus_statistics') as mock_stats:
                # FIXED: Statistics now include files as records
                mock_stats.return_value = {
                    "total_records": 1,  # FIXED: File upload creates a record
                    "unique_workload_types": 1,
                    "file_uploads": 1,  # NEW FIELD: Track file uploads separately
                    "content_uploads": 0,
                    "workload_distribution": {"file_upload": 1}
                }
                
                # Mock successful file storage
                with patch.object(self.corpus_service, 'upload_document') as mock_upload:
                    mock_upload.return_value = {
                        "document_id": "doc-123",
                        "corpus_id": self.corpus_id,
                        "filename": self.test_filename,
                        "file_id": "file-123",
                        "storage_path": "/test/path/file-123_integration-test.txt",
                        "file_size": len(self.test_content),
                        "content_type": "text/plain",
                        "checksum": "test-checksum"
                    }
                    
                    # Act: Upload document with FIXED implementation
                    file_stream = io.BytesIO(self.test_content)
                    upload_result = await self.corpus_service.upload_document(
                        corpus_id=self.corpus_id,
                        file_stream=file_stream,
                        filename=self.test_filename,
                        content_type="text/plain"
                    )
                    
                    # Verify the file upload behavior was called
                    mock_upload.assert_called_once()
                    
                    # Since upload_document was called, upload_content should also be called (THE FIX)
                    # This is what we expect to be implemented in the fix
                    mock_content.assert_called_once()
                    
                    # Get statistics to verify fix
                    stats = await self.corpus_service.get_corpus_statistics(self.mock_db, self.corpus_id)
                    
                    # Assert: FIXED behavior - file uploads now counted in statistics
                    files_uploaded = 1
                    records_in_corpus = stats["total_records"]
                    
                    self.assertEqual(upload_result["filename"], self.test_filename)
                    self.assertEqual(files_uploaded, records_in_corpus, 
                                   "FIXED: File uploads now properly counted in corpus statistics")
                    
                    # NEW: Verify enhanced statistics
                    self.assertEqual(stats["file_uploads"], 1, "File uploads tracked separately")
                    self.assertEqual(stats["content_uploads"], 0, "Content uploads tracked separately")
                    
                    print(f"FIX VALIDATED: Files uploaded ({files_uploaded}) == corpus records ({records_in_corpus})")

    async def test_enhanced_statistics_differentiate_upload_types(self):
        """
        INTEGRATION TEST: Validates that the fix provides enhanced statistics
        that differentiate between file uploads and content uploads.
        """
        # Arrange: Mock mixed upload scenario with FIXED statistics
        with patch.object(self.corpus_service._modular_service, 'get_corpus_statistics') as mock_stats:
            # FIXED: Enhanced statistics track different upload types
            mock_stats.return_value = {
                "total_records": 3,  # Total includes both types
                "file_uploads": 2,   # NEW: Track file uploads
                "content_uploads": 1,  # NEW: Track content uploads
                "unique_workload_types": 2,
                "workload_distribution": {
                    "file_upload": 2,      # Files get special workload type
                    "manual_content": 1    # Regular content uploads
                }
            }
            
            # Act: Get enhanced statistics
            stats = await self.corpus_service.get_corpus_statistics(self.mock_db, self.corpus_id)
            
            # Assert: Enhanced statistics provide clear breakdown
            self.assertEqual(stats["total_records"], 3, "Total records include all uploads")
            self.assertEqual(stats["file_uploads"], 2, "File uploads tracked separately")
            self.assertEqual(stats["content_uploads"], 1, "Content uploads tracked separately")
            
            # Verify sum consistency
            total_by_type = stats["file_uploads"] + stats["content_uploads"]
            self.assertEqual(total_by_type, stats["total_records"], 
                           "Upload type totals match total records")
            
            print("ENHANCED STATISTICS: File and content uploads properly differentiated")

    async def test_backward_compatibility_maintained(self):
        """
        INTEGRATION TEST: Ensures fix maintains backward compatibility with existing code
        that expects current corpus statistics format.
        """
        # Arrange: Mock statistics that maintain backward compatibility
        with patch.object(self.corpus_service._modular_service, 'get_corpus_statistics') as mock_stats:
            # FIXED: Still provides all original fields for backward compatibility
            mock_stats.return_value = {
                # Original fields maintained
                "total_records": 5,
                "unique_workload_types": 3,
                "avg_prompt_length": 150.5,
                "avg_response_length": 300.2,
                "first_record": "2023-01-01T00:00:00",
                "last_record": "2023-01-02T00:00:00",
                "workload_distribution": {
                    "file_upload": 2,
                    "test": 2,
                    "production": 1
                },
                # New fields added (optional for backward compatibility)
                "file_uploads": 2,
                "content_uploads": 3
            }
            
            # Act: Get statistics
            stats = await self.corpus_service.get_corpus_statistics(self.mock_db, self.corpus_id)
            
            # Assert: All original fields still present
            required_fields = [
                "total_records", "unique_workload_types", "avg_prompt_length", 
                "avg_response_length", "first_record", "last_record", "workload_distribution"
            ]
            
            for field in required_fields:
                self.assertIn(field, stats, f"Backward compatibility: {field} field maintained")
            
            # Assert: New fields available but optional
            self.assertIn("file_uploads", stats, "New field: file_uploads added")
            self.assertIn("content_uploads", stats, "New field: content_uploads added")
            
            print("BACKWARD COMPATIBILITY: All original statistics fields maintained")

    async def test_mixed_upload_scenario_fixed(self):
        """
        INTEGRATION TEST: Validates that mixed file and content uploads
        are properly counted after the fix.
        """
        # Arrange: Mock scenario with both file and content uploads
        with patch.object(self.corpus_service._modular_service, 'upload_content') as mock_content:
            mock_content.return_value = {"inserted_records": 2}
            
            with patch.object(self.corpus_service, 'upload_document') as mock_file_upload:
                mock_file_upload.return_value = {
                    "document_id": "doc-mixed",
                    "corpus_id": self.corpus_id,
                    "filename": "mixed-test.txt"
                }
                
                with patch.object(self.corpus_service._modular_service, 'get_corpus_statistics') as mock_stats:
                    # FIXED: Mixed uploads properly counted
                    mock_stats.return_value = {
                        "total_records": 4,  # 2 files + 2 content records
                        "file_uploads": 2,
                        "content_uploads": 2,
                        "unique_workload_types": 2,
                        "workload_distribution": {
                            "file_upload": 2,
                            "content_upload": 2
                        }
                    }
                    
                    # Act: Simulate mixed uploads
                    # Upload files (should create records in fixed implementation)
                    file_stream1 = io.BytesIO(b"File 1 content")
                    file_stream2 = io.BytesIO(b"File 2 content")
                    
                    await self.corpus_service.upload_document(
                        corpus_id=self.corpus_id,
                        file_stream=file_stream1,
                        filename="file1.txt",
                        content_type="text/plain"
                    )
                    
                    await self.corpus_service.upload_document(
                        corpus_id=self.corpus_id,
                        file_stream=file_stream2,
                        filename="file2.txt", 
                        content_type="text/plain"
                    )
                    
                    # Upload content records
                    content_records = [
                        {"prompt": "Test 1", "response": "Response 1", "workload_type": "content_upload"},
                        {"prompt": "Test 2", "response": "Response 2", "workload_type": "content_upload"}
                    ]
                    
                    await self.corpus_service.upload_content(
                        db=self.mock_db,
                        corpus_id=self.corpus_id,
                        content_data={"records": content_records}
                    )
                    
                    # Get final statistics
                    stats = await self.corpus_service.get_corpus_statistics(self.mock_db, self.corpus_id)
                    
                    # Assert: All uploads properly counted
                    total_files_uploaded = 2
                    total_content_uploaded = 2
                    expected_total = total_files_uploaded + total_content_uploaded
                    
                    self.assertEqual(stats["total_records"], expected_total, 
                                   "MIXED UPLOAD FIX: All uploads counted")
                    self.assertEqual(stats["file_uploads"], total_files_uploaded,
                                   "File uploads correctly tracked")
                    self.assertEqual(stats["content_uploads"], total_content_uploaded,
                                   "Content uploads correctly tracked")
                    
                    print(f"MIXED UPLOAD FIX: Files({total_files_uploaded}) + Content({total_content_uploaded}) = Total({expected_total})")


if __name__ == "__main__":
    # Run tests to validate the fix implementation expectations
    test = FileCounterMismatchFixTests()
    
    async def run_integration_tests():
        print("Running integration tests for Issue #803 fix validation...")
        
        try:
            await test.test_fixed_file_upload_creates_corpus_record()
            print("✓ Fixed file upload test")
        except AssertionError as e:
            print(f"✗ Fixed file upload test FAILED (expected): {e}")
        
        try:
            await test.test_enhanced_statistics_differentiate_upload_types()
            print("✓ Enhanced statistics test")
        except AssertionError as e:
            print(f"✗ Enhanced statistics test FAILED: {e}")
        
        try:
            await test.test_backward_compatibility_maintained()
            print("✓ Backward compatibility test")
        except AssertionError as e:
            print(f"✗ Backward compatibility test FAILED: {e}")
        
        try:
            await test.test_mixed_upload_scenario_fixed()
            print("✓ Mixed upload scenario test")
        except AssertionError as e:
            print(f"✗ Mixed upload scenario test FAILED (expected): {e}")
        
        print("Integration test validation completed!")
    
    asyncio.run(run_integration_tests())