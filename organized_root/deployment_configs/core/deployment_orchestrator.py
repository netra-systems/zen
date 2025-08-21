"""
Main deployment orchestrator for GCP deployments.
Coordinates Docker builds, Cloud Run deployments, and health checks.
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cloud_run_deployer import CloudRunDeployer, CloudRunService
from .docker_image_manager import DockerImageManager
from .health_checker import HealthChecker, HealthStatus

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from test_framework.gcp_integration.log_reader_core import GCPLogReader

logger = logging.getLogger(__name__)

class DeploymentPhase(Enum):
    """Deployment phases."""
    PRE_DEPLOYMENT = "pre_deployment"
    AUTHENTICATION = "authentication"
    BUILD = "build"
    DEPLOY = "deploy"
    HEALTH_CHECK = "health_check"
    POST_DEPLOYMENT = "post_deployment"
    ROLLBACK = "rollback"

@dataclass
class DeploymentConfig:
    """Complete deployment configuration."""
    project_id: str
    region: str = "us-central1"
    services: List[Dict[str, Any]] = field(default_factory=list)
    skip_health_checks: bool = False
    skip_auth: bool = False
    skip_tests: bool = False
    skip_error_monitoring: bool = False
    enable_rollback: bool = True
    max_error_rate: float = 0.05  # 5% error rate threshold

@dataclass
class DeploymentResult:
    """Deployment result tracking."""
    phase: DeploymentPhase
    success: bool
    start_time: datetime
    end_time: datetime
    services_deployed: List[str] = field(default_factory=list)
    services_failed: List[str] = field(default_factory=list)
    health_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    rollback_performed: bool = False
    
    @property
    def duration_seconds(self) -> float:
        """Get deployment duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

