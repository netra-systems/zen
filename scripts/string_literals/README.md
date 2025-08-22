# String Literals Documentation System

A comprehensive system for scanning, categorizing, and documenting string literals in the Netra platform codebase.

## Overview

The string literals system consists of several modular components:

1. **Scanner Core** (`scanner_core.py`) - AST-based scanning for Python files
2. **Enhanced Categorizer** (`categorizer_enhanced.py`) - Context-aware categorization with confidence scoring
3. **Markdown Reporter** (`markdown_reporter.py`) - Human-readable documentation generator
4. **Integration Scripts** - Easy-to-use interfaces for the complete pipeline

## Quick Start

### Generate Documentation from Existing Index

```bash
# Generate markdown docs from existing JSON index
python scripts/generate_string_literals_docs.py

# Specify custom paths
python scripts/generate_string_literals_docs.py \
  --input SPEC/generated/string_literals.json \
  --output SPEC/generated
```

### Full Pipeline with Enhanced Categorization

```bash
# Complete pipeline: scan -> categorize -> generate docs
python scripts/enhanced_string_literals_docs.py

# Include test directories
python scripts/enhanced_string_literals_docs.py --include-tests

# Scan specific directories
python scripts/enhanced_string_literals_docs.py \
  --dirs frontend auth_service netra_backend
```

## Output Structure

The system generates comprehensive markdown documentation:

```
SPEC/generated/
├── string_literals_index.md              # Main index with overview
└── string_literals/
    ├── README.md                          # Category directory index
    ├── configuration.md                   # Configuration literals
    ├── paths.md                          # API endpoints, file paths
    ├── database.md                       # Database-related literals
    ├── events.md                         # Event names and handlers
    ├── identifiers.md                    # Component names, IDs
    ├── metrics.md                        # Performance metrics
    ├── states.md                         # Status values, states
    ├── messages.md                       # Log messages, errors
    └── [other categories...]
```

## Features

### 📊 Statistics Dashboard
- Total literals count and file coverage
- Categorization rate and confidence distribution
- Category breakdown with counts

### 🔍 Quick Reference
- Most frequently used literals
- Search patterns for common types
- Cross-category navigation

### 📂 Category-Specific Documentation
- Hierarchical subcategory organization
- Confidence-based grouping (High/Medium/Low)
- Usage examples with file locations
- Related literals and cross-references

### 🔗 Navigation Features
- Table of contents with anchor links
- Cross-links between related categories
- "Jump to" navigation within long files
- Breadcrumb navigation

### 🎨 Visual Enhancements
- Category icons and badges
- Confidence level indicators
- Structured tables for easy scanning
- Code blocks for literal values

## Categories

The system recognizes these main categories:

| Category | Icon | Description |
|----------|------|-------------|
| **Configuration** | ⚙️ | Environment variables, config keys, settings |
| **Paths** | 🛤️ | API endpoints, file paths, directories |
| **Identifiers** | 🏷️ | Component names, class names, field names |
| **Database** | 🗄️ | Table names, column names, SQL keywords |
| **Events** | ⚡ | Event handlers, event types, lifecycle events |
| **Metrics** | 📊 | Performance metrics, measurements |
| **States** | 🔄 | Status values, boolean states |
| **Messages** | 💬 | Log messages, error messages, notifications |
| **Documentation** | 📝 | Docstrings, comments, markdown |
| **Formats** | 📋 | Templates, regex, JSON, datetime formats |
| **Network** | 🌐 | IP addresses, ports, network constants |
| **Constants** | 🔒 | Enumeration values, constant definitions |

## Advanced Features

### Confidence Scoring
- **High (≥0.8)**: Confident categorization based on strong patterns
- **Medium (0.5-0.8)**: Moderate confidence with context hints
- **Low (<0.5)**: Fallback categorization or uncertain matches

### Context Awareness
- File path analysis for categorization hints
- Function/class context consideration
- Import statement analysis
- Cross-reference with related literals

### Smart Filtering
- Automatic exclusion of very short/long strings
- Skip common Python artifacts (`__main__`, `__name__`, etc.)
- Filter out whitespace-heavy strings
- Intelligent message detection

## API Reference

### Core Functions

```python
from string_literals.markdown_reporter import generate_markdown_docs
from string_literals.categorizer_enhanced import CategorizedLiteral

# Main interface
def generate_markdown_docs(literals: List[CategorizedLiteral], output_dir: Path) -> None
```

### Data Structures

```python
@dataclass
class CategorizedLiteral:
    value: str                    # The literal string value
    file: str                     # Source file path
    line: int                     # Line number
    category: str                 # Main category
    subcategory: Optional[str]    # Subcategory if applicable
    confidence: float             # Confidence score (0.0-1.0)
    context: str                  # Function/class context
    type_hint: str               # Type hint for the literal
```

## Integration with Existing Tools

The markdown reporter integrates seamlessly with:

- **String Literals Scanner** (`scripts/scan_string_literals.py`)
- **Query Tool** (`scripts/query_string_literals.py`)
- **Enhanced Categorizer** (this package)

## Performance

- Handles 10,000+ literals efficiently
- Generates documentation in seconds
- Memory-efficient streaming processing
- Optimized for large codebases

## Future Enhancements

- **Interactive Web Interface**: Browse documentation with search and filtering
- **Real-time Updates**: Watch for file changes and update docs automatically
- **Custom Categories**: User-defined categorization rules
- **Export Formats**: PDF, HTML, JSON exports
- **IDE Integration**: VS Code extension for inline documentation

## Examples

### Basic Usage

```python
from pathlib import Path
from string_literals.categorizer_enhanced import CategorizedLiteral
from string_literals.markdown_reporter import generate_markdown_docs

# Create sample literals
literals = [
    CategorizedLiteral("NETRA_API_KEY", "config.py", 10, "configuration", "env_var", 0.95),
    CategorizedLiteral("/api/v1/threads", "routes.py", 25, "paths", "api", 0.95),
]

# Generate documentation
output_dir = Path("docs/string_literals")
generate_markdown_docs(literals, output_dir)
```

### Command Line Usage

```bash
# Quick documentation generation
python scripts/generate_string_literals_docs.py

# Custom output location
python scripts/generate_string_literals_docs.py --output docs/literals

# Enhanced pipeline with specific directories
python scripts/enhanced_string_literals_docs.py --dirs frontend backend --include-tests
```

## Troubleshooting

### Common Issues

1. **Unicode Encoding Errors**: The system handles Windows console limitations gracefully
2. **Large Files**: Very large files are processed in chunks to avoid memory issues
3. **Missing Categories**: Unknown patterns fall back to smart categorization
4. **Path Issues**: All paths are normalized for cross-platform compatibility

### Debug Mode

Enable verbose output for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

To extend the categorization system:

1. Add new patterns to `categorizer_enhanced.py`
2. Update category descriptions in `markdown_reporter.py`
3. Add corresponding icons and visual elements
4. Update this README with new features

---

*This documentation system helps developers quickly find and understand the string literals used throughout the Netra platform, improving code maintainability and preventing string literal hallucination in LLM-generated code.*