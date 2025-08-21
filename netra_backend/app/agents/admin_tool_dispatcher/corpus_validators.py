"""
Corpus Admin Tool Validators

Validation functions for corpus admin tool parameters.
All functions maintain 25-line limit with single responsibility.
"""

from typing import Dict, Optional, Tuple
from netra_backend.app.corpus_models import CorpusToolType


class CorpusValidators:
    """Validation functions for corpus admin tools"""
    
    @staticmethod
    async def validate_create_params(params: Dict) -> Tuple[bool, Optional[str]]:
        """Validate corpus creation parameters"""
        if "name" not in params:
            return False, "Corpus name is required"
        if "workload_type" not in params:
            return False, "Workload type is required"
        return True, None
    
    @staticmethod
    async def validate_generation_params(params: Dict) -> Tuple[bool, Optional[str]]:
        """Validate data generation parameters"""
        if "record_count" not in params:
            return False, "Record count is required"
        if params["record_count"] > 10000000:
            return False, "Record count exceeds maximum limit"
        return True, None
    
    @staticmethod
    async def validate_optimization_params(params: Dict) -> Tuple[bool, Optional[str]]:
        """Validate optimization parameters"""
        valid_opts = ["index_optimization", "compression", "partitioning"]
        if not any(opt in params for opt in valid_opts):
            return False, "At least one optimization type required"
        return True, None
    
    @staticmethod
    async def validate_export_params(params: Dict) -> Tuple[bool, Optional[str]]:
        """Validate export parameters"""
        valid_formats = ["json", "csv", "parquet", "avro"]
        if "format" in params and params["format"] not in valid_formats:
            return False, f"Invalid format. Must be one of: {valid_formats}"
        return True, None
    
    @staticmethod
    def get_validator_registry() -> Dict[CorpusToolType, callable]:
        """Get registry of validators for each tool type"""
        return {
            CorpusToolType.CREATE: CorpusValidators.validate_create_params,
            CorpusToolType.GENERATE: CorpusValidators.validate_generation_params,
            CorpusToolType.OPTIMIZE: CorpusValidators.validate_optimization_params,
            CorpusToolType.EXPORT: CorpusValidators.validate_export_params
        }