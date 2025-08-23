#!/usr/bin/env python3
"""
Claude Code Audit Analyzer - Spawns fresh Claude instances for code analysis
Provides intelligent remediation suggestions
"""

import subprocess
import json
import tempfile
import asyncio
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import shutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle


@dataclass
class AuditRequest:
    """Request for Claude audit analysis"""
    request_id: str
    category: str  # duplicate, legacy, complexity, naming
    context: Dict[str, Any]
    priority: str  # critical, high, medium, low
    timeout: int = 60


@dataclass
class AuditResponse:
    """Response from Claude analysis"""
    request_id: str
    analysis: str
    suggestions: List[str]
    can_auto_fix: bool
    fix_commands: Optional[List[str]] = None
    severity_assessment: str = "medium"
    business_impact: Optional[str] = None
    estimated_effort: Optional[str] = None


class ClaudeAuditCache:
    """Cache for Claude audit results"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(".git/claude-audit-cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=1)
    
    def get_key(self, request: AuditRequest) -> str:
        """Generate cache key for request"""
        context_str = json.dumps(request.context, sort_keys=True)
        return hashlib.sha256(
            f"{request.category}:{context_str}".encode()
        ).hexdigest()[:16]
    
    def get(self, request: AuditRequest) -> Optional[AuditResponse]:
        """Get cached response if available"""
        cache_file = self.cache_dir / f"{self.get_key(request)}.pkl"
        
        if cache_file.exists():
            # Check age
            age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if age < self.ttl:
                try:
                    with open(cache_file, 'rb') as f:
                        return pickle.load(f)
                except Exception:
                    pass
        return None
    
    def set(self, request: AuditRequest, response: AuditResponse):
        """Cache response"""
        cache_file = self.cache_dir / f"{self.get_key(request)}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(response, f)
        except Exception:
            pass
    
    def clear(self):
        """Clear old cache entries"""
        for cache_file in self.cache_dir.glob("*.pkl"):
            age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if age > self.ttl:
                cache_file.unlink(missing_ok=True)


class ClaudeAuditAnalyzer:
    """Manages Claude Code spawning for audit analysis"""
    
    def __init__(self, config: Optional[Any] = None):
        self.config = config
        self.cache = ClaudeAuditCache()
        self.recursion_marker = Path(".git/CLAUDE_AUDIT_IN_PROGRESS")
        self.max_parallel = 4
        
    def is_available(self) -> bool:
        """Check if Claude Code is available"""
        return shutil.which("claude") is not None
    
    def check_recursion(self) -> bool:
        """Check if we're already in a Claude audit"""
        if self.recursion_marker.exists():
            age = datetime.now() - datetime.fromtimestamp(
                self.recursion_marker.stat().st_mtime
            )
            if age > timedelta(minutes=10):
                self.recursion_marker.unlink()
                return False
            return True
        return False
    
    async def analyze_duplicate(self, duplicate_info: Dict[str, Any]) -> AuditResponse:
        """Analyze a duplicate with Claude"""
        request = AuditRequest(
            request_id=f"dup_{id(duplicate_info)}",
            category="duplicate",
            context=duplicate_info,
            priority=duplicate_info.get("severity", "medium")
        )
        
        return await self._analyze(request)
    
    async def analyze_legacy(self, legacy_info: Dict[str, Any]) -> AuditResponse:
        """Analyze legacy code with Claude"""
        request = AuditRequest(
            request_id=f"legacy_{id(legacy_info)}",
            category="legacy",
            context=legacy_info,
            priority=legacy_info.get("severity", "medium")
        )
        
        return await self._analyze(request)
    
    async def _analyze(self, request: AuditRequest) -> AuditResponse:
        """Core analysis with Claude"""
        # Check cache
        if cached := self.cache.get(request):
            return cached
        
        # Check recursion
        if self.check_recursion():
            return self._fallback_response(request)
        
        try:
            # Set recursion marker
            self.recursion_marker.touch()
            
            # Prepare context file
            context_file = self._prepare_context(request)
            
            # Build Claude prompt
            prompt = self._build_prompt(request)
            
            # Call Claude
            result = await self._call_claude(prompt, context_file, request.timeout)
            
            # Parse response
            response = self._parse_response(result, request)
            
            # Cache result
            self.cache.set(request, response)
            
            return response
            
        except Exception as e:
            print(f"Claude analysis error: {e}")
            return self._fallback_response(request)
        finally:
            self.recursion_marker.unlink(missing_ok=True)
    
    def _prepare_context(self, request: AuditRequest) -> Path:
        """Prepare context file for Claude"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            dir=Path.cwd()
        ) as f:
            json.dump({
                "category": request.category,
                "context": request.context,
                "priority": request.priority,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2, default=str)
            return Path(f.name)
    
    def _build_prompt(self, request: AuditRequest) -> str:
        """Build Claude prompt based on category"""
        prompts = {
            "duplicate": """Analyze the duplicate code in the context file.
