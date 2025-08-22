#!/usr/bin/env python3
"""
Service management for DevLauncher.
Handles backend and frontend service startup and management.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from .dev_launcher_config import (
    get_free_port,
    print_with_emoji_fallback,
    resolve_path,
    setup_environment_variables,
    setup_frontend_environment,
)
from .dev_launcher_processes import (
    LogStreamer,
    create_backend_process,
    create_frontend_process,
)


class ServiceManager:
    """Manages backend and frontend service operations."""
    
    def __init__(self, launcher) -> None:
        """Initialize with reference to main launcher."""
        self.launcher = launcher
        self.use_emoji = launcher.use_emoji
    
    def _print(self, emoji: str, text: str, message: str) -> None:
        """Print with emoji if supported, otherwise with text prefix."""
        print_with_emoji_fallback(emoji, text, message, self.use_emoji)
    
    def start_backend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the backend server with real-time log streaming."""
        self._print("\n[START]", "LAUNCH", "Starting backend server...")
        
        # Determine port
        port = self._get_backend_port()
        
        # Build command
        server_script = self._get_server_script()
        if not server_script:
            return None, None
        
        cmd = self._build_backend_command(server_script, port)
        
        return self._start_backend_process(cmd, port)
    
    def _get_backend_port(self) -> int:
        """Get backend port (dynamic or configured)."""
        if self.launcher.dynamic_ports:
            port = get_free_port()
            print(f"   Allocated port: {port}")
        else:
            port = self.launcher.backend_port or 8000
        
        # Store port for later use
        self.launcher.backend_port = port
        return port
    
    def _get_server_script(self) -> Optional[Path]:
        """Get the server script path."""
        run_server_enhanced = resolve_path("scripts", "run_server_enhanced.py")
        run_server_path = resolve_path("scripts", "run_server.py")
        
        if run_server_enhanced and run_server_enhanced.exists():
            print("   Using enhanced server with health monitoring")
            return run_server_enhanced
        elif run_server_path and run_server_path.exists():
            return run_server_path
        else:
            self._print("❌", "ERROR", "Could not find run_server.py")
            return None
    
    def _build_backend_command(self, server_script: Path, port: int) -> list:
        """Build backend command with appropriate flags."""
        cmd = [sys.executable, str(server_script), "--port", str(port)]
        
        # Add reload flag
        if not self.launcher.backend_reload:
            cmd.append("--no-reload")
            print("   Hot reload: DISABLED")
        else:
            print("   Hot reload: ENABLED")
        
        # Add verbose flag if requested
        if self.launcher.verbose:
            cmd.append("--verbose")
            print(f"   Command: {' '.join(cmd)}")
        
        return cmd
    
    def _start_backend_process(self, cmd: list, port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the backend process."""
        try:
            # Set environment
            env = setup_environment_variables(port)
            
            # Start process
            process = create_backend_process(cmd, env)
            
            # Start log streamer with color
            log_streamer = LogStreamer(process, "BACKEND", "\033[36m")  # Cyan color
            log_streamer.start()
            
            return self._finalize_backend_startup(process, log_streamer, port)
            
        except Exception as e:
            self._print("❌", "ERROR", f"Failed to start backend: {e}")
            return None, None
    
    def _finalize_backend_startup(self, process: subprocess.Popen, 
                                 log_streamer: LogStreamer, port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Finalize backend startup."""
        # Wait a moment for the server to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is not None:
            self._print("❌", "ERROR", "Backend failed to start")
            return None, None
        
        # Write service discovery info
        self.launcher.service_discovery.write_backend_info(port)
        
        self._print("[OK]", "OK", f"Backend started on port {port}")
        print(f"   API URL: http://localhost:{port}")
        print(f"   WebSocket URL: ws://localhost:{port}/ws")
        
        return process, log_streamer
    
    def start_frontend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the frontend server with real-time log streaming."""
        self._print("\n[START]", "LAUNCH", "Starting frontend server...")
        
        # Read backend info from service discovery
        backend_info = self.launcher.service_discovery.read_backend_info()
        if not backend_info:
            self._print("❌", "ERROR", "Backend service discovery not found. Backend may not be running.")
            return None, None
        
        # Get port and paths
        port = self._get_frontend_port()
        frontend_path = self._get_frontend_path()
        if not frontend_path:
            return None, None
        
        cmd = self._build_frontend_command(frontend_path)
        
        return self._start_frontend_process(cmd, frontend_path, backend_info, port)
    
    def _get_frontend_port(self) -> int:
        """Get frontend port (dynamic or configured)."""
        if self.launcher.dynamic_ports:
            port = get_free_port()
            print(f"   Allocated port: {port}")
            # Update the frontend_port to the actual allocated port
            self.launcher.frontend_port = port
        else:
            port = self.launcher.frontend_port
        
        return port
    
    def _get_frontend_path(self) -> Optional[Path]:
        """Get frontend directory path."""
        frontend_path = resolve_path("frontend")
        if not frontend_path or not frontend_path.exists():
            self._print("❌", "ERROR", "Frontend directory not found")
            return None
        return frontend_path
    
    def _build_frontend_command(self, frontend_path: Path) -> list:
        """Build frontend command."""
        # Check if start_with_discovery.js exists
        start_script = frontend_path / "scripts" / "start_with_discovery.js"
        
        npm_command = "dev"
        if self.launcher.use_turbopack:
            print("   Using Turbopack (experimental)")
        
        if start_script.exists():
            cmd = ["node", "scripts/start_with_discovery.js", npm_command]
        else:
            npm_executable = "npm.cmd" if sys.platform == "win32" else "npm"
            cmd = [npm_executable, "run", npm_command]
        
        if self.launcher.verbose:
            print(f"   Command: {' '.join(cmd)}")
            print(f"   Working directory: {frontend_path}")
        
        return cmd
    
    def _start_frontend_process(self, cmd: list, frontend_path: Path, 
                               backend_info: dict, port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the frontend process."""
        try:
            # Set environment with backend URLs
            env = setup_frontend_environment(
                backend_info, port, self.launcher.frontend_reload
            )
            
            # Configure hot reload logging
            if not self.launcher.frontend_reload:
                print("   Hot reload: DISABLED")
            else:
                print("   Hot reload: ENABLED")
            
            # Start process
            process = create_frontend_process(cmd, str(frontend_path), env)
            
            return self._finalize_frontend_startup(process, port)
            
        except Exception as e:
            self._print("❌", "ERROR", f"Failed to start frontend: {e}")
            return None, None
    
    def _finalize_frontend_startup(self, process: subprocess.Popen, 
                                  port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Finalize frontend startup."""
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
        self.launcher.service_discovery.write_frontend_info(port)
        
        return process, log_streamer