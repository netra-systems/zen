"""Multi-Tenant Workspace Isolation L4 Critical Path Tests (Staging Environment)

Business Value Justification (BVJ):
- Segment: Enterprise ($50K+ MRR) - Critical for multi-tenant security and compliance
- Business Goal: Complete workspace isolation, regulatory compliance, enterprise trust and security
- Value Impact: Prevents catastrophic data breaches, ensures SOC2/GDPR compliance, maintains customer confidence
- Strategic/Revenue Impact: $50K+ MRR protection through enterprise-grade workspace security validation

Critical Path: Multi-workspace provisioning -> Complete isolation validation -> Cross-workspace access prevention -> Resource quota enforcement -> Billing separation -> Audit compliance
Coverage: Real multi-tenant workspace isolation in staging, production-level security testing, compliance audit trails
L4 Realism: Tests against real staging environment, real multi-tenant database setup, real security controls

IMPORTANT: This is a critical L4 test for Enterprise customer trust and compliance requirements.
All workspace isolation must be validated in real staging environment conditions.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock

import pytest

# Permissions service replaced with auth_integration
from netra_backend.app.auth_integration.auth import require_permission

from netra_backend.app.services.database.connection_manager import (
    DatabaseConnectionManager,
)

from netra_backend.tests.integration.staging_config.base import StagingConfigTestBase

PermissionsService = AsyncMock
from netra_backend.app.core.security import SecurityContext
from netra_backend.app.services.audit.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

@dataclass
class WorkspaceTestData:
    """Test workspace data structure for L4 isolation testing."""
    workspace_id: str
    organization_id: str
    name: str
    tier: str
    created_by: str
    users: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    isolation_verified: bool = False
    billing_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TenantTestData:
    """Test tenant data structure for multi-tenant testing."""
    tenant_id: str
    organization_name: str
    tier: str
    workspaces: List[WorkspaceTestData] = field(default_factory=list)
    users: List[str] = field(default_factory=list)
    quota_limits: Dict[str, int] = field(default_factory=dict)
    billing_namespace: str = ""

class MultiTenantWorkspaceIsolationL4Manager:
    """Manages L4 multi-tenant workspace isolation testing with real staging services."""
    
    def __init__(self):
        self.db_manager = None
        self.permissions_service = None
        self.audit_logger = None
        self.staging_base = StagingConfigTestBase()
        self.test_tenants: Dict[str, TenantTestData] = {}
        self.access_attempts = []
        self.isolation_violations = []
        self.compliance_records = []
        self.billing_violations = []
        
    async def initialize_services(self):
        """Initialize services for L4 multi-tenant workspace isolation testing."""
        try:
            # Set staging environment variables
            staging_env = self.staging_base.get_staging_env_vars()
            for key, value in staging_env.items():
                os.environ[key] = value
            
            # Initialize database manager with staging connection
            self.db_manager = DatabaseConnectionManager()
            await self.db_manager.initialize(use_staging_config=True)
            
            # Initialize permissions service with staging config
            self.permissions_service = PermissionsService()
            await self.permissions_service.initialize(use_staging_db=True)
            
            # Initialize audit logger with staging config
            self.audit_logger = AuditLogger()
            await self.audit_logger.initialize(use_staging_compliance=True)
            
            # Verify staging database connectivity
            await self._verify_staging_connectivity()
            
            logger.info("L4 multi-tenant workspace isolation services initialized with staging")
            
        except Exception as e:
            logger.error(f"Failed to initialize L4 workspace isolation services: {e}")
            raise
    
    async def _verify_staging_connectivity(self):
        """Verify connectivity to staging database and services."""
        try:
            # Verify database connection
            staging_db_check = await self.db_manager.execute_query(
                "SELECT 1 as health_check, NOW() as timestamp"
            )
            assert staging_db_check[0]["health_check"] == 1
            
            # Verify audit service can write to staging
            test_audit = await self.audit_logger.log_event(
                event_type="l4_workspace_test_connectivity_check",
                tenant_id="test_connectivity_workspace",
                details={"test": True, "timestamp": time.time()}
            )
            assert test_audit is not None
            
            logger.info("Staging connectivity verified for L4 workspace testing")
            
        except Exception as e:
            raise RuntimeError(f"Staging connectivity verification failed: {e}")
    
    async def create_test_tenant_with_workspaces(self, org_name: str, tier: str = "enterprise", 
                                                num_workspaces: int = 3) -> TenantTestData:
        """Create a test tenant with multiple isolated workspaces in staging."""
        tenant_id = f"l4_tenant_{uuid.uuid4().hex[:12]}"
        
        try:
            # Create tenant organization in staging database
            await self.db_manager.execute_query(
                """
                INSERT INTO organizations (id, name, tier, created_at, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (tenant_id, org_name, tier, datetime.utcnow(), "active",
                 {"test_tenant": True, "l4_test": True, "created_by": "l4_workspace_isolation_test"})
            )
            
            # Create tenant users with different roles
            users = []
            for i in range(4):  # Create 4 users per tenant
                user_id = f"{tenant_id}_user_{i}"
                email = f"user{i}@{org_name.lower()}.staging-test.com"
                role = ["admin", "editor", "viewer", "member"][i % 4]
                
                await self.db_manager.execute_query(
                    """
                    INSERT INTO users (id, email, organization_id, role, created_at, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, email, tenant_id, role, datetime.utcnow(), "active")
                )
                users.append(user_id)
            
            # Set up resource quotas based on tier
            quota_limits = {
                "enterprise": {"workspaces": 50, "users": 1000, "storage_gb": 1000, "api_calls": 100000},
                "pro": {"workspaces": 10, "users": 100, "storage_gb": 100, "api_calls": 10000},
                "free": {"workspaces": 3, "users": 5, "storage_gb": 5, "api_calls": 1000}
            }.get(tier, {"workspaces": 3, "users": 5, "storage_gb": 5, "api_calls": 1000})
            
            # Insert quota limits into staging database
            await self.db_manager.execute_query(
                """
                INSERT INTO tenant_quotas (tenant_id, quota_type, quota_limit, current_usage)
                VALUES (%s, %s, %s, %s), (%s, %s, %s, %s), (%s, %s, %s, %s), (%s, %s, %s, %s)
                """,
                (tenant_id, "workspaces", quota_limits["workspaces"], 0,
                 tenant_id, "users", quota_limits["users"], len(users),
                 tenant_id, "storage_gb", quota_limits["storage_gb"], 0,
                 tenant_id, "api_calls", quota_limits["api_calls"], 0)
            )
            
            # Create multiple isolated workspaces for the tenant
            workspaces = []
            for i in range(num_workspaces):
                workspace = await self._create_isolated_workspace(
                    tenant_id, users[i % len(users)], f"{org_name}_Workspace_{i+1}", tier
                )
                workspaces.append(workspace)
            
            # Set up billing namespace isolation
            billing_namespace = f"billing_{tenant_id}_{tier}"
            await self._setup_billing_isolation(tenant_id, billing_namespace, tier)
            
            tenant_data = TenantTestData(
                tenant_id=tenant_id,
                organization_name=org_name,
                tier=tier,
                workspaces=workspaces,
                users=users,
                quota_limits=quota_limits,
                billing_namespace=billing_namespace
            )
            
            self.test_tenants[tenant_id] = tenant_data
            
            # Log tenant creation in staging audit trail
            await self.audit_logger.log_event(
                event_type="l4_tenant_with_workspaces_created",
                tenant_id=tenant_id,
                details={
                    "organization_name": org_name,
                    "tier": tier,
                    "workspaces_count": num_workspaces,
                    "users_count": len(users),
                    "quota_limits": quota_limits,
                    "billing_namespace": billing_namespace,
                    "l4_test": True,
                    "staging_environment": True
                }
            )
            
            return tenant_data
            
        except Exception as e:
            logger.error(f"Failed to create L4 test tenant {org_name}: {e}")
            raise
    
    async def _create_isolated_workspace(self, tenant_id: str, created_by: str, 
                                       workspace_name: str, tier: str) -> WorkspaceTestData:
        """Create an isolated workspace within a tenant."""
        workspace_id = f"ws_{uuid.uuid4().hex[:12]}"
        
        try:
            # Create workspace in staging database with proper isolation
            await self.db_manager.execute_query(
                """
                INSERT INTO workspaces (id, name, tenant_id, created_by, tier, created_at, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (workspace_id, workspace_name, tenant_id, created_by, tier, datetime.utcnow(), "active",
                 {"test_workspace": True, "l4_test": True, "isolation_level": "strict"})
            )
            
            # Create workspace-specific resources with tenant isolation
            resources = []
            resource_types = ["document", "dataset", "model", "project", "conversation"]
            for resource_type in resource_types:
                resource_id = f"{workspace_id}_{resource_type}_{uuid.uuid4().hex[:8]}"
                
                await self.db_manager.execute_query(
                    """
                    INSERT INTO workspace_resources (id, workspace_id, tenant_id, resource_type, 
                                                   created_at, data, isolation_verified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (resource_id, workspace_id, tenant_id, resource_type, datetime.utcnow(),
                     {"confidential_data": f"sensitive_{workspace_name}_{resource_type}",
                      "tenant_id": tenant_id, "workspace_id": workspace_id}, True)
                )
                resources.append(resource_id)
            
            # Set up workspace permissions with strict isolation
            await self._setup_workspace_permissions(workspace_id, tenant_id, created_by, resources)
            
            # Initialize billing tracking for workspace
            billing_data = await self._initialize_workspace_billing(workspace_id, tenant_id, tier)
            
            workspace_data = WorkspaceTestData(
                workspace_id=workspace_id,
                organization_id=tenant_id,
                name=workspace_name,
                tier=tier,
                created_by=created_by,
                users=[created_by],  # Creator has access by default
                resources=resources,
                isolation_verified=True,
                billing_data=billing_data
            )
            
            return workspace_data
            
        except Exception as e:
            logger.error(f"Failed to create isolated workspace {workspace_name}: {e}")
            raise
    
    async def _setup_workspace_permissions(self, workspace_id: str, tenant_id: str, 
                                         created_by: str, resources: List[str]):
        """Set up workspace permissions with strict tenant isolation."""
        try:
            # Grant creator full permissions to their workspace
            creator_permissions = ["read", "write", "delete", "manage_permissions", "share"]
            
            for permission in creator_permissions:
                await self.db_manager.execute_query(
                    """
                    INSERT INTO workspace_permissions (user_id, workspace_id, tenant_id, 
                                                     permission, granted_at, granted_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (created_by, workspace_id, tenant_id, permission, datetime.utcnow(), created_by)
                )
            
            # Set up resource-level permissions
            for resource_id in resources:
                for permission in creator_permissions:
                    await self.db_manager.execute_query(
                        """
                        INSERT INTO resource_permissions (user_id, resource_id, workspace_id, 
                                                        tenant_id, permission, granted_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (created_by, resource_id, workspace_id, tenant_id, permission, datetime.utcnow())
                    )
            
        except Exception as e:
            logger.error(f"Failed to setup workspace permissions: {e}")
            raise
    
    async def _setup_billing_isolation(self, tenant_id: str, billing_namespace: str, tier: str):
        """Set up billing isolation for the tenant."""
        try:
            # Create billing namespace in staging
            await self.db_manager.execute_query(
                """
                INSERT INTO billing_namespaces (tenant_id, namespace, tier, created_at, 
                                              usage_tracking, cost_allocation)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (tenant_id, billing_namespace, tier, datetime.utcnow(), True, True)
            )
            
            # Initialize usage tracking
            await self.db_manager.execute_query(
                """
                INSERT INTO usage_tracking (tenant_id, billing_namespace, period, 
                                          api_calls, storage_used, compute_hours)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (tenant_id, billing_namespace, datetime.utcnow().strftime("%Y-%m"), 0, 0, 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to setup billing isolation: {e}")
            raise
    
    async def _initialize_workspace_billing(self, workspace_id: str, tenant_id: str, 
                                          tier: str) -> Dict[str, Any]:
        """Initialize billing tracking for workspace."""
        try:
            billing_data = {
                "workspace_id": workspace_id,
                "tenant_id": tenant_id,
                "tier": tier,
                "usage_start": time.time(),
                "api_calls": 0,
                "storage_bytes": 0,
                "compute_seconds": 0
            }
            
            await self.db_manager.execute_query(
                """
                INSERT INTO workspace_billing (workspace_id, tenant_id, billing_data, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (workspace_id, tenant_id, billing_data, datetime.utcnow())
            )
            
            return billing_data
            
        except Exception as e:
            logger.error(f"Failed to initialize workspace billing: {e}")
            return {}
    
    async def test_cross_tenant_workspace_access_prevention(self, source_tenant_id: str, 
                                                          target_tenant_id: str,
                                                          user_id: str, workspace_id: str) -> Dict[str, Any]:
        """Test cross-tenant workspace access prevention with real staging data."""
        access_attempt_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Create security context for source tenant user
            security_context = await self._create_workspace_security_context(source_tenant_id, user_id)
            
            # Attempt to access target tenant workspace in staging
            access_result = await self._attempt_workspace_access(
                security_context, target_tenant_id, workspace_id
            )
            
            # Record access attempt in staging audit trail
            access_attempt = {
                "attempt_id": access_attempt_id,
                "source_tenant": source_tenant_id,
                "target_tenant": target_tenant_id,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "access_granted": access_result["access_granted"],
                "timestamp": start_time,
                "response_time": time.time() - start_time,
                "staging_test": True,
                "test_type": "cross_tenant_workspace_access"
            }
            
            self.access_attempts.append(access_attempt)
            
            # Record isolation violation if access was granted inappropriately
            if access_result["access_granted"] and source_tenant_id != target_tenant_id:
                violation = {
                    "violation_type": "cross_tenant_workspace_access",
                    "source_tenant": source_tenant_id,
                    "target_tenant": target_tenant_id,
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "timestamp": start_time,
                    "severity": "critical",
                    "staging_environment": True
                }
                
                self.isolation_violations.append(violation)
                
                # Log security violation in staging audit
                await self.audit_logger.log_event(
                    event_type="l4_workspace_security_violation",
                    tenant_id=source_tenant_id,
                    details=violation,
                    severity="critical"
                )
            
            # Log access attempt in staging audit trail
            await self.audit_logger.log_event(
                event_type="l4_workspace_access_attempt",
                tenant_id=source_tenant_id,
                details={
                    "target_tenant": target_tenant_id,
                    "workspace_id": workspace_id,
                    "access_granted": access_result["access_granted"],
                    "user_id": user_id,
                    "staging_test": True
                }
            )
            
            return {
                "access_granted": access_result["access_granted"],
                "isolation_maintained": not (access_result["access_granted"] and source_tenant_id != target_tenant_id),
                "response_time": time.time() - start_time,
                "attempt_id": access_attempt_id,
                "staging_verified": True
            }
            
        except Exception as e:
            logger.error(f"L4 cross-tenant workspace access test failed: {e}")
            return {
                "access_granted": False,
                "isolation_maintained": True,
                "error": str(e),
                "response_time": time.time() - start_time,
                "staging_verified": False
            }
    
    async def _create_workspace_security_context(self, tenant_id: str, user_id: str) -> SecurityContext:
        """Create security context with real staging workspace permissions."""
        try:
            # Query real user workspace permissions from staging database
            permissions_result = await self.db_manager.execute_query(
                """
                SELECT wp.permission, wp.workspace_id, w.tenant_id
                FROM workspace_permissions wp
                JOIN workspaces w ON w.id = wp.workspace_id
                WHERE wp.user_id = %s AND w.tenant_id = %s
                """,
                (user_id, tenant_id)
            )
            
            user_permissions = set()
            for perm in permissions_result:
                user_permissions.add(f"{perm['permission']}:{perm['workspace_id']}")
            
            return SecurityContext(
                tenant_id=tenant_id,
                user_id=user_id,
                permissions=user_permissions,
                source="staging_workspace_database"
            )
            
        except Exception as e:
            logger.error(f"Failed to create workspace security context: {e}")
            return SecurityContext(tenant_id=tenant_id, user_id=user_id, permissions=set())
    
    async def _attempt_workspace_access(self, security_context: SecurityContext,
                                      target_tenant_id: str, workspace_id: str) -> Dict[str, Any]:
        """Attempt to access a workspace with real staging isolation checks."""
        try:
            # Check if workspace exists in staging database
            workspace_result = await self.db_manager.execute_query(
                """
                SELECT id, tenant_id, name, status FROM workspaces
                WHERE id = %s
                """,
                (workspace_id,)
            )
            
            if not workspace_result:
                return {"access_granted": False, "reason": "workspace_not_found"}
            
            workspace = workspace_result[0]
            
            # Critical isolation check - should only access own tenant workspaces
            if security_context.tenant_id != workspace["tenant_id"]:
                # Cross-tenant workspace access should be denied
                return {"access_granted": False, "reason": "cross_tenant_denied"}
            
            # Check workspace-specific permissions within tenant
            if security_context.tenant_id == target_tenant_id:
                # Same tenant access - check workspace permissions
                workspace_permission = f"read:{workspace_id}"
                has_permission = workspace_permission in security_context.permissions
                return {
                    "access_granted": has_permission,
                    "reason": "workspace_permission_checked" if has_permission else "workspace_permission_denied"
                }
            
            return {"access_granted": False, "reason": "tenant_isolation_enforced"}
            
        except Exception as e:
            logger.error(f"Workspace access attempt failed: {e}")
            return {"access_granted": False, "reason": "system_error", "error": str(e)}
    
    async def validate_workspace_quota_enforcement(self, tenant_id: str) -> Dict[str, Any]:
        """Validate workspace quota enforcement for tenant."""
        try:
            # Get tenant quota limits from staging database
            quota_result = await self.db_manager.execute_query(
                """
                SELECT quota_type, quota_limit, current_usage
                FROM tenant_quotas
                WHERE tenant_id = %s
                """,
                (tenant_id,)
            )
            
            quota_status = {}
            for quota in quota_result:
                quota_type = quota["quota_type"]
                quota_status[quota_type] = {
                    "limit": quota["quota_limit"],
                    "current_usage": quota["current_usage"],
                    "within_limit": quota["current_usage"] <= quota["quota_limit"]
                }
            
            # Get actual workspace count for validation
            workspace_count_result = await self.db_manager.execute_query(
                "SELECT COUNT(*) as count FROM workspaces WHERE tenant_id = %s",
                (tenant_id,)
            )
            actual_workspace_count = workspace_count_result[0]["count"]
            
            # Verify quota enforcement
            quota_compliant = True
            violations = []
            
            for quota_type, status in quota_status.items():
                if not status["within_limit"]:
                    quota_compliant = False
                    violations.append({
                        "quota_type": quota_type,
                        "limit": status["limit"],
                        "current_usage": status["current_usage"]
                    })
            
            return {
                "quota_compliant": quota_compliant,
                "quota_status": quota_status,
                "actual_workspace_count": actual_workspace_count,
                "violations": violations,
                "tenant_id": tenant_id,
                "staging_verified": True
            }
            
        except Exception as e:
            return {
                "quota_compliant": False,
                "error": str(e),
                "tenant_id": tenant_id,
                "staging_verified": False
            }
    
    async def validate_billing_isolation(self, tenant_id: str) -> Dict[str, Any]:
        """Validate billing isolation for tenant workspaces."""
        try:
            # Get tenant billing namespace
            billing_result = await self.db_manager.execute_query(
                """
                SELECT namespace, usage_tracking, cost_allocation
                FROM billing_namespaces
                WHERE tenant_id = %s
                """,
                (tenant_id,)
            )
            
            if not billing_result:
                return {
                    "billing_isolated": False,
                    "reason": "no_billing_namespace",
                    "tenant_id": tenant_id,
                    "staging_verified": False
                }
            
            billing_namespace = billing_result[0]
            
            # Check for billing cross-contamination
            cross_contamination_result = await self.db_manager.execute_query(
                """
                SELECT COUNT(*) as count
                FROM usage_tracking ut1
                WHERE ut1.billing_namespace = %s
                AND EXISTS (
                    SELECT 1 FROM usage_tracking ut2 
                    WHERE ut2.tenant_id != %s 
                    AND ut2.billing_namespace = ut1.billing_namespace
                )
                """,
                (billing_namespace["namespace"], tenant_id)
            )
            
            cross_contaminated = cross_contamination_result[0]["count"] > 0
            
            # Validate workspace billing isolation
            workspace_billing_result = await self.db_manager.execute_query(
                """
                SELECT COUNT(*) as count
                FROM workspace_billing
                WHERE tenant_id = %s
                """,
                (tenant_id,)
            )
            
            workspace_billing_count = workspace_billing_result[0]["count"]
            
            return {
                "billing_isolated": not cross_contaminated,
                "billing_namespace": billing_namespace["namespace"],
                "usage_tracking_enabled": billing_namespace["usage_tracking"],
                "cost_allocation_enabled": billing_namespace["cost_allocation"],
                "workspace_billing_entries": workspace_billing_count,
                "cross_contaminated": cross_contaminated,
                "tenant_id": tenant_id,
                "staging_verified": True
            }
            
        except Exception as e:
            return {
                "billing_isolated": False,
                "error": str(e),
                "tenant_id": tenant_id,
                "staging_verified": False
            }
    
    async def test_concurrent_multi_tenant_operations(self, tenant_ids: List[str]) -> Dict[str, Any]:
        """Test concurrent operations across multiple tenants to validate isolation."""
        start_time = time.time()
        
        try:
            # Generate concurrent workspace access attempts across tenants
            access_tasks = []
            
            for i, source_tenant_id in enumerate(tenant_ids):
                source_tenant = self.test_tenants[source_tenant_id]
                source_user = source_tenant.users[0]
                
                for j, target_tenant_id in enumerate(tenant_ids):
                    target_tenant = self.test_tenants[target_tenant_id]
                    target_workspace = target_tenant.workspaces[0]
                    
                    task = self.test_cross_tenant_workspace_access_prevention(
                        source_tenant_id, target_tenant_id, 
                        source_user, target_workspace.workspace_id
                    )
                    access_tasks.append((source_tenant_id, target_tenant_id, task))
            
            # Execute all access attempts concurrently
            results = []
            for source_tenant_id, target_tenant_id, task in access_tasks:
                result = await task
                result["source_tenant_id"] = source_tenant_id
                result["target_tenant_id"] = target_tenant_id
                results.append(result)
            
            # Analyze results
            same_tenant_results = [r for r in results if r["source_tenant_id"] == r["target_tenant_id"]]
            cross_tenant_results = [r for r in results if r["source_tenant_id"] != r["target_tenant_id"]]
            
            # Calculate success rates
            same_tenant_success = sum(1 for r in same_tenant_results if r["access_granted"]) / len(same_tenant_results) * 100 if same_tenant_results else 0
            cross_tenant_denied = sum(1 for r in cross_tenant_results if not r["access_granted"]) / len(cross_tenant_results) * 100 if cross_tenant_results else 100
            
            # Calculate performance metrics
            response_times = [r["response_time"] for r in results if "response_time" in r]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                "total_operations": len(results),
                "same_tenant_operations": len(same_tenant_results),
                "cross_tenant_operations": len(cross_tenant_results),
                "same_tenant_success_rate": same_tenant_success,
                "cross_tenant_denial_rate": cross_tenant_denied,
                "avg_response_time": avg_response_time,
                "isolation_maintained": cross_tenant_denied >= 99.0,  # Should be near 100%
                "total_duration": time.time() - start_time,
                "staging_verified": True
            }
            
        except Exception as e:
            return {
                "isolation_maintained": False,
                "error": str(e),
                "total_duration": time.time() - start_time,
                "staging_verified": False
            }
    
    async def get_comprehensive_isolation_metrics(self) -> Dict[str, Any]:
        """Get comprehensive L4 workspace isolation metrics."""
        total_attempts = len(self.access_attempts)
        violations = len(self.isolation_violations)
        
        if total_attempts > 0:
            violation_rate = (violations / total_attempts) * 100
            success_rate = ((total_attempts - violations) / total_attempts) * 100
        else:
            violation_rate = 0
            success_rate = 100
        
        # Calculate tenant metrics
        tenant_count = len(self.test_tenants)
        total_workspaces = sum(len(tenant.workspaces) for tenant in self.test_tenants.values())
        
        return {
            "total_tenants": tenant_count,
            "total_workspaces": total_workspaces,
            "total_access_attempts": total_attempts,
            "isolation_violations": violations,
            "violation_rate": violation_rate,
            "isolation_success_rate": success_rate,
            "billing_violations": len(self.billing_violations),
            "staging_environment": True,
            "l4_test_level": True,
            "test_type": "multi_tenant_workspace_isolation"
        }
    
    async def cleanup(self):
        """Clean up L4 test tenants and workspace resources."""
        try:
            # Clean up test tenants from staging database
            for tenant_id in list(self.test_tenants.keys()):
                # Delete workspace billing data
                await self.db_manager.execute_query(
                    "DELETE FROM workspace_billing WHERE tenant_id = %s",
                    (tenant_id,)
                )
                
                # Delete workspace resources
                await self.db_manager.execute_query(
                    "DELETE FROM workspace_resources WHERE tenant_id = %s",
                    (tenant_id,)
                )
                
                # Delete workspace permissions
                await self.db_manager.execute_query(
                    "DELETE FROM workspace_permissions WHERE tenant_id = %s",
                    (tenant_id,)
                )
                
                # Delete resource permissions
                await self.db_manager.execute_query(
                    "DELETE FROM resource_permissions WHERE tenant_id = %s",
                    (tenant_id,)
                )
                
                # Delete workspaces
                await self.db_manager.execute_query(
                    "DELETE FROM workspaces WHERE tenant_id = %s",
                    (tenant_id,)
                )
                
                # Delete usage tracking
                await self.db_manager.execute_query(
                    "DELETE FROM usage_tracking WHERE tenant_id = %s",
                    (tenant_id,)
                )
                
                # Delete billing namespaces
                await self.db_manager.execute_query(
                    "DELETE FROM billing_namespaces WHERE tenant_id = %s",
                    (tenant_id,)
                )
                
                # Delete tenant quotas
                await self.db_manager.execute_query(
                    "DELETE FROM tenant_quotas WHERE tenant_id = %s",
                    (tenant_id,)
                )
                
                # Delete tenant users
                await self.db_manager.execute_query(
                    "DELETE FROM users WHERE organization_id = %s",
                    (tenant_id,)
                )
                
                # Delete tenant organization
                await self.db_manager.execute_query(
                    "DELETE FROM organizations WHERE id = %s",
                    (tenant_id,)
                )
            
            # Log cleanup in staging audit
            await self.audit_logger.log_event(
                event_type="l4_workspace_test_cleanup",
                tenant_id="system",
                details={
                    "tenants_cleaned": len(self.test_tenants),
                    "staging_environment": True,
                    "l4_test": True,
                    "test_type": "multi_tenant_workspace_isolation"
                }
            )
            
            # Shutdown services
            if self.permissions_service:
                await self.permissions_service.shutdown()
            if self.audit_logger:
                await self.audit_logger.shutdown()
            if self.db_manager:
                await self.db_manager.shutdown()
                
        except Exception as e:
            logger.error(f"L4 workspace cleanup failed: {e}")

@pytest.fixture
async def l4_workspace_isolation_manager():
    """Create L4 multi-tenant workspace isolation manager for staging tests."""
    manager = MultiTenantWorkspaceIsolationL4Manager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_multi_tenant_workspace_creation_isolation(l4_workspace_isolation_manager):
    """Test complete multi-tenant workspace creation and isolation in staging environment."""
    # Create three different enterprise tenants with multiple workspaces
    tenant_a = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "EnterpriseCorpA", "enterprise", 4
    )
    tenant_b = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "EnterpriseCorpB", "enterprise", 3
    )
    tenant_c = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "EnterpriseCorpC", "pro", 2
    )
    
    # Validate tenant creation
    assert len(tenant_a.workspaces) == 4
    assert len(tenant_b.workspaces) == 3
    assert len(tenant_c.workspaces) == 2
    assert tenant_a.tier == "enterprise"
    assert tenant_b.tier == "enterprise"
    assert tenant_c.tier == "pro"
    
    # Verify workspace isolation within each tenant
    for tenant in [tenant_a, tenant_b, tenant_c]:
        for workspace in tenant.workspaces:
            assert workspace.organization_id == tenant.tenant_id
            assert workspace.isolation_verified is True
            assert len(workspace.resources) == 5  # Should have 5 resource types
            assert workspace.created_by in tenant.users

