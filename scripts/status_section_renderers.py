#!/usr/bin/env python3
"""
Status Section Renderers Module
Handles rendering of specific report sections.
Complies with 300-line and 8-line function limits.
"""

from typing import Dict, List, Tuple
try:
    from .status_types import (
        StatusReportData, PatternMatch, IntegrationStatus, AgentSystemStatus,
        TestCoverageStatus, TestResults, ComponentHealthData, WebSocketStatus,
        ApiSyncStatus, OAuthStatus, SupervisorStatus, SubAgentInfo,
        ApexOptimizerStatus, TestCoverageInfo
    )
except ImportError:
    from status_types import (
        StatusReportData, PatternMatch, IntegrationStatus, AgentSystemStatus,
        TestCoverageStatus, TestResults, ComponentHealthData, WebSocketStatus,
        ApiSyncStatus, OAuthStatus, SupervisorStatus, SubAgentInfo,
        ApexOptimizerStatus, TestCoverageInfo
    )


class ComponentDetailsRenderer:
    """Renders component status details"""
    
    def build_component_details(self, data: StatusReportData) -> str:
        """Build component status details"""
        backend_section = self._build_backend_section(data.component_health)
        frontend_section = self._build_frontend_section(data.component_health)
        agent_section = self._build_agent_section(data.agent_status)
        
        return f"""## Component Status Details

{backend_section}{frontend_section}{agent_section}"""
    
    def _build_backend_section(self, component_health: Dict[str, ComponentHealthData]) -> str:
        """Build backend services section"""
        backend_data = component_health.get('backend_services')
        issues_text = self._format_component_issues(backend_data, "All backend services operational")
        
        return f"""### Backend Services
{issues_text}
"""
    
    def _build_frontend_section(self, component_health: Dict[str, ComponentHealthData]) -> str:
        """Build frontend components section"""
        frontend_data = component_health.get('frontend_components')
        issues_text = self._format_component_issues(frontend_data, "All frontend components operational")
        
        return f"""### Frontend Components
{issues_text}
"""
    
    def _format_component_issues(self, component_data: ComponentHealthData, fallback_text: str) -> str:
        """Format component issues"""
        if not component_data or not component_data.details:
            return f"- {fallback_text}"
        
        issue_lines = []
        for issue in component_data.details[:5]:
            issue_lines.append(f"- **{issue.type}**: {issue.file} (line {issue.line})")
        return "\n".join(issue_lines)
    
    def _build_agent_section(self, agent_status: AgentSystemStatus) -> str:
        """Build agent system section"""
        supervisor_info = self._format_supervisor_info(agent_status.supervisor)
        sub_agents_info = self._format_sub_agents_info(agent_status.sub_agents)
        apex_info = self._format_apex_info(agent_status.apex_optimizer)
        
        return f"""### Agent System
{supervisor_info}
{sub_agents_info}
{apex_info}
"""
    
    def _format_supervisor_info(self, supervisor: SupervisorStatus) -> str:
        """Format supervisor status"""
        return f"""- **Supervisor Status**: {supervisor.active_version} version active
  - Legacy exists: {supervisor.legacy_exists}
  - Consolidated exists: {supervisor.consolidated_exists}"""
    
    def _format_sub_agents_info(self, sub_agents: List[SubAgentInfo]) -> str:
        """Format sub-agents info"""
        agent_lines = []
        for agent in sub_agents:
            agent_lines.append(f"  - {agent.name}: Tools={agent.has_tools}, Error Handling={agent.has_error_handling}")
        
        return f"""- **Sub-Agents**: {len(sub_agents)} agents found
""" + "\n".join(agent_lines)
    
    def _format_apex_info(self, apex: ApexOptimizerStatus) -> str:
        """Format Apex Optimizer info"""
        status = 'Configured' if apex.exists else 'Not Found'
        tools_sample = ', '.join(apex.tools[:5])
        
        return f"""- **Apex Optimizer Agent**: {status}
  - Tool Count: {apex.tool_count}
  - Sample Tools: {tools_sample}"""


