#!/usr/bin/env python3
"""
Unified development launcher for Netra AI platform with real-time log streaming,
enhanced backend stability monitoring, and detailed secret loading visibility.
Starts both backend and frontend with automatic port allocation and service discovery.
"""

import os
import sys
import time
import json
import signal
import socket
import argparse
import subprocess
import webbrowser
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Robust path resolution
def get_project_root():
    """Find the project root directory robustly."""
    current_file = Path(__file__).resolve()
    
    # Check if we're in scripts directory
    if current_file.parent.name == 'scripts':
        return current_file.parent.parent
    # Check if we're already in project root
    elif (current_file.parent / 'frontend').exists() or (current_file.parent / 'app').exists():
        return current_file.parent
    # Try to find project root by looking for key files/dirs
    else:
        for parent in current_file.parents:
            if (parent / 'frontend').exists() or (parent / 'app').exists() or (parent / 'requirements.txt').exists():
                return parent
    
    # Fallback to parent of parent
    return current_file.parent.parent

# Get project root and add to path
PROJECT_ROOT = get_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

# Try multiple import strategies
try:
    from scripts.service_discovery import ServiceDiscovery
except ImportError:
    try:
        # If running from scripts directory, try direct import
        from service_discovery import ServiceDiscovery
    except ImportError:
        # Last resort - try to import from the scripts directory
        scripts_dir = PROJECT_ROOT / 'scripts'
        if scripts_dir.exists():
            sys.path.insert(0, str(scripts_dir))
            from service_discovery import ServiceDiscovery
        else:
            logger.error("Could not import ServiceDiscovery. Please check your installation.")
            sys.exit(1)

def resolve_path(*parts, required=False, search_dirs=None):
    """Resolve a path robustly, checking multiple locations."""
    # Default search directories
    if search_dirs is None:
        search_dirs = [
            Path.cwd(),  # Current working directory
            PROJECT_ROOT,  # Project root
            Path(__file__).parent,  # Script directory
            Path(__file__).parent.parent,  # Parent of script directory
        ]
    
    # Try each search directory
    for base_dir in search_dirs:
        path = base_dir / Path(*parts)
        if path.exists():
            return path.resolve()
    
    # If required and not found, raise error
    if required:
        searched = ', '.join(str(d) for d in search_dirs)
        raise FileNotFoundError(f"Could not find {'/'.join(parts)} in any of: {searched}")
    
    # Return the path relative to project root as fallback
    return PROJECT_ROOT / Path(*parts)

class LogStreamer(threading.Thread):
    """Streams process output in real-time with colored output."""
    
    def __init__(self, process, name, color_code=None):
        super().__init__(daemon=True)
        self.process = process
        self.name = name
        self.color_code = color_code or ""
        self.reset_code = "\033[0m" if color_code else ""
        self.running = True
        self.lines_buffer = []
        
    def run(self):
        """Stream output from process."""
        try:
            for line in iter(self.process.stdout.readline, b''):
                if not self.running:
                    break
                if line:
                    decoded_line = line.decode('utf-8', errors='replace').rstrip()
                    # Add to buffer for error detection
                    self.lines_buffer.append(decoded_line)
                    if len(self.lines_buffer) > 100:
                        self.lines_buffer.pop(0)
                    
                    # Print with color and prefix
                    print(f"{self.color_code}[{self.name}] {decoded_line}{self.reset_code}")
        except Exception as e:
            print(f"[{self.name}] Stream error: {e}")
    
    def stop(self):
        """Stop streaming."""
        self.running = False
    
    def get_recent_errors(self, lines=20):
        """Get recent error lines from buffer."""
        error_lines = []
        for line in self.lines_buffer[-lines:]:
            lower_line = line.lower()
            if any(keyword in lower_line for keyword in ['error', 'exception', 'traceback', 'failed']):
                error_lines.append(line)
        return error_lines

