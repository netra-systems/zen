#!/usr/bin/env python3
"""
Manage pre-commit hooks configuration
Easily enable/disable pre-commit checks without removing files
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

CONFIG_FILE = Path(__file__).parent.parent / ".githooks" / "config.json"

def load_config():
    """Load current configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "precommit_checks_enabled": True,
        "max_file_lines": 300,
        "max_function_lines": 8
    }

def save_config(config):
    """Save configuration"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Configuration saved to {CONFIG_FILE}")

def enable_hooks(reason=None):
    """Enable pre-commit hooks"""
    config = load_config()
    config["precommit_checks_enabled"] = True
    if "disabled_reason" in config:
        del config["disabled_reason"]
    if "disabled_date" in config:
        del config["disabled_date"]
    if "disabled_by" in config:
        del config["disabled_by"]
    
    if reason:
        config["enabled_reason"] = reason
        config["enabled_date"] = datetime.now().isoformat()
    
    save_config(config)
    print("[SUCCESS] Pre-commit hooks ENABLED")
    print("Architecture checks will run on every commit")

def disable_hooks(reason=None, user=None):
    """Disable pre-commit hooks"""
    config = load_config()
    config["precommit_checks_enabled"] = False
    config["disabled_date"] = datetime.now().isoformat()
    
    if reason:
        config["disabled_reason"] = reason
    else:
        config["disabled_reason"] = "Temporarily disabled for development"
    
    if user:
        config["disabled_by"] = user
    else:
        import os
        config["disabled_by"] = os.environ.get("USER", "Unknown")
    
    save_config(config)
    print("[SUCCESS] Pre-commit hooks DISABLED")
    print(f"Reason: {config['disabled_reason']}")
    print("To re-enable: python scripts/manage_precommit.py enable")

def status():
    """Show current status"""
    config = load_config()
    enabled = config.get("precommit_checks_enabled", True)
    
    print("=" * 50)
    print("PRE-COMMIT HOOKS STATUS")
    print("=" * 50)
    print(f"Status: {'ENABLED' if enabled else 'DISABLED'}")
    print(f"Config file: {CONFIG_FILE}")
    
    if enabled:
        print("\nActive checks:")
        print(f"  - Max file lines: {config.get('max_file_lines', 300)}")
        print(f"  - Max function lines: {config.get('max_function_lines', 8)}")
        if "enabled_date" in config:
            print(f"\nEnabled on: {config['enabled_date']}")
        if "enabled_reason" in config:
            print(f"Reason: {config['enabled_reason']}")
    else:
        print("\n[WARNING] Hooks are disabled!")
        if "disabled_date" in config:
            print(f"Disabled on: {config['disabled_date']}")
        if "disabled_by" in config:
            print(f"Disabled by: {config['disabled_by']}")
        if "disabled_reason" in config:
            print(f"Reason: {config['disabled_reason']}")
    
    print("\nCommands:")
    print("  Enable:  python scripts/manage_precommit.py enable")
    print("  Disable: python scripts/manage_precommit.py disable --reason 'Your reason'")
    print("  Status:  python scripts/manage_precommit.py status")

def main():
    parser = argparse.ArgumentParser(description='Manage pre-commit hooks')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable pre-commit hooks')
    enable_parser.add_argument('--reason', help='Reason for enabling')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable pre-commit hooks')
    disable_parser.add_argument('--reason', help='Reason for disabling', 
                               default='Temporarily disabled for development')
    disable_parser.add_argument('--user', help='User disabling the hooks')
    
    # Status command
    subparsers.add_parser('status', help='Show current status')
    
    args = parser.parse_args()
    
    if args.command == 'enable':
        enable_hooks(reason=args.reason)
    elif args.command == 'disable':
        disable_hooks(reason=args.reason, user=args.user)
    elif args.command == 'status':
        status()
    else:
        status()  # Default to showing status

if __name__ == '__main__':
    main()