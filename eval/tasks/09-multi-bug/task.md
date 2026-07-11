# Task 09 — Multi-Bug Hunt (rate limiter)

A token-bucket rate limiter misbehaves in two opposite directions. Code and bug report
are in `context/rate_limiter.py`.

**Bug report:** "Users get rate-limited (429) *earlier* than the documented 100 req/min —
some after only ~60 requests. But a few power users say they can sometimes burst *way
over* the limit right after a quiet period. Both complaints are real. Fix the limiter so
it actually enforces 100/min."

Find and fix what's wrong. The report describes two different symptoms — make sure your
fix accounts for everything the report describes.
