#!/usr/bin/env python3
"""
Database Manager - Handles metadata database setup and management
Focused module for database operations
"""

import sqlite3
from pathlib import Path
from typing import Any, Tuple


class DatabaseManager:
    """Manages metadata tracking database operations"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.db_path = self._get_database_path()

    def _get_database_path(self) -> Path:
        """Get database file path"""
        return self.project_root / "metadata_tracking.db"

    def _get_ai_modifications_schema(self) -> str:
        """Get AI modifications table schema"""
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
                review_score INTEGER,
                session_id TEXT,
                sequence_number INTEGER,
                lines_added INTEGER,
                lines_modified INTEGER,
                lines_deleted INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """

    def _get_audit_log_schema(self) -> str:
        """Get audit log table schema"""
        return """
            CREATE TABLE IF NOT EXISTS metadata_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modification_id TEXT,
                event_type TEXT,
                event_data TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (modification_id) REFERENCES ai_modifications(id)
            )
        """

    def _get_rollback_history_schema(self) -> str:
        """Get rollback history table schema"""
        return """
            CREATE TABLE IF NOT EXISTS rollback_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modification_id TEXT,
                rollback_command TEXT,
                rollback_timestamp TEXT,
                rollback_status TEXT,
                rollback_by TEXT,
                FOREIGN KEY (modification_id) REFERENCES ai_modifications(id)
            )
        """

    def _setup_connection(self) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        """Setup and return database connection"""
        conn = sqlite3.connect(self.db_path)
        return conn, conn.cursor()

    def _create_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create all database tables"""
        cursor.execute(self._get_ai_modifications_schema())
        cursor.execute(self._get_audit_log_schema())
        cursor.execute(self._get_rollback_history_schema())

    def _create_indices(self, cursor: sqlite3.Cursor) -> None:
        """Create database indices for performance"""
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_file_path ON ai_modifications(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON ai_modifications(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_session_id ON ai_modifications(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_risk_level ON ai_modifications(risk_level)",
            "CREATE INDEX IF NOT EXISTS idx_review_status ON ai_modifications(review_status)"
        ]
        
        for index_sql in indices:
            cursor.execute(index_sql)

    def _finalize_setup(self, conn: sqlite3.Connection) -> None:
        """Finalize database setup"""
        conn.commit()
        conn.close()
        print(f"[SUCCESS] Metadata database created at {self.db_path}")

    def create_database(self) -> bool:
        """Initialize metadata tracking database"""
        try:
            conn, cursor = self._setup_connection()
            self._create_tables(cursor)
            self._create_indices(cursor)
            self._finalize_setup(conn)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create metadata database: {e}")
            return False

    def database_exists(self) -> bool:
        """Check if database exists"""
        return self.db_path.exists()

    def validate_schema(self) -> bool:
        """Validate database schema is correct"""
        try:
            conn, cursor = self._setup_connection()
            
            # Check if required tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN 
                ('ai_modifications', 'metadata_audit_log', 'rollback_history')
            """)
            
            tables = cursor.fetchall()
            conn.close()
            
            return len(tables) == 3
        except Exception:
            return False