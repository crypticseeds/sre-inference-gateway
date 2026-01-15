---
trigger: always
---

# Graphite Workflow Guidelines

## ⚠️ CRITICAL ENFORCEMENT RULES ⚠️

**IF YOU VIOLATE THESE RULES, STOP IMMEDIATELY AND EXPLAIN THE VIOLATION TO THE USER**

These are HARD CONSTRAINTS, not suggestions:
- Using `git checkout` is a VIOLATION
- Using `git commit` instead of `gt create` is a VIOLATION
- Using `git push` instead of `gt submit --no-interactive` is a VIOLATION
- Deleting branches manually is a VIOLATION
- Committing without user confirmation is a VIOLATION
- Submitting without user confirmation is a VIOLATION

**Before executing ANY git or gt command, verify it complies with these rules.**

## Mandatory Commands

- Never use `git checkout`
- **COMMITS**: Always use `gt create` - NEVER use `git commit`
- **PUSHES**: Always use `gt submit --no-interactive` - NEVER use `git push`
- **BRANCH DELETION**: NEVER delete branches - let Graphite manage lifecycle
- **SYNCING**: Always use `gt sync` - NEVER use `git pull`
 
## Commit Process

1. Stage changes with `git add`
2. Create commit with `gt create -m "commit message"`
3. Branch names should include issue ID, be descriptive and relate to the issue (e.g., `dev-XX: fix-auth-validation`, dev-xx: `add-metrics-endpoint`)
4. Use conventional commit format (feat:, fix:, docs:, etc.)
5. First line of commit message becomes PR title

## Code Review Workflow

- Code review agent must review all changes before committing
- Wait for explicit user instruction after review completion
- User will specify whether to commit OR submit - never assume both
- Only perform the exact action requested by the user

## Submission Process

- Always ask user for confirmation before running `gt submit --no-interactive`
- Verify stacked PR structure is correct before submission
- Use `gt state` to check current stack status

## Essential Commands

- Create commit: `gt create -m "message"`
- Submit stack: `gt submit --no-interactive`
- Check status: `gt state`
- Sync with trunk: `gt sync`
- Rebase stack: `gt restack`
- Navigate: `gt up` / `gt down`

## User Interaction Rules

- Never assume user intent - wait for explicit instructions
- Ask for confirmation before any submission actions
- Only perform the specific action requested, nothing additional

## Pre-Execution Checklist

**Before running ANY command, verify:**
- [ ] Am I using `gt create` instead of `git commit` or `git checkout`? ✓
- [ ] Am I using `gt submit --no-interactive` instead of `git push`? ✓
- [ ] Did the user explicitly ask me to commit/submit? ✓
- [ ] Have I asked for confirmation if submitting? ✓
- [ ] Am I avoiding branch deletion? ✓

**If any checkbox fails, STOP and ask the user for clarification.**

