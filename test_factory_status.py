"""Test script for AI Factory Status Report system.

Validates that all components work correctly.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.factory_status.report_builder import ReportBuilder


def test_report_generation():
    """Test basic report generation."""
    print("=" * 60)
    print("AI FACTORY STATUS REPORT - TEST RUN")
    print("=" * 60)
    
    try:
        # Initialize report builder
        print("\n1. Initializing report builder...")
        builder = ReportBuilder()
        print("   [OK] Report builder initialized")
        
        # Generate report for last 24 hours
        print("\n2. Generating report for last 24 hours...")
        report = builder.build_report(hours=24)
        print(f"   [OK] Report generated: {report.report_id}")
        
        # Display executive summary
        print("\n3. Executive Summary:")
        print(f"   - Timestamp: {report.executive_summary.timestamp}")
        print(f"   - Productivity Score: {report.executive_summary.productivity_score}/10")
        print(f"   - Business Value Score: {report.executive_summary.business_value_score}/10")
        print(f"   - Overall Status: {report.executive_summary.overall_status.upper()}")
        
        # Display key highlights
        print("\n4. Key Highlights:")
        for highlight in report.executive_summary.key_highlights:
            print(f"   - {highlight}")
        
        # Display action items
        print("\n5. Action Items:")
        for action in report.executive_summary.action_items:
            print(f"   - {action}")
        
        # Display velocity metrics
        print("\n6. Velocity Metrics:")
        print(f"   - Commits per hour: {report.velocity_metrics['commits_per_hour']:.2f}")
        print(f"   - Commits per day: {report.velocity_metrics['commits_per_day']:.2f}")
        print(f"   - Velocity trend: {report.velocity_metrics['velocity_trend']:.1%}")
        
        # Display impact metrics
        print("\n7. Impact Metrics:")
        print(f"   - Lines added: {report.impact_metrics['total_lines_added']}")
        print(f"   - Lines deleted: {report.impact_metrics['total_lines_deleted']}")
        print(f"   - Files changed: {report.impact_metrics['files_changed']}")
        print(f"   - Customer-facing ratio: {report.impact_metrics['customer_facing_ratio']:.1%}")
        
        # Display quality metrics
        print("\n8. Quality Metrics:")
        print(f"   - Quality score: {report.quality_metrics['quality_score']:.1f}/10")
        compliance = report.quality_metrics['architecture_compliance']
        print(f"   - Architecture compliance: {compliance['compliance_rate']:.1%}")
        if compliance['violations'] > 0:
            print(f"     [WARNING] {compliance['violations']} violations found!")
        
        # Display business value metrics
        print("\n9. Business Value Metrics:")
        print(f"   - Overall value score: {report.business_value_metrics['overall_value_score']:.1f}/10")
        print("   - Objective scores:")
        for obj, score in report.business_value_metrics['objective_scores'].items():
            print(f"     - {obj}: {score:.1f}")
        
        # Display branch metrics
        print("\n10. Branch Metrics:")
        print(f"   - Total branches: {report.branch_metrics['total_branches']}")
        print(f"   - Active branches: {report.branch_metrics['active_branches']}")
        print(f"   - Stale branches: {report.branch_metrics['stale_branches']}")
        print(f"   - Collaboration score: {report.branch_metrics['collaboration_score']:.1f}/10")
        
        # Display feature progress
        print("\n11. Feature Progress:")
        print(f"   - Features added: {report.feature_progress['features_added']}")
        print(f"   - Bugs fixed: {report.feature_progress['bugs_fixed']}")
        
        # Display recommendations
        print("\n12. Recommendations:")
        for rec in report.recommendations:
            print(f"   - {rec}")
        
        # Export reports
        print("\n13. Exporting reports...")
        
        # Export JSON
        json_report = builder.export_json(report)
        with open("test_report.json", "w") as f:
            f.write(json_report)
        print(f"   [OK] JSON report saved to test_report.json ({len(json_report)} bytes)")
        
        # Export summary
        summary_report = builder.export_summary(report)
        with open("test_summary.txt", "w") as f:
            f.write(summary_report)
        print(f"   [OK] Summary saved to test_summary.txt ({len(summary_report)} bytes)")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_individual_components():
    """Test individual components."""
    print("\n" + "=" * 60)
    print("TESTING INDIVIDUAL COMPONENTS")
    print("=" * 60)
    
    try:
        # Test git commit parser
        print("\n1. Testing Git Commit Parser...")
        from app.services.factory_status.git_commit_parser import GitCommitParser
        parser = GitCommitParser()
        commits = parser.get_commits(hours=168)  # Last week
        print(f"   [OK] Found {len(commits)} commits in last week")
        if commits:
            print(f"   [OK] Latest commit: {commits[0].message[:50]}...")
        
        # Test git diff analyzer
        print("\n2. Testing Git Diff Analyzer...")
        from app.services.factory_status.git_diff_analyzer import GitDiffAnalyzer
        analyzer = GitDiffAnalyzer()
        if commits:
            metrics = analyzer.analyze_commit(commits[0].hash)
            print(f"   [OK] Analyzed commit: {metrics.files_changed} files changed")
            print(f"   [OK] Business impact: {metrics.business_impact.value}")
        
        # Test git branch tracker
        print("\n3. Testing Git Branch Tracker...")
        from app.services.factory_status.git_branch_tracker import GitBranchTracker
        tracker = GitBranchTracker()
        branches = tracker.get_all_branches()
        print(f"   [OK] Found {len(branches)} branches")
        active = [b for b in branches if b.status.value == "active"]
        print(f"   [OK] Active branches: {len(active)}")
        
        # Test velocity calculator
        print("\n4. Testing Velocity Calculator...")
        from app.services.factory_status.metrics_velocity import VelocityCalculator
        vel_calc = VelocityCalculator()
        vel_metrics = vel_calc.calculate_velocity(24)
        print(f"   [OK] Velocity calculated: {vel_metrics.commits_per_period:.2f} commits/period")
        
        # Test impact calculator
        print("\n5. Testing Impact Calculator...")
        from app.services.factory_status.metrics_impact import ImpactCalculator
        imp_calc = ImpactCalculator()
        imp_metrics = imp_calc.calculate_impact_metrics(24)
        print(f"   [OK] Impact calculated: {imp_metrics.lines_added} lines added")
        
        # Test quality calculator
        print("\n6. Testing Quality Calculator...")
        from app.services.factory_status.metrics_quality import QualityCalculator
        qual_calc = QualityCalculator()
        qual_metrics = qual_calc.calculate_quality_metrics()
        print(f"   [OK] Quality score: {qual_metrics.quality_score:.1f}/10")
        
        # Test business value calculator
        print("\n7. Testing Business Value Calculator...")
        from app.services.factory_status.metrics_business_value import BusinessValueCalculator
        bus_calc = BusinessValueCalculator()
        bus_metrics = bus_calc.calculate_business_value_metrics(24)
        print(f"   [OK] Business value score: {bus_metrics.overall_value_score:.1f}/10")
        
        print("\n" + "=" * 60)
        print("ALL COMPONENTS TESTED SUCCESSFULLY!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] COMPONENT TEST: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nStarting AI Factory Status Report Test Suite...")
    print("Repository:", Path.cwd())
    print("Timestamp:", datetime.now().isoformat())
    
    # Run tests
    success = True
    
    # Test individual components first
    if not test_individual_components():
        success = False
    
    # Test full report generation
    if not test_report_generation():
        success = False
    
    # Final result
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] ALL TESTS PASSED!")
        print("\nThe AI Factory Status Report system is ready for use.")
        print("\nNext steps:")
        print("1. Review the generated test_report.json and test_summary.txt")
        print("2. Deploy the API endpoints to your FastAPI server")
        print("3. Enable the GitHub Actions workflow")
        print("4. Implement the frontend dashboard")
    else:
        print("[FAILED] SOME TESTS FAILED")
        print("\nPlease review the errors above and fix any issues.")
    print("=" * 60)
    
    sys.exit(0 if success else 1)