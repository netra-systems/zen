#!/usr/bin/env python3
"""
Architecture Dashboard Generator
Focused module for generating HTML dashboards with small, focused functions
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from architecture_dashboard_html import DashboardHTMLComponents
from architecture_dashboard_tables import DashboardTableRenderers


class ArchitectureDashboard:
    """Generates comprehensive HTML dashboard with modular functions"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
    
    def generate_html_dashboard(self, metrics: Dict[str, Any], violations: Dict[str, Any], 
                              scan_timestamp: datetime, output_path: str = None) -> str:
        """Generate comprehensive HTML dashboard"""
        if not output_path:
            output_path = str(self.root_path / "reports" / "architecture_dashboard.html")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        html_content = self._build_html_dashboard(metrics, violations, scan_timestamp)
        
        self._write_dashboard_file(output_path, html_content)
        print(f"HTML Dashboard generated: {output_path}")
        return output_path
    
    def _write_dashboard_file(self, output_path: str, content: str) -> None:
        """Write dashboard HTML to file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _build_html_dashboard(self, metrics: Dict[str, Any], violations: Dict[str, Any], 
                            scan_timestamp: datetime) -> str:
        """Build comprehensive HTML dashboard"""
        js_data = self._prepare_javascript_data(metrics, violations, scan_timestamp)
        sections = self._generate_dashboard_sections(metrics, violations, scan_timestamp)
        javascript = self._generate_javascript(js_data)
        return self._combine_dashboard_sections(*sections, javascript)

    def _generate_dashboard_sections(self, metrics: Dict[str, Any], violations: Dict[str, Any], 
                                   scan_timestamp: datetime) -> tuple:
        """Generate all dashboard sections."""
        header = DashboardHTMLComponents.generate_dashboard_header(scan_timestamp)
        metrics_section = DashboardHTMLComponents.generate_metrics_section(metrics)
        charts_section = DashboardHTMLComponents.generate_charts_section()
        violations_section = self.generate_violations_table(violations)
        recommendations = self._render_recommendations_section(metrics)
        footer = DashboardHTMLComponents.generate_footer()
        return (header, metrics_section, charts_section, violations_section, recommendations, footer)
    
    def _prepare_javascript_data(self, metrics: Dict[str, Any], violations: Dict[str, Any], 
                               scan_timestamp: datetime) -> Dict[str, Any]:
        """Prepare data for JavaScript charts"""
        return {
            'metrics': metrics,
            'violations': violations,
            'timestamp': scan_timestamp.isoformat()
        }
    
    def generate_violations_table(self, violations: Dict[str, Any]) -> str:
        """Generate violations table section"""
        return f"""
            <div class="tab-container">
                {self._generate_tab_headers()}
                {self._generate_tab_contents(violations)}
            </div>"""
    
    def _generate_tab_headers(self) -> str:
        """Generate tab navigation headers"""
        return """
                <div class="tabs">
                    <div class="tab active" onclick="showTab('file-size')">File Size Violations</div>
                    <div class="tab" onclick="showTab('function-complexity')">Function Complexity</div>
                    <div class="tab" onclick="showTab('duplicates')">Duplicate Types</div>
                    <div class="tab" onclick="showTab('worst-offenders')">Worst Offenders</div>
                </div>"""
    
    def _generate_tab_contents(self, violations: Dict[str, Any]) -> str:
        """Generate all tab content sections"""
        file_content = self._render_file_violations_table(violations)
        function_content = self._render_function_violations_table(violations)
        duplicates_content = self._render_duplicates_table(violations)
        offenders_content = self._render_worst_offenders_table(violations)
        
        return f"""
                <div id="file-size" class="tab-content active">{file_content}</div>
                <div id="function-complexity" class="tab-content">{function_content}</div>
                <div id="duplicates" class="tab-content">{duplicates_content}</div>
                <div id="worst-offenders" class="tab-content">{offenders_content}</div>"""
    
    def _render_recommendations_section(self, metrics: Dict[str, Any]) -> str:
        """Generate recommendations section"""
        return f"""
            <div class="recommendations">
                <h3> TARGET:  Recommended Actions</h3>
                <ul>{self._render_recommendations_list(metrics)}</ul>
            </div>"""
    
    def _render_recommendations_list(self, metrics: Dict[str, Any]) -> str:
        """Render recommendations list items"""
        suggestions = metrics.get('improvement_suggestions', [])
        return "".join([f"<li>{suggestion}</li>" for suggestion in suggestions])
    
    def _combine_dashboard_sections(self, header: str, metrics: str, charts: str, 
                                  violations: str, recommendations: str, footer: str, 
                                  javascript: str) -> str:
        """Combine all dashboard sections"""
        return header + metrics + charts + violations + recommendations + footer + javascript + """
