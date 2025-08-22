"""Direct ClickHouse reset script - drops all tables for both cloud and local instances."""

import os
from typing import Any, Dict, List, Optional, Tuple

import clickhouse_connect

# ClickHouse configurations
CLOUD_CONFIG = {
    'name': 'Cloud ClickHouse',
    'host': os.environ.get('CLICKHOUSE_HOST', 'clickhouse_host_url_placeholder'),
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

def _print_instance_header(config: Dict[str, Any]) -> None:
    """Print header for instance processing."""
    print("\n" + "=" * 60)
    print(f"Processing: {config['name']}")
    print("=" * 60)

def _check_password_required(config: Dict[str, Any]) -> bool:
    """Check if password is required and available."""
    if config['secure'] and not config['password']:
        print("\n[WARNING] No password provided for secure connection!")
        print(f"Set CLICKHOUSE_PASSWORD environment variable or update script.")
        return False
    return True

def _print_connection_info(config: Dict[str, Any]) -> None:
    """Print connection information."""
    print(f"\nConnecting to {config['name']}...")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")

def _connect_and_test(config: Dict[str, Any]):
    """Connect to ClickHouse and test connection."""
    client = get_client(config)
    client.ping()
    print("[OK] Connected successfully!\n")
    return client

def _fetch_and_display_tables(client) -> List:
    """Fetch and display existing tables."""
    print("Fetching existing tables...")
    tables = list_tables(client)
    if not tables:
        print("[OK] No tables found. Database is already clean.")
        return tables
    print(f"\nFound {len(tables)} table(s):")
    for row in tables:
        print(f"  - {row[0]}")
    return tables

def validate_clickhouse_config(config: Dict[str, Any]) -> bool:
    """Validate ClickHouse configuration requirements."""
    if config['secure'] and not config['password']:
        print("\n[WARNING] No password provided for secure connection!")
        print(f"Set CLICKHOUSE_PASSWORD environment variable or update script.")
        return False
    return True

def connect_to_clickhouse(config: Dict[str, Any]):
    """Connect to ClickHouse and test connection."""
    print(f"\nConnecting to {config['name']}...")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")
    
    client = get_client(config)
    client.ping()
    print("[OK] Connected successfully!\n")
    return client

def fetch_and_display_tables(client) -> List:
    """Fetch and display existing tables."""
    print("Fetching existing tables...")
    tables = list_tables(client)
    
    if not tables:
        print("[OK] No tables found. Database is already clean.")
        return tables
    
    print(f"\nFound {len(tables)} table(s):")
    for row in tables:
        print(f"  - {row[0]}")
    return tables

def confirm_table_deletion(config: Dict[str, Any], skip_confirmation: bool) -> bool:
    """Confirm table deletion operation with user."""
    if skip_confirmation:
        return True
    
    print("\n" + "-" * 40)
    response = input(f"[!] Drop ALL tables in {config['name']}? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Operation cancelled for this instance.")
        return False
    return True

def drop_all_tables(client, config: Dict[str, Any], tables: List) -> None:
    """Drop all tables in the database."""
    print(f"\nDropping all tables in {config['name']}...")
    for row in tables:
        drop_table(client, row[0])

def verify_table_cleanup(client, config: Dict[str, Any]) -> bool:
    """Verify all tables were successfully dropped."""
    print("\nVerifying...")
    remaining = list_tables(client)
    
    if not remaining:
        print(f"\n[SUCCESS] All tables dropped in {config['name']}!")
        return True
    else:
        print(f"\n[WARNING] {len(remaining)} table(s) still exist:")
        for row in remaining:
            print(f"  - {row[0]}")
        return False

def reset_clickhouse_instance(config: Dict[str, Any], skip_confirmation: bool = False):
    """Reset a single ClickHouse instance."""
    _print_instance_header(config)
    
    if not validate_clickhouse_config(config):
        return False
    
    try:
        client = connect_to_clickhouse(config)
        tables = fetch_and_display_tables(client)
        
        if not tables:
            return True
        
        if not confirm_table_deletion(config, skip_confirmation):
            return False
        
        drop_all_tables(client, config, tables)
        return verify_table_cleanup(client, config)
    except ConnectionError as e:
        print(f"\n[ERROR] Connection failed: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return False

def print_main_header():
    """Print the main header for the tool."""
    print("=" * 60)
    print("ClickHouse Database Reset Tool (Cloud & Local)")
    print("=" * 60)

def show_menu_and_get_choice() -> str:
    """Show menu options and get user choice."""
    print("\nWhich ClickHouse instance(s) to reset?")
    print("1. Cloud only")
    print("2. Local only")
    print("3. Both Cloud and Local")
    print("4. Exit")
    return input("\nEnter choice (1-4): ").strip()

def determine_configs_from_choice(choice: str) -> List[Dict[str, Any]]:
    """Determine which configurations to use based on choice."""
    if choice == '1':
        return [CLOUD_CONFIG]
    elif choice == '2':
        return [LOCAL_CONFIG]
    elif choice == '3':
        return [CLOUD_CONFIG, LOCAL_CONFIG]
    return []

def print_confirmation_header(configs: List[Dict[str, Any]]) -> None:
    """Print confirmation header with selected instances."""
    print("\n" + "=" * 60)
    print("CONFIRMATION")
    print("=" * 60)
    print("This will DROP ALL TABLES in the selected instance(s):")
    for config in configs:
        print(f"  - {config['name']} ({config['host']})")

def get_batch_confirmation() -> bool:
    """Get batch confirmation from user."""
    batch_confirm = input("\nProceed with ALL selected instances? (yes/no): ")
    skip_individual = batch_confirm.lower() == 'yes'
    if not skip_individual:
        print("\nWill ask for confirmation for each instance...")
    return skip_individual

def process_all_instances(configs: List[Dict[str, Any]], skip_individual: bool) -> List[Tuple[str, bool]]:
    """Process all selected instances and return results."""
    results = []
    for config in configs:
        success = reset_clickhouse_instance(config, skip_confirmation=skip_individual)
        results.append((config['name'], success))
    return results

def print_operation_summary(results: List[Tuple[str, bool]]) -> None:
    """Print the final operation summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, success in results:
        status = "[SUCCESS]" if success else "[FAILED/SKIPPED]"
        print(f"{status} {name}")
    print("\nOperation complete!")

def handle_user_choice() -> List[Dict[str, Any]]:
    """Handle user menu choice and return selected configurations."""
    choice = show_menu_and_get_choice()
    if choice == '4':
        print("Exiting...")
        return []
    configs = determine_configs_from_choice(choice)
    if not configs:
        print("Invalid choice. Exiting...")
    return configs

def execute_reset_operation(configs: List[Dict[str, Any]]) -> None:
    """Execute reset operation with user confirmation."""
    print_confirmation_header(configs)
    skip_individual = get_batch_confirmation()
    results = process_all_instances(configs, skip_individual)
    print_operation_summary(results)

def main():
    """Main function to reset ClickHouse instances."""
    print_main_header()
    configs = handle_user_choice()
    if not configs:
        return
    execute_reset_operation(configs)

if __name__ == "__main__":
    main()