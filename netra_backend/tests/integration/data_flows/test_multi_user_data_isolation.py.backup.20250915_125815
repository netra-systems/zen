"""
Multi-User Data Isolation Integration Tests

These tests validate data isolation, privacy protection, and secure data processing 
across multiple users and tenants without cross-contamination.

Focus Areas:
- Cross-tenant data segregation validation
- User context data protection and privacy
- Session data isolation and management
- Concurrent user data processing without contamination
- Enterprise data security and access controls
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Set
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from netra_backend.app.services.billing.usage_tracker import UsageTracker, UsageType, UsageEvent
from netra_backend.app.services.resource_management.tenant_isolator import (
    TenantIsolator, TenantResourceQuota, ResourceUsage
)
from netra_backend.app.services.billing.cost_calculator import CostCalculator


class UserSession:
    """Mock user session for isolation testing."""
    
    def __init__(self, user_id: str, tenant_id: str, session_id: str, 
                 security_level: str = "standard"):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.session_id = session_id
        self.security_level = security_level
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at
        self.data_context = {}
        self.permissions = set()
        self.isolated_storage = {}
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def set_data_context(self, key: str, value: Any):
        """Set data in user's isolated context."""
        self.data_context[key] = value
        self.update_activity()
    
    def get_data_context(self, key: str) -> Any:
        """Get data from user's isolated context."""
        self.update_activity()
        return self.data_context.get(key)
    
    def add_permission(self, permission: str):
        """Add permission to user session."""
        self.permissions.add(permission)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions


class SessionManager:
    """Mock session manager for multi-user isolation testing."""
    
    def __init__(self):
        self.active_sessions: Dict[str, UserSession] = {}
        self.tenant_sessions: Dict[str, Set[str]] = {}  # tenant_id -> session_ids
        self.user_sessions: Dict[str, Set[str]] = {}    # user_id -> session_ids
        self.session_lock = threading.RLock()
    
    def create_session(self, user_id: str, tenant_id: str, 
                      security_level: str = "standard") -> UserSession:
        """Create isolated user session."""
        with self.session_lock:
            session_id = f"session_{user_id}_{tenant_id}_{datetime.now(timezone.utc).timestamp()}"
            session = UserSession(user_id, tenant_id, session_id, security_level)
            
            # Store session
            self.active_sessions[session_id] = session
            
            # Track by tenant
            if tenant_id not in self.tenant_sessions:
                self.tenant_sessions[tenant_id] = set()
            self.tenant_sessions[tenant_id].add(session_id)
            
            # Track by user
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)
            
            return session
    
    def get_session(self, session_id: str) -> UserSession:
        """Get session by ID."""
        with self.session_lock:
            return self.active_sessions.get(session_id)
    
    def get_tenant_sessions(self, tenant_id: str) -> List[UserSession]:
        """Get all sessions for a tenant."""
        with self.session_lock:
            session_ids = self.tenant_sessions.get(tenant_id, set())
            return [self.active_sessions[sid] for sid in session_ids if sid in self.active_sessions]
    
    def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """Get all sessions for a user."""
        with self.session_lock:
            session_ids = self.user_sessions.get(user_id, set())
            return [self.active_sessions[sid] for sid in session_ids if sid in self.active_sessions]
    
    def validate_cross_tenant_isolation(self) -> Dict[str, Any]:
        """Validate no data leakage between tenants."""
        with self.session_lock:
            violations = []
            
            # Check each tenant's sessions
            for tenant_id, session_ids in self.tenant_sessions.items():
                tenant_sessions = [self.active_sessions[sid] for sid in session_ids 
                                 if sid in self.active_sessions]
                
                # Verify all sessions belong to this tenant
                for session in tenant_sessions:
                    if session.tenant_id != tenant_id:
                        violations.append({
                            "type": "tenant_session_mismatch",
                            "session_id": session.session_id,
                            "expected_tenant": tenant_id,
                            "actual_tenant": session.tenant_id
                        })
                
                # Check for data context isolation
                tenant_data_keys = set()
                for session in tenant_sessions:
                    session_keys = set(session.data_context.keys())
                    
                    # Look for potential cross-contamination
                    for other_tenant_id, other_session_ids in self.tenant_sessions.items():
                        if other_tenant_id == tenant_id:
                            continue
                        
                        other_sessions = [self.active_sessions[sid] for sid in other_session_ids 
                                        if sid in self.active_sessions]
                        
                        for other_session in other_sessions:
                            other_keys = set(other_session.data_context.keys())
                            # Check if any data contexts share keys with same values
                            common_keys = session_keys.intersection(other_keys)
                            
                            for key in common_keys:
                                session_value = session.data_context[key]
                                other_value = other_session.data_context[key]
                                
                                # Same values across tenants might indicate data leakage
                                if (session_value == other_value and 
                                    isinstance(session_value, (str, int, float)) and
                                    len(str(session_value)) > 5):  # Non-trivial values
                                    violations.append({
                                        "type": "potential_data_leakage",
                                        "tenant_a": tenant_id,
                                        "tenant_b": other_tenant_id,
                                        "session_a": session.session_id,
                                        "session_b": other_session.session_id,
                                        "shared_key": key,
                                        "shared_value": session_value
                                    })
            
            return {
                "violations": violations,
                "total_tenants": len(self.tenant_sessions),
                "total_sessions": len(self.active_sessions),
                "isolation_score": 1.0 - (len(violations) / max(len(self.active_sessions), 1))
            }


