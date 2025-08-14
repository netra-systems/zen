#!/usr/bin/env python3
"""
System Status Report Generator
Analyzes codebase according to Status.xml specification and generates comprehensive status reports.
"""

import os
import re
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import glob
import asyncio
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

class StatusReportGenerator:
    def __init__(self, spec_path: str = "SPEC/Status.xml"):
        self.spec_path = Path(spec_path)
        self.project_root = Path(__file__).parent.parent
        self.report_data = defaultdict(dict)
        self.issues = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        self.wip_items = []
        self.component_status = {}
        
    def load_specification(self) -> ET.Element:
        """Load and parse the Status.xml specification"""
        tree = ET.parse(self.spec_path)
        return tree.getroot()
    
    def search_patterns(self, file_path: Path, patterns: List[Dict]) -> List[Dict]:
        """Search for patterns in a file"""
        results = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
                for pattern_info in patterns:
                    pattern = pattern_info.get('pattern', '')
                    pattern_type = pattern_info.get('type', 'general')
                    priority = pattern_info.get('priority', 'medium')
                    
                    for line_num, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            results.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': line_num,
                                'content': line.strip(),
                                'type': pattern_type,
                                'priority': priority,
                                'pattern': pattern
                            })
        except Exception as e:
            pass  # Skip files that can't be read
        return results
    
    def analyze_component_health(self, spec: ET.Element) -> Dict:
        """Analyze overall component health"""
        health_data = {}
        category = spec.find(".//category[@id='component_health']")
        
        if category:
            for check in category.findall(".//check"):
                check_id = check.get('id')
                target = check.find('target')
                patterns_elem = check.find('patterns')
                
                if target is not None and patterns_elem is not None:
                    target_pattern = target.text
                    patterns = []
                    
                    for pattern in patterns_elem.findall('pattern'):
                        patterns.append({
                            'pattern': pattern.text,
                            'type': pattern.get('type', 'general')
                        })
                    
                    # Find matching files
                    files = glob.glob(
                        str(self.project_root / target_pattern),
                        recursive=True
                    )
                    
                    issues_found = []
                    for file_path in files:
                        file_issues = self.search_patterns(Path(file_path), patterns)
                        issues_found.extend(file_issues)
                    
                    health_data[check_id] = {
                        'total_files': len(files),
                        'issues_found': len(issues_found),
                        'details': issues_found[:10]  # Limit to first 10 for brevity
                    }
        
        return health_data
    
    def analyze_work_in_progress(self, spec: ET.Element) -> List[Dict]:
        """Find all work-in-progress items"""
        wip_items = []
        category = spec.find(".//category[@id='work_in_progress']")
        
        if category:
            for check in category.findall(".//check"):
                target = check.find('target')
                patterns_elem = check.find('patterns')
                
                if target is not None and patterns_elem is not None:
                    target_pattern = target.text
                    patterns = []
                    
                    for pattern in patterns_elem.findall('pattern'):
                        patterns.append({
                            'pattern': pattern.text,
                            'priority': pattern.get('priority', 'medium')
                        })
                    
                    # Find matching files
                    files = glob.glob(
                        str(self.project_root / target_pattern),
                        recursive=True
                    )
                    
                    for file_path in files:
                        file_wip = self.search_patterns(Path(file_path), patterns)
                        wip_items.extend(file_wip)
        
        return wip_items
    
    def check_integration_status(self) -> Dict:
        """Check integration points between frontend and backend"""
        integration_status = {
            "websocket": self._check_websocket_integration(),
            "api_sync": self._check_api_sync(),
            "oauth": self._check_oauth_integration()
        }
        return integration_status
    
    def _check_websocket_integration(self) -> Dict:
        """Check WebSocket integration status"""
        status = {
            "backend_configured": False,
            "frontend_configured": False,
            "heartbeat_enabled": False,
            "auth_enabled": False
        }
        
        # Check backend WebSocket
        ws_manager = self.project_root / "app" / "ws_manager.py"
        if ws_manager.exists():
            with open(ws_manager, 'r', encoding='utf-8') as f:
                content = f.read()
                status["backend_configured"] = True
                status["heartbeat_enabled"] = "heartbeat" in content.lower()
                status["auth_enabled"] = "authenticate" in content.lower()
        
        # Check frontend WebSocket
        ws_provider = self.project_root / "frontend" / "providers" / "WebSocketProvider.tsx"
        if ws_provider.exists():
            status["frontend_configured"] = True
        
        return status
    
    def _check_api_sync(self) -> Dict:
        """Check API endpoint synchronization"""
        backend_routes = set()
        frontend_calls = set()
        
        # Scan backend routes
        routes_dir = self.project_root / "app" / "routes"
        if routes_dir.exists():
            for route_file in routes_dir.glob("**/*.py"):
                with open(route_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Find route decorators
                    routes = re.findall(r'@\w+\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', content)
                    for method, path in routes:
                        backend_routes.add(f"{method.upper()} {path}")
        
        # Scan frontend API calls
        services_dir = self.project_root / "frontend" / "services"
        if services_dir.exists():
            for service_file in services_dir.glob("**/*.ts"):
                with open(service_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Find fetch calls
                    calls = re.findall(r'fetch\s*\([^,]+,\s*\{[^}]*method:\s*["\'](\w+)', content, re.IGNORECASE)
                    frontend_calls.update(calls)
        
        return {
            "backend_endpoints": len(backend_routes),
            "frontend_calls": len(frontend_calls),
            "sample_backend": list(backend_routes)[:5],
            "sample_frontend": list(frontend_calls)[:5]
        }
    
    def _check_oauth_integration(self) -> Dict:
        """Check OAuth integration status"""
        oauth_status = {
            "google_configured": False,
            "callback_configured": False,
            "frontend_login": False
        }
        
        # Check backend OAuth
        oauth_file = self.project_root / "app" / "auth" / "oauth.py"
        if oauth_file.exists():
            with open(oauth_file, 'r', encoding='utf-8') as f:
                content = f.read()
                oauth_status["google_configured"] = "google" in content.lower()
                oauth_status["callback_configured"] = "callback" in content.lower()
        
        # Check frontend OAuth
        auth_dir = self.project_root / "frontend" / "app" / "auth"
        if auth_dir.exists():
            for auth_file in auth_dir.glob("**/*.tsx"):
                with open(auth_file, 'r', encoding='utf-8') as f:
                    if "google" in f.read().lower():
                        oauth_status["frontend_login"] = True
                        break
        
        return oauth_status
    
    def check_agent_system(self) -> Dict:
        """Check agent system status"""
        agent_status = {
            "supervisor": self._check_supervisor_status(),
            "sub_agents": self._check_sub_agents(),
            "apex_optimizer": self._check_apex_optimizer()
        }
        return agent_status
    
    def _check_supervisor_status(self) -> Dict:
        """Check supervisor implementation status"""
        status = {
            "legacy_exists": False,
            "consolidated_exists": False,
            "active_version": "unknown"
        }
        
        legacy = self.project_root / "app" / "agents" / "supervisor.py"
        consolidated = self.project_root / "app" / "agents" / "supervisor_consolidated.py"
        
        status["legacy_exists"] = legacy.exists()
        status["consolidated_exists"] = consolidated.exists()
        
        # Check which is imported in agent_service
        agent_service = self.project_root / "app" / "services" / "agent_service.py"
        if agent_service.exists():
            with open(agent_service, 'r', encoding='utf-8') as f:
                content = f.read()
                if "supervisor_consolidated" in content:
                    status["active_version"] = "consolidated"
                elif "supervisor" in content:
                    status["active_version"] = "legacy"
        
        return status
    
    def _check_sub_agents(self) -> List[Dict]:
        """Check sub-agent status"""
        agents = []
        agents_dir = self.project_root / "app" / "agents"
        
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*_sub_agent.py"):
                agent_name = agent_file.stem
                with open(agent_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    has_tools = "tool" in content.lower()
                    has_error_handling = "try:" in content or "except:" in content
                    
                    agents.append({
                        "name": agent_name,
                        "file": agent_file.name,
                        "has_tools": has_tools,
                        "has_error_handling": has_error_handling
                    })
        
        return agents
    
    def _check_apex_optimizer(self) -> Dict:
        """Check Apex Optimizer Agent status"""
        status = {
            "exists": False,
            "tool_count": 0,
            "tools": []
        }
        
        apex_dir = self.project_root / "app" / "services" / "apex_optimizer_agent"
        if apex_dir.exists():
            status["exists"] = True
            tools_dir = apex_dir / "tools"
            if tools_dir.exists():
                tool_files = list(tools_dir.glob("*.py"))
                status["tool_count"] = len(tool_files)
                status["tools"] = [f.stem for f in tool_files if f.stem != "__init__" and f.stem != "base"][:10]
        
        return status
    
    def check_test_coverage(self) -> Dict:
        """Check test coverage status"""
        coverage_status = {
            "backend": {
                "target": 70,
                "current": "unknown",
                "test_files": 0
            },
            "frontend": {
                "target": 60,
                "current": "unknown",
                "test_files": 0
            }
        }
        
        # Count backend test files
        backend_tests = self.project_root / "app" / "tests"
        if backend_tests.exists():
            test_files = list(backend_tests.glob("**/*.py"))
            coverage_status["backend"]["test_files"] = len(test_files)
        
        # Count frontend test files
        frontend_tests = self.project_root / "frontend" / "__tests__"
        if frontend_tests.exists():
            test_files = list(frontend_tests.glob("**/*.test.tsx")) + list(frontend_tests.glob("**/*.test.ts"))
            coverage_status["frontend"]["test_files"] = len(test_files)
        
        # Check for coverage reports
        backend_coverage = self.project_root / "reports" / "coverage" / "index.html"
        if backend_coverage.exists():
            coverage_status["backend"]["current"] = "Report exists - check manually"
        
        frontend_coverage = self.project_root / "reports" / "frontend-coverage" / "index.html"
        if frontend_coverage.exists():
            coverage_status["frontend"]["current"] = "Report exists - check manually"
        
        return coverage_status
    
    def run_quick_tests(self) -> Dict:
        """Run quick tests to check system health"""
        test_results = {
            "executed": False,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            # Try to run quick tests
            result = subprocess.run(
                ["python", "test_runner.py", "--mode", "quick"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            test_results["executed"] = True
            output = result.stdout + result.stderr
            
            # Parse test results
            if "passed" in output.lower():
                matches = re.findall(r'(\d+)\s+passed', output, re.IGNORECASE)
                if matches:
                    test_results["passed"] = int(matches[0])
            
            if "failed" in output.lower():
                matches = re.findall(r'(\d+)\s+failed', output, re.IGNORECASE)
                if matches:
                    test_results["failed"] = int(matches[0])
            
            if result.returncode != 0:
                test_results["errors"].append("Test runner returned non-zero exit code")
                
        except subprocess.TimeoutExpired:
            test_results["errors"].append("Test execution timed out")
        except FileNotFoundError:
            test_results["errors"].append("Test runner not found")
        except Exception as e:
            test_results["errors"].append(str(e))
        
        return test_results
    
    def generate_report(self) -> str:
        """Generate the complete status report"""
        spec = self.load_specification()
        data = self._gather_report_data(spec)
        return self._build_complete_report(data)
    
    def _gather_report_data(self, spec) -> Dict[str, Any]:
        """Gather all data needed for the report"""
        return {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'component_health': self.analyze_component_health(spec),
            'wip_items': self.analyze_work_in_progress(spec),
            'integration_status': self.check_integration_status(),
            'agent_status': self.check_agent_system(),
            'test_coverage': self.check_test_coverage(),
            'test_results': self.run_quick_tests()
        }
    
    def _build_complete_report(self, data: Dict[str, Any]) -> str:
        """Build the complete status report from gathered data"""
        health_score = self._calculate_health_score(
            data['component_health'], data['integration_status'], data['test_results']
        )
        
        header = self._build_report_header(data['timestamp'], health_score, data)
        executive_summary = self._build_executive_summary(data, health_score)
        component_details = self._build_component_details(data)
        integration_section = self._build_integration_section(data['integration_status'])
        test_section = self._build_test_section(data['test_coverage'], data['test_results'])
        wip_section = self._build_wip_section(data['wip_items'])
        recommendations = self._build_recommendations_section(data)
        appendix = self._build_appendix(data)
        
        return header + executive_summary + component_details + integration_section + test_section + wip_section + recommendations + appendix
    
    def _build_report_header(self, timestamp: str, health_score: int, data: Dict) -> str:
        """Build the report header with title and timestamp"""
        return f"""# System Status Report
Generated: {timestamp}

## Executive Summary

### Overall System Health Score: {health_score}/100

"""
    
    def _build_executive_summary(self, data: Dict, health_score: int) -> str:
        """Build the executive summary section"""
        metrics = self._build_key_metrics(data)
        critical_issues = self._build_critical_issues_section(data['wip_items'])
        wip_summary = self._build_wip_summary(data['wip_items'])
        return metrics + critical_issues + wip_summary
    
    def _build_key_metrics(self, data: Dict) -> str:
        """Build the key metrics section"""
        ch = data['component_health']
        tr = data['test_results']
        return f"""### Key Metrics
- **Backend Services**: {ch.get('backend_services', {}).get('total_files', 0)} files analyzed, {ch.get('backend_services', {}).get('issues_found', 0)} issues found
- **Frontend Components**: {ch.get('frontend_components', {}).get('total_files', 0)} files analyzed, {ch.get('frontend_components', {}).get('issues_found', 0)} issues found
- **API Endpoints**: {ch.get('api_endpoints', {}).get('total_files', 0)} files analyzed, {ch.get('api_endpoints', {}).get('issues_found', 0)} issues found
- **Test Results**: {tr['passed']} passed, {tr['failed']} failed

"""
    
    def _build_critical_issues_section(self, wip_items: List) -> str:
        """Build the critical issues section"""
        critical_count, critical_report = self._extract_critical_issues(wip_items)
        return f"""### Critical Issues Requiring Immediate Attention
{critical_report}
"""
    
    def _extract_critical_issues(self, wip_items: List) -> Tuple[int, str]:
        """Extract and format critical issues"""
        critical_count = 0
        critical_report = ""
        for item in wip_items:
            if item.get('priority') == 'high' and 'CRITICAL' in item.get('content', ''):
                critical_count += 1
                critical_report += f"- **{item['file']}:{item['line']}** - {item['content'][:100]}\n"
        
        if critical_count == 0:
            critical_report += "- No critical issues found\n"
        
        return critical_count, critical_report
    
    def _build_wip_summary(self, wip_items: List) -> str:
        """Build the work-in-progress summary"""
        high_count = len([i for i in wip_items if i.get('priority') == 'high'])
        medium_count = len([i for i in wip_items if i.get('priority') == 'medium'])
        low_count = len([i for i in wip_items if i.get('priority') == 'low'])
        
        return f"""
### Components Marked as Work-In-Progress
- **Total WIP Items**: {len(wip_items)}
- **High Priority**: {high_count}
- **Medium Priority**: {medium_count}
- **Low Priority**: {low_count}

"""
    
    def _build_component_details(self, data: Dict) -> str:
        """Build the component status details section"""
        backend_section = self._build_backend_section(data['component_health'])
        frontend_section = self._build_frontend_section(data['component_health'])
        agent_section = self._build_agent_section(data['agent_status'])
        return f"""## Component Status Details

{backend_section}{frontend_section}{agent_section}"""
    
    def _build_backend_section(self, component_health: Dict) -> str:
        """Build the backend services section"""
        backend_issues = component_health.get('backend_services', {}).get('details', [])
        issues_text = self._format_component_issues(backend_issues, "All backend services operational")
        return f"""### Backend Services
{issues_text}
"""
    
    def _build_frontend_section(self, component_health: Dict) -> str:
        """Build the frontend components section"""
        frontend_issues = component_health.get('frontend_components', {}).get('details', [])
        issues_text = self._format_component_issues(frontend_issues, "All frontend components operational")
        return f"""### Frontend Components
{issues_text}
"""
    
    def _format_component_issues(self, issues: List, fallback_text: str) -> str:
        """Format component issues or return fallback text"""
        if issues:
            return "\n".join(f"- **{issue['type']}**: {issue['file']} (line {issue['line']})" for issue in issues[:5])
        return f"- {fallback_text}"
    
    def _build_agent_section(self, agent_status: Dict) -> str:
        """Build the agent system section"""
        supervisor_info = self._build_supervisor_info(agent_status['supervisor'])
        sub_agents_info = self._build_sub_agents_info(agent_status['sub_agents'])
        apex_info = self._build_apex_info(agent_status['apex_optimizer'])
        return f"""### Agent System
{supervisor_info}
{sub_agents_info}
{apex_info}
"""
    
    def _build_supervisor_info(self, supervisor: Dict) -> str:
        """Build supervisor status information"""
        return f"""- **Supervisor Status**: {supervisor['active_version']} version active
  - Legacy exists: {supervisor['legacy_exists']}
  - Consolidated exists: {supervisor['consolidated_exists']}"""
    
    def _build_sub_agents_info(self, sub_agents: List) -> str:
        """Build sub-agents information"""
        agent_lines = [f"  - {agent['name']}: Tools={agent['has_tools']}, Error Handling={agent['has_error_handling']}" for agent in sub_agents]
        return f"""- **Sub-Agents**: {len(sub_agents)} agents found
""" + "\n".join(agent_lines)
    
    def _build_apex_info(self, apex: Dict) -> str:
        """Build Apex Optimizer Agent information"""
        status = 'Configured' if apex['exists'] else 'Not Found'
        tools_sample = ', '.join(apex['tools'][:5])
        return f"""- **Apex Optimizer Agent**: {status}
  - Tool Count: {apex['tool_count']}
  - Sample Tools: {tools_sample}"""
    
    def _build_integration_section(self, integration_status: Dict) -> str:
        """Build the integration health section"""
        websocket_info = self._build_websocket_info(integration_status['websocket'])
        api_sync_info = self._build_api_sync_info(integration_status['api_sync'])
        oauth_info = self._build_oauth_info(integration_status['oauth'])
        return f"""
## Integration Health

{websocket_info}
{api_sync_info}
{oauth_info}
"""
    
    def _build_websocket_info(self, websocket: Dict) -> str:
        """Build WebSocket connection information"""
        return f"""### WebSocket Connection
- Backend Configured: {websocket['backend_configured']}
- Frontend Configured: {websocket['frontend_configured']}
- Heartbeat Enabled: {websocket['heartbeat_enabled']}
- Authentication Enabled: {websocket['auth_enabled']}"""
    
    def _build_api_sync_info(self, api_sync: Dict) -> str:
        """Build API endpoint synchronization information"""
        return f"""### API Endpoint Synchronization
- Backend Endpoints: {api_sync['backend_endpoints']}
- Frontend API Calls: {api_sync['frontend_calls']}"""
    
    def _build_oauth_info(self, oauth: Dict) -> str:
        """Build OAuth integration information"""
        return f"""### OAuth Integration
- Google OAuth Configured: {oauth['google_configured']}
- Callback Configured: {oauth['callback_configured']}
- Frontend Login: {oauth['frontend_login']}"""
    
    def _build_test_section(self, test_coverage: Dict, test_results: Dict) -> str:
        """Build the test coverage status section"""
        backend_testing = self._build_backend_testing_info(test_coverage['backend'])
        frontend_testing = self._build_frontend_testing_info(test_coverage['frontend'])
        quick_results = self._build_quick_results_info(test_results)
        return f"""
## Test Coverage Status

{backend_testing}
{frontend_testing}
{quick_results}"""
    
    def _build_backend_testing_info(self, backend: Dict) -> str:
        """Build backend testing information"""
        return f"""### Backend Testing
- **Target Coverage**: {backend['target']}%
- **Current Coverage**: {backend['current']}
- **Test Files**: {backend['test_files']}"""
    
    def _build_frontend_testing_info(self, frontend: Dict) -> str:
        """Build frontend testing information"""
        return f"""### Frontend Testing
- **Target Coverage**: {frontend['target']}%
- **Current Coverage**: {frontend['current']}
- **Test Files**: {frontend['test_files']}"""
    
    def _build_quick_results_info(self, test_results: Dict) -> str:
        """Build quick test results information"""
        error_text = "- **Errors**: " + ", ".join(test_results['errors']) + "\n" if test_results['errors'] else ""
        return f"""### Quick Test Results
- **Tests Executed**: {test_results['executed']}
- **Passed**: {test_results['passed']}
- **Failed**: {test_results['failed']}
{error_text}"""
    
    def _build_wip_section(self, wip_items: List) -> str:
        """Build the work in progress items section"""
        high_priority_section = self._build_high_priority_section(wip_items)
        incomplete_section = self._build_incomplete_section(wip_items)
        return f"""
## Work In Progress Items

{high_priority_section}
{incomplete_section}"""
    
    def _build_high_priority_section(self, wip_items: List) -> str:
        """Build high priority TODOs section"""
        high_priority = [i for i in wip_items if i.get('priority') == 'high'][:10]
        if high_priority:
            items_text = "\n".join(f"- {item['file']}:{item['line']} - {item['content'][:100]}" for item in high_priority)
        else:
            items_text = "- No high priority items found"
        return f"""### High Priority TODOs
{items_text}"""
    
    def _build_incomplete_section(self, wip_items: List) -> str:
        """Build incomplete implementations section"""
        incomplete = [i for i in wip_items if 'NotImplemented' in i.get('content', '') or 'not implemented' in i.get('content', '').lower()][:5]
        if incomplete:
            items_text = "\n".join(f"- {item['file']}:{item['line']} - {item['content'][:100]}" for item in incomplete)
        else:
            items_text = "- No incomplete implementations found"
        return f"""### Incomplete Implementations
{items_text}"""
    
    def _build_recommendations_section(self, data: Dict) -> str:
        """Build the recommendations section"""
        critical_count, _ = self._extract_critical_issues(data['wip_items'])
        wip_count = len(data['wip_items'])
        failed_tests = data['test_results']['failed']
        
        return f"""
## Known Issues and Risks

### Performance Considerations
- Review caching implementation in LLM cache service
- Check database query optimization opportunities
- Monitor WebSocket connection pool performance

### Security Considerations
- Ensure all API endpoints have proper authentication
- Verify OAuth token validation is working correctly
- Check for any exposed secrets or API keys

### Technical Debt
- **Total TODO/FIXME items**: {wip_count}
- Consider refactoring components with multiple issues
- Update deprecated endpoints and functions

## Recommendations

### Immediate Actions Required
1. Address {critical_count} critical issues found in the codebase
2. Fix {failed_tests} failing tests
3. Complete implementation of NotImplementedError functions

### Short-term Improvements (1-2 weeks)
1. Increase test coverage to meet targets (Backend: 70%, Frontend: 60%)
2. Complete work-in-progress features marked as high priority
3. Synchronize API endpoints between frontend and backend
4. Ensure WebSocket heartbeat and authentication are fully operational

### Long-term Roadmap Items (1-3 months)
1. Migrate from legacy supervisor to consolidated supervisor implementation
2. Achieve 97% test coverage goal through automated test improvement
3. Implement comprehensive monitoring and alerting system
4. Complete Apex Optimizer Agent integration with all 30+ tools
"""
    
    def _build_appendix(self, data: Dict) -> str:
        """Build the appendix section"""
        total_backend_files = sum(v.get('total_files', 0) for v in data['component_health'].values() if isinstance(v, dict))
        total_test_files = data['test_coverage']['backend']['test_files'] + data['test_coverage']['frontend']['test_files']
        
        return f"""
## Appendix

### Files Analyzed
- Backend: {total_backend_files} files
- Frontend: Check frontend/components and frontend/app directories
- Tests: {total_test_files} test files

### Report Metadata
- Specification Version: 1.0.0
- Report Generated: {data['timestamp']}
- Next Scheduled Report: Weekly

---
*This report was automatically generated based on the Status.xml specification*
"""
    
    def _calculate_health_score(self, component_health: Dict, integration: Dict, tests: Dict) -> int:
        """Calculate overall system health score (0-100)"""
        score = 100
        
        # Deduct for component issues
        for component in component_health.values():
            if isinstance(component, dict):
                issues = component.get('issues_found', 0)
                score -= min(issues * 2, 20)  # Max 20 point deduction per component
        
        # Deduct for integration issues
        if not integration['websocket']['backend_configured']:
            score -= 10
        if not integration['websocket']['frontend_configured']:
            score -= 10
        if not integration['oauth']['google_configured']:
            score -= 5
        
        # Deduct for test failures
        if tests['failed'] > 0:
            score -= min(tests['failed'] * 5, 25)  # Max 25 point deduction for test failures
        
        return max(score, 0)  # Don't go below 0
    
    def save_report(self, report: str, filename: str = None):
        """Save the report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_status_report_{timestamp}.md"
        
        reports_dir = self.project_root / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        report_path = reports_dir / filename
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Also save as the latest report
        latest_path = reports_dir / "system_status_report.md"
        with open(latest_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return report_path, latest_path


def main():
    """Main execution function"""
    print("System Status Report Generator")
    print("=" * 50)
    
    generator = StatusReportGenerator()
    
    print("Analyzing codebase according to Status.xml specification...")
    report = generator.generate_report()
    
    print("Saving report...")
    report_path, latest_path = generator.save_report(report)
    
    print(f"\nReport generated successfully!")
    print(f"- Full report: {report_path}")
    print(f"- Latest report: {latest_path}")
    
    # Print summary
    lines = report.split('\n')
    for line in lines[:30]:  # Print first 30 lines as summary
        print(line)
    
    print("\n... (see full report for complete details)")
    
    return 0


if __name__ == "__main__":
    exit(main())