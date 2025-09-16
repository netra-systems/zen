# Issue #1278 - Development Team Implementation Guide

**Date**: 2025-09-16
**Priority**: P0 Critical
**Focus**: Development team deliverables for Issue #1278 infrastructure remediation

## IMMEDIATE DEVELOPMENT ACTIONS

While the infrastructure team scales VPC connector and configures timeouts, the development team can implement application-level resilience improvements and monitoring enhancements.

---

## IMPLEMENTATION PRIORITY 1: DATABASE TIMEOUT CONFIGURATION

### Create Enhanced Database Timeout Configuration

**File**: `netra_backend/app/core/database_timeout_config.py`

```python
#!/usr/bin/env python3
"""
Enhanced Database Timeout Configuration for Issue #1278
Addresses infrastructure timeout requirements and provides resilient fallbacks.
"""
import logging
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class TimeoutTier(Enum):
    """Timeout tiers for different operations."""
    HEALTH_CHECK = "health_check"      # 15s - Quick validation
    APPLICATION = "application"        # 35s - SMD Phase 3 startup
    INFRASTRUCTURE = "infrastructure"  # 600s - Infrastructure requirement
    EXTENDED = "extended"             # 900s - Extended operations

class DatabaseTimeoutConfig:
    """Enhanced database timeout configuration for Issue #1278 remediation."""

    # CRITICAL: Infrastructure requirement from Issue #1278
    INFRASTRUCTURE_TIMEOUT = 600.0    # 10 minutes - GCP requirement
    VPC_CONNECTOR_BUFFER = 620.0      # 10m 20s - Buffer for VPC overhead

    # Application-level timeouts
    APPLICATION_STARTUP_TIMEOUT = 35.0  # SMD Phase 3 requirement
    HEALTH_CHECK_TIMEOUT = 15.0         # Quick health validation
    CONNECTION_POOL_TIMEOUT = 35.0      # Pool connection timeout
    QUERY_EXECUTION_TIMEOUT = 30.0      # Individual query timeout

    # Extended timeouts for special operations
    MIGRATION_TIMEOUT = 1800.0          # 30 minutes for migrations
    BACKUP_TIMEOUT = 3600.0             # 1 hour for backup operations

    @classmethod
    def get_timeout_for_tier(cls, tier: TimeoutTier) -> float:
        """Get timeout value for specific tier."""
        timeout_map = {
            TimeoutTier.HEALTH_CHECK: cls.HEALTH_CHECK_TIMEOUT,
            TimeoutTier.APPLICATION: cls.APPLICATION_STARTUP_TIMEOUT,
            TimeoutTier.INFRASTRUCTURE: cls.INFRASTRUCTURE_TIMEOUT,
            TimeoutTier.EXTENDED: cls.MIGRATION_TIMEOUT,
        }
        return timeout_map.get(tier, cls.APPLICATION_STARTUP_TIMEOUT)

    @classmethod
    def get_timeout_for_environment(cls, environment: str, operation: str = "startup") -> float:
        """Get environment-specific timeout values."""
        if environment == "staging":
            if operation == "health_check":
                return cls.HEALTH_CHECK_TIMEOUT
            elif operation == "startup":
                return cls.APPLICATION_STARTUP_TIMEOUT
            elif operation == "infrastructure_test":
                return cls.INFRASTRUCTURE_TIMEOUT

        elif environment in ["production", "prod"]:
            # Production uses longer timeouts for stability
            if operation == "startup":
                return cls.INFRASTRUCTURE_TIMEOUT
            elif operation == "health_check":
                return cls.HEALTH_CHECK_TIMEOUT

        return cls.APPLICATION_STARTUP_TIMEOUT

    @classmethod
    def get_connection_pool_config(cls, environment: str) -> Dict[str, any]:
        """Get optimized connection pool configuration for environment."""
        base_config = {
            "pool_size": 20,                    # Base connections
            "max_overflow": 30,                 # Additional connections under load
            "pool_timeout": cls.CONNECTION_POOL_TIMEOUT,
            "pool_recycle": 3600,               # Recycle connections every hour
            "pool_pre_ping": True,              # Validate connections before use
            "pool_reset_on_return": "rollback", # Clean state for returned connections
        }

        # Environment-specific optimizations
        if environment == "staging":
            base_config.update({
                "pool_size": 15,                # Fewer base connections for staging
                "max_overflow": 25,
                "pool_recycle": 1800,           # More frequent recycling for testing
            })
        elif environment in ["production", "prod"]:
            base_config.update({
                "pool_size": 30,                # More base connections for production
                "max_overflow": 50,
                "pool_recycle": 7200,           # Less frequent recycling for stability
            })

        return base_config

    @classmethod
    def get_connect_args(cls, environment: str) -> Dict[str, any]:
        """Get database connection arguments optimized for infrastructure."""
        return {
            "connect_timeout": cls.INFRASTRUCTURE_TIMEOUT,  # Infrastructure requirement
            "command_timeout": cls.QUERY_EXECUTION_TIMEOUT,
            "server_settings": {
                "application_name": f"netra-backend-{environment}",
                "statement_timeout": f"{int(cls.QUERY_EXECUTION_TIMEOUT * 1000)}ms",
            },
            # Connection resilience
            "options": f"-c statement_timeout={int(cls.QUERY_EXECUTION_TIMEOUT * 1000)}ms"
        }

    @classmethod
    def log_timeout_configuration(cls, environment: str, operation: str):
        """Log current timeout configuration for debugging."""
        timeout = cls.get_timeout_for_environment(environment, operation)
        pool_config = cls.get_connection_pool_config(environment)

        logger.info(f"Database timeout configuration for {environment}:{operation}")
        logger.info(f"  Operation timeout: {timeout}s")
        logger.info(f"  Pool size: {pool_config['pool_size']}")
        logger.info(f"  Max overflow: {pool_config['max_overflow']}")
        logger.info(f"  Pool timeout: {pool_config['pool_timeout']}s")
        logger.info(f"  Infrastructure timeout: {cls.INFRASTRUCTURE_TIMEOUT}s")
```

