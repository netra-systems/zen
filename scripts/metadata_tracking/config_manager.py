#!/usr/bin/env python3
"""
Configuration Manager - Handles metadata tracking configuration
Focused module for configuration operations
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class ConfigurationManager:
    """Manages metadata tracking configuration"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_path = self._get_config_path()

    def _get_config_path(self) -> Path:
        """Get configuration file path"""
        return self.project_root / "metadata_config.json"

    def _get_risk_levels_config(self) -> Dict[str, Dict[str, Any]]:
        """Get risk levels configuration"""
        return {
            "Low": {"review_required": False, "auto_approve_score": 90},
            "Medium": {"review_required": False, "auto_approve_score": 85},
            "High": {"review_required": True, "auto_approve_score": 95},
            "Critical": {"review_required": True, "auto_approve_score": 100}
        }

    def _get_file_patterns_config(self) -> Dict[str, list]:
        """Get file patterns configuration"""
        return {
            "high_risk": ["**/auth/**", "**/security/**", "**/payment/**", "**/supervisor*"],
            "medium_risk": ["**/agents/**", "**/services/**", "**/routes/**"],
            "low_risk": ["**/tests/**", "**/docs/**", "**/scripts/**"]
        }

    def _get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return {
            "alert_on_critical_changes": True,
            "alert_on_coverage_drop": True,
            "coverage_drop_threshold": 2,
            "daily_audit_report": True,
            "weekly_summary_report": True
        }

    def _get_integrations_config(self) -> Dict[str, bool]:
        """Get integrations configuration"""
        return {
            "test_automation": True,
            "ci_cd_pipeline": True,
            "code_review_tools": True,
            "monitoring_systems": True
        }

    def _get_settings_config(self) -> Dict[str, Any]:
        """Get main settings configuration"""
        return {
            "enforce_metadata": True,
            "block_commits_without_metadata": True,
            "auto_review_enabled": True,
            "auto_review_threshold": 85,
            "risk_levels": self._get_risk_levels_config(),
            "file_patterns": self._get_file_patterns_config(),
            "monitoring": self._get_monitoring_config()
        }

    def _create_config_structure(self) -> Dict[str, Any]:
        """Create complete configuration structure"""
        return {
            "enabled": True,
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "settings": self._get_settings_config(),
            "integrations": self._get_integrations_config()
        }

    def _write_config_file(self, config: Dict[str, Any]) -> bool:
        """Write configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception:
            return False

    def create_configuration(self) -> bool:
        """Create and save tracking configuration"""
        try:
            config = self._create_config_structure()
            
            if self._write_config_file(config):
                print(f"[SUCCESS] Configuration saved to {self.config_path}")
                return True
            else:
                print("[ERROR] Failed to write configuration file")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to save configuration: {e}")
            return False

    def config_exists(self) -> bool:
        """Check if configuration file exists"""
        return self.config_path.exists()

    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def is_enabled(self) -> bool:
        """Check if metadata tracking is enabled"""
        config = self.load_configuration()
        return config.get("enabled", False)