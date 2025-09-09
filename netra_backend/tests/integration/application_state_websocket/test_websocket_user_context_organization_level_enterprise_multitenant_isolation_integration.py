"""
Test WebSocket Organization-Level Isolation for Enterprise Multi-Tenant Scenarios Integration (#28)

Business Value Justification (BVJ):
- Segment: Enterprise (Critical for B2B SaaS multi-tenant security)
- Business Goal: Ensure perfect organization-level isolation in enterprise multi-tenant deployments
- Value Impact: Enterprise customers trust their organization data is completely isolated from other tenants
- Strategic Impact: Foundation of enterprise B2B sales - enables $100K+ contracts with security guarantees

CRITICAL ENTERPRISE REQUIREMENT: Organization-level isolation must be absolute in enterprise
multi-tenant scenarios. No data, events, users, or context should EVER cross organization
boundaries. Any organization-level isolation breach is a critical security violation that
could result in contract termination and legal liability.
"""

import asyncio
import pytest
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState, MessageType
from shared.isolated_environment import get_env

# Type definitions
UserID = str
OrganizationID = str
TenantID = str
DataNamespaceID = str


class OrganizationTier(Enum):
    """Organization subscription tiers with different isolation requirements."""
    STARTUP = "startup"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    ENTERPRISE_PLUS = "enterprise_plus"


class IsolationLevel(Enum):
    """Levels of isolation enforcement."""
    BASIC = "basic"  # Basic namespace separation
    STANDARD = "standard"  # Enhanced isolation with audit trails
    STRICT = "strict"  # Maximum isolation with encrypted separation
    ULTRA_STRICT = "ultra_strict"  # Government/finance grade isolation


@dataclass
class OrganizationTenantContext:
    """Complete organization tenant context for isolation testing."""
    organization_id: OrganizationID
    tenant_id: TenantID
    organization_name: str
    tier: OrganizationTier
    isolation_level: IsolationLevel
    users: Set[UserID] = field(default_factory=set)
    data_namespaces: Set[DataNamespaceID] = field(default_factory=set)
    websocket_connections: Set[str] = field(default_factory=set)
    thread_ids: Set[str] = field(default_factory=set)
    message_ids: Set[str] = field(default_factory=set)
    allowed_integrations: Set[str] = field(default_factory=set)
    security_constraints: Dict[str, Any] = field(default_factory=dict)
    data_residency_region: str = "us-east-1"
    encryption_key_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "tenant_id": self.tenant_id,
            "organization_name": self.organization_name,
            "tier": self.tier.value,
            "isolation_level": self.isolation_level.value,
            "users": list(self.users),
            "data_namespaces": list(self.data_namespaces),
            "websocket_connections": list(self.websocket_connections),
            "thread_ids": list(self.thread_ids),
            "message_ids": list(self.message_ids),
            "allowed_integrations": list(self.allowed_integrations),
            "security_constraints": self.security_constraints,
            "data_residency_region": self.data_residency_region,
            "encryption_key_id": self.encryption_key_id,
            "created_at": self.created_at
        }


@dataclass
class OrganizationIsolationViolation:
    """Represents a detected organization isolation violation."""
    violation_id: str
    violation_type: str
    source_organization: OrganizationID
    target_organization: OrganizationID
    affected_resource_type: str
    affected_resource_id: str
    severity: str  # low, medium, high, critical
    details: Dict[str, Any]
    detected_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "violation_type": self.violation_type,
            "source_organization": self.source_organization,
            "target_organization": self.target_organization,
            "affected_resource_type": self.affected_resource_type,
            "affected_resource_id": self.affected_resource_id,
            "severity": self.severity,
            "details": self.details,
            "detected_at": self.detected_at
        }


