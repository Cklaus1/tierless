# Design Doc: Real-Time Notification Fanout

**Author:** platform team · **Status:** proposed · **Reviewers:** TBD

## Background

Our app sends users notifications (new message, mention, follow, system alert). Today each
notification is written to a `notifications` table and the client polls `GET /notifications`
every 30 seconds. Users complain notifications feel slow, and the polling load on the DB is
now ~40% of read traffic at peak. We want notifications to feel instant.

## Proposed design

We'll add a real-time fanout service using WebSockets.

1. When an event occurs (e.g. user A mentions user B), the originating service publishes a
   message to a new Redis Pub/Sub channel, `notifications:<user_id>`.
2. A new **Fanout Service** (Node.js) holds one WebSocket connection per online user. It
   subscribes to the Redis channel for each connected user. On receiving a published message,
   it pushes the notification down the user's WebSocket immediately.
3. The client opens a WebSocket to the Fanout Service on app load and renders notifications
   as they arrive. We keep writing to the `notifications` table so history still works, and
   we drop the 30-second polling.

We'll run 3 instances of the Fanout Service behind a load balancer for redundancy.

## Data model

No schema changes. The existing `notifications` table is unchanged. Redis holds only
transient pub/sub messages (not persisted).

## Rollout

We'll deploy the Fanout Service, switch the client to WebSockets in the next app release, and
turn off polling. Expected latency: sub-second delivery.

## Why WebSockets

WebSockets give us true server push with low overhead per message, which is what "instant"
requires. They're widely supported in browsers.

## Open questions

- What WebSocket library should we use?
