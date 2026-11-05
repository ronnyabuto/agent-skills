# Development data, migration rehearsal, and production verification

Use this guidance when choosing test data, rehearsing database changes, or
checking a release. Scale it to the affected boundary; ordinary development
with adequate synthetic fixtures needs no production access or full audit.
These are procedures, not authorization or enforced security controls.

## Discover the project's approved route

Read relevant project instructions, runbooks, scripts, CI jobs and release
configuration. Establish the target environment, current task authorization,
data classification, permitted recipients (including model/tool services),
access method, retention/cleanup rules, and operational owner. Inspect what a
command actually does before running it; a name such as `dev` is insufficient.
Reuse an approved workflow within its documented scope. Credentials or a
reachable endpoint establish capability, not permission. Continue independent
local work if a missing authorization blocks only a production action; ask a
focused question only for the unresolved boundary, without repeating settled
permissions.

Keep schemas, sanitizers, database grants, storage policies, deployment commands
and enforced controls in their owning project/infrastructure. If a needed route
is absent, propose the smallest project-owned addition within authorized scope;
do not invent an export command or change global agent configuration.

## Choose data for the claim

- Use synthetic fixtures for known rules, constraints and edge cases that can
  be represented without real records. Explain any missing property before
  seeking production-derived data.
- Use an authorized sanitized subset when real distributions, legacy states,
  relationships or volume materially improve the test and its handling is
  approved. Verify its provenance, sanitizer coverage and permitted destination.
- When records cannot enter the agent environment, use an approved restricted
  job that runs inside the owner's boundary and returns bounded evidence:
  invariant results, coverage counts, migration status and reviewed diagnostics.
  Suppress identifying examples and small groups where they reveal individuals.
  Bound errors and logs too. Do not pull raw records to debug a failed job.

Masking suppresses or replaces values; pseudonymization preserves a link through
additional information and does not establish anonymity. Anonymization is a
contextual disclosure-risk claim requiring evidence about identifiability and
linkage. Synthetic data uses generated values or records; partial synthesis can leave
original fields intact, and generation from real data can retain information. A label such as “sanitized,” hashes of
identifiers, or a pattern scan alone proves neither anonymity nor export safety.
[NIST SP 800-188](https://csrc.nist.gov/pubs/sp/800/188/final) discusses these
tradeoffs and protected access alternatives; use the project's classification
and risk assessment rather than declaring legal compliance yourself. Check its
recipient/linkage context, transformation version, coverage and known gaps.

Inspect the relevant data flow, not just obvious name/email columns. Sensitive
content or working authority can survive in free text, nested JSON, historical
and audit rows, raw imports, attachments/files, filenames, identifiers and
cross-table links, precise dates/locations, logs, credentials, session cookies,
reset tokens and other authentication state. Keep source mappings and secret
material inside the approved boundary. Sanitization should address the actual
surfaces and preserve the properties under test. Validate coverage without
printing private matches; quarantine an unexpected leak with the owner and
resume using an approved corrected artifact or synthetic substitute.

For example, replacing every legacy identifier with a fresh unique value can
hide duplicates that break a new unique constraint. Preserve the duplicate
relationship using synthetic values, or test it inside the restricted job.
Do not solve fidelity loss by exporting the original identifiers.

## Rehearse the relevant transition

Identify the source schema/migration state, candidate application and migration
revision, required invariants, and failure/recovery outcomes. Match the engine,
version/extensions, collation, roles/privileges, constraints and application
compatibility where they affect the change. Match data shape, skew, relationships
and scale for relevant correctness or performance claims. A tiny fixture can
prove a constraint failure but cannot establish production duration or locking.
Record important mismatches and the claims they leave untested.

Before restoring or starting a copy, check side effects through workers, queues,
schedulers, database functions/triggers, outbound integrations, mounted files,
shared caches/services and network routes. Reuse project isolation and controlled
substitutes; verify effective destinations and identities. “Staging” and a local
container name do not prove isolation. Prevent real notifications, payments or
shared-state writes according to the project's controls.

Run the approved transition from representative prior state. Check relevant
constraints, backfill results, application behavior and compatibility during
rollout. Exercise interruption/retry, partial failure or recovery when the
migration's mechanics warrant it. For large operations, use the project's
resource limits, observability and stop conditions; stop on unexpected load,
exposure, wrong target or invariant failure and retain bounded diagnostics.
Recovery may require a forward fix or tested restore; do not assume reversing
DDL recovers lost data or that every operation is transactionally reversible.

## Bound usable authority and workload

Read-only permissions can prevent specified mutations. They do not prevent
reading/exporting allowed data, expensive scans, resource consumption or every
function's side effects. Inspect effective roles, callable functions and
external effects for the actual engine; a session read-only default may be
changeable. PostgreSQL's [read-only transaction definition](https://www.postgresql.org/docs/18/sql-set-transaction.html)
is deliberately limited. Reads also take [locks](https://www.postgresql.org/docs/18/explicit-locking.html).
Use owner-approved query/result bounds and applicable
[statement/lock limits](https://www.postgresql.org/docs/18/runtime-config-client.html),
concurrency and cancellation controls; a result `LIMIT` alone need not bound work.
These are engine examples, not required versions or portable grant recipes.

Reuse scoped credentials or workload identity where available, with resource,
operation and duration limits appropriate to the job. Short-lived access limits
future use, not copies already obtained. Proxy substitution can hide secret
bytes while retaining the ability to authenticate broad requests; destination
allowlisting alone need not limit objects or operations at that destination.
Review usable authority, including tools and escalated execution, rather than
merely checking whether a token is visible. Verify runtime controls using
[the platform notes](data-runtime.md); do not copy another client's flags.

Treat presigned links as access capabilities, keep them out of transcripts and
public artifacts, and verify provider-specific scope/reuse/expiry rules. For
example, [S3 presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
can be reused before expiration; expiry does not retract downloaded content.

An existing controlled job with limited inputs, outputs, credentials and
cleanup may suffice. Propose a persistent broker only for demonstrated needs
such as repeated multi-user access, centrally enforced operation restrictions,
or lifecycle/audit requirements that the simpler workflow cannot meet. Account
for its own operational burden and failure paths; do not build it by default.

## Release and verify within authorization

A successful rehearsal supplies evidence; it grants no deployment authority.
Use the existing release procedure only when deployment to that target is in
scope. Otherwise deliver the result and outstanding release checks. Do not
silently turn rehearsal access into production access or artifact publication.

For an authorized release, verify the actual deployed revision/artifact and
target, completed migration state, relevant schema/data invariants and bounded
application smoke checks. Check applicable error/latency/queue signals and
recovery readiness (usable backup/restore or forward-fix procedure, owner and
trigger), according to the project's release risk. A green pipeline or process
health check alone does not establish those outcomes. Stop/contain failures
using the authorized recovery procedure rather than retrying blindly.

Retain only approved evidence: revision/environment, data provenance and coverage
without records, commands or job IDs without capabilities, relevant mismatches,
observed outcomes and untested claims. Keep artifacts private per project
retention rules, clean up disposable copies/jobs/access as prescribed, and
verify cleanup or report its outstanding owner. Local or gitignored artifacts
are not automatically appropriate for sensitive output or external sharing.

Sources reviewed 2026-11-05. The procedures are recommendations to adapt to
project constraints; cited platform examples do not establish local enforcement.
