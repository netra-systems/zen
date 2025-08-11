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
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Gather all data
        component_health = self.analyze_component_health(spec)
        wip_items = self.analyze_work_in_progress(spec)
        integration_status = self.check_integration_status()
        agent_status = self.check_agent_system()
        test_coverage = self.check_test_coverage()
        test_results = self.run_quick_tests()
        
        # Calculate health score
        health_score = self._calculate_health_score(
            component_health, integration_status, test_results
        )
        
        # Build report
        report = f"""# System Status Report
Generated: {timestamp}

## Executive Summary

### Overall System Health Score: {health_score}/100

### Key Metrics
- **Backend Services**: {component_health.get('backend_services', {}).get('total_files', 0)} files analyzed, {component_health.get('backend_services', {}).get('issues_found', 0)} issues found
- **Frontend Components**: {component_health.get('frontend_components', {}).get('total_files', 0)} files analyzed, {component_health.get('frontend_components', {}).get('issues_found', 0)} issues found
- **API Endpoints**: {component_health.get('api_endpoints', {}).get('total_files', 0)} files analyzed, {component_health.get('api_endpoints', {}).get('issues_found', 0)} issues found
- **Test Results**: {test_results['passed']} passed, {test_results['failed']} failed

### Critical Issues Requiring Immediate Attention
"""
        
        # Add critical issues
        critical_count = 0
        for item in wip_items:
            if item.get('priority') == 'high' and 'CRITICAL' in item.get('content', ''):
                critical_count += 1
                report += f"- **{item['file']}:{item['line']}** - {item['content'][:100]}\n"
        
        if critical_count == 0:
            report += "- No critical issues found\n"
        
        report += f"""
### Components Marked as Work-In-Progress
- **Total WIP Items**: {len(wip_items)}
- **High Priority**: {len([i for i in wip_items if i.get('priority') == 'high'])}
- **Medium Priority**: {len([i for i in wip_items if i.get('priority') == 'medium'])}
- **Low Priority**: {len([i for i in wip_items if i.get('priority') == 'low'])}

## Component Status Details

### Backend Services
"""
        
        # Backend service issues
        backend_issues = component_health.get('backend_services', {}).get('details', [])
        if backend_issues:
            for issue in backend_issues[:5]:
                report += f"- **{issue['type']}**: {issue['file']} (line {issue['line']})\n"
        else:
            report += "- All backend services operational\n"
        
        report += """
### Frontend Components
"""
        
        # Frontend component issues
        frontend_issues = component_health.get('frontend_components', {}).get('details', [])
        if frontend_issues:
            for issue in frontend_issues[:5]:
                report += f"- **{issue['type']}**: {issue['file']} (line {issue['line']})\n"
        else:
            report += "- All frontend components operational\n"
        
        report += f"""
### Agent System
- **Supervisor Status**: {agent_status['supervisor']['active_version']} version active
  - Legacy exists: {agent_status['supervisor']['legacy_exists']}
  - Consolidated exists: {agent_status['supervisor']['consolidated_exists']}
- **Sub-Agents**: {len(agent_status['sub_agents'])} agents found
"""
        
        for agent in agent_status['sub_agents']:
            report += f"  - {agent['name']}: Tools={agent['has_tools']}, Error Handling={agent['has_error_handling']}\n"
        
        report += f"""
- **Apex Optimizer Agent**: {'Configured' if agent_status['apex_optimizer']['exists'] else 'Not Found'}
  - Tool Count: {agent_status['apex_optimizer']['tool_count']}
  - Sample Tools: {', '.join(agent_status['apex_optimizer']['tools'][:5])}

## Integration Health

### WebSocket Connection
- Backend Configured: {integration_status['websocket']['backend_configured']}
- Frontend Configured: {integration_status['websocket']['frontend_configured']}
- Heartbeat Enabled: {integration_status['websocket']['heartbeat_enabled']}
- Authentication Enabled: {integration_status['websocket']['auth_enabled']}

### API Endpoint Synchronization
- Backend Endpoints: {integration_status['api_sync']['backend_endpoints']}
- Frontend API Calls: {integration_status['api_sync']['frontend_calls']}

### OAuth Integration
- Google OAuth Configured: {integration_status['oauth']['google_configured']}
- Callback Configured: {integration_status['oauth']['callback_configured']}
- Frontend Login: {integration_status['oauth']['frontend_login']}

## Test Coverage Status

### Backend Testing
- **Target Coverage**: {test_coverage['backend']['target']}%
- **Current Coverage**: {test_coverage['backend']['current']}
- **Test Files**: {test_coverage['backend']['test_files']}

### Frontend Testing
- **Target Coverage**: {test_coverage['frontend']['target']}%
- **Current Coverage**: {test_coverage['frontend']['current']}
- **Test Files**: {test_coverage['frontend']['test_files']}

### Quick Test Results
- **Tests Executed**: {test_results['executed']}
- **Passed**: {test_results['passed']}
- **Failed**: {test_results['failed']}
"""
        
        if test_results['errors']:
            report += "- **Errors**: " + ", ".join(test_results['errors']) + "\n"
        
        report += """
## Work In Progress Items

### High Priority TODOs
"""
        
        high_priority = [i for i in wip_items if i.get('priority') == 'high'][:10]
        for item in high_priority:
            report += f"- {item['file']}:{item['line']} - {item['content'][:100]}\n"
        
        if not high_priority:
            report += "- No high priority items found\n"
        
        report += """
### Incomplete Implementations
"""
        
        incomplete = [i for i in wip_items if 'NotImplemented' in i.get('content', '') or 'not implemented' in i.get('content', '').lower()][:5]
        for item in incomplete:
            report += f"- {item['file']}:{item['line']} - {item['content'][:100]}\n"
        
        if not incomplete:
            report += "- No incomplete implementations found\n"
        
        report += f"""
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
- **Total TODO/FIXME items**: {len(wip_items)}
- Consider refactoring components with multiple issues
- Update deprecated endpoints and functions

## Recommendations

### Immediate Actions Required
1. Address {critical_count} critical issues found in the codebase
2. Fix {test_results['failed']} failing tests
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

## Appendix

### Files Analyzed
- Backend: {sum(v.get('total_files', 0) for v in component_health.values() if isinstance(v, dict))} files
- Frontend: Check frontend/components and frontend/app directories
- Tests: {test_coverage['backend']['test_files'] + test_coverage['frontend']['test_files']} test files

### Report Metadata
- Specification Version: 1.0.0
- Report Generated: {timestamp}
- Next Scheduled Report: Weekly

---
*This report was automatically generated based on the Status.xml specification*
"""
        
        return report
    
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