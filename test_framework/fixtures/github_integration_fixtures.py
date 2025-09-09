"""
GitHub Integration Test Fixtures

Shared fixtures for GitHub integration testing across all test levels.
Provides SSOT patterns for GitHub test configuration and setup.

CRITICAL: Follows SSOT principles and IsolatedEnvironment patterns.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Generator
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass
import httpx

from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase

@dataclass
class GitHubTestConfig:
    """GitHub test configuration following SSOT principles"""
    enabled: bool
    token: str
    repo_owner: str
    repo_name: str
    api_base_url: str
    webhook_url: str
    rate_limit_buffer: int
    max_issues_per_hour: int
    test_label: str
    cleanup_enabled: bool

@dataclass
class MockGitHubIssue:
    """Mock GitHub issue for testing"""
    number: int
    title: str
    body: str
    state: str
    labels: List[Dict[str, str]]
    created_at: str
    updated_at: str
    html_url: str
    user: Dict[str, str]
    assignee: Optional[Dict[str, str]] = None
    milestone: Optional[Dict[str, str]] = None
    comments: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state,
            "labels": self.labels,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "html_url": self.html_url,
            "user": self.user,
            "assignee": self.assignee,
            "milestone": self.milestone,
            "comments": self.comments
        }

@dataclass 
class GitHubErrorContext:
    """Standardized error context for GitHub integration testing"""
    error_message: str
    error_type: str
    stack_trace: str
    user_id: str
    thread_id: str
    timestamp: str
    severity: str
    component: str
    context_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "error_message": self.error_message,
            "error_type": self.error_type,
            "stack_trace": self.stack_trace,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "component": self.component,
            "context_data": self.context_data
        }


class GitHubTestFixtures:
    """SSOT GitHub integration test fixtures"""
    
    @pytest.fixture(scope="session")
    def github_test_config(self) -> GitHubTestConfig:
        """GitHub test configuration from isolated environment"""
        env = IsolatedEnvironment()
        
        return GitHubTestConfig(
            enabled=env.get("GITHUB_INTEGRATION_TEST_ENABLED", "false").lower() == "true",
            token=env.get("GITHUB_TEST_TOKEN", ""),
            repo_owner=env.get("GITHUB_TEST_REPO_OWNER", ""),
            repo_name=env.get("GITHUB_TEST_REPO_NAME", ""),
            api_base_url=env.get("GITHUB_API_BASE_URL", "https://api.github.com"),
            webhook_url=env.get("GITHUB_TEST_WEBHOOK_URL", ""),
            rate_limit_buffer=int(env.get("GITHUB_RATE_LIMIT_BUFFER", "100")),
            max_issues_per_hour=int(env.get("GITHUB_MAX_ISSUES_PER_HOUR", "50")),
            test_label=env.get("GITHUB_TEST_LABEL", "automated-test"),
            cleanup_enabled=env.get("GITHUB_TEST_CLEANUP_ENABLED", "true").lower() == "true"
        )
    
    @pytest.fixture
    def github_error_context_factory(self):
        """Factory for creating GitHub error contexts"""
        def create_error_context(
            error_type: str = "TestError",
            error_message: str = "Test error message",
            user_id: str = "test_user",
            thread_id: str = None,
            severity: str = "MEDIUM",
            component: str = "TestComponent",
            **kwargs
        ) -> GitHubErrorContext:
            
            thread_id = thread_id or f"test_thread_{datetime.now().timestamp()}"
            timestamp = datetime.now(timezone.utc).isoformat()
            
            context_data = {
                "test_generated": True,
                "timestamp": timestamp,
                **kwargs.get("context_data", {})
            }
            
            return GitHubErrorContext(
                error_message=error_message,
                error_type=error_type,
                stack_trace=f"Traceback (test case):\n  File test.py, line 1, in test\n    raise {error_type}('{error_message}')",
                user_id=user_id,
                thread_id=thread_id,
                timestamp=timestamp,
                severity=severity,
                component=component,
                context_data=context_data
            )
        
        return create_error_context
    
    @pytest.fixture
    def mock_github_issue_factory(self):
        """Factory for creating mock GitHub issues"""
        def create_mock_issue(
            number: int = None,
            title: str = "Test Issue",
            body: str = "Test issue body", 
            state: str = "open",
            labels: List[str] = None,
            **kwargs
        ) -> MockGitHubIssue:
            
            number = number or int(datetime.now().timestamp() % 1000000)
            labels = labels or ["bug", "automated-test"]
            
            label_objects = [{"name": label, "color": "d73a4a"} for label in labels]
            
            return MockGitHubIssue(
                number=number,
                title=title,
                body=body,
                state=state,
                labels=label_objects,
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                html_url=f"https://github.com/test/repo/issues/{number}",
                user={"login": "test-user", "id": 12345},
                **kwargs
            )
        
        return create_mock_issue
    
    @pytest.fixture
    def mock_github_client(self, mock_github_issue_factory):
        """Mock GitHub client for unit testing"""
        client = Mock()
        
        # Mock repository info
        client.get_repository_info.return_value = {
            "name": "test-repo",
            "owner": {"login": "test-owner"},
            "permissions": {"push": True, "admin": False}
        }
        
        # Mock issue creation
        client.create_issue.return_value = mock_github_issue_factory()
        
        # Mock issue search
        client.search_issues.return_value = []
        
        # Mock health check
        client.health_check.return_value = True
        
        # Mock rate limit info
        client.get_rate_limit.return_value = {
            "remaining": 5000,
            "limit": 5000,
            "reset": int((datetime.now() + timedelta(hours=1)).timestamp())
        }
        
        return client
    
    @pytest.fixture
    def github_api_responses(self):
        """Standard GitHub API response fixtures"""
        return {
            "issue_created": {
                "number": 123,
                "title": "Test Issue",
                "body": "Test issue body",
                "state": "open",
                "labels": [{"name": "bug", "color": "d73a4a"}],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "html_url": "https://github.com/test/repo/issues/123",
                "user": {"login": "test-user", "id": 12345}
            },
            "rate_limit": {
                "resources": {
                    "core": {
                        "limit": 5000,
                        "remaining": 4999,
                        "reset": int((datetime.now() + timedelta(hours=1)).timestamp())
                    }
                }
            },
            "repository": {
                "name": "test-repo",
                "full_name": "test-owner/test-repo",
                "owner": {"login": "test-owner"},
                "permissions": {"admin": False, "push": True, "pull": True}
            },
            "search_issues": {
                "total_count": 0,
                "incomplete_results": False,
                "items": []
            }
        }
    
    @pytest.fixture
    def github_webhook_payload(self):
        """GitHub webhook payload fixtures"""
        return {
            "issues_opened": {
                "action": "opened",
                "issue": {
                    "number": 123,
                    "title": "Test Issue",
                    "body": "Test issue body",
                    "state": "open",
                    "html_url": "https://github.com/test/repo/issues/123"
                },
                "repository": {
                    "name": "test-repo",
                    "full_name": "test-owner/test-repo"
                }
            },
            "issues_closed": {
                "action": "closed",
                "issue": {
                    "number": 123,
                    "title": "Test Issue",
                    "state": "closed",
                    "html_url": "https://github.com/test/repo/issues/123"
                },
                "repository": {
                    "name": "test-repo",
                    "full_name": "test-owner/test-repo"
                }
            }
        }
    
    @pytest.fixture
    def github_error_scenarios(self):
        """Common GitHub error scenarios for testing"""
        return {
            "rate_limited": {
                "status_code": 403,
                "response": {
                    "message": "API rate limit exceeded for user.",
                    "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"
                }
            },
            "unauthorized": {
                "status_code": 401,
                "response": {
                    "message": "Bad credentials",
                    "documentation_url": "https://docs.github.com/rest"
                }
            },
            "forbidden": {
                "status_code": 403,
                "response": {
                    "message": "Resource not accessible by integration",
                    "documentation_url": "https://docs.github.com/rest"
                }
            },
            "not_found": {
                "status_code": 404,
                "response": {
                    "message": "Not Found",
                    "documentation_url": "https://docs.github.com/rest"
                }
            },
            "validation_failed": {
                "status_code": 422,
                "response": {
                    "message": "Validation Failed",
                    "errors": [
                        {
                            "field": "title",
                            "code": "missing_field"
                        }
                    ]
                }
            }
        }
    
    @pytest.fixture
    def github_test_cleanup(self, github_test_config):
        """Test cleanup handler for GitHub integration tests"""
        created_issues = []
        
        def register_for_cleanup(issue_number: int):
            """Register issue for cleanup after test"""
            created_issues.append(issue_number)
        
        yield register_for_cleanup
        
        # Cleanup created issues if enabled
        if github_test_config.cleanup_enabled and github_test_config.token:
            async def cleanup():
                async with httpx.AsyncClient() as client:
                    for issue_number in created_issues:
                        try:
                            # Close test issues
                            await client.patch(
                                f"{github_test_config.api_base_url}/repos/{github_test_config.repo_owner}/{github_test_config.repo_name}/issues/{issue_number}",
                                json={"state": "closed"},
                                headers={
                                    "Authorization": f"token {github_test_config.token}",
                                    "Accept": "application/vnd.github.v3+json"
                                }
                            )
                            
                            # Add cleanup comment
                            await client.post(
                                f"{github_test_config.api_base_url}/repos/{github_test_config.repo_owner}/{github_test_config.repo_name}/issues/{issue_number}/comments",
                                json={"body": "🧹 Automated test cleanup - issue closed after test completion"},
                                headers={
                                    "Authorization": f"token {github_test_config.token}",
                                    "Accept": "application/vnd.github.v3+json"
                                }
                            )
                        except Exception as e:
                            # Log cleanup failure but don't fail test
                            print(f"Warning: Failed to cleanup GitHub issue #{issue_number}: {e}")
            
            # Run cleanup
            try:
                asyncio.run(cleanup())
            except Exception as e:
                print(f"Warning: GitHub test cleanup failed: {e}")


# Export fixtures for use in test files
github_fixtures = GitHubTestFixtures()

# Make fixtures available for pytest discovery
github_test_config = github_fixtures.github_test_config
github_error_context_factory = github_fixtures.github_error_context_factory
mock_github_issue_factory = github_fixtures.mock_github_issue_factory
mock_github_client = github_fixtures.mock_github_client
github_api_responses = github_fixtures.github_api_responses
github_webhook_payload = github_fixtures.github_webhook_payload
github_error_scenarios = github_fixtures.github_error_scenarios
github_test_cleanup = github_fixtures.github_test_cleanup