class DeploymentOrchestrator:
    """Orchestrates the complete deployment pipeline."""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.docker_manager = DockerImageManager(config.project_id, config.region)
        self.cloud_run_deployer = CloudRunDeployer(config.project_id, config.region)
        self.current_phase = DeploymentPhase.PRE_DEPLOYMENT
        self.deployment_history: List[DeploymentResult] = []
        self.previous_versions: Dict[str, str] = {}  # For rollback
        
    async def execute_deployment(self) -> DeploymentResult:
        """
        Execute the complete deployment pipeline.
        
        Returns:
            DeploymentResult with deployment status
        """
        start_time = datetime.utcnow()
        result = DeploymentResult(
            phase=self.current_phase,
            success=False,
            start_time=start_time,
            end_time=start_time
        )
        
        try:
            # Phase 1: Pre-deployment validation
            if not await self._pre_deployment_checks():
                result.errors.append("Pre-deployment checks failed")
                return result
            
            # Phase 2: Authentication setup
            self.current_phase = DeploymentPhase.AUTHENTICATION
            if not self.config.skip_auth:
                if not await self._setup_authentication():
                    result.errors.append("Authentication setup failed")
                    return result
            
            # Phase 3: Build Docker images
            self.current_phase = DeploymentPhase.BUILD
            build_results = await self._build_images()
            if not all(build_results.values()):
                result.services_failed = [s for s, success in build_results.items() if not success]
                result.errors.append(f"Failed to build: {', '.join(result.services_failed)}")
                return result
            
            # Phase 4: Deploy to Cloud Run
            self.current_phase = DeploymentPhase.DEPLOY
            deploy_results = await self._deploy_services()
            result.services_deployed = [s for s, success in deploy_results.items() if success]
            result.services_failed = [s for s, success in deploy_results.items() if not success]
            
            if result.services_failed:
                result.errors.append(f"Failed to deploy: {', '.join(result.services_failed)}")
                
                # Attempt rollback if enabled
                if self.config.enable_rollback:
                    await self._rollback_failed_services(result.services_failed)
                    result.rollback_performed = True
                    
                return result
            
            # Phase 5: Health checks
            self.current_phase = DeploymentPhase.HEALTH_CHECK
            if not self.config.skip_health_checks:
                health_results = await self._run_health_checks()
                result.health_results = {
                    name: {
                        "status": r.status.value,
                        "response_time_ms": r.response_time_ms,
                        "checks": r.checks
                    }
                    for name, r in health_results.items()
                }
                
                unhealthy = [
                    name for name, r in health_results.items() 
                    if r.status == HealthStatus.UNHEALTHY
                ]
                
                if unhealthy:
                    result.errors.append(f"Unhealthy services: {', '.join(unhealthy)}")
                    
                    # Rollback unhealthy services
                    if self.config.enable_rollback:
                        await self._rollback_failed_services(unhealthy)
                        result.rollback_performed = True
                        
                    return result
            
            # Phase 6: Post-deployment monitoring
            self.current_phase = DeploymentPhase.POST_DEPLOYMENT
            if not self.config.skip_error_monitoring:
                error_rate = await self._monitor_post_deployment()
                if error_rate > self.config.max_error_rate:
                    result.errors.append(f"Error rate {error_rate:.2%} exceeds threshold")
                    
                    if self.config.enable_rollback:
                        await self._rollback_all_services()
                        result.rollback_performed = True
                        
                    return result
            
            result.success = True
            logger.info("Deployment completed successfully")
            
        except Exception as e:
            logger.error(f"Deployment failed with exception: {str(e)}")
            result.errors.append(str(e))
            
            # Emergency rollback
            if self.config.enable_rollback and self.current_phase == DeploymentPhase.DEPLOY:
                await self._rollback_all_services()
                result.rollback_performed = True
                
        finally:
            result.end_time = datetime.utcnow()
            result.phase = self.current_phase
            self.deployment_history.append(result)
            
        return result
    
    async def _pre_deployment_checks(self) -> bool:
        """Run pre-deployment validation checks."""
        if self.config.skip_tests:
            logger.warning("Skipping pre-deployment tests")
            return True
            
        logger.info("Running pre-deployment validation...")
        
        # Check if services are configured
        if not self.config.services:
            logger.error("No services configured for deployment")
            return False
        
        # Validate service configurations
        for service in self.config.services:
            if "name" not in service:
                logger.error(f"Service missing 'name' field: {service}")
                return False
            if "dockerfile" not in service and "image" not in service:
                logger.error(f"Service {service['name']} missing dockerfile or image")
                return False
        
        # Store current versions for potential rollback
        for service in self.config.services:
            current_version = await self._get_current_version(service["name"])
            if current_version:
                self.previous_versions[service["name"]] = current_version
        
        return True
    
    async def _setup_authentication(self) -> bool:
        """Setup GCP authentication."""
        logger.info("Setting up GCP authentication...")
        
        # Configure Docker authentication
        if not self.docker_manager.configure_docker_auth():
            logger.error("Failed to configure Docker authentication")
            return False
            
        return True
    
    async def _build_images(self) -> Dict[str, bool]:
        """Build Docker images for all services."""
        logger.info("Building Docker images...")
        
        # Filter services that need building
        services_to_build = [
            s for s in self.config.services 
            if "dockerfile" in s
        ]
        
        if not services_to_build:
            logger.info("No services require building")
            return {}
        
        # Build and push images
        results = self.docker_manager.build_and_push_services(services_to_build)
        
        # Clean up old images
        for service in services_to_build:
            if results.get(service["name"], False):
                self.docker_manager.cleanup_old_images(service["name"], keep_count=5)
        
        return results
    
    async def _deploy_services(self) -> Dict[str, bool]:
        """Deploy services to Cloud Run."""
        logger.info("Deploying services to Cloud Run...")
        
        results = {}
        
        for service_config in self.config.services:
            # Get image URL
            if "image" in service_config:
                image = service_config["image"]
            else:
                registry_url = f"{self.config.region}-docker.pkg.dev/{self.config.project_id}/netra-apex"
                image = f"{registry_url}/{service_config['name']}:latest"
            
            # Create Cloud Run service configuration
            service = CloudRunService(
                name=service_config["name"],
                image=image,
                region=self.config.region,
                project_id=self.config.project_id,
                memory=service_config.get("memory", "512Mi"),
                cpu=service_config.get("cpu", "1"),
                min_instances=service_config.get("min_instances", 0),
                max_instances=service_config.get("max_instances", 10),
                port=service_config.get("port", 8000),
                env_vars=service_config.get("env_vars"),
                secrets=service_config.get("secrets"),
                vpc_connector=service_config.get("vpc_connector"),
                service_account=service_config.get("service_account"),
                allow_unauthenticated=service_config.get("allow_unauthenticated", False)
            )
            
            # Deploy service
            success = self.cloud_run_deployer.deploy_service(service)
            results[service_config["name"]] = success
            
            if success:
                # Get and log service URL
                url = self.cloud_run_deployer.get_service_url(service_config["name"])
                if url:
                    logger.info(f"Service {service_config['name']} deployed at: {url}")
        
        return results
    
    async def _run_health_checks(self) -> Dict[str, Any]:
        """Run health checks on deployed services."""
        logger.info("Running health checks on deployed services...")
        
        services_to_check = []
        
        for service in self.config.services:
            url = self.cloud_run_deployer.get_service_url(service["name"])
            if url:
                services_to_check.append({
                    "name": service["name"],
                    "url": url,
                    "health_endpoint": service.get("health_endpoint", "/health")
                })
        
        if not services_to_check:
            logger.warning("No services found for health checks")
            return {}
        
        async with HealthChecker() as checker:
            results = await checker.check_multiple_services(services_to_check)
            
            # Generate and log health report
            report = checker.generate_health_report(results)
            logger.info(f"\n{report}")
            
            # Wait for unhealthy services to become healthy
            for service_name, result in results.items():
                if result.status == HealthStatus.UNHEALTHY:
                    service_config = next(
                        (s for s in services_to_check if s["name"] == service_name), 
                        None
                    )
                    if service_config:
                        became_healthy = await checker.wait_for_healthy(
                            service_config["url"],
                            service_name,
                            max_wait_seconds=120
                        )
                        if became_healthy:
                            # Update result
                            results[service_name] = await checker.check_service_health(
                                service_config["url"],
                                service_name
                            )
        
        return results
    
    async def _monitor_post_deployment(self) -> float:
        """Monitor services post-deployment for errors."""
        if self.config.skip_error_monitoring:
            return 0.0
            
        logger.info("Monitoring post-deployment errors...")
        
        try:
            # Use GCP log reader to check for errors
            log_reader = GCPLogReader(self.config.project_id)
            
            error_count = 0
            total_logs = 0
            
            for service in self.config.services:
                # Read recent logs
                logs = log_reader.read_logs(
                    resource_type="cloud_run_revision",
                    resource_labels={"service_name": service["name"]},
                    severity_filter="ERROR",
                    limit=100
                )
                
                error_count += len([l for l in logs if "ERROR" in l.get("severity", "")])
                
                # Get total log count for error rate calculation
                all_logs = log_reader.read_logs(
                    resource_type="cloud_run_revision",
                    resource_labels={"service_name": service["name"]},
                    limit=1000
                )
                total_logs += len(all_logs)
            
            error_rate = error_count / total_logs if total_logs > 0 else 0.0
            
            logger.info(f"Post-deployment error rate: {error_rate:.2%} ({error_count}/{total_logs})")
            
            return error_rate
            
        except Exception as e:
            logger.error(f"Error monitoring post-deployment: {str(e)}")
            return 0.0
    
    async def _get_current_version(self, service_name: str) -> Optional[str]:
        """Get current deployed version of a service."""
        status = self.cloud_run_deployer.get_service_status(service_name)
        return status.get("latest_revision")
    
    async def _rollback_failed_services(self, service_names: List[str]) -> bool:
        """Rollback failed services to previous versions."""
        self.current_phase = DeploymentPhase.ROLLBACK
        logger.warning(f"Rolling back services: {', '.join(service_names)}")
        
        success = True
        for service_name in service_names:
            if service_name in self.previous_versions:
                if not self.cloud_run_deployer.rollback_service(
                    service_name, 
                    self.previous_versions[service_name]
                ):
                    logger.error(f"Failed to rollback {service_name}")
                    success = False
                else:
                    logger.info(f"Successfully rolled back {service_name}")
        
        return success
    
    async def _rollback_all_services(self) -> bool:
        """Rollback all deployed services."""
        service_names = [s["name"] for s in self.config.services]
        return await self._rollback_failed_services(service_names)
    
    def get_deployment_summary(self) -> str:
        """Get a summary of the last deployment."""
        if not self.deployment_history:
            return "No deployments executed"
        
        last = self.deployment_history[-1]
        
        lines = [
            "=" * 60,
            "DEPLOYMENT SUMMARY",
            "=" * 60,
            f"Status: {'SUCCESS' if last.success else 'FAILED'}",
            f"Phase: {last.phase.value}",
            f"Duration: {last.duration_seconds:.2f} seconds",
            f"Services Deployed: {', '.join(last.services_deployed) or 'None'}",
            f"Services Failed: {', '.join(last.services_failed) or 'None'}",
            f"Rollback Performed: {'Yes' if last.rollback_performed else 'No'}",
        ]
        
        if last.errors:
            lines.append(f"Errors: {'; '.join(last.errors)}")
        
        if last.health_results:
            lines.append("\nHealth Check Results:")
            for service, health in last.health_results.items():
                lines.append(f"  {service}: {health['status']}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)