class TestMultiUserDataIsolation:
    """Test suite for multi-user data isolation and privacy protection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = SessionManager()
        self.tenant_isolator = TenantIsolator()
        self.usage_tracker = UsageTracker()
        self.cost_calculator = CostCalculator()
        
        # Test tenants
        self.enterprise_tenant = "enterprise_corp_001"
        self.startup_tenant = "startup_inc_002"
        self.government_tenant = "gov_agency_003"
        
        # Test users
        self.enterprise_users = ["ent_user_001", "ent_user_002", "ent_user_003"]
        self.startup_users = ["startup_user_001", "startup_user_002"]
        self.government_users = ["gov_user_001"]
    
    @pytest.mark.asyncio
    async def test_cross_tenant_data_segregation_validation(self):
        """Test that tenant data is completely segregated without cross-contamination."""
        # Register tenants with different security requirements
        enterprise_quota = TenantResourceQuota(
            tenant_id=self.enterprise_tenant,
            cpu_cores=32.0,
            memory_mb=65536,
            storage_gb=1000,
            max_concurrent_requests=1000,
            max_api_calls_per_hour=500000
        )
        
        startup_quota = TenantResourceQuota(
            tenant_id=self.startup_tenant,
            cpu_cores=4.0,
            memory_mb=8192,
            storage_gb=100,
            max_concurrent_requests=100,
            max_api_calls_per_hour=50000
        )
        
        government_quota = TenantResourceQuota(
            tenant_id=self.government_tenant,
            cpu_cores=16.0,
            memory_mb=32768,
            storage_gb=500,
            max_concurrent_requests=200,
            max_api_calls_per_hour=100000
        )
        
        # Register all tenants
        await self.tenant_isolator.register_tenant(self.enterprise_tenant, enterprise_quota)
        await self.tenant_isolator.register_tenant(self.startup_tenant, startup_quota)
        await self.tenant_isolator.register_tenant(self.government_tenant, government_quota)
        
        # Create usage data for each tenant
        tenant_usage_data = {
            self.enterprise_tenant: {
                "api_calls": 400000,
                "llm_tokens": 10000000,
                "storage": 800,
                "sensitive_operations": 5000
            },
            self.startup_tenant: {
                "api_calls": 30000,
                "llm_tokens": 500000,
                "storage": 50,
                "development_operations": 1000
            },
            self.government_tenant: {
                "api_calls": 80000,
                "llm_tokens": 2000000,
                "storage": 400,
                "classified_operations": 2000
            }
        }
        
        # Process usage for each tenant
        for tenant_id, usage_data in tenant_usage_data.items():
            for usage_type_str, quantity in usage_data.items():
                if usage_type_str in ["api_calls", "llm_tokens", "storage"]:
                    # Map to UsageType
                    usage_type_map = {
                        "api_calls": UsageType.API_CALL,
                        "llm_tokens": UsageType.LLM_TOKENS,
                        "storage": UsageType.STORAGE
                    }
                    
                    if usage_type_str in usage_type_map:
                        await self.usage_tracker.track_usage(
                            user_id=f"{tenant_id}_aggregate",
                            usage_type=usage_type_map[usage_type_str],
                            quantity=quantity,
                            unit="units",
                            metadata={"tenant_id": tenant_id, "isolation_test": True}
                        )
        
        # Validate tenant isolation
        tenant_statuses = []
        for tenant_id in [self.enterprise_tenant, self.startup_tenant, self.government_tenant]:
            status = await self.tenant_isolator.get_tenant_status(tenant_id)
            tenant_statuses.append(status)
            
            # Validate tenant has unique namespace
            assert status["namespace"] is not None
            assert tenant_id in status["namespace"] or "tenant" in status["namespace"]
            
            # Validate tenant-specific quotas
            quota = status["quota"]
            if tenant_id == self.enterprise_tenant:
                assert quota["cpu_cores"] == 32.0
                assert quota["memory_mb"] == 65536
            elif tenant_id == self.startup_tenant:
                assert quota["cpu_cores"] == 4.0
                assert quota["memory_mb"] == 8192
            elif tenant_id == self.government_tenant:
                assert quota["cpu_cores"] == 16.0
                assert quota["memory_mb"] == 32768
        
        # Validate no shared namespaces
        namespaces = [status["namespace"] for status in tenant_statuses]
        assert len(set(namespaces)) == len(namespaces), "Each tenant must have unique namespace"
        
        # Validate usage data isolation
        for tenant_id in [self.enterprise_tenant, self.startup_tenant, self.government_tenant]:
            user_usage = await self.usage_tracker.get_user_usage(f"{tenant_id}_aggregate")
            
            # Validate tenant-specific metadata
            for event in self.usage_tracker.usage_events:
                if event.user_id == f"{tenant_id}_aggregate":
                    assert event.metadata.get("tenant_id") == tenant_id
                    assert event.metadata.get("isolation_test") == True
    
    def test_user_context_data_protection_and_privacy(self):
        """Test user context data protection and privacy across sessions."""
        # Create multiple user sessions with different security levels
        sessions = []
        
        # Enterprise users with high security
        for user_id in self.enterprise_users:
            session = self.session_manager.create_session(
                user_id, self.enterprise_tenant, "high_security"
            )
            session.add_permission("enterprise_data_access")
            session.add_permission("financial_data_read")
            session.set_data_context("department", "finance")
            session.set_data_context("clearance_level", "confidential")
            session.set_data_context("sensitive_data", f"enterprise_secret_{user_id}")
            sessions.append(session)
        
        # Startup users with standard security
        for user_id in self.startup_users:
            session = self.session_manager.create_session(
                user_id, self.startup_tenant, "standard"
            )
            session.add_permission("basic_data_access")
            session.set_data_context("department", "engineering")
            session.set_data_context("clearance_level", "public")
            session.set_data_context("project_data", f"startup_project_{user_id}")
            sessions.append(session)
        
        # Government user with maximum security
        for user_id in self.government_users:
            session = self.session_manager.create_session(
                user_id, self.government_tenant, "maximum_security"
            )
            session.add_permission("classified_data_access")
            session.add_permission("government_operations")
            session.set_data_context("department", "defense")
            session.set_data_context("clearance_level", "top_secret")
            session.set_data_context("classified_data", f"classified_operation_{user_id}")
            sessions.append(session)
        
        # Validate context isolation
        for session in sessions:
            # Validate session belongs to correct tenant
            if session.user_id in self.enterprise_users:
                assert session.tenant_id == self.enterprise_tenant
                assert session.security_level == "high_security"
                assert session.has_permission("enterprise_data_access")
                assert session.get_data_context("clearance_level") == "confidential"
            
            elif session.user_id in self.startup_users:
                assert session.tenant_id == self.startup_tenant
                assert session.security_level == "standard"
                assert session.has_permission("basic_data_access")
                assert not session.has_permission("enterprise_data_access")
                assert session.get_data_context("clearance_level") == "public"
            
            elif session.user_id in self.government_users:
                assert session.tenant_id == self.government_tenant
                assert session.security_level == "maximum_security"
                assert session.has_permission("classified_data_access")
                assert session.get_data_context("clearance_level") == "top_secret"
        
        # Validate cross-tenant isolation
        isolation_report = self.session_manager.validate_cross_tenant_isolation()
        
        # Should have minimal or no violations
        assert isolation_report["isolation_score"] > 0.9, "High isolation score required"
        assert len(isolation_report["violations"]) == 0, "No isolation violations allowed"
        assert isolation_report["total_tenants"] == 3
        assert isolation_report["total_sessions"] == len(sessions)
    
    def test_session_data_isolation_and_management(self):
        """Test session data isolation and proper session lifecycle management."""
        # Create concurrent sessions for same users across different contexts
        user_sessions = {}
        
        # Create multiple sessions per user to test isolation
        for user_id in self.enterprise_users[:2]:  # Test with 2 enterprise users
            user_sessions[user_id] = []
            
            # Web session
            web_session = self.session_manager.create_session(
                user_id, self.enterprise_tenant, "high_security"
            )
            web_session.set_data_context("session_type", "web")
            web_session.set_data_context("active_project", f"web_project_{user_id}")
            web_session.set_data_context("temporary_data", {"calculations": [1, 2, 3, 4, 5]})
            user_sessions[user_id].append(web_session)
            
            # API session
            api_session = self.session_manager.create_session(
                user_id, self.enterprise_tenant, "high_security" 
            )
            api_session.set_data_context("session_type", "api")
            api_session.set_data_context("active_project", f"api_project_{user_id}")
            api_session.set_data_context("temporary_data", {"batch_processing": True})
            user_sessions[user_id].append(api_session)
            
            # Mobile session
            mobile_session = self.session_manager.create_session(
                user_id, self.enterprise_tenant, "standard"  # Different security level
            )
            mobile_session.set_data_context("session_type", "mobile")
            mobile_session.set_data_context("active_project", f"mobile_project_{user_id}")
            mobile_session.set_data_context("temporary_data", {"mobile_optimized": True})
            user_sessions[user_id].append(mobile_session)
        
        # Validate session isolation for each user
        for user_id, sessions in user_sessions.items():
            assert len(sessions) == 3, "Should have 3 sessions per user"
            
            # Validate each session has isolated data
            session_types = []
            active_projects = []
            temporary_data_values = []
            
            for session in sessions:
                session_type = session.get_data_context("session_type")
                active_project = session.get_data_context("active_project")
                temp_data = session.get_data_context("temporary_data")
                
                session_types.append(session_type)
                active_projects.append(active_project)
                temporary_data_values.append(temp_data)
                
                # Validate session belongs to correct user and tenant
                assert session.user_id == user_id
                assert session.tenant_id == self.enterprise_tenant
            
            # Each session should have unique data contexts
            assert len(set(session_types)) == 3, "Session types should be unique"
            assert len(set(active_projects)) == 3, "Active projects should be unique per session"
            assert len(temporary_data_values) == 3, "Temporary data should be isolated"
            
            # Validate data doesn't leak between sessions
            for i, session_a in enumerate(sessions):
                for j, session_b in enumerate(sessions):
                    if i != j:
                        # Different sessions should not share data contexts
                        assert session_a.session_id != session_b.session_id
                        assert (session_a.get_data_context("active_project") != 
                               session_b.get_data_context("active_project"))
        
        # Test session retrieval isolation
        all_user_sessions = self.session_manager.get_user_sessions(self.enterprise_users[0])
        assert len(all_user_sessions) == 3, "Should retrieve all user sessions"
        
        # Validate retrieved sessions belong to correct user
        for session in all_user_sessions:
            assert session.user_id == self.enterprise_users[0]
            assert session.tenant_id == self.enterprise_tenant
    
    @pytest.mark.asyncio
    async def test_concurrent_user_data_processing_without_contamination(self):
        """Test concurrent data processing across multiple users without data contamination."""
        # Create test scenario with concurrent users processing data
        concurrent_users = [
            f"concurrent_user_{i:03d}" for i in range(10)
        ]
        
        # Assign users to different tenants
        user_tenant_mapping = {}
        for i, user_id in enumerate(concurrent_users):
            if i < 4:
                user_tenant_mapping[user_id] = self.enterprise_tenant
            elif i < 7:
                user_tenant_mapping[user_id] = self.startup_tenant
            else:
                user_tenant_mapping[user_id] = self.government_tenant
        
        async def process_user_data(user_id: str, tenant_id: str) -> Dict[str, Any]:
            """Simulate concurrent user data processing."""
            # Create unique usage patterns for each user
            user_seed = hash(user_id) % 1000
            
            # Track usage with user-specific patterns
            api_calls = 1000 + (user_seed * 10)
            tokens = 50000 + (user_seed * 100) 
            storage = 5.0 + (user_seed * 0.1)
            
            # Process usage tracking
            events = []
            for usage_type, quantity in [
                (UsageType.API_CALL, api_calls),
                (UsageType.LLM_TOKENS, tokens),
                (UsageType.STORAGE, storage)
            ]:
                event = await self.usage_tracker.track_usage(
                    user_id=user_id,
                    usage_type=usage_type,
                    quantity=quantity,
                    unit="units",
                    metadata={
                        "tenant_id": tenant_id,
                        "processing_batch": f"batch_{user_seed}",
                        "concurrent_test": True,
                        "user_specific_data": f"data_{user_id}_{datetime.now(timezone.utc).isoformat()}"
                    }
                )
                events.append(event)
            
            # Calculate costs for user
            usage_data = {
                "api_calls": {"quantity": api_calls},
                "llm_tokens": {"quantity": tokens},
                "storage": {"quantity": storage}
            }
            
            # Determine tier based on tenant
            tier_mapping = {
                self.enterprise_tenant: "enterprise",
                self.startup_tenant: "professional", 
                self.government_tenant: "professional"
            }
            tier = tier_mapping.get(tenant_id, "starter")
            
            cost_breakdown = self.cost_calculator.calculate_cost_breakdown(
                user_id=user_id,
                usage_data=usage_data,
                tier_name=tier
            )
            
            return {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "events": events,
                "cost_breakdown": cost_breakdown,
                "processing_completed": datetime.now(timezone.utc)
            }
        
        # Execute concurrent processing
        async def run_concurrent_processing():
            tasks = []
            for user_id in concurrent_users:
                tenant_id = user_tenant_mapping[user_id]
                task = process_user_data(user_id, tenant_id)
                tasks.append(task)
            
            # Run all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        # Execute concurrent processing
        processing_results = await run_concurrent_processing()
        
        # Validate no exceptions occurred
        exceptions = [result for result in processing_results if isinstance(result, Exception)]
        assert len(exceptions) == 0, f"Concurrent processing failed with exceptions: {exceptions}"
        
        # Validate results integrity
        successful_results = [result for result in processing_results if not isinstance(result, Exception)]
        assert len(successful_results) == len(concurrent_users), "All users should have successful results"
        
        # Validate data isolation in results
        user_data_signatures = {}
        for result in successful_results:
            user_id = result["user_id"]
            tenant_id = result["tenant_id"]
            events = result["events"]
            
            # Validate user-tenant mapping
            assert tenant_id == user_tenant_mapping[user_id], "User-tenant mapping should be preserved"
            
            # Validate unique data per user
            user_signature = set()
            for event in events:
                # Each event should have unique user-specific metadata
                user_specific_data = event.metadata.get("user_specific_data", "")
                assert user_id in user_specific_data, "Event should contain user-specific data"
                
                batch_id = event.metadata.get("processing_batch", "")
                user_signature.add((event.usage_type, event.quantity, batch_id))
            
            # Store signature for cross-user validation
            user_data_signatures[user_id] = user_signature
        
        # Validate no data contamination between users
        user_ids = list(user_data_signatures.keys())
        for i, user_a in enumerate(user_ids):
            for j, user_b in enumerate(user_ids):
                if i != j:
                    sig_a = user_data_signatures[user_a]
                    sig_b = user_data_signatures[user_b]
                    
                    # Signatures should be completely unique (no overlap)
                    overlap = sig_a.intersection(sig_b)
                    assert len(overlap) == 0, f"Data contamination detected between {user_a} and {user_b}: {overlap}"
    
    @pytest.mark.asyncio
    async def test_enterprise_data_security_and_access_controls(self):
        """Test enterprise-level data security and granular access controls."""
        # Set up enterprise tenant with strict security
        enterprise_quota = TenantResourceQuota(
            tenant_id=self.enterprise_tenant,
            cpu_cores=64.0,
            memory_mb=131072,  # 128GB
            storage_gb=5000,
            max_concurrent_requests=2000,
            max_api_calls_per_hour=1000000
        )
        
        await self.tenant_isolator.register_tenant(self.enterprise_tenant, enterprise_quota)
        
        # Create enterprise users with different access levels
        enterprise_roles = {
            "admin_user": {
                "permissions": ["full_access", "user_management", "billing_access", "audit_access"],
                "security_level": "maximum_security",
                "data_classification": "all_levels"
            },
            "finance_user": {
                "permissions": ["billing_access", "cost_analysis", "financial_reporting"],
                "security_level": "high_security", 
                "data_classification": "financial_sensitive"
            },
            "developer_user": {
                "permissions": ["api_access", "development_tools", "performance_monitoring"],
                "security_level": "standard",
                "data_classification": "technical_data"
            },
            "auditor_user": {
                "permissions": ["audit_access", "read_only_access", "compliance_reporting"],
                "security_level": "high_security",
                "data_classification": "audit_logs"
            }
        }
        
        # Create sessions with role-based access
        role_sessions = {}
        for role, config in enterprise_roles.items():
            user_id = f"enterprise_{role}"
            session = self.session_manager.create_session(
                user_id, self.enterprise_tenant, config["security_level"]
            )
            
            # Add permissions
            for permission in config["permissions"]:
                session.add_permission(permission)
            
            # Set role-specific data contexts
            session.set_data_context("role", role)
            session.set_data_context("data_classification", config["data_classification"])
            session.set_data_context("department", role.split("_")[0])
            
            # Add role-specific sensitive data
            if role == "admin_user":
                session.set_data_context("admin_keys", ["master_key_001", "backup_key_002"])
                session.set_data_context("user_database_access", True)
            elif role == "finance_user":
                session.set_data_context("financial_reports", ["Q1_2024", "Q2_2024", "Q3_2024"])
                session.set_data_context("budget_access", True)
            elif role == "developer_user":
                session.set_data_context("api_keys", ["dev_key_001", "staging_key_002"])
                session.set_data_context("code_repository_access", ["main", "develop", "feature/*"])
            elif role == "auditor_user":
                session.set_data_context("audit_trails", ["security_audit", "compliance_audit"])
                session.set_data_context("readonly_database_access", True)
            
            role_sessions[role] = session
        
        # Test access control enforcement
        for role, session in role_sessions.items():
            # Validate role-based permissions
            config = enterprise_roles[role]
            
            # Check all assigned permissions exist
            for permission in config["permissions"]:
                assert session.has_permission(permission), f"{role} should have {permission}"
            
            # Check unauthorized permissions don't exist
            all_permissions = set()
            for other_config in enterprise_roles.values():
                all_permissions.update(other_config["permissions"])
            
            unauthorized_permissions = all_permissions - set(config["permissions"])
            for permission in unauthorized_permissions:
                assert not session.has_permission(permission), f"{role} should NOT have {permission}"
            
            # Validate data classification isolation
            assert session.get_data_context("data_classification") == config["data_classification"]
            assert session.get_data_context("role") == role
        
        # Test cross-role data access restrictions
        # Admin should not directly access finance-specific data contexts
        admin_session = role_sessions["admin_user"]
        finance_session = role_sessions["finance_user"]
        developer_session = role_sessions["developer_user"]
        auditor_session = role_sessions["auditor_user"]
        
        # Validate data isolation between roles
        assert admin_session.get_data_context("financial_reports") is None
        assert finance_session.get_data_context("admin_keys") is None
        assert developer_session.get_data_context("audit_trails") is None
        assert auditor_session.get_data_context("api_keys") is None
        
        # Test tenant-level resource allocation
        resource_request = {
            "cpu_cores": 32.0,
            "memory_mb": 65536,
            "concurrent_requests": 500
        }
        
        # Enterprise tenant should be able to allocate significant resources
        allocation_result = await self.tenant_isolator.check_resource_availability(
            self.enterprise_tenant, resource_request
        )
        
        assert allocation_result["allowed"] == True, "Enterprise should have sufficient resources"
        
        # Successful allocation
        allocation_success = await self.tenant_isolator.allocate_resources(
            self.enterprise_tenant, resource_request
        )
        assert allocation_success == True, "Resource allocation should succeed"
        
        # Validate tenant status after allocation
        tenant_status = await self.tenant_isolator.get_tenant_status(self.enterprise_tenant)
        utilization = tenant_status["utilization"]
        
        # Should show resource utilization
        assert utilization["cpu_percent"] > 0, "CPU utilization should be tracked"
        assert utilization["memory_percent"] > 0, "Memory utilization should be tracked"
        
        # Security policies should be enforced
        assert tenant_status["policy"]["network_isolation"] == True
        assert tenant_status["policy"]["storage_isolation"] == True
        assert tenant_status["policy"]["compute_isolation"] == True
        assert tenant_status["policy"]["strict_quota_enforcement"] == True
    
    @pytest.mark.asyncio  
    async def test_data_privacy_compliance_validation(self):
        """Test data privacy compliance and GDPR-style data protection measures."""
        # Create test users with different privacy requirements
        privacy_test_users = [
            {
                "user_id": "gdpr_user_001",
                "tenant_id": self.enterprise_tenant,
                "region": "eu",
                "privacy_level": "strict_gdpr",
                "consent_given": True,
                "data_minimization": True
            },
            {
                "user_id": "ccpa_user_002", 
                "tenant_id": self.startup_tenant,
                "region": "california",
                "privacy_level": "ccpa_compliant",
                "consent_given": True,
                "data_minimization": False
            },
            {
                "user_id": "standard_user_003",
                "tenant_id": self.startup_tenant,
                "region": "us_standard",
                "privacy_level": "standard",
                "consent_given": True,
                "data_minimization": False
            }
        ]
        
        # Process data for each privacy tier
        privacy_compliance_results = []
        
        for user_config in privacy_test_users:
            user_id = user_config["user_id"]
            tenant_id = user_config["tenant_id"]
            privacy_level = user_config["privacy_level"]
            
            # Create usage data with privacy considerations
            usage_metadata = {
                "tenant_id": tenant_id,
                "privacy_level": privacy_level,
                "region": user_config["region"],
                "consent_timestamp": datetime.now(timezone.utc).isoformat(),
                "data_purpose": "service_optimization",
                "retention_period": "90_days" if user_config["data_minimization"] else "365_days"
            }
            
            # Track usage with privacy-compliant metadata
            events = []
            usage_amounts = [(UsageType.API_CALL, 5000), (UsageType.LLM_TOKENS, 100000)]
            
            for usage_type, quantity in usage_amounts:
                event = await self.usage_tracker.track_usage(
                    user_id=user_id,
                    usage_type=usage_type,
                    quantity=quantity,
                    unit="units",
                    metadata=usage_metadata
                )
                events.append(event)
            
            # Validate privacy compliance in stored data
            compliance_check = {
                "user_id": user_id,
                "privacy_level": privacy_level,
                "events_processed": len(events),
                "compliance_violations": []
            }
            
            # Check each event for privacy compliance
            for event in events:
                event_metadata = event.metadata
                
                # GDPR compliance checks
                if privacy_level == "strict_gdpr":
                    # Should have explicit consent timestamp
                    if "consent_timestamp" not in event_metadata:
                        compliance_check["compliance_violations"].append({
                            "violation": "missing_consent_timestamp",
                            "event_id": event.timestamp.isoformat()
                        })
                    
                    # Should specify data purpose
                    if "data_purpose" not in event_metadata:
                        compliance_check["compliance_violations"].append({
                            "violation": "missing_data_purpose",
                            "event_id": event.timestamp.isoformat()
                        })
                    
                    # Should have retention period specified
                    if "retention_period" not in event_metadata:
                        compliance_check["compliance_violations"].append({
                            "violation": "missing_retention_policy",
                            "event_id": event.timestamp.isoformat()
                        })
                
                # Validate no personal identifiable information in metadata
                sensitive_keys = ["email", "phone", "address", "ssn", "personal_data"]
                for key in event_metadata.keys():
                    if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                        compliance_check["compliance_violations"].append({
                            "violation": "potential_pii_in_metadata",
                            "event_id": event.timestamp.isoformat(),
                            "suspicious_key": key
                        })
                
                # Validate user_id is properly anonymized or encrypted for high privacy levels
                if privacy_level in ["strict_gdpr", "ccpa_compliant"]:
                    if len(event.user_id) < 10 or event.user_id.startswith("test_"):
                        compliance_check["compliance_violations"].append({
                            "violation": "insufficiently_anonymized_user_id",
                            "event_id": event.timestamp.isoformat()
                        })
            
            privacy_compliance_results.append(compliance_check)
        
        # Validate overall privacy compliance
        total_violations = 0
        for result in privacy_compliance_results:
            violations = result["compliance_violations"]
            total_violations += len(violations)
            
            # High privacy users should have zero violations
            if result["privacy_level"] == "strict_gdpr":
                assert len(violations) == 0, f"GDPR user should have no violations: {violations}"
            
            # All users should have processed events
            assert result["events_processed"] > 0, "Events should be processed for all users"
        
        # Overall compliance should be high
        total_events = sum(result["events_processed"] for result in privacy_compliance_results)
        compliance_rate = 1.0 - (total_violations / total_events) if total_events > 0 else 1.0
        
        assert compliance_rate >= 0.95, f"Privacy compliance rate should be >= 95%, got {compliance_rate:.2%}"