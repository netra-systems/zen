"""Service discovery utilities for development environment."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

class ServiceDiscovery:
    """Manages service discovery for development environment."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize service discovery manager."""
        # Find project root (parent of scripts directory)
        if base_dir is None:
            current_file = Path(__file__).resolve()
            if current_file.parent.name == 'scripts':
                project_root = current_file.parent.parent
            else:
                project_root = current_file.parent
            base_dir = project_root / ".netra"
        
        self.base_dir = base_dir
        self.base_dir.mkdir(exist_ok=True)
    
    def read_backend_info(self) -> Optional[Dict[str, Any]]:
        """Read backend service information."""
        backend_file = self.base_dir / "backend.json"
        if backend_file.exists():
            with open(backend_file, 'r') as f:
                return json.load(f)
        return None
    
    def write_backend_info(self, port: int, host: str = "localhost") -> Dict[str, Any]:
        """Write backend service information."""
        info = {
            "host": host,
            "port": port,
            "api_url": f"http://{host}:{port}",
            "ws_url": f"ws://{host}:{port}/ws",
            "pid": os.getpid()
        }
        
        backend_file = self.base_dir / "backend.json"
        with open(backend_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        return info
    
    def read_frontend_info(self) -> Optional[Dict[str, Any]]:
        """Read frontend service information."""
        frontend_file = self.base_dir / "frontend.json"
        if frontend_file.exists():
            with open(frontend_file, 'r') as f:
                return json.load(f)
        return None
    
    def write_frontend_info(self, port: int, host: str = "localhost") -> Dict[str, Any]:
        """Write frontend service information."""
        info = {
            "host": host,
            "port": port,
            "url": f"http://{host}:{port}",
            "pid": os.getpid()
        }
        
        frontend_file = self.base_dir / "frontend.json"
        with open(frontend_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        return info
    
    def get_all_services(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get information for all registered services."""
        return {
            "backend": self.read_backend_info(),
            "frontend": self.read_frontend_info()
        }
    
    def clear_all(self):
        """Clear all service discovery information."""
        for file in self.base_dir.glob("*.json"):
            file.unlink()
    
    def is_service_running(self, service_name: str) -> bool:
        """Check if a service is running by checking its process."""
        info = None
        if service_name == "backend":
            info = self.read_backend_info()
        elif service_name == "frontend":
            info = self.read_frontend_info()
        
        if not info or "pid" not in info:
            return False
        
        # Check if process is still running
        try:
            import psutil
            return psutil.pid_exists(info["pid"])
        except ImportError:
            # Fallback method if psutil is not available
            import platform
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {info['pid']}"],
                    capture_output=True,
                    text=True
                )
                return str(info['pid']) in result.stdout
            else:
                # Unix-like systems
                try:
                    os.kill(info['pid'], 0)
                    return True
                except OSError:
                    return False


if __name__ == "__main__":
    # Command-line interface for service discovery
    import argparse
    
    parser = argparse.ArgumentParser(description="Service discovery utilities")
    parser.add_argument("action", choices=["get", "clear", "status"],
                       help="Action to perform")
    parser.add_argument("--service", choices=["backend", "frontend", "all"],
                       default="all", help="Service to query")
    
    args = parser.parse_args()
    
    sd = ServiceDiscovery()
    
    if args.action == "get":
        if args.service == "all":
            services = sd.get_all_services()
            print(json.dumps(services, indent=2))
        elif args.service == "backend":
            info = sd.read_backend_info()
            if info:
                print(json.dumps(info, indent=2))
            else:
                print("Backend service not found")
        elif args.service == "frontend":
            info = sd.read_frontend_info()
            if info:
                print(json.dumps(info, indent=2))
            else:
                print("Frontend service not found")
    
    elif args.action == "clear":
        sd.clear_all()
        print("Service discovery information cleared")
    
    elif args.action == "status":
        services = {"backend": "backend", "frontend": "frontend"}
        if args.service != "all":
            services = {args.service: args.service}
        
        for name, service in services.items():
            running = sd.is_service_running(service)
            status = "running" if running else "not running"
            print(f"{name}: {status}")