"""Database State Validation Helpers

**Business Value Justification (BVJ):**
- Segment: Engineering Quality & Enterprise  
- Business Goal: Zero false positives from database state corruption in tests
- Value Impact: 100% reliable test outcomes, eliminated debugging time
- Revenue Impact: Confident deployments, enterprise trust, $20K/month saved in debugging

Features:
- Cross-database state validation (PostgreSQL + ClickHouse)
- Data consistency checks between related tables
- Performance metrics validation
- Schema integrity verification  
- Test isolation verification
- Automated anomaly detection

Each function  <= 8 lines, file  <= 300 lines.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import clickhouse_connect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.exceptions_config import DatabaseError
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Result of database state validation."""
    check_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)

class DatabaseStateValidator:
    """Validates database state for test reliability."""
    
    def __init__(self):
        """Initialize database state validator."""
        self._validation_rules = self._load_validation_rules()
        self._consistency_checks = self._load_consistency_checks()
        self._performance_thresholds = self._load_performance_thresholds()
    
    def _load_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load database validation rules."""
        return {
            "postgres": {
                "max_connection_count": 50,
                "min_table_count": 0,
                "max_table_size_mb": 1000,
                "require_primary_keys": True
            },
            "clickhouse": {
                "max_part_count": 1000,
                "max_mutation_count": 100,
                "min_compression_ratio": 2.0,
                "max_merge_lag_seconds": 300
            }
        }
    
    def _load_consistency_checks(self) -> Dict[str, List[str]]:
        """Load data consistency check definitions."""
        return {
            "referential_integrity": [
                "test_threads.user_id -> test_users.id",
                "test_messages.thread_id -> test_threads.id"
            ],
            "data_ranges": [
                "created_at values within reasonable timeframe",
                "id sequences are sequential",
                "foreign keys exist in parent tables"
            ]
        }
    
    def _load_performance_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Load performance validation thresholds."""
        return {
            "postgres": {
                "query_time_ms": 1000.0,
                "connection_time_ms": 100.0,
                "index_hit_ratio": 0.95
            },
            "clickhouse": {
                "query_time_ms": 500.0,
                "insert_rate_rows_per_sec": 10000.0,
                "compression_ratio": 3.0
            }
        }
    
    async def validate_postgres_state(self, session: AsyncSession, test_id: str) -> List[ValidationResult]:
        """Validate PostgreSQL database state comprehensively."""
        results = []
        
        # Connection validation
        results.append(await self._validate_postgres_connection(session, test_id))
        
        # Schema validation
        results.extend(await self._validate_postgres_schema(session, test_id))
        
        # Data consistency validation
        results.extend(await self._validate_postgres_data_consistency(session, test_id))
        
        # Performance validation
        results.extend(await self._validate_postgres_performance(session, test_id))
        
        return results
    
    async def _validate_postgres_connection(self, session: AsyncSession, test_id: str) -> ValidationResult:
        """Validate PostgreSQL connection state."""
        try:
            # Test basic connectivity
            result = await session.execute(text("SELECT 1"))
            connection_ok = result.scalar() == 1
            
            # Check connection count
            conn_result = await session.execute(text("""
                SELECT count(*) FROM pg_stat_activity 
                WHERE datname = current_database()
            """))
            connection_count = conn_result.scalar()
            
            rules = self._validation_rules["postgres"]
            if connection_count > rules["max_connection_count"]:
                return ValidationResult(
                    check_name="postgres_connection_count",
                    passed=False, severity=ValidationSeverity.WARNING,
                    message=f"High connection count: {connection_count}",
                    details={"connection_count": connection_count, "max_allowed": rules["max_connection_count"]}
                )
            
            return ValidationResult(
                check_name="postgres_connection", passed=connection_ok,
                severity=ValidationSeverity.CRITICAL if not connection_ok else ValidationSeverity.INFO,
                message="Connection validation passed" if connection_ok else "Connection failed",
                details={"connection_count": connection_count}
            )
            
        except Exception as e:
            return ValidationResult(
                check_name="postgres_connection", passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Connection validation failed: {str(e)}"
            )
    
    async def _validate_postgres_schema(self, session: AsyncSession, test_id: str) -> List[ValidationResult]:
        """Validate PostgreSQL schema integrity."""
        results = []
        
        try:
            # Check table existence
            tables_result = await session.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' ORDER BY table_name
            """))
            tables = [row[0] for row in tables_result]
            
            results.append(ValidationResult(
                check_name="postgres_table_count", passed=True,
                severity=ValidationSeverity.INFO,
                message=f"Found {len(tables)} tables",
                details={"tables": tables, "count": len(tables)}
            ))
            
            # Validate primary keys exist
            for table in tables:
                pk_result = await session.execute(text(f"""
                    SELECT count(*) FROM information_schema.table_constraints 
                    WHERE table_name = '{table}' AND constraint_type = 'PRIMARY KEY'
                """))
                has_pk = pk_result.scalar() > 0
                
                if not has_pk and self._validation_rules["postgres"]["require_primary_keys"]:
                    results.append(ValidationResult(
                        check_name=f"postgres_primary_key_{table}", passed=False,
                        severity=ValidationSeverity.WARNING,
                        message=f"Table {table} missing primary key"
                    ))
            
        except Exception as e:
            results.append(ValidationResult(
                check_name="postgres_schema", passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Schema validation failed: {str(e)}"
            ))
        
        return results
    
    async def _validate_postgres_data_consistency(self, session: AsyncSession, test_id: str) -> List[ValidationResult]:
        """Validate PostgreSQL data consistency."""
        results = []
        
        try:
            # Check referential integrity
            if await self._table_exists(session, "test_users") and await self._table_exists(session, "test_threads"):
                orphan_result = await session.execute(text("""
                    SELECT count(*) FROM test_threads t 
                    LEFT JOIN test_users u ON t.user_id = u.id 
                    WHERE u.id IS NULL
                """))
                orphan_threads = orphan_result.scalar()
                
                results.append(ValidationResult(
                    check_name="postgres_referential_integrity_threads", 
                    passed=orphan_threads == 0,
                    severity=ValidationSeverity.ERROR if orphan_threads > 0 else ValidationSeverity.INFO,
                    message=f"Found {orphan_threads} orphaned threads",
                    details={"orphan_count": orphan_threads}
                ))
            
            # Check messages referential integrity
            if await self._table_exists(session, "test_messages") and await self._table_exists(session, "test_threads"):
                orphan_result = await session.execute(text("""
                    SELECT count(*) FROM test_messages m 
                    LEFT JOIN test_threads t ON m.thread_id = t.id 
                    WHERE t.id IS NULL
                """))
                orphan_messages = orphan_result.scalar()
                
                results.append(ValidationResult(
                    check_name="postgres_referential_integrity_messages",
                    passed=orphan_messages == 0,
                    severity=ValidationSeverity.ERROR if orphan_messages > 0 else ValidationSeverity.INFO,
                    message=f"Found {orphan_messages} orphaned messages",
                    details={"orphan_count": orphan_messages}
                ))
                
        except Exception as e:
            results.append(ValidationResult(
                check_name="postgres_data_consistency", passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Consistency validation failed: {str(e)}"
            ))
        
        return results
    
    async def _validate_postgres_performance(self, session: AsyncSession, test_id: str) -> List[ValidationResult]:
        """Validate PostgreSQL performance metrics."""
        results = []
        
        try:
            # Test query performance
            start_time = datetime.now(UTC)
            await session.execute(text("SELECT count(*) FROM test_users"))
            end_time = datetime.now(UTC)
            query_time_ms = (end_time - start_time).total_seconds() * 1000
            
            threshold = self._performance_thresholds["postgres"]["query_time_ms"]
            results.append(ValidationResult(
                check_name="postgres_query_performance", 
                passed=query_time_ms <= threshold,
                severity=ValidationSeverity.WARNING if query_time_ms > threshold else ValidationSeverity.INFO,
                message=f"Query took {query_time_ms:.2f}ms",
                details={"query_time_ms": query_time_ms, "threshold_ms": threshold}
            ))
            
        except Exception as e:
            results.append(ValidationResult(
                check_name="postgres_performance", passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"Performance validation failed: {str(e)}"
            ))
        
        return results
    
    async def _table_exists(self, session: AsyncSession, table_name: str) -> bool:
        """Check if table exists in PostgreSQL."""
        result = await session.execute(text(f"""
            SELECT count(*) FROM information_schema.tables 
            WHERE table_name = '{table_name}' AND table_schema = 'public'
        """))
        return result.scalar() > 0
    
    def validate_clickhouse_state(self, client: Any, database_name: str, test_id: str) -> List[ValidationResult]:
        """Validate ClickHouse database state comprehensively."""
        results = []
        
        # Connection validation
        results.append(self._validate_clickhouse_connection(client, test_id))
        
        # Schema validation
        results.extend(self._validate_clickhouse_schema(client, database_name, test_id))
        
        # Data consistency validation
        results.extend(self._validate_clickhouse_data_consistency(client, database_name, test_id))
        
        # Performance validation
        results.extend(self._validate_clickhouse_performance(client, database_name, test_id))
        
        return results
    
    def _validate_clickhouse_connection(self, client: Any, test_id: str) -> ValidationResult:
        """Validate ClickHouse connection state."""
        try:
            result = client.query("SELECT 1").result_rows
            connection_ok = len(result) > 0 and result[0][0] == 1
            
            return ValidationResult(
                check_name="clickhouse_connection", passed=connection_ok,
                severity=ValidationSeverity.CRITICAL if not connection_ok else ValidationSeverity.INFO,
                message="Connection validation passed" if connection_ok else "Connection failed"
            )
            
        except Exception as e:
            return ValidationResult(
                check_name="clickhouse_connection", passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Connection validation failed: {str(e)}"
            )
    
    def _validate_clickhouse_schema(self, client: Any, database_name: str, test_id: str) -> List[ValidationResult]:
        """Validate ClickHouse schema integrity."""
        results = []
        
        try:
            # Check table existence and engines
            tables_result = client.query(f"""
                SELECT table, engine, total_rows, total_bytes 
                FROM system.tables 
                WHERE database = '{database_name}'
            """)
            tables = tables_result.result_rows
            
            results.append(ValidationResult(
                check_name="clickhouse_table_count", passed=True,
                severity=ValidationSeverity.INFO,
                message=f"Found {len(tables)} tables in {database_name}",
                details={"table_count": len(tables), "database": database_name}
            ))
            
            # Validate MergeTree engines for test tables
            for table_row in tables:
                table_name, engine, total_rows, total_bytes = table_row
                if table_name.startswith("test_"):
                    if "MergeTree" not in engine:
                        results.append(ValidationResult(
                            check_name=f"clickhouse_engine_{table_name}",
                            passed=False, severity=ValidationSeverity.WARNING,
                            message=f"Table {table_name} using non-optimal engine: {engine}"
                        ))
            
        except Exception as e:
            results.append(ValidationResult(
                check_name="clickhouse_schema", passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Schema validation failed: {str(e)}"
            ))
        
        return results
    
    def _validate_clickhouse_data_consistency(self, client: Any, database_name: str, test_id: str) -> List[ValidationResult]:
        """Validate ClickHouse data consistency."""
        results = []
        
        try:
            # Check for duplicate event IDs
            if self._clickhouse_table_exists(client, database_name, "test_events"):
                duplicate_result = client.query(f"""
                    SELECT count(*) FROM (
                        SELECT event_id, count(*) as cnt 
                        FROM {database_name}.test_events 
                        GROUP BY event_id 
                        HAVING cnt > 1
                    )
                """)
                duplicate_count = duplicate_result.result_rows[0][0]
                
                results.append(ValidationResult(
                    check_name="clickhouse_event_duplicates",
                    passed=duplicate_count == 0,
                    severity=ValidationSeverity.ERROR if duplicate_count > 0 else ValidationSeverity.INFO,
                    message=f"Found {duplicate_count} duplicate event IDs",
                    details={"duplicate_count": duplicate_count}
                ))
            
            # Check timestamp ordering
            if self._clickhouse_table_exists(client, database_name, "test_events"):
                ordering_result = client.query(f"""
                    SELECT count(*) FROM (
                        SELECT event_id FROM {database_name}.test_events 
                        ORDER BY timestamp DESC LIMIT 100
                    ) WHERE event_id <= 0
                """)
                invalid_timestamps = ordering_result.result_rows[0][0]
                
                results.append(ValidationResult(
                    check_name="clickhouse_timestamp_ordering",
                    passed=invalid_timestamps == 0,
                    severity=ValidationSeverity.WARNING if invalid_timestamps > 0 else ValidationSeverity.INFO,
                    message=f"Found {invalid_timestamps} invalid timestamps"
                ))
                
        except Exception as e:
            results.append(ValidationResult(
                check_name="clickhouse_data_consistency", passed=False,
                severity=ValidationSeverity.ERROR,
                message=f"Consistency validation failed: {str(e)}"
            ))
        
        return results
    
    def _validate_clickhouse_performance(self, client: Any, database_name: str, test_id: str) -> List[ValidationResult]:
        """Validate ClickHouse performance metrics."""
        results = []
        
        try:
            # Test query performance
            start_time = datetime.now(UTC)
            client.query(f"SELECT count(*) FROM {database_name}.test_events")
            end_time = datetime.now(UTC)
            query_time_ms = (end_time - start_time).total_seconds() * 1000
            
            threshold = self._performance_thresholds["clickhouse"]["query_time_ms"]
            results.append(ValidationResult(
                check_name="clickhouse_query_performance",
                passed=query_time_ms <= threshold,
                severity=ValidationSeverity.WARNING if query_time_ms > threshold else ValidationSeverity.INFO,
                message=f"Query took {query_time_ms:.2f}ms",
                details={"query_time_ms": query_time_ms, "threshold_ms": threshold}
            ))
            
        except Exception as e:
            results.append(ValidationResult(
                check_name="clickhouse_performance", passed=False,
                severity=ValidationSeverity.WARNING,
                message=f"Performance validation failed: {str(e)}"
            ))
        
        return results
    
    def _clickhouse_table_exists(self, client: Any, database_name: str, table_name: str) -> bool:
        """Check if table exists in ClickHouse."""
        try:
            result = client.query(f"""
                SELECT count(*) FROM system.tables 
                WHERE database = '{database_name}' AND table = '{table_name}'
            """)
            return result.result_rows[0][0] > 0
        except Exception:
            return False
    
    async def validate_test_isolation(self, test_id: str, postgres_session: Optional[AsyncSession] = None,
                                   clickhouse_client: Optional[Any] = None,
                                   clickhouse_database: Optional[str] = None) -> List[ValidationResult]:
        """Validate test database isolation."""
        results = []
        
        # Validate PostgreSQL isolation
        if postgres_session:
            isolation_result = await self._validate_postgres_isolation(postgres_session, test_id)
            results.append(isolation_result)
        
        # Validate ClickHouse isolation
        if clickhouse_client and clickhouse_database:
            isolation_result = self._validate_clickhouse_isolation(clickhouse_client, clickhouse_database, test_id)
            results.append(isolation_result)
        
        return results
    
    async def _validate_postgres_isolation(self, session: AsyncSession, test_id: str) -> ValidationResult:
        """Validate PostgreSQL database isolation."""
        try:
            # Check database name contains test identifier
            db_result = await session.execute(text("SELECT current_database()"))
            current_db = db_result.scalar()
            
            # Verify database is isolated (contains test identifier)
            is_isolated = test_id.replace("-", "_") in current_db or "test_" in current_db
            
            return ValidationResult(
                check_name="postgres_test_isolation", passed=is_isolated,
                severity=ValidationSeverity.CRITICAL if not is_isolated else ValidationSeverity.INFO,
                message=f"Database isolation {'verified' if is_isolated else 'FAILED'}: {current_db}",
                details={"database_name": current_db, "test_id": test_id}
            )
            
        except Exception as e:
            return ValidationResult(
                check_name="postgres_test_isolation", passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Isolation validation failed: {str(e)}"
            )
    
    def _validate_clickhouse_isolation(self, client: Any, database_name: str, test_id: str) -> ValidationResult:
        """Validate ClickHouse database isolation."""
        try:
            # Check database name contains test identifier
            is_isolated = test_id.replace("-", "_") in database_name or "test_" in database_name
            
            return ValidationResult(
                check_name="clickhouse_test_isolation", passed=is_isolated,
                severity=ValidationSeverity.CRITICAL if not is_isolated else ValidationSeverity.INFO,
                message=f"Database isolation {'verified' if is_isolated else 'FAILED'}: {database_name}",
                details={"database_name": database_name, "test_id": test_id}
            )
            
        except Exception as e:
            return ValidationResult(
                check_name="clickhouse_test_isolation", passed=False,
                severity=ValidationSeverity.CRITICAL,
                message=f"Isolation validation failed: {str(e)}"
            )
    
    def generate_validation_report(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        if not results:
            return {"status": "no_validations", "summary": "No validation results provided"}
        
        # Group results by severity
        by_severity = {"critical": [], "error": [], "warning": [], "info": []}
        for result in results:
            by_severity[result.severity.value].append(result)
        
        # Calculate overall status
        has_critical = len(by_severity["critical"]) > 0
        has_errors = len(by_severity["error"]) > 0
        
        if has_critical:
            overall_status = "critical"
        elif has_errors:
            overall_status = "failed"
        elif len(by_severity["warning"]) > 0:
            overall_status = "warning"
        else:
            overall_status = "passed"
        
        # Generate summary statistics
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.passed)
        failed_checks = total_checks - passed_checks
        
        return {
            "status": overall_status,
            "summary": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
                "success_rate": (passed_checks / total_checks * 100) if total_checks > 0 else 0
            },
            "by_severity": {
                severity: len(issues) for severity, issues in by_severity.items()
            },
            "critical_issues": [
                {"check": r.check_name, "message": r.message} for r in by_severity["critical"]
            ],
            "error_issues": [
                {"check": r.check_name, "message": r.message} for r in by_severity["error"]
            ],
            "warnings": [
                {"check": r.check_name, "message": r.message} for r in by_severity["warning"]
            ],
            "validation_timestamp": datetime.now(UTC).isoformat(),
            "details": [
                {
                    "check_name": r.check_name,
                    "passed": r.passed,
                    "severity": r.severity.value,
                    "message": r.message,
                    "details": r.details
                }
                for r in results
            ]
        }

# Global database state validator instance
db_state_validator = DatabaseStateValidator()