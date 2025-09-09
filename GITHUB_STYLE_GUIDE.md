# GitHub Style Guide

## Core Principles

### 1. Lead with Impact & Naunce
- **First sentence = key takeaway**
- Put the most critical information in the first 2 lines
- Use the inverted pyramid structure (most important → details)
- Keep naunces of importance, for example maybe it's a really important impact, yet a very small code change
- For existing information sources prefer to link over recreating

### 2. Minimize Noise
- Remove unnecessary pleasantries, filler words, and redundant information
- Use bullet points over paragraphs when possible
- Avoid "I think," "maybe," "perhaps" - be direct
- Limit the overall volume of information
- Limit the complexity and take time to "make it simple smartie"
- Make it readable in a few moments, in a conversational and accurate way
- Seperate required "bulk dump" information from conversational information

### 3. Actionable Communication
- Every piece of communication should have a clear next step
- Use imperatives: "Fix X," "Update Y," "Review Z"
- Include specific file paths, line numbers, and error messages

---

## Issues

### Title Format
```
[TYPE] Brief description of actual impact
```
**Good:** `[BUG] Auth service returns 500 on valid JWT tokens`  
**Bad:** `Authentication isn't working properly for some users`

### Body Structure
```markdown
## Impact
<!-- What business/user value is affected? -->

## Current Behavior
<!-- What actually happens -->

## Expected Behavior
<!-- What should happen -->

## Reproduction Steps
1. Specific action
2. Specific result

## Technical Details
- File: `path/to/file.py:123`
- Error: `Exact error message`
- Environment: staging/production
```

### Labels
Use **maximum 3 labels** per issue:
- Priority: `critical`, `high`, `normal`
- Type: `bug`, `feature`, `refactor`
- Area: `auth`, `websocket`, `ui`

---

## Pull Requests

### Title Format
```
[TYPE] Action taken - outcome achieved
```
**Good:** `[FIX] Update auth validation - resolves 500 errors on staging`  
**Bad:** `Fix some authentication issues`

### Description Template
```markdown
## Changes Made
- Specific change 1
- Specific change 2

## Business Value
<!-- Why this matters to users/revenue -->

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing in staging

## Breaking Changes
<!-- List any breaking changes or "None" -->

Closes #123
```

### Size Guidelines
- **Target:** 1-5 files changed
- **Maximum:** 15 files changed
- **If larger:** Break into multiple PRs

---

## Comments

### Issue Comments
**Structure:**
1. **Status/Result** (if providing update)
2. **Key findings** (if investigating)
3. **Next action** (always end with this)

**Example:**
```markdown
**Status:** Bug reproduced in staging

**Root cause:** JWT validation fails when `user_id` contains hyphens

**Next:** Fixing validation regex in `auth_service/validators.py:45`
```

### PR Review Comments
**For bugs:**
```markdown
**Issue:** [Specific problem]
**Fix:** [Exact solution]
**File:** `path/file.py:123`
```

**For suggestions:**
```markdown
**Suggestion:** [Brief improvement]
**Reason:** [Why it's better]
**Optional:** [If not blocking]
```

### Code Review Priorities
1. **Blocking issues** (bugs, security, breaking changes)
2. **Architecture concerns** (SSOT violations, performance)
3. **Style/preference issues** (lowest priority)

---

## Commit Messages

### Format
```
[type] brief description

Optional body with why this change was made
```

### Types
- `fix` - Bug fixes
- `feat` - New features  
- `refactor` - Code restructuring
- `test` - Test additions/fixes
- `docs` - Documentation only

### Examples
**Good:**
```
fix: resolve auth 500 errors on hyphenated user IDs

Auth validator regex was too restrictive for user_id format.
Updated pattern to accept hyphens per user context spec.
```

**Bad:**
```
Fixed authentication bug
```

---

## Anti-Patterns to Avoid

### ❌ Noise Words
- "I think we should probably..."
- "It might be nice if..."  
- "Thanks in advance"
- "Hope this helps"
- "Let me know if you have questions"

### ❌ Vague Language
- "Some users are experiencing issues"
- "The system is slow"
- "Authentication problems"
- "It's not working"

### ❌ Unnecessary Context
- Long backstories about how you discovered the issue
- Detailed explanations of obvious concepts
- Multiple possible solutions without clear recommendation

### ✅ Direct Communication
- "Auth service returns 500 on staging"
- "Response time increased from 200ms to 2s"
- "JWT validation fails for user_id format ABC-123"
- "Fix: Update regex in auth_service/validators.py:45"