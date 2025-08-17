#!/usr/bin/env python3
"""
Status Manager - Handles metadata tracking system status
Focused module for status checking and reporting
"""

import json
from pathlib import Path
from typing import Dict, Any


class StatusManager:
    """Manages metadata tracking system status checks"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._setup_paths()

    def _setup_paths(self) -> None:
        """Setup all required paths"""
        self.git_hooks_dir = self.project_root / ".git" / "hooks"
        self.db_path = self.project_root / "metadata_tracking.db"
        self.config_path = self.project_root / "metadata_config.json"
        self.scripts_dir = self.project_root / "scripts"

    def _check_git_hooks(self) -> bool:
        """Check if git hooks are installed"""
        pre_commit = self.git_hooks_dir / "pre-commit"
        post_commit = self.git_hooks_dir / "post-commit"
        
        if not (pre_commit.exists() and post_commit.exists()):
            return False
        
        return self._validate_hook_content(pre_commit)

    def _validate_hook_content(self, hook_path: Path) -> bool:
        """Validate hook contains expected content"""
        try:
            with open(hook_path, 'r') as f:
                content = f.read()
            return "metadata_validator" in content
        except Exception:
            return False

    def _check_database(self) -> bool:
        """Check if database exists"""
        return self.db_path.exists()

    def _check_configuration(self) -> bool:
        """Check if configuration exists"""
        return self.config_path.exists()

    def _is_system_enabled(self) -> bool:
        """Check if system is enabled in configuration"""
        if not self._check_configuration():
            return False
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return config.get("enabled", False)
        except Exception:
            return False

    def _check_validator_script(self) -> bool:
        """Check if validator script exists"""
        validator_path = self.scripts_dir / "metadata_validator.py"
        return validator_path.exists()

    def _check_archiver_script(self) -> bool:
        """Check if archiver script exists"""
        archiver_path = self.scripts_dir / "metadata_archiver.py"
        return archiver_path.exists()

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of metadata tracking system"""
        status = {
            "enabled": self._is_system_enabled(),
            "git_hooks_installed": self._check_git_hooks(),
            "database_exists": self._check_database(),
            "configuration_exists": self._check_configuration(),
            "validator_exists": self._check_validator_script(),
            "archiver_exists": self._check_archiver_script()
        }
        
        return status

    def _format_status_item(self, label: str, is_good: bool) -> str:
        """Format status item for display"""
        status_text = "[YES]" if is_good else "[NO]"
        return f"  {label}: {status_text}"

    def _format_component_status(self, label: str, exists: bool) -> str:
        """Format component status for display"""
        status_text = "[EXISTS]" if exists else "[NOT FOUND]"
        return f"  {label}: {status_text}"

    def _format_installation_status(self, installed: bool) -> str:
        """Format installation status for display"""
        status_text = "[INSTALLED]" if installed else "[NOT INSTALLED]"
        return f"  Git Hooks: {status_text}"

    def _check_all_components(self, status: Dict[str, Any]) -> bool:
        """Check if all components are properly configured"""
        return all([
            status['enabled'],
            status['git_hooks_installed'],
            status['database_exists'],
            status['configuration_exists'],
            status['validator_exists'],
            status['archiver_exists']
        ])

    def print_status(self) -> None:
        """Print detailed status of metadata tracking system"""
        status = self.get_status()
        
        print("\n== AI Agent Metadata Tracking System Status ==\n")
        
        print(self._format_status_item("System Enabled", status['enabled']))
        print(self._format_installation_status(status['git_hooks_installed']))
        print(self._format_component_status("Database", status['database_exists']))
        print(self._format_component_status("Configuration", status['configuration_exists']))
        print(self._format_component_status("Validator Script", status['validator_exists']))
        print(self._format_component_status("Archiver Script", status['archiver_exists']))
        
        if self._check_all_components(status):
            print("\n[SUCCESS] All components are properly configured and running!")
        else:
            print("\n[WARNING] Some components are missing. Run with --activate to enable them.")

    def is_fully_configured(self) -> bool:
        """Check if system is fully configured"""
        status = self.get_status()
        return self._check_all_components(status)