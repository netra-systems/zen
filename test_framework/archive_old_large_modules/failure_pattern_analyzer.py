#!/usr/bin/env python
"""
Test Failure Pattern Analyzer - Intelligent analysis of test failures
Identifies patterns, root causes, and provides actionable recommendations
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import difflib
import hashlib
from enum import Enum

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class FailureCategory(Enum):
    """Categories of test failures"""
    IMPORT_ERROR = "import_error"
    ASSERTION_FAILURE = "assertion_failure"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    CONFIGURATION_ERROR = "configuration_error"
    MOCK_ERROR = "mock_error"
    DATABASE_ERROR = "database_error"
    PERMISSION_ERROR = "permission_error"
    TYPE_ERROR = "type_error"
    RESOURCE_ERROR = "resource_error"
    FLAKY = "flaky"
    REGRESSION = "regression"
    UNKNOWN = "unknown"

@dataclass
class FailurePattern:
    """Pattern identified in test failures"""
    pattern_id: str
    category: FailureCategory
    description: str
    occurrences: int = 0
    affected_tests: List[str] = field(default_factory=list)
    error_signatures: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    suggested_fix: Optional[str] = None
    confidence: float = 0.0  # 0-1 confidence in pattern identification
    
    def matches(self, error_text: str) -> bool:
        """Check if error text matches this pattern"""
        for signature in self.error_signatures:
            if re.search(signature, error_text, re.IGNORECASE):
                return True
        return False

@dataclass
class TestFailure:
    """Individual test failure instance"""
    test_name: str
    test_path: str
    error_type: str
    error_message: str
    stack_trace: str
    timestamp: datetime
    duration: float
    exit_code: int
    category: Optional[FailureCategory] = None
    pattern_id: Optional[str] = None
    
    def get_error_signature(self) -> str:
        """Generate a signature for this error"""
        # Remove specific values but keep structure
        cleaned = re.sub(r'\b\d+\b', 'N', self.error_message)
        cleaned = re.sub(r"'[^']+'", "'...'", cleaned)
        cleaned = re.sub(r'"[^"]+"', '"..."', cleaned)
        return hashlib.md5(cleaned.encode()).hexdigest()[:8]

class FailurePatternAnalyzer:
    """Analyzes test failures to identify patterns and root causes"""
    
    def __init__(self):
        self.patterns: Dict[str, FailurePattern] = {}
        self.failures: List[TestFailure] = []
        self.failure_history: Dict[str, List[TestFailure]] = defaultdict(list)
        
        # Initialize known patterns
        self._initialize_known_patterns()
        
        # Load historical data
        self.history_file = PROJECT_ROOT / "test_framework" / "failure_history.json"
        self.patterns_file = PROJECT_ROOT / "test_framework" / "failure_patterns.json"
        self._load_data()
    
    def _initialize_known_patterns(self):
        """Initialize with known failure patterns"""
        known_patterns = [
            FailurePattern(
                pattern_id="import_missing_module",
                category=FailureCategory.IMPORT_ERROR,
                description="Module not found during import",
                error_signatures=[
                    r"ModuleNotFoundError.*No module named",
                    r"ImportError.*cannot import name",
                    r"ImportError.*No module named"
                ],
                suggested_fix="Check dependencies in requirements.txt and ensure all imports are correct"
            ),
            FailurePattern(
                pattern_id="database_connection",
                category=FailureCategory.DATABASE_ERROR,
                description="Database connection failure",
                error_signatures=[
                    r"psycopg2.*could not connect",
                    r"sqlalchemy.*OperationalError",
                    r"Connection refused.*5432",
                    r"database.*does not exist"
                ],
                suggested_fix="Ensure database is running and connection string is correct"
            ),
            FailurePattern(
                pattern_id="redis_connection",
                category=FailureCategory.CONNECTION_ERROR,
                description="Redis connection failure",
                error_signatures=[
                    r"redis.*ConnectionError",
                    r"Connection refused.*6379",
                    r"Redis.*not available"
                ],
                suggested_fix="Ensure Redis is running or mocked for tests"
            ),
            FailurePattern(
                pattern_id="mock_assertion",
                category=FailureCategory.MOCK_ERROR,
                description="Mock assertion failure",
                error_signatures=[
                    r"Mock.*assert.*called",
                    r"Expected.*but.*called",
                    r"mock.*AssertionError"
                ],
                suggested_fix="Review mock setup and expected calls"
            ),
            FailurePattern(
                pattern_id="timeout_error",
                category=FailureCategory.TIMEOUT,
                description="Test timeout",
                error_signatures=[
                    r"TimeoutError",
                    r"timed? out after",
                    r"asyncio.*TimeoutError",
                    r"deadline.*exceeded"
                ],
                suggested_fix="Increase timeout or optimize test performance"
            ),
            FailurePattern(
                pattern_id="type_mismatch",
                category=FailureCategory.TYPE_ERROR,
                description="Type mismatch error",
                error_signatures=[
                    r"TypeError.*expected.*got",
                    r"TypeError.*takes.*positional",
                    r"TypeError.*missing.*required"
                ],
                suggested_fix="Check function signatures and type hints"
            ),
            FailurePattern(
                pattern_id="assertion_equality",
                category=FailureCategory.ASSERTION_FAILURE,
                description="Assertion equality failure",
                error_signatures=[
                    r"AssertionError.*==",
                    r"assert.*==.*False",
                    r"Expected.*to equal"
                ],
                suggested_fix="Review expected vs actual values in assertions"
            ),
            FailurePattern(
                pattern_id="fixture_not_found",
                category=FailureCategory.CONFIGURATION_ERROR,
                description="Pytest fixture not found",
                error_signatures=[
                    r"fixture.*not found",
                    r"fixture.*is not available",
                    r"fixture.*cannot be found"
                ],
                suggested_fix="Check fixture definitions and imports in conftest.py"
            ),
            FailurePattern(
                pattern_id="websocket_closed",
                category=FailureCategory.CONNECTION_ERROR,
                description="WebSocket connection closed",
                error_signatures=[
                    r"WebSocket.*closed",
                    r"WebSocket.*disconnected",
                    r"Connection.*closed.*unexpectedly"
                ],
                suggested_fix="Ensure WebSocket server is running and connection handling is correct"
            ),
            FailurePattern(
                pattern_id="permission_denied",
                category=FailureCategory.PERMISSION_ERROR,
                description="Permission denied error",
                error_signatures=[
                    r"PermissionError",
                    r"Permission denied",
                    r"Access.*denied",
                    r"Operation not permitted"
                ],
                suggested_fix="Check file/directory permissions and user privileges"
            )
        ]
        
        for pattern in known_patterns:
            self.patterns[pattern.pattern_id] = pattern
    
    def _load_data(self):
        """Load historical failure data and patterns"""
        # Load failure history
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                for failure_data in data:
                    failure = TestFailure(
                        test_name=failure_data["test_name"],
                        test_path=failure_data["test_path"],
                        error_type=failure_data["error_type"],
                        error_message=failure_data["error_message"],
                        stack_trace=failure_data.get("stack_trace", ""),
                        timestamp=datetime.fromisoformat(failure_data["timestamp"]),
                        duration=failure_data.get("duration", 0),
                        exit_code=failure_data.get("exit_code", 1),
                        category=FailureCategory(failure_data["category"]) if failure_data.get("category") else None,
                        pattern_id=failure_data.get("pattern_id")
                    )
                    self.failures.append(failure)
                    self.failure_history[failure.test_name].append(failure)
        
        # Load additional patterns
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r') as f:
                patterns_data = json.load(f)
                for pattern_id, pattern_data in patterns_data.items():
                    if pattern_id not in self.patterns:
                        pattern = FailurePattern(
                            pattern_id=pattern_id,
                            category=FailureCategory(pattern_data["category"]),
                            description=pattern_data["description"],
                            occurrences=pattern_data.get("occurrences", 0),
                            affected_tests=pattern_data.get("affected_tests", []),
                            error_signatures=pattern_data.get("error_signatures", []),
                            first_seen=datetime.fromisoformat(pattern_data["first_seen"]) if pattern_data.get("first_seen") else None,
                            last_seen=datetime.fromisoformat(pattern_data["last_seen"]) if pattern_data.get("last_seen") else None,
                            suggested_fix=pattern_data.get("suggested_fix"),
                            confidence=pattern_data.get("confidence", 0)
                        )
                        self.patterns[pattern_id] = pattern
    
    def analyze_failure(self, failure: TestFailure) -> Tuple[FailureCategory, Optional[str]]:
        """Analyze a single failure and categorize it"""
        error_text = f"{failure.error_type} {failure.error_message} {failure.stack_trace}"
        
        # Check against known patterns
        best_match = None
        best_confidence = 0.0
        
        for pattern in self.patterns.values():
            if pattern.matches(error_text):
                # Calculate confidence based on signature matches
                confidence = sum(1 for sig in pattern.error_signatures if re.search(sig, error_text, re.IGNORECASE))
                confidence = confidence / len(pattern.error_signatures) if pattern.error_signatures else 0
                
                if confidence > best_confidence:
                    best_match = pattern
                    best_confidence = confidence
        
        if best_match:
            # Update pattern statistics
            best_match.occurrences += 1
            if failure.test_name not in best_match.affected_tests:
                best_match.affected_tests.append(failure.test_name)
            best_match.last_seen = failure.timestamp
            if not best_match.first_seen:
                best_match.first_seen = failure.timestamp
            best_match.confidence = best_confidence
            
            failure.category = best_match.category
            failure.pattern_id = best_match.pattern_id
            
            return best_match.category, best_match.pattern_id
        
        # If no pattern matches, try to categorize based on error type
        category = self._categorize_by_error_type(failure.error_type, error_text)
        failure.category = category
        
        return category, None
    
    def _categorize_by_error_type(self, error_type: str, error_text: str) -> FailureCategory:
        """Categorize based on error type when no pattern matches"""
        error_type_lower = error_type.lower()
        
        if "import" in error_type_lower or "module" in error_type_lower:
            return FailureCategory.IMPORT_ERROR
        elif "assertion" in error_type_lower:
            return FailureCategory.ASSERTION_FAILURE
        elif "timeout" in error_type_lower:
            return FailureCategory.TIMEOUT
        elif "connection" in error_type_lower or "refused" in error_text.lower():
            return FailureCategory.CONNECTION_ERROR
        elif "permission" in error_type_lower or "denied" in error_text.lower():
            return FailureCategory.PERMISSION_ERROR
        elif "type" in error_type_lower:
            return FailureCategory.TYPE_ERROR
        elif "mock" in error_text.lower():
            return FailureCategory.MOCK_ERROR
        elif "database" in error_text.lower() or "sql" in error_text.lower():
            return FailureCategory.DATABASE_ERROR
        else:
            return FailureCategory.UNKNOWN
    
    def analyze_batch(self, failures: List[TestFailure]) -> Dict[str, Any]:
        """Analyze a batch of failures and identify patterns"""
        analysis = {
            "total_failures": len(failures),
            "categories": defaultdict(int),
            "patterns": defaultdict(list),
            "new_patterns": [],
            "flaky_tests": [],
            "consistent_failures": [],
            "regression_candidates": [],
            "recommendations": []
        }
        
        # Analyze each failure
        for failure in failures:
            category, pattern_id = self.analyze_failure(failure)
            analysis["categories"][category.value] += 1
            
            if pattern_id:
                analysis["patterns"][pattern_id].append(failure.test_name)
            
            # Track in history
            self.failures.append(failure)
            self.failure_history[failure.test_name].append(failure)
        
        # Identify flaky tests
        for test_name, history in self.failure_history.items():
            if len(history) >= 5:
                recent = history[-10:]
                success_count = sum(1 for f in recent if f.category != FailureCategory.ASSERTION_FAILURE)
                failure_count = len(recent) - success_count
                
                if 0.2 < failure_count / len(recent) < 0.8:
                    analysis["flaky_tests"].append({
                        "test": test_name,
                        "failure_rate": failure_count / len(recent),
                        "recent_failures": failure_count
                    })
        
        # Identify consistent failures
        for test_name, history in self.failure_history.items():
            if len(history) >= 3:
                recent = history[-3:]
                if all(f.category == recent[0].category for f in recent):
                    analysis["consistent_failures"].append({
                        "test": test_name,
                        "category": recent[0].category.value,
                        "consecutive_failures": len(recent)
                    })
        
        # Check for regression candidates (tests that recently started failing)
        one_week_ago = datetime.now() - timedelta(days=7)
        for test_name, history in self.failure_history.items():
            if history:
                old_failures = [f for f in history if f.timestamp < one_week_ago]
                recent_failures = [f for f in history if f.timestamp >= one_week_ago]
                
                if not old_failures and len(recent_failures) >= 2:
                    analysis["regression_candidates"].append({
                        "test": test_name,
                        "first_failure": recent_failures[0].timestamp.isoformat(),
                        "failure_count": len(recent_failures)
                    })
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        # Save updated data
        self._save_data()
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict) -> List[Dict[str, str]]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # Check for import errors
        if analysis["categories"].get(FailureCategory.IMPORT_ERROR.value, 0) > 3:
            recommendations.append({
                "priority": "HIGH",
                "issue": "Multiple import errors detected",
                "action": "Review requirements.txt and ensure all dependencies are installed",
                "affected_count": analysis["categories"][FailureCategory.IMPORT_ERROR.value]
            })
        
        # Check for database errors
        if analysis["categories"].get(FailureCategory.DATABASE_ERROR.value, 0) > 2:
            recommendations.append({
                "priority": "HIGH",
                "issue": "Database connection issues",
                "action": "Verify database is running and migrations are up to date",
                "affected_count": analysis["categories"][FailureCategory.DATABASE_ERROR.value]
            })
        
        # Check for flaky tests
        if len(analysis["flaky_tests"]) > 5:
            recommendations.append({
                "priority": "MEDIUM",
                "issue": f"{len(analysis['flaky_tests'])} flaky tests detected",
                "action": "Add retry logic or fix race conditions in flaky tests",
                "affected_tests": [t["test"] for t in analysis["flaky_tests"][:5]]
            })
        
        # Check for consistent failures
        critical_failures = [f for f in analysis["consistent_failures"] if f["consecutive_failures"] >= 5]
        if critical_failures:
            recommendations.append({
                "priority": "CRITICAL",
                "issue": f"{len(critical_failures)} tests consistently failing",
                "action": "Immediate attention required for consistently failing tests",
                "affected_tests": [f["test"] for f in critical_failures]
            })
        
        # Check for regressions
        if analysis["regression_candidates"]:
            recommendations.append({
                "priority": "HIGH",
                "issue": f"{len(analysis['regression_candidates'])} potential regressions detected",
                "action": "Review recent code changes that may have introduced failures",
                "affected_tests": [r["test"] for r in analysis["regression_candidates"]]
            })
        
        # Check for timeout issues
        if analysis["categories"].get(FailureCategory.TIMEOUT.value, 0) > 5:
            recommendations.append({
                "priority": "MEDIUM",
                "issue": "Multiple timeout errors",
                "action": "Consider increasing test timeouts or optimizing slow tests",
                "affected_count": analysis["categories"][FailureCategory.TIMEOUT.value]
            })
        
        # Sort by priority
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 99))
        
        return recommendations
    
    def identify_new_patterns(self, min_occurrences: int = 3) -> List[FailurePattern]:
        """Identify new patterns from recent failures"""
        new_patterns = []
        
        # Group failures by error signature
        signature_groups = defaultdict(list)
        for failure in self.failures[-100:]:  # Look at last 100 failures
            signature = failure.get_error_signature()
            signature_groups[signature].append(failure)
        
        # Check for new patterns
        for signature, failures in signature_groups.items():
            if len(failures) >= min_occurrences:
                # Check if this is already a known pattern
                is_known = False
                for pattern in self.patterns.values():
                    if any(f.pattern_id == pattern.pattern_id for f in failures if f.pattern_id):
                        is_known = True
                        break
                
                if not is_known:
                    # Create new pattern
                    pattern = FailurePattern(
                        pattern_id=f"auto_{signature}",
                        category=failures[0].category or FailureCategory.UNKNOWN,
                        description=f"Auto-detected pattern: {failures[0].error_type}",
                        occurrences=len(failures),
                        affected_tests=[f.test_name for f in failures],
                        error_signatures=[failures[0].error_message[:100]],
                        first_seen=min(f.timestamp for f in failures),
                        last_seen=max(f.timestamp for f in failures),
                        confidence=0.7
                    )
                    new_patterns.append(pattern)
                    self.patterns[pattern.pattern_id] = pattern
        
        return new_patterns
    
    def get_pattern_report(self) -> str:
        """Generate a report of all identified patterns"""
        report = []
        report.append("=" * 80)
        report.append("TEST FAILURE PATTERN ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Total Patterns: {len(self.patterns)}")
        report.append(f"Total Failures Analyzed: {len(self.failures)}")
        report.append("")
        
        # Sort patterns by occurrence
        sorted_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.occurrences,
            reverse=True
        )
        
        # Top patterns
        report.append("TOP FAILURE PATTERNS")
        report.append("-" * 40)
        
        for i, pattern in enumerate(sorted_patterns[:10], 1):
            report.append(f"\n{i}. {pattern.description}")
            report.append(f"   Category: {pattern.category.value}")
            report.append(f"   Occurrences: {pattern.occurrences}")
            report.append(f"   Affected Tests: {len(pattern.affected_tests)}")
            report.append(f"   Confidence: {pattern.confidence:.2%}")
            if pattern.suggested_fix:
                report.append(f"   Fix: {pattern.suggested_fix}")
        
        # Category summary
        report.append("\n" + "=" * 40)
        report.append("FAILURE CATEGORIES")
        report.append("-" * 40)
        
        category_counts = defaultdict(int)
        for failure in self.failures:
            if failure.category:
                category_counts[failure.category.value] += 1
        
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.failures) * 100) if self.failures else 0
            report.append(f"  {category:25} {count:5} ({percentage:.1f}%)")
        
        # Flaky tests
        flaky_tests = []
        for test_name, history in self.failure_history.items():
            if len(history) >= 5:
                categories = set(f.category for f in history[-5:] if f.category)
                if len(categories) > 1:
                    flaky_tests.append(test_name)
        
        if flaky_tests:
            report.append("\n" + "=" * 40)
            report.append("FLAKY TESTS")
            report.append("-" * 40)
            for test in flaky_tests[:10]:
                report.append(f"  - {test}")
        
        return "\n".join(report)
    
    def _save_data(self):
        """Save failure history and patterns"""
        # Ensure directory exists
        self.history_file.parent.mkdir(exist_ok=True)
        
        # Save failure history (keep last 1000)
        history_data = []
        for failure in self.failures[-1000:]:
            history_data.append({
                "test_name": failure.test_name,
                "test_path": failure.test_path,
                "error_type": failure.error_type,
                "error_message": failure.error_message,
                "stack_trace": failure.stack_trace,
                "timestamp": failure.timestamp.isoformat(),
                "duration": failure.duration,
                "exit_code": failure.exit_code,
                "category": failure.category.value if failure.category else None,
                "pattern_id": failure.pattern_id
            })
        
        with open(self.history_file, 'w') as f:
            json.dump(history_data, f, indent=2)
        
        # Save patterns
        patterns_data = {}
        for pattern_id, pattern in self.patterns.items():
            patterns_data[pattern_id] = {
                "category": pattern.category.value,
                "description": pattern.description,
                "occurrences": pattern.occurrences,
                "affected_tests": pattern.affected_tests[-50:],  # Keep last 50
                "error_signatures": pattern.error_signatures,
                "first_seen": pattern.first_seen.isoformat() if pattern.first_seen else None,
                "last_seen": pattern.last_seen.isoformat() if pattern.last_seen else None,
                "suggested_fix": pattern.suggested_fix,
                "confidence": pattern.confidence
            }
        
        with open(self.patterns_file, 'w') as f:
            json.dump(patterns_data, f, indent=2)


def main():
    """Example usage of the Failure Pattern Analyzer"""
    analyzer = FailurePatternAnalyzer()
    
    # Example: Analyze some test failures
    example_failures = [
        TestFailure(
            test_name="test_database_connection",
            test_path="tests/test_db.py",
            error_type="OperationalError",
            error_message="could not connect to database",
            stack_trace="...",
            timestamp=datetime.now(),
            duration=0.5,
            exit_code=1
        ),
        TestFailure(
            test_name="test_import_module",
            test_path="tests/test_imports.py",
            error_type="ModuleNotFoundError",
            error_message="No module named 'missing_module'",
            stack_trace="...",
            timestamp=datetime.now(),
            duration=0.1,
            exit_code=1
        )
    ]
    
    # Analyze batch
    print("Analyzing test failures...")
    analysis = analyzer.analyze_batch(example_failures)
    
    print(f"\nAnalysis Results:")
    print(f"  Total Failures: {analysis['total_failures']}")
    print(f"  Categories: {dict(analysis['categories'])}")
    
    if analysis['recommendations']:
        print("\nRecommendations:")
        for rec in analysis['recommendations']:
            print(f"  [{rec['priority']}] {rec['issue']}")
            print(f"    Action: {rec['action']}")
    
    # Generate report
    print("\n" + analyzer.get_pattern_report())


if __name__ == "__main__":
    main()