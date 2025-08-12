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

import os
import sys
import json
import subprocess
from typing import Dict, List, Tuple
import psycopg2
import redis
import clickhouse_connect
from colorama import init, Fore, Style

init(autoreset=True)

def print_section(title: str):
    """Print a section header."""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}{title:^60}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

def check_env_var(var_name: str, required: bool = True, sensitive: bool = False) -> Tuple[bool, str]:
    """Check if an environment variable is set."""
    value = os.getenv(var_name)
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
        if os.getenv(secret_name):
            print(f"{Fore.GREEN}✓ {secret_name}: Configured{Style.RESET_ALL}")
            secrets[secret_name] = True
        else:
            if secret_name in ["GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING"]:
                print(f"{Fore.YELLOW}⚠ {secret_name}: Not set (optional){Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ {secret_name}: Not configured{Style.RESET_ALL}")
    
    return secrets

def check_database_connection() -> bool:
    """Test PostgreSQL database connection."""
    print_section("PostgreSQL Connection Test")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print(f"{Fore.RED}✗ DATABASE_URL not set{Style.RESET_ALL}")
        return False
    
    try:
        # Parse DATABASE_URL
        if db_url.startswith("postgresql://"):
            db_url = db_url[13:]  # Remove postgresql://
        
        # Handle Cloud SQL socket format
        if "?host=/cloudsql/" in db_url:
            parts = db_url.split("?host=/cloudsql/")
            creds_and_db = parts[0]
            socket_path = f"/cloudsql/{parts[1]}"
            
            # Parse credentials and database
            if "@" in creds_and_db:
                creds, db = creds_and_db.split("@")[0], creds_and_db.split("/")[-1]
                user, password = creds.split(":")
            else:
                print(f"{Fore.RED}✗ Invalid DATABASE_URL format{Style.RESET_ALL}")
                return False
            
            print(f"  User: {user}")
            print(f"  Database: {db}")
            print(f"  Socket: {socket_path}")
            
            # Test connection via Cloud SQL proxy
            conn = psycopg2.connect(
                host=socket_path,
                database=db,
                user=user,
                password=password
            )
        else:
            # Standard connection format
            conn = psycopg2.connect(db_url)
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"{Fore.GREEN}✓ PostgreSQL connected: {version[:50]}...{Style.RESET_ALL}")
        
        # Check tables
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
        conn.close()
        return True
        
    except Exception as e:
        print(f"{Fore.RED}✗ PostgreSQL connection failed: {e}{Style.RESET_ALL}")
        return False

def check_redis_connection() -> bool:
    """Test Redis connection."""
    print_section("Redis Connection Test")
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        # Try to construct from individual components
        redis_host = os.getenv("REDIS_HOST")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        
        if redis_host:
            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
            print(f"  Constructed Redis URL from components")
        else:
            print(f"{Fore.RED}✗ Redis configuration not found{Style.RESET_ALL}")
            return False
    
    try:
        # Parse Redis URL
        if redis_url.startswith("redis://"):
            redis_url = redis_url[8:]  # Remove redis://
        
        parts = redis_url.split("/")
        host_port = parts[0].split(":")
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 6379
        db = int(parts[1]) if len(parts) > 1 else 0
        
        print(f"  Host: {host}")
        print(f"  Port: {port}")
        print(f"  Database: {db}")
        
        # Test connection
        r = redis.Redis(host=host, port=port, db=db, socket_timeout=5)
        r.ping()
        
        # Get info
        info = r.info()
        print(f"{Fore.GREEN}✓ Redis connected: v{info.get('redis_version', 'unknown')}{Style.RESET_ALL}")
        print(f"  Memory used: {info.get('used_memory_human', 'unknown')}")
        print(f"  Connected clients: {info.get('connected_clients', 'unknown')}")
        
        # Test write/read
        test_key = f"staging_test_pr_{os.getenv('PR_NUMBER', 'unknown')}"
        r.set(test_key, "test_value", ex=60)
        value = r.get(test_key)
        if value == b"test_value":
            print(f"  ✓ Read/write test passed")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}✗ Redis connection failed: {e}{Style.RESET_ALL}")
        return False

