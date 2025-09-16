"""
NetraOptimizer Command Parser

Intelligently dissects command strings into structured data for analysis.
Extracts semantic features that impact token usage and performance.
"""

import re
from typing import Dict, Any, List, Optional


def parse_command(command_raw: str) -> Dict[str, Any]:
    """
    Parse a command string into structured components.

    Args:
        command_raw: The complete command string

    Returns:
        Dictionary containing parsed command components
    """
    # Clean the command
    command = command_raw.strip()

    # Initialize result
    result = {
        'base': '',
        'targets': [],
        'flags': {},
        'scope': None,
        'test_type': None,
        'priority': None,
        'components': []
    }

    # Remove leading slash if present
    if command.startswith('/'):
        command = command[1:]

    # Split into parts
    parts = command.split()
    if not parts:
        return result

    # Extract base command
    result['base'] = '/' + parts[0]

    # Parse remaining arguments
    remaining = parts[1:] if len(parts) > 1 else []

    # Parse based on known command patterns
    if 'gitissueprogressorv3' in parts[0].lower():
        result = _parse_git_issue_command(remaining, result)
    elif 'createtest' in parts[0].lower():
        result = _parse_create_test_command(remaining, result)
    elif 'gardener' in parts[0].lower():
        result = _parse_gardener_command(remaining, result)
    elif 'deploy' in parts[0].lower():
        result = _parse_deploy_command(remaining, result)
    else:
        result = _parse_generic_command(remaining, result)

    return result


