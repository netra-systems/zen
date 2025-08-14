#!/usr/bin/env python3
"""
Improved development launcher for Netra AI platform with auto-restart and better monitoring.
This is the main entry point that orchestrates the modular components.
"""

import sys
import argparse
from typing import Optional

from dev_launcher_core import DevLauncher


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Improved development launcher for Netra AI platform with auto-restart",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
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
    )
    
    parser.add_argument("--backend-port", type=int, help="Backend server port")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend server port")
    parser.add_argument("--dynamic", action="store_true", help="Use dynamic port allocation")
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--no-backend-reload", action="store_true", help="Disable backend hot reload")
    parser.add_argument("--no-frontend-reload", action="store_true", help="Disable frontend hot reload")
    parser.add_argument("--no-reload", action="store_true", help="Disable all hot reload")
    parser.add_argument("--load-secrets", action="store_true", help="Load secrets from Google Cloud")
    parser.add_argument("--project-id", type=str, help="Google Cloud project ID")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--auto-restart", action="store_true", help="Automatically restart crashed services")
    parser.add_argument("--no-turbopack", action="store_true", help="Use webpack instead of turbopack")
    
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
        no_browser=args.no_browser,
        auto_restart=args.auto_restart,
        use_turbopack=not args.no_turbopack
    )
    
    sys.exit(launcher.run())


if __name__ == "__main__":
    main()