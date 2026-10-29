# Headless capture and measured probes

Keep the same assertion discipline as desktop testing. Save the repeatable
script, its output and an `assertions.md` under `.artifacts/<task>/`. Identify
the revision, environment, starting state and any missing prerequisites.

## Browser behavior

Use the project's existing browser tooling. With Playwright available in the
script's module environment, a capture can look like this:

```js
import { chromium } from "playwright";

const browser = await chromium.launch();
try {
  const context = await browser.newContext({
    recordVideo: { dir: ".artifacts/<task>/" },
  });
  try {
    const page = await context.newPage();
    await page.goto("http://localhost:3000/path-under-test");
    // Drive the actual flow and assert its observable outcome here.
    await page.screenshot({ path: ".artifacts/<task>/01-result.png" });
  } finally {
    await context.close(); // Finalizes the recorded video.
  }
} finally {
  await browser.close();
}
```

A screenshot proves a state; a recording can show transitions. Choose the
smaller sufficient artifact. Number captures in test order with the assertion
in the name, such as `01-precondition-signed-in.png` and
`02-saves-on-blur-passed.png`. In `assertions.md`, list each test and meaningful
assertion as `passed`, `failed` or `untested` with its reason. Review the captures
before reporting success.

If tooling is missing, evaluate an isolated tooling environment or another
available driver before changing project dependencies. A CLI package installed
through `npx --package` does not by itself guarantee that a standalone Node
script can import that package. Verify module resolution and browser availability
rather than assuming either works. Do not claim a recording when only numbered
screenshots were captured.

## APIs, queries and performance

Write a probe that exercises the real boundary and records measured values in
`probe-output.json` or `probe-output.txt`. Preserve its inputs and invocation.
For a query reduction, measure actual SQL or request traces on both versions
and compare returned data, not just the counters. For latency, record workload,
run count and environment; keep competing builds and tests off the machine.
Distinguish lab measurements from field data and estimates.

Confirm the server is yours before trusting it: inspect the listening process
with `lsof -i :<port>` or `ss -ltnp`, then inspect that process's arguments.
Use isolated data and controlled external boundaries; do not perform live
charges or production writes merely to obtain evidence.

## Agent behavior and rendering

For agent behavior, retain the relevant transcript excerpt with the tool call,
result and observed outcome. Invocation alone does not establish task success.
When evaluating a skill, compare fresh sessions with it enabled and disabled;
keep trigger scores separate from outcome scores.

For rendering or canvas changes, save rendered frames and meaningful pixel
assertions, then review the images. Clearly label synthetic fixtures and
measurements. Include before/after artifacts when they support a fix claim.
