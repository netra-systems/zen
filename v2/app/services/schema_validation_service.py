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
    async def validate_schema(cls, engine: AsyncEngine) -> Dict[str, Any]:
        """Validate database schema against SQLAlchemy models"""
        validation_results = {
            "passed": True,
            "missing_tables": [],
            "missing_columns": {},
            "type_mismatches": {},
            "warnings": []
        }
        
        try:
            async with engine.connect() as conn:
                # Get database inspector
                inspector = inspect(conn)
                
                # Get all table names from models
                model_tables = {table.name for table in Base.metadata.tables.values()}
                
                # Get all table names from database
                db_tables = set(await conn.run_sync(inspector.get_table_names))
                
                # Check for missing tables
                missing_tables = model_tables - db_tables
                if missing_tables:
                    validation_results["missing_tables"] = list(missing_tables)
                    validation_results["passed"] = False
                    logger.error(f"Missing tables in database: {missing_tables}")
                
                # Check columns for each table
                for table_name in model_tables & db_tables:
                    await cls._validate_table_columns(
                        conn, inspector, table_name, validation_results
                    )
                
                # Check for extra tables in database
                extra_tables = db_tables - model_tables
                if extra_tables:
                    validation_results["warnings"].append(
                        f"Extra tables in database not defined in models: {extra_tables}"
                    )
                    logger.warning(f"Extra tables found: {extra_tables}")
        
        except Exception as e:
            logger.error(f"Schema validation failed with error: {e}")
            validation_results["passed"] = False
            validation_results["error"] = str(e)
        
        return validation_results
    
    @classmethod
    async def _validate_table_columns(
        cls,
        conn,
        inspector,
        table_name: str,
        validation_results: Dict[str, Any]
    ) -> None:
        """Validate columns for a specific table"""
        try:
            # Get model columns
            model_table = Base.metadata.tables[table_name]
            model_columns = {col.name: col for col in model_table.columns}
            
            # Get database columns
            db_columns = await conn.run_sync(inspector.get_columns, table_name)
            db_column_names = {col["name"] for col in db_columns}
            
            # Check for missing columns
            missing_columns = set(model_columns.keys()) - db_column_names
            if missing_columns:
                validation_results["missing_columns"][table_name] = list(missing_columns)
                validation_results["passed"] = False
                logger.error(f"Missing columns in table {table_name}: {missing_columns}")
            
            # Check for extra columns
            extra_columns = db_column_names - set(model_columns.keys())
            if extra_columns:
                validation_results["warnings"].append(
                    f"Extra columns in table {table_name}: {extra_columns}"
                )
        
        except Exception as e:
            logger.error(f"Failed to validate table {table_name}: {e}")
            validation_results["warnings"].append(
                f"Could not validate table {table_name}: {str(e)}"
            )
    
    @classmethod
    async def check_database_connectivity(cls, engine: AsyncEngine) -> bool:
        """Check if database is accessible"""
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connectivity check failed: {e}")
            return False
    
    @classmethod
    async def get_schema_info(cls, engine: AsyncEngine) -> Dict[str, Any]:
        """Get detailed schema information"""
        schema_info = {
            "tables": {},
            "indexes": {},
            "constraints": {}
        }
        
        try:
            async with engine.connect() as conn:
                inspector = inspect(conn)
                
                # Get all tables
                table_names = await conn.run_sync(inspector.get_table_names)
                
                for table_name in table_names:
                    # Get columns
                    columns = await conn.run_sync(inspector.get_columns, table_name)
                    
                    # Get indexes
                    indexes = await conn.run_sync(inspector.get_indexes, table_name)
                    
                    # Get foreign keys
                    foreign_keys = await conn.run_sync(
                        inspector.get_foreign_keys, table_name
                    )
                    
                    schema_info["tables"][table_name] = {
                        "columns": columns,
                        "indexes": indexes,
                        "foreign_keys": foreign_keys
                    }
        
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