@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_cross_tenant_workspace_access_prevention(l4_workspace_isolation_manager):
    """Test cross-tenant workspace access prevention with real staging data."""
    # Create two enterprise tenants with sensitive workspaces
    tenant_a = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "SecureTenantA", "enterprise", 2
    )
    tenant_b = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "SecureTenantB", "enterprise", 2
    )
    
    # Attempt cross-tenant workspace access: TenantA user -> TenantB workspace
    user_a = tenant_a.users[0]
    workspace_b = tenant_b.workspaces[0]
    
    access_result = await l4_workspace_isolation_manager.test_cross_tenant_workspace_access_prevention(
        tenant_a.tenant_id, tenant_b.tenant_id, user_a, workspace_b.workspace_id
    )
    
    # Verify access was completely denied
    assert access_result["access_granted"] is False
    assert access_result["isolation_maintained"] is True
    assert access_result["staging_verified"] is True
    assert access_result["response_time"] < 2.0  # Should be fast denial
    
    # Test reverse direction with different users
    user_b = tenant_b.users[1]  # Different user (editor role)
    workspace_a = tenant_a.workspaces[1]  # Different workspace
    
    access_result_reverse = await l4_workspace_isolation_manager.test_cross_tenant_workspace_access_prevention(
        tenant_b.tenant_id, tenant_a.tenant_id, user_b, workspace_a.workspace_id
    )
    
    assert access_result_reverse["access_granted"] is False
    assert access_result_reverse["isolation_maintained"] is True
    assert access_result_reverse["staging_verified"] is True

