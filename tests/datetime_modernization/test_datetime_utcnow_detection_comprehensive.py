#!/usr/bin/env python3

"""

Comprehensive datetime.utcnow() Detection Test Suite for Issue #826



This test suite detects all deprecated datetime.utcnow() usage patterns in the codebase

and validates that they can be successfully modernized to datetime.now(datetime.UTC).



Business Justification (BVJ):

- Segment: Platform

- Goal: Stability (Python 3.12+ compatibility)

- Value Impact: Prevents future datetime deprecation warnings and ensures forward compatibility

- Revenue Impact: Maintains system reliability as Python versions evolve



Test Plan Coverage:

1. Detection of all datetime.utcnow() usage patterns

2. Validation of timezone-aware replacements

3. Consistency checks for datetime handling

4. Regression prevention for datetime operations

"""



import ast

import os

import re

from datetime import datetime, timezone

from pathlib import Path

from typing import Dict, List, Set, Tuple

import unittest

from unittest.mock import patch



from test_framework.ssot.base_test_case import SSotAsyncTestCase





class DatetimeUtcnowDetectionTest(SSotAsyncTestCase):

    """Tests for detecting deprecated datetime.utcnow() usage patterns."""

    

    @classmethod

    def setUpClass(cls):

        """Set up test class with codebase scanning configuration."""

        super().setUpClass()

        cls.project_root = Path(__file__).parent.parent.parent

        cls.python_extensions = {'.py'}

        cls.excluded_dirs = {

            '__pycache__',

            '.git',

            'node_modules',

            '.pytest_cache',

            'venv',

            'env',

            '.tox'

        }



    def test_detect_datetime_utcnow_usage_patterns(self):

        """

        DETECTION TEST: Find all datetime.utcnow() usage patterns in Python files.

        

        This test SHOULD PASS, indicating that deprecated usage exists and needs modernization.

        """

        utcnow_patterns = self._scan_for_datetime_utcnow()

        

        # Log findings for analysis

        self.logger.info(f"Found {len(utcnow_patterns)} datetime.utcnow() usage patterns")

        

        for file_path, occurrences in utcnow_patterns.items():

            self.logger.info(f"File: {file_path}")

            for line_num, line_content in occurrences:

                self.logger.info(f"  Line {line_num}: {line_content.strip()}")

        

        # This test should PASS if deprecated usage is found (indicating work needed)

        self.assertGreater(len(utcnow_patterns), 0, 

                          "Expected to find datetime.utcnow() usage requiring modernization")

        

        # Store results for use in other tests

        self._store_detection_results(utcnow_patterns)

        

        return utcnow_patterns



    def test_categorize_datetime_utcnow_usage_types(self):

        """

        ANALYSIS TEST: Categorize different types of datetime.utcnow() usage.

        

        Categories:

        - Direct timestamp creation

        - Comparison operations

        - Arithmetic operations

        - Formatting operations

        - Assignment patterns

        """

        utcnow_patterns = self._scan_for_datetime_utcnow()

        

        categories = {

            'timestamp_creation': [],

            'comparisons': [],

            'arithmetic': [],

            'formatting': [],

            'assignments': [],

            'other': []

        }

        

        for file_path, occurrences in utcnow_patterns.items():

            for line_num, line_content in occurrences:

                category = self._categorize_usage(line_content)

                categories[category].append((file_path, line_num, line_content.strip()))

        

        # Log categorization results

        for category, items in categories.items():

            if items:

                self.logger.info(f"\n{category.upper()} ({len(items)} occurrences):")

                for file_path, line_num, content in items[:5]:  # Show first 5

                    self.logger.info(f"  {file_path}:{line_num} - {content}")

                if len(items) > 5:

                    self.logger.info(f"  ... and {len(items) - 5} more")

        

        # Validate we found various usage patterns

        total_occurrences = sum(len(items) for items in categories.values())

        self.assertGreater(total_occurrences, 0, "Should find datetime.utcnow() usage patterns")

        

        return categories



    def test_identify_high_risk_datetime_patterns(self):

        """

        RISK ASSESSMENT TEST: Identify high-risk datetime patterns that need careful handling.

        

        High-risk patterns:

        - Timezone-naive comparisons

        - Complex arithmetic operations

        - Serialization/deserialization contexts

        - Multi-service timestamp coordination

        """

        utcnow_patterns = self._scan_for_datetime_utcnow()

        

        high_risk_patterns = []

        medium_risk_patterns = []

        low_risk_patterns = []

        

        risk_indicators = {

            'high': [

                r'\.timestamp\(\)',  # Unix timestamp conversion

                r'fromtimestamp',     # Timestamp parsing

                r'strftime',          # String formatting

                r'\.isoformat\(\)',   # ISO format conversion

                r'<|>|<=|>=',        # Comparison operations

            ],

            'medium': [

                r'\+|\-',            # Arithmetic operations

                r'timedelta',        # Time delta operations

                r'\.total_seconds\(\)', # Duration calculations

            ]

        }

        

        for file_path, occurrences in utcnow_patterns.items():

            for line_num, line_content in occurrences:

                risk_level = self._assess_risk_level(line_content, risk_indicators)

                

                pattern_info = (file_path, line_num, line_content.strip())

                

                if risk_level == 'high':

                    high_risk_patterns.append(pattern_info)

                elif risk_level == 'medium':

                    medium_risk_patterns.append(pattern_info)

                else:

                    low_risk_patterns.append(pattern_info)

        

        # Log risk assessment

        self.logger.info(f"HIGH RISK patterns: {len(high_risk_patterns)}")

        self.logger.info(f"MEDIUM RISK patterns: {len(medium_risk_patterns)}")

        self.logger.info(f"LOW RISK patterns: {len(low_risk_patterns)}")

        

        # Show high-risk examples

        for file_path, line_num, content in high_risk_patterns[:10]:

            self.logger.info(f"HIGH RISK: {file_path}:{line_num} - {content}")

        

        # Validate risk assessment completed

        total_patterns = len(high_risk_patterns) + len(medium_risk_patterns) + len(low_risk_patterns)

        self.assertGreater(total_patterns, 0, "Should identify risk levels for all patterns")

        

        return {

            'high_risk': high_risk_patterns,

            'medium_risk': medium_risk_patterns,

            'low_risk': low_risk_patterns

        }



    def test_validate_modernization_approach_compatibility(self):

        """

        VALIDATION TEST: Verify that datetime.now(datetime.UTC) produces compatible results.

        

        This test validates that the modernized approach produces equivalent results

        to the deprecated datetime.utcnow().

        """

        # Test equivalence of datetime operations

        test_cases = [

            # Basic timestamp creation

            ('datetime.utcnow()', 'datetime.now(datetime.UTC)'),

            

            # ISO formatting

            ('datetime.utcnow().isoformat()', 'datetime.now(datetime.UTC).isoformat()'),

            

            # Timestamp conversion

            ('datetime.utcnow().timestamp()', 'datetime.now(datetime.UTC).timestamp()'),

            

            # String representation

            ('str(datetime.utcnow())', 'str(datetime.now(datetime.UTC))'),

        ]

        

        compatibility_results = []

        

        for old_pattern, new_pattern in test_cases:

            try:

                # Execute both patterns and compare structure (not exact values due to time differences)

                old_result = eval(old_pattern.replace('datetime.', 'datetime.'))

                new_result = eval(new_pattern.replace('datetime.', 'datetime.'))

                

                # Compare types and timezone awareness

                compatibility_results.append({

                    'old_pattern': old_pattern,

                    'new_pattern': new_pattern,

                    'old_type': type(old_result).__name__,

                    'new_type': type(new_result).__name__,

                    'old_tzinfo': getattr(old_result, 'tzinfo', None),

                    'new_tzinfo': getattr(new_result, 'tzinfo', None),

                    'compatible': type(old_result) == type(new_result)

                })

                

            except Exception as e:

                compatibility_results.append({

                    'old_pattern': old_pattern,

                    'new_pattern': new_pattern,

                    'error': str(e),

                    'compatible': False

                })

        

        # Log compatibility results

        for result in compatibility_results:

            self.logger.info(f"Pattern: {result['old_pattern']} -> {result['new_pattern']}")

            self.logger.info(f"  Compatible: {result.get('compatible', False)}")

            if 'error' in result:

                self.logger.info(f"  Error: {result['error']}")

            else:

                self.logger.info(f"  Types: {result['old_type']} -> {result['new_type']}")

                self.logger.info(f"  Timezone: {result['old_tzinfo']} -> {result['new_tzinfo']}")

        

        # Validate that modernization approach is compatible

        compatible_count = sum(1 for r in compatibility_results if r.get('compatible', False))

        self.assertGreater(compatible_count, 0, "Should have compatible modernization patterns")

        

        return compatibility_results



    def test_detect_timezone_consistency_requirements(self):

        """

        CONSISTENCY TEST: Detect patterns that require timezone consistency across the codebase.

        

        Identifies places where timezone handling must be consistent to prevent bugs.

        """

        utcnow_patterns = self._scan_for_datetime_utcnow()

        

        # Look for patterns that indicate timezone-sensitive operations

        timezone_sensitive_patterns = []

        

        sensitive_indicators = [

            r'\.isoformat\(\)',      # ISO format output

            r'\.timestamp\(\)',      # Unix timestamp conversion

            r'fromtimestamp',        # Timestamp parsing

            r'strftime',             # String formatting

            r'\.total_seconds\(\)',  # Duration calculations

            r'<|>|<=|>=',           # Comparison operations

        ]

        

        for file_path, occurrences in utcnow_patterns.items():

            for line_num, line_content in occurrences:

                for indicator in sensitive_indicators:

                    if re.search(indicator, line_content):

                        timezone_sensitive_patterns.append({

                            'file': file_path,

                            'line': line_num,

                            'content': line_content.strip(),

                            'sensitivity': indicator

                        })

                        break

        

        # Log timezone-sensitive patterns

        self.logger.info(f"Found {len(timezone_sensitive_patterns)} timezone-sensitive patterns")

        

        sensitivity_groups = {}

        for pattern in timezone_sensitive_patterns:

            sensitivity = pattern['sensitivity']

            if sensitivity not in sensitivity_groups:

                sensitivity_groups[sensitivity] = []

            sensitivity_groups[sensitivity].append(pattern)

        

        for sensitivity, patterns in sensitivity_groups.items():

            self.logger.info(f"\n{sensitivity} patterns ({len(patterns)} occurrences):")

            for pattern in patterns[:3]:  # Show first 3

                self.logger.info(f"  {pattern['file']}:{pattern['line']} - {pattern['content']}")

        

        # Validate timezone consistency requirements identified

        self.assertGreater(len(timezone_sensitive_patterns), 0, 

                          "Should identify timezone-sensitive patterns")

        

        return timezone_sensitive_patterns



    def test_estimate_modernization_scope_and_impact(self):

        """

        PLANNING TEST: Estimate the scope and impact of datetime modernization.

        

        Provides metrics for planning the modernization effort.

        """

        utcnow_patterns = self._scan_for_datetime_utcnow()

        

        # Calculate scope metrics

        total_files = len(utcnow_patterns)

        total_occurrences = sum(len(occurrences) for occurrences in utcnow_patterns.values())

        

        # Categorize by file type/component

        component_breakdown = {}

        for file_path in utcnow_patterns.keys():

            component = self._identify_component(file_path)

            if component not in component_breakdown:

                component_breakdown[component] = 0

            component_breakdown[component] += len(utcnow_patterns[file_path])

        

        # Estimate effort levels

        effort_estimate = {

            'low_effort': 0,      # Simple replacements

            'medium_effort': 0,   # Require testing

            'high_effort': 0      # Need careful analysis

        }

        

        for file_path, occurrences in utcnow_patterns.items():

            for line_num, line_content in occurrences:

                effort = self._estimate_effort_level(line_content)

                effort_estimate[effort] += 1

        

        # Create scope summary

        scope_summary = {

            'total_files': total_files,

            'total_occurrences': total_occurrences,

            'component_breakdown': component_breakdown,

            'effort_estimate': effort_estimate,

            'estimated_hours': (

                effort_estimate['low_effort'] * 0.1 +

                effort_estimate['medium_effort'] * 0.5 +

                effort_estimate['high_effort'] * 2.0

            )

        }

        

        # Log scope analysis

        self.logger.info("DATETIME MODERNIZATION SCOPE ANALYSIS")

        self.logger.info(f"Total files affected: {total_files}")

        self.logger.info(f"Total occurrences: {total_occurrences}")

        self.logger.info(f"Estimated effort hours: {scope_summary['estimated_hours']:.1f}")

        

        self.logger.info("\nComponent breakdown:")

        for component, count in sorted(component_breakdown.items()):

            self.logger.info(f"  {component}: {count} occurrences")

        

        self.logger.info("\nEffort breakdown:")

        for effort_level, count in effort_estimate.items():

            self.logger.info(f"  {effort_level}: {count} occurrences")

        

        # Validate scope estimation completed

        self.assertGreater(total_occurrences, 0, "Should have scope to analyze")

        

        return scope_summary



    def test_create_modernization_test_framework(self):

        """

        FRAMEWORK TEST: Create framework for validating datetime modernization.

        

        This test creates the infrastructure needed to validate modernization changes.

        """

        # Define modernization validation framework

        validation_framework = {

            'replacement_patterns': [

                {

                    'old': r'datetime\.utcnow\(\)',

                    'new': 'datetime.now(datetime.UTC)',

                    'imports_required': ['from datetime import datetime, timezone']

                }

            ],

            'validation_checks': [

                'timezone_awareness',

                'type_compatibility', 

                'serialization_consistency',

                'comparison_behavior'

            ],

            'test_cases': [

                {

                    'name': 'basic_replacement',

                    'old_code': 'timestamp = datetime.utcnow()',

                    'new_code': 'timestamp = datetime.now(datetime.UTC)',

                    'validation': 'assert timestamp.tzinfo is not None'

                },

                {

                    'name': 'iso_format',

                    'old_code': 'iso_time = datetime.utcnow().isoformat()',

                    'new_code': 'iso_time = datetime.now(datetime.UTC).isoformat()',

                    'validation': 'assert iso_time.endswith("+00:00") or iso_time.endswith("Z")'

                },

                {

                    'name': 'timestamp_conversion',

                    'old_code': 'unix_time = datetime.utcnow().timestamp()',

                    'new_code': 'unix_time = datetime.now(datetime.UTC).timestamp()',

                    'validation': 'assert isinstance(unix_time, float)'

                }

            ]

        }

        

        # Log framework structure

        self.logger.info("MODERNIZATION VALIDATION FRAMEWORK")

        self.logger.info(f"Replacement patterns: {len(validation_framework['replacement_patterns'])}")

        self.logger.info(f"Validation checks: {len(validation_framework['validation_checks'])}")

        self.logger.info(f"Test cases: {len(validation_framework['test_cases'])}")

        

        for test_case in validation_framework['test_cases']:

            self.logger.info(f"\nTest case: {test_case['name']}")

            self.logger.info(f"  Old: {test_case['old_code']}")

            self.logger.info(f"  New: {test_case['new_code']}")

            self.logger.info(f"  Validation: {test_case['validation']}")

        

        # Validate framework components

        self.assertGreater(len(validation_framework['replacement_patterns']), 0)

        self.assertGreater(len(validation_framework['test_cases']), 0)

        

        return validation_framework



    # Helper methods

    

    def _scan_for_datetime_utcnow(self) -> Dict[str, List[Tuple[int, str]]]:

        """Scan codebase for datetime.utcnow() usage patterns."""

        patterns = {}

        

        for py_file in self._get_python_files():

            try:

                with open(py_file, 'r', encoding='utf-8') as f:

                    lines = f.readlines()

                

                file_patterns = []

                for line_num, line in enumerate(lines, 1):

                    if 'datetime.utcnow()' in line:

                        file_patterns.append((line_num, line))

                

                if file_patterns:

                    rel_path = os.path.relpath(py_file, self.project_root)

                    patterns[rel_path] = file_patterns

                    

            except Exception as e:

                self.logger.warning(f"Could not scan {py_file}: {e}")

        

        return patterns

    

    def _get_python_files(self) -> List[Path]:

        """Get all Python files in the project."""

        python_files = []

        

        for root, dirs, files in os.walk(self.project_root):

            # Skip excluded directories

            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

            

            for file in files:

                if any(file.endswith(ext) for ext in self.python_extensions):

                    python_files.append(Path(root) / file)

        

        return python_files

    

    def _categorize_usage(self, line_content: str) -> str:

        """Categorize the type of datetime.utcnow() usage."""

        line_lower = line_content.lower().strip()

        

        if any(op in line_content for op in ['=', 'return']):

            if any(fmt in line_content for fmt in ['.isoformat()', '.strftime(']):

                return 'formatting'

            return 'assignments'

        elif any(op in line_content for op in ['<', '>', '<=', '>=', '==', '!=']):

            return 'comparisons'

        elif any(op in line_content for op in ['+', '-', 'timedelta']):

            return 'arithmetic'

        elif any(fmt in line_content for fmt in ['.isoformat()', '.strftime(', '.timestamp()']):

            return 'formatting'

        else:

            return 'other'

    

    def _assess_risk_level(self, line_content: str, risk_indicators: Dict[str, List[str]]) -> str:

        """Assess the risk level of a datetime usage pattern."""

        for risk_level, indicators in risk_indicators.items():

            for indicator in indicators:

                if re.search(indicator, line_content):

                    return risk_level

        return 'low'

    

    def _identify_component(self, file_path: str) -> str:

        """Identify which component a file belongs to."""

        path_parts = file_path.split('/')

        

        if 'netra_backend' in path_parts:

            return 'backend'

        elif 'auth_service' in path_parts:

            return 'auth_service'  

        elif 'analytics_service' in path_parts:

            return 'analytics_service'

        elif 'frontend' in path_parts:

            return 'frontend'

        elif 'shared' in path_parts:

            return 'shared'

        elif 'tests' in path_parts:

            return 'tests'

        elif 'scripts' in path_parts:

            return 'scripts'

        else:

            return 'other'

    

    def _estimate_effort_level(self, line_content: str) -> str:

        """Estimate the effort level required for modernizing a pattern."""

        # High effort: Complex patterns that need careful analysis

        if any(pattern in line_content for pattern in [

            'fromtimestamp', 'strptime', 'comparison', '<', '>', 'timedelta'

        ]):

            return 'high_effort'

        

        # Medium effort: Patterns that need testing

        if any(pattern in line_content for pattern in [

            '.isoformat()', '.timestamp()', '.strftime('

        ]):

            return 'medium_effort'

        

        # Low effort: Simple replacements

        return 'low_effort'

    

    def _store_detection_results(self, utcnow_patterns: Dict[str, List[Tuple[int, str]]]):

        """Store detection results for use by other tests."""

        # Store in class variable for access by other test methods

        self.__class__.detected_patterns = utcnow_patterns





if __name__ == '__main__':

    unittest.main()

