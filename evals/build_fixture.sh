#!/bin/bash
# Builds the throwaway repos the trigger evals run in.
#   evals/build_fixture.sh <out-dir> [vault-source-dir]
# <out-dir>/webapp        a small Next.js/Express app the queries refer to
# <out-dir>/agent-skills  a copy of the vault for the vault-memory cases,
#                         named like this repo so project-scoped recall works
set -e
OUT=${1:?usage: build_fixture.sh <out-dir> [vault-source-dir]}
VAULT_SRC=${2:-$(cd "$(dirname "$0")/.." && pwd)}
F="$OUT/webapp"
rm -rf "$F"
mkdir -p "$F"/{src,payments,api,handlers,flows,app/dashboard,app/settings,components,lib}
cd "$F"

cat > package.json <<'EOF'
{
  "name": "webapp",
  "private": true,
  "scripts": { "dev": "next dev", "build": "next build", "start": "next start", "test": "vitest" },
  "dependencies": { "next": "14.2.3", "react": "18.3.1", "express": "4.19.2", "stripe": "14.25.0", "@aws-sdk/client-s3": "3.577.0", "nodemailer": "6.9.13" },
  "devDependencies": { "typescript": "5.4.5", "vitest": "1.6.0" }
}
EOF
cat > src/profile.ts <<'EOF'
export function displayName(usr: { first: string; last: string }) {
  return `${usr.first} ${usr.last}`;
}
EOF
cat > payments/charge.ts <<'EOF'
import Stripe from "stripe";
const stripe = new Stripe(process.env.STRIPE_KEY!);

export async function charge(customerId: string, amountCents: number) {
  const customer = await stripe.customers.retrieve(customerId);
  if (customer == null) return { ok: false, reason: "no-customer" };
  if (!customer || (customer as any).deleted) return { ok: false, reason: "no-customer" };
  return stripe.paymentIntents.create({ customer: customerId, amount: amountCents, currency: "usd" });
}
EOF
cat > api/parse.ts <<'EOF'
export type ParseResult<T> = { ok: true; value: T } | { ok: false; error: string };

export function parseRequest(body: unknown): ParseResult<{ email: string; plan: string }> {
  if (typeof body !== "object" || body === null) return { ok: false, error: "body must be an object" };
  const { email, plan } = body as Record<string, unknown>;
  if (typeof email !== "string") return { ok: false, error: "email is required" };
  if (typeof plan !== "string") return { ok: false, error: "plan is required" };
  return { ok: true, value: { email, plan } };
}
EOF
for h in upload-avatar upload-document; do cat > "handlers/$h.ts" <<'EOF'
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
const s3 = new S3Client({ region: process.env.AWS_REGION });

async function putFile(key: string, body: Buffer, contentType: string) {
  await s3.send(new PutObjectCommand({ Bucket: process.env.BUCKET, Key: key, Body: body, ContentType: contentType }));
  return `https://${process.env.BUCKET}.s3.amazonaws.com/${key}`;
}

export async function handle(req: { userId: string; file: Buffer; type: string }) {
  return putFile(`${req.userId}/${Date.now()}`, req.file, req.type);
}
EOF
done
for f in signup admin-invite password-reset; do cat > "flows/$f.ts" <<'EOF'
import nodemailer from "nodemailer";
const transport = nodemailer.createTransport({ host: process.env.SMTP_HOST });

async function sendWithRetry(to: string, subject: string, html: string) {
  for (let attempt = 0; attempt < 3; attempt++) {
    try { return await transport.sendMail({ to, subject, html }); }
    catch (e) { await new Promise((r) => setTimeout(r, 500 * attempt)); }
  }
  throw new Error("send failed");
}

export async function run(user: { email: string; name: string }) {
  await sendWithRetry(user.email, "Hello", `<p>Hi ${user.name}</p>`);
}
EOF
done
cat > lib/report.ts <<'EOF'
export function buildReport(rows: { amount: number; region: string }[]) {
  // Step 1: filter rows
  const step1Result = rows.filter((r) => r.amount > 0);
  // Step 2: group by region
  const step2Result: Record<string, number> = {};
  for (const r of step1Result) step2Result[r.region] = (step2Result[r.region] ?? 0) + r.amount;
  // Step 3: return
  return step2Result;
}
EOF
cat > components/DatePicker.tsx <<'EOF'
export function daysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate() + 1;
}
EOF
cat > app/dashboard/page.tsx <<'EOF'
export default async function Dashboard() {
  const orders = await fetch("http://localhost:4000/orders").then((r) => r.json());
  const users = await fetch("http://localhost:4000/users").then((r) => r.json());
  return <main><h1>Dashboard</h1><p>{orders.length} orders, {users.length} users</p></main>;
}
EOF
cat > app/settings/page.tsx <<'EOF'
"use client";
export default function Settings() {
  return <form action="/api/settings" method="post"><button>Save</button></form>;
}
EOF
cat > middleware.ts <<'EOF'
import { NextResponse } from "next/server";
export function middleware() { return NextResponse.next(); }
EOF
echo "# webapp" > README.md

git init -q -b main
git -c user.name=fixture -c user.email=fixture@example.com add -A
git -c user.name=fixture -c user.email=fixture@example.com commit -q -m "Initial app"

V="$OUT/agent-skills"
rm -rf "$V"
mkdir -p "$V"
[ -d "$VAULT_SRC/claude" ] && cp -r "$VAULT_SRC/claude" "$V/claude"
cp "$VAULT_SRC/AGENTS.md" "$V/AGENTS.md"
echo "fixtures ready in $OUT"
