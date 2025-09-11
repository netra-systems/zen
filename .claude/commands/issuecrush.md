---
description: "Issue Crush - Intelligently groups and solves related issues together"
argument-hint: "[focus area, defaults to latest]"
---

You MUST process ALL SIMILAR ISSUES as one cohesive effort.
INTELLIGENT SIMILARITY DETECTION - Go beyond labels, analyze issue content deeply.
AS LONG AS IT TAKES KEEP GOING ALL NIGHT. At ONE FULL DAY OF WORK.

Have sub agents use built in github tools or direct `git` or `gh` if needed.
ALWAYS think about overall repo safety and STOP if anything might damage overall health of repo.

Focus area: ISSUE ${1 : latest}

SNST = SPAWN NEW SUBAGENT TASK (EVERY STEP IN PROCESS)
ALL Github output MUST follow @GITHUB_STYLE_GUIDE.md
Stay on develop-long-lived branch as current branch.

**CRITICAL BRANCH SAFETY POLICY:**
- **NEVER change current working branch** during issue processing
- **Current branch**: develop-long-lived (as per CLAUDE.md)
- **All work performed on**: develop-long-lived
- **PR target**: develop-long-lived (current working branch) - NEVER main
- **Verification**: Check `git branch --show-current` at each major step

PROCESS INSTRUCTIONS START:

0) BRANCH SAFETY CHECK : SNST: 
Verify current branch is develop-long-lived: `git branch --show-current`
If not on develop-long-lived, STOP and switch: `git checkout develop-long-lived`
Record branch state for safety monitoring throughout process.

1) READ TARGET ISSUE : SNST: Use gh to read the TARGET ISSUE ${1 : latest open issue}.

1) INTELLIGENT SIMILARITY ANALYSIS : SNST : 
Analyze ALL open issues to find related ones using sophisticated similarity detection:

**SIMILARITY CRITERIA (Beyond labels):**
- Root cause analysis - issues with same underlying technical cause
- Feature area overlap - issues affecting same system components  
- User story correlation - issues impacting same user workflows
- Error pattern matching - issues with similar stack traces/error signatures
- Dependency relationships - issues that are prerequisites/consequences of each other
- Business impact correlation - issues affecting same business metrics
- Technical debt clustering - issues stemming from same architectural problems

**ANALYSIS METHOD:**
- Extract key technical terms, error patterns, file paths from issue descriptions
- Identify common business workflows and user pain points
- Map component dependencies and interaction patterns
- Detect causal relationships (Issue A causes Issue B, Issue C blocks Issue D)
- Group by shared solutions or remediation approaches

**OUTPUT FORMAT:**
```markdown
## Issue Similarity Cluster Analysis

### Primary Issue: #[NUMBER] - [TITLE]
**Core Problem:** [Technical root cause]
**Business Impact:** [User/revenue impact]

### Related Issues Found:
#### High Similarity (>80% overlap)
- #[NUM] - [TITLE] | **Relationship:** [same root cause/blocking dependency/consequence]
- #[NUM] - [TITLE] | **Relationship:** [shared component/user workflow]

#### Medium Similarity (50-80% overlap)  
- #[NUM] - [TITLE] | **Relationship:** [related feature area/similar symptoms]

#### Low Similarity (20-50% overlap)
- #[NUM] - [TITLE] | **Relationship:** [tangential connection/potential synergy]

### Recommended Processing Strategy:
- **Merge candidates:** [Issues that should be consolidated]
- **Sequential processing:** [Issues with dependency order]
- **Parallel processing:** [Independent but related issues]
- **Holistic solution scope:** [Combined fix approach]
```

1.1) CREATE OR UPDATE comment on PRIMARY ISSUE with similarity analysis following @GITHUB_STYLE_GUIDE.md

2) SIMILARITY DECISION & CONSOLIDATION : SNST : (Pass full context from step 1)

**CONSOLIDATION LOGIC:**
- If 2+ issues have >90% similarity: MERGE into primary issue
- If issues have clear dependency chain: Process in sequence  
- If issues share solution approach: Process together with unified fix
- If issues are truly independent: Process primary only but note relationships

**MERGE PROCESS (when applicable):**
- Copy important details from duplicate issues to primary
- Add cross-references and context
- Close duplicates with clear merge explanation
- Preserve all valuable information and different perspectives

2.1) UPDATE existing comment on PRIMARY ISSUE with consolidation decisions following @GITHUB_STYLE_GUIDE.md

3) COMPREHENSIVE STATUS AUDIT : SNST : (Pass context from 1 and 2)
AUDIT current codebase, linked PRs (closed and open), and ALL related issues in the cluster using FIVE WHYS approach.

**EXPANDED AUDIT SCOPE:**
- Check if ANY issue in cluster is already resolved
- Analyze PRs that might have partially addressed cluster
- Identify shared technical debt or architectural issues
- Map business impact across entire issue cluster
- Assess cumulative user experience impact

3.1) UPDATE comment with comprehensive cluster audit following @GITHUB_STYLE_GUIDE.md

4) CLUSTER STATUS DECISION : SNST : (Pass context from 1, 2, and 3)
IF primary issue and all high-similarity issues are resolved, close them all and restart loop.
OTHERWISE continue with holistic solution approach.

