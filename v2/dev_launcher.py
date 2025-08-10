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
                 frontend_reload: bool = True):
        """Initialize the development launcher."""
        self.backend_port = backend_port
        self.frontend_port = frontend_port or 3000
        self.dynamic_ports = dynamic_ports
        self.verbose = verbose
        self.backend_reload = backend_reload
        self.frontend_reload = frontend_reload
        self.processes: List[subprocess.Popen] = []
        self.service_discovery = ServiceDiscovery()
        
        # Register cleanup handler
        signal.signal(signal.SIGINT, self._cleanup_handler)
        signal.signal(signal.SIGTERM, self._cleanup_handler)
        
        # Windows-specific signal
        if sys.platform == "win32":
            signal.signal(signal.SIGBREAK, self._cleanup_handler)
    
    def get_free_port(self) -> int:
        """Get a free port by binding to port 0."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def _cleanup_handler(self, signum, frame):
        """Handle cleanup on exit."""
        print("\n🛑 Shutting down development environment...")
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
        print("✅ Cleanup complete")
    
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
        
        print("✅ All dependencies satisfied")
        return True
    
    def start_backend(self) -> Optional[subprocess.Popen]:
        """Start the backend server."""
        print("\n🚀 Starting backend server...")
        
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
                print("❌ Backend failed to start")
                return None
            
            print(f"✅ Backend started on port {port}")
            print(f"   API URL: http://localhost:{port}")
            print(f"   WebSocket URL: ws://localhost:{port}/ws")
            
            return process
            
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return None
    
    def start_frontend(self) -> Optional[subprocess.Popen]:
        """Start the frontend server."""
        print("\n🚀 Starting frontend server...")
        
        # Read backend info from service discovery
        backend_info = self.service_discovery.read_backend_info()
        if not backend_info:
            print("❌ Backend service discovery not found. Backend may not be running.")
            return None
        
        # Determine the npm command based on reload setting
        npm_command = "dev" if self.frontend_reload else "start"
        
        # Build command based on OS
        if sys.platform == "win32":
            # Windows
            cmd = ["cmd", "/c", "cd", "frontend", "&&", "node", "scripts/start_with_discovery.js", npm_command]
        else:
            # Unix-like
            cmd = ["sh", "-c", f"cd frontend && node scripts/start_with_discovery.js {npm_command}"]
        
        if self.verbose:
            print(f"   Command: {' '.join(cmd)}")
        
        # Set environment with backend URLs
        env = os.environ.copy()
        env["NEXT_PUBLIC_API_URL"] = backend_info["api_url"]
        env["NEXT_PUBLIC_WS_URL"] = backend_info["ws_url"]
        env["PORT"] = str(self.frontend_port)
        
        # Start process
        try:
            if sys.platform == "win32":
                # Windows: create new process group
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Unix: create new process group
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    shell=True,
                    preexec_fn=os.setsid
                )
            
            # Wait for frontend to start
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is not None:
                print("❌ Frontend failed to start")
                return None
            
            print(f"✅ Frontend started on port {self.frontend_port}")
            print(f"   URL: http://localhost:{self.frontend_port}")
            print(f"   Hot reload: {'ENABLED' if self.frontend_reload else 'DISABLED'}")
            
            # Write frontend info to service discovery
            self.service_discovery.write_frontend_info(self.frontend_port)
            
            return process
            
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return None
    
    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        """Wait for a service to become available."""
        import urllib.request
        import urllib.error
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status == 200:
                        return True
            except (urllib.error.URLError, ConnectionError):
                time.sleep(1)
        
        return False
    
    def run(self):
        """Run the development environment."""
        print("=" * 60)
        print("🚀 Netra AI Development Environment Launcher")
        print("=" * 60)
        
        # Check dependencies
        if not self.check_dependencies():
            print("\n❌ Please install missing dependencies and try again")
            return 1
        
        # Clear old service discovery
        self.service_discovery.clear_all()
        
        # Start backend
        backend_process = self.start_backend()
        if not backend_process:
            print("❌ Failed to start backend")
            self.cleanup()
            return 1
        
        self.processes.append(backend_process)
        
        # Wait for backend to be ready
        backend_info = self.service_discovery.read_backend_info()
        if backend_info:
            print("\n⏳ Waiting for backend to be ready...")
            backend_url = f"{backend_info['api_url']}/api/health"
            if self.wait_for_service(backend_url, timeout=30):
                print("✅ Backend is ready")
            else:
                print("⚠️  Backend health check timed out, continuing anyway...")
        
        # Start frontend
        frontend_process = self.start_frontend()
        if not frontend_process:
            print("❌ Failed to start frontend")
            self.cleanup()
            return 1
        
        self.processes.append(frontend_process)
        
        # Wait for frontend to be ready
        print("\n⏳ Waiting for frontend to be ready...")
        frontend_url = f"http://localhost:{self.frontend_port}"
        if self.wait_for_service(frontend_url, timeout=60):
            print("✅ Frontend is ready")
        else:
            print("⚠️  Frontend readiness check timed out")
        
        # Print summary
        print("\n" + "=" * 60)
        print("✨ Development environment is running!")
        print("=" * 60)
        
        if backend_info:
            print(f"\n📡 Backend:")
            print(f"   API: {backend_info['api_url']}")
            print(f"   WebSocket: {backend_info['ws_url']}")
        
        print(f"\n🌐 Frontend:")
        print(f"   URL: http://localhost:{self.frontend_port}")
        
        print("\n📝 Service Discovery:")
        print(f"   Info stored in: .netra/")
        
        print("\n⌨️  Commands:")
        print("   Press Ctrl+C to stop all services")
        print("   Run 'python scripts/service_discovery.py status' to check service status")
        
        print("\n📊 Logs:")
        print("   Backend and frontend logs will appear here")
        print("-" * 60)
        
        # Wait for processes
        try:
            while True:
                # Check if processes are still running
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        service_name = "Backend" if i == 0 else "Frontend"
                        print(f"\n⚠️  {service_name} process has stopped")
                        self.cleanup()
                        return 1
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\nReceived interrupt signal")
        
        self.cleanup()
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Unified development launcher for Netra AI platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dev_launcher.py                    # Start with default ports and hot reload
  python dev_launcher.py --dynamic          # Use dynamic port allocation
  python dev_launcher.py --backend-port 8080  # Specify backend port
  python dev_launcher.py --no-backend-reload  # Disable backend hot reload
  python dev_launcher.py --no-frontend-reload # Disable frontend hot reload
  python dev_launcher.py --no-reload        # Disable all hot reload
  python dev_launcher.py --verbose          # Show detailed output
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
        frontend_reload=frontend_reload
    )
    
    sys.exit(launcher.run())


if __name__ == "__main__":
    main()