# Design: Email customers when order status changes

## Load (from README)

- ~500 orders/day × ~4 status changes ≈ **2,000 emails/day**.
- Mostly 08:00–18:00 on weekdays → ~200/hour average, maybe a few per second during a bulk update.
- SMTP relay (`smtp.internal`) accepts 30 msg/s. Even sent one at a time, the relay could handle all of a day's email in about 70 seconds.

That's tiny. No message broker, cache or extra server is needed. The existing Postgres database and VM can handle it. What matters is **correctness**: never email for a change that was rolled back, never lose an email for a change that committed, and don't send duplicates.

## Approach: transactional outbox in the existing Postgres

### 1. Record the notification in the same transaction as the status change

`set_status` already runs inside `db.transaction()`. Inside that same transaction, also insert a row into a new `email_outbox` table:

```sql
CREATE TABLE email_outbox (
    id            bigserial PRIMARY KEY,
    order_id      bigint      NOT NULL REFERENCES orders(id),
    old_status    text,
    new_status    text        NOT NULL,
    recipient     text        NOT NULL,        -- customer email, captured at change time
    created_at    timestamptz NOT NULL DEFAULT now(),
    attempts      int         NOT NULL DEFAULT 0,
    next_attempt  timestamptz NOT NULL DEFAULT now(),
    sent_at       timestamptz,
    last_error    text
);
CREATE INDEX email_outbox_pending ON email_outbox (next_attempt) WHERE sent_at IS NULL;
```

Planned change to `set_status` (described here, not applied):

```python
with db.transaction():
    row = db.execute(
        "SELECT o.status, c.email FROM orders o JOIN customers c ON c.id = o.customer_id "
        "WHERE o.id = %s FOR UPDATE", (order_id,)).fetchone()
    if row.status == status:
        return                                   # no-op change, no email
    db.execute("UPDATE orders SET status = %s, updated_at = now() WHERE id = %s", (status, order_id))
    db.execute("INSERT INTO email_outbox (order_id, old_status, new_status, recipient) "
               "VALUES (%s, %s, %s, %s)", (order_id, row.status, status, row.email))
```

If the transaction rolls back, no email is queued. If it commits, the email is guaranteed to be queued. The request path never calls SMTP, so a slow or unavailable relay can't slow down or break status updates.

*Assumption:* customer email is reachable via `orders.customer_id → customers.email`. Adjust the join to match the real schema. If some customers should not get email, add an `email_opt_out` flag on `customers` and skip the insert when it's set.

### 2. One small sender process on the same VM

`notifier.py` runs as a systemd service (`Restart=always`) next to the app. It loops:

1. Claim a batch:
   ```sql
   SELECT * FROM email_outbox
   WHERE sent_at IS NULL AND next_attempt <= now() AND attempts < 10
   ORDER BY id LIMIT 50
   FOR UPDATE SKIP LOCKED;
   ```
2. For each row, render the template for `new_status` and send it through `smtp.internal` over one reused SMTP connection.
3. On success: `sent_at = now()`. On failure: `attempts += 1`, `last_error = …`, `next_attempt = now() + least(2^attempts, 60) minutes`.
4. Commit. If the batch was empty, sleep for ~5 s. Optionally use `LISTEN email_outbox` with a `NOTIFY` from `set_status` so emails go out immediately. Polling every 5 s is fine at this volume.

`SKIP LOCKED` means a second copy of the process, started by accident or for redundancy, won't double-send.

**Delivery semantics:** at-least-once. A crash after the SMTP send but before the commit can cause one duplicate. At this volume that's acceptable. To reduce it, set a stable `Message-ID: <outbox-{id}@orders.internal>` so mail clients and relays can dedupe.

**Rate limiting:** a simple ≤10 msg/s throttle in the loop keeps the process well under the relay's 30/s limit, even when draining a backlog after an outage.

### 3. Content

- One plain-text + HTML template per status, e.g. `confirmed`, `shipped`, `delivered`, `cancelled`, stored as files in the repo next to the app. Statuses with no template are marked sent without emailing, so internal-only statuses stay quiet.
- The subject includes the order number. The body includes the order number, the new status and a contact address.
- `From:` is a team address such as `orders@<company>`. Use `Reply-To` if replies should go to sales.

**Optional coalescing:** if an order changes status several times within a minute, for example a mistaken click followed by a correction, the sender can delay rows by ~60 s (`next_attempt = created_at + 1 min`). It then sends only the latest pending row per order and marks the older ones as superseded. This is recommended because it costs only one `DISTINCT ON (order_id)` query.

### 4. Operations

- **Monitoring:** watch two numbers, both available with SQL: rows with `sent_at IS NULL AND created_at < now() - interval '15 min'` (stuck) and rows with `attempts >= 10` (dead). Alert the team via a cron check or the existing monitoring, if there is any.
- **Retention:** a nightly `DELETE FROM email_outbox WHERE sent_at < now() - interval '90 days'`. At ~2k rows/day, the table stays small and doubles as a "what did we email this customer?" audit log.
- **Resend / manual fix:** reset `sent_at`/`attempts` on a row, or insert a new one.
- **Deploy:** one migration (table + index), the `set_status` change, `notifier.py` and a systemd unit file. No new infrastructure.

## Rejected alternatives

- **Sending SMTP inside `set_status`:** couples request latency and success to the relay, and can email for a change that later rolls back.
- **A message broker (RabbitMQ/Redis/SQS) or a third-party email service:** extra infrastructure to run and secure for ~2k emails/day. Postgres already gives transactional guarantees, and IT already provides the relay.
- **A Postgres trigger on `orders` to fill the outbox:** this would also work and would catch updates made outside `set_status`. But it hides logic in the database. Choose it only if other code paths update `orders.status` directly.
