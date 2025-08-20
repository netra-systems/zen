"""Core Tests - Split from test_staging_database_migration_validation.py

    BVJ: Protects data integrity for all customers, preventing data loss and compliance violations.
    Priority: P0 - Data corruption would cause immediate customer churn.
"""

import asyncio
import pytest
import time
import os
import subprocess
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime
import json
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import hashlib

    def __init__(self):
        """Initialize database migration validator."""
        self.is_staging = os.getenv("ENVIRONMENT", "local") == "staging"
        
        # Database configuration
        if self.is_staging:
            # Cloud SQL format: postgresql://user:pass@/db?host=/cloudsql/instance
            self.db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://netra:password@/netra_staging?host=/cloudsql/netra-staging:us-central1:netra-db"
            )
            # For Alembic, must use synchronous URL (not postgresql+asyncpg)
            self.alembic_db_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
        else:
            self.db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost:5432/netra_test"
            )
            self.alembic_db_url = self.db_url
        
        # Migration paths
        self.alembic_ini = "app/alembic.ini"
        self.migrations_dir = "app/alembic/versions"
        
        # Test data for validation
        self.test_schema_validations = {
            "users": ["id", "email", "created_at", "tier"],
            "threads": ["id", "user_id", "created_at", "status"],
            "messages": ["id", "thread_id", "content", "created_at"],
            "api_keys": ["id", "user_id", "key_hash", "created_at"]
        }

    def get_db_connection(self):
        """Get direct database connection for validation."""
        try:
            # Parse connection string
            if "/cloudsql/" in self.db_url:
                # Cloud SQL format
                parts = self.db_url.split("?")
                base = parts[0].replace("postgresql://", "")
                user_pass, db = base.split("@/")
                user, password = user_pass.split(":")
                host = parts[1].replace("host=", "") if len(parts) > 1 else "localhost"
                
                return psycopg2.connect(
                    host=host,
                    database=db,
                    user=user,
                    password=password
                )
            else:
                # Standard format
                return psycopg2.connect(self.db_url)
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
