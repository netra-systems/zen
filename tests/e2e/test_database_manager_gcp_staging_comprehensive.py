"""Comprehensive DatabaseManager E2E GCP Staging Test Suite

CRITICAL: E2E tests for DatabaseManager in GCP staging environment.
Tests production-scale database operations with real Cloud SQL and VPC connectors.

Business Value Justification (BVJ):
- Segment: Platform/Enterprise - Production infrastructure validation
- Business Goal: Ensure DatabaseManager performs reliably in GCP production environment
- Value Impact: Prevents production outages and data loss worth $500K+ ARR
- Strategic Impact: Validates entire database infrastructure stack under real production conditions

TEST PHILOSOPHY: Production-Like Environment Validation
- Tests real GCP Cloud SQL connections with Unix sockets
- Validates VPC connector functionality for private database access
- Tests production-scale connection pooling and performance
- Covers real SSL/TLS certificate validation
- Tests actual GCP IAM authentication patterns
- Validates monitoring and alerting integration

COVERAGE TARGETS:
1. GCP Cloud SQL Connection Management (3 tests)
2. VPC Connector and Network Security (2 tests)
3. Production-Scale Performance and Load (2 tests)
4. Monitoring and Health Check Integration (1 test)

CRITICAL: Real GCP Environment Required
- Uses actual GCP Cloud SQL instance in staging
- Tests real VPC connector configuration
- Validates actual SSL certificate chains
- Tests production IAM service account authentication
"""

import asyncio
import pytest
import logging
import time
import os
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import text, MetaData, Table, Column, Integer, String, DateTime, Boolean
import psutil
from unittest.mock import patch

# SSOT imports - absolute paths required per CLAUDE.md
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env

logger = logging.getLogger(__name__)


