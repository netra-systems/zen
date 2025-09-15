#!/usr/bin/env python3
"""
Local Services Setup for Integration Tests
Sets up PostgreSQL and Redis locally without Docker for Golden Path tests
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import asyncpg
import aioredis


async def check_postgres_connection(host="localhost", port=5432, user="netra_user", password="netra_password", database="netra_test"):
    """Check if PostgreSQL is accessible and create database if needed."""
    try:
        # First try to connect to postgres database to create our database
        conn = await asyncpg.connect(
            host=host, port=port, user=user, password=password, database="postgres"
        )
        
        # Check if our database exists
        result = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", database)
        if not result:
            print(f"Creating database: {database}")
            await conn.execute(f'CREATE DATABASE "{database}"')
        
        await conn.close()
        
        # Now connect to our database to verify it works
        conn = await asyncpg.connect(
            host=host, port=port, user=user, password=password, database=database
        )
        
        result = await conn.fetchval("SELECT version()")
        print(f"✅ PostgreSQL connected: {result.split(',')[0]}")
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False


async def check_redis_connection(host="localhost", port=6379, db=1):
    """Check if Redis is accessible."""
    try:
        redis = aioredis.from_url(f"redis://{host}:{port}/{db}")
        await redis.ping()
        await redis.set("test_key", "test_value")
        value = await redis.get("test_key")
        await redis.delete("test_key")
        await redis.close()
        
        print(f"✅ Redis connected successfully at {host}:{port}/{db}")
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def setup_postgresql():
    """Install and configure PostgreSQL via Homebrew."""
    print("🔧 Setting up PostgreSQL...")
    
    try:
        # Check if PostgreSQL is installed
        result = subprocess.run(["which", "psql"], capture_output=True)
        if result.returncode != 0:
            print("Installing PostgreSQL...")
            subprocess.run(["brew", "install", "postgresql@15"], check=True)
        
        # Start PostgreSQL service
        print("Starting PostgreSQL service...")
        subprocess.run(["brew", "services", "start", "postgresql@15"], check=True)
        
        # Wait a moment for service to start
        time.sleep(3)
        
        # Create user and databases
        print("Creating user and databases...")
        try:
            subprocess.run([
                "createuser", "-s", "netra_user"
            ], check=False)  # Don't fail if user exists
            
            subprocess.run([
                "psql", "-d", "postgres", "-c", 
                "ALTER USER netra_user WITH PASSWORD 'netra_password';"
            ], check=True)
            
            # Create databases
            for db_name in ["netra_dev", "netra_test"]:
                try:
                    subprocess.run(["createdb", "-O", "netra_user", db_name], check=False)
                except:
                    pass  # Database might already exist
            
        except subprocess.CalledProcessError as e:
            print(f"Warning: Database setup had issues: {e}")
            print("This might be normal if databases already exist.")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ PostgreSQL setup failed: {e}")
        return False


def setup_redis():
    """Install and configure Redis via Homebrew."""
    print("🔧 Setting up Redis...")
    
    try:
        # Check if Redis is installed
        result = subprocess.run(["which", "redis-server"], capture_output=True)
        if result.returncode != 0:
            print("Installing Redis...")
            subprocess.run(["brew", "install", "redis"], check=True)
        
        # Start Redis service
        print("Starting Redis service...")
        subprocess.run(["brew", "services", "start", "redis"], check=True)
        
        # Wait a moment for service to start
        time.sleep(2)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Redis setup failed: {e}")
        return False


def create_test_env_file():
    """Create the test environment file."""
    env_content = """# Local Test Environment Configuration
# For Golden Path integration tests without Docker

# Enable real services for integration testing
USE_REAL_SERVICES=true
REAL_SERVICES_ENABLED=true

# Database Configuration
DATABASE_URL=postgresql://netra_user:netra_password@localhost:5432/netra_test
DB_HOST=localhost
DB_PORT=5432
DB_NAME=netra_test
DB_USER=netra_user
DB_PASSWORD=netra_password
DB_SSL_MODE=prefer

# Redis Configuration
REDIS_URL=redis://localhost:6379/1
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1
REDIS_PASSWORD=

# Test Environment Settings
ENVIRONMENT=test
PYTHON_ENV=test
NODE_ENV=test
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# JWT Configuration for tests
JWT_SECRET_KEY=test-jwt-secret-key-for-integration-tests
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# WebSocket Configuration for tests
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8000
WEBSOCKET_URL=ws://localhost:8000/ws

# Disable external services for tests
OPENAI_API_KEY=test-key
ANTHROPIC_API_KEY=test-key

# Test-specific flags
ENABLE_ANALYTICS=false
ENABLE_CACHING=true
ENABLE_WEBSOCKET_COMPRESSION=false
ENABLE_HEALTH_CHECKS=true
"""
    
    env_file = Path(__file__).parent.parent / ".env.test.local"
    with open(env_file, "w") as f:
        f.write(env_content)
    
    print(f"✅ Created test environment file: {env_file}")


async def main():
    """Main setup function."""
    print("🚀 Setting up local services for Golden Path integration tests...")
    print("=" * 60)
    
    # Setup services
    postgres_ok = setup_postgresql()
    redis_ok = setup_redis()
    
    if not postgres_ok or not redis_ok:
        print("\n❌ Service setup failed. Please check the errors above.")
        sys.exit(1)
    
    # Create environment file
    create_test_env_file()
    
    # Test connections
    print("\n🔍 Testing connections...")
    postgres_connected = await check_postgres_connection()
    redis_connected = await check_redis_connection()
    
    if postgres_connected and redis_connected:
        print("\n✅ All services are ready!")
        print("\nYou can now run Golden Path integration tests:")
        print("export PYTHONPATH=/Users/anthony/Desktop/netra-apex:$PYTHONPATH")
        print("source .env.test.local")
        print("python3 -m pytest tests/integration/golden_path/ -v")
        
        print("\nOr run a specific test:")
        print("python3 -m pytest tests/integration/golden_path/test_agent_orchestration_execution_comprehensive.py::TestAgentOrchestrationExecution::test_supervisor_agent_orchestration_basic_flow -v")
    else:
        print("\n❌ Connection tests failed. Please check the service configurations.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())