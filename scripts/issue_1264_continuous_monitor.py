"""
Issue #1264 Continuous Monitoring Script

This script continuously monitors the staging environment to confirm the
PostgreSQL/asyncpg configuration remains healthy and to detect when the
backend service recovers from the Issue #1263 startup failure.

When the infrastructure recovers, it automatically runs the comprehensive
validation suite and reports the results.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Immediate detection of infrastructure fix application
- Value Impact: Reduces time to validation and enables rapid response
- Strategic Impact: Minimizes downtime and ensures quick Golden Path restoration

Usage:
    python scripts/issue_1264_continuous_monitor.py --interval 60 --max-checks 1440
"""

import asyncio
import argparse
import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Project imports
from tests.validation.issue_1264_staging_validation_suite import Issue1264StagingValidator
from shared.isolated_environment import IsolatedEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('issue_1264_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Issue1264ContinuousMonitor:
    """
    Continuous monitor for Issue #1264 regression signals.

    Monitors staging environment health, keeps watch on asyncpg/PostgreSQL
    connectivity, and highlights when backend recovery (Issue #1263) occurs.
    """

    def __init__(self, check_interval: int = 60, max_checks: int = 1440):
        """
        Initialize continuous monitor.

        Args:
            check_interval: Seconds between health checks (default: 60s)
            max_checks: Maximum number of checks before stopping (default: 1440 = 24 hours)
        """
        self.env = IsolatedEnvironment()
        self.validator = Issue1264StagingValidator()
        self.check_interval = check_interval
        self.max_checks = max_checks

        self.check_count = 0
        self.start_time = time.time()
        self.last_health_status = None
        self.fix_detected = False

        # Monitoring state
        self.monitoring_log_file = "issue_1264_monitoring_log.json"
        self.results_file = "issue_1264_validation_results.json"

    def log_monitoring_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log monitoring event to file."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "check_number": self.check_count,
            "elapsed_time": time.time() - self.start_time,
            "data": data
        }

        # Append to monitoring log
        try:
            if Path(self.monitoring_log_file).exists():
                with open(self.monitoring_log_file, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = {"monitoring_session": [], "start_time": self.start_time}

            log_data["monitoring_session"].append(log_entry)

            with open(self.monitoring_log_file, 'w') as f:
                json.dump(log_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to log monitoring event: {e}")

    async def quick_health_check(self) -> Dict[str, Any]:
        """
        Perform quick health check to detect infrastructure changes.

        This is a lightweight check to detect when the fix is applied
        without running the full validation suite each time.
        """
        start_time = time.time()

        try:
            # Quick database connectivity test
            db_result = await self.validator.validate_database_connectivity()

            # Quick health endpoint test
            health_result = await self.validator.validate_health_endpoint()

            health_check = {
                "database_connectivity": db_result.success,
                "database_connection_time": db_result.execution_time,
                "health_endpoint": health_result.success,
                "health_response_time": health_result.execution_time,
                "overall_healthy": db_result.success and health_result.success,
                "check_duration": time.time() - start_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Add error details if any
            if not db_result.success:
                health_check["database_error"] = db_result.error_message
                logger.warning("Database connectivity failed. Run scripts/issue_1264_config_audit.py to verify secrets and driver state.")
            if db_result.success and not health_result.success:
                health_check["health_endpoint_error"] = health_result.error_message
                logger.error("Backend health endpoint failing despite successful PostgreSQL connection. Likely Issue #1263 backend startup regression.")
            elif not health_result.success:
                health_check["health_endpoint_error"] = health_result.error_message

            return health_check

        except Exception as e:
            return {
                "database_connectivity": False,
                "health_endpoint": False,
                "overall_healthy": False,
                "check_duration": time.time() - start_time,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def detect_infrastructure_fix(self, current_health: Dict[str, Any]) -> bool:
        """
        Detect if infrastructure fix has been applied.

        Returns True if fix is detected based on health status changes.
        """
        if self.last_health_status is None:
            # First check - store baseline
            self.last_health_status = current_health
            return False

        # Check for improvement in health status
        previous_healthy = self.last_health_status.get("overall_healthy", False)
        current_healthy = current_health.get("overall_healthy", False)

        # Check for database connection improvement
        previous_db_time = self.last_health_status.get("database_connection_time", float('inf'))
        current_db_time = current_health.get("database_connection_time", float('inf'))

        # Fix detected if:
        # 1. Health status improved from unhealthy to healthy
        # 2. Database connection time significantly improved (>50% reduction)

        fix_detected = False

        if not previous_healthy and current_healthy:
            logger.info("🎉 Infrastructure fix detected: Health status improved from unhealthy to healthy")
            fix_detected = True

        if (previous_db_time > self.validator.staging_timeout_threshold and
            current_db_time < self.validator.staging_timeout_threshold):
            logger.info(f"🎉 Infrastructure fix detected: Database connection time improved from {previous_db_time:.2f}s to {current_db_time:.2f}s")
            fix_detected = True

        # Significant connection time improvement
        if (previous_db_time > 5.0 and current_db_time < previous_db_time * 0.5):
            logger.info(f"🎉 Infrastructure fix detected: Significant connection time improvement ({previous_db_time:.2f}s → {current_db_time:.2f}s)")
            fix_detected = True

        # Update baseline
        self.last_health_status = current_health

        return fix_detected

    async def run_full_validation(self) -> Dict[str, Any]:
        """
        Run full validation suite when fix is detected.

        Returns comprehensive validation results.
        """
        logger.info("Running comprehensive validation suite...")

        try:
            health_status = await self.validator.run_comprehensive_validation()

            validation_results = {
                "validation_timestamp": health_status.timestamp,
                "overall_health": health_status.overall_health,
                "database_connectivity": health_status.database_connectivity,
                "database_connection_time": health_status.connection_time,
                "health_endpoint_status": health_status.health_endpoint_status,
                "websocket_connectivity": health_status.websocket_connectivity,
                "golden_path_status": health_status.golden_path_status,
                "issue_1264_resolved": health_status.overall_health,
                "detailed_results": health_status.details
            }

            # Save results to file
            with open(self.results_file, 'w') as f:
                json.dump(validation_results, f, indent=2)

            return validation_results

        except Exception as e:
            error_results = {
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                "validation_error": str(e),
                "validation_successful": False
            }

            with open(self.results_file, 'w') as f:
                json.dump(error_results, f, indent=2)

            return error_results

    def print_status_update(self, health_check: Dict[str, Any]) -> None:
        """Print status update to console."""
        elapsed_hours = (time.time() - self.start_time) / 3600

        print(f"\n{'='*60}")
        print(f"Check #{self.check_count} - Elapsed: {elapsed_hours:.1f}h")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Database Connectivity: {'✓' if health_check.get('database_connectivity') else '❌'}")
        print(f"Database Connection Time: {health_check.get('database_connection_time', 0):.2f}s")
        print(f"Health Endpoint: {'✓' if health_check.get('health_endpoint') else '❌'}")
        print(f"Overall Health: {'✓ HEALTHY' if health_check.get('overall_healthy') else '❌ UNHEALTHY'}")

        if not health_check.get('overall_healthy'):
            if health_check.get('database_error'):
                print(f"Database Error: {health_check['database_error'][:100]}...")
            if health_check.get('health_endpoint_error'):
                print(f"Health Error: {health_check['health_endpoint_error'][:100]}...")

        print(f"Next check in {self.check_interval}s...")

    async def start_monitoring(self) -> None:
        """
        Start continuous monitoring for Issue #1264 infrastructure fix.
        """
        logger.info(f"Starting Issue #1264 continuous monitoring")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(f"Maximum checks: {self.max_checks}")
        logger.info(f"Maximum monitoring time: {(self.max_checks * self.check_interval) / 3600:.1f} hours")

        # Validate environment
        current_env = self.env.get('ENVIRONMENT', 'development')
        if current_env.lower() != 'staging':
            logger.error(f"Monitoring requires staging environment (current: {current_env})")
            return

        logger.info(f"Environment validated: {current_env}")

        # Log monitoring start
        self.log_monitoring_event("monitoring_started", {
            "check_interval": self.check_interval,
            "max_checks": self.max_checks,
            "environment": current_env
        })

        print(f"\n🔍 MONITORING STARTED - Issue #1264 Infrastructure Fix Detection")
        print(f"Monitoring staging environment for PostgreSQL configuration fix...")
        print(f"Press Ctrl+C to stop monitoring\n")

        try:
            while self.check_count < self.max_checks and not self.fix_detected:
                self.check_count += 1

                # Perform health check
                health_check = await self.quick_health_check()

                # Log health check
                self.log_monitoring_event("health_check", health_check)

                # Print status update
                self.print_status_update(health_check)

                # Check for infrastructure fix
                if self.detect_infrastructure_fix(health_check):
                    self.fix_detected = True

                    print(f"\n🎉 INFRASTRUCTURE FIX DETECTED!")
                    print(f"Running comprehensive validation suite...")

                    # Log fix detection
                    self.log_monitoring_event("fix_detected", {
                        "detection_check": self.check_count,
                        "elapsed_time": time.time() - self.start_time
                    })

                    # Run full validation
                    validation_results = await self.run_full_validation()

                    # Log validation results
                    self.log_monitoring_event("full_validation", validation_results)

                    # Report results
                    if validation_results.get("overall_health", False):
                        print(f"\n🎉 SUCCESS: Issue #1264 RESOLVED!")
                        print(f"   Staging environment is healthy")
                        print(f"   Database connectivity: ✓")
                        print(f"   Connection time: {validation_results.get('database_connection_time', 0):.2f}s")
                        print(f"   Golden Path: ✓")
                        print(f"\nValidation results saved to: {self.results_file}")
                        logger.info("Issue #1264 successfully resolved and validated")
                    else:
                        print(f"\n⚠️  PARTIAL FIX: Improvement detected but validation failed")
                        print(f"   Some issues may remain - check validation results")
                        print(f"   Validation results saved to: {self.results_file}")
                        logger.warning("Partial fix detected but full validation failed")

                    break

                # Wait for next check
                if not self.fix_detected and self.check_count < self.max_checks:
                    await asyncio.sleep(self.check_interval)

            # Handle monitoring completion
            if self.check_count >= self.max_checks:
                print(f"\n⏰ MONITORING TIMEOUT: Reached maximum checks ({self.max_checks})")
                print(f"   No infrastructure fix detected within monitoring period")
                logger.info(f"Monitoring completed - reached maximum checks without detecting fix")

        except KeyboardInterrupt:
            print(f"\n\n⏹️  MONITORING STOPPED: User interrupted")
            logger.info("Monitoring stopped by user")

        except Exception as e:
            print(f"\n💥 MONITORING ERROR: {e}")
            logger.error(f"Monitoring failed: {e}")

        finally:
            # Log monitoring end
            self.log_monitoring_event("monitoring_ended", {
                "total_checks": self.check_count,
                "total_time": time.time() - self.start_time,
                "fix_detected": self.fix_detected
            })

            elapsed_time = time.time() - self.start_time
            print(f"\nMonitoring Summary:")
            print(f"  Total Checks: {self.check_count}")
            print(f"  Total Time: {elapsed_time/3600:.1f} hours")
            print(f"  Fix Detected: {'Yes' if self.fix_detected else 'No'}")
            print(f"  Log File: {self.monitoring_log_file}")
            if self.fix_detected:
                print(f"  Results File: {self.results_file}")


def main():
    """Main entry point for continuous monitoring."""
    parser = argparse.ArgumentParser(
        description="Continuous monitor for Issue #1264 infrastructure fix detection"
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--max-checks',
        type=int,
        default=1440,  # 24 hours at 60s intervals
        help='Maximum number of checks before stopping (default: 1440 = 24 hours)'
    )
    parser.add_argument(
        '--environment',
        type=str,
        default='staging',
        help='Environment to monitor (default: staging)'
    )

    args = parser.parse_args()

    # Set environment
    env = IsolatedEnvironment()
    env.set('ENVIRONMENT', args.environment, source='monitor_script')

    # Create and start monitor
    monitor = Issue1264ContinuousMonitor(
        check_interval=args.interval,
        max_checks=args.max_checks
    )

    # Run monitoring
    try:
        asyncio.run(monitor.start_monitoring())
    except Exception as e:
        logger.error(f"Monitor failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()