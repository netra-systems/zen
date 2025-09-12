"""
Utility functions for the dev launcher.
"""

import logging
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from shared.isolated_environment import get_env

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
        " PASS: ".encode(sys.stdout.encoding or 'utf-8')
        
        # Check if we're on Windows terminal that supports emojis
        if sys.platform == "win32":
            # Windows Terminal and VS Code terminal support emojis
            # But for safety, disable by default on Windows unless in known good terminals
            env = get_env()
            return bool(env.get('WT_SESSION') or env.get('TERM_PROGRAM') == 'vscode')
        
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


def is_port_available(port: int, host: str = '0.0.0.0', allow_reuse: bool = False) -> bool:
    """
    Check if a specific port is available on the specified host interface.
    
    Args:
        port: Port number to check
        host: Host interface to check (defaults to '0.0.0.0' for all interfaces)
        allow_reuse: Whether to use SO_REUSEADDR (should match target application behavior)
    
    Returns:
        True if port is available, False otherwise
    """
    try:
        # Use bind attempt instead of connect to properly detect TIME_WAIT connections
        # Check the same interface that will actually be used to prevent race conditions
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Only set SO_REUSEADDR if specifically requested
            # This matches uvicorn's default behavior (no SO_REUSEADDR initially)
            if allow_reuse:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        # Port is already in use or blocked (including TIME_WAIT)
        return False
    except Exception:
        return False


def find_available_port(preferred_port: int, port_range: tuple = (8081, 8090), host: str = '0.0.0.0') -> int:
    """
    Find an available port, preferring the specified port with enhanced fallback mechanisms.
    
    Args:
        preferred_port: Preferred port to try first
        port_range: Range of ports to try (min, max)
        host: Host interface to check (defaults to '0.0.0.0' for all interfaces)
    
    Returns:
        Available port number
    """
    # Log port allocation attempt for debugging
    logger.debug(f"Finding available port: preferred={preferred_port}, range={port_range}, host={host}")
    
    # Try preferred port first with race condition protection
    if _is_port_available_with_retry(preferred_port, host):
        logger.info(f"Using preferred port {preferred_port}")
        # Add small delay on Windows to prevent race condition
        if sys.platform == "win32":
            time.sleep(0.01)
        return preferred_port
    else:
        # Log why preferred port failed
        process_info = _get_process_using_port(preferred_port)
        if process_info:
            logger.info(f"Port {preferred_port} unavailable (used by: {process_info})")
        else:
            logger.info(f"Port {preferred_port} unavailable")
    
    # Try ports in the specified range with improved fallback
    available_ports = []
    for port in range(port_range[0], port_range[1] + 1):
        if port != preferred_port and _is_port_available_with_retry(port, host):
            available_ports.append(port)
    
    # Use first available port in range
    if available_ports:
        selected_port = available_ports[0]
        logger.info(f"Port {preferred_port} unavailable, using {selected_port} instead")
        # Add small delay on Windows to prevent race condition
        if sys.platform == "win32":
            time.sleep(0.01)
        return selected_port
    
    # Extended fallback: try wider range for frontend (3000-3999), auth (8000-8999), etc.
    extended_range = _get_extended_port_range(preferred_port, port_range)
    if extended_range != port_range:
        logger.info(f"Trying extended port range {extended_range}")
        for port in range(extended_range[0], extended_range[1] + 1):
            if port not in range(port_range[0], port_range[1] + 1) and _is_port_available_with_retry(port, host):
                logger.warning(f"Using extended range port {port}")
                if sys.platform == "win32":
                    time.sleep(0.01)
                return port
    
    # Final fallback: get a random free port from OS
    try:
        free_port = get_free_port()
        logger.warning(f"All ports in range {port_range} and extended range taken, using OS-allocated port {free_port}")
        return free_port
    except Exception as e:
        logger.error(f"Failed to get free port from OS: {e}")
        # Ultimate fallback: try high numbered ports
        for port in range(50000, 60000):
            if _is_port_available_with_retry(port, host):
                logger.error(f"Emergency fallback to high-numbered port {port}")
                return port
        
        # This should almost never happen
        raise RuntimeError(f"Unable to find any available port after extensive search")


def _is_port_available_with_retry(port: int, host: str, max_retries: int = 3) -> bool:
    """
    Check port availability with retry mechanism for race conditions.
    
    Args:
        port: Port number to check
        host: Host interface to check
        max_retries: Maximum number of retries
        
    Returns:
        True if port is available, False otherwise
    """
    for attempt in range(max_retries):
        if is_port_available(port, host):
            # Double-check with small delay to catch race conditions
            if sys.platform == "win32":
                time.sleep(0.02)
                # Re-verify on Windows due to timing issues
                return is_port_available(port, host)
            return True
        
        if attempt < max_retries - 1:
            # Small delay between retries
            time.sleep(0.05 * (attempt + 1))
    
    return False


def _get_extended_port_range(preferred_port: int, original_range: tuple) -> tuple:
    """
    Get extended port range based on service type.
    
    Args:
        preferred_port: Original preferred port
        original_range: Original port range
        
    Returns:
        Extended port range tuple
    """
    # Frontend ports (3000-3999)
    if 3000 <= preferred_port <= 3999:
        return (3000, 3099)
    
    # Backend API ports (8000-8999)  
    elif 8000 <= preferred_port <= 8999:
        return (8000, 8099)
    
    # Auth service ports (8080-8199)
    elif 8080 <= preferred_port <= 8199:
        return (8080, 8199)
    
    # Database ports (5400-5499)
    elif 5400 <= preferred_port <= 5499:
        return (5400, 5499)
    
    # Redis ports (6300-6399)
    elif 6300 <= preferred_port <= 6399:
        return (6300, 6399)
    
    # Default: extend original range by 50 ports
    else:
        start, end = original_range
        return (start, min(end + 50, 65535))


def _get_process_using_port(port: int) -> Optional[str]:
    """
    Get information about process using a specific port.
    
    Args:
        port: Port number to check
        
    Returns:
        Process information string or None
    """
    try:
        if sys.platform == "win32":
            return _get_windows_process_info(port)
        else:
            return _get_unix_process_info(port)
    except Exception as e:
        logger.debug(f"Failed to get process info for port {port}: {e}")
        return None


def _get_windows_process_info(port: int) -> Optional[str]:
    """Get process info on Windows using netstat."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if f":{port} " in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        # Try to get process name
                        try:
                            name_result = subprocess.run(
                                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                                capture_output=True,
                                text=True,
                                timeout=3
                            )
                            if name_result.returncode == 0:
                                lines = name_result.stdout.strip().split('\n')
                                if len(lines) > 1:
                                    process_name = lines[1].split(',')[0].strip('"')
                                    return f"{process_name} (PID: {pid})"
                        except Exception:
                            pass
                        return f"PID: {pid}"
    except Exception:
        pass
    return None


def _get_unix_process_info(port: int) -> Optional[str]:
    """Get process info on Unix systems using lsof."""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Skip header
                parts = lines[1].split()
                if len(parts) >= 2:
                    return f"{parts[0]} (PID: {parts[1]})"
    except Exception:
        pass
    return None


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
        base_env: Base environment to start with (defaults to isolated environment)
        **kwargs: Additional environment variables to add
    
    Returns:
        Complete environment dictionary
    """
    if base_env is None:
        isolated_env = get_env()
        env = isolated_env.get_subprocess_env()
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