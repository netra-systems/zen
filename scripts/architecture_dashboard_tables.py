#!/usr/bin/env python3
"""
Architecture Dashboard Table Renderers
Table rendering functions for the architecture dashboard
"""

import os
from typing import Any, Dict, List


class DashboardTableRenderers:
    """Renders HTML tables for dashboard violations"""
    
    @staticmethod
    def render_file_violations_table(violations: Dict[str, Any]) -> str:
        """Render file size violations table"""
        file_violations = violations.get('file_size_violations', [])[:20]
        if not file_violations:
            return "<p> CELEBRATION:  No file size violations found! All files are under 300 lines.</p>"
        
        rows = DashboardTableRenderers._generate_file_violation_rows(file_violations)
        return DashboardTableRenderers._build_violations_table(['File', 'Lines', 'Excess Lines', 'Severity', 'Recommendation'], rows)
    
    @staticmethod
    def _generate_file_violation_rows(violations: list) -> str:
        """Generate table rows for file violations"""
        rows = ""
        for violation in violations:
            severity_class = f"severity-{violation['severity']}"
            rows += f"""
            <tr>
                <td>{os.path.basename(violation['file'])}</td>
                <td>{violation['lines']}</td>
                <td>{violation['excess_lines']}</td>
                <td class="{severity_class}">{violation['severity'].title()}</td>
                <td>{violation['recommendation']}</td>
            </tr>"""
        return rows
    
    @staticmethod
    def render_function_violations_table(violations: Dict[str, Any]) -> str:
        """Render function complexity violations table"""
        func_violations = violations.get('function_complexity_violations', [])[:20]
        if not func_violations:
            return "<p> CELEBRATION:  No function complexity violations found! All functions are under 8 lines.</p>"
        
        rows = DashboardTableRenderers._generate_function_violation_rows(func_violations)
        return DashboardTableRenderers._build_violations_table(['File', 'Function', 'Lines', 'Excess Lines', 'Severity', 'Recommendation'], rows)
    
    @staticmethod
    def _generate_function_violation_rows(violations: list) -> str:
        """Generate table rows for function violations"""
        rows = ""
        for violation in violations:
            severity_class = f"severity-{violation['severity']}"
            rows += f"""
            <tr>
                <td>{os.path.basename(violation['file'])}</td>
                <td>{violation['function']}</td>
                <td>{violation['lines']}</td>
                <td>{violation['excess_lines']}</td>
                <td class="{severity_class}">{violation['severity'].title()}</td>
                <td>{violation['recommendation']}</td>
            </tr>"""
        return rows
    
    @staticmethod
    def render_duplicates_table(violations: Dict[str, Any]) -> str:
        """Render duplicate types table"""
        duplicates = violations.get('duplicate_types', {})
        if not duplicates:
            return "<p> CELEBRATION:  No duplicate type definitions found!</p>"
        
        rows = DashboardTableRenderers._generate_duplicate_rows(duplicates)
        return DashboardTableRenderers._build_violations_table(['Type Name', 'Duplicates', 'Files', 'Severity', 'Recommendation'], rows)
    
    @staticmethod
    def _generate_duplicate_rows(duplicates: dict) -> str:
        """Generate table rows for duplicate types"""
        rows = ""
        for type_name, data in list(duplicates.items())[:20]:
            severity_class = f"severity-{data['severity']}"
            files_list = DashboardTableRenderers._format_files_list(data['definitions'])
            rows += f"""
            <tr>
                <td>{type_name}</td>
                <td>{data['count']}</td>
                <td>{files_list}</td>
                <td class="{severity_class}">{data['severity'].title()}</td>
                <td>{data['recommendation']}</td>
            </tr>"""
        return rows
    
    @staticmethod
    def _format_files_list(definitions: list) -> str:
        """Format files list for display"""
        files_list = ", ".join([os.path.basename(d['file']) for d in definitions[:3]])
        if len(definitions) > 3:
            files_list += f" (+{len(definitions)-3} more)"
        return files_list
    
    @staticmethod
    def render_worst_offenders_table(violations: Dict[str, Any]) -> str:
        """Render worst offenders table"""
        file_violations = violations.get('file_size_violations', [])[:10]
        if not file_violations:
            return "<p> CELEBRATION:  No major offenders found!</p>"
        
        rows = DashboardTableRenderers._generate_offender_rows(file_violations)
        return DashboardTableRenderers._build_violations_table(['File', 'Violation Type', 'Details', 'Severity'], rows)
    
    @staticmethod
    def _generate_offender_rows(violations: list) -> str:
        """Generate table rows for worst offenders"""
        rows = ""
        for violation in violations:
            severity_class = f"severity-{violation['severity']}"
            rows += f"""
            <tr>
                <td>{os.path.basename(violation['file'])}</td>
                <td>File Size</td>
                <td>{violation['lines']} lines</td>
                <td class="{severity_class}">{violation['severity'].title()}</td>
            </tr>"""
        return rows
    
    @staticmethod
    def _build_violations_table(headers: list, rows: str) -> str:
        """Build HTML table with headers and rows"""
        header_cells = "".join([f"<th>{header}</th>" for header in headers])
        return f"""
        <table class="violations-table">
            <thead><tr>{header_cells}</tr></thead>
            <tbody>{rows}</tbody>
        </table>"""