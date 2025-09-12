#!/usr/bin/env python3
"""
Docker Compose Log Monitor and Auto-Fixer
Process A: Continuous monitoring with issue detection
Process B: Spawns sub-agents to fix detected issues
"""

import subprocess
import time
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field, asdict
from queue import Queue
import hashlib

@dataclass
class LogIssue:
    """Represents a detected issue in the logs"""
    id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    service: str = ""
    pattern: str = ""
    message: str = ""
    count: int = 1
    severity: str = "medium"  # low, medium, high, critical
    category: str = ""  # error, warning, performance, config, connection
    suggested_fix: str = ""
    status: str = "detected"  # detected, assigned, fixing, fixed, failed
    sub_agent_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            # Generate unique ID based on service, pattern, and message hash
            content = f"{self.service}:{self.pattern}:{self.message[:100]}"
            self.id = hashlib.md5(content.encode()).hexdigest()[:8]

class IssuePatternDetector:
    """Detects various issue patterns in Docker logs"""
    
    # Define comprehensive issue patterns
    PATTERNS = {
        # Critical errors
        r"FATAL|CRITICAL|PANIC": {"severity": "critical", "category": "error"},
        r"Cannot connect to|Connection refused": {"severity": "high", "category": "connection"},
        r"Database is locked|deadlock detected": {"severity": "critical", "category": "database"},
        
        # High priority errors
        r"ERROR|Exception|Traceback": {"severity": "high", "category": "error"},
        r"Failed to|Could not|Unable to": {"severity": "high", "category": "error"},
        r"Timeout|timed out": {"severity": "high", "category": "performance"},
        r"Out of memory|OOM": {"severity": "critical", "category": "resource"},
        
        # Connection issues
        r"Connection reset|Broken pipe": {"severity": "high", "category": "connection"},
        r"ECONNREFUSED|ETIMEDOUT": {"severity": "high", "category": "connection"},
        r"502 Bad Gateway|503 Service Unavailable": {"severity": "high", "category": "connection"},
        r"getaddrinfo failed": {"severity": "high", "category": "connection"},
        
        # Authentication/Authorization
        r"401 Unauthorized|403 Forbidden": {"severity": "medium", "category": "auth"},
        r"Invalid token|Token expired": {"severity": "medium", "category": "auth"},
        r"Authentication failed": {"severity": "medium", "category": "auth"},
        
        # Configuration issues
        r"Missing required|Invalid configuration": {"severity": "high", "category": "config"},
        r"Environment variable .* not set": {"severity": "high", "category": "config"},
        r"Port .* already in use": {"severity": "critical", "category": "config"},
        
        # Performance issues
        r"Slow query|Query took": {"severity": "medium", "category": "performance"},
        r"High memory usage|Memory limit": {"severity": "medium", "category": "resource"},
        r"CPU usage": {"severity": "low", "category": "resource"},
        
        # Repeating logs (detected separately)
        r"Retrying|Retry attempt": {"severity": "medium", "category": "retry"},
        r"Reconnecting|Attempting to reconnect": {"severity": "medium", "category": "connection"},
        
        # Warnings
        r"WARNING|WARN|Deprecated": {"severity": "low", "category": "warning"},
        r"healthcheck.*unhealthy": {"severity": "high", "category": "health"},
        
        # Import/Module issues
        r"ModuleNotFoundError|ImportError": {"severity": "critical", "category": "import"},
        r"No module named": {"severity": "critical", "category": "import"},
        
        # File system issues
        r"Permission denied|Access denied": {"severity": "high", "category": "filesystem"},
        r"No such file or directory": {"severity": "high", "category": "filesystem"},
        r"Disk full|No space left": {"severity": "critical", "category": "filesystem"},
    }
    
    def __init__(self):
        self.compiled_patterns = {
            pattern: {
                "regex": re.compile(pattern, re.IGNORECASE),
                **metadata
            }
            for pattern, metadata in self.PATTERNS.items()
        }
        self.recent_logs = []  # Keep last 100 logs for pattern detection
        self.log_counts = {}  # Track repeating messages
    
    def detect_issues(self, log_line: str, service: str) -> Optional[LogIssue]:
        """Detect issues in a single log line"""
        # Clean ANSI codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_line = ansi_escape.sub('', log_line)
        
        # Track for repetition detection
        self.recent_logs.append(clean_line)
        if len(self.recent_logs) > 100:
            self.recent_logs.pop(0)
        
        # Check for repeating patterns
        log_hash = hashlib.md5(clean_line.encode()).hexdigest()
        self.log_counts[log_hash] = self.log_counts.get(log_hash, 0) + 1
        
        # Check against all patterns
        for pattern_str, pattern_data in self.compiled_patterns.items():
            if pattern_data["regex"].search(clean_line):
                issue = LogIssue(
                    service=service,
                    pattern=pattern_str,
                    message=clean_line[:500],  # Limit message length
                    severity=pattern_data["severity"],
                    category=pattern_data["category"],
                    suggested_fix=self._suggest_fix(pattern_data["category"], clean_line)
                )
                
                # Increase severity if repeating
                if self.log_counts[log_hash] > 5:
                    issue.count = self.log_counts[log_hash]
                    if issue.severity == "low":
                        issue.severity = "medium"
                    elif issue.severity == "medium":
                        issue.severity = "high"
                
                return issue
        
        # Check for rapid repetition (5+ same messages in recent logs)
        if self.log_counts[log_hash] > 5 and self.log_counts[log_hash] % 5 == 0:
            return LogIssue(
                service=service,
                pattern="Repeating message",
                message=f"Message repeated {self.log_counts[log_hash]} times: {clean_line[:200]}",
                severity="medium",
                category="repetition",
                count=self.log_counts[log_hash],
                suggested_fix="Investigate cause of repetitive logging"
            )
        
        return None
    
    def _suggest_fix(self, category: str, message: str) -> str:
        """Suggest fixes based on category and message content"""
        suggestions = {
            "connection": "Check network connectivity, service health, and firewall rules",
            "database": "Verify database connection settings and check database health",
            "auth": "Review authentication configuration and token validity",
            "config": "Check environment variables and configuration files",
            "import": "Verify dependencies are installed and Python path is correct",
            "filesystem": "Check file permissions and disk space",
            "performance": "Review resource allocation and optimize queries/operations",
            "health": "Check service dependencies and restart if necessary",
            "resource": "Monitor resource usage and consider scaling",
        }
        
        # Specific suggestions based on message content
        if "redis" in message.lower():
            return "Check Redis connection settings and ensure Redis is running"
        elif "postgres" in message.lower() or "psql" in message.lower():
            return "Verify PostgreSQL connection and credentials"
        elif "clickhouse" in message.lower():
            return "Check ClickHouse service and connection settings"
        elif "port" in message.lower() and "already in use" in message.lower():
            return "Kill process using the port or change port configuration"
        elif "environment variable" in message.lower():
            return "Set missing environment variables in .env files"
        
        return suggestions.get(category, "Investigate root cause and apply appropriate fix")

