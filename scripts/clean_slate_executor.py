#!/usr/bin/env python3
"""
Clean Slate Executor for Netra Apex
Automates the clean slate process with safety checks
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class CleanSlateExecutor:
    """Executes clean slate operations for Netra Apex."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.log_file = self.root_dir / f"clean_slate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.dry_run = False
        self.backup_dir = self.root_dir / "backups" / f"pre_clean_slate_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def log(self, message: str, level: str = "INFO"):
        """Log message to file and console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        with open(self.log_file, "a") as f:
            f.write(log_message + "\n")
    
    def confirm_action(self, action: str) -> bool:
        """Confirm dangerous action with user."""
        if self.dry_run:
            self.log(f"DRY RUN: Would execute - {action}")
            return False
        response = input(f"\n WARNING: [U+FE0F]  {action}\nContinue? (yes/no): ")
        return response.lower() == "yes"
    
    def run_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run shell command with logging."""
        self.log(f"Running: {' '.join(cmd)}")
        if self.dry_run:
            self.log("DRY RUN: Command not executed")
            return subprocess.CompletedProcess(cmd, 0)
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        if result.returncode != 0:
            self.log(f"Command failed: {result.stderr}", "ERROR")
        return result
    
    def phase1_assessment(self):
        """Phase 1: Assessment and Backup."""
        self.log("="*50)
        self.log("PHASE 1: ASSESSMENT & BACKUP")
        self.log("="*50)
        
        # Check git status
        self.log("Checking git status...")
        result = self.run_command(["git", "status", "--porcelain"])
        if result.stdout:
            self.log("Uncommitted changes found:", "WARNING")
            self.log(result.stdout)
            if not self.confirm_action("Proceed with uncommitted changes?"):
                sys.exit(1)
        
        # Create backup directory
        self.log(f"Creating backup directory: {self.backup_dir}")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup critical files
        critical_files = [".env", "config/settings.yaml", "CLAUDE.md"]
        for file in critical_files:
            src = self.root_dir / file
            if src.exists():
                dst = self.backup_dir / file
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                self.log(f"Backed up: {file}")
        
        # Find legacy files
        self.log("Searching for legacy files...")
        legacy_patterns = ["*_old.*", "*_backup.*", "*_deprecated.*", "*_temp.*"]
        legacy_files = []
        for pattern in legacy_patterns:
            legacy_files.extend(self.root_dir.rglob(pattern))
        
        if legacy_files:
            self.log(f"Found {len(legacy_files)} legacy files")
            with open(self.backup_dir / "legacy_files.txt", "w") as f:
                for file in legacy_files:
                    f.write(str(file) + "\n")
    
    def phase2_database_reset(self):
        """Phase 2: Database Clean Slate."""
        self.log("="*50)
        self.log("PHASE 2: DATABASE RESET")
        self.log("="*50)
        
        if not self.confirm_action("Reset all databases? This will DELETE all data!"):
            self.log("Skipping database reset")
            return
        
        # Reset PostgreSQL
        self.log("Resetting PostgreSQL...")
        self.run_command([
            "python", "-c",
            "from netra_backend.app.db.postgres import Base, engine; "
            "Base.metadata.drop_all(bind=engine); "
            "print('PostgreSQL tables dropped')"
        ])
        
        # Run migrations
        self.log("Running Alembic migrations...")
        self.run_command(["alembic", "upgrade", "head"])
        
        self.log("Database reset complete")
    
    def phase3_code_cleanup(self):
        """Phase 3: Code Cleanup."""
        self.log("="*50)
        self.log("PHASE 3: CODE CLEANUP")
        self.log("="*50)
        
        # Remove test artifacts
        artifacts_to_remove = [
            "test_reports",
            "failing_tests.log",
            ".coverage",
            "htmlcov",
            ".pytest_cache",
            "__pycache__"
        ]
        
        for artifact in artifacts_to_remove:
            for path in self.root_dir.rglob(artifact):
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    self.log(f"Removed: {path}")
        
        # Check architecture compliance
        self.log("Checking architecture compliance...")
        result = self.run_command([
            "python", 
            str(self.root_dir / "scripts" / "check_architecture_compliance.py")
        ], check=False)
        
        if result.returncode != 0:
            self.log("Architecture violations found", "WARNING")
    
    def phase4_validation(self):
        """Phase 4: Validation."""
        self.log("="*50)
        self.log("PHASE 4: VALIDATION")
        self.log("="*50)
        
        # Run smoke tests
        self.log("Running smoke tests...")
        result = self.run_command([
            "python", "test_runner.py",
            "--level", "smoke"
        ], check=False)
        
        if result.returncode != 0:
            self.log("Smoke tests failed", "ERROR")
            return False
        
        # Run integration tests
        self.log("Running integration tests...")
        result = self.run_command([
            "python", "test_runner.py",
            "--level", "integration",
            "--no-coverage", "--fast-fail"
        ], check=False)
        
        if result.returncode != 0:
            self.log("Integration tests failed", "WARNING")
        
        return True
    
    def execute(self, dry_run: bool = False):
        """Execute the clean slate process."""
        self.dry_run = dry_run
        
        self.log("Starting Clean Slate Process")
        self.log(f"Dry run: {dry_run}")
        self.log(f"Log file: {self.log_file}")
        
        try:
            # Phase 1
            self.phase1_assessment()
            
            # Phase 2
            self.phase2_database_reset()
            
            # Phase 3
            self.phase3_code_cleanup()
            
            # Phase 4
            success = self.phase4_validation()
            
            if success:
                self.log("="*50)
                self.log("CLEAN SLATE COMPLETE!", "SUCCESS")
                self.log(f"Backup saved to: {self.backup_dir}")
                self.log(f"Log saved to: {self.log_file}")
            else:
                self.log("Clean slate completed with warnings", "WARNING")
                
        except Exception as e:
            self.log(f"Clean slate failed: {e}", "ERROR")
            self.log("Consider restoring from backup", "ERROR")
            raise

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean Slate Executor for Netra Apex")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--skip-backup", action="store_true", help="Skip backup phase")
    parser.add_argument("--skip-database", action="store_true", help="Skip database reset")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation phase")
    
    args = parser.parse_args()
    
    print("[U+1F9F9] NETRA APEX CLEAN SLATE EXECUTOR")
    print("="*50)
    print("This will reset your project to a clean state.")
    print("Make sure you have committed any important changes!")
    print("="*50)
    
    if not args.dry_run:
        response = input("\n WARNING: [U+FE0F]  This is NOT a dry run. Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    
    executor = CleanSlateExecutor()
    executor.execute(dry_run=args.dry_run)

if __name__ == "__main__":
    main()