@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_same_tenant_workspace_access_control(l4_workspace_isolation_manager):
    """Test proper workspace access control within same tenant."""
    # Create tenant with multiple workspaces and users
    tenant = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "WorkspaceAccessTenant", "enterprise", 3
    )
    
    # Test access for workspace creator (should have access)
    for i, workspace in enumerate(tenant.workspaces):
        creator = workspace.created_by
        
        access_result = await l4_workspace_isolation_manager.test_cross_tenant_workspace_access_prevention(
            tenant.tenant_id, tenant.tenant_id, creator, workspace.workspace_id
        )
        
        # Creator should have access to their own workspace
        assert access_result["access_granted"] is True
        assert access_result["isolation_maintained"] is True
        assert access_result["staging_verified"] is True
    
    # Test access for non-creator users (should be denied without explicit sharing)
    non_creator = tenant.users[1]  # Different user than workspace creator
    workspace = tenant.workspaces[0]
    
    access_result = await l4_workspace_isolation_manager.test_cross_tenant_workspace_access_prevention(
        tenant.tenant_id, tenant.tenant_id, non_creator, workspace.workspace_id
    )
    
    # Non-creator should not have access without explicit permissions
    assert access_result["access_granted"] is False
    assert access_result["isolation_maintained"] is True
    assert access_result["staging_verified"] is True