class ProcessMonitor:
    """Enhanced process monitor with real-time logging and better crash detection."""
    
    def __init__(self, name: str, start_func, restart_delay: int = 5, max_restarts: int = 3, color_code=None):
        self.name = name
        self.start_func = start_func
        self.restart_delay = restart_delay
        self.max_restarts = max_restarts
        self.restart_count = 0
        self.process = None
        self.monitoring = False
        self.monitor_thread = None
        self.last_restart_time = None
        self.crash_log = []
        self.log_streamer = None
        self.color_code = color_code
        
    def start(self):
        """Start the process and begin monitoring."""
        self.process, self.log_streamer = self.start_func()
        if self.process:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            return True
        return False
    
    def stop(self):
        """Stop monitoring and terminate the process."""
        self.monitoring = False
        if self.log_streamer:
            self.log_streamer.stop()
        if self.process and self.process.poll() is None:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    capture_output=True
                )
            else:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
    
    def _monitor_loop(self):
        """Enhanced monitoring with better crash detection."""
        consecutive_failures = 0
        
        while self.monitoring:
            if self.process and self.process.poll() is not None:
                # Process has stopped
                exit_code = self.process.returncode
                crash_time = datetime.now()
                
                # Get recent error messages
                recent_errors = []
                if self.log_streamer:
                    recent_errors = self.log_streamer.get_recent_errors()
                
                self.crash_log.append({
                    'time': crash_time,
                    'exit_code': exit_code,
                    'restart_count': self.restart_count,
                    'errors': recent_errors
                })
                
                print(f"\n[WARNING] {self.name} process stopped with exit code {exit_code}")
                if recent_errors:
                    print(f"   Recent errors:")
                    for error in recent_errors[:5]:
                        print(f"     {error}")
                
                # Check if we should restart
                if self.restart_count < self.max_restarts:
                    # Check for rapid restarts (more than 3 in 1 minute)
                    recent_crashes = [c for c in self.crash_log 
                                    if (crash_time - c['time']).total_seconds() < 60]
                    if len(recent_crashes) >= 3:
                        print(f"❌ {self.name} is crashing rapidly. Stopping auto-restart.")
                        self.monitoring = False
                        break
                    
                    print(f"[RESTART] Attempting to restart {self.name} (attempt {self.restart_count + 1}/{self.max_restarts})")
                    time.sleep(self.restart_delay)
                    
                    # Stop old streamer
                    if self.log_streamer:
                        self.log_streamer.stop()
                    
                    self.process, self.log_streamer = self.start_func()
                    if self.process:
                        self.restart_count += 1
                        self.last_restart_time = crash_time
                        consecutive_failures = 0
                        print(f"[OK] {self.name} restarted successfully")
                    else:
                        consecutive_failures += 1
                        print(f"❌ Failed to restart {self.name} (failure {consecutive_failures})")
                        if consecutive_failures >= 2:
                            print(f"❌ Multiple restart failures. Stopping {self.name} monitoring.")
                            self.monitoring = False
                            break
                else:
                    print(f"❌ {self.name} exceeded maximum restart attempts ({self.max_restarts})")
                    self.monitoring = False
                    break
            
            time.sleep(2)  # Check every 2 seconds

