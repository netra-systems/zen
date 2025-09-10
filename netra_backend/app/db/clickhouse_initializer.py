"""
ClickHouse Database Initializer
Ensures all required ClickHouse databases and tables are created on startup
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
try:
    from clickhouse_driver import Client
    from clickhouse_driver.errors import ServerException, ErrorCodes
    CLICKHOUSE_DRIVER_AVAILABLE = True
except ImportError:
    # ClickHouse driver not available - provide stub
    Client = None
    ServerException = Exception
    ErrorCodes = None
    CLICKHOUSE_DRIVER_AVAILABLE = False

logger = logging.getLogger(__name__)


class ClickHouseInitializer:
    """Initialize and verify ClickHouse databases and tables."""
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 9000,
                 user: str = 'default',
                 password: str = '',
                 **kwargs):
        """Initialize ClickHouse initializer."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.client_kwargs = kwargs
        
        self._client: Optional[Client] = None
        self.migration_path = Path(__file__).parent.parent.parent / 'migrations' / 'clickhouse'
        
        # Define required databases
        self.required_databases = {
            'netra_traces': 'Trace and telemetry data',
            'netra_analytics': 'Analytics and metrics data'
        }
        
        # Define critical tables per database
        self.critical_tables = {
            'netra_traces': [
                'agent_executions',
                'agent_events',
                'performance_metrics',
                'trace_correlations',
                'error_logs'
            ],
            'netra_analytics': [
                'performance_metrics',
                'events',
                'system_health_metrics',
                'error_analytics'
            ]
        }
    
    def _get_client(self) -> Client:
        """Get or create ClickHouse client."""
        if self._client is None:
            self._client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                **self.client_kwargs
            )
        return self._client
    
    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize all ClickHouse databases and tables.
        Returns status dictionary with initialization results.
        """
        status = {
            'success': False,
            'databases_created': [],
            'tables_created': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            # Step 1: Create databases
            logger.info("Creating ClickHouse databases...")
            for db_name, description in self.required_databases.items():
                if await self._create_database(db_name):
                    status['databases_created'].append(db_name)
                    logger.info(f"Database '{db_name}' ready ({description})")
            
            # Step 2: Run all migrations
            logger.info("Running ClickHouse migrations...")
            migration_results = await self._run_migrations()
            status.update(migration_results)
            
            # Step 3: Verify critical tables
            logger.info("Verifying critical tables...")
            verification_results = await self._verify_critical_tables()
            
            # Check if all critical tables exist
            missing_tables = []
            for db_name, tables in self.critical_tables.items():
                for table in tables:
                    table_key = f"{db_name}.{table}"
                    if not verification_results.get(table_key, False):
                        missing_tables.append(table_key)
            
            if missing_tables:
                status['warnings'].append(f"Missing critical tables: {', '.join(missing_tables)}")
                logger.warning(f"Missing critical tables: {missing_tables}")
            else:
                logger.info("All critical tables verified successfully")
            
            status['success'] = len(status['errors']) == 0
            status['verification'] = verification_results
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse: {e}")
            status['errors'].append(str(e))
            return status
        finally:
            if self._client:
                self._client.disconnect()
                self._client = None
    
    async def _create_database(self, db_name: str) -> bool:
        """Create a database if it doesn't exist."""
        try:
            client = self._get_client()
            
            # Check if database exists
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                client.execute,
                f"SELECT 1 FROM system.databases WHERE name = '{db_name}'"
            )
            
            if result:
                logger.debug(f"Database '{db_name}' already exists")
                return True
            
            # Create database
            await asyncio.get_event_loop().run_in_executor(
                None,
                client.execute,
                f"CREATE DATABASE IF NOT EXISTS {db_name}"
            )
            
            logger.info(f"Created database '{db_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database '{db_name}': {e}")
            return False
    
    async def _run_migrations(self) -> Dict[str, Any]:
        """Run all migration files."""
        results = {
            'migrations_run': [],
            'statements_executed': 0,
            'migration_errors': []
        }
        
        try:
            client = self._get_client()
            
            # Get all migration files
            migration_files = sorted(self.migration_path.glob('*.sql'))
            if not migration_files:
                logger.warning(f"No migration files found in {self.migration_path}")
                return results
            
            for migration_file in migration_files:
                logger.info(f"Running migration: {migration_file.name}")
                
                try:
                    with open(migration_file, 'r') as f:
                        sql_content = f.read()
                    
                    # Parse and execute statements
                    statements = self._parse_sql_statements(sql_content)
                    successful_statements = 0
                    
                    for statement in statements:
                        if statement.strip():
                            try:
                                await asyncio.get_event_loop().run_in_executor(
                                    None, client.execute, statement
                                )
                                successful_statements += 1
                            except ServerException as e:
                                # Ignore "already exists" errors
                                if e.code in [ErrorCodes.TABLE_ALREADY_EXISTS,
                                            ErrorCodes.DATABASE_ALREADY_EXISTS]:
                                    successful_statements += 1
                                else:
                                    logger.error(f"Failed to execute statement in {migration_file.name}: {e}")
                                    raise
                    
                    results['migrations_run'].append(migration_file.name)
                    results['statements_executed'] += successful_statements
                    logger.info(f"Completed {migration_file.name}: {successful_statements} statements")
                    
                except Exception as e:
                    logger.error(f"Failed to run migration {migration_file.name}: {e}")
                    results['migration_errors'].append({
                        'file': migration_file.name,
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            results['migration_errors'].append({'general': str(e)})
            return results
    
    async def _verify_critical_tables(self) -> Dict[str, bool]:
        """Verify that critical tables exist."""
        verification_status = {}
        
        try:
            client = self._get_client()
            
            for db_name, tables in self.critical_tables.items():
                for table in tables:
                    table_key = f"{db_name}.{table}"
                    
                    try:
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            client.execute,
                            f"SELECT 1 FROM system.tables WHERE database = '{db_name}' AND name = '{table}'"
                        )
                        
                        verification_status[table_key] = bool(result)
                        
                        if result:
                            # Also check if table has data (for monitoring)
                            try:
                                count_result = await asyncio.get_event_loop().run_in_executor(
                                    None,
                                    client.execute,
                                    f"SELECT count() FROM {db_name}.{table}"
                                )
                                row_count = count_result[0][0] if count_result else 0
                                verification_status[f"{table_key}_rows"] = row_count
                            except:
                                pass  # Row count is optional
                                
                    except Exception as e:
                        logger.warning(f"Failed to verify table {table_key}: {e}")
                        verification_status[table_key] = False
            
            return verification_status
            
        except Exception as e:
            logger.error(f"Failed to verify tables: {e}")
            return verification_status
    
    def _parse_sql_statements(self, sql_content: str) -> list:
        """Parse SQL content into individual statements."""
        lines = []
        for line in sql_content.split('\n'):
            # Remove SQL comments
            if not line.strip().startswith('--'):
                lines.append(line)
        
        # Join and split by semicolons
        sql = '\n'.join(lines)
        statements = sql.split(';')
        
        # Filter out empty statements
        return [s.strip() for s in statements if s.strip()]
    
    async def ensure_healthy(self) -> bool:
        """
        Quick health check to ensure ClickHouse is accessible and has required tables.
        Returns True if healthy, False otherwise.
        """
        try:
            client = self._get_client()
            
            # Quick connectivity check
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                client.execute,
                "SELECT 1"
            )
            
            if not result:
                return False
            
            # Check critical databases exist
            for db_name in self.required_databases:
                db_result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    client.execute,
                    f"SELECT 1 FROM system.databases WHERE name = '{db_name}'"
                )
                if not db_result:
                    logger.warning(f"Database '{db_name}' not found")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return False
        finally:
            if self._client:
                self._client.disconnect()
                self._client = None


# Convenience functions

async def initialize_clickhouse(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Initialize ClickHouse with proper configuration.
    
    Args:
        config: Optional configuration dictionary with connection parameters
        
    Returns:
        Status dictionary with initialization results
    """
    if config is None:
        # Use default configuration
        from netra_backend.app.db.clickhouse import get_clickhouse_config
        ch_config = get_clickhouse_config()
        config = {
            'host': ch_config.host,
            'port': ch_config.port,
            'user': ch_config.user,
            'password': ch_config.password
        }
    
    initializer = ClickHouseInitializer(**config)
    return await initializer.initialize()


async def ensure_clickhouse_healthy(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Quick health check for ClickHouse.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        True if healthy, False otherwise
    """
    if config is None:
        from netra_backend.app.db.clickhouse import get_clickhouse_config
        ch_config = get_clickhouse_config()
        config = {
            'host': ch_config.host,
            'port': ch_config.port,
            'user': ch_config.user,
            'password': ch_config.password
        }
    
    initializer = ClickHouseInitializer(**config)
    return await initializer.ensure_healthy()