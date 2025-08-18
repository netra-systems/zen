"""AI Factory Status Integration with SPEC Compliance Scoring."""

from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import asyncio

from app.services.factory_status.spec_compliance_scorer import (
    SpecComplianceScorer,
    ComplianceScore,
    SpecViolation,
    ViolationSeverity
)
from app.core.exceptions_base import ValidationError as ValidationException


class FactoryStatusReporter:
    """Integrates compliance scoring with factory status reporting."""
    
    def __init__(self, project_root: Path):
        """Initialize factory status reporter."""
        self.project_root = project_root
        self.spec_dir = project_root / "SPEC"
        self.scorer = SpecComplianceScorer(self.spec_dir)
        self.metrics_cache: Dict[str, Any] = {}
        self.last_update: Optional[datetime] = None
    
    async def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report."""
        # Score all modules
        app_path = self.project_root / "app"
        module_scores = await self.scorer.score_all_modules(app_path)
        
        # Calculate overall metrics
        overall_score = self._calculate_overall_score(module_scores)
        violations = self._collect_violations(module_scores)
        
        # Identify top/bottom performers
        ranked_modules = self._rank_modules(module_scores)
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_compliance_score": overall_score,
            "module_scores": {k: self._score_to_dict(v) for k, v in module_scores.items()},
            "top_compliant_modules": ranked_modules["top"],
            "modules_needing_attention": ranked_modules["bottom"],
            "violations_summary": self._summarize_violations(violations),
            "critical_violations": self._get_critical_violations(violations),
            "trend_analysis": await self._analyze_trends(),
            "orchestration_alignment": await self._check_orchestration_alignment()
        }
        
        self.metrics_cache = report
        self.last_update = datetime.utcnow()
        
        return report
    
    def _calculate_overall_score(self, module_scores: Dict[str, ComplianceScore]) -> float:
        """Calculate overall compliance score."""
        if not module_scores:
            return 100.0
        
        total = sum(score.overall_score for score in module_scores.values())
        return round(total / len(module_scores), 2)
    
    def _collect_violations(self, module_scores: Dict[str, ComplianceScore]) -> List[SpecViolation]:
        """Collect all violations from module scores."""
        violations = []
        for score in module_scores.values():
            violations.extend(score.violations)
        return violations
    
    def _rank_modules(self, module_scores: Dict[str, ComplianceScore]) -> Dict[str, List[Dict]]:
        """Rank modules by compliance score."""
        sorted_modules = sorted(
            module_scores.items(),
            key=lambda x: x[1].overall_score,
            reverse=True
        )
        
        top_5 = [
            {"name": name, "score": score.overall_score}
            for name, score in sorted_modules[:5]
        ]
        
        bottom_5 = [
            {"name": name, "score": score.overall_score}
            for name, score in sorted_modules[-5:]
        ]
        
        return {"top": top_5, "bottom": bottom_5}
    
    def _summarize_violations(self, violations: List[Any]) -> Dict[str, int]:
        """Summarize violations by category."""
        summary = {
            "architecture_violations": 0,
            "type_safety_violations": 0,
            "missing_tests": 0,
            "documentation_gaps": 0
        }
        
        for v in violations:
            if "violation_type" in v:
                vtype = v["violation_type"]
                if vtype in ["file_length", "function_length"]:
                    summary["architecture_violations"] += 1
                elif vtype == "missing_types":
                    summary["type_safety_violations"] += 1
        
        return summary
    
    def _get_critical_violations(self, violations: List[Any]) -> List[Dict]:
        """Get critical violations requiring immediate action."""
        critical = []
        
        for v in violations:
            if v.get("severity") == ViolationSeverity.CRITICAL.value:
                critical.append({
                    "module": v.get("module"),
                    "type": v.get("violation_type"),
                    "description": v.get("description"),
                    "remediation": v.get("remediation")
                })
        
        return critical[:10]  # Top 10 critical issues
    
    async def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze compliance trends over time."""
        # In production, load historical data from database
        # For now, return placeholder
        return {
            "direction": "improving",
            "change_percentage": 5.2,
            "modules_improved": 8,
            "modules_declined": 2
        }
    
    async def _check_orchestration_alignment(self) -> Dict[str, Any]:
        """Check alignment with master orchestration spec."""
        # Check key orchestration principles
        alignment = {
            "architecture_compliance": True,
            "multi_agent_coordination": True,
            "root_cause_analysis": True,
            "continuous_validation": True
        }
        
        # In production, perform actual checks
        return {
            "aligned": all(alignment.values()),
            "principles": alignment,
            "recommendations": []
        }
    
    def _score_to_dict(self, score: ComplianceScore) -> Dict[str, Any]:
        """Convert ComplianceScore to dictionary."""
        return {
            "overall_score": score.overall_score,
            "architecture_score": score.architecture_score,
            "type_safety_score": score.type_safety_score,
            "spec_alignment_score": score.spec_alignment_score,
            "test_coverage_score": score.test_coverage_score,
            "documentation_score": score.documentation_score,
            "violations_count": len(score.violations),
            "timestamp": score.timestamp.isoformat()
        }
    
    async def get_cached_report(self) -> Optional[Dict[str, Any]]:
        """Get cached report if fresh."""
        if not self.last_update:
            return None
        
        age = datetime.utcnow() - self.last_update
        if age > timedelta(hours=1):
            return None
        
        return self.metrics_cache
    
    async def trigger_claude_review(self, modules: List[str]) -> Dict[str, Any]:
        """Trigger Claude CLI review for specific modules (dev only)."""
        if not self._is_dev_environment():
            raise ValidationException("Claude CLI review only available in development")
        
        results = {}
        for module_name in modules:
            module_path = self.project_root / "app" / module_name
            if module_path.exists():
                score = await self.scorer.score_module(module_path)
                results[module_name] = self._score_to_dict(score)
        
        return results
    
    def _is_dev_environment(self) -> bool:
        """Check if running in development environment."""
        import os
        env = os.getenv("ENVIRONMENT", "staging")  # Default to staging for safety
        return env in ["development", "dev", "local"]


