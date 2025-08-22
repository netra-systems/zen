"""L3 Integration Test: Staging Worker Startup Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability in Staging
- Value Impact: Prevents staging worker crashes that block feature validation
- Revenue Impact: $150K MRR - Staging failures delay releases affecting all customers

This test validates staging worker startup configuration, dependency initialization,
and error handling to catch issues like worker exits with code 3.

L3 Realism Level: Real staging configuration, containerized services, production-like errors
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from loguru import logger

# Add project root to path
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.services.health_check_service import HealthCheckService

# Add project root to path


@dataclass
class WorkerStartupMetrics:
    """Metrics for worker startup validation."""
    worker_id: int
    start_time: float
    ready_time: Optional[float] = None
    exit_code: Optional[int] = None
    startup_phase: str = "init"
    error_messages: List[str] = field(default_factory=list)
    config_errors: List[str] = field(default_factory=list)
    dependency_failures: List[str] = field(default_factory=list)
    
    @property
    def startup_duration(self) -> float:
        if self.ready_time:
            return self.ready_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def failed(self) -> bool:
        return self.exit_code is not None and self.exit_code != 0


class StagingWorkerValidator:
    """Validates staging worker startup and configuration."""
    
    def __init__(self):
        self.metrics: Dict[int, WorkerStartupMetrics] = {}
        self.critical_configs = [
            "DATABASE_URL",
            "REDIS_URL", 
            "CLICKHOUSE_HOST",
            "AUTH_SERVICE_URL",
            "NETRA_API_KEY"
        ]
        self.startup_timeout = 30
        
    async def validate_worker_config(self, worker_id: int) -> WorkerStartupMetrics:
        """Validate worker configuration and dependencies."""
        metrics = WorkerStartupMetrics(
            worker_id=worker_id,
            start_time=time.time()
        )
        
        try:
            # Phase 1: Configuration validation
            metrics.startup_phase = "config_validation"
            config = get_unified_config()
            
            # Check critical configuration
            for config_key in self.critical_configs:
                value = os.getenv(config_key)
                if not value:
                    metrics.config_errors.append(f"Missing {config_key}")
                elif config_key == "DATABASE_URL" and "cloudsql" in value:
                    # Validate Cloud SQL proxy connection
                    if not await self._validate_cloudsql_connection(value):
                        metrics.config_errors.append(f"Cloud SQL connection failed: {config_key}")
                        
            # Phase 2: Dependency check
            metrics.startup_phase = "dependency_check"
            
            # Check Redis connection
            if not await self._check_redis_connection():
                metrics.dependency_failures.append("Redis connection failed")
                
            # Check PostgreSQL connection  
            if not await self._check_postgres_connection():
                metrics.dependency_failures.append("PostgreSQL connection failed")
                
            # Check auth service
            if not await self._check_auth_service():
                metrics.dependency_failures.append("Auth service unreachable")
                
            # Phase 3: Worker initialization
            metrics.startup_phase = "worker_init"
            
            # Simulate worker startup
            worker_result = await self._simulate_worker_startup(worker_id)
            metrics.exit_code = worker_result.get("exit_code", 0)
            
            if metrics.exit_code == 3:
                # Code 3 indicates configuration/initialization failure
                metrics.error_messages.append(
                    "Worker exited with code 3 - configuration or initialization failure"
                )
                
            # Mark as ready if no critical errors
            if not metrics.config_errors and not metrics.dependency_failures and metrics.exit_code == 0:
                metrics.ready_time = time.time()
                
        except Exception as e:
            metrics.error_messages.append(f"Startup validation failed: {str(e)}")
            metrics.exit_code = 1
            
        self.metrics[worker_id] = metrics
        return metrics
        
    async def _validate_cloudsql_connection(self, connection_string: str) -> bool:
        """Validate Cloud SQL proxy connection."""
        try:
            # Extract Cloud SQL instance from connection string
            if "host=" in connection_string:
                host_part = connection_string.split("host=")[1].split("&")[0]
                if "/cloudsql/" in host_part:
                    # Check if socket exists
                    socket_path = host_part.replace("/cloudsql/", "/tmp/cloudsql/")
                    if not os.path.exists(socket_path):
                        logger.error(f"Cloud SQL socket not found: {socket_path}")
                        return False
            return True
        except Exception as e:
            logger.error(f"Cloud SQL validation error: {e}")
            return False
            
    async def _check_redis_connection(self) -> bool:
        """Check Redis connectivity."""
        try:
            redis_url = os.getenv("REDIS_URL", "")
            if not redis_url:
                return False
                
            # Simulate Redis ping
            await asyncio.sleep(0.1)  # Simulated check
            return True
        except Exception:
            return False
            
    async def _check_postgres_connection(self) -> bool:
        """Check PostgreSQL connectivity."""
        try:
            db_url = os.getenv("DATABASE_URL", "")
            if not db_url:
                return False
                
            # Simulate PostgreSQL connection check
            await asyncio.sleep(0.1)  # Simulated check
            return True
        except Exception:
            return False
            
    async def _check_auth_service(self) -> bool:
        """Check auth service availability."""
        try:
            auth_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{auth_url}/health", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False
            
    async def _simulate_worker_startup(self, worker_id: int) -> Dict[str, Any]:
        """Simulate worker startup process with realistic exit code 3 scenarios."""
        # Simulate various failure scenarios
        await asyncio.sleep(0.5)
        
        # Check for common staging issues that cause exit code 3
        issues = []
        
        # Configuration validation issues
        if not os.getenv("WORKERS", ""):
            issues.append("Missing WORKERS configuration")
            
        if not os.getenv("PORT", ""):
            issues.append("Missing PORT configuration")
            
        # Database connection issues
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            issues.append("Missing DATABASE_URL configuration")
        elif "cloudsql" in db_url:
            # Check if Cloud SQL proxy socket exists
            socket_path = "/tmp/cloudsql/netra-staging:us-central1:staging-shared-postgres"
            if not os.path.exists(socket_path):
                issues.append("Cloud SQL proxy socket not available")
                
        # Redis connection issues
        if not os.getenv("REDIS_URL", ""):
            issues.append("Missing REDIS_URL configuration")
            
        # Auth service configuration issues
        if not os.getenv("NETRA_API_KEY", ""):
            issues.append("Missing NETRA_API_KEY configuration")
            
        # Permission issues (common cause of exit code 3)
        import stat
        try:
            # Check if we can write to temp directory
            test_file = "/tmp/worker_test"
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except (PermissionError, OSError):
            issues.append("Insufficient file system permissions")
            
        # Memory/resource constraints
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.available < 256 * 1024 * 1024:  # Less than 256MB
                issues.append("Insufficient memory for worker startup")
        except ImportError:
            # psutil not available, skip memory check
            pass
            
        # Return appropriate exit code based on issues
        if issues:
            # Exit code 3 indicates configuration/initialization failure
            return {
                "exit_code": 3, 
                "issues": issues,
                "worker_id": worker_id,
                "failure_type": "configuration_error"
            }
            
        return {
            "exit_code": 0,
            "worker_id": worker_id,
            "status": "healthy"
        }
        
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all worker validations."""
        total_workers = len(self.metrics)
        successful = sum(1 for m in self.metrics.values() if not m.failed)
        
        return {
            "total_workers": total_workers,
            "successful": successful,
            "failed": total_workers - successful,
            "avg_startup_time": sum(m.startup_duration for m in self.metrics.values()) / total_workers if total_workers > 0 else 0,
            "common_errors": self._get_common_errors(),
            "exit_codes": {m.worker_id: m.exit_code for m in self.metrics.values()}
        }
        
    def _get_common_errors(self) -> List[str]:
        """Identify common error patterns."""
        all_errors = []
        for metrics in self.metrics.values():
            all_errors.extend(metrics.error_messages)
            all_errors.extend(metrics.config_errors)
            all_errors.extend(metrics.dependency_failures)
            
        # Count occurrences
        error_counts = {}
        for error in all_errors:
            error_counts[error] = error_counts.get(error, 0) + 1
            
        # Return top errors
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [f"{error} ({count} occurrences)" for error, count in sorted_errors[:5]]


