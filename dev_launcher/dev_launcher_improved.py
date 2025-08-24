#!/usr/bin/env python3
"""
Improved development launcher for Netra AI platform with auto-restart and better monitoring.
This is the main entry point that orchestrates the modular components.
"""

import argparse
import sys
from typing import Optional

from dev_launcher_core import DevLauncher


def main():
    """Main entry point."""
    parser = _create_argument_parser()
    args = parser.parse_args()
    launcher = _create_launcher_from_args(args)
    sys.exit(launcher.run())

def _create_argument_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Improved development launcher for Netra AI platform with auto-restart",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_get_usage_examples()
    )
    _add_parser_arguments(parser)
    return parser

def _get_usage_examples() -> str:
    """Get usage examples string."""
    return """
RECOMMENDED USAGE:
  python dev_launcher_improved.py --dynamic --no-backend-reload --auto-restart
  
  This configuration provides:
    • Automatic port allocation (no conflicts)
    • 30-50% faster performance
    • Auto-restart on crashes
    • Better error logging

Examples:
  python dev_launcher_improved.py --dynamic --auto-restart  # Best for development
  python dev_launcher_improved.py --no-turbopack           # Use webpack instead of turbopack
  python dev_launcher_improved.py --no-reload              # Maximum performance
        """

def _add_parser_arguments(parser):
    """Add all arguments to the parser."""
    _add_port_arguments(parser)
    _add_control_arguments(parser)
    _add_feature_arguments(parser)

def _add_port_arguments(parser):
    """Add port-related arguments."""
    parser.add_argument("--backend-port", type=int, help="Backend server port")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend server port")
    parser.add_argument("--dynamic", action="store_true", help="Use dynamic port allocation")

def _add_control_arguments(parser):
    """Add control-related arguments."""
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--no-backend-reload", action="store_true", help="Disable backend hot reload")
    parser.add_argument("--no-frontend-reload", action="store_true", help="Disable frontend hot reload")
    parser.add_argument("--no-reload", action="store_true", help="Disable all hot reload")

def _add_feature_arguments(parser):
    """Add feature-related arguments."""
    parser.add_argument("--load-secrets", action="store_true", help="Load secrets from Google Cloud")
    parser.add_argument("--project-id", type=str, help="Google Cloud project ID")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--auto-restart", action="store_true", help="Automatically restart crashed services")
    parser.add_argument("--no-turbopack", action="store_true", help="Use webpack instead of turbopack")

def _create_launcher_from_args(args):
    """Create DevLauncher instance from parsed arguments."""
    reload_config = _calculate_reload_flags(args)
    return DevLauncher(
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        dynamic_ports=args.dynamic,
        verbose=args.verbose,
        backend_reload=reload_config['backend'],
        frontend_reload=reload_config['frontend'],
        load_secrets=args.load_secrets,
        project_id=args.project_id,
        no_browser=args.no_browser,
        auto_restart=args.auto_restart,
        use_turbopack=not args.no_turbopack
    )

def _calculate_reload_flags(args) -> dict:
    """Calculate reload flags from arguments."""
    backend_reload = not args.no_backend_reload and not args.no_reload
    frontend_reload = not args.no_frontend_reload and not args.no_reload
    return {'backend': backend_reload, 'frontend': frontend_reload}


if __name__ == "__main__":
    main()