"""
Test Cloud SQL Proxy Connectivity

Validates database connectivity through Cloud SQL proxy
in the staging environment.
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import os
from typing import Optional

import asyncpg
import psycopg2
from psycopg2 import sql

# Add project root to path
from .base import StagingConfigTestBase

# Add project root to path


class TestCloudSQLProxyConnectivity(StagingConfigTestBase):
    """Test Cloud SQL proxy connectivity in staging."""
    
    def test_cloud_sql_instance_exists(self):
        """Verify Cloud SQL instance exists and is running."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        instance_name = 'postgres-staging'
        instance_info = self.assert_cloud_sql_instance_exists(instance_name)
        
        # Verify connection name format
        expected_connection = f"{self.project_id}:{self.region}:{instance_name}"
        self.assertEqual(instance_info['connection_name'], expected_connection,
                        f"Connection name mismatch. Expected: {expected_connection}")
                        
    def test_proxy_socket_connection(self):
        """Test connection via Cloud SQL proxy Unix socket."""
        self.skip_if_not_staging()
        
        # Cloud SQL proxy socket path
        socket_path = f"/cloudsql/{self.project_id}:{self.region}:postgres-staging"
        
        # Skip if socket doesn't exist (proxy not running locally)
        if not os.path.exists(socket_path):
            self.skipTest(f"Cloud SQL proxy socket not found at {socket_path}")
            
        try:
            # Get database credentials from secrets
            db_password = self.assert_secret_exists('database-password')
            
            # Connect via Unix socket
            conn = psycopg2.connect(
                host=socket_path,
                database='netra_staging',
                user='netra_user',
                password=db_password
            )
            
            # Test connection
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                self.assertIn('PostgreSQL', version,
                            "Connected to non-PostgreSQL database")
                            
            conn.close()
            
        except psycopg2.Error as e:
            self.fail(f"Failed to connect via Cloud SQL proxy: {e}")
            
    def test_direct_ssl_connection(self):
        """Test direct SSL connection to Cloud SQL."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        # Get Cloud SQL instance public IP
        instance_info = self.assert_cloud_sql_instance_exists('postgres-staging')
        
        if not instance_info.get('ip_address'):
            self.skipTest("Cloud SQL instance has no public IP")
            
        try:
            # Get database credentials
            db_password = self.assert_secret_exists('database-password')
            
            # Connect directly with SSL
            conn = psycopg2.connect(
                host=instance_info['ip_address'],
                port=5432,
                database='netra_staging',
                user='netra_user',
                password=db_password,
                sslmode='require'
            )
            
            # Verify SSL is active
            with conn.cursor() as cursor:
                cursor.execute("SELECT ssl_is_used()")
                ssl_used = cursor.fetchone()[0]
                self.assertTrue(ssl_used, "SSL not used for direct connection")
                
            conn.close()
            
        except psycopg2.Error as e:
            self.fail(f"Failed direct SSL connection: {e}")
            
    def test_database_url_formats(self):
        """Test different database URL formats work correctly."""
        self.skip_if_not_staging()
        
        connection_formats = [
            # Cloud SQL proxy format
            {
                'name': 'Cloud SQL Proxy',
                'url': 'postgresql://netra_user:{password}@/netra_staging?host=/cloudsql/{project}:{region}:postgres-staging',
                'requires_proxy': True
            },
            # Direct connection format
            {
                'name': 'Direct SSL',
                'url': 'postgresql://netra_user:{password}@{host}:5432/netra_staging?sslmode=require',
                'requires_proxy': False
            },
            # Connection with parameters
            {
                'name': 'With Pool Settings',
                'url': 'postgresql://netra_user:{password}@{host}/netra_staging?pool_size=20&max_overflow=0',
                'requires_proxy': False
            }
        ]
        
        # Get credentials
        try:
            db_password = self.assert_secret_exists('database-password')
        except AssertionError:
            self.skipTest("Database password secret not found")
            
        instance_info = self.assert_cloud_sql_instance_exists('postgres-staging')
        
        for conn_format in connection_formats:
            with self.subTest(format=conn_format['name']):
                # Skip proxy tests if proxy not running
                if conn_format['requires_proxy']:
                    socket_path = f"/cloudsql/{self.project_id}:{self.region}:postgres-staging"
                    if not os.path.exists(socket_path):
                        continue
                        
                # Format URL
                url = conn_format['url'].format(
                    password=db_password,
                    project=self.project_id,
                    region=self.region,
                    host=instance_info.get('ip_address', 'localhost')
                )
                
                # Test connection
                try:
                    conn = psycopg2.connect(url)
                    conn.close()
                except psycopg2.Error as e:
                    self.fail(f"Connection format '{conn_format['name']}' failed: {e}")
                    
    async def test_async_connection_pool(self):
        """Test async connection pooling with Cloud SQL."""
        self.skip_if_not_staging()
        
        try:
            db_password = self.assert_secret_exists('database-password')
        except AssertionError:
            self.skipTest("Database password secret not found")
            
        instance_info = self.assert_cloud_sql_instance_exists('postgres-staging')
        
        # Create async connection pool
        try:
            pool = await asyncpg.create_pool(
                host=instance_info.get('ip_address', 'localhost'),
                port=5432,
                user='netra_user',
                password=db_password,
                database='netra_staging',
                ssl='require',
                min_size=2,
                max_size=10,
                timeout=10
            )
            
            # Test pool connections
            async with pool.acquire() as conn:
                version = await conn.fetchval('SELECT version()')
                self.assertIn('PostgreSQL', version)
                
            # Test concurrent connections
            tasks = []
            for i in range(5):
                async def query(idx):
                    async with pool.acquire() as conn:
                        return await conn.fetchval('SELECT $1::int', idx)
                        
                tasks.append(query(i))
                
            results = await asyncio.gather(*tasks)
            self.assertEqual(results, list(range(5)),
                           "Concurrent queries failed")
                           
            await pool.close()
            
        except Exception as e:
            self.fail(f"Async connection pool failed: {e}")
            
    def test_connection_with_iam_auth(self):
        """Test connection using IAM database authentication."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        # IAM auth requires specific setup
        instance_info = self.assert_cloud_sql_instance_exists('postgres-staging')
        
        # Check if IAM auth is enabled
        try:
            # This would use IAM token instead of password
            # Requires database user created with Cloud IAM type
            self.skipTest("IAM database auth test requires specific user setup")
            
        except Exception as e:
            self.fail(f"IAM authentication failed: {e}")