def check_clickhouse_connection() -> bool:
    """Test ClickHouse connection."""
    print_section("ClickHouse Connection Test")
    
    ch_host = os.getenv("CLICKHOUSE_HOST", "xedvrr4c3r.us-central1.gcp.clickhouse.cloud")
    ch_port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    ch_user = os.getenv("CLICKHOUSE_USER", "default")
    ch_password = os.getenv("CLICKHOUSE_PASSWORD", "")
    ch_secure = os.getenv("CLICKHOUSE_SECURE", "true").lower() == "true"
    
    print(f"  Host: {ch_host}")
    print(f"  Port: {ch_port}")
    print(f"  User: {ch_user}")
    print(f"  Secure: {ch_secure}")
    
    if not ch_password:
        print(f"{Fore.RED}✗ CLICKHOUSE_PASSWORD not set{Style.RESET_ALL}")
        return False
    
    try:
        # Connect to ClickHouse
        client = clickhouse_connect.get_client(
            host=ch_host,
            port=ch_port,
            username=ch_user,
            password=ch_password,
            secure=ch_secure,
            verify=ch_secure,
            connect_timeout=30
        )
        
        # Test query
        result = client.query("SELECT version()")
        version = result.result_rows[0][0] if result.result_rows else "unknown"
        print(f"{Fore.GREEN}✓ ClickHouse connected: v{version}{Style.RESET_ALL}")
        
        # Check tables
        tables = client.query("SHOW TABLES").result_rows
        if tables:
            print(f"  Tables found: {len(tables)}")
            for table in tables[:5]:
                print(f"    - {table[0]}")
        else:
            print(f"  No tables found (will be created on startup)")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"{Fore.RED}✗ ClickHouse connection failed: {e}{Style.RESET_ALL}")
        print(f"  Ensure CLICKHOUSE_PASSWORD is set correctly")
        return False

def check_environment_variables() -> Dict[str, bool]:
    """Check all required environment variables."""
    print_section("Environment Variables Check")
    
    required_vars = {
        "DATABASE_URL": True,
        "REDIS_URL": True, 
        "CLICKHOUSE_URL": False,
        "CLICKHOUSE_HOST": True,
        "CLICKHOUSE_PORT": True,
        "CLICKHOUSE_PASSWORD": True,
        "PR_NUMBER": True,
        "ENVIRONMENT": True,
        "GCP_PROJECT_ID": False,
        "SECRET_MANAGER_PROJECT": False,
    }
    
    results = {}
    for var, is_required in required_vars.items():
        sensitive = "PASSWORD" in var or "URL" in var
        success, value = check_env_var(var, required=is_required, sensitive=sensitive)
        
        if success:
            if value == "NOT SET (optional)":
                print(f"{Fore.YELLOW}⚠ {var}: {value}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}✓ {var}: {value}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ {var}: {value}{Style.RESET_ALL}")
        
        results[var] = success
    
    return results

def check_gcp_configuration() -> bool:
    """Check GCP configuration and permissions."""
    print_section("GCP Configuration Check")
    
    try:
        # Check if gcloud is installed
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            project = result.stdout.strip()
            print(f"{Fore.GREEN}✓ GCP Project: {project}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ gcloud not configured{Style.RESET_ALL}")
            return False
        
        # Check Cloud SQL proxy
        result = subprocess.run(
            ["which", "cloud_sql_proxy"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"{Fore.GREEN}✓ Cloud SQL Proxy installed{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ Cloud SQL Proxy not found (needed for migrations){Style.RESET_ALL}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.YELLOW}⚠ GCP check skipped: {e}{Style.RESET_ALL}")
        return False

def main():
    """Run all validation checks."""
    print(f"{Fore.MAGENTA}╔{'═' * 58}╗")
    print(f"║{'Staging Environment Configuration Validator':^58}║")
    print(f"╚{'═' * 58}╝{Style.RESET_ALL}")
    
    # Track results
    results = {
        "github_secrets": False,
        "environment_vars": False,
        "postgresql": False,
        "redis": False,
        "clickhouse": False,
        "gcp": False,
    }
    
    # Run checks
    if os.getenv("GITHUB_ACTIONS"):
        print(f"\n{Fore.BLUE}Running in GitHub Actions environment{Style.RESET_ALL}")
        secrets = check_github_secrets()
        results["github_secrets"] = all([
            secrets.get("GCP_STAGING_SA_KEY", False),
            secrets.get("STAGING_DB_PASSWORD", False),
            secrets.get("CLICKHOUSE_PASSWORD", False)
        ])
    else:
        print(f"\n{Fore.BLUE}Running in local environment{Style.RESET_ALL}")
    
    env_results = check_environment_variables()
    results["environment_vars"] = all([
        v for k, v in env_results.items() 
        if k in ["DATABASE_URL", "REDIS_URL", "CLICKHOUSE_PASSWORD", "PR_NUMBER"]
    ])
    
    results["postgresql"] = check_database_connection()
    results["redis"] = check_redis_connection()
    results["clickhouse"] = check_clickhouse_connection()
    results["gcp"] = check_gcp_configuration()
    
    # Summary
    print_section("Validation Summary")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for check, passed in results.items():
        status = f"{Fore.GREEN}✓ PASS" if passed else f"{Fore.RED}✗ FAIL"
        print(f"  {check.replace('_', ' ').title():30} {status}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
    
    if passed == total:
        print(f"{Fore.GREEN}✓ All checks passed! ({passed}/{total}){Style.RESET_ALL}")
        print(f"{Fore.GREEN}Your staging environment is properly configured.{Style.RESET_ALL}")
        return 0
    else:
        print(f"{Fore.YELLOW}⚠ Some checks failed ({passed}/{total}){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Please review the errors above and update your configuration.{Style.RESET_ALL}")
        print(f"\nRefer to docs/STAGING_SECRETS_GUIDE.md for setup instructions.")
        return 1

if __name__ == "__main__":
    sys.exit(main())