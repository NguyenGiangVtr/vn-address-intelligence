---
description: 'Guidelines for creating high-quality Agent Skills for GitHub Copilot. Use when creating or updating SKILL.md files, skill bundles, templates, scripts, references, and skill metadata.'
name: 'Agent Skills'
applyTo: '**/skills/**/SKILL.md'
---

# Agent Skills File Guidelines

Create skills that are discoverable, portable, and operational with minimal ambiguity.

## Scope and Intent

- Apply these rules when authoring or editing any SKILL.md under skills folders.
- Prioritize project-scoped skills in .github/skills/<skill-name>/ unless user explicitly asks for personal scope.
- Keep one concern per skill: each skill should solve one repeatable workflow.

## Required Frontmatter

- name:
  - lowercase with hyphens only
  - 1 to 64 characters
  - must match folder name
- description:
  - single-quoted string
  - include WHAT the skill does and WHEN to use it
  - include trigger keywords users are likely to type
  - keep concise and specific
- Optional fields:
  - argument-hint when slash invocation needs structured inputs
  - user-invocable true or false when discoverability must be controlled
  - license when legal terms are required by project policy (default: optional)

## Description Quality Rules

- Do not use vague text like "helpers" or "misc tools".
- Include concrete scenarios and nouns: file types, technologies, workflows, outcomes.
- Prefer this pattern: "Use when ..." with searchable keywords.

## SKILL.md Body Structure

Use the following sections when applicable:

1. Title and one-line purpose
2. When to Use
3. Inputs To Collect First
4. Procedure or Workflow
5. Decision Rules
6. Quality Gates
7. Output Format
8. Example Prompts
9. References

Skip sections only when not relevant. For non-trivial workflows, include Procedure, Decision Rules, and Quality Gates.

## Workflow Authoring Rules

- Write steps as actionable operations, not abstract advice.
- Include branching logic for ambiguous conditions and defaults.
- Encode fallback behavior when arguments are omitted.
- Separate default behavior from optional behavior explicitly.

## Resource Bundling Rules

- Keep related files inside the skill folder using relative links only.
- references/: decision support docs and domain specifics.
- scripts/: deterministic automation with usage/help text and clear errors.
- assets/: static files consumed unchanged.
- templates/: starter files intended to be modified.

When SKILL.md references a file, ensure the file exists.
Referenced companion files are mandatory before considering the skill creation task complete.

## Quality and Safety Rules

- Prefer conservative defaults unless the user requests aggressive automation.
- Do not claim actions were performed unless they were actually executed.
- For code-changing skills, include validation expectations.
- For review-only skills, state "do not modify code" explicitly.
- Keep instructions aligned with repository constraints and framework versions.

## Iteration Pattern

When creating a new skill:

1. Draft and save SKILL.md first.
2. Identify ambiguous defaults and ask focused questions.
3. Apply clarified defaults to the saved file.
4. Add referenced resources and verify links are valid.
5. Summarize outputs, example prompts, and related next customizations.

## Gotchas

- The description field is the primary discovery signal. If weak, the skill will not load.
- Folder name mismatch with frontmatter name causes silent confusion.
- Missing referenced files reduces trust and makes skills non-operational.
- Overly long SKILL.md files should be split with references for progressive loading.

## Validation Checklist

- Frontmatter is valid YAML.
- name matches folder and uses lowercase-hyphen format.
- description is specific, keyword-rich, and single-quoted.
- applyTo is set only when explicit file auto-attachment is desired.
- Default applyTo scope for this instruction stays limited to SKILL.md files only.
- Body includes workflow, decision logic, and completion criteria for complex skills.
- All internal links resolve to existing files.
- Examples reflect realistic prompts for this repository.
