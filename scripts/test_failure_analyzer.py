#!/usr/bin/env python3
"""
Test Failure Analyzer - Diagnostic and Recommendation Tool

IMPORTANT: This tool DOES NOT automatically fix issues. It only:
1. Analyzes test failures to identify root causes
2. Suggests potential fixes and strategies  
3. Runs diagnostic commands to gather information
4. Generates detailed reports with recommendations

For actual fixes, a human or LLM agent must:
- Review the analysis and recommendations
- Implement the suggested changes manually
- Run tests to verify the fixes work

This is a diagnostic assistant, NOT an automated fixer.
"""

import json
import os
import sys
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFailureAnalyzer:
    """Analyzes test failures and provides diagnostic information and recommendations."""
    
    def __init__(self, test_name: str, failure_info: Dict, report_path: str):
        self.test_name = test_name
        self.failure_info = failure_info
        self.report_path = Path(report_path)
        self.fix_log = []
        
    def analyze(self) -> bool:
        """Main analysis process. Returns True if analysis completed successfully."""
        print(f"\n{'='*60}")
        print(f"Analyzing failure: {self.test_name}")
        print(f"{'='*60}")
        
        try:
            # Step 1: Analyze the failure
            analysis = self.analyze_failure()
            self.log(f"Analysis complete: {analysis['type']}")
            
            # Step 2: Determine fix strategy
            strategy = self.determine_fix_strategy(analysis)
            self.log(f"Fix strategy: {strategy['approach']}")
            
            # Step 3: Run diagnostic commands
            diagnostics_completed = self.run_diagnostics(strategy)
            
            if diagnostics_completed:
                self.log("[U+2713] Analysis complete - recommendations generated")
                self.update_report(success=True, analysis=analysis, strategy=strategy)
                return True
            else:
                self.log("[U+2717] Failed to complete diagnostics")
                self.update_report(success=False, analysis=analysis, strategy=strategy)
                return False
                
        except Exception as e:
            self.log(f"Error during analysis: {e}")
            self.update_report(success=False, error=str(e))
            return False
            
    def analyze_failure(self) -> Dict:
        """Analyze the test failure to understand the root cause."""
        error_details = self.failure_info.get('error_details', '')
        
        analysis = {
            'type': 'unknown',
            'details': {},
            'suggested_fixes': []
        }
        
        # Check for common failure patterns
        if 'connection refused' in error_details.lower():
            analysis['type'] = 'connection_error'
            analysis['details']['service'] = self._extract_service_from_error(error_details)
            analysis['suggested_fixes'] = [
                'Check service health',
                'Verify port configuration',
                'Ensure service is running'
            ]
            
        elif 'import error' in error_details.lower() or 'modulenotfounderror' in error_details.lower():
            analysis['type'] = 'import_error'
            analysis['details']['module'] = self._extract_module_from_error(error_details)
            analysis['suggested_fixes'] = [
                'Install missing dependencies',
                'Fix import paths',
                'Update PYTHONPATH'
            ]
            
        elif 'assertion' in error_details.lower():
            analysis['type'] = 'assertion_error'
            analysis['details']['assertion'] = self._extract_assertion_from_error(error_details)
            analysis['suggested_fixes'] = [
                'Fix test logic',
                'Update expected values',
                'Fix implementation bug'
            ]
            
        elif 'timeout' in error_details.lower():
            analysis['type'] = 'timeout_error'
            analysis['suggested_fixes'] = [
                'Increase timeout values',
                'Optimize slow operations',
                'Check for deadlocks'
            ]
            
        elif 'database' in error_details.lower() or 'postgres' in error_details.lower():
            analysis['type'] = 'database_error'
            analysis['suggested_fixes'] = [
                'Check database connectivity',
                'Run migrations',
                'Fix database configuration'
            ]
            
        elif 'redis' in error_details.lower():
            analysis['type'] = 'redis_error'
            analysis['suggested_fixes'] = [
                'Check Redis connectivity',
                'Verify Redis configuration',
                'Clear Redis cache'
            ]
            
        elif 'llm' in error_details.lower() or 'api key' in error_details.lower():
            analysis['type'] = 'llm_error'
            analysis['suggested_fixes'] = [
                'Verify API keys',
                'Check LLM service availability',
                'Update mock configurations'
            ]
            
        return analysis
        
    def _extract_service_from_error(self, error: str) -> str:
        """Extract service name from connection error."""
        patterns = [
            r'connect to (\w+)',
            r'(\w+):\d+ refused',
            r'service[: ]+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error, re.IGNORECASE)
            if match:
                return match.group(1)
                
        return 'unknown_service'
        
    def _extract_module_from_error(self, error: str) -> str:
        """Extract module name from import error."""
        patterns = [
            r"No module named '([^']+)'",
            r'cannot import name ([^\s]+)',
            r'ImportError: ([^\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error)
            if match:
                return match.group(1)
                
        return 'unknown_module'
        
    def _extract_assertion_from_error(self, error: str) -> str:
        """Extract assertion details from error."""
        patterns = [
            r'AssertionError: (.+)',
            r'assert (.+)',
            r'Expected (.+) but got (.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error)
            if match:
                return match.group(0)
                
        return 'assertion failed'
        
    def determine_fix_strategy(self, analysis: Dict) -> Dict:
        """Determine the best fix strategy based on analysis."""
        strategy = {
            'approach': 'unknown',
            'actions': [],
            'files_to_modify': [],
            'commands': []
        }
        
        if analysis['type'] == 'connection_error':
            service = analysis['details'].get('service', 'unknown')
            strategy['approach'] = f'fix_service_connection_{service}'
            strategy['actions'] = [
                f'Check if {service} service is running',
                'Verify port configuration',
                'Update connection settings'
            ]
            strategy['commands'] = [
                'docker ps',
                f'docker logs netra-test-{service}',
                'netstat -an | findstr LISTENING'
            ]
            
        elif analysis['type'] == 'import_error':
            module = analysis['details'].get('module', 'unknown')
            strategy['approach'] = f'fix_import_{module}'
            strategy['actions'] = [
                f'Install {module} if missing',
                'Fix import statements',
                'Update requirements.txt'
            ]
            strategy['commands'] = [
                f'pip install {module}',
                'pip freeze | findstr {module}'
            ]
            
        elif analysis['type'] == 'assertion_error':
            strategy['approach'] = 'fix_test_assertion'
            strategy['actions'] = [
                'Analyze expected vs actual values',
                'Update test expectations or fix implementation'
            ]
            # Identify test file
            test_file = self._find_test_file()
            if test_file:
                strategy['files_to_modify'].append(test_file)
                
        elif analysis['type'] == 'timeout_error':
            strategy['approach'] = 'fix_timeout'
            strategy['actions'] = [
                'Increase timeout values in test configuration',
                'Optimize slow operations'
            ]
            
        elif analysis['type'] == 'database_error':
            strategy['approach'] = 'fix_database'
            strategy['actions'] = [
                'Check database connectivity',
                'Run pending migrations',
                'Reset test database if needed'
            ]
            strategy['commands'] = [
                'docker exec netra-test-backend alembic upgrade head',
                'docker logs netra-test-postgres'
            ]
            
        elif analysis['type'] == 'redis_error':
            strategy['approach'] = 'fix_redis'
            strategy['actions'] = [
                'Check Redis connectivity',
                'Clear Redis cache',
                'Restart Redis service'
            ]
            strategy['commands'] = [
                'docker restart netra-test-redis',
                'docker exec netra-test-redis redis-cli FLUSHALL'
            ]
            
        elif analysis['type'] == 'llm_error':
            strategy['approach'] = 'fix_llm_config'
            strategy['actions'] = [
                'Verify API keys in test environment',
                'Update mock configurations',
                'Check LLM service availability'
            ]
            
        return strategy
        
    def _find_test_file(self) -> Optional[Path]:
        """Find the test file from the test name."""
        # Extract file name from test name (e.g., test_file.py::TestClass::test_method)
        parts = self.test_name.split('::')
        if parts:
            test_file_name = parts[0]
            
            # Search for the file
            for root, dirs, files in os.walk('.'):
                if test_file_name in files:
                    return Path(root) / test_file_name
                    
        return None
        
    def run_diagnostics(self, strategy: Dict) -> bool:
        """Run diagnostic commands to gather information. Does NOT apply fixes."""
        self.log(f"Running diagnostics for strategy: {strategy['approach']}")
        
        success = True
        
        # Execute commands
        for cmd in strategy.get('commands', []):
            self.log(f"Executing: {cmd}")
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    self.log(f"Command failed: {result.stderr}")
                    success = False
                else:
                    self.log(f"Command output: {result.stdout[:200]}")
                    
            except subprocess.TimeoutExpired:
                self.log(f"Command timed out: {cmd}")
                success = False
            except Exception as e:
                self.log(f"Error executing command: {e}")
                success = False
                
        # Log files that would need modification (for human/LLM to implement)
        for file_path in strategy.get('files_to_modify', []):
            self.log(f"RECOMMENDATION: Modify file: {file_path}")
            self.log("  Actions needed:")
            for action in strategy.get('actions', []):
                self.log(f"    - {action}")
            
        return success
        
    def verify_current_state(self) -> bool:
        """Verify current test state (optional diagnostic step)."""
        self.log(f"Checking current test state: {self.test_name}")
        
        # Run just this specific test
        cmd = [
            "python", "unified_test_runner.py",
            "--category", "agent",
            "--real-llm",
            "--env", "test",
            "-k", self.test_name
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for single test
            )
            
            if result.returncode == 0:
                self.log("Test is currently passing")
                return True
            else:
                self.log("Test is currently failing")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Test verification timed out")
            return False
        except Exception as e:
            self.log(f"Error during verification: {e}")
            return False
            
    def log(self, message: str):
        """Log a message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.fix_log.append(log_entry)
        
    def update_report(self, success: bool, analysis: Dict = None, strategy: Dict = None, error: str = None):
        """Update the unified failure report."""
        # Read existing report
        report_content = ""
        if self.report_path.exists():
            with open(self.report_path, 'r') as f:
                report_content = f.read()
                
        # Find or create section for this test
        test_section = f"\n## Fix Report: {self.test_name}\n"
        test_section += f"Timestamp: {datetime.now().isoformat()}\n"
        test_section += f"Status: {'[U+2713] FIXED' if success else '[U+2717] FAILED'}\n\n"
        
        if analysis:
            test_section += f"### Analysis\n"
            test_section += f"- Type: {analysis['type']}\n"
            test_section += f"- Details: {json.dumps(analysis['details'], indent=2)}\n"
            test_section += f"- Suggested fixes: {', '.join(analysis['suggested_fixes'])}\n\n"
            
        if strategy:
            test_section += f"### Strategy\n"
            test_section += f"- Approach: {strategy['approach']}\n"
            test_section += f"- Actions taken:\n"
            for action in strategy['actions']:
                test_section += f"  - {action}\n"
                
        if error:
            test_section += f"### Error\n"
            test_section += f"```\n{error}\n```\n"
            
        test_section += f"\n### Fix Log\n"
        test_section += "```\n"
        test_section += '\n'.join(self.fix_log)
        test_section += "\n```\n"
        
        # Append to report
        with open(self.report_path, 'a') as f:
            f.write(test_section)
            
        print(f"Updated report: {self.report_path}")


def main():
    """Standalone entry point for testing."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_failure_analyzer.py <test_name>")
        sys.exit(1)
        
    test_name = sys.argv[1]
    
    # Mock failure info for testing
    failure_info = {
        'test_name': test_name,
        'error_details': 'Sample error for testing',
        'timestamp': datetime.now().isoformat()
    }
    
    analyzer = TestFailureAnalyzer(
        test_name=test_name,
        failure_info=failure_info,
        report_path="test_failure_report.md"
    )
    
    success = analyzer.analyze()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()