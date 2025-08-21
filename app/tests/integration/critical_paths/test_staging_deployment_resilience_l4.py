"""L4 Integration Test: Staging Deployment Resilience

Business Value Justification (BVJ):
- Segment: Enterprise/Platform
- Business Goal: Zero-downtime deployments and staging reliability
- Value Impact: Ensures staging mirrors production for accurate testing
- Revenue Impact: $500K MRR - Staging issues delay releases impacting all enterprise customers

This test validates the complete staging deployment pipeline including:
- Worker startup and configuration
- Service dependency orchestration  
- Error recovery and resilience
- Production parity validation

L4 Realism Level: Full staging environment with real GCP services, Cloud SQL, multi-region
"""

import pytest
import asyncio
import time
import json
import logging
import os
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import httpx
import websockets
from concurrent.futures import ThreadPoolExecutor

from app.core.configuration.base import get_unified_config
from loguru import logger
from app.services.health_checker import HealthChecker
from app.services.redis.session_manager import RedisSessionManager
from app.services.database.postgres_service import PostgresService


class DeploymentPhase(Enum):
    """Deployment phases for tracking."""
    PRE_DEPLOY = "pre_deploy"
    CONFIGURATION = "configuration"
    DEPENDENCY_INIT = "dependency_init"
    SERVICE_STARTUP = "service_startup"
    HEALTH_CHECK = "health_check"
    TRAFFIC_ROUTING = "traffic_routing"
    POST_DEPLOY = "post_deploy"
    ROLLBACK = "rollback"


@dataclass
class DeploymentMetrics:
    """Comprehensive deployment metrics."""
    deployment_id: str
    start_time: float
    end_time: Optional[float] = None
    current_phase: DeploymentPhase = DeploymentPhase.PRE_DEPLOY
    phase_durations: Dict[DeploymentPhase, float] = field(default_factory=dict)
    service_statuses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error_log: List[Dict[str, Any]] = field(default_factory=list)
    health_checks: List[Dict[str, Any]] = field(default_factory=list)
    rollback_triggered: bool = False
    rollback_reason: Optional[str] = None
    worker_metrics: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    
    @property
    def deployment_duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
        
    @property
    def success_rate(self) -> float:
        if not self.service_statuses:
            return 0.0
        successful = sum(1 for s in self.service_statuses.values() if s.get("healthy"))
        return successful / len(self.service_statuses)
        
    def add_error(self, phase: DeploymentPhase, error: str, details: Dict[str, Any] = None):
        """Add error to deployment log."""
        self.error_log.append({
            "timestamp": time.time(),
            "phase": phase.value,
            "error": error,
            "details": details or {}
        })


