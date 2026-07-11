# Task 04 — Migration Plan

A production Postgres table `users` has a column `full_name` (text). Product wants to
split it into `first_name` and `last_name` so they can personalize emails ("Hi Sarah").
The `users` table has ~4 million rows. The app is a live, always-on service with many
other features reading and writing `users`.

Plan this change.
