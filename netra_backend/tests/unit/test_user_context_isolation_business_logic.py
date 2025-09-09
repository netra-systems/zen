"""
Test User Context Isolation Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure complete user data isolation for multi-tenant security
- Value Impact: Protects customer data and enables enterprise-grade privacy
- Strategic Impact: Core security foundation for B2B customer trust and compliance

CRITICAL COMPLIANCE:
- Tests factory-based user isolation patterns
- Validates session boundary enforcement
- Ensures thread-level data separation
- Tests permission-based access control isolation
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.user_context_factory import UserContextFactory
from netra_backend.app.services.session_isolation_manager import SessionIsolationManager
from test_framework.mock_factory import MockFactory


class TestUserContextIsolationBusinessLogic:
    """Test user context isolation business logic patterns."""
    
    @pytest.fixture
    def user_context_factory(self):
        """Create user context factory for testing."""
        return UserContextFactory()
    
    @pytest.fixture
    def session_isolation_manager(self):
        """Create session isolation manager for testing."""
        return SessionIsolationManager()
    
    @pytest.fixture
    def sample_users(self):
        """Create sample users for multi-tenant testing."""
        return [
            {
                "user_id": str(uuid.uuid4()),
                "email": "tenant1@company-a.com",
                "organization": "company-a", 
                "subscription_tier": "enterprise",
                "permissions": ["read_data", "execute_agents", "admin_access"],
                "data_classification": "confidential"
            },
            {
                "user_id": str(uuid.uuid4()),
                "email": "tenant2@company-b.com", 
                "organization": "company-b",
                "subscription_tier": "premium",
                "permissions": ["read_data", "execute_agents"],
                "data_classification": "internal"
            },
            {
                "user_id": str(uuid.uuid4()),
                "email": "tenant3@startup-c.com",
                "organization": "startup-c", 
                "subscription_tier": "basic",
                "permissions": ["read_basic"],
                "data_classification": "public"
            }
        ]
    
    @pytest.mark.unit
    def test_user_context_factory_isolation_boundaries(self, user_context_factory, sample_users):
        """Test user context factory creates proper isolation boundaries."""
        # Given: Multiple enterprise users requiring strict isolation
        user_contexts = []
        
        for user_data in sample_users:
            # When: Creating isolated user contexts
            context = user_context_factory.create_isolated_context(
                user_id=user_data["user_id"],
                email=user_data["email"],
                organization=user_data["organization"],
                permissions=user_data["permissions"],
                subscription_tier=user_data["subscription_tier"],
                thread_id=str(uuid.uuid4())
            )
            
            user_contexts.append((user_data, context))
        
        # Then: Each context should be completely isolated
        for i, (user_data, context) in enumerate(user_contexts):
            assert context.user_id == user_data["user_id"]
            assert context.email == user_data["email"]
            assert context.organization == user_data["organization"]
            assert context.permissions == user_data["permissions"]
            
            # Verify isolation from other users
            for j, (other_user_data, other_context) in enumerate(user_contexts):
                if i != j:  # Different users
                    assert context.user_id != other_context.user_id
                    assert context.email != other_context.email
                    assert context.organization != other_context.organization
                    assert context.thread_id != other_context.thread_id
                    
                    # Data should never leak between contexts
                    assert not context.has_access_to_user_data(other_context.user_id)
                    assert not other_context.has_access_to_user_data(context.user_id)
    
    @pytest.mark.unit
    def test_session_boundary_enforcement_business_security(self, session_isolation_manager, sample_users):
        """Test session boundary enforcement protects business data."""
        # Given: Multiple active user sessions with sensitive business data
        active_sessions = {}
        
        for user_data in sample_users:
            session_id = str(uuid.uuid4())
            
            # Create session with business-sensitive data
            session_data = {
                "user_id": user_data["user_id"],
                "organization": user_data["organization"],
                "active_analyses": [
                    {"type": "cost_optimization", "aws_account_id": f"123456789{len(active_sessions)}"},
                    {"type": "security_scan", "resource_count": 1000 + len(active_sessions) * 100}
                ],
                "data_classification": user_data["data_classification"],
                "session_metadata": {
                    "created_at": datetime.now(timezone.utc),
                    "last_activity": datetime.now(timezone.utc),
                    "ip_address": f"192.168.1.{10 + len(active_sessions)}"
                }
            }
            
            session_isolation_manager.create_isolated_session(session_id, session_data)
            active_sessions[session_id] = (user_data, session_data)
        
        # When: Testing session boundary enforcement
        for session_id, (user_data, session_data) in active_sessions.items():
            # Then: User should only access their own session data
            retrieved_session = session_isolation_manager.get_user_session(session_id, user_data["user_id"])
            assert retrieved_session is not None
            assert retrieved_session["user_id"] == user_data["user_id"]
            assert retrieved_session["organization"] == user_data["organization"]
            
            # Verify business data isolation
            user_analyses = retrieved_session["active_analyses"]
            assert len(user_analyses) == 2
            
            for analysis in user_analyses:
                # Each user should have unique business identifiers
                if analysis["type"] == "cost_optimization":
                    aws_account = analysis["aws_account_id"]
                    assert user_data["user_id"] in str(aws_account) or aws_account.startswith("123456789")
            
            # Should not be able to access other users' sessions
            for other_session_id, (other_user_data, _) in active_sessions.items():
                if session_id != other_session_id:
                    unauthorized_access = session_isolation_manager.get_user_session(
                        other_session_id, user_data["user_id"]
                    )
                    assert unauthorized_access is None  # Should be blocked
    
    @pytest.mark.unit
    def test_thread_level_data_separation_multi_conversation(self, user_context_factory):
        """Test thread-level data separation for multi-conversation isolation."""
        # Given: Single user with multiple concurrent conversations (threads)
        user_id = str(uuid.uuid4())
        email = "multithread@enterprise.com"
        organization = "enterprise-corp"
        
        # User has multiple business conversations running simultaneously
        business_threads = [
            {
                "thread_id": str(uuid.uuid4()),
                "conversation_type": "cost_optimization",
                "aws_accounts": ["123456789001", "123456789002"],
                "confidential_data": {"monthly_spend": 85000.00, "optimization_target": 20000.00}
            },
            {
                "thread_id": str(uuid.uuid4()),
                "conversation_type": "security_analysis", 
                "security_scope": ["production", "staging"],
                "confidential_data": {"vulnerability_count": 12, "critical_issues": 3}
            },
            {
                "thread_id": str(uuid.uuid4()),
                "conversation_type": "compliance_audit",
                "audit_scope": ["SOC2", "GDPR", "HIPAA"],
                "confidential_data": {"compliance_score": 0.89, "remediation_needed": 5}
            }
        ]
        
        # When: Creating isolated contexts for each thread
        thread_contexts = []
        for thread_data in business_threads:
            context = user_context_factory.create_isolated_context(
                user_id=user_id,
                email=email,
                organization=organization,
                thread_id=thread_data["thread_id"],
                permissions=["read_data", "execute_agents", "admin_access"],
                thread_metadata=thread_data["confidential_data"]
            )
            thread_contexts.append((thread_data, context))
        
        # Then: Each thread should have completely isolated data
        for i, (thread_data, context) in enumerate(thread_contexts):
            assert context.user_id == user_id  # Same user
            assert context.thread_id == thread_data["thread_id"]  # Different threads
            
            # Thread-specific data should be isolated
            thread_metadata = context.get_thread_metadata()
            if thread_data["conversation_type"] == "cost_optimization":
                assert "monthly_spend" in thread_metadata
                assert thread_metadata["monthly_spend"] == 85000.00
                # Should not contain security or compliance data
                assert "vulnerability_count" not in thread_metadata
                assert "compliance_score" not in thread_metadata
            
            elif thread_data["conversation_type"] == "security_analysis":
                assert "vulnerability_count" in thread_metadata
                assert thread_metadata["vulnerability_count"] == 12
                # Should not contain cost or compliance data
                assert "monthly_spend" not in thread_metadata
                assert "compliance_score" not in thread_metadata
            
            elif thread_data["conversation_type"] == "compliance_audit":
                assert "compliance_score" in thread_metadata
                assert thread_metadata["compliance_score"] == 0.89
                # Should not contain cost or security data
                assert "monthly_spend" not in thread_metadata
                assert "vulnerability_count" not in thread_metadata
            
            # Verify cross-thread isolation
            for j, (other_thread_data, other_context) in enumerate(thread_contexts):
                if i != j:
                    assert context.thread_id != other_context.thread_id
                    assert not context.can_access_thread_data(other_context.thread_id)
    
    @pytest.mark.unit
    def test_permission_based_access_control_isolation(self, user_context_factory):
        """Test permission-based access control maintains proper isolation."""
        # Given: Users with different permission levels accessing same organization
        organization = "shared-enterprise-corp"
        organization_data = {
            "public_data": {"company_name": "Shared Enterprise Corp", "industry": "Technology"},
            "internal_data": {"employee_count": 500, "office_locations": ["NYC", "SF", "Austin"]},
            "confidential_data": {"revenue": 50000000, "profit_margin": 0.15},
            "restricted_data": {"api_keys": ["secret-key-1", "secret-key-2"], "database_credentials": "encrypted"}
        }
        
        permission_scenarios = [
            {
                "user_type": "viewer",
                "user_id": str(uuid.uuid4()),
                "permissions": ["read_basic"],
                "can_access": ["public_data"],
                "cannot_access": ["internal_data", "confidential_data", "restricted_data"]
            },
            {
                "user_type": "analyst", 
                "user_id": str(uuid.uuid4()),
                "permissions": ["read_basic", "read_internal"],
                "can_access": ["public_data", "internal_data"],
                "cannot_access": ["confidential_data", "restricted_data"]
            },
            {
                "user_type": "manager",
                "user_id": str(uuid.uuid4()),
                "permissions": ["read_basic", "read_internal", "read_confidential"],
                "can_access": ["public_data", "internal_data", "confidential_data"],
                "cannot_access": ["restricted_data"]
            },
            {
                "user_type": "admin",
                "user_id": str(uuid.uuid4()),
                "permissions": ["read_basic", "read_internal", "read_confidential", "admin_access"],
                "can_access": ["public_data", "internal_data", "confidential_data", "restricted_data"],
                "cannot_access": []
            }
        ]
        
        # When: Creating contexts with different permission levels
        for scenario in permission_scenarios:
            context = user_context_factory.create_isolated_context(
                user_id=scenario["user_id"],
                email=f"{scenario['user_type']}@{organization.replace('-', '')}.com",
                organization=organization,
                permissions=scenario["permissions"],
                thread_id=str(uuid.uuid4())
            )
            
            # Then: Should enforce permission-based access control
            for data_type, data_content in organization_data.items():
                can_access = data_type in scenario["can_access"]
                cannot_access = data_type in scenario["cannot_access"]
                
                if can_access:
                    # Should be able to access permitted data
                    access_result = context.check_data_access_permission(data_type)
                    assert access_result is True
                    
                    # Should be able to retrieve data
                    retrieved_data = context.get_authorized_data(data_type, data_content)
                    assert retrieved_data is not None
                    
                elif cannot_access:
                    # Should be blocked from restricted data
                    access_result = context.check_data_access_permission(data_type)
                    assert access_result is False
                    
                    # Should not be able to retrieve restricted data
                    retrieved_data = context.get_authorized_data(data_type, data_content)
                    assert retrieved_data is None
    
    @pytest.mark.unit
    def test_user_context_memory_isolation_security(self, user_context_factory):
        """Test user context memory isolation prevents data leakage."""
        # Given: Users with sensitive data that must not leak between contexts
        sensitive_users = [
            {
                "user_id": str(uuid.uuid4()),
                "organization": "bank-corp",
                "sensitive_data": {
                    "account_numbers": ["****1234", "****5678"],
                    "transaction_amounts": [150000.00, 275000.00],
                    "customer_pii": {"ssn": "***-**-1234", "account_balance": 500000.00}
                }
            },
            {
                "user_id": str(uuid.uuid4()),
                "organization": "healthcare-corp", 
                "sensitive_data": {
                    "patient_records": ["patient-001", "patient-002"],
                    "diagnoses": ["diabetes", "hypertension"],
                    "phi_data": {"mrn": "MRN-98765", "dob": "1980-01-01"}
                }
            },
            {
                "user_id": str(uuid.uuid4()),
                "organization": "defense-corp",
                "sensitive_data": {
                    "clearance_levels": ["SECRET", "TOP_SECRET"],
                    "project_codes": ["PROJECT-ALPHA", "PROJECT-BETA"],
                    "classified_data": {"access_level": "TS/SCI", "compartment": "CRYPTO"}
                }
            }
        ]
        
        # When: Creating contexts and storing sensitive data
        user_contexts = []
        for user_data in sensitive_users:
            context = user_context_factory.create_isolated_context(
                user_id=user_data["user_id"],
                email=f"user@{user_data['organization']}.com",
                organization=user_data["organization"],
                permissions=["read_confidential", "admin_access"],
                thread_id=str(uuid.uuid4())
            )
            
            # Store sensitive data in isolated context
            context.store_sensitive_data(user_data["sensitive_data"])
            user_contexts.append((user_data, context))
        
        # Then: Sensitive data should be completely isolated
        for i, (user_data, context) in enumerate(user_contexts):
            # Should be able to access own sensitive data
            own_sensitive_data = context.get_sensitive_data()
            assert own_sensitive_data is not None
            
            # Verify own data is correct
            if user_data["organization"] == "bank-corp":
                assert "account_numbers" in own_sensitive_data
                assert "****1234" in own_sensitive_data["account_numbers"]
                # Should not contain healthcare or defense data
                assert "patient_records" not in own_sensitive_data
                assert "clearance_levels" not in own_sensitive_data
            
            elif user_data["organization"] == "healthcare-corp":
                assert "patient_records" in own_sensitive_data
                assert "patient-001" in own_sensitive_data["patient_records"]
                # Should not contain banking or defense data
                assert "account_numbers" not in own_sensitive_data
                assert "clearance_levels" not in own_sensitive_data
            
            elif user_data["organization"] == "defense-corp":
                assert "clearance_levels" in own_sensitive_data
                assert "SECRET" in own_sensitive_data["clearance_levels"]
                # Should not contain banking or healthcare data
                assert "account_numbers" not in own_sensitive_data
                assert "patient_records" not in own_sensitive_data
            
            # Verify memory isolation - should not be able to access other users' data
            for j, (other_user_data, other_context) in enumerate(user_contexts):
                if i != j:
                    # Direct access should be blocked
                    other_sensitive_data = context.attempt_cross_user_access(other_context.user_id)
                    assert other_sensitive_data is None
                    
                    # Context should not contain references to other users' data
                    context_memory = context.get_memory_references()
                    other_user_identifiers = [
                        other_user_data["user_id"], 
                        other_user_data["organization"]
                    ]
                    
                    for identifier in other_user_identifiers:
                        assert identifier not in str(context_memory)
    
    @pytest.mark.unit
    def test_concurrent_user_context_isolation_thread_safety(self, user_context_factory):
        """Test concurrent user context operations maintain isolation thread safety."""
        import threading
        import time
        
        # Given: Multiple threads creating and accessing user contexts simultaneously
        num_concurrent_users = 10
        operations_per_user = 5
        
        context_creation_results = []
        data_isolation_results = []
        thread_safety_lock = threading.Lock()
        
        def create_and_test_user_context(user_index):
            """Create user context and test isolation in concurrent environment."""
            user_id = str(uuid.uuid4())
            email = f"concurrent-user-{user_index}@test.com"
            organization = f"org-{user_index}"
            
            try:
                for operation_index in range(operations_per_user):
                    # Create isolated context
                    context = user_context_factory.create_isolated_context(
                        user_id=user_id,
                        email=email,
                        organization=organization,
                        permissions=["read_data", "execute_agents"],
                        thread_id=str(uuid.uuid4())
                    )
                    
                    # Store user-specific data
                    user_specific_data = {
                        "user_index": user_index,
                        "operation_index": operation_index,
                        "creation_time": time.time(),
                        "sensitive_value": f"secret-{user_index}-{operation_index}"
                    }
                    context.store_user_data(user_specific_data)
                    
                    # Verify data isolation
                    retrieved_data = context.get_user_data()
                    assert retrieved_data["user_index"] == user_index
                    assert retrieved_data["operation_index"] == operation_index
                    assert retrieved_data["sensitive_value"] == f"secret-{user_index}-{operation_index}"
                    
                    with thread_safety_lock:
                        context_creation_results.append((user_index, operation_index, "success"))
                        data_isolation_results.append((user_index, retrieved_data))
                
            except Exception as e:
                with thread_safety_lock:
                    context_creation_results.append((user_index, -1, f"failed: {e}"))
        
        # When: Running concurrent context operations
        threads = []
        for user_index in range(num_concurrent_users):
            thread = threading.Thread(target=create_and_test_user_context, args=(user_index,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Then: All operations should succeed with proper isolation
        assert len(context_creation_results) == num_concurrent_users * operations_per_user
        
        # Verify all operations succeeded
        successful_operations = [result for result in context_creation_results if result[2] == "success"]
        assert len(successful_operations) == num_concurrent_users * operations_per_user
        
        # Verify data isolation was maintained across threads
        assert len(data_isolation_results) == num_concurrent_users * operations_per_user
        
        for user_index, user_data in data_isolation_results:
            assert user_data["user_index"] == user_index
            assert user_data["sensitive_value"].startswith(f"secret-{user_index}-")
            
            # Should not contain data from other users
            for other_user_index in range(num_concurrent_users):
                if other_user_index != user_index:
                    assert f"secret-{other_user_index}-" not in user_data["sensitive_value"]