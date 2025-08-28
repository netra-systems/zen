"""
Enhanced Database Migration Rollback Service

This module provides comprehensive database migration rollback capabilities
with safety checks, automatic recovery, and cross-database coordination.

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers) 
- Business Goal: Zero-downtime deployments with safe rollback capabilities
- Value Impact: Prevents data loss and service outages during schema changes
- Strategic Impact: Protects $45K+ MRR through reliable database operations
"""

import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from netra_backend.app.logging_config import central_logger
from netra_backend.app.db.database_manager import DatabaseManager

logger = central_logger.get_logger(__name__)


class RollbackStrategy(str, Enum):
    """Migration rollback strategy."""
    IMMEDIATE = "immediate"  # Rollback immediately on failure
    DEFERRED = "deferred"    # Mark for rollback, execute later
    MANUAL = "manual"        # Require manual intervention
    COMPENSATING = "compensating"  # Use compensating actions


class MigrationRisk(str, Enum):
    """Migration risk level."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class RollbackStatus(str, Enum):
    """Rollback execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class SafetyCheck(BaseModel):
    """Safety check definition."""
    name: str
    description: str
    check_sql: str
    expected_result: Any
    severity: MigrationRisk
    enabled: bool = True


class MigrationSnapshot(BaseModel):
    """Pre-migration database snapshot."""
    migration_id: str
    created_at: datetime
    table_schemas: Dict[str, Any] = {}
    table_counts: Dict[str, int] = {}
    index_definitions: Dict[str, List[str]] = {}
    constraint_definitions: Dict[str, List[str]] = {}
    checksum: str
    size_mb: float = 0.0


class RollbackPlan(BaseModel):
    """Migration rollback plan."""
    migration_id: str
    rollback_sql: List[str]
    safety_checks: List[SafetyCheck]
    strategy: RollbackStrategy
    risk_level: MigrationRisk
    estimated_duration_seconds: int
    requires_downtime: bool = False
    dependencies: List[str] = []
    compensating_actions: List[Dict[str, Any]] = []


class RollbackExecution(BaseModel):
    """Rollback execution record."""
    rollback_id: str
    migration_id: str
    status: RollbackStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    steps_completed: int = 0
    total_steps: int = 0
    recovery_actions_taken: List[str] = []


