#!/usr/bin/env python3
"""
Audit System Configuration - Feature flags and permission levels
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict, field


class AuditLevel(Enum):
    """Audit strictness levels"""
    OFF = "off"                # Completely disabled
    NOTIFY = "notify"          # Only notify, never block
    WARN = "warn"              # Warn but don't block
    SOFT_BLOCK = "soft_block"  # Block but allow override
    HARD_BLOCK = "hard_block"  # Block with no override
    ENFORCE = "enforce"        # Strictest - block and require fix


class DuplicateThreshold(Enum):
    """Duplicate detection sensitivity"""
    LENIENT = 0.95    # Only exact or near-exact duplicates
    MODERATE = 0.85   # Similar code patterns
    STRICT = 0.75     # Even partially similar code
    PARANOID = 0.65   # Very aggressive detection


@dataclass
class FeatureFlags:
    """Feature flag configuration for audit system"""
    
    # Core Features
    duplicate_detection: bool = True
    legacy_code_detection: bool = True
    claude_analysis: bool = True
    auto_remediation: bool = False
    
    # Audit Levels per Category
    duplicate_level: AuditLevel = AuditLevel.WARN
    legacy_level: AuditLevel = AuditLevel.NOTIFY
    naming_level: AuditLevel = AuditLevel.OFF
    complexity_level: AuditLevel = AuditLevel.WARN
    import_level: AuditLevel = AuditLevel.SOFT_BLOCK
    
    # Thresholds
    duplicate_threshold: DuplicateThreshold = DuplicateThreshold.MODERATE
    max_complexity: int = 20  # Cyclomatic complexity
    max_file_lines: int = 500
    max_function_lines: int = 50
    min_duplicate_lines: int = 10  # Minimum lines to consider duplicate
    
    # Scope Controls
    check_new_files_only: bool = False
    check_modified_lines_only: bool = True
    exclude_tests: bool = True
    exclude_migrations: bool = True
    exclude_generated: bool = True
    
    # Claude Integration
    claude_timeout: int = 60  # seconds
    claude_max_context: int = 50000  # characters
    claude_parallel: bool = True
    claude_cache_results: bool = True
    claude_cache_ttl: int = 3600  # seconds
    
    # Bypass Options
    allow_emergency_bypass: bool = True
    allow_user_override: bool = True
    bypass_keywords: List[str] = field(default_factory=lambda: [
        "EMERGENCY_FIX",
        "BYPASS_AUDIT",
        "SKIP_AUDIT",
        "[no-audit]",
        "HOTFIX"
    ])
    
    # Reporting
    generate_report: bool = True
    report_format: str = "markdown"  # markdown, json, html
    verbose_output: bool = False
    show_suggestions: bool = True
    
    # Performance
    parallel_workers: int = 4
    use_cache: bool = True
    incremental_analysis: bool = True


@dataclass
class TeamPermissions:
    """Team-specific permission overrides"""
    
    team_name: str
    can_override_blocks: bool = False
    can_disable_audit: bool = False
    max_override_count: int = 3  # Per day
    required_approval_level: AuditLevel = AuditLevel.SOFT_BLOCK
    custom_thresholds: Optional[Dict[str, Any]] = None


class AuditConfig:
    """Main configuration manager for audit system"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._find_config_file()
        self.flags = FeatureFlags()
        self.team_permissions: Dict[str, TeamPermissions] = {}
        self.load_config()
        
    def _find_config_file(self) -> Path:
        """Find configuration file in order of precedence"""
        # Check environment variable
        if env_path := os.environ.get("NETRA_AUDIT_CONFIG"):
            return Path(env_path)
        
        # Check standard locations
        locations = [
            Path(".netra-audit.json"),
            Path(".git/netra-audit-config.json"),
            Path("config/audit.json"),
            Path.home() / ".netra" / "audit-config.json"
        ]
        
        for loc in locations:
            if loc.exists():
                return loc
        
        # Default location
        return Path(".git/netra-audit-config.json")
    
    def load_config(self) -> None:
        """Load configuration from file"""
        if not self.config_path.exists():
            self.save_config()  # Create default
            return
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            # Load feature flags
            if "features" in data:
                for key, value in data["features"].items():
                    if hasattr(self.flags, key):
                        # Handle enums
                        if key == "duplicate_threshold":
                            setattr(self.flags, key, DuplicateThreshold[value])
                        elif key.endswith("_level"):
                            setattr(self.flags, key, AuditLevel(value))
                        else:
                            setattr(self.flags, key, value)
            
            # Load team permissions
            if "teams" in data:
                for team_data in data["teams"]:
                    team = TeamPermissions(**team_data)
                    self.team_permissions[team.team_name] = team
                    
        except Exception as e:
            print(f"Warning: Could not load audit config: {e}")
            print("Using default configuration")
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        # Convert to JSON-serializable format
        config_data = {
            "version": "1.0.0",
            "features": {
                k: v.value if isinstance(v, (AuditLevel, DuplicateThreshold)) else v
                for k, v in asdict(self.flags).items()
            },
            "teams": [
                asdict(team) for team in self.team_permissions.values()
            ]
        }
        
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def get_effective_level(self, category: str, team: Optional[str] = None) -> AuditLevel:
        """Get effective audit level considering team permissions"""
        base_level = getattr(self.flags, f"{category}_level", AuditLevel.OFF)
        
        if team and team in self.team_permissions:
            team_perms = self.team_permissions[team]
            if team_perms.required_approval_level.value > base_level.value:
                return team_perms.required_approval_level
        
        return base_level
    
    def can_bypass(self, message: str, team: Optional[str] = None) -> bool:
        """Check if commit can bypass audit"""
        # Check emergency bypass
        if self.flags.allow_emergency_bypass:
            for keyword in self.flags.bypass_keywords:
                if keyword.lower() in message.lower():
                    return True
        
        # Check team permissions
        if team and team in self.team_permissions:
            return self.team_permissions[team].can_override_blocks
        
        return self.flags.allow_user_override
    
    def should_block(self, level: AuditLevel) -> bool:
        """Determine if given level should block commit"""
        return level in [AuditLevel.SOFT_BLOCK, AuditLevel.HARD_BLOCK, AuditLevel.ENFORCE]
    
    def should_use_claude(self, category: str) -> bool:
        """Check if Claude analysis should be used for category"""
        if not self.flags.claude_analysis:
            return False
        
        level = self.get_effective_level(category)
        # Use Claude for anything above NOTIFY level
        return level.value >= AuditLevel.WARN.value
    
    def get_threshold(self, threshold_type: str, team: Optional[str] = None) -> Any:
        """Get threshold value with team overrides"""
        base_value = getattr(self.flags, threshold_type, None)
        
        if team and team in self.team_permissions:
            team_perms = self.team_permissions[team]
            if team_perms.custom_thresholds and threshold_type in team_perms.custom_thresholds:
                return team_perms.custom_thresholds[threshold_type]
        
        return base_value
    
    def update_flag(self, flag_name: str, value: Any) -> None:
        """Update a specific flag and save"""
        if hasattr(self.flags, flag_name):
            setattr(self.flags, flag_name, value)
            self.save_config()
        else:
            raise ValueError(f"Unknown flag: {flag_name}")
    
    def add_team(self, team: TeamPermissions) -> None:
        """Add or update team permissions"""
        self.team_permissions[team.team_name] = team
        self.save_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            "flags": asdict(self.flags),
            "teams": {
                name: asdict(team) 
                for name, team in self.team_permissions.items()
            }
        }
    
    def from_env(self) -> None:
        """Override config from environment variables"""
        env_mappings = {
            "NETRA_AUDIT_LEVEL": "duplicate_level",
            "NETRA_AUDIT_THRESHOLD": "duplicate_threshold",
            "NETRA_AUDIT_CLAUDE": "claude_analysis",
            "NETRA_AUDIT_BLOCK": "duplicate_level",
            "NETRA_AUDIT_BYPASS": "allow_emergency_bypass"
        }
        
        for env_var, flag_name in env_mappings.items():
            if value := os.environ.get(env_var):
                if flag_name.endswith("_level"):
                    self.update_flag(flag_name, AuditLevel(value.lower()))
                elif flag_name == "duplicate_threshold":
                    self.update_flag(flag_name, DuplicateThreshold[value.upper()])
                elif flag_name in ["claude_analysis", "allow_emergency_bypass"]:
                    self.update_flag(flag_name, value.lower() in ["true", "1", "yes"])