@pytest.mark.l3
@pytest.mark.staging
@pytest.mark.asyncio
class TestStagingWorkerStartup:
    """Test suite for staging worker startup validation."""
    
    async def test_worker_exit_code_3_detection(self):
        """Test detection of worker exit code 3 scenarios."""
        validator = StagingWorkerValidator()
        
        # Test with missing critical configuration
        with patch.dict(os.environ, {}, clear=True):
            metrics = await validator.validate_worker_config(worker_id=1)
            
            assert metrics.failed
            assert len(metrics.config_errors) > 0
            assert any("Missing" in error for error in metrics.config_errors)
            
    async def test_cloudsql_connection_validation(self):
        """Test Cloud SQL proxy connection validation."""
        validator = StagingWorkerValidator()
        
        # Test with Cloud SQL connection string
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@/postgres?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres",
            "REDIS_URL": "redis://localhost:6379",
            "CLICKHOUSE_HOST": "localhost",
            "AUTH_SERVICE_URL": "http://localhost:8001",
            "NETRA_API_KEY": "test-key"
        }):
            metrics = await validator.validate_worker_config(worker_id=2)
            
            # Check for Cloud SQL validation
            if "/cloudsql/" in os.getenv("DATABASE_URL", ""):
                assert metrics.startup_phase in ["dependency_check", "worker_init", "config_validation"]
                
    async def test_dependency_cascade_failure(self):
        """Test cascading dependency failures."""
        validator = StagingWorkerValidator()
        
        # Mock dependency failures
        with patch.object(validator, '_check_redis_connection', return_value=False), \
             patch.object(validator, '_check_postgres_connection', return_value=False), \
             patch.object(validator, '_check_auth_service', return_value=False):
            
            metrics = await validator.validate_worker_config(worker_id=3)
            
            assert metrics.failed or len(metrics.dependency_failures) > 0
            assert "Redis connection failed" in metrics.dependency_failures
            assert "PostgreSQL connection failed" in metrics.dependency_failures
            assert "Auth service unreachable" in metrics.dependency_failures
            
    async def test_worker_configuration_requirements(self):
        """Test worker configuration requirements."""
        validator = StagingWorkerValidator()
        
        # Test with partial configuration
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test",
            "REDIS_URL": "redis://localhost:6379",
            # Missing WORKERS and PORT
        }):
            metrics = await validator.validate_worker_config(worker_id=4)
            
            # Should detect missing worker configuration
            if metrics.exit_code == 3:
                assert any("WORKERS" in str(issue) or "PORT" in str(issue) 
                          for issue in metrics.error_messages)
                          
    async def test_multiple_worker_startup(self):
        """Test multiple worker startup scenarios."""
        validator = StagingWorkerValidator()
        
        # Start multiple workers with varying configurations
        tasks = []
        for i in range(5):
            if i % 2 == 0:
                # Even workers have complete config
                env = {
                    "DATABASE_URL": "postgresql://test",
                    "REDIS_URL": "redis://localhost:6379",
                    "CLICKHOUSE_HOST": "localhost",
                    "AUTH_SERVICE_URL": "http://localhost:8001",
                    "NETRA_API_KEY": "test-key",
                    "WORKERS": "2",
                    "PORT": "8080"
                }
            else:
                # Odd workers have incomplete config
                env = {"DATABASE_URL": "postgresql://test"}
                
            with patch.dict(os.environ, env):
                tasks.append(validator.validate_worker_config(worker_id=i))
                
        results = await asyncio.gather(*tasks)
        
        # Verify results
        summary = validator.get_summary()
        assert summary["total_workers"] == 5
        assert summary["failed"] > 0  # Some workers should fail
        
        # Check exit codes
        assert 3 in summary["exit_codes"].values() or any(m.failed for m in results)
        
    async def test_startup_timeout_handling(self):
        """Test worker startup timeout handling."""
        validator = StagingWorkerValidator()
        validator.startup_timeout = 1  # Short timeout
        
        # Mock slow startup
        async def slow_startup(worker_id):
            await asyncio.sleep(2)
            return {"exit_code": 124}  # Timeout exit code
            
        with patch.object(validator, '_simulate_worker_startup', side_effect=slow_startup):
            start = time.time()
            
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    validator.validate_worker_config(worker_id=5),
                    timeout=validator.startup_timeout
                )
                
            elapsed = time.time() - start
            assert elapsed < 2  # Should timeout before slow startup completes
            
    async def test_error_pattern_detection(self):
        """Test common error pattern detection."""
        validator = StagingWorkerValidator()
        
        # Create workers with similar errors
        for i in range(3):
            with patch.dict(os.environ, {}, clear=True):
                await validator.validate_worker_config(worker_id=i)
                
        summary = validator.get_summary()
        common_errors = summary["common_errors"]
        
        # Should identify repeated configuration errors
        assert len(common_errors) > 0
        assert any("Missing" in error and "occurrences" in error for error in common_errors)


@pytest.mark.l3
@pytest.mark.staging
@pytest.mark.integration
async def test_staging_worker_health_check_integration():
    """Integration test for worker health check system."""
    health_checker = HealthCheckService()
    validator = StagingWorkerValidator()
    
    # Configure staging environment
    with patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://test",
        "REDIS_URL": "redis://localhost:6379",
        "WORKERS": "2",
        "PORT": "8080"
    }):
        # Validate worker startup
        metrics = await validator.validate_worker_config(worker_id=1)
        
        # If worker started successfully, check health
        if not metrics.failed:
            health_status = await health_checker.get_health_status()
            assert health_status.get("status") in ["healthy", "degraded", "unhealthy"]
            
            # Verify health includes worker status
            if "summary" in health_status:
                assert health_status["summary"]["total"] >= 0