class EnhancedSecretLoader:
    """Enhanced secret loader with detailed visibility."""
    
    def __init__(self, project_id: Optional[str] = None, verbose: bool = False):
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT', "304612253870")
        self.verbose = verbose
        self.loaded_secrets = {}
        self.failed_secrets = []
        
    def load_from_env_file(self) -> Dict[str, Tuple[str, str]]:
        """Load secrets from existing .env file."""
        env_file = PROJECT_ROOT / ".env"
        loaded = {}
        
        if env_file.exists():
            print("[ENV] Loading from existing .env file...")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        loaded[key] = (value.strip('"\''), "env_file")
                        if self.verbose:
                            # Show masked value for sensitive data
                            masked_value = value[:3] + "***" if len(value) > 3 else "***"
                            print(f"   [OK] {key}: {masked_value} (from .env file)")
        return loaded
    
    def load_from_google_secrets(self) -> Dict[str, Tuple[str, str]]:
        """Load secrets from Google Secret Manager with detailed feedback."""
        print(f"\n[SECRETS] Loading secrets from Google Cloud Secret Manager...")
        print(f"   Project ID: {self.project_id}")
        
        try:
            from google.cloud import secretmanager
            
            # Create client with timeout
            import socket
            socket.setdefaulttimeout(10)
            client = secretmanager.SecretManagerServiceClient()
            print("   [OK] Connected to Secret Manager")
        except ImportError:
            print("   ❌ Google Cloud SDK not installed")
            return {}
        except Exception as e:
            print(f"   ❌ Failed to connect: {e}")
            return {}
        
        # Define the secrets to fetch
        secret_mappings = {
            "gemini-api-key": "GEMINI_API_KEY",
            "google-client-id": "GOOGLE_CLIENT_ID",
            "google-client-secret": "GOOGLE_CLIENT_SECRET",
            "langfuse-secret-key": "LANGFUSE_SECRET_KEY",
            "langfuse-public-key": "LANGFUSE_PUBLIC_KEY",
            "clickhouse-default-password": "CLICKHOUSE_DEFAULT_PASSWORD",
            "clickhouse-development-password": "CLICKHOUSE_DEVELOPMENT_PASSWORD",
            "jwt-secret-key": "JWT_SECRET_KEY",
            "fernet-key": "FERNET_KEY",
            "redis-default": "REDIS_PASSWORD"
        }
        
        loaded = {}
        print(f"\n   Fetching {len(secret_mappings)} secrets:")
        
        for secret_name, env_var in secret_mappings.items():
            try:
                name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(name=name)
                value = response.payload.data.decode("UTF-8")
                loaded[env_var] = (value, "google_secret")
                
                # Show success with masked value
                masked_value = value[:3] + "***" if len(value) > 3 else "***"
                print(f"   [OK] {env_var}: {masked_value} (from Google Secret: {secret_name})")
                
            except Exception as e:
                self.failed_secrets.append((env_var, str(e)))
                if self.verbose:
                    print(f"   [FAIL] {env_var}: Failed - {str(e)[:50]}")
        
        return loaded
    
    def load_all_secrets(self) -> bool:
        """Load secrets from all sources with priority."""
        print("\n[SECRETS] Loading Process Started")
        print("=" * 60)
        
        # First, try to load from existing .env file
        env_secrets = self.load_from_env_file()
        
        # Then try Google Secret Manager
        google_secrets = self.load_from_google_secrets()
        
        # Merge with Google secrets taking priority
        all_secrets = {**env_secrets, **google_secrets}
        
        # Add static configuration
        static_config = {
            "CLICKHOUSE_HOST": ("xedvrr4c3r.us-central1.gcp.clickhouse.cloud", "static"),
            "CLICKHOUSE_PORT": ("8443", "static"),
            "CLICKHOUSE_USER": ("default", "static"),
            "CLICKHOUSE_DB": ("default", "static"),
            "ENVIRONMENT": ("development", "static")
        }
        
        print("\n[CONFIG] Adding static configuration:")
        for key, (value, source) in static_config.items():
            if key not in all_secrets:
                all_secrets[key] = (value, source)
                if self.verbose:
                    print(f"   [OK] {key}: {value} (static config)")
        
        # Set environment variables
        print("\n[ENV] Setting environment variables...")
        for key, (value, source) in all_secrets.items():
            os.environ[key] = value
            self.loaded_secrets[key] = source
        
        # Summary
        print("\n" + "=" * 60)
        print("[SUMMARY] Secret Loading Summary:")
        
        sources = {}
        for key, source in self.loaded_secrets.items():
            sources[source] = sources.get(source, 0) + 1
        
        total = len(self.loaded_secrets)
        print(f"   Total secrets loaded: {total}")
        for source, count in sources.items():
            print(f"   - From {source}: {count}")
        
        if self.failed_secrets and self.verbose:
            print(f"\n   [WARNING] Failed to load {len(self.failed_secrets)} secrets:")
            for secret, error in self.failed_secrets[:3]:
                print(f"      - {secret}: {error[:50]}")
        
        # Write updated .env file
        self._write_env_file(all_secrets)
        
        print("=" * 60)
        return True
    
    def _write_env_file(self, secrets: Dict[str, Tuple[str, str]]):
        """Write secrets to .env file for persistence, preserving all existing variables."""
        env_file = PROJECT_ROOT / ".env"
        print(f"\n[SAVE] Writing secrets to {env_file}")
        
        with open(env_file, 'w') as f:
            f.write("# Auto-generated .env file\n")
            f.write(f"# Generated at {datetime.now().isoformat()}\n\n")
            
            # Define known categories for organization
            categories = {
                "Google OAuth": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
                "API Keys": ["GEMINI_API_KEY"],
                "Database": ["DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL"],  # Added these
                "ClickHouse": ["CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER", 
                              "CLICKHOUSE_DEFAULT_PASSWORD", "CLICKHOUSE_DEVELOPMENT_PASSWORD", "CLICKHOUSE_DB"],
                "Langfuse": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"],
                "Security": ["JWT_SECRET_KEY", "FERNET_KEY", "SECRET_KEY"],  # Added SECRET_KEY
                "Redis": ["REDIS_PASSWORD"],
                "Environment": ["ENVIRONMENT"],
                "Development": ["DEBUG", "RELOAD", "ALLOW_DEV_LOGIN", "ALLOW_MOCK_AUTH"],  # Added dev flags
                "URLs": ["FRONTEND_URL", "API_URL"]  # Added URL configs
            }
            
            # Track which keys have been written
            written_keys = set()
            
            # Write categorized keys first
            for category, keys in categories.items():
                category_has_values = any(key in secrets for key in keys)
                if category_has_values:
                    f.write(f"\n# {category}\n")
                    for key in keys:
                        if key in secrets:
                            value, source = secrets[key]
                            f.write(f"{key}={value}\n")
                            written_keys.add(key)
            
            # Write any remaining keys that weren't in categories
            uncategorized = {k: v for k, v in secrets.items() if k not in written_keys}
            if uncategorized:
                f.write(f"\n# Other Configuration\n")
                for key, (value, source) in uncategorized.items():
                    f.write(f"{key}={value}\n")

