#!/usr/bin/env python3
"""
Metadata Tracking Enabler
Main coordinator for enabling and managing metadata tracking system.
"""

from pathlib import Path
from typing import Any, Dict

from scripts.metadata_tracking.archiver_generator import ArchiverGenerator
from scripts.metadata_tracking.config_manager import ConfigManager
from scripts.metadata_tracking.database_manager import DatabaseManager
from scripts.metadata_tracking.git_hooks_manager import GitHooksManager
from scripts.metadata_tracking.validator_generator import ValidatorGenerator


class MetadataTrackingEnabler:
    """Main coordinator for metadata tracking system."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        
        # Initialize component managers
        self.git_hooks = GitHooksManager(self.project_root)
        self.database = DatabaseManager(self.project_root)
        self.validator = ValidatorGenerator(self.project_root)
        self.archiver = ArchiverGenerator(self.project_root)
        self.config = ConfigManager(self.project_root)
    
    def enable_all(self) -> bool:
        """Enable all metadata tracking components."""
        print("=== Enabling AI Agent Metadata Tracking ===")
        
        success_count = 0
        total_steps = 5
        
        # Step 1: Create configuration
        print("\n[1/5] Creating configuration...")
        if self.config.create_config():
            success_count += 1
        
        # Step 2: Create database
        print("\n[2/5] Setting up database...")
        if self.database.create_database():
            success_count += 1
        
        # Step 3: Generate validator script
        print("\n[3/5] Creating validator script...")
        if self.validator.create_script():
            success_count += 1
        
        # Step 4: Generate archiver script
        print("\n[4/5] Creating archiver script...")
        if self.archiver.create_script():
            success_count += 1
        
        # Step 5: Install git hooks
        print("\n[5/5] Installing git hooks...")
        if self.git_hooks.install_hooks():
            success_count += 1
        
        # Report results
        success = success_count == total_steps
        print(f"\n=== Setup Complete: {success_count}/{total_steps} steps successful ===")
        
        if success:
            print(" PASS:  Metadata tracking enabled successfully!")
            print("\nNext steps:")
            print("1. Review configuration in metadata_config.json")
            print("2. Test with: python scripts/metadata_validator.py --validate-all")
            print("3. Make a test commit to verify hooks are working")
        else:
            print(" FAIL:  Some setup steps failed. Check error messages above.")
        
        return success
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of metadata tracking system."""
        return {
            "project_root": str(self.project_root),
            "timestamp": self._get_timestamp(),
            "components": {
                "git_hooks": self.git_hooks.get_status(),
                "database": self.database.get_status(),
                "validator": self.validator.get_status(),
                "archiver": self.archiver.get_status(),
                "config": self.config.get_status()
            },
            "overall_status": self._calculate_overall_status()
        }
    
    def print_status(self):
        """Print formatted status report."""
        status = self.get_status()
        
        print("=== Metadata Tracking System Status ===")
        print(f"Project Root: {status['project_root']}")
        print(f"Timestamp: {status['timestamp']}")
        print(f"Overall Status: {status['overall_status']}")
        
        print("\n--- Component Status ---")
        
        for component, details in status['components'].items():
            print(f"\n{component.upper()}:")
            for key, value in details.items():
                status_icon = " PASS: " if value else " FAIL: "
                if isinstance(value, bool):
                    print(f"  {status_icon} {key}: {value}")
                else:
                    print(f"   PIN:  {key}: {value}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def _calculate_overall_status(self) -> str:
        """Calculate overall system status."""
        status = self.get_status()
        components = status['components']
        
        # Check critical components
        git_hooks_ok = components['git_hooks']['git_hooks_installed']
        database_ok = components['database']['database_exists']
        validator_ok = components['validator']['validator_script_exists']
        archiver_ok = components['archiver']['archiver_script_exists']
        config_ok = components['config']['config_exists']
        
        critical_components = [git_hooks_ok, database_ok, validator_ok, archiver_ok, config_ok]
        working_count = sum(critical_components)
        total_count = len(critical_components)
        
        if working_count == total_count:
            return "FULLY_ENABLED"
        elif working_count >= total_count * 0.8:
            return "MOSTLY_ENABLED"
        elif working_count >= total_count * 0.5:
            return "PARTIALLY_ENABLED"
        else:
            return "DISABLED"