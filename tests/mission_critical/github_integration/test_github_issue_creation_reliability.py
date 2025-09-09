"""
Mission critical tests for GitHub issue creation reliability.

CRITICAL: These tests validate core business requirements for GitHub integration.
Success criteria: >99% reliability, <5 second response time, proper error handling.
"""

import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional

from test_framework.ssot.base_test_case import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.mission_critical
@pytest.mark.github_integration
@pytest.mark.reliability
class TestGitHubIssueCreationReliability(BaseTestCase):
    """Mission critical tests for GitHub issue creation reliability."""

    def setup_method(self):
        """Set up mission critical test environment."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.github_token = self.env.get("GITHUB_TOKEN_TEST")
        self.test_repo = self.env.get("GITHUB_TEST_REPO", "netra-systems/test-repo")
        
        if not self.github_token:
            pytest.skip("GITHUB_TOKEN_TEST not configured for mission critical testing")

    async def test_high_volume_concurrent_issue_creation(self):
        """Test creating 100 GitHub issues concurrently - business critical capability."""
        # EXPECTED FAILURE: High-volume creation doesn't exist
        try:
            from test_framework.ssot.github_issue_manager import GitHubIssueManager
            
            manager = GitHubIssueManager(token=self.github_token)
            
            # Create 100 different error scenarios for testing
            error_scenarios = []
            for i in range(100):
                error_scenarios.append({
                    "error_type": f"TestError{i % 10}",  # 10 different error types
                    "message": f"Test error message {i}",
                    "service": ["netra_backend", "auth_service", "frontend"][i % 3],
                    "severity": ["low", "medium", "high", "critical"][i % 4],
                    "timestamp": datetime.now().isoformat(),
                    "context": {"test_batch": "reliability_test", "index": i}
                })
            
            # Measure performance and reliability
            start_time = time.time()
            
            # Create issues concurrently
            tasks = [
                manager.create_issue_from_error(error=error, repo=self.test_repo)
                for error in error_scenarios
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # CRITICAL BUSINESS REQUIREMENTS
            success_count = sum(1 for result in results if not isinstance(result, Exception))
            success_rate = success_count / len(error_scenarios)
            
            # BUSINESS REQUIREMENT: >99% success rate
            assert success_rate > 0.99, f"Success rate {success_rate:.2%} below 99% requirement"
            
            # BUSINESS REQUIREMENT: <5 seconds per batch of 100
            assert duration < 5.0, f"Duration {duration:.2f}s exceeds 5 second requirement"
            
            # Verify all successful results have required fields
            successful_results = [r for r in results if not isinstance(r, Exception)]
            for result in successful_results:
                assert result["success"] is True
                assert "issue_number" in result
                assert "issue_url" in result
                assert result["issue_number"] > 0
            
            # Clean up: Close all created issues
            cleanup_tasks = []
            for result in successful_results:
                cleanup_tasks.append(
                    manager.close_issue(
                        repo=self.test_repo,
                        issue_number=result["issue_number"]
                    )
                )
            
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        except ImportError:
            pytest.fail("GitHub high-volume issue creation not implemented - CRITICAL BUSINESS CAPABILITY MISSING")

    async def test_github_api_failure_recovery_reliability(self):
        """Test reliability when GitHub API experiences failures."""
        # EXPECTED FAILURE: API failure recovery doesn't exist
        try:
            from test_framework.ssot.github_resilient_client import GitHubResilientClient
            
            client = GitHubResilientClient(
                token=self.github_token,
                max_retries=3,
                backoff_strategy="exponential"
            )
            
            # Test with simulated API failures
            test_error = {
                "error_type": "APIFailureTest",
                "message": "Testing API failure recovery",
                "severity": "high",
                "timestamp": datetime.now().isoformat()
            }
            
            # Simulate network issues, rate limits, and temporary failures
            failure_scenarios = [
                {"failure_type": "network_timeout", "expected_retry": True},
                {"failure_type": "rate_limit", "expected_backoff": True},
                {"failure_type": "server_error_500", "expected_retry": True},
                {"failure_type": "temporary_unavailable", "expected_retry": True}
            ]
            
            recovery_results = []
            
            for scenario in failure_scenarios:
                # Test resilient behavior with simulated failures
                recovery_result = await client.create_issue_with_resilience(
                    repo=self.test_repo,
                    error=test_error,
                    simulate_failure=scenario["failure_type"]
                )
                
                recovery_results.append({
                    "scenario": scenario,
                    "result": recovery_result
                })
            
            # CRITICAL: All scenarios should eventually succeed due to resilience
            for recovery in recovery_results:
                assert recovery["result"]["eventually_succeeded"] is True, f"Failed to recover from {recovery['scenario']['failure_type']}"
                assert recovery["result"]["retry_count"] > 0, "No retry attempts made"
                assert recovery["result"]["total_duration"] < 30.0, "Recovery took too long"
            
            # Clean up any created issues
            for recovery in recovery_results:
                if recovery["result"]["eventually_succeeded"]:
                    await client.close_issue(
                        repo=self.test_repo,
                        issue_number=recovery["result"]["issue_number"]
                    )
            
        except ImportError:
            pytest.fail("GitHub API failure recovery not implemented - CRITICAL FOR PRODUCTION RELIABILITY")

    async def test_duplicate_detection_accuracy_under_load(self):
        """Test duplicate detection accuracy with high volume of similar errors."""
        # EXPECTED FAILURE: High-volume duplicate detection doesn't exist
        try:
            from test_framework.ssot.github_duplicate_detector import GitHubDuplicateDetector
            from test_framework.ssot.github_issue_manager import GitHubIssueManager
            
            detector = GitHubDuplicateDetector(github_token=self.github_token)
            manager = GitHubIssueManager(token=self.github_token)
            
            # Create base error that others should be detected as duplicates of
            base_error = {
                "error_type": "ImportError",
                "message": "No module named 'missing_dependency'",
                "service": "netra_backend",
                "severity": "high",
                "timestamp": datetime.now().isoformat()
            }
            
            # Create the original issue
            original_issue = await manager.create_issue_from_error(
                error=base_error, 
                repo=self.test_repo
            )
            
            # Generate 50 similar errors that should be detected as duplicates
            similar_errors = []
            for i in range(50):
                similar_errors.append({
                    "error_type": "ImportError", 
                    "message": f"No module named 'missing_dependency' - variant {i}",
                    "service": "netra_backend",
                    "severity": ["medium", "high"][i % 2],
                    "timestamp": datetime.now().isoformat(),
                    "context": {"variation": i}
                })
            
            # Test duplicate detection accuracy
            start_time = time.time()
            
            duplicate_checks = await asyncio.gather(*[
                detector.check_for_duplicates(error=error, repo=self.test_repo)
                for error in similar_errors
            ])
            
            end_time = time.time()
            detection_duration = end_time - start_time
            
            # CRITICAL ACCURACY REQUIREMENTS
            detected_duplicates = sum(1 for check in duplicate_checks if check["is_duplicate"])
            accuracy = detected_duplicates / len(similar_errors)
            
            # BUSINESS REQUIREMENT: >95% duplicate detection accuracy
            assert accuracy > 0.95, f"Duplicate detection accuracy {accuracy:.2%} below 95% requirement"
            
            # PERFORMANCE REQUIREMENT: <10 seconds for 50 duplicate checks
            assert detection_duration < 10.0, f"Duplicate detection took {detection_duration:.2f}s, exceeds 10s limit"
            
            # Verify all detections point to the original issue
            for check in duplicate_checks:
                if check["is_duplicate"]:
                    assert original_issue["issue_number"] in [issue["number"] for issue in check["matching_issues"]]
            
            # Clean up: Close original issue
            await manager.close_issue(
                repo=self.test_repo,
                issue_number=original_issue["issue_number"]
            )
            
        except ImportError:
            pytest.fail("High-volume duplicate detection not implemented - CRITICAL FOR PREVENTING ISSUE SPAM")


@pytest.mark.mission_critical
@pytest.mark.github_integration
@pytest.mark.security
class TestGitHubDataSanitization(BaseTestCase):
    """Mission critical tests for data sanitization in GitHub issues."""

    def setup_method(self):
        """Set up security testing environment."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.github_token = self.env.get("GITHUB_TOKEN_TEST")
        
        if not self.github_token:
            pytest.skip("GITHUB_TOKEN_TEST not configured")

    async def test_sensitive_data_sanitization_critical(self):
        """Test that sensitive data is properly sanitized before GitHub issue creation."""
        # EXPECTED FAILURE: Data sanitization doesn't exist
        try:
            from test_framework.ssot.github_data_sanitizer import GitHubDataSanitizer
            from test_framework.ssot.github_issue_manager import GitHubIssueManager
            
            sanitizer = GitHubDataSanitizer()
            manager = GitHubIssueManager(token=self.github_token)
            
            # Create error with sensitive data that MUST be sanitized
            sensitive_error = {
                "error_type": "AuthenticationError",
                "message": "Authentication failed with key: sk-abc123xyz789secretkey",
                "stack_trace": """
                Traceback (most recent call last):
                  File "auth.py", line 45
                    api_key = 'sk-abc123xyz789secretkey'
                    password = 'super_secret_password_123'
                    jwt_secret = 'jwt-secret-key-production-do-not-share'
                    database_url = 'postgresql://user:password@db.internal:5432/prod'
                AuthenticationError: Invalid API key
                """,
                "context": {
                    "user_email": "test.user@company.com",
                    "api_key": "sk-abc123xyz789secretkey", 
                    "session_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.secret_payload",
                    "database_password": "db_prod_password_2024"
                },
                "service": "auth_service",
                "timestamp": datetime.now().isoformat()
            }
            
            # CRITICAL SECURITY TEST: Sanitize before creating issue
            sanitized_error = await sanitizer.sanitize_error_for_github(sensitive_error)
            
            # Verify ALL sensitive data is removed/masked
            sensitive_patterns = [
                "sk-abc123xyz789secretkey",
                "super_secret_password_123", 
                "jwt-secret-key-production",
                "postgresql://user:password@",
                "db_prod_password_2024",
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"
            ]
            
            sanitized_content = str(sanitized_error)
            
            for sensitive_pattern in sensitive_patterns:
                assert sensitive_pattern not in sanitized_content, f"CRITICAL SECURITY FAILURE: '{sensitive_pattern}' not sanitized"
            
            # Verify sanitized placeholders are present
            assert "[API_KEY_REDACTED]" in sanitized_content
            assert "[PASSWORD_REDACTED]" in sanitized_content  
            assert "[JWT_REDACTED]" in sanitized_content
            assert "[DATABASE_URL_REDACTED]" in sanitized_content
            
            # Create GitHub issue with sanitized data
            issue_result = await manager.create_issue_from_error(
                error=sanitized_error,
                repo=self.test_repo
            )
            
            # DOUBLE-CHECK: Verify GitHub issue content is clean
            issue_details = await manager.get_issue_details(
                repo=self.test_repo,
                issue_number=issue_result["issue_number"]
            )
            
            issue_content = issue_details["title"] + " " + issue_details["body"]
            
            for sensitive_pattern in sensitive_patterns:
                assert sensitive_pattern not in issue_content, f"CRITICAL: Sensitive data '{sensitive_pattern}' leaked to GitHub"
            
            # Clean up
            await manager.close_issue(
                repo=self.test_repo,
                issue_number=issue_result["issue_number"]
            )
            
        except ImportError:
            pytest.fail("Data sanitization not implemented - CRITICAL SECURITY VULNERABILITY")

    async def test_multi_user_data_isolation_security(self):
        """Test that user data is properly isolated in GitHub issues."""
        # EXPECTED FAILURE: Multi-user isolation doesn't exist
        try:
            from test_framework.ssot.github_multi_user_security import GitHubMultiUserSecurity
            from test_framework.ssot.github_issue_manager import GitHubIssueManager
            
            security = GitHubMultiUserSecurity()
            manager = GitHubIssueManager(token=self.github_token)
            
            # Create errors from different users with potentially conflicting data
            user_1_error = {
                "error_type": "ValidationError",
                "user_id": "user-123-sensitive",
                "user_email": "user1@company.com",
                "private_data": "user1-private-information",
                "message": "User 1 validation failed",
                "timestamp": datetime.now().isoformat()
            }
            
            user_2_error = {
                "error_type": "ValidationError", 
                "user_id": "user-456-confidential",
                "user_email": "user2@company.com",
                "private_data": "user2-private-information",
                "message": "User 2 validation failed",
                "timestamp": datetime.now().isoformat()
            }
            
            # Test user data isolation
            user_1_secure = await security.prepare_user_scoped_error(user_1_error)
            user_2_secure = await security.prepare_user_scoped_error(user_2_error)
            
            # Create issues for both users
            issue_1 = await manager.create_issue_from_error(
                error=user_1_secure,
                repo=self.test_repo
            )
            
            issue_2 = await manager.create_issue_from_error(
                error=user_2_secure, 
                repo=self.test_repo
            )
            
            # CRITICAL SECURITY VERIFICATION: No cross-user data leakage
            issue_1_details = await manager.get_issue_details(
                repo=self.test_repo,
                issue_number=issue_1["issue_number"]
            )
            
            issue_2_details = await manager.get_issue_details(
                repo=self.test_repo,
                issue_number=issue_2["issue_number"]
            )
            
            # User 1 issue should NOT contain User 2 data
            issue_1_content = issue_1_details["title"] + " " + issue_1_details["body"]
            assert "user-456-confidential" not in issue_1_content
            assert "user2@company.com" not in issue_1_content
            assert "user2-private-information" not in issue_1_content
            
            # User 2 issue should NOT contain User 1 data
            issue_2_content = issue_2_details["title"] + " " + issue_2_details["body"]
            assert "user-123-sensitive" not in issue_2_content
            assert "user1@company.com" not in issue_2_content
            assert "user1-private-information" not in issue_2_content
            
            # Clean up
            await asyncio.gather(
                manager.close_issue(repo=self.test_repo, issue_number=issue_1["issue_number"]),
                manager.close_issue(repo=self.test_repo, issue_number=issue_2["issue_number"])
            )
            
        except ImportError:
            pytest.fail("Multi-user data isolation not implemented - CRITICAL SECURITY RISK")