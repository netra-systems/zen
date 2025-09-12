#!/usr/bin/env python3
"""
Main entry point for the dev launcher.

This module can be run directly as:
    python -m dev_launcher [options]

Windows Compatibility Features:
- Enhanced process management with taskkill /F /T for process trees
- Port cleanup verification using netstat
- Proper signal handling for Windows console events
- Frontend Next.js compilation monitoring with Windows-specific paths
- Clear error messages with Windows-specific troubleshooting steps
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

# Set UTF-8 encoding for Windows and Mac
if sys.platform in ("win32", "darwin"):
    # Import here to avoid circular imports since this is __main__
    from shared.isolated_environment import get_env
    env_manager = get_env()
    env_manager.set("PYTHONIOENCODING", "utf-8", "__main__")
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add parent directory to path for imports

from dev_launcher import DevLauncher, LauncherConfig

# Global launcher instance for signal handling
_launcher_instance: Optional[DevLauncher] = None
logger = logging.getLogger(__name__)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown on all platforms."""
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        signal_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
        print(f"\n[U+1F6D1] SHUTDOWN | Received {signal_name} signal")
        if _launcher_instance:
            try:
                # Trigger graceful shutdown
                asyncio.create_task(_launcher_instance.cleanup())
            except RuntimeError:
                # If no event loop is running, cleanup synchronously
                print(" WARNING: [U+FE0F]  WARNING | Performing emergency cleanup...")
                _launcher_instance.emergency_cleanup()
        sys.exit(0)
    
    # Install signal handlers for graceful shutdown
    if sys.platform == "win32":
        # Windows-specific signal handling
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Terminate
        
        # Try to handle console close events on Windows
        try:
            import win32api
            def console_ctrl_handler(ctrl_type):
                """Handle Windows console control events."""
                if ctrl_type in [win32api.CTRL_C_EVENT, win32api.CTRL_BREAK_EVENT, win32api.CTRL_CLOSE_EVENT]:
                    signal_handler(signal.SIGTERM, None)
                    return True
                return False
            win32api.SetConsoleCtrlHandler(console_ctrl_handler, True)
        except ImportError:
            logger.debug("pywin32 not available, using basic Windows signal handling")
    else:
        # Unix-like systems
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Netra AI Development Launcher - Modular development environment with real-time monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
DEFAULT CONFIGURATION (Optimized for Development):
  python -m dev_launcher
  
  This provides:
    - Docker containers for databases (no local installation needed)
    - Static ports (8000/3000) for consistent frontend-backend communication
    - No hot reload by default (maximum performance)
    - Local-only secret loading (no GCP by default)
    - Real-time log streaming with emoji indicators
    - Professional syntax highlighting
    - Better error detection and reporting

EXAMPLES:
  python -m dev_launcher                           # Default: static ports (8000/3000), no backend reload
  python -m dev_launcher --dynamic                 # Use dynamic port allocation
  python -m dev_launcher --backend-reload          # Enable backend hot reload
  python -m dev_launcher --load-secrets            # Enable GCP secret loading
  python -m dev_launcher --no-turbopack            # Use webpack instead of turbopack
  python -m dev_launcher --verbose                 # Show detailed debug information

