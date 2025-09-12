#!/usr/bin/env python3
"""
Test Dashboard - Interactive test metrics and insights

Provides a comprehensive view of test execution history, trends, and recommendations.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.test_execution_tracker import TestExecutionTracker
    from scripts.business_value_test_index import BusinessValueTestIndexer
except ImportError:
    print("Error: Required modules not found. Please ensure test_execution_tracker.py exists.")
    sys.exit(1)


class TestDashboard:
    """Interactive dashboard for test metrics and insights"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.tracker = TestExecutionTracker(project_root)
        self.business_indexer = BusinessValueTestIndexer(project_root)
        
    def show_overview(self):
        """Display test system overview"""
        print("\n" + "="*80)
        print("TEST SYSTEM OVERVIEW")
        print("="*80)
        
        # Category summary
        category_summary = self.tracker.get_category_summary()
        
        print("\nCATEGORY STATUS:")
        print("-"*40)
        print(f"{'Category':<15} {'Tests':<10} {'Default':<10} {'Fail Rate':<12} {'Avg Duration':<12}")
        print("-"*40)
        
        for category, stats in sorted(category_summary.items()):
            default_marker = "[U+2713]" if stats['is_default'] else " "
            print(f"{category:<15} {stats['total_tests']:<10} {default_marker:<10} "
                  f"{stats['avg_failure_rate']:.1f}%{'':>8} {stats['avg_duration']:.2f}s")
        
        # Recent trends
        trends = self.tracker.get_failure_trends(days=7)
        
        if trends['daily_stats']:
            print("\nRECENT TRENDS (7 days):")
            print("-"*40)
            
            recent_stats = trends['daily_stats'][-7:]
            total_runs = sum(s['total'] for s in recent_stats)
            total_failures = sum(s['failures'] for s in recent_stats)
            avg_failure_rate = (total_failures / total_runs * 100) if total_runs > 0 else 0
            
            print(f"Total Test Runs: {total_runs}")
            print(f"Total Failures: {total_failures}")
            print(f"Average Failure Rate: {avg_failure_rate:.1f}%")
            
            # Show trend direction
            if len(recent_stats) >= 2:
                yesterday = recent_stats[-2]['failure_rate'] if len(recent_stats) > 1 else 0
                today = recent_stats[-1]['failure_rate']
                trend = " up " if today > yesterday else " down " if today < yesterday else " -> "
                print(f"Trend Direction: {trend} ({today:.1f}% today vs {yesterday:.1f}% yesterday)")
        
        # Flaky tests
        flaky_tests = self.tracker.get_flaky_tests(threshold=0.3, min_runs=5)
        if flaky_tests:
            print("\nFLAKY TESTS DETECTED:")
            print("-"*40)
            for i, test in enumerate(flaky_tests[:5], 1):
                print(f"{i}. {test['test_name'][:60]}")
                print(f"   Failure Rate: {test['failure_rate']:.1%}")
                if 'alternation_score' in test:
                    print(f"   Instability: {test['alternation_score']:.1%}")
    
    def show_recommendations(self):
        """Show actionable recommendations"""
        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)
        
        recommendations = []
        
        # Check category health
        category_summary = self.tracker.get_category_summary()
        
        # Find categories with high failure rates
        for category, stats in category_summary.items():
            if stats['recent_failure_rate'] > 20:
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'Stability',
                    'message': f"Fix {category} tests - {stats['recent_failure_rate']:.1f}% failure rate",
                    'action': f"python unified_test_runner.py --category {category} --verbose"
                })
        
        # Check for missing default categories
        default_categories = self.tracker.get_default_categories()
        for category in default_categories:
            if category not in category_summary or category_summary[category]['total_tests'] == 0:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'Coverage',
                    'message': f"No tests found for default category '{category}'",
                    'action': f"Create tests in appropriate directory for {category}"
                })
        
        # Check for slow tests
        slowest = self.tracker.get_slowest_tests(limit=5)
        if slowest and slowest[0]['average_duration'] > 30:
            recommendations.append({
                'priority': 'LOW',
                'category': 'Performance',
                'message': f"Optimize slow tests - slowest takes {slowest[0]['average_duration']:.1f}s",
                'action': "Review and optimize test fixtures and setup"
            })
        
        # Display recommendations
        if recommendations:
            # Sort by priority
            priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
            recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
            
            for i, rec in enumerate(recommendations, 1):
                priority_marker = {
                    'HIGH': '[U+1F534]',
                    'MEDIUM': '[U+1F7E1]',
                    'LOW': '[U+1F7E2]'
                }.get(rec['priority'], '[U+26AA]')
                
                print(f"\n{i}. [{rec['priority']}] {rec['category']}")
                print(f"   {rec['message']}")
                if rec.get('action'):
                    print(f"   Action: {rec['action']}")
        else:
            print("\n PASS:  No critical issues detected. Test system is healthy!")
    
    def show_category_details(self, category: str):
        """Show detailed information for a specific category"""
        print(f"\n" + "="*80)
        print(f"CATEGORY DETAILS: {category.upper()}")
        print("="*80)
        
        # Get category summary
        all_categories = self.tracker.get_category_summary()
        if category not in all_categories:
            print(f"Category '{category}' not found in test system.")
            return
        
        stats = all_categories[category]
        
        print(f"\nSTATISTICS:")
        print(f"  Total Tests: {stats['total_tests']}")
        print(f"  Total Runs: {stats['total_runs']}")
        print(f"  Average Failure Rate: {stats['avg_failure_rate']:.1f}%")
        print(f"  Recent Failure Rate (7d): {stats['recent_failure_rate']:.1f}%")
        print(f"  Average Duration: {stats['avg_duration']:.2f}s")
        print(f"  Default Category: {'Yes' if stats['is_default'] else 'No'}")
        
        # Get recent failures
        recent_history = self.tracker.get_test_history(days=7)
        category_failures = [h for h in recent_history 
                           if h.get('category') == category and h.get('status') == 'failed']
        
        if category_failures:
            print(f"\nRECENT FAILURES (last 7 days):")
            print("-"*40)
            for failure in category_failures[:10]:
                timestamp = failure.get('timestamp', 'unknown')
                test_name = failure.get('test_name', 'unknown')
                print(f"  {timestamp}: {test_name}")
        
        # Show slowest tests in category
        slowest = self.tracker.get_slowest_tests(category=category, limit=5)
        if slowest:
            print(f"\nSLOWEST TESTS:")
            print("-"*40)
            for test in slowest:
                print(f"  {test['test_name'][:60]}: {test['average_duration']:.2f}s")
    
    def show_test_history(self, test_path: str = None, days: int = 7):
        """Show test execution history"""
        print(f"\n" + "="*80)
        print(f"TEST HISTORY (last {days} days)")
        print("="*80)
        
        history = self.tracker.get_test_history(file_path=test_path, days=days)
        
        if not history:
            print("No test history found for the specified criteria.")
            return
        
        # Group by day
        by_day = {}
        for run in history:
            timestamp = run.get('timestamp', '')
            if timestamp:
                day = timestamp.split('T')[0]
                if day not in by_day:
                    by_day[day] = []
                by_day[day].append(run)
        
        # Display by day
        for day in sorted(by_day.keys(), reverse=True):
            runs = by_day[day]
            passed = sum(1 for r in runs if r.get('status') == 'passed')
            failed = sum(1 for r in runs if r.get('status') == 'failed')
            
            print(f"\n{day}: {len(runs)} tests ({passed} passed, {failed} failed)")
            
            # Show failed tests
            failed_tests = [r for r in runs if r.get('status') == 'failed']
            if failed_tests:
                print("  Failed tests:")
                for test in failed_tests[:5]:
                    print(f"    - {test.get('test_name', 'unknown')}")
    
    def generate_html_report(self, output_path: str = None):
        """Generate an HTML dashboard report"""
        if output_path is None:
            output_path = self.project_root / "test_reports" / "dashboard.html"
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Gather all data
        category_summary = self.tracker.get_category_summary()
        failure_trends = self.tracker.get_failure_trends(days=30)
        flaky_tests = self.tracker.get_flaky_tests()
        slowest_tests = self.tracker.get_slowest_tests(limit=10)
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #4CAF50; color: white; }}
        .status-pass {{ color: green; font-weight: bold; }}
        .status-fail {{ color: red; font-weight: bold; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
        .metric-label {{ color: #666; font-size: 14px; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }}
        .chart {{ width: 100%; height: 300px; background: #fafafa; border: 1px solid #ddd; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Test Execution Dashboard</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="card">
        <h2>Overview</h2>
        <div class="metrics">
"""
        
        # Calculate overall metrics
        total_categories = len(category_summary)
        default_categories = sum(1 for c in category_summary.values() if c['is_default'])
        avg_failure_rate = sum(c['avg_failure_rate'] for c in category_summary.values()) / max(total_categories, 1)
        
        html_content += f"""
            <div class="metric">
                <div class="metric-value">{total_categories}</div>
                <div class="metric-label">Test Categories</div>
            </div>
            <div class="metric">
                <div class="metric-value">{default_categories}</div>
                <div class="metric-label">Default Categories</div>
            </div>
            <div class="metric">
                <div class="metric-value">{avg_failure_rate:.1f}%</div>
                <div class="metric-label">Avg Failure Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{len(flaky_tests)}</div>
                <div class="metric-label">Flaky Tests</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>Category Summary</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Tests</th>
                <th>Default</th>
                <th>Failure Rate</th>
                <th>Recent Failure Rate</th>
                <th>Avg Duration</th>
            </tr>
"""
        
        for category, stats in sorted(category_summary.items()):
            default_marker = "[U+2713]" if stats['is_default'] else ""
            failure_class = "status-fail" if stats['avg_failure_rate'] > 20 else ""
            html_content += f"""
            <tr>
                <td><strong>{category}</strong></td>
                <td>{stats['total_tests']}</td>
                <td>{default_marker}</td>
                <td class="{failure_class}">{stats['avg_failure_rate']:.1f}%</td>
                <td>{stats['recent_failure_rate']:.1f}%</td>
                <td>{stats['avg_duration']:.2f}s</td>
            </tr>
"""
        
        html_content += """
        </table>
    </div>
    
    <div class="card">
        <h2>Flaky Tests</h2>
"""
        
        if flaky_tests:
            html_content += """
        <table>
            <tr>
                <th>Test Name</th>
                <th>File Path</th>
                <th>Failure Rate</th>
                <th>Total Runs</th>
            </tr>
"""
            for test in flaky_tests[:10]:
                html_content += f"""
            <tr>
                <td>{test['test_name'][:80]}</td>
                <td>{test['file_path']}</td>
                <td class="status-fail">{test['failure_rate']:.1%}</td>
                <td>{test['total_runs']}</td>
            </tr>
"""
            html_content += "</table>"
        else:
            html_content += "<p>No flaky tests detected.</p>"
        
        html_content += """
    </div>
    
    <div class="card">
        <h2>Slowest Tests</h2>
        <table>
            <tr>
                <th>Test Name</th>
                <th>Average Duration</th>
                <th>Categories</th>
            </tr>
"""
        
        for test in slowest_tests:
            categories = json.loads(test.get('categories', '[]'))
            html_content += f"""
            <tr>
                <td>{test['test_name'][:80]}</td>
                <td>{test['average_duration']:.2f}s</td>
                <td>{', '.join(categories)}</td>
            </tr>
"""
        
        html_content += """
        </table>
    </div>
    
    <div class="card">
        <h2>Recommendations</h2>
"""
        
        # Add recommendations
        recommendations = []
        for category, stats in category_summary.items():
            if stats['recent_failure_rate'] > 20:
                recommendations.append(f"Fix {category} tests - {stats['recent_failure_rate']:.1f}% failure rate")
        
        if len(flaky_tests) > 10:
            recommendations.append(f"Address {len(flaky_tests)} flaky tests to improve reliability")
        
        if slowest_tests and slowest_tests[0]['average_duration'] > 30:
            recommendations.append(f"Optimize slow tests - slowest takes {slowest_tests[0]['average_duration']:.1f}s")
        
        if recommendations:
            html_content += "<ul>"
            for rec in recommendations:
                html_content += f"<li>{rec}</li>"
            html_content += "</ul>"
        else:
            html_content += "<p> PASS:  Test system is healthy!</p>"
        
        html_content += """
    </div>
</body>
</html>
"""
        
        # Write HTML file
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        print(f"HTML dashboard generated: {output_path}")
        return output_path


def main():
    """CLI for test dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Dashboard - Interactive test metrics')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Overview command
    overview_parser = subparsers.add_parser('overview', help='Show test system overview')
    
    # Recommendations command
    rec_parser = subparsers.add_parser('recommendations', help='Show recommendations')
    
    # Category command
    cat_parser = subparsers.add_parser('category', help='Show category details')
    cat_parser.add_argument('name', help='Category name')
    
    # History command
    hist_parser = subparsers.add_parser('history', help='Show test history')
    hist_parser.add_argument('--test', help='Test file path')
    hist_parser.add_argument('--days', type=int, default=7, help='Days of history')
    
    # HTML report command
    html_parser = subparsers.add_parser('html', help='Generate HTML dashboard')
    html_parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    dashboard = TestDashboard(args.project_root)
    
    if args.command == 'overview' or not args.command:
        dashboard.show_overview()
        dashboard.show_recommendations()
    elif args.command == 'recommendations':
        dashboard.show_recommendations()
    elif args.command == 'category':
        dashboard.show_category_details(args.name)
    elif args.command == 'history':
        dashboard.show_test_history(test_path=args.test, days=args.days)
    elif args.command == 'html':
        dashboard.generate_html_report(output_path=args.output)
    else:
        dashboard.show_overview()


if __name__ == '__main__':
    main()