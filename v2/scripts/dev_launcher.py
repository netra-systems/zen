#!/usr/bin/env python3
"""
Unified development launcher for Netra AI platform.
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
from pathlib import Path
from typing import Optional, Dict, Any, List

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
            print("ERROR: Could not import ServiceDiscovery. Please check your installation.")
            sys.exit(1)

def resolve_path(*parts, required=False, search_dirs=None):
    """Resolve a path robustly, checking multiple locations.
    
    Args:
        *parts: Path components to join
        required: If True, raise error if path not found
        search_dirs: Additional directories to search in
    
    Returns:
        Path object if found, None otherwise
    """
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

class DevLauncher:
    """Manages the development environment launch process."""
    
    def __init__(self, backend_port: Optional[int] = None, 
                 frontend_port: Optional[int] = None,
                 dynamic_ports: bool = False,
                 verbose: bool = False,
                 backend_reload: bool = True,
                 frontend_reload: bool = True,
                 load_secrets: bool = False,
                 project_id: Optional[str] = None,
                 no_browser: bool = False):
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
        self.processes: List[subprocess.Popen] = []
        self.service_discovery = ServiceDiscovery()
        self.use_emoji = self._check_emoji_support()
        self.project_root = PROJECT_ROOT
        
        if self.verbose:
            print(f"[DEBUG] Project root detected: {self.project_root}")
            print(f"[DEBUG] Current working directory: {Path.cwd()}")
            print(f"[DEBUG] Script location: {Path(__file__).resolve()}")
        
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
        for process in self.processes:
            if process.poll() is None:  # Process is still running
                if sys.platform == "win32":
                    # Windows: terminate process tree
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        capture_output=True
                    )
                else:
                    # Unix: terminate process group
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
        
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
            # Check if fetch_secrets_to_env.py exists - try PROJECT_ROOT first
            fetch_script = PROJECT_ROOT / "fetch_secrets_to_env.py"
            if not fetch_script.exists():
                # Try scripts directory
                fetch_script = PROJECT_ROOT / "scripts" / "fetch_secrets_to_env.py"
            if not fetch_script.exists():
                # Try resolve_path as last resort
                fetch_script = resolve_path("fetch_secrets_to_env.py")
            
            if not fetch_script or not fetch_script.exists():
                errors.append("❌ fetch_secrets_to_env.py not found")
                if self.verbose:
                    errors.append(f"   Searched in: {PROJECT_ROOT} and {PROJECT_ROOT / 'scripts'}")
            
            # Check for project ID
            if not self.project_id and not os.environ.get('GOOGLE_CLOUD_PROJECT'):
                errors.append("❌ Google Cloud project ID not specified. Use --project-id or set GOOGLE_CLOUD_PROJECT env var")
        
        # Check if frontend directory exists - force using PROJECT_ROOT
        frontend_dir = PROJECT_ROOT / "frontend"
        if not frontend_dir.exists():
            # Try resolve_path as fallback
            frontend_dir = resolve_path("frontend")
        
        if not frontend_dir or not frontend_dir.exists():
            errors.append("❌ Frontend directory not found")
            if self.verbose:
                errors.append(f"   Searched in: {PROJECT_ROOT}")
                errors.append(f"   Current directory: {Path.cwd()}")
                # List what directories ARE present
                try:
                    dirs = [d.name for d in PROJECT_ROOT.iterdir() if d.is_dir()]
                    errors.append(f"   Available directories: {', '.join(dirs[:10])}")
                except:
                    pass
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
        
        # Build command
        # Find run_server.py robustly
        run_server_path = resolve_path("run_server.py")
        if not run_server_path or not run_server_path.exists():
            # Try scripts directory as fallback
            run_server_path = resolve_path("scripts", "run_server.py")
        
        if not run_server_path or not run_server_path.exists():
            self._print("❌", "ERROR", "Could not find run_server.py")
            if self.verbose:
                print(f"   Searched in: {PROJECT_ROOT}")
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
        
        if self.verbose:
            print(f"   Command: {' '.join(cmd)}")
        
        # Set environment
        env = os.environ.copy()
        env["BACKEND_PORT"] = str(port)
        
        # Start process
        try:
            if sys.platform == "win32":
                # Windows: create new process group
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Unix: create new process group
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    preexec_fn=os.setsid
                )
            
            # Wait a moment for the server to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                self._print("❌", "ERROR", "Backend failed to start")
                return None
            
            self._print("✅", "OK", f"Backend started on port {port}")
            print(f"   API URL: http://localhost:{port}")
            print(f"   WebSocket URL: ws://localhost:{port}/ws")
            
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
        
        # Always use dev command for simplicity - we'll control hot reload via env var
        npm_command = "dev"
        
        # Build command based on OS - avoid shell=True with arguments to prevent deprecation warning
        # Determine frontend path robustly
        frontend_path = resolve_path("frontend")
        if not frontend_path or not frontend_path.exists():
            self._print("❌", "ERROR", "Frontend directory not found")
            if self.verbose:
                print(f"   Searched in: {PROJECT_ROOT}")
            return None
        
        # Check if start_with_discovery.js exists
        start_script = frontend_path / "scripts" / "start_with_discovery.js"
        if not start_script.exists():
            self._print("⚠️", "WARN", "start_with_discovery.js not found, using npm directly")
            # Fallback to npm directly
            if sys.platform == "win32":
                cmd = ["npm.cmd", "run", npm_command]
            else:
                cmd = ["npm", "run", npm_command]
        else:
            if sys.platform == "win32":
                # Windows - use node directly without shell
                cmd = ["node", "scripts/start_with_discovery.js", npm_command]
            else:
                # Unix-like - use node directly without shell
                cmd = ["node", "scripts/start_with_discovery.js", npm_command]
        
        cwd_path = str(frontend_path)
        
        if self.verbose:
            print(f"   Command: {' '.join(cmd)}")
            print(f"   Working directory: {cwd_path}")
        
        # Set environment with backend URLs
        env = os.environ.copy()
        env["NEXT_PUBLIC_API_URL"] = backend_info["api_url"]
        env["NEXT_PUBLIC_WS_URL"] = backend_info["ws_url"]
        env["PORT"] = str(port)
        
        # Disable hot reload if requested
        # Next.js respects WATCHPACK_POLLING environment variable
        # Setting it to a very high value effectively disables file watching
        if not self.frontend_reload:
            # Disable file watching by setting a very high polling interval
            env["WATCHPACK_POLLING"] = "false"
            # Also disable Fast Refresh
            env["NEXT_DISABLE_FAST_REFRESH"] = "true"
            print("   Hot reload: DISABLED (dev server without file watching)")
        else:
            print("   Hot reload: ENABLED")
        
        # Start process
        try:
            if sys.platform == "win32":
                # Windows: create new process group
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd_path,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Unix: create new process group
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd_path,
                    env=env,
                    preexec_fn=os.setsid
                )
            
            # Wait for frontend to start
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is not None:
                self._print("❌", "ERROR", "Frontend failed to start")
                return None
            
            self._print("✅", "OK", f"Frontend started on port {port}")
            print(f"   URL: http://localhost:{port}")
            
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
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
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
            # Find fetch_secrets_to_env.py robustly
            fetch_script = resolve_path("fetch_secrets_to_env.py")
            if not fetch_script or not fetch_script.exists():
                # Try scripts directory
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
                text=True
            )
            
            if result.returncode == 0:
                self._print("✅", "OK", "Secrets loaded successfully")
                # Load the created .env file into current environment
                # Try multiple locations for .env file
                env_file = resolve_path(".env")
                if env_file and env_file.exists():
                    with open(env_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                os.environ[key] = value.strip('"\'')
                return True
            else:
                self._print("❌", "ERROR", f"Failed to load secrets: {result.stderr}")
                return False
            
        except Exception as e:
            self._print("❌", "ERROR", f"Failed to load secrets: {e}")
            print("   Continuing without secrets (some features may not work)")
            return False
    
    def run(self):
        """Run the development environment."""
        print("=" * 60)
        self._print("🚀", "LAUNCH", "Netra AI Development Environment Launcher")
        print("=" * 60)
        
        # Add diagnostic info in verbose mode
        if self.verbose:
            print("\n[DIAGNOSTIC INFO]")
            print(f"  Python: {sys.version}")
            print(f"  Platform: {sys.platform}")
            print(f"  Project Root: {self.project_root}")
            print(f"  Current Dir: {Path.cwd()}")
            print(f"  Script Path: {Path(__file__).resolve()}")
            print("-" * 60)
        
        # Show configuration summary
        if self.dynamic_ports and not self.backend_reload:
            self._print("\n🎆", "RECOMMENDED", "Running with RECOMMENDED configuration:")
            print("   * Dynamic ports: YES (avoiding conflicts)")
            print("   * Backend hot reload: NO (30-50% faster)")
            print(f"   * Frontend hot reload: {'YES' if self.frontend_reload else 'NO (faster compilation)'}")
            if self.load_secrets:
                print("   * Secret loading: YES (from Google Cloud)")
            print("   Perfect for first-time setup!\n")
        elif self.dynamic_ports or not self.backend_reload or not self.frontend_reload:
            self._print("\n📝", "Configuration", ":")
            if self.dynamic_ports:
                print("   * Dynamic ports: YES")
            print(f"   * Backend hot reload: {'YES' if self.backend_reload else 'NO (faster)'}")
            print(f"   * Frontend hot reload: {'YES' if self.frontend_reload else 'NO (faster compilation)'}")
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
        
        # Start backend
        backend_process = self.start_backend()
        if not backend_process:
            self._print("❌", "ERROR", "Failed to start backend")
            self.cleanup()
            return 1
        
        self.processes.append(backend_process)
        
        # Wait for backend to be ready
        backend_info = self.service_discovery.read_backend_info()
        if backend_info:
            self._print("\n⏳", "WAIT", "Waiting for backend to be ready...")
            # Use /health/ready endpoint for readiness check
            backend_url = f"{backend_info['api_url']}/health/ready"
            if self.wait_for_service(backend_url, timeout=30):
                self._print("✅", "OK", "Backend is ready")
            else:
                self._print("⚠️", "WARN", "Backend health check timed out, continuing anyway...")
        
        # Start frontend
        frontend_process = self.start_frontend()
        if not frontend_process:
            self._print("❌", "ERROR", "Failed to start frontend")
            self.cleanup()
            return 1
        
        self.processes.append(frontend_process)
        
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
            self._print("⚠️", "WARN", "Frontend readiness check timed out (this is usually OK)")
            print("   The frontend may still be compiling. You can proceed.")
        
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
        if not self.no_browser and frontend_ready:
            print("   Browser: Automatically opened")
        elif self.no_browser:
            print("   Browser: Manual open required (--no-browser flag used)")
        
        self._print("\n📝", "Service Discovery", ":")
        print(f"   Info stored in: .netra/")
        
        print("\n[COMMANDS]:")
        print("   Press Ctrl+C to stop all services")
        print("   Run 'python scripts/service_discovery.py status' to check service status")
        
        self._print("\n📊", "Logs", ":")
        print("   Backend and frontend logs will appear here")
        print("-" * 60)
        
        # Wait for processes
        try:
            while True:
                # Check if processes are still running
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        service_name = "Backend" if i == 0 else "Frontend"
                        self._print(f"\n⚠️", "WARN", f"{service_name} process has stopped")
                        self.cleanup()
                        return 1
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            self._print("\n\n🔄", "INTERRUPT", "Received interrupt signal")
        
        self.cleanup()
        return 0


def run_diagnostic():
    """Run diagnostic checks to help identify issues."""
    print("=" * 60)
    print("NETRA AI DEVELOPMENT LAUNCHER - DIAGNOSTIC MODE")
    print("=" * 60)
    
    print("\n1. ENVIRONMENT INFO:")
    print(f"   Python Version: {sys.version}")
    print(f"   Python Executable: {sys.executable}")
    print(f"   Platform: {sys.platform}")
    print(f"   Current Directory: {Path.cwd()}")
    print(f"   Script Location: {Path(__file__).resolve()}")
    
    print("\n2. PROJECT STRUCTURE:")
    project_root = get_project_root()
    print(f"   Detected Project Root: {project_root}")
    print(f"   Project Root Exists: {project_root.exists()}")
    
    # Check key directories
    dirs_to_check = ['frontend', 'app', 'scripts', 'alembic', 'terraform-gcp']
    print("\n   Key Directories:")
    for dir_name in dirs_to_check:
        dir_path = project_root / dir_name
        # Use safe characters for Windows console
        status = "[OK]" if dir_path.exists() else "[MISSING]"
        print(f"     {status} {dir_name}: {dir_path.exists()}")
    
    # Check key files
    files_to_check = ['requirements.txt', 'run_server.py', 'package.json', 'CLAUDE.md']
    print("\n   Key Files:")
    for file_name in files_to_check:
        file_path = project_root / file_name
        status = "[OK]" if file_path.exists() else "[MISSING]"
        print(f"     {status} {file_name}: {file_path.exists()}")
    
    print("\n3. FRONTEND STATUS:")
    frontend_dir = resolve_path("frontend")
    if frontend_dir and frontend_dir.exists():
        print(f"   Frontend Directory: {frontend_dir}")
        package_json = frontend_dir / "package.json"
        node_modules = frontend_dir / "node_modules"
        print(f"   package.json exists: {package_json.exists()}")
        print(f"   node_modules exists: {node_modules.exists()}")
        if node_modules.exists():
            try:
                module_count = len(list(node_modules.iterdir()))
                print(f"   node_modules count: {module_count}")
            except:
                print("   node_modules count: Unable to count")
    else:
        print("   Frontend directory not found!")
    
    print("\n4. BACKEND STATUS:")
    run_server = resolve_path("run_server.py")
    if run_server and run_server.exists():
        print(f"   run_server.py: {run_server}")
    else:
        print("   run_server.py not found!")
    
    # Check Python packages
    print("\n   Python Packages:")
    packages = ['fastapi', 'uvicorn', 'sqlalchemy', 'pydantic']
    for package in packages:
        try:
            __import__(package)
            print(f"     [OK] {package} installed")
        except ImportError:
            print(f"     [MISSING] {package} NOT installed")
    
    print("\n5. PATH RESOLUTION TEST:")
    test_paths = [
        ("frontend",),
        ("frontend", "package.json"),
        ("run_server.py",),
        ("scripts", "service_discovery.py"),
        (".env",),
    ]
    for path_parts in test_paths:
        resolved = resolve_path(*path_parts)
        exists = resolved.exists() if resolved else False
        status = "[OK]" if exists else "[MISSING]"
        print(f"   {status} {'/'.join(path_parts)}: {resolved if resolved else 'Not found'}")
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print("\nIf you see issues above, please:")
    print("1. Ensure you're in the correct directory")
    print("2. Run 'pip install -r requirements.txt' for backend deps")
    print("3. Run 'cd frontend && npm install' for frontend deps")
    print("4. Check that all project files are present")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified development launcher for Netra AI platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RECOMMENDED FOR FIRST-TIME DEVELOPERS:
  python dev_launcher.py --dynamic --no-backend-reload --load-secrets
  
  This configuration provides:
    • Automatic port allocation (no conflicts)
    • 30-50% faster performance
    • Secure secret loading from cloud
    • Auto-launches browser when ready

Examples:
  python dev_launcher.py --dynamic --no-backend-reload  # Best for most developers
  python dev_launcher.py                    # Start with defaults
  python dev_launcher.py --dynamic          # Auto port allocation
  python dev_launcher.py --no-reload        # Maximum performance (no hot reload)
  python dev_launcher.py --no-frontend-reload  # Frontend dev server without hot reload
  python dev_launcher.py --no-browser       # Don't open browser automatically
  python dev_launcher.py --load-secrets --project-id my-project  # With GCP secrets
  python dev_launcher.py --verbose          # Detailed output
        """
    )
    
    parser.add_argument(
        "--backend-port",
        type=int,
        help="Backend server port (default: 8000 or dynamic)"
    )
    
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=3000,
        help="Frontend server port (default: 3000)"
    )
    
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="Use dynamic port allocation for backend"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    
    parser.add_argument(
        "--no-backend-reload",
        action="store_true",
        help="Disable backend hot reload (file watching)"
    )
    
    parser.add_argument(
        "--no-frontend-reload",
        action="store_true",
        help="Disable frontend hot reload while keeping dev server (no file watching)"
    )
    
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable all hot reload for both frontend and backend"
    )
    
    parser.add_argument(
        "--load-secrets",
        action="store_true",
        help="Load secrets from Google Cloud Secret Manager before starting"
    )
    
    parser.add_argument(
        "--project-id",
        type=str,
        help="Google Cloud project ID for secret loading (or set GOOGLE_CLOUD_PROJECT env var)"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open the browser automatically after frontend is ready"
    )
    
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Run diagnostic checks to identify configuration issues"
    )
    
    args = parser.parse_args()
    
    # Run diagnostic mode if requested
    if args.diagnostic:
        run_diagnostic()
        return 0
    
    # Handle reload flags
    backend_reload = not args.no_backend_reload and not args.no_reload
    frontend_reload = not args.no_frontend_reload and not args.no_reload
    
    launcher = DevLauncher(
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        dynamic_ports=args.dynamic,
        verbose=args.verbose,
        backend_reload=backend_reload,
        frontend_reload=frontend_reload,
        load_secrets=args.load_secrets,
        project_id=args.project_id,
        no_browser=args.no_browser
    )
    
    sys.exit(launcher.run())


if __name__ == "__main__":
    main()