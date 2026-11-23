# contexts/

This is the team brain. Markdown only. No code, no configs.

## Files

- `01-project-brief.md` — **READ FIRST.** Locked pitch, scope, stack, hour-by-hour, judge-trap answers.
- `02-fraud-research-brief.md` — the research. What the fraud actually is, why "$50 insulin vs $5 Amazon" is a strawman, where the $45 markup actually lives. Read before pitching anything.
- `03-demo-plan.md` — the build plan with schema + schedule + pitch script + competitive matrix.
- `<first-name>.md` — one per teammate. Own your own file. Record ideas, decisions, open questions, blockers.

## Conventions

- Each teammate owns exactly one file named by their first name (lowercase). See `saswata.md` for the template.
- Do NOT edit another teammate's file without permission. If you have an ask for them, drop a TODO section at the bottom of THEIR file using this format:

  ```markdown
  ## TODO from <your-name> — <what this unblocks>

  ### [ ] TODO 1 — <one-line goal> (priority, ~<time estimate>)

  <context + code sketch if applicable>
  ```

- Checkboxes let the owner track progress. Time estimates signal ordering. Code sketches remove "what shape exactly?" round-trips.
- When a design decision is reversed, update `01-project-brief.md` + `AGENTS.md` in the same commit. Leave the old reasoning visible with "(updated)" so future readers see the history.
