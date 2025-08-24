#!/usr/bin/env python3
"""
Test Database Connections - Root Cause Analysis for Dev Launcher Failures

This test validates database connections to identify why the dev launcher
is failing to connect to Docker containers.

Implements Five Whys methodology for systematic root cause analysis.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_postgres_connection():
    """Test PostgreSQL connection to identify root cause of failures."""
    print("\n" + "="*60)
    print("TESTING: PostgreSQL Connection")
    print("="*60)
    
    # Check environment variables first
    from dev_launcher.isolated_environment import get_env
    env = get_env()
    
    # Load environment files
    env_files = ['.env', '.env.local', '.secrets']
    for env_file in env_files:
        env_path = project_root / env_file
        if env_path.exists():
            print(f"[+] Found {env_file}")
            env.load_from_file(str(env_path), override_existing=True)
        else:
            print(f"[-] Missing {env_file}")
    
    database_url = env.get("DATABASE_URL")
    print(f"DATABASE_URL: {database_url}")
    
    if not database_url:
        print("[ERROR] WHY 1: DATABASE_URL not found in environment")
        return False
    
    # Parse the URL to check components
    from urllib.parse import urlparse
    parsed = urlparse(database_url)
    print(f"   Host: {parsed.hostname}")
    print(f"   Port: {parsed.port}")
    print(f"   Database: {parsed.path.lstrip('/')}")
    print(f"   Username: {parsed.username}")
    print(f"   Password: {'***' if parsed.password else 'None'}")
    
    # Test connection with asyncpg
    try:
        import asyncpg
        print("[+] asyncpg library available")
        
        # Clean URL for asyncpg
        clean_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        print(f"Clean URL: {clean_url}")
        
        # Try connection with timeout
        print("🔄 Attempting connection...")
        conn = await asyncio.wait_for(
            asyncpg.connect(clean_url),
            timeout=10.0
        )
        
        # Test basic query
        result = await conn.execute("SELECT 1")
        await conn.close()
        
        print("✅ PostgreSQL connection successful")
        return True
        
    except ImportError:
        print("❌ WHY 2: asyncpg library not installed")
        return False
    except asyncio.TimeoutError:
        print("❌ WHY 2: Connection timeout - Docker container not accessible")
        return False
    except Exception as e:
        print(f"❌ WHY 2: Connection failed - {str(e)}")
        return False

async def test_redis_connection():
    """Test Redis connection to identify root cause of failures."""
    print("\n" + "="*60)
    print("TESTING: Redis Connection")
    print("="*60)
    
    from dev_launcher.isolated_environment import get_env
    env = get_env()
    
    redis_url = env.get("REDIS_URL", "redis://localhost:6379")
    print(f"REDIS_URL: {redis_url}")
    
    try:
        import redis.asyncio as redis
        print("✓ redis library available")
        
        # Test connection
        print("🔄 Attempting connection...")
        client = redis.from_url(redis_url, socket_connect_timeout=5)
        await client.ping()
        await client.close()
        
        print("✅ Redis connection successful")
        return True
        
    except ImportError:
        print("❌ WHY 2: redis library not installed")
        return False
    except Exception as e:
        print(f"❌ WHY 2: Redis connection failed - {str(e)}")
        return False

async def test_clickhouse_connection():
    """Test ClickHouse connection to identify root cause of failures."""
    print("\n" + "="*60)
    print("TESTING: ClickHouse Connection")
    print("="*60)
    
    from dev_launcher.isolated_environment import get_env
    env = get_env()
    
    # Get ClickHouse configuration
    host = env.get("CLICKHOUSE_HOST", "localhost")
    port = env.get("CLICKHOUSE_HTTP_PORT", "8123")
    user = env.get("CLICKHOUSE_USER", "default")
    password = env.get("CLICKHOUSE_PASSWORD", "")
    
    print(f"ClickHouse Config:")
    print(f"   Host: {host}")
    print(f"   HTTP Port: {port}")
    print(f"   User: {user}")
    print(f"   Password: {'***' if password else 'None'}")
    
    try:
        import aiohttp
        print("✓ aiohttp library available")
        
        # Build URL
        base_url = f"http://{host}:{port}"
        print(f"Base URL: {base_url}")
        
        # Test ping endpoint
        print("🔄 Attempting ping...")
        async with aiohttp.ClientSession() as session:
            auth = aiohttp.BasicAuth(user, password) if user else None
            async with session.get(
                f"{base_url}/ping", 
                auth=auth, 
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    print("✅ ClickHouse connection successful")
                    return True
                else:
                    print(f"❌ WHY 2: ClickHouse ping failed - HTTP {response.status}")
                    return False
                    
    except ImportError:
        print("❌ WHY 2: aiohttp library not installed")
        return False
    except Exception as e:
        print(f"❌ WHY 2: ClickHouse connection failed - {str(e)}")
        return False

def check_docker_containers():
    """Check if Docker containers are running."""
    print("\n" + "="*60)
    print("TESTING: Docker Container Status")
    print("="*60)
    
    import subprocess
    
    try:
        # Check if Docker is available
        result = subprocess.run(
            ["docker", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode != 0:
            print("❌ WHY 1: Docker not available")
            return False
            
        print(f"✓ Docker available: {result.stdout.strip()}")
        
        # List running containers
        result = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Ports}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print("❌ WHY 2: Cannot list Docker containers")
            return False
            
        print("Docker containers:")
        print(result.stdout)
        
        # Check specific database containers
        containers_to_check = ["postgres", "redis", "clickhouse"]
        running_containers = result.stdout.lower()
        
        for container in containers_to_check:
            if container in running_containers:
                print(f"✓ {container.upper()} container appears to be running")
            else:
                print(f"❌ {container.upper()} container not found")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ WHY 2: Docker command timeout")
        return False
    except FileNotFoundError:
        print("❌ WHY 1: Docker command not found")
        return False
    except Exception as e:
        print(f"❌ WHY 2: Docker check failed - {str(e)}")
        return False

def check_network_ports():
    """Check if database ports are accessible."""
    print("\n" + "="*60)
    print("TESTING: Network Port Accessibility")
    print("="*60)
    
    import socket
    
    ports_to_check = [
        ("PostgreSQL", "localhost", 5432),
        ("Redis", "localhost", 6379), 
        ("ClickHouse HTTP", "localhost", 8123),
        ("ClickHouse Native", "localhost", 9000)
    ]
    
    accessible_ports = []
    
    for service, host, port in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"✅ {service} port {port} is accessible")
                accessible_ports.append((service, port))
            else:
                print(f"❌ {service} port {port} is NOT accessible")
                
        except Exception as e:
            print(f"❌ {service} port {port} check failed - {str(e)}")
    
    return len(accessible_ports) > 0

async def five_whys_analysis():
    """Perform Five Whys root cause analysis."""
    print("\n" + "="*80)
    print("FIVE WHYS ROOT CAUSE ANALYSIS")
    print("="*80)
    
    # WHY 1: Why are database connections failing?
    print("🔍 WHY 1: Why are database connections failing?")
    
    # Check basic prerequisites
    docker_ok = check_docker_containers()
    ports_ok = check_network_ports()
    
    if not docker_ok:
        print("🔍 WHY 2: Why aren't Docker containers running?")
        print("   - Docker service may not be started")
        print("   - Containers may have failed to start")
        print("   - Docker daemon may be inaccessible")
        return
    
    if not ports_ok:
        print("🔍 WHY 2: Why aren't database ports accessible?")
        print("   - Containers may not be exposing ports correctly")
        print("   - Port mapping configuration incorrect")
        print("   - Network connectivity issues")
        return
    
    # Test actual database connections
    postgres_ok = await test_postgres_connection()
    redis_ok = await test_redis_connection() 
    clickhouse_ok = await test_clickhouse_connection()
    
    if not any([postgres_ok, redis_ok, clickhouse_ok]):
        print("🔍 WHY 3: Why can't the app connect to running Docker containers?")
        print("   - Connection configuration may be incorrect")
        print("   - Authentication credentials may be wrong")
        print("   - SSL/TLS configuration may be incompatible")
        
        print("🔍 WHY 4: Why is the connection configuration incorrect?")
        print("   - Environment variables not loaded properly")
        print("   - URL format incompatible with drivers")
        print("   - Host networking vs Docker networking mismatch")
        
        print("🔍 WHY 5: What is the root configuration issue?")
        print("   - .env files may have wrong connection strings")
        print("   - Docker containers using different ports than expected")
        print("   - Host vs container hostname resolution issues")

async def main():
    """Main test runner with comprehensive root cause analysis."""
    # Set encoding for Windows
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)
    
    print("Database Connection Root Cause Analysis")
    print("Testing database connections for dev launcher failures...")
    
    try:
        await five_whys_analysis()
        
        print("\n" + "="*80)
        print("DIAGNOSIS COMPLETE")
        print("="*80)
        print("Check the output above for specific root causes and fixes needed.")
        
    except Exception as e:
        print(f"Test runner failed: {str(e)}")
        logger.error(f"Test runner exception: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())