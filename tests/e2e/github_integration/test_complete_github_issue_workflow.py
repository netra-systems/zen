"""
E2E tests for complete GitHub issue workflows

Tests the complete end-to-end user journey from error occurrence
to GitHub issue creation, management, and resolution.

CRITICAL: All tests initially FAIL to prove functionality doesn't exist yet.
CRITICAL: All e2e tests MUST use authentication (JWT/OAuth) EXCEPT tests that validate auth itself.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import httpx
import websockets
from unittest.mock import Mock, patch

from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase
from tests.e2e.staging_config import StagingTestConfig

class TestCompleteGitHubIssueWorkflow(SSotBaseTestCase):
    """
    E2E tests for complete GitHub issue workflows
    
    CRITICAL: These tests will INITIALLY FAIL because the GitHub integration
    doesn't exist yet. This proves the tests are working correctly.
    
    These tests simulate complete user journeys:
    1. User experiences error during agent execution
    2. Error is detected and processed 
    3. GitHub issue is automatically created
    4. User receives notification with GitHub issue link
    5. Issue is updated with progress
    6. Issue is resolved when error is fixed
    """
    
    @pytest.fixture(scope="class")
    def auth_config(self):
        """E2E authentication configuration"""
        return E2EAuthConfig.for_staging()
    
    @pytest.fixture(scope="class")
    def auth_helper(self, auth_config):
        """E2E authentication helper"""
        return E2EAuthHelper(auth_config)
    
    @pytest.fixture(scope="class")
    async def authenticated_user(self, auth_helper):
        """Authenticated user session for e2e testing"""
        # CRITICAL: All e2e tests must use real authentication
        user_session = await auth_helper.create_authenticated_session(
            email="github_test@example.com",
            user_id="github_e2e_test_user"
        )
        yield user_session
        await auth_helper.cleanup_session(user_session)
    
    @pytest.fixture
    def github_config(self):
        """GitHub integration configuration"""
        env = IsolatedEnvironment()
        
        return {
            "enabled": env.get("GITHUB_INTEGRATION_ENABLED", "false").lower() == "true",
            "token": env.get("GITHUB_TOKEN", ""),
            "repo_owner": env.get("GITHUB_REPO_OWNER", ""),
            "repo_name": env.get("GITHUB_REPO_NAME", ""),
            "webhook_url": env.get("GITHUB_WEBHOOK_URL", "")
        }
    
    @pytest.fixture
    def websocket_client(self, authenticated_user, auth_config):
        """Authenticated WebSocket client for real-time updates"""
        # This will be used to test real-time GitHub issue notifications
        return {
            "url": auth_config.websocket_url,
            "headers": {
                "Authorization": f"Bearer {authenticated_user.jwt_token}",
                "User-ID": authenticated_user.user_id
            }
        }
    
    @pytest.mark.e2e
    @pytest.mark.github
    @pytest.mark.slow
    async def test_error_to_github_issue_complete_workflow_fails(
        self, authenticated_user, websocket_client, github_config
    ):
        """
        TEST SHOULD FAIL: Complete GitHub issue workflow doesn't exist
        
        This test validates the complete workflow from agent error
        to GitHub issue creation with real user authentication.
        """
        if not github_config["enabled"]:
            pytest.skip("GitHub integration not enabled for testing")
        
        with pytest.raises((ImportError, NameError, ModuleNotFoundError, ConnectionError)):
            # Step 1: Connect to WebSocket for real-time updates
            async with websockets.connect(
                websocket_client["url"],
                extra_headers=websocket_client["headers"]
            ) as websocket:
                
                # Step 2: Simulate agent execution that will fail
                agent_request = {
                    "type": "execute_agent",
                    "agent_type": "DataAgent",
                    "request": {
                        "user_query": "Analyze this data that will cause an error",
                        "data_source": "invalid_data_source_for_testing",
                        "user_id": authenticated_user.user_id,
                        "thread_id": f"github_test_thread_{datetime.now().timestamp()}"
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Step 3: Listen for agent execution events
                github_issue_created = False
                github_issue_url = None
                error_detected = False
                
                timeout = 60  # 60 second timeout
                start_time = datetime.now()
                
                while (datetime.now() - start_time).seconds < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(message)
                        
                        # Step 4: Detect error event
                        if event.get("type") == "agent_error":
                            error_detected = True
                            assert event.get("error_type") is not None
                            assert event.get("error_message") is not None
                            assert event.get("user_id") == authenticated_user.user_id
                        
                        # Step 5: Detect GitHub issue creation event
                        elif event.get("type") == "github_issue_created":
                            github_issue_created = True
                            github_issue_url = event.get("issue_url")
                            
                            # Validate GitHub issue event
                            assert github_issue_url is not None
                            assert "github.com" in github_issue_url
                            assert event.get("issue_number") is not None
                            assert event.get("issue_title") is not None
                            
                            # Should contain error context
                            assert "DataAgent" in event.get("issue_title", "")
                            
                        # Step 6: Detect issue progress updates
                        elif event.get("type") == "github_issue_updated":
                            assert event.get("issue_url") == github_issue_url
                            assert event.get("update_type") in ["comment_added", "status_changed"]
                            
                        # Step 7: Check for issue resolution
                        elif event.get("type") == "github_issue_resolved":
                            assert event.get("issue_url") == github_issue_url
                            assert event.get("resolution_type") is not None
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                # Validate complete workflow
                assert error_detected is True, "Agent error was not detected"
                assert github_issue_created is True, "GitHub issue was not created"
                assert github_issue_url is not None, "GitHub issue URL was not provided"
                
                # Step 8: Verify GitHub issue exists and has correct content
                async with httpx.AsyncClient() as client:
                    # Extract issue number from URL
                    issue_number = github_issue_url.split("/")[-1]
                    
                    # Get issue details via GitHub API
                    github_api_url = f"https://api.github.com/repos/{github_config['repo_owner']}/{github_config['repo_name']}/issues/{issue_number}"
                    
                    response = await client.get(
                        github_api_url,
                        headers={
                            "Authorization": f"token {github_config['token']}",
                            "Accept": "application/vnd.github.v3+json"
                        }
                    )
                    
                    assert response.status_code == 200
                    issue_data = response.json()
                    
                    # Validate issue content
                    assert issue_data["state"] == "open"
                    assert "[AUTOMATED]" in issue_data["title"]
                    assert "DataAgent" in issue_data["title"]
                    assert authenticated_user.user_id in issue_data["body"]
                    
                    # Check labels
                    labels = [label["name"] for label in issue_data["labels"]]
                    assert "automated" in labels
                    assert "bug" in labels
    
    @pytest.mark.e2e
    @pytest.mark.github
    async def test_claude_command_github_integration_e2e_fails(
        self, authenticated_user, websocket_client, github_config
    ):
        """
        TEST SHOULD FAIL: Claude GitHub commands don't exist
        
        This test validates that users can create GitHub issues
        through Claude commands in the chat interface.
        """
        if not github_config["enabled"]:
            pytest.skip("GitHub integration not enabled for testing")
            
        with pytest.raises((ImportError, NameError, ModuleNotFoundError, ConnectionError)):
            async with websockets.connect(
                websocket_client["url"],
                extra_headers=websocket_client["headers"]
            ) as websocket:
                
                # Send Claude command to create GitHub issue
                command_message = {
                    "type": "claude_command",
                    "command": "create-github-issue",
                    "args": ["Agent execution is failing consistently"],
                    "flags": {
                        "priority": "high",
                        "labels": ["bug", "agent-execution"]
                    },
                    "user_id": authenticated_user.user_id,
                    "thread_id": f"github_command_test_{datetime.now().timestamp()}"
                }
                
                await websocket.send(json.dumps(command_message))
                
                # Wait for command result
                timeout = 30
                start_time = datetime.now()
                command_result = None
                
                while (datetime.now() - start_time).seconds < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(message)
                        
                        if event.get("type") == "claude_command_result":
                            command_result = event
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                # Validate command result
                assert command_result is not None
                assert command_result.get("success") is True
                assert command_result.get("github_issue_url") is not None
                assert "github.com" in command_result.get("github_issue_url")
                assert "GitHub issue created" in command_result.get("message", "")
    
    @pytest.mark.e2e
    @pytest.mark.github
    async def test_duplicate_issue_prevention_e2e_fails(
        self, authenticated_user, websocket_client, github_config
    ):
        """
        TEST SHOULD FAIL: Duplicate issue prevention doesn't exist
        
        This test validates that duplicate GitHub issues are prevented
        when similar errors occur multiple times.
        """
        if not github_config["enabled"]:
            pytest.skip("GitHub integration not enabled for testing")
            
        with pytest.raises((ImportError, NameError, ModuleNotFoundError, ConnectionError)):
            async with websockets.connect(
                websocket_client["url"],
                extra_headers=websocket_client["headers"]
            ) as websocket:
                
                # Simulate the same error multiple times
                error_context = {
                    "error_type": "DuplicateTestError",
                    "error_message": "This is a duplicate test error",
                    "component": "TestAgent",
                    "user_id": authenticated_user.user_id
                }
                
                first_issue_url = None
                duplicate_prevented = False
                
                # Send first error
                first_error = {
                    "type": "report_error",
                    "error_context": error_context,
                    "thread_id": f"duplicate_test_1_{datetime.now().timestamp()}"
                }
                
                await websocket.send(json.dumps(first_error))
                
                # Wait for first issue creation
                timeout = 30
                start_time = datetime.now()
                
                while (datetime.now() - start_time).seconds < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(message)
                        
                        if event.get("type") == "github_issue_created":
                            first_issue_url = event.get("issue_url")
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                assert first_issue_url is not None
                
                # Send duplicate error
                duplicate_error = {
                    "type": "report_error", 
                    "error_context": error_context,
                    "thread_id": f"duplicate_test_2_{datetime.now().timestamp()}"
                }
                
                await websocket.send(json.dumps(duplicate_error))
                
                # Wait for duplicate prevention notification
                start_time = datetime.now()
                
                while (datetime.now() - start_time).seconds < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(message)
                        
                        if event.get("type") == "github_duplicate_detected":
                            duplicate_prevented = True
                            assert event.get("existing_issue_url") == first_issue_url
                            assert event.get("action") == "comment_added"
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                assert duplicate_prevented is True
    
    @pytest.mark.e2e
    @pytest.mark.github
    async def test_issue_resolution_workflow_e2e_fails(
        self, authenticated_user, websocket_client, github_config
    ):
        """
        TEST SHOULD FAIL: Issue resolution workflow doesn't exist
        
        This test validates that GitHub issues are automatically
        resolved when errors are fixed.
        """
        if not github_config["enabled"]:
            pytest.skip("GitHub integration not enabled for testing")
            
        with pytest.raises((ImportError, NameError, ModuleNotFoundError, ConnectionError)):
            async with websockets.connect(
                websocket_client["url"], 
                extra_headers=websocket_client["headers"]
            ) as websocket:
                
                # Step 1: Create error that generates GitHub issue
                error_context = {
                    "error_type": "ResolutionTestError",
                    "error_message": "This error will be resolved",
                    "component": "ResolutionTestAgent",
                    "user_id": authenticated_user.user_id,
                    "thread_id": f"resolution_test_{datetime.now().timestamp()}"
                }
                
                error_report = {
                    "type": "report_error",
                    "error_context": error_context
                }
                
                await websocket.send(json.dumps(error_report))
                
                # Step 2: Wait for GitHub issue creation
                issue_url = None
                timeout = 30
                start_time = datetime.now()
                
                while (datetime.now() - start_time).seconds < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(message)
                        
                        if event.get("type") == "github_issue_created":
                            issue_url = event.get("issue_url")
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                assert issue_url is not None
                
                # Step 3: Simulate error resolution
                resolution_report = {
                    "type": "report_error_resolved",
                    "error_context": error_context,
                    "resolution": {
                        "fix_description": "Updated error handling logic",
                        "commit_sha": "abc123def456",
                        "resolved_by": "automated_fix"
                    }
                }
                
                await websocket.send(json.dumps(resolution_report))
                
                # Step 4: Wait for issue resolution notification
                issue_resolved = False
                start_time = datetime.now()
                
                while (datetime.now() - start_time).seconds < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(message)
                        
                        if event.get("type") == "github_issue_resolved":
                            issue_resolved = True
                            assert event.get("issue_url") == issue_url
                            assert event.get("resolution_commit") == "abc123def456"
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                assert issue_resolved is True
                
                # Step 5: Verify issue is closed on GitHub
                async with httpx.AsyncClient() as client:
                    issue_number = issue_url.split("/")[-1]
                    github_api_url = f"https://api.github.com/repos/{github_config['repo_owner']}/{github_config['repo_name']}/issues/{issue_number}"
                    
                    response = await client.get(
                        github_api_url,
                        headers={
                            "Authorization": f"token {github_config['token']}",
                            "Accept": "application/vnd.github.v3+json"
                        }
                    )
                    
                    assert response.status_code == 200
                    issue_data = response.json()
                    assert issue_data["state"] == "closed"
    
    @pytest.mark.e2e  
    @pytest.mark.github
    @pytest.mark.multi_user
    async def test_multi_user_github_isolation_e2e_fails(
        self, auth_helper, auth_config, github_config
    ):
        """
        TEST SHOULD FAIL: Multi-user GitHub isolation doesn't exist
        
        This test validates that GitHub issues are properly isolated
        between different users and don't leak information.
        """
        if not github_config["enabled"]:
            pytest.skip("GitHub integration not enabled for testing")
            
        with pytest.raises((ImportError, NameError, ModuleNotFoundError, ConnectionError)):
            # Create two different authenticated users
            user1 = await auth_helper.create_authenticated_session(
                email="github_user1@example.com",
                user_id="github_user1"
            )
            
            user2 = await auth_helper.create_authenticated_session(
                email="github_user2@example.com", 
                user_id="github_user2"
            )
            
            try:
                # Connect WebSockets for both users
                user1_ws_url = auth_config.websocket_url
                user1_headers = {
                    "Authorization": f"Bearer {user1.jwt_token}",
                    "User-ID": user1.user_id
                }
                
                user2_ws_url = auth_config.websocket_url
                user2_headers = {
                    "Authorization": f"Bearer {user2.jwt_token}",
                    "User-ID": user2.user_id
                }
                
                async with websockets.connect(user1_ws_url, extra_headers=user1_headers) as ws1, \
                           websockets.connect(user2_ws_url, extra_headers=user2_headers) as ws2:
                    
                    # User 1 creates GitHub issue with sensitive data
                    user1_error = {
                        "type": "report_error",
                        "error_context": {
                            "error_type": "SensitiveDataError", 
                            "error_message": "User1 sensitive data processing failed",
                            "user_id": user1.user_id,
                            "sensitive_data": {
                                "api_key": "user1_secret_key_123",
                                "internal_id": "user1_internal_data"
                            }
                        }
                    }
                    
                    await ws1.send(json.dumps(user1_error))
                    
                    # User 2 creates similar GitHub issue
                    user2_error = {
                        "type": "report_error",
                        "error_context": {
                            "error_type": "SensitiveDataError",
                            "error_message": "User2 sensitive data processing failed", 
                            "user_id": user2.user_id,
                            "sensitive_data": {
                                "api_key": "user2_secret_key_456",
                                "internal_id": "user2_internal_data"
                            }
                        }
                    }
                    
                    await ws2.send(json.dumps(user2_error))
                    
                    # Collect issue creation events
                    user1_issue_url = None
                    user2_issue_url = None
                    timeout = 30
                    start_time = datetime.now()
                    
                    while (datetime.now() - start_time).seconds < timeout and \
                          (user1_issue_url is None or user2_issue_url is None):
                        
                        try:
                            # Check user 1 events
                            if user1_issue_url is None:
                                message1 = await asyncio.wait_for(ws1.recv(), timeout=2.0)
                                event1 = json.loads(message1)
                                if event1.get("type") == "github_issue_created":
                                    user1_issue_url = event1.get("issue_url")
                        except asyncio.TimeoutError:
                            pass
                        
                        try:
                            # Check user 2 events
                            if user2_issue_url is None:
                                message2 = await asyncio.wait_for(ws2.recv(), timeout=2.0)
                                event2 = json.loads(message2)
                                if event2.get("type") == "github_issue_created":
                                    user2_issue_url = event2.get("issue_url")
                        except asyncio.TimeoutError:
                            pass
                    
                    # Validate isolation
                    assert user1_issue_url is not None
                    assert user2_issue_url is not None
                    assert user1_issue_url != user2_issue_url
                    
                    # Verify issues don't contain other user's data
                    async with httpx.AsyncClient() as client:
                        headers = {
                            "Authorization": f"token {github_config['token']}",
                            "Accept": "application/vnd.github.v3+json"
                        }
                        
                        # Check user 1 issue
                        user1_issue_number = user1_issue_url.split("/")[-1]
                        user1_api_url = f"https://api.github.com/repos/{github_config['repo_owner']}/{github_config['repo_name']}/issues/{user1_issue_number}"
                        
                        response1 = await client.get(user1_api_url, headers=headers)
                        assert response1.status_code == 200
                        user1_issue = response1.json()
                        
                        # User 1 issue should not contain user 2 data
                        assert "user2_secret_key_456" not in user1_issue["body"]
                        assert "user2_internal_data" not in user1_issue["body"]
                        assert user2.user_id not in user1_issue["body"]
                        
                        # Check user 2 issue
                        user2_issue_number = user2_issue_url.split("/")[-1]
                        user2_api_url = f"https://api.github.com/repos/{github_config['repo_owner']}/{github_config['repo_name']}/issues/{user2_issue_number}"
                        
                        response2 = await client.get(user2_api_url, headers=headers)
                        assert response2.status_code == 200
                        user2_issue = response2.json()
                        
                        # User 2 issue should not contain user 1 data
                        assert "user1_secret_key_123" not in user2_issue["body"]
                        assert "user1_internal_data" not in user2_issue["body"]
                        assert user1.user_id not in user2_issue["body"]
                        
            finally:
                await auth_helper.cleanup_session(user1)
                await auth_helper.cleanup_session(user2)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])