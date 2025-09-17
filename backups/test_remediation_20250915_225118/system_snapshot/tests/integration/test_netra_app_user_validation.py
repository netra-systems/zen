'''
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
'''

import asyncio
import pytest
import time
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncpg
import psycopg2
from shared.isolated_environment import IsolatedEnvironment

    # Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
from test_framework.environment_markers import env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


class NetraAppUserValidator:
    """Validator for netra_app database user configuration and permissions."""

    def __init__(self):
        pass
        self.env = get_env()

    def get_netra_app_config(self) -> Dict[str, str]:
        """Get database configuration for netra_app user."""
        return { )
        'host': self.env.get('POSTGRES_HOST', 'localhost'),
        'port': self.env.get('POSTGRES_PORT', '5433'),
        'user': 'netra_app',  # Specific user for application
        'password': self.env.get('POSTGRES_PASSWORD', ''),  # Uses same password as postgres for dev
        'database': self.env.get('POSTGRES_DB', 'netra_dev')
    

    def get_postgres_admin_config(self) -> Dict[str, str]:
        """Get database configuration for postgres admin user."""
        return { )
        'host': self.env.get('POSTGRES_HOST', 'localhost'),
        'port': self.env.get('POSTGRES_PORT', '5433'),
        'user': self.env.get('POSTGRES_USER', 'postgres'),
        'password': self.env.get('POSTGRES_PASSWORD', ''),
        'database': self.env.get('POSTGRES_DB', 'netra_dev')
    

    async def validate_netra_app_user_access(self, config: Dict[str, str]) -> Dict[str, Any]:
        """Validate netra_app user can connect and access database."""
        result = { )
        'user': config['user'],
        'success': False,
        'connection_time': None,
        'error': None,
        'permissions': {},
        'accessible_tables': [],
        'config_used': config
    

        url = "formatted_string"

        start_time = time.time()
        try:
        conn = await asyncpg.connect(url, timeout=5)
        connection_time = time.time() - start_time

        # Test basic permissions
        permissions = await self._check_user_permissions(conn, config['user'])
        accessible_tables = await self._get_accessible_tables(conn)

        await conn.close()

        result.update({ ))
        'success': True,
        'connection_time': connection_time,
        'permissions': permissions,
        'accessible_tables': accessible_tables
        

        except Exception as e:
        result.update({ ))
        'error': str(e),
        'connection_time': time.time() - start_time
            

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
                Check if user can select from information_schema
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
        tables = await conn.fetch( )
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
        
        return [row['table_name'] for row in tables]
        except Exception:
        return []

    async def validate_user_vs_admin_access(self) -> Dict[str, Any]:
        """Compare netra_app user access vs postgres admin access."""
        netra_app_config = self.get_netra_app_config()
        admin_config = self.get_postgres_admin_config()

        netra_app_result = await self.validate_netra_app_user_access(netra_app_config)
        admin_result = await self.validate_netra_app_user_access(admin_config)

        comparison = { )
        'netra_app': netra_app_result,
        'postgres_admin': admin_result,
        'both_successful': netra_app_result['success'] and admin_result['success'],
        'access_differences': {},
        'table_access_comparison': {}
    

        if comparison['both_successful']:
        # Compare permissions
        netra_permissions = netra_app_result.get('permissions', {})
        admin_permissions = admin_result.get('permissions', {})

        for perm in set(netra_permissions.keys()) | set(admin_permissions.keys()):
        netra_has = netra_permissions.get(perm, False)
        admin_has = admin_permissions.get(perm, False)
        if netra_has != admin_has:
        comparison['access_differences'][perm] = { )
        'netra_app': netra_has,
        'postgres_admin': admin_has
                

                # Compare table access
        netra_tables = set(netra_app_result.get('accessible_tables', []))
        admin_tables = set(admin_result.get('accessible_tables', []))

        comparison['table_access_comparison'] = { )
        'netra_app_only': list(netra_tables - admin_tables),
        'admin_only': list(admin_tables - netra_tables),
        'shared': list(netra_tables & admin_tables),
        'total_netra_app': len(netra_tables),
        'total_admin': len(admin_tables)
                

        return comparison


class TestNetraAppUserValidation:
        """Test suite for netra_app user database access validation."""

        @pytest.fixture
    def validator(self):
        pass
        return NetraAppUserValidator()

@pytest.mark.asyncio
    async def test_netra_app_user_connectivity(self, validator):
'''
CRITICAL TEST: Validate netra_app user can connect to database.

This test ensures the netra_app user exists and can successfully
connect to the database with the configured credentials.
'''
pass
config = validator.get_netra_app_config()
result = await validator.validate_netra_app_user_access(config)

print(f" )
=== NETRA_APP USER CONNECTIVITY TEST ===")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string" if result['connection_time'] else "N/A")

if result['success']:
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

if result['accessible_tables']:
print("formatted_string")
if len(result['accessible_tables']) > 5:
print("formatted_string")
else:
print("formatted_string")

                        # For development environment, allow fallback to postgres user
                        # In production, netra_app user should exist
