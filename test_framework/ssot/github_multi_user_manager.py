"""
GitHub Multi-User Manager - Single Source of Truth for Multi-User GitHub Operations

This module provides secure multi-user isolation for GitHub operations, ensuring
proper user context management, data isolation, and enterprise-grade security
for GitHub integration in multi-tenant environments.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for multi-user GitHub operations.
All multi-user GitHub functionality across the entire codebase MUST use this manager.

Business Value: Enterprise - Security & Data Isolation
Enables enterprise usage with proper user isolation, security boundaries, and
data protection, ensuring GitHub operations maintain user context and permissions.

REQUIREMENTS per CLAUDE.md:
- Complete user context isolation per Factory pattern
- Security validation and authorization checks
- Data sanitization and privacy protection
- User-scoped operations and permissions
- Integration with SSOT authentication systems
"""

import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, asdict, field
from enum import Enum

from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.github_client import GitHubClient, GitHubIssue, GitHubComment, create_github_client
from test_framework.ssot.github_issue_manager import (
    GitHubIssueManager, ErrorContext, create_github_issue_manager
)
from test_framework.ssot.github_duplicate_detector import (
    GitHubDuplicateDetector, create_github_duplicate_detector
)
from test_framework.ssot.claude_github_command_executor import (
    ClaudeGitHubCommandExecutor, CommandResult, create_claude_github_command_executor
)


logger = logging.getLogger(__name__)


class UserPermissionLevel(Enum):
    """User permission levels for GitHub operations."""
    READ_ONLY = "read_only"
    CREATE_ISSUES = "create_issues"
    MANAGE_ISSUES = "manage_issues"
    ADMIN = "admin"


class IsolationLevel(Enum):
    """User isolation levels for multi-user operations."""
    STRICT = "strict"          # Complete isolation - users see only their own data
    TEAM = "team"             # Team-based isolation - users see team data
    ORGANIZATION = "organization"  # Org-level isolation - users see org data
    PUBLIC = "public"         # No isolation - users see all public data


