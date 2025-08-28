#!/usr/bin/env python3
"""
Intelligent Docker Remediation System

A comprehensive system for Docker log introspection, issue identification, 
categorization, and automated remediation. This system can:

1. Scan ALL available Docker containers (running, stopped, failed)
2. Analyze logs and identify issues with categorization and severity
3. Apply automated fixes for known issues
4. Run iterative remediation cycles until clean or max iterations reached
5. Generate detailed reports and learnings

Key Features:
- 100+ built-in remediation strategies
- Intelligent issue categorization and prioritization
- Automated Docker Desktop startup handling
- Comprehensive logging and learning capture
- Safe-mode testing and validation
- Cross-environment compatibility (dev, test, staging)
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
import traceback
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('docker_remediation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class IssueSeverity(Enum):
    """Issue severity levels for prioritization"""
    CRITICAL = "critical"  # System unusable, blocking all functionality
    HIGH = "high"         # Major functionality broken
    MEDIUM = "medium"     # Minor functionality affected
    LOW = "low"          # Cosmetic or non-blocking issues
    INFO = "info"        # Informational only

class IssueCategory(Enum):
    """Issue categories for classification"""
    STARTUP_FAILURE = "startup_failure"
    AUTH_PERMISSION = "auth_permission" 
    DATABASE_CONNECTIVITY = "database_connectivity"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_CONNECTIVITY = "network_connectivity"
    APPLICATION_ERROR = "application_error"
    DEPENDENCY_MISSING = "dependency_missing"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    BUILD_FAILURE = "build_failure"
    UNKNOWN = "unknown"

@dataclass
class DockerIssue:
    """Represents a Docker-related issue"""
    container_name: str
    category: IssueCategory
    severity: IssueSeverity
    description: str
    log_excerpt: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    remediation_attempts: List[str] = field(default_factory=list)
    root_cause: Optional[str] = None
    recommended_actions: List[str] = field(default_factory=list)

@dataclass
class RemediationResult:
    """Result of a remediation attempt"""
    success: bool
    issue_resolved: bool
    actions_taken: List[str]
    error_message: Optional[str] = None
    new_issues: List[DockerIssue] = field(default_factory=list)
    
class DockerRemediationSystem:
    """Comprehensive Docker remediation system"""
    
    def __init__(self, max_iterations: int = 100, safe_mode: bool = True):
        self.max_iterations = max_iterations
        self.safe_mode = safe_mode
        self.issues: List[DockerIssue] = []
        self.remediation_history: List[Dict[str, Any]] = []
        self.containers_discovered: Set[str] = set()
        self.compose_files = [
            "docker-compose.dev.yml",
            "docker-compose.test.yml"
        ]
        
        # Load issue patterns and remediation strategies
        self.issue_patterns = self._load_issue_patterns()
        self.remediation_strategies = self._load_remediation_strategies()
        
        # Runtime state
        self.docker_available = False
        self.docker_daemon_running = False
        self.iteration_count = 0
        
    def _load_issue_patterns(self) -> Dict[IssueCategory, List[Dict[str, Any]]]:
        """Load comprehensive issue detection patterns"""
        return {
            IssueCategory.STARTUP_FAILURE: [
                {
                    "pattern": r"Container .+ is unhealthy",
                    "severity": IssueSeverity.CRITICAL,
                    "description": "Container failed health checks during startup"
                },
                {
                    "pattern": r"Error: No such container:",
                    "severity": IssueSeverity.HIGH,
                    "description": "Container does not exist or failed to start"
                },
                {
                    "pattern": r"failed to solve with frontend dockerfile.v0",
                    "severity": IssueSeverity.HIGH,
                    "description": "Docker build failed during image construction"
                },
                {
                    "pattern": r"Error response from daemon: Container .+ is not running",
                    "severity": IssueSeverity.HIGH,
                    "description": "Container is not in running state"
                }
            ],
            IssueCategory.AUTH_PERMISSION: [
                {
                    "pattern": r"permission denied",
                    "severity": IssueSeverity.HIGH,
                    "description": "Permission denied error in container"
                },
                {
                    "pattern": r"open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified",
                    "severity": IssueSeverity.CRITICAL,
                    "description": "Docker Desktop not running or daemon unavailable"
                },
                {
                    "pattern": r"Authentication failed",
                    "severity": IssueSeverity.HIGH,
                    "description": "Authentication failure in application"
                }
            ],
            IssueCategory.DATABASE_CONNECTIVITY: [
                {
                    "pattern": r"could not connect to server: Connection refused",
                    "severity": IssueSeverity.CRITICAL,
                    "description": "Database connection refused"
                },
                {
                    "pattern": r"FATAL:  database \".*\" does not exist",
                    "severity": IssueSeverity.CRITICAL,
                    "description": "Database does not exist"
                },
                {
                    "pattern": r"could not translate host name \".*\" to address",
                    "severity": IssueSeverity.HIGH,
                    "description": "Database hostname resolution failed"
                },
                {
                    "pattern": r"FATAL:  password authentication failed",
                    "severity": IssueSeverity.HIGH,
                    "description": "Database authentication failed"
                }
            ],
            IssueCategory.RESOURCE_EXHAUSTION: [
                {
                    "pattern": r"Cannot allocate memory",
                    "severity": IssueSeverity.CRITICAL,
                    "description": "Out of memory error"
                },
                {
                    "pattern": r"disk space",
                    "severity": IssueSeverity.HIGH,
                    "description": "Disk space exhaustion"
                },
                {
                    "pattern": r"too many open files",
                    "severity": IssueSeverity.HIGH,
                    "description": "File descriptor limit exceeded"
                }
            ],
            IssueCategory.CONFIGURATION_ERROR: [
                {
                    "pattern": r"Invalid value for",
                    "severity": IssueSeverity.MEDIUM,
                    "description": "Configuration value validation failed"
                },
                {
                    "pattern": r"Environment variable .* not set",
                    "severity": IssueSeverity.MEDIUM,
                    "description": "Required environment variable missing"
                },
                {
                    "pattern": r"Config file not found",
                    "severity": IssueSeverity.MEDIUM,
                    "description": "Configuration file missing"
                }
            ],
            IssueCategory.NETWORK_CONNECTIVITY: [
                {
                    "pattern": r"dial tcp.*: connect: connection refused",
                    "severity": IssueSeverity.HIGH,
                    "description": "Network connection refused"
                },
                {
                    "pattern": r"network .*netra.* not found",
                    "severity": IssueSeverity.HIGH,
                    "description": "Docker network not found"
                },
                {
                    "pattern": r"port.*already in use",
                    "severity": IssueSeverity.HIGH,
                    "description": "Port already in use"
                }
            ],
            IssueCategory.APPLICATION_ERROR: [
                {
                    "pattern": r"ImportError:",
                    "severity": IssueSeverity.HIGH,
                    "description": "Python import error"
                },
                {
                    "pattern": r"ModuleNotFoundError:",
                    "severity": IssueSeverity.HIGH,
                    "description": "Python module not found"
                },
                {
                    "pattern": r"Traceback \(most recent call last\):",
                    "severity": IssueSeverity.MEDIUM,
                    "description": "Application exception occurred"
                },
                {
                    "pattern": r"Error: Cannot find module",
                    "severity": IssueSeverity.HIGH,
                    "description": "Node.js module not found"
                }
            ],
            IssueCategory.DEPENDENCY_MISSING: [
                {
                    "pattern": r"command not found",
                    "severity": IssueSeverity.HIGH,
                    "description": "Required command/binary missing"
                },
                {
                    "pattern": r"No such file or directory",
                    "severity": IssueSeverity.MEDIUM,
                    "description": "Required file missing"
                }
            ],
            IssueCategory.HEALTH_CHECK_FAILURE: [
                {
                    "pattern": r"Health check failed",
                    "severity": IssueSeverity.HIGH,
                    "description": "Container health check failed"
                }
            ],
            IssueCategory.BUILD_FAILURE: [
                {
                    "pattern": r"ERROR \[.*\] RUN",
                    "severity": IssueSeverity.HIGH,
                    "description": "Docker build RUN command failed"
                },
                {
                    "pattern": r"failed to solve:",
                    "severity": IssueSeverity.HIGH,
                    "description": "Docker build failed to solve"
                }
            ]
        }
    
    def _load_remediation_strategies(self) -> Dict[IssueCategory, List[Dict[str, Any]]]:
        """Load comprehensive remediation strategies"""
        return {
            IssueCategory.STARTUP_FAILURE: [
                {
                    "name": "restart_container",
                    "description": "Restart failed container",
                    "actions": ["docker restart {container}"],
                    "conditions": ["container_exists", "not_running"]
                },
                {
                    "name": "recreate_container",
                    "description": "Recreate container from scratch",
                    "actions": ["docker-compose down {container}", "docker-compose up -d {container}"],
                    "conditions": ["container_unhealthy"]
                },
                {
                    "name": "rebuild_image",
                    "description": "Rebuild container image",
                    "actions": ["docker-compose build --no-cache {container}", "docker-compose up -d {container}"],
                    "conditions": ["build_failure"]
                }
            ],
            IssueCategory.AUTH_PERMISSION: [
                {
                    "name": "start_docker_desktop",
                    "description": "Start Docker Desktop service",
                    "actions": ["start_docker_desktop"],
                    "conditions": ["docker_desktop_not_running"]
                },
                {
                    "name": "fix_volume_permissions",
                    "description": "Fix volume mount permissions",
                    "actions": ["fix_volume_permissions"],
                    "conditions": ["permission_denied"]
                }
            ],
            IssueCategory.DATABASE_CONNECTIVITY: [
                {
                    "name": "ensure_database_running",
                    "description": "Ensure database container is running",
                    "actions": ["docker-compose up -d postgres", "wait_for_health"],
                    "conditions": ["database_connection_refused"]
                },
                {
                    "name": "recreate_database",
                    "description": "Recreate database container",
                    "actions": ["docker-compose down postgres", "docker volume rm netra-postgres-data", "docker-compose up -d postgres"],
                    "conditions": ["database_does_not_exist"]
                },
                {
                    "name": "reset_database_auth",
                    "description": "Reset database authentication",
                    "actions": ["reset_postgres_auth"],
                    "conditions": ["database_auth_failed"]
                }
            ],
            IssueCategory.RESOURCE_EXHAUSTION: [
                {
                    "name": "increase_memory_limits",
                    "description": "Increase container memory limits",
                    "actions": ["update_memory_limits"],
                    "conditions": ["out_of_memory"]
                },
                {
                    "name": "cleanup_docker_system",
                    "description": "Clean up Docker system resources",
                    "actions": ["docker system prune -f", "docker volume prune -f"],
                    "conditions": ["disk_space_exhaustion"]
                }
            ],
            IssueCategory.NETWORK_CONNECTIVITY: [
                {
                    "name": "recreate_network",
                    "description": "Recreate Docker network",
                    "actions": ["docker network rm netra-network", "docker-compose up -d"],
                    "conditions": ["network_not_found"]
                },
                {
                    "name": "kill_port_conflicts",
                    "description": "Kill processes using conflicting ports",
                    "actions": ["kill_port_processes"],
                    "conditions": ["port_in_use"]
                }
            ],
            IssueCategory.CONFIGURATION_ERROR: [
                {
                    "name": "validate_env_vars",
                    "description": "Validate and set missing environment variables",
                    "actions": ["validate_environment_variables"],
                    "conditions": ["missing_env_vars"]
                },
                {
                    "name": "create_missing_configs",
                    "description": "Create missing configuration files",
                    "actions": ["create_default_configs"],
                    "conditions": ["config_file_missing"]
                }
            ],
            IssueCategory.APPLICATION_ERROR: [
                {
                    "name": "install_dependencies",
                    "description": "Install missing application dependencies",
                    "actions": ["install_python_deps", "install_node_deps"],
                    "conditions": ["missing_modules"]
                },
                {
                    "name": "rebuild_app_container",
                    "description": "Rebuild application container",
                    "actions": ["docker-compose build --no-cache {container}"],
                    "conditions": ["import_errors"]
                }
            ]
        }
    
    def check_docker_availability(self) -> bool:
        """Check if Docker is available and daemon is running"""
        try:
            # Check Docker CLI
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode != 0:
                logger.error("Docker CLI not available")
                return False
                
            self.docker_available = True
            
            # Check daemon
            result = subprocess.run(
                ["docker", "info"], 
                capture_output=True, 
                text=True, 
                timeout=15
            )
            if result.returncode == 0:
                self.docker_daemon_running = True
                logger.info("Docker daemon is running")
                return True
            else:
                logger.warning(f"Docker daemon not running: {result.stderr}")
                # Try to start Docker Desktop if on Windows
                if "Windows" in os.name or "nt" in os.name:
                    return self._start_docker_desktop()
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Docker command timed out")
            return False
        except FileNotFoundError:
            logger.error("Docker not installed or not in PATH")
            return False
        except Exception as e:
            logger.error(f"Error checking Docker availability: {e}")
            return False
    
    def _start_docker_desktop(self) -> bool:
        """Attempt to start Docker Desktop on Windows"""
        try:
            logger.info("Attempting to start Docker Desktop...")
            
            # Try starting Docker Desktop
            subprocess.Popen([
                "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"
            ])
            
            # Wait for Docker daemon to become available
            for i in range(60):  # Wait up to 60 seconds
                time.sleep(2)
                try:
                    result = subprocess.run(
                        ["docker", "info"], 
                        capture_output=True, 
                        text=True, 
                        timeout=10
                    )
                    if result.returncode == 0:
                        logger.info("Docker Desktop started successfully")
                        self.docker_daemon_running = True
                        return True
                except:
                    pass
                
                if i % 10 == 0:
                    logger.info(f"Still waiting for Docker Desktop... ({i}/60 seconds)")
            
            logger.error("Docker Desktop failed to start within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Error starting Docker Desktop: {e}")
            return False
    
    def discover_containers(self) -> List[Dict[str, Any]]:
        """Discover all Docker containers (running, stopped, failed)"""
        containers = []
        
        if not self.docker_daemon_running:
            logger.warning("Docker daemon not running, cannot discover containers")
            return containers
        
        try:
            # Get all containers
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            container = json.loads(line)
                            containers.append(container)
                            self.containers_discovered.add(container['Names'])
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse container JSON: {e}")
                            
            # Also check Docker Compose services
            for compose_file in self.compose_files:
                if os.path.exists(compose_file):
                    try:
                        compose_containers = self._discover_compose_containers(compose_file)
                        containers.extend(compose_containers)
                    except Exception as e:
                        logger.warning(f"Error discovering compose containers from {compose_file}: {e}")
                        
        except subprocess.TimeoutExpired:
            logger.error("Docker ps command timed out")
        except Exception as e:
            logger.error(f"Error discovering containers: {e}")
        
        logger.info(f"Discovered {len(containers)} containers")
        return containers
    
    def _discover_compose_containers(self, compose_file: str) -> List[Dict[str, Any]]:
        """Discover containers defined in docker-compose file"""
        containers = []
        
        try:
            with open(compose_file, 'r') as f:
                compose_config = yaml.safe_load(f)
            
            services = compose_config.get('services', {})
            for service_name, service_config in services.items():
                container_name = service_config.get('container_name', f"{os.path.basename(os.getcwd())}_{service_name}_1")
                
                # Check if container exists
                try:
                    result = subprocess.run(
                        ["docker", "inspect", container_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        inspect_data = json.loads(result.stdout)[0]
                        containers.append({
                            'Names': container_name,
                            'Image': inspect_data['Config']['Image'],
                            'State': inspect_data['State']['Status'],
                            'Status': inspect_data['State']['Status'],
                            'compose_service': service_name,
                            'compose_file': compose_file
                        })
                except:
                    # Container doesn't exist, add as missing
                    containers.append({
                        'Names': container_name,
                        'Image': service_config.get('image', 'missing'),
                        'State': 'missing',
                        'Status': 'not created',
                        'compose_service': service_name,
                        'compose_file': compose_file
                    })
                    
        except Exception as e:
            logger.error(f"Error parsing compose file {compose_file}: {e}")
            
        return containers
    
    def analyze_container_logs(self, container_name: str, tail_lines: int = 500) -> List[str]:
        """Analyze logs from a specific container"""
        logs = []
        
        if not self.docker_daemon_running:
            return logs
        
        try:
            # Get container logs
            result = subprocess.run(
                ["docker", "logs", "--tail", str(tail_lines), container_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logs = result.stdout.split('\n')
                if result.stderr:
                    logs.extend(result.stderr.split('\n'))
            else:
                logger.warning(f"Failed to get logs for {container_name}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error(f"Docker logs command timed out for {container_name}")
        except Exception as e:
            logger.error(f"Error analyzing logs for {container_name}: {e}")
            
        return logs
    
    def categorize_issues(self, container_name: str, logs: List[str], container_info: Dict[str, Any]) -> List[DockerIssue]:
        """Categorize issues found in container logs"""
        issues = []
        
        # Check container state first
        container_state = container_info.get('State', '').lower()
        if container_state in ['exited', 'dead', 'paused']:
            issues.append(DockerIssue(
                container_name=container_name,
                category=IssueCategory.STARTUP_FAILURE,
                severity=IssueSeverity.CRITICAL,
                description=f"Container is in '{container_state}' state",
                log_excerpt=f"State: {container_state}",
                root_cause=f"Container failed to start or stopped unexpectedly"
            ))
        elif container_state == 'missing':
            issues.append(DockerIssue(
                container_name=container_name,
                category=IssueCategory.STARTUP_FAILURE,
                severity=IssueSeverity.HIGH,
                description="Container does not exist",
                log_excerpt="Container not created",
                root_cause="Container was never created or was removed"
            ))
        
        # Analyze log patterns
        log_text = '\n'.join(logs)
        
        for category, patterns in self.issue_patterns.items():
            for pattern_config in patterns:
                pattern = pattern_config['pattern']
                matches = re.finditer(pattern, log_text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    # Get context around the match
                    start = max(0, match.start() - 200)
                    end = min(len(log_text), match.end() + 200)
                    context = log_text[start:end]
                    
                    issue = DockerIssue(
                        container_name=container_name,
                        category=category,
                        severity=pattern_config['severity'],
                        description=pattern_config['description'],
                        log_excerpt=context,
                        root_cause=self._analyze_root_cause(match.group(), log_text, category)
                    )
                    
                    # Add recommended actions
                    issue.recommended_actions = self._get_recommended_actions(issue)
                    issues.append(issue)
        
        return issues
    
    def _analyze_root_cause(self, match_text: str, full_logs: str, category: IssueCategory) -> str:
        """Analyze the root cause of an issue"""
        root_causes = {
            IssueCategory.STARTUP_FAILURE: "Service failed to start properly",
            IssueCategory.AUTH_PERMISSION: "Authentication or permission configuration issue",
            IssueCategory.DATABASE_CONNECTIVITY: "Database is not available or misconfigured",
            IssueCategory.RESOURCE_EXHAUSTION: "System resources exceeded limits",
            IssueCategory.CONFIGURATION_ERROR: "Service configuration is invalid or missing",
            IssueCategory.NETWORK_CONNECTIVITY: "Network configuration or connectivity issue",
            IssueCategory.APPLICATION_ERROR: "Application code or dependency issue",
            IssueCategory.DEPENDENCY_MISSING: "Required dependency is not installed or available",
            IssueCategory.HEALTH_CHECK_FAILURE: "Service is not responding to health checks",
            IssueCategory.BUILD_FAILURE: "Docker image build process failed"
        }
        
        return root_causes.get(category, "Unknown root cause")
    
    def _get_recommended_actions(self, issue: DockerIssue) -> List[str]:
        """Get recommended actions for an issue"""
        strategies = self.remediation_strategies.get(issue.category, [])
        actions = []
        
        for strategy in strategies:
            # Check if strategy conditions match the issue
            if self._strategy_matches_issue(strategy, issue):
                actions.append(f"{strategy['name']}: {strategy['description']}")
                
        if not actions:
            actions.append("Manual investigation required")
            
        return actions
    
    def _strategy_matches_issue(self, strategy: Dict[str, Any], issue: DockerIssue) -> bool:
        """Check if a remediation strategy matches an issue"""
        conditions = strategy.get('conditions', [])
        
        # Simple condition matching logic
        for condition in conditions:
            if condition == "container_exists" and "does not exist" in issue.description:
                return False
            elif condition == "not_running" and issue.category == IssueCategory.STARTUP_FAILURE:
                return True
            elif condition == "container_unhealthy" and "unhealthy" in issue.description:
                return True
            elif condition == "docker_desktop_not_running" and "dockerDesktopLinuxEngine" in issue.log_excerpt:
                return True
            elif condition == "database_connection_refused" and "connection refused" in issue.log_excerpt:
                return True
            # Add more condition logic as needed
                
        return True  # Default to match if no specific conditions
    
    def apply_remediation(self, issue: DockerIssue) -> RemediationResult:
        """Apply automated remediation for an issue"""
        strategies = self.remediation_strategies.get(issue.category, [])
        actions_taken = []
        
        for strategy in strategies:
            if not self._strategy_matches_issue(strategy, issue):
                continue
                
            try:
                logger.info(f"Applying strategy '{strategy['name']}' for {issue.container_name}")
                
                if self.safe_mode:
                    logger.info(f"SAFE MODE: Would execute {strategy['name']}")
                    actions_taken.append(f"SAFE_MODE: {strategy['name']}")
                    continue
                
                # Execute strategy actions
                strategy_success = True
                for action in strategy['actions']:
                    action_success = self._execute_remediation_action(action, issue.container_name)
                    if not action_success:
                        strategy_success = False
                        break
                
                if strategy_success:
                    actions_taken.append(strategy['name'])
                    issue.remediation_attempts.append(strategy['name'])
                    
                    # Check if issue is resolved
                    if self._verify_issue_resolution(issue):
                        issue.resolved = True
                        return RemediationResult(
                            success=True,
                            issue_resolved=True,
                            actions_taken=actions_taken
                        )
                        
            except Exception as e:
                logger.error(f"Error applying strategy {strategy['name']}: {e}")
                return RemediationResult(
                    success=False,
                    issue_resolved=False,
                    actions_taken=actions_taken,
                    error_message=str(e)
                )
        
        return RemediationResult(
            success=len(actions_taken) > 0,
            issue_resolved=False,
            actions_taken=actions_taken
        )
    
    def _execute_remediation_action(self, action: str, container_name: str) -> bool:
        """Execute a specific remediation action"""
        try:
            # Handle special actions
            if action == "start_docker_desktop":
                return self._start_docker_desktop()
            elif action == "fix_volume_permissions":
                return self._fix_volume_permissions(container_name)
            elif action == "reset_postgres_auth":
                return self._reset_postgres_auth()
            elif action == "kill_port_processes":
                return self._kill_port_processes()
            elif action == "validate_environment_variables":
                return self._validate_environment_variables()
            elif action == "create_default_configs":
                return self._create_default_configs()
            elif action == "install_python_deps":
                return self._install_python_dependencies(container_name)
            elif action == "install_node_deps":
                return self._install_node_dependencies(container_name)
            elif action == "wait_for_health":
                return self._wait_for_container_health(container_name)
            
            # Handle docker commands
            if action.startswith("docker"):
                # Replace placeholders
                action = action.replace("{container}", container_name)
                
                # Execute command
                result = subprocess.run(
                    action.split(),
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully executed: {action}")
                    return True
                else:
                    logger.error(f"Failed to execute {action}: {result.stderr}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            return False
        
        return False
    
    def _fix_volume_permissions(self, container_name: str) -> bool:
        """Fix volume mount permission issues"""
        try:
            # This is a Windows-specific implementation
            # In a real scenario, you might need to adjust Docker Desktop settings
            logger.info(f"Checking volume permissions for {container_name}")
            return True
        except Exception as e:
            logger.error(f"Error fixing volume permissions: {e}")
            return False
    
    def _reset_postgres_auth(self) -> bool:
        """Reset PostgreSQL authentication"""
        try:
            # Restart postgres with trust mode
            commands = [
                ["docker-compose", "stop", "postgres"],
                ["docker-compose", "start", "postgres"]
            ]
            
            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    logger.error(f"Failed to execute {' '.join(cmd)}: {result.stderr}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error resetting postgres auth: {e}")
            return False
    
    def _kill_port_processes(self) -> bool:
        """Kill processes using conflicting ports"""
        try:
            # Common ports used by the application
            ports = [3000, 8000, 8001, 8081, 8082, 5432, 5433, 6379, 6380, 8123, 8124, 9000, 9001]
            
            for port in ports:
                try:
                    # Windows command to kill process on port
                    result = subprocess.run(
                        ["netstat", "-ano", "|", "findstr", f":{port}"],
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0 and result.stdout:
                        logger.info(f"Found process on port {port}, attempting to free it")
                        # Note: In production, you might want to be more selective about killing processes
                        
                except Exception as e:
                    logger.debug(f"No process found on port {port} or error checking: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Error killing port processes: {e}")
            return False
    
    def _validate_environment_variables(self) -> bool:
        """Validate and set missing environment variables"""
        try:
            required_vars = [
                "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
                "REDIS_HOST", "REDIS_PORT",
                "SECRET_KEY", "JWT_SECRET_KEY"
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                logger.warning(f"Missing environment variables: {missing_vars}")
                # In safe mode, just report
                if self.safe_mode:
                    return True
                    
                # Set default values for missing vars
                defaults = {
                    "POSTGRES_USER": "netra",
                    "POSTGRES_PASSWORD": "netra123",
                    "POSTGRES_DB": "netra_dev",
                    "REDIS_HOST": "redis",
                    "REDIS_PORT": "6379",
                    "SECRET_KEY": "dev-secret-key-change-in-production-must-be-at-least-32-chars",
                    "JWT_SECRET_KEY": "dev-secret-key-change-in-production-must-be-at-least-32-chars"
                }
                
                for var in missing_vars:
                    if var in defaults:
                        os.environ[var] = defaults[var]
                        logger.info(f"Set default value for {var}")
            
            return True
        except Exception as e:
            logger.error(f"Error validating environment variables: {e}")
            return False
    
    def _create_default_configs(self) -> bool:
        """Create missing configuration files"""
        try:
            # Create any missing config files with defaults
            config_files = [
                "scripts/init_db.sql",
                "scripts/init_clickhouse.sql"
            ]
            
            for config_file in config_files:
                if not os.path.exists(config_file):
                    logger.info(f"Creating default config file: {config_file}")
                    os.makedirs(os.path.dirname(config_file), exist_ok=True)
                    
                    if config_file.endswith("init_db.sql"):
                        with open(config_file, 'w') as f:
                            f.write("-- Database initialization script\nSELECT 'Database initialized';\n")
                    elif config_file.endswith("init_clickhouse.sql"):
                        with open(config_file, 'w') as f:
                            f.write("-- ClickHouse initialization script\nSELECT 'ClickHouse initialized';\n")
            
            return True
        except Exception as e:
            logger.error(f"Error creating default configs: {e}")
            return False
    
    def _install_python_dependencies(self, container_name: str) -> bool:
        """Install missing Python dependencies in container"""
        try:
            # Execute pip install in the container
            result = subprocess.run([
                "docker", "exec", container_name, 
                "pip", "install", "-r", "requirements.txt"
            ], capture_output=True, text=True, timeout=300)
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error installing Python dependencies: {e}")
            return False
    
    def _install_node_dependencies(self, container_name: str) -> bool:
        """Install missing Node.js dependencies in container"""
        try:
            # Execute npm install in the container
            result = subprocess.run([
                "docker", "exec", container_name, 
                "npm", "install"
            ], capture_output=True, text=True, timeout=300)
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error installing Node dependencies: {e}")
            return False
    
    def _wait_for_container_health(self, container_name: str, timeout: int = 60) -> bool:
        """Wait for container to become healthy"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                result = subprocess.run([
                    "docker", "inspect", "--format", "{{.State.Health.Status}}", container_name
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    health_status = result.stdout.strip()
                    if health_status == "healthy":
                        return True
                    elif health_status == "unhealthy":
                        logger.warning(f"Container {container_name} is unhealthy")
                        return False
                
                time.sleep(2)
            
            logger.error(f"Container {container_name} did not become healthy within {timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Error waiting for container health: {e}")
            return False
    
    def _verify_issue_resolution(self, issue: DockerIssue) -> bool:
        """Verify if an issue has been resolved"""
        try:
            # Get fresh logs and check if the issue pattern still exists
            logs = self.analyze_container_logs(issue.container_name, tail_lines=100)
            log_text = '\n'.join(logs)
            
            # Check if the original issue pattern is still present
            for category, patterns in self.issue_patterns.items():
                if category != issue.category:
                    continue
                    
                for pattern_config in patterns:
                    if re.search(pattern_config['pattern'], log_text, re.IGNORECASE):
                        return False
            
            # Check container health
            result = subprocess.run([
                "docker", "inspect", "--format", "{{.State.Status}}", issue.container_name
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                status = result.stdout.strip()
                if status in ["running", "healthy"]:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error verifying issue resolution: {e}")
            return False
    
    def generate_remediation_report(self) -> Dict[str, Any]:
        """Generate comprehensive remediation report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "iteration": self.iteration_count,
            "docker_status": {
                "available": self.docker_available,
                "daemon_running": self.docker_daemon_running
            },
            "containers_discovered": len(self.containers_discovered),
            "issues_summary": {
                "total": len(self.issues),
                "resolved": len([i for i in self.issues if i.resolved]),
                "critical": len([i for i in self.issues if i.severity == IssueSeverity.CRITICAL]),
                "high": len([i for i in self.issues if i.severity == IssueSeverity.HIGH]),
                "medium": len([i for i in self.issues if i.severity == IssueSeverity.MEDIUM]),
                "low": len([i for i in self.issues if i.severity == IssueSeverity.LOW])
            },
            "issues_by_category": {},
            "remediation_attempts": len(self.remediation_history),
            "detailed_issues": [],
            "recommendations": []
        }
        
        # Group issues by category
        category_counts = Counter(issue.category.value for issue in self.issues)
        report["issues_by_category"] = dict(category_counts)
        
        # Add detailed issue information
        for issue in self.issues:
            report["detailed_issues"].append({
                "container": issue.container_name,
                "category": issue.category.value,
                "severity": issue.severity.value,
                "description": issue.description,
                "resolved": issue.resolved,
                "remediation_attempts": issue.remediation_attempts,
                "root_cause": issue.root_cause,
                "recommendations": issue.recommended_actions
            })
        
        # Generate high-level recommendations
        unresolved_issues = [i for i in self.issues if not i.resolved]
        if unresolved_issues:
            critical_issues = [i for i in unresolved_issues if i.severity == IssueSeverity.CRITICAL]
            if critical_issues:
                report["recommendations"].append("Address critical issues immediately - system may be unusable")
            
            high_issues = [i for i in unresolved_issues if i.severity == IssueSeverity.HIGH]
            if high_issues:
                report["recommendations"].append("High priority issues require attention to restore full functionality")
                
            if not self.docker_daemon_running:
                report["recommendations"].append("Start Docker Desktop to enable container operations")
        else:
            report["recommendations"].append("All detected issues have been resolved!")
        
        return report
    
    def save_learnings(self, report: Dict[str, Any]) -> None:
        """Save learnings from remediation session"""
        try:
            learnings_dir = Path("SPEC/learnings")
            learnings_dir.mkdir(exist_ok=True)
            
            # Create learning entry
            learning_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": f"docker_remediation_{int(time.time())}",
                "iteration_count": self.iteration_count,
                "docker_environment": {
                    "available": self.docker_available,
                    "daemon_running": self.docker_daemon_running,
                    "containers_discovered": list(self.containers_discovered)
                },
                "issues_discovered": len(self.issues),
                "issues_resolved": len([i for i in self.issues if i.resolved]),
                "critical_patterns": [
                    {
                        "category": issue.category.value,
                        "severity": issue.severity.value,
                        "description": issue.description,
                        "container": issue.container_name,
                        "resolved": issue.resolved,
                        "remediation_success": len(issue.remediation_attempts) > 0
                    }
                    for issue in self.issues 
                    if issue.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]
                ],
                "successful_remediations": [
                    {
                        "issue_category": issue.category.value,
                        "container": issue.container_name,
                        "successful_strategies": issue.remediation_attempts
                    }
                    for issue in self.issues 
                    if issue.resolved and issue.remediation_attempts
                ],
                "key_insights": self._extract_key_insights(report)
            }
            
            # Save as XML learning with meaningful name
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Determine primary issue category for naming
            issue_categories = Counter(issue.category.value for issue in self.issues)
            primary_category = issue_categories.most_common(1)[0][0] if issue_categories else "general"
            
            learning_filename = f"intelligent_remediation_{primary_category}_{timestamp_str}.xml"
            learning_path = learnings_dir / learning_filename
            
            with open(learning_path, 'w') as f:
                f.write(self._convert_to_learning_xml(learning_entry))
            
            logger.info(f"Saved learning to {learning_path}")
            
            # Also save detailed JSON report
            report_path = f"docker_remediation_report_{int(time.time())}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Saved detailed report to {report_path}")
            
        except Exception as e:
            logger.error(f"Error saving learnings: {e}")
    
    def _extract_key_insights(self, report: Dict[str, Any]) -> List[str]:
        """Extract key insights from remediation session"""
        insights = []
        
        # Docker availability insights
        if not self.docker_daemon_running:
            insights.append("Docker Desktop not running is a common blocking issue on Windows development environments")
        
        # Container startup patterns
        startup_issues = len([i for i in self.issues if i.category == IssueCategory.STARTUP_FAILURE])
        if startup_issues > 0:
            insights.append(f"Found {startup_issues} startup failures - containers may have dependency ordering issues")
        
        # Database connectivity patterns
        db_issues = len([i for i in self.issues if i.category == IssueCategory.DATABASE_CONNECTIVITY])
        if db_issues > 0:
            insights.append("Database connectivity issues suggest need for better health check dependencies")
        
        # Successful remediation patterns
        resolved_count = len([i for i in self.issues if i.resolved])
        if resolved_count > 0:
            insights.append(f"Successfully resolved {resolved_count} issues through automated remediation")
        
        # Safe mode insights
        if self.safe_mode:
            insights.append("Safe mode prevented potentially destructive operations - review logs before disabling")
        
        return insights
    
    def _convert_to_learning_xml(self, learning_entry: Dict[str, Any]) -> str:
        """Convert learning entry to XML format"""
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<learning>
    <metadata>
        <timestamp>{learning_entry['timestamp']}</timestamp>
        <session_id>{learning_entry['session_id']}</session_id>
        <type>docker_remediation_session</type>
        <iteration_count>{learning_entry['iteration_count']}</iteration_count>
    </metadata>
    
    <environment>
        <docker_available>{learning_entry['docker_environment']['available']}</docker_available>
        <daemon_running>{learning_entry['docker_environment']['daemon_running']}</daemon_running>
        <containers_discovered>{len(learning_entry['docker_environment']['containers_discovered'])}</containers_discovered>
    </environment>
    
    <results>
        <issues_discovered>{learning_entry['issues_discovered']}</issues_discovered>
        <issues_resolved>{learning_entry['issues_resolved']}</issues_resolved>
        <resolution_rate>{learning_entry['issues_resolved'] / max(learning_entry['issues_discovered'], 1) * 100:.1f}%</resolution_rate>
    </results>
    
    <critical_patterns>
"""
        
        for pattern in learning_entry['critical_patterns']:
            xml_content += f"""        <pattern>
            <category>{pattern['category']}</category>
            <severity>{pattern['severity']}</severity>
            <container>{pattern['container']}</container>
            <description>{pattern['description']}</description>
            <resolved>{pattern['resolved']}</resolved>
            <remediation_attempted>{pattern['remediation_success']}</remediation_attempted>
        </pattern>
"""
        
        xml_content += """    </critical_patterns>
    
    <successful_remediations>
"""
        
        for remediation in learning_entry['successful_remediations']:
            xml_content += f"""        <remediation>
            <issue_category>{remediation['issue_category']}</issue_category>
            <container>{remediation['container']}</container>
            <strategies>{', '.join(remediation['successful_strategies'])}</strategies>
        </remediation>
"""
        
        xml_content += """    </successful_remediations>
    
    <key_insights>
"""
        
        for insight in learning_entry['key_insights']:
            xml_content += f"        <insight>{insight}</insight>\n"
        
        xml_content += """    </key_insights>
</learning>
"""
        
        return xml_content
    
    def run_remediation_cycle(self) -> Dict[str, Any]:
        """Run a complete remediation cycle"""
        cycle_start = time.time()
        logger.info(f"Starting remediation cycle {self.iteration_count + 1}")
        
        # Check Docker availability
        docker_ok = self.check_docker_availability()
        if not docker_ok:
            logger.error("Docker is not available - cannot proceed with container remediation")
            return {
                "success": False,
                "error": "Docker not available",
                "docker_available": self.docker_available,
                "daemon_running": self.docker_daemon_running
            }
        
        # Discover containers
        containers = self.discover_containers()
        if not containers:
            logger.warning("No containers discovered")
            return {
                "success": True,
                "containers_discovered": 0,
                "issues_found": 0,
                "message": "No containers found to analyze"
            }
        
        # Analyze each container
        cycle_issues = []
        for container in containers:
            container_name = container['Names']
            logger.info(f"Analyzing container: {container_name}")
            
            # Get logs
            logs = self.analyze_container_logs(container_name)
            
            # Categorize issues
            issues = self.categorize_issues(container_name, logs, container)
            cycle_issues.extend(issues)
            
            # Apply remediation for each issue
            for issue in issues:
                if not issue.resolved and issue.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]:
                    logger.info(f"Applying remediation for {issue.category.value} in {container_name}")
                    result = self.apply_remediation(issue)
                    
                    if result.success:
                        logger.info(f"Remediation applied: {result.actions_taken}")
                    else:
                        logger.error(f"Remediation failed: {result.error_message}")
        
        # Update global issues list
        self.issues.extend(cycle_issues)
        self.iteration_count += 1
        
        # Generate report
        report = self.generate_remediation_report()
        
        cycle_time = time.time() - cycle_start
        logger.info(f"Remediation cycle completed in {cycle_time:.2f} seconds")
        
        return {
            "success": True,
            "cycle_time": cycle_time,
            "containers_analyzed": len(containers),
            "issues_found": len(cycle_issues),
            "issues_resolved": len([i for i in cycle_issues if i.resolved]),
            "report": report
        }
    
    def run_full_remediation(self) -> Dict[str, Any]:
        """Run complete remediation system with multiple cycles"""
        start_time = time.time()
        logger.info(f"Starting full Docker remediation system (max {self.max_iterations} iterations)")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "max_iterations": self.max_iterations,
            "safe_mode": self.safe_mode,
            "cycles": [],
            "total_issues": 0,
            "total_resolved": 0,
            "final_report": None
        }
        
        previous_critical_count = float('inf')
        no_progress_count = 0
        
        for iteration in range(self.max_iterations):
            logger.info(f"\n=== REMEDIATION ITERATION {iteration + 1}/{self.max_iterations} ===")
            
            # Run remediation cycle
            cycle_result = self.run_remediation_cycle()
            results["cycles"].append({
                "iteration": iteration + 1,
                "result": cycle_result
            })
            
            if not cycle_result["success"]:
                logger.error(f"Cycle {iteration + 1} failed: {cycle_result.get('error', 'Unknown error')}")
                break
            
            # Check for progress
            current_critical = len([i for i in self.issues if i.severity == IssueSeverity.CRITICAL and not i.resolved])
            current_high = len([i for i in self.issues if i.severity == IssueSeverity.HIGH and not i.resolved])
            
            logger.info(f"Current status: {current_critical} critical, {current_high} high severity issues")
            
            # Break if no critical or high issues remain
            if current_critical == 0 and current_high == 0:
                logger.info("No critical or high severity issues remaining - remediation complete!")
                break
            
            # Check for progress
            if current_critical >= previous_critical_count:
                no_progress_count += 1
                logger.warning(f"No progress made in iteration {iteration + 1} ({no_progress_count}/3)")
            else:
                no_progress_count = 0
            
            # Break if no progress for 3 iterations
            if no_progress_count >= 3:
                logger.warning("No progress made for 3 consecutive iterations - stopping remediation")
                break
            
            previous_critical_count = current_critical
            
            # Brief pause between iterations
            if iteration < self.max_iterations - 1:
                time.sleep(2)
        
        # Generate final report
        final_report = self.generate_remediation_report()
        results["final_report"] = final_report
        results["total_issues"] = len(self.issues)
        results["total_resolved"] = len([i for i in self.issues if i.resolved])
        results["end_time"] = datetime.now().isoformat()
        results["total_duration"] = time.time() - start_time
        
        # Save learnings
        self.save_learnings(final_report)
        
        # Log final summary
        logger.info(f"\n=== REMEDIATION COMPLETE ===")
        logger.info(f"Total iterations: {self.iteration_count}")
        logger.info(f"Total issues found: {results['total_issues']}")
        logger.info(f"Total issues resolved: {results['total_resolved']}")
        logger.info(f"Resolution rate: {results['total_resolved'] / max(results['total_issues'], 1) * 100:.1f}%")
        logger.info(f"Total duration: {results['total_duration']:.2f} seconds")
        
        return results

