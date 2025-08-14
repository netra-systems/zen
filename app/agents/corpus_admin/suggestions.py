"""
Configuration Suggestion Engine

Provides intelligent configuration suggestions for corpus generation.
All functions maintain 8-line limit with single responsibility.
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from app.logging_config import central_logger
from app.schemas.corpus import WorkloadType, GenerationParameters

logger = central_logger.get_logger(__name__)


class SuggestionCategory(str, Enum):
    """Categories of configuration suggestions"""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    COST = "cost"
    DOMAIN_SPECIFIC = "domain_specific"
    WORKLOAD_OPTIMIZED = "workload_optimized"


class ConfigurationSuggestion(BaseModel):
    """Model for configuration suggestions"""
    parameter: str
    suggested_value: Any
    reason: str
    impact: str
    category: SuggestionCategory
    priority: int = Field(ge=1, le=5)


class OptimizationProfile(BaseModel):
    """Profile for optimization preferences"""
    focus: str  # "performance", "quality", "balanced"
    domain: Optional[str] = None
    workload_type: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)


class ConfigurationSuggestionEngine:
    """Provides intelligent configuration suggestions"""
    
    def __init__(self):
        """Initialize suggestion engine with optimization rules"""
        self.optimization_rules = self._initialize_optimization_rules()
        self.domain_profiles = self._initialize_domain_profiles()
        self.workload_optimizations = self._initialize_workload_optimizations()
        self.parameter_dependencies = self._initialize_parameter_dependencies()
    
    def _initialize_optimization_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize optimization rules for different focuses"""
        return {
            "performance": {
                "batch_size": {"value": 256, "impact": "Higher throughput"},
                "concurrency": {"value": 20, "impact": "Parallel processing"},
                "compression": {"value": "lz4", "impact": "Fast compression"}
            },
            "quality": {
                "error_rate": {"value": 0.001, "impact": "High accuracy"},
                "validation": {"value": True, "impact": "Data integrity"},
                "sampling_rate": {"value": 1.0, "impact": "Complete data"}
            },
            "balanced": {
                "batch_size": {"value": 128, "impact": "Balanced load"},
                "error_rate": {"value": 0.01, "impact": "Acceptable accuracy"},
                "concurrency": {"value": 10, "impact": "Moderate parallelism"}
            }
        }
    
    def _initialize_domain_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Initialize domain-specific configuration profiles"""
        return {
            "fintech": {
                "precision": "high",
                "audit_logging": True,
                "encryption": "AES-256",
                "compliance": ["PCI-DSS", "SOX"]
            },
            "healthcare": {
                "privacy": "HIPAA",
                "anonymization": True,
                "retention": "7y",
                "validation": "strict"
            },
            "ecommerce": {
                "scalability": "elastic",
                "cache_ttl": 300,
                "real_time": True,
                "analytics": "enabled"
            }
        }
    
    def _initialize_workload_optimizations(self) -> Dict[str, Dict[str, Any]]:
        """Initialize workload-specific optimizations"""
        return {
            "machine_learning": {
                "gpu_enabled": True,
                "tensor_format": True,
                "shuffle": True,
                "augmentation": "auto"
            },
            "web_services": {
                "rate_limiting": True,
                "circuit_breaker": True,
                "timeout": 30,
                "retry_policy": "exponential"
            },
            "data_processing": {
                "streaming": True,
                "checkpointing": True,
                "exactly_once": True,
                "windowing": "sliding"
            }
        }
    
    def _initialize_parameter_dependencies(self) -> Dict[str, List[str]]:
        """Initialize parameter dependencies"""
        return {
            "batch_size": ["memory_limit", "concurrency"],
            "concurrency": ["cpu_cores", "memory_limit"],
            "compression": ["storage_type", "performance_mode"],
            "encryption": ["compliance", "performance_mode"]
        }
    
    async def analyze_user_intent(self, query: str, context: Dict[str, Any]) -> OptimizationProfile:
        """Analyze user intent to determine optimization profile"""
        profile = OptimizationProfile(focus="balanced")
        profile = self._extract_focus_from_query(profile, query.lower())
        profile = self._apply_context_to_profile(profile, context)
        return profile
    
    def _extract_focus_from_query(self, profile: OptimizationProfile, query: str) -> OptimizationProfile:
        """Extract optimization focus from query"""
        if any(word in query for word in ["fast", "speed", "performance", "quick"]):
            profile.focus = "performance"
        elif any(word in query for word in ["accurate", "quality", "precise", "reliable"]):
            profile.focus = "quality"
        elif any(word in query for word in ["cost", "efficient", "optimize", "balanced"]):
            profile.focus = "balanced"
        return profile
    
    def _apply_context_to_profile(self, profile: OptimizationProfile, context: Dict) -> OptimizationProfile:
        """Apply context information to optimization profile"""
        if "domain" in context:
            profile.domain = context["domain"]
        if "workload_type" in context:
            profile.workload_type = context["workload_type"]
        if "constraints" in context:
            profile.constraints = context["constraints"]
        return profile
    
    async def suggest_parameters(self, profile: OptimizationProfile) -> List[ConfigurationSuggestion]:
        """Generate parameter suggestions based on profile"""
        suggestions = []
        suggestions.extend(await self._get_focus_suggestions(profile.focus))
        suggestions.extend(await self._get_domain_suggestions(profile.domain))
        suggestions.extend(await self._get_workload_suggestions(profile.workload_type))
        return self._prioritize_suggestions(suggestions)
    
    async def _get_focus_suggestions(self, focus: str) -> List[ConfigurationSuggestion]:
        """Get suggestions based on optimization focus"""
        suggestions = []
        if focus in self.optimization_rules:
            rules = self.optimization_rules[focus]
            for param, config in rules.items():
                suggestions.append(self._create_suggestion(param, config, SuggestionCategory.PERFORMANCE))
        return suggestions
    
    async def _get_domain_suggestions(self, domain: Optional[str]) -> List[ConfigurationSuggestion]:
        """Get domain-specific suggestions"""
        suggestions = []
        if domain and domain in self.domain_profiles:
            profile = self.domain_profiles[domain]
            for param, value in profile.items():
                suggestions.append(self._create_domain_suggestion(param, value))
        return suggestions
    
    async def _get_workload_suggestions(self, workload: Optional[str]) -> List[ConfigurationSuggestion]:
        """Get workload-specific suggestions"""
        suggestions = []
        if workload and workload in self.workload_optimizations:
            optimizations = self.workload_optimizations[workload]
            for param, value in optimizations.items():
                suggestions.append(self._create_workload_suggestion(param, value))
        return suggestions
    
    def _create_suggestion(self, param: str, config: Dict, category: SuggestionCategory) -> ConfigurationSuggestion:
        """Create a configuration suggestion"""
        return ConfigurationSuggestion(
            parameter=param,
            suggested_value=config.get("value"),
            reason=f"Optimized for {category.value}",
            impact=config.get("impact", "Performance improvement"),
            category=category,
            priority=3
        )
    
    def _create_domain_suggestion(self, param: str, value: Any) -> ConfigurationSuggestion:
        """Create domain-specific suggestion"""
        return ConfigurationSuggestion(
            parameter=param,
            suggested_value=value,
            reason="Domain best practice",
            impact="Compliance and optimization",
            category=SuggestionCategory.DOMAIN_SPECIFIC,
            priority=4
        )
    
    def _create_workload_suggestion(self, param: str, value: Any) -> ConfigurationSuggestion:
        """Create workload-specific suggestion"""
        return ConfigurationSuggestion(
            parameter=param,
            suggested_value=value,
            reason="Workload optimization",
            impact="Improved workload performance",
            category=SuggestionCategory.WORKLOAD_OPTIMIZED,
            priority=4
        )
    
    def _prioritize_suggestions(self, suggestions: List[ConfigurationSuggestion]) -> List[ConfigurationSuggestion]:
        """Prioritize suggestions by importance"""
        return sorted(suggestions, key=lambda s: s.priority, reverse=True)
    
    async def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration for completeness and conflicts"""
        errors = []
        errors.extend(self._check_required_parameters(config))
        errors.extend(self._check_parameter_conflicts(config))
        errors.extend(self._check_value_ranges(config))
        return len(errors) == 0, errors
    
    def _check_required_parameters(self, config: Dict) -> List[str]:
        """Check for missing required parameters"""
        required = ["workload_type", "record_count"]
        missing = [p for p in required if p not in config]
        return [f"Missing required parameter: {p}" for p in missing]
    
    def _check_parameter_conflicts(self, config: Dict) -> List[str]:
        """Check for conflicting parameter values"""
        errors = []
        if config.get("streaming") and config.get("batch_size", 0) > 1000:
            errors.append("Large batch size conflicts with streaming mode")
        if config.get("gpu_enabled") and config.get("cpu_only"):
            errors.append("GPU and CPU-only modes are mutually exclusive")
        return errors
    
    def _check_value_ranges(self, config: Dict) -> List[str]:
        """Check if values are within acceptable ranges"""
        errors = []
        if "record_count" in config and config["record_count"] > 10000000:
            errors.append("Record count exceeds maximum limit of 10M")
        if "concurrency" in config and config["concurrency"] > 100:
            errors.append("Concurrency exceeds recommended limit of 100")
        return errors
    
    async def optimize_for_domain(self, config: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """Optimize configuration for specific domain"""
        optimized = config.copy()
        if domain in self.domain_profiles:
            optimized = self._merge_domain_settings(optimized, self.domain_profiles[domain])
        optimized = await self._apply_domain_rules(optimized, domain)
        return optimized
    
    def _merge_domain_settings(self, config: Dict, domain_settings: Dict) -> Dict[str, Any]:
        """Merge domain-specific settings into configuration"""
        for key, value in domain_settings.items():
            if key not in config: config[key] = value
        return config
    
    async def _apply_domain_rules(self, config: Dict, domain: str) -> Dict[str, Any]:
        """Apply domain-specific business rules"""
        if domain == "fintech":
            config["audit_logging"] = True
            config["encryption"] = config.get("encryption", "AES-256")
        elif domain == "healthcare":
            config["anonymization"] = True
            config["retention"] = config.get("retention", "7y")
        return config
    
    def get_auto_complete_options(self, partial: str, category: str) -> List[str]:
        """Get auto-complete options for partial input"""
        return [opt for opt in self._get_category_options(category) if opt.startswith(partial.lower())]
    
    def _get_category_options(self, category: str) -> List[str]:
        """Get available options for a category"""
        category_map = {
            "workload": list(self.workload_optimizations.keys()),
            "domain": list(self.domain_profiles.keys()),
            "parameter": ["batch_size", "concurrency", "error_rate", "compression"]
        }
        return category_map.get(category, [])
    
    async def generate_config_preview(self, suggestions: List[ConfigurationSuggestion]) -> Dict[str, Any]:
        """Generate configuration preview from suggestions"""
        preview = {s.parameter: s.suggested_value for s in suggestions}
        preview["_metadata"] = {"generated_by": "suggestion_engine", "suggestion_count": len(suggestions)}
        return preview