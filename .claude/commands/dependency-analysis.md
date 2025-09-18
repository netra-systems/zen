# Dependency Analysis Command

Analyze dependencies for a specific issue or set of issues to identify blocking relationships and execution order.

## Usage
- `/dependency-analysis <issue-number>` - Analyze dependencies for specific issue
- `/dependency-analysis P0` - Analyze all P0 issue dependencies
- `/dependency-analysis golden-path` - Analyze Golden Path dependencies

## What This Command Does

1. **Search for Related Issues**
   - Use GitHub search with relevant keywords and labels
   - Check for issues in same functional domain
   - Review recent issues that might be related

2. **Identify Blocking Relationships**
   - Infrastructure dependencies (databases, services, deployment)
   - Code dependencies (shared components, APIs, interfaces)
   - Sequential workflows (auth → validation → deployment)

3. **Recommend Consolidation Opportunities**
   - Issues with same root cause → merge/close duplicates
   - Related work that should be coordinated → cross-link
   - Sequential work that could be batched → combine

4. **Apply Labels and Cross-Links**
   - Add dependency labels (`depends-on-XXXX`, `blocks-golden-path`)
   - Add blocking labels (`infrastructure-blocker`)
   - Add cross-reference comments to all related issues

5. **Create Execution Sequence**
   - Generate dependency tree visualization
   - Identify critical path vs parallel work
   - Estimate timelines and provide resolution order

## Expected Output

- Dependency tree diagram showing relationships
- List of blocking issues that must be resolved first
- Recommended consolidation actions
- Updated GitHub issues with proper labels and cross-links
- Execution sequence with timelines

## Key Principles

- Always check for infrastructure blockers first
- Look for single points of failure blocking multiple issues
- Identify opportunities for parallel execution
- Apply DEPENDENCY_MANAGEMENT_SPEC.md standards
- Focus on preventing wheel-spinning and optimization of development velocity

## Integration

This command respects the dependency management specification and applies consistent labeling and cross-linking patterns across all issues.