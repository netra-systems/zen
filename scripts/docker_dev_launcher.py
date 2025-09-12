from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Docker-based Development Launcher for Netra Platform

This script provides a Docker-based alternative to the standard dev launcher,
offering containerized isolation, consistency across environments, and simplified setup.
"""

import argparse
import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from typing import List, Dict, Optional
import json

# Fix Unicode output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.resolve()
if parent_dir not in sys.path:
    sys.path.insert(0, str(parent_dir))


class DockerDevLauncher:
    """Docker-based development environment launcher."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.project_root = Path.cwd()
        self.compose_file = "docker-compose.dev.yml"
        self.env_file = ".env"
        self.running = False
        
    def check_docker(self) -> bool:
        """Check if Docker and Docker Compose are available."""
        try:
            # Check Docker
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                print("[ERROR] Docker is not installed or not in PATH")
                return False
                
            # Check Docker Compose
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                # Try legacy docker-compose command
                result = subprocess.run(
                    ["docker-compose", "--version"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode != 0:
                    print("[ERROR] Docker Compose is not installed or not in PATH")
                    return False
                    
            print("[OK] Docker and Docker Compose are available")
            return True
            
        except FileNotFoundError:
            print("[ERROR] Docker or Docker Compose not found")
            return False
            
    def prepare_environment(self):
        """Prepare environment variables for Docker Compose."""
        print("[INFO] Preparing environment configuration...")
        
        # Load existing .env if it exists
        env_vars = {}
        env_path = self.project_root / self.env_file
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        # Set default values if not present
        defaults = {
            'ENVIRONMENT': 'development',
            'POSTGRES_USER': 'netra',
            'POSTGRES_PASSWORD': 'netra123',
            'POSTGRES_DB': 'netra_db',
            'POSTGRES_PORT': '5432',
            'REDIS_PORT': '6379',
            'CLICKHOUSE_USER': 'netra',
            'CLICKHOUSE_PASSWORD': 'netra123',
            'CLICKHOUSE_DB': 'netra_analytics',
            'CLICKHOUSE_HTTP_PORT': '8123',
            'CLICKHOUSE_TCP_PORT': '9000',
            'BACKEND_PORT': str(self.config.get('backend_port', 8000)),
            'FRONTEND_PORT': str(self.config.get('frontend_port', 3000)),
            'AUTH_PORT': '8081',
            'JWT_SECRET_KEY': 'dev-secret-key-change-in-production',
        }
        
        for key, default_value in defaults.items():
            if key not in env_vars:
                env_vars[key] = default_value
                
        # Apply config overrides
        if self.config.get('backend_port'):
            env_vars['BACKEND_PORT'] = str(self.config['backend_port'])
        if self.config.get('frontend_port'):
            env_vars['FRONTEND_PORT'] = str(self.config['frontend_port'])
            
        # Export to environment
        for key, value in env_vars.items():
            os.environ[key] = value
            
        print(f"    ->  Backend port: {env_vars['BACKEND_PORT']}")
        print(f"    ->  Frontend port: {env_vars['FRONTEND_PORT']}")
        print(f"    ->  Auth port: {env_vars['AUTH_PORT']}")
        
    def create_db_init_scripts(self):
        """Create database initialization scripts if they don't exist."""
        scripts_dir = self.project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # PostgreSQL init script
        postgres_init = scripts_dir / "init_db.sql"
        if not postgres_init.exists():
            postgres_init.write_text("""-- Initialize Netra Database
CREATE SCHEMA IF NOT EXISTS public;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant permissions
GRANT ALL ON SCHEMA public TO netra;
GRANT ALL ON ALL TABLES IN SCHEMA public TO netra;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO netra;

-- Initial setup complete
SELECT 'Database initialized successfully' as status;
""", encoding='utf-8')
            print("    ->  Created PostgreSQL initialization script")
            
        # ClickHouse init script (optional)
        clickhouse_init = scripts_dir / "init_clickhouse.sql"
        if not clickhouse_init.exists():
            clickhouse_init.write_text("""-- Initialize ClickHouse Analytics Database
CREATE DATABASE IF NOT EXISTS netra_analytics;

USE netra_analytics;

-- Create tables for analytics
CREATE TABLE IF NOT EXISTS events (
    timestamp DateTime,
    event_type String,
    user_id String,
    session_id String,
    data String
) ENGINE = MergeTree()
ORDER BY (timestamp, event_type, user_id);

SELECT 'ClickHouse initialized successfully' as status;
""", encoding='utf-8')
            print("    ->  Created ClickHouse initialization script")
            
        # Wait for DB script
        wait_script = scripts_dir / "wait_for_db.py"
        if not wait_script.exists():
            wait_script.write_text("""#!/usr/bin/env python3
import os
import sys
import time
import psycopg2
from psycopg2 import OperationalError

def wait_for_db(max_retries=30, delay=2):
    \"\"\"Wait for PostgreSQL to be ready.\"\"\"
    db_url = os.environ.get('DATABASE_URL', '')
    
    if not db_url:
        # Build from components
        host = os.environ.get('POSTGRES_HOST', 'localhost')
        port = os.environ.get('POSTGRES_PORT', '5432')
        user = os.environ.get('POSTGRES_USER', 'netra')
        password = os.environ.get('POSTGRES_PASSWORD', 'netra123')
        database = os.environ.get('POSTGRES_DB', 'netra_db')
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            print("[OK] Database is ready!")
            return True
        except OperationalError as e:
            if i < max_retries - 1:
                print(f"[WAIT] Waiting for database... ({i+1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"[ERROR] Database connection failed after {max_retries} attempts")
                print(f"   Error: {e}")
                return False
    return False

if __name__ == "__main__":
    success = wait_for_db()
    sys.exit(0 if success else 1)
""", encoding='utf-8')
            print("    ->  Created database wait script")
            
    def build_services(self, services: Optional[List[str]] = None):
        """Build Docker images for services."""
        print("[INFO] Building Docker images...")
        
        cmd = ["docker", "compose", "-f", self.compose_file, "build"]
        if services:
            cmd.extend(services)
            
        if self.config.get('no_cache'):
            cmd.append("--no-cache")
            
        result = subprocess.run(cmd, cwd=self.project_root)
        if result.returncode != 0:
            print("[ERROR] Failed to build Docker images")
            return False
            
        print("[OK] Docker images built successfully")
        return True
        
    def start_services(self):
        """Start all services using Docker Compose."""
        print("[INFO] Starting services...")
        
        # Prepare the command
        cmd = ["docker", "compose", "-f", self.compose_file, "up"]
        
        if not self.config.get('verbose'):
            cmd.append("-d")  # Detached mode for cleaner output
            
        # Add profiles if needed
        profiles = []
        if self.config.get('enable_clickhouse'):
            profiles.append('analytics')
            
        for profile in profiles:
            cmd.extend(["--profile", profile])
            
        # Start services
        if self.config.get('verbose'):
            # Run in foreground with full output
            process = subprocess.Popen(cmd, cwd=self.project_root)
            self.running = True
            
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n[INFO] Stopping services...")
                self.stop_services()
                
        else:
            # Run in background
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            if result.returncode != 0:
                print("[ERROR] Failed to start services")
                print(result.stderr)
                return False
                
            self.running = True
            print("[OK] All services started successfully")
            
            # Show service URLs
            self.show_service_info()
            
            # Follow logs if not in silent mode
            if not self.config.get('silent'):
                print("\n[INFO] Following service logs (Ctrl+C to stop)...")
                self.follow_logs()
                
        return True
        
    def follow_logs(self, services: Optional[List[str]] = None):
        """Follow logs from Docker Compose services."""
        cmd = ["docker", "compose", "-f", self.compose_file, "logs", "-f"]
        if services:
            cmd.extend(services)
            
        try:
            subprocess.run(cmd, cwd=self.project_root)
        except KeyboardInterrupt:
            print("\n[INFO] Stopped following logs")
            
    def show_service_info(self):
        """Display information about running services."""
        print("\n" + "="*60)
        print("Service URLs:")
        print("="*60)
        
        backend_port = os.environ.get('BACKEND_PORT', '8000')
        frontend_port = os.environ.get('FRONTEND_PORT', '3000')
        auth_port = os.environ.get('AUTH_PORT', '8081')
        
        print(f"   Frontend:    http://localhost:{frontend_port}")
        print(f"   Backend API: http://localhost:{backend_port}")
        print(f"   Auth API:    http://localhost:{auth_port}")
        print(f"   PostgreSQL:  localhost:{os.environ.get('POSTGRES_PORT', '5432')}")
        print(f"   Redis:       localhost:{os.environ.get('REDIS_PORT', '6379')}")
        
        if self.config.get('enable_clickhouse'):
            print(f"   ClickHouse:  http://localhost:{os.environ.get('CLICKHOUSE_HTTP_PORT', '8123')}")
            
        print("\n" + "="*60)
        print("Useful commands:")
        print("   View logs:        docker compose -f docker-compose.dev.yml logs -f [service]")
        print("   Restart service:  docker compose -f docker-compose.dev.yml restart [service]")
        print("   Stop all:         docker compose -f docker-compose.dev.yml down")
        print("   Clean volumes:    docker compose -f docker-compose.dev.yml down -v")
        print("="*60)
        
    def stop_services(self):
        """Stop all Docker Compose services."""
        if not self.running:
            return
            
        print("[INFO] Stopping services...")
        cmd = ["docker", "compose", "-f", self.compose_file, "down"]
        
        if self.config.get('remove_volumes'):
            cmd.append("-v")
            
        subprocess.run(cmd, cwd=self.project_root)
        self.running = False
        print("[OK] All services stopped")
        
    def cleanup(self):
        """Clean up Docker resources."""
        print("[INFO] Cleaning up Docker resources...")
        
        # Stop services
        self.stop_services()
        
        # Remove volumes if requested
        if self.config.get('clean_volumes'):
            print("    ->  Removing volumes...")
            subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "down", "-v"],
                cwd=self.project_root
            )
            
        # Prune if requested
        if self.config.get('prune'):
            print("    ->  Pruning unused resources...")
            subprocess.run(["docker", "system", "prune", "-f"])
            
        print("[OK] Cleanup completed")
        
    def run(self):
        """Main execution flow."""
        print("[NETRA] Docker Development Environment")
        print("="*60)
        
        # Check Docker availability
        if not self.check_docker():
            print("\n[INFO] Please install Docker Desktop from: https://www.docker.com/products/docker-desktop")
            return 1
            
        # Prepare environment
        self.prepare_environment()
        
        # Create initialization scripts
        self.create_db_init_scripts()
        
        # Build images if requested or first time
        if self.config.get('build') or not self.images_exist():
            if not self.build_services():
                return 1
                
        # Start services
        if not self.start_services():
            return 1
            
        return 0
        
    def images_exist(self) -> bool:
        """Check if Docker images already exist."""
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "ps", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            return len(result.stdout.strip()) > 0
        except:
            return False


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Docker-based Netra Development Environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python scripts/docker_dev_launcher.py              # Start with defaults
  python scripts/docker_dev_launcher.py --build      # Rebuild images
  python scripts/docker_dev_launcher.py --verbose    # Show all logs
  python scripts/docker_dev_launcher.py --cleanup    # Stop and clean up
        """
    )
    
    # Port configuration
    parser.add_argument(
        "--backend-port",
        type=int,
        default=8000,
        help="Backend port (default: 8000)"
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=3000,
        help="Frontend port (default: 3000)"
    )
    
    # Build options
    parser.add_argument(
        "--build",
        action="store_true",
        help="Force rebuild of Docker images"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Build without cache"
    )
    
    # Service options
    parser.add_argument(
        "--enable-clickhouse",
        action="store_true",
        help="Enable ClickHouse analytics service"
    )
    
    # Output options
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Minimal output"
    )
    
    # Cleanup options
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Stop services and exit"
    )
    parser.add_argument(
        "--clean-volumes",
        action="store_true",
        help="Remove volumes when stopping"
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Prune unused Docker resources"
    )
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Convert args to config dict
    config = vars(args)
    
    # Handle cleanup mode
    if args.cleanup:
        launcher = DockerDevLauncher(config)
        launcher.cleanup()
        return 0
        
    # Create and run launcher
    launcher = DockerDevLauncher(config)
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        print("\n[INFO] Received shutdown signal")
        launcher.stop_services()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the launcher
    exit_code = launcher.run()
    
    if exit_code != 0:
        print("\n[ERROR] Failed to start Docker development environment")
        print("   Check the logs above for details")
        
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
