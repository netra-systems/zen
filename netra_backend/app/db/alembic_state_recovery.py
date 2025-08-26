"""
Alembic State Recovery Utilities

Critical utilities for handling database migration state mismatches, specifically:
- Databases with existing schema but no alembic_version table
- Corrupted or inconsistent migration states
- Recovery strategies to prevent system startup failures

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate critical startup failures from migration state conflicts
- Value Impact: Prevents 100% system downtime and enables reliable deployments
- Strategic Impact: Ensures system resilience and operational continuity

This module implements the core fixes for the critical migration issue that blocks
system startup when databases exist but lack proper migration tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

import alembic.config
import alembic.command
import alembic.script
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

from netra_backend.app.db.migration_utils import (
    get_sync_database_url,
    create_alembic_config,
    get_head_revision
)
from netra_backend.app.core.unified_logging import get_logger

logger = get_logger(__name__)


class MigrationStateAnalyzer:
    """Analyzes database migration state to detect recovery scenarios."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.sync_url = get_sync_database_url(database_url)
        self.logger = logger
    
    async def analyze_migration_state(self) -> Dict[str, Any]:
        """
        Analyze current migration state and determine recovery strategy.
        
        Returns:
            Dictionary containing:
            - has_existing_schema: bool
            - has_alembic_version: bool  
            - requires_recovery: bool
            - recovery_strategy: str
            - current_revision: Optional[str]
            - existing_tables: List[str]
            - missing_expected_tables: List[str]
        """
        try:
            engine = create_engine(self.sync_url)
            
            with engine.connect() as conn:
                # Check for existing tables
                existing_tables = await self._get_existing_tables(conn)
                has_existing_schema = len(existing_tables) > 0
                
                # Check for alembic_version table
                has_alembic_version = "alembic_version" in existing_tables
                current_revision = None
                
                if has_alembic_version:
                    current_revision = await self._get_current_revision_safe(conn)
                
                # Determine recovery strategy
                recovery_info = self._determine_recovery_strategy(
                    has_existing_schema, has_alembic_version, existing_tables
                )
                
                return {
                    "has_existing_schema": has_existing_schema,
                    "has_alembic_version": has_alembic_version,
                    "requires_recovery": recovery_info["requires_recovery"],
                    "recovery_strategy": recovery_info["strategy"],
                    "current_revision": current_revision,
                    "existing_tables": existing_tables,
                    "missing_expected_tables": recovery_info.get("missing_tables", []),
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to analyze migration state: {e}")
            return {
                "has_existing_schema": False,
                "has_alembic_version": False,
                "requires_recovery": False,
                "recovery_strategy": "ANALYSIS_FAILED",
                "error": str(e),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_existing_tables(self, conn) -> List[str]:
        """Get list of existing tables in the database."""
        try:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            self.logger.warning(f"Could not retrieve existing tables: {e}")
            return []
    
    async def _get_current_revision_safe(self, conn) -> Optional[str]:
        """Safely get current revision from alembic_version table."""
        try:
            result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            return row[0] if row else None
        except Exception as e:
            self.logger.warning(f"Could not retrieve current revision: {e}")
            return None
    
    def _determine_recovery_strategy(
        self, has_existing_schema: bool, has_alembic_version: bool, existing_tables: List[str]
    ) -> Dict[str, Any]:
        """Determine the appropriate recovery strategy based on current state."""
        
        # Expected core tables from migrations
        expected_core_tables = {
            "users", "threads", "messages", "runs", "steps", 
            "analyses", "assistants", "secrets", "corpora"
        }
        
        existing_set = set(existing_tables)
        missing_tables = expected_core_tables - existing_set
        
        if not has_existing_schema:
            # Fresh database - normal migration path
            return {
                "requires_recovery": False,
                "strategy": "NORMAL_MIGRATION",
                "reason": "Fresh database, no existing schema"
            }
        
        if has_existing_schema and not has_alembic_version:
            # CRITICAL ISSUE: Schema exists but no migration tracking
            return {
                "requires_recovery": True,
                "strategy": "INITIALIZE_ALEMBIC_VERSION",
                "reason": "Existing schema without alembic_version table",
                "missing_tables": list(missing_tables)
            }
        
        if has_alembic_version and missing_tables:
            # Partial migration state
            return {
                "requires_recovery": True,
                "strategy": "COMPLETE_PARTIAL_MIGRATION", 
                "reason": "Alembic tracking exists but some tables missing",
                "missing_tables": list(missing_tables)
            }
        
        if has_alembic_version and not missing_tables:
            # Healthy state
            return {
                "requires_recovery": False,
                "strategy": "NO_ACTION_NEEDED",
                "reason": "Healthy migration state"
            }
        
        # Fallback
        return {
            "requires_recovery": False,
            "strategy": "MANUAL_INSPECTION_NEEDED",
            "reason": "Unknown state requiring manual inspection"
        }


class AlembicStateRecovery:
    """Handles recovery of various alembic migration states."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.sync_url = get_sync_database_url(database_url)
        self.logger = logger
    
    async def initialize_alembic_version_for_existing_schema(self) -> bool:
        """
        Initialize alembic_version table for existing schema.
        
        This is the CRITICAL fix for the main migration issue:
        - Database has existing schema but no alembic_version table
        - Creates alembic_version table and stamps it with current head
        - Enables normal migration flow to resume
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Initializing alembic_version table for existing schema...")
            
            # Step 1: Create alembic_version table if it doesn't exist
            success = await self._create_alembic_version_table()
            if not success:
                return False
            
            # Step 2: Stamp the database with current head revision
            success = await self._stamp_database_to_head()
            if not success:
                return False
            
            self.logger.info("Successfully initialized alembic_version table")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize alembic_version table: {e}")
            return False
    
    async def _create_alembic_version_table(self) -> bool:
        """Create the alembic_version table if it doesn't exist."""
        try:
            engine = create_engine(self.sync_url)
            
            with engine.connect() as conn:
                # Check if table already exists
                inspector = inspect(engine)
                if "alembic_version" in inspector.get_table_names():
                    self.logger.info("alembic_version table already exists")
                    return True
                
                # Create alembic_version table
                conn.execute(text("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL, 
                        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                    )
                """))
                
                conn.commit()
                self.logger.info("Created alembic_version table")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create alembic_version table: {e}")
            return False
    
    async def _stamp_database_to_head(self) -> bool:
        """Stamp the database with the current head revision."""
        try:
            # Get alembic config
            cfg = create_alembic_config(self.sync_url)
            
            # Get current head revision
            head_revision = get_head_revision(cfg)
            
            if not head_revision:
                self.logger.error("Could not determine head revision")
                return False
            
            # Stamp database to head
            alembic.command.stamp(cfg, head_revision)
            
            self.logger.info(f"Stamped database to head revision: {head_revision}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stamp database to head: {e}")
            return False
    
    async def stamp_existing_schema_to_head(self) -> bool:
        """
        Stamp existing schema to head revision.
        Alternative approach to initialize_alembic_version_for_existing_schema.
        """
        try:
            cfg = create_alembic_config(self.sync_url)
            alembic.command.stamp(cfg, "head")
            
            self.logger.info("Successfully stamped existing schema to head")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stamp schema to head: {e}")
            return False
    
    async def repair_corrupted_alembic_version(self) -> bool:
        """Repair corrupted alembic_version table."""
        try:
            engine = create_engine(self.sync_url)
            
            with engine.connect() as conn:
                # Clear existing entries
                conn.execute(text("DELETE FROM alembic_version"))
                
                # Get current head and insert it
                cfg = create_alembic_config(self.sync_url)
                head_revision = get_head_revision(cfg)
                
                if head_revision:
                    conn.execute(
                        text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                        {"version": head_revision}
                    )
                    conn.commit()
                    
                    self.logger.info(f"Repaired alembic_version with revision: {head_revision}")
                    return True
                else:
                    self.logger.error("Could not determine head revision for repair")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to repair alembic_version table: {e}")
            return False
    
    async def complete_partial_migration(self) -> bool:
        """Complete a partial migration by running migrations to head."""
        try:
            cfg = create_alembic_config(self.sync_url)
            alembic.command.upgrade(cfg, "head")
            
            self.logger.info("Completed partial migration to head")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to complete partial migration: {e}")
            return False


class MigrationStateManager:
    """High-level manager for migration state analysis and recovery."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.analyzer = MigrationStateAnalyzer(database_url)
        self.recovery = AlembicStateRecovery(database_url)
        self.logger = logger
    
    async def ensure_healthy_migration_state(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Ensure database is in healthy migration state.
        
        This is the main entry point for handling migration state issues.
        Analyzes current state and applies appropriate recovery strategies.
        
        Returns:
            Tuple of (success: bool, state_info: Dict)
        """
        try:
            # Analyze current state
            state = await self.analyzer.analyze_migration_state()
            
            self.logger.info(f"Migration state analysis: {state['recovery_strategy']}")
            
            if not state["requires_recovery"]:
                self.logger.info("Migration state is healthy, no recovery needed")
                return True, state
            
            # Apply recovery strategy
            recovery_success = await self._apply_recovery_strategy(
                state["recovery_strategy"], state
            )
            
            if recovery_success:
                # Re-analyze to verify recovery
                updated_state = await self.analyzer.analyze_migration_state()
                return True, updated_state
            else:
                self.logger.error("Migration state recovery failed")
                return False, state
                
        except Exception as e:
            self.logger.error(f"Failed to ensure healthy migration state: {e}")
            return False, {"error": str(e)}
    
    async def _apply_recovery_strategy(
        self, strategy: str, state: Dict[str, Any]
    ) -> bool:
        """Apply the appropriate recovery strategy."""
        
        if strategy == "INITIALIZE_ALEMBIC_VERSION":
            self.logger.info("Applying INITIALIZE_ALEMBIC_VERSION recovery strategy")
            return await self.recovery.initialize_alembic_version_for_existing_schema()
        
        elif strategy == "COMPLETE_PARTIAL_MIGRATION":
            self.logger.info("Applying COMPLETE_PARTIAL_MIGRATION recovery strategy")
            return await self.recovery.complete_partial_migration()
        
        elif strategy == "REPAIR_CORRUPTED_ALEMBIC":
            self.logger.info("Applying REPAIR_CORRUPTED_ALEMBIC recovery strategy")  
            return await self.recovery.repair_corrupted_alembic_version()
        
        elif strategy == "NO_ACTION_NEEDED":
            self.logger.info("No recovery action needed")
            return True
        
        else:
            self.logger.warning(f"Unknown recovery strategy: {strategy}")
            return False
    
    async def get_migration_status_report(self) -> Dict[str, Any]:
        """Get comprehensive migration status report."""
        state = await self.analyzer.analyze_migration_state()
        
        return {
            "database_url": self.database_url,
            "migration_state": state,
            "health_status": "HEALTHY" if not state["requires_recovery"] else "REQUIRES_RECOVERY",
            "recommended_action": state["recovery_strategy"],
            "timestamp": datetime.utcnow().isoformat()
        }


# Convenience functions for easy integration
async def ensure_migration_state_healthy(database_url: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to ensure migration state is healthy.
    
    This is the main function that other parts of the system should call
    to handle migration state issues.
    """
    manager = MigrationStateManager(database_url)
    return await manager.ensure_healthy_migration_state()


async def analyze_migration_state(database_url: str) -> Dict[str, Any]:
    """Convenience function to analyze migration state."""
    analyzer = MigrationStateAnalyzer(database_url)
    return await analyzer.analyze_migration_state()


# Export main classes and functions
__all__ = [
    "MigrationStateAnalyzer",
    "AlembicStateRecovery", 
    "MigrationStateManager",
    "ensure_migration_state_healthy",
    "analyze_migration_state"
]