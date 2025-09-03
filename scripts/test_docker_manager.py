#!/usr/bin/env python3
"""
Test Docker Manager - DEPRECATED

⚠️  DEPRECATION NOTICE ⚠️ 
This script is DEPRECATED and should NOT be used for new code.

ALL Docker operations must now go through UnifiedDockerManager per CLAUDE.md Section 7.1.

Use instead:
- test_framework.unified_docker_manager.UnifiedDockerManager
- scripts/docker_manual.py (uses UnifiedDockerManager)
- tests/unified_test_runner.py --real-services (automatic Docker management)

This file remains only for legacy compatibility and will be removed in a future version.
"""

import os
import sys
import subprocess
import time
import warnings
from pathlib import Path
from typing import List, Optional, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Issue deprecation warning
warnings.warn(
    "TestDockerManager is deprecated. Use test_framework.unified_docker_manager.UnifiedDockerManager instead.",
    DeprecationWarning,
    stacklevel=2
)

from scripts.docker_health_manager import DockerHealthManager


class TestDockerManager:
    """Docker management optimized for test environments."""
    
    def __init__(self, environment: str = "test"):
        """Initialize for test or dev environment."""
        self.environment = environment
        
        if environment == "dev":
            self.manager = DockerHealthManager("docker-compose.yml", "netra-dev")
            # Dev service names (from docker-compose.yml)
            self.core_services = ["dev-postgres", "dev-redis"]
            self.extended_services = self.core_services + ["dev-clickhouse"] 
            self.all_services = self.extended_services + ["dev-backend", "dev-auth"]
        else:  # test
            self.manager = DockerHealthManager("docker-compose.test.yml", "netra-test") 
            # Test service names (from docker-compose.test.yml)
            self.core_services = ["test-postgres", "test-redis"]
            self.extended_services = self.core_services + ["test-clickhouse"]
            self.all_services = self.extended_services + ["test-backend", "test-auth"]
    
    def ensure_services(self, services: Optional[List[str]] = None, 
                      timeout: int = 60) -> bool:
        """Ensure services are running, reusing existing healthy containers."""
        services = services or self.core_services
        
        env_label = self.environment.upper()
        print(f"[{env_label}-DOCKER] Ensuring {self.environment} services: {', '.join(services)}")
        
        # First check if we can reuse existing containers
        status = self.manager.get_container_status(services)
        
        healthy_count = sum(1 for container in status.values() 
                          if container.state.value == "healthy")
        
        if healthy_count == len(services):
            print(f"[{env_label}-DOCKER] ✓ All {len(services)} services already healthy, reusing containers")
            return True
        
        print(f"[{env_label}-DOCKER] Found {healthy_count}/{len(services)} healthy services, starting missing ones")
        
        # Start services intelligently (only those that need it)
        success = self.manager.start_services_smart(services, wait_healthy=True)
        
        if success:
            print(f"[{env_label}-DOCKER] ✓ All {self.environment} services ready")
        else:
            print(f"[{env_label}-DOCKER] ✗ Failed to start {self.environment} services")
        
        return success
    
    def cleanup_environment(self, force: bool = False) -> bool:
        """Clean up environment gracefully."""
        env_label = self.environment.upper()
        if force:
            print(f"[{env_label}-DOCKER] Force cleanup requested")
            return self.manager.cleanup_orphans()
        else:
            # For normal cleanup, just stop the services but keep containers
            # for faster next startup
            print(f"[{env_label}-DOCKER] Graceful cleanup (containers preserved)")
            return True
    
    def reset_test_data(self, services: Optional[List[str]] = None) -> bool:
        """Reset test data without restarting containers."""
        services = services or self.core_services
        
        print("[TEST-DOCKER] Resetting test data without container restart")
        
        # For PostgreSQL: truncate tables
        if "postgres-test" in services:
            pg_reset_cmd = [
                "docker", "exec", "netra-test-postgres",
                "psql", "-U", "test_user", "-d", "netra_test",
                "-c", """
                    DO $$ 
                    DECLARE 
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
                        LOOP
                            EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' RESTART IDENTITY CASCADE';
                        END LOOP;
                    END $$;
                """
            ]
            try:
                subprocess.run(pg_reset_cmd, check=True, capture_output=True)
                print("[TEST-DOCKER] ✓ PostgreSQL data reset")
            except subprocess.CalledProcessError as e:
                print(f"[TEST-DOCKER] ✗ Failed to reset PostgreSQL: {e}")
        
        # For Redis: flush all data
        if "redis-test" in services:
            redis_reset_cmd = [
                "docker", "exec", "netra-test-redis",
                "redis-cli", "FLUSHALL"
            ]
            try:
                subprocess.run(redis_reset_cmd, check=True, capture_output=True)
                print("[TEST-DOCKER] ✓ Redis data reset")
            except subprocess.CalledProcessError as e:
                print(f"[TEST-DOCKER] ✗ Failed to reset Redis: {e}")
        
        return True
    
    def get_service_urls(self) -> dict:
        """Get service URLs for configuration."""
        if self.environment == "dev":
            # Dev environment configuration
            try:
                postgres_inspect = subprocess.run([
                    "docker", "port", "netra-dev-postgres", "5432"
                ], capture_output=True, text=True)
                
                redis_inspect = subprocess.run([
                    "docker", "port", "netra-dev-redis", "6379"  
                ], capture_output=True, text=True)
                
                pg_port = postgres_inspect.stdout.strip().split(':')[-1] if postgres_inspect.returncode == 0 else "5433"
                redis_port = redis_inspect.stdout.strip().split(':')[-1] if redis_inspect.returncode == 0 else "6380"
                
                return {
                    "DATABASE_URL": f"postgresql://netra:netra123@localhost:{pg_port}/netra",
                    "REDIS_URL": f"redis://localhost:{redis_port}",
                    "DEV_POSTGRES_PORT": pg_port,
                    "DEV_REDIS_PORT": redis_port
                }
            except Exception as e:
                print(f"[DEV-DOCKER] Warning: Could not discover ports: {e}")
                return {
                    "DATABASE_URL": "postgresql://netra:netra123@localhost:5433/netra",
                    "REDIS_URL": "redis://localhost:6380",
                    "DEV_POSTGRES_PORT": "5433",
                    "DEV_REDIS_PORT": "6380"
                }
        else:
            # Test environment configuration  
            try:
                postgres_inspect = subprocess.run([
                    "docker", "port", "netra-test-postgres", "5432"
                ], capture_output=True, text=True)
                
                redis_inspect = subprocess.run([
                    "docker", "port", "netra-test-redis", "6379"  
                ], capture_output=True, text=True)
                
                pg_port = postgres_inspect.stdout.strip().split(':')[-1] if postgres_inspect.returncode == 0 else "5434"
                redis_port = redis_inspect.stdout.strip().split(':')[-1] if redis_inspect.returncode == 0 else "6381"
                
                return {
                    "DATABASE_URL": f"postgresql://test_user:test_pass@localhost:{pg_port}/netra_test",
                    "REDIS_URL": f"redis://localhost:{redis_port}/1",
                    "TEST_POSTGRES_PORT": pg_port,
                    "TEST_REDIS_PORT": redis_port
                }
            except Exception as e:
                print(f"[TEST-DOCKER] Warning: Could not discover ports: {e}")
                return {
                    "DATABASE_URL": "postgresql://test_user:test_pass@localhost:5434/netra_test",
                    "REDIS_URL": "redis://localhost:6381/1",
                    "TEST_POSTGRES_PORT": "5434",
                    "TEST_REDIS_PORT": "6381"
                }
    
    def status_report(self):
        """Print status report for debugging."""
        env_label = self.environment.upper()
        print("\n" + "=" * 70)
        print(f"{env_label} DOCKER ENVIRONMENT STATUS")
        print("=" * 70)
        
        print(f"\n{env_label} Services:")
        self.manager.print_status(self.all_services)


