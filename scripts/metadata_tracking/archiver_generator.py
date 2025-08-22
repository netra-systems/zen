#!/usr/bin/env python3
"""
Archiver Generator - Generates metadata archiver script
Focused module for archiver script creation
"""

from pathlib import Path

from .script_generator import ScriptGeneratorBase


class ArchiverGenerator(ScriptGeneratorBase):
    """Generates metadata archiver script"""

    def __init__(self, project_root: Path):
        super().__init__(project_root)
        self.script_filename = "metadata_archiver.py"

    def _get_archiver_imports(self) -> str:
        """Get archiver script imports"""
        header = self._get_script_header("Metadata Archiver - Archives AI agent metadata to audit log")
        
        imports = '''import os
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime'''
        
        argparse_import = self._get_argparse_imports()
        
        return self._combine_imports(header, imports, argparse_import)

    def _get_class_init(self) -> str:
        """Get archiver class initialization"""
        return '''class MetadataArchiver:
    """Archives metadata to audit log"""
    
    def __init__(self):
        self.db_path = Path.cwd() / "metadata_tracking.db"'''

    def _get_commit_method(self) -> str:
        """Get current commit hash method"""
        return '''    def get_current_commit(self) -> str:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()[:8]
        except subprocess.CalledProcessError:
            return "unknown"'''

    def _get_database_connection_method(self) -> str:
        """Get database connection method"""
        return '''    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def _execute_archive_query(self, cursor: sqlite3.Cursor, data: dict) -> None:
        """Execute archive query"""
        cursor.execute("""
            INSERT INTO metadata_audit_log (event_type, event_data, timestamp)
            VALUES (?, ?, ?)
        """, ("archive", json.dumps(data), datetime.now().isoformat()))'''

    def _get_archive_method(self) -> str:
        """Get archive metadata method"""
        return '''    def archive_metadata(self) -> bool:
        """Archive current metadata to database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            commit_hash = self.get_current_commit()
            archive_data = {"commit": commit_hash}
            
            self._execute_archive_query(cursor, archive_data)
            
            conn.commit()
            conn.close()
            
            print(f"[SUCCESS] Metadata archived for commit {commit_hash}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to archive metadata: {e}")
            return False'''

    def _get_verification_methods(self) -> str:
        """Get verification methods"""
        return '''    def verify_database(self) -> bool:
        """Verify database is accessible"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metadata_audit_log")
            conn.close()
            return True
        except Exception:
            return False

    def get_archive_count(self) -> int:
        """Get count of archived entries"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metadata_audit_log")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0'''

    def _get_main_function(self) -> str:
        """Get main function"""
        return '''def main():
    parser = argparse.ArgumentParser(description="Archive AI agent metadata")
    parser.add_argument("--archive", action="store_true", 
                       help="Archive current metadata")
    parser.add_argument("--verify", action="store_true",
                       help="Verify database connection")
    parser.add_argument("--count", action="store_true",
                       help="Show archive count")
    
    args = parser.parse_args()
    archiver = MetadataArchiver()
    
    if args.archive:
        archiver.archive_metadata()
    elif args.verify:
        if archiver.verify_database():
            print("[SUCCESS] Database connection verified")
        else:
            print("[ERROR] Database connection failed")
    elif args.count:
        count = archiver.get_archive_count()
        print(f"Archive entries: {count}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()'''

    def _generate_complete_content(self) -> str:
        """Generate complete archiver script content"""
        imports = self._get_archiver_imports()
        class_init = self._get_class_init()
        commit_method = self._get_commit_method()
        connection_method = self._get_database_connection_method()
        archive_method = self._get_archive_method()
        verification_methods = self._get_verification_methods()
        main_function = self._get_main_function()
        
        return f"""{imports}

{class_init}

{commit_method}

{connection_method}

{archive_method}

{verification_methods}


{main_function}"""

    def create_archiver_script(self) -> bool:
        """Create metadata archiver script"""
        content = self._generate_complete_content()
        return self._create_script(self.script_filename, content)

    def archiver_exists(self) -> bool:
        """Check if archiver script exists"""
        return self.script_exists(self.script_filename)