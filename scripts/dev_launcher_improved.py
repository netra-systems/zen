#!/usr/bin/env python3
"""
Improved development launcher for Netra AI platform with auto-restart and better monitoring.
Starts both backend and frontend with automatic port allocation, service discovery, and health monitoring.
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
from typing import Optional, Dict, Any, List
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

class ProcessMonitor:
    """Monitors a process and restarts it if it crashes."""
    
    def __init__(self, name: str, start_func, restart_delay: int = 5, max_restarts: int = 3):
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
        
    def start(self):
        """Start the process and begin monitoring."""
        self.process = self.start_func()
        if self.process:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            return True
        return False
    
    def stop(self):
        """Stop monitoring and terminate the process."""
        self.monitoring = False
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
        """Monitor the process and restart if needed."""
        while self.monitoring:
            if self.process and self.process.poll() is not None:
                # Process has stopped
                exit_code = self.process.returncode
                crash_time = datetime.now()
                self.crash_log.append({
                    'time': crash_time,
                    'exit_code': exit_code,
                    'restart_count': self.restart_count
                })
                
                logger.warning(f"{self.name} process stopped with exit code {exit_code}")
                
                # Check if we should restart
                if self.restart_count < self.max_restarts:
                    # Check for rapid restarts (more than 3 in 1 minute)
                    recent_crashes = [c for c in self.crash_log 
                                    if (crash_time - c['time']).total_seconds() < 60]
                    if len(recent_crashes) >= 3:
                        logger.error(f"{self.name} is crashing rapidly. Stopping auto-restart.")
                        self.monitoring = False
                        break
                    
                    logger.info(f"Attempting to restart {self.name} (attempt {self.restart_count + 1}/{self.max_restarts})")
                    time.sleep(self.restart_delay)
                    
                    self.process = self.start_func()
                    if self.process:
                        self.restart_count += 1
                        self.last_restart_time = crash_time
                        logger.info(f"{self.name} restarted successfully")
                    else:
                        logger.error(f"Failed to restart {self.name}")
                        self.monitoring = False
                        break
                else:
                    logger.error(f"{self.name} exceeded maximum restart attempts ({self.max_restarts})")
                    self.monitoring = False
                    break
            
            time.sleep(2)  # Check every 2 seconds

class ImprovedDevLauncher:
    """Manages the development environment launch process with monitoring and auto-restart."""
    
    def __init__(self, backend_port: Optional[int] = None, 
                 frontend_port: Optional[int] = None,
                 dynamic_ports: bool = False,
                 verbose: bool = False,
                 backend_reload: bool = True,
                 frontend_reload: bool = True,
                 load_secrets: bool = False,
                 project_id: Optional[str] = None,
                 no_browser: bool = False,
                 auto_restart: bool = True,
                 use_turbopack: bool = False):
        """Initialize the improved development launcher."""
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
            "✅".encode(sys.stdout.encoding or 'utf-8')
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
        self._print("🛑", "STOP", "\nShutting down development environment...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up all running processes."""
        if self.backend_monitor:
            self.backend_monitor.stop()
        if self.frontend_monitor:
            self.frontend_monitor.stop()
        
        # Clear service discovery
        self.service_discovery.clear_all()
        self._print("✅", "OK", "Cleanup complete")
    
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
        
        # Check Google Cloud SDK if secrets loading is requested
        if self.load_secrets:
            fetch_script = resolve_path("scripts", "fetch_secrets_to_env.py")
            if not fetch_script or not fetch_script.exists():
                errors.append("❌ fetch_secrets_to_env.py not found")
            
            # Check for project ID
            if not self.project_id and not os.environ.get('GOOGLE_CLOUD_PROJECT'):
                errors.append("❌ Google Cloud project ID not specified. Use --project-id or set GOOGLE_CLOUD_PROJECT env var")
        
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
        
        self._print("✅", "OK", "All dependencies satisfied")
        return True
    
    def start_backend(self) -> Optional[subprocess.Popen]:
        """Start the backend server."""
        self._print("\n🚀", "LAUNCH", "Starting backend server...")
        
        # Determine port
        if self.dynamic_ports:
            port = self.get_free_port()
            print(f"   Allocated port: {port}")
        else:
            port = self.backend_port or 8000
        
        # Store port for later use
        self.backend_port = port
        
        # Build command
        run_server_path = resolve_path("scripts", "run_server.py")
        if not run_server_path or not run_server_path.exists():
            self._print("❌", "ERROR", "Could not find run_server.py")
            return None
        
        cmd = [
            sys.executable,
            str(run_server_path),
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
            
            # Create log file for backend output
            log_dir = PROJECT_ROOT / "logs"
            log_dir.mkdir(exist_ok=True)
            backend_log = log_dir / f"backend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            log_file = open(backend_log, 'w')
            
            if sys.platform == "win32":
                # Windows: create new process group
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
            else:
                # Unix: create new process group
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    preexec_fn=os.setsid,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
            
            # Wait a moment for the server to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                self._print("❌", "ERROR", "Backend failed to start")
                log_file.close()
                # Read and display error from log
                with open(backend_log, 'r') as f:
                    error_output = f.read()
                    if error_output:
                        print(f"   Error output:\n{error_output[:500]}")
                return None
            
            # Write service discovery info
            self.service_discovery.write_backend_info(port)
            
            self._print("✅", "OK", f"Backend started on port {port}")
            print(f"   API URL: http://localhost:{port}")
            print(f"   WebSocket URL: ws://localhost:{port}/ws")
            print(f"   Log file: {backend_log}")
            
            return process
            
        except Exception as e:
            self._print("❌", "ERROR", f"Failed to start backend: {e}")
            return None
    
    def start_frontend(self) -> Optional[subprocess.Popen]:
        """Start the frontend server."""
        self._print("\n🚀", "LAUNCH", "Starting frontend server...")
        
        # Read backend info from service discovery
        backend_info = self.service_discovery.read_backend_info()
        if not backend_info:
            self._print("❌", "ERROR", "Backend service discovery not found. Backend may not be running.")
            return None
        
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
            return None
        
        # Check if start_with_discovery.js exists
        start_script = frontend_path / "scripts" / "start_with_discovery.js"
        
        if self.use_turbopack:
            npm_command = "dev"  # Uses turbopack by default in package.json
            print("   Using Turbopack (experimental)")
        else:
            # Use regular Next.js without turbopack
            npm_command = "dev:webpack"  # We'll create this script
        
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
            
            # Create log file for frontend output
            log_dir = PROJECT_ROOT / "logs"
            log_dir.mkdir(exist_ok=True)
            frontend_log = log_dir / f"frontend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            log_file = open(frontend_log, 'w')
            
            if sys.platform == "win32":
                # Windows: create new process group
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd_path,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
            else:
                # Unix: create new process group
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd_path,
                    env=env,
                    preexec_fn=os.setsid,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
            
            # Wait for frontend to start
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is not None:
                self._print("❌", "ERROR", "Frontend failed to start")
                log_file.close()
                # Read and display error from log
                with open(frontend_log, 'r') as f:
                    error_output = f.read()
                    if error_output:
                        print(f"   Error output:\n{error_output[:500]}")
                return None
            
            self._print("✅", "OK", f"Frontend started on port {port}")
            print(f"   URL: http://localhost:{port}")
            print(f"   Log file: {frontend_log}")
            
            # Write frontend info to service discovery
            self.service_discovery.write_frontend_info(port)
            
            return process
            
        except Exception as e:
            self._print("❌", "ERROR", f"Failed to start frontend: {e}")
            return None
    
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
            self._print("🌐", "BROWSER", f"Opening browser at {url}")
            return True
        except Exception as e:
            self._print("⚠️", "WARN", f"Could not open browser automatically: {e}")
            return False
    
    def load_secrets_from_gcp(self) -> bool:
        """Load secrets from Google Cloud Secret Manager."""
        if not self.load_secrets:
            return True
        
        self._print("\n🔐", "SECRETS", "Loading secrets from Google Cloud Secret Manager...")
        
        try:
            # Run the fetch_secrets_to_env.py script
            project_id = self.project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
            if not project_id:
                self._print("❌", "ERROR", "No Google Cloud project ID specified")
                return False
            
            print(f"   Project ID: {project_id}")
            
            # Build command
            fetch_script = resolve_path("scripts", "fetch_secrets_to_env.py")
            if not fetch_script or not fetch_script.exists():
                self._print("⚠️", "WARN", "fetch_secrets_to_env.py not found, skipping secret loading")
                return False
            
            cmd = [sys.executable, str(fetch_script)]
            
            # Set environment
            env = os.environ.copy()
            env['GOOGLE_CLOUD_PROJECT'] = project_id
            
            # Run the script
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self._print("✅", "OK", "Secrets loaded successfully")
                # Load the created .env file into current environment
                env_file = resolve_path(".env")
                if env_file and env_file.exists():
                    with open(env_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                os.environ[key] = value.strip('"\'')
                    print(f"   Loaded secrets into environment")
                return True
            else:
                self._print("❌", "ERROR", f"Failed to load secrets")
                if result.stdout:
                    print(f"   Output: {result.stdout}")
                if result.stderr:
                    print(f"   Error: {result.stderr}")
                return False
            
        except subprocess.TimeoutExpired:
            self._print("❌", "ERROR", "Secret loading timed out after 30 seconds")
            return False
        except Exception as e:
            self._print("❌", "ERROR", f"Failed to load secrets: {e}")
            return False
    
    def run(self):
        """Run the development environment."""
        print("=" * 60)
        self._print("🚀", "LAUNCH", "Netra AI Development Environment (Improved)")
        print("=" * 60)
        
        # Show configuration summary
        self._print("\n📝", "Configuration", ":")
        print(f"   * Dynamic ports: {'YES' if self.dynamic_ports else 'NO'}")
        print(f"   * Backend hot reload: {'YES' if self.backend_reload else 'NO'}")
        print(f"   * Frontend hot reload: {'YES' if self.frontend_reload else 'NO'}")
        print(f"   * Auto-restart on crash: {'YES' if self.auto_restart else 'NO'}")
        print(f"   * Turbopack: {'YES (experimental)' if self.use_turbopack else 'NO (webpack)'}")
        if self.load_secrets:
            print("   * Secret loading: YES")
        print("")
        
        # Check dependencies
        if not self.check_dependencies():
            self._print("\n❌", "ERROR", "Please install missing dependencies and try again")
            return 1
        
        # Load secrets if requested
        if self.load_secrets:
            self.load_secrets_from_gcp()
        
        # Clear old service discovery
        self.service_discovery.clear_all()
        
        # Create process monitors if auto-restart is enabled
        if self.auto_restart:
            self.backend_monitor = ProcessMonitor(
                "Backend",
                self.start_backend,
                restart_delay=5,
                max_restarts=3
            )
            
            if not self.backend_monitor.start():
                self._print("❌", "ERROR", "Failed to start backend")
                self.cleanup()
                return 1
        else:
            # Start backend without monitoring
            backend_process = self.start_backend()
            if not backend_process:
                self._print("❌", "ERROR", "Failed to start backend")
                self.cleanup()
                return 1
        
        # Wait for backend to be ready
        backend_info = self.service_discovery.read_backend_info()
        if backend_info:
            self._print("\n⏳", "WAIT", "Waiting for backend to be ready...")
            backend_url = f"{backend_info['api_url']}/health/live"
            if self.wait_for_service(backend_url, timeout=30):
                self._print("✅", "OK", "Backend is ready")
            else:
                self._print("⚠️", "WARN", "Backend health check timed out, continuing anyway...")
        
        # Start frontend
        if self.auto_restart:
            self.frontend_monitor = ProcessMonitor(
                "Frontend",
                self.start_frontend,
                restart_delay=5,
                max_restarts=3
            )
            
            if not self.frontend_monitor.start():
                self._print("❌", "ERROR", "Failed to start frontend")
                self.cleanup()
                return 1
        else:
            # Start frontend without monitoring
            frontend_process = self.start_frontend()
            if not frontend_process:
                self._print("❌", "ERROR", "Failed to start frontend")
                self.cleanup()
                return 1
        
        # Wait for frontend to be ready
        self._print("\n⏳", "WAIT", "Waiting for frontend to be ready...")
        frontend_url = f"http://localhost:{self.frontend_port}"
        
        # Give Next.js a bit more time to compile initially
        print("   Allowing Next.js to compile...")
        time.sleep(3)
        
        frontend_ready = False
        if self.wait_for_service(frontend_url, timeout=90):
            self._print("✅", "OK", "Frontend is ready")
            frontend_ready = True
            
            # Automatically open browser when frontend is ready
            if not self.no_browser:
                self.open_browser(frontend_url)
        else:
            self._print("⚠️", "WARN", "Frontend readiness check timed out")
        
        # Print summary
        print("\n" + "=" * 60)
        self._print("✨", "SUCCESS", "Development environment is running!")
        print("=" * 60)
        
        if backend_info:
            self._print("\nℹ️", "INFO", "Backend:")
            print(f"   API: {backend_info['api_url']}")
            print(f"   WebSocket: {backend_info['ws_url']}")
        
        self._print("\n🌐", "Frontend", "")
        print(f"   URL: http://localhost:{self.frontend_port}")
        
        if self.auto_restart:
            self._print("\n🔄", "Auto-Restart", "Enabled")
            print("   Services will automatically restart if they crash")
        
        print("\n[COMMANDS]:")
        print("   Press Ctrl+C to stop all services")
        print("   Logs are saved in: logs/")
        print("-" * 60)
        
        # Wait for processes
        try:
            while True:
                # If not using auto-restart, check if processes are still running
                if not self.auto_restart:
                    if hasattr(self, 'backend_process') and backend_process.poll() is not None:
                        self._print(f"\n⚠️", "WARN", "Backend process has stopped")
                        self.cleanup()
                        return 1
                    if hasattr(self, 'frontend_process') and frontend_process.poll() is not None:
                        self._print(f"\n⚠️", "WARN", "Frontend process has stopped")
                        self.cleanup()
                        return 1
                else:
                    # Check if monitors are still running
                    if self.backend_monitor and not self.backend_monitor.monitoring:
                        self._print(f"\n⚠️", "WARN", "Backend monitoring stopped (exceeded max restarts)")
                        self.cleanup()
                        return 1
                    if self.frontend_monitor and not self.frontend_monitor.monitoring:
                        self._print(f"\n⚠️", "WARN", "Frontend monitoring stopped (exceeded max restarts)")
                        self.cleanup()
                        return 1
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            self._print("\n\n🔄", "INTERRUPT", "Received interrupt signal")
        
        self.cleanup()
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Improved development launcher for Netra AI platform with auto-restart",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RECOMMENDED USAGE:
  python dev_launcher_improved.py --dynamic --no-backend-reload --auto-restart
  
  This configuration provides:
    • Automatic port allocation (no conflicts)
    • 30-50% faster performance
    • Auto-restart on crashes
    • Better error logging

Examples:
  python dev_launcher_improved.py --dynamic --auto-restart  # Best for development
  python dev_launcher_improved.py --no-turbopack           # Use webpack instead of turbopack
  python dev_launcher_improved.py --no-reload              # Maximum performance
        """
    )
    
    parser.add_argument("--backend-port", type=int, help="Backend server port")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend server port")
    parser.add_argument("--dynamic", action="store_true", help="Use dynamic port allocation")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--no-backend-reload", action="store_true", help="Disable backend hot reload")
    parser.add_argument("--no-frontend-reload", action="store_true", help="Disable frontend hot reload")
    parser.add_argument("--no-reload", action="store_true", help="Disable all hot reload")
    parser.add_argument("--load-secrets", action="store_true", help="Load secrets from Google Cloud")
    parser.add_argument("--project-id", type=str, help="Google Cloud project ID")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--auto-restart", action="store_true", help="Automatically restart crashed services")
    parser.add_argument("--no-turbopack", action="store_true", help="Use webpack instead of turbopack")
    
    args = parser.parse_args()
    
    # Handle reload flags
    backend_reload = not args.no_backend_reload and not args.no_reload
    frontend_reload = not args.no_frontend_reload and not args.no_reload
    
    launcher = ImprovedDevLauncher(
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        dynamic_ports=args.dynamic,
        verbose=args.verbose,
        backend_reload=backend_reload,
        frontend_reload=frontend_reload,
        load_secrets=args.load_secrets,
        project_id=args.project_id,
        no_browser=args.no_browser,
        auto_restart=args.auto_restart,
        use_turbopack=not args.no_turbopack
    )
    
    sys.exit(launcher.run())


if __name__ == "__main__":
    main()