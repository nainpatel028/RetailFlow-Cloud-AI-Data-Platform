# Learning Plan

This project exists to build hands-on skill with SQL, Python, cloud data
platforms, and agentic AI design — not to produce a finished product by
generation alone.

## Principles

- **The user writes representative SQL, Python, and cloud configuration
  personally.** AI assistance scaffolds structure, fixtures, tests, and
  documentation, but does not solve core learning tickets on the user's
  behalf before the user has attempted them. See [AGENTS.md](AGENTS.md).
- **Every ticket requires an input / process / output / failure
  explanation.** Before a ticket is marked done, the user should be able to
  state: what data went in, what the process did to it, what came out, and
  what happens when something fails (bad input, missing dependency, partial
  run).
- **Every ticket ends with three things:**
  1. A modification exercise (change a rule, add a column, alter a
     threshold, and observe the effect)
  2. A debugging exercise (something is deliberately or naturally broken;
     the user diagnoses and fixes it)
  3. An interview-style explanation (the user explains the component out
     loud or in writing as if to an interviewer, without notes)

## Working with the raw source data

The `development` and `portfolio` Parquet profiles are **generated, not
manually edited** — see [docs/data_contracts.md](docs/data_contracts.md).
They are deliberately dirty: cleaning them (validating, casting,
standardizing, deduplicating, quarantining bad rows) in the Silver layer is
itself a core learning exercise, not something to route around. If a rule
in the generator's issue list seems too easy or too hard to handle in
Silver, adjust `config/data_generation.yml` and regenerate — don't hand-fix
the output data.

## Time budget

Planned at **45–60 focused hours** across all phases in
[README.md](README.md). This is a guideline for pacing, not a hard deadline.

## A note on mastery

Generated scaffolding (this repository's initial structure, fixtures, and
tests) is a starting point, not evidence of skill. Mastery is demonstrated by
completing the modification, debugging, and explanation exercises for each
ticket — not by the presence of working generated code.
