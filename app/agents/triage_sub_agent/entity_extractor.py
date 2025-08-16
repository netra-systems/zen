"""Triage Entity Extractor

This module handles the extraction of key entities from user requests.
"""

import re
from .models import ExtractedEntities


class EntityExtractor:
    """Extracts key entities from user requests"""
    
    def __init__(self):
        """Initialize the entity extractor"""
        self.model_patterns = self._get_model_patterns()
        self.metric_keywords = self._get_metric_keywords()
        self.time_patterns = self._get_time_patterns()
    
    def _get_model_patterns(self):
        """Get model name patterns."""
        return [
            r'gpt-?[0-9]+\.?[0-9]*(?:-?turbo)?',
            r'claude-?[0-9]+(?:-[a-z]+)?',
            r'llama-?[0-9]+(?:b)?(?:-[a-z]+)?',
            r'mistral',
            r'gemini(?:-[a-z]+)?',
            r'anthropic',
            r'openai',
            r'palm-?[0-9]*'
        ]
    
    def _get_metric_keywords(self):
        """Get metric keywords."""
        return [
            'latency', 'throughput', 'cost', 'accuracy', 'error',
            'response time', 'tokens', 'requests per second', 'rps', 'memory'
        ]
    
    def _get_time_patterns(self):
        """Get time pattern expressions."""
        return [
            r'last\s+(\d+)\s+(hours?|days?|weeks?|months?)',
            r'past\s+(\d+)\s+(hours?|days?|weeks?|months?)',
            r'(\d{4}-\d{2}-\d{2})',
            r'today|yesterday|this\s+week|last\s+week'
        ]
    
    def extract_entities(self, request: str) -> ExtractedEntities:
        """Extract key entities from the user request"""
        entities = ExtractedEntities()
        
        self._populate_models_and_metrics(entities, request)
        self._populate_numbers_and_times(entities, request)
        
        return entities
    
    def _populate_models_and_metrics(self, entities: ExtractedEntities, request: str):
        """Populate models and metrics in entities."""
        entities.models_mentioned = self._extract_models(request)
        entities.metrics_mentioned = self._extract_metrics(request)
    
    def _populate_numbers_and_times(self, entities: ExtractedEntities, request: str):
        """Populate thresholds, targets, and time ranges."""
        entities.thresholds, entities.targets = self._extract_numbers(request)
        entities.time_ranges = self._extract_time_ranges(request)
    
    def _extract_models(self, request: str) -> list:
        """Extract model names from request"""
        models = []
        for pattern in self.model_patterns:
            matches = re.findall(pattern, request.lower())
            models.extend(matches)
        return models
    
    def _extract_metrics(self, request: str) -> list:
        """Extract metric keywords from request"""
        metrics = []
        request_lower = request.lower()
        for keyword in self.metric_keywords:
            if keyword in request_lower:
                metrics.append(keyword)
        return metrics
    
    def _extract_numbers(self, request: str) -> tuple:
        """Extract numerical values as potential thresholds/targets"""
        thresholds = []
        targets = []
        
        number_pattern = r'\b\d+(?:\.\d+)?(?:\s*(?:ms|s|%|tokens?|requests?|RPS|USD|dollars?))?'
        numbers = re.findall(number_pattern, request)
        
        self._categorize_numbers(numbers, request, thresholds, targets)
        return thresholds, targets
    
    def _categorize_numbers(self, numbers, request, thresholds, targets):
        """Categorize numbers into thresholds and targets."""
        for num in numbers:
            remaining_text = request[request.find(num):]
            self._classify_number(num, remaining_text, thresholds, targets)
    
    def _classify_number(self, num, remaining_text, thresholds, targets):
        """Classify a single number based on context."""
        if self._is_time_value(remaining_text, num):
            thresholds.append({"type": "time", "value": num})
        elif self._is_percentage(remaining_text, num):
            targets.append({"type": "percentage", "value": self._format_percentage(num)})
        elif self._is_token_value(remaining_text):
            thresholds.append({"type": "tokens", "value": num})
        elif self._is_rate_value(remaining_text):
            thresholds.append({"type": "rate", "value": num})
    
    def _is_time_value(self, remaining_text: str, num: str) -> bool:
        """Check if number represents a time value"""
        return ('ms' in remaining_text[:10] or 
                num.endswith('ms') or 
                num.endswith('s'))
    
    def _is_percentage(self, remaining_text: str, num: str) -> bool:
        """Check if number represents a percentage"""
        return '%' in remaining_text[:5] or num.endswith('%')
    
    def _format_percentage(self, num: str) -> str:
        """Format percentage value"""
        return num + '%' if not num.endswith('%') else num
    
    def _is_token_value(self, remaining_text: str) -> bool:
        """Check if number represents tokens"""
        return 'token' in remaining_text[:20].lower()
    
    def _is_rate_value(self, remaining_text: str) -> bool:
        """Check if number represents a rate"""
        return ('RPS' in remaining_text[:10] or 
                'requests' in remaining_text[:20].lower())
    
    def _extract_time_ranges(self, request: str) -> list:
        """Extract time range patterns from request"""
        time_ranges = []
        
        for pattern in self.time_patterns:
            self._process_time_pattern(pattern, request, time_ranges)
        
        return time_ranges
    
    def _process_time_pattern(self, pattern, request, time_ranges):
        """Process a single time pattern and add matches."""
        matches = re.findall(pattern, request.lower())
        for match in matches:
            time_ranges.append({"pattern": match})