#!/usr/bin/env python3
"""
Agent System Status Analyzer Module
Handles agent system analysis and checks.
Complies with 300-line and 8-line function limits.
"""

from pathlib import Path
from typing import Dict, List, Optional
from .status_types import (
    SupervisorStatus, SubAgentInfo, ApexOptimizerStatus, AgentSystemStatus, StatusConfig
)


class AgentSystemAnalyzer:
    """Analyzes agent system status"""
    
    def __init__(self, config: StatusConfig):
        self.config = config
        self.project_root = config.project_root
    
    def check_agent_system(self) -> AgentSystemStatus:
        """Check complete agent system status"""
        supervisor = self._check_supervisor_status()
        sub_agents = self._check_sub_agents()
        apex_optimizer = self._check_apex_optimizer()
        
        return AgentSystemStatus(
            supervisor=supervisor,
            sub_agents=sub_agents,
            apex_optimizer=apex_optimizer
        )
    
    def _check_supervisor_status(self) -> SupervisorStatus:
        """Check supervisor implementation status"""
        legacy = self.project_root / "app" / "agents" / "supervisor.py"
        consolidated = self.project_root / "app" / "agents" / "supervisor_consolidated.py"
        active_version = self._determine_active_supervisor()
        
        return SupervisorStatus(
            legacy_exists=legacy.exists(),
            consolidated_exists=consolidated.exists(),
            active_version=active_version
        )
    
    def _determine_active_supervisor(self) -> str:
        """Determine which supervisor is active"""
        agent_service = self.project_root / "app" / "services" / "agent_service.py"
        if not agent_service.exists():
            return "unknown"
        
        content = self._read_file_safely(agent_service)
        if not content:
            return "unknown"
        
        if "supervisor_consolidated" in content:
            return "consolidated"
        elif "supervisor" in content:
            return "legacy"
        return "unknown"
    
    def _check_sub_agents(self) -> List[SubAgentInfo]:
        """Check sub-agent status"""
        agents = []
        agents_dir = self.project_root / "app" / "agents"
        
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*_sub_agent.py"):
                agent_info = self._analyze_sub_agent(agent_file)
                agents.append(agent_info)
        
        return agents
    
    def _analyze_sub_agent(self, agent_file: Path) -> SubAgentInfo:
        """Analyze individual sub-agent"""
        content = self._read_file_safely(agent_file)
        has_tools = "tool" in content.lower() if content else False
        has_error_handling = ("try:" in content or "except:" in content) if content else False
        
        return SubAgentInfo(
            name=agent_file.stem,
            file=agent_file.name,
            has_tools=has_tools,
            has_error_handling=has_error_handling
        )
    
    def _check_apex_optimizer(self) -> ApexOptimizerStatus:
        """Check Apex Optimizer Agent status"""
        apex_dir = self.project_root / "app" / "services" / "apex_optimizer_agent"
        if not apex_dir.exists():
            return ApexOptimizerStatus(exists=False, tool_count=0, tools=[])
        
        tools_dir = apex_dir / "tools"
        if not tools_dir.exists():
            return ApexOptimizerStatus(exists=True, tool_count=0, tools=[])
        
        tool_files = [f for f in tools_dir.glob("*.py") 
                     if f.stem not in ["__init__", "base"]]
        tool_names = [f.stem for f in tool_files][:10]
        
        return ApexOptimizerStatus(
            exists=True,
            tool_count=len(tool_files),
            tools=tool_names
        )
    
    def _read_file_safely(self, file_path: Path) -> Optional[str]:
        """Read file content safely"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None


class TestCoverageAnalyzer:
    """Analyzes test coverage status"""
    
    def __init__(self, config: StatusConfig):
        self.config = config
        self.project_root = config.project_root
    
    def check_test_coverage(self) -> "TestCoverageStatus":
        """Check test coverage status"""
        from .status_types import TestCoverageStatus
        backend = self._check_backend_coverage()
        frontend = self._check_frontend_coverage()
        
        return TestCoverageStatus(
            backend=backend,
            frontend=frontend
        )
    
    def _check_backend_coverage(self) -> "TestCoverageInfo":
        """Check backend test coverage"""
        from .status_types import TestCoverageInfo
        test_files = self._count_backend_test_files()
        current_coverage = self._check_backend_coverage_report()
        
        return TestCoverageInfo(
            target=70,
            current=current_coverage,
            test_files=test_files
        )
    
    def _count_backend_test_files(self) -> int:
        """Count backend test files"""
        backend_tests = self.project_root / "app" / "tests"
        if not backend_tests.exists():
            return 0
        
        test_files = list(backend_tests.glob("**/*.py"))
        return len(test_files)
    
    def _check_backend_coverage_report(self) -> str:
        """Check backend coverage report"""
        coverage_report = self.project_root / "reports" / "coverage" / "index.html"
        return "Report exists - check manually" if coverage_report.exists() else "unknown"
    
    def _check_frontend_coverage(self) -> "TestCoverageInfo":
        """Check frontend test coverage"""
        from .status_types import TestCoverageInfo
        test_files = self._count_frontend_test_files()
        current_coverage = self._check_frontend_coverage_report()
        
        return TestCoverageInfo(
            target=60,
            current=current_coverage,
            test_files=test_files
        )
    
    def _count_frontend_test_files(self) -> int:
        """Count frontend test files"""
        frontend_tests = self.project_root / "frontend" / "__tests__"
        if not frontend_tests.exists():
            return 0
        
        test_files = (list(frontend_tests.glob("**/*.test.tsx")) + 
                     list(frontend_tests.glob("**/*.test.ts")))
        return len(test_files)
    
    def _check_frontend_coverage_report(self) -> str:
        """Check frontend coverage report"""
        coverage_report = self.project_root / "reports" / "frontend-coverage" / "index.html"
        return "Report exists - check manually" if coverage_report.exists() else "unknown"


class HealthScoreCalculator:
    """Calculates overall system health score"""
    
    def calculate_health_score(self, component_health: Dict, integration: "IntegrationStatus", tests: "TestResults") -> int:
        """Calculate overall system health score (0-100)"""
        score = 100
        score = self._deduct_component_issues(score, component_health)
        score = self._deduct_integration_issues(score, integration)
        score = self._deduct_test_failures(score, tests)
        return max(score, 0)
    
    def _deduct_component_issues(self, score: int, component_health: Dict) -> int:
        """Deduct points for component issues"""
        from .status_types import ComponentHealthData
        for component in component_health.values():
            if isinstance(component, ComponentHealthData):
                issues = component.issues_found
                score -= min(issues * 2, 20)  # Max 20 point deduction per component
        return score
    
    def _deduct_integration_issues(self, score: int, integration: "IntegrationStatus") -> int:
        """Deduct points for integration issues"""
        if not integration.websocket.backend_configured:
            score -= 10
        if not integration.websocket.frontend_configured:
            score -= 10
        if not integration.oauth.google_configured:
            score -= 5
        return score
    
    def _deduct_test_failures(self, score: int, tests: "TestResults") -> int:
        """Deduct points for test failures"""
        if tests.failed > 0:
            score -= min(tests.failed * 5, 25)  # Max 25 point deduction
        return score