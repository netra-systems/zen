#!/usr/bin/env python3
"""
Database Connectivity Debug Script
==================================

This script comprehensively diagnoses database connectivity issues in the test environment.
It tests all components of the database configuration pipeline and provides detailed fix recommendations.

Usage:
    python database_connectivity_debug.py

This will:
1. Test environment variable loading
2. Test DatabaseURLBuilder configuration  
3. Test database connection attempts
4. Test Docker service connectivity
5. Provide detailed error messages for fixing issues
"""

import sys
import os
import traceback
import asyncio
import socket

# Ensure we can import our modules
sys.path.insert(0, os.path.abspath('.'))

def test_environment_loading():
    """Test that environment variables are being loaded correctly."""
    print("=" * 60)
    print("STEP 1: Testing Environment Variable Loading")
    print("=" * 60)
    
    try:
        from shared.isolated_environment import get_env
        env = get_env()
        
        print(f"Environment instance type: {type(env)}")
        print(f"Isolation enabled: {env.is_isolated()}")
        print(f"Environment name: {env.get_environment_name()}")
        
        # Check critical database variables
        db_vars = [
            'DATABASE_URL',
            'POSTGRES_HOST', 
            'POSTGRES_PORT',
            'POSTGRES_USER',
            'POSTGRES_PASSWORD', 
            'POSTGRES_DB',
            'ENVIRONMENT',
            'TEST_POSTGRES_PORT',
            'ALPINE_TEST_POSTGRES_PORT'
        ]
        
        print("\nDatabase-related environment variables:")
        for var in db_vars:
            value = env.get(var)
            if value and 'password' in var.lower():
                print(f"  {var}: {'*' * min(len(value), 8)} (masked)")
            else:
                print(f"  {var}: {value}")
        
        return True, env
        
    except Exception as e:
        print(f"ERROR: Failed to load environment: {e}")
        traceback.print_exc()
        return False, None


def test_database_url_builder(env):
    """Test DatabaseURLBuilder functionality."""
    print("\n" + "=" * 60)
    print("STEP 2: Testing DatabaseURLBuilder")
    print("=" * 60)
    
    try:
        from shared.database_url_builder import DatabaseURLBuilder
        
        builder = DatabaseURLBuilder(env.as_dict())
        
        print(f"Environment detected: {builder.environment}")
        print(f"Docker environment: {builder.is_docker_environment()}")
        print(f"Has Cloud SQL config: {builder.cloud_sql.is_cloud_sql}")
        print(f"Has TCP config: {builder.tcp.has_config}")
        
        # Test different URL builders
        print("\nURL Generation Tests:")
        
        # Test environment-specific URL
        auto_url = builder.get_url_for_environment(sync=False)
        print(f"Auto URL (async): {builder.mask_url_for_logging(auto_url)}")
        
        # Test specific builders based on environment
        if builder.environment == "test":
            test_postgres_url = builder.test.postgres_url
            test_memory_url = builder.test.memory_url
            test_auto_url = builder.test.auto_url
            
            print(f"Test PostgreSQL URL: {builder.mask_url_for_logging(test_postgres_url)}")
            print(f"Test Memory URL: {test_memory_url}")
            print(f"Test Auto URL: {builder.mask_url_for_logging(test_auto_url)}")
            
            # Show raw URLs for debugging (masked passwords)
            if test_postgres_url:
                print(f"Raw Test PostgreSQL URL: {test_postgres_url.replace(builder.postgres_password, '***') if builder.postgres_password else test_postgres_url}")
        
        elif builder.environment == "development":
            dev_url = builder.development.auto_url
            print(f"Development URL: {builder.mask_url_for_logging(dev_url)}")
        
        if builder.tcp.has_config:
            tcp_url = builder.tcp.async_url
            print(f"TCP URL: {builder.mask_url_for_logging(tcp_url)}")
        
        # Validation
        is_valid, error_msg = builder.validate()
        print(f"\nValidation result: {'PASS' if is_valid else 'FAIL'}")
        if not is_valid:
            print(f"Validation error: {error_msg}")
        
        print(f"\nSafe log message: {builder.get_safe_log_message()}")
        
        # Debug info
        debug_info = builder.debug_info()
        print(f"\nDebug Info:")
        for key, value in debug_info.items():
            print(f"  {key}: {value}")
        
        return True, builder, auto_url
        
    except Exception as e:
        print(f"ERROR: DatabaseURLBuilder failed: {e}")
        traceback.print_exc()
        return False, None, None


