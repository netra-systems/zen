#!/usr/bin/env python3
"""
Production Rollout Control Script
=================================

Command-line interface for managing production rollout of isolation features
with zero-downtime deployment and instant rollback capabilities.

This script provides safe, auditable control over feature flag rollouts
with comprehensive logging and safety checks.

Usage Examples:
    # Check current rollout status
    python scripts/production_rollout_control.py status --environment production
    
    # Update rollout stage
    python scripts/production_rollout_control.py update-stage \
        --flag request_isolation --stage canary --updated-by deployment_team
    
    # Emergency disable all features
    python scripts/production_rollout_control.py emergency-disable \
        --reason "Production incident" --updated-by incident_response
    
    # Initialize production feature flags
    python scripts/production_rollout_control.py init --environment production
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional, List
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.feature_flags import (
    ProductionFeatureFlags, 
    FeatureFlagConfig, 
    RolloutStage, 
    IsolationMetrics,
    get_feature_flags
)
from shared.isolated_environment import IsolatedEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionRolloutController:
    """Controller for managing production feature flag rollouts."""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.env = IsolatedEnvironment.get_instance()
        self.feature_flags = ProductionFeatureFlags(environment)
        
        # Isolation feature flags
        self.isolation_flags = [
            "request_isolation",
            "factory_pattern", 
            "websocket_isolation",
            "database_session_isolation",
            "context_isolation"
        ]
        
        logger.info(f"Initialized ProductionRolloutController for {environment}")

    def initialize_flags(self) -> bool:
        """Initialize all isolation feature flags in disabled state."""
        logger.info("Initializing production feature flags...")
        
        success_count = 0
        
        for flag_name in self.isolation_flags:
            config = FeatureFlagConfig(
                name=flag_name,
                enabled=False,
                rollout_percentage=0.0,
                rollout_stage=RolloutStage.OFF,
                internal_users_only=False,
                circuit_breaker_threshold=0.99,  # 99% isolation score required
                circuit_breaker_open=False,
                updated_by="init_script",
                metadata={
                    "description": f"Production rollout flag for {flag_name}",
                    "created_at": time.time(),
                    "environment": self.environment,
                    "safety_level": "high"
                }
            )
            
            if self.feature_flags.create_flag(flag_name, config):
                logger.info(f" PASS:  Initialized flag: {flag_name}")
                success_count += 1
            else:
                logger.error(f" FAIL:  Failed to initialize flag: {flag_name}")
        
        logger.info(f"Initialized {success_count}/{len(self.isolation_flags)} flags")
        return success_count == len(self.isolation_flags)

    def get_status(self, detailed: bool = False) -> Dict:
        """Get current rollout status."""
        logger.info("Retrieving rollout status...")
        
        status = {
            "environment": self.environment,
            "timestamp": time.time(),
            "flags": {},
            "overall_status": "unknown",
            "isolation_metrics": None
        }
        
        # Get all flags
        flags = self.feature_flags.get_all_flags()
        active_flags = 0
        total_percentage = 0.0
        
        for flag_name in self.isolation_flags:
            if flag_name in flags:
                flag_config = flags[flag_name]
                
                flag_status = {
                    "enabled": flag_config.enabled,
                    "rollout_stage": flag_config.rollout_stage.value,
                    "rollout_percentage": flag_config.rollout_percentage,
                    "circuit_breaker_open": flag_config.circuit_breaker_open,
                    "last_updated": flag_config.last_updated,
                    "updated_by": flag_config.updated_by
                }
                
                if detailed:
                    flag_status.update({
                        "internal_users_only": flag_config.internal_users_only,
                        "circuit_breaker_threshold": flag_config.circuit_breaker_threshold,
                        "metadata": flag_config.metadata
                    })
                
                status["flags"][flag_name] = flag_status
                
                if flag_config.enabled:
                    active_flags += 1
                    total_percentage += flag_config.rollout_percentage
            else:
                status["flags"][flag_name] = {
                    "enabled": False,
                    "rollout_stage": "not_found",
                    "error": "Flag not found - may need initialization"
                }
        
        # Determine overall status
        if active_flags == 0:
            status["overall_status"] = "off"
        elif active_flags == len(self.isolation_flags):
            avg_percentage = total_percentage / len(self.isolation_flags)
            if avg_percentage == 0:
                status["overall_status"] = "off"
            elif avg_percentage <= 10:
                status["overall_status"] = "canary"
            elif avg_percentage <= 50:
                status["overall_status"] = "staged"
            elif avg_percentage >= 100:
                status["overall_status"] = "full"
            else:
                status["overall_status"] = "partial"
        else:
            status["overall_status"] = "inconsistent"
        
        # Get isolation metrics if available
        metrics = self.feature_flags.get_current_isolation_metrics()
        if metrics:
            status["isolation_metrics"] = {
                "isolation_score": metrics.isolation_score,
                "total_requests": metrics.total_requests,
                "failed_requests": metrics.failed_requests,
                "cascade_failures": metrics.cascade_failures,
                "error_rate": metrics.error_rate,
                "response_time_p95": metrics.response_time_p95,
                "last_cascade_failure": metrics.last_cascade_failure,
                "timestamp": metrics.timestamp
            }
        
        return status

    def update_stage(self, flag_name: str, stage: RolloutStage, updated_by: str) -> bool:
        """Update a specific flag to a rollout stage."""
        if flag_name not in self.isolation_flags:
            logger.error(f"Unknown flag: {flag_name}. Valid flags: {self.isolation_flags}")
            return False
        
        logger.info(f"Updating {flag_name} to stage {stage.value} by {updated_by}")
        
        # Safety checks before updating
        if stage != RolloutStage.OFF:
            if not self._safety_checks_passed():
                logger.error("Safety checks failed - aborting stage update")
                return False
        
        success = self.feature_flags.update_rollout_stage(flag_name, stage, updated_by)
        
        if success:
            logger.info(f" PASS:  Successfully updated {flag_name} to {stage.value}")
            
            # Log audit trail
            self._log_audit_event("stage_update", {
                "flag_name": flag_name,
                "new_stage": stage.value,
                "updated_by": updated_by,
                "timestamp": time.time()
            })
        else:
            logger.error(f" FAIL:  Failed to update {flag_name} to {stage.value}")
        
        return success

    def update_all_flags_to_stage(self, stage: RolloutStage, updated_by: str) -> bool:
        """Update all isolation flags to the same stage."""
        logger.info(f"Updating all flags to stage {stage.value} by {updated_by}")
        
        # Safety checks for non-off stages
        if stage != RolloutStage.OFF:
            if not self._safety_checks_passed():
                logger.error("Safety checks failed - aborting mass update")
                return False
        
        success_count = 0
        
        for flag_name in self.isolation_flags:
            if self.update_stage(flag_name, stage, updated_by):
                success_count += 1
        
        all_successful = success_count == len(self.isolation_flags)
        
        if all_successful:
            logger.info(f" PASS:  Successfully updated all {len(self.isolation_flags)} flags to {stage.value}")
        else:
            logger.error(f" FAIL:  Only {success_count}/{len(self.isolation_flags)} flags updated successfully")
        
        return all_successful

    def emergency_disable(self, reason: str, updated_by: str) -> bool:
        """Emergency disable all isolation features."""
        logger.critical(f"EMERGENCY DISABLE initiated by {updated_by}: {reason}")
        
        # Use the emergency disable function from feature flags
        success = self.feature_flags.emergency_disable_all(reason, updated_by)
        
        if success:
            logger.critical(" PASS:  Emergency disable completed successfully")
            
            # Log critical audit event
            self._log_audit_event("emergency_disable", {
                "reason": reason,
                "updated_by": updated_by,
                "timestamp": time.time(),
                "all_flags_disabled": True
            })
        else:
            logger.critical(" FAIL:  Emergency disable failed - manual intervention required")
        
        return success

    def emergency_rollback(self, reason: str) -> bool:
        """Emergency rollback to previous Cloud Run revisions."""
        logger.critical(f"EMERGENCY ROLLBACK initiated: {reason}")
        
        try:
            import subprocess
            
            # Disable feature flags first
            self.emergency_disable(reason, "emergency_rollback")
            
            # Rollback services to previous revision
            services = [
                "netra-backend-production",
                "netra-auth-service-production" 
            ]
            
            for service in services:
                logger.info(f"Rolling back {service}...")
                
                # Get previous revision
                get_revisions_cmd = [
                    "gcloud", "run", "revisions", "list",
                    "--service", service,
                    "--platform", "managed",
                    "--region", "us-central1",
                    "--limit", "2",
                    "--format", "value(metadata.name)"
                ]
                
                result = subprocess.run(
                    get_revisions_cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    revisions = result.stdout.strip().split('\n')
                    if len(revisions) >= 2:
                        previous_revision = revisions[1]  # Second revision (previous)
                        
                        # Update traffic to previous revision
                        rollback_cmd = [
                            "gcloud", "run", "services", "update-traffic",
                            service,
                            f"--to-revisions={previous_revision}=100",
                            "--platform", "managed",
                            "--region", "us-central1"
                        ]
                        
                        rollback_result = subprocess.run(
                            rollback_cmd,
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        
                        if rollback_result.returncode == 0:
                            logger.info(f" PASS:  Successfully rolled back {service} to {previous_revision}")
                        else:
                            logger.error(f" FAIL:  Failed to rollback {service}: {rollback_result.stderr}")
                            return False
                    else:
                        logger.error(f" FAIL:  Not enough revisions found for {service}")
                        return False
                else:
                    logger.error(f" FAIL:  Failed to get revisions for {service}: {result.stderr}")
                    return False
            
            logger.critical(" PASS:  Emergency rollback completed successfully")
            return True
            
        except Exception as e:
            logger.critical(f" FAIL:  Emergency rollback failed: {e}")
            return False

    def verify_full_deployment(self) -> bool:
        """Verify that full deployment is successful."""
        logger.info("Verifying full deployment status...")
        
        status = self.get_status(detailed=True)
        
        # Check all flags are at 100%
        for flag_name in self.isolation_flags:
            if flag_name not in status["flags"]:
                logger.error(f" FAIL:  Flag not found: {flag_name}")
                return False
            
            flag_status = status["flags"][flag_name]
            
            if not flag_status.get("enabled", False):
                logger.error(f" FAIL:  Flag not enabled: {flag_name}")
                return False
            
            if flag_status.get("rollout_percentage", 0) < 100:
                logger.error(f" FAIL:  Flag not at 100%: {flag_name} ({flag_status.get('rollout_percentage', 0)}%)")
                return False
            
            if flag_status.get("circuit_breaker_open", False):
                logger.error(f" FAIL:  Circuit breaker open: {flag_name}")
                return False
        
        # Check isolation metrics
        metrics = status.get("isolation_metrics")
        if metrics:
            if metrics.get("isolation_score", 0) < 0.99:
                logger.error(f" FAIL:  Isolation score too low: {metrics.get('isolation_score', 0)}")
                return False
            
            if metrics.get("cascade_failures", 0) > 0:
                logger.error(f" FAIL:  Cascade failures detected: {metrics.get('cascade_failures', 0)}")
                return False
            
            if metrics.get("error_rate", 0) > 0.01:
                logger.error(f" FAIL:  Error rate too high: {metrics.get('error_rate', 0)}")
                return False
        
        logger.info(" PASS:  Full deployment verification successful")
        return True

    def _safety_checks_passed(self) -> bool:
        """Run safety checks before enabling features."""
        logger.info("Running safety checks...")
        
        # Check Redis connectivity
        try:
            self.feature_flags.redis.ping()
            logger.info(" PASS:  Redis connectivity verified")
        except Exception as e:
            logger.error(f" FAIL:  Redis connectivity failed: {e}")
            return False
        
        # Check environment
        if self.environment not in ["staging", "production"]:
            logger.warning(f" WARNING: [U+FE0F] Unusual environment: {self.environment}")
        
        # Check current isolation metrics
        metrics = self.feature_flags.get_current_isolation_metrics()
        if metrics:
            if metrics.isolation_score < 0.95:
                logger.error(f" FAIL:  Current isolation score too low: {metrics.isolation_score}")
                return False
            
            if metrics.cascade_failures > 0:
                logger.error(f" FAIL:  Active cascade failures: {metrics.cascade_failures}")
                return False
        
        logger.info(" PASS:  All safety checks passed")
        return True

    def _log_audit_event(self, event_type: str, details: Dict) -> None:
        """Log audit events for compliance and debugging."""
        audit_event = {
            "event_type": event_type,
            "environment": self.environment,
            "timestamp": time.time(),
            "details": details
        }
        
        # Log to application logs
        logger.info(f"AUDIT: {event_type}", extra=audit_event)
        
        # Store in Redis for audit trail
        try:
            audit_key = f"audit_trail:{self.environment}:{int(time.time())}"
            self.feature_flags.redis.setex(
                audit_key, 
                30 * 24 * 60 * 60,  # 30 days
                json.dumps(audit_event)
            )
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")

    def print_status_report(self, status: Dict, detailed: bool = False) -> None:
        """Print formatted status report."""
        print("\n" + "="*60)
        print(f"PRODUCTION ROLLOUT STATUS - {status['environment'].upper()}")
        print("="*60)
        
        print(f"\nOverall Status: {status['overall_status'].upper()}")
        print(f"Timestamp: {time.ctime(status['timestamp'])}")
        
        # Isolation metrics
        if status.get('isolation_metrics'):
            metrics = status['isolation_metrics']
            print(f"\nIsolation Metrics:")
            print(f"  Score: {metrics['isolation_score']:.1%}")
            print(f"  Total Requests: {metrics['total_requests']:,}")
            print(f"  Error Rate: {metrics['error_rate']:.2%}")
            print(f"  Cascade Failures: {metrics['cascade_failures']}")
            if metrics['last_cascade_failure']:
                print(f"  Last Cascade: {time.ctime(metrics['last_cascade_failure'])}")
        
        # Flag status
        print(f"\nFeature Flags:")
        for flag_name, flag_status in status['flags'].items():
            enabled = " PASS:  ON " if flag_status.get('enabled', False) else " FAIL:  OFF"
            stage = flag_status.get('rollout_stage', 'unknown')
            percentage = flag_status.get('rollout_percentage', 0)
            circuit = " ALERT:  OPEN" if flag_status.get('circuit_breaker_open', False) else ""
            
            print(f"  {flag_name:25} {enabled} {stage:10} {percentage:5.1f}% {circuit}")
            
            if detailed and 'last_updated' in flag_status:
                updated_time = time.ctime(flag_status['last_updated'])
                updated_by = flag_status.get('updated_by', 'unknown')
                print(f"    [U+2514][U+2500] Updated: {updated_time} by {updated_by}")
        
        print("\n" + "="*60)


def main():
    """Main entry point for production rollout control."""
    parser = argparse.ArgumentParser(
        description="Production Rollout Control for Isolation Features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check current status
  python scripts/production_rollout_control.py status --environment production
  
  # Initialize flags (first time setup)
  python scripts/production_rollout_control.py init --environment production
  
  # Update to canary stage
  python scripts/production_rollout_control.py update-stage \\
    --flag request_isolation --stage canary --updated-by deployment_team
  
  # Update all flags to staged
  python scripts/production_rollout_control.py update-all-stages \\
    --stage staged --updated-by deployment_team
  
  # Emergency disable
  python scripts/production_rollout_control.py emergency-disable \\
    --reason "Production incident" --updated-by incident_response
        """
    )
    
    parser.add_argument(
        "command",
        choices=["status", "init", "update-stage", "update-all-stages", 
                "emergency-disable", "emergency-rollback", "verify-full-deployment"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--environment", 
        default="production",
        help="Environment (production, staging, development)"
    )
    
    parser.add_argument(
        "--flag",
        choices=["request_isolation", "factory_pattern", "websocket_isolation", 
                "database_session_isolation", "context_isolation"],
        help="Specific feature flag to update"
    )
    
    parser.add_argument(
        "--stage",
        choices=["off", "internal", "canary", "staged", "full"],
        help="Rollout stage"
    )
    
    parser.add_argument(
        "--updated-by",
        default="script",
        help="Who is making the update (for audit trail)"
    )
    
    parser.add_argument(
        "--reason",
        help="Reason for emergency actions"
    )
    
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information"
    )
    
    args = parser.parse_args()
    
    # Initialize controller
    controller = ProductionRolloutController(args.environment)
    
    try:
        if args.command == "status":
            status = controller.get_status(detailed=args.detailed)
            controller.print_status_report(status, detailed=args.detailed)
            
        elif args.command == "init":
            success = controller.initialize_flags()
            sys.exit(0 if success else 1)
            
        elif args.command == "update-stage":
            if not args.flag or not args.stage:
                print(" FAIL:  --flag and --stage required for update-stage")
                sys.exit(1)
            
            stage = RolloutStage(args.stage)
            success = controller.update_stage(args.flag, stage, args.updated_by)
            sys.exit(0 if success else 1)
            
        elif args.command == "update-all-stages":
            if not args.stage:
                print(" FAIL:  --stage required for update-all-stages")
                sys.exit(1)
            
            stage = RolloutStage(args.stage)
            success = controller.update_all_flags_to_stage(stage, args.updated_by)
            sys.exit(0 if success else 1)
            
        elif args.command == "emergency-disable":
            if not args.reason:
                print(" FAIL:  --reason required for emergency-disable")
                sys.exit(1)
            
            success = controller.emergency_disable(args.reason, args.updated_by)
            sys.exit(0 if success else 1)
            
        elif args.command == "emergency-rollback":
            if not args.reason:
                print(" FAIL:  --reason required for emergency-rollback")
                sys.exit(1)
            
            success = controller.emergency_rollback(args.reason)
            sys.exit(0 if success else 1)
            
        elif args.command == "verify-full-deployment":
            success = controller.verify_full_deployment()
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n WARNING: [U+FE0F] Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f" FAIL:  Error: {e}")
        logger.exception("Unexpected error in rollout control")
        sys.exit(1)


if __name__ == "__main__":
    main()