---
name: generate-custom-instructions-from-codebase
description: 'Migration and code evolution instructions generator for GitHub Copilot. Analyzes differences between two project versions (branches, commits, or releases) to create precise instructions allowing Copilot to maintain consistency during technology migrations, major refactoring, or framework version upgrades.'
argument-hint: 'Migration type, source ref, target ref, analysis scope, focus, automation level, examples, validation requirement'
user-invocable: true
---

# Migration and Code Evolution Instructions Generator

Generate migration-focused Copilot instructions by comparing two codebase states and extracting repeatable transformation rules.

## Configuration Variables

- MIGRATION_TYPE: Framework Version | Architecture Refactoring | Technology Migration | Dependencies Update | Pattern Changes
- SOURCE_REFERENCE: branch | commit | tag
- TARGET_REFERENCE: branch | commit | tag
- ANALYSIS_SCOPE: Entire project | Specific folder | Modified files only
- CHANGE_FOCUS: Breaking Changes | New Conventions | Obsolete Patterns | API Changes | Configuration
- AUTOMATION_LEVEL: Conservative | Balanced | Aggressive
- GENERATE_EXAMPLES: true | false
- VALIDATION_REQUIRED: true | false

Default values when omitted:
- ANALYSIS_SCOPE: Modified files only
- AUTOMATION_LEVEL: Balanced
- GENERATE_EXAMPLES: true
- VALIDATION_REQUIRED: true

## When to Use

- Framework upgrades with breaking API changes.
- Technology replacement migrations.
- Large architecture refactoring and convention shifts.
- Dependency modernization requiring pattern updates.

## Workflow

1. Comparative state analysis
- Compare structure between source and target references.
- Detect moved, renamed, and deleted files.
- Identify dependency and configuration shifts.
- Extract repeated code transformations.

2. Transformation pattern extraction
- Build old to new correspondence matrix.
- Capture triggers, actions, and exceptions.
- Separate mandatory rules from validation-required rules.

3. Migration instructions generation
- Produce .github/copilot-migration-instructions.md with context, rules, API mapping, new and obsolete patterns, validation points, and monitoring metrics.

4. Example synthesis
- When enabled, generate before and after examples from real project deltas.

5. Validation and optimization
- Test instructions on representative files.
- Tune rules to reduce false positives.
- Document edge cases and manual escalation scenarios.

## Decision Logic

- If MIGRATION_TYPE is Framework Version:
- Prioritize API correspondence mapping and obsolete API replacement.

- If MIGRATION_TYPE is Architecture Refactoring:
- Prioritize responsibility boundaries, layer dependencies, and abstraction shifts.

- If MIGRATION_TYPE is Technology Migration:
- Prioritize equivalent capability mapping, syntax conversion, and setup changes.

- If AUTOMATION_LEVEL is Conservative:
- Favor suggestions over automatic transformations.

- If AUTOMATION_LEVEL is Balanced:
- Automate low-risk repetitive transformations, validate medium-risk.

- If AUTOMATION_LEVEL is Aggressive:
- Maximize automatic transformations with stronger post-change checks.

- If VALIDATION_REQUIRED is true:
- Route uncertain or high-impact transformations through explicit validation checkpoints.

- If GENERATE_EXAMPLES is true:
- Include file-type-specific before and after snippets.

## Quality Gates

- Rules are grounded in observed source to target deltas.
- Each rule has clear trigger and action.
- Breaking changes and obsolete patterns are explicitly listed.
- Validation checkpoints include tests and compatibility checks.
- Manual escalation scenarios are documented.

## Output Contract

Generate one of these outputs:
- Preferred: .github/copilot-migration-instructions-<source>-to-<target>.md
- Fallback: .github/copilot-migration-instructions.md when source and target cannot be normalized for filename safety

Include sections:
1. Migration Context
2. Automatic Transformation Rules
3. Transformations with Validation
4. API Correspondences
5. New Patterns to Adopt
6. Obsolete Patterns to Avoid
7. File Type Specific Instructions
8. Validation and Security
9. Migration Monitoring
10. Error Reporting

## Suggested Prompt Template

Analyze code evolution between SOURCE_REFERENCE and TARGET_REFERENCE and generate migration instructions that allow Copilot to reproduce the same transformation patterns in future changes while preserving consistency and reducing regressions.

## Typical Use Cases

- Angular major upgrade.
- React class to hooks migration.
- .NET Framework to .NET migration.
- Monolith to modular architecture.
- REST to GraphQL transition.

## Benefits

- Captures migration knowledge as reusable transformation rules.
- Improves consistency of future code changes.
- Reduces manual repetition and migration drift.
- Speeds up subsequent modernization efforts.
