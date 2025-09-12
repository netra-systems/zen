#!/usr/bin/env python3
"""
Configure the Code Audit System
Manage feature flags, permission levels, and team settings
"""

import sys
import json
import argparse
import io
from pathlib import Path
from typing import Optional

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from audit_config import (
    AuditConfig, AuditLevel, DuplicateThreshold, 
    FeatureFlags, TeamPermissions, get_default_config
)


class AuditConfigurator:
    """Interactive configuration manager"""
    
    def __init__(self):
        self.config = get_default_config()
    
    def show_status(self):
        """Show current configuration status"""
        print("\n" + "=" * 60)
        print(" SEARCH:  NETRA CODE AUDIT - Configuration Status")
        print("=" * 60)
        
        print("\n[U+1F4CB] Core Features:")
        print(f"  Duplicate Detection: {' PASS: ' if self.config.flags.duplicate_detection else ' FAIL: '}")
        print(f"  Legacy Detection: {' PASS: ' if self.config.flags.legacy_code_detection else ' FAIL: '}")
        print(f"  Claude Analysis: {' PASS: ' if self.config.flags.claude_analysis else ' FAIL: '}")
        print(f"  Auto Remediation: {' PASS: ' if self.config.flags.auto_remediation else ' FAIL: '}")
        
        print("\n[U+1F39A][U+FE0F] Audit Levels:")
        print(f"  Duplicates: {self.config.flags.duplicate_level.value}")
        print(f"  Legacy: {self.config.flags.legacy_level.value}")
        print(f"  Complexity: {self.config.flags.complexity_level.value}")
        print(f"  Imports: {self.config.flags.import_level.value}")
        
        print("\n CHART:  Thresholds:")
        print(f"  Duplicate Similarity: {self.config.flags.duplicate_threshold.value}")
        print(f"  Max Complexity: {self.config.flags.max_complexity}")
        print(f"  Max File Lines: {self.config.flags.max_file_lines}")
        print(f"  Max Function Lines: {self.config.flags.max_function_lines}")
        
        print("\n[U+1F527] Options:")
        print(f"  Allow Emergency Bypass: {' PASS: ' if self.config.flags.allow_emergency_bypass else ' FAIL: '}")
        print(f"  Allow User Override: {' PASS: ' if self.config.flags.allow_user_override else ' FAIL: '}")
        print(f"  Check New Files Only: {' PASS: ' if self.config.flags.check_new_files_only else ' FAIL: '}")
        print(f"  Exclude Tests: {' PASS: ' if self.config.flags.exclude_tests else ' FAIL: '}")
        
        print("\n[U+1F4C1] Config File:")
        print(f"  Location: {self.config.config_path}")
        print(f"  Exists: {' PASS: ' if self.config.config_path.exists() else ' FAIL: '}")
    
    def set_level(self, category: str, level: str):
        """Set audit level for a category"""
        try:
            audit_level = AuditLevel(level)
            field_name = f"{category}_level"
            
            if hasattr(self.config.flags, field_name):
                setattr(self.config.flags, field_name, audit_level)
                self.config.save_config()
                print(f" PASS:  Set {category} level to {level}")
            else:
                print(f" FAIL:  Unknown category: {category}")
        except ValueError:
            print(f" FAIL:  Invalid level: {level}")
            print(f"   Valid levels: {', '.join([l.value for l in AuditLevel])}")
    
    def set_feature(self, feature: str, enabled: bool):
        """Enable/disable a feature"""
        feature_map = {
            "duplicates": "duplicate_detection",
            "legacy": "legacy_code_detection",
            "claude": "claude_analysis",
            "auto-fix": "auto_remediation"
        }
        
        field_name = feature_map.get(feature, feature)
        
        if hasattr(self.config.flags, field_name):
            setattr(self.config.flags, field_name, enabled)
            self.config.save_config()
            status = "enabled" if enabled else "disabled"
            print(f" PASS:  {feature} {status}")
        else:
            print(f" FAIL:  Unknown feature: {feature}")
    
    def set_threshold(self, threshold_type: str, value: str):
        """Set a threshold value"""
        if threshold_type == "duplicate":
            try:
                threshold = DuplicateThreshold[value.upper()]
                self.config.flags.duplicate_threshold = threshold
                self.config.save_config()
                print(f" PASS:  Set duplicate threshold to {threshold.value}")
            except KeyError:
                print(f" FAIL:  Invalid threshold: {value}")
                print(f"   Valid: {', '.join([t.name.lower() for t in DuplicateThreshold])}")
        else:
            # Numeric thresholds
            try:
                numeric_value = int(value)
                field_name = f"max_{threshold_type}"
                
                if hasattr(self.config.flags, field_name):
                    setattr(self.config.flags, field_name, numeric_value)
                    self.config.save_config()
                    print(f" PASS:  Set {threshold_type} threshold to {numeric_value}")
                else:
                    print(f" FAIL:  Unknown threshold: {threshold_type}")
            except ValueError:
                print(f" FAIL:  Invalid numeric value: {value}")
    
    def quick_setup(self, mode: str):
        """Quick setup for common scenarios"""
        modes = {
            "strict": {
                "duplicate_level": AuditLevel.HARD_BLOCK,
                "legacy_level": AuditLevel.SOFT_BLOCK,
                "import_level": AuditLevel.HARD_BLOCK,
                "duplicate_threshold": DuplicateThreshold.STRICT,
                "allow_emergency_bypass": False,
                "claude_analysis": True
            },
            "moderate": {
                "duplicate_level": AuditLevel.SOFT_BLOCK,
                "legacy_level": AuditLevel.WARN,
                "import_level": AuditLevel.SOFT_BLOCK,
                "duplicate_threshold": DuplicateThreshold.MODERATE,
                "allow_emergency_bypass": True,
                "claude_analysis": True
            },
            "lenient": {
                "duplicate_level": AuditLevel.WARN,
                "legacy_level": AuditLevel.NOTIFY,
                "import_level": AuditLevel.WARN,
                "duplicate_threshold": DuplicateThreshold.LENIENT,
                "allow_emergency_bypass": True,
                "claude_analysis": False
            },
            "dev": {
                "duplicate_level": AuditLevel.NOTIFY,
                "legacy_level": AuditLevel.NOTIFY,
                "import_level": AuditLevel.WARN,
                "duplicate_threshold": DuplicateThreshold.MODERATE,
                "allow_emergency_bypass": True,
                "claude_analysis": False,
                "check_new_files_only": True
            },
            "ci": {
                "duplicate_level": AuditLevel.HARD_BLOCK,
                "legacy_level": AuditLevel.HARD_BLOCK,
                "import_level": AuditLevel.ENFORCE,
                "duplicate_threshold": DuplicateThreshold.STRICT,
                "allow_emergency_bypass": False,
                "claude_analysis": False,
                "enforce_in_ci": True
            }
        }
        
        if mode not in modes:
            print(f" FAIL:  Unknown mode: {mode}")
            print(f"   Available: {', '.join(modes.keys())}")
            return
        
        settings = modes[mode]
        for key, value in settings.items():
            setattr(self.config.flags, key, value)
        
        self.config.save_config()
        print(f" PASS:  Applied {mode} configuration preset")
        print("\nSettings applied:")
        for key, value in settings.items():
            print(f"  {key}: {value if not hasattr(value, 'value') else value.value}")
    
    def add_team(self, team_name: str, can_override: bool = False, max_overrides: int = 3):
        """Add team-specific permissions"""
        team = TeamPermissions(
            team_name=team_name,
            can_override_blocks=can_override,
            max_override_count=max_overrides
        )
        
        self.config.add_team(team)
        print(f" PASS:  Added team: {team_name}")
        print(f"   Can override: {can_override}")
        print(f"   Max overrides/day: {max_overrides}")
    
    def test_config(self):
        """Test configuration with sample code"""
        print("\n[U+1F9EA] Testing configuration...")
        
        # Create test file
        test_file = Path("test_audit_config.py")
        test_file.write_text("""
# Test file with intentional issues

def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total

def compute_sum(items):
    # Duplicate of calculate_total
    sum = 0
    for item in items:
        sum += item.price
    return sum

# Legacy patterns - removed relative import example
print("Debug output")  # Print in production
        """)
        
        try:
            # Run audit
            import subprocess
            result = subprocess.run(
                [sys.executable, "scripts/code_audit_orchestrator.py", "--files", str(test_file)],
                capture_output=True,
                text=True
            )
            
            print("\n CHART:  Test Results:")
            print(result.stdout)
            
            if result.returncode == 0:
                print(" PASS:  Audit passed (no blocking issues)")
            else:
                print("[U+26D4] Audit would block commit")
            
        finally:
            test_file.unlink(missing_ok=True)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Configure Code Audit System")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status command
    subparsers.add_parser("status", help="Show current configuration")
    
    # Set level command
    level_parser = subparsers.add_parser("level", help="Set audit level")
    level_parser.add_argument("category", choices=["duplicate", "legacy", "complexity", "import"])
    level_parser.add_argument("level", choices=["off", "notify", "warn", "soft_block", "hard_block", "enforce"])
    
    # Feature command
    feature_parser = subparsers.add_parser("feature", help="Enable/disable features")
    feature_parser.add_argument("name", choices=["duplicates", "legacy", "claude", "auto-fix"])
    feature_parser.add_argument("state", choices=["on", "off"])
    
    # Threshold command
    threshold_parser = subparsers.add_parser("threshold", help="Set thresholds")
    threshold_parser.add_argument("type", choices=["duplicate", "complexity", "file_lines", "function_lines"])
    threshold_parser.add_argument("value")
    
    # Quick setup command
    quick_parser = subparsers.add_parser("quick", help="Quick configuration presets")
    quick_parser.add_argument("mode", choices=["strict", "moderate", "lenient", "dev", "ci"])
    
    # Team command
    team_parser = subparsers.add_parser("team", help="Add team permissions")
    team_parser.add_argument("name", help="Team name")
    team_parser.add_argument("--can-override", action="store_true", help="Allow override")
    team_parser.add_argument("--max-overrides", type=int, default=3, help="Max overrides per day")
    
    # Test command
    subparsers.add_parser("test", help="Test configuration")
    
    # Init command
    subparsers.add_parser("init", help="Initialize configuration file")
    
    args = parser.parse_args()
    
    configurator = AuditConfigurator()
    
    if not args.command or args.command == "status":
        configurator.show_status()
    
    elif args.command == "level":
        configurator.set_level(args.category, args.level)
    
    elif args.command == "feature":
        enabled = args.state == "on"
        configurator.set_feature(args.name, enabled)
    
    elif args.command == "threshold":
        configurator.set_threshold(args.type, args.value)
    
    elif args.command == "quick":
        configurator.quick_setup(args.mode)
    
    elif args.command == "team":
        configurator.add_team(args.name, args.can_override, args.max_overrides)
    
    elif args.command == "test":
        configurator.test_config()
    
    elif args.command == "init":
        configurator.config.save_config()
        print(f" PASS:  Initialized config at {configurator.config.config_path}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()