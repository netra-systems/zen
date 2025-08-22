#!/usr/bin/env python3
"""
Markdown Documentation Generator for String Literals
Generates human-readable and LLM-friendly documentation from categorized string literals.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    from scripts.string_literals.categorizer_enhanced import CategorizedLiteral
except ImportError:
    # Handle direct execution
    from categorizer_enhanced import CategorizedLiteral


class MarkdownReporter:
    """Generates comprehensive markdown documentation for string literals."""
    
    def __init__(self):
        """Initialize the markdown reporter with formatting templates."""
        self.confidence_badges = {
            'high': '🟢 High (≥0.8)',
            'medium': '🟡 Medium (0.5-0.8)', 
            'low': '🔴 Low (<0.5)'
        }
        
        self.category_icons = {
            'configuration': '⚙️',
            'paths': '🛤️',
            'identifiers': '🏷️',
            'database': '🗄️',
            'events': '⚡',
            'metrics': '📊',
            'states': '🔄',
            'messages': '💬',
            'documentation': '📝',
            'formats': '📋',
            'network': '🌐',
            'constants': '🔒',
            'cli': '💻',
            'web': '🌍',
            'language': '🐍',
            'content': '📄',
            'metadata': '📋',
            'uncategorized': '❓',
            'ignored': '⛔'
        }
        
        self.category_descriptions = {
            'configuration': 'System configuration keys, environment variables, and settings',
            'paths': 'API endpoints, file paths, directories, and URLs',
            'identifiers': 'Component names, class names, field names, and identifiers',
            'database': 'Table names, column names, SQL keywords, and database queries',
            'events': 'Event handlers, event types, and lifecycle events',
            'metrics': 'Performance metrics, measurements, and monitoring data',
            'states': 'Status values, boolean states, and lifecycle states',
            'messages': 'Log messages, user messages, error messages, and notifications',
            'documentation': 'Docstrings, comments, and markdown content',
            'formats': 'Template strings, regex patterns, JSON, and datetime formats',
            'network': 'IP addresses, ports, and network-related constants',
            'constants': 'Enumeration values and constant definitions',
            'cli': 'Command line arguments and CLI-related strings',
            'web': 'Query parameters, form fields, and web-related strings',
            'language': 'Python keywords and language constructs',
            'content': 'General text content and user-facing text',
            'metadata': 'Version numbers, hashes, and metadata information',
            'uncategorized': 'Strings that could not be automatically categorized',
            'ignored': 'Strings that were intentionally skipped during processing'
        }

    def _get_confidence_level(self, confidence: float) -> str:
        """Get confidence level from confidence score."""
        if confidence >= 0.8:
            return 'high'
        elif confidence >= 0.5:
            return 'medium'
        else:
            return 'low'

    def _sanitize_for_markdown(self, text: str) -> str:
        """Sanitize text for safe markdown rendering."""
        # Escape markdown special characters
        special_chars = ['\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!', '|']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    def _format_code_block(self, content: str, language: str = '') -> str:
        """Format content as a code block."""
        return f"```{language}\n{content}\n```"

    def _generate_toc_entry(self, title: str, anchor: str, level: int = 1) -> str:
        """Generate a table of contents entry."""
        indent = "  " * (level - 1)
        return f"{indent}- [{title}](#{anchor})"

    def _create_anchor(self, text: str) -> str:
        """Create a markdown anchor from text."""
        # Convert to lowercase, replace spaces and special chars with hyphens
        anchor = text.lower()
        anchor = ''.join(c if c.isalnum() else '-' for c in anchor)
        anchor = '-'.join(filter(None, anchor.split('-')))  # Remove empty parts
        return anchor

    def _group_literals_by_category(self, literals: List[CategorizedLiteral]) -> Dict[str, Dict[str, List[CategorizedLiteral]]]:
        """Group literals by category and subcategory."""
        grouped = defaultdict(lambda: defaultdict(list))
        
        for literal in literals:
            if literal.category == 'ignored':
                continue
            grouped[literal.category][literal.subcategory or 'general'].append(literal)
        
        return dict(grouped)

    def _calculate_statistics(self, literals: List[CategorizedLiteral]) -> Dict:
        """Calculate comprehensive statistics."""
        stats = {
            'total_literals': len(literals),
            'total_categories': 0,
            'total_subcategories': 0,
            'by_category': defaultdict(int),
            'by_confidence': {'high': 0, 'medium': 0, 'low': 0},
            'avg_confidence': 0.0,
            'top_categories': [],
            'categorization_rate': 0.0,
            'unique_files': set(),
            'total_files': 0
        }
        
        if not literals:
            return stats
        
        total_confidence = 0.0
        categorized_count = 0
        categories_set = set()
        subcategories_set = set()
        
        for literal in literals:
            if literal.category == 'ignored':
                continue
                
            # Category tracking
            categories_set.add(literal.category)
            if literal.subcategory:
                subcategories_set.add(f"{literal.category}.{literal.subcategory}")
            
            stats['by_category'][literal.category] += 1
            
            # Confidence tracking
            confidence_level = self._get_confidence_level(literal.confidence)
            stats['by_confidence'][confidence_level] += 1
            total_confidence += literal.confidence
            
            # Categorization tracking
            if literal.category != 'uncategorized':
                categorized_count += 1
                
            # File tracking
            stats['unique_files'].add(literal.file)
        
        # Calculate derived stats
        active_literals = len([l for l in literals if l.category != 'ignored'])
        if active_literals > 0:
            stats['avg_confidence'] = total_confidence / active_literals
            stats['categorization_rate'] = categorized_count / active_literals
        
        stats['total_categories'] = len(categories_set)
        stats['total_subcategories'] = len(subcategories_set)
        stats['total_files'] = len(stats['unique_files'])
        
        # Top categories
        stats['top_categories'] = sorted(
            stats['by_category'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return stats

    def _find_related_literals(self, literal: CategorizedLiteral, all_literals: List[CategorizedLiteral], max_related: int = 5) -> List[CategorizedLiteral]:
        """Find literals related to the given literal."""
        related = []
        
        # Find literals in the same subcategory
        for other in all_literals:
            if (other.category == literal.category and 
                other.subcategory == literal.subcategory and 
                other.value != literal.value and
                len(related) < max_related):
                related.append(other)
        
        # If not enough, find literals in the same category
        if len(related) < max_related:
            for other in all_literals:
                if (other.category == literal.category and 
                    other.value != literal.value and 
                    other not in related and
                    len(related) < max_related):
                    related.append(other)
        
        return related

    def _generate_usage_examples(self, literals: List[CategorizedLiteral], max_examples: int = 3) -> List[str]:
        """Generate usage examples from literal contexts."""
        examples = []
        
        for literal in literals[:max_examples]:
            if literal.context and literal.context.strip():
                # Clean up the context for display
                context = literal.context.replace('class:', '').replace('func:', '')
                example = f"**{literal.file}:{literal.line}** - `{context}`"
                examples.append(example)
        
        return examples

    def _generate_main_index(self, literals: List[CategorizedLiteral], stats: Dict, output_dir: Path) -> str:
        """Generate the main index markdown file."""
        content = []
        
        # Header
        content.append("# String Literals Index")
        content.append("")
        content.append("Comprehensive index of all string literals in the Netra platform codebase.")
        content.append("")
        content.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        content.append("")
        
        # Quick stats dashboard
        content.append("## 📊 Statistics Dashboard")
        content.append("")
        content.append("| Metric | Value |")
        content.append("|--------|-------|")
        content.append(f"| Total Literals | {stats['total_literals']:,} |")
        content.append(f"| Unique Categories | {stats['total_categories']} |")
        content.append(f"| Unique Subcategories | {stats['total_subcategories']} |")
        content.append(f"| Files Analyzed | {stats['total_files']} |")
        content.append(f"| Categorization Rate | {stats['categorization_rate']:.1%} |")
        content.append(f"| Average Confidence | {stats['avg_confidence']:.3f} |")
        content.append("")
        
        # Confidence distribution
        content.append("### Confidence Distribution")
        content.append("")
        total_active = sum(stats['by_confidence'].values())
        for level, count in stats['by_confidence'].items():
            percentage = (count / total_active * 100) if total_active > 0 else 0
            badge = self.confidence_badges[level]
            content.append(f"- {badge}: {count:,} literals ({percentage:.1f}%)")
        content.append("")
        
        # Table of Contents
        content.append("## 📋 Table of Contents")
        content.append("")
        
        # Quick Reference section
        content.append(self._generate_toc_entry("Quick Reference", "quick-reference"))
        content.append(self._generate_toc_entry("Most Used Literals", "most-used-literals", 2))
        content.append(self._generate_toc_entry("Search Patterns", "search-patterns", 2))
        content.append("")
        
        # Categories section
        content.append(self._generate_toc_entry("Categories", "categories"))
        
        grouped = self._group_literals_by_category(literals)
        for category in sorted(grouped.keys()):
            icon = self.category_icons.get(category, '📄')
            anchor = self._create_anchor(f"category-{category}")
            content.append(self._generate_toc_entry(f"{icon} {category.title()}", anchor, 2))
        content.append("")
        
        # Quick Reference Section
        content.append("## 🔍 Quick Reference")
        content.append("")
        
        # Most used literals
        content.append("### Most Used Literals")
        content.append("")
        
        # Count usage by value
        usage_count = defaultdict(int)
        usage_literals = {}
        for literal in literals:
            if literal.category != 'ignored':
                usage_count[literal.value] += len(literal.file.split(':'))  # Rough usage estimate
                if literal.value not in usage_literals:
                    usage_literals[literal.value] = literal
        
        top_used = sorted(usage_count.items(), key=lambda x: x[1], reverse=True)[:10]
        
        content.append("| Literal | Category | Confidence | Usage |")
        content.append("|---------|----------|------------|-------|")
        
        for value, usage in top_used:
            literal = usage_literals[value]
            confidence_level = self._get_confidence_level(literal.confidence)
            badge = self.confidence_badges[confidence_level]
            safe_value = self._sanitize_for_markdown(value[:50])
            if len(value) > 50:
                safe_value += "..."
            content.append(f"| `{safe_value}` | {literal.category} | {badge} | {usage} |")
        
        content.append("")
        
        # Search patterns
        content.append("### Search Patterns")
        content.append("")
        content.append("Use these patterns to quickly find specific types of literals:")
        content.append("")
        
        search_patterns = [
            ("API Endpoints", "`/api/`, `websocket`", "paths.api, paths.websocket"),
            ("Configuration Keys", "`_config`, `_url`, `_key`", "configuration.config_key"),
            ("Database Elements", "`SELECT`, table names, `_id`", "database.sql, database.table, database.column"),
            ("Event Names", "`_created`, `_updated`, `websocket_`", "events.type"),
            ("Error Messages", "`Error`, `Failed`, `Exception`", "messages.error"),
            ("Environment Variables", "`NETRA_`, `APP_`, `DB_`", "configuration.env_var"),
        ]
        
        for pattern_name, pattern, categories in search_patterns:
            content.append(f"- **{pattern_name}**: {pattern} → *{categories}*")
        
        content.append("")
        
        # Categories Overview
        content.append("## 📂 Categories")
        content.append("")
        content.append("Detailed breakdown of all string literal categories found in the codebase.")
        content.append("")
        
        for category in sorted(grouped.keys()):
            icon = self.category_icons.get(category, '📄')
            count = stats['by_category'][category]
            description = self.category_descriptions.get(category, 'No description available')
            
            anchor = self._create_anchor(f"category-{category}")
            content.append(f"### {icon} {category.title()} {{{anchor}}}")
            content.append("")
            content.append(f"**Count**: {count:,} literals")
            content.append("")
            content.append(f"**Description**: {description}")
            content.append("")
            
            # Subcategories
            subcategories = grouped[category]
            if len(subcategories) > 1 or 'general' not in subcategories:
                content.append("**Subcategories**:")
                content.append("")
                for subcategory, subcat_literals in sorted(subcategories.items()):
                    subcat_count = len(subcat_literals)
                    content.append(f"- `{subcategory}`: {subcat_count} literals")
                content.append("")
            
            # Top examples
            all_category_literals = []
            for subcat_literals in subcategories.values():
                all_category_literals.extend(subcat_literals)
            
            # Sort by confidence and take top examples
            top_examples = sorted(all_category_literals, key=lambda x: x.confidence, reverse=True)[:5]
            
            if top_examples:
                content.append("**Top Examples**:")
                content.append("")
                for example in top_examples:
                    confidence_level = self._get_confidence_level(example.confidence)
                    badge = self.confidence_badges[confidence_level]
                    safe_value = self._sanitize_for_markdown(example.value[:60])
                    if len(example.value) > 60:
                        safe_value += "..."
                    subcategory_text = f".{example.subcategory}" if example.subcategory and example.subcategory != 'general' else ""
                    content.append(f"- `{safe_value}` - *{category}{subcategory_text}* {badge}")
                content.append("")
            
            # Link to detailed category file
            category_file = f"string_literals/{category}.md"
            content.append(f"📄 **[View detailed {category} documentation]({category_file})**")
            content.append("")
            content.append("---")
            content.append("")
        
        # Footer
        content.append("## 🔗 Navigation")
        content.append("")
        content.append("- 🏠 [Back to Top](#string-literals-index)")
        content.append("- 📂 [Browse Categories by File](string_literals/)")
        content.append("- 🔍 [Query String Literals](../../scripts/query_string_literals.py)")
        content.append("- ⚙️ [Scan for New Literals](../../scripts/scan_string_literals.py)")
        content.append("")
        content.append("---")
        content.append("")
        content.append("*This documentation is automatically generated from the string literals index.*")
        content.append("*For questions or improvements, see the [String Literals System Documentation](../string_literals_index.xml).*")
        
        return "\n".join(content)

    def _generate_category_file(self, category: str, category_literals: Dict[str, List[CategorizedLiteral]], all_literals: List[CategorizedLiteral]) -> str:
        """Generate a detailed category-specific markdown file."""
        content = []
        
        # Header
        icon = self.category_icons.get(category, '📄')
        content.append(f"# {icon} {category.title()} Literals")
        content.append("")
        
        description = self.category_descriptions.get(category, 'No description available')
        content.append(description)
        content.append("")
        content.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        content.append("")
        
        # Calculate category stats
        total_literals = sum(len(literals) for literals in category_literals.values())
        avg_confidence = sum(l.confidence for subcat in category_literals.values() for l in subcat) / total_literals if total_literals > 0 else 0
        
        content.append("## 📊 Category Statistics")
        content.append("")
        content.append("| Metric | Value |")
        content.append("|--------|-------|")
        content.append(f"| Total Literals | {total_literals:,} |")
        content.append(f"| Subcategories | {len(category_literals)} |")
        content.append(f"| Average Confidence | {avg_confidence:.3f} |")
        content.append("")
        
        # Table of Contents for subcategories
        if len(category_literals) > 1:
            content.append("## 📋 Subcategories")
            content.append("")
            for subcategory in sorted(category_literals.keys()):
                count = len(category_literals[subcategory])
                anchor = self._create_anchor(f"subcategory-{subcategory}")
                content.append(self._generate_toc_entry(f"{subcategory} ({count} literals)", anchor))
            content.append("")
        
        # Generate subcategory sections
        for subcategory in sorted(category_literals.keys()):
            literals = category_literals[subcategory]
            
            if subcategory == 'general' and len(category_literals) == 1:
                # Don't show subcategory header if it's the only one and it's 'general'
                section_title = "Literals"
            else:
                section_title = f"Subcategory: {subcategory}"
            
            anchor = self._create_anchor(f"subcategory-{subcategory}")
            content.append(f"## {section_title} {{{anchor}}}")
            content.append("")
            content.append(f"**Count**: {len(literals)} literals")
            content.append("")
            
            # Sort literals by confidence, then alphabetically
            sorted_literals = sorted(literals, key=lambda x: (-x.confidence, x.value.lower()))
            
            # Group by confidence level for better organization
            by_confidence = defaultdict(list)
            for literal in sorted_literals:
                confidence_level = self._get_confidence_level(literal.confidence)
                by_confidence[confidence_level].append(literal)
            
            # Display by confidence level
            for confidence_level in ['high', 'medium', 'low']:
                if confidence_level not in by_confidence:
                    continue
                    
                confidence_literals = by_confidence[confidence_level]
                badge = self.confidence_badges[confidence_level]
                
                content.append(f"### {badge} ({len(confidence_literals)} literals)")
                content.append("")
                
                # Create table for this confidence level
                content.append("| Literal | Files | Context | Related |")
                content.append("|---------|-------|---------|---------|")
                
                for literal in confidence_literals:
                    # Prepare literal value (truncate if too long)
                    safe_value = self._sanitize_for_markdown(literal.value)
                    if len(safe_value) > 40:
                        display_value = safe_value[:37] + "..."
                    else:
                        display_value = safe_value
                    
                    # File information
                    file_info = f"{Path(literal.file).name}:{literal.line}"
                    
                    # Context information
                    context_info = literal.context.replace('class:', '').replace('func:', '') if literal.context else 'N/A'
                    if len(context_info) > 30:
                        context_info = context_info[:27] + "..."
                    
                    # Find related literals
                    related = self._find_related_literals(literal, all_literals, 2)
                    if related:
                        related_info = ", ".join([f"`{r.value[:15]}{'...' if len(r.value) > 15 else ''}`" for r in related])
                        if len(related_info) > 40:
                            related_info = related_info[:37] + "..."
                    else:
                        related_info = "None"
                    
                    content.append(f"| `{display_value}` | {file_info} | {context_info} | {related_info} |")
                
                content.append("")
            
            # Usage examples
            usage_examples = self._generate_usage_examples(sorted_literals[:3])
            if usage_examples:
                content.append("### Usage Examples")
                content.append("")
                for example in usage_examples:
                    content.append(f"- {example}")
                content.append("")
            
            content.append("---")
            content.append("")
        
        # Navigation
        content.append("## 🔗 Navigation")
        content.append("")
        content.append("- 🏠 [Back to Main Index](../string_literals_index.md)")
        content.append("- 📂 [Browse Other Categories](./)")
        content.append("")
        
        # Cross-references to related categories
        related_categories = self._find_related_categories(category, all_literals)
        if related_categories:
            content.append("### Related Categories")
            content.append("")
            for related_cat, relation_reason in related_categories:
                icon = self.category_icons.get(related_cat, '📄')
                content.append(f"- {icon} [{related_cat.title()}]({related_cat}.md) - {relation_reason}")
            content.append("")
        
        content.append("---")
        content.append("")
        content.append(f"*This is the detailed documentation for the `{category}` category.*")
        content.append("*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*")
        
        return "\n".join(content)

    def _find_related_categories(self, category: str, all_literals: List[CategorizedLiteral]) -> List[Tuple[str, str]]:
        """Find categories related to the given category."""
        related = []
        
        # Define relationships between categories
        relationships = {
            'configuration': [('paths', 'Configuration often contains paths and URLs')],
            'paths': [('configuration', 'Paths are often stored in configuration')],
            'database': [('identifiers', 'Database elements often serve as identifiers')],
            'events': [('identifiers', 'Events often use identifier patterns')],
            'messages': [('documentation', 'Messages and documentation overlap')],
            'metrics': [('identifiers', 'Metrics often follow identifier patterns')],
            'states': [('events', 'State changes often trigger events')],
        }
        
        return relationships.get(category, [])

    def generate_markdown_docs(self, literals: List[CategorizedLiteral], output_dir: Path) -> None:
        """Generate complete markdown documentation for string literals."""
        # Ensure output directories exist
        output_dir.mkdir(parents=True, exist_ok=True)
        category_dir = output_dir / "string_literals"
        category_dir.mkdir(exist_ok=True)
        
        # Calculate statistics
        stats = self._calculate_statistics(literals)
        
        # Generate main index file
        print("Generating main index file...")
        main_content = self._generate_main_index(literals, stats, output_dir)
        main_file = output_dir / "string_literals_index.md"
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(main_content)
        print(f"[OK] Generated: {main_file}")
        
        # Group literals by category
        grouped = self._group_literals_by_category(literals)
        
        # Generate category-specific files
        print("\nGenerating category-specific files...")
        for category, subcategories in grouped.items():
            print(f"  [DIR] Processing {category}...")
            category_content = self._generate_category_file(category, subcategories, literals)
            category_file = category_dir / f"{category}.md"
            with open(category_file, 'w', encoding='utf-8') as f:
                f.write(category_content)
            print(f"  [OK] Generated: {category_file}")
        
        # Generate category index
        print("Generating category directory index...")
        self._generate_category_index(grouped, stats, category_dir)
        
        # Summary
        print(f"\n[DONE] Documentation generation complete!")
        print(f"[STATS] Generated documentation for {stats['total_literals']:,} literals")
        print(f"[STATS] Created {len(grouped)} category files")
        print(f"[INFO] Main index: {main_file}")
        print(f"[INFO] Category files: {category_dir}")

    def _generate_category_index(self, grouped: Dict, stats: Dict, category_dir: Path) -> None:
        """Generate an index file for the category directory."""
        content = []
        
        content.append("# String Literals Categories")
        content.append("")
        content.append("Browse string literals by category. Each category contains detailed information about specific types of string literals found in the codebase.")
        content.append("")
        content.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        content.append("")
        
        # Categories table
        content.append("## 📂 Available Categories")
        content.append("")
        content.append("| Category | Count | Description | File |")
        content.append("|----------|-------|-------------|------|")
        
        for category in sorted(grouped.keys()):
            icon = self.category_icons.get(category, '📄')
            count = stats['by_category'][category]
            description = self.category_descriptions.get(category, 'No description available')
            # Truncate long descriptions
            if len(description) > 60:
                description = description[:57] + "..."
            
            file_link = f"[{category}.md]({category}.md)"
            content.append(f"| {icon} **{category.title()}** | {count:,} | {description} | {file_link} |")
        
        content.append("")
        content.append("## 🔗 Navigation")
        content.append("")
        content.append("- 🏠 [Back to Main Index](../string_literals_index.md)")
        content.append("- 🔍 [Query String Literals](../../scripts/query_string_literals.py)")
        content.append("")
        
        index_file = category_dir / "README.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
        print(f"  [OK] Generated: {index_file}")


def generate_markdown_docs(literals: List[CategorizedLiteral], output_dir: Path) -> None:
    """Main interface function for generating markdown documentation."""
    reporter = MarkdownReporter()
    reporter.generate_markdown_docs(literals, output_dir)


if __name__ == '__main__':
    # Example usage for testing
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        from categorizer_enhanced import CategorizedLiteral
        from scanner_core import RawLiteral
        
        # Create some test data
        test_literals = [
            CategorizedLiteral("NETRA_API_KEY", "config.py", 10, "configuration", "env_var", 0.95, "load_config", "env_var"),
            CategorizedLiteral("/api/v1/threads", "routes.py", 25, "paths", "api", 0.95, "create_route", "api"),
            CategorizedLiteral("thread_created", "events.py", 15, "events", "type", 0.95, "emit_event", "type"),
            CategorizedLiteral("SELECT * FROM users", "db.py", 30, "database", "sql", 0.95, "query_users", "sql"),
            CategorizedLiteral("Error: User not found", "errors.py", 40, "messages", "error", 0.85, "handle_error", "error"),
        ]
        
        # Generate documentation
        output_dir = Path("test_output")
        generate_markdown_docs(test_literals, output_dir)
        print("Test documentation generated successfully!")
        
    except ImportError as e:
        print(f"Import error during testing: {e}")
        print("This is expected when running as part of the larger system.")