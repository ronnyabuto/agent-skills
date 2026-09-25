---
name: code-structure
description: Separates actions (domain rules, the when/why) from a shared service layer (reusable operational mechanics, the how), extracting only proven duplication. Use when multiple workflows duplicate the same operational logic, when deciding what belongs in actions vs shared services, or when refactoring repeated operational blocks across domain flows. Use when adding new features that share mechanics with existing ones. Also use when adding code to an existing codebase, to decide whether it belongs in an existing file or a new one and to keep the change to what was asked — no speculative options, single-implementation abstractions, or unrequested refactors.
---

# Service Layer Architecture

## Overview

**Two-layer separation:** Actions orchestrate domain rules (the "why/when"), while a service layer centralizes reusable operational mechanics (the "how").

This prevents duplicated code, inconsistent behavior, and bugs fixed in one path but not others.

## When to Use

- Multiple callers need the same low-level operation (sandbox creation, email sending, payment processing)
- You're copy-pasting operational logic between action files
- A bug fix in one workflow doesn't propagate to others doing the same thing
- Adding a new feature that shares mechanics with existing flows

**Don't use when:** Logic is truly domain-specific and used by only one caller.

## Scope and Placement

Settle these before writing anything; they're the cheapest point to keep a
change small.

**Where it goes:** into the existing file that already owns the behavior,
extended in that file's style (read it first — `understand-before-changing`).
Create a new file only when:

- nothing existing owns the concern,
- it's a rule-of-three extraction into the service layer (below),
- the project's convention gives it its own file (tests, migrations, routes,
  one-component-per-file), or
- the addition would bolt an unrelated concern onto the existing file.

"It keeps my diff tidy" isn't on the list — a module the next reader has to
go find costs more than a few lines where they'd already look.

**How much to build:** what was asked, done correctly — nothing speculative.

- No options, flags, or config for variations nobody requested.
- No interface, base class, or factory with a single implementation.
- No refactoring or cleanup of surrounding code during a fix; mention it
  instead.

Small isn't the goal on its own: keep validation at real boundaries, error
handling on real failure paths, and the test the change needs to be trusted.

## Core Pattern

```
Orchestration Layer (Actions)          Service Layer (Shared Mechanics)
├── owns business rules                ├── owns reusable operations
├── owns state transitions             ├── owns provider/SDK interactions
├── owns auth/ownership checks         ├── owns command execution details
├── owns failure classification        ├── owns health checks / readiness
├── owns retries / user-facing errors  └── returns structured results
└── calls service functions
```

**Rule of thumb:**
- "What this product flow means" → keep in actions
- "How to do this operation reliably" → move to service layer

## Quick Reference

| Design Principle | Do | Don't |
|---|---|---|
| API shape | Composable capability blocks | One giant "do everything" method |
| Inputs/outputs | Explicit params, structured returns | Hidden global state, reaching into DB |
| Migration | Extract one block, replace one caller, verify, then migrate rest | Refactor everything at once |
| Domain logic | Keep auth, policy, error classification in actions | Let service mutate domain state directly |
| Extraction trigger | Third occurrence (rule of three), or a bug that had to be fixed in more than one copy | Extracting at the second copy by reflex, or logic used once |

## Designing Service Functions

Design as **capability blocks**, not monoliths:

```ts
// Good: composable, each caller chooses what to use
createManagedSandbox(...)
prepareRepo(...)
detectPackageManager(...)
installDependencies(...)
runBuildCommand(...)
startSandboxRuntime(...)
```

Each function should:
- Accept all required data as **explicit parameters**
- Return **structured outputs** (e.g., `{ ready, previewUrl, proxyPort }`)
- Never reach into database/state directly
- Make failure explicit (structured results, not swallowed errors)

This lets callers choose strict vs relaxed behavior per flow.

## Migration Checklist

When extracting shared logic:

1. Write the flow in action code first (clear behavior)
2. Mark repeated operational chunks across callers
3. Extract **only** repeated, non-domain chunks to service
4. Replace one caller → verify → replace remaining callers
5. Keep domain policy in actions (auth, status transitions, error classification)
6. Run verification: typecheck, lint, confirm all flows still work

## Anti-Patterns

| Anti-Pattern | Problem |
|---|---|
| **God service** | One huge function hides all control flow |
| **Leaky service** | Service mutates database tables directly |
| **Inconsistent API** | Each function uses different argument styles and error semantics |
| **Over-abstraction** | Extracting logic used by only one caller |
| **Wrong abstraction** | A shared function that keeps growing flags and branches so each caller gets its variant — inline it back into the callers and re-extract only what's truly common (duplication is cheaper than the wrong abstraction) |

## Example: Email Service (Simple)

```ts
// emailService.ts — shared mechanics
export async function sendWelcomeEmail(params: { to: string; name: string }) {
  const html = `<h1>Welcome ${escapeHtml(params.name)}</h1>`;
  await emailProvider.send(params.to, "Welcome", html);
}

// userSignup.ts — orchestration (owns WHEN to send)
if (user.marketingOptIn) {
  await sendWelcomeEmail({ to: user.email, name: user.name });
}

// adminInvite.ts — orchestration (different business rule, same mechanic)
await sendWelcomeEmail({ to: invitee.email, name: invitee.name });
```

## Mental Model

```
New code?    → The existing file that owns it, unless a new-file condition above holds
New feature? → Write in action first → Third copy of the same op? → Extract to service
                                      → Two copies?  → Tolerate it, note it
                                      → One copy?    → Keep in action
```

Your architecture in one sentence: **Actions orchestrate domain rules, while the service layer centralizes reusable operational mechanics with a composable, explicit-input API.**
