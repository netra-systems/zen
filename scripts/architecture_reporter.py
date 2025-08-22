#!/usr/bin/env python3
"""
Architecture Reporter
Focused module for generating JSON reports and CLI output
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class ArchitectureReporter:
    """Generates comprehensive reports and CLI output"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
    
    def export_json_report(self, metrics: Dict[str, Any], violations: Dict[str, Any], 
                          trends: Dict[str, Any], scan_timestamp: datetime, 
                          output_path: str = None) -> str:
        """Export comprehensive JSON report"""
        if not output_path:
            timestamp = scan_timestamp.strftime("%Y%m%d_%H%M%S")
            output_path = str(self.root_path / "reports" / f"architecture_health_{timestamp}.json")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        report = self._build_json_report(metrics, violations, trends, scan_timestamp)
        
        self._write_json_report(output_path, report)
        print(f"JSON Report exported: {output_path}")
        return output_path
    
    def _build_json_report(self, metrics: Dict[str, Any], violations: Dict[str, Any], 
                          trends: Dict[str, Any], scan_timestamp: datetime) -> Dict[str, Any]:
        """Build complete JSON report structure"""
        return {
            'metadata': self._get_report_metadata(scan_timestamp),
            'metrics': metrics,
            'violations': violations,
            'trends': trends
        }
    
    def _get_report_metadata(self, scan_timestamp: datetime) -> Dict[str, Any]:
        """Get report metadata"""
        return {
            'scan_timestamp': scan_timestamp.isoformat(),
            'root_path': str(self.root_path),
            'tool_version': '1.0.0'
        }
    
    def _write_json_report(self, output_path: str, report: Dict[str, Any]) -> None:
        """Write JSON report to file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
    
    def print_cli_summary(self, metrics: Dict[str, Any], violations: Dict[str, Any]) -> None:
        """Print comprehensive summary to CLI"""
        self._print_header()
        self._print_health_score(metrics)
        self._print_quick_stats(metrics)
        self._print_violation_breakdown(metrics)
        self._print_worst_offenders(violations)
        self._print_recommended_actions(metrics)
        self._print_footer()
    
    def _print_header(self) -> None:
        """Print CLI header"""
        print("\n" + "="*80)
        print("ARCHITECTURE HEALTH DASHBOARD")
        print("="*80)
    
    def _print_health_score(self, metrics: Dict[str, Any]) -> None:
        """Print overall health score"""
        compliance = metrics['compliance_scores']['overall_compliance']
        health_status = self._get_health_status(compliance)
        print(f"\nOVERALL HEALTH SCORE: {compliance}% ({health_status})")
    
    def _get_health_status(self, compliance: float) -> str:
        """Get health status based on compliance score"""
        if compliance >= 90:
            return "EXCELLENT"
        elif compliance >= 70:
            return "GOOD"
        else:
            return "NEEDS IMPROVEMENT"
    
    def _print_quick_stats(self, metrics: Dict[str, Any]) -> None:
        """Print quick statistics"""
        total_violations = metrics['violation_counts']['total_violations']
        print(f"Total Violations: {total_violations}")
        print(f"Files Scanned: {metrics['total_files_scanned']}")
        print(f"Functions Scanned: {metrics['total_functions_scanned']}")
    
    def _print_violation_breakdown(self, metrics: Dict[str, Any]) -> None:
        """Print detailed violation breakdown"""
        print(f"\nVIOLATION BREAKDOWN:")
        counts = metrics['violation_counts']
        
        breakdown_items = [
            ("File Size (>300 lines)", counts['file_size_violations']),
            ("Function Complexity (>8 lines)", counts['function_complexity_violations']),
            ("Duplicate Types", counts['duplicate_types']),
            ("Test Stubs", counts['test_stubs']),
            ("Missing Type Annotations", counts['missing_type_annotations']),
            ("Architectural Debt", counts['architectural_debt']),
            ("Code Quality Issues", counts['code_quality_issues'])
        ]
        
        for description, count in breakdown_items:
            print(f"  {description}: {count}")
    
    def _print_worst_offenders(self, violations: Dict[str, Any]) -> None:
        """Print worst offending files"""
        print(f"\nWORST OFFENDERS:")
        worst_files = self._get_sorted_file_violations(violations)
        
        if worst_files:
            for i, violation in enumerate(worst_files, 1):
                print(f"  {i}. {violation['file']} ({violation['lines']} lines)")
        else:
            print("  No file size violations found!")
    
    def _get_sorted_file_violations(self, violations: Dict[str, Any]) -> list:
        """Get sorted file violations for display"""
        return sorted(
            violations.get('file_size_violations', [])[:5], 
            key=lambda x: x['lines'], 
            reverse=True
        )
    
    def _print_recommended_actions(self, metrics: Dict[str, Any]) -> None:
        """Print recommended actions"""
        print(f"\nRECOMMENDED ACTIONS:")
        for suggestion in metrics['improvement_suggestions'][:5]:
            print(f"  - {suggestion}")
    
    def _print_footer(self) -> None:
        """Print CLI footer"""
        print(f"\nFull dashboard: reports/architecture_dashboard.html")
        print("="*80)