#!/usr/bin/env python3
"""
Hybrid Development Environment with Podman

Runs infrastructure services (PostgreSQL, Redis, ClickHouse) in Podman containers
and application services (Auth, Backend, Frontend) locally for easier development.

This approach solves Podman build issues on Windows while maintaining
a consistent development environment.
"""

import sys
import os
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HybridPodmanEnvironment:
    """Manager for hybrid Podman/local development environment."""
    
    def __init__(self):
        """Initialize hybrid environment."""
        self.project_root = Path(__file__).parent.parent
        self.compose_file = self.project_root / "podman-compose.yml"
        
        # Service ports (from podman-compose.yml)
        self.ports = {
            'postgres': 5433,
            'redis': 6380,
            'clickhouse_http': 8124,
            'clickhouse_tcp': 9001,
            'auth': 8081,
            'backend': 8000,
            'frontend': 3000
        }
        
    def setup_environment_variables(self):
        """Set up environment variables for local services to connect to Podman containers."""
        print("Setting up environment variables...")
        
        # Load from .env if exists
        env_file = self.project_root / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
        
        # Override with local development settings
        os.environ['ENVIRONMENT'] = 'development'
        os.environ['LOG_LEVEL'] = 'DEBUG'
        
        # Database connection to Podman container
        os.environ['POSTGRES_HOST'] = 'localhost'
        os.environ['POSTGRES_PORT'] = str(self.ports['postgres'])
        os.environ.setdefault('POSTGRES_USER', 'netra')
        os.environ.setdefault('POSTGRES_PASSWORD', 'netra123')
        os.environ.setdefault('POSTGRES_DB', 'netra_dev')
        
        # Redis connection to Podman container
        os.environ['REDIS_HOST'] = 'localhost'
        os.environ['REDIS_PORT'] = str(self.ports['redis'])
        
        # ClickHouse connection to Podman container
        os.environ['CLICKHOUSE_HOST'] = 'localhost'
        os.environ['CLICKHOUSE_PORT'] = str(self.ports['clickhouse_tcp'])
        os.environ['CLICKHOUSE_HTTP_PORT'] = str(self.ports['clickhouse_http'])
        os.environ.setdefault('CLICKHOUSE_USER', 'netra')
        os.environ.setdefault('CLICKHOUSE_PASSWORD', 'netra123')
        os.environ.setdefault('CLICKHOUSE_DB', 'netra_analytics')
        
        # Auth service (will run locally)
        os.environ['AUTH_SERVICE_URL'] = f'http://localhost:{self.ports["auth"]}'
        
        # Service secrets
        os.environ.setdefault('JWT_SECRET_KEY', 'dev-jwt-secret-key-must-be-at-least-32-characters')
        os.environ.setdefault('SERVICE_SECRET', 'test-secret-for-local-development-only-32chars')
        os.environ.setdefault('FERNET_KEY', 'iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=')
        os.environ.setdefault('SECRET_KEY', 'dev-secret-key-for-development')
        
        print("[OK] Environment variables configured")
    
    async def start_infrastructure(self) -> bool:
        """Start infrastructure services with Podman."""
        print("\nStarting infrastructure services with Podman...")
        
        try:
            # Start only infrastructure services
            services = ['dev-postgres', 'dev-redis', 'dev-clickhouse']
            
            for service in services:
                print(f"   Starting {service}...")
                result = subprocess.run(
                    ['podman-compose', '-f', str(self.compose_file), 'up', '-d', '--no-build', service],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0 and "already in use" not in result.stderr:
                    logger.error(f"Failed to start {service}: {result.stderr}")
                    # Continue anyway - service might already be running
            
            # Wait for services to be healthy
            print("\nWaiting for infrastructure services to be healthy...")
            await asyncio.sleep(10)
            
            # Check service health
            healthy = await self.check_infrastructure_health()
            if healthy:
                print("[OK] All infrastructure services are healthy!")
                return True
            else:
                print("[WARNING] Some services may not be fully ready")
                return True  # Continue anyway
                
        except Exception as e:
            print(f"[ERROR] Error starting infrastructure: {e}")
            return False
    
    async def check_infrastructure_health(self) -> bool:
        """Check if infrastructure services are healthy."""
        all_healthy = True
        
        # Check PostgreSQL
        try:
            result = subprocess.run(
                ['podman', 'exec', 'netra-core-generation-1_dev-postgres_1', 
                 'pg_isready', '-U', 'netra'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print("   [OK] PostgreSQL is healthy")
            else:
                print("   [WARNING] PostgreSQL not ready")
                all_healthy = False
        except:
            print("   [WARNING] PostgreSQL check failed")
            all_healthy = False
        
        # Check Redis
        try:
            result = subprocess.run(
                ['podman', 'exec', 'netra-core-generation-1_dev-redis_1',
                 'redis-cli', 'ping'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print("   [OK] Redis is healthy")
            else:
                print("   [WARNING] Redis not ready")
                all_healthy = False
        except:
            print("   [WARNING] Redis check failed")
            all_healthy = False
        
        # Check ClickHouse
        try:
            result = subprocess.run(
                ['podman', 'exec', 'netra-core-generation-1_dev-clickhouse_1',
                 'clickhouse-client', '--query', 'SELECT 1'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print("   [OK] ClickHouse is healthy")
            else:
                print("   [WARNING] ClickHouse not ready")
                all_healthy = False
        except:
            print("   [WARNING] ClickHouse check failed")
            all_healthy = False
        
        return all_healthy
    
    def display_instructions(self):
        """Display instructions for running application services locally."""
        print("\n" + "="*60)
        print("Hybrid Development Environment Ready!")
        print("="*60)
        print("\nInfrastructure Services (Running in Podman):")
        print(f"  PostgreSQL:  localhost:{self.ports['postgres']} (user: netra, db: netra_dev)")
        print(f"  Redis:       localhost:{self.ports['redis']}")
        print(f"  ClickHouse:  http://localhost:{self.ports['clickhouse_http']}")
        
        print("\nTo start application services locally:")
        print("\n1. Auth Service (Terminal 1):")
        print("   cd auth_service")
        print("   python -m uvicorn auth_service.app:app --reload --port 8081")
        
        print("\n2. Backend Service (Terminal 2):")
        print("   cd netra_backend")
        print("   python -m uvicorn netra_backend.app:app --reload --port 8000")
        
        print("\n3. Frontend Service (Terminal 3):")
        print("   cd frontend")
        print("   npm install  # if not done already")
        print("   npm run dev")
        
        print("\nEnvironment variables are already configured!")
        print("   Just run the commands above in separate terminals.")
        
        print("\nTo stop infrastructure services:")
        print(f"   podman-compose -f {self.compose_file} down")
        
        print("="*60)
    
    async def stop_infrastructure(self) -> bool:
        """Stop infrastructure services."""
        print("\nStopping infrastructure services...")
        
        try:
            result = subprocess.run(
                ['podman-compose', '-f', str(self.compose_file), 'down'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("[OK] Infrastructure services stopped")
                return True
            else:
                print(f"[WARNING] Some issues stopping services: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error stopping services: {e}")
            return False
    
    def check_status(self):
        """Check status of Podman containers."""
        print("\nContainer Status:")
        print("-" * 60)
        
        try:
            result = subprocess.run(
                ["podman", "ps", "--format", 
                 "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("No containers running")
                
        except Exception as e:
            print(f"Error checking status: {e}")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manage hybrid Podman/local development environment"
    )
    
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status"],
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    # Initialize environment
    env = HybridPodmanEnvironment()
    
    if args.action == "start":
        env.setup_environment_variables()
        success = await env.start_infrastructure()
        if success:
            env.display_instructions()
        sys.exit(0 if success else 1)
        
    elif args.action == "stop":
        success = await env.stop_infrastructure()
        sys.exit(0 if success else 1)
        
    elif args.action == "restart":
        print("Restarting infrastructure services...")
        await env.stop_infrastructure()
        await asyncio.sleep(2)
        env.setup_environment_variables()
        success = await env.start_infrastructure()
        if success:
            env.display_instructions()
        sys.exit(0 if success else 1)
        
    elif args.action == "status":
        env.check_status()
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())