from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Code Audit Orchestrator - Main entry point for comprehensive code auditing
Integrates duplicate detection, legacy analysis, and Claude remediation
"""

import sys
import asyncio
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import argparse

# Import our modules
from audit_config import AuditConfig, AuditLevel, get_default_config
from duplicate_detector import DuplicateDetector, analyze_changed_files
from claude_audit_analyzer import ClaudeAuditAnalyzer, AuditRequest, AuditResponse


class CodeAuditOrchestrator:
    """Main orchestrator for code auditing"""
    
    def __init__(self, config: Optional[AuditConfig] = None):
        self.config = config or get_default_config()
        self.detector = DuplicateDetector(
            threshold=self.config.flags.duplicate_threshold.value
        )
        self.analyzer = ClaudeAuditAnalyzer(config)
        self.audit_results = {
            "duplicates": [],
            "legacy": [],
            "complexity": [],
            "violations": []
        }
        self.should_block = False
        self.bypass_reason = None
    
    def check_bypass(self, commit_message: Optional[str] = None) -> bool:
        """Check if audit should be bypassed"""
        # Check environment
        if os.environ.get("BYPASS_AUDIT") == "1":
            self.bypass_reason = "Environment bypass flag set"
            return True
        
        # Check CI/CD
        if any(os.environ.get(var) for var in ["CI", "GITHUB_ACTIONS"]):
            if not self.config.flags.enforce_in_ci:
                self.bypass_reason = "CI/CD environment"
                return True
        
        # Check commit message
        if commit_message and self.config.can_bypass(commit_message):
            self.bypass_reason = f"Bypass keyword in commit message"
            return True
        
        return False
    
    async def run_audit(self, 
                       files: Optional[List[Path]] = None,
                       check_all: bool = False) -> Dict[str, Any]:
        """Run comprehensive audit"""
        print(" SEARCH:  Starting code audit...")
        
        # Determine files to check
        if files:
            target_files = files
        elif check_all:
            target_files = list(Path.cwd().rglob("*.py"))
        else:
            # Get changed files
            target_files = self._get_changed_files()
        
        if not target_files:
            print("[U+2139][U+FE0F] No files to audit")
            return self.audit_results
        
        print(f"[U+1F4C1] Auditing {len(target_files)} files...")
        
        # Run duplicate detection
        if self.config.flags.duplicate_detection:
            await self._detect_duplicates(target_files)
        
        # Run legacy detection
        if self.config.flags.legacy_code_detection:
            await self._detect_legacy(target_files)
        
        # Run Claude analysis if enabled
        if self.config.flags.claude_analysis and self.analyzer.is_available():
            await self._run_claude_analysis()
        
        # Generate report
        report = self._generate_report()
        
        # Determine if we should block
        self._determine_blocking()
        
        # Save report
        if self.config.flags.generate_report:
            self._save_report(report)
        
        return {
            "results": self.audit_results,
            "should_block": self.should_block,
            "report": report,
            "stats": self._get_statistics()
        }
    
    def _get_changed_files(self) -> List[Path]:
        """Get list of changed files"""
        try:
            # Get staged files
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True
            )
            
            files = []
            for line in result.stdout.strip().split('\n'):
                if line and line.endswith('.py'):
                    path = Path(line)
                    if path.exists():
                        files.append(path)
            
            return files
            
        except Exception as e:
            print(f"Error getting changed files: {e}")
            return []
    
    async def _detect_duplicates(self, files: List[Path]):
        """Run duplicate detection"""
        print("   CYCLE:  Checking for duplicates...")
        
        # Analyze files
        for file_path in files:
            self.detector.analyze_file(file_path)
        
        # Find duplicates
        duplicates = self.detector.find_duplicates()
        
        # Process results
        for dup in duplicates:
            level = self.config.get_effective_level("duplicate")
            
            result = {
                "type": "duplicate",
                "severity": dup.severity,
                "level": level.value,
                "original": f"{dup.original.file_path}:{dup.original.start_line}",
                "duplicate": f"{dup.duplicate.file_path}:{dup.duplicate.start_line}",
                "similarity": dup.similarity,
                "lines": dup.original.line_count,
                "suggestion": dup.suggested_action
            }
            
            self.audit_results["duplicates"].append(result)
            
            # Check if should block
            if self.config.should_block(level) and dup.severity in ["critical", "high"]:
                self.should_block = True
        
        print(f"    Found {len(duplicates)} duplicate pairs")
    
    async def _detect_legacy(self, files: List[Path]):
        """Run legacy pattern detection"""
        print("  [U+1F570][U+FE0F] Checking for legacy patterns...")
        
        # Legacy patterns are detected during file analysis
        legacy_patterns = self.detector.legacy_patterns
        
        # Process results
        for pattern in legacy_patterns:
            level = self.config.get_effective_level("legacy")
            
            result = {
                "type": "legacy",
                "severity": pattern.severity,
                "level": level.value,
                "pattern": pattern.pattern,
                "description": pattern.description,
                "file": str(pattern.file_path),
                "line": pattern.line_number,
                "replacement": pattern.replacement
            }
            
            self.audit_results["legacy"].append(result)
            
            # Check if should block
            if self.config.should_block(level) and pattern.severity == "critical":
                self.should_block = True
        
        print(f"    Found {len(legacy_patterns)} legacy patterns")
    
    async def _run_claude_analysis(self):
        """Run Claude analysis on findings"""
        print("  [U+1F916] Running Claude analysis...")
        
        requests = []
        
        # Prepare requests for critical issues
        for dup in self.audit_results["duplicates"]:
            if dup["severity"] in ["critical", "high"]:
                requests.append(AuditRequest(
                    request_id=f"dup_{len(requests)}",
                    category="duplicate",
                    context=dup,
                    priority=dup["severity"]
                ))
        
        for legacy in self.audit_results["legacy"]:
            if legacy["severity"] in ["critical", "high"]:
                requests.append(AuditRequest(
                    request_id=f"legacy_{len(requests)}",
                    category="legacy",
                    context=legacy,
                    priority=legacy["severity"]
                ))
        
        if not requests:
            print("    No critical issues to analyze")
            return
        
        # Limit requests to avoid overwhelming
        max_requests = 10
        if len(requests) > max_requests:
            print(f"    Analyzing top {max_requests} issues...")
            requests = requests[:max_requests]
        
        # Run analysis
        try:
            responses = await self.analyzer.analyze_batch(requests)
            
            # Add Claude insights to results
            for response in responses:
                self.audit_results["violations"].append({
                    "id": response.request_id,
                    "analysis": response.analysis,
                    "suggestions": response.suggestions,
                    "can_auto_fix": response.can_auto_fix,
                    "business_impact": response.business_impact,
                    "effort": response.estimated_effort
                })
            
            print(f"    Analyzed {len(responses)} issues")
            
        except Exception as e:
            print(f"     WARNING: [U+FE0F] Claude analysis error: {e}")
    
    def _determine_blocking(self):
        """Determine if commit should be blocked"""
        # Already determined during detection
        if self.should_block:
            # Check for hard block
            for category in ["duplicate", "legacy"]:
                level = self.config.get_effective_level(category)
                if level == AuditLevel.HARD_BLOCK:
                    self.should_block = True
                    return
                elif level == AuditLevel.SOFT_BLOCK:
                    # Allow override for soft blocks
                    if not self.config.flags.allow_user_override:
                        self.should_block = True
                        return
    
    def _get_statistics(self) -> Dict[str, Any]:
        """Get audit statistics"""
        return {
            "total_duplicates": len(self.audit_results["duplicates"]),
            "critical_duplicates": len([
                d for d in self.audit_results["duplicates"] 
                if d["severity"] == "critical"
            ]),
            "total_legacy": len(self.audit_results["legacy"]),
            "critical_legacy": len([
                l for l in self.audit_results["legacy"] 
                if l["severity"] == "critical"
            ]),
            "violations_analyzed": len(self.audit_results["violations"]),
            "should_block": self.should_block
        }
    
    def _generate_report(self) -> str:
        """Generate comprehensive audit report"""
        report = ["#  SEARCH:  Code Audit Report\n"]
        report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        stats = self._get_statistics()
        
        # Summary
        report.append("## Summary")
        report.append(f"- Total Duplicates: {stats['total_duplicates']}")
        report.append(f"- Critical Duplicates: {stats['critical_duplicates']}")
        report.append(f"- Legacy Patterns: {stats['total_legacy']}")
        report.append(f"- Critical Legacy: {stats['critical_legacy']}")
        
        if self.should_block:
            report.append("\n[U+26D4] **COMMIT BLOCKED** - Critical issues found")
        elif self.bypass_reason:
            report.append(f"\n WARNING: [U+FE0F] **AUDIT BYPASSED** - {self.bypass_reason}")
        else:
            report.append("\n PASS:  **COMMIT ALLOWED** - No blocking issues")
        
        # Duplicates section
        if self.audit_results["duplicates"]:
            report.append("\n##  CYCLE:  Duplicates Found\n")
            
            for i, dup in enumerate(self.audit_results["duplicates"][:10], 1):
                severity_emoji = {
                    "critical": "[U+1F534]",
                    "high": "[U+1F7E0]", 
                    "medium": "[U+1F7E1]",
                    "low": "[U+1F7E2]"
                }.get(dup["severity"], "[U+26AA]")
                
                report.append(f"### {severity_emoji} Duplicate #{i}")
                report.append(f"- **Similarity**: {dup['similarity']:.1%}")
                report.append(f"- **Files**: `{dup['original']}` [U+2194][U+FE0F] `{dup['duplicate']}`")
                report.append(f"- **Lines**: {dup['lines']}")
                report.append(f"- **Action**: {dup['suggestion']}")
                report.append("")
        
        # Legacy section
        if self.audit_results["legacy"]:
            report.append("\n## [U+1F570][U+FE0F] Legacy Patterns Found\n")
            
            # Group by severity
            by_severity = {}
            for pattern in self.audit_results["legacy"]:
                sev = pattern["severity"]
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append(pattern)
            
            for severity in ["critical", "high", "medium", "low"]:
                if severity in by_severity:
                    report.append(f"### {severity.upper()}")
                    for p in by_severity[severity][:5]:
                        report.append(f"- {p['description']} at `{p['file']}:{p['line']}`")
                        if p.get('replacement'):
                            report.append(f"   ->  {p['replacement']}")
                    report.append("")
        
        # Claude Analysis section
        if self.audit_results["violations"]:
            report.append("\n## [U+1F916] Claude Analysis\n")
            
            for v in self.audit_results["violations"]:
                report.append(f"### {v['id']}")
                report.append(f"**Analysis**: {v['analysis']}")
                
                if v.get('business_impact'):
                    report.append(f"**Impact**: {v['business_impact']}")
                
                if v.get('suggestions'):
                    report.append("**Suggestions**:")
                    for s in v['suggestions']:
                        report.append(f"- {s}")
                
                if v.get('can_auto_fix'):
                    report.append("[U+2728] *Auto-fix available*")
                
                report.append("")
        
        # Configuration section
        report.append("\n## [U+2699][U+FE0F] Configuration")
        report.append(f"- Duplicate Detection: {self.config.flags.duplicate_detection}")
        report.append(f"- Legacy Detection: {self.config.flags.legacy_code_detection}")
        report.append(f"- Claude Analysis: {self.config.flags.claude_analysis}")
        report.append(f"- Duplicate Threshold: {self.config.flags.duplicate_threshold.value}")
        report.append(f"- Duplicate Level: {self.config.flags.duplicate_level.value}")
        report.append(f"- Legacy Level: {self.config.flags.legacy_level.value}")
        
        return "\n".join(report)
    
    def _save_report(self, report: str):
        """Save report to file"""
        report_dir = Path(".git/audit-reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"audit_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n[U+1F4C4] Report saved to: {report_file}")


async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Code Audit Orchestrator")
    parser.add_argument("--all", action="store_true", help="Audit all files")
    parser.add_argument("--files", nargs="+", help="Specific files to audit")
    parser.add_argument("--bypass", action="store_true", help="Bypass audit")
    parser.add_argument("--config", help="Config file path")
    parser.add_argument("--level", choices=["off", "notify", "warn", "soft_block", "hard_block", "enforce"],
                       help="Override audit level")
    parser.add_argument("--no-claude", action="store_true", help="Disable Claude analysis")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    
    args = parser.parse_args()
    
    # Load config
    config = AuditConfig(Path(args.config)) if args.config else get_default_config()
    
    # Apply overrides
    if args.level:
        config.flags.duplicate_level = AuditLevel(args.level)
        config.flags.legacy_level = AuditLevel(args.level)
    
    if args.no_claude:
        config.flags.claude_analysis = False
    
    if args.bypass:
        os.environ["BYPASS_AUDIT"] = "1"
    
    # Create orchestrator
    orchestrator = CodeAuditOrchestrator(config)
    
    # Determine files
    files = None
    if args.files:
        files = [Path(f) for f in args.files]
    
    # Run audit
    results = await orchestrator.run_audit(files=files, check_all=args.all)
    
    # Output results
    if args.json:
        print(json.dumps(results["stats"], indent=2))
    else:
        print(results["report"])
    
    # Exit code
    if results["should_block"]:
        print("\n FAIL:  Audit failed - commit blocked")
        sys.exit(1)
    else:
        print("\n PASS:  Audit passed")
        sys.exit(0)


if __name__ == "__main__":
    import os
    asyncio.run(main())
