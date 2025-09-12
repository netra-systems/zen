#!/usr/bin/env python3
"""
Real Docker Services Audit Script

This script provides comprehensive auditing of Docker Compose services
to identify issues with service spawning, configuration conflicts, and health status.
"""

import subprocess
import json
import sys
import time
import requests
import psycopg2
import redis
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceCheck:
    name: str
    container_name: str
    expected_port: int
    health_url: Optional[str] = None
    service_type: str = "web"  # web, database, cache, queue
    
    
@dataclass
class ServiceStatus:
    name: str
    container_status: str
    health_status: str
    port_accessible: bool
    service_responsive: bool
    errors: List[str]
    warnings: List[str]


class DockerServicesAuditor:
    """Comprehensive Docker services auditor"""
    
    def __init__(self):
        self.dev_services = {
            'dev-postgres': ServiceCheck('dev-postgres', 'netra-dev-postgres', 5433, service_type='database'),
            'dev-redis': ServiceCheck('dev-redis', 'netra-dev-redis', 6380, service_type='cache'),
            'dev-clickhouse': ServiceCheck('dev-clickhouse', 'netra-dev-clickhouse', 8124, 'http://localhost:8124/ping', service_type='database'),
            'dev-auth': ServiceCheck('dev-auth', 'netra-dev-auth', 8081, 'http://localhost:8081/health', service_type='web'),
            'dev-analytics': ServiceCheck('dev-analytics', 'netra-dev-analytics', 8090, 'http://localhost:8090/health', service_type='web'),
            'dev-backend': ServiceCheck('dev-backend', 'netra-dev-backend', 8000, 'http://localhost:8000/health', service_type='web'),
            'dev-frontend': ServiceCheck('dev-frontend', 'netra-dev-frontend', 3000, 'http://localhost:3000', service_type='web'),
        }
        
        self.test_services = {
            'test-postgres': ServiceCheck('test-postgres', 'netra-test-postgres', 5434, service_type='database'),
            'test-redis': ServiceCheck('test-redis', 'netra-test-redis', 6381, service_type='cache'),
            'test-clickhouse': ServiceCheck('test-clickhouse', 'netra-test-clickhouse', 8125, 'http://localhost:8125/ping', service_type='database'),
            'test-auth': ServiceCheck('test-auth', 'netra-test-auth', 8082, 'http://localhost:8082/health', service_type='web'),
            'test-analytics': ServiceCheck('test-analytics', 'netra-test-analytics', 8091, 'http://localhost:8091/health', service_type='web'),
            'test-backend': ServiceCheck('test-backend', 'netra-test-backend', 8001, 'http://localhost:8001/health', service_type='web'),
            'test-frontend': ServiceCheck('test-frontend', 'netra-test-frontend', 3001, 'http://localhost:3001', service_type='web'),
        }
        
        # Services that should not exist in normal development
        self.unexpected_services = {
            'test-rabbitmq': ServiceCheck('test-rabbitmq', 'netra-test-rabbitmq', 5673, service_type='queue'),
            'test-seeder': ServiceCheck('test-seeder', 'netra-test-seeder', 0, service_type='utility'),
            'test-monitor': ServiceCheck('test-monitor', 'netra-test-monitor', 9090, service_type='utility'),
        }

    def get_docker_containers(self) -> List[Dict]:
        """Get all Docker containers with details"""
        try:
            result = subprocess.run([
                'docker', 'ps', '-a', 
                '--format', '{{json .}}'
            ], capture_output=True, text=True, check=True)
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    containers.append(json.loads(line))
            return containers
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get Docker containers: {e}")
            return []

    def get_docker_networks(self) -> List[Dict]:
        """Get all Docker networks"""
        try:
            result = subprocess.run([
                'docker', 'network', 'ls', 
                '--format', '{{json .}}'
            ], capture_output=True, text=True, check=True)
            
            networks = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    networks.append(json.loads(line))
            return networks
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get Docker networks: {e}")
            return []

    def check_port_accessibility(self, port: int) -> bool:
        """Check if port is accessible"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False

    def check_service_health(self, service: ServiceCheck) -> bool:
        """Check if service health endpoint responds"""
        if not service.health_url:
            return True  # No health check URL means we can't verify, assume healthy
            
        try:
            response = requests.get(service.health_url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def check_postgres_connectivity(self, host: str, port: int, user: str, password: str, database: str) -> Tuple[bool, str]:
        """Test PostgreSQL connectivity"""
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=5
            )
            conn.close()
            return True, "Connected successfully"
        except psycopg2.OperationalError as e:
            return False, f"Connection failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def check_redis_connectivity(self, host: str, port: int) -> Tuple[bool, str]:
        """Test Redis connectivity"""
        try:
            client = redis.Redis(host=host, port=port, socket_timeout=5)
            client.ping()
            return True, "Connected successfully"
        except redis.ConnectionError as e:
            return False, f"Connection failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def audit_service(self, service: ServiceCheck, container_info: Optional[Dict] = None) -> ServiceStatus:
        """Audit a single service comprehensively"""
        errors = []
        warnings = []
        
        # Check container status
        container_status = "missing"
        if container_info:
            container_status = container_info.get('State', 'unknown')
            
        # Check port accessibility
        port_accessible = False
        if service.expected_port > 0:
            port_accessible = self.check_port_accessibility(service.expected_port)
            if not port_accessible and container_status == "running":
                errors.append(f"Port {service.expected_port} not accessible despite container running")
        
        # Check service responsiveness
        service_responsive = False
        if container_status == "running":
            service_responsive = self.check_service_health(service)
            if not service_responsive and service.health_url:
                errors.append(f"Health check failed for {service.health_url}")
        
        # Specific connectivity checks
        health_status = "unknown"
        if container_status == "running":
            if service.service_type == "database" and "postgres" in service.name:
                if "dev" in service.name:
                    conn_ok, msg = self.check_postgres_connectivity(
                        "localhost", service.expected_port, "netra", "netra123", "netra_dev"
                    )
                elif "test" in service.name:
                    conn_ok, msg = self.check_postgres_connectivity(
                        "localhost", service.expected_port, "test_user", "test_pass", "netra_test"
                    )
                else:
                    conn_ok, msg = False, "Unknown postgres configuration"
                    
                if conn_ok:
                    health_status = "healthy"
                else:
                    health_status = "unhealthy"
                    errors.append(f"PostgreSQL connectivity: {msg}")
                    
            elif service.service_type == "cache" and "redis" in service.name:
                conn_ok, msg = self.check_redis_connectivity("localhost", service.expected_port)
                if conn_ok:
                    health_status = "healthy"
                else:
                    health_status = "unhealthy"
                    errors.append(f"Redis connectivity: {msg}")
            else:
                health_status = "healthy" if service_responsive else "unhealthy"
        elif container_status in ["exited", "dead"]:
            health_status = "stopped"
        
        return ServiceStatus(
            name=service.name,
            container_status=container_status,
            health_status=health_status,
            port_accessible=port_accessible,
            service_responsive=service_responsive,
            errors=errors,
            warnings=warnings
        )

    def audit_all_services(self) -> Dict[str, ServiceStatus]:
        """Audit all services and return comprehensive status"""
        logger.info("Starting comprehensive Docker services audit...")
        
        # Get all containers
        containers = self.get_docker_containers()
        container_map = {c.get('Names', ''): c for c in containers}
        
        results = {}
        
        # Check development services
        logger.info("Auditing development services...")
        for service_name, service in self.dev_services.items():
            container_info = container_map.get(service.container_name)
            results[service_name] = self.audit_service(service, container_info)
        
        # Check test services
        logger.info("Auditing test services...")
        for service_name, service in self.test_services.items():
            container_info = container_map.get(service.container_name)
            results[service_name] = self.audit_service(service, container_info)
            
        # Check unexpected services (should not be running in dev)
        logger.info("Checking for unexpected services...")
        for service_name, service in self.unexpected_services.items():
            container_info = container_map.get(service.container_name)
            if container_info and container_info.get('State') == 'running':
                results[service_name] = self.audit_service(service, container_info)
                results[service_name].warnings.append("This service should not be running in development environment")
                
        return results

    def analyze_conflicts(self, results: Dict[str, ServiceStatus]) -> List[str]:
        """Analyze configuration conflicts and issues"""
        conflicts = []
        
        # Check for port conflicts
        running_ports = {}
        for service_name, status in results.items():
            if status.container_status == "running" and status.port_accessible:
                service = None
                if service_name in self.dev_services:
                    service = self.dev_services[service_name]
                elif service_name in self.test_services:
                    service = self.test_services[service_name]
                elif service_name in self.unexpected_services:
                    service = self.unexpected_services[service_name]
                    
                if service and service.expected_port > 0:
                    if service.expected_port in running_ports:
                        conflicts.append(f"Port {service.expected_port} conflict between {running_ports[service.expected_port]} and {service_name}")
                    else:
                        running_ports[service.expected_port] = service_name
        
        # Check for database role conflicts
        dev_postgres = results.get('dev-postgres')
        test_postgres = results.get('test-postgres')
        
        if dev_postgres and test_postgres:
            if dev_postgres.container_status == "running" and test_postgres.container_status == "running":
                conflicts.append("Both dev and test PostgreSQL instances are running simultaneously")
        
        # Check for network conflicts
        networks = self.get_docker_networks()
        netra_networks = [n for n in networks if 'netra' in n.get('Name', '')]
        if len(netra_networks) > 1:
            network_names = [n['Name'] for n in netra_networks]
            conflicts.append(f"Multiple Netra networks detected: {', '.join(network_names)}")
            
        return conflicts

    def print_detailed_report(self, results: Dict[str, ServiceStatus], conflicts: List[str]):
        """Print comprehensive audit report"""
        print("\n" + "="*80)
        print("NETRA DOCKER SERVICES AUDIT REPORT")
        print("="*80)
        print(f"Audit Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Summary
        running_count = sum(1 for s in results.values() if s.container_status == "running")
        healthy_count = sum(1 for s in results.values() if s.health_status == "healthy")
        error_count = sum(len(s.errors) for s in results.values())
        
        print("SUMMARY:")
        print(f"  Total Services Checked: {len(results)}")
        print(f"  Running Services: {running_count}")
        print(f"  Healthy Services: {healthy_count}")
        print(f"  Total Errors: {error_count}")
        print(f"  Configuration Conflicts: {len(conflicts)}")
        print()
        
        # Conflicts
        if conflicts:
            print("CRITICAL CONFLICTS:")
            for i, conflict in enumerate(conflicts, 1):
                print(f"  {i}. {conflict}")
            print()
        
        # Service Details
        print("SERVICE DETAILS:")
        print("-" * 80)
        
        categories = [
            ("Development Services", self.dev_services.keys()),
            ("Test Services", self.test_services.keys()),
            ("Unexpected Services", [k for k in results.keys() if k in self.unexpected_services])
        ]
        
        for category_name, service_names in categories:
            if not service_names:
                continue
                
            print(f"\n{category_name}:")
            for service_name in service_names:
                if service_name not in results:
                    continue
                    
                status = results[service_name]
                service = (self.dev_services.get(service_name) or 
                          self.test_services.get(service_name) or 
                          self.unexpected_services.get(service_name))
                
                # Status indicators
                container_indicator = "[U+1F7E2]" if status.container_status == "running" else "[U+1F534]" if status.container_status in ["exited", "dead"] else "[U+26AA]"
                health_indicator = "[U+1F7E2]" if status.health_status == "healthy" else "[U+1F534]" if status.health_status == "unhealthy" else "[U+26AA]"
                port_indicator = "[U+1F7E2]" if status.port_accessible else "[U+1F534]"
                
                print(f"  {service_name}")
                print(f"    Container: {container_indicator} {status.container_status}")
                print(f"    Health:    {health_indicator} {status.health_status}")
                if service and service.expected_port > 0:
                    print(f"    Port {service.expected_port}: {port_indicator} {'accessible' if status.port_accessible else 'not accessible'}")
                
                # Errors
                if status.errors:
                    print("    Errors:")
                    for error in status.errors:
                        print(f"       FAIL:  {error}")
                        
                # Warnings
                if status.warnings:
                    print("    Warnings:")
                    for warning in status.warnings:
                        print(f"       WARNING: [U+FE0F]  {warning}")
                print()
        
        # Recommendations
        print("RECOMMENDATIONS:")
        print("-" * 40)
        
        recommendations = []
        
        if any(s in results and results[s].container_status == "running" for s in self.unexpected_services):
            recommendations.append("Stop unexpected test services that are running in development")
            recommendations.append("Run: docker-compose -f docker-compose.test.yml down --remove-orphans")
        
        if conflicts:
            recommendations.append("Resolve configuration conflicts listed above")
            
        if error_count > 0:
            recommendations.append("Address service health issues before proceeding")
            
        # Check for mixed environments
        dev_running = any(s in results and results[s].container_status == "running" for s in self.dev_services)
        test_running = any(s in results and results[s].container_status == "running" for s in self.test_services)
        
        if dev_running and test_running:
            recommendations.append("Stop all services and start only the environment you need:")
            recommendations.append("  For development: docker-compose --profile dev up -d")
            recommendations.append("  For testing: docker-compose -f docker-compose.test.yml up -d")
            
        if not recommendations:
            recommendations.append("All services appear to be properly configured!")
            
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
            
        print("\n" + "="*80)


def main():
    """Main audit execution"""
    auditor = DockerServicesAuditor()
    
    try:
        # Perform comprehensive audit
        results = auditor.audit_all_services()
        conflicts = auditor.analyze_conflicts(results)
        
        # Print detailed report
        auditor.print_detailed_report(results, conflicts)
        
        # Exit with appropriate code
        error_count = sum(len(s.errors) for s in results.values())
        if conflicts or error_count > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.error("Audit interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Audit failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()