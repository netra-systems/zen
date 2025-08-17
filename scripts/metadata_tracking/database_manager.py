#!/usr/bin/env python3
"""
Database Manager for Metadata Tracking
Handles database setup, schema creation, and connection management.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any


class DatabaseManager:
    """Manages database setup for metadata tracking."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.metadata_db_path = project_root / "metadata_tracking.db"
    
    def create_database(self) -> bool:
        """Create metadata tracking database."""
        try:
            conn = self._setup_connection()
            cursor = conn.cursor()
            
            self._create_tables(cursor)
            self._create_indices(cursor)
            self._finalize_setup(conn)
            
            print(f"[SUCCESS] Database created at {self.metadata_db_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Database creation failed: {e}")
            return False
    
    def _setup_connection(self):
        """Set up database connection."""
        return sqlite3.connect(self.metadata_db_path)
    
    def _create_tables(self, cursor) -> None:
        """Create database tables."""
        cursor.execute(self._get_ai_modifications_schema())
        cursor.execute(self._get_audit_log_schema())
        cursor.execute(self._get_rollback_history_schema())
    
    def _create_indices(self, cursor) -> None:
        """Create database indices for performance."""
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_ai_modifications_timestamp ON ai_modifications(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_ai_modifications_file_path ON ai_modifications(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)"
        ]
        
        for index in indices:
            cursor.execute(index)
    
    def _finalize_setup(self, conn) -> None:
        """Finalize database setup."""
        conn.commit()
        conn.close()
    
    def _get_ai_modifications_schema(self) -> str:
        """Get AI modifications table schema."""
        return """
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
                metadata_json TEXT
            )
        """
    
    def _get_audit_log_schema(self) -> str:
        """Get audit log table schema."""
        return """
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                user_id TEXT,
                session_id TEXT
            )
        """
    
    def _get_rollback_history_schema(self) -> str:
        """Get rollback history table schema."""
        return """
            CREATE TABLE IF NOT EXISTS rollback_history (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                target_commit TEXT NOT NULL,
                rollback_reason TEXT,
                rollback_status TEXT DEFAULT 'pending',
                affected_files TEXT,
                backup_path TEXT
            )
        """
    
    def get_status(self) -> Dict[str, Any]:
        """Get database status."""
        db_exists = self.metadata_db_path.exists()
        
        status = {
            "database_exists": db_exists,
            "database_path": str(self.metadata_db_path)
        }
        
        if db_exists:
            try:
                conn = sqlite3.connect(self.metadata_db_path)
                cursor = conn.cursor()
                
                # Check if tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                status.update({
                    "tables_created": len(tables) >= 3,
                    "table_count": len(tables),
                    "tables": tables
                })
                
                conn.close()
                
            except Exception as e:
                status["error"] = str(e)
        
        return status