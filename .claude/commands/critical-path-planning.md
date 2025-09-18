# Critical Path Planning Command

Create execution plan for complex multi-issue initiatives with proper dependency sequencing.

## Usage
- `/critical-path-planning <master-issue>` - Plan execution for initiative
- `/critical-path-planning golden-path` - Plan Golden Path execution
- `/critical-path-planning P0` - Plan P0 issue resolution sequence

## What This Command Does

1. **Initiative Scope Analysis**
   - Identify all related issues in the initiative
   - Categorize by functional area and dependency type
   - Determine initiative boundaries and success criteria

2. **Dependency Mapping**
   - Analyze dependencies and blocking relationships
   - Create visual dependency tree
   - Identify critical path vs parallel work opportunities

3. **Execution Sequencing**
   - Generate sequential execution order for critical path
   - Identify work that can proceed in parallel
   - Account for resource constraints and skill requirements

4. **Timeline Estimation**
   - Estimate effort for each issue based on complexity
   - Calculate critical path timeline
   - Identify optimization opportunities

5. **Master Coordination Plan**
   - Create comprehensive execution plan in master issue
   - Apply proper labels and cross-links across all issues
   - Establish progress tracking and reporting structure

## Planning Framework

### Critical Path Identification
- Issues that block other work (infrastructure, foundational)
- Sequential dependencies that cannot be parallelized
- Single points of failure affecting multiple features

### Parallel Work Streams
- Independent functional areas
- Cleanup tasks that don't affect core functionality
- Documentation and testing that can proceed alongside development

### Resource Optimization
- Batch similar work to same developers/teams
- Identify opportunities for knowledge transfer
- Plan for review and validation cycles

## Expected Output

- Comprehensive master coordination plan
- Visual dependency tree with critical path highlighted
- Execution timeline with parallel work identified
- Updated issues with proper dependency labels
- Progress tracking structure

## Templates Generated

Uses DEPENDENCY_MANAGEMENT_SPEC.md templates:
- Master plan coordination format
- Execution sequence documentation
- Dependency relationship mapping
- Progress tracking structure

## Success Metrics

- Clear understanding of what work can start immediately
- Identification of primary blockers affecting timeline
- Optimal resource allocation across parallel work streams
- Predictable timeline for initiative completion

## Integration

Coordinates with:
- `dependency-analysis` for relationship mapping
- `issue-consolidation` for reducing tracking overhead
- `priority-triage` for resource allocation decisions