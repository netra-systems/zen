"""
Supply Data Extractor

Extracts structured supply data from research results.
Maintains 8-line function limit and focused extraction logic.
"""

import re
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime, UTC


class SupplyDataExtractor:
    """Extracts structured supply data from research results"""
    
    def __init__(self):
        self.pricing_pattern = r"\$?([\d,]+\.?\d*)\s*(?:per|/)?\s*(?:1M|million)?\s*(?:input|output)?\s*tokens?"
        self.context_pattern = r"(\d+)[kK]?\s*(?:token)?\s*context"
    
    def extract_supply_data(
        self,
        research_result: Dict[str, Any],
        parsed_request: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract structured supply data from research results"""
        questions_answered = research_result.get("questions_answered", [])
        return self._process_qa_answers(questions_answered, parsed_request)
    
    def calculate_confidence_score(
        self,
        research_result: Dict[str, Any],
        extracted_data: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for extracted data"""
        score = 0.5  # Base score
        
        score += self._score_citations(research_result.get("citations", []))
        score += self._score_data_completeness(extracted_data)
        
        return min(1.0, score)
    
    def _extract_pricing(self, answer: str) -> List[str]:
        """Extract pricing information from answer"""
        return re.findall(self.pricing_pattern, answer, re.IGNORECASE)
    
    def _extract_context(self, answer: str) -> List[str]:
        """Extract context window information from answer"""
        return re.findall(self.context_pattern, answer)
    
    def _process_qa_answers(
        self,
        questions_answered: List[Dict[str, Any]],
        parsed_request: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process Q&A answers to extract supply items"""
        supply_items = []
        for qa in questions_answered:
            item = self._extract_from_single_answer(qa, parsed_request)
            if item:
                supply_items.append(item)
        return supply_items
    
    def _extract_from_single_answer(
        self,
        qa: Dict[str, Any],
        parsed_request: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """Extract supply item from single Q&A answer"""
        answer = qa.get("answer", "")
        pricing_matches = self._extract_pricing(answer)
        context_matches = self._extract_context(answer)
        return self._build_item_if_matches(parsed_request, pricing_matches, context_matches)
    
    def _build_item_if_matches(
        self,
        parsed_request: Dict[str, Any],
        pricing_matches: List[str],
        context_matches: List[str]
    ) -> Dict[str, Any] | None:
        """Build supply item if matches found"""
        if not (pricing_matches or context_matches):
            return None
        return self._build_supply_item(parsed_request, pricing_matches, context_matches)
    
    def _build_supply_item(
        self,
        parsed_request: Dict[str, Any],
        pricing_matches: List[str],
        context_matches: List[str]
    ) -> Dict[str, Any]:
        """Build supply item from extracted data"""
        base_item = self._create_base_item(parsed_request)
        self._enrich_with_extracted_data(base_item, pricing_matches, context_matches)
        return base_item
    
    def _create_base_item(self, parsed_request: Dict[str, Any]) -> Dict[str, Any]:
        """Create base supply item structure"""
        return {
            "provider": parsed_request.get("provider", "unknown"),
            "model_name": parsed_request.get("model_name", "unknown"),
            "pricing_input": None,
            "pricing_output": None,
            "context_window": None,
            "last_updated": datetime.now(UTC),
            "research_source": "Google Deep Research",
            "confidence_score": 0.8
        }
    
    def _enrich_with_extracted_data(
        self,
        item: Dict[str, Any],
        pricing_matches: List[str],
        context_matches: List[str]
    ) -> None:
        """Enrich item with extracted pricing and context data"""
        item.update(self._parse_pricing_data(pricing_matches))
        item.update(self._parse_context_data(context_matches))
    
    def _parse_pricing_data(self, pricing_matches: List[str]) -> Dict[str, Any]:
        """Parse pricing data from matches"""
        data = {}
        
        if len(pricing_matches) >= 2:
            data["pricing_input"] = Decimal(pricing_matches[0].replace(",", ""))
            data["pricing_output"] = Decimal(pricing_matches[1].replace(",", ""))
        elif len(pricing_matches) == 1:
            data["pricing_input"] = Decimal(pricing_matches[0].replace(",", ""))
        
        return data
    
    def _parse_context_data(self, context_matches: List[str]) -> Dict[str, Any]:
        """Parse context window data from matches"""
        data = {}
        
        if context_matches:
            context_size = int(context_matches[0])
            if context_size < 1000:  # Likely in K tokens
                context_size *= 1000
            data["context_window"] = context_size
        
        return data
    
    def _score_citations(self, citations: List[Dict[str, Any]]) -> float:
        """Score based on citations quality"""
        score = 0.0
        
        if citations:
            score += min(0.2, len(citations) * 0.05)
        
        for citation in citations:
            if any(word in citation.get("source", "").lower() 
                   for word in ["official", "documentation", "pricing"]):
                score += 0.1
        
        return score
    
    def _score_data_completeness(self, extracted_data: List[Dict[str, Any]]) -> float:
        """Score based on data completeness"""
        score = 0.0
        
        for item in extracted_data:
            if item.get("pricing_input") and item.get("pricing_output"):
                score += 0.1
            if item.get("context_window"):
                score += 0.05
        
        return score