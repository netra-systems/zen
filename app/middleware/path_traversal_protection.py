"""Path traversal protection middleware."""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import os
import re
from typing import List
import logging

logger = logging.getLogger(__name__)

# Patterns that might indicate path traversal attempts
SUSPICIOUS_PATTERNS = [
    r'\.\.',  # Parent directory
    r'\.\./',  # Parent directory with slash
    r'\.\.\\',  # Parent directory with backslash
    r'\.\/',  # Current directory
    r'\.\\',  # Current directory with backslash
    r'~/',  # Home directory
    r'~\\',  # Home directory with backslash
    r'/etc/',  # Unix system files
    r'\\windows\\',  # Windows system files
    r'/proc/',  # Process information
    r'/sys/',  # System information
    r'\.env',  # Environment files
    r'\.git',  # Git files
    r'\.ssh',  # SSH files
    r'\.aws',  # AWS credentials
    r'config\.json',  # Config files
    r'secrets\.json',  # Secrets files
    r'\.htaccess',  # Apache config
    r'web\.config',  # IIS config
]

# Compile patterns for efficiency
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in SUSPICIOUS_PATTERNS]

# Blocked file extensions
BLOCKED_EXTENSIONS = {
    '.env', '.env.local', '.env.development', '.env.production',
    '.git', '.gitignore', '.gitconfig',
    '.ssh', '.pem', '.key', '.crt', '.cer',
    '.config', '.ini', '.cfg', '.conf',
    '.sql', '.db', '.sqlite',
    '.bak', '.backup', '.old', '.orig',
    '.log', '.swp', '.swo', '.tmp',
    '.pyc', '.pyo', '.pyd',
    '.class', '.jar', '.war',
    '.exe', '.dll', '.so', '.dylib',
}


async def path_traversal_protection_middleware(request: Request, call_next):
    """Protect against path traversal attacks."""
    path = request.url.path
    query = str(request.url.query) if request.url.query else ""
    
    # Check path for suspicious patterns
    if is_suspicious_path(path) or is_suspicious_path(query):
        logger.warning(
            f"Blocked potential path traversal attempt from {request.client.host}: "
            f"Path: {path}, Query: {query}"
        )
        return JSONResponse(
            status_code=403,
            content={"detail": "Forbidden"}
        )
    
    # Check for blocked file extensions
    if has_blocked_extension(path):
        logger.warning(
            f"Blocked access to restricted file type from {request.client.host}: {path}"
        )
        return JSONResponse(
            status_code=403,
            content={"detail": "Access to this file type is not allowed"}
        )
    
    # Check headers for path injection
    for header_name, header_value in request.headers.items():
        if is_suspicious_path(str(header_value)):
            logger.warning(
                f"Blocked suspicious header from {request.client.host}: "
                f"{header_name}: {header_value}"
            )
            return JSONResponse(
                status_code=400,
                content={"detail": "Bad request"}
            )
    
    response = await call_next(request)
    return response


def is_suspicious_path(path: str) -> bool:
    """Check if path contains suspicious patterns."""
    if not path:
        return False
    
    # Normalize path
    normalized = os.path.normpath(path)
    
    # Check for any compiled patterns
    for pattern in COMPILED_PATTERNS:
        if pattern.search(path):
            return True
    
    # Check for null bytes (path truncation attack)
    if '\x00' in path or '%00' in path:
        return True
    
    # Check for excessive depth (too many slashes)
    if path.count('/') > 10 or path.count('\\') > 10:
        return True
    
    return False


def has_blocked_extension(path: str) -> bool:
    """Check if path has a blocked file extension."""
    path_lower = path.lower()
    
    # Check each blocked extension
    for ext in BLOCKED_EXTENSIONS:
        if path_lower.endswith(ext):
            return True
        # Also check with URL encoding
        if path_lower.endswith(ext.replace('.', '%2e')):
            return True
    
    return False


def sanitize_path(path: str) -> str:
    """Sanitize a path to remove dangerous elements."""
    # Remove null bytes
    path = path.replace('\x00', '').replace('%00', '')
    
    # Normalize path
    path = os.path.normpath(path)
    
    # Remove any parent directory references
    path = path.replace('..', '')
    
    # Remove leading slashes to prevent absolute paths
    path = path.lstrip('/')
    
    return path