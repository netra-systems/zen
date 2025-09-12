"""
Cypress Results Processor.

Processes Cypress test execution results and converts them to the 
unified test runner format for consistent reporting and integration.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class CypressTestResult:
    """Individual Cypress test result."""
    
    title: str
    full_title: str
    state: str  # 'passed', 'failed', 'pending', 'skipped'
    duration: float  # milliseconds
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    spec_file: Optional[str] = None
    
    @property
    def passed(self) -> bool:
        return self.state == 'passed'
        
    @property
    def failed(self) -> bool:
        return self.state == 'failed'


@dataclass
class CypressSpecResult:
    """Results for a single spec file."""
    
    name: str
    relative_path: str
    absolute_path: str
    tests: List[CypressTestResult]
    stats: Dict[str, int]
    duration: float  # milliseconds
    
    @property
    def passed(self) -> bool:
        return self.stats.get('failures', 0) == 0
        
    @property
    def test_count(self) -> int:
        return len(self.tests)


@dataclass
class CypressRunResults:
    """Complete Cypress run results."""
    
    total_tests: int
    total_passed: int
    total_failed: int
    total_pending: int
    total_skipped: int
    total_duration: float  # milliseconds
    specs: List[CypressSpecResult]
    browser: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def success(self) -> bool:
        return self.total_failed == 0
        
    @property
    def total_duration_seconds(self) -> float:
        return self.total_duration / 1000.0


class CypressResults:
    """
    Processes and aggregates Cypress test execution results.
    
    Converts Cypress-specific output to unified test runner format
    for consistent reporting across all test categories.
    """
    
    def __init__(self):
        """Initialize results processor."""
        self.logger = logging.getLogger(__name__)
        
    def process_results(self, 
                       return_code: int,
                       stdout: str,
                       stderr: str,
                       execution_time: float,
                       options: Any) -> Dict[str, Any]:
        """
        Process Cypress execution results.
        
        Args:
            return_code: Process exit code
            stdout: Standard output from Cypress
            stderr: Standard error from Cypress  
            execution_time: Total execution time in seconds
            options: CypressExecutionOptions used for the run
            
        Returns:
            Processed results in unified format
        """
        logger.info("Processing Cypress test results...")
        
        # Try to parse JSON output from Cypress
        cypress_results = self._parse_cypress_json_output(stdout)
        
        if cypress_results:
            # Convert to unified format
            unified_results = self._convert_to_unified_format(cypress_results, execution_time, options)
        else:
            # Fallback parsing from text output
            unified_results = self._parse_text_output(stdout, stderr, return_code, execution_time, options)
            
        # Add execution metadata
        unified_results.update({
            "execution_time_seconds": execution_time,
            "return_code": return_code,
            "timestamp": datetime.now().isoformat(),
            "runner": "cypress"
        })
        
        return unified_results
        
    def _parse_cypress_json_output(self, stdout: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON output from Cypress.
        
        Args:
            stdout: Standard output containing JSON
            
        Returns:
            Parsed JSON data or None if parsing failed
        """
        try:
            # Look for JSON output in stdout
            lines = stdout.split('\n')
            json_line = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('{') and '"stats"' in line:
                    json_line = line
                    break
                    
            if json_line:
                return json.loads(json_line)
                
        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse Cypress JSON output: {e}")
            
        return None
        
    def _convert_to_unified_format(self, 
                                 cypress_data: Dict[str, Any],
                                 execution_time: float,
                                 options: Any) -> Dict[str, Any]:
        """
        Convert Cypress JSON results to unified format.
        
        Args:
            cypress_data: Raw Cypress results data
            execution_time: Execution time in seconds
            options: Execution options
            
        Returns:
            Results in unified format
        """
        stats = cypress_data.get('stats', {})
        runs = cypress_data.get('runs', [])
        
        # Process individual spec results
        spec_results = []
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        
        for run in runs:
            spec_result = self._process_spec_run(run)
            spec_results.append(spec_result)
            
            total_tests += spec_result['test_count']
            total_passed += spec_result['passed']
            total_failed += spec_result['failed']
            total_skipped += spec_result['skipped']
            
        success = total_failed == 0
        
        return {
            "success": success,
            "category": "cypress",
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "error_count": total_failed,
            "warning_count": 0,
            "execution_time_seconds": execution_time,
            "specs": spec_results,
            "summary": {
                "total": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0
            }
        }
        
    def _process_spec_run(self, run_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process results for a single spec file.
        
        Args:
            run_data: Cypress run data for a spec
            
        Returns:
            Processed spec results
        """
        spec = run_data.get('spec', {})
        stats = run_data.get('stats', {})
        tests = run_data.get('tests', [])
        
        spec_name = spec.get('name', 'unknown')
        relative_path = spec.get('relative', spec_name)
        
        # Process individual test results
        test_results = []
        for test in tests:
            test_result = self._process_test_result(test)
            test_results.append(test_result)
            
        return {
            "spec_name": spec_name,
            "relative_path": relative_path,
            "test_count": len(tests),
            "passed": stats.get('passes', 0),
            "failed": stats.get('failures', 0),
            "skipped": stats.get('skipped', 0),
            "duration_ms": stats.get('duration', 0),
            "tests": test_results
        }
        
    def _process_test_result(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process individual test result.
        
        Args:
            test_data: Cypress test data
            
        Returns:
            Processed test result
        """
        title = test_data.get('title', ['unknown'])
        full_title = ' > '.join(title) if isinstance(title, list) else str(title)
        state = test_data.get('state', 'unknown')
        duration = test_data.get('duration', 0)
        
        # Extract error information if present
        error_message = None
        stack_trace = None
        
        if state == 'failed':
            err = test_data.get('err', {})
            error_message = err.get('message', 'Test failed')
            stack_trace = err.get('stack')
            
        return {
            "name": full_title,
            "status": state,
            "duration_ms": duration,
            "error": error_message,
            "stack_trace": stack_trace
        }
        
    def _parse_text_output(self,
                          stdout: str,
                          stderr: str,
                          return_code: int,
                          execution_time: float,
                          options: Any) -> Dict[str, Any]:
        """
        Fallback parsing from text output when JSON is not available.
        
        Args:
            stdout: Standard output text
            stderr: Standard error text
            return_code: Process return code
            execution_time: Execution time in seconds
            options: Execution options
            
        Returns:
            Parsed results in unified format
        """
        logger.info("Parsing Cypress text output (JSON not available)")
        
        # Extract basic statistics from text output
        total_tests = self._extract_number_from_text(stdout, r'(\d+) passing')
        total_failed = self._extract_number_from_text(stdout, r'(\d+) failing')
        total_pending = self._extract_number_from_text(stdout, r'(\d+) pending')
        
        # Calculate totals
        total_passed = total_tests or 0
        if total_failed:
            total_passed = max(0, total_passed - total_failed)
            
        success = return_code == 0 and (total_failed or 0) == 0
        
        # Extract error messages
        errors = []
        if stderr:
            errors.append(stderr)
            
        if not success and not errors:
            errors.append(f"Cypress tests failed with return code {return_code}")
            
        return {
            "success": success,
            "category": "cypress",
            "total_tests": (total_tests or 0) + (total_failed or 0) + (total_pending or 0),
            "passed": total_passed,
            "failed": total_failed or 0,
            "skipped": total_pending or 0,
            "error_count": total_failed or 0,
            "warning_count": 0,
            "execution_time_seconds": execution_time,
            "errors": errors,
            "raw_output": {
                "stdout": stdout[-2000:] if len(stdout) > 2000 else stdout,  # Last 2000 chars
                "stderr": stderr[-1000:] if len(stderr) > 1000 else stderr   # Last 1000 chars
            }
        }
        
    def _extract_number_from_text(self, text: str, pattern: str) -> Optional[int]:
        """
        Extract number from text using regex pattern.
        
        Args:
            text: Text to search
            pattern: Regex pattern with one capture group
            
        Returns:
            Extracted number or None
        """
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                pass
        return None
        
    def generate_summary_report(self, results: Dict[str, Any]) -> str:
        """
        Generate human-readable summary report.
        
        Args:
            results: Processed test results
            
        Returns:
            Summary report string
        """
        success = results.get('success', False)
        total = results.get('total_tests', 0)
        passed = results.get('passed', 0)
        failed = results.get('failed', 0)
        skipped = results.get('skipped', 0)
        duration = results.get('execution_time_seconds', 0)
        
        status_icon = " PASS: " if success else " FAIL: "
        
        report = [
            f"{status_icon} Cypress E2E Test Results",
            f"  Total: {total} tests",
            f"  Passed: {passed}",
            f"  Failed: {failed}",
            f"  Skipped: {skipped}",
            f"  Duration: {duration:.1f}s"
        ]
        
        if not success and results.get('errors'):
            report.append("  Errors:")
            for error in results['errors'][:3]:  # Show first 3 errors
                report.append(f"    - {error}")
                
        return '\n'.join(report)