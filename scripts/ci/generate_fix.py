#!/usr/bin/env python3
"""Generate AI-powered fixes for test failures."""

import argparse
import difflib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FixResult:
    """Result of a fix attempt."""
    success: bool
    patch: str
    explanation: str
    confidence: float
    provider: str


class AIFixGenerator:
    """Generate fixes using AI providers."""
    
    def __init__(self, provider: str):
        """Initialize with specified AI provider."""
        self.provider = provider
        self.api_key = self._get_api_key()
        
    def _get_api_key(self) -> str:
        """Get API key for the provider."""
        key_mapping = {
            "claude": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "gpt4": "OPENAI_API_KEY"
        }
        
        env_var = key_mapping.get(self.provider)
        if not env_var:
            raise ValueError(f"Unknown provider: {self.provider}")
            
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"Missing API key: {env_var}")
            
        return api_key
        
    def generate_fix(self, test_file: str, error: str, context: Dict[str, str]) -> FixResult:
        """Generate a fix for the test failure."""
        if self.provider == "claude":
            return self._generate_claude_fix(test_file, error, context)
        elif self.provider == "gemini":
            return self._generate_gemini_fix(test_file, error, context)
        elif self.provider == "gpt4":
            return self._generate_gpt4_fix(test_file, error, context)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
            
    def _generate_claude_fix(self, test_file: str, error: str, context: Dict[str, str]) -> FixResult:
        """Generate fix using Claude."""
        try:
            import anthropic
        except ImportError:
            return FixResult(False, "", "anthropic package not installed", 0, "claude")
            
        client = anthropic.Anthropic(api_key=self.api_key)
        
        # Build prompt
        prompt = self._build_prompt(test_file, error, context)
        
        try:
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                temperature=0.2,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            content = response.content[0].text
            patch, explanation, confidence = self._parse_fix_response(content)
            
            return FixResult(
                success=bool(patch),
                patch=patch,
                explanation=explanation,
                confidence=confidence,
                provider="claude"
            )
            
        except Exception as e:
            return FixResult(False, "", f"Error calling Claude: {e}", 0, "claude")
            
    def _generate_gemini_fix(self, test_file: str, error: str, context: Dict[str, str]) -> FixResult:
        """Generate fix using Gemini."""
        try:
            import google.genai as genai
        except ImportError:
            return FixResult(False, "", "google-genai package not installed", 0, "gemini")
            
        client = genai.Client(api_key=self.api_key)
        
        # Build prompt
        prompt = self._build_prompt(test_file, error, context)
        
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=[{'parts': [{'text': prompt}]}],
                config={
                    'temperature': 0.2,
                    'max_output_tokens': 4000
                }
            )
            
            # Parse response
            content = response.candidates[0].content.parts[0].text
            patch, explanation, confidence = self._parse_fix_response(content)
            
            return FixResult(
                success=bool(patch),
                patch=patch,
                explanation=explanation,
                confidence=confidence,
                provider="gemini"
            )
            
        except Exception as e:
            return FixResult(False, "", f"Error calling Gemini: {e}", 0, "gemini")
            
    def _generate_gpt4_fix(self, test_file: str, error: str, context: Dict[str, str]) -> FixResult:
        """Generate fix using GPT-4."""
        try:
            import openai
        except ImportError:
            return FixResult(False, "", "openai package not installed", 0, "gpt4")
            
        client = openai.OpenAI(api_key=self.api_key)
        
        # Build prompt
        prompt = self._build_prompt(test_file, error, context)
        
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Python developer fixing test failures. Generate minimal, focused fixes that resolve the error while maintaining code quality."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            # Parse response
            content = response.choices[0].message.content
            patch, explanation, confidence = self._parse_fix_response(content)
            
            return FixResult(
                success=bool(patch),
                patch=patch,
                explanation=explanation,
                confidence=confidence,
                provider="gpt4"
            )
            
        except Exception as e:
            return FixResult(False, "", f"Error calling GPT-4: {e}", 0, "gpt4")
            
    def _add_test_and_error_sections(self, test_file: str, error: str, context: Dict[str, str]) -> List[str]:
        """Add test file and error sections to prompt."""
        return [
            "Fix the following test failure in the Netra AI platform.",
            "", "## Test File", "```python",
            context.get("test_code", "# Test code not available"),
            "```", "", "## Error", "```",
            error[:2000], "```"  # Limit error length
        ]

    def _add_source_code_section(self, prompt_parts: List[str], context: Dict[str, str]) -> None:
        """Add source code section if available."""
        if "source_code" in context:
            prompt_parts.extend([
                "", "## Related Source Code", "```python",
                context["source_code"][:3000], "```"  # Limit source length
            ])

    def _add_git_diff_section(self, prompt_parts: List[str], context: Dict[str, str]) -> None:
        """Add git diff section if available."""
        if "git_diff" in context:
            prompt_parts.extend([
                "", "## Recent Changes", "```diff",
                context["git_diff"][:2000], "```"  # Limit diff length
            ])

    def _add_instructions_section(self, prompt_parts: List[str]) -> None:
        """Add instructions and response format sections."""
        prompt_parts.extend([
            "", "## Instructions",
            "1. Analyze the error and identify the root cause",
            "2. Generate a minimal fix that resolves the issue",
            "3. Ensure the fix maintains the test's original intent",
            "4. Follow the project's coding conventions"
        ])
        self._add_response_format_section(prompt_parts)

    def _add_response_format_section(self, prompt_parts: List[str]) -> None:
        """Add response format section to prompt."""
        prompt_parts.extend([
            "", "## Response Format", "Provide your response in the following format:",
            "", "FIX_START", "```diff", "# Your git diff patch here", "```", "FIX_END",
            "", "EXPLANATION_START", "# Brief explanation of the fix", "EXPLANATION_END",
            "", "CONFIDENCE_START", "# Confidence score (0-100)", "CONFIDENCE_END"
        ])

    def _build_prompt(self, test_file: str, error: str, context: Dict[str, str]) -> str:
        """Build the prompt for the AI model."""
        prompt_parts = self._add_test_and_error_sections(test_file, error, context)
        self._add_source_code_section(prompt_parts, context)
        self._add_git_diff_section(prompt_parts, context)
        self._add_instructions_section(prompt_parts)
        return "\n".join(prompt_parts)
        
    def _parse_fix_response(self, content: str) -> tuple[str, str, float]:
        """Parse the AI response to extract patch, explanation, and confidence."""
        patch = ""
        explanation = ""
        confidence = 50.0
        
        # Extract patch
        if "FIX_START" in content and "FIX_END" in content:
            start = content.find("FIX_START") + len("FIX_START")
            end = content.find("FIX_END")
            patch_section = content[start:end].strip()
            
            # Clean up the patch
            if "```diff" in patch_section:
                patch_section = patch_section.replace("```diff", "").replace("```", "")
            patch = patch_section.strip()
            
        # Extract explanation
        if "EXPLANATION_START" in content and "EXPLANATION_END" in content:
            start = content.find("EXPLANATION_START") + len("EXPLANATION_START")
            end = content.find("EXPLANATION_END")
            explanation = content[start:end].strip()
            
        # Extract confidence
        if "CONFIDENCE_START" in content and "CONFIDENCE_END" in content:
            start = content.find("CONFIDENCE_START") + len("CONFIDENCE_START")
            end = content.find("CONFIDENCE_END")
            confidence_str = content[start:end].strip()
            try:
                # Extract number from string like "85" or "85%"
                import re
                match = re.search(r'\d+', confidence_str)
                if match:
                    confidence = float(match.group())
            except:
                confidence = 50.0
                
        return patch, explanation, confidence


