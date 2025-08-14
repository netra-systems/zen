#!/usr/bin/env python3
"""
Core DevLauncher class and main entry point.
Unified launcher with real-time streaming, monitoring, and enhanced secret loading.
"""

import sys
import time
import signal
from pathlib import Path
from typing import Optional

from .dev_launcher_config import (
    get_project_root, check_emoji_support, 
    validate_dependencies, validate_frontend_directory, import_service_discovery,
    print_with_emoji_fallback
)
from .dev_launcher_processes import (
    ProcessMonitor, cleanup_process
)
from .dev_launcher_secrets import EnhancedSecretLoader
from .dev_launcher_monitoring import (
    validate_backend_health, validate_frontend_health, 
    print_service_summary, print_configuration_summary,
    monitor_processes_loop, open_browser
)
from .dev_launcher_service import ServiceManager


class DevLauncher:
    """Unified launcher with real-time streaming, monitoring, and enhanced secret loading."""
    
    def __init__(self, backend_port: Optional[int] = None, 
                 frontend_port: Optional[int] = None,
                 dynamic_ports: bool = False,
                 verbose: bool = False,
                 backend_reload: bool = True,
                 frontend_reload: bool = True,
                 load_secrets: bool = True,
                 project_id: Optional[str] = None,
                 no_browser: bool = False,
                 auto_restart: bool = True,
                 use_turbopack: bool = False) -> None:
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
        self._initialize_components()
        
    def _initialize_components(self) -> None:
        """Initialize launcher components."""
        ServiceDiscovery = import_service_discovery()
        self.service_discovery = ServiceDiscovery()
        self.use_emoji = check_emoji_support()
        self.project_root = get_project_root()
        self.service_manager = ServiceManager(self)
        self._setup_process_tracking()
        self._setup_signal_handlers()
        
    def _setup_process_tracking(self) -> None:
        """Setup process and monitor tracking."""
        self.backend_monitor = None
        self.frontend_monitor = None
        self.backend_process = None
        self.backend_streamer = None
        self.frontend_process = None
        self.frontend_streamer = None
        
        if self.verbose:
            self._print_debug_info()
    
    def _print_debug_info(self) -> None:
        """Print debug information if verbose mode enabled."""
        print(f"Project root detected: {self.project_root}")
        print(f"Current working directory: {Path.cwd()}")
        print(f"Script location: {Path(__file__).resolve()}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for cleanup."""
        signal.signal(signal.SIGINT, self._cleanup_handler)
        signal.signal(signal.SIGTERM, self._cleanup_handler)
        
        # Windows-specific signal
        if sys.platform == "win32":
            signal.signal(signal.SIGBREAK, self._cleanup_handler)
    
    def _print(self, emoji: str, text: str, message: str) -> None:
        """Print with emoji if supported, otherwise with text prefix."""
        print_with_emoji_fallback(emoji, text, message, self.use_emoji)
    
    def _cleanup_handler(self, signum, frame) -> None:
        """Handle cleanup on exit."""
        self._print("[STOP]", "STOP", "\nShutting down development environment...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self) -> None:
        """Clean up all running processes."""
        if self.backend_monitor:
            self.backend_monitor.stop()
        else:
            cleanup_process(self.backend_process, self.backend_streamer)
        
        if self.frontend_monitor:
            self.frontend_monitor.stop()
        else:
            cleanup_process(self.frontend_process, self.frontend_streamer)
        
        # Clear service discovery
        self.service_discovery.clear_all()
        self._print("[OK]", "OK", "Cleanup complete")
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available."""
        errors = validate_dependencies()
        errors.extend(validate_frontend_directory())
        
        if errors:
            print("Dependency check failed:")
            for error in errors:
                print(f"  {error}")
            return False
        
        self._print("[OK]", "OK", "All dependencies satisfied")
        return True
    
    def start_backend(self):
        """Start the backend server via service manager."""
        return self.service_manager.start_backend()
    
    def start_frontend(self):
        """Start the frontend server via service manager."""
        return self.service_manager.start_frontend()
    
    def run(self) -> int:
        """Run the development environment with enhanced monitoring."""
        print("=" * 60)
        self._print("[LAUNCH]", "LAUNCH", "Netra AI Development Environment")
        print("=" * 60)
        
        # Show configuration summary
        print_configuration_summary(
            self.dynamic_ports, self.backend_reload, self.frontend_reload,
            self.auto_restart, self.use_turbopack, self.load_secrets
        )
        
        # Check dependencies
        if not self.check_dependencies():
            self._print("\n❌", "ERROR", "Please install missing dependencies and try again")
            return 1
        
        # Load secrets (default in dev mode)
        if self.load_secrets:
            secret_loader = EnhancedSecretLoader(self.project_id, self.verbose)
            secret_loader.load_all_secrets()
        
        return self._run_services()
    
    def _run_services(self) -> int:
        """Run backend and frontend services."""
        # Clear old service discovery
        self.service_discovery.clear_all()
        
        # Start backend
        if not self._start_backend_service():
            return 1
        
        # Wait for backend to be ready and start frontend
        backend_info = self.service_discovery.read_backend_info()
        validate_backend_health(backend_info, timeout=30)
        
        # Start frontend
        if not self._start_frontend_service():
            return 1
        
        return self._monitor_services()
    
    def _start_backend_service(self) -> bool:
        """Start backend service with or without monitoring."""
        if self.auto_restart:
            self.backend_monitor = ProcessMonitor(
                "Backend", self.start_backend, restart_delay=5,
                max_restarts=3, color_code="\033[36m"
            )
            
            if not self.backend_monitor.start():
                self._print("❌", "ERROR", "Failed to start backend")
                self.cleanup()
                return False
        else:
            self.backend_process, self.backend_streamer = self.start_backend()
            if not self.backend_process:
                self._print("❌", "ERROR", "Failed to start backend")
                self.cleanup()
                return False
        
        return True
    
    def _start_frontend_service(self) -> bool:
        """Start frontend service with or without monitoring."""
        if self.auto_restart:
            self.frontend_monitor = ProcessMonitor(
                "Frontend", self.start_frontend, restart_delay=5,
                max_restarts=3, color_code="\033[35m"
            )
            
            if not self.frontend_monitor.start():
                self._print("❌", "ERROR", "Failed to start frontend")
                self.cleanup()
                return False
        else:
            self.frontend_process, self.frontend_streamer = self.start_frontend()
            if not self.frontend_process:
                self._print("❌", "ERROR", "Failed to start frontend")
                self.cleanup()
                return False
        
        return True
    
    def _monitor_services(self) -> int:
        """Monitor services and handle frontend readiness."""
        # Wait for frontend to be ready
        frontend_ready = validate_frontend_health(self.frontend_port, timeout=90)
        
        # Automatically open browser when frontend is ready
        if frontend_ready and not self.no_browser:
            open_browser(f"http://localhost:{self.frontend_port}")
        
        # Print summary
        backend_info = self.service_discovery.read_backend_info()
        print_service_summary(backend_info, self.frontend_port, self.auto_restart)
        
        # Wait for processes
        return self._wait_for_processes()
    
    def _wait_for_processes(self) -> int:
        """Wait for processes to complete or handle interruption."""
        try:
            while True:
                if not monitor_processes_loop(
                    self.backend_process, self.frontend_process,
                    self.backend_monitor, self.frontend_monitor,
                    self.auto_restart
                ):
                    self.cleanup()
                    return 1
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            self._print("\n\n[INTERRUPT]", "INTERRUPT", "Received interrupt signal")
        
        self.cleanup()
        return 0