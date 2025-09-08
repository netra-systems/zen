"""
Supply Request Parser

Parses natural language requests into structured research queries.
Maintains 25-line function limit and single responsibility.
"""

import re
from typing import Any, Dict, List

from netra_backend.app.agents.supply_researcher.models import (
    ProviderPatterns,
    ResearchType,
)


class SupplyRequestParser:
    """Parses natural language requests into structured research queries"""
    
    def __init__(self):
        self.provider_patterns = ProviderPatterns.get_patterns()
    
    def parse_natural_language_request(self, request: str) -> Dict[str, Any]:
        """Parse natural language request into structured query"""
        request_lower = request.lower()
        parsed_components = self._extract_all_components(request, request_lower)
        return self._build_parsed_request(parsed_components, request)
    
    def _extract_all_components(self, request: str, request_lower: str) -> Dict[str, Any]:
        """Extract all components from request"""
        return {
            "research_type": self._determine_research_type(request_lower),
            "provider": self._extract_provider_info(request, request_lower)[0],
            "model_name": self._extract_provider_info(request, request_lower)[1],
            "timeframe": self._extract_timeframe(request_lower)
        }
    
    def _build_parsed_request(self, components: Dict[str, Any], original_request: str) -> Dict[str, Any]:
        """Build final parsed request structure"""
        return {
            "research_type": components["research_type"],
            "provider": components["provider"],
            "model_name": components["model_name"],
            "timeframe": components["timeframe"],
            "original_request": original_request
        }
    
    def _determine_research_type(self, request_lower: str) -> ResearchType:
        """Determine research type from request"""
        type_checkers = [
            (self._is_pricing_request, ResearchType.PRICING),
            (self._is_capabilities_request, ResearchType.CAPABILITIES),
            (self._is_availability_request, ResearchType.AVAILABILITY),
            (self._is_new_model_request, ResearchType.NEW_MODEL),
            (self._is_deprecation_request, ResearchType.DEPRECATION)
        ]
        return self._find_matching_type(request_lower, type_checkers)
    
    def _find_matching_type(self, request_lower: str, type_checkers: List[tuple]) -> ResearchType:
        """Find first matching research type"""
        for checker_func, research_type in type_checkers:
            if checker_func(request_lower):
                return research_type
        return ResearchType.MARKET_OVERVIEW
    
    def _is_pricing_request(self, request_lower: str) -> bool:
        """Check if request is about pricing"""
        pricing_keywords = ["price", "pricing", "cost", "dollar", "$"]
        return any(word in request_lower for word in pricing_keywords)
    
    def _is_capabilities_request(self, request_lower: str) -> bool:
        """Check if request is about capabilities"""
        capability_keywords = ["capability", "feature", "context", "token"]
        return any(word in request_lower for word in capability_keywords)
    
    def _is_availability_request(self, request_lower: str) -> bool:
        """Check if request is about availability"""
        availability_keywords = ["available", "access", "api", "endpoint"]
        return any(word in request_lower for word in availability_keywords)
    
    def _is_new_model_request(self, request_lower: str) -> bool:
        """Check if request is about new models"""
        new_model_keywords = ["new", "release", "announce"]
        return any(word in request_lower for word in new_model_keywords)
    
    def _is_deprecation_request(self, request_lower: str) -> bool:
        """Check if request is about deprecation"""
        deprecation_keywords = ["deprecat", "sunset", "retire"]
        return any(word in request_lower for word in deprecation_keywords)
    
    def _extract_provider_info(self, request: str, request_lower: str) -> tuple:
        """Extract provider and model information"""
        provider, model_name = self._find_provider_match(request, request_lower)
        return provider, model_name
    
    def _find_provider_match(self, request: str, request_lower: str) -> tuple:
        """Find first matching provider in request"""
        for provider, patterns in self.provider_patterns.items():
            found_pattern = self._check_provider_patterns(request, request_lower, patterns)
            if found_pattern is not None:
                model_name = self._extract_model_name(request, found_pattern)
                return provider, model_name
        return None, None
    
    def _check_provider_patterns(
        self, 
        request: str, 
        request_lower: str, 
        patterns: List[str]
    ) -> str | None:
        """Check if any pattern matches and return the pattern"""
        for pattern in patterns:
            if pattern in request_lower:
                return pattern
        return None
    
    def _extract_model_name(self, request: str, pattern: str) -> str:
        """Extract full model name from request"""
        model_pattern = rf"\b{pattern}[-\s]?[\d\.]+\w*\b"
        match = re.search(model_pattern, request, re.IGNORECASE)
        return match.group() if match else None
    
    def _extract_timeframe(self, request_lower: str) -> str:
        """Extract time frame if mentioned"""
        if "latest" in request_lower:
            return "latest"
        elif "month" in request_lower:
            return "monthly"
        elif "week" in request_lower:
            return "weekly"
        else:
            return "current"