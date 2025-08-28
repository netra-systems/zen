"""Factory Status Reporter for SPEC Compliance Scoring."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from netra_backend.app.core.exceptions_base import (
    ValidationError as ValidationException,
)
from netra_backend.app.services.factory_status.report_analyzer import ReportAnalyzer
from netra_backend.app.services.factory_status.spec_compliance_scorer import (
    ComplianceScore,
    SpecViolation,
)
from netra_backend.app.services.factory_status.violation_analyzer import (
    ViolationAnalyzer,
)


class FactoryStatusReporter:
    """Integrates compliance scoring with factory status reporting."""
    
    def __init__(self, project_root: Path):
        """Initialize factory status reporter."""
        self.project_root = project_root
        self.spec_dir = project_root / "SPEC"
        self._init_analyzers()
        self._init_cache()
    
    def _init_analyzers(self) -> None:
        """Initialize analyzer components."""
        self.scorer = self._create_scorer()
        self.violation_analyzer = ViolationAnalyzer()
        self.report_analyzer = ReportAnalyzer()
    
    def _init_cache(self) -> None:
        """Initialize cache storage."""
        self.metrics_cache: Dict[str, Any] = {}
        self.last_update: Optional[datetime] = None
    
    def _create_scorer(self):
        """Create spec compliance scorer."""
        from netra_backend.app.services.factory_status.spec_compliance_scorer import (
            SpecComplianceScorer,
        )
        return SpecComplianceScorer(self.spec_dir)

    async def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report."""
        module_scores = await self._get_module_scores()
        report = await self._build_report_structure(module_scores)
        self._cache_report(report)
        
        return report
    
    async def _get_module_scores(self) -> Dict[str, ComplianceScore]:
        """Get scores for all modules."""
        app_path = self.project_root / "app"
        return await self.scorer.score_all_modules(app_path)
    
    async def _build_report_structure(self, module_scores: Dict[str, ComplianceScore]) -> Dict[str, Any]:
        """Build the main report structure."""
        overall_score = self._calculate_overall_score(module_scores)
        violations = self._collect_violations(module_scores)
        ranked_modules = self.report_analyzer.rank_modules(module_scores)
        
        return await self._create_report_dict(module_scores, overall_score, violations, ranked_modules)
    
    async def _create_report_dict(self, module_scores: Dict[str, ComplianceScore], 
                                 overall_score: float, violations: List[SpecViolation],
                                 ranked_modules: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Create the final report dictionary."""
        base_data = self.report_analyzer.create_report_structure(overall_score, module_scores, ranked_modules)
        analysis_data = await self._create_analysis_data(violations)
        
        return {**base_data, **analysis_data}
    
    async def _create_analysis_data(self, violations: List[SpecViolation]) -> Dict[str, Any]:
        """Create analysis data for report."""
        return {
            "violations_summary": self.violation_analyzer.summarize_violations(violations),
            "critical_violations": self.violation_analyzer.get_critical_violations(violations),
            "trend_analysis": await self.report_analyzer.analyze_trends(),
            "orchestration_alignment": await self.report_analyzer.check_orchestration_alignment()
        }
    
    def _cache_report(self, report: Dict[str, Any]) -> None:
        """Cache the report with timestamp."""
        self.metrics_cache = report
        self.last_update = datetime.now(timezone.utc)

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

    async def get_cached_report(self) -> Optional[Dict[str, Any]]:
        """Get cached report if fresh."""
        if not self._has_valid_cache():
            return None
        
        return self.metrics_cache
    
    def _has_valid_cache(self) -> bool:
        """Check if cache is valid and not expired."""
        if not self.last_update:
            return False
        
        return not self._is_cache_expired()
    
    def _is_cache_expired(self) -> bool:
        """Check if cache is expired."""
        age = datetime.now(timezone.utc) - self.last_update
        return age > timedelta(hours=1)

    async def trigger_claude_review(self, modules: List[str]) -> Dict[str, Any]:
        """Trigger Claude CLI review for specific modules (dev only)."""
        if not self._is_dev_environment():
            raise ValidationException("Claude CLI review only available in development")
        
        return await self._process_claude_modules(modules)
    
    async def _process_claude_modules(self, modules: List[str]) -> Dict[str, Any]:
        """Process modules for Claude review."""
        results = {}
        
        for module_name in modules:
            self._add_module_result(results, module_name, await self._score_single_module(module_name))
        
        return results
    
    def _add_module_result(self, results: Dict[str, Any], module_name: str, 
                          module_result: Optional[Dict[str, Any]]) -> None:
        """Add module result to results dict if valid."""
        if module_result:
            results[module_name] = module_result
    
    async def _score_single_module(self, module_name: str) -> Optional[Dict[str, Any]]:
        """Score a single module if it exists."""
        module_path = self.project_root / "app" / module_name
        if not module_path.exists():
            return None
        
        score = await self.scorer.score_module(module_path)
        return self.report_analyzer.score_to_dict(score)

    def _is_dev_environment(self) -> bool:
        """Check if running in development environment."""
        from netra_backend.app.core.configuration import unified_config_manager
        config = unified_config_manager.get_config()
        env = getattr(config, 'environment', 'staging')  # Default to staging for safety
        return env in ["development", "dev", "local"]