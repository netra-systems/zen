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
DEFAULT CONFIGURATION (Optimized for Development):
  python -m dev_launcher
  
  This provides:
    ✅ Dynamic port allocation (no conflicts)
    ✅ No backend hot reload (30-50% faster)
    ✅ Automatic Google secret loading
    ✅ Real-time log streaming with emoji indicators
    ✅ Professional syntax highlighting
    ✅ Better error detection and reporting

EXAMPLES:
  python -m dev_launcher                           # Default: dynamic ports, no backend reload
  python -m dev_launcher --static                  # Use fixed ports (8000/3000)
  python -m dev_launcher --backend-reload          # Enable backend hot reload
  python -m dev_launcher --no-secrets              # Skip secret loading
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
        default=True,
        help="Use dynamic port allocation to avoid conflicts (default: enabled)"
    )
    port_group.add_argument(
        "--static",
        action="store_true",
        help="Use static ports instead of dynamic allocation"
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