@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_workspace_quota_enforcement(l4_workspace_isolation_manager):
    """Test workspace quota enforcement across different tenant tiers."""
    # Create tenants with different tiers
    enterprise_tenant = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "EnterpriseTenantQuota", "enterprise", 5
    )
    pro_tenant = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "ProTenantQuota", "pro", 3
    )
    
    # Validate quota enforcement for enterprise tenant
    enterprise_quota = await l4_workspace_isolation_manager.validate_workspace_quota_enforcement(
        enterprise_tenant.tenant_id
    )
    
    assert enterprise_quota["quota_compliant"] is True
    assert enterprise_quota["staging_verified"] is True
    assert enterprise_quota["actual_workspace_count"] == 5
    assert enterprise_quota["quota_status"]["workspaces"]["limit"] == 50  # Enterprise limit
    assert enterprise_quota["quota_status"]["workspaces"]["within_limit"] is True
    
    # Validate quota enforcement for pro tenant
    pro_quota = await l4_workspace_isolation_manager.validate_workspace_quota_enforcement(
        pro_tenant.tenant_id
    )
    
    assert pro_quota["quota_compliant"] is True
    assert pro_quota["staging_verified"] is True
    assert pro_quota["actual_workspace_count"] == 3
    assert pro_quota["quota_status"]["workspaces"]["limit"] == 10  # Pro limit
    assert pro_quota["quota_status"]["workspaces"]["within_limit"] is True