QUICK SHORTCUTS:
  python -m dev_launcher                           # Fast mode (default)
  python -m dev_launcher --dev                     # Development mode with hot reload
        """
    )
    
    # Port configuration
    port_group = parser.add_argument_group('Port Configuration')
    port_group.add_argument(
        "--backend-port",
        type=int,
        help="Backend server port (default: 8000)"
    )
    port_group.add_argument(
        "--frontend-port",
        type=int,
        default=3000,
        help="Frontend server port (default: 3000)"
    )
    port_group.add_argument(
        "--dynamic",
        action="store_true",
        help="Use dynamic port allocation to avoid conflicts"
    )
    port_group.add_argument(
        "-s", "--static",
        action="store_true",
        default=True,
        help="Use static ports (8000/3000) for consistent API communication (default: enabled)"
    )
    
    # Reload configuration
    reload_group = parser.add_argument_group('Hot Reload Configuration')
    reload_group.add_argument(
        "--no-backend-reload",
        action="store_true",
        default=True,
        help="Disable backend hot reload for better performance (default: disabled)"
    )
    reload_group.add_argument(
        "--backend-reload",
        action="store_true",
        help="Enable backend hot reload"
    )
    reload_group.add_argument(
        "--no-frontend-reload",
        action="store_true",
        help="Disable frontend hot reload"
    )
    reload_group.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable all hot reload (maximum performance)"
    )
    reload_group.add_argument(
        "--dev",
        action="store_true",
        help="Development mode with full hot reload"
    )
    
    # Secret management
    secret_group = parser.add_argument_group('Secret Management')
    secret_group.add_argument(
        "--load-secrets",
        action="store_true",
        help="Enable loading secrets from Google Cloud (default: local .env only)"
    )
    secret_group.add_argument(
        "--no-secrets", 
        action="store_true",
        help="Explicitly disable all secret loading (for compatibility)"
    )
    secret_group.add_argument(
        "--project-id",
        type=str,
        help="Google Cloud project ID for secret loading"
    )
    
    # UI configuration
    ui_group = parser.add_argument_group('UI Configuration')
    ui_group.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )
    ui_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output and debug information"
    )
    ui_group.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (no prompts, use defaults)"
    )
    ui_group.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel startup (use sequential startup)"
    )
    
    # Startup mode configuration
    ui_group.add_argument(
        "-m", "--mode",
        choices=["minimal", "standard", "verbose"],
        default="minimal",
        help="Startup output mode (default: minimal)"
    )
    ui_group.add_argument(
        "--minimal",
        action="store_true",
        help="Use minimal output mode (cleanest)"
    )
    ui_group.add_argument(
        "--standard",
        action="store_true",
        help="Use standard output mode (balanced)"
    )
    
    # Build configuration
    build_group = parser.add_argument_group('Build Configuration')
    build_group.add_argument(
        "--no-turbopack",
        action="store_true",
        help="Use webpack instead of turbopack (more stable)"
    )
    build_group.add_argument(
        "--turbopack",
        action="store_true",
        help="Use turbopack (experimental, faster)"
    )
    
    # Service mode configuration
    service_group = parser.add_argument_group('Service Mode Configuration')
    service_group.add_argument(
        "--docker-compose",
        action="store_true",
        help="Start all 12 services via docker-compose (dev + test environments)"
    )
    service_group.add_argument(
        "--list-services",
        action="store_true",
        help="List current service configurations and exit"
    )
    service_group.add_argument(
        "--set-redis",
        choices=["local", "shared", "docker", "disabled"],
        help="Set Redis mode (local/shared/docker/disabled)"
    )
    service_group.add_argument(
        "--set-clickhouse",
        choices=["local", "shared", "docker", "disabled"],
        help="Set ClickHouse mode (local/shared/docker/disabled)"
    )
    service_group.add_argument(
        "--set-postgres",
        choices=["local", "shared", "docker", "disabled"],
        help="Set PostgreSQL mode (local/shared/docker/disabled)"
    )
    service_group.add_argument(
        "--set-llm",
        choices=["local", "shared", "disabled"],
        help="Set LLM mode (local/shared/disabled)"
    )
    service_group.add_argument(
        "--reset-services",
        action="store_true",
        help="Reset all services to default configuration"
    )
    
    # Boundary monitoring configuration
    boundary_group = parser.add_argument_group('Boundary Monitoring')
    boundary_group.add_argument(
        "--watch-boundaries",
        dest="watch_boundaries",
        action="store_true",
        help="Enable real-time boundary monitoring (450-line/25-line limits)"
    )
    boundary_group.add_argument(
        "--boundary-check-interval",
        dest="boundary_check_interval",
        type=int,
        default=30,
        help="Boundary check interval in seconds (default: 30)"
    )
    boundary_group.add_argument(
        "--fail-on-boundary-violations",
        action="store_true",
        help="Stop dev server on critical boundary violations"
    )
    boundary_group.add_argument(
        "--no-boundary-warnings",
        action="store_true",
        help="Disable boundary violation warning messages"
    )
    
    # Phase 6 Integration: New optimization flags
    perf_group = parser.add_argument_group('Performance Optimization')
    perf_group.add_argument(
        "--silent",
        action="store_true",
        help="Silent mode with minimal output (< 20 lines on success)"
    )
    perf_group.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass all caching for testing"
    )
    perf_group.add_argument(
        "--profile",
        action="store_true",
        help="Show detailed performance metrics and timing"
    )
    
    return parser


def handle_service_configuration(args):
    """Handle service configuration commands."""
    from dev_launcher.service_config import ResourceMode, ServicesConfiguration
    from dev_launcher.unicode_utils import get_emoji, safe_print, setup_unicode_console
    
    setup_unicode_console()
    config_path = Path.cwd() / "netra-core-generation-1" / ".dev_services.json"
    if not config_path.parent.exists():
        config_path = Path.cwd() / ".dev_services.json"
    
    # Load or create configuration
    if config_path.exists():
        config = ServicesConfiguration.load_from_file(config_path)
    else:
        config = ServicesConfiguration()
    
    # Handle reset
    if args.reset_services:
        config = ServicesConfiguration()
        config.save_to_file(config_path)
        safe_print(f"{get_emoji('check')} Services reset to default configuration")
        return True
    
    # Handle service mode updates
    updated = False
    if args.set_redis:
        config.redis.mode = ResourceMode(args.set_redis)
        updated = True
    if args.set_clickhouse:
        config.clickhouse.mode = ResourceMode(args.set_clickhouse)
        updated = True
    if args.set_postgres:
        config.postgres.mode = ResourceMode(args.set_postgres)
        updated = True
    if args.set_llm:
        config.llm.mode = ResourceMode(args.set_llm)
        updated = True
    
    if updated:
        config.save_to_file(config_path)
        safe_print(f"{get_emoji('check')} Service configuration updated")
    
    # List services
    if args.list_services or updated:
        print("\n" + "="*60)
        safe_print(f"{get_emoji('gear')} Current Service Configuration")
        print("="*60)
        print(f"\nConfiguration file: {config_path}\n")
        
        services = [
            ("Redis", config.redis),
            ("ClickHouse", config.clickhouse),
            ("PostgreSQL", config.postgres),
            ("LLM", config.llm),
            ("Auth Service", config.auth_service)
        ]
        
        for name, service in services:
            mode_emoji = {
                ResourceMode.LOCAL: get_emoji('computer'),
                ResourceMode.SHARED: get_emoji('cloud'),
                ResourceMode.DOCKER: get_emoji('test_tube'),
                ResourceMode.DISABLED: get_emoji('x')
            }.get(service.mode, '')
            
            mode_desc = {
                ResourceMode.LOCAL: "Local instance",
                ResourceMode.SHARED: "Cloud/shared resource",
                ResourceMode.DOCKER: "Docker container",
                ResourceMode.DISABLED: "Disabled"
            }.get(service.mode, service.mode.value)
            
            safe_print(f"  {mode_emoji} {name:15} : {service.mode.value:8} - {mode_desc}")
            
            # Show connection details for active services
            if service.mode != ResourceMode.DISABLED:
                config_details = service.get_config()
                if service.mode == ResourceMode.LOCAL:
                    if 'host' in config_details and 'port' in config_details:
                        print(f"                       {config_details['host']}:{config_details['port']}")
                elif service.mode == ResourceMode.SHARED and name != "LLM":
                    if 'host' in config_details:
                        host = config_details['host']
                        if 'cloud' in host or 'com' in host:
                            # Truncate long cloud URLs
                            host_display = host[:30] + '...' if len(host) > 30 else host
                            print(f"                       {host_display}")
        
        print("\n" + "="*60)
        return True
    
    return False


def main():
    """Main entry point with enhanced Windows compatibility."""
    global _launcher_instance
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle docker-compose mode
    if args.docker_compose:
        print("[U+1F433] Starting all services via docker-compose...")
        print("    ->  Starting 12 services (6 dev + 6 test)")
        try:
            import subprocess
            
            # First stop any existing containers
            print("    ->  Cleaning up existing containers...")
            subprocess.run(
                ["docker-compose", "-f", "docker-compose.all.yml", "down"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )
            
            # Now start all services
            print("    ->  Starting services...")
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.all.yml", "up", "-d"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120
            )
            if result.returncode == 0:
                print(" PASS:  All Docker services started successfully!")
                print("\nDevelopment Services:")
                print("   ->  Backend: http://localhost:8000")
                print("   ->  Auth: http://localhost:8081")
                print("   ->  Frontend: http://localhost:3000")
                print("   ->  PostgreSQL: localhost:5432")
                print("   ->  Redis: localhost:6379")
                print("   ->  ClickHouse: localhost:8123")
                print("\nTest Services (docker-compose.all.yml):")
                print("   ->  Backend: http://localhost:8001")
                print("   ->  Auth: http://localhost:8082")
                print("   ->  Frontend: http://localhost:3001")
                print("   ->  PostgreSQL: localhost:5433")
                print("   ->  Redis: localhost:6380")
                print("   ->  ClickHouse: localhost:8124")
                sys.exit(0)
            else:
                print(f" FAIL:  Failed to start Docker services: {result.stderr}")
                sys.exit(1)
        except subprocess.TimeoutExpired:
            print(" FAIL:  Timeout starting Docker services")
            sys.exit(1)
        except Exception as e:
            print(f" FAIL:  Error starting Docker services: {e}")
            sys.exit(1)
    
    # Handle service configuration commands first
    if args.list_services or args.reset_services or \
       args.set_redis or args.set_clickhouse or args.set_postgres or args.set_llm:
        if handle_service_configuration(args):
            if args.list_services:
                sys.exit(0)  # Exit if only listing
            # Continue to run launcher with new configuration
    
    # Create configuration from arguments
    config = LauncherConfig.from_args(args)
    
    # Create and run launcher
    launcher = DevLauncher(config)
    _launcher_instance = launcher  # Store for signal handling
    
    # Run the async launcher with enhanced error handling
    exit_code = 0
    try:
        print("[U+1F680] Starting Netra AI Development Environment...")
        if sys.platform == "win32":
            print("    ->  Windows environment detected")
            print("    ->  Enhanced process tree management enabled")
            print("    ->  Port cleanup verification enabled")
        
        exit_code = asyncio.run(launcher.run())
        
        # Mark clean exit after successful or failed launch
        if hasattr(launcher, 'signal_handler') and launcher.signal_handler:
            launcher.signal_handler.mark_clean_exit()
        
        if exit_code == 0:
            print("\n PASS:  SUCCESS | Development environment started successfully")
            if sys.platform == "win32":
                print("    ->  Press Ctrl+C to gracefully shutdown all services")
            else:
                print("    ->  Press Ctrl+C or send SIGTERM to shutdown")
        else:
            print(f"\n FAIL:  FAILURE | Development environment failed to start (exit code: {exit_code})")
            _print_troubleshooting_info()
            
    except KeyboardInterrupt:
        print("\n[U+1F6D1] SHUTDOWN | Interrupted by user")
        exit_code = 0
        
    except Exception as e:
        print(f"\n[U+1F4A5] CRITICAL ERROR | Launcher failed: {e}")
        logger.error(f"Launcher exception: {e}", exc_info=True)
        _print_troubleshooting_info()
        exit_code = 1
        
    finally:
        # Ensure cleanup happens
        if _launcher_instance:
            try:
                _launcher_instance.emergency_cleanup()
            except Exception as cleanup_error:
                logger.error(f"Cleanup error: {cleanup_error}")
    
    sys.exit(exit_code)


def _print_troubleshooting_info():
    """Print comprehensive troubleshooting information."""
    print("\n[U+1F527] TROUBLESHOOTING GUIDE:")
    print("="*50)
    
    # System-specific process management
    if sys.platform == "win32":
        print("Process Management (Windows):")
        print("   1. Check ports: netstat -ano | findstr \":8000 :3000 :8081\"")
        print("   2. List processes: tasklist | findstr \"node python uvicorn\"")
        print("   3. Kill process: taskkill /F /T /IM \"process_name.exe\"")
        print("   4. Check Windows Defender/Firewall settings")
        print("   5. Try running as Administrator if permission issues persist")
    else:
        print("Process Management (Unix/Linux/Mac):")
        print("   1. Check ports: lsof -i :8000,:3000,:8081")
        print("   2. Kill processes: pkill -f \"uvicorn|next|node\"")
        print("   3. System resources: ps aux | grep -E \"(uvicorn|next|node)\"")
    
    print("\nService Configuration Issues:")
    print("   [U+2022] If local services not available, the platform auto-switches to shared services")
    print("   [U+2022] For Redis/ClickHouse/PostgreSQL: Install locally or use shared mode")
    print("   [U+2022] For AI features: Set up API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)")
    print("   [U+2022] Check service status: python -m dev_launcher --list-services")
    print("   [U+2022] Reset services: python -m dev_launcher --reset-services")
    
    print("\nGeneral Issues:")
    print("   [U+2022] Review logs in ./logs/ directory")
    print("   [U+2022] Run with --verbose for detailed output")
    print("   [U+2022] Check all dependencies are installed")
    print("   [U+2022] Verify .env files are properly configured")
    print("   [U+2022] Ensure you're in the project root directory")
    
    print("\nQuick Fixes:")
    print("   [U+2022] Try: python -m dev_launcher --reset-services")
    print("   [U+2022] Try: python -m dev_launcher --no-cache")
    print("   [U+2022] Try: python -m dev_launcher --verbose")
    
    print("="*50)


if __name__ == "__main__":
    main()