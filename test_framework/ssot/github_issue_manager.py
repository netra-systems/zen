"""
GitHub Issue Manager - Single Source of Truth for GitHub Issue Business Logic

This module provides the canonical GitHub issue management system with error
categorization, template generation, and complete issue lifecycle management.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for GitHub issue business logic.
All GitHub issue operations across the entire codebase MUST use this manager.

Business Value: Platform/Internal - System Stability & Development Velocity
Automates error tracking, provides structured issue management, and reduces
manual developer overhead by intelligently categorizing and managing issues.

REQUIREMENTS per CLAUDE.md:
- Real business logic for error categorization and issue management
- Template generation for structured issue creation
- Error fingerprinting for duplicate detection
- Multi-user context support
- Integration with SSOT GitHub client
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum

from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.github_client import (
    GitHubClient, GitHubIssue, GitHubComment, GitHubAPIError, GitHubErrorType,
    create_github_client
)


logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ErrorCategory(Enum):
    """Error categories for organization."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    NETWORK = "network"
    VALIDATION = "validation"
    DEPENDENCY = "dependency"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    BUSINESS_LOGIC = "business_logic"
    INTEGRATION = "integration"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Structured error context for issue creation."""
    error_message: str
    error_type: str
    stack_trace: str
    user_id: str
    thread_id: Optional[str] = None
    timestamp: Optional[str] = None
    context_data: Dict[str, Any] = None
    service: Optional[str] = None
    environment: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        
        if self.context_data is None:
            self.context_data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def generate_fingerprint(self) -> str:
        """
        Generate unique fingerprint for error deduplication.
        
        Returns:
            SHA256 hash representing the error's unique characteristics
        """
        # Key components that make an error unique
        fingerprint_data = {
            "error_type": self.error_type,
            "error_message": self._normalize_error_message(self.error_message),
            "service": self.service or "unknown",
            "environment": self.environment or "unknown"
        }
        
        # Include relevant stack trace information (normalized)
        if self.stack_trace:
            fingerprint_data["stack_trace_signature"] = self._extract_stack_signature(self.stack_trace)
        
        # Create deterministic hash
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
    
    def _normalize_error_message(self, message: str) -> str:
        """Normalize error message for consistent fingerprinting."""
        # Remove user-specific data, IDs, timestamps, etc.
        normalized = re.sub(r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '[TIMESTAMP]', message)
        normalized = re.sub(r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', '[UUID]', normalized)
        normalized = re.sub(r'\b\d+\b', '[NUMBER]', normalized)
        normalized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', normalized)
        normalized = re.sub(r'/[A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+/', '/[PATH]/', normalized)
        
        return normalized.strip()
    
    def _extract_stack_signature(self, stack_trace: str) -> str:
        """Extract meaningful signature from stack trace."""
        # Get the last few meaningful stack frames
        lines = stack_trace.split('\n')
        relevant_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(' ') and ('File "' in line or 'at ' in line):
                # Normalize file paths and line numbers
                normalized_line = re.sub(r'File "([^"]+)"', 'File "[PATH]"', line)
                normalized_line = re.sub(r', line \d+', ', line [LINE]', normalized_line)
                relevant_lines.append(normalized_line)
        
        return '|'.join(relevant_lines[-3:])  # Last 3 frames


@dataclass 
class IssueCategorization:
    """Issue categorization result."""
    severity: ErrorSeverity
    category: ErrorCategory
    labels: List[str]
    priority: int  # 1-5, 5 being highest
    should_auto_assign: bool
    estimated_effort: str  # "small", "medium", "large"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "labels": self.labels,
            "priority": self.priority,
            "should_auto_assign": self.should_auto_assign,
            "estimated_effort": self.estimated_effort
        }


class ErrorCategorizer:
    """Categorizes errors for proper GitHub issue classification."""
    
    # Patterns for error categorization
    CATEGORY_PATTERNS = {
        ErrorCategory.AUTHENTICATION: [
            r'authentication.*failed',
            r'invalid.*token',
            r'unauthorized',
            r'login.*failed',
            r'credential.*invalid'
        ],
        ErrorCategory.AUTHORIZATION: [
            r'permission.*denied',
            r'access.*forbidden', 
            r'not.*authorized',
            r'insufficient.*privileges'
        ],
        ErrorCategory.DATABASE: [
            r'database.*connection',
            r'sql.*error',
            r'connection.*timeout',
            r'deadlock',
            r'constraint.*violation',
            r'table.*not.*found'
        ],
        ErrorCategory.NETWORK: [
            r'connection.*refused',
            r'network.*timeout',
            r'dns.*resolution',
            r'socket.*error',
            r'http.*error.*[45]\d\d'
        ],
        ErrorCategory.VALIDATION: [
            r'validation.*error',
            r'invalid.*input',
            r'required.*field',
            r'format.*error',
            r'schema.*validation'
        ],
        ErrorCategory.DEPENDENCY: [
            r'module.*not.*found',
            r'import.*error',
            r'package.*not.*found',
            r'dependency.*missing',
            r'library.*not.*available'
        ],
        ErrorCategory.PERFORMANCE: [
            r'timeout.*exceeded',
            r'memory.*error',
            r'performance.*degradation',
            r'slow.*query',
            r'resource.*exhausted'
        ],
        ErrorCategory.CONFIGURATION: [
            r'configuration.*error',
            r'missing.*setting',
            r'invalid.*config',
            r'environment.*variable',
            r'config.*not.*found'
        ]
    }
    
    # Severity indicators
    CRITICAL_INDICATORS = [
        r'system.*down',
        r'service.*unavailable',
        r'data.*corruption',
        r'security.*breach',
        r'user.*data.*lost'
    ]
    
    HIGH_SEVERITY_INDICATORS = [
        r'authentication.*failed',
        r'database.*connection',
        r'payment.*failed',
        r'critical.*feature.*broken'
    ]
    
    def categorize_error(self, error_context: ErrorContext) -> IssueCategorization:
        """
        Categorize error for GitHub issue classification.
        
        Args:
            error_context: Error context to categorize
            
        Returns:
            IssueCategorization with severity, category, and labels
        """
        # Combine error message and stack trace for analysis
        analysis_text = f"{error_context.error_message} {error_context.stack_trace}".lower()
        
        # Determine category
        category = self._determine_category(analysis_text, error_context.error_type)
        
        # Determine severity
        severity = self._determine_severity(analysis_text, error_context)
        
        # Generate labels
        labels = self._generate_labels(category, severity, error_context)
        
        # Determine priority (1-5)
        priority = self._calculate_priority(severity, category, error_context)
        
        # Determine if should auto-assign
        should_auto_assign = self._should_auto_assign(category, severity)
        
        # Estimate effort
        estimated_effort = self._estimate_effort(category, severity, error_context)
        
        return IssueCategorization(
            severity=severity,
            category=category,
            labels=labels,
            priority=priority,
            should_auto_assign=should_auto_assign,
            estimated_effort=estimated_effort
        )
    
    def _determine_category(self, analysis_text: str, error_type: str) -> ErrorCategory:
        """Determine error category based on patterns."""
        # Check error type first
        error_type_lower = error_type.lower()
        
        type_category_map = {
            'authenticationerror': ErrorCategory.AUTHENTICATION,
            'authorizationerror': ErrorCategory.AUTHORIZATION,
            'validationerror': ErrorCategory.VALIDATION,
            'importerror': ErrorCategory.DEPENDENCY,
            'modulenotfounderror': ErrorCategory.DEPENDENCY,
            'connectionerror': ErrorCategory.NETWORK,
            'timeouterror': ErrorCategory.PERFORMANCE,
            'configurationerror': ErrorCategory.CONFIGURATION,
            'databaseerror': ErrorCategory.DATABASE
        }
        
        for type_key, category in type_category_map.items():
            if type_key in error_type_lower:
                return category
        
        # Check message patterns
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, analysis_text):
                    return category
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, analysis_text: str, error_context: ErrorContext) -> ErrorSeverity:
        """Determine error severity."""
        # Critical severity indicators
        for pattern in self.CRITICAL_INDICATORS:
            if re.search(pattern, analysis_text):
                return ErrorSeverity.CRITICAL
        
        # High severity indicators
        for pattern in self.HIGH_SEVERITY_INDICATORS:
            if re.search(pattern, analysis_text):
                return ErrorSeverity.HIGH
        
        # Check context data for severity hints
        context_data = error_context.context_data or {}
        
        # User-facing errors are higher priority
        if context_data.get('affects_users', False):
            return ErrorSeverity.HIGH
        
        # Core functionality errors are higher priority
        if context_data.get('blocks_core_functionality', False):
            return ErrorSeverity.HIGH
        
        # Production environment errors are higher priority
        if error_context.environment == 'production':
            return ErrorSeverity.HIGH
        
        # Default to medium for unknown errors
        return ErrorSeverity.MEDIUM
    
    def _generate_labels(
        self, 
        category: ErrorCategory, 
        severity: ErrorSeverity, 
        error_context: ErrorContext
    ) -> List[str]:
        """Generate appropriate labels for the issue."""
        labels = ["automated", "bug"]
        
        # Add category label
        labels.append(category.value)
        
        # Add severity label
        labels.append(f"priority-{severity.value}")
        
        # Add service label if available
        if error_context.service:
            labels.append(f"service-{error_context.service}")
        
        # Add environment label if available
        if error_context.environment:
            labels.append(f"env-{error_context.environment}")
        
        # Add special labels based on context
        context_data = error_context.context_data or {}
        
        if context_data.get('affects_users', False):
            labels.append("user-impact")
        
        if context_data.get('blocks_core_functionality', False):
            labels.append("core-functionality")
        
        if context_data.get('security_related', False):
            labels.append("security")
        
        if context_data.get('performance_issue', False):
            labels.append("performance")
        
        return sorted(set(labels))  # Remove duplicates and sort
    
    def _calculate_priority(
        self, 
        severity: ErrorSeverity, 
        category: ErrorCategory, 
        error_context: ErrorContext
    ) -> int:
        """Calculate numeric priority (1-5, 5 being highest)."""
        # Base priority from severity
        severity_priority = {
            ErrorSeverity.CRITICAL: 5,
            ErrorSeverity.HIGH: 4,
            ErrorSeverity.MEDIUM: 3,
            ErrorSeverity.LOW: 2,
            ErrorSeverity.INFO: 1
        }
        
        priority = severity_priority[severity]
        
        # Adjust based on category
        critical_categories = {
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.DATABASE,
            ErrorCategory.INFRASTRUCTURE
        }
        
        if category in critical_categories:
            priority = min(5, priority + 1)
        
        # Adjust based on environment
        if error_context.environment == 'production':
            priority = min(5, priority + 1)
        
        return priority
    
    def _should_auto_assign(self, category: ErrorCategory, severity: ErrorSeverity) -> bool:
        """Determine if issue should be auto-assigned."""
        # Critical and high severity issues should be auto-assigned
        if severity in {ErrorSeverity.CRITICAL, ErrorSeverity.HIGH}:
            return True
        
        # Certain categories should always be auto-assigned
        critical_categories = {
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.DATABASE,
            ErrorCategory.INFRASTRUCTURE
        }
        
        return category in critical_categories
    
    def _estimate_effort(
        self, 
        category: ErrorCategory, 
        severity: ErrorSeverity, 
        error_context: ErrorContext
    ) -> str:
        """Estimate effort required to fix the issue."""
        # Configuration and validation errors are typically quick fixes
        if category in {ErrorCategory.CONFIGURATION, ErrorCategory.VALIDATION}:
            return "small"
        
        # Dependency and network issues can vary
        if category in {ErrorCategory.DEPENDENCY, ErrorCategory.NETWORK}:
            return "medium"
        
        # Infrastructure and database issues are typically more complex
        if category in {ErrorCategory.INFRASTRUCTURE, ErrorCategory.DATABASE}:
            return "large"
        
        # Critical issues require immediate attention but might be quick fixes
        if severity == ErrorSeverity.CRITICAL:
            return "medium"
        
        # Default to medium effort
        return "medium"


class GitHubIssueManager:
    """
    Single Source of Truth GitHub Issue Manager
    
    This is the CANONICAL GitHub issue management system that handles all
    GitHub issue business logic including creation, categorization, templates,
    and lifecycle management.
    """
    
    def __init__(
        self,
        github_client: Optional[GitHubClient] = None,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        user_context: Optional[str] = None
    ):
        """
        Initialize GitHub Issue Manager.
        
        Args:
            github_client: GitHub client instance (optional, will create if not provided)
            repo_owner: Repository owner (optional, will use from config)
            repo_name: Repository name (optional, will use from config)
            user_context: User context for isolation
        """
        # Initialize environment
        self._env = IsolatedEnvironment()
        
        # Create GitHub client if not provided
        if github_client is None:
            self._github_client = create_github_client(user_context=user_context)
        else:
            self._github_client = github_client
        
        # Get configuration from client
        self._config = self._github_client.get_config()
        
        # Set repository info
        self._repo_owner = repo_owner or self._config.repo_owner
        self._repo_name = repo_name or self._config.repo_name
        
        if not self._repo_owner or not self._repo_name:
            raise ValueError("Repository owner and name must be provided")
        
        # Initialize components
        self._categorizer = ErrorCategorizer()
        self._user_context = user_context or "default"
        
        logger.info(f"Initialized GitHub Issue Manager for {self._repo_owner}/{self._repo_name}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._github_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._github_client.__aexit__(exc_type, exc_val, exc_tb)
    
    # === ISSUE CREATION AND MANAGEMENT ===
    
    async def create_issue_from_error_context(
        self,
        error_context: ErrorContext,
        check_duplicates: bool = True
    ) -> GitHubIssue:
        """
        Create GitHub issue from error context with categorization.
        
        Args:
            error_context: Structured error context
            check_duplicates: Whether to check for duplicate issues
            
        Returns:
            Created GitHubIssue
        """
        # Check for duplicates first if requested
        if check_duplicates:
            existing_issue = await self.find_existing_issue(error_context)
            if existing_issue:
                logger.info(f"Found duplicate issue #{existing_issue.number}, adding comment instead")
                await self.add_progress_comment(
                    existing_issue,
                    f"Error occurred again at {error_context.timestamp}",
                    error_context
                )
                return existing_issue
        
        # Categorize the error
        categorization = self._categorizer.categorize_error(error_context)
        
        # Generate issue title and body
        title = self.generate_issue_title(error_context, categorization)
        body = self.generate_issue_body(error_context, categorization)
        
        # Create the issue
        issue = await self._github_client.create_issue(
            repo_owner=self._repo_owner,
            repo_name=self._repo_name,
            title=title,
            body=body,
            labels=categorization.labels
        )
        
        logger.info(f"Created GitHub issue #{issue.number} for error: {error_context.error_type}")
        return issue
    
    def generate_issue_title(
        self, 
        error_context: ErrorContext, 
        categorization: IssueCategorization
    ) -> str:
        """
        Generate structured issue title.
        
        Args:
            error_context: Error context
            categorization: Error categorization
            
        Returns:
            Formatted issue title
        """
        # Truncate error message for title
        max_message_length = 80
        error_message = error_context.error_message
        
        if len(error_message) > max_message_length:
            error_message = error_message[:max_message_length].rstrip() + "..."
        
        # Format: [AUTOMATED] [Category] ErrorType: Message
        title_parts = [
            "[AUTOMATED]",
            f"[{categorization.category.value.upper()}]",
            f"{error_context.error_type}:",
            error_message
        ]
        
        title = " ".join(title_parts)
        
        # Ensure title is not too long for GitHub
        if len(title) > 255:
            title = title[:252] + "..."
        
        return title
    
    def generate_issue_body(
        self, 
        error_context: ErrorContext, 
        categorization: IssueCategorization
    ) -> str:
        """
        Generate structured issue body with all relevant information.
        
        Args:
            error_context: Error context
            categorization: Error categorization
            
        Returns:
            Formatted issue body in Markdown
        """
        # Build comprehensive issue body
        body_sections = []
        
        # Header with automated notice
        body_sections.append("## [U+1F916] Automated Issue Report")
        body_sections.append("")
        body_sections.append(
            "This issue was automatically created from an error detected in the system. "
            "Please review the details below and take appropriate action."
        )
        body_sections.append("")
        
        # Error summary
        body_sections.append("## [U+1F4CB] Error Summary")
        body_sections.append("")
        body_sections.append(f"**Error Type:** `{error_context.error_type}`")
        body_sections.append(f"**Severity:** {categorization.severity.value.upper()}")
        body_sections.append(f"**Category:** {categorization.category.value.title()}")
        body_sections.append(f"**Priority:** {categorization.priority}/5")
        body_sections.append(f"**Estimated Effort:** {categorization.estimated_effort}")
        body_sections.append("")
        
        # Error details
        body_sections.append("##  SEARCH:  Error Details")
        body_sections.append("")
        body_sections.append(f"**Message:** {error_context.error_message}")
        body_sections.append(f"**Timestamp:** {error_context.timestamp}")
        body_sections.append(f"**Fingerprint:** `{error_context.generate_fingerprint()}`")
        body_sections.append("")
        
        # Context information
        body_sections.append("## [U+1F310] Context Information")
        body_sections.append("")
        body_sections.append(f"**User ID:** `{error_context.user_id}`")
        
        if error_context.thread_id:
            body_sections.append(f"**Thread ID:** `{error_context.thread_id}`")
        
        if error_context.service:
            body_sections.append(f"**Service:** {error_context.service}")
        
        if error_context.environment:
            body_sections.append(f"**Environment:** {error_context.environment}")
        
        # Additional context data
        if error_context.context_data:
            body_sections.append("")
            body_sections.append("**Additional Context:**")
            for key, value in error_context.context_data.items():
                if isinstance(value, (str, int, float, bool)):
                    body_sections.append(f"- **{key.title()}:** {value}")
        
        body_sections.append("")
        
        # Stack trace
        if error_context.stack_trace:
            body_sections.append("##  CHART:  Stack Trace")
            body_sections.append("")
            body_sections.append("```")
            body_sections.append(error_context.stack_trace)
            body_sections.append("```")
            body_sections.append("")
        
        # Suggested actions
        body_sections.append("## [U+1F6E0][U+FE0F] Suggested Actions")
        body_sections.append("")
        suggested_actions = self._generate_suggested_actions(categorization, error_context)
        for action in suggested_actions:
            body_sections.append(f"- {action}")
        body_sections.append("")
        
        # Reproduction information
        body_sections.append("##  CYCLE:  Reproduction Information")
        body_sections.append("")
        body_sections.append("To reproduce this error:")
        body_sections.append(f"1. User: `{error_context.user_id}`")
        
        if error_context.thread_id:
            body_sections.append(f"2. Thread: `{error_context.thread_id}`")
        
        if error_context.service:
            body_sections.append(f"3. Service: {error_context.service}")
        
        body_sections.append(f"4. Check logs around: {error_context.timestamp}")
        body_sections.append("")
        
        # Labels and metadata
        body_sections.append("## [U+1F3F7][U+FE0F] Issue Metadata")
        body_sections.append("")
        body_sections.append(f"**Labels:** {', '.join(categorization.labels)}")
        body_sections.append(f"**Auto-assign:** {'Yes' if categorization.should_auto_assign else 'No'}")
        body_sections.append("")
        
        # Footer
        body_sections.append("---")
        body_sections.append("")
        body_sections.append("*This issue was created automatically by the Netra Error Tracking System.*")
        body_sections.append(f"*Report generated at: {datetime.now(timezone.utc).isoformat()}*")
        
        return "\n".join(body_sections)
    
    def _generate_suggested_actions(
        self, 
        categorization: IssueCategorization, 
        error_context: ErrorContext
    ) -> List[str]:
        """Generate suggested actions based on error category."""
        actions = []
        
        category_actions = {
            ErrorCategory.AUTHENTICATION: [
                "Check authentication service status",
                "Verify token/credential validity",
                "Review authentication flow logs"
            ],
            ErrorCategory.DATABASE: [
                "Check database connection status",
                "Review database server logs",
                "Verify database schema and constraints"
            ],
            ErrorCategory.NETWORK: [
                "Check network connectivity",
                "Review firewall and routing configuration",
                "Test external service availability"
            ],
            ErrorCategory.DEPENDENCY: [
                "Verify all dependencies are installed",
                "Check package versions and compatibility",
                "Review import statements and module paths"
            ],
            ErrorCategory.CONFIGURATION: [
                "Review configuration files",
                "Check environment variables",
                "Verify configuration schema"
            ],
            ErrorCategory.VALIDATION: [
                "Review input validation rules",
                "Check data format and schema",
                "Verify business logic constraints"
            ]
        }
        
        # Add category-specific actions
        if categorization.category in category_actions:
            actions.extend(category_actions[categorization.category])
        
        # Add severity-specific actions
        if categorization.severity == ErrorSeverity.CRITICAL:
            actions.insert(0, " ALERT:  **CRITICAL**: Investigate immediately")
        elif categorization.severity == ErrorSeverity.HIGH:
            actions.insert(0, " LIGHTNING:  **HIGH PRIORITY**: Address within 4 hours")
        
        # Add general actions
        actions.extend([
            "Review recent code changes in affected area",
            "Check system monitoring and alerts",
            "Add additional logging if needed for debugging"
        ])
        
        return actions
    
    # === DUPLICATE DETECTION ===
    
    async def find_existing_issue(self, error_context: ErrorContext) -> Optional[GitHubIssue]:
        """
        Find existing issue for the same error.
        
        Args:
            error_context: Error context to search for
            
        Returns:
            Existing GitHubIssue if found, None otherwise
        """
        fingerprint = error_context.generate_fingerprint()
        
        # Search for issues with the same fingerprint
        query = f'"{fingerprint}" is:issue is:open'
        
        try:
            issues = await self._github_client.search_issues(
                query=query,
                repo_owner=self._repo_owner,
                repo_name=self._repo_name,
                state="open"
            )
            
            if issues:
                logger.info(f"Found existing issue #{issues[0].number} for fingerprint {fingerprint}")
                return issues[0]
            
        except GitHubAPIError as e:
            logger.warning(f"Error searching for duplicate issues: {e}")
        
        return None
    
    async def is_duplicate_issue(self, error_context: ErrorContext) -> bool:
        """
        Check if an issue already exists for this error.
        
        Args:
            error_context: Error context to check
            
        Returns:
            True if duplicate exists, False otherwise
        """
        existing_issue = await self.find_existing_issue(error_context)
        return existing_issue is not None
    
    # === ISSUE UPDATES AND COMMENTS ===
    
    async def add_progress_comment(
        self,
        issue: GitHubIssue,
        progress_message: str,
        error_context: Optional[ErrorContext] = None
    ) -> GitHubComment:
        """
        Add progress comment to existing issue.
        
        Args:
            issue: GitHub issue to update
            progress_message: Progress update message
            error_context: Optional error context for additional details
            
        Returns:
            Created GitHubComment
        """
        # Build comment body
        comment_parts = [
            f"##  CYCLE:  Progress Update - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            progress_message
        ]
        
        if error_context:
            comment_parts.extend([
                "",
                "### Additional Context",
                f"- **Timestamp:** {error_context.timestamp}",
                f"- **User:** `{error_context.user_id}`"
            ])
            
            if error_context.thread_id:
                comment_parts.append(f"- **Thread:** `{error_context.thread_id}`")
        
        comment_parts.extend([
            "",
            "---",
            "*Automated update by Netra Error Tracking System*"
        ])
        
        comment_body = "\n".join(comment_parts)
        
        return await self._github_client.add_comment(
            repo_owner=self._repo_owner,
            repo_name=self._repo_name,
            issue_number=issue.number,
            body=comment_body
        )
    
    async def resolve_issue(
        self,
        issue: GitHubIssue,
        resolution_message: str,
        commit_sha: Optional[str] = None,
        pr_number: Optional[int] = None
    ) -> GitHubIssue:
        """
        Mark issue as resolved and close it.
        
        Args:
            issue: GitHub issue to resolve
            resolution_message: Resolution description
            commit_sha: Optional commit that fixed the issue
            pr_number: Optional PR number that fixed the issue
            
        Returns:
            Closed GitHubIssue
        """
        # Add resolution comment
        comment_parts = [
            f"##  PASS:  Issue Resolved - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            resolution_message
        ]
        
        if commit_sha:
            comment_parts.extend([
                "",
                f"**Fixed in commit:** {commit_sha}"
            ])
        
        if pr_number:
            comment_parts.extend([
                "",
                f"**Pull Request:** #{pr_number}"
            ])
        
        comment_parts.extend([
            "",
            "---",
            "*Automated resolution by Netra Error Tracking System*"
        ])
        
        comment_body = "\n".join(comment_parts)
        
        # Add comment
        await self._github_client.add_comment(
            repo_owner=self._repo_owner,
            repo_name=self._repo_name,
            issue_number=issue.number,
            body=comment_body
        )
        
        # Close the issue
        closed_issue = await self._github_client.close_issue(
            repo_owner=self._repo_owner,
            repo_name=self._repo_name,
            issue_number=issue.number
        )
        
        logger.info(f"Resolved and closed GitHub issue #{issue.number}")
        return closed_issue
    
    # === UTILITY METHODS ===
    
    def categorize_error_for_labels(self, error_context: ErrorContext) -> List[str]:
        """
        Get labels for error categorization.
        
        Args:
            error_context: Error context to categorize
            
        Returns:
            List of appropriate labels
        """
        categorization = self._categorizer.categorize_error(error_context)
        return categorization.labels
    
    def generate_issue_template(
        self, 
        error_context: ErrorContext
    ) -> Tuple[str, str]:
        """
        Generate issue title and body template.
        
        Args:
            error_context: Error context
            
        Returns:
            Tuple of (title, body)
        """
        categorization = self._categorizer.categorize_error(error_context)
        title = self.generate_issue_title(error_context, categorization)
        body = self.generate_issue_body(error_context, categorization)
        
        return title, body
    
    def get_repository_info(self) -> Tuple[str, str]:
        """
        Get repository owner and name.
        
        Returns:
            Tuple of (repo_owner, repo_name)
        """
        return self._repo_owner, self._repo_name
    
    def get_user_context(self) -> str:
        """Get the user context for this manager."""
        return self._user_context


# === SSOT FACTORY FUNCTIONS ===

def create_github_issue_manager(
    user_context: Optional[str] = None,
    repo_owner: Optional[str] = None,
    repo_name: Optional[str] = None,
    config_type: str = "default"
) -> GitHubIssueManager:
    """
    Create GitHub issue manager using SSOT patterns.
    
    This is the CANONICAL way to create GitHub issue managers.
    
    Args:
        user_context: User context for isolation
        repo_owner: Repository owner (optional)
        repo_name: Repository name (optional)
        config_type: Configuration type ("unit", "integration", "e2e", "default")
        
    Returns:
        Configured GitHubIssueManager
    """
    github_client = create_github_client(user_context=user_context, config_type=config_type)
    
    return GitHubIssueManager(
        github_client=github_client,
        repo_owner=repo_owner,
        repo_name=repo_name,
        user_context=user_context
    )