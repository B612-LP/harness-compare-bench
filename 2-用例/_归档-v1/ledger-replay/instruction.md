The file /app/events.jsonl is an event log exported from an order system's
ledger. Each line is one JSON event:

    {"seq": 20, "msg_id": "m0020-ord007-pay0", "ts": "2026-10-20T09:00:06",
     "order_id": "ORD007", "op": "pay", "amount": 85477, "ack": true}

- `seq`: producer sequence number (integer; not guaranteed unique — a batch of
  events emitted together can share one seq)
- `msg_id`: message id used for at-least-once delivery; redeliveries repeat the
  same msg_id
- `ts`: export timestamp at second granularity (informational)
- `order_id`: order identifier; `op` is one of create | pay | cancel | refund
- `amount`: integer amount in cents (0 for create/cancel)
- `ack`: whether the producer had received a storage ack when the event was
  emitted; some events were exported before acking

The lines are physically out of order (multi-writer export). Rebuild the books
by replaying the log under the rules below.

Replay rules:

1. Replay order is ascending `seq`; events sharing a seq replay in ascending
   `msg_id` (ASCII) order. Physical line order and `ts` never affect replay
   order.
2. Idempotency: a `msg_id` is processed at its first replay position only. Any
   later occurrence is skipped entirely and logged as an anomaly of type
   `duplicate_msg_id` (carrying that occurrence's own seq).
3. Negative amount: an event with `amount < 0` is rejected — no state change,
   no money movement — and logged as `negative_amount`. Such an event still
   counts as seen for idempotency.
4. Unacked events: an event with `ack: false` takes effect normally and is
   additionally logged as `unacked`.
5. State machine (all money in integer cents):
   - `create`: only if the order does not exist yet → state `created` with
     paid_total = refunded_total = 0
   - `pay`: when the order state is `created` or `paid` → paid_total += amount,
     state becomes `paid`
   - `cancel`: when the state is `created` → `cancelled`; when the state is
     `paid` or `refunded` the cancel arrives after completion: the state stays
     unchanged and the event is logged as `late_cancel`; cancelling an already
     cancelled order does nothing
   - `refund`: when the state is `paid` or `refunded` → refunded_total +=
     amount; as soon as refunded_total reaches paid_total the state becomes
     `refunded`, otherwise it stays `paid`
   - An operation (pay/cancel/refund) for an order that does not exist is
     ignored.
6. Anomaly precedence per event: `duplicate_msg_id` > `negative_amount` >
   `unacked` > `late_cancel`; at most one anomaly is recorded for any single
   event.

Create /app/final_state.json: a JSON array with one object per order, sorted
ascending by `order_id`:

    [{"order_id": "ORD001", "state": "created", "paid_total": 0,
      "refunded_total": 0}, ...]

`state` is one of created | paid | cancelled | refunded; the totals are
integers in cents.

Create /app/anomalies.json: a JSON array with one object per logged anomaly,
sorted ascending by `seq` (events sharing a seq: ascending `msg_id`):

    [{"type": "unacked", "msg_id": "m0022-ord008-create0",
      "order_id": "ORD008", "seq": 22}, ...]

`type` is one of duplicate_msg_id | late_cancel | unacked | negative_amount.

Both files must be valid UTF-8 JSON. Every amount is an integer number of
cents — floating point values are not acceptable anywhere.
