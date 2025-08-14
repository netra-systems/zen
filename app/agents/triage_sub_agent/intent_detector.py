"""Triage Intent Detector

This module handles user intent detection and admin mode detection.
"""

from .models import UserIntent


class IntentDetector:
    """Detects user intent and admin mode from requests"""
    
    def __init__(self):
        """Initialize the intent detector"""
        self.intent_keywords = {
            "analyze": ["analyze", "analysis", "examine", "investigate", "understand"],
            "optimize": ["optimize", "improve", "enhance", "reduce", "increase"],
            "configure": ["configure", "set", "update", "change", "modify"],
            "report": ["report", "show", "display", "visualize", "dashboard"],
            "troubleshoot": ["fix", "debug", "troubleshoot", "resolve", "issue"],
            "compare": ["compare", "versus", "vs", "difference", "better"],
            "predict": ["predict", "forecast", "estimate", "project"],
            "recommend": ["recommend", "suggest", "advise", "best"]
        }
        
        self.admin_keywords = [
            "admin", "administrator", "corpus", "synthetic data",
            "generate data", "manage corpus", "create corpus",
            "delete corpus", "export corpus", "import corpus"
        ]
        
        self.action_required_intents = ["optimize", "configure", "troubleshoot"]
    
    def detect_intent(self, request: str) -> UserIntent:
        """Determine user intent from the request"""
        request_lower = request.lower()
        
        found_intents = []
        action_required = False
        
        # Find all matching intents
        for intent, keywords in self.intent_keywords.items():
            if any(keyword in request_lower for keyword in keywords):
                found_intents.append(intent)
                
                if intent in self.action_required_intents:
                    action_required = True
        
        # Set primary and secondary intents
        primary_intent = found_intents[0] if found_intents else "analyze"
        secondary_intents = found_intents[1:] if len(found_intents) > 1 else []
        
        return UserIntent(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            action_required=action_required
        )
    
    def detect_admin_mode(self, request: str) -> bool:
        """Detect if the request is for admin operations"""
        request_lower = request.lower()
        return any(keyword in request_lower for keyword in self.admin_keywords)