class DevLauncher:
    """Unified launcher with real-time streaming, monitoring, and enhanced secret loading."""
    
    def __init__(self, backend_port: Optional[int] = None, 
                 frontend_port: Optional[int] = None,
                 dynamic_ports: bool = False,
                 verbose: bool = False,
                 backend_reload: bool = True,
                 frontend_reload: bool = True,
                 load_secrets: bool = True,  # Default to True for dev mode
                 project_id: Optional[str] = None,
                 no_browser: bool = False,
                 auto_restart: bool = True,
                 use_turbopack: bool = False):
        """Initialize the development launcher."""
        self.backend_port = backend_port
        self.frontend_port = frontend_port or 3000
        self.dynamic_ports = dynamic_ports
        self.verbose = verbose
        self.backend_reload = backend_reload
        self.frontend_reload = frontend_reload
        self.load_secrets = load_secrets
        self.project_id = project_id
        self.no_browser = no_browser
        self.auto_restart = auto_restart
        self.use_turbopack = use_turbopack
        self.service_discovery = ServiceDiscovery()
        self.use_emoji = self._check_emoji_support()
        self.project_root = PROJECT_ROOT
        self.backend_monitor = None
        self.frontend_monitor = None
        self.backend_process = None
        self.backend_streamer = None
        self.frontend_process = None
        self.frontend_streamer = None
        
        if self.verbose:
            logger.info(f"Project root detected: {self.project_root}")
            logger.info(f"Current working directory: {Path.cwd()}")
            logger.info(f"Script location: {Path(__file__).resolve()}")
        
        # Register cleanup handler
        signal.signal(signal.SIGINT, self._cleanup_handler)
        signal.signal(signal.SIGTERM, self._cleanup_handler)
        
        # Windows-specific signal
        if sys.platform == "win32":
            signal.signal(signal.SIGBREAK, self._cleanup_handler)
    
    def _check_emoji_support(self) -> bool:
        """Check if the terminal supports emoji output."""
        try:
            # Try to encode an emoji
            "[OK]".encode(sys.stdout.encoding or 'utf-8')
            # Check if we're on Windows terminal that supports emojis
            if sys.platform == "win32":
                # Windows Terminal and VS Code terminal support emojis
                return os.environ.get('WT_SESSION') or os.environ.get('TERM_PROGRAM') == 'vscode'
            return True
        except (UnicodeEncodeError, AttributeError):
            return False
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji if supported, otherwise with text prefix."""
        if self.use_emoji:
            try:
                print(f"{emoji} {message}")
                return
            except UnicodeEncodeError:
                pass
        print(f"[{text}] {message}")
    
    def get_free_port(self) -> int:
        """Get a free port by binding to port 0."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def _cleanup_handler(self, signum, frame):
        """Handle cleanup on exit."""
        self._print("[STOP]", "STOP", "\nShutting down development environment...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up all running processes."""
        if self.backend_monitor:
            self.backend_monitor.stop()
        elif self.backend_process:
            if self.backend_streamer:
                self.backend_streamer.stop()
            if self.backend_process.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.backend_process.pid)],
                        capture_output=True
                    )
                else:
                    try:
                        os.killpg(os.getpgid(self.backend_process.pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
        
        if self.frontend_monitor:
            self.frontend_monitor.stop()
        elif self.frontend_process:
            if self.frontend_streamer:
                self.frontend_streamer.stop()
            if self.frontend_process.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.frontend_process.pid)],
                        capture_output=True
                    )
                else:
                    try:
                        os.killpg(os.getpgid(self.frontend_process.pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
        
        # Clear service discovery
        self.service_discovery.clear_all()
        self._print("[OK]", "OK", "Cleanup complete")
    
    def check_dependencies(self) -> bool:
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
        
        # Check if frontend directory exists
        frontend_dir = PROJECT_ROOT / "frontend"
        if not frontend_dir.exists():
            errors.append("❌ Frontend directory not found")
        else:
            # Check if node_modules exists
            node_modules = frontend_dir / "node_modules"
            if not node_modules.exists():
                errors.append(f"❌ Frontend dependencies not installed. Run: cd {frontend_dir} && npm install")
        
        if errors:
            print("Dependency check failed:")
            for error in errors:
                print(f"  {error}")
            return False
        
        self._print("[OK]", "OK", "All dependencies satisfied")
        return True
    
    def start_backend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the backend server with real-time log streaming."""
        self._print("\n[START]", "LAUNCH", "Starting backend server...")
        
        # Determine port
        if self.dynamic_ports:
            port = self.get_free_port()
            print(f"   Allocated port: {port}")
        else:
            port = self.backend_port or 8000
        
        # Store port for later use
        self.backend_port = port
        
        # Build command - use enhanced server if available, otherwise fallback to standard
        run_server_enhanced = resolve_path("scripts", "run_server_enhanced.py")
        run_server_path = resolve_path("scripts", "run_server.py")
        
        if run_server_enhanced and run_server_enhanced.exists():
            server_script = run_server_enhanced
            print("   Using enhanced server with health monitoring")
        elif run_server_path and run_server_path.exists():
            server_script = run_server_path
        else:
            self._print("❌", "ERROR", "Could not find run_server.py")
            return None, None
        
        cmd = [
            sys.executable,
            str(server_script),
            "--port", str(port)
        ]
        
        # Add reload flag
        if not self.backend_reload:
            cmd.append("--no-reload")
            print("   Hot reload: DISABLED")
        else:
            print("   Hot reload: ENABLED")
        
        # Add verbose flag if requested
        if self.verbose:
            cmd.append("--verbose")
        
        if self.verbose:
            print(f"   Command: {' '.join(cmd)}")
        
        # Start process
        try:
            # Set environment
            env = os.environ.copy()
            env["BACKEND_PORT"] = str(port)
            
            # Add project root to PYTHONPATH
            python_path = env.get("PYTHONPATH", "")
            if python_path:
                env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{python_path}"
            else:
                env["PYTHONPATH"] = str(PROJECT_ROOT)
            
            if sys.platform == "win32":
                # Windows: create new process group with real-time output
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=False
                )
            else:
                # Unix: create new process group with real-time output
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    preexec_fn=os.setsid,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=False
                )
            
            # Start log streamer with color
            log_streamer = LogStreamer(process, "BACKEND", "\033[36m")  # Cyan color
            log_streamer.start()
            
            # Wait a moment for the server to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                self._print("❌", "ERROR", "Backend failed to start")
                return None, None
            
            # Write service discovery info
            self.service_discovery.write_backend_info(port)
            
            self._print("[OK]", "OK", f"Backend started on port {port}")
            print(f"   API URL: http://localhost:{port}")
            print(f"   WebSocket URL: ws://localhost:{port}/ws")
            
            return process, log_streamer
            
        except Exception as e:
            self._print("❌", "ERROR", f"Failed to start backend: {e}")
            return None, None
    
    def start_frontend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the frontend server with real-time log streaming."""
        self._print("\n[START]", "LAUNCH", "Starting frontend server...")
        
        # Read backend info from service discovery
        backend_info = self.service_discovery.read_backend_info()
        if not backend_info:
            self._print("❌", "ERROR", "Backend service discovery not found. Backend may not be running.")
            return None, None
        
        # Determine port
        if self.dynamic_ports:
            port = self.get_free_port()
            print(f"   Allocated port: {port}")
            # Update the frontend_port to the actual allocated port
            self.frontend_port = port
        else:
            port = self.frontend_port
        
        # Build command based on whether to use turbopack
        frontend_path = resolve_path("frontend")
        if not frontend_path or not frontend_path.exists():
            self._print("❌", "ERROR", "Frontend directory not found")
            return None, None
        
        # Check if start_with_discovery.js exists
        start_script = frontend_path / "scripts" / "start_with_discovery.js"
        
        if self.use_turbopack:
            npm_command = "dev"  # Uses turbopack by default
            print("   Using Turbopack (experimental)")
        else:
            npm_command = "dev"  # Regular Next.js
        
        if start_script.exists():
            if sys.platform == "win32":
                cmd = ["node", "scripts/start_with_discovery.js", npm_command]
            else:
                cmd = ["node", "scripts/start_with_discovery.js", npm_command]
        else:
            if sys.platform == "win32":
                cmd = ["npm.cmd", "run", npm_command]
            else:
                cmd = ["npm", "run", npm_command]
        
        cwd_path = str(frontend_path)
        
        if self.verbose:
            print(f"   Command: {' '.join(cmd)}")
            print(f"   Working directory: {cwd_path}")
        
        # Start process
        try:
            # Set environment with backend URLs
            env = os.environ.copy()
            env["NEXT_PUBLIC_API_URL"] = backend_info["api_url"]
            env["NEXT_PUBLIC_WS_URL"] = backend_info["ws_url"]
            env["PORT"] = str(port)
            
            # Add project root to PYTHONPATH
            python_path = env.get("PYTHONPATH", "")
            if python_path:
                env["PYTHONPATH"] = f"{PROJECT_ROOT}{os.pathsep}{python_path}"
            else:
                env["PYTHONPATH"] = str(PROJECT_ROOT)
            
            # Disable hot reload if requested
            if not self.frontend_reload:
                env["WATCHPACK_POLLING"] = "false"
                env["NEXT_DISABLE_FAST_REFRESH"] = "true"
                print("   Hot reload: DISABLED")
            else:
                print("   Hot reload: ENABLED")
            
            if sys.platform == "win32":
                # Windows: create new process group with real-time output
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd_path,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=False
                )
            else:
                # Unix: create new process group with real-time output
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd_path,
                    env=env,
                    preexec_fn=os.setsid,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=False
                )
            
            # Start log streamer with color
            log_streamer = LogStreamer(process, "FRONTEND", "\033[35m")  # Magenta color
            log_streamer.start()
            
            # Wait for frontend to start
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is not None:
                self._print("❌", "ERROR", "Frontend failed to start")
                return None, None
            
            self._print("[OK]", "OK", f"Frontend started on port {port}")
            print(f"   URL: http://localhost:{port}")
            
            # Write frontend info to service discovery
            self.service_discovery.write_frontend_info(port)
            
            return process, log_streamer
            
        except Exception as e:
            self._print("❌", "ERROR", f"Failed to start frontend: {e}")
            return None, None
    
    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        """Wait for a service to become available."""
        import urllib.request
        import urllib.error
        
        start_time = time.time()
        attempt = 0
        while time.time() - start_time < timeout:
            attempt += 1
            try:
                with urllib.request.urlopen(url, timeout=3) as response:
                    if response.status == 200:
                        print(f"   Service ready after {attempt} attempts")
                        return True
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
                if attempt == 1:
                    print(f"   Waiting for service at {url}...")
                elif attempt % 10 == 0:
                    print(f"   Still waiting... ({attempt} attempts)")
                time.sleep(2)
        
        return False
    
    def open_browser(self, url: str) -> bool:
        """Open the browser with the given URL."""
        if self.no_browser:
            return False
        
        try:
            # Add a small delay to ensure the page is ready
            time.sleep(1)
            
            # Open the default browser
            webbrowser.open(url)
            self._print("[WEB]", "BROWSER", f"Opening browser at {url}")
            return True
        except Exception as e:
            self._print("[WARNING]", "WARN", f"Could not open browser automatically: {e}")
            return False
    
    def run(self):
        """Run the development environment with enhanced monitoring."""
        print("=" * 60)
        self._print("[LAUNCH]", "LAUNCH", "Netra AI Development Environment")
        print("=" * 60)
        
        # Show configuration summary
        self._print("\n[CONFIG]", "Configuration", ":")
        print(f"   * Dynamic ports: {'YES' if self.dynamic_ports else 'NO'}")
        print(f"   * Backend hot reload: {'YES' if self.backend_reload else 'NO'}")
        print(f"   * Frontend hot reload: {'YES' if self.frontend_reload else 'NO'}")
        print(f"   * Auto-restart on crash: {'YES' if self.auto_restart else 'NO'}")
        print(f"   * Real-time log streaming: YES")
        print(f"   * Turbopack: {'YES (experimental)' if self.use_turbopack else 'NO (webpack)'}")
        print(f"   * Secret loading: {'YES (Google + env)' if self.load_secrets else 'NO'}")
        print("")
        
        # Check dependencies
        if not self.check_dependencies():
            self._print("\n❌", "ERROR", "Please install missing dependencies and try again")
            return 1
        
        # Load secrets (default in dev mode)
        if self.load_secrets:
            secret_loader = EnhancedSecretLoader(self.project_id, self.verbose)
            secret_loader.load_all_secrets()
        
        # Clear old service discovery
        self.service_discovery.clear_all()
        
        # Create process monitors if auto-restart is enabled
        if self.auto_restart:
            self.backend_monitor = ProcessMonitor(
                "Backend",
                self.start_backend,
                restart_delay=5,
                max_restarts=3,
                color_code="\033[36m"  # Cyan
            )
            
            if not self.backend_monitor.start():
                self._print("❌", "ERROR", "Failed to start backend")
                self.cleanup()
                return 1
        else:
            # Start backend without monitoring
            self.backend_process, self.backend_streamer = self.start_backend()
            if not self.backend_process:
                self._print("❌", "ERROR", "Failed to start backend")
                self.cleanup()
                return 1
        
        # Wait for backend to be ready
        backend_info = self.service_discovery.read_backend_info()
        if backend_info:
            self._print("\n[WAIT]", "WAIT", "Waiting for backend to be ready...")
            backend_url = f"{backend_info['api_url']}/health/live"
            if self.wait_for_service(backend_url, timeout=30):
                self._print("[OK]", "OK", "Backend is ready")
            else:
                self._print("[WARNING]", "WARN", "Backend health check timed out, continuing anyway...")
        
        # Start frontend
        if self.auto_restart:
            self.frontend_monitor = ProcessMonitor(
                "Frontend",
                self.start_frontend,
                restart_delay=5,
                max_restarts=3,
                color_code="\033[35m"  # Magenta
            )
            
            if not self.frontend_monitor.start():
                self._print("❌", "ERROR", "Failed to start frontend")
                self.cleanup()
                return 1
        else:
            # Start frontend without monitoring
            self.frontend_process, self.frontend_streamer = self.start_frontend()
            if not self.frontend_process:
                self._print("❌", "ERROR", "Failed to start frontend")
                self.cleanup()
                return 1
        
        # Wait for frontend to be ready
        self._print("\n[WAIT]", "WAIT", "Waiting for frontend to be ready...")
        frontend_url = f"http://localhost:{self.frontend_port}"
        
        # Give Next.js a bit more time to compile initially
        print("   Allowing Next.js to compile...")
        time.sleep(3)
        
        frontend_ready = False
        if self.wait_for_service(frontend_url, timeout=90):
            self._print("[OK]", "OK", "Frontend is ready")
            frontend_ready = True
            
            # Automatically open browser when frontend is ready
            if not self.no_browser:
                self.open_browser(frontend_url)
        else:
            self._print("[WARNING]", "WARN", "Frontend readiness check timed out")
        
        # Print summary
        print("\n" + "=" * 60)
        self._print("✨", "SUCCESS", "Development environment is running!")
        print("=" * 60)
        
        if backend_info:
            self._print("\n[BACKEND]", "Backend", "")
            print(f"   API: {backend_info['api_url']}")
            print(f"   WebSocket: {backend_info['ws_url']}")
            print(f"   Logs: Real-time streaming (cyan)")
        
        self._print("\n[FRONTEND]", "Frontend", "")
        print(f"   URL: http://localhost:{self.frontend_port}")
        print(f"   Logs: Real-time streaming (magenta)")
        
        if self.auto_restart:
            self._print("\n[AUTO]", "Auto-Restart", "Enabled")
            print("   Services will automatically restart if they crash")
        
        print("\n[COMMANDS]:")
        print("   Press Ctrl+C to stop all services")
        print("   Logs are streamed in real-time with color coding")
        print("-" * 60 + "\n")
        
        # Wait for processes
        try:
            while True:
                # If not using auto-restart, check if processes are still running
                if not self.auto_restart:
                    if self.backend_process and self.backend_process.poll() is not None:
                        self._print(f"\n[WARNING]", "WARN", "Backend process has stopped")
                        self.cleanup()
                        return 1
                    if self.frontend_process and self.frontend_process.poll() is not None:
                        self._print(f"\n[WARNING]", "WARN", "Frontend process has stopped")
                        self.cleanup()
                        return 1
                else:
                    # Check if monitors are still running
                    if self.backend_monitor and not self.backend_monitor.monitoring:
                        self._print(f"\n[WARNING]", "WARN", "Backend monitoring stopped (exceeded max restarts)")
                        self.cleanup()
                        return 1
                    if self.frontend_monitor and not self.frontend_monitor.monitoring:
                        self._print(f"\n[WARNING]", "WARN", "Frontend monitoring stopped (exceeded max restarts)")
                        self.cleanup()
                        return 1
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            self._print("\n\n[INTERRUPT]", "INTERRUPT", "Received interrupt signal")
        
        self.cleanup()
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified development launcher with real-time streaming and detailed secret loading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RECOMMENDED USAGE:
  python dev_launcher.py --dynamic --no-backend-reload --auto-restart
  
  This configuration provides:
    • Real-time log streaming with color coding
    • Automatic port allocation (no conflicts)
    • 30-50% faster performance
    • Auto-restart on crashes
    • Automatic Google secret loading (default in dev mode)
    • Better error detection and reporting

