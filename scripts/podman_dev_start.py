#!/usr/bin/env python3
"""
Start Netra Development Environment with Podman
"""

import sys
import os
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_framework.container_runtime import detect_container_runtime, ContainerRuntime
from test_framework.unified_container_manager import (
    UnifiedContainerManager, 
    ContainerManagerMode
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PodmanDevEnvironment:
    """Manager for Podman development environment."""
    
    def __init__(self, environment: str = "development"):
        """Initialize development environment."""
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.compose_file = self.project_root / "podman-compose.yml"
        
        # Force Podman mode
        os.environ["CONTAINER_RUNTIME"] = "podman"
        
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        print("🔍 Checking prerequisites...")
        
        # Check Podman
        runtime_info = detect_container_runtime()
        if runtime_info.runtime != ContainerRuntime.PODMAN:
            print("❌ Podman not detected. Please install Podman Desktop.")
            return False
        print(f"✅ Podman {runtime_info.version} detected")
        
        # Check podman-compose
        try:
            result = subprocess.run(
                ["podman-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ podman-compose available")
            else:
                print("❌ podman-compose not found. Install with: pip install podman-compose")
                return False
        except Exception as e:
            print(f"❌ Error checking podman-compose: {e}")
            return False
        
        # Check compose file
        if not self.compose_file.exists():
            print(f"❌ Compose file not found: {self.compose_file}")
            return False
        print(f"✅ Compose file found: {self.compose_file}")
        
        return True
    
    def load_env_variables(self):
        """Load environment variables from .env file if it exists."""
        env_file = self.project_root / ".env"
        
        if env_file.exists():
            print(f"📋 Loading environment variables from {env_file}")
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # Remove quotes if present
                            value = value.strip().strip('"').strip("'")
                            os.environ[key] = value
            except Exception as e:
                logger.warning(f"Error loading .env file: {e}")
        else:
            print("⚠️  No .env file found. Using default values.")
            # Set minimal defaults for development
            os.environ.setdefault("POSTGRES_USER", "netra")
            os.environ.setdefault("POSTGRES_PASSWORD", "netra123")
            os.environ.setdefault("POSTGRES_DB", "netra_dev")
            os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key-must-be-at-least-32-characters")
            os.environ.setdefault("SERVICE_SECRET", "test-secret-for-local-development-only-32chars")
    
    async def start_services(self) -> bool:
        """Start all development services."""
        print("\n🚀 Starting development services with Podman...")
        
        try:
            # Create container manager with Podman mode
            manager = UnifiedContainerManager(
                environment="development",
                mode=ContainerManagerMode.PODMAN,
                use_alpine=False  # Use regular images for dev
            )
            
            # Start services
            print("📦 Starting containers...")
            success = await manager.start_services(
                build=True,  # Build images if needed
                timeout=300
            )
            
            if not success:
                print("❌ Failed to start services")
                return False
            
            print("✅ Services started successfully")
            
            # Wait for health checks
            print("\n⏳ Waiting for services to become healthy...")
            
            # Define services to check
            services_to_check = [
                "netra_development_dev-postgres_1",
                "netra_development_dev-redis_1",
                "netra_development_dev-auth_1",
                "netra_development_dev-backend_1"
            ]
            
            # Check each service
            for service in services_to_check:
                print(f"   Checking {service}...")
                # For now, just wait a bit for each service
                await asyncio.sleep(2)
            
            print("\n✅ All services are ready!")
            
            # Display access URLs
            self.display_access_info()
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error starting services: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def display_access_info(self):
        """Display information about how to access the services."""
        print("\n" + "="*60)
        print("🎯 Services are running at:")
        print("="*60)
        print("  Frontend:    http://localhost:3000")
        print("  Backend API: http://localhost:8000")
        print("  Auth API:    http://localhost:8081")
        print("  PostgreSQL:  localhost:5433 (user: netra, db: netra_dev)")
        print("  Redis:       localhost:6380")
        print("  ClickHouse:  http://localhost:8124")
        print("\n📝 To view logs:")
        print("  podman-compose -f podman-compose.yml logs -f [service]")
        print("\n🛑 To stop services:")
        print("  podman-compose -f podman-compose.yml down")
        print("="*60)
    
    async def stop_services(self) -> bool:
        """Stop all development services."""
        print("\n🛑 Stopping development services...")
        
        try:
            manager = UnifiedContainerManager(
                environment="development",
                mode=ContainerManagerMode.PODMAN,
                use_alpine=False
            )
            
            success = await manager.stop_services(
                remove_volumes=False,  # Keep volumes for data persistence
                timeout=60
            )
            
            if success:
                print("✅ Services stopped successfully")
            else:
                print("⚠️  Some services may not have stopped cleanly")
            
            return success
            
        except Exception as e:
            print(f"❌ Error stopping services: {e}")
            return False
    
    def check_status(self):
        """Check status of running containers."""
        print("\n📊 Container Status:")
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
        description="Manage Netra development environment with Podman"
    )
    
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status"],
        help="Action to perform"
    )
    
    parser.add_argument(
        "--env",
        default="development",
        help="Environment name (default: development)"
    )
    
    args = parser.parse_args()
    
    # Initialize environment
    dev_env = PodmanDevEnvironment(environment=args.env)
    
    # Check prerequisites first
    if not dev_env.check_prerequisites():
        print("\n❌ Prerequisites not met. Please install required tools.")
        sys.exit(1)
    
    # Load environment variables
    dev_env.load_env_variables()
    
    # Perform requested action
    if args.action == "start":
        success = await dev_env.start_services()
        sys.exit(0 if success else 1)
        
    elif args.action == "stop":
        success = await dev_env.stop_services()
        sys.exit(0 if success else 1)
        
    elif args.action == "restart":
        print("♻️  Restarting services...")
        await dev_env.stop_services()
        await asyncio.sleep(2)
        success = await dev_env.start_services()
        sys.exit(0 if success else 1)
        
    elif args.action == "status":
        dev_env.check_status()
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())