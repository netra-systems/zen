"""
FileStorageService - File upload and storage management for corpus creation

This service handles file uploads, storage, retrieval, and deletion for document
management within corpus creation workflows. It provides production-ready file
handling with proper error handling, validation, and metadata management.

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise (corpus creation features)
- Business Goal: Content Management, AI Training Data, User Productivity
- Value Impact: Enables corpus creation and AI model training workflows
- Strategic Impact: Core content foundation for AI optimization capabilities
"""

import hashlib
import mimetypes
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional

from netra_backend.app.core.exceptions_service import ServiceError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.base import ServiceMixin

logger = central_logger.get_logger(__name__)


class FileStorageService(ServiceMixin):
    """Production-ready file storage service for corpus creation and document management."""
    
    def __init__(self, storage_root: Optional[str] = None):
        """Initialize the file storage service.
        
        Args:
            storage_root: Root directory for file storage. If None, uses default temp directory.
        """
        super().__init__("file_storage_service")
        
        # Set up storage root directory
        if storage_root is None:
            storage_root = os.path.join(os.path.expanduser("~"), ".netra", "file_storage")
        
        self.storage_root = Path(storage_root)
        self._file_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Initialize storage directory
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self) -> None:
        """Ensure the storage directory exists and is writable."""
        try:
            self.storage_root.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = self.storage_root / f".test_{uuid.uuid4().hex}"
            test_file.write_text("test")
            test_file.unlink()
            
            logger.info(f"File storage initialized at: {self.storage_root}")
        except Exception as e:
            logger.error(f"Failed to initialize storage directory: {e}")
            raise ServiceError(
                service_name=self.service_name,
                message=f"Failed to initialize storage directory: {e}",
                context={"storage_root": str(self.storage_root)}
            )
    
    def _generate_file_id(self) -> str:
        """Generate a unique file ID."""
        return str(uuid.uuid4())
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal attacks."""
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        # Remove path separators and dangerous characters
        dangerous_chars = ['/', '\\', '..', '~', '$', '&', '|', ';', ':', '<', '>', '?', '*', '"', "'"]
        sanitized = filename
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip('. ')
        
        # Ensure filename is not empty after sanitization
        if not sanitized:
            sanitized = "unnamed_file"
        
        # Limit filename length
        if len(sanitized) > 200:  # Leave room for file_id prefix
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:190] + ext
        
        return sanitized
    
    def _get_file_path(self, file_id: str, filename: str, user_id: Optional[str] = None) -> Path:
        """Get the storage path for a file with user isolation and path traversal protection."""
        # Sanitize filename to prevent path traversal
        sanitized_filename = self._sanitize_filename(filename)
        
        # Create user-specific directory for isolation
        user_dir = f"user_{user_id}" if user_id else "system"
        
        # Create subdirectory based on first 2 characters of file_id for better organization
        subdir = file_id[:2]
        storage_dir = self.storage_root / user_dir / subdir
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Use file_id as prefix to avoid filename conflicts
        safe_filename = f"{file_id}_{sanitized_filename}"
        return storage_dir / safe_filename
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _validate_file_upload_params(
        self, 
        file_stream: BinaryIO, 
        filename: str, 
        content_type: str,
        user_id: Optional[str] = None
    ) -> None:
        """Validate file upload parameters with security checks."""
        if not filename:
            raise ValueError("Filename cannot be empty")
        
        if not filename.strip():
            raise ValueError("Filename cannot be only whitespace")
        
        if len(filename) > 255:
            raise ValueError("Filename too long (max 255 characters)")
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            raise ValueError("Filename contains invalid path characters")
        
        # Check for null bytes
        if '\0' in filename:
            raise ValueError("Filename contains null bytes")
        
        # Validate user_id if provided
        if user_id is not None:
            if not user_id.isalnum():
                raise ValueError("User ID must be alphanumeric")
            if len(user_id) > 50:
                raise ValueError("User ID too long")
        
        # Check for dangerous file extensions (basic security)
        dangerous_extensions = {'.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.php', '.sh'}
        file_extension = Path(filename).suffix.lower()
        if file_extension in dangerous_extensions:
            raise ValueError(f"File type not allowed: {file_extension}")
        
        # Validate content type
        if not content_type:
            # Try to guess content type from filename
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = "application/octet-stream"
        
        logger.debug(f"Validated upload params: filename={filename}, content_type={content_type}, user_id={user_id}")
    
    async def upload_file(
        self,
        file_stream: BinaryIO,
        filename: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a file and return storage information with user isolation.
        
        Args:
            file_stream: Binary file stream to upload
            filename: Original filename
            content_type: MIME content type
            metadata: Optional metadata dictionary
            user_id: Optional user ID for isolation
            
        Returns:
            Dictionary containing file_id, storage_path, file_size, and metadata
        """
        try:
            # Validate parameters
            self._validate_file_upload_params(file_stream, filename, content_type, user_id)
            
            # Generate unique file ID
            file_id = self._generate_file_id()
            
            # Get storage path with user isolation
            storage_path = self._get_file_path(file_id, filename, user_id)
            
            # Write file to storage
            file_size = 0
            with open(storage_path, 'wb') as f:
                while chunk := file_stream.read(8192):
                    f.write(chunk)
                    file_size += len(chunk)
            
            # Calculate checksum
            checksum = self._calculate_checksum(storage_path)
            
            # Store metadata
            upload_metadata = {
                "file_id": file_id,
                "filename": filename,
                "original_filename": filename,
                "sanitized_filename": self._sanitize_filename(filename),
                "content_type": content_type,
                "file_size": file_size,
                "storage_path": str(storage_path),
                "checksum": checksum,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "metadata": metadata or {}
            }
            
            self._file_metadata[file_id] = upload_metadata
            
            logger.info(f"File uploaded successfully: {filename} -> {file_id}")
            
            return {
                "file_id": file_id,
                "storage_path": str(storage_path),
                "file_size": file_size,
                "checksum": checksum,
                "metadata": upload_metadata
            }
            
        except Exception as e:
            logger.error(f"File upload failed for {filename}: {e}")
            raise ServiceError(
                service_name=self.service_name,
                message=f"File upload failed: {e}",
                context={"filename": filename, "content_type": content_type}
            )
    
    async def upload_large_file(
        self,
        file_stream: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int,
        chunk_size: int = 1024 * 1024,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a large file with progress tracking and validation with user isolation.
        
        Args:
            file_stream: Binary file stream to upload
            filename: Original filename
            content_type: MIME content type
            file_size: Expected file size in bytes
            chunk_size: Chunk size for reading (default 1MB)
            metadata: Optional metadata dictionary
            user_id: Optional user ID for isolation
            
        Returns:
            Dictionary containing file_id, storage_path, file_size, and metadata
        """
        try:
            # Validate parameters
            self._validate_file_upload_params(file_stream, filename, content_type, user_id)
            
            if file_size <= 0:
                raise ValueError("File size must be positive")
            
            if chunk_size <= 0:
                raise ValueError("Chunk size must be positive")
            
            # Check available disk space (rough check)
            storage_stat = shutil.disk_usage(self.storage_root)
            if storage_stat.free < file_size * 1.1:  # 10% buffer
                raise ServiceError(
                    service_name=self.service_name,
                    message="Insufficient disk space for large file upload",
                    context={"required_bytes": file_size, "available_bytes": storage_stat.free}
                )
            
            # Generate unique file ID
            file_id = self._generate_file_id()
            
            # Get storage path with user isolation
            storage_path = self._get_file_path(file_id, filename, user_id)
            
            # Write file with progress tracking
            written_bytes = 0
            hasher = hashlib.sha256()
            
            with open(storage_path, 'wb') as f:
                while written_bytes < file_size:
                    remaining = min(chunk_size, file_size - written_bytes)
                    chunk = file_stream.read(remaining)
                    
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    hasher.update(chunk)
                    written_bytes += len(chunk)
            
            # Verify file size matches expected
            if written_bytes != file_size:
                # Clean up partial file
                storage_path.unlink(missing_ok=True)
                raise ServiceError(
                    service_name=self.service_name,
                    message=f"File size mismatch: expected {file_size}, got {written_bytes}",
                    context={"filename": filename, "expected_size": file_size, "actual_size": written_bytes}
                )
            
            checksum = hasher.hexdigest()
            
            # Validate expected checksum if provided
            if metadata and "expected_checksum" in metadata:
                expected_checksum = metadata["expected_checksum"]
                if checksum != expected_checksum:
                    # Clean up file with wrong checksum
                    storage_path.unlink(missing_ok=True)
                    raise ServiceError(
                        service_name=self.service_name,
                        message="File integrity check failed: checksum mismatch",
                        context={
                            "filename": filename,
                            "expected_checksum": expected_checksum,
                            "actual_checksum": checksum
                        }
                    )
            
            # Store metadata
            upload_metadata = {
                "file_id": file_id,
                "filename": filename,
                "original_filename": filename,
                "sanitized_filename": self._sanitize_filename(filename),
                "content_type": content_type,
                "file_size": written_bytes,
                "storage_path": str(storage_path),
                "checksum": checksum,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "upload_type": "large_file",
                "chunk_size": chunk_size,
                "user_id": user_id,
                "metadata": metadata or {}
            }
            
            self._file_metadata[file_id] = upload_metadata
            
            logger.info(f"Large file uploaded successfully: {filename} -> {file_id} ({written_bytes} bytes)")
            
            return {
                "file_id": file_id,
                "storage_path": str(storage_path),
                "file_size": written_bytes,
                "checksum": checksum,
                "metadata": upload_metadata
            }
            
        except Exception as e:
            logger.error(f"Large file upload failed for {filename}: {e}")
            raise ServiceError(
                service_name=self.service_name,
                message=f"Large file upload failed: {e}",
                context={"filename": filename, "content_type": content_type, "file_size": file_size}
            )
    
    def _validate_file_access(self, file_metadata: Dict[str, Any], requesting_user_id: Optional[str]) -> bool:
        """Validate if user has access to the file."""
        file_user_id = file_metadata.get("user_id")
        
        # System files (no user_id) can be accessed by anyone
        if file_user_id is None:
            return True
            
        # User can only access their own files
        return file_user_id == requesting_user_id
    
    async def get_file_metadata(self, file_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get metadata for a stored file with access control.
        
        Args:
            file_id: Unique file identifier
            user_id: User ID for access control
            
        Returns:
            File metadata dictionary or None if not found/unauthorized
        """
        metadata = self._file_metadata.get(file_id)
        if metadata and self._validate_file_access(metadata, user_id):
            return metadata
        return None
    
    async def delete_file(self, file_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete a stored file with access control.
        
        Args:
            file_id: Unique file identifier
            user_id: User ID for access control
            
        Returns:
            Dictionary with deletion status and details
        """
        try:
            metadata = self._file_metadata.get(file_id)
            if not metadata:
                return {
                    "status": "not_found",
                    "file_id": file_id,
                    "message": "File not found"
                }
            
            # Validate access permissions
            if not self._validate_file_access(metadata, user_id):
                return {
                    "status": "unauthorized",
                    "file_id": file_id,
                    "message": "Access denied"
                }
            
            storage_path = Path(metadata["storage_path"])
            
            # Delete physical file
            if storage_path.exists():
                storage_path.unlink()
                logger.info(f"Deleted file: {storage_path}")
            
            # Remove metadata
            del self._file_metadata[file_id]
            
            return {
                "status": "success",
                "file_id": file_id,
                "deleted_path": str(storage_path),
                "message": "File deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"File deletion failed for {file_id}: {e}")
            return {
                "status": "error",
                "file_id": file_id,
                "error": str(e),
                "message": "File deletion failed"
            }
    
    async def delete_files_batch(self, file_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple files in batch.
        
        Args:
            file_ids: List of file identifiers to delete
            
        Returns:
            Dictionary with batch deletion results
        """
        deleted_count = 0
        failed_count = 0
        errors = []
        
        for file_id in file_ids:
            try:
                result = await self.delete_file(file_id)
                if result["status"] == "success":
                    deleted_count += 1
                else:
                    failed_count += 1
                    errors.append(f"{file_id}: {result.get('message', 'Unknown error')}")
            except Exception as e:
                failed_count += 1
                errors.append(f"{file_id}: {str(e)}")
        
        return {
            "status": "completed",
            "total_requested": len(file_ids),
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "errors": errors[:10]  # Limit error list to avoid large responses
        }
    
    async def cleanup_orphaned_files(self) -> Dict[str, Any]:
        """Clean up orphaned files that have no metadata entries.
        
        Returns:
            Dictionary with cleanup results
        """
        try:
            orphaned_count = 0
            cleaned_size = 0
            errors = []
            
            # Get all files in storage
            for storage_path in self.storage_root.rglob("*"):
                if not storage_path.is_file():
                    continue
                
                # Skip test files and hidden files
                if storage_path.name.startswith('.'):
                    continue
                
                # Check if file has corresponding metadata
                file_found_in_metadata = False
                for metadata in self._file_metadata.values():
                    if Path(metadata["storage_path"]) == storage_path:
                        file_found_in_metadata = True
                        break
                
                if not file_found_in_metadata:
                    try:
                        file_size = storage_path.stat().st_size
                        storage_path.unlink()
                        orphaned_count += 1
                        cleaned_size += file_size
                        logger.info(f"Cleaned orphaned file: {storage_path}")
                    except Exception as e:
                        errors.append(f"{storage_path}: {str(e)}")
            
            return {
                "status": "success",
                "orphaned_files_cleaned": orphaned_count,
                "cleaned_bytes": cleaned_size,
                "errors": errors[:5]  # Limit error list
            }
            
        except Exception as e:
            logger.error(f"Orphaned file cleanup failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Orphaned file cleanup failed"
            }
