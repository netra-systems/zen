#!/usr/bin/env python3
"""
Test Execution Tracker - Maintains test execution history and metadata

This module provides comprehensive tracking of test executions including:
- Test run history with timestamps
- Failure tracking and analysis
- Category-based organization
- Performance metrics
- Smart test prioritization based on failure patterns
"""

import json
import os
import re
import sqlite3
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import hashlib
from shared.isolated_environment import IsolatedEnvironment


@dataclass
class TestRunRecord:
    """Record of a single test execution"""
    test_id: str  # Hash of file_path + test_name for unique ID
    file_path: str
    test_name: str
    category: str
    subcategory: str  # unit, integration, e2e, etc
    status: str  # passed, failed, skipped, error
    duration: float
    timestamp: str
    environment: str  # local, dev, staging, prod
    error_message: Optional[str] = None
    failure_type: Optional[str] = None  # assertion, timeout, setup_error, etc
    flaky: bool = False
    retry_count: int = 0
    coverage_impact: Optional[float] = None


@dataclass
class TestMetadata:
    """Persistent metadata about a test"""
    test_id: str
    file_path: str
    test_name: str
    categories: List[str]
    first_seen: str
    last_modified: str
    total_runs: int = 0
    total_failures: int = 0
    total_passes: int = 0
    total_skips: int = 0
    average_duration: float = 0.0
    failure_rate: float = 0.0
    last_run_timestamp: Optional[str] = None
    last_run_status: Optional[str] = None
    priority_score: float = 50.0  # 0-100, higher = run first
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    business_value: float = 50.0  # 0-100 business impact score
    
    
class TestExecutionTracker:
    """Tracks and manages test execution history"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.db_path = self.project_root / 'test_data' / 'test_execution.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Cache for current session
        self.current_session_id = None
        self.session_start_time = None
        self.tests_in_session: List[TestRunRecord] = []
        
        # Category definitions (fixed E2E issue from audit)
        self.category_definitions = {
            "unit": {
                "paths": ["tests/unit", "*/tests/unit", "*/test_*_unit.py"],
                "markers": ["pytest.mark.unit", "@unit"],
                "default": True  # Run by default
            },
            "integration": {
                "paths": ["tests/integration", "*/tests/integration"],
                "markers": ["pytest.mark.integration", "@integration"],
                "default": True  # Run by default
            },
            "e2e": {
                "paths": ["tests/e2e/integration"],  # Fixed: only actual e2e tests
                "markers": ["pytest.mark.e2e", "@e2e"],
                "default": False  # Don't run by default (expensive)
            },
            "e2e_critical": {
                "paths": ["tests/e2e/critical"],  # Curated critical e2e tests
                "markers": ["pytest.mark.e2e_critical"],
                "default": True  # Run critical e2e by default
            },
            "smoke": {
                "paths": ["tests/smoke", "*/tests/smoke"],
                "markers": ["pytest.mark.smoke"],
                "default": True  # Quick smoke tests run by default
            },
            "api": {
                "paths": ["*/test_api_*.py", "tests/api"],
                "markers": ["pytest.mark.api"],
                "default": True
            },
            "websocket": {
                "paths": ["*/test_*websocket*.py", "tests/websocket"],
                "markers": ["pytest.mark.websocket"],
                "default": False  # Requires special setup
            },
            "performance": {
                "paths": ["tests/performance", "*/test_*perf*.py"],
                "markers": ["pytest.mark.performance"],
                "default": False  # Expensive
            },
            "security": {
                "paths": ["tests/security", "*/test_*security*.py"],
                "markers": ["pytest.mark.security"],
                "default": False  # Special requirements
            }
        }
        
    def _init_database(self):
        """Initialize SQLite database for test tracking"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Test metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_metadata (
                    test_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    categories TEXT,  -- JSON array
                    first_seen TEXT,
                    last_modified TEXT,
                    total_runs INTEGER DEFAULT 0,
                    total_failures INTEGER DEFAULT 0,
                    total_passes INTEGER DEFAULT 0,
                    total_skips INTEGER DEFAULT 0,
                    average_duration REAL DEFAULT 0.0,
                    failure_rate REAL DEFAULT 0.0,
                    last_run_timestamp TEXT,
                    last_run_status TEXT,
                    priority_score REAL DEFAULT 50.0,
                    dependencies TEXT,  -- JSON array
                    tags TEXT,  -- JSON array
                    business_value REAL DEFAULT 50.0
                )
            ''')
            
            # Test run history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT NOT NULL,
                    session_id TEXT,
                    file_path TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    category TEXT,
                    subcategory TEXT,
                    status TEXT,
                    duration REAL,
                    timestamp TEXT,
                    environment TEXT,
                    error_message TEXT,
                    failure_type TEXT,
                    flaky BOOLEAN DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    coverage_impact REAL,
                    FOREIGN KEY (test_id) REFERENCES test_metadata(test_id)
                )
            ''')
            
            # Session tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    total_tests INTEGER,
                    passed INTEGER,
                    failed INTEGER,
                    skipped INTEGER,
                    environment TEXT,
                    categories_run TEXT,  -- JSON array
                    command_line TEXT,
                    metadata TEXT  -- JSON object for additional info
                )
            ''')
            
            # Create indices for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_runs_test_id ON test_runs(test_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_runs_timestamp ON test_runs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_runs_status ON test_runs(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_metadata_failure_rate ON test_metadata(failure_rate)')
            
            conn.commit()
    
    def start_session(self, environment: str = 'local', categories: List[str] = None) -> str:
        """Start a new test session"""
        self.current_session_id = f"session_{int(time.time())}_{os.getpid()}"
        self.session_start_time = datetime.now().isoformat()
        self.tests_in_session = []
        
        # Record session start
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO test_sessions (session_id, start_time, environment, categories_run)
                VALUES (?, ?, ?, ?)
            ''', (self.current_session_id, self.session_start_time, environment, 
                  json.dumps(categories or [])))
            conn.commit()
            
        return self.current_session_id
    
    def record_test_run(self, test_record: TestRunRecord) -> None:
        """Record a test execution"""
        if not self.current_session_id:
            self.start_session()
            
        # Generate test ID
        test_id = self._generate_test_id(test_record.file_path, test_record.test_name)
        test_record.test_id = test_id
        
        # Add to current session
        self.tests_in_session.append(test_record)
        
        # Update database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert run record
            cursor.execute('''
                INSERT INTO test_runs (
                    test_id, session_id, file_path, test_name, category, subcategory,
                    status, duration, timestamp, environment, error_message,
                    failure_type, flaky, retry_count, coverage_impact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_id, self.current_session_id, test_record.file_path,
                test_record.test_name, test_record.category, test_record.subcategory,
                test_record.status, test_record.duration, test_record.timestamp,
                test_record.environment, test_record.error_message,
                test_record.failure_type, test_record.flaky, test_record.retry_count,
                test_record.coverage_impact
            ))
            
            # Update or insert test metadata
            self._update_test_metadata(cursor, test_record)
            
            conn.commit()
    
    def _generate_test_id(self, file_path: str, test_name: str) -> str:
        """Generate unique test ID"""
        combined = f"{file_path}::{test_name}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _update_test_metadata(self, cursor, test_record: TestRunRecord):
        """Update test metadata based on new run"""
        # Check if metadata exists
        cursor.execute('SELECT * FROM test_metadata WHERE test_id = ?', (test_record.test_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing metadata
            cursor.execute('''
                UPDATE test_metadata SET
                    total_runs = total_runs + 1,
                    total_failures = total_failures + ?,
                    total_passes = total_passes + ?,
                    total_skips = total_skips + ?,
                    last_run_timestamp = ?,
                    last_run_status = ?,
                    average_duration = (average_duration * total_runs + ?) / (total_runs + 1),
                    failure_rate = CAST(total_failures + ? AS REAL) / (total_runs + 1)
                WHERE test_id = ?
            ''', (
                1 if test_record.status == 'failed' else 0,
                1 if test_record.status == 'passed' else 0,
                1 if test_record.status == 'skipped' else 0,
                test_record.timestamp,
                test_record.status,
                test_record.duration,
                1 if test_record.status == 'failed' else 0,
                test_record.test_id
            ))
        else:
            # Insert new metadata
            categories = self._detect_categories(test_record.file_path, test_record.test_name)
            cursor.execute('''
                INSERT INTO test_metadata (
                    test_id, file_path, test_name, categories, first_seen,
                    last_modified, total_runs, total_failures, total_passes,
                    total_skips, average_duration, failure_rate,
                    last_run_timestamp, last_run_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_record.test_id, test_record.file_path, test_record.test_name,
                json.dumps(categories), test_record.timestamp, test_record.timestamp,
                1,
                1 if test_record.status == 'failed' else 0,
                1 if test_record.status == 'passed' else 0,
                1 if test_record.status == 'skipped' else 0,
                test_record.duration,
                1.0 if test_record.status == 'failed' else 0.0,
                test_record.timestamp, test_record.status
            ))
    
    def _detect_categories(self, file_path: str, test_name: str) -> List[str]:
        """Detect test categories based on path and name patterns"""
        categories = []
        file_path_lower = file_path.lower().replace('\\', '/')
        test_name_lower = test_name.lower()
        
        for category, config in self.category_definitions.items():
            # Check path patterns
            for pattern in config.get("paths", []):
                if "*" in pattern:
                    # Handle wildcards
                    pattern_regex = pattern.replace("*", ".*")
                    if re.search(pattern_regex, file_path_lower):
                        categories.append(category)
                        break
                elif pattern in file_path_lower:
                    categories.append(category)
                    break
                    
        # Default category if none detected
        if not categories:
            if 'test' in file_path_lower:
                categories.append('unit')  # Default assumption
                
        return categories
    
    def end_session(self, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """End current test session and return summary"""
        if not self.current_session_id:
            return {}
            
        end_time = datetime.now().isoformat()
        
        # Calculate session statistics
        total_tests = len(self.tests_in_session)
        passed = sum(1 for t in self.tests_in_session if t.status == 'passed')
        failed = sum(1 for t in self.tests_in_session if t.status == 'failed')
        skipped = sum(1 for t in self.tests_in_session if t.status == 'skipped')
        
        # Update session record
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE test_sessions SET
                    end_time = ?,
                    total_tests = ?,
                    passed = ?,
                    failed = ?,
                    skipped = ?,
                    metadata = ?
                WHERE session_id = ?
            ''', (end_time, total_tests, passed, failed, skipped,
                  json.dumps(metadata or {}), self.current_session_id))
            conn.commit()
        
        summary = {
            'session_id': self.current_session_id,
            'duration': (datetime.fromisoformat(end_time) - 
                        datetime.fromisoformat(self.session_start_time)).total_seconds(),
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'pass_rate': (passed / total_tests * 100) if total_tests > 0 else 0
        }
        
        # Reset session
        self.current_session_id = None
        self.session_start_time = None
        self.tests_in_session = []
        
        return summary
    
    def get_test_history(self, test_id: str = None, file_path: str = None,
                        test_name: str = None, days: int = 30) -> List[Dict]:
        """Get test execution history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if test_id:
                query = 'SELECT * FROM test_runs WHERE test_id = ?'
                params = (test_id,)
            elif file_path and test_name:
                test_id = self._generate_test_id(file_path, test_name)
                query = 'SELECT * FROM test_runs WHERE test_id = ?'
                params = (test_id,)
            elif file_path:
                query = 'SELECT * FROM test_runs WHERE file_path = ?'
                params = (file_path,)
            else:
                # Get recent history
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                query = 'SELECT * FROM test_runs WHERE timestamp > ? ORDER BY timestamp DESC'
                params = (cutoff,)
                
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_flaky_tests(self, threshold: float = 0.3, min_runs: int = 5) -> List[Dict]:
        """Identify flaky tests based on failure patterns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Find tests with inconsistent results
            cursor.execute('''
                SELECT 
                    test_id, file_path, test_name, total_runs,
                    failure_rate, average_duration
                FROM test_metadata
                WHERE total_runs >= ?
                    AND failure_rate > ? 
                    AND failure_rate < ?
                ORDER BY failure_rate DESC
            ''', (min_runs, threshold, 1.0 - threshold))
            
            columns = [desc[0] for desc in cursor.description]
            flaky_tests = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Add recent failure pattern analysis
            for test in flaky_tests:
                recent_runs = self.get_test_history(test_id=test['test_id'], days=7)
                if recent_runs:
                    # Check for alternating pass/fail pattern
                    statuses = [r['status'] for r in recent_runs[:10]]
                    alternating = sum(1 for i in range(len(statuses)-1) 
                                     if statuses[i] != statuses[i+1])
                    test['alternation_score'] = alternating / max(len(statuses)-1, 1)
                    test['recent_failure_rate'] = (sum(1 for s in statuses if s == 'failed') / 
                                                   len(statuses))
                    
            return flaky_tests
    
    def get_slowest_tests(self, category: str = None, limit: int = 20) -> List[Dict]:
        """Get slowest tests by average duration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if category:
                # Filter by category
                cursor.execute('''
                    SELECT test_id, file_path, test_name, 
                           average_duration, total_runs, categories
                    FROM test_metadata
                    WHERE categories LIKE ?
                    ORDER BY average_duration DESC
                    LIMIT ?
                ''', (f'%"{category}"%', limit))
            else:
                cursor.execute('''
                    SELECT test_id, file_path, test_name,
                           average_duration, total_runs, categories
                    FROM test_metadata
                    ORDER BY average_duration DESC
                    LIMIT ?
                ''', (limit,))
                
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_failure_trends(self, days: int = 30) -> Dict[str, Any]:
        """Analyze failure trends over time"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Daily failure rates
            cursor.execute('''
                SELECT 
                    DATE(timestamp) as day,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures,
                    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passes
                FROM test_runs
                WHERE timestamp > ?
                GROUP BY DATE(timestamp)
                ORDER BY day
            ''', (cutoff,))
            
            daily_stats = []
            for row in cursor.fetchall():
                daily_stats.append({
                    'date': row[0],
                    'total': row[1],
                    'failures': row[2],
                    'passes': row[3],
                    'failure_rate': (row[2] / row[1] * 100) if row[1] > 0 else 0
                })
            
            # Most frequently failing tests
            cursor.execute('''
                SELECT 
                    test_id, file_path, test_name,
                    COUNT(*) as failure_count
                FROM test_runs
                WHERE timestamp > ? AND status = 'failed'
                GROUP BY test_id
                ORDER BY failure_count DESC
                LIMIT 10
            ''', (cutoff,))
            
            columns = [desc[0] for desc in cursor.description]
            frequent_failures = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return {
                'daily_stats': daily_stats,
                'frequent_failures': frequent_failures
            }
    
    def get_category_summary(self) -> Dict[str, Dict]:
        """Get summary statistics for each test category"""
        summaries = {}
        
        for category in self.category_definitions.keys():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get tests in this category
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_tests,
                        AVG(failure_rate) as avg_failure_rate,
                        AVG(average_duration) as avg_duration,
                        SUM(total_runs) as total_runs,
                        AVG(business_value) as avg_business_value
                    FROM test_metadata
                    WHERE categories LIKE ?
                ''', (f'%"{category}"%',))
                
                row = cursor.fetchone()
                if row and row[0] > 0:
                    summaries[category] = {
                        'total_tests': row[0],
                        'avg_failure_rate': row[1] or 0,
                        'avg_duration': row[2] or 0,
                        'total_runs': row[3] or 0,
                        'avg_business_value': row[4] or 50,
                        'is_default': self.category_definitions[category].get('default', False)
                    }
                    
                    # Get recent performance
                    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
                    cursor.execute('''
                        SELECT 
                            COUNT(*) as recent_runs,
                            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as recent_failures
                        FROM test_runs
                        WHERE category = ? AND timestamp > ?
                    ''', (category, cutoff))
                    
                    recent = cursor.fetchone()
                    if recent and recent[0] > 0:
                        summaries[category]['recent_failure_rate'] = (recent[1] / recent[0] * 100)
                    else:
                        summaries[category]['recent_failure_rate'] = 0
                        
        return summaries
    
    def get_default_categories(self) -> List[str]:
        """Get list of categories that should run by default"""
        return [cat for cat, config in self.category_definitions.items() 
                if config.get('default', False)]
    
    def prioritize_tests(self, tests: List[str], strategy: str = 'smart') -> List[str]:
        """Prioritize test execution order based on strategy"""
        if strategy == 'smart':
            # Smart prioritization based on multiple factors
            test_scores = []
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for test_path in tests:
                    # Try to find test metadata
                    cursor.execute('''
                        SELECT failure_rate, average_duration, last_run_status,
                               business_value, last_modified
                        FROM test_metadata
                        WHERE file_path = ?
                    ''', (test_path,))
                    
                    row = cursor.fetchone()
                    if row:
                        # Calculate priority score
                        failure_rate, avg_duration, last_status, biz_value, last_mod = row
                        
                        score = 0
                        # Recently failed tests run first
                        if last_status == 'failed':
                            score += 100
                        # High failure rate tests run early
                        score += failure_rate * 50
                        # High business value tests prioritized
                        score += (biz_value or 50) * 0.5
                        # Faster tests run first (inverse duration)
                        if avg_duration and avg_duration > 0:
                            score += (1 / avg_duration) * 10
                            
                        test_scores.append((test_path, score))
                    else:
                        # Unknown tests get medium priority
                        test_scores.append((test_path, 50))
                        
            # Sort by score (higher first)
            test_scores.sort(key=lambda x: x[1], reverse=True)
            return [t[0] for t in test_scores]
            
        elif strategy == 'fast_first':
            # Run fastest tests first
            return self._sort_by_duration(tests, ascending=True)
            
        elif strategy == 'recent_failures':
            # Run recently failed tests first
            return self._sort_by_recent_failures(tests)
            
        else:
            # No prioritization
            return tests
    
    def _sort_by_duration(self, tests: List[str], ascending: bool = True) -> List[str]:
        """Sort tests by average duration"""
        test_durations = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for test_path in tests:
                cursor.execute('''
                    SELECT average_duration FROM test_metadata
                    WHERE file_path = ?
                ''', (test_path,))
                
                row = cursor.fetchone()
                duration = row[0] if row else float('inf')
                test_durations.append((test_path, duration))
                
        test_durations.sort(key=lambda x: x[1], reverse=not ascending)
        return [t[0] for t in test_durations]
    
    def _sort_by_recent_failures(self, tests: List[str]) -> List[str]:
        """Sort tests with recent failures first"""
        failed_tests = []
        passed_tests = []
        unknown_tests = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for test_path in tests:
                cursor.execute('''
                    SELECT last_run_status FROM test_metadata
                    WHERE file_path = ?
                ''', (test_path,))
                
                row = cursor.fetchone()
                if row:
                    if row[0] == 'failed':
                        failed_tests.append(test_path)
                    else:
                        passed_tests.append(test_path)
                else:
                    unknown_tests.append(test_path)
                    
        # Failed first, then unknown (might be new), then passed
        return failed_tests + unknown_tests + passed_tests
    
    def generate_report(self, output_format: str = 'text') -> str:
        """Generate test execution report"""
        category_summary = self.get_category_summary()
        failure_trends = self.get_failure_trends(days=7)
        flaky_tests = self.get_flaky_tests()
        slowest_tests = self.get_slowest_tests(limit=10)
        
        if output_format == 'json':
            return json.dumps({
                'category_summary': category_summary,
                'failure_trends': failure_trends,
                'flaky_tests': flaky_tests,
                'slowest_tests': slowest_tests,
                'generated_at': datetime.now().isoformat()
            }, indent=2, default=str)
            
        else:  # text format
            lines = []
            lines.append("="*80)
            lines.append("TEST EXECUTION REPORT")
            lines.append("="*80)
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
            
            # Category summary
            lines.append("CATEGORY SUMMARY:")
            lines.append("-"*40)
            for category, stats in category_summary.items():
                default_marker = " [DEFAULT]" if stats['is_default'] else ""
                lines.append(f"  {category.upper()}{default_marker}:")
                lines.append(f"    Tests: {stats['total_tests']}")
                lines.append(f"    Avg Failure Rate: {stats['avg_failure_rate']:.1f}%")
                lines.append(f"    Recent Failure Rate: {stats['recent_failure_rate']:.1f}%")
                lines.append(f"    Avg Duration: {stats['avg_duration']:.2f}s")
                lines.append("")
                
            # Failure trends
            if failure_trends['daily_stats']:
                lines.append("RECENT FAILURE TRENDS (7 days):")
                lines.append("-"*40)
                for stat in failure_trends['daily_stats'][-7:]:
                    lines.append(f"  {stat['date']}: "
                                f"{stat['failures']}/{stat['total']} failures "
                                f"({stat['failure_rate']:.1f}%)")
                lines.append("")
                
            # Flaky tests
            if flaky_tests:
                lines.append("FLAKY TESTS:")
                lines.append("-"*40)
                for test in flaky_tests[:5]:
                    lines.append(f"  {test['test_name'][:60]}")
                    lines.append(f"    Failure Rate: {test['failure_rate']:.1%}")
                    if 'alternation_score' in test:
                        lines.append(f"    Alternation: {test['alternation_score']:.1%}")
                lines.append("")
                
            # Slowest tests
            if slowest_tests:
                lines.append("SLOWEST TESTS:")
                lines.append("-"*40)
                for test in slowest_tests[:5]:
                    lines.append(f"  {test['test_name'][:60]}")
                    lines.append(f"    Avg Duration: {test['average_duration']:.2f}s")
                lines.append("")
                
            lines.append("="*80)
            return "\n".join(lines)


