"""
Unified JSON Serialization/Deserialization Handler - CONSOLIDATED SSOT

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate JSON handling duplication across all services and scripts
- Value Impact: Consistent JSON formatting, error handling, and encoding across the platform
- Strategic Impact: Standardized data serialization, reduced bugs, unified debugging

This module consolidates ALL JSON functionality from across the codebase:
- Basic serialization/deserialization with custom type support
- Circular reference detection and handling
- LLM response parsing and recovery from malformed JSON
- JSON fragment extraction and reconstruction
- WebSocket message preparation with datetime conversion
- File I/O operations with proper encoding
- Validation and error fixing utilities

Consolidates 7+ competing implementations:
1. unified_json_handler.py (base implementation)
2. utils/json_utils.py (circular reference handling)
3. core/json_utils.py (WebSocket serialization)
4. core/json_parsing_utils.py (LLM response parsing)
5. agents/utils_json_extraction.py (JSON extraction)
6. agents/utils_json_validators.py (error recovery)
7. Various other scattered JSON utilities

Each function  <= 25 lines, total module split across classes for maintainability.
"""

import json
import logging
import re
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, TextIO, Union
from uuid import UUID
from dataclasses import is_dataclass, asdict

from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class UnifiedJSONEncoder(json.JSONEncoder):
    """Enhanced JSON encoder that handles common Python types."""
    
    def default(self, obj: Any) -> Any:
        """Convert non-JSON serializable objects to JSON-compatible format."""
        # Handle datetime objects
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        
        # Handle UUID objects
        elif isinstance(obj, UUID):
            return str(obj)
        
        # Handle Decimal objects
        elif isinstance(obj, Decimal):
            return float(obj)
        
        # Handle dataclasses
        elif is_dataclass(obj):
            return asdict(obj)
        
        # Handle sets
        elif isinstance(obj, set):
            return list(obj)
        
        # Handle Path objects
        elif isinstance(obj, Path):
            return str(obj)
        
        # Handle custom objects by converting to dict
        elif hasattr(obj, '__dict__'):
            return {
                key: value for key, value in obj.__dict__.items()
                if not key.startswith('_')
            }
        
        # Default behavior for other types
        return super().default(obj)


