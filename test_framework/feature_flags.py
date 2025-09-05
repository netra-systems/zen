"""Feature flag management for test execution.

This module provides feature flag functionality to control test execution
and enable TDD workflows with conditional test skipping.
"""

import os
from enum import Enum
from typing import Dict, List, Optional, Set
import json
from pathlib import Path


class FeatureStatus(Enum):
    """Feature flag status enumeration."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    IN_DEVELOPMENT = "in_development"


class FeatureFlagManager:
    """Manages feature flags for test execution control."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize feature flag manager.
        
        Args:
            config_path: Optional path to feature flag configuration file
        """
        self.flags: Dict[str, FeatureStatus] = {}
        self._load_default_flags()
        if config_path:
            self._load_config(config_path)
    
    def _load_default_flags(self):
        """Load default feature flags from environment variables."""
        # Check for common environment variables that might control features
        env_features = {
            "real_services": os.getenv("TEST_REAL_SERVICES", "false").lower() == "true",
            "real_llm": os.getenv("TEST_REAL_LLM", "false").lower() == "true",
            "fast_tests": os.getenv("TEST_FAST", "false").lower() == "true",
            "integration_tests": os.getenv("TEST_INTEGRATION", "true").lower() == "true",
            "e2e_tests": os.getenv("TEST_E2E", "true").lower() == "true",
        }
        
        for feature, enabled in env_features.items():
            if enabled:
                self.flags[feature] = FeatureStatus.ENABLED
            else:
                self.flags[feature] = FeatureStatus.DISABLED
    
    def _load_config(self, config_path: str):
        """Load feature flags from configuration file.
        
        Args:
            config_path: Path to JSON configuration file
        """
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    
                features = config.get("features", {})
                for feature, status in features.items():
                    if isinstance(status, str):
                        try:
                            self.flags[feature] = FeatureStatus(status)
                        except ValueError:
                            self.flags[feature] = FeatureStatus.DISABLED
                    elif isinstance(status, bool):
                        self.flags[feature] = FeatureStatus.ENABLED if status else FeatureStatus.DISABLED
        except (json.JSONDecodeError, IOError):
            # If config file is malformed or unreadable, continue with defaults
            pass
    
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature_name: Name of the feature to check
            
        Returns:
            True if feature is enabled, False otherwise
        """
        status = self.flags.get(feature_name, FeatureStatus.DISABLED)
        return status == FeatureStatus.ENABLED
    
    def is_in_development(self, feature_name: str) -> bool:
        """Check if a feature is in development.
        
        Args:
            feature_name: Name of the feature to check
            
        Returns:
            True if feature is in development, False otherwise
        """
        status = self.flags.get(feature_name, FeatureStatus.DISABLED)
        return status == FeatureStatus.IN_DEVELOPMENT
    
    def should_skip(self, feature_name: str) -> bool:
        """Determine if tests for a feature should be skipped.
        
        Args:
            feature_name: Name of the feature to check
            
        Returns:
            True if tests should be skipped, False otherwise
        """
        status = self.flags.get(feature_name, FeatureStatus.DISABLED)
        return status in [FeatureStatus.DISABLED, FeatureStatus.IN_DEVELOPMENT]
    
    def get_enabled_features(self) -> Set[str]:
        """Get set of enabled features.
        
        Returns:
            Set of feature names that are enabled
        """
        return {name for name, status in self.flags.items() if status == FeatureStatus.ENABLED}
    
    def get_disabled_features(self) -> Set[str]:
        """Get set of disabled features.
        
        Returns:
            Set of feature names that are disabled
        """
        return {name for name, status in self.flags.items() if status == FeatureStatus.DISABLED}
    
    def get_in_development_features(self) -> Set[str]:
        """Get set of features in development.
        
        Returns:
            Set of feature names that are in development
        """
        return {name for name, status in self.flags.items() if status == FeatureStatus.IN_DEVELOPMENT}
    
    def set_feature(self, feature_name: str, status: FeatureStatus):
        """Set the status of a feature flag.
        
        Args:
            feature_name: Name of the feature
            status: New status for the feature
        """
        self.flags[feature_name] = status
    
    def enable_feature(self, feature_name: str):
        """Enable a feature flag.
        
        Args:
            feature_name: Name of the feature to enable
        """
        self.flags[feature_name] = FeatureStatus.ENABLED
    
    def disable_feature(self, feature_name: str):
        """Disable a feature flag.
        
        Args:
            feature_name: Name of the feature to disable
        """
        self.flags[feature_name] = FeatureStatus.DISABLED


# Global feature flag manager instance
_global_manager: Optional[FeatureFlagManager] = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """Get the global feature flag manager instance.
    
    Returns:
        Global FeatureFlagManager instance
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = FeatureFlagManager()
    return _global_manager


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled.
    
    Args:
        feature_name: Name of the feature to check
        
    Returns:
        True if feature is enabled, False otherwise
    """
    manager = get_feature_flag_manager()
    return manager.is_enabled(feature_name)


def should_skip_feature(feature_name: str) -> bool:
    """Determine if tests for a feature should be skipped.
    
    Args:
        feature_name: Name of the feature to check
        
    Returns:
        True if tests should be skipped, False otherwise
    """
    manager = get_feature_flag_manager()
    return manager.should_skip(feature_name)


def set_feature_status(feature_name: str, status: FeatureStatus):
    """Set the status of a feature flag.
    
    Args:
        feature_name: Name of the feature
        status: New status for the feature
    """
    manager = get_feature_flag_manager()
    manager.set_feature(feature_name, status)


def enable_feature(feature_name: str):
    """Enable a feature flag.
    
    Args:
        feature_name: Name of the feature to enable
    """
    manager = get_feature_flag_manager()
    manager.enable_feature(feature_name)


def disable_feature(feature_name: str):
    """Disable a feature flag.
    
    Args:
        feature_name: Name of the feature to disable
    """
    manager = get_feature_flag_manager()
    manager.disable_feature(feature_name)