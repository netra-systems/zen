"""
File Upload Test Context - E2E Testing Support
Business Value: $45K MRR - Enables comprehensive document upload validation

Provides context and utilities for file upload pipeline testing.
Follows 450-line limit and 25-line function rules.
"""

import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import aiofiles

from tests.e2e.unified_e2e_harness import UnifiedE2ETestHarness
from tests.e2e.harness_utils import UnifiedTestHarnessComplete


class FileUploadTestContext:
    """Context for file upload testing operations."""
    
    def __init__(self, harness: UnifiedTestHarnessComplete):
        """Initialize file upload test context."""
        self.harness = harness
        self.test_files = {}
        self.upload_results = {}
        self.cleanup_paths = []
    
    async def create_test_pdf(self, size_mb: float = 5.0) -> Path:
        """Create test document file of specified size."""
        content = self._generate_document_content(size_mb)
        file_path = await self._save_temp_file(content, "test_document.txt")
        return file_path
    
    def _generate_document_content(self, size_mb: float) -> bytes:
        """Generate document content of specified size."""
        target_size = int(size_mb * 1024 * 1024)
        base_content = self._create_base_document_content()
        content_cycles = max(1, target_size // len(base_content.encode()))
        full_content = base_content * content_cycles
        return full_content.encode('utf-8')
    
    def _create_base_document_content(self) -> str:
        """Create base document content for analysis testing."""
        return self._get_document_template() * 100
    
    def _get_document_template(self) -> str:
        """Get document template content."""
        return """
TEST DOCUMENT FOR E2E PIPELINE VALIDATION

Executive Summary:
This document serves as a comprehensive test case for the Netra Apex file upload 
and processing pipeline. It contains structured content that enables the system 
to demonstrate document analysis capabilities.

Key Metrics Analysis:
- Processing Speed: Target < 10 seconds
- File Size Support: Up to 5MB documents
- Analysis Accuracy: Full text extraction and metadata processing
- Storage Verification: Multi-layer persistence validation

Business Value Demonstration:
The file upload pipeline directly supports enterprise document analysis features,
providing automated insight extraction that scales with customer AI spend.
This capability represents $45K MRR in potential revenue from enterprise
customers requiring document processing automation.

Technical Implementation:
- Frontend file upload simulation
- Backend processing orchestration  
- Agent-based document analysis
- Real-time WebSocket progress updates
- Multi-layer storage verification

Quality Assurance:
This test validates the complete end-to-end flow without mocking,
ensuring production reliability and performance standards.

"""
    
    async def _save_temp_file(self, content: bytes, filename: str) -> Path:
        """Save content to temporary file."""
        temp_dir = Path(tempfile.gettempdir())
        file_path = temp_dir / f"e2e_test_{int(time.time())}_{filename}"
        await self._write_file_content(file_path, content)
        self.cleanup_paths.append(file_path)
        return file_path
    
    async def _write_file_content(self, file_path: Path, content: bytes) -> None:
        """Write content to file."""
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
    
    async def test_cleanup_test_files(self) -> None:
        """Cleanup all test files."""
        for file_path in self.cleanup_paths:
            await self._cleanup_single_file(file_path)
    
    async def _cleanup_single_file(self, file_path: Path) -> None:
        """Cleanup single test file."""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Cleanup warning: {e}")


def create_file_upload_context(harness: UnifiedE2ETestHarness) -> FileUploadTestContext:
    """Create file upload test context instance."""
    return FileUploadTestContext(harness)
