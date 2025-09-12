#!/usr/bin/env python
"""Team Updates Sync - Synchronous version for testing."""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


def get_top_changed_files(since_date, limit=10):
    """Get top changed files."""
    try:
        cmd = [
            "git", "diff", "--stat", 
            f"HEAD@{{{since_date}}}", "HEAD"
        ]
        result = subprocess.run(
            cmd, capture_output=True, 
            text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')
        files = []
        for line in lines[:-1]:  # Skip summary
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    file = parts[0].strip()
                    changes = parts[1].strip()
                    files.append((file, changes))
        return files[:limit]
    except Exception:
        return []


def generate_simple_report(time_frame="last_day"):
    """Generate a simple team update report."""
    
    # Calculate time range
    end_time = datetime.now()
    hours_map = {
        "last_hour": 1, "last_5_hours": 5,
        "last_day": 24, "last_week": 168
    }
    hours = hours_map.get(time_frame, 24)
    start_time = end_time - timedelta(hours=hours)
    
    report_lines = [
        f"#  CHART:  Team Update Report",
        f"Generated: {end_time.strftime('%Y-%m-%d %H:%M')}",
        f"Time Frame: {time_frame.replace('_', ' ').title()}",
        "",
        "## [U+1F4CB] Executive Summary"
    ]
    
    # Get recent git commits
    since = start_time.strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--oneline"],
            capture_output=True, text=True, timeout=5
        )
        commits = result.stdout.strip().split('\n')
        commit_count = len([c for c in commits if c])
        report_lines.append(f"- **Commits**: {commit_count} changes made")
    except Exception as e:
        report_lines.append(f"- **Commits**: Unable to fetch (error: {e})")
    
    # Check test reports
    test_reports_dir = Path.cwd() / "test_reports"
    if test_reports_dir.exists():
        report_files = list(test_reports_dir.glob("*.md"))
        report_lines.append(f"- **Test Reports**: {len(report_files)} reports available")
        
        # Check for unified report
        unified = test_reports_dir / "unified_report.md"
        if unified.exists():
            content = unified.read_text(encoding='utf-8', errors='ignore')[:500]
            if "PASSED" in content:
                report_lines.append("- **Test Status**:  PASS:  Tests passing")
            elif "FAILED" in content:
                report_lines.append("- **Test Status**:  FAIL:  Some tests failing")
    
    # Check compliance
    try:
        result = subprocess.run(
            ["python", "scripts/check_architecture_compliance.py"],
            capture_output=True, text=True, timeout=10
        )
        if "compliant" in result.stdout.lower():
            report_lines.append("- **Compliance**:  PASS:  Architecture compliant")
        else:
            report_lines.append("- **Compliance**:  WARNING: [U+FE0F] Some violations found")
    except Exception:
        report_lines.append("- **Compliance**: Unable to check")
    
    # Check documentation
    docs_dir = Path.cwd() / "docs"
    spec_dir = Path.cwd() / "SPEC"
    
    doc_count = len(list(docs_dir.glob("*.md"))) if docs_dir.exists() else 0
    spec_count = len(list(spec_dir.glob("*.xml"))) if spec_dir.exists() else 0
    
    report_lines.append(f"- **Documentation**: {doc_count} docs, {spec_count} specs")
    
    # Get top changed files
    report_lines.extend([
        "",
        "## [U+1F4C1] Top 10 Files to Review",
        "*Most changed files in this period:*",
        ""
    ])
    
    top_files = get_top_changed_files(since, 10)
    if top_files:
        for i, (file, changes) in enumerate(top_files, 1):
            # Create relative path for linking
            file_path = Path(file)
            if file_path.exists():
                rel_path = file.replace('\\', '/')
                report_lines.append(
                    f"{i}. [`{file}`](./../{rel_path}) - {changes}"
                )
            else:
                report_lines.append(f"{i}. `{file}` - {changes}")
    else:
        report_lines.append("*No file changes detected*")
    
    # Add sections
    report_lines.extend([
        "",
        "## [U+2728] Recent Activity",
        f"Team has been active in the {time_frame.replace('_', ' ')}.",
        "",
        "## [U+1F680] How to Generate This Report",
        "",
        "### Option 1: Direct CLI Command",
        "```bash",
        "python scripts/team_updates_sync.py last_day",
        "# Or choose: last_hour, last_5_hours, last_week",
        "```",
        "",
        "### Option 2: Via Claude",
        "Simply ask Claude:",
        "> \"Generate a team update report for the last day\"",
        "",
        "Or be specific:",
        "> \"Read team_updates.xml and run it for last_week\"",
        "",
        "---",
        f"*Generated: {end_time.strftime('%Y-%m-%d %H:%M:%S')}*",
        f"*Report saved to: team_updates/{end_time.strftime('%Y-%m-%d_%H-%M')}_{time_frame}.md*"
    ])
    
    return "\n".join(report_lines)


def main():
    """Generate and save report."""
    import sys
    
    time_frame = sys.argv[1] if len(sys.argv) > 1 else "last_day"
    
    # Generate report
    report = generate_simple_report(time_frame)
    
    # Save to file
    reports_dir = Path.cwd() / "team_updates"
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_path = reports_dir / f"{timestamp}_{time_frame}.md"
    
    output_path.write_text(report, encoding='utf-8')
    
    print(f"[SUCCESS] Team update report saved to: {output_path}")
    print(f"\n[PREVIEW]\n{'-' * 50}")
    print(report[:500].encode('ascii', 'replace').decode('ascii'))
    print(f"\n{'=' * 50}")
    print(f"View full report: {output_path}")


if __name__ == "__main__":
    main()