class IntegrationRenderer:
    """Renders integration health section"""
    
    def build_integration_section(self, integration_status: IntegrationStatus) -> str:
        """Build integration health section"""
        websocket_info = self._build_websocket_info(integration_status.websocket)
        api_sync_info = self._build_api_sync_info(integration_status.api_sync)
        oauth_info = self._build_oauth_info(integration_status.oauth)
        
        return f"""
## Integration Health

{websocket_info}
{api_sync_info}
{oauth_info}
"""
    
    def _build_websocket_info(self, websocket: WebSocketStatus) -> str:
        """Build WebSocket info"""
        return f"""### WebSocket Connection
- Backend Configured: {websocket.backend_configured}
- Frontend Configured: {websocket.frontend_configured}
- Heartbeat Enabled: {websocket.heartbeat_enabled}
- Authentication Enabled: {websocket.auth_enabled}"""
    
    def _build_api_sync_info(self, api_sync: ApiSyncStatus) -> str:
        """Build API sync info"""
        return f"""### API Endpoint Synchronization
- Backend Endpoints: {api_sync.backend_endpoints}
- Frontend API Calls: {api_sync.frontend_calls}"""
    
    def _build_oauth_info(self, oauth: OAuthStatus) -> str:
        """Build OAuth info"""
        return f"""### OAuth Integration
- Google OAuth Configured: {oauth.google_configured}
- Callback Configured: {oauth.callback_configured}
- Frontend Login: {oauth.frontend_login}"""


class TestingSectionRenderer:
    """Renders testing and coverage sections"""
    
    def build_test_section(self, test_coverage: TestCoverageStatus, test_results: TestResults) -> str:
        """Build test section"""
        backend_testing = self._build_backend_testing(test_coverage.backend)
        frontend_testing = self._build_frontend_testing(test_coverage.frontend)
        quick_results = self._build_quick_results(test_results)
        
        return f"""
## Test Coverage Status

{backend_testing}
{frontend_testing}
{quick_results}"""
    
    def _build_backend_testing(self, backend: TestCoverageInfo) -> str:
        """Build backend testing info"""
        return f"""### Backend Testing
- **Target Coverage**: {backend.target}%
- **Current Coverage**: {backend.current}
- **Test Files**: {backend.test_files}"""
    
    def _build_frontend_testing(self, frontend: TestCoverageInfo) -> str:
        """Build frontend testing info"""
        return f"""### Frontend Testing
- **Target Coverage**: {frontend.target}%
- **Current Coverage**: {frontend.current}
- **Test Files**: {frontend.test_files}"""
    
    def _build_quick_results(self, test_results: TestResults) -> str:
        """Build quick test results"""
        error_text = ""
        if test_results.errors:
            error_text = "- **Errors**: " + ", ".join(test_results.errors) + "\n"
        
        return f"""### Quick Test Results
- **Tests Executed**: {test_results.executed}
- **Passed**: {test_results.passed}
- **Failed**: {test_results.failed}
{error_text}"""


class RecommendationsRenderer:
    """Renders recommendations and appendix sections"""
    
    def build_recommendations(self, data: StatusReportData) -> str:
        """Build recommendations section"""
        critical_count, _ = self._extract_critical_count(data.wip_items)
        wip_count = len(data.wip_items)
        failed_tests = data.test_results.failed
        
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
    
    def build_appendix(self, data: StatusReportData) -> str:
        """Build appendix section"""
        total_backend_files = self._calculate_total_backend_files(data.component_health)
        total_test_files = (data.test_coverage.backend.test_files + 
                           data.test_coverage.frontend.test_files)
        
        return f"""
## Appendix

### Files Analyzed
- Backend: {total_backend_files} files
- Frontend: Check frontend/components and frontend/app directories
- Tests: {total_test_files} test files

### Report Metadata
- Specification Version: 1.0.0
- Report Generated: {data.timestamp}
- Next Scheduled Report: Weekly

---
*This report was automatically generated based on the Status.xml specification*
"""
    
    def _extract_critical_count(self, wip_items: List[PatternMatch]) -> Tuple[int, str]:
        """Extract critical issues count"""
        critical_items = [item for item in wip_items 
                         if item.priority == 'high' and 'CRITICAL' in item.content]
        return len(critical_items), ""
    
    def _calculate_total_backend_files(self, component_health: Dict[str, ComponentHealthData]) -> int:
        """Calculate total backend files"""
        total = 0
        for component in component_health.values():
            if isinstance(component, ComponentHealthData):
                total += component.total_files
        return total