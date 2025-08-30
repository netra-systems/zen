"""
Unit tests for suggestion_profiles
Coverage Target: 90%
Business Value: Revenue-critical component
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from netra_backend.app.agents.corpus_admin.suggestion_profiles import (
    get_optimization_rules,
    get_domain_profiles,
    get_workload_optimizations,
    get_parameter_dependencies,
    get_category_options,
    apply_domain_rules,
    merge_domain_settings
)

class TestSuggestionProfiles:
    """Test suite for SuggestionProfiles functions"""
    
    def test_get_optimization_rules(self):
        """Test optimization rules retrieval"""
        rules = get_optimization_rules()
        assert isinstance(rules, dict)
        assert "performance" in rules
        assert "quality" in rules
        assert "balanced" in rules
    
    def test_get_domain_profiles(self):
        """Test domain profiles retrieval"""
        profiles = get_domain_profiles()
        assert isinstance(profiles, dict)
        assert "fintech" in profiles
        assert "healthcare" in profiles
        assert "ecommerce" in profiles
    
    def test_get_workload_optimizations(self):
        """Test workload optimizations retrieval"""
        optimizations = get_workload_optimizations()
        assert isinstance(optimizations, dict)
        assert "machine_learning" in optimizations
        assert "web_services" in optimizations
        assert "data_processing" in optimizations
    
    def test_get_parameter_dependencies(self):
        """Test parameter dependencies"""
        deps = get_parameter_dependencies()
        assert isinstance(deps, dict)
        assert "batch_size" in deps
        assert "concurrency" in deps
    
    def test_get_category_options(self):
        """Test category options"""
        workload_options = get_category_options("workload")
        assert isinstance(workload_options, list)
        assert len(workload_options) > 0
    
    def test_apply_domain_rules_fintech(self):
        """Test fintech domain rules"""
        config = {}
        result = apply_domain_rules(config, "fintech")
        assert result["audit_logging"] is True
        assert "encryption" in result
    
    def test_apply_domain_rules_healthcare(self):
        """Test healthcare domain rules"""
        config = {}
        result = apply_domain_rules(config, "healthcare")
        assert result["anonymization"] is True
        assert "retention" in result
    
    def test_merge_domain_settings(self):
        """Test domain settings merge"""
        config = {"existing": "value"}
        domain_settings = {"new": "setting", "existing": "ignored"}
        result = merge_domain_settings(config, domain_settings)
        assert result["existing"] == "value"  # existing not overwritten
        assert result["new"] == "setting"  # new added
