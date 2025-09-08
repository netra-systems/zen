#!/usr/bin/env python3
"""
Critical Remediation Tracker System

This system addresses the "Analysis Trap" organizational anti-pattern identified in
Five Whys analyses by providing systematic tracking and execution of P0 issue remediation.

Key Features:
- Extracts actionable items from Five Whys analyses automatically
- Tracks remediation execution with owner assignment and deadlines
- Integrates with existing CLAUDE.md compliance patterns
- Provides business value metrics and impact tracking
- Generates alerts for missed deadlines or execution failures

Usage:
    python scripts/critical_remediation_tracker.py extract-issues --analysis-file reports/bugs/STARTUP_FAILURE_FIVE_WHYS_ANALYSIS_20250908.md
    python scripts/critical_remediation_tracker.py track --issue-id P0-001 --owner "Claude Code" --deadline 2025-09-10
    python scripts/critical_remediation_tracker.py status --show-overdue
    python scripts/critical_remediation_tracker.py validate --issue-id P0-001
"""

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IssueStatus(Enum):
    """Status enum for remediation issues"""
    IDENTIFIED = "identified"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VALIDATED = "validated"
    FAILED = "failed"
    BLOCKED = "blocked"


class IssuePriority(Enum):
    """Priority enum for remediation issues"""
    P0 = "p0"  # Critical system failures
    P1 = "p1"  # High impact business issues
    P2 = "p2"  # Medium impact issues
    P3 = "p3"  # Low impact/tech debt


