"""
Supply Data Extractor

Extracts structured supply data from research results.
Maintains 25-line function limit and focused extraction logic.
"""

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Dict, List


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
        base_score = 0.5
        citation_score = self._score_citations(research_result.get("citations", []))
        completeness_score = self._score_data_completeness(extracted_data)
        total_score = base_score + citation_score + completeness_score
        return min(1.0, total_score)
    
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
            self._append_item_if_valid(supply_items, item)
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
        base_fields = self._get_base_item_fields(parsed_request)
        metadata_fields = self._get_metadata_fields()
        return {**base_fields, **metadata_fields}
    
    def _get_base_item_fields(self, parsed_request: Dict[str, Any]) -> Dict[str, Any]:
        """Get base item fields from parsed request"""
        return {
            "provider": parsed_request.get("provider", "unknown"),
            "model_name": parsed_request.get("model_name", "unknown"),
            "pricing_input": None,
            "pricing_output": None,
            "context_window": None
        }
    
    def _get_metadata_fields(self) -> Dict[str, Any]:
        """Get metadata fields for supply item"""
        return {
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
        pricing_data = self._parse_pricing_data(pricing_matches)
        context_data = self._parse_context_data(context_matches)
        item.update(pricing_data)
        item.update(context_data)
    
    def _parse_pricing_data(self, pricing_matches: List[str]) -> Dict[str, Any]:
        """Parse pricing data from matches"""
        if len(pricing_matches) >= 2:
            return self._parse_dual_pricing(pricing_matches)
        elif len(pricing_matches) == 1:
            return self._parse_single_pricing(pricing_matches)
        return {}
    
    def _parse_dual_pricing(self, pricing_matches: List[str]) -> Dict[str, Any]:
        """Parse input and output pricing from matches"""
        return {
            "pricing_input": Decimal(pricing_matches[0].replace(",", "")),
            "pricing_output": Decimal(pricing_matches[1].replace(",", ""))
        }
    
    def _parse_single_pricing(self, pricing_matches: List[str]) -> Dict[str, Any]:
        """Parse single pricing value from matches"""
        return {
            "pricing_input": Decimal(pricing_matches[0].replace(",", ""))
        }
    
    def _parse_context_data(self, context_matches: List[str]) -> Dict[str, Any]:
        """Parse context window data from matches"""
        if not context_matches:
            return {}
        raw_context_size = int(context_matches[0])
        normalized_size = self._normalize_context_size(raw_context_size)
        return {"context_window": normalized_size}
    
    def _normalize_context_size(self, context_size: int) -> int:
        """Normalize context size to full token count"""
        if context_size < 1000:  # Likely in K tokens
            return context_size * 1000
        return context_size
    
    def _score_citations(self, citations: List[Dict[str, Any]]) -> float:
        """Score based on citations quality"""
        if not citations:
            return 0.0
        quantity_score = self._calculate_citation_quantity_score(citations)
        quality_score = self._calculate_citation_quality_score(citations)
        return quantity_score + quality_score
    
    def _calculate_citation_quantity_score(self, citations: List[Dict[str, Any]]) -> float:
        """Calculate score based on number of citations"""
        return min(0.2, len(citations) * 0.05)
    
    def _calculate_citation_quality_score(self, citations: List[Dict[str, Any]]) -> float:
        """Calculate score based on citation quality keywords"""
        quality_keywords = ["official", "documentation", "pricing"]
        score = 0.0
        for citation in citations:
            source = citation.get("source", "").lower()
            if any(word in source for word in quality_keywords):
                score += 0.1
        return score
    
    def _score_data_completeness(self, extracted_data: List[Dict[str, Any]]) -> float:
        """Score based on data completeness"""
        score = 0.0
        for item in extracted_data:
            score += self._score_item_completeness(item)
        return score
    
    def _score_item_completeness(self, item: Dict[str, Any]) -> float:
        """Score completeness of individual item"""
        score = 0.0
        if item.get("pricing_input") and item.get("pricing_output"):
            score += 0.1
        if item.get("context_window"):
            score += 0.05
        return score
    
    def _append_item_if_valid(self, supply_items: List[Dict[str, Any]], item: Dict[str, Any] | None) -> None:
        """Append item to list if valid"""
        if item:
            supply_items.append(item)