Focus on:
1. Why this duplication is problematic
2. Business impact of leaving it
3. Specific refactoring steps
4. Estimated effort to fix
5. Whether it can be auto-fixed

Output JSON with: analysis, suggestions[], can_auto_fix, fix_commands[], severity_assessment, business_impact, estimated_effort""",
            
            "legacy": """Analyze the legacy code patterns in the context file.
Focus on:
1. Security and stability risks
2. Modern alternatives
3. Migration path
4. Priority for fixing
5. Automation possibilities

Output JSON with: analysis, suggestions[], can_auto_fix, fix_commands[], severity_assessment, business_impact, estimated_effort""",
            
            "complexity": """Analyze the code complexity issues in the context file.
Focus on:
1. Maintainability impact
2. Simplification strategies
3. Refactoring approach
4. Testing requirements
5. Risk assessment

Output JSON with: analysis, suggestions[], can_auto_fix, fix_commands[], severity_assessment, business_impact, estimated_effort"""
        }
        
        base_prompt = prompts.get(request.category, prompts["duplicate"])
        return f"{base_prompt}\n\nContext file: {request.context.get('file_path', 'context.json')}"
    
    async def _call_claude(self, prompt: str, context_file: Path, timeout: int) -> str:
        """Call Claude Code CLI"""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["claude", prompt],
                    cwd=Path.cwd(),
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
            )
            
            # Clean up context file
            context_file.unlink(missing_ok=True)
            
            if result.returncode == 0:
                return result.stdout
            else:
                return "{}"
                
        except subprocess.TimeoutExpired:
            context_file.unlink(missing_ok=True)
            return "{}"
        except Exception:
            context_file.unlink(missing_ok=True)
            return "{}"
    
    def _parse_response(self, output: str, request: AuditRequest) -> AuditResponse:
        """Parse Claude's JSON response"""
        try:
            # Extract JSON from output
            import re
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {}
            
            return AuditResponse(
                request_id=request.request_id,
                analysis=data.get("analysis", "Analysis unavailable"),
                suggestions=data.get("suggestions", []),
                can_auto_fix=data.get("can_auto_fix", False),
                fix_commands=data.get("fix_commands"),
                severity_assessment=data.get("severity_assessment", "medium"),
                business_impact=data.get("business_impact"),
                estimated_effort=data.get("estimated_effort")
            )
        except Exception:
            return self._fallback_response(request)
    
    def _fallback_response(self, request: AuditRequest) -> AuditResponse:
        """Generate fallback response when Claude unavailable"""
        fallbacks = {
            "duplicate": {
                "analysis": "Duplicate code detected. Manual review recommended.",
                "suggestions": [
                    "Extract common functionality to shared module",
                    "Create base class or mixin",
                    "Use composition pattern"
                ]
            },
            "legacy": {
                "analysis": "Legacy patterns detected. Modernization recommended.",
                "suggestions": [
                    "Update to current best practices",
                    "Replace deprecated APIs",
                    "Improve error handling"
                ]
            },
            "complexity": {
                "analysis": "High complexity detected. Refactoring recommended.",
                "suggestions": [
                    "Break into smaller functions",
                    "Reduce nesting levels",
                    "Extract complex conditions"
                ]
            }
        }
        
        fallback = fallbacks.get(request.category, fallbacks["duplicate"])
        
        return AuditResponse(
            request_id=request.request_id,
            analysis=fallback["analysis"],
            suggestions=fallback["suggestions"],
            can_auto_fix=False,
            severity_assessment=request.priority
        )
    
    async def analyze_batch(self, requests: List[AuditRequest]) -> List[AuditResponse]:
        """Analyze multiple requests in parallel"""
        tasks = []
        for request in requests:
            task = asyncio.create_task(self._analyze(request))
            tasks.append(task)
        
        # Limit parallelism
        results = []
        for i in range(0, len(tasks), self.max_parallel):
            batch = tasks[i:i + self.max_parallel]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
        
        return results
    
    def generate_remediation_plan(self, responses: List[AuditResponse]) -> str:
        """Generate comprehensive remediation plan"""
        plan = ["# Audit Remediation Plan\n"]
        
        # Group by severity
        by_severity = {}
        for response in responses:
            severity = response.severity_assessment
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(response)
        
        # Generate plan sections
        for severity in ["critical", "high", "medium", "low"]:
            if severity not in by_severity:
                continue
            
            plan.append(f"\n## {severity.upper()} Priority Items\n")
            
            for i, response in enumerate(by_severity[severity], 1):
                plan.append(f"### {i}. {response.request_id}")
                plan.append(f"\n**Analysis**: {response.analysis}")
                
                if response.business_impact:
                    plan.append(f"\n**Business Impact**: {response.business_impact}")
                
                if response.estimated_effort:
                    plan.append(f"\n**Estimated Effort**: {response.estimated_effort}")
                
                plan.append("\n**Suggestions**:")
                for suggestion in response.suggestions:
                    plan.append(f"- {suggestion}")
                
                if response.can_auto_fix and response.fix_commands:
                    plan.append("\n**Automated Fix Available**:")
                    plan.append("```bash")
                    for cmd in response.fix_commands:
                        plan.append(cmd)
                    plan.append("```")
                
                plan.append("")
        
        # Add summary
        total = len(responses)
        auto_fixable = len([r for r in responses if r.can_auto_fix])
        
        plan.append("\n## Summary\n")
        plan.append(f"- Total issues: {total}")
        plan.append(f"- Auto-fixable: {auto_fixable}")
        plan.append(f"- Manual fixes required: {total - auto_fixable}")
        
        return "\n".join(plan)


async def main():
    """Test the analyzer"""
    analyzer = ClaudeAuditAnalyzer()
    
    # Test duplicate analysis
    duplicate_context = {
        "file1": "app/services/user.py",
        "file2": "app/services/admin.py",
        "similarity": 0.92,
        "lines": 45,
        "code_sample": "def validate_user(...):\n    # Similar validation logic"
    }
    
    response = await analyzer.analyze_duplicate(duplicate_context)
    print("Duplicate Analysis:")
    print(f"  {response.analysis}")
    print(f"  Suggestions: {response.suggestions}")
    
    # Test legacy analysis
    legacy_context = {
        "file": "app/utils/helpers.py",
        "pattern": "relative imports",
        "occurrences": 12,
        "risk": "high"
    }
    
    response = await analyzer.analyze_legacy(legacy_context)
    print("\nLegacy Analysis:")
    print(f"  {response.analysis}")
    print(f"  Can auto-fix: {response.can_auto_fix}")


if __name__ == "__main__":
    asyncio.run(main())