class FixValidator:
    """Validate generated fixes."""
    
    def __init__(self, test_file: str):
        """Initialize validator."""
        self.test_file = Path(test_file)
        
    def validate_fix(self, patch: str) -> bool:
        """Validate a fix by applying it and running tests."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy the file to temp location
            temp_file = Path(tmpdir) / self.test_file.name
            temp_file.write_text(self.test_file.read_text())
            
            # Apply the patch
            if not self._apply_patch(patch, temp_file):
                return False
                
            # Run the test
            return self._run_test(temp_file)
            
    def _apply_patch(self, patch: str, file_path: Path) -> bool:
        """Apply a patch to a file."""
        try:
            # Save patch to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
                f.write(patch)
                patch_file = f.name
                
            # Apply using git apply or patch command
            result = subprocess.run(
                ['git', 'apply', '--check', patch_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Patch can be applied
                subprocess.run(['git', 'apply', patch_file])
                return True
            else:
                # Try with patch command as fallback
                result = subprocess.run(
                    ['patch', '-p1', '-i', patch_file],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
                
        except Exception as e:
            print(f"Error applying patch: {e}")
            return False
        finally:
            # Clean up patch file
            if 'patch_file' in locals():
                os.unlink(patch_file)
                
    def _run_test(self, test_file: Path) -> bool:
        """Run a specific test file."""
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', str(test_file), '-xvs'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Error running test: {e}")
            return False


def load_context(test_file: str, error: str) -> Dict[str, str]:
    """Load context information for the fix."""
    context = {}
    
    # Load test file
    test_path = Path(test_file)
    if test_path.exists():
        context["test_code"] = test_path.read_text()
        
    # Try to extract source file from test file name
    # e.g., test_module.py -> module.py
    if test_file.startswith("test_"):
        source_file = test_file[5:]  # Remove "test_" prefix
        source_path = Path(source_file)
        if source_path.exists():
            context["source_code"] = source_path.read_text()
            
    # Get recent git changes
    try:
        result = subprocess.run(
            ['git', 'diff', 'HEAD~1', '--', test_file],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            context["git_diff"] = result.stdout
    except:
        pass
        
    return context


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate AI-powered test fixes")
    parser.add_argument("--test", required=True, help="Test file path")
    parser.add_argument("--error", required=True, help="Error message")
    parser.add_argument("--provider", required=True, 
                       choices=["claude", "gemini", "gpt4"],
                       help="AI provider to use")
    parser.add_argument("--output", required=True, help="Output patch file")
    parser.add_argument("--validate", action="store_true", 
                       help="Validate the fix before saving")
    
    args = parser.parse_args()
    
    # Load context
    context = load_context(args.test, args.error)
    
    # Generate fix
    generator = AIFixGenerator(args.provider)
    result = generator.generate_fix(args.test, args.error, context)
    
    if not result.success:
        print(f"Failed to generate fix: {result.explanation}")
        exit(1)
        
    # Validate if requested
    if args.validate:
        validator = FixValidator(args.test)
        if not validator.validate_fix(result.patch):
            print("Fix validation failed")
            exit(1)
            
    # Save patch
    output_path = Path(args.output)
    output_path.write_text(result.patch)
    
    print(f"Fix generated successfully")
    print(f"Provider: {result.provider}")
    print(f"Confidence: {result.confidence}%")
    print(f"Explanation: {result.explanation}")
    print(f"Patch saved to: {output_path}")


if __name__ == "__main__":
    main()