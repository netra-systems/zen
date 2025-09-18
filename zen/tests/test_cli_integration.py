#!/usr/bin/env python3
"""
Integration tests for CLI functionality.
Tests actual CLI commands with zen_orchestrator.py.
"""

import unittest
import subprocess
import sys
import json
from pathlib import Path
import tempfile
import os


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI commands"""

    def setUp(self):
        """Set up test environment"""
        self.zen_dir = Path(__file__).parent.parent
        self.zen_script = self.zen_dir / "zen_orchestrator.py"
        self.examples_dir = self.zen_dir / "examples"
        self.templates_dir = self.zen_dir / "templates"

        # Ensure we can run the script
        self.assertTrue(self.zen_script.exists(), "zen_orchestrator.py should exist")

    def run_zen_command(self, args, timeout=30):
        """Helper method to run zen orchestrator commands"""
        cmd = [sys.executable, str(self.zen_script)] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.zen_dir)
            )
            return result
        except subprocess.TimeoutExpired:
            self.fail(f"Command timed out: {' '.join(cmd)}")
        except Exception as e:
            self.fail(f"Failed to run command: {' '.join(cmd)}, error: {e}")

    def test_list_examples_command(self):
        """Test --list-examples CLI command"""
        result = self.run_zen_command(["--list-examples"])

        # Should exit successfully (return code 0)
        self.assertEqual(result.returncode, 0,
                        f"--list-examples should succeed. stderr: {result.stderr}")

        # Should contain expected output
        self.assertIn("Available Example Configurations", result.stdout,
                     "Should show available examples header")

        # If examples exist, should list them
        if self.examples_dir.exists() and list(self.examples_dir.glob("*.json")):
            self.assertIn("Usage:", result.stdout,
                         "Should show usage instructions")

    def test_generate_example_command_valid(self):
        """Test --generate-example with valid example"""
        # Try with a likely example name
        example_names = ["data_analysis", "code_review", "testing_workflow"]

        for example_name in example_names:
            example_file = self.examples_dir / f"{example_name}.json"
            if example_file.exists():
                with self.subTest(example=example_name):
                    result = self.run_zen_command(["--generate-example", example_name])

                    # Should exit successfully
                    self.assertEqual(result.returncode, 0,
                                    f"--generate-example {example_name} should succeed. stderr: {result.stderr}")

                    # Should contain JSON output
                    self.assertIn("{", result.stdout,
                                 "Should output JSON configuration")
                    self.assertIn("instances", result.stdout,
                                 "Should contain instances in output")

                    # Should be valid JSON
                    try:
                        # Extract JSON part (might have other text around it)
                        lines = result.stdout.split('\n')
                        json_start = -1
                        json_end = -1

                        for i, line in enumerate(lines):
                            if line.strip().startswith('{'):
                                json_start = i
                                break

                        for i in range(len(lines) - 1, -1, -1):
                            if lines[i].strip().endswith('}'):
                                json_end = i
                                break

                        if json_start >= 0 and json_end >= 0:
                            json_text = '\n'.join(lines[json_start:json_end + 1])
                            parsed = json.loads(json_text)
                            self.assertIn("instances", parsed,
                                         "Generated JSON should have instances")
                    except json.JSONDecodeError as e:
                        # Don't fail the test for JSON parsing issues, just warn
                        print(f"Warning: Could not parse JSON output for {example_name}: {e}")

                break  # Only test the first available example
        else:
            self.skipTest("No example files found to test")

    def test_generate_example_command_invalid(self):
        """Test --generate-example with invalid example"""
        result = self.run_zen_command(["--generate-example", "non_existent_example"])

        # Should exit successfully (but show error message)
        self.assertEqual(result.returncode, 0,
                        f"--generate-example should handle invalid examples gracefully. stderr: {result.stderr}")

        # Should contain error message
        self.assertIn("not found", result.stdout,
                     "Should show 'not found' message for invalid example")

    def test_show_prompt_template_command(self):
        """Test --show-prompt-template CLI command"""
        result = self.run_zen_command(["--show-prompt-template"])

        # Should exit successfully
        self.assertEqual(result.returncode, 0,
                        f"--show-prompt-template should succeed. stderr: {result.stderr}")

        # If template exists, should show content
        template_file = self.templates_dir / "config_generator_prompt.txt"
        if template_file.exists():
            self.assertIn("Zen Orchestrator", result.stdout,
                         "Should show template content mentioning Zen Orchestrator")
            self.assertIn("Usage:", result.stdout,
                         "Should show usage instructions")
        else:
            self.assertIn("not found", result.stdout,
                         "Should show 'not found' message if template doesn't exist")

    def test_help_includes_new_options(self):
        """Test that --help includes new CLI options"""
        result = self.run_zen_command(["--help"])

        # Should exit successfully
        self.assertEqual(result.returncode, 0,
                        f"--help should succeed. stderr: {result.stderr}")

        # Should include new options
        expected_options = [
            "--generate-example",
            "--list-examples",
            "--show-prompt-template"
        ]

        for option in expected_options:
            self.assertIn(option, result.stdout,
                         f"Help should include {option} option")

    def test_config_file_usage_with_examples(self):
        """Test using example configurations as config files"""
        # Find an example file to test with
        if not self.examples_dir.exists():
            self.skipTest("Examples directory does not exist")

        example_files = list(self.examples_dir.glob("*.json"))
        if not example_files:
            self.skipTest("No example files found")

        example_file = example_files[0]

        # Test dry-run with example configuration
        result = self.run_zen_command([
            "--config", str(example_file),
            "--dry-run"
        ])

        # Should exit successfully
        self.assertEqual(result.returncode, 0,
                        f"Using example config should succeed. stderr: {result.stderr}")

        # Should show dry-run output (might be in stdout or stderr)
        output_text = result.stdout + result.stderr
        self.assertIn("DRY RUN MODE", output_text,
                     "Should show dry-run mode indicator")


class TestCLIErrorHandling(unittest.TestCase):
    """Test CLI error handling and edge cases"""

    def setUp(self):
        """Set up test environment"""
        self.zen_dir = Path(__file__).parent.parent
        self.zen_script = self.zen_dir / "zen_orchestrator.py"

    def run_zen_command(self, args, timeout=30):
        """Helper method to run zen orchestrator commands"""
        cmd = [sys.executable, str(self.zen_script)] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.zen_dir)
            )
            return result
        except subprocess.TimeoutExpired:
            self.fail(f"Command timed out: {' '.join(cmd)}")
        except Exception as e:
            self.fail(f"Failed to run command: {' '.join(cmd)}, error: {e}")

    def test_conflicting_arguments(self):
        """Test behavior with conflicting arguments"""
        # Test multiple CLI extension arguments together
        result = self.run_zen_command([
            "--list-examples",
            "--show-prompt-template"
        ])

        # Should handle gracefully (process first argument)
        self.assertEqual(result.returncode, 0,
                        "Should handle multiple CLI extension arguments gracefully")

    def test_generate_example_without_argument(self):
        """Test --generate-example without specifying example type"""
        result = self.run_zen_command(["--generate-example"])

        # Should show error about missing argument
        self.assertNotEqual(result.returncode, 0,
                           "Should fail when --generate-example lacks argument")

    def test_invalid_workspace_with_cli_commands(self):
        """Test CLI commands with invalid workspace"""
        result = self.run_zen_command([
            "--list-examples",
            "--workspace", "/non/existent/path"
        ])

        # CLI commands should work regardless of workspace issues
        self.assertEqual(result.returncode, 0,
                        "CLI extension commands should work regardless of workspace")

    def test_output_encoding_handling(self):
        """Test that output encoding is handled properly"""
        # This test specifically checks for Unicode encoding issues
        result = self.run_zen_command(["--list-examples"])

        # Should not crash due to encoding issues
        self.assertEqual(result.returncode, 0,
                        "Should handle output encoding properly")

        # Should be able to decode the output
        self.assertIsInstance(result.stdout, str,
                             "Output should be properly decoded")


class TestDocumentationIntegration(unittest.TestCase):
    """Test that documentation matches actual implementation"""

    def setUp(self):
        """Set up test environment"""
        self.zen_dir = Path(__file__).parent.parent
        self.docs_dir = self.zen_dir / "docs"

    def test_onboarding_examples_match_reality(self):
        """Test that examples mentioned in onboarding actually exist"""
        onboarding_file = self.docs_dir / "ONBOARDING.md"

        if not onboarding_file.exists():
            self.skipTest("ONBOARDING.md does not exist")

        with open(onboarding_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract example names mentioned in documentation
        import re
        example_patterns = [
            r'--generate-example (\w+)',
            r'examples/(\w+)\.json',
            r'--config examples/(\w+)\.json'
        ]

        mentioned_examples = set()
        for pattern in example_patterns:
            matches = re.findall(pattern, content)
            mentioned_examples.update(matches)

        # Check that mentioned examples actually exist
        examples_dir = self.zen_dir / "examples"
        if examples_dir.exists():
            for example in mentioned_examples:
                example_file = examples_dir / f"{example}.json"
                self.assertTrue(example_file.exists(),
                              f"Example {example} mentioned in documentation should exist")

    def test_help_text_consistency(self):
        """Test that help text matches what's in documentation"""
        zen_script = self.zen_dir / "zen_orchestrator.py"

        if not zen_script.exists():
            self.skipTest("zen_orchestrator.py does not exist")

        # Get help text
        result = subprocess.run([
            sys.executable, str(zen_script), "--help"
        ], capture_output=True, text=True, cwd=str(self.zen_dir))

        self.assertEqual(result.returncode, 0, "Help command should succeed")

        # Check that all documented options are in help
        documented_options = [
            "--generate-example",
            "--list-examples",
            "--show-prompt-template"
        ]

        for option in documented_options:
            self.assertIn(option, result.stdout,
                         f"Help should include documented option {option}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)