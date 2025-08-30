"""
File utilities for basic file operations.

This module provides a simplified interface for common file operations,
maintaining compatibility with test interfaces while leveraging standard
library functionality for file handling.
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional


class FileUtils:
    """Utility class for basic file operations."""
    
    def __init__(self):
        """Initialize file utils."""
        pass
    
    async def write_file(self, file_path: str, content: str) -> None:
        """Write content to a file."""
        def _write():
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        await asyncio.get_event_loop().run_in_executor(None, _write)
    
    async def write_file_safe(self, file_path: str, content: str) -> None:
        """Write content to a file safely with cleanup on error."""
        try:
            await self.write_file(file_path, content)
        except Exception:
            # Clean up file if it exists
            if os.path.exists(file_path):
                os.unlink(file_path)
            raise
    
    async def write_file_atomic(self, file_path: str, content: str) -> None:
        """Write content to a file atomically using temp file."""
        def _write_atomic():
            temp_path = f"{file_path}.tmp"
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                # Atomic move
                shutil.move(temp_path, file_path)
            except Exception:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        
        await asyncio.get_event_loop().run_in_executor(None, _write_atomic)
    
    async def read_file(self, file_path: str) -> str:
        """Read content from a file."""
        def _read():
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        return await asyncio.get_event_loop().run_in_executor(None, _read)
    
    async def copy_file(self, source_path: str, dest_path: str) -> None:
        """Copy a file from source to destination."""
        def _copy():
            shutil.copy2(source_path, dest_path)
        
        await asyncio.get_event_loop().run_in_executor(None, _copy)
    
    async def move_file(self, source_path: str, dest_path: str) -> None:
        """Move a file from source to destination."""
        def _move():
            shutil.move(source_path, dest_path)
        
        await asyncio.get_event_loop().run_in_executor(None, _move)
    
    async def delete_file(self, file_path: str) -> None:
        """Delete a file."""
        def _delete():
            if os.path.exists(file_path):
                os.unlink(file_path)
        
        await asyncio.get_event_loop().run_in_executor(None, _delete)
    
    def process(self) -> str:
        """Core processing method for basic testing."""
        return "processed"
    
    def process_invalid(self):
        """Method that raises exception for error testing."""
        raise ValueError("Invalid processing request")