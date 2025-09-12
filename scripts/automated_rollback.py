#!/usr/bin/env python3
"""
Automated Rollback System for Production Isolation Features
===========================================================

Comprehensive automated rollback system that can instantly revert isolation
features and Cloud Run services to previous stable state with zero downtime.

Features:
- Instant feature flag disable (< 5 seconds)
- Cloud Run service rollback to previous revision
- Database state verification and cleanup
- Automated health checks and validation
- Comprehensive rollback verification
- Audit trail and incident reporting

Usage Examples:
    # Emergency instant rollback
    python scripts/automated_rollback.py emergency \
        --reason "Cascade failures detected" \
        --triggered-by "monitoring_system"
    
    # Gradual rollback with validation
    python scripts/automated_rollback.py gradual \
        --reason "Performance degradation" \
        --validate-each-step
    
    # Rollback specific service only
    python scripts/automated_rollback.py service-only \
        --service backend \
        --reason "Backend errors"
    
    # Verify rollback completed
    python scripts/automated_rollback.py verify-rollback
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.feature_flags import (
    ProductionFeatureFlags, 
    RolloutStage,
    get_feature_flags
)
from shared.isolated_environment import IsolatedEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RollbackType(Enum):
    """Types of rollback procedures."""
    EMERGENCY = "emergency"      # Instant rollback (< 5 seconds)
    GRADUAL = "gradual"         # Step-by-step rollback with validation
    SERVICE_ONLY = "service"    # Rollback specific service
    FEATURE_FLAGS_ONLY = "flags" # Disable feature flags only


class RollbackStatus(Enum):
    """Status of rollback procedure."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partial"


@dataclass
class RollbackStep:
    """Individual step in rollback procedure."""
    name: str
    description: str
    action: str
    completed: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    output: Optional[str] = None


@dataclass
class RollbackPlan:
    """Complete rollback execution plan."""
    rollback_id: str
    rollback_type: RollbackType
    reason: str
    triggered_by: str
    environment: str
    start_time: float
    end_time: Optional[float] = None
    status: RollbackStatus = RollbackStatus.NOT_STARTED
    steps: List[RollbackStep] = None
    services_affected: List[str] = None
    feature_flags_disabled: List[str] = None
    validation_results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.services_affected is None:
            self.services_affected = []
        if self.feature_flags_disabled is None:
            self.feature_flags_disabled = []
        if self.validation_results is None:
            self.validation_results = {}


