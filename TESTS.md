# Tests

Unit tests: `python -m pytest -q` (cr.py, made-up resume, posting and leads).

Skill evals: [evals/evals.json](evals/evals.json), four cases (one trigger, one decoy, two actions). Run with evergreen-test: three runs with the skill and a no-skill baseline.

## Runs

### 2026-11-25, one run per case, sonnet testers, Windows
| Case | With skill | Bare |
|---|---|---|
| action-tailor | pass: keywords 71% before, lint clean, no Kafka or Kubernetes claimed; wrote a gaps section into the resume, which faked 100% coverage (fixed in SKILL.md: gaps go in the reply) | pass: same gaps found by reading, ATS check by grep only |
| action-track | pass: import-leads skipped the rejected lead, Acme applied, follow-up 7 days out | partial: imported the rejected lead too, follow-up 14 days by guess, no history |
| trigger-tailor, decoy-leads | not run | not run |

The skill adds repeatable checks (lint on DOCX tables and columns, coverage numbers) and a tracker with stage history and follow-ups. Owed: three runs per case and the trigger cases.
