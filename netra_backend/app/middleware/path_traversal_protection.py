"""Path traversal protection middleware."""
import os
import re
from typing import List

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from netra_backend.app.core.unified_logging import get_logger

logger = get_logger(__name__)

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
    path, query = _extract_path_and_query(request)
    security_check_response = _perform_all_security_checks(request, path, query)
    if security_check_response:
        return security_check_response
    return await call_next(request)

def _perform_all_security_checks(request: Request, path: str, query: str):
    """Perform all security checks and return response if blocked."""
    path_check = _check_path_traversal(request, path, query)
    extension_check = _check_blocked_extensions(request, path)
    header_check = _check_suspicious_headers(request)
    return path_check or extension_check or header_check

def _extract_path_and_query(request: Request) -> tuple[str, str]:
    """Extract path and query from request."""
    path = request.url.path
    query = str(request.url.query) if request.url.query else ""
    return path, query

def _check_path_traversal(request: Request, path: str, query: str) -> JSONResponse:
    """Check path and query for suspicious patterns."""
    if is_suspicious_path(path) or is_suspicious_path(query):
        _log_path_traversal_attempt(request, path, query)
        return _create_forbidden_response()
    return None

def _check_blocked_extensions(request: Request, path: str) -> JSONResponse:
    """Check for blocked file extensions."""
    if has_blocked_extension(path):
        _log_blocked_file_access(request, path)
        return _create_file_type_blocked_response()
    return None

def _check_suspicious_headers(request: Request) -> JSONResponse:
    """Check headers for path injection."""
    # Headers that should be excluded from path traversal checks
    excluded_headers = {
        'content-security-policy',
        'content-security-policy-report-only',
        'strict-transport-security',
        'x-content-security-policy',
        'x-webkit-csp',
        'accept',
        'accept-encoding',
        'accept-language',
        'content-type',
        'user-agent',
        'referer',
        'origin'
    }
    
    for header_name, header_value in request.headers.items():
        # Skip security policy headers and other standard headers
        if header_name.lower() in excluded_headers:
            continue
        # Only check headers that might contain file paths
        if header_name.lower() in ['x-forwarded-path', 'x-original-url', 'x-rewrite-url']:
            if is_suspicious_path(str(header_value)):
                _log_suspicious_header(request, header_name, header_value)
                return _create_bad_request_response()
    return None

def _log_path_traversal_attempt(request: Request, path: str, query: str) -> None:
    """Log path traversal attempt."""
    logger.warning(
        f"Blocked potential path traversal attempt from {request.client.host}: "
        f"Path: {path}, Query: {query}"
    )

def _log_blocked_file_access(request: Request, path: str) -> None:
    """Log blocked file access attempt."""
    logger.warning(
        f"Blocked access to restricted file type from {request.client.host}: {path}"
    )

def _log_suspicious_header(request: Request, header_name: str, header_value: str) -> None:
    """Log suspicious header attempt."""
    logger.warning(
        f"Blocked suspicious header from {request.client.host}: "
        f"{header_name}: {header_value}"
    )

def _create_forbidden_response() -> JSONResponse:
    """Create forbidden response."""
    return JSONResponse(
        status_code=403,
        content={"detail": "Forbidden"}
    )

def _create_file_type_blocked_response() -> JSONResponse:
    """Create file type blocked response."""
    return JSONResponse(
        status_code=403,
        content={"detail": "Access to this file type is not allowed"}
    )

def _create_bad_request_response() -> JSONResponse:
    """Create bad request response."""
    return JSONResponse(
        status_code=400,
        content={"detail": "Bad request"}
    )


def is_suspicious_path(path: str) -> bool:
    """Check if path contains suspicious patterns."""
    if not path:
        return False
    normalized = os.path.normpath(path)
    return (_has_suspicious_patterns(path) or
            _has_null_bytes(path) or
            _has_excessive_depth(path))

def _has_suspicious_patterns(path: str) -> bool:
    """Check for suspicious patterns in path."""
    for pattern in COMPILED_PATTERNS:
        if pattern.search(path):
            return True
    return False

def _has_null_bytes(path: str) -> bool:
    """Check for null bytes (path truncation attack)."""
    return '\x00' in path or '%00' in path

def _has_excessive_depth(path: str) -> bool:
    """Check for excessive path depth."""
    return path.count('/') > 10 or path.count('\\') > 10


def has_blocked_extension(path: str) -> bool:
    """Check if path has a blocked file extension."""
    path_lower = path.lower()
    return _check_extensions_against_path(path_lower)

def _check_extensions_against_path(path_lower: str) -> bool:
    """Check blocked extensions against lowercase path."""
    for ext in BLOCKED_EXTENSIONS:
        if _extension_matches_path(path_lower, ext):
            return True
    return False

def _extension_matches_path(path_lower: str, ext: str) -> bool:
    """Check if extension matches path (including URL encoded)."""
    if path_lower.endswith(ext):
        return True
    encoded_ext = ext.replace('.', '%2e')
    return path_lower.endswith(encoded_ext)


def sanitize_path(path: str) -> str:
    """Sanitize a path to remove dangerous elements."""
    path = _remove_null_bytes(path)
    path = _normalize_path(path)
    path = _remove_parent_references(path)
    path = _remove_leading_slashes(path)
    return path

def _remove_null_bytes(path: str) -> str:
    """Remove null bytes from path."""
    return path.replace('\x00', '').replace('%00', '')

def _normalize_path(path: str) -> str:
    """Normalize path using os.path.normpath."""
    return os.path.normpath(path)

def _remove_parent_references(path: str) -> str:
    """Remove parent directory references."""
    return path.replace('..', '')

def _remove_leading_slashes(path: str) -> str:
    """Remove leading slashes to prevent absolute paths."""
    return path.lstrip('/')