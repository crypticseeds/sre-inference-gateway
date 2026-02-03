---
trigger: manual
---

# Linear Issue Creation Guidelines

When creating Linear issues for this project, follow these conventions:

## Default Settings
- **Assignee**: Femi
- **State**: Backlog
- **Project**: sre-inference-gateway
- **Team**: Use the appropriate team based on the issue type

## Issue Structure
- **Title**: Use clear, actionable titles that describe the work to be done
- **Description**: Include context, acceptance criteria, and technical requirements
- **Labels**: Apply relevant labels based on issue type:
  - `bug` for defects
  - `feature` for new functionality
  - `enhancement` for improvements
  - `documentation` for docs work
  - `infrastructure` for deployment/ops tasks
  - `MVP` for MVP-related work
  - `Post-MVP` for post-MVP work
  etc....

## Sub-Issue Guidelines
- Maximum of 3 sub-issues per parent issue
- Break down complex work into manageable chunks
- Each sub-issue should be completable in 1-2 days
- Link related issues using blocking/blocked-by relationships

## Required Output
After creating an issue, provide:
- Issue ID (e.g., TEAM-123, such as SRE-123 or DEV-123)
- Brief summary of what was created
- Links to any related issues or sub-issues

## Technical Context
When creating issues related to the inference gateway:
- Reference relevant architecture components (gateway, providers, Redis, vLLM)
- Include performance requirements or SLA considerations
- Specify which tech stack components are affected
- Add observability requirements (metrics, tracing, logging) 