class UnifiedJSONHandler:
    """
    Unified JSON handler for consistent serialization across all services.
    
    Provides standardized JSON operations with consistent formatting,
    error handling, and support for common Python types.
    """
    
    def __init__(self, service_name: str = "unknown"):
        self.service_name = service_name
        self.env = IsolatedEnvironment()
        self._load_config()
    
    def _load_config(self) -> None:
        """Load JSON configuration from environment."""
        self.default_indent = int(self.env.get("JSON_INDENT", "2"))
        self.ensure_ascii = self.env.get("JSON_ENSURE_ASCII", "false").lower() == "true"
        self.sort_keys = self.env.get("JSON_SORT_KEYS", "false").lower() == "true"
        self.separators = (',', ': ') if self.default_indent else (',', ':')
        
    def dumps(self, obj: Any, indent: Optional[int] = None, **kwargs) -> str:
        """
        Serialize object to JSON string with unified formatting.
        
        Args:
            obj: Object to serialize
            indent: JSON indentation (defaults to configured value)
            **kwargs: Additional json.dumps arguments
            
        Returns:
            JSON string
            
        Raises:
            JSONSerializationError: If serialization fails
        """
        try:
            return json.dumps(
                obj,
                cls=UnifiedJSONEncoder,
                indent=indent if indent is not None else self.default_indent,
                ensure_ascii=self.ensure_ascii,
                sort_keys=self.sort_keys,
                separators=self.separators,
                **kwargs
            )
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization failed for {self.service_name}: {e}")
            raise JSONSerializationError(f"Failed to serialize object: {e}") from e
    
    def loads(self, json_str: str, **kwargs) -> Any:
        """
        Deserialize JSON string to Python object.
        
        Args:
            json_str: JSON string to deserialize
            **kwargs: Additional json.loads arguments
            
        Returns:
            Deserialized Python object
            
        Raises:
            JSONDeserializationError: If deserialization fails
        """
        try:
            return json.loads(json_str, **kwargs)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON deserialization failed for {self.service_name}: {e}")
            raise JSONDeserializationError(f"Failed to deserialize JSON: {e}") from e
    
    def dump_to_file(self, obj: Any, file_path: Union[str, Path], indent: Optional[int] = None, **kwargs) -> None:
        """
        Serialize object to JSON file with error handling.
        
        Args:
            obj: Object to serialize
            file_path: Path to output file
            indent: JSON indentation (defaults to configured value)
            **kwargs: Additional json.dump arguments
            
        Raises:
            JSONFileError: If file operation fails
        """
        file_path = Path(file_path)
        
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(
                    obj,
                    f,
                    cls=UnifiedJSONEncoder,
                    indent=indent if indent is not None else self.default_indent,
                    ensure_ascii=self.ensure_ascii,
                    sort_keys=self.sort_keys,
                    separators=self.separators,
                    **kwargs
                )
                
            logger.debug(f"Successfully wrote JSON to {file_path}")
            
        except (OSError, IOError) as e:
            logger.error(f"Failed to write JSON file {file_path}: {e}")
            raise JSONFileError(f"Failed to write JSON file {file_path}: {e}") from e
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization failed for file {file_path}: {e}")
            raise JSONSerializationError(f"Failed to serialize object to {file_path}: {e}") from e
    
    def load_from_file(self, file_path: Union[str, Path], **kwargs) -> Any:
        """
        Load and deserialize JSON from file with error handling.
        
        Args:
            file_path: Path to JSON file
            **kwargs: Additional json.load arguments
            
        Returns:
            Deserialized Python object
            
        Raises:
            JSONFileError: If file operation fails
        """
        file_path = Path(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f, **kwargs)
                
            logger.debug(f"Successfully loaded JSON from {file_path}")
            return data
            
        except FileNotFoundError:
            logger.error(f"JSON file not found: {file_path}")
            raise JSONFileError(f"JSON file not found: {file_path}")
        except (OSError, IOError) as e:
            logger.error(f"Failed to read JSON file {file_path}: {e}")
            raise JSONFileError(f"Failed to read JSON file {file_path}: {e}") from e
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid JSON in file {file_path}: {e}")
            raise JSONDeserializationError(f"Invalid JSON in file {file_path}: {e}") from e
    
    def safe_load_from_file(self, file_path: Union[str, Path], default: Any = None, **kwargs) -> Any:
        """
        Safely load JSON from file with fallback value.
        
        Args:
            file_path: Path to JSON file
            default: Default value if file doesn't exist or is invalid
            **kwargs: Additional json.load arguments
            
        Returns:
            Deserialized object or default value
        """
        try:
            return self.load_from_file(file_path, **kwargs)
        except (JSONFileError, JSONDeserializationError):
            logger.debug(f"Using default value for {file_path}")
            return default
    
    def pretty_format(self, obj: Any, indent: int = 2) -> str:
        """
        Format object as pretty-printed JSON string.
        
        Args:
            obj: Object to format
            indent: Indentation level
            
        Returns:
            Pretty-formatted JSON string
        """
        try:
            return json.dumps(
                obj,
                cls=UnifiedJSONEncoder,
                indent=indent,
                ensure_ascii=self.ensure_ascii,
                sort_keys=True,
                separators=(',', ': ')
            )
        except (TypeError, ValueError) as e:
            logger.error(f"JSON pretty formatting failed for {self.service_name}: {e}")
            raise JSONSerializationError(f"Failed to format object: {e}") from e
    
    def compact_format(self, obj: Any) -> str:
        """
        Format object as compact JSON string (no whitespace).
        
        Args:
            obj: Object to format
            
        Returns:
            Compact JSON string
        """
        try:
            return json.dumps(
                obj,
                cls=UnifiedJSONEncoder,
                indent=None,
                ensure_ascii=self.ensure_ascii,
                sort_keys=False,
                separators=(',', ':')
            )
        except (TypeError, ValueError) as e:
            logger.error(f"JSON compact formatting failed for {self.service_name}: {e}")
            raise JSONSerializationError(f"Failed to format object: {e}") from e
    
    def validate_json_string(self, json_str: str) -> bool:
        """
        Validate if string is valid JSON.
        
        Args:
            json_str: String to validate
            
        Returns:
            True if valid JSON, False otherwise
        """
        try:
            json.loads(json_str)
            return True
        except (json.JSONDecodeError, ValueError):
            return False
    
    def merge_json_objects(self, *objects: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple JSON objects into one.
        
        Args:
            *objects: JSON objects to merge
            
        Returns:
            Merged JSON object
        """
        result = {}
        for obj in objects:
            if isinstance(obj, dict):
                result.update(obj)
            else:
                logger.warning(f"Non-dict object ignored in merge: {type(obj)}")
        return result
    
    def serialize_for_websocket(self, data: Union[Dict[str, Any], Any]) -> str:
        """
        Serialize data for WebSocket transmission with datetime handling.
        
        Args:
            data: Data to serialize
            
        Returns:
            JSON string with datetime objects converted to ISO format
        """
        try:
            return self.dumps(data)
        except JSONSerializationError as e:
            logger.error(f"Failed to serialize data for WebSocket: {e}")
            raise
    
    def prepare_websocket_message(self, message: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """
        Prepare message for WebSocket transmission.
        
        Args:
            message: Message to prepare
            
        Returns:
            Message with datetime fields converted to ISO strings
        """
        if not isinstance(message, dict):
            return message
        return self._prepare_dict_message(message)
    
    def _prepare_dict_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare dictionary message for WebSocket transmission."""
        prepared = {}
        for key, value in message.items():
            prepared[key] = self._convert_datetime_fields(value)
        return prepared
    
    def _convert_datetime_fields(self, value: Any) -> Any:
        """Recursively convert datetime fields to ISO strings."""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: self._convert_datetime_fields(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._convert_datetime_fields(item) for item in value]
        elif isinstance(value, (Decimal, UUID)):
            return str(value)
        return value


# Custom exceptions for better error handling
class JSONError(Exception):
    """Base exception for JSON operations."""
    pass


class JSONSerializationError(JSONError):
    """Exception raised when JSON serialization fails."""
    pass


class JSONDeserializationError(JSONError):
    """Exception raised when JSON deserialization fails."""
    pass


class JSONFileError(JSONError):
    """Exception raised when JSON file operations fail."""
    pass


# Convenience functions for backward compatibility
def safe_json_dumps(obj: Any, indent: int = 2, default: Any = None) -> str:
    """Safe JSON dumps with fallback (backward compatibility)."""
    try:
        handler = UnifiedJSONHandler()
        return handler.dumps(obj, indent=indent)
    except JSONSerializationError:
        return json.dumps(default or {}, indent=indent)


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safe JSON loads with fallback (backward compatibility)."""
    try:
        handler = UnifiedJSONHandler()
        return handler.loads(json_str)
    except JSONDeserializationError:
        return default


def safe_json_load_file(file_path: Union[str, Path], default: Any = None) -> Any:
    """Safe JSON file load with fallback (backward compatibility)."""
    handler = UnifiedJSONHandler()
    return handler.safe_load_from_file(file_path, default)


def safe_json_dump_file(obj: Any, file_path: Union[str, Path], indent: int = 2) -> bool:
    """Safe JSON file dump (backward compatibility)."""
    try:
        handler = UnifiedJSONHandler()
        handler.dump_to_file(obj, file_path, indent=indent)
        return True
    except (JSONSerializationError, JSONFileError):
        return False


class CircularReferenceHandler:
    """Handles circular reference detection and safe serialization."""
    
    def __init__(self):
        self._circular_refs: Set[int] = set()
    
    def serialize_safe(self, data: Any, max_depth: int = 50) -> str:
        """
        Safely serialize data with circular reference handling.
        
        Args:
            data: Data to serialize
            max_depth: Maximum recursion depth
            
        Returns:
            JSON string with circular references handled
        """
        self._circular_refs.clear()
        try:
            safe_data = self._handle_circular_refs(data, 0, max_depth)
            handler = UnifiedJSONHandler()
            return handler.dumps(safe_data)
        except Exception as e:
            logger.error(f"Safe serialization failed: {e}")
            return '"[Safe Serialization Error]"'
        finally:
            self._circular_refs.clear()
    
    def _handle_circular_refs(self, obj: Any, depth: int, max_depth: int) -> Any:
        """Handle circular references in data structures."""
        if depth > max_depth:
            return "[Max Depth Exceeded]"
        
        obj_id = id(obj)
        
        if obj_id in self._circular_refs:
            return "[Circular Reference]"
        
        if isinstance(obj, (dict, list)):
            self._circular_refs.add(obj_id)
            try:
                if isinstance(obj, dict):
                    return self._handle_dict_circular_refs(obj, depth, max_depth)
                else:
                    return self._handle_list_circular_refs(obj, depth, max_depth)
            finally:
                self._circular_refs.discard(obj_id)
        
        return obj
    
    def _handle_dict_circular_refs(self, obj: Dict[Any, Any], depth: int, max_depth: int) -> Dict[Any, Any]:
        """Handle circular references in dictionaries."""
        result = {}
        for key, value in obj.items():
            try:
                result[key] = self._handle_circular_refs(value, depth + 1, max_depth)
            except Exception:
                result[key] = "[Processing Error]"
        return result
    
    def _handle_list_circular_refs(self, obj: list, depth: int, max_depth: int) -> list:
        """Handle circular references in lists."""
        result = []
        for item in obj:
            try:
                result.append(self._handle_circular_refs(item, depth + 1, max_depth))
            except Exception:
                result.append("[Processing Error]")
        return result


class LLMResponseParser:
    """Handles parsing of LLM responses and JSON extraction/recovery."""
    
    def safe_json_parse(self, value: Any, fallback: Any = None) -> Any:
        """Safely parse JSON string to dict/list with fallback."""
        if not isinstance(value, str):
            return value
        if not value.strip():
            return fallback if fallback is not None else value
        return self._try_json_parse(value, fallback)
    
    def _try_json_parse(self, value: str, fallback: Any) -> Any:
        """Helper to attempt JSON parsing with error handling."""
        stripped = value.strip()
        if self._is_non_json_format(stripped):
            return self._handle_detected_non_json_format(value, fallback, stripped)
        return self._attempt_json_parsing(value, fallback)
    
    def _is_non_json_format(self, stripped: str) -> bool:
        """Check if string appears to be non-JSON format."""
        return (self._is_command_line_format(stripped) or
                self._is_key_value_pair_format(stripped) or
                self._is_descriptive_text_format(stripped) or
                self._is_json_fragment(stripped))
    
    def _is_command_line_format(self, stripped: str) -> bool:
        """Check if string appears to be command-line arguments."""
        return (stripped.startswith('--') or
                ' --' in stripped or
                ('-' in stripped.split()[0] if stripped.split() else False))
    
    def _is_key_value_pair_format(self, stripped: str) -> bool:
        """Check if string appears to be a single key-value pair."""
        return ('=' in stripped and
                not stripped.startswith(('{', '[', '"')) and
                not stripped.endswith(('}', ']', '"')) and
                ',' not in stripped)
    
    def _is_descriptive_text_format(self, stripped: str) -> bool:
        """Check if string appears to be descriptive text with commas."""
        return (',' in stripped and
                not stripped.startswith(('{', '[', '"')) and
                not stripped.endswith(('}', ']', '"')) and
                len(stripped.split(',')) > 1)
    
    def _is_json_fragment(self, stripped: str) -> bool:
        """Check if string appears to be a JSON fragment."""
        if '"' in stripped and ':' in stripped:
            if (stripped.startswith('"') and
                    not stripped.startswith(('{', '[')) and
                    not stripped.endswith(('}', ']'))):
                return True
            if ', "' in stripped and not stripped.startswith(('{', '[')):
                return True
        return False
    
    def _handle_detected_non_json_format(self, value: str, fallback: Any, stripped: str) -> Any:
        """Handle detected non-JSON format string."""
        if self._is_command_line_format(stripped):
            logger.debug(f"String appears to be command-line arguments, not JSON: {value[:100]}...")
        elif self._is_key_value_pair_format(stripped):
            logger.debug(f"String appears to be key-value pair, not JSON: {value[:100]}...")
        elif self._is_json_fragment(stripped):
            return self._handle_json_fragment(value, fallback)
        else:
            logger.debug(f"String appears to be descriptive text, not JSON: {value[:100]}...")
        return fallback if fallback is not None else value
    
    def _handle_json_fragment(self, value: str, fallback: Any) -> Any:
        """Handle JSON fragment strings by attempting to wrap them."""
        stripped = value.strip()
        wrapped = f"{{{stripped}}}"
        
        try:
            parsed = json.loads(wrapped)
            logger.debug(f"Successfully parsed JSON fragment by wrapping: {value[:100]}...")
            return parsed
        except (json.JSONDecodeError, TypeError):
            logger.debug(f"JSON fragment cannot be parsed even with wrapping: {value[:100]}...")
            return fallback if fallback is not None else value
    
    def _attempt_json_parsing(self, value: str, fallback: Any) -> Any:
        """Attempt to parse string as JSON."""
        try:
            parsed = json.loads(value)
            logger.debug(f"Successfully parsed JSON string: {value[:100]}...")
            return parsed
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse JSON string: {value[:100]}... Error: {e}")
            return fallback if fallback is not None else value
    
    def ensure_agent_response_is_json(self, response: Any) -> Dict[str, Any]:
        """Ensure agent response is a proper JSON object."""
        if isinstance(response, dict):
            return response
        elif isinstance(response, str):
            return self._fix_string_response_to_json(response)
        elif isinstance(response, list):
            return {"items": response, "type": "list_response"}
        else:
            return {
                "type": "unknown_response",
                "content": str(response),
                "parsed": False,
                "message": f"Response type {type(response)} is not JSON serializable"
            }
    
    def _fix_string_response_to_json(self, data: str) -> Dict[str, Any]:
        """Fix string responses that should be JSON objects."""
        stripped = data.strip()
        if stripped.startswith('--') or ' --' in stripped:
            return {
                "type": "command_result",
                "raw_response": stripped,
                "parsed": False,
                "message": "Response contains command-line arguments instead of JSON"
            }
        if not stripped.startswith(('{', '[')):
            return {
                "type": "text_response",
                "content": stripped,
                "parsed": False,
                "message": "Response is plain text instead of JSON"
            }
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else {"content": parsed}
        except (json.JSONDecodeError, TypeError):
            return {
                "type": "malformed_json",
                "raw_response": stripped,
                "parsed": False,
                "message": "Response contains malformed JSON"
            }


class JSONErrorFixer:
    """Fixes common JSON formatting errors and recovers truncated JSON."""
    
    def fix_common_json_errors(self, json_str: str) -> str:
        """Fix common JSON formatting errors."""
        json_str = self._remove_trailing_commas(json_str)
        lines = self._add_missing_commas_to_lines(json_str.split('\n'))
        json_str = '\n'.join(lines)
        json_str = self._remove_single_quotes(json_str)
        json_str = self._remove_comments(json_str)
        json_str = self._quote_property_names(json_str)
        json_str = self._remove_bom_chars(json_str)
        return self._fix_unclosed_quotes(json_str)
    
    def _remove_trailing_commas(self, json_str: str) -> str:
        """Remove trailing commas before closing brackets/braces."""
        return re.sub(r',\s*([}\]])', r'\1', json_str)
    
    def _remove_single_quotes(self, json_str: str) -> str:
        """Replace single quotes with double quotes."""
        return re.sub(r"(?<!\\)'", '"', json_str)
    
    def _remove_comments(self, json_str: str) -> str:
        """Remove JavaScript-style comments."""
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        return re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    def _quote_property_names(self, json_str: str) -> str:
        """Ensure property names are quoted."""
        return re.sub(r'(?<!["\w])(\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*):', r'\1"\2"\3:', json_str)
    
    def _remove_bom_chars(self, json_str: str) -> str:
        """Remove BOM and zero-width characters."""
        return json_str.replace('\ufeff', '').replace('\u200b', '')
    
    def _fix_unclosed_quotes(self, json_str: str) -> str:
        """Fix unclosed string values."""
        quote_count = json_str.count('"') - json_str.count('\\"')
        if quote_count % 2 != 0:
            last_idx = json_str.rfind('"')
            if last_idx > 0 and json_str[last_idx - 1] != '\\':
                if ':' in json_str[max(0, last_idx - 50):last_idx]:
                    json_str = json_str[:last_idx + 1] + '"'
        return json_str
    
    def _add_missing_commas_to_lines(self, lines: List[str]) -> List[str]:
        """Add missing commas between JSON elements."""
        fixed = []
        for i, line in enumerate(lines):
            current = line.rstrip()
            if i < len(lines) - 1 and self._check_needs_comma(current, lines[i + 1].lstrip()):
                fixed.append(current + ',' if not current.endswith(',') else line)
            else:
                fixed.append(line)
        return fixed
    
    def _check_needs_comma(self, current: str, next_line: str) -> bool:
        """Check if a comma is needed between lines."""
        ends_structure = current.endswith('}') or current.endswith(']')
        ends_value = current.endswith('"') or re.search(r'(\d|true|false|null)$', current)
        starts_key = next_line.startswith('"') and ':' in next_line
        return (ends_structure or ends_value) and starts_key
    
    def count_structure_balance(self, json_str: str) -> Dict[str, int]:
        """Count unbalanced brackets and braces."""
        return {
            'braces': json_str.count('{') - json_str.count('}'),
            'brackets': json_str.count('[') - json_str.count(']'),
            'quotes': (json_str.count('"') - json_str.count('\\"')) % 2
        }
    
    def build_closing_sequence(self, balance: Dict[str, int]) -> str:
        """Build sequence to close open structures."""
        seq = '"' if balance['quotes'] else ''
        seq += ']' * balance['brackets']
        seq += '}' * balance['braces']
        return seq
    
    def recover_truncated_json(self, json_str: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Recover from truncated JSON by closing open structures."""
        if not json_str:
            return None
        
        # Try direct parse first
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Apply common fixes
        fixed_json = self.fix_common_json_errors(json_str)
        try:
            return json.loads(fixed_json)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Try recovery with closing sequences
        for attempt in range(max_retries):
            working = self._clean_trailing_comma(fixed_json)
            balance = self.count_structure_balance(working)
            closing = self.build_closing_sequence(balance)
            
            try:
                recovered = json.loads(working + closing)
                logger.info(f"Recovered JSON on attempt {attempt + 1} with: {closing}")
                return recovered
            except (json.JSONDecodeError, ValueError):
                # Try truncating at last comma
                last_comma = fixed_json.rfind(',')
                if last_comma > 0:
                    after = fixed_json[last_comma + 1:].strip()
                    if after and not after.startswith('}') and not after.startswith(']'):
                        fixed_json = fixed_json[:last_comma].rstrip()
                        continue
                break
        
        return None
    
    def _clean_trailing_comma(self, json_str: str) -> str:
        """Remove trailing comma if present."""
        stripped = json_str.rstrip()
        return stripped[:-1] if stripped.endswith(',') else json_str


# Global instances for common service patterns
auth_json_handler = UnifiedJSONHandler("auth_service")
backend_json_handler = UnifiedJSONHandler("netra_backend")
launcher_json_handler = UnifiedJSONHandler("dev_launcher")

# Global utility instances
circular_handler = CircularReferenceHandler()
llm_parser = LLMResponseParser()
error_fixer = JSONErrorFixer()

# Configuration class for backwards compatibility
class JSONSerializerConfig:
    """Configuration class for JSON serialization settings."""
    
    def __init__(self, indent: int = 2, ensure_ascii: bool = False, sort_keys: bool = False):
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self.sort_keys = sort_keys

# Convenience functions for backwards compatibility
def serialize_json(data: Any, config: Optional[JSONSerializerConfig] = None) -> str:
    """Serialize data to JSON string with optional configuration."""
    handler = UnifiedJSONHandler()
    if config:
        return handler.dumps(data, indent=config.indent)
    return handler.dumps(data)

def deserialize_json(json_str: str) -> Any:
    """Deserialize JSON string to Python object."""
    handler = UnifiedJSONHandler()
    return handler.loads(json_str)

def validate_json_schema(data: Any) -> bool:
    """Validate if data can be JSON serialized."""
    handler = UnifiedJSONHandler()
    return handler.validate_json_string(str(data)) if isinstance(data, str) else True

# Default handler instance
default_json_handler = backend_json_handler

# Additional convenience functions for specific use cases
def parse_dict_field(value: Any) -> Dict[str, Any]:
    """Parse a field that should be a dictionary - for LLM response parsing."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = llm_parser.safe_json_parse(value, {})
        return parsed if isinstance(parsed, dict) else {}
    return {}

def parse_list_field(value: Any) -> List[Any]:
    """Parse a field that should be a list - for LLM response parsing."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parsed = llm_parser.safe_json_parse(value, [])
        return parsed if isinstance(parsed, list) else []
    return []


def parse_string_list_field(value: Any) -> List[str]:
    """Parse a field that should be a list of strings - for LLM response parsing."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        parsed = llm_parser.safe_json_parse(value, [])
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def ensure_agent_response_is_json(response: Any) -> Dict[str, Any]:
    """Ensure agent response is a proper JSON object."""
    return llm_parser.ensure_agent_response_is_json(response)


def comprehensive_json_fix(data: Any) -> Any:
    """Comprehensive JSON fixing using error fixer."""
    error_fixer = JSONErrorFixer()
    if isinstance(data, str):
        fixed_str = error_fixer.fix_common_json_errors(data)
        try:
            return json.loads(fixed_str)
        except json.JSONDecodeError:
            recovered = error_fixer.recover_truncated_json(fixed_str)
            return recovered if recovered is not None else data
    return data

def fix_tool_parameters(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fix tool recommendation parameters that come as JSON strings."""
    if not isinstance(data, dict):
        return data
    if "tool_recommendations" in data and isinstance(data["tool_recommendations"], list):
        for rec in data["tool_recommendations"]:
            if isinstance(rec, dict) and "parameters" in rec:
                rec["parameters"] = parse_dict_field(rec["parameters"])
    return data

def ensure_agent_response_is_json(response: Any) -> Dict[str, Any]:
    """Ensure agent response is valid JSON."""
    parser = LLMResponseParser()
    return parser.ensure_agent_response_is_json(response)

def comprehensive_json_fix(data: Any) -> Any:
    """Apply comprehensive JSON string parsing fixes to data."""
    if isinstance(data, dict):
        data = fix_tool_parameters(data)
        for key, value in data.items():
            data[key] = comprehensive_json_fix(value)
        return data
    elif isinstance(data, list):
        return [comprehensive_json_fix(item) for item in data]
    elif isinstance(data, str):
        return llm_parser.ensure_agent_response_is_json(data)
    else:
        return data