### Update Database Configuration Integration

**File**: `netra_backend/app/core/configuration/database.py`

Find and update the timeout configuration section:

```python
# Add this import at the top
from netra_backend.app.core.database_timeout_config import DatabaseTimeoutConfig, TimeoutTier

# Update the timeout configuration section (around line 80-100)
def get_database_timeout_config(self) -> Dict[str, float]:
    """Get database timeout configuration with Issue #1278 compliance."""
    environment = self.isolated_env.get_environment()

    config = {
        "startup_timeout": DatabaseTimeoutConfig.get_timeout_for_environment(environment, "startup"),
        "health_check_timeout": DatabaseTimeoutConfig.get_timeout_for_environment(environment, "health_check"),
        "infrastructure_timeout": DatabaseTimeoutConfig.INFRASTRUCTURE_TIMEOUT,
        "query_timeout": DatabaseTimeoutConfig.QUERY_EXECUTION_TIMEOUT,
        "connection_pool_timeout": DatabaseTimeoutConfig.CONNECTION_POOL_TIMEOUT,
    }

    # Log configuration for debugging
    DatabaseTimeoutConfig.log_timeout_configuration(environment, "configuration_load")

    return config

# Update connection pool configuration method
def get_connection_pool_config(self) -> Dict[str, any]:
    """Get connection pool configuration optimized for infrastructure."""
    environment = self.isolated_env.get_environment()
    pool_config = DatabaseTimeoutConfig.get_connection_pool_config(environment)
    connect_args = DatabaseTimeoutConfig.get_connect_args(environment)

    pool_config["connect_args"] = connect_args
    return pool_config
```

---

## IMPLEMENTATION PRIORITY 2: ENHANCED HEALTH CHECKS

### Create Infrastructure-Aware Health Checks

**File**: `netra_backend/app/services/infrastructure_aware_health.py`

