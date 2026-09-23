---
name: no-ai-tells
description: Strips comment and structural patterns that read as LLM-generated, over-commented, or templated — comments that restate code, change-history narration, untracked stubs, generic names, near-duplicate blocks — so code reads as written by someone who knows this codebase. Use as a final pass before finishing, finalizing, or committing any code-writing task, and whenever asked to clean up, tidy, or polish a file's comments — over-commenting, "// Step 1:" narration, placeholder names — or to remove "AI tells"/vibecoded signs from code.
---

# No AI Tells

A final-pass filter, not a first-pass style. Write the code, then run this
checklist before calling it done. The goal isn't "no comments ever", and it
isn't disguising who wrote the code — it's code that's cheap for the next
reader: comments that carry information the code can't, and structure that
fits *this codebase's* conventions rather than a generic template.

What the evidence supports: large human-vs-LLM code comparisons find
generated code more templated and repetitive, with more generic naming,
unused constructs, and duplicated blocks. The comment-level entries below
are established readability practice more than measured AI signatures —
treat them as review heuristics, not a detector.

## Comment tells

| Tell | Bad | Why it reads as AI |
|---|---|---|
| Restates the line | `// increment the counter` above `i++` | Comment adds zero information the code didn't already give |
| Explains what, not why | `// hash the password` above `bcrypt.hash(...)` | The *what* is obvious from the call; the missing signal is *why this choice* (e.g. "bcrypt over argon2 — deploy target has no libsodium") |
| Banner/divider comments | `# ===== User Authentication =====` in a file that doesn't otherwise use them | The tell is the mismatch with the codebase's convention — some codebases use section banners deliberately; follow theirs |
| Uniform density | A comment on every function, evenly spaced | Humans comment where they had to think hard, not everywhere equally |
| Backwards placement | Comments on the obvious lines, silence at the actual decision point | The tell isn't volume, it's *where* the comments land |
| Change-history references | `// fixed for issue #123`, `// added for the new signup flow` | Narrates when/why the line was *changed* — that belongs in the commit message and rots in the file. Not the same as a link to an upstream bug that a live workaround depends on (`// works around foo#123; remove once fixed`) — that one tells the reader when the code can go, so keep it |
| Removed-code narration | `// removed the old validation here`, `// no longer using X` | Git history is the record of what changed; the file should only describe what *is* |
| Staged/phased narration | `// Step 1: validate input` / `// Step 2: process` | Narrates the plan instead of just writing the steps as code |
| Leftover scaffolding | `// TODO: implement`, `// placeholder`, unfinished stubs in "done" code | Signals it was never finished. A *tracked* TODO — owner or issue ID plus a concrete removal condition (`// TODO(#482): drop after the v2 API sunset`) — is standard practice (Google's C++ style guide recommends this form) and stays |
| Apologetic/hedging | `// this might not be the best way but...` | Ship a decision, don't narrate uncertainty into the file |
| Generic, context-free phrasing | Formal boilerplate ("The provided email address is not in a valid format") that doesn't match this codebase's existing tone | Reads as templated, not written by someone in this repo |

**Default:** no comment. Add one only when the *why* is genuinely non-obvious —
a hidden constraint, a workaround for a specific bug, behavior that would
surprise the next reader. If deleting the comment wouldn't confuse anyone,
delete it.

### Worked example — these tells compound, they don't appear alone

```js
// AI-authored, uncleaned
function createUser(email, password) {
  // check if email is provided
  if (!email) {
    // throw an error
    throw new Error("Email is required");
  }
  // hash the password
  const hash = bcrypt.hashSync(password, 10);
  // create the user object
  const user = { email, hash };
  // save the user
  return db.users.insert(user);
}
```

```js
// cleaned
function createUser(email, password) {
  if (!email) throw new Error("Email is required");
  const hash = bcrypt.hashSync(password, 10); // cost 10 — matches the rest of this service
  return db.users.insert({ email, hash });
}
```

Every stripped comment restated its line; the one kept explains a choice
(bcrypt cost) the code itself doesn't show. Same move on a real diff: read
the whole function first, then remove line-by-line before deciding what, if
anything, earns a comment — don't decide comment-by-comment on a first pass.

## Structural/naming tells

- **Disproportionate defensive completeness** — every branch handled, every
  input re-validated, when the actual failure modes don't justify it (e.g.
  re-validating data already validated one layer up). Completeness is good;
  completeness *in excess of real risk* is a tell.
- **Naming inconsistent with the surrounding file** — `userAuthenticationService`
  dropped into a file that abbreviates everywhere else, or vice versa. The tell
  is the mismatch, not verbosity or brevity in isolation.
- **Near-duplicated logic instead of one shared path** — two or three blocks
  that are 90% identical with minor variants, rather than extracted once. (Pairs
  with the `code-structure` skill's actions/service-layer lens.)
- **Mechanical placeholder names** — `tempData`, `result`, `item` used past the
  point where a real name is easy and cheap.
- **Phase-named identifiers** — functions, variables, or section headers named
  after the narration order instead of what they do: `step1Validate()`,
  `phaseTwoProcess()`, `step1Result`, a `## Step 1: Setup` prose header. Same
  tell as staged/phased comment narration, just moved into the name instead of
  a comment above it. Name for what the thing *is* — `validateSignupPayload()`,
  `hashedPassword` — not where it sits in a plan.
- **Test-specific smells** — module-wide `jest.mock()` where a targeted
  `spyOn()` would do, redundant `beforeEach` resets "just to be safe," loose
  `as any` typing, regex assertions where exact-match works, reimplementing a
  helper that already exists in the codebase.

## Nuance — don't overcorrect

This is cumulative-case reasoning: one match isn't a verdict, several
co-occurring ones are. Full test coverage, complete error handling, and
consistent formatting are normally *good* engineering — they only become a
tell when disproportionate to the code's actual risk surface. Don't strip a
comment or a defensive check just because this checklist mentions the
category; strip it because, on inspection, it's not earning its place here.
