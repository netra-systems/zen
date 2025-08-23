"""Mock implementation of aiofiles for testing without external dependencies

This provides a minimal mock implementation of aiofiles to avoid dependency issues
while maintaining compatibility with existing test code.
"""

import asyncio
from pathlib import Path
from typing import Any, AsyncIterator, Optional, Union


class AsyncFileContextManager:
    """Async file context manager mock"""
    
    def __init__(self, file_path: Union[str, Path], mode: str = "r", encoding: Optional[str] = None):
        self.file_path = Path(file_path)
        self.mode = mode
        self.encoding = encoding or "utf-8"
        self._file = None
        
    async def __aenter__(self):
        # Use sync file operations wrapped in async
        try:
            self._file = open(self.file_path, self.mode, encoding=self.encoding)
        except Exception:
            # If file doesn't exist and we're reading, create a mock
            if 'r' in self.mode:
                self._file = None  # Signal no file
            else:
                # For write modes, ensure parent dir exists
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                self._file = open(self.file_path, self.mode, encoding=self.encoding)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            self._file.close()
            
    async def read(self, size: int = -1) -> str:
        """Read file content"""
        if self._file is None:
            return ""  # Mock empty file
        await asyncio.sleep(0)  # Make it actually async
        return self._file.read(size)
        
    async def write(self, data: str) -> int:
        """Write data to file"""
        if self._file is None:
            return len(data)  # Mock successful write
        await asyncio.sleep(0)  # Make it actually async
        return self._file.write(data)
        
    async def readline(self) -> str:
        """Read a single line"""
        if self._file is None:
            return ""  # Mock empty file
        await asyncio.sleep(0)
        return self._file.readline()
        
    async def readlines(self) -> list:
        """Read all lines"""
        if self._file is None:
            return []  # Mock empty file
        await asyncio.sleep(0)
        return self._file.readlines()
        
    async def __aiter__(self) -> AsyncIterator[str]:
        """Async iterator over lines"""
        if self._file is None:
            return  # Empty file
        for line in self._file:
            yield line


def open(file_path: Union[str, Path], mode: str = "r", **kwargs) -> AsyncFileContextManager:
    """Mock aiofiles.open function"""
    return AsyncFileContextManager(file_path, mode, **kwargs)


# Provide commonly used aiofiles functions
async def exists(path: Union[str, Path]) -> bool:
    """Check if file exists"""
    await asyncio.sleep(0)  # Make it async
    return Path(path).exists()


async def remove(path: Union[str, Path]) -> None:
    """Remove file"""
    await asyncio.sleep(0)  # Make it async
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass  # Already removed


async def mkdir(path: Union[str, Path], parents: bool = False, exist_ok: bool = False) -> None:
    """Create directory"""
    await asyncio.sleep(0)  # Make it async
    Path(path).mkdir(parents=parents, exist_ok=exist_ok)


# Mock for aiofiles.os module
class MockAioFilesOS:
    @staticmethod
    async def path_exists(path: Union[str, Path]) -> bool:
        await asyncio.sleep(0)
        return Path(path).exists()
    
    @staticmethod
    async def remove(path: Union[str, Path]) -> None:
        await asyncio.sleep(0)
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass


# Create the os mock module
os = MockAioFilesOS()