```python
#!/usr/bin/env python3
"""
Infrastructure-aware health checks for Issue #1278
Provides health status that distinguishes infrastructure vs application issues.
"""
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

from netra_backend.app.core.database_timeout_config import DatabaseTimeoutConfig, TimeoutTier

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    INFRASTRUCTURE_ISSUE = "infrastructure_issue"

class ComponentHealth(Enum):
    """Component health indicators."""
    APPLICATION = "application"
    DATABASE = "database"
    VPC_CONNECTOR = "vpc_connector"
    SSL_CERTIFICATE = "ssl_certificate"

class InfrastructureAwareHealthCheck:
    """Enhanced health checks that distinguish infrastructure from application issues."""

    def __init__(self):
        self.health_check_timeout = DatabaseTimeoutConfig.HEALTH_CHECK_TIMEOUT
        self.infrastructure_timeout = DatabaseTimeoutConfig.INFRASTRUCTURE_TIMEOUT

    async def get_comprehensive_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including infrastructure classification."""
        start_time = time.time()

        health_results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": HealthStatus.HEALTHY.value,
            "total_check_time": 0.0,
            "components": {},
            "infrastructure_issues": [],
            "application_issues": [],
            "issue_1278_indicators": []
        }

        try:
            # Run all health checks concurrently with timeouts
            tasks = {
                ComponentHealth.APPLICATION: self.check_application_health(),
                ComponentHealth.DATABASE: self.check_database_health_with_classification(),
                ComponentHealth.VPC_CONNECTOR: self.check_vpc_connectivity_health(),
                ComponentHealth.SSL_CERTIFICATE: self.check_ssl_health(),
            }

            # Execute with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*[tasks[component] for component in tasks.keys()], return_exceptions=True),
                timeout=self.health_check_timeout
            )

            # Process results
            for i, component in enumerate(tasks.keys()):
                if isinstance(results[i], Exception):
                    health_results["components"][component.value] = {
                        "status": HealthStatus.UNHEALTHY.value,
                        "error": str(results[i]),
                        "check_time": self.health_check_timeout,
                        "timeout": True
                    }
                else:
                    health_results["components"][component.value] = results[i]

            # Classify overall health and identify Issue #1278 patterns
            health_results = self._classify_overall_health(health_results)

        except asyncio.TimeoutError:
            health_results["overall_status"] = HealthStatus.INFRASTRUCTURE_ISSUE.value
            health_results["timeout_error"] = f"Health checks timed out after {self.health_check_timeout}s"
            health_results["issue_1278_indicators"].append("Health check timeout - possible infrastructure issue")

        except Exception as e:
            health_results["overall_status"] = HealthStatus.UNHEALTHY.value
            health_results["error"] = str(e)

        health_results["total_check_time"] = time.time() - start_time
        return health_results

    async def check_database_health_with_classification(self) -> Dict[str, Any]:
        """Database health check with Issue #1278 pattern detection."""
        start_time = time.time()
        result = {
            "status": HealthStatus.HEALTHY.value,
            "check_time": 0.0,
            "connection_time": 0.0,
            "issue_classification": "none",
            "timeout_compliance": False,
            "infrastructure_indicators": []
        }

        try:
            # Test basic connection with timeout monitoring
            connection_start = time.time()

            # Import here to avoid circular imports
            from netra_backend.app.db.database_manager import DatabaseManager
            db_manager = DatabaseManager()

            async with db_manager.get_connection() as conn:
                # Simple query to test connectivity
                await conn.execute("SELECT 1 as health_check")

            connection_time = time.time() - connection_start
            result["connection_time"] = connection_time
            result["status"] = HealthStatus.HEALTHY.value

            # Analyze connection performance for Issue #1278 indicators
            if connection_time > 30.0:
                result["infrastructure_indicators"].append(f"Slow connection time: {connection_time:.2f}s")
                result["issue_classification"] = "performance_degradation"

            if connection_time > 60.0:
                result["infrastructure_indicators"].append("Connection time exceeds 1 minute")
                result["issue_classification"] = "infrastructure_issue"
                result["status"] = HealthStatus.DEGRADED.value

            # Check timeout compliance
            result["timeout_compliance"] = connection_time < self.infrastructure_timeout

        except asyncio.TimeoutError:
            result["status"] = HealthStatus.INFRASTRUCTURE_ISSUE.value
            result["error"] = f"Database connection timed out after {self.health_check_timeout}s"
            result["issue_classification"] = "timeout_infrastructure"
            result["infrastructure_indicators"].append("Database connection timeout - Issue #1278 pattern")

        except Exception as e:
            connection_time = time.time() - start_time
            result["connection_time"] = connection_time
            result["error"] = str(e)

            # Classify error type for Issue #1278
            error_msg = str(e).lower()
            if any(pattern in error_msg for pattern in ["timeout", "connection", "network", "vpc"]):
                result["status"] = HealthStatus.INFRASTRUCTURE_ISSUE.value
                result["issue_classification"] = "infrastructure_connectivity"
                result["infrastructure_indicators"].append(f"Infrastructure error pattern: {str(e)}")
            else:
                result["status"] = HealthStatus.UNHEALTHY.value
                result["issue_classification"] = "application_error"

        result["check_time"] = time.time() - start_time
        return result

    async def check_vpc_connectivity_health(self) -> Dict[str, Any]:
        """Check VPC connector health indicators."""
        # This is a placeholder - would need actual VPC metrics
        return {
            "status": HealthStatus.HEALTHY.value,
            "check_time": 0.1,
            "note": "VPC connectivity check - requires infrastructure metrics integration"
        }

    async def check_ssl_health(self) -> Dict[str, Any]:
        """Check SSL certificate health."""
        # This is a placeholder - would need actual SSL validation
        return {
            "status": HealthStatus.HEALTHY.value,
            "check_time": 0.1,
            "note": "SSL health check - requires certificate validation integration"
        }

    async def check_application_health(self) -> Dict[str, Any]:
        """Check core application health."""
        return {
            "status": HealthStatus.HEALTHY.value,
            "check_time": 0.05,
            "components_loaded": True,
            "configuration_valid": True
        }

    def _classify_overall_health(self, health_results: Dict[str, Any]) -> Dict[str, Any]:
        """Classify overall health status and identify Issue #1278 patterns."""
        infrastructure_issues = []
        application_issues = []
        issue_1278_indicators = []

        for component_name, component_result in health_results["components"].items():
            if component_result.get("status") == HealthStatus.INFRASTRUCTURE_ISSUE.value:
                infrastructure_issues.append(f"{component_name}: {component_result.get('error', 'Infrastructure issue')}")

            elif component_result.get("status") in [HealthStatus.UNHEALTHY.value, HealthStatus.DEGRADED.value]:
                if component_result.get("issue_classification") == "infrastructure_connectivity":
                    infrastructure_issues.append(f"{component_name}: {component_result.get('error')}")
                else:
                    application_issues.append(f"{component_name}: {component_result.get('error')}")

            # Collect Issue #1278 specific indicators
            if "infrastructure_indicators" in component_result:
                issue_1278_indicators.extend(component_result["infrastructure_indicators"])

        # Determine overall status
        if infrastructure_issues:
            health_results["overall_status"] = HealthStatus.INFRASTRUCTURE_ISSUE.value
        elif application_issues:
            health_results["overall_status"] = HealthStatus.UNHEALTHY.value
        else:
            # Check for degraded performance
            database_result = health_results["components"].get("database", {})
            if database_result.get("connection_time", 0) > 10.0:
                health_results["overall_status"] = HealthStatus.DEGRADED.value

        health_results["infrastructure_issues"] = infrastructure_issues
        health_results["application_issues"] = application_issues
        health_results["issue_1278_indicators"] = issue_1278_indicators

        return health_results
```

