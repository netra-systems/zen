"""
CLI Extensions for Zen Orchestrator
Provides example generation and template functionality.
"""

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

def list_available_examples() -> List[str]:
    """List all available example configurations."""
    examples_dir = Path(__file__).parent / "examples"
    if not examples_dir.exists():
        return []

    examples = []
    for file in examples_dir.glob("*.json"):
        examples.append(file.stem)
    return sorted(examples)

def generate_example_config(example_type: str) -> Optional[str]:
    """Generate example configuration of specified type."""
    examples_dir = Path(__file__).parent / "examples"
    example_file = examples_dir / f"{example_type}.json"

    if not example_file.exists():
        return None

    try:
        with open(example_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading example file {example_file}: {e}")
        return None

def show_prompt_template() -> Optional[str]:
    """Show the LLM prompt template for configuration generation."""
    templates_dir = Path(__file__).parent / "templates"
    template_file = templates_dir / "config_generator_prompt.txt"

    if not template_file.exists():
        return None

    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading template file {template_file}: {e}")
        return None

def handle_example_commands(args) -> bool:
    """
    Handle example and template CLI commands.

    Args:
        args: Parsed command line arguments

    Returns:
        True if a command was handled and execution should stop, False otherwise
    """

    # Handle --list-examples
    if hasattr(args, 'list_examples') and args.list_examples:
        examples = list_available_examples()
        if examples:
            print("Available Example Configurations:")
            print("=" * 50)
            for example in examples:
                # Format example name for display
                display_name = example.replace('_', ' ').title()
                print(f"  {example:25} - {display_name}")
            print("\nUsage:")
            print(f"  python zen_orchestrator.py --generate-example <type>")
            print(f"  python zen_orchestrator.py --config examples/<type>.json")
        else:
            print("No example configurations found.")
            print("Examples directory may not exist or be empty.")
        return True

    # Handle --generate-example
    if hasattr(args, 'generate_example') and args.generate_example:
        example_type = args.generate_example
        config_content = generate_example_config(example_type)

        if config_content:
            print(f"Example Configuration: {example_type}")
            print("=" * 60)
            # Handle Unicode characters in output
            try:
                print(config_content)
            except UnicodeEncodeError:
                # Fallback: Replace problematic characters
                safe_content = config_content.encode('ascii', 'replace').decode('ascii')
                print(safe_content)
            print("\n" + "=" * 60)
            print(f"To use this configuration:")
            print(f"  1. Save to a file (e.g., my_{example_type}.json)")
            print(f"  2. Run: python zen_orchestrator.py --config my_{example_type}.json")
            print(f"  3. Or copy from examples: python zen_orchestrator.py --config examples/{example_type}.json")
        else:
            available = list_available_examples()
            print(f"Example '{example_type}' not found.")
            if available:
                print("Available examples:")
                for ex in available:
                    print(f"  - {ex}")
            else:
                print("No examples available.")
        return True

    # Handle --show-prompt-template
    if hasattr(args, 'show_prompt_template') and args.show_prompt_template:
        template_content = show_prompt_template()

        if template_content:
            print("LLM Prompt Template for Configuration Generation")
            print("=" * 70)
            # Handle Unicode characters in output
            try:
                print(template_content)
            except UnicodeEncodeError:
                # Fallback: Replace problematic characters
                safe_content = template_content.encode('ascii', 'replace').decode('ascii')
                print(safe_content)
            print("\n" + "=" * 70)
            print("Usage:")
            print("  1. Copy the template above")
            print("  2. Customize it with your specific requirements")
            print("  3. Provide it to your LLM (ChatGPT, Claude, etc.)")
            print("  4. Save the generated JSON as a config file")
            print("  5. Run: python zen_orchestrator.py --config your_config.json")
        else:
            print("Prompt template not found.")
            print("Template file may not exist or be inaccessible.")
        return True

    return False