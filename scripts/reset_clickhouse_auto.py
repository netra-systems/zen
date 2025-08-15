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

def reset_clickhouse_instance(config: Dict[str, Any]) -> bool:
    """Reset a single ClickHouse instance."""
    print("\n" + "=" * 60)
    print(f"Processing: {config['name']}")
    print("=" * 60)
    
    # Check for password if needed
    if config['secure'] and not config['password']:
        print("\n[WARNING] No password provided for secure connection!")
        print(f"Skipping {config['name']} - Set CLICKHOUSE_PASSWORD env var")
        return False
    
    print(f"\nConnecting to {config['name']}...")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")
    
    try:
        client = get_client(config)
        
        # Test connection
        client.ping()
        print("[OK] Connected successfully!\n")
        
        # List tables
        print("Fetching existing tables...")
        tables = list_tables(client)
        
        if not tables:
            print("[OK] No tables found. Database is already clean.")
            return True
        
        print(f"\nFound {len(tables)} table(s):")
        for row in tables:
            print(f"  - {row[0]}")
        
        # Drop all tables
        print(f"\nDropping all tables in {config['name']}...")
        for row in tables:
            drop_table(client, row[0])
        
        # Verify
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
                
    except ConnectionError as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print(f"Skipping {config['name']}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        print(f"Details: {type(e).__name__}: {str(e)}")
        return False

def main():
    """Main function to reset both ClickHouse instances."""
    print("=" * 60)
    print("ClickHouse Database Auto-Reset (Cloud & Local)")
    print("=" * 60)
    print("\nThis will attempt to drop ALL tables in both instances.")
    
    # Determine which instances to process based on command line args
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == 'cloud':
            configs = [CLOUD_CONFIG]
            print("Processing: Cloud instance only")
        elif arg == 'local':
            configs = [LOCAL_CONFIG]
            print("Processing: Local instance only")
        else:
            configs = [CLOUD_CONFIG, LOCAL_CONFIG]
            print("Processing: Both Cloud and Local instances")
    else:
        configs = [CLOUD_CONFIG, LOCAL_CONFIG]
        print("Processing: Both Cloud and Local instances")
        print("\nUsage: python reset_clickhouse_auto.py [cloud|local|both]")
    
    # Process each instance
    results = []
    for config in configs:
        success = reset_clickhouse_instance(config)
        results.append((config['name'], success))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "[SUCCESS]" if success else "[FAILED/SKIPPED]"
        print(f"{status} {name}")
    
    print(f"\nOperation complete! ({success_count}/{total_count} instances reset)")
    
    # Return exit code based on results
    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    exit(main())