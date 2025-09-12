"""
Frontend service startup management.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from dev_launcher.config import LauncherConfig, resolve_path
from shared.isolated_environment import get_env
from dev_launcher.log_streamer import Colors, LogManager, LogStreamer
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.utils import (
    create_process_env,
    create_subprocess,
    get_free_port,
    print_with_emoji,
)

# Import process tracking for cleanup
try:
    from shared.enhanced_process_cleanup import track_subprocess
except ImportError:
    track_subprocess = lambda p: None

logger = logging.getLogger(__name__)


class FrontendStarter:
    """
    Handles frontend service startup.
    
    Manages frontend server startup with proper configuration,
    environment setup, and error handling.
    """
    
    def __init__(self, config: LauncherConfig, services_config, 
                 log_manager: LogManager, service_discovery: ServiceDiscovery,
                 use_emoji: bool = True):
        """Initialize frontend starter."""
        self.config = config
        self.services_config = services_config
        self.log_manager = log_manager
        self.service_discovery = service_discovery
        self.use_emoji = use_emoji
        self.frontend_health_info = None
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def start_frontend(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the frontend server with proper error handling and environment loading wait."""
        # Wait for environment loading to complete before starting frontend
        self._wait_for_environment_loading()
        
        self._print("[U+1F680]", "FRONTEND", "Starting frontend server...")
        startup_params = self._prepare_frontend_startup()
        if not startup_params:
            # Only show detailed errors after environment is fully loaded
            self._handle_frontend_preparation_failure()
            return None, None
        backend_info, port, frontend_path = startup_params
        return self._start_frontend_process(backend_info, port, frontend_path)
    
    def _handle_frontend_preparation_failure(self):
        """Handle frontend preparation failure with appropriate error messages."""
        import os
        from dev_launcher.config import resolve_path
        
        # Only show errors if environment loading is complete
        env = get_env()
        if env.get('NETRA_SECRETS_LOADING') == 'true':
            logger.debug("Frontend preparation failed during environment loading - deferring error display")
            return
        
        # Check specific failure reasons and provide helpful messages
        backend_info = self.service_discovery.read_backend_info()
        frontend_path = resolve_path("frontend", root=self.config.project_root)
        
        if not backend_info:
            self._print(" FAIL: ", "ERROR", "Backend service not available - ensure backend is running")
            logger.info("Hint: Start backend service first or check service discovery")
        
        if not frontend_path or not frontend_path.exists():
            self._print(" FAIL: ", "ERROR", f"Frontend directory not found: {frontend_path}")
            logger.info("Hint: Ensure you're running from the project root directory")
    
    def _prepare_frontend_startup(self) -> Optional[Tuple[Dict, int, Path]]:
        """Prepare frontend startup parameters."""
        backend_info = self._get_backend_info()
        if not backend_info:
            return None
        port = self._determine_frontend_port()
        frontend_path = self._get_frontend_path()
        if not frontend_path:
            return None
        return backend_info, port, frontend_path
    
    def _wait_for_environment_loading(self) -> None:
        """Wait for environment loading to complete to prevent premature error display."""
        import os
        import time
        
        # Check if environment is still being loaded
        max_wait = 5.0  # Maximum wait time in seconds
        wait_interval = 0.1
        waited = 0.0
        
        env = get_env()
        while env.get('NETRA_SECRETS_LOADING') == 'true' and waited < max_wait:
            time.sleep(wait_interval)
            waited += wait_interval
            
        if waited > 0:
            logger.debug(f"Waited {waited:.1f}s for environment loading to complete")
    
    def _get_backend_info(self) -> Optional[Dict]:
        """Get backend service discovery info with grace period for initialization."""
        backend_info = self.service_discovery.read_backend_info()
        if not backend_info:
            # Don't immediately error - backend may still be starting up
            # This prevents premature error display during system initialization
            logger.debug("Backend service discovery not found - backend may still be initializing")
            return None
        return backend_info
    
    def _determine_frontend_port(self) -> int:
        """Determine frontend port."""
        if self.config.dynamic_ports:
            port = self._allocate_dynamic_frontend_port()
        else:
            port = self.config.frontend_port
        return port
    
    def _allocate_dynamic_frontend_port(self) -> int:
        """
        Allocate dynamic frontend port with comprehensive fallback strategy.
        
        Returns:
            Allocated port number
        """
        from dev_launcher.utils import find_available_port
        preferred_port = self.config.frontend_port or 3000
        
        try:
            # Use enhanced port allocation with extended fallback
            port = find_available_port(preferred_port, (3000, 3010), host='0.0.0.0')
            
            # Validate the allocated port is actually available
            if not self._verify_port_allocation(port):
                logger.warning(f"Allocated port {port} failed verification, trying fallback")
                # Try fallback allocation
                port = find_available_port(preferred_port + 10, (3011, 3020), host='0.0.0.0')
            
            logger.info(f"Allocated frontend port: {port}")
            self.config.frontend_port = port
            return port
            
        except Exception as e:
            logger.error(f"Failed to allocate frontend port: {e}")
            # Emergency fallback to any available port
            from dev_launcher.utils import get_free_port
            emergency_port = get_free_port()
            logger.warning(f"Emergency fallback to OS-allocated port: {emergency_port}")
            self.config.frontend_port = emergency_port
            return emergency_port
    
    def _verify_port_allocation(self, port: int) -> bool:
        """
        Verify that the allocated port is actually available.
        
        Args:
            port: Port number to verify
            
        Returns:
            True if port is available, False otherwise
        """
        try:
            import socket
            import time
            
            # Try to bind to the port briefly to ensure it's available
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('0.0.0.0', port))
                
                # Small delay on Windows for race condition prevention
                if sys.platform == "win32":
                    time.sleep(0.02)
                
                return True
                
        except OSError as e:
            logger.debug(f"Port {port} verification failed: {e}")
            return False
        except Exception as e:
            logger.debug(f"Port {port} verification error: {e}")
            return False
    
    def _get_frontend_path(self) -> Optional[Path]:
        """Get frontend path with graceful error handling."""
        frontend_path = resolve_path("frontend", root=self.config.project_root)
        if not frontend_path or not frontend_path.exists():
            # Use debug logging instead of immediate error to prevent premature display
            logger.debug(f"Frontend directory not found at expected path: {frontend_path}")
            return None
        return frontend_path
    
    def _start_frontend_process(self, backend_info: Dict, port: int, 
                               frontend_path: Path) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start frontend process."""
        cmd = self._build_frontend_command(frontend_path)
        env = self._create_frontend_env(backend_info, port)
        return self._execute_frontend_startup(cmd, env, frontend_path, port)
    
    def _build_frontend_command(self, frontend_path: Path) -> list:
        """Build frontend command."""
        start_script = frontend_path / "scripts" / "start_with_discovery.js"
        npm_command = self._get_npm_command()
        if start_script.exists():
            return ["node", "scripts/start_with_discovery.js", npm_command]
        return self._get_npm_run_command(npm_command)
    
    def _get_npm_command(self) -> str:
        """Get npm command based on configuration."""
        if self.config.use_turbopack:
            logger.info("Using Turbopack (experimental)")
        else:
            logger.info("Using standard Next.js")
        return "dev"
    
    def _get_npm_run_command(self, npm_command: str) -> list:
        """Get npm run command."""
        if sys.platform == "win32":
            return ["npm.cmd", "run", npm_command]
        return ["npm", "run", npm_command]
    
    def _create_frontend_env(self, backend_info: Dict, port: int) -> Dict:
        """Create frontend environment variables."""
        service_env_vars = self.services_config.get_all_env_vars()
        env = self._build_frontend_env_base(backend_info, port, service_env_vars)
        self._configure_frontend_reload(env)
        return env
    
    def _build_frontend_env_base(self, backend_info: Dict, port: int, 
                                service_env_vars: Dict) -> Dict:
        """Build frontend environment base."""
        return create_process_env(
            NEXT_PUBLIC_API_URL=backend_info["api_url"],
            NEXT_PUBLIC_WS_URL=backend_info["ws_url"],
            PORT=str(port),
            PYTHONPATH=str(self.config.project_root),
            # Increase Node.js memory limit to 4GB to handle large test suite and development build
            NODE_OPTIONS="--max-old-space-size=4096",
            **service_env_vars,
            **self.config.env_overrides
        )
    
    def _configure_frontend_reload(self, env: Dict):
        """Configure frontend reload settings."""
        if not self.config.frontend_reload:
            self._disable_frontend_reload(env)
        else:
            logger.info("Frontend hot reload: ENABLED")
    
    def _disable_frontend_reload(self, env: Dict):
        """Disable frontend reload."""
        env["WATCHPACK_POLLING"] = "false"
        env["NEXT_DISABLE_FAST_REFRESH"] = "true"
        logger.info("Frontend hot reload: DISABLED")
    
    def _execute_frontend_startup(self, cmd: list, env: Dict, frontend_path: Path, 
                                 port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Execute frontend startup."""
        self._log_frontend_startup_info(cmd, frontend_path)
        self._prepare_frontend_logging()
        try:
            return self._create_and_verify_frontend_process(cmd, env, frontend_path, port)
        except Exception as e:
            self._handle_frontend_startup_exception(e)
            return None, None
    
    def _log_frontend_startup_info(self, cmd: list, frontend_path: Path):
        """Log frontend startup information."""
        logger.debug(f"Frontend command: {' '.join(cmd)}")
        logger.debug(f"Frontend working directory: {frontend_path}")
    
    def _prepare_frontend_logging(self):
        """Prepare frontend logging setup."""
        self.config.log_dir.mkdir(exist_ok=True)
    
    def _create_and_verify_frontend_process(self, cmd: list, env: Dict, frontend_path: Path, 
                                           port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Create and verify frontend process."""
        process = create_subprocess(cmd, cwd=frontend_path, env=env)
        # Track the process for automatic cleanup
        track_subprocess(process)
        log_streamer = self._create_frontend_log_streamer(process)
        return self._verify_frontend_startup(process, port, log_streamer)
    
    def _handle_frontend_startup_exception(self, e: Exception):
        """Handle frontend startup exception."""
        logger.error(f"Failed to start frontend: {e}")
        self._print(" FAIL: ", "ERROR", f"Frontend startup failed: {str(e)[:100]}")
    
    def _create_frontend_log_streamer(self, process: subprocess.Popen) -> LogStreamer:
        """Create frontend log streamer."""
        return self.log_manager.add_streamer("FRONTEND", process, Colors.MAGENTA)
    
    def _verify_frontend_startup(self, process: subprocess.Popen, port: int, 
                                log_streamer: LogStreamer) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Verify frontend startup."""
        time.sleep(3)
        if process.poll() is not None:
            self._handle_frontend_startup_failure(process)
            return None, None
        self._finalize_frontend_startup(port, process)
        return process, log_streamer
    
    def _handle_frontend_startup_failure(self, process: subprocess.Popen):
        """Handle frontend startup failure with detailed error capture."""
        exit_code = process.poll()
        self._print(" FAIL: ", "ERROR", f"Frontend failed to start (exit code: {exit_code})")
        
        # Capture detailed error information
        detailed_errors = self._capture_frontend_build_errors(process)
        if detailed_errors:
            self._print("[U+1F4CB]", "DETAILS", "Frontend build errors:")
            for error in detailed_errors[:5]:  # Show max 5 most relevant errors
                print(f"   ->  {error}")
        
        self._print_frontend_troubleshooting()
    
    def _capture_frontend_build_errors(self, process: subprocess.Popen) -> list:
        """Capture detailed frontend build errors from process output and logs."""
        errors = []
        
        try:
            # Try to read from stderr if available
            if hasattr(process, 'stderr') and process.stderr:
                stderr_output = process.stderr.read()
                if stderr_output:
                    errors.extend(self._parse_frontend_errors(stderr_output.decode('utf-8', errors='ignore')))
        except Exception as e:
            logger.debug(f"Failed to read process stderr: {e}")
        
        # Try to capture errors from frontend log files
        try:
            frontend_log_path = self.config.log_dir / "frontend.log"
            if frontend_log_path.exists():
                with open(frontend_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
                    errors.extend(self._parse_frontend_errors(log_content))
        except Exception as e:
            logger.debug(f"Failed to read frontend log file: {e}")
        
        # Try to capture build errors from Next.js build output
        try:
            from dev_launcher.config import resolve_path
            frontend_path = resolve_path("frontend", root=self.config.project_root)
            if frontend_path:
                # Check for build errors in common locations
                build_log_path = frontend_path / ".next" / "trace"
                if build_log_path.exists():
                    # This is where Next.js might store build information
                    pass
                    
                # Check package.json for common script issues
                package_json_path = frontend_path / "package.json"
                if package_json_path.exists():
                    errors.extend(self._check_package_json_issues(package_json_path))
                    
        except Exception as e:
            logger.debug(f"Failed to check frontend build files: {e}")
        
        return list(set(errors))  # Remove duplicates
    
    def _parse_frontend_errors(self, output: str) -> list:
        """Parse frontend errors from output text."""
        errors = []
        lines = output.split('\n')
        
        # Common error patterns in frontend builds
        error_patterns = [
            r'Error: .+',
            r'TypeError: .+',
            r'Module not found: .+',
            r'Failed to compile .+',
            r'Syntax error: .+',
            r'npm ERR! .+',
            r'Cannot resolve .+',
            r'Module build failed: .+',
            r'Build failed .+',
        ]
        
        import re
        for line in lines:
            line = line.strip()
            if line:
                for pattern in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        errors.append(line[:200])  # Truncate very long errors
                        break
        
        return errors[:10]  # Return max 10 errors
    
    def _check_package_json_issues(self, package_json_path: Path) -> list:
        """Check for common package.json issues that could cause build failures."""
        issues = []
        
        try:
            import json
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            # Check for missing scripts
            scripts = package_data.get('scripts', {})
            if 'dev' not in scripts:
                issues.append("Missing 'dev' script in package.json")
            if 'build' not in scripts:
                issues.append("Missing 'build' script in package.json")
                
            # Check for Next.js dependency
            dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
            if 'next' not in dependencies:
                issues.append("Next.js not found in dependencies")
                
            # Check for React dependencies
            if 'react' not in dependencies:
                issues.append("React not found in dependencies")
            if 'react-dom' not in dependencies:
                issues.append("React DOM not found in dependencies")
                
        except Exception as e:
            issues.append(f"Failed to parse package.json: {e}")
            
        return issues
    
    def _print_frontend_troubleshooting(self):
        """Print frontend troubleshooting tips with enhanced diagnostics."""
        print("\nFrontend Startup Troubleshooting:")
        print("=" * 50)
        
        # Check if port was the issue
        current_port = getattr(self.config, 'frontend_port', 3000)
        print(f"[U+2022] Attempted port: {current_port}")
        
        from dev_launcher.utils import _get_process_using_port
        process_info = _get_process_using_port(current_port)
        if process_info:
            print(f"   ->  Port {current_port} is occupied by: {process_info}")
            print(f"   ->  Solution: Kill the process or use --dynamic flag for automatic port allocation")
        else:
            print(f"   ->  Port {current_port} appears available")
        
        # Check frontend directory
        try:
            from dev_launcher.config import resolve_path
            frontend_path = resolve_path("frontend", root=self.config.project_root)
            if frontend_path and frontend_path.exists():
                print(f"[U+2022] Frontend directory: [U+2713] Found at {frontend_path}")
                
                # Check for package.json
                package_json = frontend_path / "package.json"
                if package_json.exists():
                    print("[U+2022] package.json: [U+2713] Found")
                else:
                    print("[U+2022] package.json: [U+2717] Missing")
                
                # Check for node_modules
                node_modules = frontend_path / "node_modules"
                if node_modules.exists():
                    print("[U+2022] node_modules: [U+2713] Found")
                else:
                    print("[U+2022] node_modules: [U+2717] Missing (run: cd frontend && npm install)")
                    
                # Check for Next.js config
                next_config = frontend_path / "next.config.js"
                next_config_mjs = frontend_path / "next.config.mjs"
                if next_config.exists() or next_config_mjs.exists():
                    print("[U+2022] Next.js config: [U+2713] Found")
                else:
                    print("[U+2022] Next.js config:  WARNING:  Not found (may be optional)")
                    
            else:
                print(f"[U+2022] Frontend directory: [U+2717] Not found at expected location")
                print(f"   ->  Expected: {frontend_path}")
                print(f"   ->  Solution: Ensure you're running from project root")
        except Exception as e:
            print(f"[U+2022] Directory check failed: {e}")
        
        print("\nCommon Solutions:")
        print("[U+2022] For port conflicts: python scripts/dev_launcher.py --dynamic")
        print("[U+2022] For missing dependencies: cd frontend && npm install")  
        print("[U+2022] For TypeScript errors: cd frontend && npm run build")
        print("[U+2022] For permission issues: Run as administrator (Windows) or use sudo (Linux/Mac)")
        print("[U+2022] For firewall issues: Allow Node.js/npm through firewall")
        
        print(f"\nFor more help, check logs in: {self.config.log_dir}")
        print("=" * 50)
    
    def _finalize_frontend_startup(self, port: int, process: subprocess.Popen):
        """Finalize frontend startup."""
        self._print(" PASS: ", "OK", f"Frontend started on port {port}")
        logger.info(f"Frontend URL: http://localhost:{port}")
        self.service_discovery.write_frontend_info(port)
        self.frontend_health_info = {"port": port, "process": process}