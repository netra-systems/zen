#!/usr/bin/env python3
"""
Status Report Type Definitions
Strongly typed interfaces for status report generation system.
All types follow type_safety.xml specification.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PatternMatch:
    """Single pattern match result"""
    file: str
    line: int
    content: str
    type: str
    priority: str
    pattern: str


@dataclass
class ComponentHealthData:
    """Component health analysis result"""
    total_files: int
    issues_found: int
    details: List[PatternMatch]


@dataclass
class WebSocketStatus:
    """WebSocket integration status"""
    backend_configured: bool
    frontend_configured: bool
    heartbeat_enabled: bool
    auth_enabled: bool


@dataclass
class ApiSyncStatus:
    """API endpoint synchronization status"""
    backend_endpoints: int
    frontend_calls: int
    sample_backend: List[str]
    sample_frontend: List[str]


@dataclass
class OAuthStatus:
    """OAuth integration status"""
    google_configured: bool
    callback_configured: bool
    frontend_login: bool


@dataclass
class IntegrationStatus:
    """Complete integration status"""
    websocket: WebSocketStatus
    api_sync: ApiSyncStatus
    oauth: OAuthStatus


@dataclass
class SupervisorStatus:
    """Supervisor agent status"""
    legacy_exists: bool
    consolidated_exists: bool
    active_version: str


@dataclass
class SubAgentInfo:
    """Sub-agent information"""
    name: str
    file: str
    has_tools: bool
    has_error_handling: bool


@dataclass
class ApexOptimizerStatus:
    """Apex Optimizer Agent status"""
    exists: bool
    tool_count: int
    tools: List[str]


@dataclass
class AgentSystemStatus:
    """Complete agent system status"""
    supervisor: SupervisorStatus
    sub_agents: List[SubAgentInfo]
    apex_optimizer: ApexOptimizerStatus


@dataclass
class TestCoverageInfo:
    """Test coverage information"""
    target: int
    current: str
    test_files: int


@dataclass
class TestCoverageStatus:
    """Complete test coverage status"""
    backend: TestCoverageInfo
    frontend: TestCoverageInfo


@dataclass
class TestResults:
    """Test execution results"""
    executed: bool
    passed: int
    failed: int
    errors: List[str]


@dataclass
class StatusReportData:
    """Complete status report data structure"""
    timestamp: str
    component_health: Dict[str, ComponentHealthData]
    wip_items: List[PatternMatch]
    integration_status: IntegrationStatus
    agent_status: AgentSystemStatus
    test_coverage: TestCoverageStatus
    test_results: TestResults


@dataclass
class HealthMetrics:
    """Health score calculation metrics"""
    component_issues: int
    integration_score: int
    test_failures: int
    overall_score: int


class StatusConfig:
    """Configuration for status report generation"""
    
    def __init__(self, project_root: Path, spec_path: str):
        self.project_root = project_root
        self.spec_path = Path(spec_path)
        self.timeout_seconds = 60
        self.max_pattern_results = 10


class IssueCategories:
    """Issue priority categories"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReportSections:
    """Report section identifiers"""
    HEADER = "header"
    EXECUTIVE_SUMMARY = "executive_summary"
    COMPONENT_DETAILS = "component_details"
    INTEGRATION = "integration"
    TESTING = "testing"
    WIP_ITEMS = "wip_items"
    RECOMMENDATIONS = "recommendations"
    APPENDIX = "appendix"