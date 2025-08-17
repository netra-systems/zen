"""Auto-reset ClickHouse script - drops all tables without prompts."""

import clickhouse_connect
import os
import sys
from typing import List, Dict, Any

# ClickHouse configurations
CLOUD_CONFIG = {
    'name': 'Cloud ClickHouse',
    'host': os.environ.get('CLICKHOUSE_HOST', 'xedvrr4c3r.us-central1.gcp.clickhouse.cloud'),
    'port': int(os.environ.get('CLICKHOUSE_PORT', '8443')),
    'user': os.environ.get('CLICKHOUSE_USER', 'development_user'),
    'password': os.environ.get('CLICKHOUSE_PASSWORD', ''),
    'database': os.environ.get('CLICKHOUSE_DATABASE', 'netra_dev'),
    'secure': True
}

LOCAL_CONFIG = {
    'name': 'Local ClickHouse',
    'host': 'localhost',
    'port': 8123,
    'user': 'default',
    'password': '',
    'database': 'default',
    'secure': False
}

def get_client(config: Dict[str, Any]):
    """Create ClickHouse client."""
    try:
        return clickhouse_connect.get_client(
            host=config['host'],
            port=config['port'],
            username=config['user'],
            password=config['password'],
            database=config['database'],
            secure=config['secure']
        )
    except Exception as e:
        raise ConnectionError(f"Failed to connect: {e}")

def list_tables(client) -> List[tuple]:
    """List all tables in the database."""
    query = """
    SELECT name 
    FROM system.tables 
    WHERE database = currentDatabase() 
    AND engine NOT LIKE '%View%'
    AND name NOT LIKE '.inner%'
    ORDER BY name
    """
    return client.query(query).result_rows

def drop_table(client, table_name: str):
    """Drop a single table."""
    query = f"DROP TABLE IF EXISTS {table_name}"
    client.command(query)
    print(f"  [OK] Dropped table: {table_name}")

def _display_instance_header(config):
    """Display instance processing header"""
    print("\n" + "=" * 60)
    print(f"Processing: {config['name']}")
    print("=" * 60)

def _check_password_requirements(config):
    """Check password requirements for secure connections"""
    if config['secure'] and not config['password']:
        print("\n[WARNING] No password provided for secure connection!")
        print(f"Skipping {config['name']} - Set CLICKHOUSE_PASSWORD env var")
        return False
    return True

def _display_connection_info(config):
    """Display connection information"""
    print(f"\nConnecting to {config['name']}...")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")

def _establish_connection(config):
    """Establish and test ClickHouse connection"""
    client = get_client(config)
    client.ping()
    print("[OK] Connected successfully!\n")
    return client

def _process_existing_tables(client, config):
    """Process and display existing tables"""
    print("Fetching existing tables...")
    tables = list_tables(client)
    if not tables:
        print("[OK] No tables found. Database is already clean.")
        return tables, True
    print(f"\nFound {len(tables)} table(s):")
    for row in tables:
        print(f"  - {row[0]}")
    return tables, False

def _drop_all_tables(client, tables, config):
    """Drop all tables and verify deletion"""
    print(f"\nDropping all tables in {config['name']}...")
    for row in tables:
        drop_table(client, row[0])
    print("\nVerifying...")
    remaining = list_tables(client)
    return remaining

def _handle_verification_results(remaining, config):
    """Handle table deletion verification results"""
    if not remaining:
        print(f"\n[SUCCESS] All tables dropped in {config['name']}!")
        return True
    print(f"\n[WARNING] {len(remaining)} table(s) still exist:")
    for row in remaining:
        print(f"  - {row[0]}")
    return False

def reset_clickhouse_instance(config: Dict[str, Any]) -> bool:
    """Reset a single ClickHouse instance."""
    _display_instance_header(config)
    if not _check_password_requirements(config): return False
    _display_connection_info(config)
    try:
        client = _establish_connection(config)
        tables, is_clean = _process_existing_tables(client, config)
        if is_clean: return True
        remaining = _drop_all_tables(client, tables, config)
        return _handle_verification_results(remaining, config)
    except ConnectionError as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print(f"Skipping {config['name']}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        print(f"Details: {type(e).__name__}: {str(e)}")
        return False

def display_auto_reset_header() -> None:
    """Display the auto-reset header and information."""
    print("=" * 60)
    print("ClickHouse Database Auto-Reset (Cloud & Local)")
    print("=" * 60)
    print("\nThis will attempt to drop ALL tables in both instances.")

def determine_target_configs() -> List[Dict[str, Any]]:
    """Determine target configurations based on command line arguments."""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == 'cloud':
            print("Processing: Cloud instance only")
            return [CLOUD_CONFIG]
        elif arg == 'local':
            print("Processing: Local instance only")
            return [LOCAL_CONFIG]
    print("Processing: Both Cloud and Local instances")
    if len(sys.argv) <= 1:
        print("\nUsage: python reset_clickhouse_auto.py [cloud|local|both]")
    return [CLOUD_CONFIG, LOCAL_CONFIG]

def execute_auto_reset(configs: List[Dict[str, Any]]) -> List[tuple]:
    """Execute auto-reset for all configurations and return results."""
    results = []
    for config in configs:
        success = reset_clickhouse_instance(config)
        results.append((config['name'], success))
    return results

def display_auto_summary(results: List[tuple]) -> int:
    """Display summary and return appropriate exit code."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    for name, success in results:
        status = "[SUCCESS]" if success else "[FAILED/SKIPPED]"
        print(f"{status} {name}")
    print(f"\nOperation complete! ({success_count}/{total_count} instances reset)")
    return 0 if success_count == total_count else 1

def main():
    """Main function to reset both ClickHouse instances."""
    display_auto_reset_header()
    configs = determine_target_configs()
    results = execute_auto_reset(configs)
    return display_auto_summary(results)

if __name__ == "__main__":
    exit(main())