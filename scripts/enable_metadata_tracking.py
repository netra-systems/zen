#!/usr/bin/env python3
"""
AI Agent Metadata Tracking Enabler
Enables and configures comprehensive metadata tracking for AI modifications
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import argparse

class MetadataTrackingEnabler:
    """Enables and manages AI agent metadata tracking across the project"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.git_hooks_dir = self.project_root / ".git" / "hooks"
        self.scripts_dir = self.project_root / "scripts"
        self.metadata_db_path = self.project_root / "metadata_tracking.db"
        self.config_path = self.project_root / "metadata_config.json"
        
    def install_git_hooks(self) -> bool:
        """Install git hooks for metadata validation"""
        try:
            # Create hooks directory if it doesn't exist
            self.git_hooks_dir.mkdir(parents=True, exist_ok=True)
            
            # Pre-commit hook
            pre_commit_hook = self.git_hooks_dir / "pre-commit"
            pre_commit_content = """#!/bin/bash
# AI Agent Metadata Validation Hook

echo "Validating AI agent metadata headers..."

# Run metadata validator
python scripts/metadata_validator.py --validate-all

if [ $? -ne 0 ]; then
    echo "❌ Metadata validation failed. Please fix metadata headers before committing."
    exit 1
fi

echo "✅ Metadata validation passed"
exit 0
"""
            
            with open(pre_commit_hook, 'w') as f:
                f.write(pre_commit_content)
            
            # Make hook executable
            os.chmod(pre_commit_hook, 0o755)
            
            # Post-commit hook
            post_commit_hook = self.git_hooks_dir / "post-commit"
            post_commit_content = """#!/bin/bash
# AI Agent Metadata Archive Hook

echo "Archiving metadata to audit log..."

# Archive metadata
python scripts/metadata_archiver.py --archive

echo "✅ Metadata archived"
exit 0
"""
            
            with open(post_commit_hook, 'w') as f:
                f.write(post_commit_content)
            
            # Make hook executable
            os.chmod(post_commit_hook, 0o755)
            
            print("[SUCCESS] Git hooks installed successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to install git hooks: {e}")
            return False
    
    def create_metadata_database(self) -> bool:
        """Initialize metadata tracking database"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.metadata_db_path)
            cursor = conn.cursor()
            
            # Create main tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_modifications (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    agent_name TEXT,
                    agent_version TEXT,
                    task_description TEXT,
                    git_branch TEXT,
                    git_commit TEXT,
                    git_status TEXT,
                    change_type TEXT,
                    change_scope TEXT,
                    risk_level TEXT,
                    review_status TEXT DEFAULT 'Pending',
                    review_score INTEGER,
                    session_id TEXT,
                    sequence_number INTEGER,
                    lines_added INTEGER,
                    lines_modified INTEGER,
                    lines_deleted INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    modification_id TEXT,
                    event_type TEXT,
                    event_data TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (modification_id) REFERENCES ai_modifications(id)
                )
            """)
            
            # Create rollback history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rollback_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    modification_id TEXT,
                    rollback_command TEXT,
                    rollback_timestamp TEXT,
                    rollback_status TEXT,
                    rollback_by TEXT,
                    FOREIGN KEY (modification_id) REFERENCES ai_modifications(id)
                )
            """)
            
            # Create indices for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON ai_modifications(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON ai_modifications(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON ai_modifications(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_risk_level ON ai_modifications(risk_level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_review_status ON ai_modifications(review_status)")
            
            conn.commit()
            conn.close()
            
            print(f"[SUCCESS] Metadata database created at {self.metadata_db_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to create metadata database: {e}")
            return False
    
    def configure_tracking(self) -> bool:
        """Create and save tracking configuration"""
        try:
            config = {
                "enabled": True,
                "version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "settings": {
                    "enforce_metadata": True,
                    "block_commits_without_metadata": True,
                    "auto_review_enabled": True,
                    "auto_review_threshold": 85,
                    "risk_levels": {
                        "Low": {"review_required": False, "auto_approve_score": 90},
                        "Medium": {"review_required": False, "auto_approve_score": 85},
                        "High": {"review_required": True, "auto_approve_score": 95},
                        "Critical": {"review_required": True, "auto_approve_score": 100}
                    },
                    "file_patterns": {
                        "high_risk": ["**/auth/**", "**/security/**", "**/payment/**", "**/supervisor*"],
                        "medium_risk": ["**/agents/**", "**/services/**", "**/routes/**"],
                        "low_risk": ["**/tests/**", "**/docs/**", "**/scripts/**"]
                    },
                    "monitoring": {
                        "alert_on_critical_changes": True,
                        "alert_on_coverage_drop": True,
                        "coverage_drop_threshold": 2,
                        "daily_audit_report": True,
                        "weekly_summary_report": True
                    }
                },
                "integrations": {
                    "test_automation": True,
                    "ci_cd_pipeline": True,
                    "code_review_tools": True,
                    "monitoring_systems": True
                }
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"[SUCCESS] Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to save configuration: {e}")
            return False
    
    def create_validator_script(self) -> bool:
        """Create metadata validator script"""
        try:
            validator_path = self._get_validator_path()
            validator_content = self._generate_validator_content()
            return self._write_validator_script(validator_path, validator_content)
        except Exception as e:
            print(f"[ERROR] Failed to create validator script: {e}")
            return False
    
    def _get_validator_path(self) -> Path:
        """Get validator script path"""
        return self.scripts_dir / "metadata_validator.py"
    
    def _generate_validator_content(self) -> str:
        """Generate validator script content"""
        imports = self._get_validator_imports()
        class_def = self._get_validator_class()
        main_def = self._get_validator_main()
        return f"{imports}\n\n{class_def}\n\n{main_def}"
    
    def _get_validator_imports(self) -> str:
        """Get validator script imports"""
        return '''#!/usr/bin/env python3
"""
Metadata Validator - Validates AI agent metadata headers in modified files
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any'''
    
    def _get_validator_class(self) -> str:
        """Get validator class definition"""
        class_header = self._get_class_header()
        methods = self._get_class_methods()
        return f"{class_header}\n{methods}"
    
    def _get_class_header(self) -> str:
        """Get validator class header and constants"""
        return '''class MetadataValidator:
    """Validates metadata headers in files"""
    
    REQUIRED_FIELDS = [
        "Timestamp",
        "Agent",
        "Context",
        "Git",
        "Change",
        "Session",
        "Review"
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []'''
    
    def _get_class_methods(self) -> str:
        """Get validator class methods"""
        get_files = self._get_modified_files_method()
        validate_file = self._get_validate_file_method()
        validate_all = self._get_validate_all_method()
        return f"\n\n{get_files}\n\n{validate_file}\n\n{validate_all}"
    
    def _get_modified_files_method(self) -> str:
        """Get modified files method"""
        return '''    def get_modified_files(self) -> List[str]:
        """Get list of modified files from git"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                check=True
            )
            return [f for f in result.stdout.splitlines() if f.endswith(('.py', '.js', '.ts', '.jsx', '.tsx'))]
        except subprocess.CalledProcessError:
            return []'''
    
    def _get_validate_file_method(self) -> str:
        """Get validate file method"""
        return '''    def validate_file(self, file_path: str) -> bool:
        """Validate metadata header in a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(2000)  # Read first 2000 chars
            
            # Check for metadata header
            if "AI AGENT MODIFICATION METADATA" not in content:
                self.errors.append(f"{file_path}: Missing metadata header")
                return False
            
            # Validate required fields
            for field in self.REQUIRED_FIELDS:
                if field not in content[:1000]:
                    self.errors.append(f"{file_path}: Missing required field '{field}'")
                    return False
            
            # Validate timestamp format
            timestamp_match = re.search(r'Timestamp:\\s*(\\S+)', content)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                try:
                    from datetime import datetime
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    self.warnings.append(f"{file_path}: Invalid timestamp format")
            
            return True
            
        except Exception as e:
            self.errors.append(f"{file_path}: Error reading file - {e}")
            return False'''
    
    def _get_validate_all_method(self) -> str:
        """Get validate all method"""
        return '''    def validate_all(self) -> bool:
        """Validate all modified files"""
        files = self.get_modified_files()
        
        if not files:
            print("No modified files to validate")
            return True
        
        print(f"Validating {len(files)} modified files...")
        
        all_valid = True
        for file_path in files:
            if not self.validate_file(file_path):
                all_valid = False
        
        # Print results
        if self.errors:
            print("\\n❌ Validation Errors:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\\n⚠️  Validation Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if all_valid and not self.errors:
            print("\\n✅ All files have valid metadata headers")
        
        return all_valid and not self.errors'''
    
    def _get_validator_main(self) -> str:
        """Get validator main function"""
        return '''def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate AI agent metadata headers")
    parser.add_argument("--validate-all", action="store_true", help="Validate all modified files")
    parser.add_argument("--validate", help="Validate specific file")
    
    args = parser.parse_args()
    
    validator = MetadataValidator()
    
    if args.validate_all:
        success = validator.validate_all()
        sys.exit(0 if success else 1)
    elif args.validate:
        success = validator.validate_file(args.validate)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()'''
    
    def _write_validator_script(self, validator_path: Path, content: str) -> bool:
        """Write validator script to file"""
        with open(validator_path, 'w') as f:
            f.write(content)
        os.chmod(validator_path, 0o755)
        print(f"[SUCCESS] Validator script created at {validator_path}")
        return True
    
    def create_archiver_script(self) -> bool:
        """Create metadata archiver script"""
        try:
            archiver_path = self._get_archiver_path()
            archiver_content = self._generate_archiver_content()
            return self._write_archiver_script(archiver_path, archiver_content)
        except Exception as e:
            print(f"[ERROR] Failed to create archiver script: {e}")
            return False
    
    def _get_archiver_path(self) -> Path:
        """Get archiver script path"""
        return self.scripts_dir / "metadata_archiver.py"
    
    def _generate_archiver_content(self) -> str:
        """Generate archiver script content"""
        imports = self._get_archiver_imports()
        class_def = self._get_archiver_class()
        main_def = self._get_archiver_main()
        return f"{imports}\n\n{class_def}\n\n{main_def}"
    
    def _get_archiver_imports(self) -> str:
        """Get archiver script imports"""
        return '''#!/usr/bin/env python3
"""
Metadata Archiver - Archives AI agent metadata to audit log
"""

import os
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime'''
    
    def _get_archiver_class(self) -> str:
        """Get archiver class definition"""
        class_header = self._get_archiver_class_header()
        methods = self._get_archiver_class_methods()
        return f"{class_header}\n\n{methods}"
    
    def _get_archiver_class_header(self) -> str:
        """Get archiver class header"""
        return '''class MetadataArchiver:
    """Archives metadata to audit log"""
    
    def __init__(self):
        self.db_path = Path.cwd() / "metadata_tracking.db"'''
    
    def _get_archiver_class_methods(self) -> str:
        """Get archiver class methods"""
        get_commit = self._get_commit_method()
        archive_method = self._get_archive_method()
        return f"{get_commit}\n\n{archive_method}"
    
    def _get_commit_method(self) -> str:
        """Get commit hash method"""
        return '''    def get_current_commit(self) -> str:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()[:8]
        except subprocess.CalledProcessError:
            return "unknown"'''
    
    def _get_archive_method(self) -> str:
        """Get archive metadata method"""
        return '''    def archive_metadata(self) -> bool:
        """Archive current metadata to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            commit_hash = self.get_current_commit()
            timestamp = datetime.now().isoformat()
            
            # Log archive event
            cursor.execute("""
                INSERT INTO metadata_audit_log (event_type, event_data, timestamp)
                VALUES (?, ?, ?)
            """, ("archive", json.dumps({"commit": commit_hash}), timestamp))
            
            conn.commit()
            conn.close()
            
            print(f"[SUCCESS] Metadata archived for commit {commit_hash}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to archive metadata: {e}")
            return False'''
    
    def _get_archiver_main(self) -> str:
        """Get archiver main function"""
        return '''def main():
    import argparse
    parser = argparse.ArgumentParser(description="Archive AI agent metadata")
    parser.add_argument("--archive", action="store_true", help="Archive current metadata")
    
    args = parser.parse_args()
    
    archiver = MetadataArchiver()
    
    if args.archive:
        archiver.archive_metadata()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()'''
    
    def _write_archiver_script(self, archiver_path: Path, content: str) -> bool:
        """Write archiver script to file"""
        with open(archiver_path, 'w') as f:
            f.write(content)
        os.chmod(archiver_path, 0o755)
        print(f"[SUCCESS] Archiver script created at {archiver_path}")
        return True
    
    def enable_all(self) -> bool:
        """Enable all metadata tracking components"""
        print("\n[STARTING] Enabling AI Agent Metadata Tracking System...\n")
        
        success = True
        
        # Step 1: Install git hooks
        print("Step 1: Installing git hooks...")
        if not self.install_git_hooks():
            success = False
        
        # Step 2: Create metadata database
        print("\nStep 2: Creating metadata database...")
        if not self.create_metadata_database():
            success = False
        
        # Step 3: Save configuration
        print("\nStep 3: Saving configuration...")
        if not self.configure_tracking():
            success = False
        
        # Step 4: Create validator script
        print("\nStep 4: Creating validator script...")
        if not self.create_validator_script():
            success = False
        
        # Step 5: Create archiver script
        print("\nStep 5: Creating archiver script...")
        if not self.create_archiver_script():
            success = False
        
        if success:
            print("\n[COMPLETE] AI Agent Metadata Tracking System successfully enabled!")
            print("\nWhat's been set up:")
            print("  [OK] Git hooks for automatic validation")
            print("  [OK] SQLite database for metadata storage")
            print("  [OK] Configuration file with tracking settings")
            print("  [OK] Validator script for metadata checking")
            print("  [OK] Archiver script for audit logging")
            print("\nNext steps:")
            print("  1. All AI-modified files will now require metadata headers")
            print("  2. Commits will be blocked if metadata is missing or invalid")
            print("  3. Metadata will be automatically archived after each commit")
            print("  4. Run 'python scripts/metadata_validator.py --validate-all' to check existing files")
        else:
            print("\n[WARNING] Some components failed to install. Please check the errors above.")
        
        return success
    
    def status(self) -> Dict[str, Any]:
        """Check status of metadata tracking system"""
        status = {
            "enabled": False,
            "git_hooks_installed": False,
            "database_exists": False,
            "configuration_exists": False,
            "validator_exists": False,
            "archiver_exists": False
        }
        
        # Check git hooks
        pre_commit = self.git_hooks_dir / "pre-commit"
        post_commit = self.git_hooks_dir / "post-commit"
        if pre_commit.exists() and post_commit.exists():
            with open(pre_commit, 'r') as f:
                if "metadata_validator" in f.read():
                    status["git_hooks_installed"] = True
        
        # Check database
        if self.metadata_db_path.exists():
            status["database_exists"] = True
        
        # Check configuration
        if self.config_path.exists():
            status["configuration_exists"] = True
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                status["enabled"] = config.get("enabled", False)
        
        # Check scripts
        validator_path = self.scripts_dir / "metadata_validator.py"
        archiver_path = self.scripts_dir / "metadata_archiver.py"
        
        if validator_path.exists():
            status["validator_exists"] = True
        
        if archiver_path.exists():
            status["archiver_exists"] = True
        
        return status
    
    def print_status(self):
        """Print current status of metadata tracking system"""
        status = self.status()
        
        print("\n== AI Agent Metadata Tracking System Status ==\n")
        print(f"  System Enabled: {'[YES]' if status['enabled'] else '[NO]'}")
        print(f"  Git Hooks: {'[INSTALLED]' if status['git_hooks_installed'] else '[NOT INSTALLED]'}")
        print(f"  Database: {'[EXISTS]' if status['database_exists'] else '[NOT FOUND]'}")
        print(f"  Configuration: {'[EXISTS]' if status['configuration_exists'] else '[NOT FOUND]'}")
        print(f"  Validator Script: {'[EXISTS]' if status['validator_exists'] else '[NOT FOUND]'}")
        print(f"  Archiver Script: {'[EXISTS]' if status['archiver_exists'] else '[NOT FOUND]'}")
        
        all_good = all([
            status['enabled'],
            status['git_hooks_installed'],
            status['database_exists'],
            status['configuration_exists'],
            status['validator_exists'],
            status['archiver_exists']
        ])
        
        if all_good:
            print("\n[SUCCESS] All components are properly configured and running!")
        else:
            print("\n[WARNING] Some components are missing. Run with --activate to enable them.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enable AI Agent Metadata Tracking")
    parser.add_argument("--activate", action="store_true", help="Enable all tracking components")
    parser.add_argument("--status", action="store_true", help="Check current status")
    parser.add_argument("--install-hooks", action="store_true", help="Install git hooks only")
    parser.add_argument("--create-db", action="store_true", help="Create database only")
    
    args = parser.parse_args()
    
    enabler = MetadataTrackingEnabler()
    
    if args.activate:
        enabler.enable_all()
    elif args.status:
        enabler.print_status()
    elif args.install_hooks:
        enabler.install_git_hooks()
    elif args.create_db:
        enabler.create_metadata_database()
    else:
        # Default to showing status
        enabler.print_status()
        print("\nUse --activate to enable the metadata tracking system")


if __name__ == "__main__":
    main()