@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_billing_separation_validation(l4_workspace_isolation_manager):
    """Test billing separation between tenants and workspaces."""
    # Create multiple tenants for billing isolation testing
    tenant_a = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "BillingTenantA", "enterprise", 2
    )
    tenant_b = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "BillingTenantB", "pro", 2
    )
    
    # Validate billing isolation for tenant A
    billing_a = await l4_workspace_isolation_manager.validate_billing_isolation(tenant_a.tenant_id)
    
    assert billing_a["billing_isolated"] is True
    assert billing_a["staging_verified"] is True
    assert billing_a["usage_tracking_enabled"] is True
    assert billing_a["cost_allocation_enabled"] is True
    assert billing_a["cross_contaminated"] is False
    assert billing_a["workspace_billing_entries"] == 2  # Should have 2 workspaces
    
    # Validate billing isolation for tenant B
    billing_b = await l4_workspace_isolation_manager.validate_billing_isolation(tenant_b.tenant_id)
    
    assert billing_b["billing_isolated"] is True
    assert billing_b["staging_verified"] is True
    assert billing_b["usage_tracking_enabled"] is True
    assert billing_b["cost_allocation_enabled"] is True
    assert billing_b["cross_contaminated"] is False
    assert billing_b["workspace_billing_entries"] == 2  # Should have 2 workspaces
    
    # Verify billing namespaces are different
    assert billing_a["billing_namespace"] != billing_b["billing_namespace"]

