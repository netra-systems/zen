"""
Schema Sync Utilities

Utility functions for schema synchronization and database validation.
Maintains 8-line function limit and focused functionality.
"""

import sys
import argparse
from typing import List
from sqlalchemy import text
from app.core.exceptions_base import ValidationError
from app.logging_config import central_logger as logger
from .models import SchemaValidationLevel
from .synchronizer import SchemaSynchronizer


async def validate_schema(db, expected_tables: List[str]):
    """Validate database schema against expected tables."""
    try:
        result = await db.execute("SELECT table_name, column_name, data_type FROM information_schema.columns")
        
        rows = await _get_fetchall_result(result)
        existing_tables = {row[0] for row in rows}
        missing_tables = set(expected_tables) - existing_tables
        
        if missing_tables:
            raise ValidationError(f"Missing tables: {missing_tables}")
        
        return True
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Schema validation failed: {e}")


def is_migration_safe(sql: str) -> bool:
    """Check if a SQL migration is safe to run."""
    sql_upper = sql.upper()
    
    if _has_unsafe_patterns(sql_upper):
        return False
    
    if _has_safe_patterns(sql_upper):
        return True
    
    return False


def create_sync_command():
    """Create a CLI command for schema synchronization."""
    parser = _create_argument_parser()
    args = parser.parse_args()
    
    validation_level = SchemaValidationLevel(args.validation_level)
    synchronizer = _create_synchronizer(args, validation_level)
    
    try:
        report = synchronizer.sync_schemas(force=args.force)
        _log_sync_results(report)
        return 0 if report.success else 1
        
    except Exception as e:
        logger.error(f"Schema synchronization failed: {e}")
        return 1


async def _get_fetchall_result(result):
    """Handle both async and sync fetchall results"""
    fetchall_result = result.fetchall()
    if hasattr(fetchall_result, '__await__'):
        return await fetchall_result
    else:
        return fetchall_result


def _has_unsafe_patterns(sql_upper: str) -> bool:
    """Check for unsafe SQL patterns"""
    unsafe_patterns = [
        'DROP TABLE',
        'DROP DATABASE',
        'TRUNCATE',
        'DELETE FROM',
    ]
    
    for pattern in unsafe_patterns:
        if pattern in sql_upper:
            if pattern == 'DELETE FROM' and 'WHERE' in sql_upper:
                continue
            return True
    
    return False


def _has_safe_patterns(sql_upper: str) -> bool:
    """Check for safe SQL patterns"""
    safe_patterns = [
        'ALTER TABLE',
        'ADD COLUMN',
        'CREATE TABLE',
        'CREATE INDEX',
        'INSERT INTO',
        'UPDATE',
        'SELECT',
    ]
    
    return any(pattern in sql_upper for pattern in safe_patterns)


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI"""
    parser = argparse.ArgumentParser(description="Synchronize schemas between backend and frontend")
    parser.add_argument('--modules', nargs='+', default=['app.schemas'], help='Backend modules to extract schemas from')
    parser.add_argument('--output', default='frontend/types/backend_schema_auto_generated.ts', help='Frontend output path')
    parser.add_argument('--validation-level', choices=['strict', 'moderate', 'lenient'], default='moderate', help='Validation level')
    parser.add_argument('--force', action='store_true', help='Force sync even with breaking changes')
    
    return parser


def _create_synchronizer(args, validation_level: SchemaValidationLevel) -> SchemaSynchronizer:
    """Create schema synchronizer from arguments"""
    return SchemaSynchronizer(
        backend_modules=args.modules,
        frontend_output_path=args.output,
        validation_level=validation_level
    )


def _log_sync_results(report) -> None:
    """Log synchronization results"""
    logger.info(f"Schema synchronization completed at {report.timestamp}")
    logger.info(f"Processed {report.schemas_processed} schemas")
    logger.info(f"Changes detected: {len(report.changes_detected)}")
    logger.info(f"Files generated: {len(report.files_generated)}")
    
    if report.changes_detected:
        logger.info("\nChanges detected:")
        for change in report.changes_detected:
            logger.info(f"  - {change.schema_name}: {change.description}")
    
    if report.validation_errors:
        logger.error("\nValidation errors:")
        for error in report.validation_errors:
            logger.error(f"  - {error}")
    
    logger.info(f"\nSync {'succeeded' if report.success else 'failed'}")


if __name__ == "__main__":
    sys.exit(create_sync_command())