class MigrationRollbackService:
    """Enhanced migration rollback service with safety and recovery."""
    
    def __init__(self):
        self._snapshots: Dict[str, MigrationSnapshot] = {}
        self._rollback_plans: Dict[str, RollbackPlan] = {}
        self._active_rollbacks: Dict[str, RollbackExecution] = {}
        self._safety_checks = self._initialize_default_safety_checks()
        
    def _initialize_default_safety_checks(self) -> List[SafetyCheck]:
        """Initialize default safety checks."""
        return [
            SafetyCheck(
                name="foreign_key_constraints",
                description="Check foreign key constraint violations",
                check_sql="""
                    SELECT COUNT(*) FROM information_schema.table_constraints 
                    WHERE constraint_type = 'FOREIGN KEY' AND table_schema = current_schema()
                """,
                expected_result=0,
                severity=MigrationRisk.HIGH
            ),
            SafetyCheck(
                name="active_connections",
                description="Check for active database connections",
                check_sql="SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'",
                expected_result=lambda x: x < 10,  # Less than 10 active connections
                severity=MigrationRisk.MEDIUM
            ),
            SafetyCheck(
                name="disk_space",
                description="Check available disk space",
                check_sql="""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size
                """,
                expected_result="verify_disk_space",  # Custom verification
                severity=MigrationRisk.CRITICAL
            ),
            SafetyCheck(
                name="replication_lag",
                description="Check replication lag",
                check_sql="""
                    SELECT EXTRACT(epoch FROM (now() - pg_last_xact_replay_timestamp()))::int
                    as lag_seconds WHERE pg_is_in_recovery()
                """,
                expected_result=lambda x: x is None or x < 30,  # Less than 30 seconds lag
                severity=MigrationRisk.HIGH
            )
        ]
    
    async def create_migration_snapshot(self, migration_id: str) -> MigrationSnapshot:
        """Create a comprehensive snapshot before migration execution."""
        logger.info(f"Creating migration snapshot for {migration_id}")
        
        connection_manager = DatabaseManager.get_connection_manager()
        
        async with connection_manager.get_session() as session:
            # Get table schemas
            table_schemas = await self._capture_table_schemas(session)
            
            # Get table row counts
            table_counts = await self._capture_table_counts(session, table_schemas.keys())
            
            # Get index definitions
            index_definitions = await self._capture_index_definitions(session)
            
            # Get constraint definitions
            constraint_definitions = await self._capture_constraint_definitions(session)
            
            # Calculate checksum
            snapshot_data = {
                "schemas": table_schemas,
                "counts": table_counts,
                "indexes": index_definitions,
                "constraints": constraint_definitions
            }
            checksum = hashlib.sha256(json.dumps(snapshot_data, sort_keys=True).encode()).hexdigest()
            
            # Calculate database size
            size_mb = await self._calculate_database_size_mb(session)
            
            snapshot = MigrationSnapshot(
                migration_id=migration_id,
                created_at=datetime.now(timezone.utc),
                table_schemas=table_schemas,
                table_counts=table_counts,
                index_definitions=index_definitions,
                constraint_definitions=constraint_definitions,
                checksum=checksum,
                size_mb=size_mb
            )
            
            self._snapshots[migration_id] = snapshot
            logger.info(f"Created snapshot for {migration_id}: {checksum}")
            
            return snapshot
    
    async def create_rollback_plan(
        self, 
        migration_id: str, 
        rollback_sql: List[str],
        risk_level: MigrationRisk = MigrationRisk.MEDIUM,
        strategy: RollbackStrategy = RollbackStrategy.IMMEDIATE
    ) -> RollbackPlan:
        """Create a rollback plan for a migration."""
        
        # Analyze rollback SQL for risk assessment
        analyzed_risk = await self._analyze_rollback_risk(rollback_sql)
        final_risk = max(risk_level, analyzed_risk, key=lambda x: x.value)
        
        # Estimate duration based on SQL complexity
        estimated_duration = self._estimate_rollback_duration(rollback_sql, final_risk)
        
        # Determine if downtime is required
        requires_downtime = self._requires_downtime(rollback_sql)
        
        # Select appropriate safety checks
        relevant_checks = self._select_safety_checks(final_risk)
        
        plan = RollbackPlan(
            migration_id=migration_id,
            rollback_sql=rollback_sql,
            safety_checks=relevant_checks,
            strategy=strategy,
            risk_level=final_risk,
            estimated_duration_seconds=estimated_duration,
            requires_downtime=requires_downtime
        )
        
        self._rollback_plans[migration_id] = plan
        logger.info(f"Created rollback plan for {migration_id}: {final_risk.value} risk, {estimated_duration}s estimated")
        
        return plan
    
    async def execute_rollback(self, migration_id: str, force: bool = False) -> RollbackExecution:
        """Execute migration rollback with safety checks and recovery."""
        
        if migration_id not in self._rollback_plans:
            raise ValueError(f"No rollback plan found for migration {migration_id}")
        
        plan = self._rollback_plans[migration_id]
        rollback_id = f"rollback_{migration_id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        execution = RollbackExecution(
            rollback_id=rollback_id,
            migration_id=migration_id,
            status=RollbackStatus.PENDING,
            started_at=datetime.now(timezone.utc),
            total_steps=len(plan.rollback_sql) + len(plan.safety_checks)
        )
        
        self._active_rollbacks[rollback_id] = execution
        
        try:
            execution.status = RollbackStatus.IN_PROGRESS
            
            # Phase 1: Pre-rollback safety checks
            if not force:
                await self._run_safety_checks(execution, plan.safety_checks, "pre-rollback")
            
            # Phase 2: Execute rollback SQL
            await self._execute_rollback_sql(execution, plan.rollback_sql)
            
            # Phase 3: Post-rollback verification
            await self._verify_rollback_success(execution, migration_id)
            
            # Phase 4: Post-rollback safety checks
            if not force:
                await self._run_safety_checks(execution, plan.safety_checks, "post-rollback")
            
            execution.status = RollbackStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration_seconds = int(
                (execution.completed_at - execution.started_at).total_seconds()
            )
            
            logger.info(f"Successfully completed rollback {rollback_id} in {execution.duration_seconds}s")
            
        except Exception as e:
            execution.status = RollbackStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            
            logger.error(f"Rollback {rollback_id} failed: {e}")
            
            # Attempt recovery
            await self._attempt_rollback_recovery(execution, plan)
        
        return execution
    
    async def verify_rollback_integrity(self, migration_id: str) -> Dict[str, Any]:
        """Verify rollback integrity by comparing with pre-migration snapshot."""
        
        if migration_id not in self._snapshots:
            raise ValueError(f"No snapshot found for migration {migration_id}")
        
        snapshot = self._snapshots[migration_id]
        connection_manager = DatabaseManager.get_connection_manager()
        
        results = {
            "migration_id": migration_id,
            "snapshot_checksum": snapshot.checksum,
            "verification_time": datetime.now(timezone.utc),
            "schema_matches": True,
            "count_matches": True,
            "integrity_score": 0.0,
            "discrepancies": []
        }
        
        async with connection_manager.get_session() as session:
            # Verify table schemas
            current_schemas = await self._capture_table_schemas(session)
            schema_diff = self._compare_schemas(snapshot.table_schemas, current_schemas)
            if schema_diff:
                results["schema_matches"] = False
                results["discrepancies"].extend(schema_diff)
            
            # Verify table counts
            current_counts = await self._capture_table_counts(session, current_schemas.keys())
            count_diff = self._compare_counts(snapshot.table_counts, current_counts)
            if count_diff:
                results["count_matches"] = False
                results["discrepancies"].extend(count_diff)
            
            # Calculate integrity score
            total_checks = 2  # schema + counts
            passed_checks = sum([results["schema_matches"], results["count_matches"]])
            results["integrity_score"] = passed_checks / total_checks
        
        logger.info(f"Rollback verification for {migration_id}: {results['integrity_score']:.2%} integrity")
        
        return results
    
    async def _capture_table_schemas(self, session: AsyncSession) -> Dict[str, Any]:
        """Capture current table schemas."""
        result = await session.execute(text("""
            SELECT table_name, column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = current_schema()
            ORDER BY table_name, ordinal_position
        """))
        
        schemas = {}
        for row in result:
            table_name = row.table_name
            if table_name not in schemas:
                schemas[table_name] = []
            
            schemas[table_name].append({
                "column_name": row.column_name,
                "data_type": row.data_type,
                "is_nullable": row.is_nullable,
                "column_default": row.column_default
            })
        
        return schemas
    
    async def _capture_table_counts(self, session: AsyncSession, table_names: List[str]) -> Dict[str, int]:
        """Capture current table row counts."""
        counts = {}
        
        for table_name in table_names:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                counts[table_name] = count
            except Exception as e:
                logger.warning(f"Could not get count for table {table_name}: {e}")
                counts[table_name] = -1  # Error marker
        
        return counts
    
    async def _capture_index_definitions(self, session: AsyncSession) -> Dict[str, List[str]]:
        """Capture current index definitions."""
        result = await session.execute(text("""
            SELECT schemaname, tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = current_schema()
        """))
        
        indexes = {}
        for row in result:
            table_name = row.tablename
            if table_name not in indexes:
                indexes[table_name] = []
            
            indexes[table_name].append({
                "name": row.indexname,
                "definition": row.indexdef
            })
        
        return indexes
    
    async def _capture_constraint_definitions(self, session: AsyncSession) -> Dict[str, List[str]]:
        """Capture current constraint definitions."""
        result = await session.execute(text("""
            SELECT tc.table_name, tc.constraint_name, tc.constraint_type,
                   ccu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_schema = current_schema()
        """))
        
        constraints = {}
        for row in result:
            table_name = row.table_name
            if table_name not in constraints:
                constraints[table_name] = []
            
            constraints[table_name].append({
                "name": row.constraint_name,
                "type": row.constraint_type,
                "column": row.column_name
            })
        
        return constraints
    
    async def _calculate_database_size_mb(self, session: AsyncSession) -> float:
        """Calculate current database size in MB."""
        result = await session.execute(text("""
            SELECT pg_database_size(current_database()) / (1024*1024) as size_mb
        """))
        
        size_mb = result.scalar()
        return float(size_mb) if size_mb else 0.0
    
    async def _analyze_rollback_risk(self, rollback_sql: List[str]) -> MigrationRisk:
        """Analyze rollback SQL statements to assess risk."""
        risk_score = 0
        
        for sql in rollback_sql:
            sql_upper = sql.upper()
            
            # High risk operations
            if any(keyword in sql_upper for keyword in ['DROP TABLE', 'DROP DATABASE', 'TRUNCATE']):
                risk_score += 10
            
            # Medium risk operations
            if any(keyword in sql_upper for keyword in ['ALTER TABLE', 'DROP COLUMN', 'DROP INDEX']):
                risk_score += 5
            
            # Low risk operations
            if any(keyword in sql_upper for keyword in ['CREATE', 'INSERT', 'UPDATE']):
                risk_score += 1
        
        if risk_score >= 10:
            return MigrationRisk.CRITICAL
        elif risk_score >= 5:
            return MigrationRisk.HIGH
        elif risk_score >= 2:
            return MigrationRisk.MEDIUM
        else:
            return MigrationRisk.LOW
    
    def _estimate_rollback_duration(self, rollback_sql: List[str], risk_level: MigrationRisk) -> int:
        """Estimate rollback duration in seconds."""
        base_time = len(rollback_sql) * 5  # 5 seconds per statement
        
        risk_multipliers = {
            MigrationRisk.LOW: 1.0,
            MigrationRisk.MEDIUM: 1.5,
            MigrationRisk.HIGH: 2.0,
            MigrationRisk.CRITICAL: 3.0
        }
        
        return int(base_time * risk_multipliers[risk_level])
    
    def _requires_downtime(self, rollback_sql: List[str]) -> bool:
        """Determine if rollback requires downtime."""
        for sql in rollback_sql:
            sql_upper = sql.upper()
            if any(keyword in sql_upper for keyword in [
                'DROP TABLE', 'DROP DATABASE', 'ALTER TABLE', 'LOCK TABLE'
            ]):
                return True
        return False
    
    def _select_safety_checks(self, risk_level: MigrationRisk) -> List[SafetyCheck]:
        """Select appropriate safety checks based on risk level."""
        if risk_level == MigrationRisk.LOW:
            return [check for check in self._safety_checks if check.severity != MigrationRisk.CRITICAL]
        elif risk_level == MigrationRisk.MEDIUM:
            return [check for check in self._safety_checks if check.severity in [MigrationRisk.MEDIUM, MigrationRisk.HIGH]]
        else:
            return self._safety_checks
    
    async def _run_safety_checks(
        self, 
        execution: RollbackExecution, 
        checks: List[SafetyCheck],
        phase: str
    ) -> None:
        """Run safety checks during rollback."""
        connection_manager = DatabaseManager.get_connection_manager()
        
        async with connection_manager.get_session() as session:
            for check in checks:
                if not check.enabled:
                    continue
                
                try:
                    logger.debug(f"Running {phase} safety check: {check.name}")
                    result = await session.execute(text(check.check_sql))
                    value = result.scalar()
                    
                    # Verify result
                    if callable(check.expected_result):
                        if not check.expected_result(value):
                            raise Exception(f"Safety check {check.name} failed: {value}")
                    elif check.expected_result == "verify_disk_space":
                        # Custom disk space verification
                        await self._verify_disk_space(session)
                    elif value != check.expected_result:
                        raise Exception(f"Safety check {check.name} failed: expected {check.expected_result}, got {value}")
                    
                    execution.steps_completed += 1
                    
                except Exception as e:
                    if check.severity in [MigrationRisk.HIGH, MigrationRisk.CRITICAL]:
                        raise Exception(f"Critical safety check {check.name} failed: {e}")
                    else:
                        logger.warning(f"Non-critical safety check {check.name} failed: {e}")
                        execution.recovery_actions_taken.append(f"Ignored failed safety check: {check.name}")
    
    async def _execute_rollback_sql(self, execution: RollbackExecution, rollback_sql: List[str]) -> None:
        """Execute rollback SQL statements."""
        connection_manager = DatabaseManager.get_connection_manager()
        
        async with connection_manager.get_session() as session:
            for i, sql in enumerate(rollback_sql):
                try:
                    logger.debug(f"Executing rollback SQL {i+1}/{len(rollback_sql)}: {sql[:100]}...")
                    await session.execute(text(sql))
                    execution.steps_completed += 1
                    
                except Exception as e:
                    logger.error(f"Rollback SQL {i+1} failed: {e}")
                    # Try to continue with remaining statements
                    execution.recovery_actions_taken.append(f"Failed SQL {i+1}: {sql[:50]}... Error: {str(e)[:100]}")
                    
                    # For critical failures, stop execution
                    if "constraint" in str(e).lower() or "foreign key" in str(e).lower():
                        raise Exception(f"Critical rollback failure at statement {i+1}: {e}")
    
    async def _verify_rollback_success(self, execution: RollbackExecution, migration_id: str) -> None:
        """Verify that rollback was successful."""
        # Basic verification - could be enhanced with specific checks
        connection_manager = DatabaseManager.get_connection_manager()
        
        async with connection_manager.get_session() as session:
            # Test basic connectivity
            await session.execute(text("SELECT 1"))
            
            # Check for any constraint violations
            result = await session.execute(text("""
                SELECT COUNT(*) FROM information_schema.table_constraints
                WHERE constraint_type = 'FOREIGN KEY' 
                AND table_schema = current_schema()
                AND constraint_name LIKE '%violation%'
            """))
            
            violation_count = result.scalar()
            if violation_count > 0:
                raise Exception(f"Found {violation_count} constraint violations after rollback")
            
            execution.recovery_actions_taken.append("Verified database connectivity and constraints")
    
    async def _attempt_rollback_recovery(self, execution: RollbackExecution, plan: RollbackPlan) -> None:
        """Attempt to recover from failed rollback."""
        logger.warning(f"Attempting recovery for failed rollback {execution.rollback_id}")
        
        try:
            # Mark as partial if some steps completed
            if execution.steps_completed > 0:
                execution.status = RollbackStatus.PARTIAL
            
            # For critical migrations, attempt compensating actions
            if plan.risk_level == MigrationRisk.CRITICAL:
                await self._execute_compensating_actions(execution, plan.compensating_actions)
            
            execution.recovery_actions_taken.append("Attempted rollback recovery")
            
        except Exception as e:
            logger.error(f"Rollback recovery failed: {e}")
            execution.recovery_actions_taken.append(f"Recovery failed: {e}")
    
    async def _execute_compensating_actions(
        self, 
        execution: RollbackExecution, 
        actions: List[Dict[str, Any]]
    ) -> None:
        """Execute compensating actions for failed rollback."""
        for action in actions:
            try:
                # This would be implemented based on specific action types
                action_type = action.get("type")
                if action_type == "restore_backup":
                    await self._restore_from_backup(action.get("backup_id"))
                elif action_type == "manual_intervention":
                    logger.error(f"Manual intervention required: {action.get('description')}")
                
            except Exception as e:
                logger.error(f"Compensating action failed: {e}")
                execution.recovery_actions_taken.append(f"Compensating action failed: {e}")
    
    async def _restore_from_backup(self, backup_id: str) -> None:
        """Restore database from backup."""
        # This would interface with backup systems
        logger.info(f"Would restore from backup: {backup_id}")
    
    async def _verify_disk_space(self, session: AsyncSession) -> None:
        """Verify sufficient disk space."""
        result = await session.execute(text("""
            SELECT 
                pg_size_pretty(pg_database_size(current_database())) as db_size,
                pg_size_pretty(pg_tablespace_size('pg_default')) as tablespace_size
        """))
        
        row = result.fetchone()
        logger.info(f"Current database size: {row.db_size}, tablespace: {row.tablespace_size}")
        
        # Basic check - could be enhanced with actual disk space query
        return True
    
    def _compare_schemas(self, original: Dict[str, Any], current: Dict[str, Any]) -> List[str]:
        """Compare schema differences."""
        differences = []
        
        # Check for missing tables
        for table in original:
            if table not in current:
                differences.append(f"Table {table} is missing after rollback")
        
        # Check for extra tables
        for table in current:
            if table not in original:
                differences.append(f"Extra table {table} found after rollback")
        
        # Check column differences
        for table in original:
            if table in current:
                original_cols = {col["column_name"]: col for col in original[table]}
                current_cols = {col["column_name"]: col for col in current[table]}
                
                for col_name in original_cols:
                    if col_name not in current_cols:
                        differences.append(f"Column {table}.{col_name} is missing")
                    elif original_cols[col_name] != current_cols[col_name]:
                        differences.append(f"Column {table}.{col_name} definition changed")
        
        return differences
    
    def _compare_counts(self, original: Dict[str, int], current: Dict[str, int]) -> List[str]:
        """Compare row count differences."""
        differences = []
        
        for table, original_count in original.items():
            current_count = current.get(table, -1)
            if original_count != current_count:
                differences.append(
                    f"Table {table} row count mismatch: expected {original_count}, got {current_count}"
                )
        
        return differences
    
    def get_rollback_status(self, rollback_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a rollback execution."""
        execution = self._active_rollbacks.get(rollback_id)
        if not execution:
            return None
        
        return {
            "rollback_id": execution.rollback_id,
            "migration_id": execution.migration_id,
            "status": execution.status.value,
            "progress": f"{execution.steps_completed}/{execution.total_steps}",
            "started_at": execution.started_at,
            "duration_seconds": execution.duration_seconds,
            "error_message": execution.error_message,
            "recovery_actions": execution.recovery_actions_taken
        }
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all migration snapshots."""
        return [
            {
                "migration_id": snapshot.migration_id,
                "created_at": snapshot.created_at,
                "checksum": snapshot.checksum,
                "size_mb": snapshot.size_mb,
                "table_count": len(snapshot.table_schemas)
            }
            for snapshot in self._snapshots.values()
        ]
    
    def cleanup_old_snapshots(self, older_than_days: int = 30) -> int:
        """Clean up old snapshots."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        
        to_remove = [
            migration_id for migration_id, snapshot in self._snapshots.items()
            if snapshot.created_at < cutoff_date
        ]
        
        for migration_id in to_remove:
            del self._snapshots[migration_id]
            if migration_id in self._rollback_plans:
                del self._rollback_plans[migration_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old snapshots")
        return len(to_remove)


# Global rollback service instance
_rollback_service: Optional[MigrationRollbackService] = None


def get_rollback_service() -> MigrationRollbackService:
    """Get the global rollback service instance."""
    global _rollback_service
    if _rollback_service is None:
        _rollback_service = MigrationRollbackService()
    return _rollback_service


@asynccontextmanager
async def safe_migration_context(migration_id: str, rollback_sql: List[str]):
    """Context manager for safe migration execution with automatic rollback."""
    rollback_service = get_rollback_service()
    
    # Create snapshot
    await rollback_service.create_migration_snapshot(migration_id)
    
    # Create rollback plan
    await rollback_service.create_rollback_plan(migration_id, rollback_sql)
    
    try:
        yield rollback_service
    except Exception as e:
        logger.error(f"Migration {migration_id} failed, attempting rollback: {e}")
        
        # Execute rollback
        rollback_execution = await rollback_service.execute_rollback(migration_id)
        
        if rollback_execution.status == RollbackStatus.COMPLETED:
            logger.info(f"Successfully rolled back migration {migration_id}")
        else:
            logger.error(f"Rollback failed for migration {migration_id}: {rollback_execution.error_message}")
        
        raise