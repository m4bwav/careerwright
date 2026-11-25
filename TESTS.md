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

### 2026-11-25, full suite: 3 runs with the skill, 1 baseline (sonnet testers, Windows)
| Case | With skill | Bare | Notes |
|---|---|---|---|
| decoy-leads | 3/3 | 1/1 | r1: not invoked; r3: scope declined -> job-lead-scout; b1: job-lead-scout |
| trigger-tailor | 3/3 | 0/1 | r2: cr.py keywords; r3: cr.py keywords+lint; b1: no cr.py; honest hand tailoring |
| action-tailor | 3/3 | 0/1 | r2: keywords+lint, no Kafka/K8s, lint warn only; r3: keywords+lint, honest; b1: no cr.py; manual ATS, honest gaps |
| action-track | 3/3 | 0/1 | r2: wrote to HOME then copied; b1: no cr.py; 3 entries incl rejected Globex, expect 2; follow-up 7d ok; r3: import-leads 2, move, follow-up 12-02 |

Bare runs that reached the right answer without the plugin's script are graded FAIL, because each case expects the script.
