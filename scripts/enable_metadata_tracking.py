#!/usr/bin/env python3
"""
AI Agent Metadata Tracking Enabler
Streamlined entry point using modular metadata tracking components.
"""

import sys
import argparse
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from metadata_tracking import MetadataTrackingEnabler


def main():
    """Main entry point for metadata tracking enabler."""
    parser = argparse.ArgumentParser(
        description="Enable and manage AI agent metadata tracking"
    )
    
    parser.add_argument(
        "--enable",
        action="store_true",
        help="Enable all metadata tracking components"
    )
    
    parser.add_argument(
        "--status",
        action="store_true", 
        help="Show current status of metadata tracking system"
    )
    
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory (defaults to current directory)"
    )
    
    args = parser.parse_args()
    
    # Initialize enabler
    enabler = MetadataTrackingEnabler(args.project_root)
    
    if args.enable:
        success = enabler.enable_all()
        sys.exit(0 if success else 1)
    
    elif args.status:
        enabler.print_status()
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()