class EnterpriseMultiTenantIsolationValidator:
    """Validates organization-level isolation in enterprise multi-tenant scenarios."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.redis_client = None
        self.organization_contexts = {}  # org_id -> OrganizationTenantContext
        self.isolation_violations = []
        self.cross_tenant_access_attempts = []
        self.data_access_matrix = defaultdict(list)  # org_id -> [accessed_resources]
        self.websocket_event_routing = defaultdict(list)  # org_id -> [routed_events]
    
    async def setup(self):
        """Set up validator with Redis connection."""
        import redis.asyncio as redis
        self.redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        await self.redis_client.ping()
    
    async def cleanup(self):
        """Clean up validator resources."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def create_organization_tenant(self, org_suffix: str, tier: OrganizationTier,
                                       isolation_level: IsolationLevel = IsolationLevel.STANDARD,
                                       user_count: int = 3) -> OrganizationTenantContext:
        """Create complete organization tenant with users and isolated resources."""
        organization_id = f"enterprise-org-{org_suffix}"
        tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
        
        # Create organization in database
        await self.real_services["db"].execute("""
            INSERT INTO backend.organizations (id, name, slug, plan, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                plan = EXCLUDED.plan,
                updated_at = NOW()
        """, organization_id, f"Enterprise Org {org_suffix}", 
            f"enterprise-org-{org_suffix}", tier.value)
        
        # Create organization tenant context
        tenant_context = OrganizationTenantContext(
            organization_id=organization_id,
            tenant_id=tenant_id,
            organization_name=f"Enterprise Org {org_suffix}",
            tier=tier,
            isolation_level=isolation_level,
            security_constraints={
                "data_encryption_required": isolation_level in [IsolationLevel.STRICT, IsolationLevel.ULTRA_STRICT],
                "audit_all_access": True,
                "cross_tenant_access_denied": True,
                "websocket_namespace_isolated": True,
                "database_schema_isolated": True,
                "cache_namespace_isolated": True
            },
            data_residency_region="us-east-1",
            encryption_key_id=f"enc-key-{tenant_id}" if isolation_level == IsolationLevel.ULTRA_STRICT else None
        )
        
        # Create users for this organization
        for i in range(user_count):
            user_id = f"enterprise-user-{org_suffix}-{i}"
            
            # Create user in database
            await self.real_services["db"].execute("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (id) DO UPDATE SET 
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
            """, user_id, f"{user_id}@{org_suffix}-enterprise.com", 
                f"Enterprise User {i} from {org_suffix}", True)
            
            # Create organization membership
            await self.real_services["db"].execute("""
                INSERT INTO backend.organization_memberships (user_id, organization_id, role, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id, organization_id) DO UPDATE SET role = EXCLUDED.role
            """, user_id, organization_id, "member")
            
            tenant_context.users.add(user_id)
            
            # Create isolated threads for each user
            for j in range(2):
                thread_id = f"thread-{org_suffix}-{user_id}-{j}"
                await self.real_services["db"].execute("""
                    INSERT INTO backend.threads (id, user_id, title, created_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (id) DO UPDATE SET 
                        title = EXCLUDED.title,
                        updated_at = NOW()
                """, thread_id, user_id, f"Enterprise Thread {j} for {org_suffix}")
                tenant_context.thread_ids.add(thread_id)
                
                # Create messages in threads
                for k in range(2):
                    message_id = f"msg-{org_suffix}-{user_id}-{j}-{k}"
                    await self.real_services["db"].execute("""
                        INSERT INTO backend.messages (id, thread_id, user_id, content, role, created_at)
                        VALUES ($1, $2, $3, $4, $5, NOW())
                        ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content
                    """, message_id, thread_id, user_id, 
                        f"Enterprise message {k} from {org_suffix} organization", "user")
                    tenant_context.message_ids.add(message_id)
        
        # Create data namespaces for organization
        namespace_types = ["user_data", "org_settings", "analytics", "exports"]
        for namespace_type in namespace_types:
            namespace_id = f"{namespace_type}:{organization_id}"
            tenant_context.data_namespaces.add(namespace_id)
        
        # Store organization tenant context in Redis with isolation
        tenant_key = f"tenant_context:{tenant_id}"
        await self.redis_client.set(
            tenant_key,
            json.dumps(tenant_context.to_dict()),
            ex=3600
        )
        
        # Store organization isolation metadata
        org_isolation_key = f"org_isolation:{organization_id}"
        await self.redis_client.set(
            org_isolation_key,
            json.dumps({
                "organization_id": organization_id,
                "tenant_id": tenant_id,
                "isolation_level": isolation_level.value,
                "tier": tier.value,
                "data_namespaces": list(tenant_context.data_namespaces),
                "security_constraints": tenant_context.security_constraints,
                "created_at": time.time()
            }),
            ex=3600
        )
        
        self.organization_contexts[organization_id] = tenant_context
        return tenant_context
    
    async def simulate_multi_tenant_websocket_operations(self, 
                                                        operations_per_org: int = 5) -> Dict[str, Any]:
        """Simulate multi-tenant WebSocket operations and validate isolation."""
        operation_results = {
            "total_organizations": len(self.organization_contexts),
            "operations_per_organization": operations_per_org,
            "total_operations": 0,
            "successful_operations": 0,
            "isolation_violations": 0,
            "organization_summaries": {},
            "cross_tenant_attempts": []
        }
        
        # Execute operations for each organization tenant
        for org_id, tenant_context in self.organization_contexts.items():
            org_operations = await self._execute_organization_websocket_operations(
                tenant_context, operations_per_org
            )
            
            operation_results["organization_summaries"][org_id] = org_operations
            operation_results["total_operations"] += org_operations["operations_executed"]
            operation_results["successful_operations"] += org_operations["successful_operations"]
            operation_results["isolation_violations"] += len(org_operations["isolation_violations"])
        
        # Validate cross-tenant isolation
        cross_tenant_validation = await self._validate_cross_tenant_isolation()
        operation_results["cross_tenant_attempts"] = cross_tenant_validation["cross_tenant_attempts"]
        operation_results["isolation_violations"] += len(cross_tenant_validation["violations"])
        
        return operation_results
    
    async def _execute_organization_websocket_operations(self, 
                                                        tenant_context: OrganizationTenantContext,
                                                        operation_count: int) -> Dict[str, Any]:
        """Execute WebSocket operations for a specific organization tenant."""
        org_operations = {
            "organization_id": tenant_context.organization_id,
            "operations_executed": 0,
            "successful_operations": 0,
            "isolation_violations": [],
            "websocket_connections_created": 0,
            "messages_sent": 0,
            "data_accessed": []
        }
        
        # Create WebSocket connections for organization users
        for user_id in list(tenant_context.users)[:2]:  # Use first 2 users
            connection_id = f"ws-{tenant_context.tenant_id}-{user_id}-{uuid.uuid4().hex[:8]}"
            tenant_context.websocket_connections.add(connection_id)
            
            # Store WebSocket connection with organization isolation
            ws_connection_data = {
                "connection_id": connection_id,
                "user_id": user_id,
                "organization_id": tenant_context.organization_id,
                "tenant_id": tenant_context.tenant_id,
                "isolation_namespace": f"ws:{tenant_context.organization_id}",
                "allowed_data_namespaces": list(tenant_context.data_namespaces),
                "security_constraints": tenant_context.security_constraints,
                "connected_at": time.time()
            }
            
            await self.redis_client.set(
                f"ws_connection:{connection_id}",
                json.dumps(ws_connection_data),
                ex=3600
            )
            
            org_operations["websocket_connections_created"] += 1
        
        # Execute various operations for each connection
        for i, connection_id in enumerate(list(tenant_context.websocket_connections)[:operation_count]):
            try:
                # Operation 1: Send organization-scoped message
                await self._execute_organization_scoped_message(tenant_context, connection_id)
                org_operations["messages_sent"] += 1
                org_operations["successful_operations"] += 1
                
                # Operation 2: Access organization data
                data_access_result = await self._execute_organization_data_access(tenant_context, connection_id)
                org_operations["data_accessed"].extend(data_access_result["accessed_namespaces"])
                if data_access_result["access_granted"]:
                    org_operations["successful_operations"] += 1
                
                # Operation 3: Attempt cross-organization operation (should be blocked)
                cross_org_attempt = await self._attempt_cross_organization_access(tenant_context, connection_id)
                if not cross_org_attempt["blocked"]:
                    # This is a violation - cross-org access should be blocked
                    violation = OrganizationIsolationViolation(
                        violation_id=f"cross-org-{uuid.uuid4().hex[:8]}",
                        violation_type="unauthorized_cross_organization_access",
                        source_organization=tenant_context.organization_id,
                        target_organization=cross_org_attempt["target_organization"],
                        affected_resource_type="websocket_connection",
                        affected_resource_id=connection_id,
                        severity="critical",
                        details=cross_org_attempt
                    )
                    org_operations["isolation_violations"].append(violation.to_dict())
                    self.isolation_violations.append(violation)
                
                org_operations["operations_executed"] += 1
                
            except Exception as e:
                # Log operation failure
                org_operations["isolation_violations"].append({
                    "type": "operation_failure",
                    "connection_id": connection_id,
                    "error": str(e),
                    "timestamp": time.time()
                })
        
        return org_operations
    
    async def _execute_organization_scoped_message(self, tenant_context: OrganizationTenantContext, 
                                                  connection_id: str):
        """Execute a message operation scoped to organization."""
        user_id = list(tenant_context.users)[0]  # Get first user
        thread_id = list(tenant_context.thread_ids)[0]  # Get first thread
        
        message_data = {
            "type": MessageType.USER_MESSAGE.value,
            "connection_id": connection_id,
            "user_id": user_id,
            "organization_id": tenant_context.organization_id,
            "thread_id": thread_id,
            "content": f"Organization-scoped message from {tenant_context.organization_name}",
            "isolation_namespace": f"msg:{tenant_context.organization_id}",
            "tenant_id": tenant_context.tenant_id,
            "timestamp": time.time()
        }
        
        # Store message with organization isolation
        message_key = f"org_message:{tenant_context.organization_id}:{connection_id}:{int(time.time())}"
        await self.redis_client.set(message_key, json.dumps(message_data), ex=600)
        
        # Track event routing for this organization
        self.websocket_event_routing[tenant_context.organization_id].append({
            "event_type": "organization_message",
            "connection_id": connection_id,
            "namespace": f"msg:{tenant_context.organization_id}",
            "timestamp": time.time()
        })
    
    async def _execute_organization_data_access(self, tenant_context: OrganizationTenantContext, 
                                               connection_id: str) -> Dict[str, Any]:
        """Execute organization data access with isolation validation."""
        access_result = {
            "access_granted": True,
            "accessed_namespaces": [],
            "denied_namespaces": [],
            "isolation_validated": True
        }
        
        # Attempt to access organization's own data namespaces
        for namespace in list(tenant_context.data_namespaces)[:2]:  # Access first 2 namespaces
            # This should succeed - organization accessing its own data
            data_key = f"namespace_data:{namespace}"
            namespace_data = {
                "namespace_id": namespace,
                "organization_id": tenant_context.organization_id,
                "data_type": namespace.split(":")[0],
                "accessed_by_connection": connection_id,
                "access_time": time.time(),
                "tenant_id": tenant_context.tenant_id
            }
            
            await self.redis_client.set(data_key, json.dumps(namespace_data), ex=300)
            access_result["accessed_namespaces"].append(namespace)
            
            # Track data access
            self.data_access_matrix[tenant_context.organization_id].append({
                "namespace": namespace,
                "connection_id": connection_id,
                "access_type": "read",
                "timestamp": time.time()
            })
        
        return access_result
    
    async def _attempt_cross_organization_access(self, tenant_context: OrganizationTenantContext,
                                                connection_id: str) -> Dict[str, Any]:
        """Attempt cross-organization access (should be blocked)."""
        cross_access_attempt = {
            "source_organization": tenant_context.organization_id,
            "target_organization": None,
            "attempt_type": "cross_organization_data_access",
            "blocked": True,  # Should be blocked
            "attempt_timestamp": time.time()
        }
        
        # Try to access another organization's data (if any other orgs exist)
        other_orgs = [org_id for org_id in self.organization_contexts.keys() 
                     if org_id != tenant_context.organization_id]
        
        if other_orgs:
            target_org_id = other_orgs[0]
            target_tenant = self.organization_contexts[target_org_id]
            cross_access_attempt["target_organization"] = target_org_id
            
            # Attempt to access target organization's data namespace
            target_namespace = list(target_tenant.data_namespaces)[0]
            
            # This access attempt should be blocked by isolation mechanisms
            try:
                # Simulate access attempt
                unauthorized_key = f"unauthorized_access:{connection_id}:{target_namespace}"
                await self.redis_client.set(unauthorized_key, json.dumps({
                    "attempt": "cross_organization_access",
                    "source_org": tenant_context.organization_id,
                    "target_namespace": target_namespace,
                    "should_be_blocked": True
                }), ex=60)
                
                # If we reach here, the access was NOT blocked (violation)
                cross_access_attempt["blocked"] = False
                
                # Log this attempt for analysis
                self.cross_tenant_access_attempts.append(cross_access_attempt)
                
            except Exception:
                # Access was blocked (good!)
                cross_access_attempt["blocked"] = True
        
        return cross_access_attempt
    
    async def _validate_cross_tenant_isolation(self) -> Dict[str, Any]:
        """Validate isolation between different organization tenants."""
        validation_result = {
            "isolation_maintained": True,
            "violations": [],
            "cross_tenant_attempts": len(self.cross_tenant_access_attempts),
            "organization_boundaries_intact": True
        }
        
        # Check for any cross-tenant data access
        for org_id, access_records in self.data_access_matrix.items():
            org_context = self.organization_contexts[org_id]
            
            for access_record in access_records:
                accessed_namespace = access_record["namespace"]
                
                # Verify accessed namespace belongs to this organization
                if accessed_namespace not in org_context.data_namespaces:
                    violation = OrganizationIsolationViolation(
                        violation_id=f"data-access-{uuid.uuid4().hex[:8]}",
                        violation_type="unauthorized_namespace_access",
                        source_organization=org_id,
                        target_organization="unknown",
                        affected_resource_type="data_namespace",
                        affected_resource_id=accessed_namespace,
                        severity="critical",
                        details={
                            "access_record": access_record,
                            "organization_namespaces": list(org_context.data_namespaces)
                        }
                    )
                    validation_result["violations"].append(violation.to_dict())
                    validation_result["isolation_maintained"] = False
        
        # Check for cross-organization WebSocket event routing
        for org_id, event_records in self.websocket_event_routing.items():
            for event_record in event_records:
                expected_namespace = f"msg:{org_id}"
                actual_namespace = event_record.get("namespace")
                
                if actual_namespace != expected_namespace:
                    violation = OrganizationIsolationViolation(
                        violation_id=f"routing-{uuid.uuid4().hex[:8]}",
                        violation_type="incorrect_event_routing_namespace",
                        source_organization=org_id,
                        target_organization="namespace_mismatch",
                        affected_resource_type="websocket_event",
                        affected_resource_id=event_record.get("connection_id", "unknown"),
                        severity="high",
                        details={
                            "expected_namespace": expected_namespace,
                            "actual_namespace": actual_namespace,
                            "event_record": event_record
                        }
                    )
                    validation_result["violations"].append(violation.to_dict())
                    validation_result["isolation_maintained"] = False
        
        # Check for successful cross-tenant access attempts (should be zero)
        successful_cross_access = [attempt for attempt in self.cross_tenant_access_attempts 
                                 if not attempt.get("blocked", True)]
        
        if successful_cross_access:
            for attempt in successful_cross_access:
                violation = OrganizationIsolationViolation(
                    violation_id=f"cross-access-{uuid.uuid4().hex[:8]}",
                    violation_type="successful_cross_tenant_access",
                    source_organization=attempt["source_organization"],
                    target_organization=attempt["target_organization"],
                    affected_resource_type="cross_tenant_data",
                    affected_resource_id="multiple",
                    severity="critical",
                    details=attempt
                )
                validation_result["violations"].append(violation.to_dict())
                validation_result["isolation_maintained"] = False
                validation_result["organization_boundaries_intact"] = False
        
        return validation_result
    
    async def generate_enterprise_isolation_report(self) -> Dict[str, Any]:
        """Generate comprehensive enterprise isolation compliance report."""
        report = {
            "report_timestamp": time.time(),
            "total_organizations": len(self.organization_contexts),
            "total_violations": len(self.isolation_violations),
            "isolation_compliance_score": 0.0,
            "organization_summaries": {},
            "violation_breakdown": defaultdict(int),
            "recommendations": []
        }
        
        # Analyze each organization
        for org_id, tenant_context in self.organization_contexts.items():
            org_violations = [v for v in self.isolation_violations 
                            if v.source_organization == org_id or v.target_organization == org_id]
            
            org_summary = {
                "organization_id": org_id,
                "tenant_id": tenant_context.tenant_id,
                "tier": tenant_context.tier.value,
                "isolation_level": tenant_context.isolation_level.value,
                "user_count": len(tenant_context.users),
                "websocket_connections": len(tenant_context.websocket_connections),
                "data_namespaces": len(tenant_context.data_namespaces),
                "violations_count": len(org_violations),
                "compliance_status": "compliant" if len(org_violations) == 0 else "violations_detected"
            }
            
            report["organization_summaries"][org_id] = org_summary
        
        # Calculate compliance score
        if len(self.organization_contexts) > 0:
            orgs_without_violations = sum(1 for summary in report["organization_summaries"].values() 
                                        if summary["violations_count"] == 0)
            report["isolation_compliance_score"] = orgs_without_violations / len(self.organization_contexts)
        
        # Violation breakdown
        for violation in self.isolation_violations:
            report["violation_breakdown"][violation.violation_type] += 1
        
        # Generate recommendations
        if report["total_violations"] > 0:
            report["recommendations"].extend([
                "Review organization isolation mechanisms",
                "Implement stricter namespace enforcement",
                "Audit cross-tenant access controls",
                "Consider upgrading to higher isolation tiers"
            ])
        else:
            report["recommendations"].append("Organization isolation is compliant")
        
        return report


class TestWebSocketOrganizationLevelEnterpriseIsolation(BaseIntegrationTest):
    """
    Integration test for organization-level isolation in enterprise multi-tenant scenarios.
    
    ENTERPRISE CRITICAL: Validates absolute organization isolation in multi-tenant deployments.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.enterprise_critical
    async def test_enterprise_multi_tenant_organization_isolation(self, real_services_fixture):
        """
        Test complete organization isolation in enterprise multi-tenant scenario.
        
        ENTERPRISE CRITICAL: Organizations must be completely isolated from each other.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = EnterpriseMultiTenantIsolationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create multiple enterprise organization tenants
            enterprise_tenants = []
            
            # Enterprise tier with standard isolation
            enterprise_alpha = await validator.create_organization_tenant(
                "alpha", OrganizationTier.ENTERPRISE, IsolationLevel.STANDARD, user_count=4
            )
            enterprise_tenants.append(enterprise_alpha)
            
            # Enterprise Plus tier with strict isolation
            enterprise_beta = await validator.create_organization_tenant(
                "beta", OrganizationTier.ENTERPRISE_PLUS, IsolationLevel.STRICT, user_count=3
            )
            enterprise_tenants.append(enterprise_beta)
            
            # Professional tier with basic isolation
            professional_gamma = await validator.create_organization_tenant(
                "gamma", OrganizationTier.PROFESSIONAL, IsolationLevel.BASIC, user_count=2
            )
            enterprise_tenants.append(professional_gamma)
            
            # Verify tenant contexts are properly isolated
            assert len(validator.organization_contexts) == 3
            
            # Verify no overlapping resources between organizations
            all_users = set()
            all_threads = set()
            all_namespaces = set()
            
            for tenant in enterprise_tenants:
                # Check for user overlap
                user_overlap = all_users.intersection(tenant.users)
                assert len(user_overlap) == 0, f"User overlap detected: {user_overlap}"
                all_users.update(tenant.users)
                
                # Check for thread overlap
                thread_overlap = all_threads.intersection(tenant.thread_ids)
                assert len(thread_overlap) == 0, f"Thread overlap detected: {thread_overlap}"
                all_threads.update(tenant.thread_ids)
                
                # Check for namespace overlap
                namespace_overlap = all_namespaces.intersection(tenant.data_namespaces)
                assert len(namespace_overlap) == 0, f"Namespace overlap detected: {namespace_overlap}"
                all_namespaces.update(tenant.data_namespaces)
            
            # Execute multi-tenant operations
            operations_result = await validator.simulate_multi_tenant_websocket_operations(operations_per_org=10)
            
            # ENTERPRISE CRITICAL VALIDATIONS
            
            # No isolation violations should occur
            assert operations_result["isolation_violations"] == 0, \
                f"Isolation violations detected: {operations_result['isolation_violations']}"
            
            # All operations should succeed within organization boundaries
            assert operations_result["successful_operations"] > 0, \
                "Some operations should succeed within organization boundaries"
            
            # Cross-tenant access attempts should all be blocked
            blocked_cross_tenant = sum(1 for attempt in operations_result["cross_tenant_attempts"] 
                                     if attempt.get("blocked", False))
            total_cross_tenant = len(operations_result["cross_tenant_attempts"])
            
            if total_cross_tenant > 0:
                assert blocked_cross_tenant == total_cross_tenant, \
                    f"Cross-tenant access not properly blocked: {blocked_cross_tenant}/{total_cross_tenant}"
            
            # Verify each organization operated independently
            for org_id, org_summary in operations_result["organization_summaries"].items():
                assert org_summary["successful_operations"] > 0, \
                    f"Organization {org_id} should have successful operations"
                assert len(org_summary["isolation_violations"]) == 0, \
                    f"Organization {org_id} has isolation violations"
            
            # Generate compliance report
            compliance_report = await validator.generate_enterprise_isolation_report()
            
            # Enterprise compliance requirements
            assert compliance_report["isolation_compliance_score"] == 1.0, \
                f"Enterprise isolation compliance must be 100%, got {compliance_report['isolation_compliance_score']}"
            assert compliance_report["total_violations"] == 0, \
                f"Enterprise deployment cannot have any violations: {compliance_report['total_violations']}"
            
            # Verify all organizations are compliant
            for org_id, org_summary in compliance_report["organization_summaries"].items():
                assert org_summary["compliance_status"] == "compliant", \
                    f"Organization {org_id} is not compliant: {org_summary}"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.ultra_strict_isolation
    async def test_ultra_strict_isolation_enterprise_scenario(self, real_services_fixture):
        """Test ultra-strict isolation for highly sensitive enterprise scenarios."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = EnterpriseMultiTenantIsolationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create ultra-strict isolation tenants (e.g., finance/healthcare)
            finance_org = await validator.create_organization_tenant(
                "finance", OrganizationTier.ENTERPRISE_PLUS, IsolationLevel.ULTRA_STRICT, user_count=2
            )
            
            healthcare_org = await validator.create_organization_tenant(
                "healthcare", OrganizationTier.ENTERPRISE_PLUS, IsolationLevel.ULTRA_STRICT, user_count=2
            )
            
            # Verify ultra-strict isolation features
            assert finance_org.encryption_key_id is not None, "Finance org must have encryption key"
            assert healthcare_org.encryption_key_id is not None, "Healthcare org must have encryption key"
            assert finance_org.encryption_key_id != healthcare_org.encryption_key_id, \
                "Organizations must have different encryption keys"
            
            # Execute operations with ultra-strict validation
            ultra_strict_operations = await validator.simulate_multi_tenant_websocket_operations(
                operations_per_org=5
            )
            
            # ULTRA-STRICT VALIDATIONS
            
            # Zero tolerance for any violations
            assert ultra_strict_operations["isolation_violations"] == 0, \
                "Ultra-strict isolation allows ZERO violations"
            
            # Cross-tenant attempts should be completely blocked
            assert len(ultra_strict_operations["cross_tenant_attempts"]) == 0 or \
                   all(attempt.get("blocked", False) for attempt in ultra_strict_operations["cross_tenant_attempts"]), \
                "Ultra-strict isolation must block all cross-tenant attempts"
            
            # Generate ultra-strict compliance report
            ultra_compliance = await validator.generate_enterprise_isolation_report()
            
            # Ultra-strict requirements
            assert ultra_compliance["isolation_compliance_score"] == 1.0, \
                "Ultra-strict compliance must be perfect"
            assert ultra_compliance["total_violations"] == 0, \
                "Ultra-strict isolation allows zero violations"
            
            # Verify encryption and security constraints
            for org_id, org_summary in ultra_compliance["organization_summaries"].items():
                tenant_context = validator.organization_contexts[org_id]
                assert tenant_context.security_constraints["data_encryption_required"], \
                    f"Ultra-strict org {org_id} must require encryption"
                assert tenant_context.security_constraints["audit_all_access"], \
                    f"Ultra-strict org {org_id} must audit all access"
                assert tenant_context.security_constraints["cross_tenant_access_denied"], \
                    f"Ultra-strict org {org_id} must deny cross-tenant access"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.concurrent_enterprise
    async def test_concurrent_multi_tenant_operations_isolation(self, real_services_fixture):
        """Test organization isolation under concurrent multi-tenant load."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = EnterpriseMultiTenantIsolationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create multiple concurrent enterprise tenants
            concurrent_tenants = []
            for i in range(4):  # 4 concurrent enterprise organizations
                tenant = await validator.create_organization_tenant(
                    f"concurrent-{i}", 
                    OrganizationTier.ENTERPRISE, 
                    IsolationLevel.STANDARD, 
                    user_count=3
                )
                concurrent_tenants.append(tenant)
            
            # Execute high-concurrency multi-tenant operations
            concurrent_tasks = []
            for i in range(4):  # Multiple concurrent operation batches
                task = validator.simulate_multi_tenant_websocket_operations(operations_per_org=8)
                concurrent_tasks.append(task)
            
            # Wait for all concurrent operations to complete
            concurrent_results = await asyncio.gather(*concurrent_tasks)
            
            # Validate isolation maintained under concurrency
            total_violations = sum(result["isolation_violations"] for result in concurrent_results)
            assert total_violations == 0, \
                f"Concurrent operations caused {total_violations} isolation violations"
            
            # Verify each batch maintained isolation
            for i, result in enumerate(concurrent_results):
                assert result["isolation_violations"] == 0, \
                    f"Concurrent batch {i} had isolation violations"
                
                # Each organization should have successful operations
                for org_id, org_summary in result["organization_summaries"].items():
                    assert org_summary["successful_operations"] > 0, \
                        f"Org {org_id} in batch {i} had no successful operations"
            
            # Generate final compliance report after concurrent load
            final_compliance = await validator.generate_enterprise_isolation_report()
            
            # Concurrency must not affect compliance
            assert final_compliance["isolation_compliance_score"] == 1.0, \
                "Concurrent operations must not affect isolation compliance"
            assert final_compliance["total_violations"] == 0, \
                "Concurrent load must not introduce violations"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.enterprise_scaling
    async def test_enterprise_scaling_isolation_maintained(self, real_services_fixture):
        """Test isolation is maintained as enterprise tenant count scales up."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = EnterpriseMultiTenantIsolationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create increasing number of tenants to test scaling
            scaling_tenants = []
            tier_cycle = [OrganizationTier.PROFESSIONAL, OrganizationTier.ENTERPRISE, OrganizationTier.ENTERPRISE_PLUS]
            isolation_cycle = [IsolationLevel.BASIC, IsolationLevel.STANDARD, IsolationLevel.STRICT]
            
            # Scale up to 6 organizations (simulating growth)
            for i in range(6):
                tier = tier_cycle[i % 3]
                isolation = isolation_cycle[i % 3]
                
                tenant = await validator.create_organization_tenant(
                    f"scale-{i}", tier, isolation, user_count=2
                )
                scaling_tenants.append(tenant)
                
                # Test isolation after each new tenant addition
                scaling_operations = await validator.simulate_multi_tenant_websocket_operations(
                    operations_per_org=3
                )
                
                # Isolation must be maintained at every scale
                assert scaling_operations["isolation_violations"] == 0, \
                    f"Isolation violation at scale {i+1} tenants"
                assert scaling_operations["successful_operations"] > 0, \
                    f"No successful operations at scale {i+1} tenants"
            
            # Final scaling validation
            final_scaling_report = await validator.generate_enterprise_isolation_report()
            
            # Scaling requirements
            assert final_scaling_report["total_organizations"] == 6, \
                "Should have 6 scaled organizations"
            assert final_scaling_report["isolation_compliance_score"] == 1.0, \
                "Scaling must maintain perfect isolation compliance"
            assert final_scaling_report["total_violations"] == 0, \
                "Scaling should not introduce any violations"
            
            # Verify each scaled organization maintained isolation
            for org_id, org_summary in final_scaling_report["organization_summaries"].items():
                assert org_summary["compliance_status"] == "compliant", \
                    f"Scaled organization {org_id} lost compliance"
                assert org_summary["violations_count"] == 0, \
                    f"Scaled organization {org_id} has violations"
            
        finally:
            await validator.cleanup()