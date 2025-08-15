"""Final ClickHouse reset script using Docker for local and env vars for cloud."""

import os
import subprocess
import sys

def reset_local_clickhouse():
    """Reset local ClickHouse using Docker."""
    print("\n" + "=" * 60)
    print("Resetting Local ClickHouse (Docker)")
    print("=" * 60)
    
    try:
        # Check if container is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=netra-clickhouse-dev", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        
        if "netra-clickhouse-dev" not in result.stdout:
            print("[WARNING] Docker container 'netra-clickhouse-dev' not found or not running")
            return False
        
        print("[OK] Found Docker container: netra-clickhouse-dev")
        
        # List databases
        print("\nChecking databases...")
        databases = ["default", "netra_dev"]
        
        for db in databases:
            print(f"\nProcessing database: {db}")
            
            # Get all tables
            cmd = f'docker exec netra-clickhouse-dev clickhouse-client --database {db} --query "SELECT name FROM system.tables WHERE database = \'{db}\' AND engine NOT LIKE \'%View%\' ORDER BY name"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"  [ERROR] Failed to list tables: {result.stderr}")
                continue
            
            tables = result.stdout.strip().split('\n') if result.stdout.strip() else []
            tables = [t for t in tables if t]  # Remove empty strings
            
            if not tables:
                print(f"  [OK] No tables found in {db}")
                continue
            
            print(f"  Found {len(tables)} table(s):")
            for table in tables:
                print(f"    - {table}")
            
            # Drop each table
            print(f"\n  Dropping tables in {db}...")
            for table in tables:
                drop_cmd = f'docker exec netra-clickhouse-dev clickhouse-client --database {db} --query "DROP TABLE IF EXISTS {table}"'
                drop_result = subprocess.run(drop_cmd, shell=True, capture_output=True, text=True)
                
                if drop_result.returncode == 0:
                    print(f"    [OK] Dropped: {table}")
                else:
                    print(f"    [ERROR] Failed to drop {table}: {drop_result.stderr}")
            
            # Verify
            verify_cmd = f'docker exec netra-clickhouse-dev clickhouse-client --database {db} --query "SELECT count(*) FROM system.tables WHERE database = \'{db}\' AND engine NOT LIKE \'%View%\'"'
            verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
            
            if verify_result.returncode == 0:
                count = verify_result.stdout.strip()
                if count == "0":
                    print(f"  [SUCCESS] All tables dropped from {db}")
                else:
                    print(f"  [WARNING] {count} tables still exist in {db}")
        
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

def main():
    """Main function."""
    print("=" * 60)
    print("ClickHouse Complete Reset Tool")
    print("=" * 60)
    
    # Determine what to reset
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    
    results = []
    
    if target in ["local", "both"]:
        success = reset_local_clickhouse()
        results.append(("Local ClickHouse", success))
    
    if target in ["cloud", "both"]:
        success = reset_cloud_clickhouse()
        results.append(("Cloud ClickHouse", success))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, success in results:
        status = "[SUCCESS]" if success else "[FAILED/SKIPPED]"
        print(f"{status} {name}")
    
    print("\nOperation complete!")
    return 0 if all(s for _, s in results) else 1

if __name__ == "__main__":
    exit(main())