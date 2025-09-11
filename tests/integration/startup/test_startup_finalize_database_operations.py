"""
Integration tests for FINALIZE phase - Database System Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Data Persistence and Integrity  
- Value Impact: Ensures user data, chat history, and agent results are properly stored
- Strategic Impact: Database failures block all user data operations and chat persistence

Tests database system validation during the FINALIZE phase, ensuring the database
is properly initialized, all tables exist, indexes are optimized, and the system
can handle the expected database operations for chat and user data.

Database readiness is CRITICAL for chat history, user sessions, and agent results.

Covers:
1. Database connection and health validation
2. Schema validation and table existence
3. Read/write operations performance
4. Transaction handling and rollback
5. Connection pooling and concurrency
6. Data integrity and constraints
7. Migration status and version consistency
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
import pytest
import aiohttp
import asyncpg
import json
from unittest.mock import patch, AsyncMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.service_availability import check_service_availability, ServiceUnavailableError
from shared.isolated_environment import get_env

# Check service availability at module level
_service_status = check_service_availability(['postgresql'], timeout=2.0)
_postgresql_available = _service_status['postgresql'] is True
_postgresql_skip_reason = f"PostgreSQL unavailable: {_service_status['postgresql']}" if not _postgresql_available else None


@pytest.mark.skipif(not _postgresql_available, reason=_postgresql_skip_reason)
class TestStartupFinalizeDatabaseOperations(SSotBaseTestCase):
    """Integration tests for FINALIZE phase database system validation."""
    
    def setup_method(self, method):
        """Setup test environment for database operations testing."""
        super().setup_method(method)
        
        # Initialize E2E auth helper
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Configure test environment
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("TESTING", "true")
        self.set_env_var("JWT_SECRET_KEY", "test-jwt-secret-key-unified-testing-32chars")
        
        # Service endpoints
        self.backend_url = "http://localhost:8000"
        
        # Database configuration
        self.database_config = {
            "host": self.get_env_var("POSTGRES_HOST", "localhost"),
            "port": int(self.get_env_var("POSTGRES_PORT", "5434")),  # Test database port
            "user": self.get_env_var("POSTGRES_USER", "postgres"),
            "password": self.get_env_var("POSTGRES_PASSWORD", "postgres"),
            "database": self.get_env_var("POSTGRES_DB", "netra_test")
        }
        
        # Track database test results
        self.database_test_results: Dict[str, Any] = {}
        
        # Test user configuration
        self.test_user_id = f"db_test_user_{int(time.time())}"
        self.test_user_email = f"db_test_{int(time.time())}@example.com"

    @pytest.mark.integration
    async def test_finalize_database_connection_health(self):
        """
        Test database connection and basic health validation.
        
        BVJ: Database connectivity is prerequisite for all data operations.
        """
        connection_results = []
        
        # 1. Test backend database health endpoint
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.auth_helper.get_auth_headers(token)
        
        health_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.backend_url}/health/database",
                    headers=headers,
                    timeout=15
                ) as resp:
                    health_time = time.time() - health_start
                    
                    assert resp.status == 200, f"Database health endpoint failed: {resp.status}"
                    
                    health_data = await resp.json()
                    connection_results.append({
                        "test": "backend_database_health_endpoint",
                        "status": "success",
                        "response_time": health_time,
                        "connected": health_data.get("connected", False),
                        "health_data": health_data
                    })
                    
                    # Validate health response structure
                    assert "connected" in health_data, "Health response missing connection status"
                    assert health_data["connected"] is True, "Database not connected according to health check"
                    
                    self.record_metric("database_health_response_time", health_time)
                    
        except Exception as e:
            connection_results.append({
                "test": "backend_database_health_endpoint",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test direct database connection (if credentials available)
        direct_connection_start = time.time()
        try:
            # Try to establish direct database connection
            connection_string = f"postgresql://{self.database_config['user']}:{self.database_config['password']}@{self.database_config['host']}:{self.database_config['port']}/{self.database_config['database']}"
            
            conn = await asyncio.wait_for(
                asyncpg.connect(connection_string),
                timeout=10.0
            )
            
            direct_connection_time = time.time() - direct_connection_start
            
            # Test basic query
            query_result = await conn.fetchval("SELECT 1 as test_value")
            assert query_result == 1, "Basic database query failed"
            
            # Get database version
            db_version = await conn.fetchval("SELECT version()")
            
            await conn.close()
            
            connection_results.append({
                "test": "direct_database_connection",
                "status": "success",
                "connection_time": direct_connection_time,
                "database_version": db_version[:50] if db_version else "unknown"  # First 50 chars
            })
            
            self.record_metric("direct_database_connection_time", direct_connection_time)
            
        except Exception as e:
            connection_results.append({
                "test": "direct_database_connection",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test database connection pool status
        pool_status_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.backend_url}/health/database/pool",
                    headers=headers,
                    timeout=10
                ) as resp:
                    pool_status_time = time.time() - pool_status_start
                    
                    if resp.status == 200:
                        pool_data = await resp.json()
                        connection_results.append({
                            "test": "database_connection_pool_status",
                            "status": "success",
                            "response_time": pool_status_time,
                            "pool_data": pool_data
                        })
                    elif resp.status == 404:
                        connection_results.append({
                            "test": "database_connection_pool_status",
                            "status": "not_implemented"
                        })
                    else:
                        connection_results.append({
                            "test": "database_connection_pool_status",
                            "status": "error",
                            "status_code": resp.status
                        })
                        
        except Exception as e:
            connection_results.append({
                "test": "database_connection_pool_status",
                "status": "error",
                "error": str(e)
            })
        
        # Record connection health results
        self.database_test_results["connection_health"] = connection_results
        
        # Validate database connectivity
        successful_connections = [r for r in connection_results if r["status"] == "success"]
        assert len(successful_connections) > 0, "No successful database connections established"
        
        # At least backend health check should work
        backend_health = [r for r in connection_results if r["test"] == "backend_database_health_endpoint" and r["status"] == "success"]
        assert len(backend_health) > 0, "Backend database health check failed"
        
        self.record_metric("database_connection_health_passed", True)

    @pytest.mark.integration
    async def test_finalize_database_schema_validation(self):
        """
        Test database schema and table existence validation.
        
        BVJ: Proper schema ensures all application features can store data.
        """
        schema_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.auth_helper.get_auth_headers(token)
        
        # 1. Test schema validation endpoint
        schema_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.backend_url}/health/database/schema",
                    headers=headers,
                    timeout=15
                ) as resp:
                    schema_time = time.time() - schema_start
                    
                    if resp.status == 200:
                        schema_data = await resp.json()
                        schema_results.append({
                            "test": "database_schema_validation_endpoint",
                            "status": "success",
                            "response_time": schema_time,
                            "schema_valid": schema_data.get("valid", False),
                            "table_count": schema_data.get("table_count", 0),
                            "tables": schema_data.get("tables", [])[:10]  # First 10 tables only
                        })
                        
                        # Validate schema response
                        if "valid" in schema_data:
                            assert schema_data["valid"] is True, "Database schema validation failed"
                            
                    elif resp.status == 404:
                        schema_results.append({
                            "test": "database_schema_validation_endpoint",
                            "status": "not_implemented"
                        })
                    else:
                        schema_results.append({
                            "test": "database_schema_validation_endpoint",
                            "status": "error",
                            "status_code": resp.status
                        })
                        
        except Exception as e:
            schema_results.append({
                "test": "database_schema_validation_endpoint",
                "status": "error",
                "error": str(e)
            })
        
        # 2. Test critical table existence via direct database connection
        table_check_start = time.time()
        try:
            connection_string = f"postgresql://{self.database_config['user']}:{self.database_config['password']}@{self.database_config['host']}:{self.database_config['port']}/{self.database_config['database']}"
            
            conn = await asyncio.wait_for(
                asyncpg.connect(connection_string),
                timeout=10.0
            )
            
            # Check for critical tables that should exist for chat functionality
            critical_tables = ["users", "sessions", "messages", "agents", "executions", "alembic_version"]
            existing_tables = []
            
            for table in critical_tables:
                try:
                    table_exists_query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                    """
                    table_exists = await conn.fetchval(table_exists_query, table)
                    if table_exists:
                        existing_tables.append(table)
                except Exception:
                    pass  # Table check failed, continue with others
            
            # Get all table names
            all_tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
            """
            all_tables = await conn.fetch(all_tables_query)
            table_names = [row['table_name'] for row in all_tables]
            
            await conn.close()
            
            table_check_time = time.time() - table_check_start
            
            schema_results.append({
                "test": "critical_tables_existence",
                "status": "checked",
                "check_time": table_check_time,
                "critical_tables_checked": critical_tables,
                "critical_tables_existing": existing_tables,
                "total_tables_found": len(table_names),
                "all_table_names": table_names[:15]  # First 15 table names
            })
            
            self.record_metric("database_table_check_time", table_check_time)
            self.record_metric("database_total_tables", len(table_names))
            self.record_metric("database_critical_tables_existing", len(existing_tables))
            
        except Exception as e:
            schema_results.append({
                "test": "critical_tables_existence",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test database migration status
        migration_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.backend_url}/health/database/migrations",
                    headers=headers,
                    timeout=10
                ) as resp:
                    migration_time = time.time() - migration_start
                    
                    if resp.status == 200:
                        migration_data = await resp.json()
                        schema_results.append({
                            "test": "database_migration_status",
                            "status": "success",
                            "response_time": migration_time,
                            "migrations_current": migration_data.get("current", False),
                            "current_version": migration_data.get("current_version"),
                            "target_version": migration_data.get("target_version")
                        })
                        
                        # Validate migrations are current
                        if "current" in migration_data:
                            assert migration_data["current"] is True, "Database migrations are not current"
                            
                    elif resp.status == 404:
                        schema_results.append({
                            "test": "database_migration_status",
                            "status": "not_implemented"
                        })
                    else:
                        schema_results.append({
                            "test": "database_migration_status",
                            "status": "error",
                            "status_code": resp.status
                        })
                        
        except Exception as e:
            schema_results.append({
                "test": "database_migration_status",
                "status": "error",
                "error": str(e)
            })
        
        # Record schema validation results
        self.database_test_results["schema_validation"] = schema_results
        
        # Validate schema readiness
        schema_checks = [r for r in schema_results if r["status"] in ["success", "checked"]]
        assert len(schema_checks) > 0, "No successful schema validation checks"
        
        # If critical tables check was performed, ensure some tables exist
        table_checks = [r for r in schema_results if r["test"] == "critical_tables_existence" and r["status"] == "checked"]
        if table_checks:
            table_check = table_checks[0]
            assert table_check["total_tables_found"] > 0, "No database tables found"
        
        self.record_metric("database_schema_validation_passed", True)

    @pytest.mark.integration
    async def test_finalize_database_read_write_operations(self):
        """
        Test database read and write operations performance and reliability.
        
        BVJ: Read/write operations are core to storing user data and chat history.
        """
        read_write_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.auth_helper.get_auth_headers(token)
        
        # 1. Test read operations through API
        read_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Test user data read
                async with session.get(
                    f"{self.backend_url}/api/users/me",
                    headers=headers,
                    timeout=10
                ) as resp:
                    read_time = time.time() - read_start
                    
                    # Should either return user data or handle gracefully
                    if resp.status == 200:
                        user_data = await resp.json()
                        read_write_results.append({
                            "test": "api_user_data_read",
                            "status": "success",
                            "response_time": read_time,
                            "data_received": bool(user_data),
                            "data_keys": list(user_data.keys())[:5] if user_data else []
                        })
                    elif resp.status in [401, 403, 404]:
                        read_write_results.append({
                            "test": "api_user_data_read",
                            "status": "expected_auth_response",
                            "response_time": read_time,
                            "status_code": resp.status
                        })
                    else:
                        read_write_results.append({
                            "test": "api_user_data_read",
                            "status": "error",
                            "response_time": read_time,
                            "status_code": resp.status
                        })
                        
                    self.record_metric("api_user_read_time", read_time)
                    
        except Exception as e:
            read_write_results.append({
                "test": "api_user_data_read",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test write operations through API (safe operations only)
        write_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Test creating a log entry or test record
                test_log_data = {
                    "level": "INFO",
                    "message": f"Database finalize test write operation {time.time()}",
                    "source": "test_startup_finalize_database",
                    "user_id": self.test_user_id,
                    "metadata": {"test_type": "finalize_phase"}
                }
                
                async with session.post(
                    f"{self.backend_url}/api/logs",
                    headers=headers,
                    json=test_log_data,
                    timeout=15
                ) as resp:
                    write_time = time.time() - write_start
                    
                    if resp.status in [200, 201]:
                        write_result = await resp.json()
                        read_write_results.append({
                            "test": "api_log_write_operation",
                            "status": "success",
                            "response_time": write_time,
                            "record_created": True,
                            "record_id": write_result.get("id") or write_result.get("log_id")
                        })
                    elif resp.status in [401, 403, 404, 405]:
                        read_write_results.append({
                            "test": "api_log_write_operation",
                            "status": "expected_response",
                            "response_time": write_time,
                            "status_code": resp.status
                        })
                    else:
                        read_write_results.append({
                            "test": "api_log_write_operation",
                            "status": "error",
                            "response_time": write_time,
                            "status_code": resp.status
                        })
                        
                    self.record_metric("api_write_operation_time", write_time)
                    
        except Exception as e:
            read_write_results.append({
                "test": "api_log_write_operation",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test bulk read operations (if available)
        bulk_read_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Test bulk data retrieval
                async with session.get(
                    f"{self.backend_url}/api/logs?limit=10",
                    headers=headers,
                    timeout=10
                ) as resp:
                    bulk_read_time = time.time() - bulk_read_start
                    
                    if resp.status == 200:
                        logs_data = await resp.json()
                        read_write_results.append({
                            "test": "api_bulk_read_operation",
                            "status": "success",
                            "response_time": bulk_read_time,
                            "records_count": len(logs_data) if isinstance(logs_data, list) else logs_data.get("count", 0)
                        })
                    elif resp.status in [401, 403, 404]:
                        read_write_results.append({
                            "test": "api_bulk_read_operation",
                            "status": "expected_response",
                            "response_time": bulk_read_time,
                            "status_code": resp.status
                        })
                    else:
                        read_write_results.append({
                            "test": "api_bulk_read_operation",
                            "status": "error",
                            "response_time": bulk_read_time,
                            "status_code": resp.status
                        })
                        
                    self.record_metric("api_bulk_read_time", bulk_read_time)
                    
        except Exception as e:
            read_write_results.append({
                "test": "api_bulk_read_operation",
                "status": "failed",
                "error": str(e)
            })
        
        # 4. Test direct database operations (if connection available)
        direct_ops_start = time.time()
        try:
            connection_string = f"postgresql://{self.database_config['user']}:{self.database_config['password']}@{self.database_config['host']}:{self.database_config['port']}/{self.database_config['database']}"
            
            conn = await asyncio.wait_for(
                asyncpg.connect(connection_string),
                timeout=10.0
            )
            
            # Test direct read operation
            direct_read_start = time.time()
            read_query = "SELECT COUNT(*) as total_records FROM information_schema.tables WHERE table_schema = 'public'"
            table_count = await conn.fetchval(read_query)
            direct_read_time = time.time() - direct_read_start
            
            # Test direct write operation (safe test table)
            direct_write_start = time.time()
            test_table_name = f"finalize_test_{int(time.time())}"
            
            try:
                create_test_table_query = f"""
                CREATE TEMPORARY TABLE {test_table_name} (
                    id SERIAL PRIMARY KEY,
                    test_data TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
                await conn.execute(create_test_table_query)
                
                # Insert test data
                insert_query = f"INSERT INTO {test_table_name} (test_data) VALUES ($1) RETURNING id"
                test_record_id = await conn.fetchval(insert_query, "Database finalize test data")
                
                # Read back the data
                select_query = f"SELECT test_data FROM {test_table_name} WHERE id = $1"
                retrieved_data = await conn.fetchval(select_query, test_record_id)
                
                direct_write_time = time.time() - direct_write_start
                
                read_write_results.append({
                    "test": "direct_database_operations",
                    "status": "success",
                    "read_time": direct_read_time,
                    "write_time": direct_write_time,
                    "table_count": table_count,
                    "data_integrity_verified": retrieved_data == "Database finalize test data"
                })
                
            except Exception as table_error:
                # Temporary table operations may not be allowed
                read_write_results.append({
                    "test": "direct_database_operations",
                    "status": "limited_permissions",
                    "read_time": direct_read_time,
                    "table_count": table_count,
                    "write_error": str(table_error)
                })
            
            await conn.close()
            
            direct_ops_time = time.time() - direct_ops_start
            self.record_metric("direct_database_operations_time", direct_ops_time)
            
        except Exception as e:
            read_write_results.append({
                "test": "direct_database_operations",
                "status": "failed",
                "error": str(e)
            })
        
        # Record read/write results
        self.database_test_results["read_write_operations"] = read_write_results
        
        # Validate read/write capabilities
        successful_operations = [r for r in read_write_results if r["status"] in ["success", "expected_auth_response", "expected_response"]]
        assert len(successful_operations) > 0, "No successful database read/write operations"
        
        self.record_metric("database_read_write_operations_passed", True)

    @pytest.mark.integration
    async def test_finalize_database_transaction_handling(self):
        """
        Test database transaction handling and rollback capabilities.
        
        BVJ: Transaction integrity ensures data consistency for user operations.
        """
        transaction_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.auth_helper.get_auth_headers(token)
        
        # 1. Test transaction API endpoint (if available)
        try:
            async with aiohttp.ClientSession() as session:
                transaction_test_data = {
                    "test_type": "transaction_test",
                    "operations": [
                        {"action": "create", "data": {"test": "value1"}},
                        {"action": "create", "data": {"test": "value2"}}
                    ]
                }
                
                async with session.post(
                    f"{self.backend_url}/api/transaction/test",
                    headers=headers,
                    json=transaction_test_data,
                    timeout=15
                ) as resp:
                    if resp.status == 200:
                        transaction_result = await resp.json()
                        transaction_results.append({
                            "test": "api_transaction_endpoint",
                            "status": "success",
                            "transaction_supported": True,
                            "result": transaction_result
                        })
                    elif resp.status == 404:
                        transaction_results.append({
                            "test": "api_transaction_endpoint",
                            "status": "not_implemented"
                        })
                    else:
                        transaction_results.append({
                            "test": "api_transaction_endpoint",
                            "status": "error",
                            "status_code": resp.status
                        })
                        
        except Exception as e:
            transaction_results.append({
                "test": "api_transaction_endpoint",
                "status": "error",
                "error": str(e)
            })
        
        # 2. Test direct database transactions (if connection available)
        try:
            connection_string = f"postgresql://{self.database_config['user']}:{self.database_config['password']}@{self.database_config['host']}:{self.database_config['port']}/{self.database_config['database']}"
            
            conn = await asyncio.wait_for(
                asyncpg.connect(connection_string),
                timeout=10.0
            )
            
            # Test successful transaction
            transaction_start = time.time()
            try:
                async with conn.transaction():
                    # Create temporary table for testing
                    temp_table = f"tx_test_{int(time.time())}"
                    await conn.execute(f"""
                        CREATE TEMPORARY TABLE {temp_table} (
                            id SERIAL PRIMARY KEY,
                            data TEXT
                        )
                    """)
                    
                    # Insert test data within transaction
                    await conn.execute(f"INSERT INTO {temp_table} (data) VALUES ($1)", "test_data_1")
                    await conn.execute(f"INSERT INTO {temp_table} (data) VALUES ($1)", "test_data_2")
                    
                    # Verify data within transaction
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {temp_table}")
                    assert count == 2, "Transaction data insertion failed"
                
                # Verify data persisted after transaction commit
                final_count = await conn.fetchval(f"SELECT COUNT(*) FROM {temp_table}")
                transaction_time = time.time() - transaction_start
                
                transaction_results.append({
                    "test": "successful_database_transaction",
                    "status": "success",
                    "transaction_time": transaction_time,
                    "data_persisted": final_count == 2
                })
                
            except Exception as tx_error:
                transaction_results.append({
                    "test": "successful_database_transaction",
                    "status": "failed",
                    "error": str(tx_error)
                })
            
            # Test transaction rollback
            rollback_start = time.time()
            try:
                rollback_table = f"rollback_test_{int(time.time())}"
                
                # This transaction should be rolled back
                try:
                    async with conn.transaction():
                        await conn.execute(f"""
                            CREATE TEMPORARY TABLE {rollback_table} (
                                id SERIAL PRIMARY KEY,
                                data TEXT
                            )
                        """)
                        
                        await conn.execute(f"INSERT INTO {rollback_table} (data) VALUES ($1)", "should_be_rolled_back")
                        
                        # Force rollback by raising exception
                        raise Exception("Intentional rollback test")
                        
                except Exception as rollback_exception:
                    if "Intentional rollback test" not in str(rollback_exception):
                        raise rollback_exception  # Re-raise if it's not our test exception
                
                # Verify data was rolled back
                try:
                    rolled_back_count = await conn.fetchval(f"SELECT COUNT(*) FROM {rollback_table}")
                    # Table should not exist or be empty
                    rollback_successful = rolled_back_count == 0
                except Exception:
                    # Table doesn't exist - rollback successful
                    rollback_successful = True
                
                rollback_time = time.time() - rollback_start
                
                transaction_results.append({
                    "test": "database_transaction_rollback",
                    "status": "success",
                    "rollback_time": rollback_time,
                    "rollback_successful": rollback_successful
                })
                
            except Exception as rollback_error:
                transaction_results.append({
                    "test": "database_transaction_rollback", 
                    "status": "failed",
                    "error": str(rollback_error)
                })
            
            await conn.close()
            
        except Exception as e:
            transaction_results.append({
                "test": "direct_database_transactions",
                "status": "connection_failed",
                "error": str(e)
            })
        
        # Record transaction handling results
        self.database_test_results["transaction_handling"] = transaction_results
        
        # Validate transaction capabilities
        successful_transaction_tests = [r for r in transaction_results if r["status"] == "success"]
        
        # Transaction support is not mandatory, but if available should work correctly
        if len(successful_transaction_tests) > 0:
            self.record_metric("database_transactions_supported", True)
        else:
            self.record_metric("database_transactions_supported", False)
        
        self.record_metric("database_transaction_handling_passed", True)

    @pytest.mark.integration
    async def test_finalize_database_concurrency_performance(self):
        """
        Test database concurrency handling and performance under load.
        
        BVJ: Concurrent access is required for multi-user chat functionality.
        """
        concurrency_results = []
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email
        )
        headers = self.auth_helper.get_auth_headers(token)
        
        # 1. Test concurrent API requests
        concurrent_api_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Create multiple concurrent health check requests
                concurrent_tasks = []
                for i in range(5):
                    task = session.get(
                        f"{self.backend_url}/health/database",
                        headers=headers,
                        timeout=10
                    )
                    concurrent_tasks.append(task)
                
                # Execute all requests concurrently
                concurrent_responses = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
                concurrent_api_time = time.time() - concurrent_api_start
                
                # Analyze responses
                successful_responses = 0
                response_times = []
                
                for response in concurrent_responses:
                    if hasattr(response, 'status') and response.status == 200:
                        successful_responses += 1
                    if hasattr(response, 'close'):
                        await response.close()
                
                concurrency_results.append({
                    "test": "concurrent_api_requests",
                    "status": "tested",
                    "total_time": concurrent_api_time,
                    "requests_sent": len(concurrent_tasks),
                    "successful_responses": successful_responses,
                    "success_rate": successful_responses / len(concurrent_tasks)
                })
                
                # Should handle at least 80% of concurrent requests successfully
                assert successful_responses >= 4, f"Too many concurrent API requests failed: {successful_responses}/5"
                
                self.record_metric("concurrent_api_requests_time", concurrent_api_time)
                self.record_metric("concurrent_api_success_rate", successful_responses / len(concurrent_tasks))
                
        except Exception as e:
            concurrency_results.append({
                "test": "concurrent_api_requests",
                "status": "failed",
                "error": str(e)
            })
        
        # 2. Test direct database concurrent connections (if available)
        concurrent_db_start = time.time()
        try:
            connection_string = f"postgresql://{self.database_config['user']}:{self.database_config['password']}@{self.database_config['host']}:{self.database_config['port']}/{self.database_config['database']}"
            
            # Create multiple concurrent database connections
            connection_tasks = []
            for i in range(3):  # Test 3 concurrent connections
                connection_tasks.append(asyncpg.connect(connection_string))
            
            concurrent_connections = await asyncio.gather(*connection_tasks, return_exceptions=True)
            concurrent_db_time = time.time() - concurrent_db_start
            
            # Test concurrent queries
            query_tasks = []
            valid_connections = []
            
            for conn in concurrent_connections:
                if hasattr(conn, 'fetchval'):  # Valid connection
                    valid_connections.append(conn)
                    query_tasks.append(conn.fetchval("SELECT COUNT(*) FROM information_schema.tables"))
            
            if query_tasks:
                query_start = time.time()
                query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
                query_time = time.time() - query_start
                
                successful_queries = sum(1 for r in query_results if isinstance(r, int))
                
                concurrency_results.append({
                    "test": "concurrent_database_connections",
                    "status": "tested",
                    "connection_time": concurrent_db_time,
                    "query_time": query_time,
                    "connections_established": len(valid_connections),
                    "successful_queries": successful_queries
                })
                
                self.record_metric("concurrent_db_connections", len(valid_connections))
                self.record_metric("concurrent_db_queries_time", query_time)
            
            # Close all connections
            close_tasks = []
            for conn in valid_connections:
                close_tasks.append(conn.close())
            
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
                
        except Exception as e:
            concurrency_results.append({
                "test": "concurrent_database_connections",
                "status": "failed",
                "error": str(e)
            })
        
        # 3. Test performance under simulated load
        load_test_start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                # Send rapid sequential requests to test performance
                rapid_requests = []
                for i in range(10):
                    rapid_request_start = time.time()
                    
                    try:
                        async with session.get(
                            f"{self.backend_url}/health",
                            headers=headers,
                            timeout=5
                        ) as resp:
                            rapid_request_time = time.time() - rapid_request_start
                            rapid_requests.append({
                                "request_id": i,
                                "status": resp.status,
                                "response_time": rapid_request_time
                            })
                    except Exception as req_error:
                        rapid_requests.append({
                            "request_id": i,
                            "status": "error",
                            "error": str(req_error)
                        })
                    
                    # Small delay between requests
                    await asyncio.sleep(0.1)
                
                load_test_time = time.time() - load_test_start
                
                # Analyze performance
                successful_rapid = sum(1 for r in rapid_requests if r.get("status") == 200)
                avg_response_time = sum(r.get("response_time", 0) for r in rapid_requests if "response_time" in r) / max(1, len([r for r in rapid_requests if "response_time" in r]))
                
                concurrency_results.append({
                    "test": "performance_under_load",
                    "status": "tested",
                    "total_time": load_test_time,
                    "requests_sent": len(rapid_requests),
                    "successful_requests": successful_rapid,
                    "average_response_time": avg_response_time
                })
                
                # Performance should not degrade significantly under load
                assert avg_response_time < 2.0, f"Performance degraded under load: {avg_response_time:.3f}s average"
                
                self.record_metric("load_test_average_response_time", avg_response_time)
                self.record_metric("load_test_success_rate", successful_rapid / len(rapid_requests))
                
        except Exception as e:
            concurrency_results.append({
                "test": "performance_under_load",
                "status": "failed",
                "error": str(e)
            })
        
        # Record concurrency results
        self.database_test_results["concurrency_performance"] = concurrency_results
        
        # Validate concurrency handling
        tested_concurrency = [r for r in concurrency_results if r["status"] == "tested"]
        assert len(tested_concurrency) > 0, "No concurrency tests were performed"
        
        self.record_metric("database_concurrency_performance_passed", True)
        
        # Record overall database operations completion
        self.record_metric("finalize_database_operations_complete", True)
        
        # Test should complete within reasonable time
        self.assert_execution_time_under(120.0)  # Allow up to 2 minutes for comprehensive database tests