"""
Corpus suggestion profiles module.

Provides suggestion profiles for corpus operations.
This module has been removed but tests still reference it.
"""

from typing import Any, Dict, List


class CorpusSuggestionProfiles:
    """
    Corpus suggestion profiles handler.
    
    Handles suggestion profiles for corpus operations.
    """
    
    def __init__(self):
        self.profiles = {
            "documentation": {
                "recommended_size": "medium",
                "indexing_strategy": "full_text",
                "update_frequency": "weekly"
            },
            "knowledge_base": {
                "recommended_size": "large", 
                "indexing_strategy": "semantic",
                "update_frequency": "daily"
            },
            "reference": {
                "recommended_size": "small",
                "indexing_strategy": "keyword",
                "update_frequency": "monthly"
            }
        }
    
    def get_profile(self, corpus_type: str) -> Dict[str, Any]:
        """Get suggestion profile for corpus type."""
        return self.profiles.get(corpus_type, self.profiles["documentation"])
    
    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all available suggestion profiles."""
        return self.profiles
    
    def suggest_optimization(self, corpus_data: Dict[str, Any]) -> List[str]:
        """Suggest optimizations for corpus."""
        suggestions = []
        
        if corpus_data.get("document_count", 0) > 1000:
            suggestions.append("Consider enabling semantic indexing for better search")
        
        if corpus_data.get("size_mb", 0) > 100:
            suggestions.append("Consider document compression to reduce storage")
            
        if not suggestions:
            suggestions.append("Corpus configuration looks optimal")
            
        return suggestions
    
    def recommend_corpus_type(self, use_case: str) -> str:
        """Recommend corpus type based on use case."""
        use_case_lower = use_case.lower()
        
        if "document" in use_case_lower or "manual" in use_case_lower:
            return "documentation"
        elif "knowledge" in use_case_lower or "learning" in use_case_lower:
            return "knowledge_base"
        elif "reference" in use_case_lower or "lookup" in use_case_lower:
            return "reference"
        else:
            return "documentation"  # Default recommendation


# Compatibility functions for tests
def get_optimization_rules() -> Dict[str, Any]:
    """Get optimization rules for backward compatibility."""
    return {
        "performance": {
            "cache_size": "large",
            "indexing": "aggressive",
            "compression": "enabled"
        },
        "quality": {
            "validation": "strict",
            "deduplication": "enabled",
            "normalization": "full"
        },
        "balanced": {
            "cache_size": "medium",
            "indexing": "standard",
            "validation": "standard"
        }
    }


def get_domain_profiles() -> Dict[str, Any]:
    """Get domain profiles for backward compatibility."""
    profiles = CorpusSuggestionProfiles()
    return profiles.get_all_profiles()


def get_workload_optimizations() -> Dict[str, Any]:
    """Get workload optimizations for backward compatibility."""
    return {
        "high_read": {"cache": "aggressive", "replication": "enabled"},
        "high_write": {"batch_size": "large", "async_writes": "enabled"},
        "mixed": {"cache": "balanced", "batch_size": "medium"}
    }


def get_parameter_dependencies() -> Dict[str, List[str]]:
    """Get parameter dependencies for backward compatibility."""
    return {
        "cache_size": ["memory_limit", "disk_space"],
        "indexing_strategy": ["cpu_cores", "storage_type"],
        "replication_factor": ["node_count", "network_bandwidth"]
    }


def get_category_options() -> Dict[str, List[str]]:
    """Get category options for backward compatibility."""
    return {
        "corpus_type": ["documentation", "knowledge_base", "reference", "custom"],
        "indexing_strategy": ["full_text", "semantic", "keyword", "hybrid"],
        "update_frequency": ["realtime", "daily", "weekly", "monthly"]
    }


def apply_domain_rules(domain: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Apply domain-specific rules for backward compatibility."""
    profiles = CorpusSuggestionProfiles()
    profile = profiles.get_profile(domain)
    return {**settings, **profile}


def merge_domain_settings(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Merge domain settings for backward compatibility."""
    return {**base, **overrides}