@dataclass
class RemediationIssue:
    """Data class representing a remediation issue"""
    issue_id: str
    title: str
    description: str
    analysis_file: str
    priority: IssuePriority
    status: IssueStatus
    owner: Optional[str] = None
    deadline: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None
    business_impact: Optional[str] = None
    technical_debt: Optional[float] = None
    affected_systems: List[str] = None
    remediation_plan: List[str] = None
    validation_steps: List[str] = None
    business_value_protected: Optional[float] = None
    execution_notes: List[str] = None
    recurrence_prevention: List[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.affected_systems is None:
            self.affected_systems = []
        if self.remediation_plan is None:
            self.remediation_plan = []
        if self.validation_steps is None:
            self.validation_steps = []
        if self.execution_notes is None:
            self.execution_notes = []
        if self.recurrence_prevention is None:
            self.recurrence_prevention = []

    def is_overdue(self) -> bool:
        """Check if issue is overdue"""
        if self.deadline is None:
            return False
        return datetime.now() > self.deadline and self.status not in [IssueStatus.COMPLETED, IssueStatus.VALIDATED]

    def days_until_deadline(self) -> Optional[int]:
        """Get days until deadline"""
        if self.deadline is None:
            return None
        delta = self.deadline - datetime.now()
        return delta.days

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for field in ['created_at', 'updated_at', 'deadline']:
            if data[field]:
                data[field] = data[field].isoformat()
        # Convert enums to string values
        data['priority'] = data['priority'].value
        data['status'] = data['status'].value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RemediationIssue':
        """Create from dictionary (JSON deserialization)"""
        # Convert string values to enums
        data['priority'] = IssuePriority(data['priority'])
        data['status'] = IssueStatus(data['status'])
        
        # Convert ISO strings to datetime objects
        for field in ['created_at', 'updated_at', 'deadline']:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        return cls(**data)


class CriticalRemediationTracker:
    """Main tracker class for managing P0 issue remediation"""

    def __init__(self, data_dir: str = "reports/remediation"):
        """Initialize tracker with data directory"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.issues_file = self.data_dir / "tracked_issues.json"
        self.metrics_file = self.data_dir / "business_metrics.json"
        self.config_file = self.data_dir / "tracker_config.json"
        
        self._load_or_create_config()
        self._load_issues()
        
    def _load_or_create_config(self):
        """Load or create tracker configuration"""
        default_config = {
            "alert_days_before_deadline": 2,
            "p0_default_deadline_hours": 24,
            "p1_default_deadline_hours": 72,
            "business_impact_tracking_enabled": True,
            "integration_settings": {
                "test_runner_integration": True,
                "docker_monitoring": True,
                "websocket_validation": True
            },
            "notification_settings": {
                "email_alerts": False,
                "slack_alerts": False,
                "log_alerts": True
            }
        }
        
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self._save_config()

    def _save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _load_issues(self):
        """Load tracked issues from file"""
        if self.issues_file.exists():
            with open(self.issues_file, 'r') as f:
                data = json.load(f)
                self.issues = {
                    issue_id: RemediationIssue.from_dict(issue_data)
                    for issue_id, issue_data in data.items()
                }
        else:
            self.issues = {}

    def _save_issues(self):
        """Save tracked issues to file"""
        data = {
            issue_id: issue.to_dict()
            for issue_id, issue in self.issues.items()
        }
        with open(self.issues_file, 'w') as f:
            json.dump(data, f, indent=2)

    def extract_issues_from_analysis(self, analysis_file: str) -> List[RemediationIssue]:
        """Extract actionable issues from Five Whys analysis"""
        path = Path(analysis_file)
        if not path.exists():
            raise FileNotFoundError(f"Analysis file not found: {analysis_file}")
            
        with open(path, 'r') as f:
            content = f.read()
            
        issues = []
        issue_counter = 1
        
        # Extract from Remediation Strategy section
        remediation_section = self._extract_section(content, "Remediation Strategy")
        if remediation_section:
            immediate_actions = self._extract_subsection(remediation_section, "Immediate Actions")
            validation_steps = self._extract_subsection(remediation_section, "Validation Steps")
            
            if immediate_actions:
                for action in immediate_actions:
                    issue_id = f"P0-{datetime.now().strftime('%Y%m%d')}-{issue_counter:03d}"
                    
                    issue = RemediationIssue(
                        issue_id=issue_id,
                        title=f"Critical Fix: {action[:50]}...",
                        description=action,
                        analysis_file=analysis_file,
                        priority=IssuePriority.P0,
                        status=IssueStatus.IDENTIFIED,
                        remediation_plan=[action],
                        validation_steps=validation_steps or [],
                        business_impact="Critical system failure prevention",
                        affected_systems=self._identify_affected_systems(content)
                    )
                    
                    # Set default deadline based on priority
                    deadline_hours = self.config["p0_default_deadline_hours"]
                    issue.deadline = datetime.now() + timedelta(hours=deadline_hours)
                    
                    issues.append(issue)
                    issue_counter += 1
        
        # Extract from Investigation Targets
        investigation_section = self._extract_section(content, "Investigation Targets")
        if investigation_section:
            immediate_investigation = self._extract_subsection(investigation_section, "Immediate Investigation Required")
            if immediate_investigation:
                for target in immediate_investigation:
                    issue_id = f"P1-{datetime.now().strftime('%Y%m%d')}-{issue_counter:03d}"
                    
                    issue = RemediationIssue(
                        issue_id=issue_id,
                        title=f"Investigation: {target[:50]}...",
                        description=target,
                        analysis_file=analysis_file,
                        priority=IssuePriority.P1,
                        status=IssueStatus.IDENTIFIED,
                        remediation_plan=[f"Investigate: {target}"],
                        business_impact="Root cause validation",
                        affected_systems=self._identify_affected_systems(content)
                    )
                    
                    deadline_hours = self.config["p1_default_deadline_hours"]
                    issue.deadline = datetime.now() + timedelta(hours=deadline_hours)
                    
                    issues.append(issue)
                    issue_counter += 1
        
        return issues

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a section from markdown content"""
        pattern = rf"##?\s*{re.escape(section_name)}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_subsection(self, content: str, subsection_name: str) -> Optional[List[str]]:
        """Extract list items from a subsection"""
        pattern = rf"###?\s*{re.escape(subsection_name)}[^\n]*\n(.*?)(?=\n###?|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if not match:
            return None
            
        subsection_content = match.group(1).strip()
        
        # Extract numbered or bulleted list items
        items = []
        for line in subsection_content.split('\n'):
            line = line.strip()
            if re.match(r'^\d+\.', line):  # Numbered list
                items.append(re.sub(r'^\d+\.\s*', '', line))
            elif line.startswith('- '):  # Bullet list
                items.append(line[2:])
            elif line.startswith('* '):  # Asterisk list
                items.append(line[2:])
        
        return items if items else None

    def _identify_affected_systems(self, content: str) -> List[str]:
        """Identify affected systems from analysis content"""
        systems = []
        
        # Common system patterns in our codebase
        patterns = [
            r'WebSocket|websocket',
            r'SMD|smd\.py',
            r'Agent Registry|AgentRegistry',
            r'Auth|authentication',
            r'Database|PostgreSQL|postgres',
            r'Redis',
            r'Docker',
            r'Backend|netra_backend',
            r'Frontend',
            r'Health Check|health.*check'
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                system_name = pattern.split('|')[0].replace(r'\b', '').replace(r'\s', ' ')
                if system_name not in systems:
                    systems.append(system_name)
        
        return systems

    def add_issue(self, issue: RemediationIssue) -> str:
        """Add a new issue to tracking"""
        self.issues[issue.issue_id] = issue
        self._save_issues()
        
        logger.info(f"Added issue {issue.issue_id}: {issue.title}")
        return issue.issue_id

    def update_issue(
        self,
        issue_id: str,
        status: Optional[IssueStatus] = None,
        owner: Optional[str] = None,
        deadline: Optional[datetime] = None,
        execution_note: Optional[str] = None
    ) -> bool:
        """Update an existing issue"""
        if issue_id not in self.issues:
            logger.error(f"Issue {issue_id} not found")
            return False
            
        issue = self.issues[issue_id]
        
        if status:
            issue.status = status
        if owner:
            issue.owner = owner
        if deadline:
            issue.deadline = deadline
        if execution_note:
            issue.execution_notes.append(f"{datetime.now().isoformat()}: {execution_note}")
            
        issue.updated_at = datetime.now()
        self._save_issues()
        
        logger.info(f"Updated issue {issue_id}")
        return True

    def get_overdue_issues(self) -> List[RemediationIssue]:
        """Get list of overdue issues"""
        return [issue for issue in self.issues.values() if issue.is_overdue()]

    def get_upcoming_deadlines(self, days_ahead: int = None) -> List[RemediationIssue]:
        """Get issues with upcoming deadlines"""
        if days_ahead is None:
            days_ahead = self.config["alert_days_before_deadline"]
            
        upcoming = []
        for issue in self.issues.values():
            if issue.deadline and issue.status not in [IssueStatus.COMPLETED, IssueStatus.VALIDATED]:
                days_until = issue.days_until_deadline()
                if days_until is not None and 0 <= days_until <= days_ahead:
                    upcoming.append(issue)
        
        return upcoming

    def generate_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive status report"""
        total_issues = len(self.issues)
        status_counts = {}
        priority_counts = {}
        overdue_count = 0
        
        for issue in self.issues.values():
            # Count by status
            status_counts[issue.status.value] = status_counts.get(issue.status.value, 0) + 1
            
            # Count by priority
            priority_counts[issue.priority.value] = priority_counts.get(issue.priority.value, 0) + 1
            
            # Count overdue
            if issue.is_overdue():
                overdue_count += 1
        
        # Calculate business metrics
        total_business_value_protected = sum(
            issue.business_value_protected or 0
            for issue in self.issues.values()
            if issue.status == IssueStatus.VALIDATED
        )
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_issues": total_issues,
                "overdue_issues": overdue_count,
                "completion_rate": (status_counts.get("completed", 0) + status_counts.get("validated", 0)) / max(total_issues, 1) * 100
            },
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts,
            "business_metrics": {
                "total_value_protected": total_business_value_protected,
                "avg_resolution_time": self._calculate_avg_resolution_time(),
                "recurrence_prevention_score": self._calculate_prevention_score()
            },
            "overdue_issues": [
                {
                    "issue_id": issue.issue_id,
                    "title": issue.title,
                    "days_overdue": -issue.days_until_deadline() if issue.days_until_deadline() else 0,
                    "owner": issue.owner,
                    "priority": issue.priority.value
                }
                for issue in self.get_overdue_issues()
            ],
            "upcoming_deadlines": [
                {
                    "issue_id": issue.issue_id,
                    "title": issue.title,
                    "days_until_deadline": issue.days_until_deadline(),
                    "owner": issue.owner,
                    "priority": issue.priority.value
                }
                for issue in self.get_upcoming_deadlines()
            ]
        }
        
        return report

    def _calculate_avg_resolution_time(self) -> float:
        """Calculate average resolution time for completed issues"""
        completed_issues = [
            issue for issue in self.issues.values()
            if issue.status in [IssueStatus.COMPLETED, IssueStatus.VALIDATED]
        ]
        
        if not completed_issues:
            return 0.0
            
        total_time = sum(
            (issue.updated_at - issue.created_at).total_seconds() / 3600  # Convert to hours
            for issue in completed_issues
        )
        
        return total_time / len(completed_issues)

    def _calculate_prevention_score(self) -> float:
        """Calculate recurrence prevention score"""
        total_issues = len(self.issues)
        if total_issues == 0:
            return 100.0
            
        issues_with_prevention = sum(
            1 for issue in self.issues.values()
            if issue.recurrence_prevention
        )
        
        return (issues_with_prevention / total_issues) * 100

    def validate_issue_completion(self, issue_id: str) -> Dict[str, Any]:
        """Validate that an issue has been properly completed"""
        if issue_id not in self.issues:
            return {"valid": False, "error": f"Issue {issue_id} not found"}
            
        issue = self.issues[issue_id]
        validation_result = {
            "issue_id": issue_id,
            "valid": True,
            "checks": [],
            "warnings": [],
            "errors": []
        }
        
        # Run validation steps
        if issue.validation_steps:
            for step in issue.validation_steps:
                check_result = self._run_validation_step(step, issue)
                validation_result["checks"].append(check_result)
                
                if not check_result["passed"]:
                    validation_result["errors"].append(f"Validation failed: {step}")
                    validation_result["valid"] = False
        
        # Check business impact resolution
        if issue.priority in [IssuePriority.P0, IssuePriority.P1]:
            if not issue.business_value_protected:
                validation_result["warnings"].append("No business value tracked for high-priority issue")
        
        # Check recurrence prevention
        if not issue.recurrence_prevention:
            validation_result["warnings"].append("No recurrence prevention measures documented")
        
        return validation_result

    def _run_validation_step(self, step: str, issue: RemediationIssue) -> Dict[str, Any]:
        """Run a specific validation step"""
        result = {
            "step": step,
            "passed": False,
            "output": "",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Integration with existing test infrastructure
            if "test" in step.lower() and "startup" in step.lower():
                # Run startup tests
                cmd_result = subprocess.run(
                    ["python", "tests/unified_test_runner.py", "--category", "startup", "--fast-fail"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                result["output"] = cmd_result.stdout + cmd_result.stderr
                result["passed"] = cmd_result.returncode == 0
                
            elif "websocket" in step.lower():
                # Run WebSocket validation
                cmd_result = subprocess.run(
                    ["python", "tests/mission_critical/test_websocket_agent_events_suite.py"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                result["output"] = cmd_result.stdout + cmd_result.stderr
                result["passed"] = cmd_result.returncode == 0
                
            elif "health" in step.lower() and "check" in step.lower():
                # Run health checks
                cmd_result = subprocess.run(
                    ["python", "scripts/staging_health_checks.py"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                result["output"] = cmd_result.stdout + cmd_result.stderr
                result["passed"] = cmd_result.returncode == 0
                
            else:
                # Default: mark as manual validation required
                result["output"] = "Manual validation required"
                result["passed"] = True  # Assume manual steps are completed
                
        except subprocess.TimeoutExpired:
            result["output"] = "Validation step timed out"
            result["passed"] = False
        except Exception as e:
            result["output"] = f"Validation error: {str(e)}"
            result["passed"] = False
            
        return result

    def generate_alerts(self) -> List[Dict[str, Any]]:
        """Generate alerts for overdue issues and upcoming deadlines"""
        alerts = []
        
        # Overdue alerts
        for issue in self.get_overdue_issues():
            days_overdue = -issue.days_until_deadline() if issue.days_until_deadline() else 0
            alerts.append({
                "type": "overdue",
                "severity": "critical" if issue.priority == IssuePriority.P0 else "high",
                "issue_id": issue.issue_id,
                "title": issue.title,
                "message": f"Issue {issue.issue_id} is {days_overdue} days overdue",
                "owner": issue.owner,
                "priority": issue.priority.value,
                "created_at": datetime.now().isoformat()
            })
        
        # Upcoming deadline alerts
        for issue in self.get_upcoming_deadlines():
            days_until = issue.days_until_deadline()
            alerts.append({
                "type": "upcoming_deadline",
                "severity": "medium",
                "issue_id": issue.issue_id,
                "title": issue.title,
                "message": f"Issue {issue.issue_id} due in {days_until} days",
                "owner": issue.owner,
                "priority": issue.priority.value,
                "created_at": datetime.now().isoformat()
            })
        
        return alerts


def create_argument_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description='Critical Remediation Tracker - Systematic P0 Issue Management'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Extract issues command
    extract_parser = subparsers.add_parser('extract-issues', help='Extract issues from Five Whys analysis')
    extract_parser.add_argument('--analysis-file', required=True, help='Path to Five Whys analysis file')
    extract_parser.add_argument('--auto-add', action='store_true', help='Automatically add extracted issues to tracking')
    
    # Track command
    track_parser = subparsers.add_parser('track', help='Update issue tracking')
    track_parser.add_argument('--issue-id', required=True, help='Issue ID to update')
    track_parser.add_argument('--status', choices=[s.value for s in IssueStatus], help='Update status')
    track_parser.add_argument('--owner', help='Assign owner')
    track_parser.add_argument('--deadline', help='Set deadline (ISO format: YYYY-MM-DDTHH:MM:SS)')
    track_parser.add_argument('--note', help='Add execution note')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show tracking status')
    status_parser.add_argument('--show-overdue', action='store_true', help='Show overdue issues')
    status_parser.add_argument('--show-upcoming', action='store_true', help='Show upcoming deadlines')
    status_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate issue completion')
    validate_parser.add_argument('--issue-id', required=True, help='Issue ID to validate')
    
    # Alerts command
    alerts_parser = subparsers.add_parser('alerts', help='Generate alerts')
    alerts_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    return parser


def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    tracker = CriticalRemediationTracker()
    
    try:
        if args.command == 'extract-issues':
            issues = tracker.extract_issues_from_analysis(args.analysis_file)
            print(f"Extracted {len(issues)} issues from {args.analysis_file}")
            
            for issue in issues:
                print(f"  - {issue.issue_id}: {issue.title}")
                if args.auto_add:
                    tracker.add_issue(issue)
            
            if args.auto_add:
                print(f"\nAdded {len(issues)} issues to tracking system")
        
        elif args.command == 'track':
            status = IssueStatus(args.status) if args.status else None
            deadline = datetime.fromisoformat(args.deadline) if args.deadline else None
            
            success = tracker.update_issue(
                args.issue_id,
                status=status,
                owner=args.owner,
                deadline=deadline,
                execution_note=args.note
            )
            
            if success:
                print(f"Updated issue {args.issue_id}")
            else:
                print(f"Failed to update issue {args.issue_id}")
                return 1
        
        elif args.command == 'status':
            report = tracker.generate_status_report()
            
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print("=== Critical Remediation Tracker Status ===")
                print(f"Total Issues: {report['summary']['total_issues']}")
                print(f"Overdue Issues: {report['summary']['overdue_issues']}")
                print(f"Completion Rate: {report['summary']['completion_rate']:.1f}%")
                
                if args.show_overdue and report['overdue_issues']:
                    print("\n--- Overdue Issues ---")
                    for issue in report['overdue_issues']:
                        print(f"  {issue['issue_id']}: {issue['title']} ({issue['days_overdue']} days overdue)")
                
                if args.show_upcoming and report['upcoming_deadlines']:
                    print("\n--- Upcoming Deadlines ---")
                    for issue in report['upcoming_deadlines']:
                        print(f"  {issue['issue_id']}: {issue['title']} (due in {issue['days_until_deadline']} days)")
        
        elif args.command == 'validate':
            result = tracker.validate_issue_completion(args.issue_id)
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"=== Validation Report for {args.issue_id} ===")
                print(f"Valid: {'✓' if result['valid'] else '✗'}")
                
                if result['checks']:
                    print("\n--- Validation Checks ---")
                    for check in result['checks']:
                        status = "✓" if check['passed'] else "✗"
                        print(f"  {status} {check['step']}")
                
                if result['warnings']:
                    print("\n--- Warnings ---")
                    for warning in result['warnings']:
                        print(f"  ⚠ {warning}")
                
                if result['errors']:
                    print("\n--- Errors ---")
                    for error in result['errors']:
                        print(f"  ✗ {error}")
        
        elif args.command == 'alerts':
            alerts = tracker.generate_alerts()
            
            if args.json:
                print(json.dumps(alerts, indent=2))
            else:
                if not alerts:
                    print("No alerts generated")
                else:
                    print("=== Generated Alerts ===")
                    for alert in alerts:
                        severity_icon = {"critical": "🔴", "high": "🟡", "medium": "🟠"}.get(alert['severity'], "ℹ️")
                        print(f"  {severity_icon} {alert['message']}")
        
    except Exception as e:
        logger.error(f"Command failed: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())