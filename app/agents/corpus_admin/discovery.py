"""
Corpus Discovery Handler

Handles natural language discovery of corpus options and workload types.
All functions maintain 8-line limit with single responsibility.
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from app.logging_config import central_logger
from app.schemas.corpus import WorkloadType, GenerationParameters

logger = central_logger.get_logger(__name__)


class DiscoveryIntent(str, Enum):
    """Types of discovery intents"""
    LIST_WORKLOADS = "list_workloads"
    EXPLAIN_PARAMETERS = "explain_parameters"
    SHOW_OPTIONS = "show_options"
    GET_SYNTHETIC_OPTIONS = "get_synthetic_options"
    DESCRIBE_DOMAIN = "describe_domain"


class DiscoveryResponse(BaseModel):
    """Response model for discovery requests"""
    intent: DiscoveryIntent
    category: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    parameters: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)
    

class CorpusDiscoveryHandler:
    """Handles natural language discovery of corpus options"""
    
    def __init__(self):
        """Initialize discovery handler with workload mappings"""
        self.workload_types = self._initialize_workload_types()
        self.parameter_specs = self._initialize_parameter_specs()
        self.synthetic_options = self._initialize_synthetic_options()
        self.domain_mappings = self._initialize_domain_mappings()
    
    def _initialize_workload_types(self) -> Dict[str, Dict[str, Any]]:
        """Initialize available workload types and descriptions"""
        return {
            "data_processing": {"name": "Data Processing", "description": "Batch and stream processing workloads"},
            "machine_learning": {"name": "Machine Learning", "description": "ML training and inference workloads"},
            "web_services": {"name": "Web Services", "description": "API and microservices workloads"},
            "database": {"name": "Database", "description": "Database operations and queries"},
            "analytics": {"name": "Analytics", "description": "Data analytics and reporting"},
            "infrastructure": {"name": "Infrastructure", "description": "Infrastructure management workloads"}
        }
    
    def _initialize_parameter_specs(self) -> Dict[str, Dict[str, Any]]:
        """Initialize generation parameter specifications"""
        return {
            "record_count": {"type": "integer", "min": 100, "max": 1000000, "default": 10000},
            "complexity": {"type": "string", "options": ["low", "medium", "high"], "default": "medium"},
            "time_range": {"type": "string", "format": "duration", "default": "30d"},
            "distribution": {"type": "string", "options": ["normal", "uniform", "exponential"], "default": "normal"},
            "error_rate": {"type": "float", "min": 0.0, "max": 0.5, "default": 0.01},
            "concurrency": {"type": "integer", "min": 1, "max": 100, "default": 10}
        }
    
    def _initialize_synthetic_options(self) -> Dict[str, List[str]]:
        """Initialize synthetic data generation options"""
        return {
            "patterns": ["periodic", "trending", "seasonal", "random", "burst"],
            "anomalies": ["outliers", "drift", "spike", "dip", "changepoint"],
            "formats": ["json", "csv", "parquet", "avro", "protobuf"],
            "schemas": ["standard", "custom", "domain-specific", "auto-detect"]
        }
    
    def _initialize_domain_mappings(self) -> Dict[str, List[str]]:
        """Initialize domain to workload type mappings"""
        return {
            "ecommerce": ["web_services", "database", "analytics"],
            "fintech": ["data_processing", "analytics", "database"],
            "healthcare": ["machine_learning", "data_processing", "analytics"],
            "saas": ["web_services", "infrastructure", "database"],
            "iot": ["data_processing", "machine_learning", "infrastructure"]
        }
    
    async def parse_discovery_intent(self, query: str) -> DiscoveryIntent:
        """Parse user query to determine discovery intent"""
        query_lower = query.lower()
        if any(word in query_lower for word in ["list", "show", "what", "available"]):
            return self._determine_list_intent(query_lower)
        if any(word in query_lower for word in ["explain", "describe", "tell"]):
            return DiscoveryIntent.EXPLAIN_PARAMETERS
        if "synthetic" in query_lower or "generate" in query_lower:
            return DiscoveryIntent.GET_SYNTHETIC_OPTIONS
        return DiscoveryIntent.SHOW_OPTIONS
    
    def _determine_list_intent(self, query: str) -> DiscoveryIntent:
        """Determine specific list intent from query"""
        if "workload" in query or "type" in query:
            return DiscoveryIntent.LIST_WORKLOADS
        if "parameter" in query or "config" in query:
            return DiscoveryIntent.EXPLAIN_PARAMETERS
        if "domain" in query:
            return DiscoveryIntent.DESCRIBE_DOMAIN
        return DiscoveryIntent.SHOW_OPTIONS
    
    async def get_available_workload_types(self) -> List[Dict[str, Any]]:
        """Get list of available workload types with descriptions"""
        workloads = []
        for key, value in self.workload_types.items():
            workloads.append({
                "id": key,
                "name": value["name"],
                "description": value["description"]
            })
        return workloads
    
    async def get_generation_parameters(self, workload_type: Optional[str] = None) -> Dict[str, Any]:
        """Get available generation parameters for workload type"""
        base_params = self.parameter_specs.copy()
        if workload_type and workload_type in self.workload_types:
            base_params = self._customize_params_for_workload(base_params, workload_type)
        return {"parameters": base_params, "workload_type": workload_type}
    
    def _customize_params_for_workload(self, params: Dict, workload: str) -> Dict[str, Any]:
        """Customize parameters based on workload type"""
        custom_params = params.copy()
        if workload == "machine_learning":
            custom_params["batch_size"] = {"type": "integer", "min": 16, "max": 512, "default": 64}
        elif workload == "web_services":
            custom_params["request_rate"] = {"type": "integer", "min": 10, "max": 10000, "default": 100}
        return custom_params
    
    async def get_synthetic_data_options(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get synthetic data generation options"""
        if category and category in self.synthetic_options:
            return {"category": category, "options": self.synthetic_options[category]}
        return {"all_options": self.synthetic_options}
    
    async def format_discovery_response(self, intent: DiscoveryIntent, data: Any) -> DiscoveryResponse:
        """Format discovery data into response model"""
        response = DiscoveryResponse(intent=intent)
        response = self._populate_response_data(response, intent, data)
        response.suggestions = await self._generate_suggestions(intent, data)
        return response
    
    def _populate_response_data(self, response: DiscoveryResponse, intent: DiscoveryIntent, data: Any) -> DiscoveryResponse:
        """Populate response with intent-specific data"""
        if intent == DiscoveryIntent.LIST_WORKLOADS:
            response.items = data if isinstance(data, list) else []
        elif intent == DiscoveryIntent.EXPLAIN_PARAMETERS:
            response.parameters = data if isinstance(data, dict) else {}
        elif intent == DiscoveryIntent.GET_SYNTHETIC_OPTIONS:
            response.parameters = data if isinstance(data, dict) else {}
        return response
    
    async def _generate_suggestions(self, intent: DiscoveryIntent, data: Any) -> List[str]:
        """Generate contextual suggestions based on intent"""
        suggestions = []
        if intent == DiscoveryIntent.LIST_WORKLOADS:
            suggestions.append("Try: 'Generate corpus for machine learning workload'")
            suggestions.append("Or: 'Create web services dataset with 10k records'")
        elif intent == DiscoveryIntent.EXPLAIN_PARAMETERS:
            suggestions.append("Specify parameters like: 'Set complexity to high'")
            suggestions.append("Or: 'Use normal distribution with 0.05 error rate'")
        return suggestions
    
    async def discover_domain_workloads(self, domain: str) -> List[str]:
        """Discover recommended workload types for a domain"""
        domain_lower = domain.lower()
        if domain_lower in self.domain_mappings:
            return self.domain_mappings[domain_lower]
        return await self._infer_domain_workloads(domain_lower)
    
    async def _infer_domain_workloads(self, domain: str) -> List[str]:
        """Infer workload types for unknown domains"""
        default_workloads = ["data_processing", "analytics"]
        if "tech" in domain or "software" in domain:
            default_workloads.append("web_services")
        if "data" in domain or "ai" in domain:
            default_workloads.append("machine_learning")
        return default_workloads
    
    def validate_discovery_request(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate discovery request for basic requirements"""
        if not query or len(query.strip()) < 3:
            return False, "Query too short. Please provide more details."
        if len(query) > 500:
            return False, "Query too long. Please be more concise."
        return True, None
    
    async def get_parameter_recommendations(self, workload_type: str, domain: str) -> Dict[str, Any]:
        """Get parameter recommendations for workload and domain"""
        recommendations = {}
        recommendations["workload_type"] = workload_type
        recommendations["domain"] = domain
        recommendations["suggested_params"] = await self._calculate_param_suggestions(workload_type, domain)
        return recommendations
    
    async def _calculate_param_suggestions(self, workload: str, domain: str) -> Dict[str, Any]:
        """Calculate parameter suggestions based on context"""
        suggestions = {"record_count": 10000, "complexity": "medium"}
        if workload == "machine_learning":
            suggestions["record_count"] = 50000
            suggestions["complexity"] = "high"
        if domain in ["fintech", "healthcare"]:
            suggestions["error_rate"] = 0.001
        return suggestions