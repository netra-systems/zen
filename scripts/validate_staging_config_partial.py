from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Validate staging environment configuration and connectivity.

This script checks:
1. Required secrets are configured
2. Database connectivity
3. Redis connectivity  
4. ClickHouse connectivity
5. Environment variables
"""

import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

import clickhouse_connect
import psycopg2
import redis
from colorama import Fore, Style, init

init(autoreset=True)

def print_section(title: str):
    """Print a section header."""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}{title:^60}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

def check_env_var(var_name: str, required: bool = True, sensitive: bool = False) -> Tuple[bool, str]:
    """Check if an environment variable is set."""
    value = get_env().get(var_name)
    if value:
        display_value = "***" if sensitive else value[:20] + "..." if len(value) > 20 else value
        return True, display_value
    elif required:
        return False, "NOT SET"
    else:
        return True, "NOT SET (optional)"

def check_github_secrets() -> Dict[str, bool]:
    """Check if required GitHub secrets are available."""
    print_section("GitHub Secrets Check")
    
    secrets = {
        "GCP_STAGING_SA_KEY": False,
        "STAGING_DB_PASSWORD": False,
        "CLICKHOUSE_PASSWORD": False,
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": False,
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": False,
    }
    
    # In GitHub Actions, secrets are passed as env vars
    for secret_name in secrets:
        if get_env().get(secret_name):
            print(f"{Fore.GREEN}✓ {secret_name}: Configured{Style.RESET_ALL}")
            secrets[secret_name] = True
        else:
            if secret_name in ["GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING"]:
                print(f"{Fore.YELLOW}⚠ {secret_name}: Not set (optional){Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ {secret_name}: Not configured{Style.RESET_ALL}")
    
    return secrets

def _get_database_url() -> Optional[str]:
    """Get and validate #removed-legacyenvironment variable."""
    db_url = get_env().get("DATABASE_URL")
    if not db_url:
        print(f"{Fore.RED}✗ #removed-legacynot set{Style.RESET_ALL}")
        return None
    return db_url

def _normalize_db_url(db_url: str) -> str:
    """Normalize database URL by removing protocol prefix."""
    if db_url.startswith("postgresql://"):
        return db_url[13:]  # Remove postgresql://
    return db_url

def _parse_cloud_sql_url(db_url: str) -> Optional[Tuple[str, str, str, str]]:
    """Parse Cloud SQL socket format URL."""
    parts = db_url.split("?host=/cloudsql/")
    creds_and_db = parts[0]
    socket_path = f"/cloudsql/{parts[1]}"
    if "@" in creds_and_db:
        creds, db = creds_and_db.split("@")[0], creds_and_db.split("/")[-1]
        user, password = creds.split(":")
        return user, password, db, socket_path
    print(f"{Fore.RED}✗ Invalid #removed-legacyformat{Style.RESET_ALL}")
    return None

def _connect_cloud_sql(user: str, password: str, db: str, socket_path: str):
    """Connect to Cloud SQL database via socket."""
    print(f"  User: {user}")
    print(f"  Database: {db}")
    print(f"  Socket: {socket_path}")
    return psycopg2.connect(
        host=socket_path,
        database=db,
        user=user,
        password=password
    )

def _test_db_version(conn) -> None:
    """Test database connection and display version."""
    cursor = conn.cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    print(f"{Fore.GREEN}✓ PostgreSQL connected: {version[:50]}...{Style.RESET_ALL}")
    cursor.close()

def _check_db_tables(conn) -> None:
    """Check and display database tables."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        LIMIT 10
    """)
    tables = cursor.fetchall()
    if tables:
        print(f"  Tables found: {len(tables)}")
        for table in tables[:5]:
            print(f"    - {table[0]}")
    else:
        print(f"{Fore.YELLOW}  ⚠ No tables found (run migrations){Style.RESET_ALL}")
    cursor.close()

def check_database_connection() -> bool:
    """Test PostgreSQL database connection."""
    print_section("PostgreSQL Connection Test")
    
    db_url = _get_database_url()
    if not db_url:
        return False
    
    try:
        normalized_url = _normalize_db_url(db_url)
        
        if "?host=/cloudsql/" in normalized_url:
            parsed = _parse_cloud_sql_url(normalized_url)
            if not parsed:
                return False
            user, password, db, socket_path = parsed
            conn = _connect_cloud_sql(user, password, db, socket_path)
        else:
            conn = psycopg2.connect(db_url)
        
        _test_db_version(conn)
        _check_db_tables(conn)
        conn.close()
        return True
        
    except Exception as e:
        print(f"{Fore.RED}✗ PostgreSQL connection failed: {e}{Style.RESET_ALL}")
        return False
