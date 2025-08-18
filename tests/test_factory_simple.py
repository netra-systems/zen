"""Simple test for AI Factory Status Report - validates basic functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all factory status modules can be imported."""
    from app.services.factory_status.git_commit_parser import GitCommitParser
    from app.services.factory_status.git_diff_analyzer import GitDiffAnalyzer
    from app.services.factory_status.git_branch_tracker import GitBranchTracker
    from app.services.factory_status.report_builder import ReportBuilder
    assert GitCommitParser
    assert GitDiffAnalyzer
    assert GitBranchTracker
    assert ReportBuilder


def test_report_builder_initialization():
    """Test that ReportBuilder can be initialized."""
    from app.services.factory_status.report_builder import ReportBuilder
    builder = ReportBuilder()
    assert builder is not None


def test_git_commit_parser():
    """Test git commit parser basic functionality."""
    from app.services.factory_status.git_commit_parser import GitCommitParser
    parser = GitCommitParser()
    commits = parser.get_commits(1)  # Just last hour to be fast
    assert isinstance(commits, list)


def test_report_generation():
    """Test minimal report generation."""
    from app.services.factory_status.report_builder import ReportBuilder
    builder = ReportBuilder()
    report = builder.build_report(hours=1)
    assert report is not None
    assert hasattr(report, 'report_id')
    assert hasattr(report, 'executive_summary')


def test_export_functionality():
    """Test report export functionality."""
    from app.services.factory_status.report_builder import ReportBuilder
    builder = ReportBuilder()
    report = builder.build_report(hours=1)
    summary = builder.export_summary(report)
    assert isinstance(summary, str)
    assert len(summary) > 0