@dataclass
class UserContext:
    """Comprehensive user context for GitHub operations."""
    user_id: str
    email: str
    display_name: str
    permission_level: UserPermissionLevel
    isolation_level: IsolationLevel
    organization_id: Optional[str] = None
    team_ids: List[str] = field(default_factory=list)
    session_id: Optional[str] = None
    authenticated_at: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default values."""
        if self.authenticated_at is None:
            self.authenticated_at = datetime.now(timezone.utc).isoformat()
        
        if self.expires_at is None:
            # Default 8 hour session
            expires_at = datetime.now(timezone.utc) + timedelta(hours=8)
            self.expires_at = expires_at.isoformat()
    
    def is_session_valid(self) -> bool:
        """Check if user session is still valid."""
        if not self.expires_at:
            return True  # No expiration set
        
        try:
            expires_dt = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) < expires_dt
        except ValueError:
            return False
    
    def can_create_issues(self) -> bool:
        """Check if user can create GitHub issues."""
        return self.permission_level in {
            UserPermissionLevel.CREATE_ISSUES,
            UserPermissionLevel.MANAGE_ISSUES,
            UserPermissionLevel.ADMIN
        }
    
    def can_manage_issues(self) -> bool:
        """Check if user can manage (update/close) GitHub issues."""
        return self.permission_level in {
            UserPermissionLevel.MANAGE_ISSUES,
            UserPermissionLevel.ADMIN
        }
    
    def can_admin_operations(self) -> bool:
        """Check if user can perform admin operations."""
        return self.permission_level == UserPermissionLevel.ADMIN
    
    def should_see_user_data(self, target_user_id: str) -> bool:
        """Check if user should see data from another user."""
        # Users always see their own data
        if target_user_id == self.user_id:
            return True
        
        # Isolation level determines visibility
        if self.isolation_level == IsolationLevel.STRICT:
            return False
        elif self.isolation_level == IsolationLevel.PUBLIC:
            return True
        
        # Team and organization isolation would require additional metadata
        # For now, default to strict isolation
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "permission_level": self.permission_level.value,
            "isolation_level": self.isolation_level.value,
            "organization_id": self.organization_id,
            "team_ids": self.team_ids,
            "session_id": self.session_id,
            "authenticated_at": self.authenticated_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata
        }


@dataclass
class UserScopedOperation:
    """Represents a user-scoped GitHub operation with full context."""
    user_context: UserContext
    operation_type: str
    operation_data: Dict[str, Any]
    timestamp: str
    operation_id: str
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        
        if not self.operation_id:
            # Generate unique operation ID
            operation_string = f"{self.user_context.user_id}_{self.operation_type}_{self.timestamp}"
            self.operation_id = hashlib.sha256(operation_string.encode()).hexdigest()[:16]


class DataSanitizer:
    """Sanitizes GitHub data to protect user privacy and sensitive information."""
    
    # Patterns for sensitive data detection
    SENSITIVE_PATTERNS = [
        # API Keys and tokens
        (r'\b[A-Za-z0-9]{20,}\b', '[API_KEY]'),
        # Email addresses
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
        # IP addresses
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]'),
        # URLs with credentials
        (r'https?://[^:\s]+:[^@\s]+@[^\s]+', '[AUTHENTICATED_URL]'),
        # Social Security Numbers (US format)
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),
        # Credit card numbers (basic pattern)
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD_NUMBER]'),
        # Phone numbers (basic pattern)
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]'),
        # Database connection strings
        (r'(postgresql|mysql|mongodb)://[^\s]+', '[DB_CONNECTION]'),
    ]
    
    # Sensitive field names to redact
    SENSITIVE_FIELDS = {
        'password', 'passwd', 'pwd', 'secret', 'key', 'token', 'auth',
        'credential', 'private', 'confidential', 'ssn', 'social_security',
        'credit_card', 'card_number', 'api_key', 'access_token', 'refresh_token'
    }
    
    def sanitize_text(self, text: str, user_context: UserContext) -> str:
        """
        Sanitize text content to protect sensitive information.
        
        Args:
            text: Original text content
            user_context: User context for personalized sanitization
            
        Returns:
            Sanitized text with sensitive data masked
        """
        if not text:
            return text
        
        sanitized = text
        
        # Apply pattern-based sanitization
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            import re
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        # Protect user-specific data
        sanitized = self._sanitize_user_data(sanitized, user_context)
        
        return sanitized
    
    def sanitize_dict(self, data: Dict[str, Any], user_context: UserContext) -> Dict[str, Any]:
        """
        Sanitize dictionary data recursively.
        
        Args:
            data: Original dictionary data
            user_context: User context for personalized sanitization
            
        Returns:
            Sanitized dictionary with sensitive data masked
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if field name indicates sensitive data
            if any(sensitive_field in key_lower for sensitive_field in self.SENSITIVE_FIELDS):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_text(value, user_context)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value, user_context)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_dict(item, user_context) if isinstance(item, dict)
                    else self.sanitize_text(item, user_context) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_user_data(self, text: str, user_context: UserContext) -> str:
        """Sanitize user-specific data based on context."""
        import re
        
        # Mask other user IDs if strict isolation
        if user_context.isolation_level == IsolationLevel.STRICT:
            # Pattern for user IDs (assuming they follow common patterns)
            user_id_pattern = r'\buser_[a-zA-Z0-9_-]+\b'
            
            def replace_user_id(match):
                user_id = match.group(0)
                # Don't mask current user's ID
                if user_context.user_id in user_id:
                    return user_id
                return '[OTHER_USER_ID]'
            
            text = re.sub(user_id_pattern, replace_user_id, text, flags=re.IGNORECASE)
        
        return text


