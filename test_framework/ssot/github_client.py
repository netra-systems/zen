"""
GitHub Client - Single Source of Truth for GitHub API Operations

This module provides the canonical GitHub API client with real authentication,
rate limiting, error handling, and all core GitHub operations.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for GitHub API interactions.
All GitHub operations across the entire codebase MUST use this client.

Business Value: Platform/Internal - System Stability & Development Velocity
Enables automated issue tracking, reduces manual developer overhead, and provides
proper GitHub integration for enterprise usage.

REQUIREMENTS per CLAUDE.md:
- Real GitHub API integration (no mocks in production use)
- IsolatedEnvironment for all configuration access
- Proper error handling and rate limiting
- Multi-user isolation support
- Business-focused functionality
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import aiohttp
from aiohttp import ClientTimeout, ClientError

from shared.isolated_environment import IsolatedEnvironment
from test_framework.config.github_test_config import GitHubTestConfiguration


logger = logging.getLogger(__name__)


class GitHubErrorType(Enum):
    """GitHub API error types for categorization."""
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION = "validation"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass
class GitHubIssue:
    """GitHub issue data structure."""
    number: int
    title: str
    body: str
    state: str
    labels: List[str]
    created_at: str
    updated_at: str
    html_url: str
    user: Optional[Dict[str, Any]] = None
    assignees: List[Dict[str, Any]] = None
    milestone: Optional[Dict[str, Any]] = None
    comments: int = 0
    closed_at: Optional[str] = None
    
    @classmethod
    def from_github_api_response(cls, response_data: Dict[str, Any]) -> "GitHubIssue":
        """Create GitHubIssue from GitHub API response."""
        return cls(
            number=response_data["number"],
            title=response_data["title"],
            body=response_data["body"] or "",
            state=response_data["state"],
            labels=[label["name"] for label in response_data.get("labels", [])],
            created_at=response_data["created_at"],
            updated_at=response_data["updated_at"],
            html_url=response_data["html_url"],
            user=response_data.get("user"),
            assignees=response_data.get("assignees", []),
            milestone=response_data.get("milestone"),
            comments=response_data.get("comments", 0),
            closed_at=response_data.get("closed_at")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class GitHubComment:
    """GitHub comment data structure."""
    id: int
    body: str
    user: Dict[str, Any]
    created_at: str
    updated_at: str
    html_url: str
    
    @classmethod
    def from_github_api_response(cls, response_data: Dict[str, Any]) -> "GitHubComment":
        """Create GitHubComment from GitHub API response."""
        return cls(
            id=response_data["id"],
            body=response_data["body"],
            user=response_data["user"],
            created_at=response_data["created_at"],
            updated_at=response_data["updated_at"],
            html_url=response_data["html_url"]
        )


class GitHubAPIError(Exception):
    """GitHub API error with detailed information."""
    
    def __init__(
        self,
        message: str,
        error_type: GitHubErrorType,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code
        self.response_data = response_data or {}
        self.retry_after = retry_after
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def __str__(self) -> str:
        return f"GitHubAPIError({self.error_type.value}): {self.args[0]}"
    
    def is_retryable(self) -> bool:
        """Check if this error type is retryable."""
        retryable_types = {
            GitHubErrorType.RATE_LIMIT,
            GitHubErrorType.SERVER_ERROR,
            GitHubErrorType.NETWORK_ERROR
        }
        return self.error_type in retryable_types


class GitHubRateLimitTracker:
    """Track GitHub API rate limits per user/context."""
    
    def __init__(self):
        self._limits: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, context: str) -> Tuple[bool, Optional[int]]:
        """
        Check if we're within rate limits for a context.
        
        Returns:
            Tuple of (can_proceed: bool, wait_seconds: Optional[int])
        """
        async with self._lock:
            limit_data = self._limits.get(context, {})
            
            if not limit_data:
                return True, None
            
            reset_time = limit_data.get("reset_time", 0)
            remaining = limit_data.get("remaining", 5000)
            
            current_time = time.time()
            if current_time >= reset_time:
                # Rate limit has reset
                return True, None
            
            if remaining <= 0:
                # Rate limited
                wait_time = max(0, int(reset_time - current_time))
                return False, wait_time
            
            return True, None
    
    async def update_rate_limit(
        self,
        context: str,
        remaining: int,
        reset_time: int,
        limit: int
    ) -> None:
        """Update rate limit information for a context."""
        async with self._lock:
            self._limits[context] = {
                "remaining": remaining,
                "reset_time": reset_time,
                "limit": limit,
                "updated_at": time.time()
            }


class GitHubClient:
    """
    Single Source of Truth GitHub API Client
    
    This is the CANONICAL GitHub API client that all GitHub operations
    must use. Provides real API integration with proper authentication,
    rate limiting, error handling, and business-focused functionality.
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        config: Optional[GitHubTestConfiguration] = None,
        user_context: Optional[str] = None
    ):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token (optional, will use config or env)
            config: GitHub configuration (optional, will create from environment)
            user_context: User context for rate limiting and isolation
        """
        # Initialize configuration using SSOT patterns
        if config is None:
            self._env = IsolatedEnvironment()
            self._config = GitHubTestConfiguration.from_isolated_environment(self._env)
        else:
            self._config = config
            self._env = IsolatedEnvironment()
        
        # Override token if provided
        if token:
            self._config.token = token
        
        # Validate configuration
        validation_errors = self._config.validate()
        if validation_errors:
            raise GitHubAPIError(
                f"Invalid GitHub configuration: {'; '.join(validation_errors)}",
                GitHubErrorType.VALIDATION
            )
        
        # Initialize components
        self._user_context = user_context or "default"
        self._rate_limiter = GitHubRateLimitTracker()
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_call_count = 0
        self._start_time = time.time()
        
        logger.info(f"Initialized GitHub client for context: {self._user_context}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is created."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self._config.timeout_seconds)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._config.get_api_headers()
            )
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make authenticated GitHub API request with rate limiting and error handling.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            url: API endpoint URL
            data: Request body data
            params: Query parameters
            retry_count: Current retry attempt
            
        Returns:
            JSON response data
            
        Raises:
            GitHubAPIError: For API errors with proper categorization
        """
        await self._ensure_session()
        
        # Check rate limits
        can_proceed, wait_time = await self._rate_limiter.check_rate_limit(self._user_context)
        if not can_proceed and wait_time:
            if wait_time > 60:  # Don't wait more than 1 minute
                raise GitHubAPIError(
                    f"Rate limit exceeded, wait time too long: {wait_time}s",
                    GitHubErrorType.RATE_LIMIT,
                    retry_after=wait_time
                )
            logger.warning(f"Rate limited, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
        
        # Check API call limits
        self._api_call_count += 1
        if self._api_call_count > self._config.max_api_calls_per_test:
            raise GitHubAPIError(
                f"Exceeded max API calls per test: {self._config.max_api_calls_per_test}",
                GitHubErrorType.RATE_LIMIT
            )
        
        try:
            # Make the request
            kwargs = {
                "url": url,
                "params": params
            }
            
            if data is not None:
                kwargs["json"] = data
            
            logger.debug(f"GitHub API {method} request to {url}")
            
            async with self._session.request(method, **kwargs) as response:
                # Update rate limiting info from headers
                await self._update_rate_limit_from_headers(response.headers)
                
                # Get response data
                try:
                    response_data = await response.json()
                except aiohttp.ContentTypeError:
                    response_data = {"message": await response.text()}
                
                # Handle different status codes
                if response.status == 200 or response.status == 201:
                    logger.debug(f"GitHub API request successful: {response.status}")
                    return response_data
                
                elif response.status == 401:
                    raise GitHubAPIError(
                        "Authentication failed - invalid or expired token",
                        GitHubErrorType.AUTHENTICATION,
                        status_code=response.status,
                        response_data=response_data
                    )
                
                elif response.status == 403:
                    if "rate limit" in response_data.get("message", "").lower():
                        retry_after = response.headers.get("Retry-After")
                        raise GitHubAPIError(
                            f"Rate limit exceeded: {response_data.get('message', 'Unknown')}",
                            GitHubErrorType.RATE_LIMIT,
                            status_code=response.status,
                            response_data=response_data,
                            retry_after=int(retry_after) if retry_after else None
                        )
                    else:
                        raise GitHubAPIError(
                            f"Permission denied: {response_data.get('message', 'Unknown')}",
                            GitHubErrorType.PERMISSION_DENIED,
                            status_code=response.status,
                            response_data=response_data
                        )
                
                elif response.status == 404:
                    raise GitHubAPIError(
                        f"Resource not found: {response_data.get('message', 'Unknown')}",
                        GitHubErrorType.NOT_FOUND,
                        status_code=response.status,
                        response_data=response_data
                    )
                
                elif response.status == 422:
                    errors = response_data.get("errors", [])
                    error_messages = [error.get("message", str(error)) for error in errors]
                    raise GitHubAPIError(
                        f"Validation error: {'; '.join(error_messages)}",
                        GitHubErrorType.VALIDATION,
                        status_code=response.status,
                        response_data=response_data
                    )
                
                elif response.status >= 500:
                    error_message = f"GitHub server error: {response_data.get('message', 'Unknown')}"
                    error = GitHubAPIError(
                        error_message,
                        GitHubErrorType.SERVER_ERROR,
                        status_code=response.status,
                        response_data=response_data
                    )
                    
                    # Retry server errors
                    if retry_count < self._config.retry_attempts:
                        logger.warning(f"Server error, retrying in {self._config.retry_delay_seconds}s")
                        await asyncio.sleep(self._config.retry_delay_seconds)
                        return await self._make_request(method, url, data, params, retry_count + 1)
                    
                    raise error
                
                else:
                    raise GitHubAPIError(
                        f"Unexpected response: {response.status} - {response_data.get('message', 'Unknown')}",
                        GitHubErrorType.UNKNOWN,
                        status_code=response.status,
                        response_data=response_data
                    )
        
        except ClientError as e:
            error = GitHubAPIError(
                f"Network error: {str(e)}",
                GitHubErrorType.NETWORK_ERROR
            )
            
            # Retry network errors
            if retry_count < self._config.retry_attempts:
                logger.warning(f"Network error, retrying in {self._config.retry_delay_seconds}s")
                await asyncio.sleep(self._config.retry_delay_seconds)
                return await self._make_request(method, url, data, params, retry_count + 1)
            
            raise error
        
        except asyncio.TimeoutError:
            error = GitHubAPIError(
                f"Request timeout after {self._config.timeout_seconds}s",
                GitHubErrorType.NETWORK_ERROR
            )
            
            # Retry timeouts
            if retry_count < self._config.retry_attempts:
                logger.warning("Request timeout, retrying")
                await asyncio.sleep(self._config.retry_delay_seconds)
                return await self._make_request(method, url, data, params, retry_count + 1)
            
            raise error
    
    async def _update_rate_limit_from_headers(self, headers: Dict[str, str]) -> None:
        """Update rate limiting information from response headers."""
        try:
            remaining = headers.get("X-RateLimit-Remaining")
            reset_time = headers.get("X-RateLimit-Reset")
            limit = headers.get("X-RateLimit-Limit")
            
            if remaining is not None and reset_time is not None and limit is not None:
                await self._rate_limiter.update_rate_limit(
                    self._user_context,
                    int(remaining),
                    int(reset_time),
                    int(limit)
                )
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")
    
    # === CORE GITHUB API METHODS ===
    
    async def validate_credentials(self) -> bool:
        """
        Validate GitHub credentials and permissions.
        
        Returns:
            True if credentials are valid and have required permissions
        """
        try:
            user_data = await self._make_request("GET", f"{self._config.api_base_url}/user")
            logger.info(f"GitHub credentials valid for user: {user_data.get('login')}")
            return True
        except GitHubAPIError as e:
            if e.error_type == GitHubErrorType.AUTHENTICATION:
                logger.error("GitHub credentials are invalid")
                return False
            raise
    
    async def create_issue(
        self,
        repo_owner: str,
        repo_name: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> GitHubIssue:
        """
        Create a new GitHub issue.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            title: Issue title
            body: Issue body/description
            labels: List of label names
            assignees: List of assignee usernames
            milestone: Milestone number
            
        Returns:
            Created GitHubIssue
        """
        url = f"{self._config.api_base_url}/repos/{repo_owner}/{repo_name}/issues"
        
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        
        if assignees:
            data["assignees"] = assignees
        
        if milestone:
            data["milestone"] = milestone
        
        response_data = await self._make_request("POST", url, data=data)
        issue = GitHubIssue.from_github_api_response(response_data)
        
        logger.info(f"Created GitHub issue #{issue.number}: {issue.title}")
        return issue
    
    async def get_issue(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int
    ) -> GitHubIssue:
        """
        Get a specific GitHub issue.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            issue_number: Issue number
            
        Returns:
            GitHubIssue
        """
        url = f"{self._config.api_base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}"
        response_data = await self._make_request("GET", url)
        
        return GitHubIssue.from_github_api_response(response_data)
    
    async def update_issue(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> GitHubIssue:
        """
        Update a GitHub issue.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            issue_number: Issue number
            title: New title (optional)
            body: New body (optional)
            state: New state ('open' or 'closed') (optional)
            labels: New labels list (optional)
            assignees: New assignees list (optional)
            
        Returns:
            Updated GitHubIssue
        """
        url = f"{self._config.api_base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}"
        
        data = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None:
            data["state"] = state
        if labels is not None:
            data["labels"] = labels
        if assignees is not None:
            data["assignees"] = assignees
        
        response_data = await self._make_request("PATCH", url, data=data)
        
        logger.info(f"Updated GitHub issue #{issue_number}")
        return GitHubIssue.from_github_api_response(response_data)
    
    async def close_issue(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int
    ) -> GitHubIssue:
        """
        Close a GitHub issue.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            issue_number: Issue number
            
        Returns:
            Closed GitHubIssue
        """
        return await self.update_issue(
            repo_owner, repo_name, issue_number, state="closed"
        )
    
    async def search_issues(
        self,
        query: str,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        state: str = "open",
        labels: Optional[str] = None,
        sort: str = "created",
        order: str = "desc",
        per_page: int = 30
    ) -> List[GitHubIssue]:
        """
        Search GitHub issues.
        
        Args:
            query: Search query
            repo_owner: Repository owner (optional)
            repo_name: Repository name (optional)
            state: Issue state ('open', 'closed', 'all')
            labels: Label filter
            sort: Sort field ('created', 'updated', 'comments')
            order: Sort order ('asc', 'desc')
            per_page: Results per page (max 100)
            
        Returns:
            List of matching GitHubIssues
        """
        # Build search query
        search_terms = [query]
        
        if repo_owner and repo_name:
            search_terms.append(f"repo:{repo_owner}/{repo_name}")
        
        if state != "all":
            search_terms.append(f"state:{state}")
        
        if labels:
            search_terms.append(f"label:{labels}")
        
        search_terms.append("type:issue")
        
        search_query = " ".join(search_terms)
        
        url = f"{self._config.api_base_url}/search/issues"
        params = {
            "q": search_query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100)
        }
        
        response_data = await self._make_request("GET", url, params=params)
        
        issues = []
        for item in response_data.get("items", []):
            issues.append(GitHubIssue.from_github_api_response(item))
        
        logger.info(f"Found {len(issues)} issues matching query: {search_query}")
        return issues
    
    async def add_comment(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        body: str
    ) -> GitHubComment:
        """
        Add a comment to a GitHub issue.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            issue_number: Issue number
            body: Comment body
            
        Returns:
            Created GitHubComment
        """
        url = f"{self._config.api_base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
        
        data = {"body": body}
        response_data = await self._make_request("POST", url, data=data)
        
        comment = GitHubComment.from_github_api_response(response_data)
        logger.info(f"Added comment to issue #{issue_number}")
        return comment
    
    async def get_comments(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int
    ) -> List[GitHubComment]:
        """
        Get all comments for a GitHub issue.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            issue_number: Issue number
            
        Returns:
            List of GitHubComments
        """
        url = f"{self._config.api_base_url}/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
        response_data = await self._make_request("GET", url)
        
        comments = []
        for comment_data in response_data:
            comments.append(GitHubComment.from_github_api_response(comment_data))
        
        return comments
    
    async def update_comment(
        self,
        repo_owner: str,
        repo_name: str,
        comment_id: int,
        body: str
    ) -> GitHubComment:
        """
        Update a GitHub issue comment.
        
        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            comment_id: Comment ID
            body: New comment body
            
        Returns:
            Updated GitHubComment
        """
        url = f"{self._config.api_base_url}/repos/{repo_owner}/{repo_name}/issues/comments/{comment_id}"
        
        data = {"body": body}
        response_data = await self._make_request("PATCH", url, data=data)
        
        comment = GitHubComment.from_github_api_response(response_data)
        logger.info(f"Updated comment {comment_id}")
        return comment
    
    # === UTILITY METHODS ===
    
    def get_api_call_count(self) -> int:
        """Get the number of API calls made by this client."""
        return self._api_call_count
    
    def get_uptime(self) -> float:
        """Get client uptime in seconds."""
        return time.time() - self._start_time
    
    def get_config(self) -> GitHubTestConfiguration:
        """Get the client configuration."""
        return self._config
    
    def get_user_context(self) -> str:
        """Get the user context for this client."""
        return self._user_context


# === SSOT FACTORY FUNCTIONS ===

def create_github_client(
    user_context: Optional[str] = None,
    config_type: str = "default"
) -> GitHubClient:
    """
    Create GitHub client using SSOT configuration patterns.
    
    This is the CANONICAL way to create GitHub clients.
    
    Args:
        user_context: User context for isolation
        config_type: Configuration type ("unit", "integration", "e2e", "default")
        
    Returns:
        Configured GitHubClient
    """
    from test_framework.config.github_test_config import get_github_test_config
    
    config = get_github_test_config(config_type)
    return GitHubClient(config=config, user_context=user_context)


async def validate_github_environment() -> Tuple[bool, List[str]]:
    """
    Validate GitHub environment configuration.
    
    Returns:
        Tuple of (is_valid: bool, error_messages: List[str])
    """
    try:
        client = create_github_client()
        async with client:
            is_valid = await client.validate_credentials()
            if is_valid:
                return True, []
            else:
                return False, ["GitHub credentials validation failed"]
    except GitHubAPIError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Unexpected error validating GitHub environment: {str(e)}"]