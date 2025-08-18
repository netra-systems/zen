#!/usr/bin/env python
"""
Test Index Report - Generate comprehensive test index reports
"""

from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Optional

from test_framework.test_index_manager import TestIndexManager
from test_framework.reporter_base import ReporterConstants


class TestIndexReport:
    """Generate test index reports"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.index_manager = TestIndexManager()
        self.constants = ReporterConstants()
        
    def generate_markdown_report(self) -> str:
        """Generate a markdown test index report"""
        report = []
        report.append("# Test Index Report")
        report.append(f"\n*Generated: {datetime.now().isoformat()}*\n")
        
        # Add summary
        self._add_summary_section(report)
        
        # Add test levels
        self._add_test_levels_section(report)
        
        # Add categories
        self._add_categories_section(report)
        
        # Add catalog
        self._add_catalog_section(report)
        
        # Add statistics
        self._add_statistics_section(report)
        
        return "\n".join(report)
    
    def _add_summary_section(self, report: List[str]):
        """Add summary section"""
        stats = self.index_manager._calculate_statistics()
        report.append("## Summary")
        report.append(f"- **Total Test Modules**: {stats['total_modules']}")
        report.append(f"- **Backend Tests**: {stats['by_component'].get('backend', 0)}")
        report.append(f"- **Frontend Tests**: {stats['by_component'].get('frontend', 0)}")
        report.append(f"- **E2E Tests**: {stats['by_component'].get('e2e', 0)}")
        report.append("")
    
    def _add_test_levels_section(self, report: List[str]):
        """Add test levels section"""
        report.append("## Test Levels")
        report.append("")
        report.append("| Level | Time | Purpose | Command |")
        report.append("|-------|------|---------|---------|")
        
        levels = [
            ("integration", "3-5min", "**DEFAULT** - Feature validation", 
             "`python test_runner.py --level integration --no-coverage --fast-fail`"),
            ("unit", "1-2min", "Component testing", 
             "`python test_runner.py --level unit`"),
            ("smoke", "<30s", "Pre-commit validation", 
             "`python test_runner.py --level smoke`"),
            ("agents", "2-3min", "Agent testing", 
             "`python test_runner.py --level agents`"),
            ("critical", "1-2min", "Essential paths", 
             "`python test_runner.py --level critical`"),
            ("real_e2e", "15-20min", "Real LLM testing", 
             "`python test_runner.py --level real_e2e --real-llm`"),
            ("comprehensive", "30-45min", "Full validation", 
             "`python test_runner.py --level comprehensive`")
        ]
        
        for level, time, purpose, command in levels:
            report.append(f"| **{level}** | {time} | {purpose} | {command} |")
        
        report.append("")
    
    def _add_categories_section(self, report: List[str]):
        """Add categories section"""
        report.append("## Test Categories")
        report.append("")
        report.append("| Category | Description | Expected | Status |")
        report.append("|----------|-------------|----------|--------|")
        
        for category, info in self.constants.TEST_CATEGORIES.items():
            desc = info["description"]
            expected = info["expected"]
            report.append(f"| **{category}** | {desc} | {expected} | Pending |")
        
        report.append("")
    
    def _add_catalog_section(self, report: List[str]):
        """Add test catalog section"""
        report.append("## Test Catalog")
        report.append("")
        
        catalog = self.index_manager.test_catalog
        
        for component, categories in catalog.items():
            report.append(f"### {component.capitalize()} Tests")
            report.append("")
            
            for category, tests in categories.items():
                if tests:
                    report.append(f"#### {category.capitalize()}")
                    for test in tests:
                        report.append(f"- {test}")
                    report.append("")
    
    def _add_statistics_section(self, report: List[str]):
        """Add statistics section"""
        stats = self.index_manager._calculate_statistics()
        
        report.append("## Statistics")
        report.append("")
        report.append("### By Category")
        report.append("| Category | Count |")
        report.append("|----------|-------|")
        
        for category, count in stats["by_category"].items():
            report.append(f"| {category} | {count} |")
        
        report.append("")
        report.append("### By Component")
        report.append("| Component | Count |")
        report.append("|-----------|-------|")
        
        for component, count in stats["by_component"].items():
            report.append(f"| {component} | {count} |")
        
        report.append("")
    
    def save_report(self, output_path: Path):
        """Save the report to a file"""
        report = self.generate_markdown_report()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
    
    def generate_json_index(self) -> Dict:
        """Generate JSON test index"""
        return self.index_manager.get_test_index()