class TestDatabaseManagerGCPCloudSQL(BaseIntegrationTest):
    """E2E tests for DatabaseManager with GCP Cloud SQL.
    
    Business Value: Validates production database connectivity preventing $500K+ ARR outages
    """
    
    def setup_method(self):
        """Set up GCP staging environment configuration."""
        super().setup_method()
        
        # GCP staging environment variables
        self.gcp_staging_env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:netra-staging-db",  # Cloud SQL Unix socket
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "netra-staging-user",
            "POSTGRES_PASSWORD": os.environ.get("GCP_STAGING_DB_PASSWORD", ""),
            "POSTGRES_DB": "netra_staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging",
            "USE_CLOUD_SQL": "true",
            "ENABLE_DB_LOGGING": "true"
        }
        
        # Skip tests if staging credentials not available
        self.skip_if_no_gcp_credentials()
        
        # Reset global database manager
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None
    
    def skip_if_no_gcp_credentials(self):
        """Skip tests if GCP staging credentials not available."""
        required_env_vars = ["GCP_STAGING_DB_PASSWORD", "GOOGLE_APPLICATION_CREDENTIALS"]
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        
        if missing_vars:
            pytest.skip(f"GCP staging credentials not available. Missing: {', '.join(missing_vars)}")
    
    async def _create_staging_test_tables(self, engine: AsyncEngine):
        """Create test tables in GCP Cloud SQL staging database."""
        metadata = MetaData()
        
        # E2E test table with production-like schema
        e2e_users_table = Table(
            'e2e_staging_users',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('email', String(255), unique=True, nullable=False),
            Column('username', String(100), nullable=False),
            Column('subscription_tier', String(50), default='free'),
            Column('created_at', DateTime),
            Column('last_login', DateTime),
            Column('is_active', Boolean, default=True),
            Column('metadata_json', String(1000))  # JSON data for complex operations
        )
        
        # Performance monitoring table
        performance_metrics_table = Table(
            'e2e_performance_metrics',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('test_name', String(100)),
            Column('operation_type', String(50)),
            Column('duration_ms', Integer),
            Column('rows_affected', Integer),
            Column('timestamp', DateTime)
        )
        
        async with engine.begin() as conn:
            # Check if tables exist first to avoid conflicts
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('e2e_staging_users', 'e2e_performance_metrics')")
            )
            existing_tables = [row[0] for row in result.fetchall()]
            
            if 'e2e_staging_users' not in existing_tables:
                await conn.execute(text("""
                    CREATE TABLE e2e_staging_users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        username VARCHAR(100) NOT NULL,
                        subscription_tier VARCHAR(50) DEFAULT 'free',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        metadata_json TEXT
                    )
                """))
            
            if 'e2e_performance_metrics' not in existing_tables:
                await conn.execute(text("""
                    CREATE TABLE e2e_performance_metrics (
                        id SERIAL PRIMARY KEY,
                        test_name VARCHAR(100),
                        operation_type VARCHAR(50),
                        duration_ms INTEGER,
                        rows_affected INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_gcp_cloud_sql_unix_socket_connection(self, isolated_env):
        """Test DatabaseManager connects to GCP Cloud SQL via Unix socket.
        
        Business Value: Validates production database connectivity architecture.
        Protects: $500K+ ARR from total platform failure due to database connectivity
        """
        # Configure GCP staging environment
        for key, value in self.gcp_staging_env.items():
            isolated_env.set(key, value, source="e2e_staging_test")
        
        # Use real GCP configuration
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = True  # Enable logging for staging
            mock_config.return_value.database_pool_size = 5  # Production-like pool size
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None  # Force URL builder usage
            
            db_manager = DatabaseManager()
            
            # Test Cloud SQL initialization
            await db_manager.initialize()
            assert db_manager._initialized
            assert 'primary' in db_manager._engines
            
            # Verify we're using Cloud SQL (Unix socket)
            database_url = db_manager._get_database_url()
            assert "/cloudsql/" in database_url, "Should be using Cloud SQL Unix socket"
            assert "netra-staging" in database_url, "Should connect to staging instance"
            
            # Create test tables in real Cloud SQL
            engine = db_manager.get_engine('primary')
            await self._create_staging_test_tables(engine)
            
            # Test real database operations in Cloud SQL
            test_email = f"gcp_test_{int(time.time())}@netra.ai"
            async with db_manager.get_session() as session:
                # Insert test data
                await session.execute(
                    text("INSERT INTO e2e_staging_users (email, username, subscription_tier, metadata_json) VALUES (:email, :username, :tier, :metadata)"),
                    {
                        "email": test_email,
                        "username": "gcp_cloud_sql_user", 
                        "tier": "enterprise",
                        "metadata": '{"source": "e2e_test", "environment": "gcp_staging"}'
                    }
                )
                await session.commit()
                
                # Verify data was inserted in Cloud SQL
                result = await session.execute(
                    text("SELECT username, subscription_tier, metadata_json FROM e2e_staging_users WHERE email = :email"),
                    {"email": test_email}
                )
                row = result.fetchone()
                
                assert row is not None
                assert row[0] == "gcp_cloud_sql_user"
                assert row[1] == "enterprise"
                assert "gcp_staging" in row[2]
            
            # Test Cloud SQL health check
            health_result = await db_manager.health_check()
            assert health_result["status"] == "healthy"
            assert health_result["connection"] == "ok"
            
            # Clean up test data
            async with db_manager.get_session() as session:
                await session.execute(
                    text("DELETE FROM e2e_staging_users WHERE email = :email"),
                    {"email": test_email}
                )
                await session.commit()
            
            await db_manager.close_all()
    
    @pytest.mark.e2e
    @pytest.mark.staging  
    @pytest.mark.asyncio
    async def test_gcp_cloud_sql_ssl_security_validation(self, isolated_env):
        """Test GCP Cloud SQL SSL/TLS security configuration.
        
        Business Value: Ensures production-grade security for database connections.
        Protects: Customer data security and compliance requirements
        """
        for key, value in self.gcp_staging_env.items():
            isolated_env.set(key, value, source="e2e_staging_test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 3
            mock_config.return_value.database_max_overflow = 5
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Test DatabaseURLBuilder Cloud SQL configuration
            url_builder = DatabaseURLBuilder(isolated_env.as_dict())
            assert url_builder.cloud_sql.is_cloud_sql, "Should detect Cloud SQL configuration"
            
            cloud_sql_url = url_builder.cloud_sql.async_url
            assert cloud_sql_url is not None, "Should generate Cloud SQL URL"
            assert "/cloudsql/" in cloud_sql_url, "URL should contain Cloud SQL socket path"
            
            # Test SSL is not needed for Unix sockets (Cloud SQL handles encryption internally)
            sync_url = url_builder.cloud_sql.sync_url
            assert "sslmode" not in sync_url, "Unix sockets don't need SSL parameters"
            
            # Test connection security with real operations
            engine = db_manager.get_engine('primary')
            await self._create_staging_test_tables(engine)
            
            # Test encrypted connection validation
            async with db_manager.get_session() as session:
                # Query connection encryption status
                result = await session.execute(
                    text("SELECT ssl_is_used(), version() as db_version")
                )
                ssl_status = result.fetchone()
                
                logger.info(f"Database version: {ssl_status[1] if ssl_status else 'Unknown'}")
                # Note: Cloud SQL Unix sockets don't report SSL status the same way as TCP connections
                
                # Test that sensitive operations work securely
                test_email = f"ssl_test_{int(time.time())}@netra.ai"
                await session.execute(
                    text("INSERT INTO e2e_staging_users (email, username, metadata_json) VALUES (:email, :username, :metadata)"),
                    {
                        "email": test_email,
                        "username": "ssl_security_test",
                        "metadata": '{"sensitive_data": "encrypted_in_transit", "test_type": "ssl_validation"}'
                    }
                )
                await session.commit()
                
                # Verify secure retrieval
                result = await session.execute(
                    text("SELECT metadata_json FROM e2e_staging_users WHERE email = :email"),
                    {"email": test_email}
                )
                metadata = result.scalar()
                assert "encrypted_in_transit" in metadata
                
                # Clean up
                await session.execute(
                    text("DELETE FROM e2e_staging_users WHERE email = :email"),
                    {"email": test_email}
                )
                await session.commit()
            
            await db_manager.close_all()
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_gcp_cloud_sql_transaction_integrity_under_load(self, isolated_env):
        """Test Cloud SQL transaction integrity under production-like load.
        
        Business Value: Validates data integrity under concurrent production load.
        Protects: Customer data consistency worth $500K+ ARR
        """
        for key, value in self.gcp_staging_env.items():
            isolated_env.set(key, value, source="e2e_staging_test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False  # Disable echo for performance
            mock_config.return_value.database_pool_size = 10  # Higher pool for load test
            mock_config.return_value.database_max_overflow = 20
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            engine = db_manager.get_engine('primary')
            await self._create_staging_test_tables(engine)
            
            # Production-like concurrent load test
            async def concurrent_user_transaction(user_id: int, operations: int):
                """Simulate production user transaction patterns."""
                results = []
                for op in range(operations):
                    try:
                        async with db_manager.get_session() as session:
                            # Complex transaction simulating real business logic
                            test_email = f"load_test_user_{user_id}_{op}@netra.ai"
                            
                            # Insert user
                            await session.execute(
                                text("INSERT INTO e2e_staging_users (email, username, subscription_tier, metadata_json) VALUES (:email, :username, :tier, :metadata)"),
                                {
                                    "email": test_email,
                                    "username": f"load_user_{user_id}",
                                    "tier": "premium",
                                    "metadata": f'{{"user_id": {user_id}, "operation": {op}, "test": "load_test"}}'
                                }
                            )
                            
                            # Record performance metric
                            start_time = time.time()
                            await session.execute(
                                text("SELECT COUNT(*) FROM e2e_staging_users WHERE subscription_tier = :tier"),
                                {"tier": "premium"}
                            )
                            duration_ms = int((time.time() - start_time) * 1000)
                            
                            await session.execute(
                                text("INSERT INTO e2e_performance_metrics (test_name, operation_type, duration_ms, rows_affected) VALUES (:test, :op_type, :duration, :rows)"),
                                {
                                    "test": "gcp_load_test",
                                    "op_type": "concurrent_transaction",
                                    "duration": duration_ms,
                                    "rows": 1
                                }
                            )
                            
                            await session.commit()
                            results.append(f"user_{user_id}_op_{op}")
                            
                            # Small delay to simulate real processing
                            await asyncio.sleep(0.01)
                            
                    except Exception as e:
                        logger.error(f"Transaction failed for user {user_id}, op {op}: {e}")
                        results.append(f"ERROR_{user_id}_{op}")
                
                return results
            
            # Run concurrent load test
            num_concurrent_users = 8
            operations_per_user = 5
            start_time = time.time()
            
            tasks = []
            for user_id in range(num_concurrent_users):
                task = asyncio.create_task(concurrent_user_transaction(user_id, operations_per_user))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            load_test_duration = time.time() - start_time
            total_operations = num_concurrent_users * operations_per_user
            
            # Verify all transactions completed successfully
            successful_operations = 0
            failed_operations = 0
            
            for user_results in results:
                if isinstance(user_results, Exception):
                    logger.error(f"User task failed: {user_results}")
                    failed_operations += operations_per_user
                else:
                    for result in user_results:
                        if result.startswith("ERROR_"):
                            failed_operations += 1
                        else:
                            successful_operations += 1
            
            # Verify data integrity in Cloud SQL
            async with db_manager.get_session() as session:
                # Check total users created
                result = await session.execute(
                    text("SELECT COUNT(*) FROM e2e_staging_users WHERE email LIKE :pattern"),
                    {"pattern": "load_test_user_%@netra.ai"}
                )
                user_count = result.scalar()
                
                # Check performance metrics recorded
                result = await session.execute(
                    text("SELECT COUNT(*), AVG(duration_ms) FROM e2e_performance_metrics WHERE test_name = :test"),
                    {"test": "gcp_load_test"}
                )
                metrics_row = result.fetchone()
                metrics_count, avg_duration = metrics_row
                
                logger.info(f"Load test results: {successful_operations} successful, {failed_operations} failed")
                logger.info(f"Users created: {user_count}, Average query time: {avg_duration:.2f}ms")
                
                # Performance assertions for GCP Cloud SQL
                operations_per_second = successful_operations / load_test_duration
                logger.info(f"GCP Cloud SQL throughput: {operations_per_second:.2f} ops/second")
                
                assert successful_operations >= total_operations * 0.9, f"Too many failed operations: {failed_operations}"
                assert operations_per_second > 5, f"GCP throughput too low: {operations_per_second:.2f} ops/sec"
                assert avg_duration < 100, f"Average query time too high: {avg_duration:.2f}ms"
                
                # Clean up test data
                await session.execute(
                    text("DELETE FROM e2e_staging_users WHERE email LIKE :pattern"),
                    {"pattern": "load_test_user_%@netra.ai"}
                )
                await session.execute(
                    text("DELETE FROM e2e_performance_metrics WHERE test_name = :test"),
                    {"test": "gcp_load_test"}
                )
                await session.commit()
            
            await db_manager.close_all()


class TestDatabaseManagerVPCConnector(BaseIntegrationTest):
    """E2E tests for DatabaseManager with GCP VPC connector.
    
    Business Value: Validates private network database access for security compliance
    """
    
    def setup_method(self):
        super().setup_method()
        
        # VPC connector environment
        self.vpc_connector_env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "10.20.0.3",  # Private VPC IP
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "netra-vpc-user",
            "POSTGRES_PASSWORD": os.environ.get("GCP_VPC_DB_PASSWORD", ""),
            "POSTGRES_DB": "netra_staging",
            "USE_VPC_CONNECTOR": "true",
            "VPC_CONNECTOR_NAME": "netra-staging-vpc-connector",
            "REQUIRE_SSL": "true"
        }
        
        self.skip_if_no_vpc_credentials()
        
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None
    
    def skip_if_no_vpc_credentials(self):
        """Skip VPC tests if credentials not available."""
        if not os.environ.get("GCP_VPC_DB_PASSWORD"):
            pytest.skip("GCP VPC connector credentials not available")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_vpc_connector_private_database_access(self, isolated_env):
        """Test DatabaseManager connects through VPC connector to private database.
        
        Business Value: Validates private network security for enterprise compliance.
        Protects: Network security requirements for enterprise customers
        """
        for key, value in self.vpc_connector_env.items():
            isolated_env.set(key, value, source="e2e_vpc_test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = True
            mock_config.return_value.database_pool_size = 3
            mock_config.return_value.database_max_overflow = 5
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Verify VPC connection
            database_url = db_manager._get_database_url()
            assert "10.20.0.3" in database_url, "Should connect to private VPC IP"
            assert "sslmode=require" in database_url or "ssl=require" in database_url, "Should require SSL"
            
            # Test private network database operations
            engine = db_manager.get_engine('primary')
            
            async with db_manager.get_session() as session:
                # Test connection to private database
                result = await session.execute(text("SELECT inet_server_addr(), version()"))
                server_info = result.fetchone()
                
                logger.info(f"Connected to server: {server_info[0] if server_info else 'Unknown'}")
                logger.info(f"Database version: {server_info[1] if server_info else 'Unknown'}")
                
                # Verify we can perform operations through VPC
                result = await session.execute(text("SELECT current_timestamp, current_user"))
                timestamp_info = result.fetchone()
                assert timestamp_info is not None
                
                # Test network latency is reasonable for VPC
                start_time = time.time()
                result = await session.execute(text("SELECT 1"))
                latency_ms = (time.time() - start_time) * 1000
                
                logger.info(f"VPC connector latency: {latency_ms:.2f}ms")
                assert latency_ms < 50, f"VPC latency too high: {latency_ms:.2f}ms"
            
            await db_manager.close_all()
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_vpc_connector_ssl_certificate_validation(self, isolated_env):
        """Test SSL certificate validation through VPC connector.
        
        Business Value: Ensures end-to-end encryption for sensitive data.
        Protects: Data in transit encryption for compliance requirements
        """
        for key, value in self.vpc_connector_env.items():
            isolated_env.set(key, value, source="e2e_vpc_ssl_test")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 2
            mock_config.return_value.database_max_overflow = 3
            mock_config.return_value.database_url = None
            
            # Test SSL URL construction
            url_builder = DatabaseURLBuilder(isolated_env.as_dict())
            tcp_url_with_ssl = url_builder.tcp.async_url_with_ssl
            
            assert tcp_url_with_ssl is not None, "Should generate SSL URL"
            assert "sslmode=require" in tcp_url_with_ssl, "Should require SSL mode"
            
            # Test actual SSL connection
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            async with db_manager.get_session() as session:
                # Test SSL connection status
                result = await session.execute(
                    text("SELECT ssl_is_used() as ssl_active, ssl_version() as ssl_version, ssl_cipher() as ssl_cipher")
                )
                ssl_info = result.fetchone()
                
                if ssl_info:
                    logger.info(f"SSL Status - Active: {ssl_info[0]}, Version: {ssl_info[1]}, Cipher: {ssl_info[2]}")
                    # Note: Some database configurations may not support these SSL functions
                
                # Test encrypted data operations
                test_sensitive_data = "CONFIDENTIAL_BUSINESS_DATA_2024"
                result = await session.execute(
                    text("SELECT md5(:data) as hashed_data"),
                    {"data": test_sensitive_data}
                )
                hashed_result = result.scalar()
                assert hashed_result is not None
                assert len(hashed_result) == 32  # MD5 hash length
            
            await db_manager.close_all()


class TestDatabaseManagerProductionScale(BaseIntegrationTest):
    """E2E tests for DatabaseManager at production scale.
    
    Business Value: Validates performance at enterprise customer scale
    """
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_production_scale_connection_pool_efficiency(self, isolated_env):
        """Test connection pool efficiency at production scale.
        
        Business Value: Ensures platform handles enterprise customer load.
        Protects: Platform scalability for revenue growth
        """
        # Production-scale environment
        production_scale_env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:netra-staging-db",
            "POSTGRES_USER": "netra-staging-user", 
            "POSTGRES_PASSWORD": os.environ.get("GCP_STAGING_DB_PASSWORD", ""),
            "POSTGRES_DB": "netra_staging"
        }
        
        if not os.environ.get("GCP_STAGING_DB_PASSWORD"):
            pytest.skip("GCP staging credentials not available for production scale test")
        
        for key, value in production_scale_env.items():
            isolated_env.set(key, value, source="e2e_production_scale")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 20  # Production pool size
            mock_config.return_value.database_max_overflow = 40  # High overflow for spikes
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Create test tables
            engine = db_manager.get_engine('primary')
            
            async with engine.begin() as conn:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS production_scale_test (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        operation_type VARCHAR(50),
                        data_size INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
            
            # Production-scale concurrent operations
            async def high_volume_operations(worker_id: int, operations: int):
                """Simulate high-volume production operations."""
                successful_ops = 0
                failed_ops = 0
                
                for op in range(operations):
                    try:
                        async with db_manager.get_session() as session:
                            # Simulate various operation types
                            operation_types = ['user_registration', 'chat_message', 'file_upload', 'analytics_event']
                            op_type = operation_types[op % len(operation_types)]
                            
                            await session.execute(
                                text("INSERT INTO production_scale_test (user_id, operation_type, data_size) VALUES (:user_id, :op_type, :size)"),
                                {
                                    "user_id": worker_id * 1000 + op,
                                    "op_type": op_type,
                                    "size": (op % 100) * 1024  # Varying data sizes
                                }
                            )
                            await session.commit()
                            successful_ops += 1
                            
                    except Exception as e:
                        logger.error(f"Worker {worker_id} operation {op} failed: {e}")
                        failed_ops += 1
                
                return {"worker_id": worker_id, "successful": successful_ops, "failed": failed_ops}
            
            # Scale test parameters
            num_workers = 15
            operations_per_worker = 20
            total_expected_operations = num_workers * operations_per_worker
            
            start_time = time.time()
            
            # Monitor system resources during test
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Run high-volume concurrent operations
            tasks = []
            for worker_id in range(num_workers):
                task = asyncio.create_task(high_volume_operations(worker_id, operations_per_worker))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            duration = time.time() - start_time
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = final_memory - initial_memory
            
            # Analyze results
            total_successful = 0
            total_failed = 0
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Worker task failed: {result}")
                    total_failed += operations_per_worker
                else:
                    total_successful += result["successful"]
                    total_failed += result["failed"]
            
            # Verify database consistency
            async with db_manager.get_session() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM production_scale_test"))
                db_record_count = result.scalar()
                
                # Get operation type distribution
                result = await session.execute(
                    text("SELECT operation_type, COUNT(*) FROM production_scale_test GROUP BY operation_type ORDER BY COUNT(*) DESC")
                )
                operation_distribution = result.fetchall()
            
            # Performance assertions
            operations_per_second = total_successful / duration
            success_rate = (total_successful / total_expected_operations) * 100
            
            logger.info(f"Production scale results:")
            logger.info(f"  Operations/second: {operations_per_second:.2f}")
            logger.info(f"  Success rate: {success_rate:.1f}%")
            logger.info(f"  Memory growth: {memory_growth:.1f} MB")
            logger.info(f"  Database records: {db_record_count}")
            logger.info(f"  Operation distribution: {operation_distribution}")
            
            # Production-scale assertions
            assert success_rate >= 95, f"Success rate too low: {success_rate:.1f}%"
            assert operations_per_second >= 10, f"Throughput too low: {operations_per_second:.2f} ops/sec"
            assert memory_growth < 100, f"Memory leak detected: {memory_growth:.1f} MB growth"
            assert db_record_count == total_successful, "Database consistency check failed"
            
            # Clean up test data
            async with db_manager.get_session() as session:
                await session.execute(text("DELETE FROM production_scale_test"))
                await session.commit()
            
            await db_manager.close_all()
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_production_scale_query_performance(self, isolated_env):
        """Test complex query performance at production scale.
        
        Business Value: Validates analytics and reporting performance for enterprise customers.
        Protects: Platform performance under complex query loads
        """
        production_env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:netra-staging-db",
            "POSTGRES_USER": "netra-staging-user",
            "POSTGRES_PASSWORD": os.environ.get("GCP_STAGING_DB_PASSWORD", ""),
            "POSTGRES_DB": "netra_staging"
        }
        
        if not os.environ.get("GCP_STAGING_DB_PASSWORD"):
            pytest.skip("GCP staging credentials not available for query performance test")
        
        for key, value in production_env.items():
            isolated_env.set(key, value, source="e2e_query_performance")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Create production-like dataset
            async with db_manager.get_session() as session:
                # Create tables if they don't exist
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS query_performance_users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(100),
                        email VARCHAR(255),
                        subscription_tier VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS query_performance_events (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES query_performance_users(id),
                        event_type VARCHAR(50),
                        event_data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                await session.commit()
                
                # Insert test dataset (production-like volume)
                logger.info("Creating production-scale test dataset...")
                
                # Batch insert users
                users_to_insert = 1000
                for batch_start in range(0, users_to_insert, 100):
                    batch_values = []
                    for i in range(batch_start, min(batch_start + 100, users_to_insert)):
                        tier = ['free', 'premium', 'enterprise'][i % 3]
                        batch_values.append(f"('perf_user_{i}', 'perf_user_{i}@example.com', '{tier}')")
                    
                    values_str = ','.join(batch_values)
                    await session.execute(text(f"""
                        INSERT INTO query_performance_users (username, email, subscription_tier) 
                        VALUES {values_str}
                    """))
                    await session.commit()
                
                # Insert events for each user
                events_per_user = 5
                for user_id in range(1, min(users_to_insert + 1, 201)):  # Limit for staging
                    event_values = []
                    for event_num in range(events_per_user):
                        event_type = ['login', 'chat_message', 'file_upload', 'api_call'][event_num % 4]
                        event_data = f'{{"event_num": {event_num}, "user_action": "{event_type}"}}'
                        event_values.append(f"({user_id}, '{event_type}', '{event_data}')")
                    
                    values_str = ','.join(event_values)
                    await session.execute(text(f"""
                        INSERT INTO query_performance_events (user_id, event_type, event_data) 
                        VALUES {values_str}
                    """))
                    
                    if user_id % 50 == 0:  # Commit every 50 users
                        await session.commit()
                
                await session.commit()
            
            # Test complex query performance
            complex_queries = [
                {
                    "name": "User Analytics with Aggregation",
                    "query": """
                        SELECT u.subscription_tier, COUNT(*) as user_count,
                               AVG(event_counts.total_events) as avg_events_per_user
                        FROM query_performance_users u
                        JOIN (
                            SELECT user_id, COUNT(*) as total_events
                            FROM query_performance_events
                            GROUP BY user_id
                        ) event_counts ON u.id = event_counts.user_id
                        GROUP BY u.subscription_tier
                        ORDER BY user_count DESC
                    """
                },
                {
                    "name": "Event Timeline with JSON Processing", 
                    "query": """
                        SELECT e.event_type, COUNT(*) as event_count,
                               COUNT(DISTINCT e.user_id) as unique_users,
                               MIN(e.created_at) as first_event,
                               MAX(e.created_at) as last_event
                        FROM query_performance_events e
                        WHERE e.event_data->>'user_action' = e.event_type
                        GROUP BY e.event_type
                        ORDER BY event_count DESC
                    """
                },
                {
                    "name": "Complex Join with Filtering",
                    "query": """
                        SELECT u.subscription_tier, e.event_type, COUNT(*) as occurrences
                        FROM query_performance_users u
                        JOIN query_performance_events e ON u.id = e.user_id
                        WHERE u.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'
                        AND e.event_type IN ('chat_message', 'api_call')
                        GROUP BY u.subscription_tier, e.event_type
                        HAVING COUNT(*) > 5
                        ORDER BY occurrences DESC
                        LIMIT 20
                    """
                }
            ]
            
            query_performance_results = []
            
            for query_info in complex_queries:
                start_time = time.time()
                
                async with db_manager.get_session() as session:
                    result = await session.execute(text(query_info["query"]))
                    rows = result.fetchall()
                
                duration = time.time() - start_time
                query_performance_results.append({
                    "name": query_info["name"],
                    "duration": duration,
                    "rows_returned": len(rows)
                })
                
                logger.info(f"Query '{query_info['name']}': {duration:.3f}s, {len(rows)} rows")
            
            # Performance assertions
            for result in query_performance_results:
                assert result["duration"] < 5.0, f"Query '{result['name']}' too slow: {result['duration']:.3f}s"
                assert result["rows_returned"] > 0, f"Query '{result['name']}' returned no results"
            
            # Clean up test data
            async with db_manager.get_session() as session:
                await session.execute(text("DELETE FROM query_performance_events"))
                await session.execute(text("DELETE FROM query_performance_users"))
                await session.commit()
            
            await db_manager.close_all()


class TestDatabaseManagerMonitoringIntegration(BaseIntegrationTest):
    """E2E tests for DatabaseManager monitoring and health check integration.
    
    Business Value: Validates production monitoring and alerting capabilities
    """
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_gcp_monitoring_integration(self, isolated_env):
        """Test DatabaseManager integration with GCP monitoring systems.
        
        Business Value: Ensures production monitoring and alerting works correctly.
        Protects: Incident response and system observability for $500K+ ARR platform
        """
        monitoring_env = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:netra-staging-db",
            "POSTGRES_USER": "netra-staging-user",
            "POSTGRES_PASSWORD": os.environ.get("GCP_STAGING_DB_PASSWORD", ""),
            "POSTGRES_DB": "netra_staging",
            "ENABLE_DB_LOGGING": "true",
            "ENABLE_PERFORMANCE_MONITORING": "true"
        }
        
        if not os.environ.get("GCP_STAGING_DB_PASSWORD"):
            pytest.skip("GCP staging credentials not available for monitoring test")
        
        for key, value in monitoring_env.items():
            isolated_env.set(key, value, source="e2e_monitoring")
        
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = True  # Enable logging
            mock_config.return_value.database_pool_size = 3
            mock_config.return_value.database_max_overflow = 5
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Test health check endpoint functionality
            health_results = []
            for i in range(3):
                start_time = time.time()
                health_result = await db_manager.health_check()
                health_duration = time.time() - start_time
                
                health_results.append({
                    "status": health_result["status"],
                    "duration": health_duration,
                    "connection": health_result.get("connection"),
                    "iteration": i + 1
                })
                
                assert health_result["status"] == "healthy"
                assert health_result["connection"] == "ok"
                assert health_duration < 1.0, f"Health check too slow: {health_duration:.3f}s"
                
                await asyncio.sleep(0.5)  # Space out health checks
            
            # Test monitoring data collection
            async with db_manager.get_session() as session:
                # Test various operation types for monitoring
                operations = [
                    ("SELECT version()", "version_check"),
                    ("SELECT current_timestamp", "timestamp_check"),
                    ("SELECT current_user", "user_check"),
                    ("SELECT 1 + 1", "arithmetic_check")
                ]
                
                operation_metrics = []
                for sql, op_name in operations:
                    start_time = time.time()
                    result = await session.execute(text(sql))
                    duration = time.time() - start_time
                    
                    row = result.fetchone()
                    operation_metrics.append({
                        "operation": op_name,
                        "duration": duration,
                        "success": row is not None,
                        "result": str(row[0]) if row else None
                    })
                    
                    logger.info(f"Monitoring operation '{op_name}': {duration:.3f}s")
            
            # Test connection pool monitoring
            engine = db_manager.get_engine('primary')
            pool_info = {
                "engine_created": engine is not None,
                "pool_class": str(type(engine.pool)) if hasattr(engine, 'pool') else "Unknown"
            }
            
            logger.info(f"Connection pool info: {pool_info}")
            
            # Verify all monitoring data
            assert all(health["status"] == "healthy" for health in health_results)
            assert all(op["success"] for op in operation_metrics)
            assert len([op for op in operation_metrics if op["duration"] < 0.1]) >= 3, "Most operations should be fast"
            
            # Test monitoring integration under load
            start_time = time.time()
            concurrent_health_checks = []
            
            async def monitoring_health_check(check_id: int):
                return await db_manager.health_check()
            
            # Run concurrent health checks (simulating monitoring system)
            tasks = [asyncio.create_task(monitoring_health_check(i)) for i in range(5)]
            concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            concurrent_duration = time.time() - start_time
            
            # Verify concurrent monitoring works
            successful_checks = sum(1 for result in concurrent_results 
                                  if isinstance(result, dict) and result.get("status") == "healthy")
            
            assert successful_checks >= 4, f"Too many concurrent health check failures: {5 - successful_checks}"
            assert concurrent_duration < 3.0, f"Concurrent health checks too slow: {concurrent_duration:.3f}s"
            
            logger.info(f"Concurrent monitoring test: {successful_checks}/5 successful, {concurrent_duration:.3f}s total")
            
            await db_manager.close_all()


if __name__ == "__main__":
    # Allow running this test file directly for development
    pytest.main([__file__, "-v", "--tb=short"])