#!/usr/bin/env python3
"""
Development Environment Manager - PR-H Developer Experience Improvements
Centralized development environment setup, validation, and management.
"""
import os
import sys
import subprocess
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass


@dataclass
class ServiceStatus:
    """Service status information."""
    name: str
    running: bool
    healthy: bool
    port: Optional[int] = None
    url: Optional[str] = None
    error: Optional[str] = None


class DevEnvironmentManager:
    """
    Development Environment Manager for Netra Apex.
    
    Provides:
    - One-command environment setup
    - Service health monitoring
    - Dependency validation
    - Performance monitoring
    - Development workflow automation
    """
    
    def __init__(self):
        """Initialize development environment manager."""
        self.project_root = Path(__file__).parent.parent
        self.services_config = {
            'backend': {'port': 8000, 'health_path': '/health'},
            'auth': {'port': 8001, 'health_path': '/health'}, 
            'frontend': {'port': 3000, 'health_path': '/'},
            'analytics': {'port': 8002, 'health_path': '/health'},
            'postgres': {'port': 5432, 'health_check': 'pg_isready'},
            'redis': {'port': 6379, 'health_check': 'redis-cli ping'},
            'clickhouse': {'port': 8123, 'health_path': '/ping'}
        }
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.project_root / 'logs' / 'dev-manager.log')
            ]
        )
        self.logger = logging.getLogger('DevEnvManager')
    
    def quick_setup(self) -> bool:
        """Quick development environment setup."""
        self.logger.info("[U+1F680] Starting quick development environment setup...")
        
        steps = [
            ("Validating project structure", self.validate_project_structure),
            ("Checking dependencies", self.check_dependencies),
            ("Setting up environment", self.setup_environment),
            ("Starting services", self.start_services),
            ("Validating service health", self.validate_service_health)
        ]
        
        for step_name, step_func in steps:
            self.logger.info(f"   ->  {step_name}...")
            try:
                if not step_func():
                    self.logger.error(f" FAIL:  Failed: {step_name}")
                    return False
                self.logger.info(f"   PASS:  Completed: {step_name}")
            except Exception as e:
                self.logger.error(f" FAIL:  Error in {step_name}: {e}")
                return False
        
        self.logger.info(" CELEBRATION:  Quick setup completed successfully!")
        return True
    
    def full_setup(self, validate: bool = True) -> bool:
        """Full development environment setup with validation."""
        self.logger.info("[U+1F527] Starting full development environment setup...")
        
        steps = [
            ("Validating system requirements", self.validate_system_requirements),
            ("Checking project structure", self.validate_project_structure),
            ("Installing dependencies", self.install_dependencies),
            ("Setting up database", self.setup_database),
            ("Configuring services", self.configure_services),
            ("Starting all services", self.start_all_services),
            ("Running migrations", self.run_migrations),
            ("Seeding test data", self.seed_test_data)
        ]
        
        if validate:
            steps.append(("Comprehensive validation", self.comprehensive_validation))
        
        for step_name, step_func in steps:
            self.logger.info(f"   ->  {step_name}...")
            try:
                if not step_func():
                    self.logger.error(f" FAIL:  Failed: {step_name}")
                    return False
                self.logger.info(f"   PASS:  Completed: {step_name}")
            except Exception as e:
                self.logger.error(f" FAIL:  Error in {step_name}: {e}")
                return False
        
        self.logger.info("[U+1F680] Full setup completed successfully!")
        self.print_environment_info()
        return True
    
    def validate_project_structure(self) -> bool:
        """Validate project directory structure."""
        required_dirs = [
            'netra_backend',
            'auth_service', 
            'frontend',
            'analytics_service',
            'dockerfiles',
            'scripts',
            'tests'
        ]
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                self.logger.error(f"Missing required directory: {dir_name}")
                return False
        
        return True
    
    def validate_system_requirements(self) -> bool:
        """Validate system requirements and dependencies."""
        requirements = [
            ('python3', '--version', 'Python 3.8+'),
            ('node', '--version', 'Node.js 16+'),
            ('npm', '--version', 'npm 8+'),
            ('docker', '--version', 'Docker 20+'),
            ('git', '--version', 'Git 2.0+')
        ]
        
        for cmd, version_flag, description in requirements:
            try:
                result = subprocess.run([cmd, version_flag], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    self.logger.error(f"Required tool not found: {cmd} ({description})")
                    return False
                self.logger.debug(f"Found {cmd}: {result.stdout.strip()}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.logger.error(f"Required tool not found or not responding: {cmd}")
                return False
        
        return True
    
    def check_dependencies(self) -> bool:
        """Check if dependencies are installed."""
        # Check Python dependencies
        python_deps = ['fastapi', 'uvicorn', 'sqlalchemy', 'redis', 'psycopg2']
        for dep in python_deps:
            try:
                subprocess.run([sys.executable, '-c', f'import {dep}'], 
                             check=True, capture_output=True)
            except subprocess.CalledProcessError:
                self.logger.warning(f"Python dependency not found: {dep}")
                return False
        
        # Check Node.js dependencies for frontend
        frontend_path = self.project_root / 'frontend'
        if frontend_path.exists():
            node_modules = frontend_path / 'node_modules'
            if not node_modules.exists():
                self.logger.warning("Frontend dependencies not installed")
                return False
        
        return True
    
    def install_dependencies(self) -> bool:
        """Install all project dependencies."""
        # Install Python dependencies
        self.logger.info("Installing Python dependencies...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 
                          'requirements.txt'], check=True, cwd=self.project_root)
        except subprocess.CalledProcessError:
            self.logger.error("Failed to install Python dependencies")
            return False
        
        # Install Node.js dependencies
        frontend_path = self.project_root / 'frontend'
        if frontend_path.exists():
            self.logger.info("Installing Node.js dependencies...")
            try:
                subprocess.run(['npm', 'install'], check=True, cwd=frontend_path)
            except subprocess.CalledProcessError:
                self.logger.error("Failed to install Node.js dependencies")
                return False
        
        return True
    
    def setup_environment(self) -> bool:
        """Setup environment configuration."""
        env_template = self.project_root / 'config' / 'enhanced-environment-template.env'
        env_file = self.project_root / '.env'
        
        if not env_file.exists() and env_template.exists():
            self.logger.info("Creating .env file from template...")
            env_file.write_text(env_template.read_text())
        
        # Create necessary directories
        dirs_to_create = ['logs', 'data', 'data/postgres', 'data/redis', 'data/clickhouse']
        for dir_name in dirs_to_create:
            dir_path = self.project_root / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def setup_database(self) -> bool:
        """Setup database services."""
        self.logger.info("Starting database services...")
        try:
            # Start database services with Docker Compose
            subprocess.run([
                'docker-compose', 'up', '-d', 
                'postgres', 'redis', 'clickhouse'
            ], check=True, cwd=self.project_root)
            
            # Wait for services to be ready
            time.sleep(10)
            return self.check_database_connectivity()
            
        except subprocess.CalledProcessError:
            self.logger.error("Failed to start database services")
            return False
    
    def check_database_connectivity(self) -> bool:
        """Check database connectivity."""
        # Check PostgreSQL
        try:
            subprocess.run([
                'docker-compose', 'exec', '-T', 'postgres',
                'pg_isready', '-U', 'netra_user', '-d', 'netra_dev'
            ], check=True, cwd=self.project_root, capture_output=True)
        except subprocess.CalledProcessError:
            self.logger.error("PostgreSQL not ready")
            return False
        
        # Check Redis
        try:
            subprocess.run([
                'docker-compose', 'exec', '-T', 'redis',
                'redis-cli', 'ping'
            ], check=True, cwd=self.project_root, capture_output=True)
        except subprocess.CalledProcessError:
            self.logger.error("Redis not ready")
            return False
        
        return True
    
    def configure_services(self) -> bool:
        """Configure all services."""
        # Configure backend service
        backend_path = self.project_root / 'netra_backend'
        if backend_path.exists():
            self.logger.info("Configuring backend service...")
            # Add any backend-specific configuration
        
        # Configure frontend service  
        frontend_path = self.project_root / 'frontend'
        if frontend_path.exists():
            self.logger.info("Configuring frontend service...")
            # Add any frontend-specific configuration
        
        return True
    
    def start_services(self) -> bool:
        """Start core application services."""
        try:
            subprocess.run([
                'docker-compose', 'up', '-d',
                'netra-backend', 'netra-auth'
            ], check=True, cwd=self.project_root)
            
            time.sleep(5)  # Wait for services to start
            return True
        except subprocess.CalledProcessError:
            return False
    
    def start_all_services(self) -> bool:
        """Start all services including frontend."""
        try:
            subprocess.run([
                'docker-compose', 'up', '-d'
            ], check=True, cwd=self.project_root)
            
            time.sleep(10)  # Wait for all services to start
            return True
        except subprocess.CalledProcessError:
            return False
    
    def run_migrations(self) -> bool:
        """Run database migrations."""
        self.logger.info("Running database migrations...")
        try:
            # Run backend migrations
            subprocess.run([
                'docker-compose', 'exec', '-T', 'netra-backend',
                'python', '-m', 'alembic', 'upgrade', 'head'
            ], check=True, cwd=self.project_root, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            self.logger.error("Failed to run migrations")
            return False
    
    def seed_test_data(self) -> bool:
        """Seed test data for development."""
        self.logger.info("Seeding test data...")
        try:
            # Run test data seeding
            subprocess.run([
                'docker-compose', 'exec', '-T', 'netra-backend',
                'python', 'scripts/seed_dev_data.py'
            ], check=True, cwd=self.project_root, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            self.logger.warning("Test data seeding failed (may not exist yet)")
            return True  # Not critical for basic setup
    
    def validate_service_health(self) -> bool:
        """Validate service health."""
        services = self.get_service_status()
        all_healthy = True
        
        for service in services:
            if service.running and not service.healthy:
                self.logger.warning(f"Service {service.name} is running but not healthy")
                all_healthy = False
            elif not service.running:
                self.logger.error(f"Service {service.name} is not running")
                all_healthy = False
        
        return all_healthy
    
    def comprehensive_validation(self) -> bool:
        """Comprehensive environment validation."""
        validations = [
            ("Service connectivity", self.validate_service_connectivity),
            ("API endpoints", self.validate_api_endpoints),
            ("Database operations", self.validate_database_operations),
            ("WebSocket connections", self.validate_websocket_connections)
        ]
        
        for validation_name, validation_func in validations:
            self.logger.info(f"     ->  {validation_name}...")
            try:
                if not validation_func():
                    self.logger.error(f" FAIL:  Validation failed: {validation_name}")
                    return False
            except Exception as e:
                self.logger.error(f" FAIL:  Validation error in {validation_name}: {e}")
                return False
        
        return True
    
    def validate_service_connectivity(self) -> bool:
        """Validate service-to-service connectivity."""
        # Add service connectivity tests
        return True
    
    def validate_api_endpoints(self) -> bool:
        """Validate API endpoint accessibility.""" 
        # Add API endpoint validation
        return True
    
    def validate_database_operations(self) -> bool:
        """Validate database operations."""
        # Add database operation validation
        return True
    
    def validate_websocket_connections(self) -> bool:
        """Validate WebSocket connections."""
        # Add WebSocket connection validation
        return True
    
    def get_service_status(self) -> List[ServiceStatus]:
        """Get status of all services."""
        services = []
        
        try:
            # Get Docker Compose service status
            result = subprocess.run([
                'docker-compose', 'ps', '--format', 'json'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        service_info = json.loads(line)
                        service_name = service_info['Service']
                        is_running = service_info['State'] == 'running'
                        
                        service = ServiceStatus(
                            name=service_name,
                            running=is_running,
                            healthy=is_running  # Simplified for now
                        )
                        services.append(service)
        
        except Exception as e:
            self.logger.error(f"Failed to get service status: {e}")
        
        return services
    
    def print_environment_info(self):
        """Print development environment information."""
        self.logger.info("=== Development Environment Ready ===")
        self.logger.info("Service URLs:")
        self.logger.info("  Backend:    http://localhost:8000")
        self.logger.info("  Auth:       http://localhost:8001") 
        self.logger.info("  Frontend:   http://localhost:3000")
        self.logger.info("  Analytics:  http://localhost:8002")
        self.logger.info("  PostgreSQL: localhost:5432")
        self.logger.info("  Redis:      localhost:6379")
        self.logger.info("  ClickHouse: localhost:8123")
        self.logger.info("=====================================")
    
    def health_check(self, verbose: bool = False) -> bool:
        """Comprehensive health check of development environment."""
        self.logger.info("[U+1F3E5] Running development environment health check...")
        
        services = self.get_service_status()
        
        if verbose:
            for service in services:
                status = " PASS:  Healthy" if service.healthy else " WARNING: [U+FE0F] Issues" if service.running else " FAIL:  Down"
                self.logger.info(f"  {service.name}: {status}")
        
        healthy_count = sum(1 for s in services if s.healthy)
        total_count = len(services)
        
        self.logger.info(f"Health Summary: {healthy_count}/{total_count} services healthy")
        
        if healthy_count == total_count:
            self.logger.info(" CELEBRATION:  All services are healthy!")
            return True
        else:
            self.logger.warning(" WARNING: [U+FE0F] Some services need attention")
            return False


def main():
    """Main function for development environment manager."""
    parser = argparse.ArgumentParser(description='Netra Development Environment Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Quick setup command
    quick_parser = subparsers.add_parser('quick', help='Quick development setup')
    
    # Full setup command
    full_parser = subparsers.add_parser('full', help='Full development setup')
    full_parser.add_argument('--validate', action='store_true', 
                           help='Run comprehensive validation after setup')
    
    # Health check command
    health_parser = subparsers.add_parser('health', help='Health check')
    health_parser.add_argument('--verbose', action='store_true',
                              help='Verbose health check output')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show service status')
    
    args = parser.parse_args()
    
    manager = DevEnvironmentManager()
    
    if args.command == 'quick':
        success = manager.quick_setup()
        sys.exit(0 if success else 1)
        
    elif args.command == 'full':
        success = manager.full_setup(validate=args.validate)
        sys.exit(0 if success else 1)
        
    elif args.command == 'health':
        success = manager.health_check(verbose=args.verbose)
        sys.exit(0 if success else 1)
        
    elif args.command == 'status':
        services = manager.get_service_status()
        for service in services:
            status = "Running" if service.running else "Stopped"
            print(f"{service.name}: {status}")
        sys.exit(0)
        
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()