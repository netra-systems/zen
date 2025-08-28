#!/usr/bin/env python3
"""
Docker Log Issue Creator - Automatic GitHub Issue Generation from Errors

This tool extends the log introspector to automatically create GitHub issues
for detected errors, with deduplication and smart grouping.
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import hashlib
from collections import defaultdict

# Import the log introspector
from docker_compose_log_introspector import (
    DockerComposeLogIntrospector,
    ErrorCategory,
    ErrorSeverity,
    DetectedError,
    ServiceLogs
)


@dataclass 
class IssueTemplate:
    """Template for GitHub issue creation."""
    title: str
    body: str
    labels: List[str]
    assignees: List[str] = None
    milestone: Optional[str] = None
    project: Optional[str] = None


class GitHubIssueCreator:
    """Creates GitHub issues from detected errors."""
    
    def __init__(self, repo: Optional[str] = None, 
                 dry_run: bool = False,
                 dedupe_file: str = ".docker_log_issues.json"):
        """
        Initialize the issue creator.
        
        Args:
            repo: GitHub repository (owner/repo format)
            dry_run: If True, don't actually create issues
            dedupe_file: File to track created issues for deduplication
        """
        self.repo = repo or self.detect_repo()
        self.dry_run = dry_run
        self.dedupe_file = Path(dedupe_file)
        self.created_issues = self.load_created_issues()
        
    def detect_repo(self) -> Optional[str]:
        """Detect GitHub repository from git remote."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                url = result.stdout.strip()
                # Extract owner/repo from URL
                if "github.com" in url:
                    parts = url.split("github.com")[-1]
                    parts = parts.strip("/:").replace(".git", "")
                    return parts
        except:
            pass
        
        return None
    
    def load_created_issues(self) -> Dict[str, Dict]:
        """Load previously created issues for deduplication."""
        if self.dedupe_file.exists():
            try:
                return json.loads(self.dedupe_file.read_text())
            except:
                pass
        return {}
    
    def save_created_issues(self):
        """Save created issues for deduplication."""
        self.dedupe_file.write_text(
            json.dumps(self.created_issues, indent=2, default=str)
        )
    
    def get_error_hash(self, category: ErrorCategory, 
                       severity: ErrorSeverity,
                       errors: List[DetectedError]) -> str:
        """Generate hash for error group to detect duplicates."""
        # Create hash from category, severity, and error patterns
        hash_content = f"{category.value}:{severity.value}"
        
        # Add sample of error messages
        for error in errors[:5]:
            # Normalize the error message
            normalized = ' '.join(error.raw_log.split())[:100]
            hash_content += f":{normalized}"
        
        return hashlib.md5(hash_content.encode()).hexdigest()
    
    def should_create_issue(self, error_hash: str, 
                           category: ErrorCategory,
                           severity: ErrorSeverity) -> bool:
        """Check if issue should be created based on deduplication."""
        if error_hash in self.created_issues:
            # Check if issue was created recently (within 24 hours)
            created_time = datetime.fromisoformat(
                self.created_issues[error_hash].get('created_at', '2000-01-01')
            )
            time_diff = datetime.now() - created_time
            
            if time_diff.total_seconds() < 86400:  # 24 hours
                return False
                
        # Only create issues for errors and critical
        return severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]
    
    def create_github_issue(self, template: IssueTemplate) -> Optional[str]:
        """Create a GitHub issue using gh CLI."""
        if not self.repo:
            print("Error: No GitHub repository detected")
            return None
            
        if self.dry_run:
            print(f"[DRY RUN] Would create issue:")
            print(f"  Title: {template.title}")
            print(f"  Labels: {', '.join(template.labels)}")
            print(f"  Body preview: {template.body[:200]}...")
            return "dry-run-issue-url"
        
        try:
            # Create issue using gh CLI
            cmd = [
                "gh", "issue", "create",
                "--repo", self.repo,
                "--title", template.title,
                "--body", template.body
            ]
            
            if template.labels:
                cmd.extend(["--label", ",".join(template.labels)])
                
            if template.assignees:
                cmd.extend(["--assignee", ",".join(template.assignees)])
                
            if template.milestone:
                cmd.extend(["--milestone", template.milestone])
                
            if template.project:
                cmd.extend(["--project", template.project])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                issue_url = result.stdout.strip()
                print(f"Created issue: {issue_url}")
                return issue_url
            else:
                print(f"Failed to create issue: {result.stderr}")
                return None
                
        except FileNotFoundError:
            print("Error: gh CLI not found. Please install GitHub CLI.")
            print("Visit: https://cli.github.com/")
            return None
        except Exception as e:
            print(f"Error creating issue: {e}")
            return None
    
    def process_errors(self, service_logs: Dict[str, ServiceLogs],
                      min_occurrences: int = 1) -> List[str]:
        """Process errors and create GitHub issues."""
        created_urls = []
        
        # Group errors by category and severity
        error_groups = defaultdict(list)
        
        for service_name, logs in service_logs.items():
            for error in logs.errors:
                key = (error.category, error.severity)
                error_groups[key].append((service_name, error))
        
        # Process each error group
        for (category, severity), errors in error_groups.items():
            if len(errors) < min_occurrences:
                continue
                
            # Generate hash for deduplication
            error_hash = self.get_error_hash(
                category, severity, 
                [e for _, e in errors]
            )
            
            # Check if we should create issue
            if not self.should_create_issue(error_hash, category, severity):
                print(f"Skipping duplicate issue for {category.value} "
                      f"(already created)")
                continue
            
            # Create issue template
            template = self.create_issue_template(category, severity, errors)
            
            # Create the issue
            issue_url = self.create_github_issue(template)
            
            if issue_url:
                created_urls.append(issue_url)
                
                # Record created issue
                self.created_issues[error_hash] = {
                    'created_at': datetime.now().isoformat(),
                    'url': issue_url,
                    'category': category.value,
                    'severity': severity.value,
                    'occurrences': len(errors)
                }
                
        # Save deduplication data
        self.save_created_issues()
        
        return created_urls
    
    def create_issue_template(self, category: ErrorCategory,
                             severity: ErrorSeverity,
                             errors: List[tuple]) -> IssueTemplate:
        """Create issue template from error group."""
        # Count unique services
        services = list(set(service for service, _ in errors))
        
        # Create title
        title = f"[{severity.value.upper()}] {category.value} - "
        title += f"{len(errors)} occurrences in {len(services)} service(s)"
        
        # Create body
        body_lines = []
        body_lines.append(f"## Automated Error Report")
        body_lines.append("")
        body_lines.append(f"**Generated:** {datetime.now().isoformat()}")
        body_lines.append(f"**Category:** {category.value}")
        body_lines.append(f"**Severity:** {severity.value}")
        body_lines.append(f"**Total Occurrences:** {len(errors)}")
        body_lines.append(f"**Affected Services:** {', '.join(services)}")
        body_lines.append("")
        
        # Add error samples
        body_lines.append("## Error Samples")
        body_lines.append("")
        
        # Group by service
        errors_by_service = defaultdict(list)
        for service, error in errors:
            errors_by_service[service].append(error)
        
        for service, service_errors in list(errors_by_service.items())[:3]:
            body_lines.append(f"### Service: `{service}`")
            body_lines.append("")
            
            # Show first few errors
            for error in service_errors[:2]:
                body_lines.append("```")
                body_lines.append(error.raw_log[:500])
                body_lines.append("```")
                
                if error.context_before or error.context_after:
                    body_lines.append("<details>")
                    body_lines.append("<summary>Context (click to expand)</summary>")
                    body_lines.append("")
                    body_lines.append("```")
                    for line in error.context_before[-2:]:
                        body_lines.append(line)
                    body_lines.append(f">>> {error.raw_log}")
                    for line in error.context_after[:2]:
                        body_lines.append(line)
                    body_lines.append("```")
                    body_lines.append("</details>")
                    body_lines.append("")
            
            if len(service_errors) > 2:
                body_lines.append(f"_...and {len(service_errors) - 2} more_")
                body_lines.append("")
        
        # Add recommended actions
        body_lines.append("## Recommended Actions")
        body_lines.append("")
        body_lines.append(self.get_action_items(category))
        body_lines.append("")
        
        # Add debugging commands
        body_lines.append("## Debugging Commands")
        body_lines.append("")
        body_lines.append("```bash")
        body_lines.append("# View full logs for affected services")
        for service in services[:3]:
            body_lines.append(f"docker compose logs --tail 100 {service}")
        body_lines.append("")
        body_lines.append("# Run log introspector for detailed analysis")
        body_lines.append("python scripts/docker_compose_log_introspector.py analyze")
        body_lines.append("```")
        body_lines.append("")
        
        # Add metadata
        body_lines.append("---")
        body_lines.append("_This issue was automatically generated by Docker Log Issue Creator_")
        
        # Create labels
        labels = [
            "bug",
            f"severity:{severity.value}",
            f"component:docker",
            "automated"
        ]
        
        # Add category-specific label
        category_label = category.value.lower().replace(' ', '-').replace('/', '-')
        labels.append(f"area:{category_label}")
        
        return IssueTemplate(
            title=title,
            body="\n".join(body_lines),
            labels=labels
        )
    
    def get_action_items(self, category: ErrorCategory) -> str:
        """Get action items for specific error category."""
        actions = {
            ErrorCategory.DATABASE_CONNECTION: """
- [ ] Check PostgreSQL container status: `docker compose ps postgres`
- [ ] Verify database credentials in environment variables
- [ ] Check database migration status
- [ ] Review connection pool settings
""",
            ErrorCategory.AUTHENTICATION: """
- [ ] Verify JWT_SECRET is set correctly
- [ ] Check auth service health: `docker compose logs auth`
- [ ] Review token expiration settings
- [ ] Test authentication flow manually
""",
            ErrorCategory.NETWORK: """
- [ ] Check Docker network configuration
- [ ] Verify service names in connection strings
- [ ] Review CORS settings
- [ ] Check for port conflicts: `docker compose ps`
""",
            ErrorCategory.CONFIGURATION: """
- [ ] Review .env file for missing variables
- [ ] Check docker-compose.yml environment section
- [ ] Verify configuration file paths
- [ ] Compare with working environment
""",
            ErrorCategory.MEMORY: """
- [ ] Check container resource limits
- [ ] Monitor memory usage: `docker stats`
- [ ] Look for memory leaks in application
- [ ] Consider increasing swap space
""",
            ErrorCategory.DEPENDENCY: """
- [ ] Rebuild containers: `docker compose build --no-cache`
- [ ] Check package.json/requirements.txt
- [ ] Verify volume mounts
- [ ] Clear Docker cache if needed
""",
            ErrorCategory.WEBSOCKET: """
- [ ] Check WebSocket upgrade headers
- [ ] Verify nginx/proxy configuration
- [ ] Test with wscat or similar tool
- [ ] Check for connection timeout settings
""",
            ErrorCategory.MIGRATION: """
- [ ] Check migration status: `docker compose exec backend alembic current`
- [ ] Review recent migration files
- [ ] Consider rollback if needed
- [ ] Check database permissions
""",
            ErrorCategory.SSL_TLS: """
- [ ] Verify SSL certificate validity
- [ ] Check certificate paths in configuration
- [ ] Review SSL_MODE settings
- [ ] Test with SSL disabled (dev only)
"""
        }
        
        return actions.get(category, """
- [ ] Review detailed error logs
- [ ] Check service dependencies
- [ ] Compare with last working configuration
- [ ] Review recent code changes
""")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automatically create GitHub issues from Docker Compose errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze and create issues
  python docker_log_issue_creator.py --create-issues
  
  # Dry run (show what would be created)
  python docker_log_issue_creator.py --dry-run
  
  # Specify minimum occurrences
  python docker_log_issue_creator.py --min-occurrences 3
  
  # Use specific compose file
  python docker_log_issue_creator.py -f docker-compose.dev.yml
