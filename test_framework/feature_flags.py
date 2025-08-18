"""Test feature flags configuration and management.

This module provides a robust feature flagging system for tests, enabling:
1. TDD workflow with tests for features in development
2. 100% pass rate for enabled features
3. Clear visibility of disabled/in-progress features
4. Environment-based flag overrides
5. Feature readiness tracking
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum


class FeatureStatus(str, Enum):
    """Feature development status."""
    ENABLED = "enabled"          # Feature is complete and tests should pass
    IN_DEVELOPMENT = "in_development"  # Feature in progress, tests may fail
    DISABLED = "disabled"        # Feature disabled, tests should be skipped
    EXPERIMENTAL = "experimental"  # Feature is experimental, tests are optional


@dataclass
class FeatureFlag:
    """Feature flag configuration."""
    name: str
    status: FeatureStatus
    description: str
    owner: Optional[str] = None
    target_release: Optional[str] = None
    dependencies: Optional[Set[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def is_enabled(self) -> bool:
        """Check if feature is enabled for testing."""
        return self.status == FeatureStatus.ENABLED
    
    def should_skip(self) -> bool:
        """Check if tests should be skipped."""
        return self.status in [FeatureStatus.DISABLED, FeatureStatus.IN_DEVELOPMENT]


class FeatureFlagManager:
    """Manages feature flags for testing."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize feature flag manager.
        
        Args:
            config_path: Path to feature flags config file
        """
        self.config_path = config_path or self._get_default_config_path()
        self.flags: Dict[str, FeatureFlag] = {}
        self._load_flags()
        self._apply_env_overrides()
    
    def _get_default_config_path(self) -> Path:
        """Get default config path."""
        project_root = Path(__file__).parent.parent
        return project_root / "test_feature_flags.json"
    
    def _load_flags(self):
        """Load feature flags from config file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                for name, config in data.get("features", {}).items():
                    self.flags[name] = FeatureFlag(
                        name=name,
                        status=FeatureStatus(config["status"]),
                        description=config.get("description", ""),
                        owner=config.get("owner"),
                        target_release=config.get("target_release"),
                        dependencies=set(config.get("dependencies", [])),
                        metadata=config.get("metadata", {})
                    )
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides.
        
        Environment variables format:
        TEST_FEATURE_<FEATURE_NAME>=enabled|disabled|in_development|experimental
        """
        for key, value in os.environ.items():
            if key.startswith("TEST_FEATURE_"):
                feature_name = key[13:].lower()  # Remove prefix
                if feature_name in self.flags:
                    try:
                        self.flags[feature_name].status = FeatureStatus(value.lower())
                    except ValueError:
                        pass  # Invalid status, ignore
    
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            True if feature is enabled, False otherwise
        """
        if feature_name not in self.flags:
            # Default to enabled if not configured
            return True
        return self.flags[feature_name].is_enabled()
    
    def should_skip(self, feature_name: str) -> bool:
        """Check if tests for a feature should be skipped.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            True if tests should be skipped, False otherwise
        """
        if feature_name not in self.flags:
            return False
        return self.flags[feature_name].should_skip()
    
    def get_skip_reason(self, feature_name: str) -> str:
        """Get reason for skipping tests.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            Human-readable skip reason
        """
        if feature_name not in self.flags:
            return ""
        
        flag = self.flags[feature_name]
        if flag.status == FeatureStatus.IN_DEVELOPMENT:
            reason = f"Feature '{feature_name}' is in development"
            if flag.target_release:
                reason += f" (target: {flag.target_release})"
        elif flag.status == FeatureStatus.DISABLED:
            reason = f"Feature '{feature_name}' is disabled"
        elif flag.status == FeatureStatus.EXPERIMENTAL:
            reason = f"Feature '{feature_name}' is experimental"
        else:
            reason = ""
        
        return reason
    
    def get_enabled_features(self) -> Set[str]:
        """Get set of enabled features."""
        return {name for name, flag in self.flags.items() if flag.is_enabled()}
    
    def get_in_development_features(self) -> Set[str]:
        """Get set of features in development."""
        return {name for name, flag in self.flags.items() 
                if flag.status == FeatureStatus.IN_DEVELOPMENT}
    
    def get_disabled_features(self) -> Set[str]:
        """Get set of disabled features."""
        return {name for name, flag in self.flags.items() 
                if flag.status == FeatureStatus.DISABLED}
    
    def save_flags(self):
        """Save current flags to config file."""
        data = {
            "features": {
                name: {
                    "status": flag.status.value,
                    "description": flag.description,
                    "owner": flag.owner,
                    "target_release": flag.target_release,
                    "dependencies": list(flag.dependencies) if flag.dependencies else [],
                    "metadata": flag.metadata or {}
                }
                for name, flag in self.flags.items()
            }
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_flag(self, flag: FeatureFlag):
        """Add or update a feature flag.
        
        Args:
            flag: Feature flag to add
        """
        self.flags[flag.name] = flag
    
    def enable_feature(self, feature_name: str):
        """Enable a feature for testing.
        
        Args:
            feature_name: Name of the feature to enable
        """
        if feature_name in self.flags:
            self.flags[feature_name].status = FeatureStatus.ENABLED
    
    def disable_feature(self, feature_name: str):
        """Disable a feature for testing.
        
        Args:
            feature_name: Name of the feature to disable
        """
        if feature_name in self.flags:
            self.flags[feature_name].status = FeatureStatus.DISABLED


# Global instance for easy access
_manager: Optional[FeatureFlagManager] = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """Get the global feature flag manager instance."""
    global _manager
    if _manager is None:
        _manager = FeatureFlagManager()
    return _manager


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled.
    
    Args:
        feature_name: Name of the feature
        
    Returns:
        True if feature is enabled, False otherwise
    """
    return get_feature_flag_manager().is_enabled(feature_name)


def should_skip_feature(feature_name: str) -> bool:
    """Check if tests for a feature should be skipped.
    
    Args:
        feature_name: Name of the feature
        
    Returns:
        True if tests should be skipped, False otherwise
    """
    return get_feature_flag_manager().should_skip(feature_name)