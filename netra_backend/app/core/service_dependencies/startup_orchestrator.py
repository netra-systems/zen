"""
Startup Orchestrator - Service startup coordination and orchestration.

Provides centralized orchestration for service startup sequences,
dependency-aware initialization, and coordination with Docker
service management. Integrates with existing startup validation
while providing systematic service orchestration.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.logging_config import central_logger
from .models import (
    DependencyPhase,
    DependencyValidationResult,
    EnvironmentType,
    ServiceType,
)
from .service_dependency_checker import ServiceDependencyChecker
from .integration_manager import IntegrationManager


class StartupOrchestrationResult:
    """Result of startup orchestration process."""
    
    def __init__(self):
        self.overall_success = True
        self.phases_completed: List[DependencyPhase] = []
        self.services_started: List[ServiceType] = []
        self.services_failed: List[ServiceType] = []
        self.orchestration_duration_ms = 0.0
        self.dependency_validation_result: Optional[DependencyValidationResult] = None
        self.integration_results: Dict[str, Any] = {}
        self.error_messages: List[str] = []
        self.warnings: List[str] = []


class StartupOrchestrator:
    """
    Orchestrates systematic service startup with dependency resolution.
    
    Coordinates service dependency validation, Docker service management,
    health check orchestration, and integration with existing startup
    validation systems.
    """
    
    def __init__(self, environment: EnvironmentType = EnvironmentType.DEVELOPMENT):
        """Initialize startup orchestrator."""
        self.logger = central_logger.get_logger(__name__)
        self.environment = environment
        
        # Initialize component systems
        self.dependency_checker = ServiceDependencyChecker(environment=environment)
        self.integration_manager = IntegrationManager(environment=environment)
        
        # Track orchestration state
        self._orchestration_active = False
        self._current_phase: Optional[DependencyPhase] = None
        self._services_in_progress: List[ServiceType] = []
    
    async def orchestrate_service_startup(
        self,
        app: Any,
        target_services: Optional[List[ServiceType]] = None,
        validate_golden_path: bool = True,
        enable_docker_coordination: bool = True,
        timeout_seconds: float = 300.0  # 5 minutes default
    ) -> StartupOrchestrationResult:
        """
        Orchestrate complete service startup with dependency resolution.
        
        Args:
            app: FastAPI application instance
            target_services: Specific services to start (None for all)
            validate_golden_path: Whether to validate golden path business requirements
            enable_docker_coordination: Whether to coordinate with Docker services
            timeout_seconds: Maximum time for complete orchestration
            
        Returns:
            Complete orchestration result with detailed status
        """
        if self._orchestration_active:
            raise RuntimeError("Service startup orchestration already in progress")
        
        start_time = asyncio.get_event_loop().time()
        result = StartupOrchestrationResult()
        
        try:
            self._orchestration_active = True
            self.logger.info("=" * 90)
            self.logger.info("SERVICE STARTUP ORCHESTRATION INITIATED")
            self.logger.info(f"Environment: {self.environment.value}")
            if target_services:
                self.logger.info(f"Target Services: {[s.value for s in target_services]}")
            self.logger.info("=" * 90)
            
            # Phase 1: Pre-orchestration Docker coordination
            if enable_docker_coordination:
                docker_result = await self._coordinate_docker_services(target_services)
                result.integration_results["docker_coordination"] = docker_result
                
                if not docker_result.get("success", True):
                    result.overall_success = False
                    result.error_messages.append("Docker service coordination failed")
                    self.logger.error("❌ Docker service coordination failed")
            
            # Phase 2: Service dependency validation with timeout
            self.logger.info("Phase 1: Service Dependency Validation")
            try:
                dependency_result = await asyncio.wait_for(
                    self.dependency_checker.validate_service_dependencies(
                        app=app,
                        services_to_check=target_services,
                        include_golden_path=validate_golden_path
                    ),
                    timeout=timeout_seconds * 0.6  # 60% of total timeout for validation
                )
                
                result.dependency_validation_result = dependency_result
                
                if not dependency_result.overall_success:
                    result.overall_success = False
                    result.error_messages.extend([
                        f"Dependency validation failed: {failure}"
                        for failure in dependency_result.critical_failures
                    ])
                    self.logger.error("❌ Service dependency validation failed")
                else:
                    self.logger.info("✓ Service dependency validation succeeded")
                    
            except asyncio.TimeoutError:
                result.overall_success = False
                result.error_messages.append(f"Service dependency validation timed out after {timeout_seconds * 0.6}s")
                self.logger.error("❌ Service dependency validation timed out")
                return result
            
            # Phase 3: Service integration coordination
            if result.dependency_validation_result and result.dependency_validation_result.overall_success:
                self.logger.info("Phase 2: Service Integration Coordination")
                
                integration_result = await self._coordinate_service_integration(
                    app, result.dependency_validation_result
                )
                result.integration_results["service_integration"] = integration_result
                
                if integration_result.get("success", True):
                    self.logger.info("✓ Service integration coordination succeeded")
                else:
                    result.warnings.append("Service integration coordination had issues")
                    self.logger.warning("⚠️ Service integration coordination had issues")
            
            # Phase 4: Final validation and readiness confirmation
            if result.overall_success:
                self.logger.info("Phase 3: Final Readiness Validation")
                
                readiness_result = await self._validate_final_readiness(app, target_services)
                result.integration_results["final_readiness"] = readiness_result
                
                if readiness_result.get("success", True):
                    self.logger.info("✓ Final readiness validation succeeded")
                else:
                    result.warnings.append("Final readiness validation had issues")
                    self.logger.warning("⚠️ Final readiness validation had issues")
            
            # Calculate final statistics
            if result.dependency_validation_result:
                result.services_started = [
                    service_result.service_type
                    for service_result in result.dependency_validation_result.service_results
                    if service_result.validation_success
                ]
                result.services_failed = [
                    service_result.service_type
                    for service_result in result.dependency_validation_result.service_results
                    if not service_result.validation_success
                ]
                result.phases_completed = [
                    phase for phase, success in result.dependency_validation_result.phase_results.items()
                    if success
                ]
            
            # Final orchestration timing
            end_time = asyncio.get_event_loop().time()
            result.orchestration_duration_ms = (end_time - start_time) * 1000
            
            # Log orchestration summary
            self._log_orchestration_summary(result)
            
            return result
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            result.overall_success = False
            result.orchestration_duration_ms = (end_time - start_time) * 1000
            result.error_messages.append(f"Orchestration exception: {str(e)}")
            
            self.logger.error(f"Service startup orchestration failed with exception: {e}")
            return result
            
        finally:
            self._orchestration_active = False
            self._current_phase = None
            self._services_in_progress = []
    
    async def _coordinate_docker_services(
        self,
        target_services: Optional[List[ServiceType]]
    ) -> Dict[str, Any]:
        """Coordinate Docker service startup if needed."""
        try:
            # Use integration manager for Docker coordination
            return await self.integration_manager.ensure_docker_services_ready(target_services)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Docker coordination failed"
            }
    
    async def _coordinate_service_integration(
        self,
        app: Any,
        dependency_result: DependencyValidationResult
    ) -> Dict[str, Any]:
        """Coordinate service integration after dependency validation."""
        try:
            # Use integration manager for service integration coordination
            successful_services = [
                service_result.service_type
                for service_result in dependency_result.service_results
                if service_result.validation_success
            ]
            
            return await self.integration_manager.ensure_service_integration(
                app, successful_services
            )
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Service integration coordination failed"
            }
    
    async def _validate_final_readiness(
        self,
        app: Any,
        target_services: Optional[List[ServiceType]]
    ) -> Dict[str, Any]:
        """Perform final readiness validation after orchestration."""
        try:
            # Quick status check to ensure services are still healthy
            status_summary = await self.dependency_checker.get_service_status_summary(app)
            
            total_services = status_summary.get("total_count", 0)
            healthy_services = status_summary.get("healthy_count", 0)
            
            if total_services == 0:
                return {
                    "success": False,
                    "message": "No services found for readiness check"
                }
            
            readiness_ratio = healthy_services / total_services if total_services > 0 else 0
            
            # Consider system ready if 80% of services are healthy
            if readiness_ratio >= 0.8:
                return {
                    "success": True,
                    "message": f"System ready - {healthy_services}/{total_services} services healthy",
                    "readiness_ratio": readiness_ratio,
                    "service_statuses": status_summary.get("services", {})
                }
            else:
                return {
                    "success": False,
                    "message": f"System not ready - only {healthy_services}/{total_services} services healthy",
                    "readiness_ratio": readiness_ratio,
                    "service_statuses": status_summary.get("services", {})
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Final readiness validation failed"
            }
    
    async def orchestrate_phase_startup(
        self,
        app: Any,
        phase: DependencyPhase,
        services_in_phase: List[ServiceType]
    ) -> bool:
        """
        Orchestrate startup for a specific dependency phase.
        
        Args:
            app: FastAPI application instance
            phase: Dependency phase to orchestrate
            services_in_phase: Services to start in this phase
            
        Returns:
            True if phase startup succeeded, False otherwise
        """
        self._current_phase = phase
        self._services_in_progress = services_in_phase.copy()
        
        self.logger.info(f"Orchestrating {phase.value} startup: {[s.value for s in services_in_phase]}")
        
        try:
            # Services within a phase can generally start in parallel
            # but we coordinate the startup to avoid resource conflicts
            validation_tasks = []
            
            for service_type in services_in_phase:
                # Create validation task for each service
                task = self.dependency_checker.validate_single_service_dependency(app, service_type)
                validation_tasks.append(task)
            
            # Execute all validations in parallel with timeout
            phase_timeout = self._get_phase_timeout(phase)
            
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*validation_tasks),
                    timeout=phase_timeout
                )
                
                # Check if all services in the phase succeeded
                phase_success = all(result.validation_success for result in results)
                
                if phase_success:
                    self.logger.info(f"✓ Phase {phase.value} startup completed successfully")
                else:
                    failed_services = [
                        result.service_name for result in results
                        if not result.validation_success
                    ]
                    self.logger.error(f"❌ Phase {phase.value} startup failed for: {failed_services}")
                
                return phase_success
                
            except asyncio.TimeoutError:
                self.logger.error(f"❌ Phase {phase.value} startup timed out after {phase_timeout}s")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Phase {phase.value} orchestration failed: {e}")
            return False
        finally:
            self._current_phase = None
            self._services_in_progress = []
    
    def _get_phase_timeout(self, phase: DependencyPhase) -> float:
        """Get timeout for a specific dependency phase based on environment."""
        base_timeouts = {
            DependencyPhase.PHASE_1_CORE: 30.0,      # Database services need more time
            DependencyPhase.PHASE_2_AUTH: 15.0,      # Auth service
            DependencyPhase.PHASE_3_BACKEND: 20.0,   # Backend services
            DependencyPhase.PHASE_4_FRONTEND: 10.0,  # Frontend services
        }
        
        environment_multipliers = {
            EnvironmentType.TESTING: 0.5,
            EnvironmentType.DEVELOPMENT: 1.0,
            EnvironmentType.STAGING: 1.5,
            EnvironmentType.PRODUCTION: 2.0,
        }
        
        base_timeout = base_timeouts.get(phase, 15.0)
        multiplier = environment_multipliers.get(self.environment, 1.0)
        
        return base_timeout * multiplier
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current orchestration status."""
        return {
            "orchestration_active": self._orchestration_active,
            "current_phase": self._current_phase.value if self._current_phase else None,
            "services_in_progress": [s.value for s in self._services_in_progress],
            "environment": self.environment.value
        }
    
    async def emergency_service_restart(
        self,
        app: Any,
        service_type: ServiceType
    ) -> bool:
        """
        Emergency restart coordination for a specific service.
        
        Args:
            app: FastAPI application instance
            service_type: Service to restart
            
        Returns:
            True if restart succeeded, False otherwise
        """
        self.logger.warning(f"Emergency restart requested for {service_type.value}")
        
        try:
            # Use integration manager for emergency restart
            restart_result = await self.integration_manager.emergency_service_restart(
                service_type
            )
            
            if restart_result.get("success", False):
                # Validate service after restart
                validation_result = await self.dependency_checker.validate_single_service_dependency(
                    app, service_type
                )
                
                if validation_result.validation_success:
                    self.logger.info(f"✓ Emergency restart successful for {service_type.value}")
                    return True
                else:
                    self.logger.error(f"❌ Service validation failed after restart for {service_type.value}")
                    return False
            else:
                self.logger.error(f"❌ Emergency restart failed for {service_type.value}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Emergency restart exception for {service_type.value}: {e}")
            return False
    
    def _log_orchestration_summary(self, result: StartupOrchestrationResult) -> None:
        """Log comprehensive orchestration summary."""
        self.logger.info("=" * 90)
        self.logger.info("SERVICE STARTUP ORCHESTRATION SUMMARY")
        self.logger.info("=" * 90)
        
        # Overall status
        status_emoji = "✅" if result.overall_success else "❌"
        self.logger.info(f"Overall Status: {status_emoji} {'SUCCESS' if result.overall_success else 'FAILED'}")
        
        # Statistics
        self.logger.info(f"Services Started: {len(result.services_started)}")
        self.logger.info(f"Services Failed: {len(result.services_failed)}")
        self.logger.info(f"Phases Completed: {len(result.phases_completed)}")
        self.logger.info(f"Orchestration Duration: {result.orchestration_duration_ms:.1f}ms")
        
        # Phase completion status
        if result.phases_completed:
            self.logger.info(f"Completed Phases: {[phase.value for phase in result.phases_completed]}")
        
        # Service status details
        if result.services_started:
            self.logger.info(f"Started Services: {[service.value for service in result.services_started]}")
        
        if result.services_failed:
            self.logger.error(f"Failed Services: {[service.value for service in result.services_failed]}")
        
        # Errors and warnings
        if result.error_messages:
            self.logger.error(f"\n❌ ERRORS ({len(result.error_messages)}):")
            for i, error in enumerate(result.error_messages, 1):
                self.logger.error(f"  {i}. {error}")
        
        if result.warnings:
            self.logger.warning(f"\n⚠️ WARNINGS ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings, 1):
                self.logger.warning(f"  {i}. {warning}")
        
        # Integration results summary
        if result.integration_results:
            self.logger.info(f"\nIntegration Results:")
            for integration_type, integration_result in result.integration_results.items():
                success = integration_result.get("success", True)
                status = "✓" if success else "❌"
                self.logger.info(f"  {status} {integration_type}: {integration_result.get('message', 'completed')}")
        
        if result.overall_success:
            self.logger.info("\n🚀 SERVICE STARTUP ORCHESTRATION COMPLETED SUCCESSFULLY!")
        else:
            self.logger.error("\n💥 SERVICE STARTUP ORCHESTRATION FAILED!")
        
        self.logger.info("=" * 90)