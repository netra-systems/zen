#!/usr/bin/env python
"""
Configuration Change Tracker - SSOT for tracking configuration changes.

This module provides centralized tracking of configuration changes to prevent
regressions like the OAuth 503 errors. It monitors critical configuration
values and can detect changes, deletions, and potential cascade failures.

Based on CRITICAL_CONFIG_REGRESSION_AUDIT_REPORT.md requirements.
"""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of configuration changes."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class RiskLevel(Enum):
    """Risk levels for configuration changes."""
    CRITICAL = "critical"  # Could cause system failure
    HIGH = "high"         # Could impact functionality
    MEDIUM = "medium"     # May cause issues
    LOW = "low"          # Minimal impact
    INFO = "info"        # Informational only


@dataclass
class ConfigChange:
    """Represents a single configuration change."""
    timestamp: str
    key: str
    change_type: ChangeType
    old_value: Optional[str]
    new_value: Optional[str]
    risk_level: RiskLevel
    impact_analysis: str
    affected_services: List[str]
    requires_restart: bool = False
    requires_migration: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['change_type'] = self.change_type.value
        result['risk_level'] = self.risk_level.value
        return result


class ConfigChangeTracker:
    """
    Tracks configuration changes and analyzes their impact.
    
    This is the SSOT for configuration change tracking across the platform.
    """
    
    # Critical configs that cause cascade failures if changed incorrectly
    CRITICAL_CONFIGS = {
        'SERVICE_SECRET': {
            'risk': RiskLevel.CRITICAL,
            'services': ['auth_service', 'netra_backend', 'analytics_service'],
            'impact': '100% auth failure if missing/wrong',
            'dependencies': 173  # From SERVICE_SECRET analysis
        },
        'JWT_SECRET': {
            'risk': RiskLevel.CRITICAL,
            'services': ['auth_service', 'netra_backend'],
            'impact': 'All tokens invalid if changed',
            'dependencies': 50
        },
        'JWT_SECRET_KEY': {
            'risk': RiskLevel.CRITICAL,
            'services': ['auth_service', 'netra_backend'],
            'impact': 'JWT validation fails',
            'dependencies': 25
        },
        'JWT_SECRET_STAGING': {
            'risk': RiskLevel.HIGH,
            'services': ['auth_service', 'netra_backend'],
            'impact': 'Staging auth fails',
            'dependencies': 15
        },
        'AUTH_SERVICE_URL': {
            'risk': RiskLevel.CRITICAL,
            'services': ['netra_backend'],
            'impact': 'Cannot reach auth service',
            'dependencies': 30
        },
        'DATABASE_URL': {
            'risk': RiskLevel.CRITICAL,
            'services': ['netra_backend', 'auth_service'],
            'impact': 'No data persistence',
            'dependencies': 100
        },
        'REDIS_URL': {
            'risk': RiskLevel.HIGH,
            'services': ['netra_backend', 'auth_service'],
            'impact': 'No caching/sessions',
            'dependencies': 40
        }
    }
    
    # OAuth configs with dual naming
    OAUTH_CONFIGS = {
        'GOOGLE_CLIENT_ID': {'risk': RiskLevel.HIGH, 'pair': 'GOOGLE_CLIENT_SECRET'},
        'GOOGLE_CLIENT_SECRET': {'risk': RiskLevel.HIGH, 'pair': 'GOOGLE_CLIENT_ID'},
        'GOOGLE_OAUTH_CLIENT_ID_STAGING': {'risk': RiskLevel.HIGH, 'pair': 'GOOGLE_OAUTH_CLIENT_SECRET_STAGING'},
        'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': {'risk': RiskLevel.HIGH, 'pair': 'GOOGLE_OAUTH_CLIENT_ID_STAGING'},
        'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION': {'risk': RiskLevel.CRITICAL, 'pair': 'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION'},
        'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION': {'risk': RiskLevel.CRITICAL, 'pair': 'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION'},
    }
    
    def __init__(self, tracking_file: Optional[Path] = None):
        """
        Initialize the configuration change tracker.
        
        Args:
            tracking_file: Path to store change history (optional)
        """
        self.tracking_file = tracking_file or Path('config_changes.json')
        self.changes: List[ConfigChange] = []
        self.current_snapshot: Dict[str, str] = {}
        self.previous_snapshot: Dict[str, str] = {}
        self._lock = threading.Lock()
        
        # Load existing changes if file exists
        if self.tracking_file.exists():
            self._load_changes()
    
    def snapshot_current_config(self, config_dict: Dict[str, str]) -> None:
        """
        Take a snapshot of current configuration.
        
        Args:
            config_dict: Current configuration key-value pairs
        """
        with self._lock:
            self.previous_snapshot = self.current_snapshot.copy()
            self.current_snapshot = config_dict.copy()
    
    def detect_changes(self) -> List[ConfigChange]:
        """
        Detect changes between previous and current snapshots.
        
        Returns:
            List of detected configuration changes
        """
        detected_changes = []
        timestamp = datetime.utcnow().isoformat()
        
        with self._lock:
            # Check for added or modified keys
            for key, new_value in self.current_snapshot.items():
                old_value = self.previous_snapshot.get(key)
                
                if old_value is None:
                    # New configuration added
                    change = self._analyze_addition(key, new_value, timestamp)
                    detected_changes.append(change)
                elif old_value != new_value:
                    # Configuration modified
                    change = self._analyze_modification(key, old_value, new_value, timestamp)
                    detected_changes.append(change)
            
            # Check for deleted keys
            for key in self.previous_snapshot:
                if key not in self.current_snapshot:
                    # Configuration deleted
                    change = self._analyze_deletion(key, self.previous_snapshot[key], timestamp)
                    detected_changes.append(change)
            
            # Add to history
            self.changes.extend(detected_changes)
            
            # Save changes
            if detected_changes:
                self._save_changes()
        
        return detected_changes
    
    def _analyze_addition(self, key: str, value: str, timestamp: str) -> ConfigChange:
        """Analyze impact of adding a configuration."""
        risk_level = RiskLevel.LOW
        impact = f"New configuration added: {key}"
        affected_services = []
        requires_restart = False
        
        # Check if it's a critical config
        if key in self.CRITICAL_CONFIGS:
            config_info = self.CRITICAL_CONFIGS[key]
            risk_level = config_info['risk']
            impact = f"Critical config added - {config_info['impact']}"
            affected_services = config_info['services']
            requires_restart = True
        elif key in self.OAUTH_CONFIGS:
            config_info = self.OAUTH_CONFIGS[key]
            risk_level = config_info['risk']
            impact = f"OAuth config added - ensure {config_info['pair']} is also set"
            affected_services = ['auth_service', 'netra_backend']
            requires_restart = True
        
        return ConfigChange(
            timestamp=timestamp,
            key=key,
            change_type=ChangeType.ADDED,
            old_value=None,
            new_value=self._mask_sensitive(key, value),
            risk_level=risk_level,
            impact_analysis=impact,
            affected_services=affected_services,
            requires_restart=requires_restart
        )
    
    def _analyze_modification(self, key: str, old_value: str, new_value: str, timestamp: str) -> ConfigChange:
        """Analyze impact of modifying a configuration."""
        risk_level = RiskLevel.MEDIUM
        impact = f"Configuration modified: {key}"
        affected_services = []
        requires_restart = True
        requires_migration = False
        
        # Check if it's a critical config
        if key in self.CRITICAL_CONFIGS:
            config_info = self.CRITICAL_CONFIGS[key]
            risk_level = config_info['risk']
            impact = f"CRITICAL CHANGE - {config_info['impact']}"
            affected_services = config_info['services']
            requires_migration = key in ['JWT_SECRET', 'DATABASE_URL']
            
            # Special handling for SERVICE_SECRET
            if key == 'SERVICE_SECRET':
                impact = (f" ALERT:  ULTRA CRITICAL - SERVICE_SECRET changed! "
                         f"{config_info['dependencies']} dependencies affected. "
                         f"System-wide auth failure possible!")
        
        elif key in self.OAUTH_CONFIGS:
            config_info = self.OAUTH_CONFIGS[key]
            risk_level = config_info['risk']
            impact = f"OAuth config changed - verify {config_info['pair']} is consistent"
            affected_services = ['auth_service', 'netra_backend']
        
        return ConfigChange(
            timestamp=timestamp,
            key=key,
            change_type=ChangeType.MODIFIED,
            old_value=self._mask_sensitive(key, old_value),
            new_value=self._mask_sensitive(key, new_value),
            risk_level=risk_level,
            impact_analysis=impact,
            affected_services=affected_services,
            requires_restart=requires_restart,
            requires_migration=requires_migration
        )
    
    def _analyze_deletion(self, key: str, old_value: str, timestamp: str) -> ConfigChange:
        """Analyze impact of deleting a configuration."""
        risk_level = RiskLevel.HIGH
        impact = f"Configuration deleted: {key}"
        affected_services = []
        requires_restart = True
        
        # Check if it's a critical config
        if key in self.CRITICAL_CONFIGS:
            config_info = self.CRITICAL_CONFIGS[key]
            risk_level = RiskLevel.CRITICAL  # Deletion is always critical
            impact = f" ALERT:  CRITICAL DELETION - {config_info['impact']}"
            affected_services = config_info['services']
            
            # Special handling for SERVICE_SECRET
            if key == 'SERVICE_SECRET':
                impact = (f"[U+1F480] SYSTEM FAILURE IMMINENT - SERVICE_SECRET deleted! "
                         f"{config_info['dependencies']} dependencies will fail!")
        
        elif key in self.OAUTH_CONFIGS:
            config_info = self.OAUTH_CONFIGS[key]
            risk_level = RiskLevel.CRITICAL
            impact = f"OAuth config deleted - authentication will fail!"
            affected_services = ['auth_service', 'netra_backend']
        
        return ConfigChange(
            timestamp=timestamp,
            key=key,
            change_type=ChangeType.DELETED,
            old_value=self._mask_sensitive(key, old_value),
            new_value=None,
            risk_level=risk_level,
            impact_analysis=impact,
            affected_services=affected_services,
            requires_restart=requires_restart
        )
    
    def _mask_sensitive(self, key: str, value: Optional[str]) -> Optional[str]:
        """Mask sensitive configuration values."""
        if value is None:
            return None
        
        sensitive_patterns = [
            'SECRET', 'PASSWORD', 'KEY', 'TOKEN', 'CREDENTIAL',
            'PRIVATE', 'CLIENT_SECRET', 'JWT'
        ]
        
        # Check if key contains sensitive pattern
        key_upper = key.upper()
        for pattern in sensitive_patterns:
            if pattern in key_upper:
                # Show first 4 chars and mask rest
                if len(value) > 8:
                    return f"{value[:4]}...{value[-4:]}"
                else:
                    return "***MASKED***"
        
        # Non-sensitive, return as-is (truncated if too long)
        if len(value) > 50:
            return f"{value[:50]}..."
        return value
    
    def get_critical_changes(self) -> List[ConfigChange]:
        """Get all critical configuration changes."""
        with self._lock:
            return [c for c in self.changes if c.risk_level == RiskLevel.CRITICAL]
    
    def get_changes_by_service(self, service: str) -> List[ConfigChange]:
        """Get configuration changes affecting a specific service."""
        with self._lock:
            return [c for c in self.changes if service in c.affected_services]
    
    def get_recent_changes(self, hours: int = 24) -> List[ConfigChange]:
        """Get configuration changes within the specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()
        
        with self._lock:
            return [c for c in self.changes if c.timestamp > cutoff_str]
    
    def validate_config_consistency(self, config_dict: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        Validate configuration consistency and completeness.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check critical configs are present
        for key, info in self.CRITICAL_CONFIGS.items():
            if key not in config_dict:
                errors.append(f"Missing critical config: {key} - {info['impact']}")
        
        # Check OAuth pairs
        for key, info in self.OAUTH_CONFIGS.items():
            if key in config_dict:
                pair_key = info['pair']
                if pair_key not in config_dict:
                    errors.append(f"OAuth config {key} present but {pair_key} missing")
        
        # Check for conflicting environment configs
        env_specific = {
            'staging': ['JWT_SECRET_STAGING', 'GOOGLE_OAUTH_CLIENT_ID_STAGING'],
            'production': ['JWT_SECRET_PRODUCTION', 'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION']
        }
        
        current_env = config_dict.get('ENVIRONMENT', 'development')
        for env, configs in env_specific.items():
            if env != current_env:
                for config in configs:
                    if config in config_dict:
                        errors.append(f"{config} should not be set in {current_env} environment")
        
        return len(errors) == 0, errors
    
    def generate_change_report(self) -> str:
        """Generate a human-readable change report."""
        with self._lock:
            if not self.changes:
                return "No configuration changes detected."
            
            report = ["# Configuration Change Report\n"]
            report.append(f"**Total Changes:** {len(self.changes)}\n")
            
            # Group by risk level
            by_risk = {}
            for change in self.changes:
                risk = change.risk_level
                if risk not in by_risk:
                    by_risk[risk] = []
                by_risk[risk].append(change)
            
            # Report critical changes first
            if RiskLevel.CRITICAL in by_risk:
                report.append("\n##  ALERT:  CRITICAL Changes\n")
                for change in by_risk[RiskLevel.CRITICAL]:
                    report.append(f"- **{change.key}** ({change.change_type.value})")
                    report.append(f"  - Impact: {change.impact_analysis}")
                    report.append(f"  - Services: {', '.join(change.affected_services)}")
                    if change.requires_migration:
                        report.append("  -  WARNING: [U+FE0F] REQUIRES DATA MIGRATION")
                    report.append("")
            
            # Report other changes
            for risk in [RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW, RiskLevel.INFO]:
                if risk in by_risk:
                    report.append(f"\n## {risk.value.upper()} Risk Changes\n")
                    for change in by_risk[risk]:
                        report.append(f"- **{change.key}** ({change.change_type.value})")
                        if change.impact_analysis:
                            report.append(f"  - {change.impact_analysis}")
            
            return '\n'.join(report)
    
    def _save_changes(self) -> None:
        """Save changes to tracking file."""
        try:
            with open(self.tracking_file, 'w') as f:
                data = {
                    'changes': [c.to_dict() for c in self.changes],
                    'current_snapshot_hash': self._hash_snapshot(self.current_snapshot),
                    'timestamp': datetime.utcnow().isoformat()
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config changes: {e}")
    
    def _load_changes(self) -> None:
        """Load changes from tracking file."""
        try:
            with open(self.tracking_file, 'r') as f:
                data = json.load(f)
                # Reconstruct ConfigChange objects
                # (simplified - would need proper deserialization)
                logger.info(f"Loaded {len(data.get('changes', []))} historical changes")
        except Exception as e:
            logger.error(f"Failed to load config changes: {e}")
    
    def _hash_snapshot(self, snapshot: Dict[str, str]) -> str:
        """Generate hash of configuration snapshot."""
        # Sort keys for consistent hashing
        sorted_items = sorted(snapshot.items())
        content = json.dumps(sorted_items, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


# Singleton instance
_tracker_instance: Optional[ConfigChangeTracker] = None
_tracker_lock = threading.Lock()

def get_config_tracker() -> ConfigChangeTracker:
    """Get the singleton configuration change tracker instance."""
    global _tracker_instance
    
    if _tracker_instance is None:
        with _tracker_lock:
            if _tracker_instance is None:
                _tracker_instance = ConfigChangeTracker()
    
    return _tracker_instance


# Import timedelta for recent changes
from datetime import timedelta