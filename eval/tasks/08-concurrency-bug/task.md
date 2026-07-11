# Task 08 — Concurrency Bug (flash-sale oversell)

An inventory service oversells during high-traffic flash sales. The code, bug report,
and load harness are in `context/inventory.py`.

**Bug report (ops):** "We sold 1,240 units of SKU-9 but only had 1,000 in stock —
oversold by 240. Only happens under heavy load; we can't reproduce it with a single
test client on staging. The `reserve_stock` code has a check AND a lock AND passing
tests, and it 'looks right.' Find and fix it."

Find the root cause and fix it. Explain precisely why it oversells under load and why
the single-client test never catches it.
