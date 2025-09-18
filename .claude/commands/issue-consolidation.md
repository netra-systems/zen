# Issue Consolidation Command

Consolidate duplicate or related issues to reduce tracking fragmentation and improve development efficiency.

## Usage
- `/issue-consolidation <primary-issue> <duplicate-issue>` - Consolidate two related issues
- `/issue-consolidation scan-duplicates` - Find potential duplicate issues
- `/issue-consolidation merge-cluster <keyword>` - Consolidate related issues by keyword

## What This Command Does

1. **Analyze Issue Relationship**
   - Compare issue descriptions and root causes
   - Determine if issues are duplicates, related, or independent
   - Identify which issue should be the primary tracker

2. **Merge Information**
   - Copy relevant information from duplicate into primary issue
   - Preserve important context and analysis
   - Maintain audit trail of consolidation

3. **Update Cross-References**
   - Add consolidation comments explaining the merge
   - Update all related issues with new references
   - Transfer labels and relationships as needed

4. **Close Duplicate Issue**
   - Close with appropriate reason ("not planned" for duplicates)
   - Add consolidation comment with link to primary issue
   - Preserve searchability for future reference

## Consolidation Criteria

### Merge When:
- ✅ Same root cause (infrastructure, code bug, configuration)
- ✅ Same functional area and blocking relationship
- ✅ One issue is subset of another
- ✅ Issues would be resolved by same solution

### Keep Separate When:
- ❌ Different root causes requiring different solutions
- ❌ Different functional areas or services
- ❌ Independent implementation paths
- ❌ Different priority levels or timelines

## Expected Output

- Primary issue updated with consolidated information
- Duplicate issue closed with consolidation explanation
- All related issues updated with new cross-references
- Dependency labels transferred and updated
- Audit trail preserved in issue comments

## Templates Used

Uses standardized templates from DEPENDENCY_MANAGEMENT_SPEC.md:
- Consolidation comments
- Cross-reference linking
- Dependency relationship documentation

## Best Practices

- Preserve all important information from duplicate issue
- Explain consolidation reasoning in comments
- Update dependency chains after consolidation
- Notify stakeholders of consolidation via issue mentions
- Maintain GitHub issue searchability

## Integration

Works with dependency-analysis command to identify consolidation opportunities during dependency mapping.