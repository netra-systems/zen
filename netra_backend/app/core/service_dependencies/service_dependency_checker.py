"""
Service Dependency Checker - Main validation and orchestration logic.

Provides the central ServiceDependencyChecker class that coordinates service
health validation, dependency resolution, and startup orchestration.
Integrates with existing health check systems while providing systematic
service dependency resolution.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.logging_config import central_logger
from .models import (
    DEFAULT_SERVICE_DEPENDENCIES,
    DependencyPhase,
    DependencyValidationResult,
    EnvironmentType,
    ServiceConfiguration,
    ServiceDependency,
    ServiceType,
    ServiceValidationResult,
)
from .health_check_validator import HealthCheckValidator
from .retry_mechanism import RetryMechanism
from .dependency_graph_resolver import DependencyGraphResolver
from .golden_path_validator import GoldenPathValidator


class ServiceDependencyChecker:
    """
    Main service dependency validation and coordination system.
    
    Coordinates health checks, retry logic, dependency resolution,
    and golden path validation to ensure systematic service startup
    and dependency resolution.
    """
    
    def __init__(
        self,
        environment: EnvironmentType = EnvironmentType.DEVELOPMENT,
        service_dependencies: Optional[List[ServiceDependency]] = None
    ):
        """Initialize service dependency checker."""
        self.logger = central_logger.get_logger(__name__)
        self.environment = environment
        self.service_dependencies = service_dependencies or DEFAULT_SERVICE_DEPENDENCIES
        
        # Initialize component systems
        self.health_validator = HealthCheckValidator(environment=environment)
        self.retry_mechanism = RetryMechanism(environment=environment)
        self.dependency_resolver = DependencyGraphResolver(self.service_dependencies)
        self.golden_path_validator = GoldenPathValidator(environment=environment)
        
        # Configuration cache
        self._service_configs: Dict[ServiceType, ServiceConfiguration] = {}
        self._initialize_service_configs()
    
    def _initialize_service_configs(self) -> None:
        """Initialize service configurations for current environment."""
        for service_type in ServiceType:
            self._service_configs[service_type] = ServiceConfiguration.for_environment(
                service_type, self.environment
            )
    
    async def validate_service_dependencies(
        self,
        app: Any,
        services_to_check: Optional[List[ServiceType]] = None,
        include_golden_path: bool = True
    ) -> DependencyValidationResult:
        """
        Validate service dependencies with health checks and dependency resolution.
        
        Args:
            app: FastAPI application instance
            services_to_check: Optional list of specific services to check
            include_golden_path: Whether to include golden path business validation
            
        Returns:
            Complete dependency validation result
        """
        start_time = asyncio.get_event_loop().time()
        self.logger.info("=" * 80)
        self.logger.info("SERVICE DEPENDENCY VALIDATION STARTED")
        self.logger.info(f"Environment: {self.environment.value}")
        self.logger.info("=" * 80)
        
        try:
            # Determine which services to check
            if services_to_check is None:
                services_to_check = list(ServiceType)
            
            # Get dependency-ordered startup sequence
            startup_phases = await self.dependency_resolver.resolve_startup_order(services_to_check)
            self.logger.info(f"Dependency resolution complete - {len(startup_phases)} phases")
            
            # Initialize result tracking
            result = DependencyValidationResult(
                overall_success=True,
                total_services_checked=len(services_to_check)
            )
            
            # Validate services by dependency phases
            for phase, services_in_phase in startup_phases.items():
                self.logger.info(f"Validating {phase.value}: {[s.value for s in services_in_phase]}")
                
                # Validate services in this phase (can be parallel within phase)
                phase_results = await self._validate_phase_services(app, services_in_phase, phase)
                result.service_results.extend(phase_results)
                
                # Check phase success
                phase_success = all(r.validation_success for r in phase_results)
                result.phase_results[phase] = phase_success
                
                if not phase_success:
                    failed_services = [r.service_name for r in phase_results if not r.validation_success]
                    phase_error = f"Phase {phase.value} validation failed for services: {failed_services}"
                    result.critical_failures.append(phase_error)
                    self.logger.error(f"❌ {phase_error}")
                    
                    # For critical phases, stop validation
                    if phase in [DependencyPhase.PHASE_1_CORE, DependencyPhase.PHASE_2_AUTH]:
                        result.overall_success = False
                        self.logger.error(f"🚨 CRITICAL PHASE FAILURE - Stopping validation")
                        break
                else:
                    self.logger.info(f"✓ Phase {phase.value} validation successful")
            
            # Calculate final statistics
            result.services_healthy = sum(1 for r in result.service_results 
                                       if r.validation_success and r.health_check_result and 
                                       r.health_check_result.success)
            result.services_failed = sum(1 for r in result.service_results if not r.validation_success)
            result.services_degraded = result.total_services_checked - result.services_healthy - result.services_failed
            
            # Golden path validation if requested and core services are healthy
            if include_golden_path and result.phase_results.get(DependencyPhase.PHASE_1_CORE, False):
                golden_path_result = await self.golden_path_validator.validate_golden_path_services(
                    app, services_to_check
                )
                
                if not golden_path_result.overall_success:
                    result.overall_success = False
                    result.critical_failures.extend([
                        f"Golden path validation failed: {failure}" 
                        for failure in golden_path_result.business_impact_failures
                    ])
                    self.logger.error("❌ Golden path validation failed - business functionality at risk")
                else:
                    self.logger.info("✓ Golden path validation successful - business functionality protected")
            
            # Final success determination
            if result.critical_failures:
                result.overall_success = False
            
            # Calculate execution time
            end_time = asyncio.get_event_loop().time()
            result.execution_duration_ms = (end_time - start_time) * 1000
            
            # Log final results
            self._log_validation_summary(result)
            
            return result
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            self.logger.error(f"Service dependency validation failed with exception: {e}")
            return DependencyValidationResult(
                overall_success=False,
                critical_failures=[f"Validation exception: {str(e)}"],
                execution_duration_ms=(end_time - start_time) * 1000
            )
    
    async def _validate_phase_services(
        self,
        app: Any,
        services: List[ServiceType],
        phase: DependencyPhase
    ) -> List[ServiceValidationResult]:
        """Validate all services in a specific dependency phase."""
        # Services within a phase can be validated in parallel
        validation_tasks = [
            self._validate_single_service(app, service_type, phase)
            for service_type in services
        ]
        
        return await asyncio.gather(*validation_tasks)
    
    async def _validate_single_service(
        self,
        app: Any,
        service_type: ServiceType,
        phase: DependencyPhase
    ) -> ServiceValidationResult:
        """Validate a single service with retry logic."""
        service_config = self._service_configs[service_type]
        service_name = service_type.value
        
        self.logger.debug(f"Validating {service_name} (Phase: {phase.value})")
        
        try:
            # Use retry mechanism for health check validation
            health_result = await self.retry_mechanism.execute_with_retry(
                operation=lambda: self.health_validator.validate_service_health(app, service_type),
                service_type=service_type,
                operation_name=f"health_check_{service_name}"
            )
            
            # Create validation result
            validation_result = ServiceValidationResult(
                service_type=service_type,
                service_name=service_name,
                validation_success=health_result.success,
                health_check_result=health_result
            )
            
            # Check for warnings based on response time
            if health_result.success and health_result.response_time_ms > (service_config.timeout_seconds * 1000 * 0.8):
                validation_result.warnings.append(
                    f"Service response time ({health_result.response_time_ms:.1f}ms) approaching timeout limit"
                )
            
            # Add metadata about validation
            validation_result.metadata = {
                "phase": phase.value,
                "environment": self.environment.value,
                "retry_count": getattr(health_result, 'retry_count', 0),
                "timeout_seconds": service_config.timeout_seconds,
                "max_retries": service_config.max_retries
            }
            
            if validation_result.validation_success:
                self.logger.info(f"✓ {service_name}: Healthy ({health_result.response_time_ms:.1f}ms)")
            else:
                self.logger.warning(f"⚠️ {service_name}: Failed - {health_result.error_message}")
                
            return validation_result
            
        except Exception as e:
            self.logger.error(f"❌ {service_name}: Validation exception - {e}")
            return ServiceValidationResult(
                service_type=service_type,
                service_name=service_name,
                validation_success=False,
                dependency_failures=[f"Validation exception: {str(e)}"],
                metadata={
                    "phase": phase.value,
                    "environment": self.environment.value,
                    "exception": str(e)
                }
            )
    
    async def validate_single_service_dependency(
        self,
        app: Any,
        service_type: ServiceType
    ) -> ServiceValidationResult:
        """
        Validate a single service dependency without full orchestration.
        Useful for targeted health checks.
        """
        phase = self._get_service_phase(service_type)
        return await self._validate_single_service(app, service_type, phase)
    
    def _get_service_phase(self, service_type: ServiceType) -> DependencyPhase:
        """Get the dependency phase for a service type."""
        for dependency in self.service_dependencies:
            if dependency.service == service_type:
                return dependency.phase
        # Default to phase 3 for unknown services
        return DependencyPhase.PHASE_3_BACKEND
    
    def _log_validation_summary(self, result: DependencyValidationResult) -> None:
        """Log comprehensive validation summary."""
        self.logger.info("=" * 80)
        self.logger.info("SERVICE DEPENDENCY VALIDATION SUMMARY")
        self.logger.info("=" * 80)
        
        # Overall status
        status_emoji = "✅" if result.overall_success else "❌"
        self.logger.info(f"Overall Status: {status_emoji} {'SUCCESS' if result.overall_success else 'FAILED'}")
        
        # Statistics
        self.logger.info(f"Total Services: {result.total_services_checked}")
        self.logger.info(f"Healthy: {result.services_healthy}")
        self.logger.info(f"Degraded: {result.services_degraded}")
        self.logger.info(f"Failed: {result.services_failed}")
        self.logger.info(f"Execution Time: {result.execution_duration_ms:.1f}ms")
        
        # Phase results
        if result.phase_results:
            self.logger.info("\nPhase Results:")
            for phase, success in result.phase_results.items():
                phase_emoji = "✓" if success else "❌"
                self.logger.info(f"  {phase_emoji} {phase.value}: {'PASSED' if success else 'FAILED'}")
        
        # Critical failures
        if result.critical_failures:
            self.logger.error(f"\n🚨 CRITICAL FAILURES ({len(result.critical_failures)}):")
            for i, failure in enumerate(result.critical_failures, 1):
                self.logger.error(f"  {i}. {failure}")
        
        # Service details
        if result.service_results:
            self.logger.info("\nService Details:")
            for service_result in result.service_results:
                if service_result.health_check_result:
                    status = "✓" if service_result.validation_success else "❌"
                    response_time = service_result.health_check_result.response_time_ms
                    self.logger.info(f"  {status} {service_result.service_name}: {response_time:.1f}ms")
                else:
                    self.logger.info(f"  ❌ {service_result.service_name}: No health check result")
        
        self.logger.info("=" * 80)
    
    async def get_service_status_summary(self, app: Any) -> Dict[str, Any]:
        """Get a quick summary of service statuses without full validation."""
        try:
            service_statuses = {}
            
            for service_type in ServiceType:
                try:
                    # Quick health check without retries
                    health_result = await self.health_validator.validate_service_health(
                        app, service_type
                    )
                    
                    service_statuses[service_type.value] = {
                        "healthy": health_result.success,
                        "response_time_ms": health_result.response_time_ms,
                        "status": health_result.health_status.value,
                        "error": health_result.error_message if not health_result.success else None
                    }
                except Exception as e:
                    service_statuses[service_type.value] = {
                        "healthy": False,
                        "response_time_ms": 0.0,
                        "status": "error",
                        "error": str(e)
                    }
            
            return {
                "environment": self.environment.value,
                "services": service_statuses,
                "healthy_count": sum(1 for s in service_statuses.values() if s["healthy"]),
                "total_count": len(service_statuses)
            }
            
        except Exception as e:
            return {
                "environment": self.environment.value,
                "error": str(e),
                "services": {},
                "healthy_count": 0,
                "total_count": 0
            }