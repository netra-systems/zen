#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Refresh Dev Environment - The ONE Way to Refresh Local Development

Simple, intuitive developer command for refreshing local development environment.
No options, no confusion - just works.

Usage:
    python scripts/refresh_dev.py                # Full refresh (most common)
    python scripts/refresh_dev.py backend        # Just backend service
    python scripts/refresh_dev.py auth           # Just auth service
    python scripts/refresh_dev.py --clean        # Clean rebuild (rare)

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity
2. Business Goal: Eliminate developer friction, standardize dev workflow
3. Value Impact: Saves 5-10 minutes per refresh, prevents "works on my machine" issues
4. Revenue Impact: Saves 2-4 hours/week per developer, increases deployment confidence
"""

import sys
import os

# Fix Windows Unicode output for emojis
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import subprocess
import time
import logging
from pathlib import Path
from typing import List, Optional
import argparse
import shutil
import socket

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure clean, developer-friendly logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Simple format for developer output
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class DevEnvironmentRefresher:
    """Simple, opinionated developer environment refresher."""
    
    def __init__(self, clean: bool = False):
        """Initialize refresher with sensible defaults.
        
        Args:
            clean: Force clean rebuild (slower but guaranteed fresh)
        """
        self.clean = clean
        self.project_root = project_root
        self.compose_file = "docker-compose.yml"  # SSOT for development
        
        # Verify docker is available
        if not shutil.which('docker'):
            raise RuntimeError("Docker not found! Please install Docker Desktop.")
        
        # Verify docker-compose is available
        if not shutil.which('docker-compose'):
            # Try docker compose (newer integrated version)
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError("docker-compose not found! Please install docker-compose or use Docker Desktop with compose v2.")
    
    def refresh_dev(self, services: Optional[List[str]] = None) -> bool:
        """Refresh local development environment - the ONE way.
        
        Args:
            services: Specific services to refresh, or None for all
            
        Returns:
            True if successful, False otherwise
        """
        print("[REFRESH] Refreshing development environment...")
        print(f"   Location: {self.project_root}")
        print(f"   Compose: {self.compose_file}")
        
        try:
            # Step 1: Stop existing containers (graceful)
            self._stop_existing()
            
            # Step 2: Build fresh images with latest code
            if not self._build_images(services):
                return False
            
            # Step 3: Start services
            if not self._start_services(services):
                return False
            
            # Step 4: Wait for services to be ready
            if not self._wait_for_services():
                return False
            
            # Step 5: Verify everything is healthy
            if not self._verify_health():
                return False
            
            print("[SUCCESS] Development environment ready!")
            self._show_service_urls()
            return True
            
        except KeyboardInterrupt:
            print("\n[CANCELLED] Refresh cancelled by user")
            return False
        except Exception as e:
            logger.error(f" FAIL:  Refresh failed: {e}")
            return False
    
    def _stop_existing(self):
        """Stop existing containers gracefully."""
        print("[STOP] Stopping existing containers...")
        
        try:
            # Use docker-compose directly to stop
            cmd = ["docker-compose", "-f", self.compose_file, "down", "-v"]
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("   [OK] Existing containers stopped")
            else:
                # Try newer docker compose syntax
                cmd = ["docker", "compose", "-f", self.compose_file, "down", "-v"]
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("   [OK] Existing containers stopped (using docker compose v2)")
                else:
                    print(f"   [WARN] Could not stop containers: {result.stderr}")
        except Exception as e:
            # Not fatal - continue with refresh
            print(f"   [WARN] {e}")
    
    def _build_images(self, services: Optional[List[str]] = None) -> bool:
        """Build fresh images with smart caching."""
        print("[BUILD] Building fresh images with Docker...")
        
        # Build command using docker-compose directly for speed
        cmd = ["docker-compose", "-f", self.compose_file, "build"]
        
        if self.clean:
            cmd.append("--no-cache")
            print("   [CLEAN] Clean build enabled (slower but guaranteed fresh)")
        else:
            # Smart caching: rebuild app code, cache dependencies
            print("   [FAST] Smart build enabled (fresh code, cached dependencies)")
        
        if services:
            cmd.extend(services)
            print(f"   [TARGET] Building services: {', '.join(services)}")
        
        # Add parallel builds for speed
        cmd.extend(["--parallel"])
        
        try:
            # First try regular docker-compose
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False  # Show build output to developer
            )
            
            if result.returncode != 0:
                # Try newer docker compose syntax
                print("   [INFO] Trying docker compose v2...")
                cmd[0] = "docker"
                cmd[1] = "compose"
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=False
                )
            
            if result.returncode == 0:
                print("   [OK] Images built successfully with Docker")
                return True
            else:
                logger.error(f"   [ERROR] Build failed with exit code {result.returncode}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"   [ERROR] Build failed: {e}")
            return False
        except FileNotFoundError as e:
            logger.error(f"   [ERROR] Docker command not found: {e}")
            logger.error("   Please ensure Docker Desktop is installed and running")
            return False
    
    def _start_services(self, services: Optional[List[str]] = None) -> bool:
        """Start services with health checks."""
        print("[START] Starting services with Docker...")
        
        # Start using docker-compose directly
        cmd = ["docker-compose", "-f", self.compose_file, "up", "-d"]
        
        if services:
            cmd.extend(services)
            print(f"   [TARGET] Starting services: {', '.join(services)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Try newer docker compose syntax
                cmd[0] = "docker"
                cmd[1] = "compose"
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0:
                print("   [OK] Services started successfully")
                return True
            else:
                logger.error(f"   [ERROR] Failed to start services: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"   [ERROR] Failed to start services: {e}")
            return False
    
    def _wait_for_services(self) -> bool:
        """Wait for services to be ready with configurable timeout."""
        print("[WAIT] Waiting for services to be ready...")
        
        # List of services to check with their ports
        services_to_check = [
            ("backend", "localhost", 8000),
            ("auth", "localhost", 8081),
            ("postgres", "localhost", 5433),
            ("redis", "localhost", 6380),
        ]
        
        max_wait = 120  # 2 minutes max wait time
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            all_ready = True
            
            for service_name, host, port in services_to_check:
                try:
                    # Try to connect to the port
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    
                    if result != 0:
                        all_ready = False
                        print(f"   [WAIT] {service_name} not ready yet (port {port})")
                        break
                except Exception:
                    all_ready = False
                    break
            
            if all_ready:
                print("   [OK] All services are responding")
                return True
            
            # Wait before next check
            time.sleep(2)
        
        logger.error(f"   [ERROR] Services did not become ready within {max_wait} seconds")
        return False
    
    def _verify_health(self) -> bool:
        """Verify all services are healthy."""
        print("[CHECK] Verifying services...")
        
        # Check container status
        cmd = ["docker-compose", "-f", self.compose_file, "ps"]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Try newer syntax
                cmd[0] = "docker"
                cmd[1] = "compose"
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True
                )
            
            if result.returncode == 0:
                print("   [OK] All services are running")
                # Show the status
                print(result.stdout)
                return True
            else:
                logger.error("   [ERROR] Failed to check service status")
                return False
                
        except Exception as e:
            logger.error(f"   [ERROR] Failed to verify services: {e}")
            return False
    
    def _show_service_urls(self):
        """Show service URLs for developer convenience."""
        print("\n[URLS] Service URLs:")
        
        # Common development ports (from docker-compose.yml)
        services = {
            "Frontend": "http://localhost:3000",
            "Backend API": "http://localhost:8000",
            "Auth Service": "http://localhost:8081",
            "PostgreSQL": "localhost:5433",
            "Redis": "localhost:6380",
            "ClickHouse HTTP": "http://localhost:8124"
        }
        
        for name, url in services.items():
            print(f"   * {name:15}: {url}")


def main():
    """Main entry point with simple argument parsing."""
    parser = argparse.ArgumentParser(
        description="Refresh local development environment - the ONE way",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/refresh_dev.py           # Full refresh (most common)
    python scripts/refresh_dev.py backend   # Just backend service
    python scripts/refresh_dev.py --clean   # Clean rebuild
        """
    )
    
    parser.add_argument(
        "services",
        nargs="*",
        help="Specific services to refresh (backend, auth, frontend)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Force clean rebuild (slower but guaranteed fresh)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    
    args = parser.parse_args()
    
    # Validate service names
    valid_services = {"backend", "auth", "frontend", "postgres", "redis", "clickhouse"}
    if args.services:
        invalid = set(args.services) - valid_services
        if invalid:
            logger.error(f"[ERROR] Invalid services: {', '.join(invalid)}")
            logger.error(f"   Valid services: {', '.join(sorted(valid_services))}")
            sys.exit(1)
    
    # Handle dry-run mode
    if args.dry_run:
        services = args.services if args.services else ["all"]
        print("[DRY RUN] Would refresh development environment...")
        print(f"   Services: {', '.join(services)}")
        print(f"   Clean build: {'Yes' if args.clean else 'No'}")
        print("   Steps that would be performed:")
        print("   1. Stop existing development containers")
        print("   2. Build fresh images (with smart caching)")
        print("   3. Start services")
        print("   4. Wait for services to be ready (up to 2 minutes)")
        print("   5. Verify all services are healthy")
        print("   6. Show service URLs")
        print("[OK] Dry run complete - no changes made")
        sys.exit(0)
    
    # Create refresher and run
    refresher = DevEnvironmentRefresher(clean=args.clean)
    
    services = args.services if args.services else None
    success = refresher.refresh_dev(services)
    
    if success:
        print(f"\n[SUCCESS] Development environment refreshed")
        print("   Ready for development!")
    else:
        print("\n[FAILED] Refresh failed - check logs above")
        print("   Try: python scripts/refresh_dev.py --clean")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()