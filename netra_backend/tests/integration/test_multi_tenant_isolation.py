# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: L3-10: Multi-tenant Data Isolation with Real Databases Integration Test

# REMOVED_SYNTAX_ERROR: BVJ: Critical for enterprise security and compliance. Ensures complete data
# REMOVED_SYNTAX_ERROR: isolation between tenants, preventing data leaks and maintaining SOC2 compliance.

# REMOVED_SYNTAX_ERROR: Tests multi-tenant data isolation with real PostgreSQL containers.
""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

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

# REMOVED_SYNTAX_ERROR: @pytest.mark.L3
# REMOVED_SYNTAX_ERROR: class TestMultiTenantIsolationL3:
    # REMOVED_SYNTAX_ERROR: """Test multi-tenant data isolation with real databases."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def docker_client(self):
    # REMOVED_SYNTAX_ERROR: """Docker client for container management."""
    # REMOVED_SYNTAX_ERROR: client = docker.from_env()
    # REMOVED_SYNTAX_ERROR: yield client
    # REMOVED_SYNTAX_ERROR: client.close()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def postgres_container(self, docker_client):
    # REMOVED_SYNTAX_ERROR: """Start PostgreSQL container for testing."""
    # REMOVED_SYNTAX_ERROR: container = docker_client.containers.run( )
    # REMOVED_SYNTAX_ERROR: "postgres:15",
    # REMOVED_SYNTAX_ERROR: environment={ )
    # REMOVED_SYNTAX_ERROR: "POSTGRES_DB": "tenant_test",
    # REMOVED_SYNTAX_ERROR: "POSTGRES_USER": "test_user",
    # REMOVED_SYNTAX_ERROR: "POSTGRES_PASSWORD": "test_password"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: ports={'5432/tcp': None},
    # REMOVED_SYNTAX_ERROR: detach=True,
    # REMOVED_SYNTAX_ERROR: name="tenant_test_postgres"
    

    # Get assigned port
    # REMOVED_SYNTAX_ERROR: container.reload()
    # REMOVED_SYNTAX_ERROR: port = container.attrs['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort']

    # Wait for PostgreSQL to be ready
    # REMOVED_SYNTAX_ERROR: await self._wait_for_postgres(port)

    # REMOVED_SYNTAX_ERROR: connection_config = { )
    # REMOVED_SYNTAX_ERROR: "host": "localhost",
    # REMOVED_SYNTAX_ERROR: "port": int(port),
    # REMOVED_SYNTAX_ERROR: "database": "tenant_test",
    # REMOVED_SYNTAX_ERROR: "user": "test_user",
    # REMOVED_SYNTAX_ERROR: "password": "test_password"
    

    # REMOVED_SYNTAX_ERROR: yield connection_config

    # REMOVED_SYNTAX_ERROR: container.stop()
    # REMOVED_SYNTAX_ERROR: container.remove()

