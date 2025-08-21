"""
Utility functions for the dev launcher.
"""

import logging
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def check_emoji_support() -> bool:
    """
    Check if the terminal supports emoji output.
    
    Returns:
        True if emoji is supported
    """
    try:
        # Set UTF-8 for better compatibility
        if sys.platform == "win32":
            # Try to set UTF-8 mode
            try:
                import locale
                locale.setlocale(locale.LC_ALL, '')
                if hasattr(sys.stdout, 'reconfigure'):
                    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                if hasattr(sys.stderr, 'reconfigure'):
                    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        
        # Try to encode an emoji
        "✅".encode(sys.stdout.encoding or 'utf-8')
        
        # Check if we're on Windows terminal that supports emojis
        if sys.platform == "win32":
            # Windows Terminal and VS Code terminal support emojis
            # But for safety, disable by default on Windows unless in known good terminals
            return bool(os.environ.get('WT_SESSION') or os.environ.get('TERM_PROGRAM') == 'vscode')
        
        return True
    except (UnicodeEncodeError, AttributeError):
        return False


def print_with_emoji(emoji: str, text: str, message: str, use_emoji: bool = None):
    """
    Print with emoji if supported, otherwise with text prefix.
    
    Args:
        emoji: Emoji to display
        text: Text prefix if emoji not supported
        message: Message to print
        use_emoji: Override emoji support detection
    """
    if use_emoji is None:
        use_emoji = check_emoji_support()
    
    if use_emoji:
        try:
            print(f"{emoji} {message}")
            return
        except UnicodeEncodeError:
            pass
    
    print(f"[{text}] {message}")


def get_free_port() -> int:
    """
    Get a free port by binding to port 0.
    
    Returns:
        Available port number
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def is_port_available(port: int) -> bool:
    """
    Check if a specific port is available.
    
    Args:
        port: Port number to check
    
    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            result = s.connect_ex(('localhost', port))
            return result != 0
    except Exception:
        return False


def find_available_port(preferred_port: int, port_range: tuple = (8081, 8090)) -> int:
    """
    Find an available port, preferring the specified port.
    
    Args:
        preferred_port: Preferred port to try first
        port_range: Range of ports to try (min, max)
    
    Returns:
        Available port number
    """
    # Try preferred port first
    if is_port_available(preferred_port):
        return preferred_port
    
    # Try ports in the specified range
    for port in range(port_range[0], port_range[1] + 1):
        if port != preferred_port and is_port_available(port):
            logger.info(f"Port {preferred_port} unavailable, using {port} instead")
            return port
    
    # If all ports in range are taken, get a random free port
    free_port = get_free_port()
    logger.warning(f"All ports in range {port_range} taken, using {free_port}")
    return free_port


def wait_for_service(url: str, timeout: int = 30, check_interval: int = 2) -> bool:
    """
    Wait for a service to become available.
    
    Args:
        url: URL to check
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
    
    Returns:
        True if service became available
    """
    success, _ = wait_for_service_with_details(url, timeout, check_interval)
    return success


def wait_for_service_with_details(url: str, timeout: int = 30, check_interval: int = 2) -> Tuple[bool, Optional[str]]:
    """
    Wait for a service to become available with detailed error info.
    
    Args:
        url: URL to check
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
    
    Returns:
        Tuple of (success, error_details)
    """
    start_time = time.time()
    attempt = 0
    last_error = None
    
    while time.time() - start_time < timeout:
        attempt += 1
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    logger.info(f"Service ready at {url} after {attempt} attempts")
                    return True, None
                else:
                    last_error = f"Status {response.status}"
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            last_error = f"Connection error: {e.reason}"
        except (ConnectionError, TimeoutError, OSError) as e:
            last_error = f"Network error: {str(e)}"
        
        if attempt == 1:
            logger.debug(f"Waiting for service at {url}...")
        elif attempt % 10 == 0:
            logger.debug(f"Still waiting for {url}... ({attempt} attempts)")
        time.sleep(check_interval)
    
    elapsed = time.time() - start_time
    return False, f"{last_error} after {elapsed:.1f}s"


def open_browser(url: str, delay: float = 1.0) -> bool:
    """
    Open the browser with the given URL.
    
    Args:
        url: URL to open
        delay: Delay before opening in seconds
    
    Returns:
        True if browser was opened successfully
    """
    try:
        # Add a small delay to ensure the page is ready
        time.sleep(delay)
        
        # Open the default browser
        webbrowser.open(url)
        logger.info(f"Opening browser at {url}")
        return True
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")
        return False


