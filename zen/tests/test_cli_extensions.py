#!/usr/bin/env python3
"""
Test suite for CLI extensions functionality.
Tests example generation, template access, and CLI command handling.
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path to import cli_extensions
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from cli_extensions import (
        list_available_examples,
        generate_example_config,
        show_prompt_template,
        handle_example_commands
    )
except ImportError:
    # Graceful fallback for test environments
    list_available_examples = None
    generate_example_config = None
    show_prompt_template = None
    handle_example_commands = None


class TestCLIExtensions(unittest.TestCase):
    """Test CLI extensions functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(__file__).parent.parent
        self.examples_dir = self.test_dir / "examples"
        self.templates_dir = self.test_dir / "templates"

    def test_cli_extensions_import(self):
        """Test that CLI extensions can be imported"""
        self.assertIsNotNone(list_available_examples, "CLI extensions should be importable")
        self.assertIsNotNone(generate_example_config, "CLI extensions should be importable")
        self.assertIsNotNone(show_prompt_template, "CLI extensions should be importable")
        self.assertIsNotNone(handle_example_commands, "CLI extensions should be importable")

    @unittest.skipIf(list_available_examples is None, "CLI extensions not available")
    def test_list_available_examples(self):
        """Test listing available examples"""
        examples = list_available_examples()
        self.assertIsInstance(examples, list, "Should return a list")

        # Check if examples directory exists and has content
        if self.examples_dir.exists():
            json_files = list(self.examples_dir.glob("*.json"))
            self.assertEqual(len(examples), len(json_files),
                           "Should list all JSON files in examples directory")

    @unittest.skipIf(generate_example_config is None, "CLI extensions not available")
    def test_generate_example_config_valid(self):
        """Test generating a valid example configuration"""
        # Test with known example if it exists
        examples = list_available_examples()
        if examples:
            example_type = examples[0]
            config = generate_example_config(example_type)

            self.assertIsNotNone(config, "Should return configuration content")
            self.assertIsInstance(config, str, "Should return string content")

            # Verify it's valid JSON by parsing
            try:
                parsed = json.loads(config)
                self.assertIn("instances", parsed, "Should contain instances key")
            except json.JSONDecodeError:
                self.fail("Generated config should be valid JSON")

    @unittest.skipIf(generate_example_config is None, "CLI extensions not available")
    def test_generate_example_config_invalid(self):
        """Test generating example for non-existent type"""
        config = generate_example_config("non_existent_example")
        self.assertIsNone(config, "Should return None for non-existent example")

    @unittest.skipIf(show_prompt_template is None, "CLI extensions not available")
    def test_show_prompt_template(self):
        """Test showing prompt template"""
        template = show_prompt_template()

        if self.templates_dir.exists() and (self.templates_dir / "config_generator_prompt.txt").exists():
            self.assertIsNotNone(template, "Should return template content")
            self.assertIsInstance(template, str, "Should return string content")
            self.assertIn("Zen Orchestrator", template, "Template should mention Zen Orchestrator")
        else:
            self.assertIsNone(template, "Should return None if template file doesn't exist")

    @unittest.skipIf(handle_example_commands is None, "CLI extensions not available")
    def test_handle_example_commands_list_examples(self):
        """Test handling --list-examples command"""
        # Mock arguments object
        args = MagicMock()
        args.list_examples = True
        args.generate_example = None
        args.show_prompt_template = False

        # Capture stdout
        with patch('builtins.print') as mock_print:
            result = handle_example_commands(args)

        self.assertTrue(result, "Should return True when handling command")
        mock_print.assert_called()  # Should have printed something

    @unittest.skipIf(handle_example_commands is None, "CLI extensions not available")
    def test_handle_example_commands_generate_example(self):
        """Test handling --generate-example command"""
        # Mock arguments object
        args = MagicMock()
        args.list_examples = False
        args.generate_example = "data_analysis"  # Use a likely example name
        args.show_prompt_template = False

        # Capture stdout
        with patch('builtins.print') as mock_print:
            result = handle_example_commands(args)

        self.assertTrue(result, "Should return True when handling command")
        mock_print.assert_called()  # Should have printed something

    @unittest.skipIf(handle_example_commands is None, "CLI extensions not available")
    def test_handle_example_commands_show_template(self):
        """Test handling --show-prompt-template command"""
        # Mock arguments object
        args = MagicMock()
        args.list_examples = False
        args.generate_example = None
        args.show_prompt_template = True

        # Capture stdout
        with patch('builtins.print') as mock_print:
            result = handle_example_commands(args)

        self.assertTrue(result, "Should return True when handling command")
        mock_print.assert_called()  # Should have printed something

    @unittest.skipIf(handle_example_commands is None, "CLI extensions not available")
    def test_handle_example_commands_no_command(self):
        """Test handling when no CLI extension commands are present"""
        # Mock arguments object with no CLI extension flags
        args = MagicMock()
        args.list_examples = False
        args.generate_example = None
        args.show_prompt_template = False

        result = handle_example_commands(args)

        self.assertFalse(result, "Should return False when no commands to handle")


