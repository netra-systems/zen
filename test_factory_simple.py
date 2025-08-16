"""Simple test for AI Factory Status Report - validates basic functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("AI Factory Status Report - Simple Validation Test")
print("=" * 60)

try:
    # Test imports
    print("\n1. Testing imports...")
    from app.services.factory_status.git_commit_parser import GitCommitParser
    from app.services.factory_status.git_diff_analyzer import GitDiffAnalyzer
    from app.services.factory_status.git_branch_tracker import GitBranchTracker
    from app.services.factory_status.report_builder import ReportBuilder
    print("   [OK] All modules imported successfully")
    
    # Test basic initialization
    print("\n2. Testing initialization...")
    builder = ReportBuilder()
    print("   [OK] Report builder initialized")
    
    # Test git commit parser
    print("\n3. Testing git commit parser...")
    parser = GitCommitParser()
    commits = parser.get_commits(1)  # Just last hour to be fast
    print(f"   [OK] Found {len(commits)} commits in last hour")
    
    # Test report generation with minimal time range
    print("\n4. Generating minimal report (1 hour)...")
    report = builder.build_report(hours=1)
    print(f"   [OK] Report generated: {report.report_id}")
    print(f"   [OK] Productivity Score: {report.executive_summary.productivity_score}/10")
    print(f"   [OK] Business Value Score: {report.executive_summary.business_value_score}/10")
    
    # Export summary
    print("\n5. Testing export...")
    summary = builder.export_summary(report)
    print(f"   [OK] Summary exported ({len(summary)} chars)")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] Basic validation passed!")
    print("\nThe AI Factory Status Report system is operational.")
    print("\nKey components verified:")
    print("- Git analysis modules")
    print("- Metrics calculation")  
    print("- Report generation")
    print("- Export functionality")
    
except Exception as e:
    print(f"\n[ERROR]: {e}")
    import traceback
    traceback.print_exc()
    print("\n[FAILED] Validation failed")
    sys.exit(1)