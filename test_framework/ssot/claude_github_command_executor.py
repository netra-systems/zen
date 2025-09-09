"""
Claude GitHub Command Executor - Single Source of Truth for Claude-GitHub Integration

This module provides the canonical integration between Claude commands and GitHub
operations, enabling users to create, search, and manage GitHub issues through
natural language commands in the Claude interface.

CRITICAL: This is the SINGLE SOURCE OF TRUTH for Claude-GitHub command integration.
All Claude-GitHub command operations across the entire codebase MUST use this executor.

Business Value: Early/Mid/Enterprise - User Experience & Development Velocity  
Enables users to seamlessly manage GitHub issues through Claude commands, improving
developer workflow efficiency and providing intuitive issue tracking capabilities.

REQUIREMENTS per CLAUDE.md:
- Natural language command parsing for GitHub operations
- Integration with SSOT GitHub components
- Multi-user context and permission management
- Structured command response formatting
- Error handling and user feedback
"""

import json
import logging
import re
import shlex
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum

from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.github_client import GitHubClient, GitHubIssue, GitHubAPIError
from test_framework.ssot.github_issue_manager import (
    GitHubIssueManager, ErrorContext, create_github_issue_manager
)
from test_framework.ssot.github_duplicate_detector import (
    GitHubDuplicateDetector, create_github_duplicate_detector
)


logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Supported Claude GitHub command types."""
    CREATE_ISSUE = "create_issue"
    SEARCH_ISSUES = "search_issues"
    UPDATE_ISSUE = "update_issue"
    CLOSE_ISSUE = "close_issue"
    LINK_ISSUE = "link_issue"
    GET_ISSUE = "get_issue"
    ADD_COMMENT = "add_comment"
    LIST_ISSUES = "list_issues"
    HELP = "help"


@dataclass
class ClaudeCommand:
    """Structured Claude command representation."""
    command_type: CommandType
    raw_command: str
    parsed_args: Dict[str, Any]
    user_context: Dict[str, Any]
    flags: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "command_type": self.command_type.value,
            "raw_command": self.raw_command,
            "parsed_args": self.parsed_args,
            "user_context": self.user_context,
            "flags": self.flags
        }


@dataclass
class CommandResult:
    """Claude command execution result."""
    success: bool
    command_type: str
    message: str
    data: Optional[Dict[str, Any]] = None
    github_issue_url: Optional[str] = None
    issue_number: Optional[int] = None
    error_details: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_claude_response(self) -> str:
        """Format as Claude-friendly response."""
        if self.success:
            if self.command_type == CommandType.CREATE_ISSUE.value:
                return f"✅ GitHub issue created successfully!\n\n**Issue #{self.issue_number}**\n{self.github_issue_url}\n\n{self.message}"
            elif self.command_type == CommandType.SEARCH_ISSUES.value:
                return f"🔍 {self.message}\n\n{self._format_search_results()}"
            elif self.command_type == CommandType.UPDATE_ISSUE.value:
                return f"📝 {self.message}\n\n{self.github_issue_url if self.github_issue_url else ''}"
            else:
                return f"✅ {self.message}"
        else:
            return f"❌ **Error:** {self.message}\n\n{self.error_details if self.error_details else ''}"
    
    def _format_search_results(self) -> str:
        """Format search results for Claude response."""
        if not self.data or not self.data.get('issues'):
            return "No issues found."
        
        issues = self.data['issues'][:5]  # Limit to first 5 results
        formatted_results = []
        
        for issue in issues:
            formatted_results.append(
                f"**#{issue['number']}** - {issue['title']}\n"
                f"Status: {issue['state']} | Created: {issue['created_at'][:10]}\n"
                f"{issue['html_url']}\n"
            )
        
        result = "\n".join(formatted_results)
        
        if len(self.data['issues']) > 5:
            result += f"\n... and {len(self.data['issues']) - 5} more results"
        
        return result


class CommandParser:
    """Parses natural language Claude commands into structured commands."""
    
    # Command patterns for different GitHub operations
    COMMAND_PATTERNS = {
        CommandType.CREATE_ISSUE: [
            r'create\s+(?:github\s+)?issue(?:\s+for)?(?:\s+error)?(?:\s*[:])?\s*["\']?(.+?)["\']?$',
            r'(?:open|file|submit)\s+(?:a\s+)?(?:github\s+)?issue(?:\s+for)?(?:\s*[:])?\s*["\']?(.+?)["\']?$',
            r'report\s+(?:a\s+)?(?:github\s+)?(?:bug|error|issue)(?:\s*[:])?\s*["\']?(.+?)["\']?$'
        ],
        CommandType.SEARCH_ISSUES: [
            r'search\s+(?:github\s+)?issues?(?:\s+for)?(?:\s*[:])?\s*["\']?(.+?)["\']?$',
            r'find\s+(?:github\s+)?issues?(?:\s+about)?(?:\s*[:])?\s*["\']?(.+?)["\']?$',
            r'list\s+(?:github\s+)?issues?(?:\s+matching)?(?:\s*[:])?\s*["\']?(.+?)["\']?$'
        ],
        CommandType.UPDATE_ISSUE: [
            r'update\s+(?:github\s+)?issue\s+#?(\d+)(?:\s+with)?(?:\s*[:])?\s*(.+)$',
            r'(?:add\s+(?:comment|update)\s+to|comment\s+on)\s+(?:github\s+)?issue\s+#?(\d+)(?:\s*[:])?\s*(.+)$'
        ],
        CommandType.CLOSE_ISSUE: [
            r'close\s+(?:github\s+)?issue\s+#?(\d+)(?:\s+(?:as|with))?(?:\s*[:])?\s*(.*)$',
            r'resolve\s+(?:github\s+)?issue\s+#?(\d+)(?:\s+(?:as|with))?(?:\s*[:])?\s*(.*)$'
        ],
        CommandType.GET_ISSUE: [
            r'(?:get|show|display)\s+(?:github\s+)?issue\s+#?(\d+)$',
            r'(?:details\s+for|info\s+about)\s+(?:github\s+)?issue\s+#?(\d+)$'
        ],
        CommandType.LINK_ISSUE: [
            r'link\s+(?:to\s+)?(?:github\s+)?issue\s+#?(\d+)(?:\s+to\s+(?:this\s+)?(?:thread|conversation))?$'
        ],
        CommandType.LIST_ISSUES: [
            r'list\s+(?:all\s+)?(?:github\s+)?issues?(?:\s+(?:for|in)\s+(.+))?$',
            r'show\s+(?:all\s+)?(?:github\s+)?issues?(?:\s+(?:for|in)\s+(.+))?$'
        ]
    }
    
    # Flag patterns for command options
    FLAG_PATTERNS = {
        'priority': r'--priority[=\s]+(\w+)',
        'labels': r'--labels?[=\s]+["\']?([^"\']+)["\']?',
        'assignee': r'--assignee[=\s]+(\w+)',
        'milestone': r'--milestone[=\s]+(\d+)',
        'state': r'--state[=\s]+(open|closed|all)',
        'service': r'--service[=\s]+(\w+)',
        'environment': r'--env(?:ironment)?[=\s]+(\w+)',
        'severity': r'--severity[=\s]+(\w+)'
    }
    
    def parse_command(self, raw_command: str, user_context: Dict[str, Any]) -> ClaudeCommand:
        """
        Parse raw Claude command into structured command.
        
        Args:
            raw_command: Raw command string from user
            user_context: User context for command execution
            
        Returns:
            Parsed ClaudeCommand
            
        Raises:
            ValueError: If command cannot be parsed
        """
        # Clean and normalize command
        cleaned_command = raw_command.strip().lower()
        
        # Extract flags first
        flags = self._extract_flags(cleaned_command)
        
        # Remove flags from command for pattern matching
        command_without_flags = self._remove_flags(cleaned_command)
        
        # Try to match command patterns
        for command_type, patterns in self.COMMAND_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, command_without_flags, re.IGNORECASE)
                if match:
                    parsed_args = self._extract_args_for_command(command_type, match)
                    
                    return ClaudeCommand(
                        command_type=command_type,
                        raw_command=raw_command,
                        parsed_args=parsed_args,
                        user_context=user_context,
                        flags=flags
                    )
        
        # If no pattern matches, check for help request
        if any(word in cleaned_command for word in ['help', '?', 'usage', 'how']):
            return ClaudeCommand(
                command_type=CommandType.HELP,
                raw_command=raw_command,
                parsed_args={'topic': 'general'},
                user_context=user_context,
                flags={}
            )
        
        raise ValueError(f"Could not parse GitHub command: {raw_command}")
    
    def _extract_flags(self, command: str) -> Dict[str, Any]:
        """Extract flag values from command."""
        flags = {}
        
        for flag_name, pattern in self.FLAG_PATTERNS.items():
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                
                # Special handling for labels (comma-separated)
                if flag_name == 'labels':
                    flags[flag_name] = [label.strip() for label in value.split(',')]
                else:
                    flags[flag_name] = value
        
        return flags
    
    def _remove_flags(self, command: str) -> str:
        """Remove flags from command for pattern matching."""
        for pattern in self.FLAG_PATTERNS.values():
            command = re.sub(pattern, '', command, flags=re.IGNORECASE)
        
        return command.strip()
    
    def _extract_args_for_command(self, command_type: CommandType, match) -> Dict[str, Any]:
        """Extract command-specific arguments from regex match."""
        args = {}
        
        if command_type == CommandType.CREATE_ISSUE:
            args['title'] = match.group(1).strip()
        
        elif command_type == CommandType.SEARCH_ISSUES:
            args['query'] = match.group(1).strip()
        
        elif command_type == CommandType.UPDATE_ISSUE:
            args['issue_number'] = int(match.group(1))
            args['content'] = match.group(2).strip()
        
        elif command_type == CommandType.CLOSE_ISSUE:
            args['issue_number'] = int(match.group(1))
            args['reason'] = match.group(2).strip() if len(match.groups()) > 1 else ''
        
        elif command_type == CommandType.GET_ISSUE:
            args['issue_number'] = int(match.group(1))
        
        elif command_type == CommandType.LINK_ISSUE:
            args['issue_number'] = int(match.group(1))
        
        elif command_type == CommandType.LIST_ISSUES:
            args['filter'] = match.group(1).strip() if match.groups() and match.group(1) else None
        
        return args


class ClaudeGitHubCommandExecutor:
    """
    Single Source of Truth Claude GitHub Command Executor
    
    This is the CANONICAL executor for Claude GitHub commands that handles
    natural language command parsing, GitHub API operations, and structured
    response formatting for seamless user interaction.
    """
    
    def __init__(
        self,
        github_client: Optional[GitHubClient] = None,
        issue_manager: Optional[GitHubIssueManager] = None,
        duplicate_detector: Optional[GitHubDuplicateDetector] = None,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        user_context: Optional[str] = None
    ):
        """
        Initialize Claude GitHub command executor.
        
        Args:
            github_client: GitHub client (optional, will create if not provided)
            issue_manager: GitHub issue manager (optional, will create if not provided)
            duplicate_detector: Duplicate detector (optional, will create if not provided)
            repo_owner: Repository owner (optional, will use from config)
            repo_name: Repository name (optional, will use from config)
            user_context: User context for isolation
        """
        # Initialize environment
        self._env = IsolatedEnvironment()
        
        # Initialize or create GitHub components
        if github_client is None:
            from test_framework.ssot.github_client import create_github_client
            self._github_client = create_github_client(user_context=user_context)
        else:
            self._github_client = github_client
        
        if issue_manager is None:
            self._issue_manager = create_github_issue_manager(
                user_context=user_context,
                repo_owner=repo_owner,
                repo_name=repo_name
            )
        else:
            self._issue_manager = issue_manager
        
        if duplicate_detector is None:
            self._duplicate_detector = create_github_duplicate_detector(self._github_client)
        else:
            self._duplicate_detector = duplicate_detector
        
        # Get repository information
        if repo_owner and repo_name:
            self._repo_owner = repo_owner
            self._repo_name = repo_name
        else:
            self._repo_owner, self._repo_name = self._issue_manager.get_repository_info()
        
        # Initialize components
        self._parser = CommandParser()
        self._user_context = user_context or "default"
        
        logger.info(f"Initialized Claude GitHub command executor for {self._repo_owner}/{self._repo_name}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._github_client.__aenter__()
        await self._issue_manager.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._issue_manager.__aexit__(exc_type, exc_val, exc_tb)
        await self._github_client.__aexit__(exc_type, exc_val, exc_tb)
    
    # === COMMAND EXECUTION ===
    
    async def execute_command(
        self,
        raw_command: str,
        user_context: Optional[Dict[str, Any]] = None,
        thread_context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        Execute Claude GitHub command.
        
        Args:
            raw_command: Raw command string from user
            user_context: User context information
            thread_context: Thread/conversation context
            
        Returns:
            CommandResult with execution outcome
        """
        try:
            # Build complete user context
            full_user_context = {
                "user_id": self._user_context,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(user_context or {}),
                **(thread_context or {})
            }
            
            # Parse command
            parsed_command = self._parser.parse_command(raw_command, full_user_context)
            
            logger.info(f"Executing GitHub command: {parsed_command.command_type.value}")
            
            # Route to appropriate handler
            if parsed_command.command_type == CommandType.CREATE_ISSUE:
                return await self._handle_create_issue(parsed_command)
            elif parsed_command.command_type == CommandType.SEARCH_ISSUES:
                return await self._handle_search_issues(parsed_command)
            elif parsed_command.command_type == CommandType.UPDATE_ISSUE:
                return await self._handle_update_issue(parsed_command)
            elif parsed_command.command_type == CommandType.CLOSE_ISSUE:
                return await self._handle_close_issue(parsed_command)
            elif parsed_command.command_type == CommandType.GET_ISSUE:
                return await self._handle_get_issue(parsed_command)
            elif parsed_command.command_type == CommandType.LINK_ISSUE:
                return await self._handle_link_issue(parsed_command)
            elif parsed_command.command_type == CommandType.LIST_ISSUES:
                return await self._handle_list_issues(parsed_command)
            elif parsed_command.command_type == CommandType.HELP:
                return self._handle_help(parsed_command)
            else:
                return CommandResult(
                    success=False,
                    command_type=parsed_command.command_type.value,
                    message="Command type not yet implemented",
                    error_details=f"Handler for {parsed_command.command_type.value} is not implemented"
                )
        
        except ValueError as e:
            return CommandResult(
                success=False,
                command_type="parse_error",
                message="Could not understand the GitHub command",
                error_details=str(e)
            )
        
        except GitHubAPIError as e:
            return CommandResult(
                success=False,
                command_type="github_api_error",
                message=f"GitHub API error: {e.error_type.value}",
                error_details=str(e)
            )
        
        except Exception as e:
            logger.error(f"Unexpected error executing GitHub command: {e}", exc_info=True)
            return CommandResult(
                success=False,
                command_type="internal_error",
                message="An unexpected error occurred",
                error_details=str(e)
            )
    
    # === COMMAND HANDLERS ===
    
    async def _handle_create_issue(self, command: ClaudeCommand) -> CommandResult:
        """Handle create issue command."""
        title = command.parsed_args['title']
        
        # Build error context from command
        error_context = ErrorContext(
            error_message=title,
            error_type=command.flags.get('severity', 'UserReported'),
            stack_trace='',  # No stack trace for manual issues
            user_id=command.user_context['user_id'],
            thread_id=command.user_context.get('thread_id'),
            timestamp=command.user_context['timestamp'],
            service=command.flags.get('service'),
            environment=command.flags.get('environment', 'unknown'),
            context_data={
                'created_via': 'claude_command',
                'raw_command': command.raw_command,
                'manual_issue': True
            }
        )
        
        # Check for duplicates if requested (default: yes)
        check_duplicates = not command.flags.get('force', False)
        
        if check_duplicates:
            duplicate_result = await self._duplicate_detector.detect_duplicates(
                error_context, self._repo_owner, self._repo_name
            )
            
            if duplicate_result.is_duplicate:
                best_match = duplicate_result.get_best_match()
                if best_match:
                    issue, score = best_match
                    
                    # Add comment to existing issue
                    await self._issue_manager.add_progress_comment(
                        issue,
                        f"Similar issue reported via Claude command: {title}",
                        error_context
                    )
                    
                    return CommandResult(
                        success=True,
                        command_type=CommandType.CREATE_ISSUE.value,
                        message=f"Found similar existing issue, added comment instead of creating duplicate",
                        github_issue_url=issue.html_url,
                        issue_number=issue.number,
                        data={
                            "duplicate_detected": True,
                            "similarity_score": score.overall_score,
                            "existing_issue": issue.to_dict()
                        }
                    )
        
        # Create new issue
        issue = await self._issue_manager.create_issue_from_error_context(
            error_context,
            check_duplicates=False  # Already checked above
        )
        
        return CommandResult(
            success=True,
            command_type=CommandType.CREATE_ISSUE.value,
            message=f"Successfully created GitHub issue for: {title}",
            github_issue_url=issue.html_url,
            issue_number=issue.number,
            data={"issue": issue.to_dict()}
        )
    
    async def _handle_search_issues(self, command: ClaudeCommand) -> CommandResult:
        """Handle search issues command."""
        query = command.parsed_args['query']
        state = command.flags.get('state', 'open')
        labels = command.flags.get('labels')
        
        # Prepare search parameters
        search_labels = ','.join(labels) if labels else None
        
        issues = await self._github_client.search_issues(
            query=query,
            repo_owner=self._repo_owner,
            repo_name=self._repo_name,
            state=state,
            labels=search_labels,
            per_page=20
        )
        
        return CommandResult(
            success=True,
            command_type=CommandType.SEARCH_ISSUES.value,
            message=f"Found {len(issues)} issues matching '{query}'",
            data={
                "issues": [issue.to_dict() for issue in issues],
                "search_query": query,
                "search_state": state,
                "search_labels": labels
            }
        )
    
    async def _handle_update_issue(self, command: ClaudeCommand) -> CommandResult:
        """Handle update issue command."""
        issue_number = command.parsed_args['issue_number']
        content = command.parsed_args['content']
        
        # Get the existing issue
        issue = await self._github_client.get_issue(
            self._repo_owner, self._repo_name, issue_number
        )
        
        # Add comment with update
        comment = await self._github_client.add_comment(
            self._repo_owner, self._repo_name, issue_number, content
        )
        
        return CommandResult(
            success=True,
            command_type=CommandType.UPDATE_ISSUE.value,
            message=f"Added comment to issue #{issue_number}",
            github_issue_url=issue.html_url,
            issue_number=issue_number,
            data={
                "comment": comment.to_dict(),
                "issue": issue.to_dict()
            }
        )
    
    async def _handle_close_issue(self, command: ClaudeCommand) -> CommandResult:
        """Handle close issue command."""
        issue_number = command.parsed_args['issue_number']
        reason = command.parsed_args.get('reason', 'Closed via Claude command')
        
        # Get the existing issue
        issue = await self._github_client.get_issue(
            self._repo_owner, self._repo_name, issue_number
        )
        
        # Close the issue with reason
        closed_issue = await self._issue_manager.resolve_issue(
            issue, reason
        )
        
        return CommandResult(
            success=True,
            command_type=CommandType.CLOSE_ISSUE.value,
            message=f"Closed issue #{issue_number}: {reason}",
            github_issue_url=closed_issue.html_url,
            issue_number=issue_number,
            data={"issue": closed_issue.to_dict()}
        )
    
    async def _handle_get_issue(self, command: ClaudeCommand) -> CommandResult:
        """Handle get issue command."""
        issue_number = command.parsed_args['issue_number']
        
        issue = await self._github_client.get_issue(
            self._repo_owner, self._repo_name, issue_number
        )
        
        # Get comments too
        comments = await self._github_client.get_comments(
            self._repo_owner, self._repo_name, issue_number
        )
        
        return CommandResult(
            success=True,
            command_type=CommandType.GET_ISSUE.value,
            message=f"Retrieved details for issue #{issue_number}",
            github_issue_url=issue.html_url,
            issue_number=issue_number,
            data={
                "issue": issue.to_dict(),
                "comments": [comment.to_dict() for comment in comments]
            }
        )
    
    async def _handle_link_issue(self, command: ClaudeCommand) -> CommandResult:
        """Handle link issue command."""
        issue_number = command.parsed_args['issue_number']
        
        # Get issue details
        issue = await self._github_client.get_issue(
            self._repo_owner, self._repo_name, issue_number
        )
        
        # Add thread linking information
        thread_id = command.user_context.get('thread_id', 'unknown')
        
        link_comment = (
            f"🔗 **Linked to Claude Conversation**\n\n"
            f"This issue has been linked to Claude thread: `{thread_id}`\n"
            f"Timestamp: {command.user_context['timestamp']}\n"
            f"User: {command.user_context['user_id']}"
        )
        
        await self._github_client.add_comment(
            self._repo_owner, self._repo_name, issue_number, link_comment
        )
        
        return CommandResult(
            success=True,
            command_type=CommandType.LINK_ISSUE.value,
            message=f"Linked issue #{issue_number} to current conversation",
            github_issue_url=issue.html_url,
            issue_number=issue_number,
            data={
                "issue": issue.to_dict(),
                "thread_id": thread_id
            }
        )
    
    async def _handle_list_issues(self, command: ClaudeCommand) -> CommandResult:
        """Handle list issues command."""
        filter_term = command.parsed_args.get('filter')
        state = command.flags.get('state', 'open')
        
        # Build search query
        if filter_term:
            query = f"{filter_term} is:issue"
        else:
            query = "is:issue"
        
        issues = await self._github_client.search_issues(
            query=query,
            repo_owner=self._repo_owner,
            repo_name=self._repo_name,
            state=state,
            per_page=10
        )
        
        return CommandResult(
            success=True,
            command_type=CommandType.LIST_ISSUES.value,
            message=f"Found {len(issues)} {state} issues" + (f" matching '{filter_term}'" if filter_term else ""),
            data={
                "issues": [issue.to_dict() for issue in issues],
                "filter": filter_term,
                "state": state
            }
        )
    
    def _handle_help(self, command: ClaudeCommand) -> CommandResult:
        """Handle help command."""
        help_text = """
## 🤖 GitHub Commands for Claude

I can help you manage GitHub issues through natural language commands:

### Creating Issues
- `create github issue: "Bug in authentication system"`
- `report a bug: "Database connection timeout"`
- `open issue for error: "Import module failed"`

**Flags:** `--priority=high` `--labels=bug,critical` `--service=auth` `--environment=prod`

### Searching Issues
- `search github issues for: "authentication"`
- `find issues about: "database timeout"`
- `list issues matching: "performance"`

**Flags:** `--state=open|closed|all` `--labels=bug,feature`

### Managing Issues
- `update issue #123 with: "Found the root cause"`
- `close issue #123 as: "Fixed in latest release"`
- `get issue #123` (show details)
- `link to issue #123` (link to current conversation)

### Examples
```
create github issue: "User login fails with 500 error" --priority=high --service=auth
search issues for: "timeout" --state=all --labels=bug
update issue #45 with: "Deployed fix to staging, testing now"
close issue #45 as: "Confirmed fixed in production"
```

Need help with a specific command? Just ask!
        """
        
        return CommandResult(
            success=True,
            command_type=CommandType.HELP.value,
            message=help_text.strip()
        )
    
    # === UTILITY METHODS ===
    
    def get_repository_info(self) -> Tuple[str, str]:
        """Get repository owner and name."""
        return self._repo_owner, self._repo_name
    
    def get_user_context(self) -> str:
        """Get user context."""
        return self._user_context


# === SSOT FACTORY FUNCTIONS ===

def create_claude_github_command_executor(
    user_context: Optional[str] = None,
    repo_owner: Optional[str] = None,
    repo_name: Optional[str] = None,
    config_type: str = "default"
) -> ClaudeGitHubCommandExecutor:
    """
    Create Claude GitHub command executor using SSOT patterns.
    
    This is the CANONICAL way to create Claude GitHub command executors.
    
    Args:
        user_context: User context for isolation
        repo_owner: Repository owner (optional)
        repo_name: Repository name (optional)
        config_type: Configuration type ("unit", "integration", "e2e", "default")
        
    Returns:
        Configured ClaudeGitHubCommandExecutor
    """
    return ClaudeGitHubCommandExecutor(
        repo_owner=repo_owner,
        repo_name=repo_name,
        user_context=user_context
    )