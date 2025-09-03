#!/usr/bin/env python
"""
Manual ClickHouse table creation for production/staging.
Run this directly to create required tables in ClickHouse Cloud.

Usage:
    python scripts/create_clickhouse_tables.py --env staging
    python scripts/create_clickhouse_tables.py --env production
"""

import argparse
import sys
import os
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import clickhouse_connect
from clickhouse_connect.driver.client import Client


def get_table_schemas() -> List[Tuple[str, str]]:
    """Get all required table schemas."""
    schemas = []
    
    # Agent state history table
    schemas.append(("agent_state_history", """
        CREATE TABLE IF NOT EXISTS agent_state_history (
            run_id String,
            thread_id String,
            user_id String,
            agent_type String,
            timestamp DateTime64(3),
            event_type String,
            state_data String,
            metadata String,
            error_message Nullable(String),
            retry_count UInt32 DEFAULT 0
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (timestamp, run_id, thread_id)
        TTL timestamp + INTERVAL 90 DAY
    """))
    
    # Events table
    schemas.append(("events", """
        CREATE TABLE IF NOT EXISTS events (
            event_id UUID DEFAULT generateUUIDv4(),
            event_type String,
            timestamp DateTime DEFAULT now(),
            user_id Nullable(String),
            data String,
            metadata String
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (timestamp, event_id)
        TTL timestamp + INTERVAL 30 DAY
    """))
    
    # Metrics table
    schemas.append(("metrics", """
        CREATE TABLE IF NOT EXISTS metrics (
            metric_name String,
            timestamp DateTime DEFAULT now(),
            value Float64,
            tags Map(String, String),
            user_id Nullable(String)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (timestamp, metric_name)
        TTL timestamp + INTERVAL 7 DAY
    """))
    
    # Logs table
    schemas.append(("netra_logs", """
        CREATE TABLE IF NOT EXISTS netra_logs (
            request_id UUID,
            timestamp DateTime64(3, 'UTC'),
            level String,
            message String,
            module String,
            function String,
            line_number UInt32,
            exception Nullable(String),
            extra_data Nullable(String),
            user_id Nullable(String),
            thread_id Nullable(String),
            run_id Nullable(String)
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (timestamp, request_id)
        TTL timestamp + INTERVAL 30 DAY
    """))
    
    # Supply catalog table
    schemas.append(("netra_global_supply_catalog", """
        CREATE TABLE IF NOT EXISTS netra_global_supply_catalog (
            id UUID DEFAULT generateUUIDv4(),
            provider String,
            family String,
            variant String,
            model_id String,
            context_window UInt32,
            max_output_tokens UInt32,
            input_token_cost Float64,
            output_token_cost Float64,
            request_cost Float64,
            supports_function_calling UInt8,
            supports_streaming UInt8,
            supports_batching UInt8,
            modality String,
            last_updated DateTime DEFAULT now(),
            is_active UInt8 DEFAULT 1
        ) ENGINE = ReplacingMergeTree(last_updated)
        ORDER BY (provider, family, variant, model_id)
    """))
    
    # Workload events table
    schemas.append(("workload_events", """
        CREATE TABLE IF NOT EXISTS workload_events (
            event_id UUID DEFAULT generateUUIDv4(),
            timestamp DateTime64(3) DEFAULT now(),
            user_id UInt32,
            organization_id UInt32,
            event_type String,
            resource_type String,
            resource_id String,
            provider String,
            model String,
            tokens_input UInt64,
            tokens_output UInt64,
            latency_ms Float64,
            cost Float64,
            status String,
            error_message Nullable(String),
            metadata String
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (timestamp, user_id, event_id)
        TTL timestamp + INTERVAL 90 DAY
    """))
    
    # Schema version table
    schemas.append(("schema_version", """
        CREATE TABLE IF NOT EXISTS schema_version (
            version String,
            applied_at DateTime DEFAULT now(),
            description String
        ) ENGINE = MergeTree()
        ORDER BY applied_at
    """))
    
    # LLM events table
    schemas.append(("llm_events", """
        CREATE TABLE IF NOT EXISTS llm_events (
            event_id UUID DEFAULT generateUUIDv4(),
            timestamp DateTime64(3) DEFAULT now(),
            user_id String,
            session_id String,
            request_type String,
            provider String,
            model String,
            prompt_tokens UInt32,
            completion_tokens UInt32,
            total_tokens UInt32,
            latency_ms Float64,
            cost Float64,
            status String,
            error_message Nullable(String),
            metadata String
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (timestamp, user_id, event_id)
        TTL timestamp + INTERVAL 90 DAY
    """))
    
    return schemas