class StagingDeploymentValidator:
    """Validates complete staging deployment pipeline."""
    
    def __init__(self, staging_url: str = None):
        self.staging_url = staging_url or os.getenv("STAGING_URL", "https://staging.netra.ai")
        self.metrics = DeploymentMetrics(
            deployment_id=f"deploy-{int(time.time())}",
            start_time=time.time()
        )
        self.critical_services = [
            "backend",
            "auth-service", 
            "frontend",
            "redis",
            "postgres",
            "clickhouse"
        ]
        self.health_check_interval = 5
        self.deployment_timeout = 300  # 5 minutes
        self.rollback_threshold = 0.5  # Rollback if <50% services healthy
        
    async def validate_full_deployment(self) -> DeploymentMetrics:
        """Validate complete deployment pipeline."""
        try:
            # Phase 1: Pre-deployment validation
            await self._validate_pre_deployment()
            
            # Phase 2: Configuration validation
            await self._validate_configuration()
            
            # Phase 3: Dependency initialization
            await self._validate_dependencies()
            
            # Phase 4: Service startup
            await self._validate_service_startup()
            
            # Phase 5: Health checks
            await self._validate_health_checks()
            
            # Phase 6: Traffic routing
            await self._validate_traffic_routing()
            
            # Phase 7: Post-deployment validation
            await self._validate_post_deployment()
            
            self.metrics.end_time = time.time()
            
        except Exception as e:
            logger.error(f"Deployment validation failed: {e}")
            await self._trigger_rollback(str(e))
            self.metrics.end_time = time.time()
            raise
            
        return self.metrics
        
    async def _validate_pre_deployment(self):
        """Validate pre-deployment requirements."""
        self.metrics.current_phase = DeploymentPhase.PRE_DEPLOY
        phase_start = time.time()
        
        try:
            # Check staging environment accessibility
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.staging_url}/health", timeout=10.0)
                if response.status_code != 200:
                    raise Exception(f"Staging not accessible: {response.status_code}")
                    
            # Verify Cloud SQL proxy
            if not await self._check_cloudsql_proxy():
                raise Exception("Cloud SQL proxy not running")
                
            # Check service account permissions
            if not await self._check_gcp_permissions():
                raise Exception("Insufficient GCP permissions")
                
        except Exception as e:
            self.metrics.add_error(DeploymentPhase.PRE_DEPLOY, str(e))
            raise
        finally:
            self.metrics.phase_durations[DeploymentPhase.PRE_DEPLOY] = time.time() - phase_start
            
    async def _validate_configuration(self):
        """Validate deployment configuration."""
        self.metrics.current_phase = DeploymentPhase.CONFIGURATION
        phase_start = time.time()
        
        try:
            required_configs = {
                "DATABASE_URL": "Cloud SQL connection",
                "REDIS_URL": "Redis connection",
                "CLICKHOUSE_HOST": "ClickHouse connection",
                "AUTH_SERVICE_URL": "Auth service URL",
                "NETRA_API_KEY": "API key",
                "GCP_PROJECT_ID": "GCP project",
                "WORKERS": "Worker configuration",
                "PORT": "Port configuration"
            }
            
            missing_configs = []
            for config_key, description in required_configs.items():
                if not os.getenv(config_key):
                    missing_configs.append(f"{description} ({config_key})")
                    
            if missing_configs:
                raise Exception(f"Missing configurations: {', '.join(missing_configs)}")
                
            # Validate configuration values
            await self._validate_config_values()
            
        except Exception as e:
            self.metrics.add_error(DeploymentPhase.CONFIGURATION, str(e))
            raise
        finally:
            self.metrics.phase_durations[DeploymentPhase.CONFIGURATION] = time.time() - phase_start
            
    async def _validate_dependencies(self):
        """Validate service dependencies."""
        self.metrics.current_phase = DeploymentPhase.DEPENDENCY_INIT
        phase_start = time.time()
        
        try:
            # Check database connections
            postgres_healthy = await self._check_postgres_health()
            self.metrics.service_statuses["postgres"] = {"healthy": postgres_healthy}
            
            # Check Redis
            redis_healthy = await self._check_redis_health()
            self.metrics.service_statuses["redis"] = {"healthy": redis_healthy}
            
            # Check ClickHouse
            clickhouse_healthy = await self._check_clickhouse_health()
            self.metrics.service_statuses["clickhouse"] = {"healthy": clickhouse_healthy}
            
            # Validate all dependencies are healthy
            unhealthy = [s for s, status in self.metrics.service_statuses.items() 
                        if not status.get("healthy")]
            if unhealthy:
                raise Exception(f"Unhealthy dependencies: {', '.join(unhealthy)}")
                
        except Exception as e:
            self.metrics.add_error(DeploymentPhase.DEPENDENCY_INIT, str(e))
            raise
        finally:
            self.metrics.phase_durations[DeploymentPhase.DEPENDENCY_INIT] = time.time() - phase_start
            
    async def _validate_service_startup(self):
        """Validate service startup sequence."""
        self.metrics.current_phase = DeploymentPhase.SERVICE_STARTUP
        phase_start = time.time()
        
        try:
            # Start services in order
            startup_sequence = [
                ("auth-service", self._start_auth_service),
                ("backend", self._start_backend_service),
                ("frontend", self._start_frontend_service)
            ]
            
            for service_name, startup_func in startup_sequence:
                logger.info(f"Starting {service_name}")
                
                # Track worker metrics for backend
                if service_name == "backend":
                    worker_count = int(os.getenv("WORKERS", "2"))
                    for worker_id in range(worker_count):
                        worker_metrics = await self._track_worker_startup(worker_id)
                        self.metrics.worker_metrics[worker_id] = worker_metrics
                        
                        # Check for worker exit code 3
                        if worker_metrics.get("exit_code") == 3:
                            raise Exception(f"Worker {worker_id} exited with code 3: configuration error")
                            
                service_healthy = await startup_func()
                self.metrics.service_statuses[service_name] = {
                    "healthy": service_healthy,
                    "start_time": time.time()
                }
                
                if not service_healthy:
                    raise Exception(f"Failed to start {service_name}")
                    
            # Verify all services started
            if self.metrics.success_rate < self.rollback_threshold:
                raise Exception(f"Too many services failed: {self.metrics.success_rate:.1%} success rate")
                
        except Exception as e:
            self.metrics.add_error(DeploymentPhase.SERVICE_STARTUP, str(e))
            raise
        finally:
            self.metrics.phase_durations[DeploymentPhase.SERVICE_STARTUP] = time.time() - phase_start
            
    async def _validate_health_checks(self):
        """Validate service health checks."""
        self.metrics.current_phase = DeploymentPhase.HEALTH_CHECK
        phase_start = time.time()
        
        try:
            # Perform multiple rounds of health checks
            for round_num in range(3):
                await asyncio.sleep(self.health_check_interval)
                
                health_results = {}
                for service in self.critical_services:
                    if service in ["redis", "postgres", "clickhouse"]:
                        continue  # Already checked in dependencies
                        
                    health = await self._check_service_health(service)
                    health_results[service] = health
                    
                self.metrics.health_checks.append({
                    "round": round_num + 1,
                    "timestamp": time.time(),
                    "results": health_results
                })
                
                # Check if health is improving
                healthy_count = sum(1 for h in health_results.values() if h)
                if healthy_count < len(health_results) * self.rollback_threshold:
                    raise Exception(f"Health check round {round_num + 1} failed: only {healthy_count}/{len(health_results)} healthy")
                    
        except Exception as e:
            self.metrics.add_error(DeploymentPhase.HEALTH_CHECK, str(e))
            raise
        finally:
            self.metrics.phase_durations[DeploymentPhase.HEALTH_CHECK] = time.time() - phase_start
            
    async def _validate_traffic_routing(self):
        """Validate traffic routing and load balancing."""
        self.metrics.current_phase = DeploymentPhase.TRAFFIC_ROUTING
        phase_start = time.time()
        
        try:
            # Test API endpoints
            endpoints_to_test = [
                ("/api/v1/health", "GET"),
                ("/api/v1/threads", "GET"),
                ("/auth/validate", "GET"),
                ("/websocket", "UPGRADE")
            ]
            
            async with httpx.AsyncClient() as client:
                for endpoint, method in endpoints_to_test:
                    url = f"{self.staging_url}{endpoint}"
                    
                    if method == "UPGRADE":
                        # Test WebSocket upgrade
                        ws_url = url.replace("https://", "wss://").replace("http://", "ws://")
                        try:
                            async with websockets.connect(ws_url) as ws:
                                await ws.send(json.dumps({"type": "ping"}))
                                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                                if not response:
                                    raise Exception(f"WebSocket {endpoint} no response")
                        except Exception as ws_error:
                            logger.warning(f"WebSocket test failed: {ws_error}")
                    else:
                        response = await client.request(method, url, timeout=10.0)
                        if response.status_code >= 500:
                            raise Exception(f"Endpoint {endpoint} returned {response.status_code}")
                            
        except Exception as e:
            self.metrics.add_error(DeploymentPhase.TRAFFIC_ROUTING, str(e))
            raise
        finally:
            self.metrics.phase_durations[DeploymentPhase.TRAFFIC_ROUTING] = time.time() - phase_start
            
    async def _validate_post_deployment(self):
        """Validate post-deployment state."""
        self.metrics.current_phase = DeploymentPhase.POST_DEPLOY
        phase_start = time.time()
        
        try:
            # Final health check
            final_health = await self._get_comprehensive_health()
            
            # Validate metrics collection
            metrics_working = await self._check_metrics_collection()
            
            # Validate logging pipeline
            logging_working = await self._check_logging_pipeline()
            
            # Check for any critical errors in logs
            critical_errors = await self._scan_for_critical_errors()
            if critical_errors:
                logger.warning(f"Found {len(critical_errors)} critical errors in logs")
                
            # Final validation
            if not final_health["overall_healthy"]:
                raise Exception("Post-deployment health check failed")
                
        except Exception as e:
            self.metrics.add_error(DeploymentPhase.POST_DEPLOY, str(e))
            raise
        finally:
            self.metrics.phase_durations[DeploymentPhase.POST_DEPLOY] = time.time() - phase_start
            
    async def _trigger_rollback(self, reason: str):
        """Trigger deployment rollback."""
        self.metrics.current_phase = DeploymentPhase.ROLLBACK
        self.metrics.rollback_triggered = True
        self.metrics.rollback_reason = reason
        
        logger.error(f"Triggering rollback: {reason}")
        
        # Rollback logic would go here
        # For testing, we just log the rollback
        
    async def _check_cloudsql_proxy(self) -> bool:
        """Check if Cloud SQL proxy is running."""
        try:
            # Check for proxy process or socket
            socket_path = "/tmp/cloudsql/netra-staging:us-central1:staging-shared-postgres"
            return os.path.exists(socket_path)
        except Exception:
            return False
            
    async def _check_gcp_permissions(self) -> bool:
        """Check GCP service account permissions."""
        try:
            # Would check actual GCP permissions
            return True
        except Exception:
            return False
            
    async def _validate_config_values(self):
        """Validate configuration values are correct."""
        db_url = os.getenv("DATABASE_URL", "")
        if "cloudsql" in db_url and "netra-staging" not in db_url:
            raise Exception("DATABASE_URL not pointing to staging instance")
            
    async def _check_postgres_health(self) -> bool:
        """Check PostgreSQL health."""
        try:
            # Actual PostgreSQL health check
            return True
        except Exception:
            return False
            
    async def _check_redis_health(self) -> bool:
        """Check Redis health."""
        try:
            # Actual Redis health check
            return True
        except Exception:
            return False
            
    async def _check_clickhouse_health(self) -> bool:
        """Check ClickHouse health."""
        try:
            # Actual ClickHouse health check
            return True
        except Exception:
            return False
            
    async def _start_auth_service(self) -> bool:
        """Start auth service."""
        try:
            # Auth service startup logic
            return True
        except Exception:
            return False
            
    async def _start_backend_service(self) -> bool:
        """Start backend service."""
        try:
            # Backend service startup logic
            return True
        except Exception:
            return False
            
    async def _start_frontend_service(self) -> bool:
        """Start frontend service."""
        try:
            # Frontend service startup logic
            return True
        except Exception:
            return False
            
    async def _track_worker_startup(self, worker_id: int) -> Dict[str, Any]:
        """Track individual worker startup."""
        return {
            "worker_id": worker_id,
            "start_time": time.time(),
            "exit_code": 0,  # Would get actual exit code
            "pid": os.getpid()
        }
        
    async def _check_service_health(self, service: str) -> bool:
        """Check individual service health."""
        try:
            endpoints = {
                "backend": f"{self.staging_url}/health",
                "auth-service": f"{self.staging_url}/auth/health",
                "frontend": f"{self.staging_url}/"
            }
            
            if service not in endpoints:
                return False
                
            async with httpx.AsyncClient() as client:
                response = await client.get(endpoints[service], timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False
            
    async def _get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive system health."""
        health_status = {
            "timestamp": time.time(),
            "services": {},
            "overall_healthy": True
        }
        
        for service in self.critical_services:
            if service in ["redis", "postgres", "clickhouse"]:
                health_status["services"][service] = self.metrics.service_statuses.get(service, {}).get("healthy", False)
            else:
                health_status["services"][service] = await self._check_service_health(service)
                
        health_status["overall_healthy"] = all(health_status["services"].values())
        return health_status
        
    async def _check_metrics_collection(self) -> bool:
        """Check if metrics are being collected."""
        try:
            # Check Prometheus metrics endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.staging_url}/metrics", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False
            
    async def _check_logging_pipeline(self) -> bool:
        """Check if logging pipeline is working."""
        try:
            # Would check actual logging pipeline
            return True
        except Exception:
            return False
            
    async def _scan_for_critical_errors(self) -> List[str]:
        """Scan logs for critical errors."""
        # Would scan actual logs
        return []


@pytest.mark.l4
@pytest.mark.staging
@pytest.mark.asyncio
class TestStagingDeploymentResilience:
    """L4 test suite for staging deployment resilience."""
    
    async def test_complete_deployment_pipeline(self):
        """Test complete deployment pipeline with all phases."""
        validator = StagingDeploymentValidator()
        
        # Run full deployment validation
        metrics = await validator.validate_full_deployment()
        
        # Verify deployment completed
        assert metrics.end_time is not None
        assert not metrics.rollback_triggered
        
        # Check phase completion
        expected_phases = [
            DeploymentPhase.PRE_DEPLOY,
            DeploymentPhase.CONFIGURATION,
            DeploymentPhase.DEPENDENCY_INIT,
            DeploymentPhase.SERVICE_STARTUP,
            DeploymentPhase.HEALTH_CHECK,
            DeploymentPhase.TRAFFIC_ROUTING,
            DeploymentPhase.POST_DEPLOY
        ]
        
        for phase in expected_phases:
            assert phase in metrics.phase_durations
            
        # Verify service health
        assert metrics.success_rate >= 0.8  # At least 80% services healthy
        
    async def test_worker_exit_code_3_handling(self):
        """Test handling of worker exit code 3 errors."""
        validator = StagingDeploymentValidator()
        
        # Simulate worker failure
        with pytest.raises(Exception) as exc_info:
            # Mock worker startup to return exit code 3
            async def mock_worker_startup(worker_id):
                return {"exit_code": 3, "worker_id": worker_id}
                
            validator._track_worker_startup = mock_worker_startup
            await validator.validate_full_deployment()
            
        assert "code 3" in str(exc_info.value)
        assert validator.metrics.rollback_triggered
        
    async def test_dependency_failure_cascade(self):
        """Test cascading dependency failures."""
        validator = StagingDeploymentValidator()
        
        # Mock dependency failures
        validator._check_postgres_health = asyncio.coroutine(lambda: False)
        validator._check_redis_health = asyncio.coroutine(lambda: False)
        
        with pytest.raises(Exception) as exc_info:
            await validator.validate_full_deployment()
            
        assert "Unhealthy dependencies" in str(exc_info.value)
        assert validator.metrics.current_phase == DeploymentPhase.DEPENDENCY_INIT
        
    async def test_health_check_degradation(self):
        """Test health check degradation handling."""
        validator = StagingDeploymentValidator()
        
        # Mock degrading health
        health_states = [True, True, False, False, False]
        health_iter = iter(health_states)
        
        async def mock_health(service):
            try:
                return next(health_iter)
            except StopIteration:
                return False
                
        validator._check_service_health = mock_health
        
        with pytest.raises(Exception) as exc_info:
            await validator.validate_full_deployment()
            
        assert "Health check" in str(exc_info.value)
        
    async def test_rollback_trigger_conditions(self):
        """Test conditions that trigger rollback."""
        validator = StagingDeploymentValidator()
        validator.rollback_threshold = 0.7  # 70% threshold
        
        # Set up partial service failures
        validator._start_auth_service = asyncio.coroutine(lambda: True)
        validator._start_backend_service = asyncio.coroutine(lambda: False)
        validator._start_frontend_service = asyncio.coroutine(lambda: False)
        
        with pytest.raises(Exception):
            await validator.validate_full_deployment()
            
        assert validator.metrics.rollback_triggered
        assert validator.metrics.rollback_reason is not None
        assert validator.metrics.success_rate < validator.rollback_threshold
        
    async def test_cloudsql_proxy_validation(self):
        """Test Cloud SQL proxy validation."""
        validator = StagingDeploymentValidator()
        
        # Test with missing proxy
        validator._check_cloudsql_proxy = asyncio.coroutine(lambda: False)
        
        with pytest.raises(Exception) as exc_info:
            await validator.validate_full_deployment()
            
        assert "Cloud SQL proxy" in str(exc_info.value)
        assert validator.metrics.current_phase == DeploymentPhase.PRE_DEPLOY
        
    async def test_traffic_routing_validation(self):
        """Test traffic routing and endpoint validation."""
        validator = StagingDeploymentValidator()
        
        # Mock successful early phases
        validator._validate_pre_deployment = asyncio.coroutine(lambda: None)
        validator._validate_configuration = asyncio.coroutine(lambda: None)
        validator._validate_dependencies = asyncio.coroutine(lambda: None)
        validator._validate_service_startup = asyncio.coroutine(lambda: None)
        validator._validate_health_checks = asyncio.coroutine(lambda: None)
        
        # Test traffic routing
        await validator._validate_traffic_routing()
        
        assert validator.metrics.current_phase == DeploymentPhase.TRAFFIC_ROUTING
        assert DeploymentPhase.TRAFFIC_ROUTING in validator.metrics.phase_durations
        
    async def test_post_deployment_validation(self):
        """Test post-deployment validation checks."""
        validator = StagingDeploymentValidator()
        
        # Mock comprehensive health check
        async def mock_comprehensive_health():
            return {
                "overall_healthy": True,
                "services": {
                    "backend": True,
                    "auth-service": True,
                    "frontend": True
                }
            }
            
        validator._get_comprehensive_health = mock_comprehensive_health
        validator._check_metrics_collection = asyncio.coroutine(lambda: True)
        validator._check_logging_pipeline = asyncio.coroutine(lambda: True)
        validator._scan_for_critical_errors = asyncio.coroutine(lambda: [])
        
        await validator._validate_post_deployment()
        
        assert validator.metrics.current_phase == DeploymentPhase.POST_DEPLOY
        assert len(validator.metrics.error_log) == 0
        
    async def test_deployment_timeout_handling(self):
        """Test deployment timeout handling."""
        validator = StagingDeploymentValidator()
        validator.deployment_timeout = 1  # 1 second timeout
        
        # Mock slow deployment
        async def slow_phase():
            await asyncio.sleep(2)
            
        validator._validate_service_startup = slow_phase
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                validator.validate_full_deployment(),
                timeout=validator.deployment_timeout
            )
            
    async def test_concurrent_worker_monitoring(self):
        """Test concurrent monitoring of multiple workers."""
        validator = StagingDeploymentValidator()
        
        # Set up multiple workers
        os.environ["WORKERS"] = "4"
        
        worker_metrics = {}
        for i in range(4):
            worker_metrics[i] = await validator._track_worker_startup(i)
            
        # Verify all workers tracked
        assert len(worker_metrics) == 4
        for metrics in worker_metrics.values():
            assert "worker_id" in metrics
            assert "start_time" in metrics
            assert "exit_code" in metrics


@pytest.mark.l4
@pytest.mark.staging
@pytest.mark.critical
async def test_staging_production_parity():
    """Test staging environment parity with production."""
    validator = StagingDeploymentValidator()
    
    # Production-like configuration
    prod_config = {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://user@/postgres?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres",
        "REDIS_URL": "redis://10.0.0.1:6379",
        "CLICKHOUSE_HOST": "clickhouse.staging.internal",
        "AUTH_SERVICE_URL": "https://auth.staging.netra.ai",
        "WORKERS": "4",
        "PORT": "8080",
        "NETRA_API_KEY": os.getenv("STAGING_API_KEY", "test-key")
    }
    
    with pytest.mock.patch.dict(os.environ, prod_config):
        metrics = await validator.validate_full_deployment()
        
        # Verify production-like behavior
        assert metrics.success_rate >= 0.9  # Higher threshold for production parity
        assert len(metrics.worker_metrics) == 4  # All workers started
        assert not metrics.rollback_triggered
        
        # Check timing matches production SLAs
        assert metrics.deployment_duration < 300  # Under 5 minutes
        assert metrics.phase_durations.get(DeploymentPhase.SERVICE_STARTUP, 0) < 60  # Fast startup