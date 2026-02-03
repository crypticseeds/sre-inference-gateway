---
trigger: manual
---

# Issue Workflow Guide

## Starting Work on Linear Issues

When beginning work on a Linear issue, follow this structured workflow to ensure proper branch management and issue tracking.

### Branch Management
- **CRITICAL**: Before creating any new branch, check if a branch for the issue already exists using `gt state` or `git branch`
- **If branch exists**: Use `gt down`/`gt up` to navigate to the existing branch and work there
- **Only create new branch if**: No branch exists for the issue OR you're adding a separate feature/fix on top that needs independent tracking
- **Never create duplicate branches** for the same issue - this creates orphaned branches and submission problems
- Branch names should include issue ID, be descriptive and relate to the issue (e.g., `dev-XX: fix-auth-validation`, dev-xx: `add-metrics-endpoint`)
- Use conventional commit format (feat:, fix:, docs:, etc.)
- Use Graphite's stacking workflow for incremental changes

### Pre-Work Checklist
**Before starting any work, ALWAYS:**
1. Run `gt state` to see existing branches
2. Check if a branch for this issue already exists
3. If exists: Navigate to it with `gt down`/`gt up`
4. If not exists: Only then create new branch with `gt create`
5. **NEVER create a second branch for the same issue**

### Issue Status Management
- Mark the Linear issue as "In Progress" when starting work
- **Scope Limitation**: Work only on the specified issue - do not automatically start or work on sub-issues within an EPIC
- Focus on completing all tasks defined in the issue description

### Implementation Guidelines
- Follow the tech stack rules (Python 3.13+, FastAPI, vLLM, Redis, etc.)
- Adhere to Python conventions (snake_case, type hints, docstrings)
- Implement observability (Prometheus metrics, OpenTelemetry tracing)
- Use Doppler for secrets management

### Testing Requirements
- When adding new functionality, create corresponding tests
- Aggregate tests in a centralized test script
- Ensure tests are included in GitHub Actions CI workflow
- **Do not commit changes until user verification and testing is complete** - use `gt create` for change submission only after verification

### Completion Process
- **Do not** automatically mark the issue as "Done"
- Update the Linear issue with a concise implementation summary
- Wait for explicit user verification before proceeding to commit/submit

### Code Quality Standards
- Use type hints for all public functions
- Include comprehensive docstrings
- Follow PEP 8 and Black formatting
- Ensure all code is containerized and follows architectural constraints
