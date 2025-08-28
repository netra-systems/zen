#!/usr/bin/env python3
"""
PostgreSQL Health Monitoring Script

This script provides comprehensive health monitoring for PostgreSQL container
including recovery detection, data integrity checks, and performance monitoring.

Features:
- Container health status
- Database connectivity checks
- Recovery status detection
- Data integrity verification
- Performance metrics
- Automatic alerting on issues

Author: Netra Core Generation 1
Date: 2025-08-28
"""

import sys
import time
import subprocess
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class HealthStatus:
    """Container for health check results."""
    is_healthy: bool
    container_status: str
    db_connectivity: bool
    recovery_detected: bool
    table_count: int
    active_connections: int
    last_checkpoint: Optional[str]
    issues: List[str]
    warnings: List[str]


def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/postgres_health.log', mode='a')
        ]
    )
    return logging.getLogger(__name__)


def run_command(cmd: List[str], capture_output: bool = True, timeout: int = 30) -> subprocess.CompletedProcess:
    """Execute a command with timeout and return the result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {' '.join(cmd)}")
        return subprocess.CompletedProcess(cmd, 1, "", "Command timed out")
    except Exception as e:
        logger.error(f"Error running command {' '.join(cmd)}: {e}")
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def check_container_status() -> Tuple[bool, str]:
    """Check PostgreSQL container status."""
    result = run_command(["docker", "ps", "--filter", "name=netra-postgres", "--format", "{{.Status}}"])
    
    if result.returncode != 0:
        return False, "Docker command failed"
    
    if not result.stdout.strip():
        return False, "Container not running"
    
    status = result.stdout.strip()
    is_healthy = "healthy" in status.lower()
    return is_healthy, status


def check_db_connectivity() -> bool:
    """Test database connectivity."""
    result = run_command([
        "docker", "exec", "netra-postgres",
        "psql", "-U", "netra", "-d", "netra_dev",
        "-c", "SELECT 1;"
    ], timeout=10)
    
    return result.returncode == 0


def check_recovery_status() -> Tuple[bool, Optional[str]]:
    """Check if database recovery was detected in recent logs."""
    result = run_command([
        "docker", "logs", "netra-postgres", "--since", "24h"
    ])
    
    if result.returncode != 0:
        return False, None
    
    recovery_detected = False
    last_recovery = None
    
    for line in result.stdout.split('\n'):
        if "automatic recovery in progress" in line.lower():
            recovery_detected = True
            last_recovery = line.split()[0] + " " + line.split()[1]  # Extract timestamp
    
    return recovery_detected, last_recovery


def get_table_count() -> int:
    """Get the number of tables in the database."""
    result = run_command([
        "docker", "exec", "netra-postgres",
        "psql", "-U", "netra", "-d", "netra_dev",
        "-t", "-c", "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
    ])
    
    if result.returncode == 0:
        try:
            # The table count query was wrong earlier, let's fix it
            actual_result = run_command([
                "docker", "exec", "netra-postgres",
                "psql", "-U", "netra", "-d", "netra_dev",
                "-t", "-c", "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';"
            ])
            if actual_result.returncode == 0:
                return int(actual_result.stdout.strip())
        except ValueError:
            pass
    
    return 0


def get_active_connections() -> int:
    """Get the number of active database connections."""
    result = run_command([
        "docker", "exec", "netra-postgres",
        "psql", "-U", "netra", "-d", "netra_dev",
        "-t", "-c", "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active';"
    ])
    
    if result.returncode == 0:
        try:
            return int(result.stdout.strip())
        except ValueError:
            pass
    
    return 0


def get_last_checkpoint() -> Optional[str]:
    """Get the timestamp of the last checkpoint."""
    result = run_command([
        "docker", "logs", "netra-postgres", "--tail", "50"
    ])
    
    if result.returncode != 0:
        return None
    
    last_checkpoint = None
    for line in reversed(result.stdout.split('\n')):
        if "checkpoint complete" in line.lower():
            try:
                # Extract timestamp from log line
                parts = line.split()
                if len(parts) >= 2:
                    last_checkpoint = parts[0] + " " + parts[1]
                break
            except:
                continue
    
    return last_checkpoint


def check_critical_errors() -> List[str]:
    """Check for critical errors in recent logs."""
    result = run_command([
        "docker", "logs", "netra-postgres", "--since", "1h"
    ])
    
    if result.returncode != 0:
        return ["Unable to retrieve logs"]
    
    errors = []
    critical_patterns = [
        "FATAL:",
        "PANIC:",
        "corruption",
        "invalid page header",
        "could not read block",
        "database system is shutting down"
    ]
    
    for line in result.stdout.split('\n'):
        for pattern in critical_patterns:
            if pattern in line.lower():
                errors.append(line.strip())
                break
    
    return errors


def check_warnings() -> List[str]:
    """Check for warning conditions."""
    warnings = []
    
    # Check for foreign key violations (common but not critical)
    result = run_command([
        "docker", "logs", "netra-postgres", "--since", "1h"
    ])
    
    if result.returncode == 0:
        fk_errors = 0
        for line in result.stdout.split('\n'):
            if "violates foreign key constraint" in line:
                fk_errors += 1
        
        if fk_errors > 10:
            warnings.append(f"High number of foreign key violations: {fk_errors}")
    
    # Check connection count
    connections = get_active_connections()
    if connections > 50:
        warnings.append(f"High number of active connections: {connections}")
    
    return warnings


def perform_health_check() -> HealthStatus:
    """Perform comprehensive health check."""
    logger.info("Starting PostgreSQL health check...")
    
    # Container status
    container_healthy, container_status = check_container_status()
    
    # Database connectivity
    db_connectivity = check_db_connectivity() if container_healthy else False
    
    # Recovery detection
    recovery_detected, last_recovery = check_recovery_status()
    
    # Data integrity
    table_count = get_table_count() if db_connectivity else 0
    
    # Performance metrics
    active_connections = get_active_connections() if db_connectivity else 0
    last_checkpoint = get_last_checkpoint()
    
    # Issues and warnings
    issues = check_critical_errors() if container_healthy else ["Container not healthy"]
    warnings = check_warnings() if container_healthy else []
    
    # Overall health determination
    is_healthy = (
        container_healthy and 
        db_connectivity and 
        table_count > 0 and 
        len(issues) == 0
    )
    
    return HealthStatus(
        is_healthy=is_healthy,
        container_status=container_status,
        db_connectivity=db_connectivity,
        recovery_detected=recovery_detected,
        table_count=table_count,
        active_connections=active_connections,
        last_checkpoint=last_checkpoint,
        issues=issues,
        warnings=warnings
    )


def print_health_report(status: HealthStatus):
    """Print formatted health report."""
    print("\n" + "="*60)
    print("PostgreSQL Health Report")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Overall Health: {'[HEALTHY]' if status.is_healthy else '[UNHEALTHY]'}")
    print()
    
    print("Container Status:")
    print(f"  Status: {status.container_status}")
    print(f"  DB Connectivity: {'[OK]' if status.db_connectivity else '[FAILED]'}")
    print()
    
    print("Database Metrics:")
    print(f"  Table Count: {status.table_count}")
    print(f"  Active Connections: {status.active_connections}")
    print(f"  Last Checkpoint: {status.last_checkpoint or 'Unknown'}")
    print()
    
    if status.recovery_detected:
        print("[WARNING] Recovery Detected:")
        print("  Database recovery was detected in recent logs.")
        print("  This indicates an improper shutdown occurred.")
        print()
    
    if status.issues:
        print("[CRITICAL] Critical Issues:")
        for issue in status.issues:
            print(f"  - {issue}")
        print()
    
    if status.warnings:
        print("[WARNING] Warnings:")
        for warning in status.warnings:
            print(f"  - {warning}")
        print()
    
    print("="*60)


def main():
    """Main function."""
    global logger
    logger = setup_logging()
    
    try:
        status = perform_health_check()
        print_health_report(status)
        
        # Log results
        if status.is_healthy:
            logger.info("PostgreSQL health check passed")
        else:
            logger.error("PostgreSQL health check failed")
            for issue in status.issues:
                logger.error(f"Issue: {issue}")
        
        # Exit code based on health
        sys.exit(0 if status.is_healthy else 1)
        
    except Exception as e:
        logger.error(f"Health check failed with exception: {e}")
        print(f"[ERROR] Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()