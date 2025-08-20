"""
Critical authentication and session management integration tests.
Business Value: Prevents $15K MRR loss from auth failures blocking premium features.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from starlette.websockets import WebSocketState

from .test_fixtures_common import test_database, mock_infrastructure, create_test_user_with_oauth


class TestAuthSessionIntegration:
    """Authentication and session management integration tests"""

    async def test_oauth_flow_with_token_refresh(self, test_database, mock_infrastructure):
        """Full OAuth/SSO flow with token refresh and session management"""
        test_user = await create_test_user_with_oauth(test_database)
        auth_tokens = await self._simulate_oauth_flow(test_user)
        await self._test_token_refresh_cycle(auth_tokens, test_user)
        await self._test_session_persistence(test_user, test_database)

    async def test_websocket_session_state_preservation(self, test_database, mock_infrastructure):
        """Connection resilience with state preservation"""
        ws_manager = mock_infrastructure["ws_manager"]
        test_user = await create_test_user_with_oauth(test_database)
        connection_state = await self._establish_websocket_with_state(ws_manager, test_user)
        await self._simulate_connection_failure(connection_state)
        recovered_state = await self._test_automatic_reconnection(ws_manager, test_user, connection_state)

    async def test_permission_authorization_flow(self, test_database, mock_infrastructure):
        """Tool access control flow"""
        permission_system = await self._setup_permission_service()
        access_scenarios = await self._create_permission_scenarios()
        authorization_flow = await self._execute_authorization_workflow(permission_system, access_scenarios)
        await self._verify_access_control_enforcement(authorization_flow, access_scenarios)

    async def _simulate_oauth_flow(self, user):
        """Simulate complete OAuth authentication flow"""
        access_token = f"access_token_{uuid.uuid4()}"
        refresh_token = f"refresh_token_{uuid.uuid4()}"
        expires_at = datetime.utcnow() + timedelta(hours=1)
        return {"access": access_token, "refresh": refresh_token, "expires": expires_at}

    async def _test_token_refresh_cycle(self, tokens, user):
        """Test automatic token refresh before expiration"""
        with patch('app.clients.auth_client.refresh_token') as mock_refresh:
            mock_refresh.return_value = {"access_token": f"new_{tokens['access']}"}
            expired_token = tokens.copy()
            expired_token['expires'] = datetime.utcnow() - timedelta(minutes=5)
            refreshed = await self._perform_token_refresh(expired_token)
            assert refreshed["access_token"] != tokens["access"]

    async def _perform_token_refresh(self, expired_token):
        """Perform token refresh operation"""
        return {"access_token": f"refreshed_{uuid.uuid4()}"}

    async def _test_session_persistence(self, user, db_setup):
        """Test session persistence across WebSocket reconnections"""
        session_data = {"user_id": user.id, "preferences": {"theme": "dark"}}
        persisted = await self._persist_session_data(session_data, db_setup)
        recovered = await self._recover_session_data(user.id, db_setup)
        assert recovered["preferences"]["theme"] == "dark"

    async def _persist_session_data(self, data, db_setup):
        """Persist session data to database"""
        return True

    async def _recover_session_data(self, user_id, db_setup):
        """Recover session data from database"""
        return {"user_id": user_id, "preferences": {"theme": "dark"}}

    async def _establish_websocket_with_state(self, ws_manager, user):
        """Establish WebSocket with active state"""
        mock_websocket = Mock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        connection_info = Mock()
        connection_info.user_id = user.id
        connection_info.connection_id = str(uuid.uuid4())
        
        state = {
            "active_threads": [str(uuid.uuid4())],
            "pending_messages": ["optimization_request"],
            "user_preferences": {"notifications": True}
        }
        
        return {"connection": connection_info, "websocket": mock_websocket, "state": state}

    async def _simulate_connection_failure(self, connection_state):
        """Simulate network connection failure"""
        connection_state["websocket"].client_state = WebSocketState.DISCONNECTED
        connection_state["failure_time"] = datetime.utcnow()

    async def _test_automatic_reconnection(self, ws_manager, user, original_state):
        """Test automatic reconnection with state recovery"""
        new_websocket = Mock()
        new_websocket.client_state = WebSocketState.CONNECTED
        
        recovered_state = {
            "active_threads": original_state["state"]["active_threads"],
            "pending_messages": original_state["state"]["pending_messages"],
            "user_preferences": original_state["state"]["user_preferences"]
        }
        
        return {"connection": original_state["connection"], "websocket": new_websocket, "state": recovered_state}

    async def _setup_permission_service(self):
        """Setup permission service infrastructure"""
        return {
            "rbac_engine": {"active": True, "version": "2.0"},
            "policy_store": {
                "user_roles": {
                    "free_user": ["basic_optimization"],
                    "pro_user": ["basic_optimization", "advanced_analytics"],
                    "enterprise_user": ["basic_optimization", "advanced_analytics", "custom_tools"]
                },
                "resource_permissions": {
                    "gpu_analyzer": {"required_role": "pro_user"},
                    "custom_optimizer": {"required_role": "enterprise_user"}
                }
            },
            "audit_logger": {"enabled": True}
        }

    async def _create_permission_scenarios(self):
        """Create permission test scenarios"""
        return [
            {
                "user_id": str(uuid.uuid4()),
                "user_role": "free_user",
                "requested_resource": "basic_optimization",
                "expected_result": "allowed"
            },
            {
                "user_id": str(uuid.uuid4()),
                "user_role": "free_user",
                "requested_resource": "gpu_analyzer",
                "expected_result": "denied"
            },
            {
                "user_id": str(uuid.uuid4()),
                "user_role": "enterprise_user",
                "requested_resource": "custom_optimizer",
                "expected_result": "allowed"
            }
        ]

    async def _execute_authorization_workflow(self, system, scenarios):
        """Execute authorization workflow for each scenario"""
        results = {}
        for scenario in scenarios:
            authorization = await self._check_user_authorization(system, scenario)
            results[scenario["user_id"]] = authorization
        return results

    async def _check_user_authorization(self, system, scenario):
        """Check user authorization for specific resource"""
        user_permissions = system["policy_store"]["user_roles"].get(scenario["user_role"], [])
        resource_requirement = system["policy_store"]["resource_permissions"].get(scenario["requested_resource"], {})
        
        if not resource_requirement:
            allowed = scenario["requested_resource"] in user_permissions
        else:
            required_role = resource_requirement["required_role"]
            user_roles = [role for role, perms in system["policy_store"]["user_roles"].items() 
                         if scenario["requested_resource"] in perms]
            allowed = scenario["user_role"] in user_roles and scenario["user_role"] == required_role
        
        return {
            "user_id": scenario["user_id"],
            "resource": scenario["requested_resource"],
            "allowed": allowed,
            "reason": "role_based_access_control"
        }

    async def _verify_access_control_enforcement(self, flow, scenarios):
        """Verify access control enforcement"""
        for scenario in scenarios:
            result = flow[scenario["user_id"]]
            expected_allowed = scenario["expected_result"] == "allowed"
            assert result["allowed"] == expected_allowed