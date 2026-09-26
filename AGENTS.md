# Team and agent working agreement

## Read first

Read [context.md](context.md) for requirements and the shared data contract, then
[skills.md](skills.md) for the relevant workflow. These documents are the initial
team draft; they do not imply that the application or integrations already exist.

## Work within the hackathon

- Budget: approximately 12 hours for four people. Prioritize a working end-to-end
  demo over framework setup, broad abstractions, or exhaustive coverage.
- Deliver projects from two utilities, an interactive overlap view, and ranked
  coordination opportunities. Cost estimates are a stretch goal.
- Focus on Sperry Tech, Gemini, and Tiger Data. Do not add sponsor integrations or
  extra infrastructure without an explicit team decision.
- Build one small vertical slice early, then expand the real dataset.
- Use a small, validated dataset when time is short. Label synthetic demo fixtures
  clearly and keep them out of real opportunity rankings.

## Ownership and coordination

| Initial area | Responsibility | Initial owner |
| --- | --- | --- |
| Data science | Extract PDF/XLSX records, normalize fields, validate evidence | Piero Espinoza |
| Data engineering | Define storage, load records, maintain database queries | Boris Steeven Mino |
| Backend | Serve project and opportunity endpoints; implement analysis | Adrian Perez and Boris Steeven Mino |
| Frontend | Interactive map, filters, ranked opportunities, detail views | Diego Rios |

Boris shares backend/API work with Adrian and can help with Postman testing. Roles are flexible: agree on
the current owner of a task before overlapping edits, and hand off the changed
files, interface changes, verification, and remaining issues. Initial ownership
does not prohibit another teammate from contributing.

## Agent autonomy

- Make routine implementation changes and relevant local checks directly within
  the assigned task and agreed contracts.
- Before changing shared database schemas, API contracts, dependencies, or
  deployment settings, describe the concrete proposed change and obtain approval
  from the requesting user or designated team owner. This includes initial
  implementation choices that have not yet been agreed.
- Prepare a proposal and continue independent work while a decision is pending;
  do not apply the gated change first.
- Do not interpret an undecided option in context.md as an approved choice.
- Preserve teammates' uncommitted work. Do not reset, overwrite, force-push,
  delete data, or apply destructive database changes without explicit approval.
- Do not commit credentials, .env files, private data, or confidential/CEII data.
  Keep Gemini and database credentials on the server.

## Shared interfaces and correctness

- Use the versioned handoff contract in context.md across extraction, loading,
  backend responses, and frontend fixtures. Map database column names internally
  if needed; do not silently change the shared payload.
- Preserve source evidence, nulls, date precision, and location quality.
- Do not fabricate coordinates, construction dates, costs, or opportunities.
- Compare projects belonging to different utilities. Geographic proximity is the
  primary signal; timeline overlap is secondary. Missing timing is unknown.
- Use geodesic distances or a suitable projected coordinate system. Never treat
  differences in latitude/longitude degrees as miles.
- Keep Gemini extraction subject to validation. Calculate distances and ranking
  using deterministic code; Gemini explanations must reflect those results.

## Git and pull requests

- Use a short task branch, such as codex/project-import. Keep PRs focused and
  small enough for another teammate to review quickly.
- Title format: `<type>: <concrete outcome>`; types: feat, fix, docs, chore.
  Example: `feat: import validated utility projects`.
- Open a draft early when another teammate needs the interface. Identify the
  owner and explicitly call out any shared-contract or schema change.
- Request one teammate review before merge. An explicitly agreed team exception
  is acceptable under the time limit; agents must not self-authorize it.
- Do not merge with exposed secrets, known data corruption, or a broken demo path.
- Include actual checks performed. If a check was skipped, say so and why.
- Do not create or merge a PR merely because this document describes the process;
  follow the active task's authorization.

Use this PR body (write `None` where a section does not apply):

```markdown
## What and why
Problem solved and resulting behavior, in 1-3 sentences.

## Interfaces and handoff
Schema/API/dependency/config changes, approval reference if required,
and what another teammate needs to use this change.

## Validation
Checks actually run and their results. Add a screenshot for visible UI changes
or a sample request/response for API changes when useful.

## Risks and remaining work
Known limitations and the next owner, if any. For database/deployment changes,
include a brief recovery approach.
```

## Verification and completion

- Run checks proportionate to the change. Prioritize import validation, distance
  boundaries, timeline uncertainty, API responses, and one complete demo path.
- Do not add a heavy test framework solely for this hackathon. Do not require
  code tests for documentation-only edits.
- Update the relevant shared document when an approved decision changes.
- Report what changed, what was verified, and what remains blocked or uncertain.
