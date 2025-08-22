#!/usr/bin/env python3
"""Database Initialization Validation Script
Purpose: Validate that PostgreSQL initialization creates all required tables
Module: Validation (adheres to 450-line limit)
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

import psycopg2
from psycopg2 import sql


@dataclass
class TableValidation:
    name: str
    required_columns: List[str]
    foreign_keys: List[Tuple[str, str]]  # (column, references_table)

def get_connection():
    """Get PostgreSQL connection from environment."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
        database=os.getenv("DB_NAME", "netra_dev"),
        user=os.getenv("DB_USER", "netra_app"),
        password=os.getenv("DB_PASSWORD", "changeme")
    )

def validate_table_exists(cursor, table_name: str) -> bool:
    """Check if table exists."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        )
    """, (table_name,))
    return cursor.fetchone()[0]

def validate_columns(cursor, table_name: str, columns: List[str]) -> List[str]:
    """Check if columns exist, return missing columns."""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = %s
    """, (table_name,))
    existing = {row[0] for row in cursor.fetchall()}
    return [col for col in columns if col not in existing]

def validate_foreign_keys(cursor, table_name: str, fkeys: List[Tuple[str, str]]) -> List[str]:
    """Check foreign keys, return missing constraints."""
    cursor.execute("""
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = %s
    """, (table_name,))
    existing = {(row[0], row[1]) for row in cursor.fetchall()}
    return [f"{col} -> {ref}" for col, ref in fkeys if (col, ref) not in existing]

def get_required_tables() -> Dict[str, TableValidation]:
    """Define all required tables and their structure."""
    return {
        "userbase": TableValidation(
            "userbase",
            ["id", "email", "full_name", "hashed_password", "role", "plan_tier"],
            []
        ),
        "secrets": TableValidation(
            "secrets",
            ["id", "user_id", "key", "encrypted_value"],
            [("user_id", "userbase")]
        ),
        "tool_usage_logs": TableValidation(
            "tool_usage_logs",
            ["id", "user_id", "tool_name", "status", "created_at"],
            [("user_id", "userbase")]
        ),
        "assistants": TableValidation(
            "assistants",
            ["id", "object", "created_at", "model", "tools"],
            []
        ),
        "threads": TableValidation(
            "threads",
            ["id", "object", "created_at"],
            []
        ),
        "messages": TableValidation(
            "messages",
            ["id", "thread_id", "role", "content", "created_at"],
            [("thread_id", "threads")]
        ),
        "runs": TableValidation(
            "runs",
            ["id", "thread_id", "assistant_id", "status"],
            [("thread_id", "threads"), ("assistant_id", "assistants")]
        ),
        "steps": TableValidation(
            "steps",
            ["id", "run_id", "assistant_id", "thread_id", "type", "status"],
            [("run_id", "runs"), ("assistant_id", "assistants"), ("thread_id", "threads")]
        ),
        "supplies": TableValidation(
            "supplies",
            ["id", "name", "created_at"],
            []
        ),
        "supply_options": TableValidation(
            "supply_options",
            ["id", "provider", "family", "name", "quality_score"],
            []
        ),
        "ai_supply_items": TableValidation(
            "ai_supply_items",
            ["id", "provider", "model_name", "availability_status"],
            []
        ),
        "research_sessions": TableValidation(
            "research_sessions",
            ["id", "query", "status", "created_at"],
            []
        ),
        "supply_update_logs": TableValidation(
            "supply_update_logs",
            ["id", "supply_item_id", "field_updated", "updated_by"],
            [("supply_item_id", "ai_supply_items")]
        ),
        "analyses": TableValidation(
            "analyses",
            ["id", "name", "status", "created_at"],
            [("created_by_id", "userbase")]
        ),
        "corpora": TableValidation(
            "corpora",
            ["id", "name", "status", "created_at"],
            [("created_by_id", "userbase")]
        ),
        "corpus_audit_logs": TableValidation(
            "corpus_audit_logs",
            ["id", "timestamp", "action", "status", "resource_type"],
            [("user_id", "userbase")]
        ),
        "demo_sessions": TableValidation(
            "demo_sessions",
            ["id", "industry", "status", "started_at"],
            [("user_id", "userbase")]
        ),
        "demo_interactions": TableValidation(
            "demo_interactions",
            ["id", "session_id", "interaction_type", "timestamp"],
            [("session_id", "demo_sessions")]
        ),
        "demo_scenarios": TableValidation(
            "demo_scenarios",
            ["id", "industry", "scenario_name", "prompt_template"],
            []
        )
    }

def run_validation():
    """Run full validation of database initialization."""
    print("🔍 Database Initialization Validation\n" + "="*50)
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        tables = get_required_tables()
        total_checks = 0
        passed_checks = 0
        failed_tables = []
        
        for table_name, validation in tables.items():
            print(f"\n📊 Validating table: {table_name}")
            total_checks += 1
            
            # Check table exists
            if not validate_table_exists(cursor, table_name):
                print(f"  ❌ Table does not exist!")
                failed_tables.append(table_name)
                continue
            
            print(f"  ✅ Table exists")
            passed_checks += 1
            
            # Check columns
            missing_cols = validate_columns(cursor, table_name, validation.required_columns)
            if missing_cols:
                print(f"  ⚠️  Missing columns: {', '.join(missing_cols)}")
            else:
                print(f"  ✅ All required columns present")
            
            # Check foreign keys
            if validation.foreign_keys:
                missing_fks = validate_foreign_keys(cursor, table_name, validation.foreign_keys)
                if missing_fks:
                    print(f"  ⚠️  Missing foreign keys: {', '.join(missing_fks)}")
                else:
                    print(f"  ✅ All foreign keys configured")
        
        # Summary
        print(f"\n{'='*50}")
        print("📈 Validation Summary:")
        print(f"  Total tables checked: {total_checks}")
        print(f"  Tables present: {passed_checks}")
        print(f"  Tables missing: {len(failed_tables)}")
        
        if failed_tables:
            print(f"\n❌ Missing tables: {', '.join(failed_tables)}")
            print("\n⚠️  Run the initialization scripts to create missing tables:")
            print("  psql -U netra_app -d netra_dev -f database_scripts/00-init-main.sql")
            return 1
        else:
            print("\n✅ All required tables are present!")
            return 0
            
    except psycopg2.Error as e:
        print(f"\n❌ Database connection error: {e}")
        return 1
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    sys.exit(run_validation())