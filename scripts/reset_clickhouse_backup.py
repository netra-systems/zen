"""Direct ClickHouse reset script - drops all tables for both cloud and local instances."""

import clickhouse_connect
import os
from typing import List, Dict, Any, Optional

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

def list_tables(client) -> List[Dict[str, Any]]:
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

def _print_instance_header(config):
    """Print processing header for instance"""
    print("\n" + "=" * 60)
    print(f"Processing: {config['name']}")
    print("=" * 60)

def _validate_secure_password(config):
    """Validate password for secure connections"""
    if config['secure'] and not config['password']:
        print("\n[WARNING] No password provided for secure connection!")
        print(f"Set CLICKHOUSE_PASSWORD environment variable or update script.")
        return False
    return True

def _print_connection_details(config):
    """Print connection details"""
    print(f"\nConnecting to {config['name']}...")
    print(f"  Host: {config['host']}\n  Port: {config['port']}")
    print(f"  Database: {config['database']}\n  User: {config['user']}")

def _create_and_test_client(config):
    """Create client and test connection"""
    client = get_client(config)
    client.ping()
    print("[OK] Connected successfully!\n")
    return client

def _list_existing_tables(client):
    """List and display existing tables"""
    print("Fetching existing tables...")
    tables = list_tables(client)
    if not tables:
        print("[OK] No tables found. Database is already clean.")
        return None
    print(f"\nFound {len(tables)} table(s):")
    for row in tables: print(f"  - {row[0]}")
    return tables

def _get_drop_confirmation(config, skip_confirmation):
    """Get user confirmation for dropping tables"""
    if skip_confirmation:
        return True
    print("\n" + "-" * 40)
    response = input(f"[!] Drop ALL tables in {config['name']}? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled for this instance.")
        return False
    return True

def _drop_all_tables(client, tables, config):
    """Drop all tables in the database"""
    print(f"\nDropping all tables in {config['name']}...")
    for row in tables:
        drop_table(client, row[0])

def _verify_and_display_results(client, config):
    """Verify table deletion and display results"""
    print("\nVerifying...")
    remaining = list_tables(client)
    if not remaining:
        print(f"\n[SUCCESS] All tables dropped in {config['name']}!")
        return True
    print(f"\n[WARNING] {len(remaining)} table(s) still exist:")
    for row in remaining: print(f"  - {row[0]}")
    return False

def reset_clickhouse_instance(config: Dict[str, Any], skip_confirmation: bool = False):
    """Reset a single ClickHouse instance."""
    _print_instance_header(config)
    if not _validate_secure_password(config): return False
    _print_connection_details(config)
    try:
        client = _create_and_test_client(config)
        tables = _list_existing_tables(client)
        if not tables: return True
        if not _get_drop_confirmation(config, skip_confirmation): return False
        _drop_all_tables(client, tables, config)
        return _verify_and_display_results(client, config)
    except ConnectionError as e:
        print(f"\n[ERROR] Connection failed: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return False

def main():
    """Main function to reset ClickHouse instances."""
    print("=" * 60)
    print("ClickHouse Database Reset Tool (Cloud & Local)")
    print("=" * 60)
    
    # Ask which instances to reset
    print("\nWhich ClickHouse instance(s) to reset?")
    print("1. Cloud only")
    print("2. Local only")
    print("3. Both Cloud and Local")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == '4':
        print("Exiting...")
        return
    
    # Determine which configs to use
    configs = []
    if choice == '1':
        configs = [CLOUD_CONFIG]
    elif choice == '2':
        configs = [LOCAL_CONFIG]
    elif choice == '3':
        configs = [CLOUD_CONFIG, LOCAL_CONFIG]
    else:
        print("Invalid choice. Exiting...")
        return
    
    # Ask for batch confirmation
    print("\n" + "=" * 60)
    print("CONFIRMATION")
    print("=" * 60)
    print("This will DROP ALL TABLES in the selected instance(s):")
    for config in configs:
        print(f"  - {config['name']} ({config['host']})")
    
    batch_confirm = input("\nProceed with ALL selected instances? (yes/no): ")
    skip_individual = batch_confirm.lower() == 'yes'
    
    if not skip_individual:
        print("\nWill ask for confirmation for each instance...")
    
    # Process each instance
    results = []
    for config in configs:
        success = reset_clickhouse_instance(config, skip_confirmation=skip_individual)
        results.append((config['name'], success))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, success in results:
        status = "[SUCCESS]" if success else "[FAILED/SKIPPED]"
        print(f"{status} {name}")
    
    print("\nOperation complete!")

if __name__ == "__main__":
    main()