def test_database_manager(database_url):
    """Test DatabaseManager functionality."""
    print("\n" + "=" * 60)
    print("STEP 3: Testing DatabaseManager")
    print("=" * 60)
    
    if not database_url:
        print("SKIP: No database URL to test")
        return False
    
    try:
        from netra_backend.app.db.database_manager import get_database_manager
        
        # Mask password in URL for display
        display_url = database_url
        if 'password' in database_url.lower() and '@' in database_url:
            parts = database_url.split('@')
            if len(parts) >= 2:
                auth_part = parts[0]
                if ':' in auth_part:
                    cred_parts = auth_part.split(':')
                    if len(cred_parts) >= 3:  # scheme://user:password
                        masked_auth = ':'.join(cred_parts[:-1]) + ':***'
                        display_url = masked_auth + '@' + '@'.join(parts[1:])
        
        print(f"Testing database connection with URL: {display_url}")
        
        manager = get_database_manager()
        print(f"Database manager type: {type(manager)}")
        print(f"Manager initialized: {manager._initialized}")
        
        # Test initialization
        async def test_db_connection():
            try:
                print("Attempting to initialize database manager...")
                await manager.initialize()
                print("[U+2713] Database manager initialized successfully")
                
                # Test health check
                print("Performing health check...")
                health = await manager.health_check()
                print(f"Health check result: {health}")
                
                if health['status'] == 'healthy':
                    print("[OK] Database connection is healthy")
                    return True
                else:
                    print(f"[FAIL] Database connection unhealthy: {health.get('error', 'Unknown error')}")
                    return False
                    
            except Exception as e:
                print(f"[FAIL] Database connection failed: {e}")
                print(f"Exception type: {type(e).__name__}")
                traceback.print_exc()
                return False
            finally:
                try:
                    await manager.close_all()
                except:
                    pass
        
        # Run the async test
        result = asyncio.run(test_db_connection())
        return result
        
    except Exception as e:
        print(f"ERROR: DatabaseManager test failed: {e}")
        traceback.print_exc()
        return False


def test_config_loading():
    """Test configuration loading."""
    print("\n" + "=" * 60)
    print("STEP 4: Testing Configuration Loading")
    print("=" * 60)
    
    try:
        from netra_backend.app.core.config import get_config
        
        config = get_config()
        print(f"Config type: {type(config)}")
        print(f"Environment: {config.environment}")
        
        if config.database_url:
            # Mask password for display
            display_url = config.database_url
            if '@' in display_url and ':' in display_url:
                try:
                    parts = display_url.split('@')
                    if len(parts) >= 2:
                        auth_part = parts[0]
                        cred_parts = auth_part.split(':')
                        if len(cred_parts) >= 3:
                            masked_auth = ':'.join(cred_parts[:-1]) + ':***'
                            display_url = masked_auth + '@' + '@'.join(parts[1:])
                except:
                    display_url = "***MASKED***"
            
            print(f"Database URL: {display_url}")
        else:
            print("Database URL: NOT SET")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Configuration loading failed: {e}")
        traceback.print_exc()
        return False


def test_docker_connectivity():
    """Test Docker service connectivity."""
    print("\n" + "=" * 60)
    print("STEP 5: Testing Docker Service Connectivity")
    print("=" * 60)
    
    # Test common Docker database ports
    docker_services = [
        # Test environment ports
        ('localhost', 5435, 'Alpine Test PostgreSQL (local port)'),
        ('localhost', 5434, 'Test PostgreSQL (local port)'),
        
        # Development environment ports  
        ('localhost', 5433, 'Dev PostgreSQL (local port)'),
        ('localhost', 5432, 'Default PostgreSQL (local port)'),
        
        # Redis ports
        ('localhost', 6382, 'Alpine Test Redis'),
        ('localhost', 6381, 'Test Redis'),
        ('localhost', 6380, 'Dev Redis'),
        ('localhost', 6379, 'Default Redis'),
        
        # ClickHouse ports
        ('localhost', 8126, 'Alpine Test ClickHouse HTTP'),
        ('localhost', 8125, 'Test ClickHouse HTTP'),
        ('localhost', 8124, 'Dev ClickHouse HTTP'),
        ('localhost', 8123, 'Default ClickHouse HTTP'),
    ]
    
    reachable = []
    unreachable = []
    
    for host, port, description in docker_services:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"[OK] {description} ({host}:{port}) - REACHABLE")
                reachable.append((host, port, description))
            else:
                print(f"[FAIL] {description} ({host}:{port}) - NOT REACHABLE")
                unreachable.append((host, port, description))
                
        except Exception as e:
            print(f"[ERROR] {description} ({host}:{port}) - ERROR: {e}")
            unreachable.append((host, port, description))
    
    print(f"\nDocker Connectivity Summary:")
    print(f"  Reachable services: {len(reachable)}")
    print(f"  Unreachable services: {len(unreachable)}")
    
    return len(reachable) > 0, reachable, unreachable