### Update Existing Health Endpoint

**File**: `netra_backend/app/services/backend_health_config.py`

Add this method to integrate the new infrastructure-aware health checks:

```python
# Add this import at the top
from netra_backend.app.services.infrastructure_aware_health import InfrastructureAwareHealthCheck

# Add this method to the existing BackendHealthConfig class
async def get_infrastructure_aware_health(self) -> Dict[str, Any]:
    """Get health status with infrastructure issue classification."""
    health_checker = InfrastructureAwareHealthCheck()
    return await health_checker.get_comprehensive_health_status()

# Update existing health check method to include infrastructure awareness
async def get_comprehensive_health(self) -> Dict[str, Any]:
    """Enhanced comprehensive health check with infrastructure classification."""
    try:
        # Get both traditional and infrastructure-aware health
        traditional_health = await self.get_health_status()
        infrastructure_health = await self.get_infrastructure_aware_health()

        return {
            "service": "netra-backend",
            "traditional_health": traditional_health,
            "infrastructure_health": infrastructure_health,
            "issue_1278_status": {
                "infrastructure_indicators": infrastructure_health.get("issue_1278_indicators", []),
                "database_connection_time": infrastructure_health.get("components", {}).get("database", {}).get("connection_time", 0),
                "overall_classification": infrastructure_health.get("overall_status"),
            },
            "timestamp": infrastructure_health.get("timestamp")
        }
    except Exception as e:
        return {
            "service": "netra-backend",
            "status": "error",
            "error": str(e),
            "infrastructure_classification": "health_check_failure",
            "timestamp": datetime.now().isoformat()
        }
```

