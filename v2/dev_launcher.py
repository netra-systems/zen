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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.service_discovery import ServiceDiscovery

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
            # Check if fetch_secrets_to_env.py exists
            fetch_script = Path("fetch_secrets_to_env.py")
            if not fetch_script.exists():
                errors.append("❌ fetch_secrets_to_env.py not found in project root")
            
            # Check for project ID
            if not self.project_id and not os.environ.get('GOOGLE_CLOUD_PROJECT'):
                errors.append("❌ Google Cloud project ID not specified. Use --project-id or set GOOGLE_CLOUD_PROJECT env var")
        
        # Check if frontend directory exists
        frontend_dir = Path("frontend")
        if not frontend_dir.exists():
            errors.append("❌ Frontend directory not found")
        else:
            # Check if node_modules exists
            node_modules = frontend_dir / "node_modules"
            if not node_modules.exists():
                errors.append("❌ Frontend dependencies not installed. Run: cd frontend && npm install")
        
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
        cmd = [
            sys.executable,
            "run_server.py",
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
        
        # Determine the npm command based on reload setting
        npm_command = "dev" if self.frontend_reload else "start"
        
        # If production mode (no hot reload), build the frontend first
        if not self.frontend_reload:
            self._print("🔨", "BUILD", "Building frontend for production mode...")
            
            # Prepare environment for build
            build_env = os.environ.copy()
            build_env["NEXT_PUBLIC_API_URL"] = backend_info["api_url"]
            build_env["NEXT_PUBLIC_WS_URL"] = backend_info["ws_url"]
            
            # Use appropriate command for Windows vs Unix
            if sys.platform == "win32":
                build_cmd = ["cmd", "/c", "npm run build"]
            else:
                build_cmd = ["npm", "run", "build"]
            
            try:
                # Change to frontend directory and run build
                print("   This may take a few minutes for the first build...")
                build_result = subprocess.run(
                    build_cmd,
                    cwd="frontend",
                    env=build_env,
                    capture_output=True,
                    text=True,
                    shell=(sys.platform == "win32")  # Use shell on Windows for npm
                )
                
                if build_result.returncode == 0:
                    self._print("✅", "OK", "Frontend build completed successfully")
                else:
                    self._print("❌", "ERROR", f"Frontend build failed: {build_result.stderr}")
                    return None
                    
            except Exception as e:
                self._print("❌", "ERROR", f"Failed to build frontend: {e}")
                return None
        
        # Build command based on OS - avoid shell=True with arguments to prevent deprecation warning
        if sys.platform == "win32":
            # Windows - use node directly without shell
            cmd = ["node", "scripts/start_with_discovery.js", npm_command]
            cwd_path = "frontend"
        else:
            # Unix-like - use node directly without shell
            cmd = ["node", "scripts/start_with_discovery.js", npm_command]
            cwd_path = "frontend"
        
        if self.verbose:
            print(f"   Command: {' '.join(cmd)}")
            print(f"   Working directory: {cwd_path}")
        
        # Set environment with backend URLs
        env = os.environ.copy()
        env["NEXT_PUBLIC_API_URL"] = backend_info["api_url"]
        env["NEXT_PUBLIC_WS_URL"] = backend_info["ws_url"]
        env["PORT"] = str(port)
        
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
            print(f"   Hot reload: {'ENABLED' if self.frontend_reload else 'DISABLED'}")
            
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
            cmd = [sys.executable, "fetch_secrets_to_env.py"]
            
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
                env_file = Path(".env")
                if env_file.exists():
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
        
        # Show configuration summary
        if self.dynamic_ports and not self.backend_reload:
            self._print("\n🎆", "RECOMMENDED", "Running with RECOMMENDED configuration:")
            print("   * Dynamic ports: YES (avoiding conflicts)")
            print("   * Backend hot reload: NO (30-50% faster)")
            if self.load_secrets:
                print("   * Secret loading: YES (from Google Cloud)")
            print("   Perfect for first-time setup!\n")
        elif self.dynamic_ports:
            self._print("\n📝", "Configuration", ":")
            print("   * Dynamic ports: YES")
            print("   * Hot reload: YES (development mode)\n")
        
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
  python dev_launcher.py --no-reload        # Maximum performance
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
        help="Disable frontend hot reload (file watching)"
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
    
    args = parser.parse_args()
    
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