def main():
    """CLI for test tracker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Execution Tracker')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate test report')
    report_parser.add_argument('--format', choices=['text', 'json'], default='text')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show test history')
    history_parser.add_argument('--test', help='Test name or path')
    history_parser.add_argument('--days', type=int, default=30, help='Days of history')
    
    # Flaky command
    flaky_parser = subparsers.add_parser('flaky', help='Find flaky tests')
    flaky_parser.add_argument('--threshold', type=float, default=0.3)
    
    # Categories command
    cat_parser = subparsers.add_parser('categories', help='Show category summary')
    
    args = parser.parse_args()
    
    tracker = TestExecutionTracker(args.project_root)
    
    if args.command == 'report':
        print(tracker.generate_report(args.format))
    elif args.command == 'history':
        history = tracker.get_test_history(file_path=args.test, days=args.days)
        for run in history[:20]:
            print(f"{run['timestamp']}: {run['test_name']} - {run['status']} ({run['duration']:.2f}s)")
    elif args.command == 'flaky':
        flaky = tracker.get_flaky_tests(threshold=args.threshold)
        for test in flaky:
            print(f"{test['test_name']}: {test['failure_rate']:.1%} failure rate")
    elif args.command == 'categories':
        summary = tracker.get_category_summary()
        for cat, stats in summary.items():
            print(f"{cat}: {stats['total_tests']} tests, "
                  f"{stats['avg_failure_rate']:.1f}% failure rate")
    else:
        print(tracker.generate_report())


if __name__ == '__main__':
    main()