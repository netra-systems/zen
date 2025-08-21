"""L3 Integration Test: Agent Context Isolation Boundaries

Business Value Justification (BVJ):
- Segment: Enterprise (security and reliability)
- Business Goal: Ensure agent context isolation prevents data leakage
- Value Impact: Critical for multi-tenant security, protecting $100K MRR
- Strategic Impact: Essential for enterprise security compliance

L3 Test: Uses real local services to validate context isolation between agents.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import uuid
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
from testcontainers.redis import RedisContainer
from testcontainers.postgres import PostgresContainer

# Add project root to path

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.state_manager import AgentStateManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.services.database.postgres_service import PostgresService
from netra_backend.app.security.context_isolation import ContextIsolationManager
from test_framework.testcontainers_utils import TestcontainerHelper

# Add project root to path

logger = logging.getLogger(__name__)


class L3ContextIsolationManager:
    """Manages L3 context isolation testing with real infrastructure."""
    
    def __init__(self):
        self.redis_client = None
        self.postgres_service = None
        self.state_manager: Optional[AgentStateManager] = None
        self.isolation_manager: Optional[ContextIsolationManager] = None
        self.tenant_agents: Dict[str, List[BaseSubAgent]] = {}
        self.context_boundaries: Dict[str, Set[str]] = {}
        self.isolation_violations: List[Dict[str, Any]] = []
        self.isolation_metrics = {
            "tenants_tested": 0,
            "agents_per_tenant": 0,
            "context_checks_performed": 0,
            "isolation_violations": 0,
            "successful_isolations": 0
        }
        
    async def initialize_l3_infrastructure(self, redis_url: str, postgres_url: str):
        """Initialize L3 infrastructure with real containers."""
        # Initialize Redis connection
        self.redis_client = RedisManager()
        self.redis_client.redis_url = redis_url
        await self.redis_client.initialize()
        
        # Initialize Postgres connection
        self.postgres_service = PostgresService()
        self.postgres_service.database_url = postgres_url
        await self.postgres_service.initialize()
        
        # Initialize state manager
        self.state_manager = AgentStateManager(
            redis_client=self.redis_client,
            postgres_service=self.postgres_service
        )
        
        # Initialize context isolation manager
        self.isolation_manager = ContextIsolationManager(
            redis_client=self.redis_client,
            state_manager=self.state_manager
        )
        
    async def create_tenant_environment(self, tenant_id: str, agent_count: int = 3) -> Dict[str, Any]:
        """Create isolated tenant environment with multiple agents."""
        tenant_agents = []
        tenant_context = {
            "tenant_id": tenant_id,
            "sensitive_data": {
                "api_keys": [f"key_{tenant_id}_{i}" for i in range(3)],
                "customer_data": f"confidential_data_{tenant_id}",
                "business_metrics": {
                    "revenue": f"${(hash(tenant_id) % 1000000)}",
                    "user_count": hash(tenant_id) % 10000
                }
            },
            "permissions": [f"permission_{tenant_id}_{i}" for i in range(5)],
            "workspace_id": f"workspace_{tenant_id}",
            "created_at": time.time()
        }
        
        # Create agents for this tenant
        for i in range(agent_count):
            agent_id = f"agent_{tenant_id}_{i}_{uuid.uuid4().hex[:6]}"
            
            # Create agent with tenant-specific context
            agent = BaseSubAgent(
                agent_id=agent_id,
                agent_type=f"tenant_agent",
                state_manager=self.state_manager,
                redis_client=self.redis_client
            )
            
            # Initialize agent state with tenant context
            agent_state = DeepAgentState(
                agent_id=agent_id,
                agent_type="tenant_agent",
                status="active",
                tenant_id=tenant_id,
                context_data=tenant_context,
                isolation_boundary=tenant_id,
                created_at=time.time()
            )
            
            await self.state_manager.save_state(agent_id, agent_state)
            
            # Register agent with isolation manager
            await self.isolation_manager.register_agent(agent_id, tenant_id)
            
            tenant_agents.append(agent)
        
        self.tenant_agents[tenant_id] = tenant_agents
        self.context_boundaries[tenant_id] = {agent.agent_id for agent in tenant_agents}
        
        self.isolation_metrics["tenants_tested"] += 1
        self.isolation_metrics["agents_per_tenant"] = max(
            self.isolation_metrics["agents_per_tenant"], 
            agent_count
        )
        
        return {
            "tenant_id": tenant_id,
            "agent_count": len(tenant_agents),
            "agent_ids": [agent.agent_id for agent in tenant_agents],
            "context_hash": hashlib.sha256(json.dumps(tenant_context).encode()).hexdigest()[:16]
        }
    
    async def test_cross_tenant_isolation(self, tenant_a: str, tenant_b: str) -> Dict[str, Any]:
        """Test isolation between agents from different tenants."""
        isolation_start = time.time()
        
        try:
            # Get agents from both tenants
            agents_a = self.tenant_agents.get(tenant_a, [])
            agents_b = self.tenant_agents.get(tenant_b, [])
            
            if not agents_a or not agents_b:
                return {"success": False, "error": "Insufficient agents for cross-tenant test"}
            
            # Test context access violations
            violations = []
            
            # Test 1: Agent from tenant A trying to access tenant B context
            agent_a = agents_a[0]
            agent_b = agents_b[0]
            
            # Attempt unauthorized context access
            violation_attempt = await self._attempt_context_access(
                agent_a.agent_id, 
                tenant_b,
                "unauthorized_cross_tenant_access"
            )
            
            if violation_attempt["access_granted"]:
                violations.append({
                    "type": "cross_tenant_context_access",
                    "violating_agent": agent_a.agent_id,
                    "target_tenant": tenant_b,
                    "severity": "critical"
                })
            
            # Test 2: State isolation verification
            state_isolation_result = await self._verify_state_isolation(agent_a, agent_b)
            if not state_isolation_result["isolated"]:
                violations.append({
                    "type": "state_isolation_breach",
                    "agent_a": agent_a.agent_id,
                    "agent_b": agent_b.agent_id,
                    "severity": "high"
                })
            
            # Test 3: Redis key namespace isolation
            redis_isolation_result = await self._verify_redis_isolation(tenant_a, tenant_b)
            if not redis_isolation_result["isolated"]:
                violations.append({
                    "type": "redis_namespace_breach",
                    "tenant_a": tenant_a,
                    "tenant_b": tenant_b,
                    "severity": "high"
                })
            
            # Update metrics
            self.isolation_metrics["context_checks_performed"] += 3
            
            if violations:
                self.isolation_metrics["isolation_violations"] += len(violations)
                self.isolation_violations.extend(violations)
                
                return {
                    "success": False,
                    "isolation_breached": True,
                    "violations": violations,
                    "test_duration": time.time() - isolation_start
                }
            else:
                self.isolation_metrics["successful_isolations"] += 1
                
                return {
                    "success": True,
                    "isolation_maintained": True,
                    "checks_performed": 3,
                    "test_duration": time.time() - isolation_start
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_duration": time.time() - isolation_start
            }
    
    async def _attempt_context_access(self, agent_id: str, target_tenant: str, access_type: str) -> Dict[str, Any]:
        """Attempt unauthorized context access to test isolation."""
        try:
            # Try to access target tenant's context through isolation manager
            access_result = await self.isolation_manager.check_context_access(
                agent_id=agent_id,
                target_tenant=target_tenant,
                access_type=access_type
            )
            
            return {
                "access_granted": access_result.get("granted", False),
                "access_level": access_result.get("level", "none"),
                "reason": access_result.get("reason", "unknown")
            }
            
        except Exception as e:
            # Exception should occur for unauthorized access
            return {
                "access_granted": False,
                "access_level": "none",
                "reason": f"Access denied: {str(e)}"
            }
    
    async def _verify_state_isolation(self, agent_a: BaseSubAgent, agent_b: BaseSubAgent) -> Dict[str, Any]:
        """Verify state isolation between agents from different tenants."""
        try:
            # Load states
            state_a = await self.state_manager.load_state(agent_a.agent_id)
            state_b = await self.state_manager.load_state(agent_b.agent_id)
            
            # Check isolation boundaries
            isolation_checks = {
                "different_tenants": state_a.tenant_id != state_b.tenant_id,
                "different_isolation_boundaries": state_a.isolation_boundary != state_b.isolation_boundary,
                "no_shared_context": not self._has_shared_context_data(state_a, state_b),
                "separate_permissions": not self._has_shared_permissions(state_a, state_b)
            }
            
            all_isolated = all(isolation_checks.values())
            
            return {
                "isolated": all_isolated,
                "checks": isolation_checks,
                "tenant_a": state_a.tenant_id,
                "tenant_b": state_b.tenant_id
            }
            
        except Exception as e:
            return {
                "isolated": False,
                "error": str(e)
            }
    
    async def _verify_redis_isolation(self, tenant_a: str, tenant_b: str) -> Dict[str, Any]:
        """Verify Redis key namespace isolation between tenants."""
        try:
            # Check Redis key patterns for each tenant
            tenant_a_pattern = f"tenant:{tenant_a}:*"
            tenant_b_pattern = f"tenant:{tenant_b}:*"
            
            keys_a = await self.redis_client.keys(tenant_a_pattern)
            keys_b = await self.redis_client.keys(tenant_b_pattern)
            
            # Check for key overlaps (should be none)
            key_overlap = set(keys_a) & set(keys_b)
            
            # Verify namespace separation
            namespace_isolated = len(key_overlap) == 0
            
            # Test cross-tenant key access
            cross_access_blocked = await self._test_cross_tenant_redis_access(tenant_a, tenant_b)
            
            return {
                "isolated": namespace_isolated and cross_access_blocked,
                "namespace_separated": namespace_isolated,
                "cross_access_blocked": cross_access_blocked,
                "tenant_a_keys": len(keys_a),
                "tenant_b_keys": len(keys_b),
                "key_overlaps": len(key_overlap)
            }
            
        except Exception as e:
            return {
                "isolated": False,
                "error": str(e)
            }
    
    async def _test_cross_tenant_redis_access(self, tenant_a: str, tenant_b: str) -> bool:
        """Test if cross-tenant Redis access is properly blocked."""
        try:
            # Try to access tenant B's keys from tenant A context
            tenant_b_key = f"tenant:{tenant_b}:sensitive_data"
            
            # This should be blocked by isolation manager
            access_result = await self.isolation_manager.check_redis_access(
                requesting_tenant=tenant_a,
                target_key=tenant_b_key
            )
            
            return not access_result.get("granted", True)  # Should be denied
            
        except Exception:
            return True  # Exception means access is blocked (good)
    
    def _has_shared_context_data(self, state_a: DeepAgentState, state_b: DeepAgentState) -> bool:
        """Check if two agent states share context data."""
        if not (state_a.context_data and state_b.context_data):
            return False
            
        # Check for shared sensitive data
        sensitive_fields = ["api_keys", "customer_data", "business_metrics"]
        
        for field in sensitive_fields:
            data_a = state_a.context_data.get("sensitive_data", {}).get(field)
            data_b = state_b.context_data.get("sensitive_data", {}).get(field)
            
            if data_a and data_b and data_a == data_b:
                return True
                
        return False
    
    def _has_shared_permissions(self, state_a: DeepAgentState, state_b: DeepAgentState) -> bool:
        """Check if two agent states share permissions."""
        if not (state_a.context_data and state_b.context_data):
            return False
            
        permissions_a = set(state_a.context_data.get("permissions", []))
        permissions_b = set(state_b.context_data.get("permissions", []))
        
        return len(permissions_a & permissions_b) > 0
    
    async def test_intra_tenant_communication(self, tenant_id: str) -> Dict[str, Any]:
        """Test that agents within the same tenant can communicate properly."""
        try:
            agents = self.tenant_agents.get(tenant_id, [])
            if len(agents) < 2:
                return {"success": False, "error": "Insufficient agents for intra-tenant test"}
            
            agent_a, agent_b = agents[0], agents[1]
            
            # Test allowed communication within tenant
            communication_result = await self.isolation_manager.test_agent_communication(
                agent_a.agent_id,
                agent_b.agent_id,
                {"type": "intra_tenant_message", "content": "test communication"}
            )
            
            # Test shared context access within tenant
            shared_access_result = await self.isolation_manager.check_context_access(
                agent_id=agent_a.agent_id,
                target_tenant=tenant_id,
                access_type="intra_tenant_context_access"
            )
            
            return {
                "success": True,
                "communication_allowed": communication_result.get("allowed", False),
                "shared_access_granted": shared_access_result.get("granted", False),
                "tenant_id": tenant_id,
                "agents_tested": 2
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def generate_isolation_report(self) -> Dict[str, Any]:
        """Generate comprehensive isolation test report."""
        return {
            "test_summary": {
                "tenants_tested": self.isolation_metrics["tenants_tested"],
                "total_agents": sum(len(agents) for agents in self.tenant_agents.values()),
                "context_checks_performed": self.isolation_metrics["context_checks_performed"],
                "isolation_violations": self.isolation_metrics["isolation_violations"],
                "successful_isolations": self.isolation_metrics["successful_isolations"]
            },
            "violation_details": self.isolation_violations,
            "isolation_rate": (
                self.isolation_metrics["successful_isolations"] / 
                max(self.isolation_metrics["context_checks_performed"], 1)
            ),
            "tenant_boundaries": {
                tenant_id: list(agent_ids) 
                for tenant_id, agent_ids in self.context_boundaries.items()
            },
            "security_score": self._calculate_security_score()
        }
    
    def _calculate_security_score(self) -> float:
        """Calculate security score based on isolation test results."""
        total_checks = self.isolation_metrics["context_checks_performed"]
        violations = self.isolation_metrics["isolation_violations"]
        
        if total_checks == 0:
            return 0.0
            
        # Higher score is better (fewer violations)
        base_score = (total_checks - violations) / total_checks
        
        # Penalty for critical violations
        critical_violations = sum(
            1 for v in self.isolation_violations 
            if v.get("severity") == "critical"
        )
        
        penalty = critical_violations * 0.2
        
        return max(0.0, base_score - penalty)
    
    async def cleanup_l3_resources(self):
        """Clean up L3 test resources."""
        try:
            # Clean up all tenant agents
            for agents in self.tenant_agents.values():
                for agent in agents:
                    if hasattr(agent, 'cleanup'):
                        await agent.cleanup()
            
            # Close connections
            if self.redis_client:
                await self.redis_client.close()
            if self.postgres_service:
                await self.postgres_service.close()
                
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


@pytest.fixture
async def testcontainer_infrastructure():
    """Setup real Redis and Postgres containers for L3 testing."""
    helper = TestcontainerHelper()
    
    # Start Redis container
    redis_container_instance = RedisContainer("redis:7-alpine")
    redis_container_instance.start()
    redis_url = f"redis://localhost:{redis_container_instance.get_exposed_port(6379)}"
    
    # Start Postgres container
    postgres_container_instance = PostgresContainer("postgres:15-alpine")
    postgres_container_instance.start()
    postgres_url = postgres_container_instance.get_connection_url()
    
    yield redis_url, postgres_url
    
    # Cleanup containers
    redis_container_instance.stop()
    postgres_container_instance.stop()


@pytest.fixture
async def l3_isolation_manager(testcontainer_infrastructure):
    """Create L3 isolation manager with real infrastructure."""
    redis_url, postgres_url = testcontainer_infrastructure
    
    manager = L3ContextIsolationManager()
    await manager.initialize_l3_infrastructure(redis_url, postgres_url)
    
    yield manager
    
    await manager.cleanup_l3_resources()


@pytest.mark.L3
@pytest.mark.integration
class TestAgentContextIsolationBoundariesL3:
    """L3 integration tests for agent context isolation boundaries."""
    
    async def test_basic_tenant_isolation(self, l3_isolation_manager):
        """Test basic isolation between different tenant environments."""
        # Create two isolated tenant environments
        tenant_a = await l3_isolation_manager.create_tenant_environment("tenant_alpha", 2)
        tenant_b = await l3_isolation_manager.create_tenant_environment("tenant_beta", 2)
        
        # Verify environments created
        assert tenant_a["tenant_id"] == "tenant_alpha"
        assert tenant_b["tenant_id"] == "tenant_beta"
        assert tenant_a["agent_count"] == 2
        assert tenant_b["agent_count"] == 2
        assert tenant_a["context_hash"] != tenant_b["context_hash"]
        
        # Test cross-tenant isolation
        isolation_result = await l3_isolation_manager.test_cross_tenant_isolation(
            "tenant_alpha", "tenant_beta"
        )
        
        # Verify isolation maintained
        assert isolation_result["success"] is True
        assert isolation_result["isolation_maintained"] is True
        assert isolation_result["checks_performed"] == 3
        assert isolation_result["test_duration"] < 5.0
    
    async def test_multi_tenant_isolation_matrix(self, l3_isolation_manager):
        """Test isolation across multiple tenant combinations."""
        # Create three tenant environments
        tenants = []
        for i, tenant_name in enumerate(["enterprise_a", "enterprise_b", "startup_c"]):
            tenant = await l3_isolation_manager.create_tenant_environment(tenant_name, 2)
            tenants.append(tenant["tenant_id"])
        
        # Test all pairwise isolations
        isolation_results = []
        for i in range(len(tenants)):
            for j in range(i + 1, len(tenants)):
                result = await l3_isolation_manager.test_cross_tenant_isolation(
                    tenants[i], tenants[j]
                )
                isolation_results.append(result)
        
        # Verify all isolations successful
        successful_isolations = [r for r in isolation_results if r["success"]]
        assert len(successful_isolations) == 3  # 3 pairwise combinations
        
        # Verify no isolation breaches
        breached_isolations = [r for r in isolation_results if r.get("isolation_breached")]
        assert len(breached_isolations) == 0
        
        # Verify metrics
        assert l3_isolation_manager.isolation_metrics["tenants_tested"] == 3
        assert l3_isolation_manager.isolation_metrics["context_checks_performed"] >= 9
    
    async def test_intra_tenant_communication_allowed(self, l3_isolation_manager):
        """Test that agents within same tenant can communicate."""
        # Create tenant with multiple agents
        tenant = await l3_isolation_manager.create_tenant_environment("collaborative_tenant", 3)
        
        # Test intra-tenant communication
        communication_result = await l3_isolation_manager.test_intra_tenant_communication(
            "collaborative_tenant"
        )
        
        # Verify communication allowed within tenant
        assert communication_result["success"] is True
        assert communication_result["communication_allowed"] is True
        assert communication_result["shared_access_granted"] is True
        assert communication_result["tenant_id"] == "collaborative_tenant"
        assert communication_result["agents_tested"] == 2
    
    async def test_context_data_isolation_verification(self, l3_isolation_manager):
        """Test comprehensive context data isolation."""
        # Create tenants with different sensitive data
        tenant_financial = await l3_isolation_manager.create_tenant_environment("financial_corp", 2)
        tenant_healthcare = await l3_isolation_manager.create_tenant_environment("healthcare_inc", 2)
        
        # Test isolation with focus on sensitive data
        isolation_result = await l3_isolation_manager.test_cross_tenant_isolation(
            "financial_corp", "healthcare_inc"
        )
        
        assert isolation_result["success"] is True
        assert isolation_result["isolation_maintained"] is True
        
        # Verify no violations recorded
        assert len(l3_isolation_manager.isolation_violations) == 0
        
        # Generate detailed isolation report
        report = await l3_isolation_manager.generate_isolation_report()
        
        # Verify report shows strong isolation
        assert report["test_summary"]["isolation_violations"] == 0
        assert report["isolation_rate"] == 1.0  # Perfect isolation
        assert report["security_score"] >= 0.8  # High security score
        assert len(report["tenant_boundaries"]) == 2
    
    async def test_redis_namespace_isolation(self, l3_isolation_manager):
        """Test Redis key namespace isolation between tenants."""
        # Create two tenants
        tenant_a = await l3_isolation_manager.create_tenant_environment("redis_tenant_a", 1)
        tenant_b = await l3_isolation_manager.create_tenant_environment("redis_tenant_b", 1)
        
        # Store tenant-specific data in Redis
        await l3_isolation_manager.redis_client.set(
            "tenant:redis_tenant_a:sensitive", "tenant_a_data"
        )
        await l3_isolation_manager.redis_client.set(
            "tenant:redis_tenant_b:sensitive", "tenant_b_data"
        )
        
        # Test isolation
        isolation_result = await l3_isolation_manager.test_cross_tenant_isolation(
            "redis_tenant_a", "redis_tenant_b"
        )
        
        # Verify Redis isolation maintained
        assert isolation_result["success"] is True
        assert isolation_result["isolation_maintained"] is True
        
        # Verify no cross-tenant Redis access violations
        redis_violations = [
            v for v in l3_isolation_manager.isolation_violations 
            if v.get("type") == "redis_namespace_breach"
        ]
        assert len(redis_violations) == 0
    
    async def test_isolation_under_concurrent_load(self, l3_isolation_manager):
        """Test isolation boundaries under concurrent multi-tenant load."""
        # Create multiple tenants concurrently
        tenant_creation_tasks = [
            l3_isolation_manager.create_tenant_environment(f"concurrent_tenant_{i}", 2)
            for i in range(4)
        ]
        
        tenants = await asyncio.gather(*tenant_creation_tasks)
        tenant_ids = [t["tenant_id"] for t in tenants]
        
        # Execute concurrent isolation tests
        isolation_tasks = []
        for i in range(0, len(tenant_ids), 2):
            if i + 1 < len(tenant_ids):
                task = l3_isolation_manager.test_cross_tenant_isolation(
                    tenant_ids[i], tenant_ids[i + 1]
                )
                isolation_tasks.append(task)
        
        isolation_results = await asyncio.gather(*isolation_tasks)
        
        # Verify all concurrent isolations successful
        successful_results = [r for r in isolation_results if r["success"]]
        assert len(successful_results) == len(isolation_results)
        
        # Verify performance under load
        max_test_duration = max(r["test_duration"] for r in isolation_results)
        assert max_test_duration < 10.0  # Reasonable performance under concurrent load
        
        # Generate final report
        final_report = await l3_isolation_manager.generate_isolation_report()
        
        # Verify comprehensive testing
        assert final_report["test_summary"]["tenants_tested"] == 4
        assert final_report["test_summary"]["context_checks_performed"] >= 6
        assert final_report["security_score"] >= 0.9  # High security under load