def provide_fix_recommendations(reachable_services, unreachable_services):
    """Provide recommendations for fixing database connectivity issues."""
    print("\n" + "=" * 60)
    print("FIX RECOMMENDATIONS")
    print("=" * 60)
    
    if not reachable_services:
        print("""
[U+1F534] CRITICAL: NO SERVICES ARE REACHABLE

This indicates that Docker services are not running. Here's how to fix:

1. START DOCKER SERVICES:
   # For test environment (recommended):
   docker-compose -f docker-compose.alpine-test.yml up -d

   # Check if services are running:
   docker-compose -f docker-compose.alpine-test.yml ps

2. VERIFY SERVICE HEALTH:
   docker-compose -f docker-compose.alpine-test.yml logs alpine-test-postgres
   docker-compose -f docker-compose.alpine-test.yml logs alpine-test-redis

3. CHECK PORT CONFLICTS:
   netstat -an | grep :5434
   netstat -an | grep :5435

4. ENVIRONMENT CONFIGURATION:
   Create/update .env.test:
   ENVIRONMENT=test
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5434
   POSTGRES_USER=test  
   POSTGRES_PASSWORD=test
   POSTGRES_DB=netra_test

5. RUN TESTS WITH SERVICES:
   python tests/unified_test_runner.py --real-services
   # This will automatically start Docker services
""")
    
    elif len(unreachable_services) > len(reachable_services):
        print(f"""
[U+1F7E1] PARTIAL CONNECTIVITY: {len(reachable_services)} reachable, {len(unreachable_services)} unreachable

Some services are running but not all. Specific fixes:

1. CHECK SPECIFIC SERVICE LOGS:""")
        
        for host, port, desc in unreachable_services[:3]:  # Show first 3
            if 'PostgreSQL' in desc:
                print(f"   docker-compose logs alpine-test-postgres  # For {desc}")
            elif 'Redis' in desc:
                print(f"   docker-compose logs alpine-test-redis     # For {desc}")
            elif 'ClickHouse' in desc:
                print(f"   docker-compose logs alpine-test-clickhouse # For {desc}")
        
        print(f"""
2. RESTART SPECIFIC SERVICES:
   docker-compose -f docker-compose.alpine-test.yml restart alpine-test-postgres

3. CHECK PORT MAPPINGS:
   The services might be running on different ports than expected.
   Verify docker-compose.alpine-test.yml port mappings.
""")
    
    else:
        print(f"""
[U+1F7E2] GOOD CONNECTIVITY: {len(reachable_services)} services reachable

Most services are accessible. If database tests are still failing:

1. CHECK DATABASE URL CONSTRUCTION:
   The issue is likely in URL formatting or credentials.

2. VERIFY TEST ENVIRONMENT:
   export ENVIRONMENT=test
   python database_connectivity_debug.py

3. CHECK DOCKER HOSTNAMES:
   If running tests inside Docker, hostnames should be:
   - alpine-test-postgres:5432 (not localhost:5434)
   
4. CHECK DATABASE CREDENTIALS:
   User: test, Password: test, Database: netra_test
""")

    print("""
COMMON DEBUGGING COMMANDS:
- docker ps                                    # List running containers
- docker-compose ps                           # List compose services
- docker logs <container_name>                # View container logs
- docker exec -it <container> psql -U test   # Connect to database
- netstat -tulpn | grep :5434                # Check port usage
""")


def main():
    """Run all database connectivity tests."""
    print("Database Connectivity Debug Script")
    print("This script will test all components of database connectivity\n")
    
    # Test 1: Environment loading
    env_success, env = test_environment_loading()
    if not env_success:
        print("\n FAIL:  CRITICAL: Environment loading failed. Cannot proceed.")
        return 1
    
    # Test 2: DatabaseURLBuilder
    builder_success, builder, database_url = test_database_url_builder(env)
    if not builder_success:
        print("\n FAIL:  CRITICAL: DatabaseURLBuilder failed. Cannot proceed.")
        return 1
    
    # Test 3: Configuration loading
    config_success = test_config_loading()
    if not config_success:
        print("\n WARNING: [U+FE0F]  WARNING: Configuration loading failed. This may cause issues.")
    
    # Test 4: Docker connectivity
    docker_success, reachable, unreachable = test_docker_connectivity()
    
    # Test 5: Database connection (only if URL is available)
    db_success = False
    if database_url:
        db_success = test_database_manager(database_url)
    else:
        print(f"\n WARNING: [U+FE0F]  WARNING: No database URL generated - cannot test database connection")
    
    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    print(f"Environment Loading:  {' PASS:  PASS' if env_success else ' FAIL:  FAIL'}")
    print(f"URL Builder:         {' PASS:  PASS' if builder_success else ' FAIL:  FAIL'}")
    print(f"Configuration:       {' PASS:  PASS' if config_success else ' WARNING: [U+FE0F]  WARN'}")
    print(f"Docker Connectivity: {' PASS:  PASS' if docker_success else ' FAIL:  FAIL'}")
    print(f"Database Connection: {' PASS:  PASS' if db_success else ' FAIL:  FAIL'}")
    print(f"Database URL Generated: {' PASS:  YES' if database_url else ' FAIL:  NO'}")
    
    if env_success and builder_success and database_url and db_success and docker_success:
        print("\n CELEBRATION:  ALL TESTS PASSED - Database connectivity should work perfectly!")
        return 0
    else:
        print("\n WARNING: [U+FE0F]  ISSUES DETECTED - Database connectivity problems found")
        provide_fix_recommendations(reachable if docker_success else [], unreachable if docker_success else [])
        return 1


if __name__ == "__main__":
    sys.exit(main())