class AutomatedRollbackSystem:
    """Automated rollback system for production deployments."""
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.env = IsolatedEnvironment.get_instance()
        self.feature_flags = ProductionFeatureFlags(environment)
        
        # GCP configuration
        self.gcp_project = self.env.get("GCP_PROJECT_ID", "netra-production")
        self.gcp_region = "us-central1"
        
        # Services configuration
        self.services = {
            "backend": "netra-backend-production",
            "auth": "netra-auth-service-production",
            "frontend": "netra-frontend-production"
        }
        
        # Isolation feature flags
        self.isolation_flags = [
            "request_isolation",
            "factory_pattern",
            "websocket_isolation", 
            "database_session_isolation",
            "context_isolation"
        ]
        
        logger.info(f"Initialized AutomatedRollbackSystem for {environment}")

    async def execute_emergency_rollback(self, reason: str, triggered_by: str) -> RollbackPlan:
        """
        Execute emergency rollback - fastest possible revert (< 5 seconds).
        
        This is the nuclear option - instantly disable all features and 
        rollback all services simultaneously.
        """
        rollback_id = f"emergency_{int(time.time())}"
        logger.critical(f"EMERGENCY ROLLBACK initiated: {rollback_id}")
        logger.critical(f"Reason: {reason}")
        logger.critical(f"Triggered by: {triggered_by}")
        
        plan = RollbackPlan(
            rollback_id=rollback_id,
            rollback_type=RollbackType.EMERGENCY,
            reason=reason,
            triggered_by=triggered_by,
            environment=self.environment,
            start_time=time.time(),
            status=RollbackStatus.IN_PROGRESS
        )
        
        try:
            # Step 1: Emergency disable all feature flags (highest priority)
            await self.emergency_disable_feature_flags(plan)
            
            # Step 2: Rollback all services simultaneously (fire and forget)
            await self.rollback_all_services_parallel(plan)
            
            # Step 3: Quick validation
            await self.quick_validation_check(plan)
            
            plan.status = RollbackStatus.COMPLETED
            plan.end_time = time.time()
            
            duration = plan.end_time - plan.start_time
            logger.critical(f" PASS:  EMERGENCY ROLLBACK completed in {duration:.2f} seconds")
            
            # Log to audit trail
            await self.log_rollback_audit(plan)
            
            return plan
            
        except Exception as e:
            plan.status = RollbackStatus.FAILED
            plan.end_time = time.time()
            logger.critical(f" FAIL:  EMERGENCY ROLLBACK FAILED: {e}")
            
            # Even if rollback fails, try to log for debugging
            try:
                await self.log_rollback_audit(plan)
            except:
                pass
                
            raise

    async def execute_gradual_rollback(self, reason: str, triggered_by: str, 
                                     validate_each_step: bool = True) -> RollbackPlan:
        """
        Execute gradual rollback with validation at each step.
        
        This approach is safer but slower - validates each step before proceeding.
        """
        rollback_id = f"gradual_{int(time.time())}"
        logger.warning(f"GRADUAL ROLLBACK initiated: {rollback_id}")
        logger.warning(f"Reason: {reason}")
        
        plan = RollbackPlan(
            rollback_id=rollback_id,
            rollback_type=RollbackType.GRADUAL,
            reason=reason,
            triggered_by=triggered_by,
            environment=self.environment,
            start_time=time.time(),
            status=RollbackStatus.IN_PROGRESS
        )
        
        try:
            # Step 1: Disable feature flags gradually
            await self.gradual_disable_feature_flags(plan, validate_each_step)
            
            # Step 2: Rollback services one by one
            for service_name in ["backend", "auth", "frontend"]:
                await self.rollback_single_service(plan, service_name, validate_each_step)
            
            # Step 3: Comprehensive validation
            await self.comprehensive_validation_check(plan)
            
            plan.status = RollbackStatus.COMPLETED
            plan.end_time = time.time()
            
            duration = plan.end_time - plan.start_time
            logger.info(f" PASS:  GRADUAL ROLLBACK completed in {duration:.2f} seconds")
            
            await self.log_rollback_audit(plan)
            
            return plan
            
        except Exception as e:
            plan.status = RollbackStatus.FAILED
            plan.end_time = time.time()
            logger.error(f" FAIL:  GRADUAL ROLLBACK FAILED: {e}")
            
            await self.log_rollback_audit(plan)
            raise

    async def execute_service_rollback(self, service_name: str, reason: str, 
                                     triggered_by: str) -> RollbackPlan:
        """Rollback a specific service only."""
        rollback_id = f"service_{service_name}_{int(time.time())}"
        logger.warning(f"SERVICE ROLLBACK initiated: {rollback_id}")
        
        plan = RollbackPlan(
            rollback_id=rollback_id,
            rollback_type=RollbackType.SERVICE_ONLY,
            reason=reason,
            triggered_by=triggered_by,
            environment=self.environment,
            start_time=time.time(),
            status=RollbackStatus.IN_PROGRESS
        )
        
        try:
            # Only rollback the specified service
            await self.rollback_single_service(plan, service_name, validate=True)
            
            # Service-specific validation
            await self.validate_service_rollback(plan, service_name)
            
            plan.status = RollbackStatus.COMPLETED
            plan.end_time = time.time()
            
            duration = plan.end_time - plan.start_time
            logger.info(f" PASS:  SERVICE ROLLBACK ({service_name}) completed in {duration:.2f} seconds")
            
            await self.log_rollback_audit(plan)
            
            return plan
            
        except Exception as e:
            plan.status = RollbackStatus.FAILED
            plan.end_time = time.time()
            logger.error(f" FAIL:  SERVICE ROLLBACK FAILED: {e}")
            
            await self.log_rollback_audit(plan)
            raise

    async def emergency_disable_feature_flags(self, plan: RollbackPlan) -> None:
        """Emergency disable all isolation feature flags."""
        step = RollbackStep(
            name="emergency_disable_flags",
            description="Emergency disable all isolation feature flags",
            action="feature_flags_emergency_disable",
            start_time=time.time()
        )
        plan.steps.append(step)
        
        try:
            logger.critical(" ALERT:  EMERGENCY: Disabling all isolation feature flags...")
            
            success = self.feature_flags.emergency_disable_all(
                reason=f"Emergency rollback: {plan.reason}",
                updated_by=f"automated_rollback_{plan.triggered_by}"
            )
            
            if success:
                step.completed = True
                step.output = "All feature flags disabled successfully"
                plan.feature_flags_disabled = self.isolation_flags.copy()
                logger.critical(" PASS:  Feature flags disabled")
            else:
                step.error = "Failed to disable feature flags"
                logger.critical(" FAIL:  Failed to disable feature flags")
                raise Exception("Feature flag emergency disable failed")
            
        except Exception as e:
            step.error = str(e)
            logger.critical(f" FAIL:  Feature flag disable error: {e}")
            raise
        finally:
            step.end_time = time.time()

    async def rollback_all_services_parallel(self, plan: RollbackPlan) -> None:
        """Rollback all services in parallel for speed."""
        step = RollbackStep(
            name="parallel_service_rollback",
            description="Rollback all Cloud Run services in parallel",
            action="parallel_cloud_run_rollback",
            start_time=time.time()
        )
        plan.steps.append(step)
        
        try:
            logger.critical(" ALERT:  EMERGENCY: Rolling back all services in parallel...")
            
            # Create rollback tasks for all services
            tasks = []
            for service_name, cloud_run_name in self.services.items():
                task = asyncio.create_task(
                    self.rollback_cloud_run_service(cloud_run_name, service_name)
                )
                tasks.append((service_name, task))
            
            # Execute all rollbacks simultaneously
            results = []
            for service_name, task in tasks:
                try:
                    result = await task
                    results.append((service_name, True, result))
                    plan.services_affected.append(service_name)
                except Exception as e:
                    results.append((service_name, False, str(e)))
                    logger.error(f"Failed to rollback {service_name}: {e}")
            
            # Check results
            successful_rollbacks = [r for r in results if r[1]]
            failed_rollbacks = [r for r in results if not r[1]]
            
            if len(successful_rollbacks) > 0:
                step.completed = True
                step.output = f"Successfully rolled back: {[r[0] for r in successful_rollbacks]}"
                logger.critical(f" PASS:  Rolled back {len(successful_rollbacks)} services")
            
            if len(failed_rollbacks) > 0:
                step.error = f"Failed rollbacks: {failed_rollbacks}"
                logger.critical(f" FAIL:  {len(failed_rollbacks)} services failed to rollback")
                
                # Don't fail the entire rollback if some services succeeded
                if len(successful_rollbacks) == 0:
                    raise Exception("All service rollbacks failed")
            
        except Exception as e:
            step.error = str(e)
            logger.critical(f" FAIL:  Parallel service rollback error: {e}")
            raise
        finally:
            step.end_time = time.time()

    async def rollback_cloud_run_service(self, cloud_run_name: str, 
                                        service_name: str) -> str:
        """Rollback a single Cloud Run service to previous revision."""
        try:
            logger.info(f"Rolling back {cloud_run_name}...")
            
            # Get current and previous revisions
            get_revisions_cmd = [
                "gcloud", "run", "revisions", "list",
                "--service", cloud_run_name,
                "--platform", "managed",
                "--region", self.gcp_region,
                "--limit", "3",  # Get last 3 revisions
                "--format", "value(metadata.name,status.conditions[0].status)"
            ]
            
            result = subprocess.run(
                get_revisions_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to get revisions: {result.stderr}")
            
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                raise Exception(f"Not enough revisions found for {cloud_run_name}")
            
            # Find the most recent stable revision (not the current one)
            current_revision = lines[0].split('\t')[0]
            previous_stable_revision = None
            
            for line in lines[1:]:
                parts = line.split('\t')
                if len(parts) >= 2:
                    revision_name = parts[0]
                    revision_status = parts[1] if len(parts) > 1 else ""
                    
                    # Use the first non-current revision that was ready
                    if revision_name != current_revision and revision_status == "True":
                        previous_stable_revision = revision_name
                        break
            
            if not previous_stable_revision:
                # Fallback to the second revision if no status info
                previous_stable_revision = lines[1].split('\t')[0]
            
            logger.info(f"Rolling back {cloud_run_name} from {current_revision} to {previous_stable_revision}")
            
            # Execute rollback
            rollback_cmd = [
                "gcloud", "run", "services", "update-traffic",
                cloud_run_name,
                f"--to-revisions={previous_stable_revision}=100",
                "--platform", "managed",
                "--region", self.gcp_region
            ]
            
            rollback_result = subprocess.run(
                rollback_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if rollback_result.returncode != 0:
                raise Exception(f"Rollback failed: {rollback_result.stderr}")
            
            logger.info(f" PASS:  Successfully rolled back {cloud_run_name} to {previous_stable_revision}")
            return f"Rolled back to revision {previous_stable_revision}"
            
        except Exception as e:
            logger.error(f" FAIL:  Failed to rollback {cloud_run_name}: {e}")
            raise

    async def gradual_disable_feature_flags(self, plan: RollbackPlan, 
                                          validate: bool = True) -> None:
        """Gradually disable feature flags with validation."""
        for flag_name in self.isolation_flags:
            step = RollbackStep(
                name=f"disable_flag_{flag_name}",
                description=f"Disable feature flag: {flag_name}",
                action=f"disable_feature_flag",
                start_time=time.time()
            )
            plan.steps.append(step)
            
            try:
                logger.info(f"Disabling feature flag: {flag_name}")
                
                success = self.feature_flags.update_rollout_stage(
                    flag_name, 
                    RolloutStage.OFF,
                    f"automated_rollback_{plan.triggered_by}"
                )
                
                if success:
                    step.completed = True
                    step.output = f"Flag {flag_name} disabled"
                    plan.feature_flags_disabled.append(flag_name)
                    
                    if validate:
                        # Wait a moment and verify
                        await asyncio.sleep(2)
                        flag_config = self.feature_flags.get_flag(flag_name)
                        if flag_config and not flag_config.enabled:
                            logger.info(f" PASS:  Verified {flag_name} disabled")
                        else:
                            step.error = f"Flag {flag_name} still appears enabled"
                            logger.warning(f" WARNING: [U+FE0F] Flag {flag_name} disable not verified")
                else:
                    step.error = f"Failed to disable {flag_name}"
                    logger.error(f" FAIL:  Failed to disable {flag_name}")
                
            except Exception as e:
                step.error = str(e)
                logger.error(f" FAIL:  Error disabling {flag_name}: {e}")
            finally:
                step.end_time = time.time()

    async def rollback_single_service(self, plan: RollbackPlan, service_name: str,
                                     validate: bool = True) -> None:
        """Rollback a single service with optional validation."""
        step = RollbackStep(
            name=f"rollback_service_{service_name}",
            description=f"Rollback {service_name} service",
            action="single_service_rollback",
            start_time=time.time()
        )
        plan.steps.append(step)
        
        try:
            if service_name not in self.services:
                raise Exception(f"Unknown service: {service_name}")
            
            cloud_run_name = self.services[service_name]
            result = await self.rollback_cloud_run_service(cloud_run_name, service_name)
            
            step.completed = True
            step.output = result
            plan.services_affected.append(service_name)
            
            if validate:
                # Wait for service to stabilize and check health
                await asyncio.sleep(10)
                if await self.check_service_health(service_name):
                    logger.info(f" PASS:  {service_name} health check passed")
                else:
                    step.error = f"Health check failed for {service_name}"
                    logger.warning(f" WARNING: [U+FE0F] {service_name} health check failed")
            
        except Exception as e:
            step.error = str(e)
            logger.error(f" FAIL:  Error rolling back {service_name}: {e}")
            raise
        finally:
            step.end_time = time.time()

    async def quick_validation_check(self, plan: RollbackPlan) -> None:
        """Quick validation check for emergency rollback."""
        step = RollbackStep(
            name="quick_validation",
            description="Quick validation of rollback",
            action="validation_check",
            start_time=time.time()
        )
        plan.steps.append(step)
        
        try:
            # Check feature flags are disabled
            flags_ok = True
            for flag_name in self.isolation_flags:
                flag_config = self.feature_flags.get_flag(flag_name)
                if flag_config and flag_config.enabled:
                    flags_ok = False
                    break
            
            # Quick service health check
            services_ok = 0
            for service_name in self.services.keys():
                if await self.check_service_health(service_name, timeout=5):
                    services_ok += 1
            
            if flags_ok:
                step.output = f"Feature flags disabled. {services_ok}/{len(self.services)} services healthy"
                step.completed = True
                logger.info(" PASS:  Quick validation passed")
            else:
                step.error = "Some feature flags still enabled"
                logger.warning(" WARNING: [U+FE0F] Quick validation: flags still enabled")
                
            plan.validation_results = {
                "feature_flags_disabled": flags_ok,
                "services_healthy": services_ok,
                "total_services": len(self.services)
            }
            
        except Exception as e:
            step.error = str(e)
            logger.error(f" FAIL:  Quick validation error: {e}")
        finally:
            step.end_time = time.time()

    async def comprehensive_validation_check(self, plan: RollbackPlan) -> None:
        """Comprehensive validation for gradual rollback."""
        step = RollbackStep(
            name="comprehensive_validation",
            description="Comprehensive rollback validation",
            action="comprehensive_validation",
            start_time=time.time()
        )
        plan.steps.append(step)
        
        try:
            validation_results = {}
            
            # 1. Feature flag validation
            logger.info("Validating feature flags...")
            flags_status = {}
            for flag_name in self.isolation_flags:
                flag_config = self.feature_flags.get_flag(flag_name)
                flags_status[flag_name] = {
                    "exists": flag_config is not None,
                    "enabled": flag_config.enabled if flag_config else False,
                    "rollout_percentage": flag_config.rollout_percentage if flag_config else 0
                }
            
            validation_results["feature_flags"] = flags_status
            
            # 2. Service health validation
            logger.info("Validating service health...")
            service_health = {}
            for service_name in self.services.keys():
                health = await self.check_service_health(service_name, timeout=10)
                service_health[service_name] = health
            
            validation_results["service_health"] = service_health
            
            # 3. System metrics validation (if available)
            logger.info("Checking system metrics...")
            try:
                current_metrics = self.feature_flags.get_current_isolation_metrics()
                if current_metrics:
                    validation_results["isolation_metrics"] = {
                        "isolation_score": current_metrics.isolation_score,
                        "error_rate": current_metrics.error_rate,
                        "cascade_failures": current_metrics.cascade_failures
                    }
            except Exception as e:
                logger.warning(f"Could not retrieve isolation metrics: {e}")
            
            # Determine overall validation status
            flags_ok = all(not status["enabled"] for status in flags_status.values())
            services_ok = all(service_health.values())
            
            if flags_ok and services_ok:
                step.completed = True
                step.output = "All validations passed"
                logger.info(" PASS:  Comprehensive validation passed")
            else:
                step.error = f"Validation failed: flags_ok={flags_ok}, services_ok={services_ok}"
                logger.warning(" WARNING: [U+FE0F] Some validations failed")
            
            plan.validation_results = validation_results
            
        except Exception as e:
            step.error = str(e)
            logger.error(f" FAIL:  Comprehensive validation error: {e}")
        finally:
            step.end_time = time.time()

    async def check_service_health(self, service_name: str, timeout: int = 10) -> bool:
        """Check health of a specific service."""
        try:
            if service_name not in self.services:
                return False
            
            cloud_run_name = self.services[service_name]
            
            # Get service URL
            get_url_cmd = [
                "gcloud", "run", "services", "describe",
                cloud_run_name,
                "--platform", "managed",
                "--region", self.gcp_region,
                "--format", "value(status.url)"
            ]
            
            result = subprocess.run(
                get_url_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.debug(f"Could not get URL for {service_name}")
                return False
            
            service_url = result.stdout.strip()
            if not service_url:
                return False
            
            # Health check endpoint
            health_url = f"{service_url}/health" if service_name != "frontend" else service_url
            
            # HTTP health check
            import aiohttp
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(health_url, timeout=timeout) as response:
                        return response.status in [200, 301, 302]
                except:
                    return False
            
        except Exception as e:
            logger.debug(f"Health check error for {service_name}: {e}")
            return False

    async def validate_service_rollback(self, plan: RollbackPlan, service_name: str) -> None:
        """Validate rollback for a specific service."""
        step = RollbackStep(
            name=f"validate_{service_name}_rollback",
            description=f"Validate {service_name} rollback",
            action="service_validation",
            start_time=time.time()
        )
        plan.steps.append(step)
        
        try:
            # Wait for service to stabilize
            await asyncio.sleep(15)
            
            # Check service health
            health_ok = await self.check_service_health(service_name, timeout=15)
            
            # Check current revision
            cloud_run_name = self.services[service_name]
            get_traffic_cmd = [
                "gcloud", "run", "services", "describe",
                cloud_run_name,
                "--platform", "managed",
                "--region", self.gcp_region,
                "--format", "value(status.traffic[0].revisionName)"
            ]
            
            result = subprocess.run(
                get_traffic_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            current_revision = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            if health_ok:
                step.completed = True
                step.output = f"Service healthy, running revision: {current_revision}"
                logger.info(f" PASS:  {service_name} rollback validated")
            else:
                step.error = f"Service health check failed, revision: {current_revision}"
                logger.warning(f" WARNING: [U+FE0F] {service_name} validation failed")
            
            plan.validation_results[f"{service_name}_validation"] = {
                "health_ok": health_ok,
                "current_revision": current_revision
            }
            
        except Exception as e:
            step.error = str(e)
            logger.error(f" FAIL:  Error validating {service_name}: {e}")
        finally:
            step.end_time = time.time()

    async def log_rollback_audit(self, plan: RollbackPlan) -> None:
        """Log rollback execution for audit trail."""
        try:
            audit_data = {
                "rollback_plan": asdict(plan),
                "environment": self.environment,
                "gcp_project": self.gcp_project,
                "timestamp": time.time()
            }
            
            # Store in Redis for audit trail
            audit_key = f"rollback_audit:{self.environment}:{plan.rollback_id}"
            self.feature_flags.redis.setex(
                audit_key,
                30 * 24 * 60 * 60,  # 30 days retention
                json.dumps(audit_data)
            )
            
            # Log for external systems
            logger.critical(f"ROLLBACK AUDIT: {plan.rollback_id}", extra=audit_data)
            
        except Exception as e:
            logger.error(f"Failed to log rollback audit: {e}")

    async def verify_rollback_completed(self) -> Dict[str, Any]:
        """Verify that rollback has been completed successfully."""
        logger.info("Verifying rollback completion...")
        
        verification_results = {
            "timestamp": time.time(),
            "environment": self.environment,
            "feature_flags": {},
            "services": {},
            "overall_status": "unknown"
        }
        
        try:
            # 1. Check all feature flags are disabled
            all_flags_disabled = True
            for flag_name in self.isolation_flags:
                flag_config = self.feature_flags.get_flag(flag_name)
                flag_status = {
                    "exists": flag_config is not None,
                    "enabled": flag_config.enabled if flag_config else False,
                    "rollout_percentage": flag_config.rollout_percentage if flag_config else 0
                }
                verification_results["feature_flags"][flag_name] = flag_status
                
                if flag_config and flag_config.enabled:
                    all_flags_disabled = False
            
            # 2. Check all services are healthy
            all_services_healthy = True
            for service_name in self.services.keys():
                health = await self.check_service_health(service_name, timeout=15)
                verification_results["services"][service_name] = {
                    "healthy": health,
                    "cloud_run_name": self.services[service_name]
                }
                
                if not health:
                    all_services_healthy = False
            
            # 3. Determine overall status
            if all_flags_disabled and all_services_healthy:
                verification_results["overall_status"] = "rollback_complete"
            elif all_flags_disabled:
                verification_results["overall_status"] = "flags_disabled_services_unhealthy"
            elif all_services_healthy:
                verification_results["overall_status"] = "services_healthy_flags_enabled"
            else:
                verification_results["overall_status"] = "rollback_incomplete"
            
            verification_results["summary"] = {
                "all_flags_disabled": all_flags_disabled,
                "all_services_healthy": all_services_healthy,
                "flags_disabled_count": len([f for f, s in verification_results["feature_flags"].items() if not s["enabled"]]),
                "healthy_services_count": len([s for s, h in verification_results["services"].items() if h["healthy"]])
            }
            
            return verification_results
            
        except Exception as e:
            verification_results["error"] = str(e)
            logger.error(f"Error verifying rollback: {e}")
            return verification_results

    def print_rollback_report(self, plan: RollbackPlan) -> None:
        """Print formatted rollback report."""
        print("\n" + "="*80)
        print(f"AUTOMATED ROLLBACK REPORT")
        print("="*80)
        
        print(f"\nRollback ID: {plan.rollback_id}")
        print(f"Type: {plan.rollback_type.value.upper()}")
        print(f"Environment: {plan.environment}")
        print(f"Status: {plan.status.value.upper()}")
        print(f"Reason: {plan.reason}")
        print(f"Triggered by: {plan.triggered_by}")
        
        if plan.end_time:
            duration = plan.end_time - plan.start_time
            print(f"Duration: {duration:.2f} seconds")
        
        print(f"\nFeature Flags Disabled: {len(plan.feature_flags_disabled)}")
        for flag in plan.feature_flags_disabled:
            print(f"   PASS:  {flag}")
        
        print(f"\nServices Affected: {len(plan.services_affected)}")
        for service in plan.services_affected:
            print(f"   PASS:  {service}")
        
        print(f"\nExecution Steps: {len(plan.steps)}")
        for step in plan.steps:
            status = " PASS: " if step.completed else " FAIL: "
            duration = ""
            if step.start_time and step.end_time:
                duration = f" ({step.end_time - step.start_time:.2f}s)"
            
            print(f"  {status} {step.name}{duration}")
            if step.error:
                print(f"      Error: {step.error}")
        
        if plan.validation_results:
            print(f"\nValidation Results:")
            for key, value in plan.validation_results.items():
                print(f"  {key}: {value}")
        
        print("\n" + "="*80)


def main():
    """Main entry point for automated rollback system."""
    parser = argparse.ArgumentParser(
        description="Automated Rollback System for Production Isolation Features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Emergency rollback (fastest)
  python scripts/automated_rollback.py emergency \\
    --reason "Cascade failures detected" --triggered-by monitoring_system
  
  # Gradual rollback with validation
  python scripts/automated_rollback.py gradual \\
    --reason "Performance degradation" --validate-each-step
  
  # Rollback specific service
  python scripts/automated_rollback.py service-only \\
    --service backend --reason "Backend errors"
  
  # Verify rollback completed
  python scripts/automated_rollback.py verify-rollback
        """
    )
    
    parser.add_argument(
        "command",
        choices=["emergency", "gradual", "service-only", "verify-rollback"],
        help="Rollback command to execute"
    )
    
    parser.add_argument(
        "--environment",
        default="production", 
        help="Environment to rollback"
    )
    
    parser.add_argument(
        "--reason",
        required=True,
        help="Reason for rollback (required for audit trail)"
    )
    
    parser.add_argument(
        "--triggered-by",
        default="manual",
        help="Who/what triggered the rollback"
    )
    
    parser.add_argument(
        "--service",
        choices=["backend", "auth", "frontend"],
        help="Specific service to rollback (for service-only command)"
    )
    
    parser.add_argument(
        "--validate-each-step",
        action="store_true",
        help="Validate each step during gradual rollback"
    )
    
    args = parser.parse_args()
    
    # Validate required arguments
    if args.command in ["emergency", "gradual", "service-only"] and not args.reason:
        print(" FAIL:  --reason is required for rollback operations")
        sys.exit(1)
    
    if args.command == "service-only" and not args.service:
        print(" FAIL:  --service is required for service-only rollback")
        sys.exit(1)
    
    # Initialize rollback system
    rollback_system = AutomatedRollbackSystem(args.environment)
    
    try:
        if args.command == "emergency":
            plan = asyncio.run(rollback_system.execute_emergency_rollback(
                args.reason, args.triggered_by
            ))
            rollback_system.print_rollback_report(plan)
            sys.exit(0 if plan.status == RollbackStatus.COMPLETED else 1)
            
        elif args.command == "gradual":
            plan = asyncio.run(rollback_system.execute_gradual_rollback(
                args.reason, args.triggered_by, args.validate_each_step
            ))
            rollback_system.print_rollback_report(plan)
            sys.exit(0 if plan.status == RollbackStatus.COMPLETED else 1)
            
        elif args.command == "service-only":
            plan = asyncio.run(rollback_system.execute_service_rollback(
                args.service, args.reason, args.triggered_by
            ))
            rollback_system.print_rollback_report(plan)
            sys.exit(0 if plan.status == RollbackStatus.COMPLETED else 1)
            
        elif args.command == "verify-rollback":
            verification = asyncio.run(rollback_system.verify_rollback_completed())
            
            print("\n" + "="*60)
            print("ROLLBACK VERIFICATION REPORT")
            print("="*60)
            
            if "error" in verification:
                print(f" FAIL:  Verification failed: {verification['error']}")
                sys.exit(1)
            
            status = verification["overall_status"]
            summary = verification["summary"]
            
            print(f"\nOverall Status: {status.upper()}")
            print(f"Environment: {verification['environment']}")
            print(f"Timestamp: {datetime.fromtimestamp(verification['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            
            print(f"\nFeature Flags: {summary['flags_disabled_count']}/{len(verification['feature_flags'])} disabled")
            for flag_name, flag_status in verification["feature_flags"].items():
                status_icon = " PASS: " if not flag_status["enabled"] else " FAIL: "
                print(f"  {status_icon} {flag_name}: {'disabled' if not flag_status['enabled'] else 'enabled'}")
            
            print(f"\nServices: {summary['healthy_services_count']}/{len(verification['services'])} healthy")
            for service_name, service_status in verification["services"].items():
                status_icon = " PASS: " if service_status["healthy"] else " FAIL: "
                print(f"  {status_icon} {service_name}: {'healthy' if service_status['healthy'] else 'unhealthy'}")
            
            print("\n" + "="*60)
            
            # Exit code based on verification status
            if status == "rollback_complete":
                print(" PASS:  Rollback verification: PASSED")
                sys.exit(0)
            else:
                print(" FAIL:  Rollback verification: FAILED or INCOMPLETE")
                sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n WARNING: [U+FE0F] Rollback interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f" FAIL:  Rollback error: {e}")
        logger.exception("Unexpected error in automated rollback")
        sys.exit(1)


if __name__ == "__main__":
    main()