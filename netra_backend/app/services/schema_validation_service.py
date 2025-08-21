"""Schema Validation Service

Validates database schema and provides comprehensive checks.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import inspect, text
from app.logging_config import central_logger
from app.db.models_postgres import Base

logger = central_logger.get_logger(__name__)

class SchemaValidationService:
    """Service for validating database schema integrity"""
    
    @classmethod
    def _initialize_validation_results(cls) -> Dict[str, Any]:
        """Initialize validation results structure"""
        return {
            "passed": True,
            "missing_tables": [],
            "missing_columns": {},
            "type_mismatches": {},
            "warnings": []
        }
    
    @classmethod
    def _get_model_tables(cls) -> set[str]:
        """Get table names from SQLAlchemy models"""
        return {table.name for table in Base.metadata.tables.values()}
    
    @classmethod
    def _check_missing_tables(cls, model_tables: set[str], db_tables: set[str], 
                            validation_results: Dict[str, Any]) -> None:
        """Check for missing tables in database"""
        missing_tables = model_tables - db_tables
        if missing_tables:
            validation_results["missing_tables"] = list(missing_tables)
            validation_results["passed"] = False
    
    @classmethod
    def _validate_table_columns(cls, table_name: str, validation_results: Dict[str, Any], 
                              inspector) -> None:
        """Validate columns for a specific table"""
        try:
            model_table = Base.metadata.tables[table_name]
            model_columns = {col.name: col for col in model_table.columns}
            cls._check_column_differences(table_name, model_columns, inspector, validation_results)
        except Exception as e:
            validation_results["warnings"].append(f"Could not validate table {table_name}: {str(e)}")
    
    @classmethod
    def _check_column_differences(cls, table_name: str, model_columns: Dict[str, Any], 
                                inspector, validation_results: Dict[str, Any]) -> None:
        """Check for missing and extra columns in table"""
        db_columns = inspector.get_columns(table_name)
        db_column_names = {col["name"] for col in db_columns}
        cls._check_missing_columns(table_name, model_columns, db_column_names, validation_results)
        cls._check_extra_columns(table_name, model_columns, db_column_names, validation_results)
    
    @classmethod
    def _check_missing_columns(cls, table_name: str, model_columns: Dict[str, Any], 
                             db_column_names: set[str], validation_results: Dict[str, Any]) -> None:
        """Check for missing columns in database table"""
        missing_columns = set(model_columns.keys()) - db_column_names
        if missing_columns:
            if table_name not in validation_results["missing_columns"]:
                validation_results["missing_columns"][table_name] = []
            validation_results["missing_columns"][table_name] = list(missing_columns)
            validation_results["passed"] = False
    
    @classmethod
    def _check_extra_columns(cls, table_name: str, model_columns: Dict[str, Any], 
                           db_column_names: set[str], validation_results: Dict[str, Any]) -> None:
        """Check for extra columns in database table"""
        extra_columns = db_column_names - set(model_columns.keys())
        if extra_columns:
            validation_results["warnings"].append(
                f"Extra columns in table {table_name}: {extra_columns}"
            )
    
    @classmethod
    def _check_extra_tables(cls, db_tables: set[str], model_tables: set[str], 
                          validation_results: Dict[str, Any]) -> None:
        """Check for extra tables in database"""
        extra_tables = db_tables - model_tables
        if extra_tables:
            validation_results["warnings"].append(
                f"Extra tables in database not defined in models: {extra_tables}"
            )
    
    @classmethod
    def _log_validation_results(cls, validation_results: Dict[str, Any]) -> None:
        """Log validation results with appropriate log levels"""
        if validation_results.get("missing_tables"):
            logger.error(f"Missing tables in database: {validation_results['missing_tables']}")
        cls._log_missing_columns(validation_results)
        cls._log_warnings(validation_results)
    
    @classmethod
    def _log_missing_columns(cls, validation_results: Dict[str, Any]) -> None:
        """Log missing columns for each table"""
        for table_name, missing_cols in validation_results.get("missing_columns", {}).items():
            logger.error(f"Missing columns in table {table_name}: {missing_cols}")
    
    @classmethod
    def _log_warnings(cls, validation_results: Dict[str, Any]) -> None:
        """Log all validation warnings"""
        for warning in validation_results.get("warnings", []):
            logger.warning(warning)
    
    @classmethod
    async def validate_schema(cls, engine: AsyncEngine) -> Dict[str, Any]:
        """Validate database schema against SQLAlchemy models"""
        validation_results = cls._initialize_validation_results()
        try:
            async with engine.connect() as conn:
                await conn.run_sync(cls._perform_validation, validation_results)
                cls._log_validation_results(validation_results)
        except Exception as e:
            cls._handle_validation_error(e, validation_results)
        return validation_results
    
    @classmethod
    def _perform_validation(cls, sync_conn, validation_results: Dict[str, Any]) -> None:
        """Perform synchronous validation operations"""
        inspector = inspect(sync_conn)
        model_tables = cls._get_model_tables()
        db_tables = set(inspector.get_table_names())
        cls._check_missing_tables(model_tables, db_tables, validation_results)
        cls._validate_existing_tables(model_tables, db_tables, inspector, validation_results)
        cls._check_extra_tables(db_tables, model_tables, validation_results)
    
    @classmethod
    def _validate_existing_tables(cls, model_tables: set[str], db_tables: set[str], 
                                inspector, validation_results: Dict[str, Any]) -> None:
        """Validate columns for tables that exist in both model and database"""
        for table_name in model_tables & db_tables:
            cls._validate_table_columns(table_name, validation_results, inspector)
    
    @classmethod
    def _handle_validation_error(cls, error: Exception, validation_results: Dict[str, Any]) -> None:
        """Handle validation errors and update results"""
        logger.error(f"Schema validation failed with error: {error}")
        validation_results["passed"] = False
        validation_results["error"] = str(error)
    
    
    @classmethod
    async def check_database_connectivity(cls, engine: AsyncEngine) -> bool:
        """Check if database is accessible"""
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                scalar_result = result.scalar()
                return scalar_result == 1
        except Exception as e:
            logger.error(f"Database connectivity check failed: {e}")
            return False
    
    @classmethod
    def _initialize_schema_info(cls) -> Dict[str, Any]:
        """Initialize schema info structure"""
        return {"tables": {}, "indexes": {}, "constraints": {}}

    @classmethod
    def _collect_table_info(cls, inspector, table_name: str) -> Dict[str, Any]:
        """Collect information for a single table"""
        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        return {"columns": columns, "indexes": indexes, "foreign_keys": foreign_keys}

    @classmethod
    def _build_schema_info(cls, inspector) -> Dict[str, Any]:
        """Build complete schema information"""
        schema_info = cls._initialize_schema_info()
        table_names = inspector.get_table_names()
        for table_name in table_names:
            schema_info["tables"][table_name] = cls._collect_table_info(inspector, table_name)
        return schema_info

    @classmethod
    def _get_all_schema_info(cls, sync_conn):
        """Synchronous schema info gathering function"""
        inspector = inspect(sync_conn)
        return cls._build_schema_info(inspector)

    @classmethod
    async def get_schema_info(cls, engine: AsyncEngine) -> Dict[str, Any]:
        """Get detailed schema information"""
        schema_info = cls._initialize_schema_info()
        try:
            async with engine.connect() as conn:
                schema_info = await conn.run_sync(cls._get_all_schema_info)
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
        return schema_info

async def run_comprehensive_validation(engine: AsyncEngine) -> bool:
    """Run comprehensive schema validation"""
    service = SchemaValidationService()
    
    # Check connectivity first
    if not await service.check_database_connectivity(engine):
        logger.error("Database connectivity check failed")
        return False
    
    # Validate schema
    validation_results = await service.validate_schema(engine)
    
    if not validation_results["passed"]:
        logger.error(f"Schema validation failed: {validation_results}")
        return False
    
    if validation_results.get("warnings"):
        for warning in validation_results["warnings"]:
            logger.warning(f"Schema validation warning: {warning}")
    
    logger.info("Schema validation completed successfully")
    return True