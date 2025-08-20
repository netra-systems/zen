"""
Database migration runner for dev launcher.
Handles automatic migration checks and execution during startup.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
from dev_launcher.utils import print_with_emoji

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Handles database migration checks and execution.
    
    Ensures database schema is up-to-date before starting services.
    """
    
    def __init__(self, project_root: Path, use_emoji: bool = True):
        """Initialize migration runner."""
        self.project_root = project_root
        self.use_emoji = use_emoji
        self.alembic_config_path = project_root / "config" / "alembic.ini"
        
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def check_and_run_migrations(self, env: Optional[Dict] = None) -> bool:
        """
        Check if migrations are needed and run them if necessary.
        
        Returns:
            bool: True if migrations were successful or not needed, False otherwise
        """
        # Check if we should skip migrations
        if self._should_skip_migrations(env):
            self._print("⏭️", "MIGRATIONS", "Skipping migrations (explicitly disabled)")
            return True
            
        # Check if database is configured
        database_url = self._get_database_url(env)
        if not database_url:
            self._print("⚠️", "MIGRATIONS", "No database URL configured, skipping migrations")
            return True
            
        if "mock" in database_url.lower():
            self._print("🎭", "MIGRATIONS", "Database in mock mode, skipping migrations")
            return True
        
        try:
            # Check current revision
            current_revision = self._get_current_revision(env)
            head_revision = self._get_head_revision(env)
            
            if current_revision == head_revision:
                self._print("✅", "MIGRATIONS", "Database schema is up-to-date")
                return True
            
            # Run migrations
            self._print("🔄", "MIGRATIONS", f"Migrating database from {current_revision or 'initial'} to {head_revision}")
            return self._run_migrations(env)
            
        except Exception as e:
            logger.error(f"Migration check failed: {e}")
            self._print("❌", "MIGRATIONS", f"Migration check failed: {e}")
            
            # In development, we can continue even if migrations fail
            if self._is_development_mode(env):
                self._print("⚠️", "MIGRATIONS", "Continuing despite migration errors (development mode)")
                return True
            return False
    
    def _should_skip_migrations(self, env: Optional[Dict] = None) -> bool:
        """Check if migrations should be skipped."""
        env = env or os.environ
        
        # Check various skip flags
        skip_flags = [
            env.get("SKIP_MIGRATIONS", "").lower() == "true",
            env.get("FAST_STARTUP_MODE", "").lower() == "true",
            "pytest" in sys.modules,
        ]
        
        return any(skip_flags)
    
    def _get_database_url(self, env: Optional[Dict] = None) -> Optional[str]:
        """Get database URL from environment."""
        env = env or os.environ
        
        # Try different database URL keys
        for key in ["DATABASE_URL", "POSTGRES_URL", "DB_URL"]:
            url = env.get(key)
            if url:
                return url
        
        return None
    
    def _get_current_revision(self, env: Optional[Dict] = None) -> Optional[str]:
        """Get current database revision using alembic."""
        try:
            cmd = [
                sys.executable, "-m", "alembic",
                "-c", str(self.alembic_config_path),
                "current"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env or os.environ,
                cwd=str(self.project_root),
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse output to get revision
                for line in result.stdout.split('\n'):
                    if "(head)" in line or "-> " in line:
                        # Extract revision hash
                        parts = line.split()
                        if parts:
                            return parts[0].strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not get current revision: {e}")
            return None
    
    def _get_head_revision(self, env: Optional[Dict] = None) -> Optional[str]:
        """Get head revision from alembic scripts."""
        try:
            cmd = [
                sys.executable, "-m", "alembic",
                "-c", str(self.alembic_config_path),
                "heads"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env or os.environ,
                cwd=str(self.project_root),
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse output to get head revision
                for line in result.stdout.split('\n'):
                    if line and not line.startswith(" "):
                        # Extract revision hash
                        parts = line.split()
                        if parts:
                            return parts[0].strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not get head revision: {e}")
            return None
    
    def _run_migrations(self, env: Optional[Dict] = None) -> bool:
        """Run database migrations to head."""
        try:
            self._print("🔨", "MIGRATIONS", "Running database migrations...")
            
            cmd = [
                sys.executable, "-m", "alembic",
                "-c", str(self.alembic_config_path),
                "upgrade", "head"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env or os.environ,
                cwd=str(self.project_root),
                timeout=30
            )
            
            if result.returncode == 0:
                self._print("✅", "MIGRATIONS", "Database migrations completed successfully")
                return True
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"Migration failed: {error_msg}")
                self._print("❌", "MIGRATIONS", f"Migration failed: {error_msg[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Migration timed out")
            self._print("⏱️", "MIGRATIONS", "Migration timed out")
            return False
        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            self._print("❌", "MIGRATIONS", f"Migration execution failed: {e}")
            return False
    
    def _is_development_mode(self, env: Optional[Dict] = None) -> bool:
        """Check if running in development mode."""
        env = env or os.environ
        
        # Check various development indicators
        dev_indicators = [
            env.get("ENVIRONMENT", "").lower() in ["dev", "development", "local"],
            env.get("ENV", "").lower() in ["dev", "development", "local"],
            env.get("NODE_ENV", "").lower() in ["development"],
            not env.get("PRODUCTION", "").lower() == "true",
        ]
        
        return any(dev_indicators)
    
    def create_tables_if_missing(self, env: Optional[Dict] = None) -> bool:
        """
        Create missing tables if they don't exist.
        This is a fallback for when migrations haven't been run.
        """
        try:
            # Try to import and use the app's table creation logic
            sys.path.insert(0, str(self.project_root))
            
            from app.db.postgres import initialize_postgres
            from app.config import settings
            
            # Override database URL if provided in env
            if env and "DATABASE_URL" in env:
                settings.database_url = env["DATABASE_URL"]
            
            # Initialize database (creates tables if missing)
            import asyncio
            asyncio.run(initialize_postgres())
            
            self._print("✅", "MIGRATIONS", "Database tables verified/created")
            return True
            
        except ImportError as e:
            logger.debug(f"Could not import database modules: {e}")
            return False
        except Exception as e:
            logger.error(f"Table creation failed: {e}")
            self._print("⚠️", "MIGRATIONS", f"Could not verify tables: {e}")
            return False