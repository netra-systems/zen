#!/usr/bin/env python3
"""
Test Restoration Helper Script
Issue #837 - Post-repair restoration assistance

This script helps identify and restore placeholder test files with proper content.
"""

import os
import json
from pathlib import Path
from typing import List, Dict
import subprocess


class TestRestorationHelper:
    def __init__(self):
        self.placeholder_files = []
        self.backup_files = []
        self.restoration_plan = []

    def find_placeholder_files(self) -> List[Path]:
        """Find all placeholder test files that need restoration."""
        placeholders = []

        # Search for placeholder files
        result = subprocess.run([
            'grep', '-r', '-l',
            'Placeholder test file - original had syntax errors',
            'tests/', 'auth_service/tests/', 'netra_backend/tests/'
        ], capture_output=True, text=True, cwd='.')

        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    placeholders.append(Path(line))

        return placeholders

    def find_backup_files(self) -> List[Path]:
        """Find backup files that might contain original content."""
        backups = []

        # Look for backup files
        for pattern in ['*.backup_*', '*.syntax_error_backup', '*_backup_*']:
            backups.extend(Path('.').glob(f'**/{pattern}'))

        return backups

    def check_git_history(self, file_path: Path) -> bool:
        """Check if file has git history that might be recoverable."""
        try:
            result = subprocess.run([
                'git', 'log', '--oneline', str(file_path)
            ], capture_output=True, text=True, cwd='.')

            return result.returncode == 0 and result.stdout.strip()
        except:
            return False

    def analyze_placeholder(self, file_path: Path) -> Dict:
        """Analyze a placeholder file to understand what needs restoration."""
        info = {
            "file": str(file_path),
            "has_git_history": self.check_git_history(file_path),
            "potential_backups": [],
            "priority": "unknown",
            "category": "unknown"
        }

        # Determine priority based on file path
        if "mission_critical" in str(file_path):
            info["priority"] = "high"
        elif "e2e" in str(file_path) or "integration" in str(file_path):
            info["priority"] = "medium"
        elif "unit" in str(file_path):
            info["priority"] = "low"

        # Determine category
        if "websocket" in str(file_path):
            info["category"] = "websocket"
        elif "auth" in str(file_path):
            info["category"] = "authentication"
        elif "agent" in str(file_path):
            info["category"] = "agent"
        elif "database" in str(file_path) or "db" in str(file_path):
            info["category"] = "database"

        # Look for potential backup files
        backup_candidates = [
            f"{file_path}.backup_*",
            f"{file_path.stem}_backup*",
            f"*{file_path.stem}*.backup*"
        ]

        for pattern in backup_candidates:
            matches = list(Path('.').glob(f'**/{pattern}'))
            info["potential_backups"].extend([str(m) for m in matches])

        return info

    def generate_restoration_plan(self) -> Dict:
        """Generate a plan for restoring placeholder files."""
        placeholder_files = self.find_placeholder_files()

        plan = {
            "total_placeholders": len(placeholder_files),
            "by_priority": {"high": [], "medium": [], "low": []},
            "by_category": {},
            "restoration_steps": []
        }

        for file_path in placeholder_files:
            info = self.analyze_placeholder(file_path)

            # Add to priority groups
            priority = info["priority"]
            if priority in plan["by_priority"]:
                plan["by_priority"][priority].append(info)

            # Add to category groups
            category = info["category"]
            if category not in plan["by_category"]:
                plan["by_category"][category] = []
            plan["by_category"][category].append(info)

        # Generate restoration steps
        plan["restoration_steps"] = [
            {
                "step": 1,
                "description": "Restore high-priority mission-critical tests",
                "files": plan["by_priority"]["high"],
                "method": "Check git history, analyze backups, or rewrite from specs"
            },
            {
                "step": 2,
                "description": "Restore medium-priority integration/e2e tests",
                "files": plan["by_priority"]["medium"],
                "method": "Focus on critical business flows first"
            },
            {
                "step": 3,
                "description": "Restore low-priority unit tests",
                "files": plan["by_priority"]["low"],
                "method": "Batch restoration, focus on SSOT compliance"
            }
        ]

        return plan

    def create_restoration_report(self) -> str:
        """Create a detailed restoration report."""
        plan = self.generate_restoration_plan()

        report = [
            "# Test File Restoration Plan",
            "",
            f"**Total placeholder files requiring restoration:** {plan['total_placeholders']}",
            "",
            "## Priority Breakdown",
            f"- **High Priority (Mission Critical):** {len(plan['by_priority']['high'])} files",
            f"- **Medium Priority (Integration/E2E):** {len(plan['by_priority']['medium'])} files",
            f"- **Low Priority (Unit Tests):** {len(plan['by_priority']['low'])} files",
            "",
            "## Category Breakdown"
        ]

        for category, files in plan["by_category"].items():
            if files:
                report.append(f"- **{category.title()}:** {len(files)} files")

        report.extend([
            "",
            "## Restoration Steps",
            ""
        ])

        for step in plan["restoration_steps"]:
            report.extend([
                f"### Step {step['step']}: {step['description']}",
                f"**Files:** {len(step['files'])}",
                f"**Method:** {step['method']}",
                ""
            ])

            if step['files']:
                report.append("**File List:**")
                for file_info in step['files'][:10]:  # Show first 10
                    git_status = "✓" if file_info["has_git_history"] else "✗"
                    backups = len(file_info["potential_backups"])
                    report.append(f"- {file_info['file']} (Git: {git_status}, Backups: {backups})")

                if len(step['files']) > 10:
                    report.append(f"- ... and {len(step['files']) - 10} more files")
                report.append("")

        return "\n".join(report)

    def save_restoration_plan(self, filename: str = "test_restoration_plan.json"):
        """Save the restoration plan to a JSON file."""
        plan = self.generate_restoration_plan()

        with open(filename, 'w') as f:
            json.dump(plan, f, indent=2)

        print(f"Restoration plan saved to {filename}")
        return plan


def main():
    """Main execution function."""
    print("Analyzing placeholder test files for restoration...")
    print("=" * 60)

    helper = TestRestorationHelper()

    # Generate and save restoration plan
    plan = helper.save_restoration_plan()

    # Create detailed report
    report = helper.create_restoration_report()

    with open("TEST_RESTORATION_PLAN.md", 'w') as f:
        f.write(report)

    print(f"Found {plan['total_placeholders']} placeholder files requiring restoration")
    print(f"High priority: {len(plan['by_priority']['high'])} files")
    print(f"Medium priority: {len(plan['by_priority']['medium'])} files")
    print(f"Low priority: {len(plan['by_priority']['low'])} files")
    print()
    print("Reports generated:")
    print("- test_restoration_plan.json (machine-readable)")
    print("- TEST_RESTORATION_PLAN.md (human-readable)")

    return 0


if __name__ == "__main__":
    exit(main())