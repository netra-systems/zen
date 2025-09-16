#!/usr/bin/env python3
"""
VPC Connector Monitoring Infrastructure
======================================

This script provides monitoring capabilities for VPC connector health and
database connectivity issues that led to Issue #1278.

**Purpose:**
- Monitor VPC connector health continuously
- Detect early signs of database connectivity issues
- Preserve monitoring infrastructure after emergency bypass cleanup
- Prevent future recurrence of Issue #1278

**Integration Points:**
- Health check endpoint integration
- OpenTelemetry metrics export
- GCP monitoring dashboard data
- Alert system integration

**Safety Note:**
This monitoring system should remain operational even after emergency bypass
cleanup to prevent future infrastructure issues.
"""

import os
import sys
import time
import logging
import asyncio
import asyncpg
import aioredis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.isolated_environment import IsolatedEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ConnectivityStatus:
    """Represents connectivity status for a service."""
    service: str
    connected: bool
    latency_ms: Optional[float]
    error_message: Optional[str]
    timestamp: datetime

@dataclass
class VPCConnectorHealthReport:
    """Comprehensive VPC connector health report."""
    timestamp: datetime
    postgres_status: ConnectivityStatus
    redis_status: ConnectivityStatus
    overall_healthy: bool
    vpc_connector_operational: bool
    recommendations: List[str]

