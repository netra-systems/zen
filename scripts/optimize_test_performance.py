#!/usr/bin/env python3
"""
Test Performance Optimization Script

Analyzes and optimizes test suite performance by identifying slow tests,
flaky tests, and common performance bottlenecks.
"""

import argparse
import ast
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter

import sys
sys.path.append(str(Path(__file__).parent.parent))

from shared.isolated_environment import IsolatedEnvironment

env = IsolatedEnvironment()


class TestPerformanceAnalyzer:
    """Analyzes test suite for performance issues."""
    
    def __init__(self, test_directory: Path):
        self.test_directory = test_directory
        self.slow_patterns = {
            'sleep_calls': [r'time\.sleep\(([^)]+)\)', r'asyncio\.sleep\(([^)]+)\)'],
            'network_calls': [r'requests\.(?:get|post|put|delete)', r'httpx\.(?:get|post|put|delete)'],
            'database_operations': [r'session\.(?:add|commit|query)', r'\.execute\('],
            'llm_calls': [r'llm_manager\.', r'openai\.', r'gemini\.'],
            'file_operations': [r'open\(', r'\.write\(', r'\.read\('],
        }
        self.optimization_suggestions = []
        self.test_files_analyzed = 0
        
    def analyze_all_tests(self) -> Dict:
        """Analyze all test files for performance issues."""
        results = {
            'slow_patterns': defaultdict(list),
            'test_statistics': {},
            'optimization_suggestions': [],
            'files_analyzed': 0
        }
        
        test_files = list(self.test_directory.rglob('test_*.py'))
        results['files_analyzed'] = len(test_files)
        
        for test_file in test_files:
            file_results = self._analyze_test_file(test_file)
            
            # Merge results
            for pattern_type, matches in file_results['patterns'].items():
                results['slow_patterns'][pattern_type].extend([
                    {'file': str(test_file), 'matches': matches}
                ])
            
            results['test_statistics'][str(test_file)] = file_results['statistics']
        
        # Generate optimization suggestions
        results['optimization_suggestions'] = self._generate_optimization_suggestions(results)
        
        return results
    
    def _analyze_test_file(self, test_file: Path) -> Dict:
        """Analyze a single test file."""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {'patterns': {}, 'statistics': {'error': str(e)}}
        
        patterns_found = {}
        for pattern_type, regexes in self.slow_patterns.items():
            matches = []
            for regex in regexes:
                for match in re.finditer(regex, content):
                    matches.append({
                        'line': content[:match.start()].count('\n') + 1,
                        'match': match.group(0),
                        'value': match.group(1) if match.groups() else None
                    })
            patterns_found[pattern_type] = matches
        
        # Count test functions
        test_function_count = len(re.findall(r'def test_\w+', content))
        async_test_count = len(re.findall(r'async def test_\w+', content))
        fixture_count = len(re.findall(r'@pytest\.fixture', content))
        
        statistics = {
            'test_functions': test_function_count,
            'async_tests': async_test_count,
            'fixtures': fixture_count,
            'file_size': len(content),
            'total_patterns': sum(len(matches) for matches in patterns_found.values())
        }
        
        return {
            'patterns': patterns_found,
            'statistics': statistics
        }
    
    def _generate_optimization_suggestions(self, results: Dict) -> List[str]:
        """Generate optimization suggestions based on analysis."""
        suggestions = []
        
        # Check for excessive sleep calls
        sleep_files = []
        for pattern_data in results['slow_patterns']['sleep_calls']:
            if pattern_data['matches']:
                sleep_files.append(pattern_data['file'])
                sleep_times = []
                for match in pattern_data['matches']:
                    if match['value']:
                        try:
                            sleep_time = float(match['value'])
                            sleep_times.append(sleep_time)
                        except ValueError:
                            pass
                
                if sleep_times:
                    total_sleep = sum(sleep_times)
                    if total_sleep > 5.0:  # More than 5 seconds of sleep
                        suggestions.append(
                            f"CRITICAL: {pattern_data['file']} has {total_sleep:.1f}s of sleep calls. "
                            "Consider using fast_test decorator or mocking time.sleep."
                        )
                    elif total_sleep > 1.0:
                        suggestions.append(
                            f"HIGH: {pattern_data['file']} has {total_sleep:.1f}s of sleep calls. "
                            "Consider optimizing with performance helpers."
                        )
        
        # Check for network calls in unit tests
        unit_test_files = [f for f in results['slow_patterns']['network_calls'] 
                          if '/unit/' in f.get('file', '')]
        if unit_test_files:
            suggestions.append(
                f"MEDIUM: Found network calls in {len(unit_test_files)} unit test files. "
                "Unit tests should mock network calls."
            )
        
        # Check for excessive LLM calls
        llm_files = [f for f in results['slow_patterns']['llm_calls'] if f['matches']]
        if len(llm_files) > 10:
            suggestions.append(
                f"MEDIUM: Found LLM calls in {len(llm_files)} test files. "
                "Consider using mock LLM responses for faster testing."
            )
        
        # Check test file sizes
        large_files = []
        for file_path, stats in results['test_statistics'].items():
            if stats.get('file_size', 0) > 50000:  # > 50KB
                large_files.append(file_path)
        
        if large_files:
            suggestions.append(
                f"LOW: Found {len(large_files)} large test files (>50KB). "
                "Consider splitting into smaller, focused test files."
            )
        
        return suggestions


