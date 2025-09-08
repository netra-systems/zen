#!/usr/bin/env python
"""
Configuration Change Monitoring Script

Demonstrates how to use the ConfigChangeTracker to monitor configuration
changes and prevent regressions like the OAuth 503 errors.

Usage:
    python scripts/monitor_config_changes.py --snapshot  # Take snapshot
    python scripts/monitor_config_changes.py --check     # Check for changes
    python scripts/monitor_config_changes.py --report    # Generate report
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.config_change_tracker import get_config_tracker
from shared.isolated_environment import IsolatedEnvironment


def get_current_config() -> Dict[str, str]:
    """
    Get current configuration from environment.
    
    Returns:
        Dictionary of current configuration values
    """
    env = IsolatedEnvironment()
    
    # Critical configs to monitor
    critical_keys = [
        'SERVICE_SECRET',
        'JWT_SECRET',
        'JWT_SECRET_KEY',
        'JWT_SECRET_STAGING',
        'AUTH_SERVICE_URL',
        'DATABASE_URL',
        'REDIS_URL',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'GOOGLE_OAUTH_CLIENT_ID_STAGING',
        'GOOGLE_OAUTH_CLIENT_SECRET_STAGING',
        'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION',
        'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION',
        'ENVIRONMENT',
        'FRONTEND_URL',
        'BACKEND_URL',
        'CORS_ALLOWED_ORIGINS'
    ]
    
    config = {}
    for key in critical_keys:
        value = env.get(key)
        if value:  # Only include non-empty values
            config[key] = value
    
    return config


def take_snapshot():
    """Take a snapshot of current configuration."""
    tracker = get_config_tracker()
    current_config = get_current_config()
    
    print(f"📸 Taking configuration snapshot ({len(current_config)} keys)...")
    tracker.snapshot_current_config(current_config)
    
    print("✅ Snapshot completed")
    print(f"Monitored configs: {', '.join(sorted(current_config.keys()))}")


def check_changes():
    """Check for configuration changes."""
    tracker = get_config_tracker()
    current_config = get_current_config()
    
    print("🔍 Checking for configuration changes...")
    
    # Take new snapshot
    tracker.snapshot_current_config(current_config)
    
    # Detect changes
    changes = tracker.detect_changes()
    
    if not changes:
        print("✅ No configuration changes detected")
        return
    
    print(f"⚠️  Detected {len(changes)} configuration changes:")
    
    for change in changes:
        risk_emoji = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '🔶',
            'low': '🟡',
            'info': 'ℹ️'
        }.get(change.risk_level.value, '❓')
        
        print(f"\n{risk_emoji} {change.key} ({change.change_type.value.upper()})")
        print(f"   Risk: {change.risk_level.value.upper()}")
        print(f"   Impact: {change.impact_analysis}")
        
        if change.affected_services:
            print(f"   Services: {', '.join(change.affected_services)}")
        
        if change.requires_restart:
            print("   ⚠️  Requires service restart")
        
        if change.requires_migration:
            print("   🔄 Requires data migration")
        
        if change.old_value and change.new_value:
            print(f"   Changed: {change.old_value} → {change.new_value}")
        elif change.old_value:
            print(f"   Deleted: {change.old_value}")
        elif change.new_value:
            print(f"   Added: {change.new_value}")
    
    # Check for critical changes
    critical_changes = [c for c in changes if c.risk_level.value == 'critical']
    if critical_changes:
        print(f"\n🚨 WARNING: {len(critical_changes)} CRITICAL changes detected!")
        print("These changes could cause system failure. Review immediately!")


def generate_report():
    """Generate and display configuration change report."""
    tracker = get_config_tracker()
    
    print("📋 Generating configuration change report...")
    
    report = tracker.generate_change_report()
    print(report)
    
    # Validate current config
    current_config = get_current_config()
    is_valid, errors = tracker.validate_config_consistency(current_config)
    
    if is_valid:
        print("✅ Configuration consistency validation passed")
    else:
        print("\n❌ Configuration consistency validation FAILED:")
        for error in errors:
            print(f"   - {error}")
    
    # Show recent critical changes
    critical_changes = tracker.get_critical_changes()
    if critical_changes:
        print(f"\n🚨 Total critical changes in history: {len(critical_changes)}")


def validate_environment():
    """Validate current environment configuration."""
    tracker = get_config_tracker()
    current_config = get_current_config()
    
    print("🔍 Validating environment configuration...")
    
    is_valid, errors = tracker.validate_config_consistency(current_config)
    
    if is_valid:
        print("✅ Environment configuration is valid")
    else:
        print("❌ Environment configuration validation FAILED:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Monitor configuration changes')
    parser.add_argument('--snapshot', action='store_true', 
                       help='Take configuration snapshot')
    parser.add_argument('--check', action='store_true',
                       help='Check for configuration changes')
    parser.add_argument('--report', action='store_true',
                       help='Generate change report')
    parser.add_argument('--validate', action='store_true',
                       help='Validate current configuration')
    parser.add_argument('--tracking-file', type=str,
                       help='Path to tracking file (default: config_changes.json)')
    
    args = parser.parse_args()
    
    if args.tracking_file:
        # Initialize tracker with custom file
        from shared.config_change_tracker import ConfigChangeTracker
        global _tracker_instance
        _tracker_instance = ConfigChangeTracker(Path(args.tracking_file))
    
    try:
        if args.snapshot:
            take_snapshot()
        elif args.check:
            check_changes()
        elif args.report:
            generate_report()
        elif args.validate:
            validate_environment()
        else:
            parser.print_help()
            print("\nExample usage:")
            print("  python scripts/monitor_config_changes.py --snapshot")
            print("  python scripts/monitor_config_changes.py --check")
            print("  python scripts/monitor_config_changes.py --report")
    
    except KeyboardInterrupt:
        print("\n⚠️  Monitoring interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()