</body>
</html>"""
    
    def _generate_javascript(self, js_data: Dict[str, Any]) -> str:
        """Generate JavaScript for charts and interactions"""
        return f"""
    <script>
        const data = {json.dumps(js_data, default=str)};
        {self._generate_chart_scripts()}
        {self._generate_interaction_scripts()}
    </script>"""
    
    def _generate_chart_scripts(self) -> str:
        """Generate chart creation scripts"""
        return (self._generate_violation_chart() + 
                self._generate_severity_chart() + 
                self._generate_compliance_chart())
    
    def _generate_violation_chart(self) -> str:
        """Generate violation distribution chart"""
        return """
        const violationCtx = document.getElementById('violationChart').getContext('2d');
        new Chart(violationCtx, {
            type: 'doughnut',
            data: {
                labels: ['File Size', 'Function Complexity', 'Duplicate Types', 'Test Stubs', 'Missing Types', 'Arch Debt', 'Quality Issues'],
                datasets: [{
                    data: [
                        data.metrics.violation_counts.file_size_violations,
                        data.metrics.violation_counts.function_complexity_violations,
                        data.metrics.violation_counts.duplicate_types,
                        data.metrics.violation_counts.test_stubs,
                        data.metrics.violation_counts.missing_type_annotations,
                        data.metrics.violation_counts.architectural_debt,
                        data.metrics.violation_counts.code_quality_issues
                    ],
                    backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#6f42c1', '#6c757d', '#e83e8c']
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: 'Violation Distribution' } } }
        });"""
    
    def _generate_severity_chart(self) -> str:
        """Generate severity breakdown chart"""
        return """
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        new Chart(severityCtx, {
            type: 'bar',
            data: {
                labels: ['Critical', 'High', 'Medium'],
                datasets: [{
                    label: 'Violations by Severity',
                    data: [data.metrics.severity_breakdown.critical, data.metrics.severity_breakdown.high, data.metrics.severity_breakdown.medium],
                    backgroundColor: ['#dc3545', '#fd7e14', '#ffc107']
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { title: { display: true, text: 'Severity Breakdown' } } }
        });"""
    
    def _generate_compliance_chart(self) -> str:
        """Generate compliance scores chart"""
        return """
        const complianceCtx = document.getElementById('complianceChart').getContext('2d');
        new Chart(complianceCtx, {
            type: 'bar',
            data: {
                labels: ['File Compliance', 'Function Compliance', 'Overall Compliance'],
                datasets: [{
                    label: 'Compliance Score (%)',
                    data: [data.metrics.compliance_scores.file_compliance, data.metrics.compliance_scores.function_compliance, data.metrics.compliance_scores.overall_compliance],
                    backgroundColor: ['#28a745', '#17a2b8', '#007bff']
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } }, plugins: { title: { display: true, text: 'Compliance Scores' } } }
        });"""
    
    def _generate_interaction_scripts(self) -> str:
        """Generate tab interaction scripts"""
        return """
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(content => { content.classList.remove('active'); });
            document.querySelectorAll('.tab').forEach(tab => { tab.classList.remove('active'); });
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }"""
    
    def _render_file_violations_table(self, violations: Dict[str, Any]) -> str:
        """Render file size violations table"""
        return DashboardTableRenderers.render_file_violations_table(violations)
    
    def _render_function_violations_table(self, violations: Dict[str, Any]) -> str:
        """Render function complexity violations table"""
        return DashboardTableRenderers.render_function_violations_table(violations)
    
    def _render_duplicates_table(self, violations: Dict[str, Any]) -> str:
        """Render duplicate types table"""
        return DashboardTableRenderers.render_duplicates_table(violations)
    
    def _render_worst_offenders_table(self, violations: Dict[str, Any]) -> str:
        """Render worst offenders table"""
        return DashboardTableRenderers.render_worst_offenders_table(violations)