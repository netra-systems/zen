"""
Integration Tests: Multi-Service Failure Coordination & Recovery

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Coordinate error handling across distributed service architecture
- Value Impact: Multi-service coordination prevents cascade failures and maintains system coherence
- Strategic Impact: Foundation for reliable distributed AI service delivery and scalability

This test suite validates multi-service coordination patterns with real services:
- Cross-service error propagation and isolation with PostgreSQL and Redis
- Service dependency mapping and failure impact analysis
- Coordinated recovery procedures across service boundaries
- Distributed health monitoring and alerting systems
- Service mesh resilience patterns and communication fallbacks
- Business continuity planning during multi-service outages

CRITICAL: Uses REAL PostgreSQL, Redis, and service connections - NO MOCKS for integration testing.
Tests validate actual service coordination, failure propagation, and recovery effectiveness.
"""

import asyncio
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Callable, Tuple
from enum import Enum
import pytest
from dataclasses import dataclass, asdict

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.isolated_environment import get_env

# Core imports
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ServiceState(Enum):
    """Service operational state levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


@dataclass
class ServiceDependency:
    """Represents a dependency relationship between services."""
    dependent_service: str
    dependency_service: str
    dependency_type: str  # "hard", "soft", "optional"
    recovery_strategy: str  # "wait", "fallback", "degrade"
    timeout_seconds: float = 30.0


@dataclass
class ServiceHealthMetrics:
    """Health metrics for a service."""
    service_name: str
    state: ServiceState
    response_time_ms: float
    error_rate: float
    throughput_ops_per_sec: float
    last_health_check: datetime
    consecutive_failures: int = 0
    recovery_attempts: int = 0


class MultiServiceCoordinator:
    """Coordinates error handling and recovery across multiple services."""
    
    def __init__(self, postgres_connection, redis_connection):
        self.postgres = postgres_connection
        self.redis = redis_connection
        self.services = {}
        self.dependencies = {}
        self.health_metrics = {}
        self.failure_events = []
        self.recovery_procedures = {}
        self.alert_handlers = {}
        
    async def register_service(self, service_name: str, initial_state: ServiceState = ServiceState.HEALTHY):
        """Register a service for coordination."""
        self.services[service_name] = {
            "name": service_name,
            "state": initial_state,
            "registered_at": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc)
        }
        
        # Initialize health metrics
        self.health_metrics[service_name] = ServiceHealthMetrics(
            service_name=service_name,
            state=initial_state,
            response_time_ms=0.0,
            error_rate=0.0,
            throughput_ops_per_sec=0.0,
            last_health_check=datetime.now(timezone.utc)
        )
        
        # Store in Redis for distributed coordination
        await self.redis.set_json(f"service_state:{service_name}", {
            "state": initial_state.value,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }, ex=300)
    
    async def register_dependency(self, dependency: ServiceDependency):
        """Register service dependency relationship."""
        dep_key = f"{dependency.dependent_service}:{dependency.dependency_service}"
        self.dependencies[dep_key] = dependency
        
        # Store dependency mapping in database
        await self.postgres.execute("""
            INSERT INTO service_dependencies (dependent_service, dependency_service, dependency_type, recovery_strategy, timeout_seconds)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (dependent_service, dependency_service) DO UPDATE SET
                dependency_type = EXCLUDED.dependency_type,
                recovery_strategy = EXCLUDED.recovery_strategy,
                timeout_seconds = EXCLUDED.timeout_seconds,
                updated_at = NOW()
        """, dependency.dependent_service, dependency.dependency_service, 
            dependency.dependency_type, dependency.recovery_strategy, dependency.timeout_seconds)
    
    async def simulate_service_failure(self, service_name: str, failure_type: str = "unresponsive") -> Dict[str, Any]:
        """Simulate service failure and trigger coordination response."""
        failure_start = time.time()
        failure_id = str(uuid.uuid4())
        
        # Record failure event
        failure_event = {
            "failure_id": failure_id,
            "service_name": service_name,
            "failure_type": failure_type,
            "timestamp": datetime.now(timezone.utc),
            "initiated_by": "test_framework"
        }
        
        self.failure_events.append(failure_event)
        
        # Update service state
        old_state = self.services[service_name]["state"]
        self.services[service_name]["state"] = ServiceState.FAILED
        self.services[service_name]["last_updated"] = datetime.now(timezone.utc)
        
        # Update health metrics
        self.health_metrics[service_name].state = ServiceState.FAILED
        self.health_metrics[service_name].consecutive_failures += 1
        self.health_metrics[service_name].last_health_check = datetime.now(timezone.utc)
        
        # Update Redis state
        await self.redis.set_json(f"service_state:{service_name}", {
            "state": ServiceState.FAILED.value,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "failure_id": failure_id,
            "failure_type": failure_type
        }, ex=300)
        
        # Find dependent services
        affected_services = await self._analyze_failure_impact(service_name)
        
        # Coordinate response across affected services
        coordination_result = await self._coordinate_failure_response(service_name, affected_services)
        
        failure_duration = time.time() - failure_start
        
        # Log failure event to database
        await self.postgres.execute("""
            INSERT INTO service_failure_events (failure_id, service_name, failure_type, affected_services, coordination_result, failure_duration_ms)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, failure_id, service_name, failure_type, 
            json.dumps([svc["service"] for svc in affected_services]),
            json.dumps(coordination_result), failure_duration * 1000)
        
        return {
            "failure_id": failure_id,
            "failed_service": service_name,
            "failure_type": failure_type,
            "affected_services": affected_services,
            "coordination_result": coordination_result,
            "failure_duration_ms": failure_duration * 1000,
            "business_impact": {
                "services_degraded": len([svc for svc in affected_services if svc["impact"] == "degraded"]),
                "services_failed": len([svc for svc in affected_services if svc["impact"] == "failed"]),
                "recovery_coordination_active": coordination_result["recovery_initiated"],
                "business_continuity_maintained": coordination_result["business_continuity_score"] >= 0.5
            }
        }
    
    async def _analyze_failure_impact(self, failed_service: str) -> List[Dict[str, Any]]:
        """Analyze the impact of service failure on dependent services."""
        affected_services = []
        
        # Find all services that depend on the failed service
        for dep_key, dependency in self.dependencies.items():
            if dependency.dependency_service == failed_service:
                dependent_service = dependency.dependent_service
                
                # Determine impact based on dependency type
                if dependency.dependency_type == "hard":
                    impact = "failed"
                    new_state = ServiceState.FAILED
                elif dependency.dependency_type == "soft":
                    impact = "degraded"
                    new_state = ServiceState.DEGRADED
                else:  # optional
                    impact = "minimal"
                    new_state = ServiceState.HEALTHY
                
                # Update dependent service state
                if dependent_service in self.services:
                    self.services[dependent_service]["state"] = new_state
                    self.health_metrics[dependent_service].state = new_state
                    
                    # Update Redis
                    await self.redis.set_json(f"service_state:{dependent_service}", {
                        "state": new_state.value,
                        "last_updated": datetime.now(timezone.utc).isoformat(),
                        "affected_by_failure": failed_service
                    }, ex=300)
                
                affected_services.append({
                    "service": dependent_service,
                    "dependency_type": dependency.dependency_type,
                    "impact": impact,
                    "new_state": new_state.value,
                    "recovery_strategy": dependency.recovery_strategy
                })
        
        return affected_services
    
    async def _coordinate_failure_response(self, failed_service: str, affected_services: List[Dict]) -> Dict[str, Any]:
        """Coordinate recovery response across affected services."""
        coordination_start = time.time()
        
        # Initialize recovery coordination
        recovery_actions = []
        alerts_sent = []
        fallback_services_activated = []
        
        # Execute recovery strategies for each affected service
        for affected in affected_services:
            service_name = affected["service"]
            recovery_strategy = affected["recovery_strategy"]
            
            if recovery_strategy == "wait":
                # Wait for dependency to recover
                recovery_actions.append({
                    "service": service_name,
                    "action": "wait_for_dependency_recovery",
                    "target_service": failed_service,
                    "timeout": self.dependencies.get(f"{service_name}:{failed_service}", ServiceDependency("", "", "", "")).timeout_seconds
                })
                
            elif recovery_strategy == "fallback":
                # Activate fallback service
                fallback_service = f"{service_name}_fallback"
                fallback_services_activated.append(fallback_service)
                
                recovery_actions.append({
                    "service": service_name,
                    "action": "activate_fallback",
                    "fallback_service": fallback_service
                })
                
                # Update service state to degraded (using fallback)
                self.services[service_name]["state"] = ServiceState.DEGRADED
                self.health_metrics[service_name].state = ServiceState.DEGRADED
                
            elif recovery_strategy == "degrade":
                # Gracefully degrade service capabilities
                recovery_actions.append({
                    "service": service_name,
                    "action": "graceful_degradation",
                    "degradation_level": affected["impact"]
                })
        
        # Send coordinated alerts
        critical_services_affected = [svc for svc in affected_services if svc["impact"] == "failed"]
        if critical_services_affected:
            alert = {
                "alert_type": "multi_service_failure",
                "failed_service": failed_service,
                "critical_services_affected": len(critical_services_affected),
                "total_services_affected": len(affected_services),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            alerts_sent.append(alert)
            
            # Store alert in Redis
            await self.redis.set_json(f"alert:{failed_service}:{int(time.time())}", alert, ex=3600)
        
        # Calculate business continuity score
        total_services = len(self.services)
        healthy_services = len([svc for svc in self.services.values() if svc["state"] == ServiceState.HEALTHY])
        degraded_services = len([svc for svc in self.services.values() if svc["state"] == ServiceState.DEGRADED])
        
        business_continuity_score = (healthy_services + degraded_services * 0.5) / total_services
        
        coordination_duration = time.time() - coordination_start
        
        return {
            "coordination_duration_ms": coordination_duration * 1000,
            "recovery_actions": recovery_actions,
            "alerts_sent": alerts_sent,
            "fallback_services_activated": fallback_services_activated,
            "business_continuity_score": business_continuity_score,
            "recovery_initiated": len(recovery_actions) > 0,
            "coordination_successful": coordination_duration < 5.0  # Should complete quickly
        }
    
    async def simulate_service_recovery(self, service_name: str) -> Dict[str, Any]:
        """Simulate service recovery and coordinate restoration."""
        recovery_start = time.time()
        recovery_id = str(uuid.uuid4())
        
        # Update service state to recovering
        self.services[service_name]["state"] = ServiceState.RECOVERING
        self.health_metrics[service_name].state = ServiceState.RECOVERING
        self.health_metrics[service_name].recovery_attempts += 1
        
        # Find services affected by this recovery
        recovering_services = []
        
        for dep_key, dependency in self.dependencies.items():
            if dependency.dependency_service == service_name:
                dependent_service = dependency.dependent_service
                
                if dependent_service in self.services:
                    # Restore dependent service based on dependency type
                    if dependency.dependency_type in ["hard", "soft"]:
                        self.services[dependent_service]["state"] = ServiceState.HEALTHY
                        self.health_metrics[dependent_service].state = ServiceState.HEALTHY
                        self.health_metrics[dependent_service].consecutive_failures = 0
                        
                        recovering_services.append({
                            "service": dependent_service,
                            "dependency_type": dependency.dependency_type,
                            "restored_to": "healthy"
                        })
        
        # Complete service recovery
        self.services[service_name]["state"] = ServiceState.HEALTHY
        self.health_metrics[service_name].state = ServiceState.HEALTHY
        self.health_metrics[service_name].consecutive_failures = 0
        
        # Update Redis states
        for service in [service_name] + [svc["service"] for svc in recovering_services]:
            await self.redis.set_json(f"service_state:{service}", {
                "state": ServiceState.HEALTHY.value,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "recovered_at": datetime.now(timezone.utc).isoformat(),
                "recovery_id": recovery_id
            }, ex=300)
        
        recovery_duration = time.time() - recovery_start
        
        # Log recovery event
        await self.postgres.execute("""
            INSERT INTO service_recovery_events (recovery_id, service_name, recovering_services, recovery_duration_ms)
            VALUES ($1, $2, $3, $4)
        """, recovery_id, service_name, 
            json.dumps([svc["service"] for svc in recovering_services]),
            recovery_duration * 1000)
        
        return {
            "recovery_id": recovery_id,
            "recovered_service": service_name,
            "dependent_services_restored": recovering_services,
            "recovery_duration_ms": recovery_duration * 1000,
            "total_services_recovered": len(recovering_services) + 1
        }
    
    async def get_system_health_overview(self) -> Dict[str, Any]:
        """Get comprehensive system health from multi-service perspective."""
        total_services = len(self.services)
        healthy_count = len([svc for svc in self.services.values() if svc["state"] == ServiceState.HEALTHY])
        degraded_count = len([svc for svc in self.services.values() if svc["state"] == ServiceState.DEGRADED])
        failed_count = len([svc for svc in self.services.values() if svc["state"] == ServiceState.FAILED])
        recovering_count = len([svc for svc in self.services.values() if svc["state"] == ServiceState.RECOVERING])
        
        # Calculate system-wide metrics
        avg_response_time = sum(metrics.response_time_ms for metrics in self.health_metrics.values()) / max(total_services, 1)
        avg_error_rate = sum(metrics.error_rate for metrics in self.health_metrics.values()) / max(total_services, 1)
        total_throughput = sum(metrics.throughput_ops_per_sec for metrics in self.health_metrics.values())
        
        return {
            "system_health": "healthy" if failed_count == 0 else "degraded" if healthy_count > failed_count else "critical",
            "service_counts": {
                "total": total_services,
                "healthy": healthy_count,
                "degraded": degraded_count,
                "failed": failed_count,
                "recovering": recovering_count
            },
            "health_ratios": {
                "healthy_ratio": healthy_count / max(total_services, 1),
                "availability_ratio": (healthy_count + degraded_count) / max(total_services, 1),
                "failure_ratio": failed_count / max(total_services, 1)
            },
            "performance_metrics": {
                "avg_response_time_ms": avg_response_time,
                "avg_error_rate": avg_error_rate,
                "total_throughput_ops_per_sec": total_throughput
            },
            "failure_events_count": len(self.failure_events),
            "dependencies_count": len(self.dependencies),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }


class TestMultiServiceCoordination(BaseIntegrationTest):
    """Integration tests for multi-service failure coordination and recovery."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.env.set("USE_REAL_SERVICES", "true", source="test")
        self.auth_helper = E2EAuthHelper()
    
    @pytest.fixture
    async def service_coordinator(self, real_services_fixture):
        """Create multi-service coordinator with real database connections."""
        postgres = real_services_fixture["postgres"]
        redis = real_services_fixture["redis"]
        
        coordinator = MultiServiceCoordinator(postgres, redis)
        
        # Set up database tables
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS service_dependencies (
                id SERIAL PRIMARY KEY,
                dependent_service TEXT NOT NULL,
                dependency_service TEXT NOT NULL,
                dependency_type TEXT NOT NULL,
                recovery_strategy TEXT NOT NULL,
                timeout_seconds DECIMAL NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(dependent_service, dependency_service)
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS service_failure_events (
                id SERIAL PRIMARY KEY,
                failure_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                failure_type TEXT NOT NULL,
                affected_services JSONB,
                coordination_result JSONB,
                failure_duration_ms DECIMAL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS service_recovery_events (
                id SERIAL PRIMARY KEY,
                recovery_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                recovering_services JSONB,
                recovery_duration_ms DECIMAL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Register test services
        services = ["auth_service", "llm_service", "database_service", "cache_service", "search_service", "notification_service"]
        for service in services:
            await coordinator.register_service(service)
        
        # Register service dependencies
        dependencies = [
            ServiceDependency("llm_service", "auth_service", "hard", "wait", 30.0),
            ServiceDependency("search_service", "database_service", "hard", "fallback", 15.0),
            ServiceDependency("notification_service", "database_service", "soft", "degrade", 10.0),
            ServiceDependency("llm_service", "cache_service", "soft", "degrade", 5.0),
            ServiceDependency("search_service", "cache_service", "optional", "degrade", 5.0),
            ServiceDependency("notification_service", "llm_service", "optional", "degrade", 20.0),
        ]
        
        for dependency in dependencies:
            await coordinator.register_dependency(dependency)
        
        yield coordinator
        
        # Cleanup database tables
        await postgres.execute("DROP TABLE IF EXISTS service_recovery_events")
        await postgres.execute("DROP TABLE IF EXISTS service_failure_events")
        await postgres.execute("DROP TABLE IF EXISTS service_dependencies")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cascade_failure_coordination(self, real_services_fixture, service_coordinator):
        """Test coordinated response to cascading service failures."""
        
        # Business Value: Coordinated response minimizes business disruption during cascade failures
        
        # Get initial system health
        initial_health = await service_coordinator.get_system_health_overview()
        assert initial_health["system_health"] == "healthy"
        assert initial_health["service_counts"]["healthy"] == 6
        
        # Simulate primary service failure (database_service)
        database_failure = await service_coordinator.simulate_service_failure("database_service", "connection_timeout")
        
        # Validate failure coordination
        assert database_failure["failed_service"] == "database_service"
        assert len(database_failure["affected_services"]) >= 2  # search_service and notification_service depend on database
        
        # Check specific service impacts
        affected_service_names = [svc["service"] for svc in database_failure["affected_services"]]
        assert "search_service" in affected_service_names
        assert "notification_service" in affected_service_names
        
        # Verify coordination result
        coordination = database_failure["coordination_result"]
        assert coordination["recovery_initiated"] is True
        assert coordination["coordination_successful"] is True
        assert len(coordination["recovery_actions"]) >= 2
        
        # Check business impact assessment
        business_impact = database_failure["business_impact"]
        assert business_impact["recovery_coordination_active"] is True
        
        # Verify system health degradation
        post_failure_health = await service_coordinator.get_system_health_overview()
        assert post_failure_health["system_health"] in ["degraded", "critical"]
        assert post_failure_health["service_counts"]["failed"] >= 1
        assert post_failure_health["service_counts"]["healthy"] < initial_health["service_counts"]["healthy"]
        
        # Simulate secondary failure (auth_service)
        auth_failure = await service_coordinator.simulate_service_failure("auth_service", "service_crash")
        
        # This should affect llm_service due to hard dependency
        auth_affected = [svc for svc in auth_failure["affected_services"] if svc["service"] == "llm_service"]
        assert len(auth_affected) == 1
        assert auth_affected[0]["impact"] == "failed"  # Hard dependency should cause failure
        
        # System should now be in critical state
        critical_health = await service_coordinator.get_system_health_overview()
        assert critical_health["service_counts"]["failed"] >= 3  # database, auth, llm at minimum
        assert critical_health["health_ratios"]["failure_ratio"] >= 0.3  # Significant failure rate
        
        logger.info(" PASS:  Cascade failure coordination test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_coordinated_recovery_sequencing(self, real_services_fixture, service_coordinator):
        """Test coordinated recovery sequencing across dependent services."""
        
        # Business Value: Proper recovery sequencing ensures stable system restoration
        
        postgres = real_services_fixture["postgres"]
        
        # Create initial failure state
        await service_coordinator.simulate_service_failure("database_service", "outage")
        await service_coordinator.simulate_service_failure("auth_service", "network_partition")
        
        # Verify degraded state
        degraded_health = await service_coordinator.get_system_health_overview()
        assert degraded_health["system_health"] in ["degraded", "critical"]
        
        # Begin coordinated recovery - start with auth_service
        auth_recovery = await service_coordinator.simulate_service_recovery("auth_service")
        
        # Validate auth recovery coordination
        assert auth_recovery["recovered_service"] == "auth_service"
        assert auth_recovery["recovery_duration_ms"] < 1000  # Should be fast
        
        # Check if dependent services were restored
        dependent_services = [svc["service"] for svc in auth_recovery["dependent_services_restored"]]
        assert "llm_service" in dependent_services  # Should be restored with auth
        
        # Log recovery sequence in database
        await postgres.execute("""
            INSERT INTO service_failure_events (failure_id, service_name, failure_type, affected_services, coordination_result)
            VALUES ($1, 'recovery_sequence_test', 'auth_recovery', $2, $3)
        """, "recovery_seq_auth", json.dumps(dependent_services), json.dumps(auth_recovery))
        
        # Verify partial system recovery
        partial_recovery_health = await service_coordinator.get_system_health_overview()
        auth_restored = partial_recovery_health["service_counts"]["healthy"] > degraded_health["service_counts"]["healthy"]
        assert auth_restored, "Auth recovery did not improve system health"
        
        # Continue with database recovery
        database_recovery = await service_coordinator.simulate_service_recovery("database_service")
        
        # Validate database recovery coordination
        assert database_recovery["recovered_service"] == "database_service"
        database_dependent_services = [svc["service"] for svc in database_recovery["dependent_services_restored"]]
        
        # Both search_service and notification_service should be restored
        assert "search_service" in database_dependent_services
        assert "notification_service" in database_dependent_services
        
        # Log database recovery
        await postgres.execute("""
            INSERT INTO service_failure_events (failure_id, service_name, failure_type, affected_services, coordination_result)
            VALUES ($1, 'recovery_sequence_test', 'database_recovery', $2, $3)
        """, "recovery_seq_db", json.dumps(database_dependent_services), json.dumps(database_recovery))
        
        # Verify complete system recovery
        final_health = await service_coordinator.get_system_health_overview()
        assert final_health["system_health"] == "healthy"
        assert final_health["service_counts"]["failed"] == 0
        assert final_health["service_counts"]["healthy"] == 6
        assert final_health["health_ratios"]["healthy_ratio"] == 1.0
        
        # Validate recovery sequence timing
        recovery_events = await postgres.fetch("""
            SELECT service_name, coordination_result, created_at 
            FROM service_failure_events 
            WHERE failure_id LIKE 'recovery_seq_%' 
            ORDER BY created_at
        """)
        
        assert len(recovery_events) == 2
        assert recovery_events[0]["service_name"] == "recovery_sequence_test"  # Auth recovery first
        assert recovery_events[1]["service_name"] == "recovery_sequence_test"  # Database recovery second
        
        # Calculate total recovery time
        total_recovery_time = auth_recovery["recovery_duration_ms"] + database_recovery["recovery_duration_ms"]
        assert total_recovery_time < 5000, "Total recovery time too long"
        
        logger.info(" PASS:  Coordinated recovery sequencing test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_dependency_mapping_accuracy(self, real_services_fixture, service_coordinator):
        """Test accuracy of service dependency mapping and impact analysis."""
        
        # Business Value: Accurate dependency mapping enables precise failure impact prediction
        
        postgres = real_services_fixture["postgres"]
        
        # Verify dependency mappings in database
        stored_dependencies = await postgres.fetch("""
            SELECT dependent_service, dependency_service, dependency_type, recovery_strategy
            FROM service_dependencies
            ORDER BY dependent_service, dependency_service
        """)
        
        assert len(stored_dependencies) >= 6  # Should have the dependencies we registered
        
        # Test each service failure individually to map dependencies
        dependency_test_results = {}
        
        for service_name in ["auth_service", "database_service", "cache_service"]:
            # Reset all services to healthy state first
            for svc_name in service_coordinator.services:
                service_coordinator.services[svc_name]["state"] = ServiceState.HEALTHY
                service_coordinator.health_metrics[svc_name].state = ServiceState.HEALTHY
            
            # Simulate single service failure
            failure_result = await service_coordinator.simulate_service_failure(service_name, "dependency_test")
            
            # Analyze dependency impact
            affected_services = failure_result["affected_services"]
            dependency_test_results[service_name] = {
                "failed_service": service_name,
                "affected_count": len(affected_services),
                "affected_services": affected_services,
                "hard_dependencies": [svc for svc in affected_services if svc["dependency_type"] == "hard"],
                "soft_dependencies": [svc for svc in affected_services if svc["dependency_type"] == "soft"],
                "optional_dependencies": [svc for svc in affected_services if svc["dependency_type"] == "optional"]
            }
        
        # Validate auth_service dependency mapping
        auth_results = dependency_test_results["auth_service"]
        auth_hard_deps = [svc["service"] for svc in auth_results["hard_dependencies"]]
        assert "llm_service" in auth_hard_deps, "LLM service should have hard dependency on auth"
        
        # Validate database_service dependency mapping
        db_results = dependency_test_results["database_service"]
        db_hard_deps = [svc["service"] for svc in db_results["hard_dependencies"]]
        db_soft_deps = [svc["service"] for svc in db_results["soft_dependencies"]]
        assert "search_service" in db_hard_deps, "Search service should have hard dependency on database"
        assert "notification_service" in db_soft_deps, "Notification service should have soft dependency on database"
        
        # Validate cache_service dependency mapping
        cache_results = dependency_test_results["cache_service"]
        cache_soft_deps = [svc["service"] for svc in cache_results["soft_dependencies"]]
        cache_optional_deps = [svc["service"] for svc in cache_results["optional_dependencies"]]
        assert "llm_service" in cache_soft_deps, "LLM service should have soft dependency on cache"
        assert "search_service" in cache_optional_deps, "Search service should have optional dependency on cache"
        
        # Test dependency chain analysis
        # If database fails, it should affect both search and notification services
        db_chain_affected = [svc["service"] for svc in db_results["affected_services"]]
        expected_db_affected = {"search_service", "notification_service"}
        actual_db_affected = set(db_chain_affected)
        assert expected_db_affected.issubset(actual_db_affected), f"Database dependency chain incomplete: expected {expected_db_affected}, got {actual_db_affected}"
        
        # Store dependency analysis results
        await postgres.execute("""
            INSERT INTO service_failure_events (failure_id, service_name, failure_type, affected_services, coordination_result)
            VALUES ('dependency_mapping_test', 'dependency_analysis', 'mapping_validation', $1, $2)
        """, json.dumps(dependency_test_results), json.dumps({
            "test_type": "dependency_mapping_accuracy",
            "services_tested": list(dependency_test_results.keys()),
            "total_dependencies_validated": sum(len(result["affected_services"]) for result in dependency_test_results.values())
        }))
        
        logger.info(" PASS:  Service dependency mapping accuracy test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_multi_service_failures(self, real_services_fixture, service_coordinator):
        """Test coordination during concurrent multi-service failures."""
        
        # Business Value: Concurrent failure handling prevents system overload and ensures coordinated response
        
        redis = real_services_fixture["redis"]
        
        # Create baseline health metrics
        initial_health = await service_coordinator.get_system_health_overview()
        
        # Simulate concurrent failures across different service tiers
        concurrent_failures = [
            ("auth_service", "authentication_overload"),
            ("cache_service", "memory_exhaustion"),  
            ("notification_service", "message_queue_failure")
        ]
        
        # Execute failures concurrently
        failure_tasks = [
            service_coordinator.simulate_service_failure(service, failure_type)
            for service, failure_type in concurrent_failures
        ]
        
        failure_results = await asyncio.gather(*failure_tasks, return_exceptions=True)
        
        # Validate all failures were processed
        successful_failures = [result for result in failure_results if not isinstance(result, Exception)]
        assert len(successful_failures) == 3, "Not all concurrent failures processed successfully"
        
        # Analyze cumulative impact
        all_affected_services = set()
        total_coordination_actions = 0
        
        for failure_result in successful_failures:
            if isinstance(failure_result, dict):
                affected = failure_result.get("affected_services", [])
                all_affected_services.update(svc["service"] for svc in affected)
                
                coordination = failure_result.get("coordination_result", {})
                total_coordination_actions += len(coordination.get("recovery_actions", []))
        
        # Verify coordination effectiveness
        post_failure_health = await service_coordinator.get_system_health_overview()
        
        # System should still have some operational capacity
        assert post_failure_health["health_ratios"]["availability_ratio"] >= 0.3, "System completely unavailable after concurrent failures"
        
        # Coordination should have been triggered
        assert total_coordination_actions >= 3, "Insufficient coordination actions for concurrent failures"
        
        # Store concurrent failure analysis in Redis
        concurrent_analysis = {
            "initial_health": initial_health,
            "post_failure_health": post_failure_health,
            "failures_processed": len(successful_failures),
            "total_affected_services": len(all_affected_services),
            "coordination_actions": total_coordination_actions,
            "availability_maintained": post_failure_health["health_ratios"]["availability_ratio"],
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await redis.set_json("concurrent_failure_analysis", concurrent_analysis, ex=600)
        
        # Test recovery coordination under stress
        # Attempt to recover one service while others are still failed
        recovery_under_stress = await service_coordinator.simulate_service_recovery("cache_service")
        
        # Verify recovery was successful despite other failures
        assert recovery_under_stress["recovered_service"] == "cache_service"
        
        # Check if partial recovery improved system health
        partial_recovery_health = await service_coordinator.get_system_health_overview()
        availability_improved = (partial_recovery_health["health_ratios"]["availability_ratio"] > 
                               post_failure_health["health_ratios"]["availability_ratio"])
        assert availability_improved, "Partial recovery did not improve system availability"
        
        # Test system resilience by attempting additional operations
        resilience_test_operations = []
        
        for i in range(3):
            try:
                # Simulate attempting to use recovered cache service
                await redis.set_json(f"resilience_test_{i}", {
                    "operation_id": i,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cache_service_available": True
                }, ex=60)
                resilience_test_operations.append({"operation": i, "success": True})
            except Exception as e:
                resilience_test_operations.append({"operation": i, "success": False, "error": str(e)})
        
        successful_operations = sum(1 for op in resilience_test_operations if op["success"])
        assert successful_operations >= 2, "System not resilient enough for basic operations"
        
        logger.info(" PASS:  Concurrent multi-service failures test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_business_continuity_impact_assessment(self, real_services_fixture, service_coordinator):
        """Test business continuity impact assessment during service failures."""
        
        # Business Value: Impact assessment enables informed business decisions during outages
        
        postgres = real_services_fixture["postgres"]
        
        # Define business criticality for each service
        service_business_criticality = {
            "auth_service": {"criticality": "critical", "business_functions": ["user_authentication", "security"]},
            "database_service": {"criticality": "critical", "business_functions": ["data_persistence", "user_state"]},
            "llm_service": {"criticality": "high", "business_functions": ["ai_interactions", "content_generation"]},
            "search_service": {"criticality": "medium", "business_functions": ["information_retrieval", "discovery"]},
            "cache_service": {"criticality": "medium", "business_functions": ["performance_optimization", "response_time"]},
            "notification_service": {"criticality": "low", "business_functions": ["user_alerts", "communication"]}
        }
        
        # Store business criticality mapping
        for service, criticality_info in service_business_criticality.items():
            await postgres.execute("""
                INSERT INTO service_failure_events (failure_id, service_name, failure_type, coordination_result)
                VALUES ($1, $2, 'business_criticality_mapping', $3)
            """, f"criticality_{service}", service, json.dumps(criticality_info))
        
        # Test impact assessment for different failure scenarios
        business_impact_scenarios = [
            {
                "name": "critical_auth_failure",
                "failed_services": ["auth_service"],
                "expected_impact": "severe"
            },
            {
                "name": "performance_cache_failure", 
                "failed_services": ["cache_service"],
                "expected_impact": "moderate"
            },
            {
                "name": "multi_tier_failure",
                "failed_services": ["database_service", "llm_service"],
                "expected_impact": "critical"
            }
        ]
        
        impact_assessment_results = {}
        
        for scenario in business_impact_scenarios:
            # Reset system to healthy state
            for svc_name in service_coordinator.services:
                service_coordinator.services[svc_name]["state"] = ServiceState.HEALTHY
                service_coordinator.health_metrics[svc_name].state = ServiceState.HEALTHY
            
            # Execute failure scenario
            scenario_failures = []
            for failed_service in scenario["failed_services"]:
                failure_result = await service_coordinator.simulate_service_failure(
                    failed_service, f"business_impact_test_{scenario['name']}"
                )
                scenario_failures.append(failure_result)
            
            # Assess business impact
            system_health = await service_coordinator.get_system_health_overview()
            
            # Calculate business impact score
            affected_critical_services = 0
            affected_high_services = 0
            affected_medium_services = 0
            affected_low_services = 0
            
            for svc_name, svc_info in service_coordinator.services.items():
                if svc_info["state"] != ServiceState.HEALTHY:
                    criticality = service_business_criticality[svc_name]["criticality"]
                    if criticality == "critical":
                        affected_critical_services += 1
                    elif criticality == "high":
                        affected_high_services += 1
                    elif criticality == "medium":
                        affected_medium_services += 1
                    else:
                        affected_low_services += 1
            
            # Business impact calculation
            business_impact_score = (
                affected_critical_services * 1.0 +
                affected_high_services * 0.7 +
                affected_medium_services * 0.4 +
                affected_low_services * 0.1
            ) / len(service_business_criticality)
            
            # Determine impact level
            if business_impact_score >= 0.8:
                impact_level = "critical"
            elif business_impact_score >= 0.5:
                impact_level = "severe"
            elif business_impact_score >= 0.2:
                impact_level = "moderate"
            else:
                impact_level = "minimal"
            
            # Identify affected business functions
            affected_business_functions = set()
            for svc_name, svc_info in service_coordinator.services.items():
                if svc_info["state"] != ServiceState.HEALTHY:
                    functions = service_business_criticality[svc_name]["business_functions"]
                    affected_business_functions.update(functions)
            
            impact_assessment_results[scenario["name"]] = {
                "scenario": scenario,
                "business_impact_score": business_impact_score,
                "impact_level": impact_level,
                "affected_critical_services": affected_critical_services,
                "affected_high_services": affected_high_services,
                "affected_medium_services": affected_medium_services,
                "affected_low_services": affected_low_services,
                "affected_business_functions": list(affected_business_functions),
                "system_availability": system_health["health_ratios"]["availability_ratio"],
                "business_continuity_feasible": business_impact_score < 0.7
            }
        
        # Validate impact assessment accuracy
        auth_impact = impact_assessment_results["critical_auth_failure"]
        assert auth_impact["impact_level"] in ["severe", "critical"], "Critical service failure not properly assessed"
        assert auth_impact["affected_critical_services"] >= 1, "Critical service count incorrect"
        assert "user_authentication" in auth_impact["affected_business_functions"], "Core business function not identified"
        
        cache_impact = impact_assessment_results["performance_cache_failure"]
        assert cache_impact["impact_level"] in ["minimal", "moderate"], "Medium criticality service impact overestimated"
        assert cache_impact["business_continuity_feasible"] is True, "Business continuity assessment too pessimistic"
        
        multi_tier_impact = impact_assessment_results["multi_tier_failure"]
        assert multi_tier_impact["impact_level"] == "critical", "Multi-tier failure not assessed as critical"
        assert multi_tier_impact["business_continuity_feasible"] is False, "Multi-tier failure should threaten business continuity"
        
        # Store comprehensive impact assessment
        await postgres.execute("""
            INSERT INTO service_failure_events (failure_id, service_name, failure_type, affected_services, coordination_result)
            VALUES ('business_impact_assessment', 'system_wide', 'impact_analysis', $1, $2)
        """, json.dumps({
            "service_criticalities": service_business_criticality,
            "scenario_results": impact_assessment_results
        }), json.dumps({
            "assessment_type": "business_continuity_impact",
            "scenarios_tested": len(business_impact_scenarios),
            "impact_calculation_method": "weighted_criticality_score"
        }))
        
        logger.info(" PASS:  Business continuity impact assessment test passed")


if __name__ == "__main__":
    # Run specific test for development  
    import pytest
    pytest.main([__file__, "-v", "-s"])