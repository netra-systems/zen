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

def get_env_var_value(var_name: str) -> str:
    """Get environment variable value."""
    return os.getenv(var_name, "")

def format_env_display_value(value: str, sensitive: bool) -> str:
    """Format environment variable for display."""
    if not value:
        return ""
    if sensitive:
        return "***"
    return value[:20] + "..." if len(value) > 20 else value

def check_env_var(var_name: str, required: bool = True, sensitive: bool = False) -> Tuple[bool, str]:
    """Check if an environment variable is set."""
    value = get_env_var_value(var_name)
    if value:
        display_value = format_env_display_value(value, sensitive)
        return True, display_value
    return (False, "NOT SET") if required else (True, "NOT SET (optional)")

def get_required_github_secrets() -> Dict[str, bool]:
    """Get list of required GitHub secrets."""
    return {
        "GCP_STAGING_SA_KEY": False,
        "STAGING_DB_PASSWORD": False,
        "CLICKHOUSE_PASSWORD": False,
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": False,
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": False,
    }

def is_optional_secret(secret_name: str) -> bool:
    """Check if a secret is optional."""
    optional_secrets = ["GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING"]
    return secret_name in optional_secrets

def print_secret_status(secret_name: str, is_set: bool):
    """Print the status of a GitHub secret."""
    if is_set:
        print(f"{Fore.GREEN}✓ {secret_name}: Configured{Style.RESET_ALL}")
    elif is_optional_secret(secret_name):
        print(f"{Fore.YELLOW}⚠ {secret_name}: Not set (optional){Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗ {secret_name}: Not configured{Style.RESET_ALL}")

def check_single_github_secret(secret_name: str, secrets: Dict[str, bool]):
    """Check and update status for a single GitHub secret."""
    is_set = bool(os.getenv(secret_name))
    secrets[secret_name] = is_set
    print_secret_status(secret_name, is_set)

def check_github_secrets() -> Dict[str, bool]:
    """Check if required GitHub secrets are available."""
    print_section("GitHub Secrets Check")
    secrets = get_required_github_secrets()
    for secret_name in secrets:
        check_single_github_secret(secret_name, secrets)
    return secrets

def parse_database_url(db_url: str) -> Tuple[str, Dict[str, str]]:
    """Parse DATABASE_URL into connection format and parameters."""
    if db_url.startswith("postgresql://"):
        db_url = db_url[13:]
    
    if "?host=/cloudsql/" in db_url:
        return "cloudsql", _parse_cloudsql_url(db_url)
    else:
        return "standard", {"url": db_url}

def split_cloudsql_url_parts(db_url: str) -> Tuple[str, str]:
    """Split Cloud SQL URL into main parts."""
    parts = db_url.split("?host=/cloudsql/")
    creds_and_db = parts[0]
    socket_path = f"/cloudsql/{parts[1]}"
    return creds_and_db, socket_path

def validate_cloudsql_format(creds_and_db: str):
    """Validate Cloud SQL URL format."""
    if "@" not in creds_and_db:
        raise ValueError("Invalid DATABASE_URL format")

def extract_cloudsql_credentials(creds_and_db: str) -> Tuple[str, str, str]:
    """Extract credentials and database from Cloud SQL URL."""
    creds, db = creds_and_db.split("@")[0], creds_and_db.split("/")[-1]
    user, password = creds.split(":")
    return user, password, db

def _parse_cloudsql_url(db_url: str) -> Dict[str, str]:
    """Parse Cloud SQL socket format URL."""
    creds_and_db, socket_path = split_cloudsql_url_parts(db_url)
    validate_cloudsql_format(creds_and_db)
    user, password, db = extract_cloudsql_credentials(creds_and_db)
    return {"user": user, "password": password, "database": db, "socket": socket_path}

def create_db_connection(conn_type: str, params: Dict[str, str]):
    """Create database connection based on type and parameters."""
    if conn_type == "cloudsql":
        return psycopg2.connect(
            host=params["socket"], database=params["database"],
            user=params["user"], password=params["password"]
        )
    else:
        return psycopg2.connect(params["url"])

def test_db_connection(conn) -> str:
    """Test database connection and return version."""
    cursor = conn.cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    cursor.close()
    print(f"{Fore.GREEN}✓ PostgreSQL connected: {version[:50]}...{Style.RESET_ALL}")
    return version

def query_database_tables(conn) -> List[Tuple]:
    """Query database for existing tables."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' ORDER BY table_name LIMIT 10
    """)
    tables = cursor.fetchall()
    cursor.close()
    return tables

