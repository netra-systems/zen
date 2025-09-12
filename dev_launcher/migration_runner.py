"""
Database migration runner for dev launcher.
Handles automatic migration checks and execution during startup.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from shared.isolated_environment import get_env
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
            self._print("[U+23ED][U+FE0F]", "MIGRATIONS", "Skipping migrations (explicitly disabled)")
            return True
        
        # Check if PostgreSQL is in mock mode from service configuration
        if self._is_postgres_mock_mode():
            self._print("[U+1F3AD]", "MIGRATIONS", "PostgreSQL in mock mode, skipping migrations")
            return True
            
        # Check if database is configured
        database_url = self._get_database_url(env)
        if not database_url:
            self._print(" WARNING: [U+FE0F]", "MIGRATIONS", "No database URL configured, skipping migrations")
            return True
            
        if "mock" in database_url.lower():
            self._print("[U+1F3AD]", "MIGRATIONS", "Database in mock mode, skipping migrations")
            return True
        
        try:
            # Check current revision
            current_revision = self._get_current_revision(env)
            head_revision = self._get_head_revision(env)
            
            if current_revision == head_revision:
                self._print(" PASS: ", "MIGRATIONS", "Database schema is up-to-date")
                return True
            
            # Run migrations
            self._print(" CYCLE: ", "MIGRATIONS", f"Migrating database from {current_revision or 'initial'} to {head_revision}")
            return self._run_migrations(env)
            
        except Exception as e:
            logger.error(f"Migration check failed: {e}")
            self._print(" FAIL: ", "MIGRATIONS", f"Migration check failed: {e}")
            
            # In development, we can continue even if migrations fail
            if self._is_development_mode(env):
                self._print(" WARNING: [U+FE0F]", "MIGRATIONS", "Continuing despite migration errors (development mode)")
                return True
            return False
    
    def _should_skip_migrations(self, env: Optional[Dict] = None) -> bool:
        """Check if migrations should be skipped."""
        isolated_env = get_env()
        env = env or isolated_env.get_subprocess_env()
        
        # Check various skip flags
        skip_flags = [
            env.get("SKIP_MIGRATIONS", "").lower() == "true",
            env.get("FAST_STARTUP_MODE", "").lower() == "true",
            "pytest" in sys.modules,
        ]
        
        return any(skip_flags)
    
    def _is_postgres_mock_mode(self) -> bool:
        """Check if PostgreSQL service is configured in mock mode."""
        import json
        
        try:
            # Check dev launcher service config
            config_path = self.project_root / ".dev_services.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    postgres_config = config.get("postgres", {})
                    return postgres_config.get("mode") == "mock"
        except Exception:
            pass  # Ignore errors in config reading
        
        # Also check environment variable
        isolated_env = get_env()
        return isolated_env.get("POSTGRES_MODE", "").lower() == "mock"
    
    def _get_database_url(self, env: Optional[Dict] = None) -> Optional[str]:
        """Get database URL from environment."""
        isolated_env = get_env()
        env = env or isolated_env.get_subprocess_env()
        
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
                env=env or isolated_env.get_subprocess_env(),
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
                env=env or isolated_env.get_subprocess_env(),
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
            self._print("[U+1F528]", "MIGRATIONS", "Running database migrations...")
            
            cmd = [
                sys.executable, "-m", "alembic",
                "-c", str(self.alembic_config_path),
                "upgrade", "head"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env or isolated_env.get_subprocess_env(),
                cwd=str(self.project_root),
                timeout=30
            )
            
            if result.returncode == 0:
                self._print(" PASS: ", "MIGRATIONS", "Database migrations completed successfully")
                return True
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"Migration failed: {error_msg}")
                self._print(" FAIL: ", "MIGRATIONS", f"Migration failed: {error_msg[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Migration timed out")
            self._print("[U+23F1][U+FE0F]", "MIGRATIONS", "Migration timed out")
            return False
        except Exception as e:
            logger.error(f"Migration execution failed: {e}")
            self._print(" FAIL: ", "MIGRATIONS", f"Migration execution failed: {e}")
            return False
    
    def _is_development_mode(self, env: Optional[Dict] = None) -> bool:
        """Check if running in development mode."""
        isolated_env = get_env()
        env = env or isolated_env.get_subprocess_env()
        
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
            
            from netra_backend.app.config import get_config
            from netra_backend.app.db.postgres import initialize_postgres
            
            config = get_config()
            # Override database URL if provided in env
            if env and "DATABASE_URL" in env:
                config.database_url = env["DATABASE_URL"]
            
            # Initialize database (creates tables if missing)
            import asyncio
            asyncio.run(initialize_postgres())
            
            self._print(" PASS: ", "MIGRATIONS", "Database tables verified/created")
            return True
            
        except ImportError as e:
            logger.debug(f"Could not import database modules: {e}")
            return False
        except Exception as e:
            logger.error(f"Table creation failed: {e}")
            self._print(" WARNING: [U+FE0F]", "MIGRATIONS", f"Could not verify tables: {e}")
            return False