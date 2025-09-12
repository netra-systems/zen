# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Extract profile parsing logic from SyntheticDataSubAgent -  <= 300 lines, functions  <= 8 lines
# Git: 8-18-25-AM | new file
# Change: Create | Scope: Component | Risk: Low
# Session: module-extraction | Seq: 1
# Review: Pending | Score: 95
# ================================
"""
Synthetic Data Profile Parser Module

Responsible for parsing user requests into WorkloadProfile objects.
Handles preset matching, custom profile parsing, and default profile creation.
Single responsibility: Profile parsing and workload type determination.
"""

from typing import Any, Dict, List, Optional

from netra_backend.app.agents.synthetic_data_presets import (
    DataGenerationType,
    WorkloadProfile,
    get_all_presets,
)
from netra_backend.app.agents.utils import extract_json_from_response
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SyntheticDataProfileParser:
    """Parser for converting user requests into WorkloadProfile objects."""
    
    def __init__(self):
        """Initialize profile parser with preset workloads."""
        self.preseeded_workloads = get_all_presets()
    
    async def determine_workload_profile(
        self, 
        user_request: Optional[str], 
        llm_manager: LLMManager
    ) -> WorkloadProfile:
        """Determine workload profile from user request."""
        if not user_request:
            return self.get_default_profile()
        
        preset = self.find_matching_preset(user_request)
        if preset:
            return preset
        
        return await self.parse_custom_profile(user_request, llm_manager)
    
    def find_matching_preset(self, user_request: str) -> Optional[WorkloadProfile]:
        """Find matching preset from user request."""
        request_lower = user_request.lower()
        for name, profile in self.preseeded_workloads.items():
            if name in request_lower:
                logger.info(f"Using pre-seeded workload: {name}")
                return profile
        return None
    
    async def parse_custom_profile(
        self, user_request: str, llm_manager: LLMManager
    ) -> WorkloadProfile:
        """Parse custom profile from user request."""
        try:
            prompt = self.create_parsing_prompt(user_request)
            response = await llm_manager.ask_llm(prompt, llm_config_name='default')
            params = llm_parser.extract_json_from_response(response)
            return self.create_profile_from_params(params)
        except Exception as e:
            self._log_parsing_failure(e)
            return self.get_default_profile()
    
    def create_parsing_prompt(self, user_request: str) -> str:
        """Create prompt for parsing user request."""
        fields_spec = self.get_prompt_fields_spec()
        base_prompt = self.create_base_prompt(user_request)
        instructions = "Default volume to 1000 if not specified."
        return self.format_parsing_prompt(base_prompt, fields_spec, instructions)
    
    def create_base_prompt(self, user_request: str) -> str:
        """Create base prompt for user request analysis."""
        return f"Analyze this request for synthetic data parameters: {user_request}"
    
    def format_parsing_prompt(
        self, base_prompt: str, fields_spec: str, instructions: str
    ) -> str:
        """Format complete parsing prompt with sections."""
        return f"""
{base_prompt}

{fields_spec}

{instructions}
"""
    
    def get_default_profile(self) -> WorkloadProfile:
        """Get default workload profile."""
        return WorkloadProfile(
            workload_type=DataGenerationType.INFERENCE_LOGS,
            volume=1000,
            time_range_days=30
        )
    
    def create_profile_from_params(self, params: Optional[Dict[str, Any]]) -> WorkloadProfile:
        """Create WorkloadProfile from parsed parameters."""
        if params:
            return WorkloadProfile(**params)
        return self.get_default_profile()
    
    def get_prompt_fields_spec(self) -> str:
        """Get prompt fields specification string."""
        field_types = "workload_type (inference_logs|training_data|performance_metrics|cost_data|custom)"
        ranges = "volume (100-1000000), time_range_days (1-365)"
        options = "distribution (normal|uniform|exponential), noise_level (0.0-0.5), custom_parameters"
        return f"Return JSON with fields: {field_types}, {ranges}, {options}."
    
    def _log_parsing_failure(self, error: Exception) -> None:
        """Log workload profile parsing failure."""
        logger.warning(f"Failed to parse workload profile: {error}")


def create_profile_parser() -> SyntheticDataProfileParser:
    """Factory function to create profile parser instance."""
    return SyntheticDataProfileParser()


