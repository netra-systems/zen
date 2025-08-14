# Triage Extractors Module - Entity and intent extraction
import re
from typing import List, Dict, Any
from app.agents.triage.models import ExtractedEntities, UserIntent

class EntityExtractor:
    """Extracts entities from user requests."""
    
    @staticmethod
    def extract_entities(request: str) -> ExtractedEntities:
        """Extract key entities from the user request."""
        entities = ExtractedEntities()
        
        # Extract models
        entities.models_mentioned = EntityExtractor._extract_models(request)
        
        # Extract metrics
        entities.metrics_mentioned = EntityExtractor._extract_metrics(request)
        
        # Extract thresholds and targets
        thresholds, targets = EntityExtractor._extract_numbers(request)
        entities.thresholds = thresholds
        entities.targets = targets
        
        # Extract time ranges
        entities.time_ranges = EntityExtractor._extract_time_ranges(request)
        
        return entities
    
    @staticmethod
    def _extract_models(request: str) -> List[str]:
        """Extract model names from request."""
        patterns = [
            r'gpt-?[0-9]+\.?[0-9]*(?:-?turbo)?',
            r'claude-?[0-9]+(?:-[a-z]+)?',
            r'llama-?[0-9]+(?:b)?(?:-[a-z]+)?',
            r'mistral', r'gemini(?:-[a-z]+)?',
            r'anthropic', r'openai', r'palm-?[0-9]*'
        ]
        
        models = []
        for pattern in patterns:
            matches = re.findall(pattern, request.lower())
            models.extend(matches)
        return models
    
    @staticmethod
    def _extract_metrics(request: str) -> List[str]:
        """Extract metric keywords from request."""
        metric_keywords = [
            'latency', 'throughput', 'cost', 'accuracy', 'error',
            'response time', 'tokens', 'requests per second', 'rps', 'memory'
        ]
        
        metrics = []
        request_lower = request.lower()
        for keyword in metric_keywords:
            if keyword in request_lower:
                metrics.append(keyword)
        return metrics
    
    @staticmethod
    def _extract_numbers(request: str) -> tuple:
        """Extract numerical thresholds and targets."""
        pattern = r'\b\d+(?:\.\d+)?(?:\s*(?:ms|s|%|tokens?|requests?|RPS|USD|dollars?))?'
        numbers = re.findall(pattern, request)
        
        thresholds = []
        targets = []
        
        for num in numbers:
            context = EntityExtractor._get_number_context(request, num)
            threshold, target = EntityExtractor._classify_number(num, context)
            if threshold:
                thresholds.append(threshold)
            if target:
                targets.append(target)
        
        return thresholds, targets
    
    @staticmethod
    def _get_number_context(request: str, num: str) -> str:
        """Get context around a number."""
        idx = request.find(num)
        if idx != -1:
            return request[idx:idx+20]
        return ""
    
    @staticmethod
    def _classify_number(num: str, context: str) -> tuple:
        """Classify a number as threshold or target."""
        threshold = None
        target = None
        
        if 'ms' in context[:10] or num.endswith(('ms', 's')):
            threshold = {"type": "time", "value": num}
        elif '%' in context[:5] or num.endswith('%'):
            target = {"type": "percentage", "value": num}
        elif 'token' in context.lower():
            threshold = {"type": "tokens", "value": num}
        elif 'RPS' in context or 'requests' in context.lower():
            threshold = {"type": "rate", "value": num}
        
        return threshold, target
    
    @staticmethod
    def _extract_time_ranges(request: str) -> List[Dict[str, Any]]:
        """Extract time range patterns."""
        patterns = [
            r'last\s+(\d+)\s+(hours?|days?|weeks?|months?)',
            r'past\s+(\d+)\s+(hours?|days?|weeks?|months?)',
            r'(\d{4}-\d{2}-\d{2})',
            r'today|yesterday|this\s+week|last\s+week'
        ]
        
        time_ranges = []
        request_lower = request.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, request_lower)
            for match in matches:
                time_ranges.append({"pattern": match})
        
        return time_ranges

class IntentDetector:
    """Detects user intent from requests."""
    
    INTENT_KEYWORDS = {
        "analyze": ["analyze", "analysis", "examine", "investigate", "understand"],
        "optimize": ["optimize", "improve", "enhance", "reduce", "increase"],
        "configure": ["configure", "set", "update", "change", "modify"],
        "report": ["report", "show", "display", "visualize", "dashboard"],
        "troubleshoot": ["fix", "debug", "troubleshoot", "resolve", "issue"],
        "compare": ["compare", "versus", "vs", "difference", "better"],
        "predict": ["predict", "forecast", "estimate", "project"],
        "recommend": ["recommend", "suggest", "advise", "best"]
    }
    
    @staticmethod
    def detect_intent(request: str) -> UserIntent:
        """Determine user intent from the request."""
        request_lower = request.lower()
        found_intents = []
        action_required = False
        
        for intent, keywords in IntentDetector.INTENT_KEYWORDS.items():
            if any(keyword in request_lower for keyword in keywords):
                found_intents.append(intent)
                if intent in ["optimize", "configure", "troubleshoot"]:
                    action_required = True
        
        primary = found_intents[0] if found_intents else "analyze"
        secondary = found_intents[1:] if len(found_intents) > 1 else []
        
        return UserIntent(
            primary_intent=primary,
            secondary_intents=secondary,
            action_required=action_required
        )
    
    @staticmethod
    def detect_admin_mode(request: str) -> bool:
        """Detect if the request is for admin operations."""
        admin_keywords = [
            "admin", "administrator", "corpus", "synthetic data",
            "generate data", "manage corpus", "create corpus",
            "delete corpus", "export corpus", "import corpus"
        ]
        request_lower = request.lower()
        return any(keyword in request_lower for keyword in admin_keywords)