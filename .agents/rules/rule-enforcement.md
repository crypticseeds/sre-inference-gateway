---
trigger: always
---

# Rule Enforcement Protocol

## Critical Rule Categories

### 1. Git/Graphite Commands (HIGHEST PRIORITY)
- **FORBIDDEN**: `git commit`, `git push`, `git checkout`, manual branch deletion
- **REQUIRED**: `gt create`, `gt submit --no-interactive`
- **VIOLATION SEVERITY**: CRITICAL - Stop execution immediately

### 2. User Confirmation Requirements
- **REQUIRED**: Explicit user approval before commits or submissions
- **FORBIDDEN**: Assuming user intent or performing actions without confirmation
- **VIOLATION SEVERITY**: HIGH - Ask for clarification

### 3. Scope Control
- **REQUIRED**: Work only on specified issues, not sub-issues
- **FORBIDDEN**: Auto-starting related work without user request
- **VIOLATION SEVERITY**: MEDIUM - Confirm scope with user

## Self-Check Protocol

**Before executing ANY action, ask yourself:**

1. "Is this command on the forbidden list?" → If YES, use the required alternative
2. "Did the user explicitly ask for this?" → If NO, ask for confirmation
3. "Am I about to commit or submit?" → If YES, verify user approval first
4. "Am I working outside the specified scope?" → If YES, stop and ask

## Violation Response

If you detect you're about to violate a rule:

1. **STOP** the current action
2. **EXPLAIN** which rule would be violated
3. **ASK** the user how to proceed
4. **WAIT** for explicit instruction

## Example Violations to Avoid

❌ BAD: Running `git commit -m "fix"` 
✅ GOOD: Running `gt create -m "fix"`

❌ BAD: Committing without asking
✅ GOOD: "I've staged the changes. Would you like me to commit them with `gt create`?"

❌ BAD: Working on sub-issues automatically
✅ GOOD: "I see this issue has sub-issues. Should I work on those as well, or just the parent?"

## Enforcement Hierarchy

1. **CRITICAL** rules (Git/Graphite commands) → Never violate
2. **HIGH** rules (User confirmation) → Always verify
3. **MEDIUM** rules (Scope control) → Clarify when uncertain

**When in doubt, ASK the user. It's better to over-communicate than to violate rules.**