class VPCConnectorMonitor:
    """
    Monitor VPC connector health and database connectivity.

    **Business Context:**
    VPC connector issues were the root cause of Issue #1278 emergency bypass.
    This monitor prevents future occurrences by providing early detection.
    """

    def __init__(self):
        self.env = IsolatedEnvironment()
        self.monitoring_active = True
        self.health_reports: List[VPCConnectorHealthReport] = []
        self.max_reports = 100  # Keep last 100 reports

    async def check_postgres_connectivity(self) -> ConnectivityStatus:
        """
        Check PostgreSQL connectivity through VPC connector.

        Returns:
            ConnectivityStatus with connection details
        """
        start_time = time.time()

        try:
            # Build connection string from environment
            host = self.env.get_env("POSTGRES_HOST", "localhost")
            port = self.env.get_env("POSTGRES_PORT", "5432")
            database = self.env.get_env("POSTGRES_DB", "postgres")
            user = self.env.get_env("POSTGRES_USER", "postgres")
            password = self.env.get_env("POSTGRES_PASSWORD", "")

            # Use configurable timeout for VPC connector scenarios
            timeout = float(self.env.get_env("AUTH_DB_URL_TIMEOUT", "10.0"))

            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"

            # Attempt connection with timeout
            conn = await asyncpg.connect(connection_string, timeout=timeout)

            # Simple health check query
            result = await conn.fetchval("SELECT 1")

            await conn.close()

            latency_ms = (time.time() - start_time) * 1000

            return ConnectivityStatus(
                service="postgres",
                connected=True,
                latency_ms=latency_ms,
                error_message=None,
                timestamp=datetime.now()
            )

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            return ConnectivityStatus(
                service="postgres",
                connected=False,
                latency_ms=latency_ms,
                error_message=f"Connection timeout after {timeout}s (VPC connector issue?)",
                timestamp=datetime.now()
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ConnectivityStatus(
                service="postgres",
                connected=False,
                latency_ms=latency_ms,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def check_redis_connectivity(self) -> ConnectivityStatus:
        """
        Check Redis connectivity through VPC connector.

        Returns:
            ConnectivityStatus with connection details
        """
        start_time = time.time()

        try:
            # Build Redis URL from environment
            redis_url = self.env.get_env("REDIS_URL", "redis://localhost:6379")

            # Use timeout similar to database timeout
            timeout = 10.0

            # Connect to Redis with timeout
            redis = await aioredis.from_url(redis_url, socket_timeout=timeout)

            # Simple health check
            await redis.ping()

            await redis.close()

            latency_ms = (time.time() - start_time) * 1000

            return ConnectivityStatus(
                service="redis",
                connected=True,
                latency_ms=latency_ms,
                error_message=None,
                timestamp=datetime.now()
            )

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            return ConnectivityStatus(
                service="redis",
                connected=False,
                latency_ms=latency_ms,
                error_message="Redis connection timeout (VPC connector issue?)",
                timestamp=datetime.now()
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ConnectivityStatus(
                service="redis",
                connected=False,
                latency_ms=latency_ms,
                error_message=str(e),
                timestamp=datetime.now()
            )

    async def generate_health_report(self) -> VPCConnectorHealthReport:
        """
        Generate comprehensive VPC connector health report.

        Returns:
            VPCConnectorHealthReport with current status
        """
        logger.info("🔍 Generating VPC connector health report...")

        # Check connectivity to all services
        postgres_status = await self.check_postgres_connectivity()
        redis_status = await self.check_redis_connectivity()

        # Determine overall health
        overall_healthy = postgres_status.connected and redis_status.connected

        # Assess VPC connector operational status
        vpc_connector_operational = self._assess_vpc_connector_health(
            postgres_status, redis_status
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            postgres_status, redis_status, overall_healthy
        )

        report = VPCConnectorHealthReport(
            timestamp=datetime.now(),
            postgres_status=postgres_status,
            redis_status=redis_status,
            overall_healthy=overall_healthy,
            vpc_connector_operational=vpc_connector_operational,
            recommendations=recommendations
        )

        # Store report
        self.health_reports.append(report)
        if len(self.health_reports) > self.max_reports:
            self.health_reports.pop(0)

        return report

    def _assess_vpc_connector_health(self, postgres_status: ConnectivityStatus, redis_status: ConnectivityStatus) -> bool:
        """
        Assess VPC connector health based on service connectivity.

        Args:
            postgres_status: PostgreSQL connectivity status
            redis_status: Redis connectivity status

        Returns:
            True if VPC connector appears operational
        """
        # VPC connector is likely healthy if:
        # 1. Both services are connected
        # 2. OR only one fails but without timeout (different issue)

        if postgres_status.connected and redis_status.connected:
            return True

        # Check for timeout patterns indicating VPC connector issues
        postgres_timeout = postgres_status.error_message and "timeout" in postgres_status.error_message.lower()
        redis_timeout = redis_status.error_message and "timeout" in redis_status.error_message.lower()

        # If both services timeout, likely VPC connector issue
        if postgres_timeout and redis_timeout:
            return False

        # If only one service fails without timeout, might be service-specific
        return True

    def _generate_recommendations(self, postgres_status: ConnectivityStatus, redis_status: ConnectivityStatus, overall_healthy: bool) -> List[str]:
        """
        Generate recommendations based on connectivity status.

        Args:
            postgres_status: PostgreSQL connectivity status
            redis_status: Redis connectivity status
            overall_healthy: Overall system health

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if overall_healthy:
            recommendations.append("✅ All services healthy - continue normal operations")

            # Performance recommendations based on latency
            if postgres_status.latency_ms and postgres_status.latency_ms > 1000:
                recommendations.append("⚠️ PostgreSQL latency high (>1s) - monitor VPC connector performance")

            if redis_status.latency_ms and redis_status.latency_ms > 500:
                recommendations.append("⚠️ Redis latency high (>500ms) - monitor VPC connector performance")

        else:
            if not postgres_status.connected:
                if "timeout" in (postgres_status.error_message or "").lower():
                    recommendations.append("🚨 PostgreSQL timeout detected - VPC connector may be failing")
                    recommendations.append("🔧 Check VPC connector status in GCP console")
                    recommendations.append("⚠️ Consider enabling emergency bypass if critical")
                else:
                    recommendations.append("🔧 PostgreSQL connection issue - check database service")

            if not redis_status.connected:
                if "timeout" in (redis_status.error_message or "").lower():
                    recommendations.append("🚨 Redis timeout detected - VPC connector may be failing")
                    recommendations.append("🔧 Check VPC connector and Redis instance status")
                else:
                    recommendations.append("🔧 Redis connection issue - check Redis service")

            # If both services fail with timeouts, likely VPC connector issue
            postgres_timeout = postgres_status.error_message and "timeout" in postgres_status.error_message.lower()
            redis_timeout = redis_status.error_message and "timeout" in redis_status.error_message.lower()

            if postgres_timeout and redis_timeout:
                recommendations.append("🚨 CRITICAL: Multiple timeout failures indicate VPC connector issue")
                recommendations.append("🚨 This is the same pattern as Issue #1278")
                recommendations.append("🔧 Immediate action required: Check VPC connector configuration")
                recommendations.append("⚠️ Consider emergency bypass if service availability critical")

        return recommendations

    async def run_monitoring_cycle(self, duration_minutes: int = 5) -> None:
        """
        Run continuous monitoring for specified duration.

        Args:
            duration_minutes: How long to run monitoring (default 5 minutes)
        """
        logger.info(f"🔄 Starting VPC connector monitoring for {duration_minutes} minutes...")

        end_time = datetime.now() + timedelta(minutes=duration_minutes)

        while datetime.now() < end_time and self.monitoring_active:
            try:
                report = await self.generate_health_report()

                # Log status
                status_emoji = "✅" if report.overall_healthy else "❌"
                logger.info(f"{status_emoji} VPC Connector Health: {report.overall_healthy}")

                if report.postgres_status.connected:
                    logger.info(f"  📊 PostgreSQL: OK ({report.postgres_status.latency_ms:.1f}ms)")
                else:
                    logger.warning(f"  ❌ PostgreSQL: FAILED - {report.postgres_status.error_message}")

                if report.redis_status.connected:
                    logger.info(f"  📊 Redis: OK ({report.redis_status.latency_ms:.1f}ms)")
                else:
                    logger.warning(f"  ❌ Redis: FAILED - {report.redis_status.error_message}")

                # Log critical recommendations
                for recommendation in report.recommendations:
                    if "🚨" in recommendation:
                        logger.critical(recommendation)
                    elif "⚠️" in recommendation:
                        logger.warning(recommendation)

                # Wait before next check (30 seconds)
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(30)

        logger.info("🔄 Monitoring cycle completed")

    def get_health_summary(self) -> Dict:
        """
        Get summary of recent health reports.

        Returns:
            Dictionary with health summary
        """
        if not self.health_reports:
            return {"status": "no_data", "message": "No health reports available"}

        recent_reports = self.health_reports[-10:]  # Last 10 reports

        healthy_count = sum(1 for report in recent_reports if report.overall_healthy)
        unhealthy_count = len(recent_reports) - healthy_count

        latest_report = self.health_reports[-1]

        summary = {
            "status": "healthy" if latest_report.overall_healthy else "unhealthy",
            "latest_check": latest_report.timestamp.isoformat(),
            "recent_health_ratio": f"{healthy_count}/{len(recent_reports)}",
            "postgres_status": asdict(latest_report.postgres_status),
            "redis_status": asdict(latest_report.redis_status),
            "vpc_connector_operational": latest_report.vpc_connector_operational,
            "critical_recommendations": [
                rec for rec in latest_report.recommendations if "🚨" in rec
            ],
            "warning_recommendations": [
                rec for rec in latest_report.recommendations if "⚠️" in rec
            ]
        }

        return summary

    def export_health_data(self, file_path: str) -> None:
        """
        Export health reports to JSON file.

        Args:
            file_path: Path to export file
        """
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_reports": len(self.health_reports),
            "reports": [
                {
                    "timestamp": report.timestamp.isoformat(),
                    "overall_healthy": report.overall_healthy,
                    "vpc_connector_operational": report.vpc_connector_operational,
                    "postgres_status": asdict(report.postgres_status),
                    "redis_status": asdict(report.redis_status),
                    "recommendations": report.recommendations
                }
                for report in self.health_reports
            ]
        }

        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"📁 Health data exported to: {file_path}")

def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="VPC Connector Health Monitor")
    parser.add_argument("--check", action="store_true",
                       help="Run single health check")
    parser.add_argument("--monitor", type=int, default=5,
                       help="Run continuous monitoring for N minutes (default: 5)")
    parser.add_argument("--summary", action="store_true",
                       help="Show health summary")
    parser.add_argument("--export", type=str,
                       help="Export health data to JSON file")

    args = parser.parse_args()

    monitor = VPCConnectorMonitor()

    if args.check:
        # Single health check
        async def single_check():
            report = await monitor.generate_health_report()

            print("="*60)
            print("VPC CONNECTOR HEALTH CHECK")
            print("="*60)
            print(f"Timestamp: {report.timestamp}")
            print(f"Overall Healthy: {'✅ YES' if report.overall_healthy else '❌ NO'}")
            print(f"VPC Connector Operational: {'✅ YES' if report.vpc_connector_operational else '❌ NO'}")
            print()

            print("PostgreSQL Status:")
            print(f"  Connected: {'✅' if report.postgres_status.connected else '❌'}")
            if report.postgres_status.latency_ms:
                print(f"  Latency: {report.postgres_status.latency_ms:.1f}ms")
            if report.postgres_status.error_message:
                print(f"  Error: {report.postgres_status.error_message}")
            print()

            print("Redis Status:")
            print(f"  Connected: {'✅' if report.redis_status.connected else '❌'}")
            if report.redis_status.latency_ms:
                print(f"  Latency: {report.redis_status.latency_ms:.1f}ms")
            if report.redis_status.error_message:
                print(f"  Error: {report.redis_status.error_message}")
            print()

            if report.recommendations:
                print("Recommendations:")
                for rec in report.recommendations:
                    print(f"  • {rec}")

        asyncio.run(single_check())

    elif args.summary:
        summary = monitor.get_health_summary()
        print(json.dumps(summary, indent=2, default=str))

    elif args.export:
        monitor.export_health_data(args.export)

    else:
        # Continuous monitoring
        asyncio.run(monitor.run_monitoring_cycle(args.monitor))

if __name__ == "__main__":
    main()