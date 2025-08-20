#!/usr/bin/env python3
"""
AI Agent Metadata Tracking Enabler - Modular Enterprise-Ready Version
Enables comprehensive metadata tracking for AI modifications with enterprise audit compliance.
Supports modular command execution following 25-line function architecture.
"""

import argparse
from pathlib import Path

from metadata_tracking import MetadataTrackingEnabler

def _get_argument_parser() -> argparse.ArgumentParser:
    """Get command line argument parser"""
    parser = argparse.ArgumentParser(description="Enable AI Agent Metadata Tracking")
    parser.add_argument("--activate", action="store_true", 
                       help="Enable all tracking components")
    parser.add_argument("--status", action="store_true", 
                       help="Check current status")
    parser.add_argument("--install-hooks", action="store_true", 
                       help="Install git hooks only")
    parser.add_argument("--create-db", action="store_true", 
                       help="Create database only")
    return parser


def _handle_activate_command(enabler: MetadataTrackingEnabler) -> None:
    """Handle activate command"""
    enabler.enable_all()


def _handle_status_command(enabler: MetadataTrackingEnabler) -> None:
    """Handle status command"""
    enabler.print_status()


def _handle_install_hooks_command(enabler: MetadataTrackingEnabler) -> None:
    """Handle install hooks command"""
    enabler.install_git_hooks()


def _handle_create_db_command(enabler: MetadataTrackingEnabler) -> None:
    """Handle create database command"""
    enabler.create_metadata_database()


def _handle_default_command(enabler: MetadataTrackingEnabler) -> None:
    """Handle default command (show status)"""
    enabler.print_status()
    print("\nUse --activate to enable the metadata tracking system")


def main():
    """Main entry point - lightweight and modular"""
    parser = _get_argument_parser()
    args = parser.parse_args()
    
    # Initialize enabler
    enabler = MetadataTrackingEnabler()
    
    if args.activate:
        _handle_activate_command(enabler)
    elif args.status:
        _handle_status_command(enabler)
    elif args.install_hooks:
        _handle_install_hooks_command(enabler)
    elif args.create_db:
        _handle_create_db_command(enabler)
    else:
        _handle_default_command(enabler)


if __name__ == "__main__":
    main()