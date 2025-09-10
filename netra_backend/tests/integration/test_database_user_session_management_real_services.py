"""
Test Database User Session Management with Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable user session persistence for business continuity
- Value Impact: Protects user login state and prevents session loss scenarios
- Strategic Impact: Core authentication infrastructure for user retention

CRITICAL COMPLIANCE:
- Uses real PostgreSQL database for session testing
- Validates multi-tenant session isolation  
- Tests session expiry and cleanup for security
- Ensures session recovery for business continuity
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.models.user_session import UserSession
from netra_backend.app.services.user_execution_context import UserExecutionContext
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.real_services_test_fixtures import E2ETestFixture


class TestDatabaseUserSessionManagementRealServices(BaseIntegrationTest):
    """Test user session management with real PostgreSQL database."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_session_creation_multi_tenant_isolation(self, real_db_fixture):
        """Test user session creation maintains multi-tenant isolation with real database."""
        # Given: Multiple users from different organizations requiring session isolation
        test_users = [
            {
                "user_id": str(uuid.uuid4()),
                "email": "ceo@enterprise-a.com",
                "organization": "enterprise-a",
                "subscription_tier": "enterprise",
                "session_data": {"role": "admin", "permissions": ["full_access"]}
            },
            {
                "user_id": str(uuid.uuid4()),
                "email": "manager@company-b.com", 
                "organization": "company-b",
                "subscription_tier": "premium",
                "session_data": {"role": "manager", "permissions": ["read_write"]}
            },
            {
                "user_id": str(uuid.uuid4()),
                "email": "user@startup-c.com",
                "organization": "startup-c", 
                "subscription_tier": "basic",
                "session_data": {"role": "user", "permissions": ["read_only"]}
            }
        ]
        
        session_manager = DatabaseSessionManager(real_db_fixture)
        created_sessions = []
        
        # When: Creating sessions for multiple users
        for user_data in test_users:
            session = await session_manager.create_user_session(
                user_id=user_data["user_id"],
                email=user_data["email"],
                organization=user_data["organization"], 
                subscription_tier=user_data["subscription_tier"],
                session_data=user_data["session_data"],
                expires_in_hours=24
            )
            
            assert session is not None
            assert session.user_id == user_data["user_id"]
            assert session.organization == user_data["organization"]
            created_sessions.append((user_data, session))
        
        # Then: Each session should be completely isolated in real database
        for i, (user_data, session) in enumerate(created_sessions):
            # Verify session can be retrieved by correct user
            retrieved_session = await session_manager.get_user_session(
                session.session_id, 
                user_data["user_id"]
            )
            
            assert retrieved_session is not None
            assert retrieved_session.user_id == user_data["user_id"]
            assert retrieved_session.organization == user_data["organization"]
            assert retrieved_session.subscription_tier == user_data["subscription_tier"]
            
            # Verify isolation - other users cannot access this session
            for j, (other_user_data, _) in enumerate(created_sessions):
                if i != j:  # Different user
                    unauthorized_session = await session_manager.get_user_session(
                        session.session_id,
                        other_user_data["user_id"] 
                    )
                    
                    # Should not be able to access other user's session
                    assert unauthorized_session is None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_expiry_cleanup_business_security(self, real_db_fixture):
        """Test session expiry and cleanup for business security with real database."""
        # Given: Sessions with different expiry requirements for business security
        session_manager = DatabaseSessionManager(real_db_fixture)
        
        expiry_scenarios = [
            {
                "user_type": "free_user",
                "expires_in_minutes": 1,  # 1 minute for testing
                "should_expire": True,
                "business_reason": "encourage_upgrade"
            },
            {
                "user_type": "premium_user",
                "expires_in_minutes": 5,  # 5 minutes for testing
                "should_expire": False,  # Won't expire in test timeframe
                "business_reason": "user_retention"
            },
            {
                "user_type": "enterprise_admin",
                "expires_in_minutes": 10,  # 10 minutes for testing
                "should_expire": False,  # Won't expire in test timeframe
                "business_reason": "productivity"
            }
        ]
        
        created_sessions = []
        
        # When: Creating sessions with different expiry times
        for scenario in expiry_scenarios:
            user_id = str(uuid.uuid4())
            
            session = await session_manager.create_user_session(
                user_id=user_id,
                email=f"{scenario['user_type']}@test.com",
                organization=f"{scenario['user_type']}_org",
                subscription_tier=scenario['user_type'].split('_')[0],  # free, premium, enterprise
                session_data={"user_type": scenario["user_type"]},
                expires_in_minutes=scenario["expires_in_minutes"]
            )
            
            created_sessions.append((scenario, session, user_id))
        
        # Wait for short sessions to expire
        await asyncio.sleep(65)  # Wait 65 seconds
        
        # Then: Sessions should expire according to business rules
        for scenario, session, user_id in created_sessions:
            retrieved_session = await session_manager.get_user_session(
                session.session_id, 
                user_id
            )
            
            if scenario["should_expire"]:
                # Short-lived sessions should have expired
                assert retrieved_session is None, f"{scenario['user_type']} session should have expired"
            else:
                # Longer sessions should still be valid
                assert retrieved_session is not None, f"{scenario['user_type']} session should still be valid"
                assert retrieved_session.user_id == user_id
        
        # Clean up remaining sessions
        await session_manager.cleanup_expired_sessions()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_session_management_business_scalability(self, real_db_fixture):
        """Test concurrent session management for business scalability with real database."""
        # Given: High concurrency scenario simulating business peak load
        session_manager = DatabaseSessionManager(real_db_fixture)
        
        num_concurrent_users = 20  # Simulate moderate concurrent load
        concurrent_operations = []
        
        async def create_and_manage_user_session(user_index):
            """Create and manage a user session concurrently."""
            user_id = str(uuid.uuid4())
            email = f"concurrent-user-{user_index}@business.com"
            organization = f"business-org-{user_index % 5}"  # 5 different organizations
            
            try:
                # Create session
                session = await session_manager.create_user_session(
                    user_id=user_id,
                    email=email,
                    organization=organization,
                    subscription_tier="premium",
                    session_data={
                        "user_index": user_index,
                        "concurrent_test": True,
                        "creation_time": datetime.now(timezone.utc).isoformat()
                    },
                    expires_in_hours=2
                )
                
                # Verify immediate retrieval
                retrieved = await session_manager.get_user_session(session.session_id, user_id)
                assert retrieved is not None
                assert retrieved.user_id == user_id
                
                # Update session data
                await session_manager.update_session_data(
                    session.session_id,
                    user_id,
                    {"last_activity": datetime.now(timezone.utc).isoformat()}
                )
                
                # Final verification
                final_session = await session_manager.get_user_session(session.session_id, user_id)
                assert final_session is not None
                assert "last_activity" in final_session.session_data
                
                return {
                    "user_index": user_index,
                    "success": True,
                    "session_id": session.session_id,
                    "operations_completed": 3
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "success": False,
                    "error": str(e),
                    "operations_completed": 0
                }
        
        # When: Running concurrent session operations
        results = await asyncio.gather(
            *[create_and_manage_user_session(i) for i in range(num_concurrent_users)],
            return_exceptions=True
        )
        
        # Then: All concurrent operations should succeed with real database
        successful_operations = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_operations = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        # Should handle concurrent load successfully
        assert len(successful_operations) == num_concurrent_users
        assert len(failed_operations) == 0
        
        # Verify data integrity across concurrent operations
        for result in successful_operations:
            assert result["operations_completed"] == 3
            assert result["session_id"] is not None
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_recovery_business_continuity(self, real_db_fixture):
        """Test session recovery for business continuity with real database."""
        # Given: Business scenario requiring session recovery after system restart
        session_manager = DatabaseSessionManager(real_db_fixture)
        
        # Create enterprise user session with important business state
        enterprise_user_id = str(uuid.uuid4())
        business_session_data = {
            "active_analysis": {
                "type": "cost_optimization",
                "aws_account_id": "123456789012",
                "monthly_spend": 50000.00,
                "optimization_progress": 0.75
            },
            "user_preferences": {
                "dashboard_layout": "executive",
                "notification_settings": {"email": True, "slack": True},
                "timezone": "America/New_York"
            },
            "recent_activities": [
                {"action": "viewed_cost_dashboard", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"action": "ran_security_audit", "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()}
            ]
        }
        
        original_session = await session_manager.create_user_session(
            user_id=enterprise_user_id,
            email="cto@enterprise.com",
            organization="enterprise-corp",
            subscription_tier="enterprise",
            session_data=business_session_data,
            expires_in_hours=8  # Full business day
        )
        
        original_session_id = original_session.session_id
        
        # Simulate system restart by creating new session manager instance
        new_session_manager = DatabaseSessionManager(real_db_fixture)
        
        # When: Recovering session after system restart
        recovered_session = await new_session_manager.get_user_session(
            original_session_id,
            enterprise_user_id
        )
        
        # Then: Should recover complete business state from real database
        assert recovered_session is not None
        assert recovered_session.user_id == enterprise_user_id
        assert recovered_session.email == "cto@enterprise.com"
        assert recovered_session.organization == "enterprise-corp"
        assert recovered_session.subscription_tier == "enterprise"
        
        # Verify business data integrity
        session_data = recovered_session.session_data
        assert "active_analysis" in session_data
        assert session_data["active_analysis"]["type"] == "cost_optimization"
        assert session_data["active_analysis"]["monthly_spend"] == 50000.00
        assert session_data["active_analysis"]["optimization_progress"] == 0.75
        
        assert "user_preferences" in session_data
        assert session_data["user_preferences"]["dashboard_layout"] == "executive"
        
        assert "recent_activities" in session_data
        assert len(session_data["recent_activities"]) == 2
        assert session_data["recent_activities"][0]["action"] == "viewed_cost_dashboard"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_data_integrity_business_operations(self, real_db_fixture):
        """Test session data integrity during business operations with real database."""
        # Given: Business operations that modify session state
        session_manager = DatabaseSessionManager(real_db_fixture)
        
        user_id = str(uuid.uuid4())
        session = await session_manager.create_user_session(
            user_id=user_id,
            email="analyst@business.com",
            organization="business-corp",
            subscription_tier="premium",
            session_data={
                "workspace": {
                    "active_projects": [],
                    "recent_analyses": [],
                    "saved_queries": []
                }
            },
            expires_in_hours=4
        )
        
        # Business operations that modify session state
        business_operations = [
            {
                "operation": "start_cost_analysis",
                "data_update": {
                    "workspace.active_projects": [{
                        "id": str(uuid.uuid4()),
                        "type": "cost_analysis",
                        "status": "in_progress",
                        "started_at": datetime.now(timezone.utc).isoformat()
                    }]
                }
            },
            {
                "operation": "save_query",
                "data_update": {
                    "workspace.saved_queries": [{
                        "id": str(uuid.uuid4()),
                        "name": "High Cost Resources",
                        "query": "SELECT * FROM resources WHERE monthly_cost > 1000",
                        "saved_at": datetime.now(timezone.utc).isoformat()
                    }]
                }
            },
            {
                "operation": "complete_analysis", 
                "data_update": {
                    "workspace.recent_analyses": [{
                        "id": str(uuid.uuid4()),
                        "type": "cost_optimization",
                        "result": {"potential_savings": 15000.00},
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }]
                }
            }
        ]
        
        # When: Performing business operations that modify session state
        for operation in business_operations:
            # Update session data atomically
            current_session = await session_manager.get_user_session(session.session_id, user_id)
            updated_data = current_session.session_data.copy()
            
            for key, value in operation["data_update"].items():
                if "." in key:  # Nested key
                    parts = key.split(".")
                    nested_data = updated_data
                    for part in parts[:-1]:
                        nested_data = nested_data.setdefault(part, {})
                    nested_data[parts[-1]] = value
                else:
                    updated_data[key] = value
            
            await session_manager.update_session_data(
                session.session_id,
                user_id,
                updated_data
            )
            
            # Verify data integrity after each operation
            verified_session = await session_manager.get_user_session(session.session_id, user_id)
            assert verified_session is not None
            
            # Verify specific business data was saved correctly
            if operation["operation"] == "start_cost_analysis":
                assert "active_projects" in verified_session.session_data["workspace"]
                assert len(verified_session.session_data["workspace"]["active_projects"]) == 1
                assert verified_session.session_data["workspace"]["active_projects"][0]["type"] == "cost_analysis"
            
            elif operation["operation"] == "save_query":
                assert "saved_queries" in verified_session.session_data["workspace"]
                assert len(verified_session.session_data["workspace"]["saved_queries"]) == 1
                assert verified_session.session_data["workspace"]["saved_queries"][0]["name"] == "High Cost Resources"
            
            elif operation["operation"] == "complete_analysis":
                assert "recent_analyses" in verified_session.session_data["workspace"]
                assert len(verified_session.session_data["workspace"]["recent_analyses"]) == 1
                assert verified_session.session_data["workspace"]["recent_analyses"][0]["result"]["potential_savings"] == 15000.00
        
        # Then: Final session should contain all business operations data
        final_session = await session_manager.get_user_session(session.session_id, user_id)
        workspace = final_session.session_data["workspace"]
        
        assert len(workspace["active_projects"]) == 1
        assert len(workspace["saved_queries"]) == 1  
        assert len(workspace["recent_analyses"]) == 1
        
        # Verify business data integrity
        assert workspace["active_projects"][0]["status"] == "in_progress"
        assert workspace["saved_queries"][0]["query"].startswith("SELECT")
        assert workspace["recent_analyses"][0]["result"]["potential_savings"] == 15000.00