#!/usr/bin/env python3
"""
Metadata Tracking Enabler - Main orchestration module
Coordinates all metadata tracking components
"""

from pathlib import Path
from typing import Any, Dict

from scripts.metadata_tracking.archiver_generator import ArchiverGenerator
from scripts.metadata_tracking.config_manager import ConfigurationManager
from scripts.metadata_tracking.database_manager import DatabaseManager
from scripts.metadata_tracking.hooks_manager import GitHooksManager
from scripts.metadata_tracking.status_manager import StatusManager
from scripts.metadata_tracking.validator_generator import ValidatorGenerator


class MetadataTrackingEnabler:
    """Main enabler for AI agent metadata tracking system"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self._initialize_managers()

    def _initialize_managers(self) -> None:
        """Initialize all component managers"""
        self.hooks_manager = GitHooksManager(self.project_root)
        self.database_manager = DatabaseManager(self.project_root)
        self.config_manager = ConfigurationManager(self.project_root)
        self.validator_generator = ValidatorGenerator(self.project_root)
        self.archiver_generator = ArchiverGenerator(self.project_root)
        self.status_manager = StatusManager(self.project_root)

    def _install_git_hooks(self) -> bool:
        """Install git hooks for metadata validation"""
        print("Step 1: Installing git hooks...")
        return self.hooks_manager.install_hooks()

    def _create_database(self) -> bool:
        """Create metadata tracking database"""
        print("\nStep 2: Creating metadata database...")
        return self.database_manager.create_database()

    def _configure_tracking(self) -> bool:
        """Save tracking configuration"""
        print("\nStep 3: Saving configuration...")
        return self.config_manager.create_configuration()

    def _create_validator(self) -> bool:
        """Create validator script"""
        print("\nStep 4: Creating validator script...")
        return self.validator_generator.create_validator_script()

    def _create_archiver(self) -> bool:
        """Create archiver script"""
        print("\nStep 5: Creating archiver script...")
        return self.archiver_generator.create_archiver_script()

    def _execute_step(self, step_func) -> bool:
        """Execute a setup step and return success status"""
        try:
            return step_func()
        except Exception as e:
            print(f"[ERROR] Step failed: {e}")
            return False

    def _run_setup_steps(self) -> bool:
        """Run all setup steps in sequence"""
        steps = [
            self._install_git_hooks,
            self._create_database,
            self._configure_tracking,
            self._create_validator,
            self._create_archiver
        ]
        
        return all(self._execute_step(step) for step in steps)

    def _print_success_summary(self) -> None:
        """Print success summary"""
        print("\n[COMPLETE] AI Agent Metadata Tracking System successfully enabled!")
        print("\nWhat's been set up:")
        print("  [OK] Git hooks for automatic validation")
        print("  [OK] SQLite database for metadata storage")
        print("  [OK] Configuration file with tracking settings")
        print("  [OK] Validator script for metadata checking")
        print("  [OK] Archiver script for audit logging")

    def _print_next_steps(self) -> None:
        """Print next steps information"""
        print("\nNext steps:")
        print("  1. All AI-modified files will now require metadata headers")
        print("  2. Commits will be blocked if metadata is missing or invalid")
        print("  3. Metadata will be automatically archived after each commit")
        print("  4. Run 'python scripts/metadata_validator.py --validate-all' to check existing files")

    def _print_failure_warning(self) -> None:
        """Print failure warning"""
        print("\n[WARNING] Some components failed to install. Please check the errors above.")

    def enable_all(self) -> bool:
        """Enable all metadata tracking components"""
        print("\n[STARTING] Enabling AI Agent Metadata Tracking System...\n")
        
        success = self._run_setup_steps()
        
        if success:
            self._print_success_summary()
            self._print_next_steps()
        else:
            self._print_failure_warning()
        
        return success

    def status(self) -> Dict[str, Any]:
        """Get status of metadata tracking system"""
        return self.status_manager.get_status()

    def print_status(self) -> None:
        """Print current status of metadata tracking system"""
        self.status_manager.print_status()

    def install_git_hooks(self) -> bool:
        """Install git hooks only"""
        return self.hooks_manager.install_hooks()

    def create_metadata_database(self) -> bool:
        """Create database only"""
        return self.database_manager.create_database()