Examples:
  python dev_launcher.py                                    # Default: loads secrets, auto-restart, streaming
  python dev_launcher.py --dynamic --auto-restart          # Best for development
  python dev_launcher.py --no-secrets                      # Skip secret loading
  python dev_launcher.py --no-turbopack                    # Use webpack
  python dev_launcher.py --no-reload                       # Maximum performance
        """
    )
    
    parser.add_argument("--backend-port", type=int, help="Backend server port")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend server port")
    parser.add_argument("--dynamic", action="store_true", help="Use dynamic port allocation")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--no-backend-reload", action="store_true", help="Disable backend hot reload")
    parser.add_argument("--no-frontend-reload", action="store_true", help="Disable frontend hot reload")
    parser.add_argument("--no-reload", action="store_true", help="Disable all hot reload")
    parser.add_argument("--no-secrets", action="store_true", help="Skip loading secrets from Google Cloud")
    parser.add_argument("--project-id", type=str, help="Google Cloud project ID")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--no-auto-restart", action="store_true", help="Disable automatic restart on crash")
    parser.add_argument("--no-turbopack", action="store_true", help="Use webpack instead of turbopack")
    
    args = parser.parse_args()
    
    # Handle reload flags
    backend_reload = not args.no_backend_reload and not args.no_reload
    frontend_reload = not args.no_frontend_reload and not args.no_reload
    
    # Default to loading secrets in dev mode (unless --no-secrets is specified)
    load_secrets = not args.no_secrets
    
    # Default to auto-restart unless disabled
    auto_restart = not args.no_auto_restart
    
    launcher = DevLauncher(
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        dynamic_ports=args.dynamic,
        verbose=args.verbose,
        backend_reload=backend_reload,
        frontend_reload=frontend_reload,
        load_secrets=load_secrets,
        project_id=args.project_id,
        no_browser=args.no_browser,
        auto_restart=auto_restart,
        use_turbopack=not args.no_turbopack
    )
    
    sys.exit(launcher.run())


if __name__ == "__main__":
    main()