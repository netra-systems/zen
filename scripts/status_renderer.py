#!/usr/bin/env python3
"""
Status Report Rendering Module - Main Aggregator
Handles report generation using specialized renderers.
Complies with 300-line and 8-line function limits.
"""

from typing import Dict, List, Tuple
try:
    from .status_types import StatusReportData, PatternMatch
    from .status_section_renderers import (
        ComponentDetailsRenderer, IntegrationRenderer, 
        TestingSectionRenderer, RecommendationsRenderer
    )
except ImportError:
    from status_types import StatusReportData, PatternMatch
    from status_section_renderers import (
        ComponentDetailsRenderer, IntegrationRenderer, 
        TestingSectionRenderer, RecommendationsRenderer
    )


class StatusReportRenderer:
    """Renders status reports in markdown format"""
    
    def __init__(self):
        self.component_renderer = ComponentDetailsRenderer()
        self.integration_renderer = IntegrationRenderer()
        self.testing_renderer = TestingSectionRenderer()
        self.recommendations_renderer = RecommendationsRenderer()
    
    def build_complete_report(self, data: StatusReportData, health_score: int) -> str:
        """Build complete status report"""
        sections = []
        sections.append(self._build_header(data.timestamp, health_score))
        sections.append(self._build_executive_summary(data, health_score))
        sections.append(self.component_renderer.build_component_details(data))
        sections.append(self.integration_renderer.build_integration_section(data.integration_status))
        sections.append(self.testing_renderer.build_test_section(data.test_coverage, data.test_results))
        sections.append(self._build_wip_section(data.wip_items))
        sections.append(self.recommendations_renderer.build_recommendations(data))
        sections.append(self.recommendations_renderer.build_appendix(data))
        return "".join(sections)
    
    def _build_header(self, timestamp: str, health_score: int) -> str:
        """Build report header"""
        return f"""# System Status Report
Generated: {timestamp}

## Executive Summary

### Overall System Health Score: {health_score}/100

"""
    
    def _build_executive_summary(self, data: StatusReportData, health_score: int) -> str:
        """Build executive summary section"""
        metrics = self._build_key_metrics(data)
        critical_issues = self._build_critical_issues_summary(data.wip_items)
        wip_summary = self._build_wip_summary(data.wip_items)
        return metrics + critical_issues + wip_summary
    
    def _build_key_metrics(self, data: StatusReportData) -> str:
        """Build key metrics section"""
        ch = data.component_health
        tr = data.test_results
        backend_metrics = self._get_component_metrics(ch, 'backend_services')
        frontend_metrics = self._get_component_metrics(ch, 'frontend_components')
        api_metrics = self._get_component_metrics(ch, 'api_endpoints')
        
        return f"""### Key Metrics
- **Backend Services**: {backend_metrics['files']} files analyzed, {backend_metrics['issues']} issues found
- **Frontend Components**: {frontend_metrics['files']} files analyzed, {frontend_metrics['issues']} issues found
- **API Endpoints**: {api_metrics['files']} files analyzed, {api_metrics['issues']} issues found
- **Test Results**: {tr.passed} passed, {tr.failed} failed

"""
    
    def _get_component_metrics(self, component_health: Dict, component_key: str) -> Dict[str, int]:
        """Get metrics for component"""
        from .status_types import ComponentHealthData
        component = component_health.get(component_key, {})
        if isinstance(component, ComponentHealthData):
            return {'files': component.total_files, 'issues': component.issues_found}
        return {'files': 0, 'issues': 0}
    
    def _build_critical_issues_summary(self, wip_items: List[PatternMatch]) -> str:
        """Build critical issues summary"""
        critical_count, critical_report = self._extract_critical_issues(wip_items)
        return f"""### Critical Issues Requiring Immediate Attention
{critical_report}"""
    
    def _extract_critical_issues(self, wip_items: List[PatternMatch]) -> Tuple[int, str]:
        """Extract critical issues"""
        critical_items = [item for item in wip_items 
                         if item.priority == 'high' and 'CRITICAL' in item.content]
        
        if not critical_items:
            return 0, "- No critical issues found\n"
        
        report_lines = []
        for item in critical_items:
            content_preview = item.content[:100]
            report_lines.append(f"- **{item.file}:{item.line}** - {content_preview}")
        
        return len(critical_items), "\n".join(report_lines) + "\n"
    
    def _build_wip_summary(self, wip_items: List[PatternMatch]) -> str:
        """Build WIP summary"""
        priority_counts = self._count_by_priority(wip_items)
        
        return f"""
### Components Marked as Work-In-Progress
- **Total WIP Items**: {len(wip_items)}
- **High Priority**: {priority_counts['high']}
- **Medium Priority**: {priority_counts['medium']}
- **Low Priority**: {priority_counts['low']}

"""
    
    def _count_by_priority(self, wip_items: List[PatternMatch]) -> Dict[str, int]:
        """Count items by priority"""
        return {
            'high': len([i for i in wip_items if i.priority == 'high']),
            'medium': len([i for i in wip_items if i.priority == 'medium']),
            'low': len([i for i in wip_items if i.priority == 'low'])
        }
    
    def _build_wip_section(self, wip_items: List[PatternMatch]) -> str:
        """Build work in progress items section"""
        high_priority_section = self._build_high_priority_section(wip_items)
        incomplete_section = self._build_incomplete_section(wip_items)
        return f"""
## Work In Progress Items

{high_priority_section}
{incomplete_section}"""
    
    def _build_high_priority_section(self, wip_items: List[PatternMatch]) -> str:
        """Build high priority TODOs section"""
        high_priority = [i for i in wip_items if i.priority == 'high'][:10]
        if high_priority:
            items_text = "\n".join(f"- {item.file}:{item.line} - {item.content[:100]}" for item in high_priority)
        else:
            items_text = "- No high priority items found"
        return f"""### High Priority TODOs
{items_text}"""
    
    def _build_incomplete_section(self, wip_items: List[PatternMatch]) -> str:
        """Build incomplete implementations section"""
        incomplete = [i for i in wip_items if 'NotImplemented' in i.content or 'not implemented' in i.content.lower()][:5]
        if incomplete:
            items_text = "\n".join(f"- {item.file}:{item.line} - {item.content[:100]}" for item in incomplete)
        else:
            items_text = "- No incomplete implementations found"
        return f"""### Incomplete Implementations
{items_text}"""