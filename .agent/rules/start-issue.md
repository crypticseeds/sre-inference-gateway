---
trigger: manual
---

# Issue Workflow Guide

## Starting Work on Linear Issues

When beginning work on a Linear issue, follow this structured workflow to ensure proper branch management and issue tracking.

### Branch Management
- **Always** create a new stacked branch using Graphite: `gt create <descriptive-branch-name>`
- Use `gt create` to create a new stacked branch, then use `git commit` for commits on that branch, and finally use `gt submit` to push the stack
- Branch names should include issue ID, be descriptive and relate to the issue (e.g., `dev-XX: fix-auth-validation`, dev-xx: `add-metrics-endpoint`)
- Use conventional commit format (feat:, fix:, docs:, etc.)
- Use Graphite's stacking workflow for incremental changes

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
