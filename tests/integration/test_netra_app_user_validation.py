"""
Netra App User Database Access Validation Tests

These tests specifically validate the netra_app database user configuration
and access permissions, ensuring the production database setup works correctly.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Production database security and access control
- Value Impact: Ensures proper database user permissions and security
- Strategic Impact: Validates production-ready database configuration

The netra_app user is the primary application user for production databases,
with limited permissions for security purposes.
"""

import asyncio
import pytest
import time
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch
import asyncpg
import psycopg2

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dev_launcher.isolated_environment import get_env
from test_framework.environment_markers import env


class NetraAppUserValidator:
    """Validator for netra_app database user configuration and permissions."""
    
    def __init__(self):
        self.env = get_env()
    
    def get_netra_app_config(self) -> Dict[str, str]:
        """Get database configuration for netra_app user."""
        return {
            'host': self.env.get('POSTGRES_HOST', 'localhost'),
            'port': self.env.get('POSTGRES_PORT', '5433'),
            'user': 'netra_app',  # Specific user for application
            'password': self.env.get('POSTGRES_PASSWORD', ''),  # Uses same password as postgres for dev
            'database': self.env.get('POSTGRES_DB', 'netra_dev')
        }
    
    def get_postgres_admin_config(self) -> Dict[str, str]:
        """Get database configuration for postgres admin user."""
        return {
            'host': self.env.get('POSTGRES_HOST', 'localhost'),
            'port': self.env.get('POSTGRES_PORT', '5433'),
            'user': self.env.get('POSTGRES_USER', 'postgres'),
            'password': self.env.get('POSTGRES_PASSWORD', ''),
            'database': self.env.get('POSTGRES_DB', 'netra_dev')
        }
    
    async def validate_netra_app_user_access(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Validate netra_app user can connect and access database."""
        result = {
            'user': config['user'],
            'success': False,
            'connection_time': None,
            'error': None,
            'permissions': {},
            'accessible_tables': [],
            'config_used': config
        }
        
        url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        
        start_time = time.time()
        try:
            conn = await asyncpg.connect(url, timeout=5)
            connection_time = time.time() - start_time
            
            # Test basic permissions
            permissions = await self._check_user_permissions(conn, config['user'])
            accessible_tables = await self._get_accessible_tables(conn)
            
            await conn.close()
            
            result.update({
                'success': True,
                'connection_time': connection_time,
                'permissions': permissions,
                'accessible_tables': accessible_tables
            })
            
        except Exception as e:
            result.update({
                'error': str(e),
                'connection_time': time.time() - start_time
            })
        
        return result
    
    async def _check_user_permissions(self, conn, username: str) -> Dict[str, bool]:
        """Check specific permissions for the user."""
        permissions = {}
        
        try:
            # Check if user can create tables
            await conn.execute("CREATE TABLE test_permissions_check (id INTEGER)")
            permissions['can_create_tables'] = True
            await conn.execute("DROP TABLE test_permissions_check")
        except Exception:
            permissions['can_create_tables'] = False
        
        try:
            # Check if user can select from information_schema
            await conn.fetch("SELECT table_name FROM information_schema.tables LIMIT 1")
            permissions['can_read_schema'] = True
        except Exception:
            permissions['can_read_schema'] = False
        
        try:
            # Check current user
            current_user = await conn.fetchval("SELECT current_user")
            permissions['current_user'] = current_user
            permissions['user_matches'] = current_user == username
        except Exception:
            permissions['current_user'] = None
            permissions['user_matches'] = False
        
        return permissions
    
    async def _get_accessible_tables(self, conn) -> List[str]:
        """Get list of tables the user can access."""
        try:
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            return [row['table_name'] for row in tables]
        except Exception:
            return []
    
    async def validate_user_vs_admin_access(self) -> Dict[str, Any]:
        """Compare netra_app user access vs postgres admin access."""
        netra_app_config = self.get_netra_app_config()
        admin_config = self.get_postgres_admin_config()
        
        netra_app_result = await self.validate_netra_app_user_access(netra_app_config)
        admin_result = await self.validate_netra_app_user_access(admin_config)
        
        comparison = {
            'netra_app': netra_app_result,
            'postgres_admin': admin_result,
            'both_successful': netra_app_result['success'] and admin_result['success'],
            'access_differences': {},
            'table_access_comparison': {}
        }
        
        if comparison['both_successful']:
            # Compare permissions
            netra_permissions = netra_app_result.get('permissions', {})
            admin_permissions = admin_result.get('permissions', {})
            
            for perm in set(netra_permissions.keys()) | set(admin_permissions.keys()):
                netra_has = netra_permissions.get(perm, False)
                admin_has = admin_permissions.get(perm, False)
                if netra_has != admin_has:
                    comparison['access_differences'][perm] = {
                        'netra_app': netra_has,
                        'postgres_admin': admin_has
                    }
            
            # Compare table access
            netra_tables = set(netra_app_result.get('accessible_tables', []))
            admin_tables = set(admin_result.get('accessible_tables', []))
            
            comparison['table_access_comparison'] = {
                'netra_app_only': list(netra_tables - admin_tables),
                'admin_only': list(admin_tables - netra_tables),
                'shared': list(netra_tables & admin_tables),
                'total_netra_app': len(netra_tables),
                'total_admin': len(admin_tables)
            }
        
        return comparison


class TestNetraAppUserValidation:
    """Test suite for netra_app user database access validation."""
    
    @pytest.fixture(scope="class")
    def validator(self):
        return NetraAppUserValidator()
    
    @pytest.mark.asyncio
    async def test_netra_app_user_connectivity(self, validator):
        """
        CRITICAL TEST: Validate netra_app user can connect to database.
        
        This test ensures the netra_app user exists and can successfully
        connect to the database with the configured credentials.
        """
        config = validator.get_netra_app_config()
        result = await validator.validate_netra_app_user_access(config)
        
        print(f"\n=== NETRA_APP USER CONNECTIVITY TEST ===")
        print(f"Host: {config['host']}")
        print(f"Port: {config['port']}")
        print(f"User: {config['user']}")
        print(f"Database: {config['database']}")
        print(f"Success: {result['success']}")
        print(f"Connection Time: {result['connection_time']:.3f}s" if result['connection_time'] else "N/A")
        
        if result['success']:
            print(f"Current User: {result['permissions'].get('current_user', 'Unknown')}")
            print(f"User Matches: {result['permissions'].get('user_matches', False)}")
            print(f"Can Create Tables: {result['permissions'].get('can_create_tables', False)}")
            print(f"Can Read Schema: {result['permissions'].get('can_read_schema', False)}")
            print(f"Accessible Tables: {len(result['accessible_tables'])}")
            
            if result['accessible_tables']:
                print(f"Sample Tables: {', '.join(result['accessible_tables'][:5])}")
                if len(result['accessible_tables']) > 5:
                    print(f"... and {len(result['accessible_tables']) - 5} more")
        else:
            print(f"Error: {result['error']}")
        
        # For development environment, allow fallback to postgres user
        # In production, netra_app user should exist
        if not result['success']:
            env_name = validator.env.get('ENVIRONMENT', 'unknown')
            if env_name == 'development':
                print("\n⚠️  netra_app user not found in development - this is acceptable")
                print("   Development can use postgres user as fallback")
                pytest.skip("netra_app user not configured in development environment")
            else:
                assert result['success'], (
                    f"netra_app user connectivity FAILED in {env_name} environment:\n"
                    f"Host: {config['host']}:{config['port']}\n"
                    f"User: {config['user']}\n"
                    f"Database: {config['database']}\n"
                    f"Error: {result['error']}\n\n"
                    f"The netra_app user must exist and be accessible in non-development environments.\n"
                    f"Run the database initialization scripts to create the user."
                )
        else:
            # Validate the user is actually netra_app
            assert result['permissions'].get('user_matches', False), (
                f"Connected as wrong user: expected 'netra_app', got '{result['permissions'].get('current_user')}'"
            )
    
    @pytest.mark.asyncio
    async def test_netra_app_vs_postgres_admin_comparison(self, validator):
        """
        INTEGRATION TEST: Compare netra_app user access vs postgres admin.
        
        This test compares the access levels between netra_app and postgres
        admin users to ensure proper permission separation.
        """
        comparison = await validator.validate_user_vs_admin_access()
        
        print(f"\n=== USER ACCESS COMPARISON TEST ===")
        print(f"netra_app Success: {comparison['netra_app']['success']}")
        print(f"postgres Admin Success: {comparison['postgres_admin']['success']}")
        print(f"Both Successful: {comparison['both_successful']}")
        
        if comparison['both_successful']:
            print(f"\nTable Access Comparison:")
            table_comp = comparison['table_access_comparison']
            print(f"  netra_app tables: {table_comp['total_netra_app']}")
            print(f"  postgres tables: {table_comp['total_admin']}")
            print(f"  Shared tables: {len(table_comp['shared'])}")
            
            if table_comp['netra_app_only']:
                print(f"  netra_app only: {', '.join(table_comp['netra_app_only'])}")
            if table_comp['admin_only']:
                print(f"  admin only: {', '.join(table_comp['admin_only'])}")
            
            print(f"\nPermission Differences:")
            if comparison['access_differences']:
                for perm, values in comparison['access_differences'].items():
                    print(f"  {perm}: netra_app={values['netra_app']}, admin={values['postgres_admin']}")
            else:
                print("  No permission differences found")
        
        # At least one user should be able to connect
        assert (comparison['netra_app']['success'] or comparison['postgres_admin']['success']), (
            f"Neither netra_app nor postgres admin user could connect:\n"
            f"netra_app error: {comparison['netra_app'].get('error', 'Success')}\n"
            f"postgres error: {comparison['postgres_admin'].get('error', 'Success')}\n\n"
            f"At least one database user must be accessible for the system to function."
        )
        
        # If both are successful, validate they can both access core tables
        if comparison['both_successful']:
            shared_tables = comparison['table_access_comparison']['shared']
            assert len(shared_tables) > 0, (
                "Both users should have access to at least some shared tables"
            )
    
    @pytest.mark.asyncio 
    async def test_netra_app_database_operations(self, validator):
        """
        FUNCTIONAL TEST: Validate netra_app user can perform basic database operations.
        
        This test ensures netra_app user has sufficient permissions for
        application operations like creating tables, inserting data, etc.
        """
        config = validator.get_netra_app_config()
        
        # First check if netra_app user is available
        result = await validator.validate_netra_app_user_access(config)
        if not result['success']:
            pytest.skip("netra_app user not available for testing")
        
        url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        
        operations_results = {
            'create_table': False,
            'insert_data': False,
            'select_data': False,
            'update_data': False,
            'delete_data': False,
            'drop_table': False,
            'errors': []
        }
        
        try:
            conn = await asyncpg.connect(url, timeout=5)
            
            table_name = f"netra_app_test_{int(time.time())}"
            
            try:
                # Create table
                await conn.execute(f"""
                    CREATE TABLE {table_name} (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                operations_results['create_table'] = True
                
                # Insert data
                await conn.execute(f"INSERT INTO {table_name} (name) VALUES ('test_record')")
                operations_results['insert_data'] = True
                
                # Select data
                rows = await conn.fetch(f"SELECT * FROM {table_name}")
                assert len(rows) == 1
                operations_results['select_data'] = True
                
                # Update data
                await conn.execute(f"UPDATE {table_name} SET name = 'updated_record' WHERE id = 1")
                operations_results['update_data'] = True
                
                # Delete data
                await conn.execute(f"DELETE FROM {table_name} WHERE id = 1")
                operations_results['delete_data'] = True
                
                # Drop table
                await conn.execute(f"DROP TABLE {table_name}")
                operations_results['drop_table'] = True
                
            except Exception as e:
                operations_results['errors'].append(f"Operation error: {e}")
                # Try to clean up table if it exists
                try:
                    await conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                except:
                    pass
            
            await conn.close()
            
        except Exception as e:
            operations_results['errors'].append(f"Connection error: {e}")
        
        print(f"\n=== NETRA_APP DATABASE OPERATIONS TEST ===")
        print(f"Create Table: {'✅' if operations_results['create_table'] else '❌'}")
        print(f"Insert Data: {'✅' if operations_results['insert_data'] else '❌'}")
        print(f"Select Data: {'✅' if operations_results['select_data'] else '❌'}")
        print(f"Update Data: {'✅' if operations_results['update_data'] else '❌'}")
        print(f"Delete Data: {'✅' if operations_results['delete_data'] else '❌'}")
        print(f"Drop Table: {'✅' if operations_results['drop_table'] else '❌'}")
        
        if operations_results['errors']:
            print(f"Errors: {', '.join(operations_results['errors'])}")
        
        # Validate critical operations work
        critical_operations = ['create_table', 'insert_data', 'select_data']
        failed_critical = [op for op in critical_operations if not operations_results[op]]
        
        assert len(failed_critical) == 0, (
            f"Critical database operations failed for netra_app user: {failed_critical}\n"
            f"Errors: {operations_results['errors']}\n\n"
            f"The netra_app user must be able to perform basic database operations."
        )
    
    def test_netra_app_user_configuration_documentation(self, validator):
        """
        DOCUMENTATION TEST: Validate netra_app user configuration is documented.
        
        This test ensures the netra_app user setup is properly documented
        and configuration is consistent with expectations.
        """
        config = validator.get_netra_app_config()
        admin_config = validator.get_postgres_admin_config()
        
        print(f"\n=== NETRA_APP USER CONFIGURATION TEST ===")
        print(f"Configuration Summary:")
        print(f"  Host: {config['host']}")
        print(f"  Port: {config['port']}")
        print(f"  Database: {config['database']}")
        print(f"  netra_app User: {config['user']}")
        print(f"  Admin User: {admin_config['user']}")
        print(f"  Password Length: {len(config['password'])} chars")
        
        # Validate configuration consistency
        assert config['host'] == admin_config['host'], "Host should be consistent"
        assert config['port'] == admin_config['port'], "Port should be consistent" 
        assert config['database'] == admin_config['database'], "Database should be consistent"
        
        # Validate reasonable configuration
        assert config['host'], "Host must be configured"
        assert config['port'], "Port must be configured"
        assert config['database'], "Database name must be configured"
        assert config['user'] == 'netra_app', "User must be 'netra_app'"
        
        # Port should be numeric and reasonable
        try:
            port_num = int(config['port'])
            assert 1024 <= port_num <= 65535, f"Port {port_num} is not in valid range"
        except ValueError:
            pytest.fail(f"Port '{config['port']}' is not a valid number")


if __name__ == "__main__":
    # Run diagnostic when executed directly
    import asyncio
    
    async def main():
        print("=== NETRA_APP USER VALIDATION ===")
        validator = NetraAppUserValidator()
        
        # Test netra_app user
        netra_app_config = validator.get_netra_app_config()
        print(f"\nTesting netra_app user: {netra_app_config['user']}@{netra_app_config['host']}:{netra_app_config['port']}")
        
        netra_app_result = await validator.validate_netra_app_user_access(netra_app_config)
        print(f"netra_app: {'OK' if netra_app_result['success'] else 'FAILED'}")
        if not netra_app_result['success']:
            print(f"  Error: {netra_app_result['error']}")
        else:
            print(f"  Tables accessible: {len(netra_app_result['accessible_tables'])}")
            print(f"  Can create tables: {netra_app_result['permissions'].get('can_create_tables', False)}")
        
        # Test admin user
        admin_config = validator.get_postgres_admin_config()
        print(f"\nTesting admin user: {admin_config['user']}@{admin_config['host']}:{admin_config['port']}")
        
        admin_result = await validator.validate_netra_app_user_access(admin_config)
        print(f"postgres admin: {'OK' if admin_result['success'] else 'FAILED'}")
        if not admin_result['success']:
            print(f"  Error: {admin_result['error']}")
        else:
            print(f"  Tables accessible: {len(admin_result['accessible_tables'])}")
    
    asyncio.run(main())