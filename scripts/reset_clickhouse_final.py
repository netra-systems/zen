from shared.isolated_environment import get_env
"""Final ClickHouse reset script using Docker for local and env vars for cloud."""

import os
import subprocess
import sys
from typing import List


def _print_reset_header() -> None:
    """Print the reset operation header."""
    print("\n" + "=" * 60)
    print("Resetting Local ClickHouse (Docker)")
    print("=" * 60)

def _check_docker_container() -> bool:
    """Check if ClickHouse Docker container is running."""
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=netra-clickhouse-dev", "--format", "{{.Names}}"],
        capture_output=True, text=True
    )
    if "netra-clickhouse-dev" not in result.stdout:
        print("[WARNING] Docker container 'netra-clickhouse-dev' not found or not running")
        return False
    print("[OK] Found Docker container: netra-clickhouse-dev")
    return True

def _get_database_tables(db: str) -> List[str]:
    """Get all tables from a specific database."""
    cmd = f'docker exec netra-clickhouse-dev clickhouse-client --database {db} --query "SELECT name FROM system.tables WHERE database = '"'"'{db}'"'"' AND engine NOT LIKE '"'"'%View%'"'"' ORDER BY name"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [ERROR] Failed to list tables: {result.stderr}")
        return []
    tables = result.stdout.strip().split('\n') if result.stdout.strip() else []
    return [t for t in tables if t]  # Remove empty strings

def _display_tables_info(db: str, tables: List[str]) -> None:
    """Display information about tables found in database."""
    if not tables:
        print(f"  [OK] No tables found in {db}")
        return
    print(f"  Found {len(tables)} table(s):")
    for table in tables:
        print(f"    - {table}")

def _drop_table_from_db(db: str, table: str) -> bool:
    """Drop a single table from the database."""
    drop_cmd = f'docker exec netra-clickhouse-dev clickhouse-client --database {db} --query "DROP TABLE IF EXISTS {table}"'
    drop_result = subprocess.run(drop_cmd, shell=True, capture_output=True, text=True)
    if drop_result.returncode == 0:
        print(f"    [OK] Dropped: {table}")
        return True
    print(f"    [ERROR] Failed to drop {table}: {drop_result.stderr}")
    return False

def _verify_tables_dropped(db: str) -> bool:
    """Verify all tables have been dropped from database."""
    verify_cmd = f'docker exec netra-clickhouse-dev clickhouse-client --database {db} --query "SELECT count(*) FROM system.tables WHERE database = '"'"'{db}'"'"' AND engine NOT LIKE '"'"'%View%'"'"'"'
    verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
    if verify_result.returncode != 0:
        return False
    count = verify_result.stdout.strip()
    if count == "0":
        print(f"  [SUCCESS] All tables dropped from {db}")
        return True
    print(f"  [WARNING] {count} tables still exist in {db}")
    return False

def _process_single_database(db: str) -> bool:
    """Process and reset a single database."""
    print(f"\nProcessing database: {db}")
    tables = _get_database_tables(db)
    _display_tables_info(db, tables)
    if not tables:
        return True
    print(f"\n  Dropping tables in {db}...")
    for table in tables:
        _drop_table_from_db(db, table)
    return _verify_tables_dropped(db)

def reset_local_clickhouse() -> bool:
    """Reset local ClickHouse using Docker."""
    _print_reset_header()
    try:
        if not _check_docker_container():
            return False
        print("\nChecking databases...")
        databases = ["default", "netra_dev"]
        for db in databases:
            _process_single_database(db)
        return True
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

def reset_cloud_clickhouse():
    """Reset cloud ClickHouse - requires password."""
    print("\n" + "=" * 60)
    print("Resetting Cloud ClickHouse")
    print("=" * 60)
    
    password = os.environ.get('CLICKHOUSE_PASSWORD', '')
    if not password:
        print("[WARNING] CLICKHOUSE_PASSWORD not set")
        print("To reset cloud instance, set environment variable:")
        print("  set CLICKHOUSE_PASSWORD=your_password")
        return False
    
    print("[INFO] Cloud reset requires clickhouse-connect with proper credentials")
    print("Password is set, but automatic cloud reset not implemented in this version")
    print("Use the web console or set up credentials properly")
    return False

def display_final_header() -> None:
    """Display the final reset tool header."""
    print("=" * 60)
    print("ClickHouse Complete Reset Tool")
    print("=" * 60)

def determine_reset_target() -> str:
    """Determine reset target from command line arguments."""
    return sys.argv[1] if len(sys.argv) > 1 else "both"

def execute_final_reset(target: str) -> List[tuple]:
    """Execute reset operations based on target and return results."""
    results = []
    if target in ["local", "both"]:
        success = reset_local_clickhouse()
        results.append(("Local ClickHouse", success))
    if target in ["cloud", "both"]:
        success = reset_cloud_clickhouse()
        results.append(("Cloud ClickHouse", success))
    return results

def display_final_summary(results: List[tuple]) -> int:
    """Display final summary and return exit code."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, success in results:
        status = "[SUCCESS]" if success else "[FAILED/SKIPPED]"
        print(f"{status} {name}")
    print("\nOperation complete!")
    return 0 if all(s for _, s in results) else 1

def main():
    """Main function."""
    display_final_header()
    target = determine_reset_target()
    results = execute_final_reset(target)
    return display_final_summary(results)

if __name__ == "__main__":
    exit(main())
