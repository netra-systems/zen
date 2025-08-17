#!/usr/bin/env python3
"""
Archiver Script Generator for Metadata Tracking
Generates the metadata archiver script for post-commit processing.
"""

from pathlib import Path
from typing import Dict, Any


class ArchiverGenerator:
    """Generates archiver script for metadata tracking."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.scripts_dir = project_root / "scripts"
    
    def create_script(self) -> bool:
        """Create archiver script."""
        try:
            archiver_path = self._get_path()
            content = self._generate_content()
            success = self._write_script(archiver_path, content)
            
            if success:
                print(f"[SUCCESS] Archiver script created at {archiver_path}")
            
            return success
            
        except Exception as e:
            print(f"[ERROR] Failed to create archiver script: {e}")
            return False
    
    def _get_path(self) -> Path:
        """Get archiver script path."""
        return self.scripts_dir / "metadata_archiver.py"
    
    def _generate_content(self) -> str:
        """Generate complete archiver script content."""
        return f"""{self._get_imports()}

{self._get_class()}

{self._get_main()}
"""
    
    def _get_imports(self) -> str:
        """Get archiver script imports."""
        return '''#!/usr/bin/env python3
"""
AI Agent Metadata Archiver
Archives metadata to audit log after commits
"""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import argparse
import uuid'''
    
    def _get_class(self) -> str:
        """Get archiver class definition."""
        return f'''{self._get_class_header()}

{self._get_class_methods()}'''
    
    def _get_class_header(self) -> str:
        """Get archiver class header."""
        return '''class MetadataArchiver:
    """Archives AI agent metadata to audit log"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.db_path = self.project_root / "metadata_tracking.db"'''
    
    def _get_class_methods(self) -> str:
        """Get archiver class methods."""
        return f'''{self._get_commit_method()}

{self._get_archive_method()}'''
    
    def _get_commit_method(self) -> str:
        """Get commit info method."""
        return '''    def get_commit_info(self) -> Dict[str, Any]:
        """Get latest commit information"""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H|%s|%an|%ae|%ad"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split('|')
                return {
                    "commit_hash": parts[0],
                    "commit_message": parts[1],
                    "author_name": parts[2],
                    "author_email": parts[3],
                    "commit_date": parts[4]
                }
            
            return {}
            
        except Exception:
            return {}'''
    
    def _get_archive_method(self) -> str:
        """Get archive method."""
        return '''    def archive_metadata(self) -> bool:
        """Archive metadata to audit log"""
        try:
            if not self.db_path.exists():
                print("[WARNING] Metadata database not found")
                return True  # Don't fail if DB doesn't exist
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            commit_info = self.get_commit_info()
            
            if not commit_info:
                print("[WARNING] Could not get commit information")
                return True
            
            # Insert audit log entry
            audit_entry = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "COMMIT_ARCHIVED",
                "details": json.dumps(commit_info),
                "user_id": commit_info.get("author_email", "unknown"),
                "session_id": commit_info.get("commit_hash", "unknown")
            }
            
            cursor.execute("""
                INSERT INTO audit_log 
                (id, timestamp, action, details, user_id, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                audit_entry["id"],
                audit_entry["timestamp"],
                audit_entry["action"],
                audit_entry["details"],
                audit_entry["user_id"],
                audit_entry["session_id"]
            ))
            
            conn.commit()
            conn.close()
            
            print(f"[SUCCESS] Metadata archived for commit {commit_info['commit_hash'][:8]}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to archive metadata: {e}")
            return False'''
    
    def _get_main(self) -> str:
        """Get main function."""
        return '''def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Archive AI agent metadata")
    parser.add_argument("--archive", action="store_true", 
                       help="Archive metadata for latest commit")
    
    args = parser.parse_args()
    archiver = MetadataArchiver()
    
    if args.archive:
        success = archiver.archive_metadata()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()'''
    
    def _write_script(self, archiver_path: Path, content: str) -> bool:
        """Write archiver script to file."""
        try:
            archiver_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(archiver_path, 'w') as f:
                f.write(content)
            
            # Make script executable on Unix systems
            try:
                import stat
                current_mode = archiver_path.stat().st_mode
                archiver_path.chmod(current_mode | stat.S_IEXEC)
            except:
                pass  # Windows doesn't need executable permissions
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to write archiver script: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get archiver script status."""
        archiver_path = self._get_path()
        
        return {
            "archiver_script_exists": archiver_path.exists(),
            "archiver_path": str(archiver_path)
        }