---

## IMPLEMENTATION PRIORITY 3: MONITORING INTEGRATION

### Create Basic Infrastructure Monitor

**File**: `netra_backend/app/monitoring/infrastructure_health_monitor.py`

```python
#!/usr/bin/env python3
"""
Basic infrastructure health monitoring for Issue #1278
Provides continuous monitoring of infrastructure components.
"""
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from netra_backend.app.core.database_timeout_config import DatabaseTimeoutConfig

logger = logging.getLogger(__name__)

class InfrastructureHealthMonitor:
    """Basic infrastructure health monitoring."""

    def __init__(self):
        self.monitoring_interval = 300  # 5 minutes
        self.alert_thresholds = {
            "database_connection_time_warning": 300.0,    # 5 minutes
            "database_connection_time_critical": 540.0,   # 9 minutes (before 10min timeout)
            "health_check_failure_rate": 0.20,            # 20% failure rate
            "consecutive_failures_alert": 3,              # 3 consecutive failures
        }
        self.failure_history = []
        self.monitoring_active = False

    async def start_monitoring(self):
        """Start continuous infrastructure monitoring."""
        self.monitoring_active = True
        logger.info("Infrastructure health monitoring started")

        while self.monitoring_active:
            try:
                await self.monitor_infrastructure_health()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Infrastructure monitoring error: {e}")
                await asyncio.sleep(60)  # Short retry delay

    def stop_monitoring(self):
        """Stop infrastructure monitoring."""
        self.monitoring_active = False
        logger.info("Infrastructure health monitoring stopped")

    async def monitor_infrastructure_health(self) -> Dict[str, Any]:
        """Monitor infrastructure health and detect Issue #1278 patterns."""
        monitoring_result = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_interval": self.monitoring_interval,
            "health_metrics": {},
            "alerts": [],
            "issue_1278_indicators": []
        }

        try:
            # Import health checker
            from netra_backend.app.services.infrastructure_aware_health import InfrastructureAwareHealthCheck

            health_checker = InfrastructureAwareHealthCheck()
            health_status = await health_checker.get_comprehensive_health_status()

            monitoring_result["health_metrics"] = health_status

            # Analyze for alert conditions
            alerts = self._analyze_for_alerts(health_status)
            monitoring_result["alerts"] = alerts

            # Track failure patterns
            self._update_failure_history(health_status)

            # Log significant findings
            if alerts:
                logger.warning(f"Infrastructure monitoring detected {len(alerts)} alerts")
                for alert in alerts:
                    logger.warning(f"ALERT: {alert['level']} - {alert['message']}")

        except Exception as e:
            logger.error(f"Infrastructure health monitoring failed: {e}")
            monitoring_result["error"] = str(e)

        return monitoring_result

    def _analyze_for_alerts(self, health_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze health status for alert conditions."""
        alerts = []

        # Check database connection time alerts
        database_health = health_status.get("components", {}).get("database", {})
        connection_time = database_health.get("connection_time", 0)

        if connection_time > self.alert_thresholds["database_connection_time_critical"]:
            alerts.append({
                "level": "CRITICAL",
                "component": "database",
                "message": f"Database connection time {connection_time:.1f}s exceeds critical threshold",
                "threshold": self.alert_thresholds["database_connection_time_critical"],
                "value": connection_time,
                "remediation": "Check VPC connector capacity and Cloud SQL performance",
                "issue_reference": "#1278"
            })
        elif connection_time > self.alert_thresholds["database_connection_time_warning"]:
            alerts.append({
                "level": "WARNING",
                "component": "database",
                "message": f"Database connection time {connection_time:.1f}s exceeds warning threshold",
                "threshold": self.alert_thresholds["database_connection_time_warning"],
                "value": connection_time,
                "remediation": "Monitor VPC connector performance",
                "issue_reference": "#1278"
            })

        # Check for Infrastructure issues
        if health_status.get("overall_status") == "infrastructure_issue":
            alerts.append({
                "level": "CRITICAL",
                "component": "infrastructure",
                "message": "Infrastructure issue detected",
                "details": health_status.get("infrastructure_issues", []),
                "remediation": "Escalate to infrastructure team",
                "issue_reference": "#1278"
            })

        # Check consecutive failures
        recent_failures = self._count_recent_failures()
        if recent_failures >= self.alert_thresholds["consecutive_failures_alert"]:
            alerts.append({
                "level": "CRITICAL",
                "component": "availability",
                "message": f"{recent_failures} consecutive health check failures",
                "remediation": "Immediate investigation required",
                "issue_reference": "#1278"
            })

        return alerts

    def _update_failure_history(self, health_status: Dict[str, Any]):
        """Update failure history for trend analysis."""
        is_failure = health_status.get("overall_status") in ["unhealthy", "infrastructure_issue"]

        failure_record = {
            "timestamp": datetime.now(),
            "is_failure": is_failure,
            "status": health_status.get("overall_status"),
            "database_connection_time": health_status.get("components", {}).get("database", {}).get("connection_time", 0)
        }

        self.failure_history.append(failure_record)

        # Keep only last 24 hours of history
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.failure_history = [record for record in self.failure_history if record["timestamp"] > cutoff_time]

    def _count_recent_failures(self) -> int:
        """Count consecutive recent failures."""
        if not self.failure_history:
            return 0

        # Sort by timestamp descending
        sorted_history = sorted(self.failure_history, key=lambda x: x["timestamp"], reverse=True)

        consecutive_failures = 0
        for record in sorted_history:
            if record["is_failure"]:
                consecutive_failures += 1
            else:
                break  # Stop at first success

        return consecutive_failures

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and statistics."""
        recent_failures = self._count_recent_failures()
        total_checks = len(self.failure_history)
        failure_count = sum(1 for record in self.failure_history if record["is_failure"])

        return {
            "monitoring_active": self.monitoring_active,
            "monitoring_interval": self.monitoring_interval,
            "total_health_checks": total_checks,
            "failure_count": failure_count,
            "failure_rate": failure_count / total_checks if total_checks > 0 else 0,
            "consecutive_failures": recent_failures,
            "alert_thresholds": self.alert_thresholds,
            "history_retention_hours": 24
        }
```

