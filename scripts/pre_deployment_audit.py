#!/usr/bin/env python3
"""
Pre-Deployment Audit Script
Implements SPEC/pre_deployment_audit.xml to catch LLM coding errors before deployment
Focuses on RECENT changes and NEW issues, not pre-existing violations
"""

import os
import sys
import json
import re
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import xml.etree.ElementTree as ET

@dataclass
class AuditIssue:
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str
    description: str
    location: str
    commit: str
    impact: str
    remediation: str
    
@dataclass
class AuditReport:
    commit_range: str
    risk_score: int
    recommendation: str  # BLOCK, PROCEED_WITH_CAUTION, SAFE
    critical_issues: List[AuditIssue] = field(default_factory=list)
    high_issues: List[AuditIssue] = field(default_factory=list)
    medium_issues: List[AuditIssue] = field(default_factory=list)
    suspicious_patterns: Dict[str, List[str]] = field(default_factory=dict)
    incomplete_work: List[Dict] = field(default_factory=list)
    test_coverage_impact: Dict = field(default_factory=dict)

class PreDeploymentAuditor:
    def __init__(self, commit_count: int = 10, since: Optional[str] = None, branch: str = "main"):
        self.commit_count = commit_count
        self.since = since
        self.base_branch = branch
        self.repo_root = Path.cwd()
        self.report = AuditReport(commit_range="", risk_score=0, recommendation="")
        self.claude_md_rules = self._load_claude_md_rules()
        
    def _load_claude_md_rules(self) -> Dict:
        """Extract key rules from CLAUDE.md"""
        rules = {
            "ssot_violations": [],
            "import_patterns": [],
            "naming_violations": [],
            "incomplete_indicators": []
        }
        
        claude_md = self.repo_root / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text()
            
            # Extract SSOT patterns
            if "Single Source of Truth" in content:
                rules["ssot_violations"] = ["_v2.", "_new.", "_temp.", "_old."]
            
            # Import rules
            if "NEVER use relative imports" in content:
                rules["import_patterns"] = [r"from \.\. import", r"from \. import"]
            
            # Incomplete work indicators
            rules["incomplete_indicators"] = [
                "TODO", "FIXME", "HACK", "XXX", "NotImplementedError",
                "@skip", "@pytest.mark.skip", "pass  # TODO"
            ]
            
        return rules
    
    def run_audit(self) -> AuditReport:
        """Execute the full audit process"""
        print("[AUDIT] Starting Pre-Deployment Audit...")
        
        # Step 1: Collect recent changes
        commits = self._get_recent_commits()
        changed_files = self._get_changed_files()
        
        # Step 2: Categorize changes
        categorized = self._categorize_changes(changed_files)
        
        # Step 3: Deep analysis
        self._analyze_breaking_changes(changed_files)
        self._analyze_incomplete_work(changed_files)
        self._analyze_claude_violations(changed_files)
        self._analyze_test_coverage(changed_files)
        self._analyze_config_changes(changed_files)
        
        # Step 4: Calculate risk score
        self._calculate_risk_score()
        
        # Step 5: Generate recommendation
        self._generate_recommendation()
        
        return self.report
    
    def _get_recent_commits(self) -> List[str]:
        """Get list of recent commits"""
        if self.since:
            cmd = f"git log --oneline --since='{self.since}'"
        else:
            cmd = f"git log --oneline -n {self.commit_count}"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        commits = result.stdout.strip().split('\n')
        
        if commits:
            first = commits[-1].split()[0]
            last = commits[0].split()[0]
            self.report.commit_range = f"{first}..{last}"
        
        return commits
    
    def _get_changed_files(self) -> Dict[str, Dict]:
        """Get all changed files with their diffs"""
        cmd = f"git diff --name-status {self.base_branch}...HEAD"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        changed_files = {}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    status, filepath = parts[0], parts[1]
                    changed_files[filepath] = {
                        'status': status,
                        'diff': self._get_file_diff(filepath)
                    }
        
        return changed_files
    
    def _get_file_diff(self, filepath: str) -> str:
        """Get diff for a specific file"""
        cmd = f"git diff {self.base_branch}...HEAD -- {filepath}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        return result.stdout
    
    def _categorize_changes(self, changed_files: Dict) -> Dict[str, List[str]]:
        """Categorize files by risk level"""
        categories = {
            'critical_path': [],
            'configuration': [],
            'tests': [],
            'deployment': [],
            'authentication': [],
            'database': []
        }
        
        for filepath in changed_files.keys():
            path = Path(filepath)
            
            # Critical path files
            if any(p in str(path) for p in ['auth_service', 'authentication', 'authorization']):
                categories['authentication'].append(filepath)
            elif any(p in str(path) for p in ['database.py', 'models/', 'migrations/']):
                categories['database'].append(filepath)
            elif any(p in str(path) for p in ['config.py', 'secrets.py', '.env']):
                categories['configuration'].append(filepath)
            elif any(p in str(path) for p in ['docker', '.github/workflows', 'deploy']):
                categories['deployment'].append(filepath)
            elif 'test' in str(path):
                categories['tests'].append(filepath)
            elif any(p in str(path) for p in ['api/', 'core/', 'services/']):
                categories['critical_path'].append(filepath)
        
        return categories
    
    def _analyze_breaking_changes(self, changed_files: Dict):
        """Detect breaking changes in APIs and interfaces"""
        # Only check actual source code files
        code_extensions = ('.py', '.ts', '.tsx', '.js', '.jsx')
        
        breaking_patterns = [
            (r'-\s+def\s+(\w+)\(', 'Removed function'),
            (r'-\s+class\s+(\w+)', 'Removed class'),
            (r'def\s+\w+\([^)]*\).*?->', 'Changed function signature'),
            (r'-\s+(\w+_URL|DATABASE_\w+|API_\w+)\s*=', 'Changed critical config'),
        ]
        
        for filepath, file_data in changed_files.items():
            # Skip non-code files
            if not filepath.endswith(code_extensions):
                continue
            diff = file_data.get('diff', '')
            if not diff:
                continue
            for pattern, issue_type in breaking_patterns:
                matches = re.findall(pattern, diff, re.MULTILINE)
                if matches:
                    issue = AuditIssue(
                        severity="CRITICAL",
                        category="Breaking Change",
                        description=f"{issue_type}: {matches[0] if matches else 'Multiple'}",
                        location=filepath,
                        commit=self._get_file_commit(filepath),
                        impact="May break existing functionality",
                        remediation="Add migration path or restore compatibility"
                    )
                    self.report.critical_issues.append(issue)
    
    def _analyze_incomplete_work(self, changed_files: Dict):
        """Detect incomplete implementations"""
        # Only check code files
        code_extensions = ('.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.go', '.rs')
        
        for filepath, file_data in changed_files.items():
            # Skip non-code files
            if not filepath.endswith(code_extensions):
                continue
            diff = file_data.get('diff', '')
            if not diff:
                continue
            
            # Check for incomplete indicators
            for indicator in self.claude_md_rules['incomplete_indicators']:
                if f"+.*{indicator}" in diff:
                    self.report.incomplete_work.append({
                        'file': filepath,
                        'indicator': indicator,
                        'type': 'Incomplete implementation'
                    })
                    
                    issue = AuditIssue(
                        severity="HIGH",
                        category="Incomplete Work",
                        description=f"Contains {indicator}",
                        location=filepath,
                        commit=self._get_file_commit(filepath),
                        impact="Feature may not work as expected",
                        remediation="Complete implementation before deployment"
                    )
                    self.report.high_issues.append(issue)
    
    def _analyze_claude_violations(self, changed_files: Dict):
        """Check for violations of Claude.md principles"""
        # Only check code files
        code_extensions = ('.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.go', '.rs')
        
        for filepath, file_data in changed_files.items():
            # Skip non-code files for import checks
            if not filepath.endswith(code_extensions):
                # Still check filenames for SSOT violations
                pass
            diff = file_data.get('diff', '')
            if not diff:
                continue
            
            # Check for SSOT violations
            for pattern in self.claude_md_rules['ssot_violations']:
                if pattern in filepath:
                    issue = AuditIssue(
                        severity="HIGH",
                        category="SSOT Violation",
                        description=f"File naming indicates duplicate: {pattern}",
                        location=filepath,
                        commit=self._get_file_commit(filepath),
                        impact="Technical debt and maintenance burden",
                        remediation="Consolidate to single implementation"
                    )
                    self.report.high_issues.append(issue)
            
            # Check for relative imports (only in Python files)
            if filepath.endswith('.py'):
                for pattern in self.claude_md_rules['import_patterns']:
                    if re.search(pattern, diff):
                        issue = AuditIssue(
                            severity="HIGH",
                            category="Import Violation",
                            description="Uses relative imports",
                            location=filepath,
                            commit=self._get_file_commit(filepath),
                            impact="Violates absolute import requirement",
                            remediation="Convert to absolute imports"
                        )
                        self.report.high_issues.append(issue)
    
    def _analyze_test_coverage(self, changed_files: Dict):
        """Analyze test coverage impact"""
        test_stats = {
            'removed_tests': 0,
            'modified_tests': 0,
            'files_without_tests': [],
            'disabled_tests': 0
        }
        
        for filepath, file_data in changed_files.items():
            diff = file_data.get('diff', '')
            if not diff:
                continue
            
            # Count removed tests
            removed_tests = len(re.findall(r'-\s+def\s+test_', diff))
            test_stats['removed_tests'] += removed_tests
            
            # Check for disabled tests
            disabled = len(re.findall(r'\+.*@(skip|pytest\.mark\.skip)', diff))
            test_stats['disabled_tests'] += disabled
            
            # Track files without corresponding tests
            if not filepath.startswith('test') and not self._has_test_file(filepath):
                test_stats['files_without_tests'].append(filepath)
        
        self.report.test_coverage_impact = test_stats
        
        if test_stats['removed_tests'] > 0 or test_stats['disabled_tests'] > 0:
            issue = AuditIssue(
                severity="HIGH",
                category="Test Degradation",
                description=f"Removed {test_stats['removed_tests']} tests, disabled {test_stats['disabled_tests']}",
                location="Multiple test files",
                commit="Multiple",
                impact="Reduced test coverage",
                remediation="Restore or replace removed tests"
            )
            self.report.high_issues.append(issue)
    
    def _analyze_config_changes(self, changed_files: Dict):
        """Analyze configuration and deployment changes"""
        config_files = ['docker-compose', '.env', 'config.py', 'secrets.py']
        
        for filepath, file_data in changed_files.items():
            if any(cf in filepath for cf in config_files):
                # Check for hardcoded values
                diff = file_data.get('diff', '')
                if not diff:
                    continue
                hardcoded = re.findall(r'\+.*(localhost|127\.0\.0\.1|:\d{4})', diff)
                
                if hardcoded:
                    issue = AuditIssue(
                        severity="MEDIUM",
                        category="Configuration Risk",
                        description="Hardcoded values detected",
                        location=filepath,
                        commit=self._get_file_commit(filepath),
                        impact="Environment-specific code",
                        remediation="Use environment variables"
                    )
                    self.report.medium_issues.append(issue)
    
    def _get_file_commit(self, filepath: str) -> str:
        """Get the last commit that modified a file"""
        cmd = f"git log -1 --format=%h -- {filepath}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        return result.stdout.strip()
    
    def _has_test_file(self, filepath: str) -> bool:
        """Check if a file has corresponding tests"""
        path = Path(filepath)
        test_name = f"test_{path.stem}.py"
        
        # Look for test file in various locations
        test_locations = [
            path.parent / test_name,
            Path("tests") / test_name,
            Path("tests") / path.parent.name / test_name
        ]
        
        return any(loc.exists() for loc in test_locations)
    
    def _calculate_risk_score(self) -> int:
        """Calculate overall risk score (0-100)"""
        score = 0
        
        # Critical issues have highest weight
        score += len(self.report.critical_issues) * 25
        
        # High issues
        score += len(self.report.high_issues) * 10
        
        # Medium issues
        score += len(self.report.medium_issues) * 3
        
        # Test coverage impact
        test_impact = self.report.test_coverage_impact
        if test_impact:
            score += test_impact.get('removed_tests', 0) * 2
            score += test_impact.get('disabled_tests', 0) * 2
            score += len(test_impact.get('files_without_tests', [])) * 1
        
        # Cap at 100
        self.report.risk_score = min(score, 100)
        return self.report.risk_score
    
    def _generate_recommendation(self):
        """Generate deployment recommendation based on findings"""
        if self.report.critical_issues:
            self.report.recommendation = "BLOCK"
        elif self.report.risk_score >= 70:
            self.report.recommendation = "BLOCK"
        elif self.report.risk_score >= 40:
            self.report.recommendation = "PROCEED_WITH_CAUTION"
        else:
            self.report.recommendation = "SAFE"
    
    def generate_markdown_report(self) -> str:
        """Generate markdown report"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# Pre-Deployment Audit Report
Generated: {now}

## Executive Summary
- **Commit Range**: {self.report.commit_range}
- **Risk Score**: {self.report.risk_score}/100
- **Recommendation**: **{self.report.recommendation}**
- **Critical Issues**: {len(self.report.critical_issues)}
- **High Priority Issues**: {len(self.report.high_issues)}

"""
        
        # Critical Issues
        if self.report.critical_issues:
            report += "## 🔴 CRITICAL BLOCKERS\n\n"
            for i, issue in enumerate(self.report.critical_issues, 1):
                report += f"""### {i}. {issue.category}: {issue.description}
- **Location**: {issue.location}
- **Commit**: {issue.commit}
- **Impact**: {issue.impact}
- **Required Fix**: {issue.remediation}

"""
        
        # High Risk Issues
        if self.report.high_issues:
            report += "## ⚠️ HIGH RISK ISSUES\n\n"
            for issue in self.report.high_issues:
                report += f"""### {issue.category}
- **Description**: {issue.description}
- **Location**: {issue.location}
- **Action Required**: {issue.remediation}

"""
        
        # Test Coverage Impact
        if self.report.test_coverage_impact:
            test_stats = self.report.test_coverage_impact
            report += "## 📊 Test Coverage Impact\n\n"
            report += f"- Removed Tests: {test_stats.get('removed_tests', 0)}\n"
            report += f"- Disabled Tests: {test_stats.get('disabled_tests', 0)}\n"
            report += f"- Files Without Tests: {len(test_stats.get('files_without_tests', []))}\n\n"
        
        # Incomplete Work
        if self.report.incomplete_work:
            report += "## 🚧 Incomplete Work Detected\n\n"
            report += "| File | Indicator | Type |\n"
            report += "|------|-----------|------|\n"
            for item in self.report.incomplete_work:
                report += f"| {item['file']} | {item['indicator']} | {item['type']} |\n"
            report += "\n"
        
        # Recommendations
        if self.report.recommendation == "BLOCK":
            report += """## ❌ Deployment Blocked

**Critical issues must be resolved before deployment.**

1. Fix all CRITICAL issues listed above
2. Complete all incomplete implementations
3. Run full test suite after fixes
4. Re-run this audit to verify resolution
"""
        elif self.report.recommendation == "PROCEED_WITH_CAUTION":
            report += """## ⚠️ Proceed with Caution

**Deployment possible but risky. Consider:**

1. Reviewing all HIGH risk issues
2. Having rollback plan ready
3. Monitoring closely after deployment
4. Scheduling fixes for next sprint
"""
        else:
            report += """## ✅ Safe to Deploy

No critical issues detected. Standard deployment procedures apply.
"""
        
        return report
    
    def save_report(self, output_path: str = "PRE_DEPLOYMENT_AUDIT_REPORT.md"):
        """Save report to file"""
        report = self.generate_markdown_report()
        Path(output_path).write_text(report, encoding='utf-8')
        print(f"[SAVED] Report saved to {output_path}")
        
        # Also save JSON version
        json_path = output_path.replace('.md', '.json')
        with open(json_path, 'w') as f:
            json.dump({
                'commit_range': self.report.commit_range,
                'risk_score': self.report.risk_score,
                'recommendation': self.report.recommendation,
                'critical_count': len(self.report.critical_issues),
                'high_count': len(self.report.high_issues),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Pre-Deployment Audit - Catch LLM coding errors')
    parser.add_argument('--commits', type=int, default=10, help='Number of recent commits to audit')
    parser.add_argument('--since', type=str, help='Time range (e.g., "3 days ago")')
    parser.add_argument('--branch', type=str, default='main', help='Base branch to compare against')
    parser.add_argument('--output', type=str, default='PRE_DEPLOYMENT_AUDIT_REPORT.md', help='Output file')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--strict', action='store_true', help='Fail with exit code 1 if issues found')
    
    args = parser.parse_args()
    
    # Run audit
    auditor = PreDeploymentAuditor(
        commit_count=args.commits,
        since=args.since,
        branch=args.branch
    )
    
    report = auditor.run_audit()
    
    # Save report
    auditor.save_report(args.output)
    
    # Display summary
    print(f"\n{'='*60}")
    print(f"AUDIT COMPLETE")
    print(f"{'='*60}")
    print(f"Risk Score: {report.risk_score}/100")
    print(f"Recommendation: {report.recommendation}")
    print(f"Critical Issues: {len(report.critical_issues)}")
    print(f"High Priority Issues: {len(report.high_issues)}")
    print(f"{'='*60}\n")
    
    # Exit with error code if strict mode and issues found
    if args.strict and report.recommendation == "BLOCK":
        print("[BLOCKED] Deployment blocked due to critical issues")
        sys.exit(1)
    
    return 0

if __name__ == "__main__":
    main()