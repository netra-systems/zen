#!/usr/bin/env python3
"""
Script to add CLI extensions to zen_orchestrator.py
This approach is more stable than direct editing.
"""

import re
from pathlib import Path

def apply_cli_patch():
    """Apply CLI extensions to zen_orchestrator.py"""

    zen_file = Path(__file__).parent / "zen_orchestrator.py"

    # Read the current content
    with open(zen_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already patched
    if "--generate-example" in content:
        print("CLI extensions already applied!")
        return True

    # 1. Add import after token_transparency imports
    import_pattern = r'(    TokenUsageData = None\n\n# NetraOptimizer database functionality)'
    import_replacement = '''    TokenUsageData = None

# Add CLI extensions imports
try:
    from cli_extensions import handle_example_commands
except ImportError as e:
    # Graceful fallback if CLI extensions are not available
    handle_example_commands = None

# NetraOptimizer database functionality'''

    content = re.sub(import_pattern, import_replacement, content)

    # 2. Add arguments after disable-budget-visuals
    args_pattern = r'(    parser\.add_argument\("--disable-budget-visuals", action="store_true",\s*help="Disable budget visualization in status reports"\)\s*\n\s*args = parser\.parse_args\(\))'
    args_replacement = '''    parser.add_argument("--disable-budget-visuals", action="store_true",
                       help="Disable budget visualization in status reports")

    # New example and template commands
    parser.add_argument("--generate-example", type=str, metavar="TYPE",
                       help="Generate example configuration (data_analysis, code_review, content_creation, testing_workflow, migration_workflow, debugging_workflow)")
    parser.add_argument("--list-examples", action="store_true",
                       help="List all available example configurations")
    parser.add_argument("--show-prompt-template", action="store_true",
                       help="Show LLM prompt template for configuration generation")

    args = parser.parse_args()'''

    content = re.sub(args_pattern, args_replacement, content, flags=re.MULTILINE | re.DOTALL)

    # 3. Add handler call after workspace validation
    handler_pattern = r'(    logger\.info\(f"Using workspace: {workspace}"\)\n)'
    handler_replacement = '''    logger.info(f"Using workspace: {workspace}")

    # Handle CLI extension commands
    if handle_example_commands and handle_example_commands(args):
        return

'''

    content = re.sub(handler_pattern, handler_replacement, content)

    # Write the modified content back
    with open(zen_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("CLI extensions successfully applied to zen_orchestrator.py!")
    return True

if __name__ == "__main__":
    apply_cli_patch()