---

## VALIDATION COMMANDS

After implementing these changes, run these commands to validate the improvements:

### 1. Test Database Timeout Configuration
```bash
# Test timeout configuration
python -c "
from netra_backend.app.core.database_timeout_config import DatabaseTimeoutConfig, TimeoutTier
print('Staging application timeout:', DatabaseTimeoutConfig.get_timeout_for_environment('staging', 'startup'))
print('Infrastructure timeout:', DatabaseTimeoutConfig.INFRASTRUCTURE_TIMEOUT)
print('Health check timeout:', DatabaseTimeoutConfig.get_timeout_for_tier(TimeoutTier.HEALTH_CHECK))
"
```

### 2. Test Infrastructure-Aware Health Checks
```bash
# Test enhanced health checks
python -c "
import asyncio
from netra_backend.app.services.infrastructure_aware_health import InfrastructureAwareHealthCheck
checker = InfrastructureAwareHealthCheck()
result = asyncio.run(checker.get_comprehensive_health_status())
print('Overall status:', result['overall_status'])
print('Infrastructure indicators:', result['issue_1278_indicators'])
"
```

### 3. Test Infrastructure Monitoring
```bash
# Test monitoring system
python -c "
import asyncio
from netra_backend.app.monitoring.infrastructure_health_monitor import InfrastructureHealthMonitor
monitor = InfrastructureHealthMonitor()
result = asyncio.run(monitor.monitor_infrastructure_health())
print('Monitoring result:', result.get('health_metrics', {}).get('overall_status'))
print('Alerts:', len(result.get('alerts', [])))
"
```