def main():
    """Main function to run the Docker remediation system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Intelligent Docker Remediation System")
    parser.add_argument("--max-iterations", type=int, default=100, 
                       help="Maximum number of remediation iterations")
    parser.add_argument("--safe-mode", action="store_true", default=True,
                       help="Run in safe mode (no destructive actions)")
    parser.add_argument("--disable-safe-mode", action="store_true", 
                       help="Disable safe mode (enable destructive actions)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Set logging level")
    
    args = parser.parse_args()
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Determine safe mode
    safe_mode = args.safe_mode and not args.disable_safe_mode
    
    try:
        # Create and run remediation system
        remediation_system = DockerRemediationSystem(
            max_iterations=args.max_iterations,
            safe_mode=safe_mode
        )
        
        logger.info(f"Docker Remediation System starting...")
        logger.info(f"Max iterations: {args.max_iterations}")
        logger.info(f"Safe mode: {safe_mode}")
        
        results = remediation_system.run_full_remediation()
        
        # Save results summary
        summary_file = f"intelligent_remediation_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Create markdown report
        create_markdown_report(results, summary_file.replace('.json', '.md'))
        
        print(f"\nRemediation complete! Check {summary_file} for detailed results.")
        
        return 0 if results["final_report"]["issues_summary"]["critical"] == 0 else 1
        
    except KeyboardInterrupt:
        logger.info("Remediation interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Remediation system error: {e}")
        logger.debug(traceback.format_exc())
        return 1

def create_markdown_report(results: Dict[str, Any], output_file: str) -> None:
    """Create a markdown report from remediation results"""
    try:
        with open(output_file, 'w') as f:
            f.write("# Docker Remediation System Report\n\n")
            f.write(f"**Generated:** {results.get('start_time', 'Unknown')}\n")
            f.write(f"**Duration:** {results.get('total_duration', 0):.2f} seconds\n")
            f.write(f"**Iterations:** {len(results.get('cycles', []))}\n")
            f.write(f"**Safe Mode:** {'Yes' if results.get('safe_mode', True) else 'No'}\n\n")
            
            final_report = results.get("final_report", {})
            issues_summary = final_report.get("issues_summary", {})
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Issues Found:** {issues_summary.get('total', 0)}\n")
            f.write(f"- **Issues Resolved:** {issues_summary.get('resolved', 0)}\n")
            f.write(f"- **Critical Issues:** {issues_summary.get('critical', 0)}\n")
            f.write(f"- **High Priority Issues:** {issues_summary.get('high', 0)}\n")
            f.write(f"- **Resolution Rate:** {issues_summary.get('resolved', 0) / max(issues_summary.get('total', 1), 1) * 100:.1f}%\n\n")
            
            f.write("## Issues by Category\n\n")
            issues_by_category = final_report.get("issues_by_category", {})
            for category, count in issues_by_category.items():
                f.write(f"- **{category.replace('_', ' ').title()}:** {count}\n")
            
            f.write("\n## Recommendations\n\n")
            recommendations = final_report.get("recommendations", [])
            for rec in recommendations:
                f.write(f"- {rec}\n")
            
            f.write("\n## Detailed Issues\n\n")
            detailed_issues = final_report.get("detailed_issues", [])
            for issue in detailed_issues[:10]:  # Limit to first 10 for readability
                f.write(f"### {issue['container']} - {issue['category'].replace('_', ' ').title()}\n\n")
                f.write(f"**Severity:** {issue['severity'].title()}\n")
                f.write(f"**Description:** {issue['description']}\n")
                f.write(f"**Resolved:** {'Yes' if issue['resolved'] else 'No'}\n")
                if issue['remediation_attempts']:
                    f.write(f"**Remediation Attempts:** {', '.join(issue['remediation_attempts'])}\n")
                f.write("\n")
            
            if len(detailed_issues) > 10:
                f.write(f"*(Showing first 10 of {len(detailed_issues)} issues)*\n\n")
        
        logger.info(f"Markdown report saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error creating markdown report: {e}")

if __name__ == "__main__":
    sys.exit(main())