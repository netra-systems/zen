#!/usr/bin/env python
"""
SINGLE AUTHORITATIVE TEST REPORTER - All test results in ONE file.
No legacy reports, no confusion, just clarity.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict

from test_framework.reporter_base import ReporterConstants
from test_framework.reporter_updater import TestResultsUpdater
from test_framework.report_generators import generate_markdown_report


class ComprehensiveTestReporter:
    """Single source of truth for ALL test reporting."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)
        
        # Create history directory for archiving
        self.history_dir = reports_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
        
        # SINGLE authoritative results file
        self.results_file = reports_dir / "test_results.json"
        
        # Load constants
        self.TEST_LEVELS = ReporterConstants.TEST_LEVELS
        self.TEST_CATEGORIES = ReporterConstants.TEST_CATEGORIES
        
        # Load or initialize test results
        self.test_results = self._load_test_results()
        
        # Initialize updater
        self.updater = TestResultsUpdater()
    
    def _load_test_results(self) -> Dict:
        """Load the single test results file."""
        # Initialize with complete structure first
        default_structure = ReporterConstants.get_default_structure()
        
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r') as f:
                    loaded_data = json.load(f)
                    
                # Ensure loaded data has proper structure - merge with defaults
                if isinstance(loaded_data, dict):
                    # Merge existing data with default structure to ensure all keys exist
                    for key, value in default_structure.items():
                        if key not in loaded_data:
                            loaded_data[key] = value
                        elif isinstance(value, dict) and isinstance(loaded_data[key], dict):
                            # Merge nested dictionaries
                            for subkey, subvalue in value.items():
                                if subkey not in loaded_data[key]:
                                    loaded_data[key][subkey] = subvalue
                    return loaded_data
            except:
                pass
        
        return default_structure
    
    def generate_comprehensive_report(self, 
                                     level: str, 
                                     results: Dict,
                                     config: Dict,
                                     exit_code: int) -> None:
        """Generate and save the SINGLE comprehensive test report."""
        
        timestamp = datetime.now().isoformat()
        
        # Update metadata
        self.test_results["metadata"]["last_update"] = timestamp
        self.test_results["metadata"]["total_runs"] += 1
        
        # Update current state
        self.test_results["current_state"]["overall_status"] = self.updater.determine_status(results, exit_code)
        self.test_results["current_state"]["last_run_level"] = level
        self.test_results["current_state"]["last_run_time"] = timestamp
        self.test_results["current_state"]["last_exit_code"] = exit_code
        
        # Update known test counts (persistent)
        self.updater.update_known_counts(self.test_results, level, results)
        
        # Update category results
        self.updater.update_category_results(self.test_results, level, results, self.TEST_CATEGORIES)
        
        # Update component results
        self.updater.update_component_results(self.test_results, results)
        
        # Update failing tests
        self.updater.update_failing_tests(self.test_results, results)
        
        # Update statistics
        self.updater.update_statistics(self.test_results, results)
        
        # Add to history
        self.updater.add_to_history(self.test_results, level, exit_code, timestamp)
        
        # Handle agent performance data for agent-startup tests
        if level == "agent-startup" and hasattr(results, 'agent_performance'):
            from .agent_performance_reporter import update_agent_performance_data
            update_agent_performance_data(self.test_results, results['agent_performance'], timestamp)
        
        # Save the single file
        self._save_results()
        
        # Generate and save markdown report with history archiving
        self._generate_and_archive_markdown_report(level, results, config, exit_code)
    
    def _save_results(self):
        """Save the single test results file."""
        with open(self.results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
    
    def _generate_and_archive_markdown_report(self, level: str, results: Dict, config: Dict, exit_code: int):
        """Generate markdown report and archive previous report if it exists.
        
        Implements SPEC/testing.xml requirements:
        - Check if latest report exists before overwriting
        - If exists, move to history/ folder with timestamp
        - Create history folder if it doesn't exist
        - Write new latest report
        """
        # Define the latest report filename
        latest_report_file = self.reports_dir / f"latest_{level}_report.md"
        
        # Step 1: Archive existing report if it exists
        if latest_report_file.exists():
            self._archive_existing_report(latest_report_file, level)
        
        # Step 2: Generate new markdown report
        markdown_content = generate_markdown_report(results, level, config, exit_code)
        
        # Step 3: Write the new latest report
        with open(latest_report_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"[REPORT] Markdown report saved to: {latest_report_file}")
    
    def _archive_existing_report(self, report_file: Path, level: str):
        """Archive existing report to history folder with timestamp.
        
        Following SPEC naming: test_report_{level}_{timestamp}.md
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archived_filename = f"test_report_{level}_{timestamp}.md"
        archived_path = self.history_dir / archived_filename
        
        # Move existing report to history
        shutil.move(str(report_file), str(archived_path))
        print(f"[ARCHIVE] Previous report archived to: {archived_path}")
    
    def cleanup_archived_reports(self, keep_days: int = 30):
        """Clean up old archived reports older than specified days."""
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        purged_count = 0
        
        for report_file in self.history_dir.glob("test_report_*.md"):
            if report_file.stat().st_mtime < cutoff_time:
                report_file.unlink()
                purged_count += 1
        
        if purged_count > 0:
            print(f"[CLEANUP] Removed {purged_count} old archived reports")
    
    def get_dashboard_data(self) -> Dict:
        """Get data for dashboard display."""
        return self.test_results
    
    def cleanup_old_reports(self, keep_days: int = 7):
        """Clean up old report files - delegates to cleanup_archived_reports."""
        # Delegate to the new cleanup method
        self.cleanup_archived_reports(keep_days)