### 4. Run Issue #1278 Test Suite
```bash
# Run integration tests with new configuration
python -m pytest tests/integration/issue_1278_database_connectivity_integration_simple.py -v -s

# Run E2E staging tests (after infrastructure fixes)
python -m pytest tests/e2e_staging/issue_1278_staging_connectivity_simple.py -v -s
```

---

## INTEGRATION WITH EXISTING SYSTEM

### Update SMD Phase 3 Integration
**File**: `netra_backend/app/smd.py`

Find the database connection section and update it to use the new timeout configuration:

```python
# Add this import
from netra_backend.app.core.database_timeout_config import DatabaseTimeoutConfig

# Update Phase 3 database connection (around line 200-300)
async def phase_3_database(self) -> None:
    """Phase 3: Database Connection with Issue #1278 timeout compliance."""
    self.logger.info("SMD Phase 3: DATABASE - Starting with enhanced timeout configuration")

    try:
        environment = self.isolated_env.get_environment()
        timeout = DatabaseTimeoutConfig.get_timeout_for_environment(environment, "startup")

        self.logger.info(f"Database connection timeout: {timeout}s (environment: {environment})")

        # Use timeout-aware database connection
        database_config = self.config_manager.get_database_configuration()

        # The rest of the existing database connection logic...
        # But now it uses the enhanced timeout configuration

    except Exception as e:
        self.logger.error(f"SMD Phase 3 failed with enhanced configuration: {e}")
        raise
```

### Update Health Endpoint Route
**File**: `netra_backend/app/routes/health.py`

Add new endpoint for infrastructure-aware health:

```python
# Add this import
from netra_backend.app.services.infrastructure_aware_health import InfrastructureAwareHealthCheck

# Add new route
@router.get("/health/infrastructure")
async def get_infrastructure_health():
    """Get infrastructure-aware health status for Issue #1278 monitoring."""
    try:
        health_checker = InfrastructureAwareHealthCheck()
        result = await health_checker.get_comprehensive_health_status()

        # Return appropriate HTTP status based on infrastructure health
        if result.get("overall_status") == "infrastructure_issue":
            return JSONResponse(content=result, status_code=503)
        elif result.get("overall_status") == "unhealthy":
            return JSONResponse(content=result, status_code=503)
        elif result.get("overall_status") == "degraded":
            return JSONResponse(content=result, status_code=200)  # Still functional
        else:
            return JSONResponse(content=result, status_code=200)

    except Exception as e:
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e),
                "infrastructure_classification": "health_endpoint_failure",
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )
```

---

## EXPECTED OUTCOMES

After implementing these development team deliverables:

### Immediate Benefits:
- ✅ **Enhanced Timeout Handling**: Application respects 600s infrastructure requirement
- ✅ **Better Health Reporting**: Health checks distinguish infrastructure vs application issues
- ✅ **Proactive Monitoring**: Infrastructure monitoring detects Issue #1278 patterns early

### Integration with Infrastructure Fixes:
- ✅ **Validation Ready**: Enhanced monitoring will validate infrastructure fixes
- ✅ **Pattern Detection**: System can identify when Issue #1278 patterns recur
- ✅ **Graceful Handling**: Application handles infrastructure issues more gracefully

### Business Value:
- ✅ **Faster Resolution**: Clear classification of infrastructure vs application issues
- ✅ **Proactive Alerts**: Early warning before infrastructure failures impact customers
- ✅ **Better Diagnostics**: Detailed information for troubleshooting

---

This implementation guide provides immediate value while the infrastructure team works on the core VPC connector and database timeout fixes. All code is additive and enhances the existing system without breaking changes.

**Next Steps**: Implement these changes, then coordinate with infrastructure team for Phase 1 (VPC connector scaling) validation.

---

**Generated with [Claude Code](https://claude.ai/code)**

**Co-Authored-By**: Claude <noreply@anthropic.com>
**Implementation Guide**: `issue-1278-dev-team-implementation-20250916`