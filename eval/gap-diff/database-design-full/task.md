# Database design review

Review this Postgres schema + a query that runs on every page load of a multi-tenant B2B SaaS
(orgs, users, orders). Find every real problem — correctness, integrity, performance, multi-tenancy,
operational. Be thorough and specific.

```sql
CREATE TABLE orgs (id serial PRIMARY KEY, name text);
CREATE TABLE users (id serial PRIMARY KEY, org_id int, email text, role text);
CREATE TABLE orders (
  id serial PRIMARY KEY,
  user_id int,
  amount float,                 -- dollars
  status text,                  -- 'pending','paid','refunded'
  created_at timestamp DEFAULT now()
);

-- runs on every dashboard load, for the logged-in user's org:
SELECT o.*, u.email
FROM orders o JOIN users u ON u.id = o.user_id
WHERE u.org_id = 42
ORDER BY o.created_at DESC;
```
