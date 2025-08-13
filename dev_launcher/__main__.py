#!/usr/bin/env python3
"""
Main entry point for the dev launcher.

This module can be run directly as:
    python -m dev_launcher [options]
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dev_launcher import DevLauncher, LauncherConfig


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Netra AI Development Launcher - Modular development environment with real-time monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RECOMMENDED USAGE:
  python -m dev_launcher --dynamic --no-backend-reload --load-secrets
  
  This configuration provides:
    • Real-time log streaming with color coding
    • Automatic port allocation (no conflicts)
    • 30-50% faster performance (no backend reload)
    • Hot reload for development (native uvicorn/Next.js reload)
    • Automatic Google secret loading
    • Better error detection and reporting

EXAMPLES:
  python -m dev_launcher                           # Default: loads secrets, native reload, streaming
  python -m dev_launcher --dynamic                 # Dynamic port allocation
  python -m dev_launcher --no-secrets              # Skip secret loading
  python -m dev_launcher --no-turbopack            # Use webpack instead of turbopack
  python -m dev_launcher --no-reload               # Maximum performance (no hot reload)
  python -m dev_launcher --verbose                 # Show detailed debug information

QUICK SHORTCUTS:
  python -m dev_launcher -d                        # Dynamic ports (short form)
  python -m dev_launcher -d --no-reload            # Fast mode with dynamic ports
        """
    )
    
    # Port configuration
    port_group = parser.add_argument_group('Port Configuration')
    port_group.add_argument(
        "--backend-port",
        type=int,
        help="Backend server port (default: 8000 or dynamic)"
    )
    port_group.add_argument(
        "--frontend-port",
        type=int,
        default=3000,
        help="Frontend server port (default: 3000)"
    )
    port_group.add_argument(
        "-d", "--dynamic",
        action="store_true",
        help="Use dynamic port allocation to avoid conflicts"
    )
    
    # Reload configuration
    reload_group = parser.add_argument_group('Hot Reload Configuration')
    reload_group.add_argument(
        "--no-backend-reload",
        action="store_true",
        help="Disable backend hot reload for better performance"
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
    
    # Secret management
    secret_group = parser.add_argument_group('Secret Management')
    secret_group.add_argument(
        "--no-secrets",
        action="store_true",
        help="Skip loading secrets from Google Cloud"
    )
    secret_group.add_argument(
        "--load-secrets",
        action="store_true",
        help="Force loading secrets (default in dev mode)"
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
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Create configuration from arguments
    config = LauncherConfig.from_args(args)
    
    # Create and run launcher
    launcher = DevLauncher(config)
    exit_code = launcher.run()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()