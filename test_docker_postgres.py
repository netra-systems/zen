#!/usr/bin/env python3
"""
Test script to start PostgreSQL Docker container manually.
"""
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dev_launcher.isolated_environment import get_env
from dev_launcher.docker_services import DockerServiceManager


def test_docker_postgres():
    """Test starting PostgreSQL Docker container."""
    print("=== Testing PostgreSQL Docker Container ===\n")
    
    # Check if Docker is available
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"[OK] Docker is available: {result.stdout.strip()}")
        else:
            print(f"[ERROR] Docker not available: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Docker check failed: {e}")
        print("\nPlease ensure Docker Desktop is running.")
        return False
    
    # Load environment variables
    env = get_env()
    env_file = project_root / ".env"
    if env_file.exists():
        loaded, errors = env.load_from_file(env_file, source="test", override_existing=True)
        print(f"[OK] Loaded {loaded} variables from .env")
    
    # Check current PostgreSQL configuration
    postgres_password = env.get("POSTGRES_PASSWORD", "DTprdt5KoQXlEG4Gh9lF")
    postgres_db = env.get("POSTGRES_DB", "netra_dev")
    postgres_user = env.get("POSTGRES_USER", "postgres")
    
    print(f"\n=== Configuration ===")
    print(f"POSTGRES_USER: {postgres_user}")
    print(f"POSTGRES_PASSWORD: {'*' * len(postgres_password)}")
    print(f"POSTGRES_DB: {postgres_db}")
    print(f"Port mapping: 5433:5432")
    
    # Check if container already exists
    print(f"\n=== Checking for existing containers ===")
    container_names = ["netra-dev-postgres", "netra-postgres-dev"]
    
    for container_name in container_names:
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}: {{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip():
                print(f"Found: {result.stdout.strip()}")
                
                # Try to remove it
                print(f"Removing container {container_name}...")
                subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=10)
                subprocess.run(["docker", "rm", container_name], capture_output=True, timeout=10)
        except Exception as e:
            print(f"Error checking container {container_name}: {e}")
    
    # Start PostgreSQL container using DockerServiceManager
    print(f"\n=== Starting PostgreSQL Docker Container ===")
    
    try:
        docker_manager = DockerServiceManager()
        success, message = docker_manager.start_postgres_container()
        
        print(f"Result: {message}")
        
        if success:
            print("\n[SUCCESS] PostgreSQL container started!")
            
            # Wait a moment for the container to be ready
            print("Waiting for container to be ready...")
            time.sleep(5)
            
            # Test connection
            print("\n=== Testing Connection ===")
            import asyncio
            asyncio.run(test_connection())
            
            return True
        else:
            print(f"\n[FAILED] Could not start container: {message}")
            
            # Check Docker logs if container was created
            try:
                result = subprocess.run(
                    ["docker", "logs", "netra-dev-postgres", "--tail", "20"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout:
                    print("\n=== Docker Logs ===")
                    print(result.stdout)
            except:
                pass
            
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to start container: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_connection():
    """Test database connection to the Docker container."""
    try:
        import asyncpg
        from shared.database_url_builder import DatabaseURLBuilder
        
        # Build connection URL using DatabaseURLBuilder
        env = get_env()
        
        # Create env vars for builder with Docker container configuration
        builder_env = env.get_all().copy()
        builder_env['POSTGRES_HOST'] = 'localhost'
        builder_env['POSTGRES_PORT'] = '5433'
        builder_env['POSTGRES_DB'] = env.get("POSTGRES_DB", "netra_dev")
        builder_env['POSTGRES_USER'] = env.get("POSTGRES_USER", "postgres")
        builder_env['POSTGRES_PASSWORD'] = env.get("POSTGRES_PASSWORD", "DTprdt5KoQXlEG4Gh9lF")
        builder_env['ENVIRONMENT'] = 'development'
        
        builder = DatabaseURLBuilder(builder_env)
        # Use format_for_asyncpg_driver to get clean URL for asyncpg.connect
        connection_url = builder.format_for_asyncpg_driver(builder.tcp.sync_url)
        
        print(f"Connecting to PostgreSQL...")
        conn = await asyncpg.connect(connection_url, timeout=10)
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        print(f"[SUCCESS] Connected! PostgreSQL version: {version[:50]}...")
        
        # Create a test table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS test_connection (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("[SUCCESS] Created test table")
        
        await conn.close()
        print("[SUCCESS] Connection test complete")
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")


if __name__ == "__main__":
    success = test_docker_postgres()
    sys.exit(0 if success else 1)