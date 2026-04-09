# Task: Write a 6-File Proposal for `spec-alignment-checker`

You are designing a new OpenClaw tool called `spec-alignment-checker` that automatically detects contradictions between OpenAPI specs, Pydantic data models, and actual code.

## Background

During vtic development, we had 58 contradictions across 6+ design documents because multiple agents wrote specs independently. This wasted 10+ hours of reconciliation work. The tool should prevent this.

## Required Files

Create 6 markdown files in `/home/smoke01/.openclaw/workspace-cclow/spec-alignment-proposal/`:

### 1. `01-problem-statement.md`
- Describe the problem: spec contradictions
- Real examples from vtic (58 contradictions)
- Impact: hours wasted, bugs introduced
- Why current manual review fails

### 2. `02-solution-overview.md`
- High-level approach
- Core features
- Integration with OpenClaw
- How it prevents contradictions

### 3. `03-architecture.md`
- Component design
- Data flow (OpenAPI → Parser → Comparator → Reporter)
- File structure
- Technology choices

### 4. `04-implementation-plan.md`
- Phase breakdown (with time estimates)
- Dependencies
- Parallel vs sequential work
- Milestones

### 5. `05-usage-examples.md`
- CLI commands
- Output format
- Integration with CI/CD
- Example contradictions caught

### 6. `06-success-metrics.md`
- KPIs to measure
- Before/after comparison
- Adoption targets
- Failure modes to watch

## Guidelines

- Be specific and actionable
- Include code examples where relevant
- Reference real vtic lessons learned
- Each file should be 100-200 lines
- Make it practical, not theoretical

## Output

Write all 6 files now. Be thorough.