def apply_performance_optimizations(test_directory: Path, dry_run: bool = True) -> List[str]:
    """Apply automatic performance optimizations to test files."""
    applied_optimizations = []
    
    # Common optimization patterns
    optimizations = [
        {
            'pattern': r'time\.sleep\(([0-9.]+)\)',
            'replacement': '# time.sleep({}) # Optimized: use @fast_test decorator',
            'description': 'Comment out sleep calls with optimization note'
        },
        {
            'pattern': r'import time\n(.*?)time\.sleep',
            'replacement': 'from test_framework.performance_helpers import fast_test\nimport time\\n\\1# time.sleep',
            'description': 'Add fast_test import and comment sleep'
        }
    ]
    
    test_files = list(test_directory.rglob('test_*.py'))
    
    for test_file in test_files:
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            modified_content = original_content
            file_modified = False
            
            for opt in optimizations:
                if re.search(opt['pattern'], modified_content):
                    if not dry_run:
                        modified_content = re.sub(opt['pattern'], opt['replacement'], modified_content)
                        file_modified = True
                    applied_optimizations.append(f"{test_file}: {opt['description']}")
            
            if file_modified and not dry_run:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
        
        except Exception as e:
            applied_optimizations.append(f"ERROR processing {test_file}: {e}")
    
    return applied_optimizations


