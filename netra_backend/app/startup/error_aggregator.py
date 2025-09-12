"""
Error Aggregator - GAP-006 Implementation

Centralized error collection and analysis for startup issues.
Implements requirements from SPEC/startup_coverage.xml.

CRITICAL ARCHITECTURAL COMPLIANCE:
- ALL functions MUST be  <= 8 lines (MANDATORY)
- File MUST be  <= 250 lines total
- Strong typing with Pydantic models
- Pattern detection using similarity clustering
- SQLite database for error persistence

Usage:
    aggregator = ErrorAggregator()
    await aggregator.record_error(service="backend", message="Connection failed")
    patterns = await aggregator.find_patterns()
    report = await aggregator.generate_report()
"""

import difflib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiosqlite

from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.startup_types import (
    ErrorPattern,
    ErrorPhase,
    ErrorTrend,
    ErrorType,
    StartupError,
)


class ErrorAggregator:
    """Centralized error collection and pattern detection."""
    
    def __init__(self, db_path: str = ".netra/error_db.sqlite"):
        self.db_path = Path(db_path)
        self.similarity_threshold = 0.8

    async def record_error(self, service: str, message: str, 
                          phase: ErrorPhase = ErrorPhase.STARTUP,
                          severity: str = ErrorSeverity.MEDIUM.value,
                          error_type: ErrorType = ErrorType.OTHER,
                          stack_trace: Optional[str] = None,
                          context: Optional[Dict] = None) -> int:
        """Record error in database and return ID."""
        return await self._record_error_impl(service, message, phase, severity, error_type, stack_trace, context)

    async def _record_error_impl(self, service: str, message: str, phase: ErrorPhase, 
                                severity: str, error_type: ErrorType, stack_trace: Optional[str], 
                                context: Optional[Dict]) -> int:
        """Implementation of error recording."""
        await self._ensure_database_exists()
        error = self._create_startup_error(service, message, phase, severity, error_type, stack_trace, context)
        return await self._insert_error(error)

    def _create_startup_error(self, service: str, message: str, phase: ErrorPhase, 
                            severity: str, error_type: ErrorType, 
                            stack_trace: Optional[str], context: Optional[Dict]) -> StartupError:
        """Create StartupError instance with provided parameters."""
        return StartupError(
            timestamp=datetime.now(timezone.utc), service=service, phase=phase,
            severity=severity, error_type=error_type, message=message,
            stack_trace=stack_trace, context=context or {}
        )

    async def find_patterns(self, lookback_hours: int = 168) -> List[ErrorPattern]:
        """Detect similar error patterns using clustering."""
        await self._ensure_database_exists()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        errors = await self._get_recent_errors(cutoff)
        patterns = await self._detect_similar_errors(errors)
        for pattern in patterns:
            await self._update_pattern_frequency(pattern)
        return patterns

    async def get_trends(self, period_hours: int = 24) -> ErrorTrend:
        """Analyze error trends over specified period."""
        await self._ensure_database_exists()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=period_hours)
        errors = await self._get_recent_errors(cutoff)
        return self._analyze_error_trends(errors, f"{period_hours}h")

    async def generate_report(self, report_type: str = "daily") -> Dict:
        """Generate error analysis report."""
        hours = self._get_report_hours(report_type)
        trends = await self.get_trends(hours)
        patterns = await self.find_patterns(hours)
        return self._build_report_dict(report_type, trends, patterns)

    def _get_report_hours(self, report_type: str) -> int:
        """Get hours for report type."""
        return 24 if report_type == "daily" else 168

    def _build_report_dict(self, report_type: str, trends, patterns: List) -> Dict:
        """Build report dictionary."""
        return {
            "report_type": report_type, "generated_at": datetime.now(timezone.utc),
            "trends": trends.model_dump(), "top_patterns": patterns[:5],
            "recommendations": self._generate_recommendations(trends, patterns)
        }

    async def _ensure_database_exists(self) -> None:
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)

    async def _create_tables(self, db: aiosqlite.Connection) -> None:
        """Create required database tables."""
        script = self._build_table_creation_script()
        await db.executescript(script)
        await db.commit()

    def _build_table_creation_script(self) -> str:
        """Build table creation SQL script."""
        errors_table = self._get_errors_table_sql()
        patterns_table = self._get_patterns_table_sql()
        return f"{errors_table}\n{patterns_table}"

    def _get_errors_table_sql(self) -> str:
        """Get startup_errors table SQL."""
        return """CREATE TABLE IF NOT EXISTS startup_errors (
                id INTEGER PRIMARY KEY, timestamp DATETIME, service TEXT,
                phase TEXT, severity TEXT, error_type TEXT, message TEXT,
                stack_trace TEXT, context JSON, resolved BOOLEAN DEFAULT FALSE, resolution TEXT);"""

    def _get_patterns_table_sql(self) -> str:
        """Get error_patterns table SQL."""
        return """CREATE TABLE IF NOT EXISTS error_patterns (
                pattern_id INTEGER PRIMARY KEY, pattern TEXT UNIQUE, frequency INTEGER DEFAULT 1,
                last_seen DATETIME, suggested_fix TEXT, auto_fixable BOOLEAN DEFAULT FALSE);"""

    async def _insert_error(self, error: StartupError) -> int:
        """Insert error record and return ID."""
        async with aiosqlite.connect(self.db_path) as db:
            sql, params = self._build_insert_query(error)
            cursor = await db.execute(sql, params)
            await db.commit()
            return cursor.lastrowid

    def _build_insert_query(self, error: StartupError) -> tuple[str, tuple]:
        """Build insert query and parameters for error record."""
        sql = "INSERT INTO startup_errors (timestamp, service, phase, severity, error_type, message, stack_trace, context) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        params = (error.timestamp, error.service, error.phase.value, error.severity,
                 error.error_type.value, error.message, error.stack_trace, str(error.context))
        return sql, params

    async def _get_recent_errors(self, cutoff: datetime) -> List[StartupError]:
        """Retrieve errors since cutoff time."""
        async with aiosqlite.connect(self.db_path) as db:
            rows = await self._fetch_error_rows(db, cutoff)
            return [self._row_to_error(row) for row in rows]

    async def _fetch_error_rows(self, db: aiosqlite.Connection, cutoff: datetime) -> List:
        """Fetch error rows from database."""
        cursor = await db.execute(
            "SELECT * FROM startup_errors WHERE timestamp >= ? ORDER BY timestamp DESC",
            (cutoff,)
        )
        return await cursor.fetchall()

    def _row_to_error(self, row: Tuple) -> StartupError:
        """Convert database row to StartupError."""
        return StartupError(
            id=row[0], timestamp=datetime.fromisoformat(row[1]),
            service=row[2], phase=ErrorPhase(row[3]), severity=row[4],
            error_type=ErrorType(row[5]), message=row[6], stack_trace=row[7]
        )

    async def _detect_similar_errors(self, errors: List[StartupError]) -> List[ErrorPattern]:
        """Group similar errors into patterns."""
        if not errors:
            return []
        patterns, processed = [], set()
        self._process_error_patterns(errors, patterns, processed)
        return patterns

    def _process_error_patterns(self, errors: List[StartupError], patterns: List, processed: set) -> None:
        """Process errors to find patterns."""
        for i, error in enumerate(errors):
            if i not in processed:
                self._process_single_error_pattern(errors, i, patterns, processed)

    def _process_single_error_pattern(self, errors: List[StartupError], i: int, patterns: List, processed: set) -> None:
        """Process single error for pattern matching."""
        similar_indices = self._find_similar_messages(errors[i].message, errors, i)
        if len(similar_indices) > 1:
            pattern = self._create_pattern_from_errors([errors[j] for j in similar_indices])
            patterns.append(pattern)
            processed.update(similar_indices)

    def _find_similar_messages(self, message: str, errors: List[StartupError], start_idx: int) -> List[int]:
        """Find error indices with similar messages."""
        similar = [start_idx]
        for j in range(start_idx + 1, len(errors)):
            similarity = difflib.SequenceMatcher(None, message, errors[j].message).ratio()
            if similarity >= self.similarity_threshold:
                similar.append(j)
        return similar

    def _create_pattern_from_errors(self, similar_errors: List[StartupError]) -> ErrorPattern:
        """Create pattern from group of similar errors."""
        representative = similar_errors[0]
        return ErrorPattern(
            pattern=representative.message, frequency=len(similar_errors),
            last_seen=max(e.timestamp for e in similar_errors),
            suggested_fix=self._suggest_fix(representative.error_type)
        )

    def _suggest_fix(self, error_type: ErrorType) -> Optional[str]:
        """Get suggested fix for error type."""
        fixes = self._get_error_fix_mapping()
        return fixes.get(error_type, "Review error details and system logs")

    def _get_error_fix_mapping(self) -> Dict[ErrorType, str]:
        """Get mapping of error types to suggested fixes."""
        base_fixes = self._get_base_error_fixes()
        extended_fixes = self._get_extended_error_fixes()
        return {**base_fixes, **extended_fixes}

    def _get_base_error_fixes(self) -> Dict[ErrorType, str]:
        """Get base error type fixes."""
        return {
            ErrorType.CONNECTION: "Check network connectivity and service availability",
            ErrorType.CONFIGURATION: "Verify configuration files and environment variables",
            ErrorType.DEPENDENCY: "Run dependency installation and version checks"
        }

    def _get_extended_error_fixes(self) -> Dict[ErrorType, str]:
        """Get extended error type fixes."""
        return {
            ErrorType.MIGRATION: "Check database migration status and run pending migrations",
            ErrorType.TIMEOUT: "Increase timeout values or check system resources",
            ErrorType.PERMISSION: "Verify file/directory permissions and access rights"
        }

    async def _update_pattern_frequency(self, pattern: ErrorPattern) -> None:
        """Update or insert pattern frequency."""
        async with aiosqlite.connect(self.db_path) as db:
            sql, params = self._build_pattern_update_query(pattern)
            await db.execute(sql, params)
            await db.commit()

    def _build_pattern_update_query(self, pattern: ErrorPattern) -> tuple[str, tuple]:
        """Build pattern update query and parameters."""
        sql = "INSERT OR REPLACE INTO error_patterns (pattern, frequency, last_seen, suggested_fix) VALUES (?, ?, ?, ?)"
        params = (pattern.pattern, pattern.frequency, pattern.last_seen, pattern.suggested_fix)
        return sql, params

    def _analyze_error_trends(self, errors: List[StartupError], period: str) -> ErrorTrend:
        """Analyze error trends and create summary."""
        if not errors:
            return ErrorTrend(period=period, total_errors=0)
        breakdowns = self._calculate_error_breakdowns(errors)
        return ErrorTrend(period=period, total_errors=len(errors), **breakdowns)

    def _calculate_error_breakdowns(self, errors: List[StartupError]) -> Dict:
        """Calculate error breakdowns by type, service, and severity."""
        error_types, services, severity_breakdown = {}, {}, {}
        for error in errors:
            self._update_breakdown_counters(error, error_types, services, severity_breakdown)
        return {"error_types": error_types, "services": services, "severity_breakdown": severity_breakdown}

    def _update_breakdown_counters(self, error: StartupError, error_types: Dict, 
                                  services: Dict, severity_breakdown: Dict) -> None:
        """Update breakdown counters for single error."""
        error_types[error.error_type.value] = error_types.get(error.error_type.value, 0) + 1
        services[error.service] = services.get(error.service, 0) + 1
        severity_breakdown[error.severity] = severity_breakdown.get(error.severity, 0) + 1

    def _generate_recommendations(self, trends: ErrorTrend, patterns: List[ErrorPattern]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        self._add_volume_recommendation(trends, recommendations)
        self._add_pattern_recommendation(patterns, recommendations)
        self._add_critical_recommendation(trends, recommendations)
        return recommendations[:3]  # Limit to top 3 recommendations

    def _add_volume_recommendation(self, trends: ErrorTrend, recommendations: List[str]) -> None:
        """Add volume-based recommendation if applicable."""
        if trends.total_errors > 10:
            recommendations.append("High error volume detected - investigate system stability")

    def _add_pattern_recommendation(self, patterns: List[ErrorPattern], recommendations: List[str]) -> None:
        """Add pattern-based recommendation if applicable."""
        if patterns:
            top_pattern = max(patterns, key=lambda p: p.frequency)
            recommendations.append(f"Most frequent issue: {top_pattern.suggested_fix}")

    def _add_critical_recommendation(self, trends: ErrorTrend, recommendations: List[str]) -> None:
        """Add critical error recommendation if applicable."""
        critical_errors = trends.severity_breakdown.get("critical", 0)
        if critical_errors > 0:
            recommendations.append(f"Address {critical_errors} critical errors immediately")


# Singleton instance for application use
error_aggregator = ErrorAggregator()