def print_table_results(tables: List[Tuple]):
    """Print database table results."""
    if tables:
        print(f"  Tables found: {len(tables)}")
        for table in tables[:5]:
            print(f"    - {table[0]}")
    else:
        print(f"{Fore.YELLOW}  ⚠ No tables found (run migrations){Style.RESET_ALL}")

def check_database_tables(conn) -> bool:
    """Check for existing tables in database."""
    tables = query_database_tables(conn)
    print_table_results(tables)
    return bool(tables)

def validate_database_url() -> str:
    """Validate DATABASE_URL environment variable."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print(f"{Fore.RED}✗ DATABASE_URL not set{Style.RESET_ALL}")
        return ""
    return db_url

def perform_database_connection_test(db_url: str) -> bool:
    """Perform database connection and testing."""
    try:
        conn_type, params = parse_database_url(db_url)
        conn = create_db_connection(conn_type, params)
        test_db_connection(conn)
        check_database_tables(conn)
        conn.close()
        return True
    except Exception as e:
        print(f"{Fore.RED}✗ PostgreSQL connection failed: {e}{Style.RESET_ALL}")
        return False

def check_database_connection() -> bool:
    """Test PostgreSQL database connection."""
    print_section("PostgreSQL Connection Test")
    db_url = validate_database_url()
    if not db_url:
        return False
    return perform_database_connection_test(db_url)

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
    
    ch_host = os.getenv("CLICKHOUSE_HOST", "clickhouse_host_url_placeholder")
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

def print_validator_header():
    """Print the main validator header."""
    print(f"{Fore.MAGENTA}╔{'═' * 58}╗")
    print(f"║{'Staging Environment Configuration Validator':^58}║")
    print(f"╚{'═' * 58}╝{Style.RESET_ALL}")

def initialize_results_tracking() -> Dict[str, bool]:
    """Initialize the results tracking dictionary."""
    return {
        "github_secrets": False, "environment_vars": False,
        "postgresql": False, "redis": False,
        "clickhouse": False, "gcp": False
    }

def run_github_actions_checks(results: Dict[str, bool]):
    """Run checks specific to GitHub Actions environment."""
    print(f"\n{Fore.BLUE}Running in GitHub Actions environment{Style.RESET_ALL}")
    secrets = check_github_secrets()
    results["github_secrets"] = all([
        secrets.get("GCP_STAGING_SA_KEY", False),
        secrets.get("STAGING_DB_PASSWORD", False),
        secrets.get("CLICKHOUSE_PASSWORD", False)
    ])

def run_local_environment_checks():
    """Run checks for local environment."""
    print(f"\n{Fore.BLUE}Running in local environment{Style.RESET_ALL}")

def run_core_validation_checks(results: Dict[str, bool]):
    """Run core validation checks for all environments."""
    env_results = check_environment_variables()
    results["environment_vars"] = all([
        v for k, v in env_results.items() 
        if k in ["DATABASE_URL", "REDIS_URL", "CLICKHOUSE_PASSWORD", "PR_NUMBER"]
    ])
    results["postgresql"] = check_database_connection()
    results["redis"] = check_redis_connection()
    results["clickhouse"] = check_clickhouse_connection()
    results["gcp"] = check_gcp_configuration()

def print_validation_results(results: Dict[str, bool]):
    """Print the validation results summary."""
    print_section("Validation Summary")
    for check, check_passed in results.items():
        status = f"{Fore.GREEN}✓ PASS" if check_passed else f"{Fore.RED}✗ FAIL"
        print(f"  {check.replace('_', ' ').title():30} {status}{Style.RESET_ALL}")

def determine_final_result(results: Dict[str, bool]) -> int:
    """Determine and print the final result."""
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
    if passed == total:
        print(f"{Fore.GREEN}✓ All checks passed! ({passed}/{total}){Style.RESET_ALL}")
        print(f"{Fore.GREEN}Your staging environment is properly configured.{Style.RESET_ALL}")
        return 0
    print(f"{Fore.YELLOW}⚠ Some checks failed ({passed}/{total}){Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Please review the errors above and update your configuration.{Style.RESET_ALL}")
    print(f"\nRefer to docs/STAGING_SECRETS_GUIDE.md for setup instructions.")
    return 1

def main():
    """Run all validation checks."""
    print_validator_header()
    results = initialize_results_tracking()
    if os.getenv("GITHUB_ACTIONS"):
        run_github_actions_checks(results)
    else:
        run_local_environment_checks()
    run_core_validation_checks(results)
    print_validation_results(results)
    return determine_final_result(results)

if __name__ == "__main__":
    sys.exit(main())