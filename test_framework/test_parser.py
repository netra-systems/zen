"""Test output parsing utilities."""

import re
from datetime import datetime
from typing import Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment


def parse_test_counts(output: str, component: str) -> Dict:
    """Parse test counts from pytest/jest output."""
    counts = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0, "import_errors": 0}
    
    # Check for import errors first
    if "ImportError" in output or "ModuleNotFoundError" in output:
        counts["import_errors"] = _count_import_errors(output)
        counts["status"] = "import_error"
    
    # Track test files
    test_files = set()
    
    # Count test files first
    if component == "backend":
        # Extract test files from pytest output
        file_pattern = r"(\S+\.py)::"
        test_files = set(re.findall(file_pattern, output))
        counts["test_files"] = len(test_files)
    elif component == "frontend":
        # Extract test files from Jest output
        file_pattern = r"(PASS|FAIL)\s+(\S+\.(test|spec)\.(ts|tsx|js|jsx))"
        for match in re.finditer(file_pattern, output):
            test_files.add(match.group(2))
        counts["test_files"] = len(test_files)
    
    # Improved pytest patterns with more precise regex
    patterns = [
        # Standard pytest result patterns - match exact format from pytest summary line
        (r"=+ (\d+) passed[,\s]", "passed"),
        (r"=+ (\d+) failed[,\s]", "failed"),
        (r"=+ (\d+) skipped[,\s]", "skipped"),
        (r"=+ (\d+) error[s]?[,\s]", "errors"),
        (r"=+ (\d+) deselected[,\s]", "skipped"),
        (r"=+ (\d+) xfailed[,\s]", "skipped"),
        (r"=+ (\d+) xpassed[,\s]", "passed"),
        # Alternative patterns for different pytest output formats
        (r", (\d+) passed", "passed"),
        (r", (\d+) failed", "failed"),
        (r", (\d+) skipped", "skipped"),
        (r", (\d+) error", "errors"),
        # Short form patterns
        (r"(\d+) passed", "passed"),
        (r"(\d+) failed", "failed"),
        (r"(\d+) skipped", "skipped"),
        (r"(\d+) error", "errors"),
    ]
    
    # Jest patterns for frontend
    if component == "frontend":
        patterns.extend([
            (r"Tests:\s+(\d+) passed", "passed"),
            (r"Tests:\s+(\d+) failed", "failed"),
            (r"Tests:\s+(\d+) skipped", "skipped"),
            (r"Tests:\s+(\d+) total", "total"),
            # Additional Jest patterns
            (r"Test Suites:\s+(\d+) passed", "suites_passed"),
            (r"Test Suites:\s+(\d+) failed", "suites_failed"),
            (r"Test Suites:\s+(\d+) total", "suites_total"),
        ])
        
        # Check for specific frontend test errors
        if "Cannot find module" in output:
            counts["import_errors"] = output.count("Cannot find module")
        if "Test suite failed to run" in output:
            counts["suite_errors"] = output.count("Test suite failed to run")
    
    for pattern, key in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if key == "total":
                counts["total"] = value
            else:
                counts[key] += value
    
    # Calculate total if not explicitly found
    if counts["total"] == 0:
        counts["total"] = counts["passed"] + counts["failed"] + counts["skipped"] + counts["errors"]
    
    # Set status if not already set
    if "status" not in counts:
        if counts["total"] == 0 and counts["import_errors"] == 0:
            # Check for collection errors
            if "no tests ran" in output.lower() or "collected 0 items" in output.lower():
                counts["status"] = "no_tests"
            else:
                counts["status"] = "unknown"
        elif counts["failed"] > 0 or counts["errors"] > 0:
            counts["status"] = "failed"
        elif counts["passed"] > 0:
            counts["status"] = "passed"
        else:
            counts["status"] = "skipped"
    
    return counts

def _count_import_errors(output: str) -> int:
    """Count import errors in output."""
    import_errors = 0
    lines = output.split('\n')
    for line in lines:
        if 'ImportError' in line or 'ModuleNotFoundError' in line:
            import_errors += 1
    # Count unique import error files
    import_files = set()
    for match in re.finditer(r'ImportError.*?["\']([^"\'\.]+)', output):
        import_files.add(match.group(1))
    return max(import_errors, len(import_files), 1)  # At least 1 if found

def parse_coverage(output: str) -> Optional[float]:
    """Parse coverage percentage from test output."""
    coverage_match = re.search(r"TOTAL\s+\d+\s+\d+\s+([\d.]+)%", output)
    if not coverage_match:
        coverage_match = re.search(r"Overall coverage:\s*([\d.]+)%", output)
    if not coverage_match:
        coverage_match = re.search(r"Statements\s*:\s*([\d.]+)%", output)
    
    if coverage_match:
        return float(coverage_match.group(1))
    return None

