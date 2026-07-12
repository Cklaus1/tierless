# GRADER checklist — database-design (13 items; planted defects)

1 amount is FLOAT — money must be numeric/integer cents: r"float.*(money|amount|numeric|cents|precision)|money.*(float|numeric|decimal|cents)|amount.*(numeric|decimal|integer|cents)|never.*float.*money|use (numeric|decimal)"
2 no FOREIGN KEYs (org_id, user_id are bare int): r"foreign key|FK\b|references|no.*(fk|foreign)|orphan|referential integrit|user_id.*(fk|reference|constraint)"
3 no index on orders.user_id / created_at (the query does a scan): r"index|no index|missing index.*(user_id|created_at)|seq(uential)? scan|full.*scan|(user_id|created_at).*(index|indexed)"
4 status/role should be enum or CHECK constraint (free text): r"enum|check constraint|status.*(enum|check|constrain)|role.*(enum|check|constrain)|free.?text.*(status|role)|constrain.*(status|role)"
5 nullability not specified — org_id/email/user_id should be NOT NULL: r"not null|nullab|null.*(org_id|user_id|email)|nullable.*(should|must)|missing not.null|allow.*null"
6 no UNIQUE on users.email (or org_id+email) — duplicates possible: r"unique.*(email|constraint)|email.*(unique|duplicate)|duplicate.*email|no unique"
7 the query MISSES org-scoping on the JOIN correctness / SELECT o.* leaks all columns: r"SELECT \*|select o\.\*|select star|over.?fetch|all columns|only.*(needed|columns)|explicit column"
8 no pagination — dashboard query returns ALL orders unbounded: r"paginat|limit|unbounded|all orders|no limit|LIMIT|cursor|page"
9 org_id hardcoded (=42) — how is tenant scoping enforced / injection risk: r"hardcod|= ?42|parameter|tenant.*(scop|isolat|enforc)|injection|bind|placeholder"
10 timestamp without time zone — should be timestamptz: r"timestamptz|time zone|timezone|without time zone|tz\b|UTC"
11 N+1 or JOIN correctness / no composite index for (org via users): r"n\+1|composite index|(user_id, created_at)|covering index|index.*(user_id, created_at)|join.*(index|slow)"
12 EXPLAIN / verify query plan at realistic scale: r"explain|query plan|analyze|realistic (data|scale)|at scale|benchmark.*quer"
13 migrations/ops: no created_at index means slow ORDER BY; backfill/lock concerns for adding constraints: r"add.*constraint.*(lock|concurrent)|migration.*(lock|concurrent|backfill)|ALTER.*(lock|concurrent)|CREATE INDEX CONCURRENTLY|adding.*(fk|constraint).*(lock|large)"

## discriminating (code-specific, need to read the schema): #1 float money, #2 no FKs, #3 missing
## indexes, #7 SELECT o.* + org-scoping, #8 no pagination. Recite-generic misses: a shallow answer
## says "add indexes and constraints" without naming THIS schema's specific gaps.
