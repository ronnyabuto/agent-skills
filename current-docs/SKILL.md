---
name: current-docs
description: Use before implementing against any library/framework/SDK/API you're not certain is unchanged from training data — especially fast-moving ecosystems or unfamiliar dependencies. Identify the actual version pinned in this project, fetch that version's official docs as source of truth, and implement against what the docs say. Skip for stable/well-established syntax (POSIX shell, core language features) where the check would only add latency.
---

# Current Docs

Training data goes stale. APIs change, methods get deprecated, defaults
shift. This is the discipline for treating official docs — not memory — as
the source of truth when implementing against a specific technology.

## When to use

- Implementing or integrating a library, framework, SDK, or API whose
  current behavior you're not certain matches training data
- The technology moves fast (SDKs, cloud provider APIs, frontend frameworks)
- Anything version-sensitive: auth flows, config shape, surfaces prone to
  breaking changes

**Don't use** for stable syntax or stdlib features where checking would only
add latency for no benefit — this is for genuine uncertainty on a specific
technology's current surface, not a blanket lookup tax on every task.

## Process

1. **Identify the actual version in use.** Read the lockfile/manifest for
   each technology involved (package.json + lockfile, requirements.txt or
   pyproject.toml + lock, go.mod, Gemfile.lock, etc.). Work from what's
   actually installed, not an assumption of "latest."
2. **Fetch docs for that version, not the newest release.** Official
   first-party docs only — the vendor's own docs site, not blogs, SEO
   summaries, or Stack Overflow. A stale mirror is worse than no fetch at
   all, since it looks authoritative.
   - If the docs are versioned (a `/v14/`-style path, a version selector),
     navigate to the matching release explicitly.
   - If docs for that exact version aren't available, fetch the closest
     adjacent minor/patch and say so — don't silently substitute latest.
   - Verify exact values against the raw text. A fetch tool that summarizes
     pages through a model can paraphrase limits, defaults, and field names
     wrong — confidently. When a number, flag, or field name matters, pull the
     page's raw source (many docs sites serve a Markdown copy at the page URL
     plus `.md`, and index pages at `/llms.txt`) and grep for the exact value
     before relying on it.
3. **New or unpinned dependency** (nothing installed yet, greenfield choice):
   fetch latest docs — there's no existing version constraint to respect.
4. **Implement against what the docs say**, not what memory suggests. Where
   the docs contradict memory, the docs win — say so explicitly rather than
   quietly picking one without flagging the correction.
5. **Flag when docs couldn't be fetched** (auth-walled, blocked, offline)
   instead of silently falling back to memory. The user should know the
   implementation is running on an unverified assumption, not find out later.

## Nuance

A project pinned two majors behind "latest" needs *that* version's docs, not
the newest — mismatched-version guidance produces confidently wrong code,
which is worse than working from memory because it looks authoritative
rather than uncertain. The whole point is matching the docs to what's
actually running, not just fetching something recent.