# Standalone utility functions for profile validation
def validate_profile_params(params: Dict[str, Any]) -> bool:
    """Validate profile parameters before WorkloadProfile creation."""
    required_fields = ['workload_type']
    return all(field in params for field in required_fields)


def normalize_workload_type(workload_type_str: str) -> DataGenerationType:
    """Normalize workload type string to enum value."""
    try:
        return DataGenerationType(workload_type_str.lower())
    except ValueError:
        return DataGenerationType.CUSTOM


def extract_volume_from_text(text: str) -> Optional[int]:
    """Extract volume number from text using pattern matching."""
    import re
    volume_patterns = _get_volume_patterns()
    for pattern in volume_patterns:
        match = re.search(pattern, text.lower())
        if match:
            return _process_volume_match(match)
    return None


def _get_volume_patterns() -> List[str]:
    """Get volume extraction patterns."""
    return [
        r'(\d+)k?\s*(?:records?|entries|rows?|samples?)',
        r'volume[:\s]*(\d+)',
        r'generate[:\s]*(\d+)'
    ]


def _process_volume_match(match) -> int:
    """Process volume match and apply multipliers."""
    volume = int(match.group(1))
    is_k_notation = 'k' in match.group(0).lower()
    return volume * 1000 if is_k_notation else volume


def extract_time_range_from_text(text: str) -> Optional[int]:
    """Extract time range from text using pattern matching."""
    import re
    time_patterns = _get_time_patterns()
    multipliers = _get_time_multipliers()
    for pattern in time_patterns:
        match = re.search(pattern, text.lower())
        if match:
            return _process_time_match(match, multipliers)
    return None


def _get_time_patterns() -> List[str]:
    """Get time range extraction patterns."""
    return [
        r'(\d+)\s*days?',
        r'(\d+)\s*weeks?',
        r'(\d+)\s*months?'
    ]


def _get_time_multipliers() -> Dict[str, int]:
    """Get time unit multipliers."""
    return {'days': 1, 'weeks': 7, 'months': 30}


def _process_time_match(match, multipliers: Dict[str, int]) -> int:
    """Process time match and apply unit multipliers."""
    value = int(match.group(1))
    unit = _determine_time_unit(match, multipliers)
    return value * multipliers[unit]


def _determine_time_unit(match, multipliers: Dict[str, int]) -> str:
    """Determine time unit from match."""
    for unit_key in multipliers:
        if unit_key in match.group(0):
            return unit_key
    return 'days'


def detect_distribution_from_text(text: str) -> str:
    """Detect distribution type from text description."""
    text_lower = text.lower()
    if any(word in text_lower for word in ['spike', 'burst', 'exponential']):
        return 'exponential'
    elif any(word in text_lower for word in ['even', 'uniform', 'constant']):
        return 'uniform'
    else:
        return 'normal'


def build_profile_from_text_analysis(text: str) -> Dict[str, Any]:
    """Build profile parameters from comprehensive text analysis."""
    params = {}
    _extract_volume_to_params(text, params)
    _extract_time_range_to_params(text, params)
    _set_distribution_and_defaults(text, params)
    return params


def _extract_volume_to_params(text: str, params: Dict[str, Any]) -> None:
    """Extract volume and add to params if found."""
    volume = extract_volume_from_text(text)
    if volume:
        params['volume'] = volume


def _extract_time_range_to_params(text: str, params: Dict[str, Any]) -> None:
    """Extract time range and add to params if found."""
    time_range = extract_time_range_from_text(text)
    if time_range:
        params['time_range_days'] = time_range


def _set_distribution_and_defaults(text: str, params: Dict[str, Any]) -> None:
    """Set distribution pattern and default workload type."""
    params['distribution'] = detect_distribution_from_text(text)
    params['workload_type'] = DataGenerationType.INFERENCE_LOGS.value


# Export main parser class and factory function
__all__ = [
    'SyntheticDataProfileParser',
    'create_profile_parser',
    'validate_profile_params',
    'normalize_workload_type',
    'extract_volume_from_text',
    'extract_time_range_from_text',
    'detect_distribution_from_text',
    'build_profile_from_text_analysis'
]