class DockerLogMonitor:
    """Main monitoring class - Process A"""
    
    def __init__(self, environment: str = "dev"):
        self.environment = environment
        self.detector = IssuePatternDetector()
        self.detected_issues: Dict[str, LogIssue] = {}
        self.issue_queue = Queue()
        self.active_agents = 0
        self.max_agents = 3
        self.agent_lock = threading.Lock()
        self.monitoring = False
        self.report_file = Path(f"docker_issues_report_{environment}.md")
        self.issues_json = Path(f"docker_issues_{environment}.json")
        
    def start_monitoring(self):
        """Start continuous monitoring"""
        self.monitoring = True
        print(f"Starting Docker log monitoring for {self.environment.upper()} environment...")
        
        # Start issue processor thread
        processor_thread = threading.Thread(target=self._process_issues, daemon=True)
        processor_thread.start()
        
        # Main monitoring loop
        consecutive_no_issues = 0
        
        while self.monitoring:
            try:
                new_issues = self._collect_logs_and_detect_issues()
                
                if new_issues:
                    consecutive_no_issues = 0
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Detected {len(new_issues)} new issues")
                    
                    # Add to queue for processing
                    for issue in new_issues:
                        self.issue_queue.put(issue)
                        self.detected_issues[issue.id] = issue
                    
                    # Save current state
                    self._save_issues_state()
                else:
                    consecutive_no_issues += 1
                    if consecutive_no_issues % 10 == 0:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] No new issues detected (check #{consecutive_no_issues})")
                    
                    # Pause for 50 seconds if no issues
                    time.sleep(50)
                    continue
                
                # Short pause between checks when issues are found
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("\nStopping monitoring...")
                self.monitoring = False
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(10)
    
    def _collect_logs_and_detect_issues(self) -> List[LogIssue]:
        """Collect Docker logs and detect issues"""
        new_issues = []
        
        # Get list of running containers
        compose_file = f"docker-compose.{self.environment}.yml"
        env_file = f".env.{self.environment}"
        
        try:
            # Get container names
            result = subprocess.run(
                ["docker-compose", "-f", compose_file, "--env-file", env_file, "ps", "--services"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10
            )
            
            if result.returncode != 0:
                return new_issues
            
            services = result.stdout.strip().split('\n')
            
            # Collect logs from each service (last 100 lines)
            for service in services:
                if not service:
                    continue
                
                try:
                    result = subprocess.run(
                        ["docker-compose", "-f", compose_file, "--env-file", env_file, 
                         "logs", "--tail", "100", "--no-color", service],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='ignore',
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        logs = result.stdout.split('\n')
                        
                        for log_line in logs:
                            if not log_line.strip():
                                continue
                            
                            issue = self.detector.detect_issues(log_line, service)
                            if issue and issue.id not in self.detected_issues:
                                new_issues.append(issue)
                    
                except subprocess.TimeoutExpired:
                    print(f"Timeout collecting logs from {service}")
                except Exception as e:
                    print(f"Error collecting logs from {service}: {e}")
            
        except Exception as e:
            print(f"Error collecting Docker logs: {e}")
        
        return new_issues
    
    def _process_issues(self):
        """Process B: Spawn sub-agents to fix issues"""
        while self.monitoring:
            try:
                # Wait for issues
                if self.issue_queue.empty():
                    time.sleep(1)
                    continue
                
                # Check agent capacity
                with self.agent_lock:
                    if self.active_agents >= self.max_agents:
                        time.sleep(5)
                        continue
                
                # Get next issue
                issue = self.issue_queue.get(timeout=1)
                
                # Spawn sub-agent
                with self.agent_lock:
                    self.active_agents += 1
                
                # Start fix thread
                fix_thread = threading.Thread(
                    target=self._spawn_fix_agent,
                    args=(issue,),
                    daemon=True
                )
                fix_thread.start()
                
            except Exception as e:
                if "Empty" not in str(e):
                    print(f"Error in issue processor: {e}")
    
    def _spawn_fix_agent(self, issue: LogIssue):
        """Spawn a sub-agent to fix an issue"""
        try:
            print(f"\n[SUB-AGENT] Spawning agent for issue {issue.id}")
            print(f"  Service: {issue.service}")
            print(f"  Category: {issue.category}")
            print(f"  Severity: {issue.severity}")
            print(f"  Suggested fix: {issue.suggested_fix}")
            
            # Update issue status
            issue.status = "assigned"
            issue.sub_agent_id = f"agent_{issue.id}"
            self._save_issues_state()
            
            # Create fix command for sub-agent
            fix_command = self._generate_fix_command(issue)
            
            if fix_command:
                print(f"  Executing fix: {fix_command['description']}")
                issue.status = "fixing"
                self._save_issues_state()
                
                # Execute fix
                success = self._execute_fix(fix_command, issue)
                
                if success:
                    issue.status = "fixed"
                    print(f"  [U+2713] Issue {issue.id} fixed successfully")
                else:
                    issue.status = "failed"
                    print(f"  [U+2717] Failed to fix issue {issue.id}")
            else:
                issue.status = "needs_manual"
                print(f"  ! Issue {issue.id} requires manual intervention")
            
            # Update report
            self._update_unified_report(issue)
            
        except Exception as e:
            print(f"Error in fix agent for issue {issue.id}: {e}")
            issue.status = "failed"
        finally:
            with self.agent_lock:
                self.active_agents -= 1
            self._save_issues_state()
    
    def _generate_fix_command(self, issue: LogIssue) -> Optional[Dict]:
        """Generate fix command based on issue type"""
        commands = {
            "connection": {
                "redis": {
                    "description": "Restart Redis service",
                    "commands": [
                        f"docker-compose -f docker-compose.{self.environment}.yml --env-file .env.{self.environment} restart redis"
                    ]
                },
                "postgres": {
                    "description": "Restart PostgreSQL service",
                    "commands": [
                        f"docker-compose -f docker-compose.{self.environment}.yml --env-file .env.{self.environment} restart postgres"
                    ]
                },
                "default": {
                    "description": "Restart affected service",
                    "commands": [
                        f"docker-compose -f docker-compose.{self.environment}.yml --env-file .env.{self.environment} restart {issue.service}"
                    ]
                }
            },
            "import": {
                "default": {
                    "description": "Rebuild container to install dependencies",
                    "commands": [
                        f"docker-compose -f docker-compose.{self.environment}.yml --env-file .env.{self.environment} build --no-cache {issue.service}",
                        f"docker-compose -f docker-compose.{self.environment}.yml --env-file .env.{self.environment} up -d {issue.service}"
                    ]
                }
            },
            "health": {
                "default": {
                    "description": "Restart unhealthy service",
                    "commands": [
                        f"docker-compose -f docker-compose.{self.environment}.yml --env-file .env.{self.environment} restart {issue.service}"
                    ]
                }
            },
            "config": {
                "port": {
                    "description": "Kill process using port and restart",
                    "commands": [
                        "python scripts/docker_env_manager.py stop all",
                        f"python scripts/docker_env_manager.py start {self.environment}"
                    ]
                }
            }
        }
        
        # Find appropriate fix
        category_fixes = commands.get(issue.category, {})
        
        # Check for specific service fixes
        for key in category_fixes:
            if key != "default" and key in issue.message.lower():
                return category_fixes[key]
        
        # Return default fix if available
        return category_fixes.get("default")
    
    def _execute_fix(self, fix_command: Dict, issue: LogIssue) -> bool:
        """Execute fix commands"""
        try:
            for cmd in fix_command["commands"]:
                print(f"    Running: {cmd}")
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=60
                )
                
                if result.returncode != 0:
                    print(f"    Command failed: {result.stderr}")
                    return False
            
            # Verify fix by checking if issue persists
            time.sleep(10)  # Wait for services to stabilize
            
            # Check recent logs
            new_issues = self._collect_logs_and_detect_issues()
            
            # Check if same issue still exists
            for new_issue in new_issues:
                if (new_issue.service == issue.service and 
                    new_issue.category == issue.category and
                    new_issue.pattern == issue.pattern):
                    return False  # Issue still exists
            
            return True
            
        except Exception as e:
            print(f"    Error executing fix: {e}")
            return False
    
    def _update_unified_report(self, issue: LogIssue):
        """Update the unified markdown report"""
        try:
            # Read existing report or create new
            if self.report_file.exists():
                content = self.report_file.read_text(encoding='utf-8')
            else:
                content = f"# Docker Issues Report - {self.environment.upper()} Environment\n\n"
                content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Add/update issue section
            issue_section = f"""
## Issue {issue.id} - {issue.service}

- **Detected**: {issue.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- **Category**: {issue.category}
- **Severity**: {issue.severity}
- **Status**: {issue.status}
- **Pattern**: `{issue.pattern}`
- **Message**: {issue.message[:200]}...
- **Count**: {issue.count}
- **Suggested Fix**: {issue.suggested_fix}
- **Sub-Agent**: {issue.sub_agent_id or 'N/A'}

### Resolution:
"""
            
            if issue.status == "fixed":
                issue_section += " PASS:  **FIXED** - Issue has been automatically resolved\n"
            elif issue.status == "failed":
                issue_section += " FAIL:  **FAILED** - Automatic fix failed, manual intervention required\n"
            elif issue.status == "needs_manual":
                issue_section += " WARNING: [U+FE0F] **MANUAL** - Requires manual intervention\n"
            else:
                issue_section += " CYCLE:  **IN PROGRESS** - Fix in progress\n"
            
            issue_section += "\n---\n"
            
            # Check if issue already in report
            if f"## Issue {issue.id}" in content:
                # Update existing
                pattern = re.compile(
                    f"## Issue {issue.id}.*?(?=##|$)",
                    re.DOTALL
                )
                content = pattern.sub(issue_section, content)
            else:
                # Add new
                content += issue_section
            
            # Write updated report with proper encoding
            self.report_file.write_text(content, encoding='utf-8')
            
        except Exception as e:
            print(f"Error updating report: {e}")
    
    def _save_issues_state(self):
        """Save current issues state to JSON"""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "environment": self.environment,
                "issues": [asdict(issue) for issue in self.detected_issues.values()],
                "stats": {
                    "total": len(self.detected_issues),
                    "fixed": sum(1 for i in self.detected_issues.values() if i.status == "fixed"),
                    "failed": sum(1 for i in self.detected_issues.values() if i.status == "failed"),
                    "pending": sum(1 for i in self.detected_issues.values() if i.status in ["detected", "assigned", "fixing"]),
                }
            }
            
            # Convert datetime objects to strings
            for issue in state["issues"]:
                if isinstance(issue["timestamp"], datetime):
                    issue["timestamp"] = issue["timestamp"].isoformat()
            
            self.issues_json.write_text(json.dumps(state, indent=2))
            
        except Exception as e:
            print(f"Error saving issues state: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Docker Compose Log Monitor and Auto-Fixer")
    parser.add_argument(
        "--env",
        choices=["dev", "test"],
        default="dev",
        help="Environment to monitor (default: dev)"
    )
    parser.add_argument(
        "--max-agents",
        type=int,
        default=3,
        help="Maximum concurrent fix agents (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Create and start monitor
    monitor = DockerLogMonitor(environment=args.env)
    monitor.max_agents = args.max_agents
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()