4.1) UPDATE comment with cluster status decision following @GITHUB_STYLE_GUIDE.md

OPTIONAL STEPS IF CLUSTER HAS OPEN ISSUES:

5) HOLISTIC TEST PLANNING : SNST : (Pass full cluster context)
PLAN comprehensive test strategy covering:
- Primary issue reproduction  
- All related issue scenarios
- Cross-component integration testing
- Business workflow validation
- Regression prevention for entire cluster

**TEST STRATEGY:**
- Unit tests for shared components
- Integration tests for workflow dependencies  
- E2E tests for complete user journeys affected
- Performance tests if multiple issues affect same bottleneck
- Edge case coverage for issue cluster boundaries

Following reports\testing\TEST_CREATION_GUIDE.md and latest testing practices per claude.md
ONLY RUN tests that don't require docker (unit, integration non-docker, e2e staging GCP).

5.1) UPDATE comment with comprehensive TEST PLAN following @GITHUB_STYLE_GUIDE.md

6) EXECUTE HOLISTIC TEST PLAN : SNST : (with fresh sub agent)
Execute test plan covering entire issue cluster scope.

**VALIDATION CRITERIA:**
- Tests fail appropriately for all cluster issues
- Tests cover interaction patterns between issues
- Tests validate business workflows end-to-end
- Tests prevent regression of entire issue cluster

6.1) UPDATE comment with test execution results and decisions following @GITHUB_STYLE_GUIDE.md

7) UNIFIED REMEDIATION PLANNING : SNST :
PLAN comprehensive solution addressing:
- Root cause fixes for all high-similarity issues
- Shared infrastructure improvements  
- Business workflow optimizations
- Architectural debt reduction
- Preventive measures for similar issue recurrence

**SOLUTION ARCHITECTURE:**
- Identify shared code changes benefiting multiple issues
- Plan component interaction improvements
- Design user experience enhancements
- Architect preventive patterns and monitoring

7.1) UPDATE comment with unified remediation plan following @GITHUB_STYLE_GUIDE.md

8) EXECUTE UNIFIED REMEDIATION : SNST :
Implement solution addressing entire issue cluster:
- Fix primary issue completely
- Address all high-similarity issues simultaneously  
- Improve shared components and workflows
- Add preventive measures and monitoring

8.1) UPDATE comment with implementation results following @GITHUB_STYLE_GUIDE.md
8.2) Git commit work in logical, reviewable batches per issue cluster component

9) COMPREHENSIVE PROOF : SNST :
PROVE that changes address entire issue cluster without introducing regressions:
- Validate all cluster issues are resolved
- Confirm no new breaking changes across affected components
- Verify business workflows work end-to-end
- Validate preventive measures are effective

9.1) UPDATE comment with comprehensive PROOF following @GITHUB_STYLE_GUIDE.md

10) STAGING DEPLOY & CLUSTER VALIDATION : SNST :
Deploy and validate entire issue cluster resolution in staging:

10.1) Deploy affected services (if not deployed in last 3 minutes)
10.2) WAIT for deployment success/failure  
10.3) Read logs to confirm no new issues
10.4) Run cluster-wide validation tests on staging
10.5) Validate all business workflows affected by issue cluster
10.6) UPDATE comment with staging validation results following @GITHUB_STYLE_GUIDE.md
10.7) IF new issues detected, document them and restart from step 1 with expanded cluster

11) PR CREATION & CLUSTER CLOSURE : SNST :
11.1) Git commit any remaining work in logical batches
11.2) **SAFE PR CREATION**: Create comprehensive PR WITHOUT changing current branch:
    - Record current branch (should be develop-long-lived): `git branch --show-current`
    - Create feature branch remotely: `git push origin HEAD:feature/cluster-${PRIMARY_ISSUE_NUMBER}-$(date +%s)`
    - Create PR from feature branch to current branch: `gh pr create --base develop-long-lived --head feature/cluster-${PRIMARY_ISSUE_NUMBER}-$(date +%s) --title "Fix: Issue Cluster #${PRIMARY_ISSUE_NUMBER} + Related" --body "Comprehensive cluster fix addressing multiple related issues"`
    - VERIFY current branch unchanged: `git branch --show-current`
    - **CRITICAL**: Never checkout different branches - work stays on develop-long-lived
    - **PR MERGES TO**: Current working branch (develop-long-lived) - NEVER main
11.3) Cross-link ALL issues in cluster for automatic closure
11.4) Document cluster relationships and solution approach in PR description
11.5) **PR TARGET VALIDATION**: Ensure PR merges back to current working branch (develop-long-lived)
11.6) Final update covering entire cluster resolution following @GITHUB_STYLE_GUIDE.md

END PROCESS INSTRUCTIONS

You MUST repeat the entire PROCESS until ALL RELATED ISSUES are resolved.
EVERY NEW PROCESS ENTRY MUST SPAWN NEW SNST FOR EACH ITEM.
STOP AFTER 3 PROCESS CYCLES OR ALL CLUSTER ISSUES ARE CLOSED.

**KEY SUCCESS METRICS:**
- Higher issue resolution efficiency through cluster processing
- Reduced duplicate effort across related issues  
- Better architectural improvements addressing root causes
- Enhanced business value through holistic workflow fixes
- Preventive measures reducing similar issue recurrence