class TestExampleConfigurations(unittest.TestCase):
    """Test the example configurations themselves"""

    def setUp(self):
        """Set up test environment"""
        self.examples_dir = Path(__file__).parent.parent / "examples"

    def test_examples_directory_exists(self):
        """Test that examples directory exists"""
        self.assertTrue(self.examples_dir.exists(), "Examples directory should exist")

    def test_example_files_exist(self):
        """Test that expected example files exist"""
        expected_examples = [
            "data_analysis.json",
            "code_review.json",
            "content_creation.json",
            "testing_workflow.json",
            "migration_workflow.json",
            "debugging_workflow.json"
        ]

        for example_file in expected_examples:
            example_path = self.examples_dir / example_file
            self.assertTrue(example_path.exists(),
                          f"Example file {example_file} should exist")

    def test_example_files_valid_json(self):
        """Test that all example files contain valid JSON"""
        if not self.examples_dir.exists():
            self.skipTest("Examples directory does not exist")

        for json_file in self.examples_dir.glob("*.json"):
            with self.subTest(file=json_file.name):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)

                    # Basic structure validation
                    self.assertIn("instances", config,
                                f"{json_file.name} should have 'instances' key")
                    self.assertIsInstance(config["instances"], list,
                                        f"{json_file.name} instances should be a list")
                    self.assertGreater(len(config["instances"]), 0,
                                     f"{json_file.name} should have at least one instance")

                    # Validate each instance
                    for i, instance in enumerate(config["instances"]):
                        self.assertIn("name", instance,
                                    f"Instance {i} in {json_file.name} should have 'name'")
                        self.assertIn("command", instance,
                                    f"Instance {i} in {json_file.name} should have 'command'")
                        self.assertIn("description", instance,
                                    f"Instance {i} in {json_file.name} should have 'description'")

                except json.JSONDecodeError as e:
                    self.fail(f"{json_file.name} contains invalid JSON: {e}")
                except Exception as e:
                    self.fail(f"Error processing {json_file.name}: {e}")

    def test_example_configurations_completeness(self):
        """Test that example configurations have all recommended fields"""
        if not self.examples_dir.exists():
            self.skipTest("Examples directory does not exist")

        required_fields = ["name", "command", "description"]
        recommended_fields = [
            "permission_mode", "output_format", "max_tokens_per_command",
            "session_id", "clear_history", "compact_history"
        ]

        for json_file in self.examples_dir.glob("*.json"):
            with self.subTest(file=json_file.name):
                with open(json_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                for i, instance in enumerate(config["instances"]):
                    # Check required fields
                    for field in required_fields:
                        self.assertIn(field, instance,
                                    f"Instance {i} in {json_file.name} missing required field '{field}'")

                    # Check recommended fields (warnings only)
                    missing_recommended = []
                    for field in recommended_fields:
                        if field not in instance:
                            missing_recommended.append(field)

                    if missing_recommended:
                        print(f"Warning: Instance {i} in {json_file.name} missing recommended fields: {missing_recommended}")


class TestTemplates(unittest.TestCase):
    """Test the prompt templates"""

    def setUp(self):
        """Set up test environment"""
        self.templates_dir = Path(__file__).parent.parent / "templates"

    def test_templates_directory_exists(self):
        """Test that templates directory exists"""
        self.assertTrue(self.templates_dir.exists(), "Templates directory should exist")

    def test_prompt_template_exists(self):
        """Test that prompt template file exists"""
        template_file = self.templates_dir / "config_generator_prompt.txt"
        self.assertTrue(template_file.exists(), "Prompt template file should exist")

    def test_prompt_template_content(self):
        """Test that prompt template has expected content"""
        template_file = self.templates_dir / "config_generator_prompt.txt"

        if not template_file.exists():
            self.skipTest("Prompt template file does not exist")

        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for key sections
        expected_sections = [
            "Zen Orchestrator",
            "configuration generator",
            "instances",
            "max_tokens_per_command",
            "allowed_tools",
            "session_id"
        ]

        for section in expected_sections:
            self.assertIn(section, content,
                         f"Template should contain section about '{section}'")

    def test_llm_prompts_file_exists(self):
        """Test that LLM prompts documentation exists"""
        prompts_file = self.templates_dir / "llm_prompts.md"
        self.assertTrue(prompts_file.exists(), "LLM prompts documentation should exist")

    def test_llm_prompts_content(self):
        """Test that LLM prompts documentation has expected content"""
        prompts_file = self.templates_dir / "llm_prompts.md"

        if not prompts_file.exists():
            self.skipTest("LLM prompts file does not exist")

        with open(prompts_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for key sections
        expected_sections = [
            "Quick Start Template",
            "Advanced Configuration Template",
            "Specialized Workflow Templates",
            "Configuration Optimization",
            "Best Practices"
        ]

        for section in expected_sections:
            self.assertIn(section, content,
                         f"LLM prompts should contain section about '{section}'")


class TestCLIIntegration(unittest.TestCase):
    """Test CLI integration with zen_orchestrator.py"""

    def setUp(self):
        """Set up test environment"""
        self.zen_file = Path(__file__).parent.parent / "zen_orchestrator.py"

    def test_zen_orchestrator_exists(self):
        """Test that zen_orchestrator.py exists"""
        self.assertTrue(self.zen_file.exists(), "zen_orchestrator.py should exist")

    def test_cli_arguments_added(self):
        """Test that new CLI arguments are added to zen_orchestrator.py"""
        if not self.zen_file.exists():
            self.skipTest("zen_orchestrator.py does not exist")

        with open(self.zen_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for new CLI arguments
        expected_args = [
            "--generate-example",
            "--list-examples",
            "--show-prompt-template"
        ]

        for arg in expected_args:
            self.assertIn(arg, content,
                         f"zen_orchestrator.py should include {arg} argument")

    def test_cli_extensions_import(self):
        """Test that CLI extensions are imported in zen_orchestrator.py"""
        if not self.zen_file.exists():
            self.skipTest("zen_orchestrator.py does not exist")

        with open(self.zen_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for CLI extensions import
        self.assertIn("handle_example_commands", content,
                     "zen_orchestrator.py should import handle_example_commands")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)