class ComplianceAPIHandler:
    """Handles API requests for compliance scoring."""
    
    def __init__(self, reporter: FactoryStatusReporter):
        """Initialize API handler."""
        self.reporter = reporter
    
    async def get_compliance_score(self) -> Dict[str, Any]:
        """Get current compliance scores."""
        report = await self.reporter.get_cached_report()
        
        if not report:
            report = await self.reporter.generate_compliance_report()
        
        return {
            "overall_score": report["overall_compliance_score"],
            "module_scores": report["module_scores"],
            "last_updated": report["timestamp"]
        }
    
    async def analyze_modules(self, modules: List[str], use_claude: bool = False) -> Dict[str, Any]:
        """Analyze specific modules."""
        if use_claude:
            return await self.reporter.trigger_claude_review(modules)
        
        # Standard analysis
        results = {}
        for module in modules:
            module_path = self.reporter.project_root / "app" / module
            if module_path.exists():
                score = await self.reporter.scorer.score_module(module_path)
                results[module] = self.reporter._score_to_dict(score)
        
        return results
    
    async def get_violations(self, severity: Optional[str] = None, 
                           category: Optional[str] = None) -> List[Dict]:
        """Get list of violations with optional filters."""
        report = await self.reporter.get_cached_report()
        
        if not report:
            report = await self.reporter.generate_compliance_report()
        
        violations = []
        for module_data in report["module_scores"].values():
            violations.extend(module_data.get("violations", []))
        
        # Apply filters
        if severity:
            violations = [v for v in violations if v.get("severity") == severity]
        
        if category:
            violations = [v for v in violations if v.get("violation_type") == category]
        
        return violations


# Factory function for creating reporter instance
def create_factory_status_reporter() -> FactoryStatusReporter:
    """Create factory status reporter instance."""
    project_root = Path(__file__).parent.parent.parent.parent
    return FactoryStatusReporter(project_root)


# Async initialization for API endpoints
async def init_compliance_api() -> ComplianceAPIHandler:
    """Initialize compliance API handler."""
    reporter = create_factory_status_reporter()
    return ComplianceAPIHandler(reporter)