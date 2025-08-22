"""
L3-10: Multi-tenant Data Isolation with Real Databases Integration Test

BVJ: Critical for enterprise security and compliance. Ensures complete data 
isolation between tenants, preventing data leaks and maintaining SOC2 compliance.

Tests multi-tenant data isolation with real PostgreSQL containers.
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

import asyncpg
import docker
import pytest
from netra_backend.app.database.row_level_security import RowLevelSecurityManager
from netra_backend.app.database.tenant_manager import TenantManager

from netra_backend.app.services.tenant_service import TenantService

@pytest.mark.L3
class TestMultiTenantIsolationL3:
    """Test multi-tenant data isolation with real databases."""
    
    @pytest.fixture(scope="class")
    async def docker_client(self):
        """Docker client for container management."""
        client = docker.from_env()
        yield client
        client.close()
    
    @pytest.fixture(scope="class")
    async def postgres_container(self, docker_client):
        """Start PostgreSQL container for testing."""
        container = docker_client.containers.run(
            "postgres:15",
            environment={
                "POSTGRES_DB": "tenant_test",
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_password"
            },
            ports={'5432/tcp': None},
            detach=True,
            name="tenant_test_postgres"
        )
        
        # Get assigned port
        container.reload()
        port = container.attrs['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort']
        
        # Wait for PostgreSQL to be ready
        await self._wait_for_postgres(port)
        
        connection_config = {
            "host": "localhost",
            "port": int(port),
            "database": "tenant_test",
            "user": "test_user",
            "password": "test_password"
        }
        
        yield connection_config
        
        container.stop()
        container.remove()
    
    async def _wait_for_postgres(self, port: str, timeout: int = 30):
        """Wait for PostgreSQL to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                conn = await asyncpg.connect(
                    host="localhost",
                    port=int(port),
                    database="tenant_test",
                    user="test_user",
                    password="test_password"
                )
                await conn.close()
                return
            except:
                await asyncio.sleep(0.5)
        raise TimeoutError(f"PostgreSQL not ready within {timeout}s")
    
    @pytest.fixture
    async def tenant_manager(self, postgres_container):
        """Create tenant manager with test database."""
        manager = TenantManager(postgres_container)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def rls_manager(self, postgres_container):
        """Create Row Level Security manager."""
        manager = RowLevelSecurityManager(postgres_container)
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.fixture
    async def test_tenants(self, tenant_manager):
        """Create test tenants."""
        tenant_a_id = str(uuid.uuid4())
        tenant_b_id = str(uuid.uuid4())
        tenant_c_id = str(uuid.uuid4())
        
        tenants = {
            "tenant_a": {
                "id": tenant_a_id,
                "name": "Acme Corp",
                "plan": "enterprise"
            },
            "tenant_b": {
                "id": tenant_b_id,
                "name": "Beta Inc",
                "plan": "professional"
            },
            "tenant_c": {
                "id": tenant_c_id,
                "name": "Gamma LLC",
                "plan": "starter"
            }
        }
        
        # Create tenants
        for tenant_key, tenant_data in tenants.items():
            await tenant_manager.create_tenant(
                tenant_data["id"],
                tenant_data["name"],
                tenant_data["plan"]
            )
        
        return tenants
    
    @pytest.mark.asyncio
    async def test_tenant_schema_isolation(
        self, 
        tenant_manager, 
        test_tenants
    ):
        """Test that each tenant has isolated database schema."""
        # Verify tenant schemas exist
        for tenant_key, tenant_data in test_tenants.items():
            schema_exists = await tenant_manager.schema_exists(tenant_data["id"])
            assert schema_exists is True
        
        # Verify schemas are isolated
        tenant_a_tables = await tenant_manager.get_tenant_tables(test_tenants["tenant_a"]["id"])
        tenant_b_tables = await tenant_manager.get_tenant_tables(test_tenants["tenant_b"]["id"])
        
        # Each tenant should have their own set of tables
        assert len(tenant_a_tables) > 0
        assert len(tenant_b_tables) > 0
        
        # Verify tenant-specific table naming
        for table in tenant_a_tables:
            assert test_tenants["tenant_a"]["id"] in table or "tenant_" in table
    
    @pytest.mark.asyncio
    async def test_row_level_security_isolation(
        self, 
        tenant_manager, 
        rls_manager, 
        test_tenants
    ):
        """Test Row Level Security prevents cross-tenant data access."""
        # Create shared table with RLS
        await rls_manager.create_shared_table(
            "documents",
            """
            id SERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL,
            title VARCHAR(200) NOT NULL,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
        )
        
        # Enable RLS on documents table
        await rls_manager.enable_rls("documents")
        
        # Create RLS policies
        await rls_manager.create_tenant_policy("documents")
        
        # Insert data for different tenants
        tenant_a_id = test_tenants["tenant_a"]["id"]
        tenant_b_id = test_tenants["tenant_b"]["id"]
        
        # Insert documents for tenant A
        await tenant_manager.insert_tenant_data(
            tenant_a_id,
            "documents",
            {"title": "Tenant A Doc 1", "content": "Secret A content"}
        )
        await tenant_manager.insert_tenant_data(
            tenant_a_id,
            "documents",
            {"title": "Tenant A Doc 2", "content": "More A content"}
        )
        
        # Insert documents for tenant B
        await tenant_manager.insert_tenant_data(
            tenant_b_id,
            "documents",
            {"title": "Tenant B Doc 1", "content": "Secret B content"}
        )
        
        # Query as tenant A - should only see tenant A data
        tenant_a_docs = await tenant_manager.query_tenant_data(
            tenant_a_id,
            "SELECT * FROM documents"
        )
        
        assert len(tenant_a_docs) == 2
        assert all(doc["tenant_id"] == tenant_a_id for doc in tenant_a_docs)
        assert "Secret A content" in [doc["content"] for doc in tenant_a_docs]
        assert "Secret B content" not in [doc["content"] for doc in tenant_a_docs]
        
        # Query as tenant B - should only see tenant B data
        tenant_b_docs = await tenant_manager.query_tenant_data(
            tenant_b_id,
            "SELECT * FROM documents"
        )
        
        assert len(tenant_b_docs) == 1
        assert tenant_b_docs[0]["tenant_id"] == tenant_b_id
        assert tenant_b_docs[0]["content"] == "Secret B content"
    
    @pytest.mark.asyncio
    async def test_tenant_user_isolation(
        self, 
        tenant_manager, 
        test_tenants
    ):
        """Test that tenant users cannot access other tenants' data."""
        # Create tenant-specific database users
        tenant_a_id = test_tenants["tenant_a"]["id"]
        tenant_b_id = test_tenants["tenant_b"]["id"]
        
        tenant_a_user = await tenant_manager.create_tenant_user(
            tenant_a_id,
            f"user_{tenant_a_id[:8]}"
        )
        
        tenant_b_user = await tenant_manager.create_tenant_user(
            tenant_b_id,
            f"user_{tenant_b_id[:8]}"
        )
        
        # Create test data
        await tenant_manager.create_tenant_table(
            tenant_a_id,
            "projects",
            """
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT
            """
        )
        
        await tenant_manager.insert_tenant_data(
            tenant_a_id,
            "projects",
            {"name": "Secret Project A", "description": "Top secret project"}
        )
        
        # Try to access tenant A data as tenant B user
        try:
            # This should fail due to isolation
            forbidden_data = await tenant_manager.query_as_tenant_user(
                tenant_b_user,
                tenant_a_id,
                "SELECT * FROM projects"
            )
            # If we get here, isolation failed
            assert False, "Tenant B user should not access Tenant A data"
        except Exception as e:
            # Expected - access should be denied
            assert "permission denied" in str(e).lower() or "does not exist" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_tenant_data_encryption(
        self, 
        tenant_manager, 
        test_tenants
    ):
        """Test that sensitive tenant data is encrypted at rest."""
        tenant_a_id = test_tenants["tenant_a"]["id"]
        
        # Create table with encrypted columns
        await tenant_manager.create_encrypted_table(
            tenant_a_id,
            "sensitive_data",
            """
            id SERIAL PRIMARY KEY,
            public_field VARCHAR(100),
            encrypted_field TEXT  -- This will be encrypted
            """
        )
        
        # Insert sensitive data
        sensitive_value = "Very sensitive information"
        await tenant_manager.insert_encrypted_data(
            tenant_a_id,
            "sensitive_data",
            {
                "public_field": "Public info",
                "encrypted_field": sensitive_value
            }
        )
        
        # Query decrypted data (should work with proper key)
        decrypted_data = await tenant_manager.query_decrypted_data(
            tenant_a_id,
            "SELECT * FROM sensitive_data"
        )
        
        assert len(decrypted_data) == 1
        assert decrypted_data[0]["encrypted_field"] == sensitive_value
        
        # Query raw data (should be encrypted)
        raw_data = await tenant_manager.query_raw_data(
            tenant_a_id,
            "SELECT * FROM sensitive_data"
        )
        
        assert raw_data[0]["encrypted_field"] != sensitive_value
        assert len(raw_data[0]["encrypted_field"]) > len(sensitive_value)  # Encrypted is longer
    
    @pytest.mark.asyncio
    async def test_cross_tenant_query_prevention(
        self, 
        tenant_manager, 
        test_tenants
    ):
        """Test that queries cannot access data across tenants."""
        tenant_a_id = test_tenants["tenant_a"]["id"]
        tenant_b_id = test_tenants["tenant_b"]["id"]
        
        # Create similar tables for both tenants
        for tenant_id in [tenant_a_id, tenant_b_id]:
            await tenant_manager.create_tenant_table(
                tenant_id,
                "orders",
                """
                id SERIAL PRIMARY KEY,
                amount DECIMAL(10,2),
                customer_name VARCHAR(100)
                """
            )
        
        # Insert data for both tenants
        await tenant_manager.insert_tenant_data(
            tenant_a_id,
            "orders",
            {"amount": 1000.00, "customer_name": "Customer A"}
        )
        
        await tenant_manager.insert_tenant_data(
            tenant_b_id,
            "orders",
            {"amount": 2000.00, "customer_name": "Customer B"}
        )
        
        # Try to run cross-tenant query as tenant A
        try:
            # This should fail - cannot access tenant B's schema
            cross_tenant_query = f"""
                SELECT a.amount as a_amount, b.amount as b_amount 
                FROM {tenant_a_id}.orders a 
                JOIN {tenant_b_id}.orders b ON 1=1
            """
            
            result = await tenant_manager.query_tenant_data(
                tenant_a_id,
                cross_tenant_query
            )
            
            # If we get here, isolation failed
            assert False, "Cross-tenant query should not be allowed"
            
        except Exception as e:
            # Expected - cross-tenant access should be denied
            assert "permission denied" in str(e).lower() or "does not exist" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_tenant_resource_limits(
        self, 
        tenant_manager, 
        test_tenants
    ):
        """Test that tenants have enforced resource limits."""
        tenant_a_id = test_tenants["tenant_a"]["id"]  # Enterprise plan
        tenant_c_id = test_tenants["tenant_c"]["id"]  # Starter plan
        
        # Set different limits based on plans
        await tenant_manager.set_tenant_limits(
            tenant_a_id,
            {"max_tables": 100, "max_rows_per_table": 1000000}
        )
        
        await tenant_manager.set_tenant_limits(
            tenant_c_id,
            {"max_tables": 5, "max_rows_per_table": 10000}
        )
        
        # Test table creation limits for starter plan
        table_count = 0
        try:
            for i in range(10):  # Try to create more than limit
                await tenant_manager.create_tenant_table(
                    tenant_c_id,
                    f"test_table_{i}",
                    "id SERIAL PRIMARY KEY, data TEXT"
                )
                table_count += 1
        except Exception as e:
            # Should hit limit before reaching 10 tables
            assert table_count <= 5
            assert "limit exceeded" in str(e).lower() or "quota" in str(e).lower()
        
        # Enterprise plan should allow more tables
        enterprise_table_count = 0
        for i in range(10):
            await tenant_manager.create_tenant_table(
                tenant_a_id,
                f"enterprise_table_{i}",
                "id SERIAL PRIMARY KEY, data TEXT"
            )
            enterprise_table_count += 1
        
        assert enterprise_table_count == 10
    
    @pytest.mark.asyncio
    async def test_tenant_backup_isolation(
        self, 
        tenant_manager, 
        test_tenants
    ):
        """Test that tenant backups are isolated and secure."""
        tenant_a_id = test_tenants["tenant_a"]["id"]
        tenant_b_id = test_tenants["tenant_b"]["id"]
        
        # Create and populate test data
        await tenant_manager.create_tenant_table(
            tenant_a_id,
            "backup_test",
            "id SERIAL PRIMARY KEY, data VARCHAR(100)"
        )
        
        await tenant_manager.insert_tenant_data(
            tenant_a_id,
            "backup_test",
            {"data": "Tenant A backup data"}
        )
        
        # Create backup for tenant A
        backup_id = await tenant_manager.create_tenant_backup(tenant_a_id)
        
        # Verify backup exists and is isolated
        backup_info = await tenant_manager.get_backup_info(backup_id)
        
        assert backup_info["tenant_id"] == tenant_a_id
        assert backup_info["status"] == "completed"
        
        # Try to access backup as tenant B (should fail)
        try:
            forbidden_backup = await tenant_manager.get_backup_info_as_tenant(
                backup_id, 
                tenant_b_id
            )
            assert False, "Tenant B should not access Tenant A backup"
        except Exception as e:
            assert "access denied" in str(e).lower() or "not found" in str(e).lower()
        
        # Restore backup for tenant A
        restore_result = await tenant_manager.restore_tenant_backup(
            tenant_a_id, 
            backup_id
        )
        
        assert restore_result["success"] is True
        
        # Verify restored data
        restored_data = await tenant_manager.query_tenant_data(
            tenant_a_id,
            "SELECT * FROM backup_test"
        )
        
        assert len(restored_data) == 1
        assert restored_data[0]["data"] == "Tenant A backup data"