def find_flaky_tests(test_directory: Path) -> List[Dict]:
    """Find potentially flaky tests by analyzing test patterns."""
    flaky_indicators = [
        r'random\.',
        r'time\.time\(\)',
        r'datetime\.now\(\)',
        r'threading\.',
        r'multiprocessing\.',
        r'subprocess\.',
        r'os\.environ',
        r'tempfile\.',
    ]
    
    flaky_tests = []
    test_files = list(test_directory.rglob('test_*.py'))
    
    for test_file in test_files:
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            flaky_matches = []
            for indicator in flaky_indicators:
                matches = re.finditer(indicator, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    flaky_matches.append({
                        'pattern': indicator,
                        'line': line_num,
                        'match': match.group(0)
                    })
            
            if flaky_matches:
                # Find test functions near these patterns
                test_functions = re.finditer(r'def (test_\w+)', content)
                for func_match in test_functions:
                    func_line = content[:func_match.start()].count('\n') + 1
                    nearby_flaky = [fm for fm in flaky_matches 
                                   if abs(fm['line'] - func_line) < 20]
                    if nearby_flaky:
                        flaky_tests.append({
                            'file': str(test_file),
                            'function': func_match.group(1),
                            'line': func_line,
                            'indicators': nearby_flaky
                        })
        
        except Exception as e:
            continue
    
    return flaky_tests


def generate_performance_report(results: Dict, flaky_tests: List[Dict]) -> str:
    """Generate a comprehensive performance report."""
    report = []
    report.append("# Test Suite Performance Analysis Report")
    report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary statistics
    total_files = results['files_analyzed']
    total_patterns = sum(
        sum(len(pattern_data.get('matches', [])) for pattern_data in pattern_list)
        for pattern_list in results['slow_patterns'].values()
    )
    
    report.append("## Summary")
    report.append(f"- **Files Analyzed**: {total_files}")
    report.append(f"- **Performance Issues Found**: {total_patterns}")
    report.append(f"- **Potentially Flaky Tests**: {len(flaky_tests)}")
    report.append("")
    
    # Optimization suggestions
    if results['optimization_suggestions']:
        report.append("## Critical Optimization Recommendations")
        for i, suggestion in enumerate(results['optimization_suggestions'], 1):
            priority = suggestion.split(':')[0]
            report.append(f"{i}. **{priority}**: {suggestion}")
        report.append("")
    
    # Pattern analysis
    report.append("## Performance Pattern Analysis")
    for pattern_type, pattern_data in results['slow_patterns'].items():
        if pattern_data:
            total_occurrences = sum(len(pd.get('matches', [])) for pd in pattern_data)
            affected_files = len([pd for pd in pattern_data if pd.get('matches')])
            report.append(f"### {pattern_type.replace('_', ' ').title()}")
            report.append(f"- **Occurrences**: {total_occurrences}")
            report.append(f"- **Files Affected**: {affected_files}")
            report.append("")
    
    # Flaky test analysis
    if flaky_tests:
        report.append("## Potentially Flaky Tests")
        report.append("Tests that may be unreliable due to timing, randomness, or external dependencies:")
        report.append("")
        
        flaky_by_file = defaultdict(list)
        for test in flaky_tests:
            flaky_by_file[test['file']].append(test)
        
        for file_path, tests in flaky_by_file.items():
            report.append(f"### {file_path}")
            for test in tests:
                indicators = [ind['pattern'] for ind in test['indicators']]
                report.append(f"- `{test['function']}` (line {test['line']}) - Indicators: {', '.join(set(indicators))}")
            report.append("")
    
    # Recommendations
    report.append("## Recommended Actions")
    report.append("1. **Immediate**: Apply `@fast_test` decorator to tests with sleep calls")
    report.append("2. **Short-term**: Mock external dependencies (network, LLM, database)")
    report.append("3. **Medium-term**: Refactor large test files into smaller, focused modules")
    report.append("4. **Long-term**: Implement comprehensive performance monitoring in CI")
    report.append("")
    
    report.append("## Tools Available")
    report.append("- `test_framework.performance_helpers.fast_test` - Mock sleep functions")
    report.append("- `test_framework.performance_helpers.timeout_override` - Reduce timeouts")
    report.append("- `test_framework.performance_helpers.mock_external_dependencies` - Mock external calls")
    report.append("- `test_framework.performance_helpers.FlakynessReducer` - Stable wait conditions")
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Optimize test suite performance")
    parser.add_argument("--test-dir", type=Path, default=Path("netra_backend/tests"),
                       help="Test directory to analyze")
    parser.add_argument("--output", type=Path, help="Output file for report")
    parser.add_argument("--apply-optimizations", action="store_true",
                       help="Apply automatic optimizations")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Show what would be changed without modifying files")
    
    args = parser.parse_args()
    
    if not args.test_dir.exists():
        print(f"Error: Test directory {args.test_dir} does not exist")
        return 1
    
    print(f"Analyzing test performance in {args.test_dir}...")
    
    # Analyze performance
    analyzer = TestPerformanceAnalyzer(args.test_dir)
    results = analyzer.analyze_all_tests()
    
    # Find flaky tests
    print("Identifying potentially flaky tests...")
    flaky_tests = find_flaky_tests(args.test_dir)
    
    # Generate report
    report = generate_performance_report(results, flaky_tests)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)
    
    # Apply optimizations if requested
    if args.apply_optimizations:
        print("\nApplying performance optimizations...")
        optimizations = apply_performance_optimizations(args.test_dir, args.dry_run)
        
        if args.dry_run:
            print("DRY RUN - Would apply these optimizations:")
        else:
            print("Applied optimizations:")
        
        for opt in optimizations[:10]:  # Show first 10
            print(f"  - {opt}")
        
        if len(optimizations) > 10:
            print(f"  ... and {len(optimizations) - 10} more")
    
    # Summary
    total_issues = sum(
        sum(len(pattern_data.get('matches', [])) for pattern_data in pattern_list)
        for pattern_list in results['slow_patterns'].values()
    )
    
    print(f"\n=== SUMMARY ===")
    print(f"Files analyzed: {results['files_analyzed']}")
    print(f"Performance issues: {total_issues}")
    print(f"Potentially flaky tests: {len(flaky_tests)}")
    print(f"Optimization suggestions: {len(results['optimization_suggestions'])}")
    
    if total_issues > 0 or flaky_tests:
        print("\nRecommendation: Review the generated report and apply optimizations to improve test suite performance.")
        return 1 if total_issues > 20 else 0
    else:
        print("[U+2713] Test suite looks well optimized!")
        return 0


if __name__ == "__main__":
    exit(main())