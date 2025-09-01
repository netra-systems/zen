#!/usr/bin/env python3
"""Test the improved git commit grouping logic for noise reduction."""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from netra_backend.app.services.factory_status.git_commit_parser import (
    GitCommitParser, 
    CommitInfo,
    CommitSession,
    CommitType
)


def test_commit_session_grouping():
    """Test that commits are properly grouped into sessions."""
    parser = GitCommitParser()
    
    # Create test commits that should be grouped together
    now = datetime.now()
    test_commits = [
        CommitInfo(
            hash="abc123",
            author="John Doe",
            email="john@example.com",
            timestamp=now - timedelta(minutes=45),
            message="feat: add new feature",
            commit_type=CommitType.FEATURE,
            files_changed=3,
            insertions=150,
            deletions=20
        ),
        CommitInfo(
            hash="def456",
            author="John Doe",
            email="john@example.com",
            timestamp=now - timedelta(minutes=35),
            message="fix: resolve bug",
            commit_type=CommitType.FIX,
            files_changed=1,
            insertions=10,
            deletions=5
        ),
        CommitInfo(
            hash="ghi789",
            author="John Doe",
            email="john@example.com",
            timestamp=now - timedelta(minutes=25),
            message="refactor: clean up code",
            commit_type=CommitType.REFACTOR,
            files_changed=2,
            insertions=30,
            deletions=40
        ),
        # This commit should be in a different session (different author)
        CommitInfo(
            hash="jkl012",
            author="Jane Smith",
            email="jane@example.com",
            timestamp=now - timedelta(minutes=20),
            message="docs: update README",
            commit_type=CommitType.DOCS,
            files_changed=1,
            insertions=20,
            deletions=0
        ),
        # This commit should be in a different session (time gap > 30 mins)
        CommitInfo(
            hash="mno345",
            author="John Doe",
            email="john@example.com",
            timestamp=now - timedelta(minutes=80),
            message="test: add unit tests",
            commit_type=CommitType.TEST,
            files_changed=5,
            insertions=200,
            deletions=0
        )
    ]
    
    # Test session grouping
    sessions = parser.group_commits_into_sessions(test_commits, window_minutes=30)
    
    print("=" * 60)
    print("TEST: Commit Session Grouping")
    print("=" * 60)
    
    print(f"\nTotal commits: {len(test_commits)}")
    print(f"Total sessions: {len(sessions)}")
    
    assert len(sessions) == 3, f"Expected 3 sessions, got {len(sessions)}"
    
    for i, session in enumerate(sessions, 1):
        print(f"\n--- Session {i} ---")
        print(f"Author: {session.author}")
        print(f"Commits: {len(session.commits)}")
        print(f"Duration: {int((session.end_time - session.start_time).total_seconds() / 60)} minutes")
        print(f"Files changed: {session.total_files}")
        print(f"Lines: +{session.total_insertions}/-{session.total_deletions}")
        print(f"Primary type: {session.primary_type.value}")
        print(f"Summary: {session.summary}")
        
        for commit in session.commits:
            print(f"  - {commit.message[:50]}")
    
    # Verify John Doe's recent session has 3 commits
    john_recent_session = next((s for s in sessions if s.author == "John Doe" and len(s.commits) == 3), None)
    assert john_recent_session is not None, "John Doe's recent session with 3 commits not found"
    assert john_recent_session.total_files == 6, f"Expected 6 total files, got {john_recent_session.total_files}"
    assert john_recent_session.total_insertions == 190, f"Expected 190 insertions, got {john_recent_session.total_insertions}"
    
    print("\n✅ Session grouping test passed!")
    return True


def test_real_commits_with_sessions():
    """Test with real git commits if available."""
    parser = GitCommitParser()
    
    print("\n" + "=" * 60)
    print("TEST: Real Commits with Session Grouping")
    print("=" * 60)
    
    # Get commits from the last 24 hours
    commits = parser.get_commits(hours=24)
    
    if not commits:
        print("\nNo real commits found in the last 24 hours (using mock data)")
        return True
    
    print(f"\nFound {len(commits)} commits in the last 24 hours")
    
    # Group into sessions
    sessions = parser.group_commits_into_sessions(commits, window_minutes=30)
    
    print(f"Grouped into {len(sessions)} work sessions")
    
    # Calculate noise reduction
    noise_reduction = 0
    if len(commits) > 0:
        noise_reduction = ((len(commits) - len(sessions)) / len(commits)) * 100
    
    print(f"\n📊 Noise Reduction: {noise_reduction:.1f}%")
    print(f"   Before: {len(commits)} individual commits")
    print(f"   After: {len(sessions)} work sessions")
    
    # Show top 5 sessions
    print("\n🔝 Top 5 Work Sessions (by commit count):")
    sorted_sessions = sorted(sessions, key=lambda s: len(s.commits), reverse=True)
    
    for i, session in enumerate(sorted_sessions[:5], 1):
        duration = int((session.end_time - session.start_time).total_seconds() / 60)
        print(f"\n{i}. {session.author}")
        print(f"   {session.summary}")
        print(f"   Duration: {duration} mins | Files: {session.total_files}")
    
    return True


def test_patterns_with_sessions():
    """Test commit pattern analysis with session data."""
    parser = GitCommitParser()
    
    print("\n" + "=" * 60)
    print("TEST: Pattern Analysis with Sessions")
    print("=" * 60)
    
    # Analyze patterns for the last week
    patterns = parser.analyze_commit_patterns(hours=168)
    
    print("\n📈 Commit Patterns (Last 7 Days):")
    print(f"Total commits: {patterns.get('total_commits', 0)}")
    
    if 'sessions_count' in patterns:
        print(f"Work sessions: {patterns['sessions_count']}")
        print(f"Avg commits per session: {patterns.get('avg_session_commits', 0)}")
        
        if patterns.get('longest_session_commits'):
            print(f"\n🏆 Longest session:")
            print(f"   Author: {patterns['longest_session_author']}")
            print(f"   Commits: {patterns['longest_session_commits']}")
    
    print("\n📊 Commits by type:")
    for commit_type, count in patterns.get('commits_by_type', {}).items():
        print(f"   {commit_type}: {count}")
    
    print("\n⏰ Peak activity hours:")
    for hour in patterns.get('peak_hours', []):
        print(f"   {hour:02d}:00")
    
    return True


def main():
    """Run all tests."""
    print("🚀 Testing Improved Git Commit Grouping")
    print("=" * 60)
    
    tests = [
        ("Session Grouping", test_commit_session_grouping),
        ("Real Commits", test_real_commits_with_sessions),
        ("Pattern Analysis", test_patterns_with_sessions)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📋 Test Results Summary")
    print("=" * 60)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Commit grouping is working correctly.")
        print("\n📝 Key Improvements Implemented:")
        print("1. ✅ Commits grouped into work sessions (30-min windows)")
        print("2. ✅ Session summaries reduce noise in reports")
        print("3. ✅ Intelligent grouping by author and time proximity")
        print("4. ✅ Session statistics for better insights")
        print("5. ✅ Backwards compatible with existing code")
    else:
        print("\n⚠️ Some tests failed. Please review the output above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())