def main():
    """CLI interface for Docker management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Docker Manager for Test and Dev environments")
    parser.add_argument("command", choices=[
        "start", "stop", "reset", "status", "cleanup", "urls"
    ])
    parser.add_argument("--env", choices=["test", "dev"], default="test",
                       help="Environment to manage (test or dev)")
    parser.add_argument("--services", nargs="*", help="Specific services")
    parser.add_argument("--force", action="store_true", help="Force cleanup")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout")
    
    args = parser.parse_args()
    
    manager = TestDockerManager(args.env)
    
    if args.command == "start":
        services = args.services or manager.core_services
        success = manager.ensure_services(services, args.timeout)
        sys.exit(0 if success else 1)
        
    elif args.command == "stop":
        success = manager.cleanup_environment(args.force)
        sys.exit(0 if success else 1)
        
    elif args.command == "reset":
        success = manager.reset_test_data(args.services)
        sys.exit(0 if success else 1)
        
    elif args.command == "status":
        manager.status_report()
        
    elif args.command == "cleanup":
        success = manager.cleanup_environment(force=True)
        sys.exit(0 if success else 1)
        
    elif args.command == "urls":
        urls = manager.get_service_urls()
        for key, value in urls.items():
            print(f"{key}={value}")


if __name__ == "__main__":
    main()