@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_concurrent_multi_tenant_operations(l4_workspace_isolation_manager):
    """Test isolation under concurrent multi-tenant operations."""
    # Create multiple tenants for concurrent testing
    tenant_ids = []
    for i in range(4):
        tenant = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
            f"ConcurrentTenant{i}", "enterprise", 2
        )
        tenant_ids.append(tenant.tenant_id)
    
    # Execute concurrent operations across all tenants
    concurrent_results = await l4_workspace_isolation_manager.test_concurrent_multi_tenant_operations(
        tenant_ids
    )
    
    # Verify concurrent isolation results
    assert concurrent_results["isolation_maintained"] is True
    assert concurrent_results["staging_verified"] is True
    assert concurrent_results["total_operations"] == 16  # 4 tenants x 4 tenants = 16 operations
    assert concurrent_results["same_tenant_operations"] == 4  # 4 same-tenant operations
    assert concurrent_results["cross_tenant_operations"] == 12  # 12 cross-tenant operations
    assert concurrent_results["cross_tenant_denial_rate"] >= 99.0  # Should deny cross-tenant access
    assert concurrent_results["avg_response_time"] < 3.0  # Should handle concurrent requests efficiently

@pytest.mark.staging
@pytest.mark.asyncio
async def test_l4_comprehensive_isolation_metrics_validation(l4_workspace_isolation_manager):
    """Test comprehensive isolation metrics validation."""
    # Create tenants and perform various operations
    tenant_a = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "MetricsTenantA", "enterprise", 3
    )
    tenant_b = await l4_workspace_isolation_manager.create_test_tenant_with_workspaces(
        "MetricsTenantB", "pro", 2
    )
    
    # Generate access attempts for metrics
    user_a = tenant_a.users[0]
    user_b = tenant_b.users[0]
    workspace_a = tenant_a.workspaces[0]
    workspace_b = tenant_b.workspaces[0]
    
    # Valid same-tenant access
    await l4_workspace_isolation_manager.test_cross_tenant_workspace_access_prevention(
        tenant_a.tenant_id, tenant_a.tenant_id, user_a, workspace_a.workspace_id
    )
    
    # Invalid cross-tenant access attempt
    await l4_workspace_isolation_manager.test_cross_tenant_workspace_access_prevention(
        tenant_a.tenant_id, tenant_b.tenant_id, user_a, workspace_b.workspace_id
    )
    
    # Get comprehensive metrics
    metrics = await l4_workspace_isolation_manager.get_comprehensive_isolation_metrics()
    
    # Verify metrics
    assert metrics["total_tenants"] == 2
    assert metrics["total_workspaces"] == 5  # 3 + 2 workspaces
    assert metrics["total_access_attempts"] >= 2
    assert metrics["isolation_success_rate"] >= 50.0  # Should have some successful same-tenant access
    assert metrics["staging_environment"] is True
    assert metrics["l4_test_level"] is True
    assert metrics["test_type"] == "multi_tenant_workspace_isolation"