def get_default_config() -> AuditConfig:
    """Get default configuration instance"""
    config = AuditConfig()
    config.from_env()  # Apply environment overrides
    return config


if __name__ == "__main__":
    # CLI for configuration management
    import sys
    
    if len(sys.argv) > 1:
        config = get_default_config()
        
        if sys.argv[1] == "show":
            print(json.dumps(config.to_dict(), indent=2, default=str))
        
        elif sys.argv[1] == "set" and len(sys.argv) >= 4:
            flag_name = sys.argv[2]
            value = sys.argv[3]
            
            # Parse value type
            if value.lower() in ["true", "false"]:
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            
            config.update_flag(flag_name, value)
            print(f"Updated {flag_name} = {value}")
        
        elif sys.argv[1] == "init":
            config.save_config()
            print(f"Created config at {config.config_path}")
        
        else:
            print("Usage: audit_config.py [show|set <flag> <value>|init]")
    else:
        # Show current config
        config = get_default_config()
        print("Current Audit Configuration:")
        print(f"  Config file: {config.config_path}")
        print(f"  Duplicate Detection: {config.flags.duplicate_detection}")
        print(f"  Audit Level: {config.flags.duplicate_level.value}")
        print(f"  Claude Analysis: {config.flags.claude_analysis}")
        print(f"  Threshold: {config.flags.duplicate_threshold.value}")