"""
    )
    
    parser.add_argument('--create-issues', action='store_true',
                       help='Actually create GitHub issues')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what issues would be created without creating them')
    parser.add_argument('--repo', help='GitHub repository (owner/repo)')
    parser.add_argument('--min-occurrences', type=int, default=1,
                       help='Minimum error occurrences to create issue (default: 1)')
    parser.add_argument('--tail', type=int, default=500,
                       help='Number of log lines to analyze (default: 500)')
    parser.add_argument('-f', '--compose-file', default='docker-compose.yml',
                       help='Docker Compose file to use')
    parser.add_argument('-p', '--project', help='Docker Compose project name')
    parser.add_argument('--service', help='Analyze specific service only')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Clear issue deduplication cache')
    
    args = parser.parse_args()
    
    # Create components
    introspector = DockerComposeLogIntrospector(
        args.compose_file, 
        args.project
    )
    
    issue_creator = GitHubIssueCreator(
        repo=args.repo,
        dry_run=args.dry_run or not args.create_issues
    )
    
    # Clear cache if requested
    if args.clear_cache:
        if issue_creator.dedupe_file.exists():
            issue_creator.dedupe_file.unlink()
            print("Cleared issue deduplication cache")
    
    # Analyze logs
    print("Analyzing Docker Compose logs...")
    if args.service:
        logs = introspector.get_service_logs(args.service, tail=args.tail)
        all_logs = {args.service: logs}
    else:
        all_logs = introspector.analyze_all_services(tail=args.tail)
    
    # Generate report
    report = introspector.generate_error_report(all_logs)
    print("\n" + report)
    
    # Create issues if requested
    if args.create_issues or args.dry_run:
        print("\n" + "="*60)
        print("GITHUB ISSUE CREATION")
        print("="*60)
        
        if not issue_creator.repo:
            print("Error: Could not detect GitHub repository")
            print("Please specify with --repo owner/repo")
            return 1
            
        print(f"Repository: {issue_creator.repo}")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
        print("")
        
        created_urls = issue_creator.process_errors(
            all_logs,
            min_occurrences=args.min_occurrences
        )
        
        if created_urls:
            print(f"\nCreated {len(created_urls)} issue(s):")
            for url in created_urls:
                print(f"  - {url}")
        else:
            print("\nNo issues created (no significant errors or all duplicates)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())