def get_connection_config(env: str) -> dict:
    """Get connection configuration for the specified environment."""
    if env == "staging":
        return {
            "host": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "port": 8443,
            "username": "default",
            "password": "6a_z1t0qQ1.ET",  # From Secret Manager
            "database": "default",
            "secure": True
        }
    elif env == "production":
        # Production credentials should be retrieved from Secret Manager
        # For now, raise an error to prevent accidental production changes
        raise ValueError("Production credentials must be manually configured for safety")
    else:
        raise ValueError(f"Unknown environment: {env}")


def create_tables(client: Client, schemas: List[Tuple[str, str]], verbose: bool = True):
    """Create all required tables."""
    success_count = 0
    failure_count = 0
    
    for table_name, schema in schemas:
        try:
            if verbose:
                print(f"Creating table: {table_name}...")
            
            # Execute the CREATE TABLE statement
            client.execute(schema)
            
            # Verify the table was created
            result = client.execute(f"EXISTS TABLE {table_name}")
            if result[0][0] == 1:
                print(f"✅ Successfully created/verified table: {table_name}")
                success_count += 1
            else:
                print(f"⚠️ Table creation uncertain: {table_name}")
                failure_count += 1
                
        except Exception as e:
            print(f"❌ Failed to create table {table_name}: {e}")
            failure_count += 1
    
    return success_count, failure_count


def verify_tables(client: Client, schemas: List[Tuple[str, str]]):
    """Verify all tables exist and show their structure."""
    print("\n" + "=" * 80)
    print("VERIFYING TABLES")
    print("=" * 80)
    
    for table_name, _ in schemas:
        try:
            # Check if table exists
            result = client.execute(f"EXISTS TABLE {table_name}")
            exists = result[0][0] == 1
            
            if exists:
                # Get row count
                count_result = client.execute(f"SELECT count() FROM {table_name}")
                row_count = count_result[0][0]
                print(f"✅ Table {table_name}: EXISTS ({row_count} rows)")
            else:
                print(f"❌ Table {table_name}: DOES NOT EXIST")
                
        except Exception as e:
            print(f"❌ Error checking table {table_name}: {e}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Create ClickHouse tables for Netra")
    parser.add_argument(
        "--env", 
        choices=["staging", "production"],
        required=True,
        help="Environment to create tables in"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify tables exist, don't create them"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    print(f"\n{'=' * 80}")
    print(f"CLICKHOUSE TABLE CREATION SCRIPT")
    print(f"Environment: {args.env.upper()}")
    print(f"{'=' * 80}\n")
    
    try:
        # Get connection configuration
        config = get_connection_config(args.env)
        
        # Connect to ClickHouse
        print(f"Connecting to ClickHouse at {config['host']}:{config['port']}...")
        client = clickhouse_connect.get_client(**config)
        print("✅ Connected successfully\n")
        
        # Get table schemas
        schemas = get_table_schemas()
        
        if args.verify_only:
            # Only verify tables
            verify_tables(client, schemas)
        else:
            # Create tables
            print(f"Creating {len(schemas)} tables...\n")
            success, failure = create_tables(client, schemas, args.verbose)
            
            print(f"\n{'=' * 80}")
            print(f"SUMMARY")
            print(f"{'=' * 80}")
            print(f"✅ Successfully created/verified: {success} tables")
            if failure > 0:
                print(f"❌ Failed: {failure} tables")
            
            # Verify all tables
            verify_tables(client, schemas)
            
            if failure == 0:
                print(f"\n🎉 All tables created successfully!")
            else:
                print(f"\n⚠️ Some tables failed to create. Check the errors above.")
                sys.exit(1)
                
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Check network connectivity to ClickHouse Cloud")
        print("2. Verify credentials in Secret Manager")
        print("3. Ensure your IP is whitelisted in ClickHouse Cloud")
        sys.exit(1)


if __name__ == "__main__":
    main()