def _parse_git_issue_command(args: List[str], result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse gitissueprogressorv3 specific arguments."""
    for arg in args:
        arg_lower = arg.lower()

        # Check for priority levels
        if arg_lower in ['p0', 'p1', 'p2', 'critical', 'high', 'medium', 'low']:
            result['priority'] = arg_lower
            result['targets'].append(arg)

        # Check for components
        elif arg_lower in ['agents', 'websocket', 'auth', 'database', 'frontend']:
            result['components'].append(arg_lower)
            result['targets'].append(arg)

        # Check for scope keywords
        elif arg_lower in ['all', 'open', 'closed', 'blocking']:
            result['scope'] = arg_lower

        else:
            result['targets'].append(arg)

    return result


def _parse_create_test_command(args: List[str], result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse createtest command arguments."""
    # Join args to handle multi-word targets
    full_arg = ' '.join(args)

    # Check for test types
    test_types = ['unit', 'integration', 'e2e', 'performance', 'smoke']
    for test_type in test_types:
        if test_type in full_arg.lower():
            result['test_type'] = test_type

    # Extract components and features
    component_match = re.search(r'(\w+)\s+(goldenpath|auth|websocket|database)', full_arg.lower())
    if component_match:
        result['components'].append(component_match.group(1))
        result['targets'].append(component_match.group(2))

    # Check for complex conditions
    if ' and ' in full_arg.lower() or ' or ' in full_arg.lower():
        result['flags']['complex_condition'] = True

    # Parse remaining as targets
    if not result['targets']:
        result['targets'] = args

    return result


def _parse_gardener_command(args: List[str], result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse gardener command arguments."""
    for arg in args:
        arg_lower = arg.lower()

        if arg_lower in ['refresh', 'commit', 'clean', 'optimize']:
            result['flags']['action'] = arg_lower
        elif arg_lower in ['force', 'dry-run', 'verbose']:
            result['flags'][arg_lower] = True
        else:
            result['targets'].append(arg)

    return result


def _parse_deploy_command(args: List[str], result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse deployment command arguments."""
    for arg in args:
        arg_lower = arg.lower()

        if arg_lower in ['staging', 'production', 'dev']:
            result['flags']['environment'] = arg_lower
        elif arg_lower in ['rollback', 'canary', 'blue-green']:
            result['flags']['strategy'] = arg_lower
        elif arg.startswith('--'):
            # Parse flag with potential value
            flag_parts = arg[2:].split('=')
            if len(flag_parts) == 2:
                result['flags'][flag_parts[0]] = flag_parts[1]
            else:
                result['flags'][flag_parts[0]] = True
        else:
            result['targets'].append(arg)

    return result


def _parse_generic_command(args: List[str], result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse generic command arguments."""
    for arg in args:
        if arg.startswith('--'):
            # Long flag
            flag_parts = arg[2:].split('=')
            if len(flag_parts) == 2:
                result['flags'][flag_parts[0]] = flag_parts[1]
            else:
                result['flags'][flag_parts[0]] = True
        elif arg.startswith('-'):
            # Short flag
            result['flags'][arg[1:]] = True
        else:
            # Regular argument
            result['targets'].append(arg)

    return result


def extract_features(command_raw: str, parsed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract semantic features that affect token usage.

    Args:
        command_raw: The complete command string
        parsed: Optional pre-parsed command data

    Returns:
        Dictionary of features that impact token usage
    """
    # Parse if not already done
    if parsed is None:
        parsed = parse_command(command_raw)

    features = {
        # Command structure features
        'base_command': parsed['base'],
        'arg_count': len(command_raw.split()) - 1,
        'has_multiple_targets': len(parsed['targets']) > 1,
        'target_count': len(parsed['targets']),

        # Semantic features
        'test_type': parsed.get('test_type'),
        'scope_breadth': _estimate_scope_breadth(parsed),
        'operation_type': _classify_operation(parsed),

        # Complexity indicators
        'has_compound_criteria': ' and ' in command_raw.lower() or ' or ' in command_raw.lower(),
        'specificity_level': _measure_specificity(parsed),
        'estimated_complexity': _estimate_complexity(parsed),

        # Component involvement
        'affects_components': parsed.get('components', []),
        'component_count': len(parsed.get('components', [])),

        # Priority and urgency
        'priority_level': parsed.get('priority'),
        'is_high_priority': parsed.get('priority') and parsed.get('priority').lower() in ['p0', 'critical', 'high'],

        # Execution characteristics
        'parallel_friendly': _is_parallel_friendly(parsed),
        'cache_heavy': _is_cache_heavy(parsed),
        'expected_duration_category': _estimate_duration_category(parsed)
    }

    return features


def _estimate_scope_breadth(parsed: Dict[str, Any]) -> str:
    """Estimate the scope breadth of the command."""
    scope = parsed.get('scope')
    target_count = len(parsed.get('targets', []))
    component_count = len(parsed.get('components', []))

    if scope == 'all' or target_count > 3 or component_count > 2:
        return 'broad'
    elif target_count > 1 or component_count > 0:
        return 'medium'
    else:
        return 'narrow'


def _classify_operation(parsed: Dict[str, Any]) -> str:
    """Classify the type of operation."""
    base = parsed.get('base', '').lower()

    if 'test' in base:
        return 'test'
    elif 'deploy' in base:
        return 'deploy'
    elif 'analyze' in base or 'progress' in base:
        return 'analyze'
    elif 'create' in base or 'generate' in base:
        return 'write'
    elif 'refresh' in base or 'clean' in base:
        return 'maintenance'
    else:
        return 'read'


def _measure_specificity(parsed: Dict[str, Any]) -> str:
    """Measure how specific the command is."""
    has_priority = bool(parsed.get('priority'))
    has_components = bool(parsed.get('components'))
    target_count = len(parsed.get('targets', []))
    has_flags = bool(parsed.get('flags'))

    specificity_score = sum([has_priority, has_components, target_count > 0, has_flags])

    if specificity_score >= 3:
        return 'high'
    elif specificity_score >= 1:
        return 'medium'
    else:
        return 'low'


def _estimate_complexity(parsed: Dict[str, Any]) -> float:
    """Estimate command complexity on a 0-10 scale."""
    base_score = 1.0

    # Base command complexity
    base = parsed.get('base', '').lower()
    if 'progress' in base or 'analyze' in base:
        base_score += 3.0
    elif 'create' in base or 'test' in base:
        base_score += 2.0
    elif 'deploy' in base:
        base_score += 2.5

    # Scope multiplier
    scope_breadth = _estimate_scope_breadth(parsed)
    if scope_breadth == 'broad':
        base_score *= 2.0
    elif scope_breadth == 'medium':
        base_score *= 1.5

    # Component multiplier
    component_count = len(parsed.get('components', []))
    base_score += component_count * 0.5

    # Priority boost
    priority = parsed.get('priority')
    if priority and priority.lower() in ['p0', 'critical']:
        base_score += 1.0

    # Cap at 10
    return min(10.0, base_score)


def _is_parallel_friendly(parsed: Dict[str, Any]) -> bool:
    """Determine if command is suitable for parallel execution."""
    base = parsed.get('base', '').lower()

    # Commands that are parallel-friendly
    parallel_commands = ['test', 'analyze', 'progress', 'validate']

    # Commands that should not be parallelized
    sequential_commands = ['deploy', 'migrate', 'backup', 'restore']

    for cmd in parallel_commands:
        if cmd in base:
            return True

    for cmd in sequential_commands:
        if cmd in base:
            return False

    # Default to parallel-friendly
    return True


def _is_cache_heavy(parsed: Dict[str, Any]) -> bool:
    """Determine if command benefits significantly from caching."""
    base = parsed.get('base', '').lower()

    # Cache-heavy commands
    cache_commands = ['analyze', 'progress', 'test', 'validate', 'report']

    for cmd in cache_commands:
        if cmd in base:
            return True

    # Commands that benefit from caching if they have similar predecessors
    if parsed.get('components') or parsed.get('priority'):
        return True

    return False


def _estimate_duration_category(parsed: Dict[str, Any]) -> str:
    """Estimate the duration category of the command."""
    complexity = _estimate_complexity(parsed)

    if complexity >= 7:
        return 'long'  # > 10 minutes
    elif complexity >= 4:
        return 'medium'  # 2-10 minutes
    else:
        return 'short'  # < 2 minutes