class UserPermissionValidator:
    """Validates user permissions for GitHub operations."""
    
    def __init__(self):
        self.sanitizer = DataSanitizer()
    
    def validate_operation(
        self,
        user_context: UserContext,
        operation_type: str,
        operation_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if user can perform the requested operation.
        
        Args:
            user_context: User context
            operation_type: Type of operation (create_issue, update_issue, etc.)
            operation_data: Operation-specific data
            
        Returns:
            Tuple of (is_allowed: bool, error_message: Optional[str])
        """
        # Check session validity
        if not user_context.is_session_valid():
            return False, "User session has expired"
        
        # Check operation-specific permissions
        if operation_type == "create_issue":
            if not user_context.can_create_issues():
                return False, "User does not have permission to create issues"
        
        elif operation_type in ["update_issue", "close_issue", "add_comment"]:
            if not user_context.can_manage_issues():
                return False, "User does not have permission to manage issues"
            
            # Check if user can modify specific issue
            issue_owner = operation_data.get('issue_owner')
            if issue_owner and not user_context.should_see_user_data(issue_owner):
                return False, "User does not have permission to modify this issue"
        
        elif operation_type in ["admin_operation", "bulk_operation"]:
            if not user_context.can_admin_operations():
                return False, "User does not have admin permissions"
        
        return True, None
    
    def filter_visible_issues(
        self,
        user_context: UserContext,
        issues: List[GitHubIssue]
    ) -> List[GitHubIssue]:
        """
        Filter issues based on user's visibility permissions.
        
        Args:
            user_context: User context
            issues: List of GitHub issues
            
        Returns:
            Filtered list of issues the user can see
        """
        visible_issues = []
        
        for issue in issues:
            # Check if user should see this issue
            issue_visible = True
            
            # Extract user information from issue (if available)
            issue_creator = self._extract_issue_creator(issue)
            
            if issue_creator and not user_context.should_see_user_data(issue_creator):
                issue_visible = False
            
            if issue_visible:
                # Sanitize issue content
                sanitized_issue = self._sanitize_issue(issue, user_context)
                visible_issues.append(sanitized_issue)
        
        return visible_issues
    
    def _extract_issue_creator(self, issue: GitHubIssue) -> Optional[str]:
        """Extract issue creator information."""
        # Look for user ID in issue body or title
        import re
        
        # Pattern for user IDs in issue content
        user_id_pattern = r'\b(user_[a-zA-Z0-9_-]+)\b'
        
        # Check issue body first
        if issue.body:
            matches = re.findall(user_id_pattern, issue.body, re.IGNORECASE)
            if matches:
                return matches[0]
        
        # Check issue title
        matches = re.findall(user_id_pattern, issue.title, re.IGNORECASE)
        if matches:
            return matches[0]
        
        return None
    
    def _sanitize_issue(self, issue: GitHubIssue, user_context: UserContext) -> GitHubIssue:
        """Sanitize GitHub issue content for user visibility."""
        # Create sanitized copy
        sanitized_data = self.sanitizer.sanitize_dict(issue.to_dict(), user_context)
        
        # Create new GitHubIssue with sanitized data
        return GitHubIssue.from_github_api_response(sanitized_data)


class GitHubMultiUserManager:
    """
    Single Source of Truth GitHub Multi-User Manager
    
    This is the CANONICAL multi-user management system that provides secure
    user isolation, permission validation, and enterprise-grade multi-tenant
    support for GitHub operations.
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        default_isolation_level: IsolationLevel = IsolationLevel.STRICT,
        session_timeout_hours: int = 8
    ):
        """
        Initialize GitHub multi-user manager.
        
        Args:
            github_token: GitHub token for API access
            default_isolation_level: Default isolation level for new users
            session_timeout_hours: Default session timeout in hours
        """
        self._env = IsolatedEnvironment()
        self._github_token = github_token or self._env.get("GITHUB_TOKEN", "")
        self._default_isolation_level = default_isolation_level
        self._session_timeout_hours = session_timeout_hours
        
        # Initialize components
        self._permission_validator = UserPermissionValidator()
        self._active_users: Dict[str, UserContext] = {}
        self._user_clients: Dict[str, GitHubClient] = {}
        self._user_managers: Dict[str, GitHubIssueManager] = {}
        self._user_executors: Dict[str, ClaudeGitHubCommandExecutor] = {}
        
        logger.info("Initialized GitHub multi-user manager")
    
    # === USER MANAGEMENT ===
    
    def register_user(
        self,
        user_id: str,
        email: str,
        display_name: str,
        permission_level: UserPermissionLevel = UserPermissionLevel.CREATE_ISSUES,
        isolation_level: Optional[IsolationLevel] = None,
        organization_id: Optional[str] = None,
        team_ids: Optional[List[str]] = None
    ) -> UserContext:
        """
        Register a new user for GitHub operations.
        
        Args:
            user_id: Unique user identifier
            email: User email address
            display_name: User display name
            permission_level: User permission level
            isolation_level: User isolation level (optional, uses default)
            organization_id: Organization ID (optional)
            team_ids: List of team IDs (optional)
            
        Returns:
            UserContext for the registered user
        """
        if isolation_level is None:
            isolation_level = self._default_isolation_level
        
        # Create user context
        user_context = UserContext(
            user_id=user_id,
            email=email,
            display_name=display_name,
            permission_level=permission_level,
            isolation_level=isolation_level,
            organization_id=organization_id,
            team_ids=team_ids or []
        )
        
        # Store user context
        self._active_users[user_id] = user_context
        
        logger.info(f"Registered user: {user_id} with permission level: {permission_level.value}")
        return user_context
    
    def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """Get user context by user ID."""
        return self._active_users.get(user_id)
    
    def is_user_session_valid(self, user_id: str) -> bool:
        """Check if user session is valid."""
        user_context = self.get_user_context(user_id)
        return user_context is not None and user_context.is_session_valid()
    
    def refresh_user_session(self, user_id: str) -> bool:
        """Refresh user session timeout."""
        user_context = self.get_user_context(user_id)
        if user_context:
            # Extend session by default timeout
            new_expires_at = datetime.now(timezone.utc) + timedelta(hours=self._session_timeout_hours)
            user_context.expires_at = new_expires_at.isoformat()
            return True
        return False
    
    def unregister_user(self, user_id: str) -> bool:
        """Unregister user and clean up resources."""
        if user_id in self._active_users:
            # Clean up user-specific clients and managers
            if user_id in self._user_clients:
                # Note: In production, would properly close async clients
                del self._user_clients[user_id]
            
            if user_id in self._user_managers:
                del self._user_managers[user_id]
            
            if user_id in self._user_executors:
                del self._user_executors[user_id]
            
            # Remove user context
            del self._active_users[user_id]
            
            logger.info(f"Unregistered user: {user_id}")
            return True
        
        return False
    
    # === USER-SCOPED GITHUB OPERATIONS ===
    
    async def create_user_scoped_issue(
        self,
        user_id: str,
        error_context: ErrorContext,
        repo_owner: str,
        repo_name: str,
        check_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Create GitHub issue with user context and isolation.
        
        Args:
            user_id: User ID for operation
            error_context: Error context for issue creation
            repo_owner: Repository owner
            repo_name: Repository name
            check_duplicates: Whether to check for duplicates
            
        Returns:
            Dictionary with operation result
        """
        # Validate user and permissions
        user_context = self.get_user_context(user_id)
        if not user_context:
            return {"success": False, "error": "User not found"}
        
        is_allowed, error_msg = self._permission_validator.validate_operation(
            user_context, "create_issue", {"repo_owner": repo_owner, "repo_name": repo_name}
        )
        
        if not is_allowed:
            return {"success": False, "error": error_msg}
        
        # Get user-scoped issue manager
        issue_manager = await self._get_user_issue_manager(user_id, repo_owner, repo_name)
        
        # Create issue with user context
        try:
            async with issue_manager:
                issue = await issue_manager.create_issue_from_error_context(
                    error_context, check_duplicates
                )
                
                return {
                    "success": True,
                    "issue_number": issue.number,
                    "issue_url": issue.html_url,
                    "issue": issue.to_dict()
                }
        
        except Exception as e:
            logger.error(f"Error creating user-scoped issue for {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_visible_issues(
        self,
        user_id: str,
        repo_owner: str,
        repo_name: str,
        query: Optional[str] = None,
        state: str = "open"
    ) -> Dict[str, Any]:
        """
        Get issues visible to user based on isolation level.
        
        Args:
            user_id: User ID for operation
            repo_owner: Repository owner
            repo_name: Repository name
            query: Search query (optional)
            state: Issue state filter
            
        Returns:
            Dictionary with filtered issues
        """
        # Validate user
        user_context = self.get_user_context(user_id)
        if not user_context:
            return {"success": False, "error": "User not found"}
        
        # Get user-scoped GitHub client
        github_client = await self._get_user_github_client(user_id)
        
        try:
            async with github_client:
                # Search for issues
                if query:
                    issues = await github_client.search_issues(
                        query=query,
                        repo_owner=repo_owner,
                        repo_name=repo_name,
                        state=state
                    )
                else:
                    # Get all issues for repo
                    issues = await github_client.search_issues(
                        query="is:issue",
                        repo_owner=repo_owner,
                        repo_name=repo_name,
                        state=state
                    )
                
                # Filter issues based on user visibility
                visible_issues = self._permission_validator.filter_visible_issues(
                    user_context, issues
                )
                
                return {
                    "success": True,
                    "issues": [issue.to_dict() for issue in visible_issues],
                    "total_found": len(issues),
                    "visible_count": len(visible_issues)
                }
        
        except Exception as e:
            logger.error(f"Error getting user visible issues for {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_user_scoped_command(
        self,
        user_id: str,
        command: str,
        repo_owner: str,
        repo_name: str,
        thread_context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        Execute Claude GitHub command with user context.
        
        Args:
            user_id: User ID for operation
            command: Claude command to execute
            repo_owner: Repository owner
            repo_name: Repository name
            thread_context: Thread context (optional)
            
        Returns:
            CommandResult with execution outcome
        """
        # Validate user
        user_context = self.get_user_context(user_id)
        if not user_context:
            return CommandResult(
                success=False,
                command_type="permission_error",
                message="User not found",
                error_details=f"User {user_id} is not registered"
            )
        
        # Get user-scoped command executor
        executor = await self._get_user_command_executor(user_id, repo_owner, repo_name)
        
        # Execute command with user context
        try:
            async with executor:
                return await executor.execute_command(
                    command,
                    user_context=user_context.to_dict(),
                    thread_context=thread_context
                )
        
        except Exception as e:
            logger.error(f"Error executing user command for {user_id}: {e}")
            return CommandResult(
                success=False,
                command_type="execution_error",
                message="Command execution failed",
                error_details=str(e)
            )
    
    # === INTERNAL HELPER METHODS ===
    
    async def _get_user_github_client(self, user_id: str) -> GitHubClient:
        """Get or create user-scoped GitHub client."""
        if user_id not in self._user_clients:
            self._user_clients[user_id] = create_github_client(user_context=user_id)
        
        return self._user_clients[user_id]
    
    async def _get_user_issue_manager(
        self,
        user_id: str,
        repo_owner: str,
        repo_name: str
    ) -> GitHubIssueManager:
        """Get or create user-scoped issue manager."""
        manager_key = f"{user_id}_{repo_owner}_{repo_name}"
        
        if manager_key not in self._user_managers:
            self._user_managers[manager_key] = create_github_issue_manager(
                user_context=user_id,
                repo_owner=repo_owner,
                repo_name=repo_name
            )
        
        return self._user_managers[manager_key]
    
    async def _get_user_command_executor(
        self,
        user_id: str,
        repo_owner: str,
        repo_name: str
    ) -> ClaudeGitHubCommandExecutor:
        """Get or create user-scoped command executor."""
        executor_key = f"{user_id}_{repo_owner}_{repo_name}"
        
        if executor_key not in self._user_executors:
            self._user_executors[executor_key] = create_claude_github_command_executor(
                user_context=user_id,
                repo_owner=repo_owner,
                repo_name=repo_name
            )
        
        return self._user_executors[executor_key]
    
    # === UTILITY METHODS ===
    
    def get_active_user_count(self) -> int:
        """Get number of active users."""
        return len(self._active_users)
    
    def get_active_users(self) -> List[str]:
        """Get list of active user IDs."""
        return list(self._active_users.keys())
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired user sessions and return count of cleaned sessions."""
        expired_users = []
        
        for user_id, user_context in self._active_users.items():
            if not user_context.is_session_valid():
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.unregister_user(user_id)
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired user sessions")
        
        return len(expired_users)


# === SSOT FACTORY FUNCTIONS ===

def create_github_multi_user_manager(
    github_token: Optional[str] = None,
    default_isolation_level: IsolationLevel = IsolationLevel.STRICT,
    session_timeout_hours: int = 8
) -> GitHubMultiUserManager:
    """
    Create GitHub multi-user manager using SSOT patterns.
    
    This is the CANONICAL way to create GitHub multi-user managers.
    
    Args:
        github_token: GitHub token for API access
        default_isolation_level: Default isolation level for new users
        session_timeout_hours: Default session timeout in hours
        
    Returns:
        Configured GitHubMultiUserManager
    """
    return GitHubMultiUserManager(
        github_token=github_token,
        default_isolation_level=default_isolation_level,
        session_timeout_hours=session_timeout_hours
    )