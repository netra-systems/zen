#!/usr/bin/env python3
"""
Docker Health Integration Script

Integrates staging health monitoring with Docker Compose infrastructure.
Provides health check enhancements, monitoring service deployment,
and Docker-based health management.
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DockerHealthIntegration:
    """Docker health integration for staging environment monitoring."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docker_compose_file = project_root / "docker-compose.yml"
        self.health_config_file = project_root / "config" / "staging_health_config.yaml"
        
        # Load configurations
        self.docker_config = self._load_docker_compose()
        self.health_config = self._load_health_config()
        
        # Environment setup
        self.env = get_env()
        
    def _load_docker_compose(self) -> Dict[str, Any]:
        """Load Docker Compose configuration."""
        try:
            with open(self.docker_compose_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load Docker Compose config: {e}")
            return {}
    
    def _load_health_config(self) -> Dict[str, Any]:
        """Load health monitoring configuration."""
        try:
            with open(self.health_config_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load health config: {e}")
            return {}
    
    def enhance_docker_compose(self) -> None:
        """Enhance Docker Compose with health monitoring capabilities."""
        logger.info("[U+1F527] Enhancing Docker Compose with health monitoring")
        
        # Create enhanced Docker Compose for staging with health monitoring
        enhanced_compose = self._create_enhanced_compose()
        
        # Save enhanced compose file
        enhanced_file = self.project_root / "docker-compose.staging-health.yml"
        self._save_enhanced_compose(enhanced_compose, enhanced_file)
        
        logger.info(f" PASS:  Enhanced Docker Compose saved to {enhanced_file}")
    
    def _create_enhanced_compose(self) -> Dict[str, Any]:
        """Create enhanced Docker Compose configuration with health monitoring."""
        # Start with base configuration
        enhanced = self.docker_config.copy()
        
        # Add health monitoring service
        health_monitor_service = self._create_health_monitor_service()
        enhanced["services"]["health-monitor"] = health_monitor_service
        
        # Add health dashboard service
        health_dashboard_service = self._create_health_dashboard_service()
        enhanced["services"]["health-dashboard"] = health_dashboard_service
        
        # Enhance existing services with health monitoring integration
        self._enhance_existing_services(enhanced)
        
        # Add health monitoring volumes
        self._add_health_volumes(enhanced)
        
        # Add health monitoring networks
        self._add_health_networks(enhanced)
        
        return enhanced
    
    def _create_health_monitor_service(self) -> Dict[str, Any]:
        """Create health monitor service configuration."""
        return {
            "image": "netra-health-monitor:latest",
            "build": {
                "context": ".",
                "dockerfile": "./docker/health-monitor.Dockerfile"
            },
            "profiles": ["staging", "health"],
            "environment": {
                "ENVIRONMENT": "staging",
                "LOG_LEVEL": "INFO",
                
                # Health monitoring configuration
                "HEALTH_CONFIG_PATH": "/app/config/staging_health_config.yaml",
                "BACKEND_URL": "http://staging-backend:8000",
                "AUTH_URL": "http://staging-auth:8081",
                
                # Monitoring intervals
                "COMPREHENSIVE_CHECK_INTERVAL": "300",
                "CRITICAL_CHECK_INTERVAL": "60",
                "PERFORMANCE_CHECK_INTERVAL": "30",
                
                # Alert configuration
                "HEALTH_WEBHOOK_URL": "${HEALTH_WEBHOOK_URL}",
                "WEBHOOK_TOKEN": "${WEBHOOK_TOKEN}",
                "SLACK_WEBHOOK_URL": "${SLACK_WEBHOOK_URL}",
                
                # Database connections for monitoring
                "POSTGRES_HOST": "staging-postgres",
                "POSTGRES_PORT": "5432",
                "POSTGRES_USER": "${POSTGRES_USER:-netra}",
                "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD:-netra123}",
                "POSTGRES_DB": "${POSTGRES_DB:-netra_staging}",
                
                "REDIS_HOST": "staging-redis",
                "REDIS_PORT": "6379",
                
                "CLICKHOUSE_HOST": "staging-clickhouse",
                "CLICKHOUSE_PORT": "9000",
                "CLICKHOUSE_USER": "${CLICKHOUSE_USER:-netra}",
                "CLICKHOUSE_PASSWORD": "${CLICKHOUSE_PASSWORD:-netra123}",
                
                # Docker integration
                "DOCKER_HOST": "unix:///var/run/docker.sock",
                "COMPOSE_PROJECT_NAME": "${COMPOSE_PROJECT_NAME:-netra}",
                
                # Security
                "HEALTH_API_TOKEN": "${HEALTH_API_TOKEN}",
                "WEBHOOK_SECRET": "${WEBHOOK_SECRET}"
            },
            "ports": [
                "${HEALTH_MONITOR_PORT:-9000}:9000"
            ],
            "volumes": [
                # Configuration
                "./config/staging_health_config.yaml:/app/config/staging_health_config.yaml:ro",
                
                # Docker socket for container monitoring
                "/var/run/docker.sock:/var/run/docker.sock:ro",
                
                # Health data persistence
                "health_monitor_data:/app/data",
                
                # Logs
                "health_monitor_logs:/app/logs"
            ],
            "depends_on": {
                "staging-postgres": {"condition": "service_healthy"},
                "staging-redis": {"condition": "service_healthy"},
                "staging-backend": {"condition": "service_healthy"},
                "staging-auth": {"condition": "service_healthy"}
            },
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:9000/health"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "45s"
            },
            "networks": ["health-monitoring", "default"],
            "restart": "unless-stopped",
            "deploy": {
                "resources": {
                    "limits": {
                        "memory": "512M",
                        "cpus": "0.2"
                    },
                    "reservations": {
                        "memory": "256M"
                    }
                }
            },
            "labels": {
                "netra.service.type": "health-monitor",
                "netra.service.priority": "critical",
                "netra.monitoring.enabled": "true"
            }
        }
    
    def _create_health_dashboard_service(self) -> Dict[str, Any]:
        """Create health dashboard service configuration."""
        return {
            "image": "netra-health-dashboard:latest",
            "build": {
                "context": ".",
                "dockerfile": "./docker/health-dashboard.Dockerfile"
            },
            "profiles": ["staging", "health"],
            "environment": {
                "ENVIRONMENT": "staging",
                "LOG_LEVEL": "INFO",
                
                # Dashboard configuration
                "BACKEND_URL": "http://health-monitor:9000",
                "DASHBOARD_REFRESH_INTERVAL": "5",
                "DASHBOARD_PORT": "8080",
                
                # Authentication
                "DASHBOARD_AUTH_ENABLED": "true",
                "DASHBOARD_USERNAME": "${DASHBOARD_USERNAME:-admin}",
                "DASHBOARD_PASSWORD": "${DASHBOARD_PASSWORD}",
                
                # Data retention
                "DASHBOARD_DATA_RETENTION_HOURS": "168",  # 7 days
                
                # Export configuration
                "EXPORT_ENABLED": "true",
                "EXPORT_FORMATS": "json,csv,pdf"
            },
            "ports": [
                "${HEALTH_DASHBOARD_PORT:-8080}:8080"
            ],
            "volumes": [
                # Dashboard data persistence
                "health_dashboard_data:/app/data",
                
                # Export storage
                "health_exports:/app/exports"
            ],
            "depends_on": {
                "health-monitor": {"condition": "service_healthy"}
            },
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "30s"
            },
            "networks": ["health-monitoring", "default"],
            "restart": "unless-stopped",
            "deploy": {
                "resources": {
                    "limits": {
                        "memory": "256M",
                        "cpus": "0.1"
                    },
                    "reservations": {
                        "memory": "128M"
                    }
                }
            },
            "labels": {
                "netra.service.type": "health-dashboard",
                "netra.service.priority": "medium",
                "netra.monitoring.enabled": "true"
            }
        }
    
    def _enhance_existing_services(self, enhanced_config: Dict[str, Any]) -> None:
        """Enhance existing services with health monitoring integration."""
        services = enhanced_config.get("services", {})
        
        # Rename development services to staging for health monitoring
        staging_services = {
            "staging-postgres": services.get("dev-postgres", {}),
            "staging-redis": services.get("dev-redis", {}),
            "staging-clickhouse": services.get("dev-clickhouse", {}),
            "staging-auth": services.get("dev-auth", {}),
            "staging-backend": services.get("dev-backend", {}),
            "staging-frontend": services.get("dev-frontend", {})
        }
        
        # Update service configurations for staging environment
        for service_name, service_config in staging_services.items():
            if service_config:
                # Add staging profile
                service_config["profiles"] = ["staging", "health"]
                
                # Update environment variables
                env = service_config.get("environment", {})
                if isinstance(env, dict):
                    env["ENVIRONMENT"] = "staging"
                    env["HEALTH_MONITORING_ENABLED"] = "true"
                    env["HEALTH_MONITOR_URL"] = "http://health-monitor:9000"
                
                # Add health monitoring labels
                labels = service_config.get("labels", {})
                labels.update({
                    "netra.service.environment": "staging",
                    "netra.monitoring.enabled": "true",
                    "netra.health.check.enabled": "true"
                })
                service_config["labels"] = labels
                
                # Enhance health checks
                self._enhance_service_healthcheck(service_config, service_name)
                
                # Add to health monitoring network
                networks = service_config.get("networks", ["default"])
                if isinstance(networks, list) and "health-monitoring" not in networks:
                    networks.append("health-monitoring")
                service_config["networks"] = networks
                
                # Update service in enhanced config
                enhanced_config["services"][service_name] = service_config
    
    def _enhance_service_healthcheck(self, service_config: Dict[str, Any], service_name: str) -> None:
        """Enhance individual service health check configuration."""
        current_healthcheck = service_config.get("healthcheck", {})
        
        # More aggressive health checks for staging monitoring
        enhanced_healthcheck = {
            "interval": "15s",  # More frequent checks
            "timeout": "5s",
            "retries": 3,
            "start_period": "30s"
        }
        
        # Keep existing test command if available
        if "test" in current_healthcheck:
            enhanced_healthcheck["test"] = current_healthcheck["test"]
        
        # Service-specific health check enhancements
        if "postgres" in service_name:
            enhanced_healthcheck.update({
                "interval": "10s",
                "retries": 5,
                "start_period": "20s"
            })
        elif "redis" in service_name:
            enhanced_healthcheck.update({
                "interval": "10s",
                "timeout": "3s"
            })
        elif "backend" in service_name or "auth" in service_name:
            enhanced_healthcheck.update({
                "interval": "20s",
                "timeout": "10s",
                "start_period": "40s"
            })
        
        service_config["healthcheck"] = enhanced_healthcheck
    
    def _add_health_volumes(self, enhanced_config: Dict[str, Any]) -> None:
        """Add health monitoring volumes to configuration."""
        volumes = enhanced_config.get("volumes", {})
        
        health_volumes = {
            "health_monitor_data": {},
            "health_monitor_logs": {},
            "health_dashboard_data": {},
            "health_exports": {}
        }
        
        volumes.update(health_volumes)
        enhanced_config["volumes"] = volumes
    
    def _add_health_networks(self, enhanced_config: Dict[str, Any]) -> None:
        """Add health monitoring networks to configuration."""
        networks = enhanced_config.get("networks", {})
        
        health_networks = {
            "health-monitoring": {
                "driver": "bridge",
                "labels": {
                    "netra.network.type": "health-monitoring",
                    "netra.network.environment": "staging"
                }
            }
        }
        
        networks.update(health_networks)
        enhanced_config["networks"] = networks
    
    def _save_enhanced_compose(self, enhanced_config: Dict[str, Any], output_file: Path) -> None:
        """Save enhanced Docker Compose configuration to file."""
        try:
            with open(output_file, 'w') as f:
                yaml.dump(enhanced_config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Enhanced Docker Compose configuration saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save enhanced compose config: {e}")
            raise
    
    def create_health_dockerfiles(self) -> None:
        """Create Dockerfiles for health monitoring services."""
        logger.info("[U+1F433] Creating Dockerfiles for health monitoring services")
        
        docker_dir = self.project_root / "docker"
        docker_dir.mkdir(exist_ok=True)
        
        # Create health monitor Dockerfile
        health_monitor_dockerfile = self._create_health_monitor_dockerfile()
        with open(docker_dir / "health-monitor.Dockerfile", 'w') as f:
            f.write(health_monitor_dockerfile)
        
        # Create health dashboard Dockerfile
        health_dashboard_dockerfile = self._create_health_dashboard_dockerfile()
        with open(docker_dir / "health-dashboard.Dockerfile", 'w') as f:
            f.write(health_dashboard_dockerfile)
        
        logger.info(" PASS:  Health monitoring Dockerfiles created")
    
    def _create_health_monitor_dockerfile(self) -> str:
        """Create Dockerfile for health monitor service."""
        return """
# Health Monitor Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    docker.io \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
COPY shared/requirements.txt shared/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r shared/requirements.txt

# Install additional health monitoring dependencies
RUN pip install --no-cache-dir \\
    psutil \\
    httpx \\
    rich \\
    pydantic \\
    pyyaml

# Copy application code
COPY netra_backend/app /app/netra_backend/app
COPY shared /app/shared
COPY scripts/staging_health_*.py /app/scripts/
COPY config/staging_health_config.yaml /app/config/

# Create required directories
RUN mkdir -p /app/data /app/logs

# Set Python path
ENV PYTHONPATH=/app

# Expose health monitor port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \\
    CMD curl -f http://localhost:9000/health || exit 1

# Run health monitor
CMD ["python", "-m", "scripts.staging_health_monitor_service"]
"""
    
    def _create_health_dashboard_dockerfile(self) -> str:
        """Create Dockerfile for health dashboard service."""
        return """
# Health Dashboard Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install dashboard-specific dependencies
RUN pip install --no-cache-dir \\
    rich \\
    httpx \\
    fastapi \\
    uvicorn \\
    jinja2 \\
    pyyaml

# Copy application code
COPY scripts/staging_health_dashboard.py /app/scripts/
COPY config/staging_health_config.yaml /app/config/

# Create required directories
RUN mkdir -p /app/data /app/exports

# Set Python path
ENV PYTHONPATH=/app

# Expose dashboard port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Run health dashboard
CMD ["python", "-m", "scripts.staging_health_dashboard_service"]
"""
    
    def create_health_monitor_service_script(self) -> None:
        """Create health monitor service entry point script."""
        service_script_path = self.project_root / "scripts" / "staging_health_monitor_service.py"
        
        service_script = '''#!/usr/bin/env python3
"""
Health Monitor Service Entry Point

Runs the health monitor as a service with proper error handling and logging.
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.monitoring.staging_health_monitor import staging_health_monitor
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for service management
health_monitor_task = None
monitoring_active = True

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global monitoring_active
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    monitoring_active = False

# Set up signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Create FastAPI app for health endpoints
app = FastAPI(title="Health Monitor Service", version="1.0.0")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "health-monitor"}

@app.get("/status")
async def get_status():
    """Get health monitor status."""
    return {
        "status": "running" if monitoring_active else "stopped",
        "monitor_active": monitoring_active,
        "service": "health-monitor"
    }

@app.get("/metrics")
async def get_metrics():
    """Get health metrics."""
    try:
        health_status = await staging_health_monitor.get_comprehensive_health()
        return health_status
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to retrieve metrics", "details": str(e)}
        )

async def run_health_monitoring():
    """Run continuous health monitoring."""
    global monitoring_active
    
    logger.info("Starting health monitoring service...")
    
    while monitoring_active:
        try:
            # Run health checks
            await staging_health_monitor.get_comprehensive_health()
            
            # Wait before next check
            await asyncio.sleep(60)  # 1 minute interval
            
        except asyncio.CancelledError:
            logger.info("Health monitoring task cancelled")
            break
        except Exception as e:
            logger.error(f"Health monitoring error: {e}")
            await asyncio.sleep(10)  # Brief pause before retry

async def startup():
    """Application startup."""
    global health_monitor_task
    
    logger.info("Health Monitor Service starting up...")
    
    # Start health monitoring task
    health_monitor_task = asyncio.create_task(run_health_monitoring())
    
    logger.info("Health Monitor Service started successfully")

async def shutdown():
    """Application shutdown."""
    global health_monitor_task, monitoring_active
    
    logger.info("Health Monitor Service shutting down...")
    
    monitoring_active = False
    
    if health_monitor_task:
        health_monitor_task.cancel()
        try:
            await health_monitor_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Health Monitor Service shut down complete")

# Add startup/shutdown event handlers
app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)

if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9000,
        log_level="info",
        access_log=True
    )
'''
        
        with open(service_script_path, 'w') as f:
            f.write(service_script)
        
        # Make script executable
        service_script_path.chmod(0o755)
        
        logger.info(f"Health monitor service script created at {service_script_path}")
    
    def create_deployment_scripts(self) -> None:
        """Create deployment scripts for health-enhanced staging."""
        logger.info("[U+1F4CB] Creating deployment scripts")
        
        scripts_dir = self.project_root / "scripts"
        
        # Deploy staging with health monitoring
        deploy_script = self._create_deploy_staging_script()
        deploy_script_path = scripts_dir / "deploy_staging_with_health.py"
        with open(deploy_script_path, 'w') as f:
            f.write(deploy_script)
        deploy_script_path.chmod(0o755)
        
        # Health check integration script
        integration_script = self._create_integration_script()
        integration_script_path = scripts_dir / "health_check_integration.py"
        with open(integration_script_path, 'w') as f:
            f.write(integration_script)
        integration_script_path.chmod(0o755)
        
        logger.info(" PASS:  Deployment scripts created")
    
    def _create_deploy_staging_script(self) -> str:
        """Create deployment script for staging with health monitoring."""
        return '''#!/usr/bin/env python3
"""
Deploy Staging Environment with Health Monitoring

Deploys staging environment with integrated health monitoring system.
"""

import subprocess
import sys
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(cmd, cwd=None):
    """Run shell command and return result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            logger.error(f"Command failed: {cmd}")
            logger.error(f"Error: {result.stderr}")
            return False
        logger.info(f"Command succeeded: {cmd}")
        return True
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return False

def main():
    """Main deployment function."""
    logger.info("[U+1F680] Starting staging deployment with health monitoring")
    
    # Step 1: Build health monitoring images
    logger.info("[U+1F4E6] Building health monitoring Docker images...")
    if not run_command("docker-compose -f docker-compose.staging-health.yml build health-monitor health-dashboard"):
        logger.error("Failed to build health monitoring images")
        sys.exit(1)
    
    # Step 2: Start infrastructure services first
    logger.info("[U+1F527] Starting infrastructure services...")
    if not run_command("docker-compose -f docker-compose.staging-health.yml up -d staging-postgres staging-redis staging-clickhouse"):
        logger.error("Failed to start infrastructure services")
        sys.exit(1)
    
    # Wait for infrastructure to be ready
    logger.info("[U+23F3] Waiting for infrastructure services to be healthy...")
    time.sleep(30)
    
    # Step 3: Start application services
    logger.info(" TARGET:  Starting application services...")
    if not run_command("docker-compose -f docker-compose.staging-health.yml up -d staging-auth staging-backend staging-frontend"):
        logger.error("Failed to start application services")
        sys.exit(1)
    
    # Wait for applications to be ready
    logger.info("[U+23F3] Waiting for application services to be healthy...")
    time.sleep(45)
    
    # Step 4: Start health monitoring services
    logger.info(" CHART:  Starting health monitoring services...")
    if not run_command("docker-compose -f docker-compose.staging-health.yml up -d health-monitor health-dashboard"):
        logger.error("Failed to start health monitoring services")
        sys.exit(1)
    
    # Step 5: Verify deployment
    logger.info(" SEARCH:  Verifying deployment...")
    time.sleep(15)
    
    # Check service status
    if not run_command("docker-compose -f docker-compose.staging-health.yml ps"):
        logger.warning("Could not verify service status")
    
    # Run health checks
    logger.info("[U+1F3E5] Running post-deployment health checks...")
    if not run_command("python scripts/staging_health_checks.py post-deployment --deployment-id staging-$(date +%Y%m%d-%H%M%S)"):
        logger.warning("Post-deployment health checks had issues")
    
    logger.info(" PASS:  Staging deployment with health monitoring completed")
    logger.info(" CHART:  Health Dashboard: http://localhost:8080")
    logger.info(" SEARCH:  Health API: http://localhost:9000")
    logger.info(" TARGET:  Backend API: http://localhost:8000")

if __name__ == "__main__":
    main()
'''
    
    def _create_integration_script(self) -> str:
        """Create health check integration script."""
        return '''#!/usr/bin/env python3
"""
Health Check Integration Script

Integrates health monitoring with existing deployment pipelines.
"""

import argparse
import subprocess
import json
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_health_check(check_type, deployment_id=None):
    """Run health check and return result."""
    cmd = f"python scripts/staging_health_checks.py {check_type}"
    
    if deployment_id and check_type == "post-deployment":
        cmd += f" --deployment-id {deployment_id}"
    
    cmd += " --output /tmp/health_check_result.json"
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Load results
        try:
            with open("/tmp/health_check_result.json", "r") as f:
                health_result = json.load(f)
        except:
            health_result = {"result": "unknown", "summary": {}}
        
        return result.returncode == 0, health_result
    except Exception as e:
        logger.error(f"Health check execution failed: {e}")
        return False, {"result": "failed", "error": str(e)}

def integrate_with_ci_cd():
    """Integration point for CI/CD pipelines."""
    parser = argparse.ArgumentParser(description="Health Check CI/CD Integration")
    parser.add_argument("phase", choices=["pre-deploy", "post-deploy", "continuous"])
    parser.add_argument("--deployment-id", help="Deployment ID")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit with error code on health check failure")
    
    args = parser.parse_args()
    
    if args.phase == "pre-deploy":
        success, result = run_health_check("pre-deployment")
        if not success:
            logger.error("Pre-deployment health checks failed")
            if args.fail_on_error:
                sys.exit(1)
        else:
            logger.info("Pre-deployment health checks passed")
    
    elif args.phase == "post-deploy":
        if not args.deployment_id:
            logger.error("Deployment ID required for post-deployment checks")
            sys.exit(1)
        
        success, result = run_health_check("post-deployment", args.deployment_id)
        if not success:
            logger.error("Post-deployment health checks failed")
            if args.fail_on_error:
                sys.exit(1)
        else:
            logger.info("Post-deployment health checks passed")
    
    elif args.phase == "continuous":
        logger.info("Starting continuous health monitoring...")
        subprocess.run("python scripts/staging_health_checks.py continuous", shell=True)

if __name__ == "__main__":
    integrate_with_ci_cd()
'''
    
    def validate_integration(self) -> bool:
        """Validate Docker health integration setup."""
        logger.info(" SEARCH:  Validating Docker health integration")
        
        validation_results = []
        
        # Check if enhanced Docker Compose exists
        enhanced_compose = self.project_root / "docker-compose.staging-health.yml"
        validation_results.append({
            "check": "Enhanced Docker Compose exists",
            "passed": enhanced_compose.exists(),
            "path": str(enhanced_compose)
        })
        
        # Check if health config exists
        validation_results.append({
            "check": "Health config exists",
            "passed": self.health_config_file.exists(),
            "path": str(self.health_config_file)
        })
        
        # Check if Docker directory exists
        docker_dir = self.project_root / "docker"
        validation_results.append({
            "check": "Docker directory exists",
            "passed": docker_dir.exists(),
            "path": str(docker_dir)
        })
        
        # Check if health monitor Dockerfile exists
        health_monitor_dockerfile = docker_dir / "health-monitor.Dockerfile"
        validation_results.append({
            "check": "Health monitor Dockerfile exists",
            "passed": health_monitor_dockerfile.exists(),
            "path": str(health_monitor_dockerfile)
        })
        
        # Check if deployment scripts exist
        deploy_script = self.project_root / "scripts" / "deploy_staging_with_health.py"
        validation_results.append({
            "check": "Deployment script exists",
            "passed": deploy_script.exists(),
            "path": str(deploy_script)
        })
        
        # Print validation results
        all_passed = True
        for result in validation_results:
            status = " PASS:  PASS" if result["passed"] else " FAIL:  FAIL"
            logger.info(f"{status} - {result['check']}: {result['path']}")
            if not result["passed"]:
                all_passed = False
        
        if all_passed:
            logger.info(" PASS:  Docker health integration validation passed")
        else:
            logger.error(" FAIL:  Docker health integration validation failed")
        
        return all_passed


def main():
    """Main function for Docker health integration."""
    parser = argparse.ArgumentParser(description="Docker Health Integration")
    parser.add_argument("action", choices=[
        "enhance", "create-dockerfiles", "create-scripts", "validate", "all"
    ], help="Action to perform")
    parser.add_argument("--project-root", help="Project root directory", default=".")
    
    args = parser.parse_args()
    
    # Initialize integration
    project_root = Path(args.project_root).resolve()
    integration = DockerHealthIntegration(project_root)
    
    try:
        if args.action == "enhance":
            integration.enhance_docker_compose()
        elif args.action == "create-dockerfiles":
            integration.create_health_dockerfiles()
        elif args.action == "create-scripts":
            integration.create_health_monitor_service_script()
            integration.create_deployment_scripts()
        elif args.action == "validate":
            success = integration.validate_integration()
            sys.exit(0 if success else 1)
        elif args.action == "all":
            integration.enhance_docker_compose()
            integration.create_health_dockerfiles()
            integration.create_health_monitor_service_script()
            integration.create_deployment_scripts()
            
            # Validate the integration
            success = integration.validate_integration()
            if success:
                logger.info(" CELEBRATION:  Docker health integration setup completed successfully!")
                logger.info("Next steps:")
                logger.info("1. Review docker-compose.staging-health.yml")
                logger.info("2. Set required environment variables")
                logger.info("3. Run: python scripts/deploy_staging_with_health.py")
            else:
                logger.error(" FAIL:  Integration setup completed with validation errors")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"Docker health integration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()