if not result['success']:
env_name = validator.env.get('ENVIRONMENT', 'unknown')
if env_name == 'development':
print(" )
WARNING: [U+FE0F]  netra_app user not found in development - this is acceptable")
print("   Development can use postgres user as fallback")
pytest.skip("netra_app user not configured in development environment")
else:
assert result['success'], ( )
"formatted_string"
"formatted_string"port"]}
"
"formatted_string"
"formatted_string"
"formatted_string"
f"The netra_app user must exist and be accessible in non-development environments.
"
f"Run the database initialization scripts to create the user."
                                        
else:
                                            # Validate the user is actually netra_app
assert result['permissions'].get('user_matches', False), ( )
"formatted_string"
                                            

@pytest.mark.asyncio
    async def test_netra_app_vs_postgres_admin_comparison(self, validator):
'''
INTEGRATION TEST: Compare netra_app user access vs postgres admin.

This test compares the access levels between netra_app and postgres
admin users to ensure proper permission separation.
'''
pass
comparison = await validator.validate_user_vs_admin_access()

print(f" )
=== USER ACCESS COMPARISON TEST ===")
print("formatted_string")
print("formatted_string")
print("formatted_string")

if comparison['both_successful']:
print(f" )
Table Access Comparison:")
table_comp = comparison['table_access_comparison']
print("formatted_string")
print("formatted_string")
print("formatted_string")

if table_comp['netra_app_only']:
print("formatted_string")
if table_comp['admin_only']:
print("formatted_string")

print(f" )
Permission Differences:")
if comparison['access_differences']:
for perm, values in comparison['access_differences'].items():
print("formatted_string")
else:
print("  No permission differences found")

                                                                        # At least one user should be able to connect
assert (comparison['netra_app']['success'] or comparison['postgres_admin']['success']), ( )
f"Neither netra_app nor postgres admin user could connect:
"
"formatted_string"
"formatted_string"
f"At least one database user must be accessible for the system to function."
                                                                            

                                                                            # If both are successful, validate they can both access core tables
if comparison['both_successful']:
shared_tables = comparison['table_access_comparison']['shared']
assert len(shared_tables) > 0, ( )
"Both users should have access to at least some shared tables"
                                                                                

@pytest.mark.asyncio
    async def test_netra_app_database_operations(self, validator):
'''
FUNCTIONAL TEST: Validate netra_app user can perform basic database operations.

This test ensures netra_app user has sufficient permissions for
application operations like creating tables, inserting data, etc.
'''
pass
config = validator.get_netra_app_config()

                                                                                    # First check if netra_app user is available
result = await validator.validate_netra_app_user_access(config)
if not result['success']:
pytest.skip("netra_app user not available for testing")

url = "formatted_string"

operations_results = { )
'create_table': False,
'insert_data': False,
'select_data': False,
'update_data': False,
'delete_data': False,
'drop_table': False,
'errors': []
                                                                                        

try:
conn = await asyncpg.connect(url, timeout=5)

table_name = "formatted_string"

try:
                                                                                                # Create table
                                                                                                # Removed problematic line: await conn.execute(f''' )
CREATE TABLE {table_name} ( )
id SERIAL PRIMARY KEY,
name VARCHAR(50),
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                                                                                
''')
operations_results['create_table'] = True

                                                                                                # Insert data
await conn.execute("formatted_string")
operations_results['insert_data'] = True

                                                                                                # Select data
rows = await conn.fetch("formatted_string")
assert len(rows) == 1
operations_results['select_data'] = True

                                                                                                # Update data
await conn.execute("formatted_string")
operations_results['update_data'] = True

                                                                                                # Delete data
await conn.execute("formatted_string")
operations_results['delete_data'] = True

                                                                                                # Drop table
await conn.execute("formatted_string")
operations_results['drop_table'] = True

except Exception as e:
operations_results['errors'].append("formatted_string")
                                                                                                    # Try to clean up table if it exists
try:
await conn.execute("formatted_string")
except:
pass

await conn.close()

except Exception as e:
operations_results['errors'].append("formatted_string")

print(f" )
=== NETRA_APP DATABASE OPERATIONS TEST ===")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

if operations_results['errors']:
print("formatted_string")

                                                                                                                    # Validate critical operations work
critical_operations = ['create_table', 'insert_data', 'select_data']
failed_critical = [item for item in []]]

assert len(failed_critical) == 0, ( )
"formatted_string"
"formatted_string"
f"The netra_app user must be able to perform basic database operations."
                                                                                                                    

def test_netra_app_user_configuration_documentation(self, validator):
'''
DOCUMENTATION TEST: Validate netra_app user configuration is documented.

This test ensures the netra_app user setup is properly documented
and configuration is consistent with expectations.
'''
pass
config = validator.get_netra_app_config()
admin_config = validator.get_postgres_admin_config()

print(f" )
=== NETRA_APP USER CONFIGURATION TEST ===")
print(f"Configuration Summary:")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")
print("formatted_string")

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
assert 1024 <= port_num <= 65535, "formatted_string"
except ValueError:
pytest.fail("formatted_string")


if __name__ == "__main__":
                # Run diagnostic when executed directly
import asyncio

async def main():
pass
print("=== NETRA_APP USER VALIDATION ===")
validator = NetraAppUserValidator()

    # Test netra_app user
netra_app_config = validator.get_netra_app_config()
print("formatted_string"host"]}:{netra_app_config["port"]}")

netra_app_result = await validator.validate_netra_app_user_access(netra_app_config)
print("formatted_string")
if not netra_app_result['success']:
print("formatted_string")
else:
print("formatted_string")
print("formatted_string")

            # Test admin user
admin_config = validator.get_postgres_admin_config()
print("formatted_string"host"]}:{admin_config["port"]}")

admin_result = await validator.validate_netra_app_user_access(admin_config)
print("formatted_string")
if not admin_result['success']:
print("formatted_string")
else:
print("formatted_string")

asyncio.run(main())
