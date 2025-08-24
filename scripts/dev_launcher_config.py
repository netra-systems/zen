#!/usr/bin/env python3
"""
Configuration and path resolution utilities for dev launcher.
Provides robust path handling and project configuration management.
"""

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Find the project root directory robustly."""
    current_file = Path(__file__).resolve()
    
    # Check if we're in scripts directory
    if current_file.parent.name == 'scripts':
        return current_file.parent.parent
    
    return _find_project_root_by_markers(current_file)


def _find_project_root_by_markers(current_file: Path) -> Path:
    """Find project root by looking for key markers."""
    # Check if we're already in project root
    parent_dir = current_file.parent
    if _has_project_markers(parent_dir):
        return parent_dir
    
    # Try to find project root by looking for key files/dirs
    for parent in current_file.parents:
        if _has_project_markers(parent):
            return parent
    
    # Fallback to parent of parent
    return current_file.parent.parent


def _has_project_markers(path: Path) -> bool:
    """Check if path contains project markers."""
    markers = ['frontend', 'app', 'requirements.txt']
    return any((path / marker).exists() for marker in markers)


def resolve_path(*parts: str, required: bool = False, 
                search_dirs: Optional[List[Path]] = None) -> Path:
    """Resolve a path robustly, checking multiple locations."""
    if search_dirs is None:
        search_dirs = _get_default_search_dirs()
    
    # Try each search directory
    for base_dir in search_dirs:
        path = base_dir / Path(*parts)
        if path.exists():
            return path.resolve()
    
    return _handle_path_not_found(parts, required, search_dirs)


def _get_default_search_dirs() -> List[Path]:
    """Get default search directories for path resolution."""
    project_root = get_project_root()
    return [
        Path.cwd(),  # Current working directory
        project_root,  # Project root
        Path(__file__).parent,  # Script directory
        Path(__file__).parent.parent,  # Parent of script directory
    ]


def _handle_path_not_found(parts: tuple, required: bool, 
                          search_dirs: List[Path]) -> Path:
    """Handle case when path is not found."""
    if required:
        searched = ', '.join(str(d) for d in search_dirs)
        path_str = '/'.join(parts)
        raise FileNotFoundError(f"Could not find {path_str} in any of: {searched}")
    
    # Return the path relative to project root as fallback
    project_root = get_project_root()
    return project_root / Path(*parts)


def check_emoji_support() -> bool:
    """Check if the terminal supports emoji output."""
    try:
        # Try to encode an emoji
        "[OK]".encode(sys.stdout.encoding or 'utf-8')
        return _check_platform_emoji_support()
    except (UnicodeEncodeError, AttributeError):
        return False


def _check_platform_emoji_support() -> bool:
    """Check platform-specific emoji support."""
    # Check if we're on Windows terminal that supports emojis
    if sys.platform == "win32":
        wt_session = os.environ.get('WT_SESSION')
        term_program = os.environ.get('TERM_PROGRAM')
        return bool(wt_session or term_program == 'vscode')
    return True


def setup_project_path() -> None:
    """Add project root to Python path."""


def print_with_emoji_fallback(emoji: str, text: str, 
                             message: str, use_emoji: bool) -> None:
    """Print with emoji if supported, otherwise with text prefix."""
    if use_emoji:
        try:
            print(f"{emoji} {message}")
            return
        except UnicodeEncodeError:
            pass
    print(f"[{text}] {message}")


def get_free_port() -> int:
    """Get a free port by binding to port 0."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def setup_environment_variables(port: int) -> dict:
    """Setup environment variables for backend process."""
    env = os.environ.copy()
    env["BACKEND_PORT"] = str(port)
    
    # Add project root to PYTHONPATH
    project_root = get_project_root()
    python_path = env.get("PYTHONPATH", "")
    if python_path:
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{python_path}"
    else:
        env["PYTHONPATH"] = str(project_root)
    
    return env


def setup_frontend_environment(backend_info: dict, port: int, 
                              reload_enabled: bool) -> dict:
    """Setup environment variables for frontend process."""
    env = os.environ.copy()
    env["NEXT_PUBLIC_API_URL"] = backend_info["api_url"]
    env["NEXT_PUBLIC_WS_URL"] = backend_info["ws_url"]
    env["PORT"] = str(port)
    
    # Add project root to PYTHONPATH
    project_root = get_project_root()
    python_path = env.get("PYTHONPATH", "")
    if python_path:
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{python_path}"
    else:
        env["PYTHONPATH"] = str(project_root)
    
    # Configure hot reload
    if not reload_enabled:
        env["WATCHPACK_POLLING"] = "false"
        env["NEXT_DISABLE_FAST_REFRESH"] = "true"
    
    return env


def validate_dependencies() -> List[str]:
    """Check if all required dependencies are available."""
    errors = []
    
    # Check Python dependencies
    try:
        import uvicorn
    except ImportError:
        errors.append("❌ uvicorn not installed. Run: pip install uvicorn")
    
    try:
        import fastapi
    except ImportError:
        errors.append("❌ FastAPI not installed. Run: pip install fastapi")
    
    return errors


def validate_frontend_directory() -> List[str]:
    """Validate frontend directory and dependencies."""
    errors = []
    project_root = get_project_root()
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        errors.append("❌ Frontend directory not found")
        return errors
    
    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        error_msg = f"❌ Frontend dependencies not installed. Run: cd {frontend_dir} && npm install"
        errors.append(error_msg)
    
    return errors


def import_service_discovery():
    """Import ServiceDiscovery with multiple strategies."""
    try:
        from scripts.service_discovery import ServiceDiscovery
        return ServiceDiscovery
    except ImportError:
        return _try_alternative_imports()


def _try_alternative_imports():
    """Try alternative import strategies for ServiceDiscovery."""
    try:
        # If running from scripts directory, try direct import
        from service_discovery import ServiceDiscovery
        return ServiceDiscovery
    except ImportError:
        return _try_last_resort_import()


def _try_last_resort_import():
    """Last resort import strategy for ServiceDiscovery."""
    project_root = get_project_root()
    scripts_dir = project_root / 'scripts'
    
    if scripts_dir.exists():
        from service_discovery import ServiceDiscovery
        return ServiceDiscovery
    else:
        logger.error("Could not import ServiceDiscovery. Please check your installation.")
        sys.exit(1)