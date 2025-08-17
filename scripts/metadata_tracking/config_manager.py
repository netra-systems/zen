#!/usr/bin/env python3
"""
Configuration Manager for Metadata Tracking
Handles configuration creation and management for metadata tracking system.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any


class ConfigManager:
    """Manages configuration for metadata tracking system."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_path = project_root / "metadata_config.json"
    
    def create_config(self) -> bool:
        """Create default configuration."""
        try:
            config = self._get_default_config()
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"[SUCCESS] Configuration created at {self.config_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to create configuration: {e}")
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration settings."""
        return {
            "metadata_tracking": {
                "enabled": True,
                "version": "1.0.0",
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            "validation": {
                "required_headers": [
                    "AI_AGENT_NAME",
                    "AI_AGENT_VERSION",
                    "AI_MODIFICATION_TIMESTAMP",
                    "AI_TASK_DESCRIPTION"
                ],
                "strict_mode": True,
                "allow_partial_headers": False
            },
            "database": {
                "path": "metadata_tracking.db",
                "backup_enabled": True,
                "backup_interval_hours": 24
            },
            "git_hooks": {
                "pre_commit_enabled": True,
                "post_commit_enabled": True,
                "validation_on_commit": True
            },
            "archiving": {
                "auto_archive": True,
                "retention_days": 365,
                "compress_old_entries": True
            },
            "notifications": {
                "email_alerts": False,
                "slack_webhook": "",
                "alert_on_validation_failure": True
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            if not self.config_path.exists():
                return self._get_default_config()
            
            with open(self.config_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"[WARNING] Failed to load config: {e}")
            return self._get_default_config()
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values."""
        try:
            config = self.load_config()
            config.update(updates)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to update config: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration status."""
        config_exists = self.config_path.exists()
        
        status = {
            "config_exists": config_exists,
            "config_path": str(self.config_path)
        }
        
        if config_exists:
            try:
                config = self.load_config()
                status.update({
                    "config_valid": True,
                    "tracking_enabled": config.get("metadata_tracking", {}).get("enabled", False),
                    "version": config.get("metadata_tracking", {}).get("version", "unknown")
                })
            except Exception as e:
                status.update({
                    "config_valid": False,
                    "error": str(e)
                })
        
        return status