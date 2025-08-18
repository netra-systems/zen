#!/usr/bin/env python
"""
SINGLE AUTHORITATIVE TEST REPORTER - All test results in ONE file.
No legacy reports, no confusion, just clarity.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict

from test_framework.reporter_base import ReporterConstants
from test_framework.reporter_updater import TestResultsUpdater


class ComprehensiveTestReporter:
    """Single source of truth for ALL test reporting."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)
        
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
        
        # Save the single file
        self._save_results()
    
    def _save_results(self):
        """Save the single test results file."""
        with open(self.results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
    
    def get_dashboard_data(self) -> Dict:
        """Get data for dashboard display."""
        return self.test_results
    
    def cleanup_old_reports(self, keep_days: int = 7):
        """Clean up old report files - NO LONGER NEEDED."""
        # This method is kept for backward compatibility but does nothing
        # All test results are now in a single test_results.json file
        pass