def parse_cypress_counts(output: str) -> Dict:
    """Parse test counts from Cypress output."""
    counts = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    
    # Cypress output patterns
    patterns = [
        (r"(\d+) passing", "passed"),
        (r"(\d+) failing", "failed"),
        (r"(\d+) pending", "skipped"),
        (r"Tests:\s+(\d+)", "total"),
        (r"Passing:\s+(\d+)", "passed"),
        (r"Failing:\s+(\d+)", "failed"),
        (r"Pending:\s+(\d+)", "skipped"),
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if key == "total":
                counts["total"] = value
            else:
                counts[key] = max(counts[key], value)  # Take the max to avoid double counting
    
    # Calculate total if not explicitly found
    if counts["total"] == 0:
        counts["total"] = counts["passed"] + counts["failed"] + counts["skipped"]
    
    return counts

def extract_failing_tests(output: str, component: str) -> List[Dict]:
    """Extract failing test details from test output."""
    failing_tests = []
    
    if component == "backend":
        # Parse pytest failures
        # Look for FAILED lines
        failure_pattern = r"FAILED\s+([^\s]+)::([^\s]+)(?:\[([^\]]+)\])?\s*-\s*(.+)"
        for match in re.finditer(failure_pattern, output):
            test_path = match.group(1)
            test_name = match.group(2)
            if match.group(3):  # Parametrized test
                test_name += f"[{match.group(3)}]"
            error_msg = match.group(4)
            
            failing_tests.append({
                "test_path": test_path,
                "test_name": test_name,
                "error_type": extract_error_type(error_msg),
                "error_message": error_msg[:500],  # Limit message length
                "traceback": extract_traceback(output, test_name)[:1000],
                "first_failed": datetime.now().isoformat(),
                "consecutive_failures": 1
            })
        
        # Also look for ERROR lines
        error_pattern = r"ERROR\s+([^\s]+)(?:::([^\s]+))?\s*-\s*(.+)"
        for match in re.finditer(error_pattern, output):
            test_path = match.group(1)
            test_name = match.group(2) or "setup/teardown"
            error_msg = match.group(3)
            
            failing_tests.append({
                "test_path": test_path,
                "test_name": test_name,
                "error_type": "Error",
                "error_message": error_msg[:500],
                "traceback": "",
                "first_failed": datetime.now().isoformat(),
                "consecutive_failures": 1
            })
            
    elif component == "frontend":
        # Parse Jest/Cypress failures
        # Look for FAIL lines in Jest
        fail_pattern = r"FAIL\s+([^\s]+)"
        for match in re.finditer(fail_pattern, output):
            test_path = match.group(1)
            
            # Extract test names from the output after the FAIL line
            test_section = output[match.end():match.end() + 2000]
            test_name_pattern = r"[U+2715]\s+(.+?)\s*\(\d+\s*ms\)"
            for test_match in re.finditer(test_name_pattern, test_section):
                test_name = test_match.group(1)
                
                failing_tests.append({
                    "test_path": test_path,
                    "test_name": test_name,
                    "error_type": "AssertionError",
                    "error_message": "Test failed",
                    "first_failed": datetime.now().isoformat(),
                    "consecutive_failures": 1
                })
        
        # Look for Cypress failures
        cypress_pattern = r"\d+\)\s+(.+?)\n\s+(.+?):"
        for match in re.finditer(cypress_pattern, output):
            if "failing" in output[max(0, match.start()-100):match.start()]:
                test_name = match.group(1)
                test_path = match.group(2)
                
                failing_tests.append({
                    "test_path": test_path,
                    "test_name": test_name,
                    "error_type": "CypressError",
                    "error_message": "Cypress test failed",
                    "first_failed": datetime.now().isoformat(),
                    "consecutive_failures": 1
                })
    
    return failing_tests

def extract_error_type(error_msg: str) -> str:
    """Extract error type from error message."""
    if "AssertionError" in error_msg:
        return "AssertionError"
    elif "ImportError" in error_msg or "ModuleNotFoundError" in error_msg:
        return "ImportError"
    elif "AttributeError" in error_msg:
        return "AttributeError"
    elif "TypeError" in error_msg:
        return "TypeError"
    elif "ValueError" in error_msg:
        return "ValueError"
    elif "KeyError" in error_msg:
        return "KeyError"
    elif "TimeoutError" in error_msg or "timeout" in error_msg.lower():
        return "TimeoutError"
    else:
        return "Error"

def extract_traceback(output: str, test_name: str) -> str:
    """Extract last few lines of traceback for a test."""
    # Find the test in output and get traceback
    test_pos = output.find(test_name)
    if test_pos == -1:
        return ""
    
    # Look for traceback after test name
    traceback_section = output[test_pos:min(test_pos + 3000, len(output))]
    
    # Get last 5 lines of traceback
    lines = traceback_section.split('\n')
    traceback_lines = []
    for line in lines:
        if line.strip().startswith('>') or 'assert' in line.lower() or '==' in line:
            traceback_lines.append(line)
        if len(traceback_lines) >= 5:
            break
    
    return '\n'.join(traceback_lines)

def extract_test_details(output: str, component: str) -> List[Dict]:
    """Extract individual test details with status from output."""
    test_details = []
    
    if component == "backend":
        # Parse pytest output for all tests
        # Pattern for passed tests
        passed_pattern = r"PASSED\s+([^\s]+)::([^\s]+)(?:\[([^\]]+)\])?"
        for match in re.finditer(passed_pattern, output):
            test_path = match.group(1)
            test_name = match.group(2)
            if match.group(3):  # Parametrized test
                test_name += f"[{match.group(3)}]"
            test_details.append({
                "name": f"{test_path}::{test_name}",
                "status": "passed",
                "error": None
            })
        
        # Pattern for failed tests
        failed_pattern = r"FAILED\s+([^\s]+)::([^\s]+)(?:\[([^\]]+)\])?\s*-\s*(.+)"
        for match in re.finditer(failed_pattern, output):
            test_path = match.group(1)
            test_name = match.group(2)
            if match.group(3):  # Parametrized test
                test_name += f"[{match.group(3)}]"
            error_msg = match.group(4)
            test_details.append({
                "name": f"{test_path}::{test_name}",
                "status": "failed",
                "error": error_msg[:200]
            })
        
        # Pattern for skipped tests
        skipped_pattern = r"SKIPPED\s+([^\s]+)::([^\s]+)(?:\[([^\]]+)\])?"
        for match in re.finditer(skipped_pattern, output):
            test_path = match.group(1)
            test_name = match.group(2)
            if match.group(3):  # Parametrized test
                test_name += f"[{match.group(3)}]"
            test_details.append({
                "name": f"{test_path}::{test_name}",
                "status": "skipped",
                "error": None
            })
            
    elif component == "frontend":
        # Parse Jest output
        # Pattern for passed tests
        passed_pattern = r"[U+2713]\s+(.+?)\s*\(\d+\s*ms\)"
        current_file = None
        
        # Track current test file being processed
        file_pattern = r"(PASS|FAIL)\s+(\S+\.(test|spec)\.(ts|tsx|js|jsx))"
        for match in re.finditer(file_pattern, output):
            current_file = match.group(2)
            # Get test section after file declaration
            file_pos = match.end()
            next_file = re.search(file_pattern, output[file_pos:])
            section_end = file_pos + next_file.start() if next_file else len(output)
            test_section = output[file_pos:section_end]
            
            # Extract passed tests in this file
            for test_match in re.finditer(r"[U+2713]\s+(.+?)\s*\(\d+\s*ms\)", test_section):
                test_name = test_match.group(1).strip()
                test_details.append({
                    "name": f"{current_file}::{test_name}",
                    "status": "passed",
                    "error": None
                })
            
            # Extract failed tests in this file
            for test_match in re.finditer(r"[U+2715]\s+(.+?)\s*\(\d+\s*ms\)", test_section):
                test_name = test_match.group(1).strip()
                test_details.append({
                    "name": f"{current_file}::{test_name}",
                    "status": "failed",
                    "error": "Test failed"
                })
    
    return test_details

def categorize_test(test_path: str, component: str = "backend") -> str:
    """Categorize test based on file path and name.
    
    CATEGORIZATION LOGIC:
    Tests are categorized to help understand what's being tested:
    - unit: Isolated component tests with mocked dependencies
    - integration: Tests that verify component interactions
    - service: Business logic layer tests
    - api/route: HTTP endpoint tests
    - database: Data access layer tests
    - agent: AI agent orchestration tests
    - websocket: Real-time communication tests
    - auth: Security and authentication tests
    - llm: Language model integration tests
    
    This helps identify test purposes and organize test execution.
    """
    path_lower = test_path.lower()
    
    if component == "backend":
        if "unit" in path_lower:
            return "unit"
        elif "integration" in path_lower:
            return "integration"
        elif "service" in path_lower:
            return "service"
        elif "route" in path_lower or "api" in path_lower:
            return "api"
        elif "database" in path_lower or "repository" in path_lower:
            return "database"
        elif "agent" in path_lower:
            return "agent"
        elif "websocket" in path_lower or "ws_" in path_lower:
            return "websocket"
        elif "auth" in path_lower or "security" in path_lower:
            return "auth"
        elif "llm" in path_lower:
            return "llm"
        else:
            return "other"
    else:  # frontend
        if "component" in path_lower:
            return "component"
        elif "hook" in path_lower:
            return "hook"
        elif "service" in path_lower or "api" in path_lower:
            return "service"
        elif "store" in path_lower:
            return "store"
        elif "auth" in path_lower:
            return "auth"
        elif "websocket" in path_lower or "ws" in path_lower:
            return "websocket"
        elif "util" in path_lower or "helper" in path_lower:
            return "utility"
        else:
            return "other"