def check_dependencies() -> Dict[str, bool]:
    """
    Check if all required dependencies are available.
    
    Returns:
        Dictionary mapping dependency names to availability status
    """
    dependencies = {}
    
    # Check Python packages
    try:
        import uvicorn
        dependencies['uvicorn'] = True
    except ImportError:
        dependencies['uvicorn'] = False
        logger.error("uvicorn not installed. Run: pip install uvicorn")
    
    try:
        import fastapi
        dependencies['fastapi'] = True
    except ImportError:
        dependencies['fastapi'] = False
        logger.error("FastAPI not installed. Run: pip install fastapi")
    
    try:
        from google.cloud import secretmanager
        dependencies['google-cloud-secret-manager'] = True
    except ImportError:
        dependencies['google-cloud-secret-manager'] = False
        logger.debug("Google Cloud Secret Manager SDK not installed (optional)")
    
    # Check Node.js and npm
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        dependencies['node'] = result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        dependencies['node'] = False
        logger.error("Node.js not found. Please install Node.js")
    
    try:
        if sys.platform == "win32":
            npm_cmd = ["npm.cmd", "--version"]
        else:
            npm_cmd = ["npm", "--version"]
        
        result = subprocess.run(
            npm_cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        dependencies['npm'] = result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        dependencies['npm'] = False
        logger.error("npm not found. Please install npm")
    
    return dependencies


def check_project_structure(project_root: Path) -> Dict[str, bool]:
    """
    Check if the project structure is valid.
    
    Args:
        project_root: Root directory of the project
    
    Returns:
        Dictionary mapping structure elements to existence status
    """
    structure = {}
    
    # Check backend
    backend_dir = project_root / "netra_backend" / "app"
    structure['backend'] = backend_dir.exists()
    if not structure['backend']:
        logger.error(f"Backend directory not found: {backend_dir}")
    
    # Check frontend
    frontend_dir = project_root / "frontend"
    structure['frontend'] = frontend_dir.exists()
    if not structure['frontend']:
        logger.error(f"Frontend directory not found: {frontend_dir}")
    
    # Check frontend dependencies
    node_modules = frontend_dir / "node_modules"
    structure['frontend_deps'] = node_modules.exists()
    if structure['frontend'] and not structure['frontend_deps']:
        logger.error(f"Frontend dependencies not installed. Run: cd {frontend_dir} && npm install")
    
    # Check for key files
    requirements_file = project_root / "requirements.txt"
    structure['requirements'] = requirements_file.exists()
    
    package_json = frontend_dir / "package.json"
    structure['package_json'] = package_json.exists()
    
    return structure


def create_process_env(base_env: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, str]:
    """
    Create environment variables for a subprocess.
    
    Args:
        base_env: Base environment to start with (defaults to os.environ)
        **kwargs: Additional environment variables to add
    
    Returns:
        Complete environment dictionary
    """
    if base_env is None:
        env = os.environ.copy()
    else:
        env = base_env.copy()
    
    # Add/override with provided kwargs
    for key, value in kwargs.items():
        if value is not None:
            env[key] = str(value)
    
    return env


def create_subprocess(
    cmd: list,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT
) -> subprocess.Popen:
    """
    Create a subprocess with platform-appropriate settings.
    
    Args:
        cmd: Command to execute
        cwd: Working directory
        env: Environment variables
        stdout: stdout configuration
        stderr: stderr configuration
    
    Returns:
        The created subprocess
    """
    kwargs = {
        'stdout': stdout,
        'stderr': stderr,
        'bufsize': 1,
        'universal_newlines': False
    }
    
    if cwd:
        kwargs['cwd'] = str(cwd)
    
    if env:
        kwargs['env'] = env
    
    if sys.platform == "win32":
        # Windows: create new process group
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    elif sys.platform == "darwin":
        # Mac: don't use setsid as it can cause issues
        pass
    else:
        # Linux: create new process group
        kwargs['preexec_fn'] = os.setsid
    
    return subprocess.Popen(cmd, **kwargs)


def terminate_process(process: subprocess.Popen):
    """
    Terminate a process cross-platform.
    
    Args:
        process: Process to terminate
    """
    if process.poll() is None:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True
            )
        elif sys.platform == "darwin":
            # Mac: use kill instead of killpg
            try:
                os.kill(process.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
        else:
            # Linux: use killpg
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass