"""Triage Intent Detector

This module handles user intent detection and admin mode detection.
"""

from netra_backend.app.services.apex_optimizer_agent.models import UserIntent


class IntentDetector:
    """Detects user intent and admin mode from requests"""
    
    def __init__(self):
        """Initialize the intent detector"""
        self.intent_keywords = self._get_intent_keywords()
        self.admin_keywords = self._get_admin_keywords()
        self.action_required_intents = self._get_action_required_intents()
    
    def _get_intent_keywords(self) -> dict:
        """Get intent keyword mappings."""
        return {
            "analyze": ["analyze", "analysis", "examine", "investigate", "understand"],
            "optimize": ["optimize", "improve", "enhance", "reduce", "increase"],
            "configure": ["configure", "set", "update", "change", "modify"],
            "report": ["report", "show", "display", "visualize", "dashboard"],
            "troubleshoot": ["fix", "debug", "troubleshoot", "resolve", "issue"],
            "compare": ["compare", "versus", "vs", "difference", "better"],
            "predict": ["predict", "forecast", "estimate", "project"],
            "recommend": ["recommend", "suggest", "advise", "best"]
        }
    
    def _get_admin_keywords(self) -> list:
        """Get admin mode keywords."""
        return [
            "admin", "administrator", "corpus", "synthetic data",
            "generate data", "manage corpus", "create corpus",
            "delete corpus", "export corpus", "import corpus"
        ]
    
    def _get_action_required_intents(self) -> list:
        """Get intents that require action."""
        return ["optimize", "configure", "troubleshoot"]
    
    def detect_intent(self, request: str) -> UserIntent:
        """Determine user intent from the request"""
        request_lower = request.lower()
        found_intents, action_required = self._find_matching_intents(request_lower)
        primary_intent, secondary_intents = self._process_intent_results(found_intents)
        return self._build_user_intent(primary_intent, secondary_intents, action_required)
    
    def _find_matching_intents(self, request_lower: str) -> tuple:
        """Find all matching intents in the request."""
        found_intents = []
        action_required = False
        for intent, keywords in self.intent_keywords.items():
            if self._intent_matches_keywords(intent, keywords, request_lower):
                found_intents.append(intent)
                action_required = self._check_action_required(intent, action_required)
        return found_intents, action_required
    
    def _intent_matches_keywords(self, intent: str, keywords: list, request_lower: str) -> bool:
        """Check if intent matches any keywords."""
        return any(keyword in request_lower for keyword in keywords)
    
    def _check_action_required(self, intent: str, current_action_required: bool) -> bool:
        """Check if intent requires action."""
        return current_action_required or intent in self.action_required_intents
    
    def _process_intent_results(self, found_intents: list) -> tuple:
        """Process found intents into primary and secondary."""
        primary_intent = found_intents[0] if found_intents else "analyze"
        secondary_intents = found_intents[1:] if len(found_intents) > 1 else []
        return primary_intent, secondary_intents
    
    def _build_user_intent(self, primary_intent: str, secondary_intents: list, action_required: bool) -> UserIntent:
        """Build UserIntent object from components."""
        return UserIntent(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            action_required=action_required
        )
    
    def detect_admin_mode(self, request: str) -> bool:
        """Detect if the request is for admin operations"""
        request_lower = request.lower()
        return any(keyword in request_lower for keyword in self.admin_keywords)