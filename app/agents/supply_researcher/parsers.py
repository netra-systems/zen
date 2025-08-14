"""
Supply Request Parser

Parses natural language requests into structured research queries.
Maintains 8-line function limit and single responsibility.
"""

import re
from typing import Dict, Any
from .models import ResearchType, ProviderPatterns


class SupplyRequestParser:
    """Parses natural language requests into structured research queries"""
    
    def __init__(self):
        self.provider_patterns = ProviderPatterns.get_patterns()
    
    def parse_natural_language_request(self, request: str) -> Dict[str, Any]:
        """Parse natural language request into structured query"""
        request_lower = request.lower()
        
        research_type = self._determine_research_type(request_lower)
        provider, model_name = self._extract_provider_info(request, request_lower)
        timeframe = self._extract_timeframe(request_lower)
        
        return {
            "research_type": research_type,
            "provider": provider,
            "model_name": model_name,
            "timeframe": timeframe,
            "original_request": request
        }
    
    def _determine_research_type(self, request_lower: str) -> ResearchType:
        """Determine research type from request"""
        if any(word in request_lower for word in ["price", "pricing", "cost", "dollar", "$"]):
            return ResearchType.PRICING
        elif any(word in request_lower for word in ["capability", "feature", "context", "token"]):
            return ResearchType.CAPABILITIES
        elif any(word in request_lower for word in ["available", "access", "api", "endpoint"]):
            return ResearchType.AVAILABILITY
        elif any(word in request_lower for word in ["new", "release", "announce"]):
            return ResearchType.NEW_MODEL
        elif any(word in request_lower for word in ["deprecat", "sunset", "retire"]):
            return ResearchType.DEPRECATION
        else:
            return ResearchType.MARKET_OVERVIEW
    
    def _extract_provider_info(self, request: str, request_lower: str) -> tuple:
        """Extract provider and model information"""
        provider = None
        model_name = None
        
        for prov, patterns in self.provider_patterns.items():
            for pattern in patterns:
                if pattern in request_lower:
                    provider = prov
                    model_name = self._extract_model_name(request, pattern)
                    break
            if provider:
                break
        
        return provider, model_name
    
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