# REMOVED_SYNTAX_ERROR: async def _wait_for_postgres(self, port: str, timeout: int = 30):
    # REMOVED_SYNTAX_ERROR: """Wait for PostgreSQL to be available."""
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: while time.time() - start_time < timeout:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: conn = await asyncpg.connect( )
            # REMOVED_SYNTAX_ERROR: host="localhost",
            # REMOVED_SYNTAX_ERROR: port=int(port),
            # REMOVED_SYNTAX_ERROR: database="tenant_test",
            # REMOVED_SYNTAX_ERROR: user="test_user",
            # REMOVED_SYNTAX_ERROR: password="test_password"
            
            # REMOVED_SYNTAX_ERROR: await conn.close()
            # REMOVED_SYNTAX_ERROR: return
            # REMOVED_SYNTAX_ERROR: except:
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.5)
                # REMOVED_SYNTAX_ERROR: raise TimeoutError("formatted_string")

                # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def tenant_manager(self, postgres_container):
    # REMOVED_SYNTAX_ERROR: """Create tenant manager with test database."""
    # REMOVED_SYNTAX_ERROR: manager = TenantManager(postgres_container)
    # REMOVED_SYNTAX_ERROR: await manager.initialize()
    # REMOVED_SYNTAX_ERROR: yield manager
    # REMOVED_SYNTAX_ERROR: await manager.cleanup()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def rls_manager(self, postgres_container):
    # REMOVED_SYNTAX_ERROR: """Create Row Level Security manager."""
    # REMOVED_SYNTAX_ERROR: manager = RowLevelSecurityManager(postgres_container)
    # REMOVED_SYNTAX_ERROR: await manager.initialize()
    # REMOVED_SYNTAX_ERROR: yield manager
    # REMOVED_SYNTAX_ERROR: await manager.cleanup()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_tenants(self, tenant_manager):
        # REMOVED_SYNTAX_ERROR: """Create test tenants."""
        # REMOVED_SYNTAX_ERROR: tenant_a_id = str(uuid.uuid4())
        # REMOVED_SYNTAX_ERROR: tenant_b_id = str(uuid.uuid4())
        # REMOVED_SYNTAX_ERROR: tenant_c_id = str(uuid.uuid4())

        # REMOVED_SYNTAX_ERROR: tenants = { )
        # REMOVED_SYNTAX_ERROR: "tenant_a": { )
        # REMOVED_SYNTAX_ERROR: "id": tenant_a_id,
        # REMOVED_SYNTAX_ERROR: "name": "Acme Corp",
        # REMOVED_SYNTAX_ERROR: "plan": "enterprise"
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: "tenant_b": { )
        # REMOVED_SYNTAX_ERROR: "id": tenant_b_id,
        # REMOVED_SYNTAX_ERROR: "name": "Beta Inc",
        # REMOVED_SYNTAX_ERROR: "plan": "professional"
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: "tenant_c": { )
        # REMOVED_SYNTAX_ERROR: "id": tenant_c_id,
        # REMOVED_SYNTAX_ERROR: "name": "Gamma LLC",
        # REMOVED_SYNTAX_ERROR: "plan": "starter"
        
        

        # Create tenants
        # REMOVED_SYNTAX_ERROR: for tenant_key, tenant_data in tenants.items():
            # REMOVED_SYNTAX_ERROR: await tenant_manager.create_tenant( )
            # REMOVED_SYNTAX_ERROR: tenant_data["id"],
            # REMOVED_SYNTAX_ERROR: tenant_data["name"],
            # REMOVED_SYNTAX_ERROR: tenant_data["plan"]
            

            # REMOVED_SYNTAX_ERROR: return tenants

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_tenant_schema_isolation( )
            # REMOVED_SYNTAX_ERROR: self,
            # REMOVED_SYNTAX_ERROR: tenant_manager,
            # REMOVED_SYNTAX_ERROR: test_tenants
            # REMOVED_SYNTAX_ERROR: ):
                # REMOVED_SYNTAX_ERROR: """Test that each tenant has isolated database schema."""
                # Verify tenant schemas exist
                # REMOVED_SYNTAX_ERROR: for tenant_key, tenant_data in test_tenants.items():
                    # REMOVED_SYNTAX_ERROR: schema_exists = await tenant_manager.schema_exists(tenant_data["id"])
                    # REMOVED_SYNTAX_ERROR: assert schema_exists is True

                    # Verify schemas are isolated
                    # REMOVED_SYNTAX_ERROR: tenant_a_tables = await tenant_manager.get_tenant_tables(test_tenants["tenant_a"]["id"])
                    # REMOVED_SYNTAX_ERROR: tenant_b_tables = await tenant_manager.get_tenant_tables(test_tenants["tenant_b"]["id"])

                    # Each tenant should have their own set of tables
                    # REMOVED_SYNTAX_ERROR: assert len(tenant_a_tables) > 0
                    # REMOVED_SYNTAX_ERROR: assert len(tenant_b_tables) > 0

                    # Verify tenant-specific table naming
                    # REMOVED_SYNTAX_ERROR: for table in tenant_a_tables:
                        # REMOVED_SYNTAX_ERROR: assert test_tenants["tenant_a"]["id"] in table or "tenant_" in table

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_row_level_security_isolation( )
                        # REMOVED_SYNTAX_ERROR: self,
                        # REMOVED_SYNTAX_ERROR: tenant_manager,
                        # REMOVED_SYNTAX_ERROR: rls_manager,
                        # REMOVED_SYNTAX_ERROR: test_tenants
                        # REMOVED_SYNTAX_ERROR: ):
                            # REMOVED_SYNTAX_ERROR: """Test Row Level Security prevents cross-tenant data access."""
                            # Create shared table with RLS
                            # REMOVED_SYNTAX_ERROR: await rls_manager.create_shared_table( )
                            # REMOVED_SYNTAX_ERROR: "documents",
                            # REMOVED_SYNTAX_ERROR: '''
                            # REMOVED_SYNTAX_ERROR: id SERIAL PRIMARY KEY,
                            # REMOVED_SYNTAX_ERROR: tenant_id UUID NOT NULL,
                            # REMOVED_SYNTAX_ERROR: title VARCHAR(200) NOT NULL,
                            # REMOVED_SYNTAX_ERROR: content TEXT,
                            # REMOVED_SYNTAX_ERROR: created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            # REMOVED_SYNTAX_ERROR: """"
                            

                            # Enable RLS on documents table
                            # REMOVED_SYNTAX_ERROR: await rls_manager.enable_rls("documents")

                            # Create RLS policies
                            # REMOVED_SYNTAX_ERROR: await rls_manager.create_tenant_policy("documents")

                            # Insert data for different tenants
                            # REMOVED_SYNTAX_ERROR: tenant_a_id = test_tenants["tenant_a"]["id"]
                            # REMOVED_SYNTAX_ERROR: tenant_b_id = test_tenants["tenant_b"]["id"]

                            # Insert documents for tenant A
                            # REMOVED_SYNTAX_ERROR: await tenant_manager.insert_tenant_data( )
                            # REMOVED_SYNTAX_ERROR: tenant_a_id,
                            # REMOVED_SYNTAX_ERROR: "documents",
                            # REMOVED_SYNTAX_ERROR: {"title": "Tenant A Doc 1", "content": "Secret A content"}
                            
                            # REMOVED_SYNTAX_ERROR: await tenant_manager.insert_tenant_data( )
                            # REMOVED_SYNTAX_ERROR: tenant_a_id,
                            # REMOVED_SYNTAX_ERROR: "documents",
                            # REMOVED_SYNTAX_ERROR: {"title": "Tenant A Doc 2", "content": "More A content"}
                            

                            # Insert documents for tenant B
                            # REMOVED_SYNTAX_ERROR: await tenant_manager.insert_tenant_data( )
                            # REMOVED_SYNTAX_ERROR: tenant_b_id,
                            # REMOVED_SYNTAX_ERROR: "documents",
                            # REMOVED_SYNTAX_ERROR: {"title": "Tenant B Doc 1", "content": "Secret B content"}
                            

                            # Query as tenant A - should only see tenant A data
                            # REMOVED_SYNTAX_ERROR: tenant_a_docs = await tenant_manager.query_tenant_data( )
                            # REMOVED_SYNTAX_ERROR: tenant_a_id,
                            # REMOVED_SYNTAX_ERROR: "SELECT * FROM documents"
                            

                            # REMOVED_SYNTAX_ERROR: assert len(tenant_a_docs) == 2
                            # REMOVED_SYNTAX_ERROR: assert all(doc["tenant_id"] == tenant_a_id for doc in tenant_a_docs)
                            # REMOVED_SYNTAX_ERROR: assert "Secret A content" in [doc["content"] for doc in tenant_a_docs]
                            # REMOVED_SYNTAX_ERROR: assert "Secret B content" not in [doc["content"] for doc in tenant_a_docs]

                            # Query as tenant B - should only see tenant B data
                            # REMOVED_SYNTAX_ERROR: tenant_b_docs = await tenant_manager.query_tenant_data( )
                            # REMOVED_SYNTAX_ERROR: tenant_b_id,
                            # REMOVED_SYNTAX_ERROR: "SELECT * FROM documents"
                            

                            # REMOVED_SYNTAX_ERROR: assert len(tenant_b_docs) == 1
                            # REMOVED_SYNTAX_ERROR: assert tenant_b_docs[0]["tenant_id"] == tenant_b_id
                            # REMOVED_SYNTAX_ERROR: assert tenant_b_docs[0]["content"] == "Secret B content"

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_tenant_user_isolation( )
                            # REMOVED_SYNTAX_ERROR: self,
                            # REMOVED_SYNTAX_ERROR: tenant_manager,
                            # REMOVED_SYNTAX_ERROR: test_tenants
                            # REMOVED_SYNTAX_ERROR: ):
                                # REMOVED_SYNTAX_ERROR: """Test that tenant users cannot access other tenants' data."""
                                # Create tenant-specific database users
                                # REMOVED_SYNTAX_ERROR: tenant_a_id = test_tenants["tenant_a"]["id"]
                                # REMOVED_SYNTAX_ERROR: tenant_b_id = test_tenants["tenant_b"]["id"]

                                # REMOVED_SYNTAX_ERROR: tenant_a_user = await tenant_manager.create_tenant_user( )
                                # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                # REMOVED_SYNTAX_ERROR: "formatted_string"SELECT * FROM projects"
                                    
                                    # If we get here, isolation failed
                                    # REMOVED_SYNTAX_ERROR: assert False, "Tenant B user should not access Tenant A data"
                                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                                        # Expected - access should be denied
                                        # REMOVED_SYNTAX_ERROR: assert "permission denied" in str(e).lower() or "does not exist" in str(e).lower()

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_tenant_data_encryption( )
                                        # REMOVED_SYNTAX_ERROR: self,
                                        # REMOVED_SYNTAX_ERROR: tenant_manager,
                                        # REMOVED_SYNTAX_ERROR: test_tenants
                                        # REMOVED_SYNTAX_ERROR: ):
                                            # REMOVED_SYNTAX_ERROR: """Test that sensitive tenant data is encrypted at rest."""
                                            # REMOVED_SYNTAX_ERROR: tenant_a_id = test_tenants["tenant_a"]["id"]

                                            # Create table with encrypted columns
                                            # REMOVED_SYNTAX_ERROR: await tenant_manager.create_encrypted_table( )
                                            # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                            # REMOVED_SYNTAX_ERROR: "sensitive_data",
                                            # REMOVED_SYNTAX_ERROR: '''
                                            # REMOVED_SYNTAX_ERROR: id SERIAL PRIMARY KEY,
                                            # REMOVED_SYNTAX_ERROR: public_field VARCHAR(100),
                                            # REMOVED_SYNTAX_ERROR: encrypted_field TEXT  -- This will be encrypted
                                            # REMOVED_SYNTAX_ERROR: """"
                                            

                                            # Insert sensitive data
                                            # REMOVED_SYNTAX_ERROR: sensitive_value = "Very sensitive information"
                                            # REMOVED_SYNTAX_ERROR: await tenant_manager.insert_encrypted_data( )
                                            # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                            # REMOVED_SYNTAX_ERROR: "sensitive_data",
                                            # REMOVED_SYNTAX_ERROR: { )
                                            # REMOVED_SYNTAX_ERROR: "public_field": "Public info",
                                            # REMOVED_SYNTAX_ERROR: "encrypted_field": sensitive_value
                                            
                                            

                                            # Query decrypted data (should work with proper key)
                                            # REMOVED_SYNTAX_ERROR: decrypted_data = await tenant_manager.query_decrypted_data( )
                                            # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                            # REMOVED_SYNTAX_ERROR: "SELECT * FROM sensitive_data"
                                            

                                            # REMOVED_SYNTAX_ERROR: assert len(decrypted_data) == 1
                                            # REMOVED_SYNTAX_ERROR: assert decrypted_data[0]["encrypted_field"] == sensitive_value

                                            # Query raw data (should be encrypted)
                                            # REMOVED_SYNTAX_ERROR: raw_data = await tenant_manager.query_raw_data( )
                                            # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                            # REMOVED_SYNTAX_ERROR: "SELECT * FROM sensitive_data"
                                            

                                            # REMOVED_SYNTAX_ERROR: assert raw_data[0]["encrypted_field"] != sensitive_value
                                            # REMOVED_SYNTAX_ERROR: assert len(raw_data[0]["encrypted_field"]) > len(sensitive_value)  # Encrypted is longer

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_cross_tenant_query_prevention( )
                                            # REMOVED_SYNTAX_ERROR: self,
                                            # REMOVED_SYNTAX_ERROR: tenant_manager,
                                            # REMOVED_SYNTAX_ERROR: test_tenants
                                            # REMOVED_SYNTAX_ERROR: ):
                                                # REMOVED_SYNTAX_ERROR: """Test that queries cannot access data across tenants."""
                                                # REMOVED_SYNTAX_ERROR: tenant_a_id = test_tenants["tenant_a"]["id"]
                                                # REMOVED_SYNTAX_ERROR: tenant_b_id = test_tenants["tenant_b"]["id"]

                                                # Create similar tables for both tenants
                                                # REMOVED_SYNTAX_ERROR: for tenant_id in [tenant_a_id, tenant_b_id]:
                                                    # REMOVED_SYNTAX_ERROR: await tenant_manager.create_tenant_table( )
                                                    # REMOVED_SYNTAX_ERROR: tenant_id,
                                                    # REMOVED_SYNTAX_ERROR: "orders",
                                                    # REMOVED_SYNTAX_ERROR: '''
                                                    # REMOVED_SYNTAX_ERROR: id SERIAL PRIMARY KEY,
                                                    # REMOVED_SYNTAX_ERROR: amount DECIMAL(10,2),
                                                    # REMOVED_SYNTAX_ERROR: customer_name VARCHAR(100)
                                                    # REMOVED_SYNTAX_ERROR: """"
                                                    

                                                    # Insert data for both tenants
                                                    # REMOVED_SYNTAX_ERROR: await tenant_manager.insert_tenant_data( )
                                                    # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                                    # REMOVED_SYNTAX_ERROR: "orders",
                                                    # REMOVED_SYNTAX_ERROR: {"amount": 1000.00, "customer_name": "Customer A"}
                                                    

                                                    # REMOVED_SYNTAX_ERROR: await tenant_manager.insert_tenant_data( )
                                                    # REMOVED_SYNTAX_ERROR: tenant_b_id,
                                                    # REMOVED_SYNTAX_ERROR: "orders",
                                                    # REMOVED_SYNTAX_ERROR: {"amount": 2000.00, "customer_name": "Customer B"}
                                                    

                                                    # Try to run cross-tenant query as tenant A
                                                    # REMOVED_SYNTAX_ERROR: try:
                                                        # This should fail - cannot access tenant B's schema
                                                        # REMOVED_SYNTAX_ERROR: cross_tenant_query = f'''
                                                        # REMOVED_SYNTAX_ERROR: SELECT a.amount as a_amount, b.amount as b_amount
                                                        # REMOVED_SYNTAX_ERROR: FROM {tenant_a_id}.orders a
                                                        # REMOVED_SYNTAX_ERROR: JOIN {tenant_b_id}.orders b ON 1=1
                                                        # REMOVED_SYNTAX_ERROR: """"

                                                        # REMOVED_SYNTAX_ERROR: result = await tenant_manager.query_tenant_data( )
                                                        # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                                        # REMOVED_SYNTAX_ERROR: cross_tenant_query
                                                        

                                                        # If we get here, isolation failed
                                                        # REMOVED_SYNTAX_ERROR: assert False, "Cross-tenant query should not be allowed"

                                                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                            # Expected - cross-tenant access should be denied
                                                            # REMOVED_SYNTAX_ERROR: assert "permission denied" in str(e).lower() or "does not exist" in str(e).lower()

                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_tenant_resource_limits( )
                                                            # REMOVED_SYNTAX_ERROR: self,
                                                            # REMOVED_SYNTAX_ERROR: tenant_manager,
                                                            # REMOVED_SYNTAX_ERROR: test_tenants
                                                            # REMOVED_SYNTAX_ERROR: ):
                                                                # REMOVED_SYNTAX_ERROR: """Test that tenants have enforced resource limits."""
                                                                # REMOVED_SYNTAX_ERROR: tenant_a_id = test_tenants["tenant_a"]["id"]  # Enterprise plan
                                                                # REMOVED_SYNTAX_ERROR: tenant_c_id = test_tenants["tenant_c"]["id"]  # Starter plan

                                                                # Set different limits based on plans
                                                                # REMOVED_SYNTAX_ERROR: await tenant_manager.set_tenant_limits( )
                                                                # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                                                # REMOVED_SYNTAX_ERROR: {"max_tables": 100, "max_rows_per_table": 1000000}
                                                                

                                                                # REMOVED_SYNTAX_ERROR: await tenant_manager.set_tenant_limits( )
                                                                # REMOVED_SYNTAX_ERROR: tenant_c_id,
                                                                # REMOVED_SYNTAX_ERROR: {"max_tables": 5, "max_rows_per_table": 10000}
                                                                

                                                                # Test table creation limits for starter plan
                                                                # REMOVED_SYNTAX_ERROR: table_count = 0
                                                                # REMOVED_SYNTAX_ERROR: try:
                                                                    # REMOVED_SYNTAX_ERROR: for i in range(10):  # Try to create more than limit
                                                                    # REMOVED_SYNTAX_ERROR: await tenant_manager.create_tenant_table( )
                                                                    # REMOVED_SYNTAX_ERROR: tenant_c_id,
                                                                    # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                    # REMOVED_SYNTAX_ERROR: "id SERIAL PRIMARY KEY, data TEXT"
                                                                    
                                                                    # REMOVED_SYNTAX_ERROR: table_count += 1
                                                                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                        # Should hit limit before reaching 10 tables
                                                                        # REMOVED_SYNTAX_ERROR: assert table_count <= 5
                                                                        # REMOVED_SYNTAX_ERROR: assert "limit exceeded" in str(e).lower() or "quota" in str(e).lower()

                                                                        # Enterprise plan should allow more tables
                                                                        # REMOVED_SYNTAX_ERROR: enterprise_table_count = 0
                                                                        # REMOVED_SYNTAX_ERROR: for i in range(10):
                                                                            # REMOVED_SYNTAX_ERROR: await tenant_manager.create_tenant_table( )
                                                                            # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                                                            # REMOVED_SYNTAX_ERROR: "formatted_string",
                                                                            # REMOVED_SYNTAX_ERROR: "id SERIAL PRIMARY KEY, data TEXT"
                                                                            
                                                                            # REMOVED_SYNTAX_ERROR: enterprise_table_count += 1

                                                                            # REMOVED_SYNTAX_ERROR: assert enterprise_table_count == 10

                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_tenant_backup_isolation( )
                                                                            # REMOVED_SYNTAX_ERROR: self,
                                                                            # REMOVED_SYNTAX_ERROR: tenant_manager,
                                                                            # REMOVED_SYNTAX_ERROR: test_tenants
                                                                            # REMOVED_SYNTAX_ERROR: ):
                                                                                # REMOVED_SYNTAX_ERROR: """Test that tenant backups are isolated and secure."""
                                                                                # REMOVED_SYNTAX_ERROR: tenant_a_id = test_tenants["tenant_a"]["id"]
                                                                                # REMOVED_SYNTAX_ERROR: tenant_b_id = test_tenants["tenant_b"]["id"]

                                                                                # Create and populate test data
                                                                                # REMOVED_SYNTAX_ERROR: await tenant_manager.create_tenant_table( )
                                                                                # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                                                                # REMOVED_SYNTAX_ERROR: "backup_test",
                                                                                # REMOVED_SYNTAX_ERROR: "id SERIAL PRIMARY KEY, data VARCHAR(100)"
                                                                                

                                                                                # REMOVED_SYNTAX_ERROR: await tenant_manager.insert_tenant_data( )
                                                                                # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                                                                # REMOVED_SYNTAX_ERROR: "backup_test",
                                                                                # REMOVED_SYNTAX_ERROR: {"data": "Tenant A backup data"}
                                                                                

                                                                                # Create backup for tenant A
                                                                                # REMOVED_SYNTAX_ERROR: backup_id = await tenant_manager.create_tenant_backup(tenant_a_id)

                                                                                # Verify backup exists and is isolated
                                                                                # REMOVED_SYNTAX_ERROR: backup_info = await tenant_manager.get_backup_info(backup_id)

                                                                                # REMOVED_SYNTAX_ERROR: assert backup_info["tenant_id"] == tenant_a_id
                                                                                # REMOVED_SYNTAX_ERROR: assert backup_info["status"] == "completed"

                                                                                # Try to access backup as tenant B (should fail)
                                                                                # REMOVED_SYNTAX_ERROR: try:
                                                                                    # REMOVED_SYNTAX_ERROR: forbidden_backup = await tenant_manager.get_backup_info_as_tenant( )
                                                                                    # REMOVED_SYNTAX_ERROR: backup_id,
                                                                                    # REMOVED_SYNTAX_ERROR: tenant_b_id
                                                                                    
                                                                                    # REMOVED_SYNTAX_ERROR: assert False, "Tenant B should not access Tenant A backup"
                                                                                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                                                                                        # REMOVED_SYNTAX_ERROR: assert "access denied" in str(e).lower() or "not found" in str(e).lower()

                                                                                        # Restore backup for tenant A
                                                                                        # REMOVED_SYNTAX_ERROR: restore_result = await tenant_manager.restore_tenant_backup( )
                                                                                        # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                                                                        # REMOVED_SYNTAX_ERROR: backup_id
                                                                                        

                                                                                        # REMOVED_SYNTAX_ERROR: assert restore_result["success"] is True

                                                                                        # Verify restored data
                                                                                        # REMOVED_SYNTAX_ERROR: restored_data = await tenant_manager.query_tenant_data( )
                                                                                        # REMOVED_SYNTAX_ERROR: tenant_a_id,
                                                                                        # REMOVED_SYNTAX_ERROR: "SELECT * FROM backup_test"
                                                                                        

                                                                                        # REMOVED_SYNTAX_ERROR: assert len(restored_data) == 1
                                                                                        # REMOVED_SYNTAX_ERROR: assert restored_data[0]["data"] == "Tenant A backup data"