"""
E2E tests for complete GitHub issue workflow.

CRITICAL: These tests use REAL services and REAL authentication per CLAUDE.md.
Tests are designed to INITIALLY FAIL to prove functionality doesn't exist.
All E2E tests MUST use authentication except for auth validation tests.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.e2e
@pytest.mark.github_integration
@pytest.mark.authenticated
class TestCompleteGitHubIssueWorkflowE2E(SSotAsyncTestCase):
    """E2E test for complete GitHub issue creation and management workflow."""

    def setup_method(self, method):
        """Set up E2E test with real authentication and services."""
        super().setup_method(method)
        
        # Setup sync components  
        self.env = IsolatedEnvironment()
        self.github_token = self.env.get("GITHUB_TOKEN_TEST")
        self.test_repo = self.env.get("GITHUB_TEST_REPO", "netra-systems/test-repo")
        
        if not self.github_token:
            pytest.skip("GITHUB_TOKEN_TEST not configured for E2E testing")
    
    async def _setup_auth(self):
        """Setup authentication - called from test methods."""
        # CRITICAL: All E2E tests must use real authentication per CLAUDE.md
        self.auth_helper = E2EAuthHelper()
        self.authenticated_user = await self.auth_helper.create_authenticated_test_user()

    async def test_end_to_end_error_to_github_issue_flow(self):
        """Test complete flow from error detection to GitHub issue creation."""
        # Setup authentication
        await self._setup_auth()
        
        # Simulate a real error occurring in the system
        system_error = {
            "error_type": "ImportError",
            "message": "No module named 'nonexistent_module'",
            "stack_trace": "Traceback (most recent call last):\n  File test.py, line 1\n    import nonexistent_module\nImportError: No module named 'nonexistent_module'",
            "service": "netra_backend",
            "environment": "test",
            "user_id": self.authenticated_user["user_id"],
            "timestamp": datetime.now().isoformat(),
            "severity": "high",
            "affects_business_logic": True
        }
        
        # EXPECTED FAILURE: End-to-end workflow doesn't exist
        try:
            from test_framework.ssot.github_issue_e2e_workflow import GitHubIssueE2EWorkflow
            
            workflow = GitHubIssueE2EWorkflow(
                github_token=self.github_token,
                auth_context=self.authenticated_user
            )
            
            # Step 1: Error detection and analysis
            error_analysis = await workflow.analyze_error(system_error)
            
            assert error_analysis["should_create_issue"] is True
            assert error_analysis["priority"] in ["high", "critical"]
            assert error_analysis["category"] == "dependency"
            
            # Step 2: Duplicate check against existing issues
            duplicate_check = await workflow.check_for_duplicates(
                error=system_error,
                repo=self.test_repo
            )
            
            assert "is_duplicate" in duplicate_check
            assert "similar_issues" in duplicate_check
            
            # Step 3: Create GitHub issue if not duplicate
            if not duplicate_check["is_duplicate"]:
                issue_result = await workflow.create_github_issue(
                    error=system_error,
                    repo=self.test_repo,
                    analysis=error_analysis
                )
                
                assert issue_result["success"] is True
                assert "issue_number" in issue_result
                assert "issue_url" in issue_result
                
                # Step 4: Verify issue was created with correct metadata
                issue_details = await workflow.get_issue_details(
                    repo=self.test_repo,
                    issue_number=issue_result["issue_number"]
                )
                
                assert system_error["error_type"] in issue_details["title"]
                assert system_error["service"] in issue_details["body"]
                assert "dependency" in [label["name"] for label in issue_details["labels"]]
                
                # Clean up: Close the test issue
                await workflow.close_issue(
                    repo=self.test_repo,
                    issue_number=issue_result["issue_number"],
                    reason="E2E test cleanup"
                )
            
        except ImportError:
            pytest.fail("End-to-end GitHub issue workflow not implemented")

    async def test_multi_error_batch_processing_e2e(self):
        """Test processing multiple errors and creating corresponding GitHub issues."""
        # Setup authentication
        await self._setup_auth()
        
        multiple_errors = [
            {
                "error_type": "ConnectionError", 
                "message": "Failed to connect to database",
                "service": "netra_backend",
                "severity": "critical",
                "user_id": self.authenticated_user["user_id"],
                "timestamp": datetime.now().isoformat()
            },
            {
                "error_type": "TimeoutError",
                "message": "Request timeout after 30 seconds", 
                "service": "auth_service",
                "severity": "medium",
                "user_id": self.authenticated_user["user_id"],
                "timestamp": datetime.now().isoformat()
            },
            {
                "error_type": "ValidationError",
                "message": "Invalid user input format",
                "service": "frontend",
                "severity": "low", 
                "user_id": self.authenticated_user["user_id"],
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        # EXPECTED FAILURE: Batch processing doesn't exist
        try:
            from test_framework.ssot.github_issue_batch_processor import GitHubIssueBatchProcessor
            
            processor = GitHubIssueBatchProcessor(
                github_token=self.github_token,
                auth_context=self.authenticated_user
            )
            
            # Process all errors in batch
            batch_result = await processor.process_error_batch(
                errors=multiple_errors,
                repo=self.test_repo
            )
            
            assert batch_result["processed_count"] == len(multiple_errors)
            assert batch_result["issues_created"] >= 0  # Some may be duplicates
            assert batch_result["duplicates_found"] >= 0
            assert len(batch_result["results"]) == len(multiple_errors)
            
            # Verify each error was processed
            for i, error_result in enumerate(batch_result["results"]):
                assert error_result["error_index"] == i
                assert error_result["status"] in ["created", "duplicate", "skipped"]
                
                if error_result["status"] == "created":
                    assert "issue_number" in error_result
                    assert "issue_url" in error_result
                    
            # Clean up: Close created issues
            for result in batch_result["results"]:
                if result["status"] == "created":
                    await processor.close_issue(
                        repo=self.test_repo,
                        issue_number=result["issue_number"],
                        reason="E2E test cleanup"
                    )
                    
        except ImportError:
            pytest.fail("GitHub issue batch processing not implemented")

    async def test_github_issue_progress_tracking_e2e(self):
        """Test complete issue progress tracking from creation to resolution."""
        # Setup authentication
        await self._setup_auth()
        
        test_error = {
            "error_type": "APIError",
            "message": "External API rate limit exceeded",
            "service": "netra_backend", 
            "user_id": self.authenticated_user["user_id"],
            "severity": "medium",
            "timestamp": datetime.now().isoformat()
        }
        
        # EXPECTED FAILURE: Progress tracking doesn't exist
        try:
            from test_framework.ssot.github_issue_progress_tracker import GitHubIssueProgressTracker
            
            tracker = GitHubIssueProgressTracker(
                github_token=self.github_token,
                auth_context=self.authenticated_user
            )
            
            # Step 1: Create issue
            creation_result = await tracker.create_tracked_issue(
                error=test_error,
                repo=self.test_repo
            )
            
            issue_number = creation_result["issue_number"]
            
            # Step 2: Update progress - Investigation phase
            investigation_update = {
                "phase": "investigation",
                "status": "analyzing root cause",
                "findings": "Rate limit occurs during peak usage hours",
                "next_steps": "Implement exponential backoff strategy"
            }
            
            progress_result_1 = await tracker.update_issue_progress(
                repo=self.test_repo,
                issue_number=issue_number,
                progress=investigation_update
            )
            
            assert progress_result_1["success"] is True
            assert progress_result_1["comment_updated"] is True
            
            # Step 3: Update progress - Implementation phase
            implementation_update = {
                "phase": "implementation",
                "status": "implementing fix",
                "progress": "Added exponential backoff to API client",
                "commit_reference": "abc123def456",
                "testing_status": "unit tests passing"
            }
            
            progress_result_2 = await tracker.update_issue_progress(
                repo=self.test_repo,
                issue_number=issue_number,
                progress=implementation_update
            )
            
            assert progress_result_2["success"] is True
            
            # Step 4: Mark as resolved with commit link
            resolution_data = {
                "phase": "resolved",
                "status": "fixed",
                "resolution": "Implemented exponential backoff strategy",
                "commit_hash": "abc123def456",
                "pr_number": 789,
                "verification": "Tested under load - no more rate limit errors"
            }
            
            resolution_result = await tracker.resolve_issue(
                repo=self.test_repo,
                issue_number=issue_number,
                resolution=resolution_data
            )
            
            assert resolution_result["success"] is True
            assert resolution_result["issue_closed"] is True
            assert resolution_result["commit_linked"] is True
            
        except ImportError:
            pytest.fail("GitHub issue progress tracking not implemented")


@pytest.mark.e2e
@pytest.mark.github_integration
@pytest.mark.claude_commands
@pytest.mark.authenticated
class TestClaudeCommandGitHubIntegrationE2E(SSotAsyncTestCase):
    """E2E test for Claude command integration with GitHub operations."""

    def setup_method(self, method):
        """Set up E2E test with authenticated Claude command context."""
        super().setup_method(method)
        
        # Setup sync components
        self.env = IsolatedEnvironment()
        self.github_token = self.env.get("GITHUB_TOKEN_TEST")
        
        if not self.github_token:
            pytest.skip("GITHUB_TOKEN_TEST not configured")
    
    async def _setup_auth(self):
        """Setup authentication - called from test methods."""
        # CRITICAL: Must use real authentication
        self.auth_helper = E2EAuthHelper()
        self.authenticated_user = await self.auth_helper.create_authenticated_test_user()

    async def test_claude_create_github_issue_command_e2e(self):
        """Test creating GitHub issues through Claude commands."""
        # Setup authentication
        await self._setup_auth()
        
        claude_command = """
        create github issue for error: "DatabaseConnectionError: Failed to connect to PostgreSQL"
        service: netra_backend
        severity: critical
        context: "Occurs during user authentication flow"
        """
        
        # EXPECTED FAILURE: Claude command GitHub integration doesn't exist
        try:
            from test_framework.ssot.claude_github_command_executor import ClaudeGitHubCommandExecutor
            
            executor = ClaudeGitHubCommandExecutor(
                github_token=self.github_token,
                auth_context=self.authenticated_user
            )
            
            # Execute Claude command
            execution_result = await executor.execute_command(
                command=claude_command,
                repo="netra-systems/test-repo"
            )
            
            assert execution_result["success"] is True
            assert execution_result["command_type"] == "create_issue"
            assert "issue_number" in execution_result
            assert "issue_url" in execution_result
            assert "claude_response" in execution_result
            
            # Verify Claude response format
            claude_response = execution_result["claude_response"]
            assert "Issue created successfully" in claude_response
            assert str(execution_result["issue_number"]) in claude_response
            assert "github.com" in claude_response
            
            # Clean up
            await executor.close_issue(
                repo="netra-systems/test-repo",
                issue_number=execution_result["issue_number"]
            )
            
        except ImportError:
            pytest.fail("Claude GitHub command execution not implemented")

    async def test_claude_search_and_update_github_issues_e2e(self):
        """Test searching and updating GitHub issues through Claude commands."""
        # Setup authentication
        await self._setup_auth()
        
        # First create a test issue to search for and update
        setup_command = 'create github issue for error: "Test search and update functionality"'
        
        # EXPECTED FAILURE: Search and update commands don't exist
        try:
            from test_framework.ssot.claude_github_command_executor import ClaudeGitHubCommandExecutor
            
            executor = ClaudeGitHubCommandExecutor(
                github_token=self.github_token,
                auth_context=self.authenticated_user
            )
            
            # Create test issue
            creation_result = await executor.execute_command(
                command=setup_command,
                repo="netra-systems/test-repo"
            )
            
            issue_number = creation_result["issue_number"]
            
            # Search for the issue
            search_command = f'search github issues for pattern: "Test search and update"'
            
            search_result = await executor.execute_command(
                command=search_command,
                repo="netra-systems/test-repo"
            )
            
            assert search_result["success"] is True
            assert search_result["command_type"] == "search_issues"
            assert search_result["results_found"] > 0
            assert any(result["number"] == issue_number for result in search_result["issues"])
            
            # Update the issue with progress
            update_command = f'''
            update github issue #{issue_number} with status: "investigating"
            progress: "Root cause identified - implementing fix"
            next_steps: "Deploy fix to staging environment"
            '''
            
            update_result = await executor.execute_command(
                command=update_command,
                repo="netra-systems/test-repo"
            )
            
            assert update_result["success"] is True
            assert update_result["command_type"] == "update_issue"
            assert update_result["issue_number"] == issue_number
            assert "comment_id" in update_result
            
            # Clean up
            await executor.close_issue(
                repo="netra-systems/test-repo",
                issue_number=issue_number
            )
            
        except ImportError:
            pytest.fail("Claude GitHub search and update commands not implemented")


@pytest.mark.e2e
@pytest.mark.github_integration
@pytest.mark.multi_user
@pytest.mark.authenticated
class TestGitHubIntegrationMultiUserE2E(SSotAsyncTestCase):
    """E2E test for GitHub integration in multi-user scenarios."""

    def setup_method(self, method):
        """Set up multi-user E2E test scenario."""
        super().setup_method(method)
        
        # Setup sync components
        self.env = IsolatedEnvironment()
        self.github_token = self.env.get("GITHUB_TOKEN_TEST")
        
        if not self.github_token:
            pytest.skip("GITHUB_TOKEN_TEST not configured")
    
    async def _setup_auth(self):
        """Setup authentication - called from test methods."""
        # CRITICAL: Create multiple authenticated users
        self.auth_helper = E2EAuthHelper()
        self.user_1 = await self.auth_helper.create_authenticated_test_user()
        self.user_2 = await self.auth_helper.create_authenticated_test_user()

    async def test_multi_user_github_issue_isolation_e2e(self):
        """Test that GitHub issues are properly isolated per user context."""
        # Setup authentication
        await self._setup_auth()
        
        # User 1 creates an issue
        user_1_error = {
            "error_type": "ValidationError",
            "message": "User 1 validation failure",
            "user_id": self.user_1["user_id"], 
            "service": "auth_service",
            "timestamp": datetime.now().isoformat()
        }
        
        # User 2 creates a similar issue
        user_2_error = {
            "error_type": "ValidationError", 
            "message": "User 2 validation failure",
            "user_id": self.user_2["user_id"],
            "service": "auth_service", 
            "timestamp": datetime.now().isoformat()
        }
        
        # EXPECTED FAILURE: Multi-user isolation doesn't exist
        try:
            from test_framework.ssot.github_multi_user_manager import GitHubMultiUserManager
            
            manager = GitHubMultiUserManager(github_token=self.github_token)
            
            # Create issues for both users
            user_1_result = await manager.create_user_scoped_issue(
                error=user_1_error,
                auth_context=self.user_1,
                repo="netra-systems/test-repo"
            )
            
            user_2_result = await manager.create_user_scoped_issue(
                error=user_2_error,
                auth_context=self.user_2, 
                repo="netra-systems/test-repo"
            )
            
            # Both issues should be created (not considered duplicates due to different users)
            assert user_1_result["success"] is True
            assert user_2_result["success"] is True
            assert user_1_result["issue_number"] != user_2_result["issue_number"]
            
            # Verify user context is preserved in issue metadata
            user_1_issue_details = await manager.get_issue_with_user_context(
                repo="netra-systems/test-repo",
                issue_number=user_1_result["issue_number"],
                auth_context=self.user_1
            )
            
            assert self.user_1["user_id"] in user_1_issue_details["body"]
            assert self.user_2["user_id"] not in user_1_issue_details["body"]
            
            # Clean up both issues
            await manager.close_user_scoped_issue(
                repo="netra-systems/test-repo",
                issue_number=user_1_result["issue_number"],
                auth_context=self.user_1
            )
            
            await manager.close_user_scoped_issue(
                repo="netra-systems/test-repo", 
                issue_number=user_2_result["issue_number"],
                auth_context=self.user_2
            )
            
        except ImportError:
            pytest.fail("GitHub multi-user isolation not implemented")