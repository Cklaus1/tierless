## Migration: Split users.full_name into users.first_name and users.last_name
**Rows affected (estimated):** ~4,000,000
**Irreversible after:** Step 3 (DROP COLUMN full_name)

---

### Pre-flight

- [ ] Backup / snapshot taken and RESTORE TESTED (an unverified backup is a hope, not a backup)
- [ ] Rehearsed on a production-shaped copy -- row counts and timing recorded
- [ ] Batch size chosen: 10,000 rows per batch, 50ms sleep between batches -- never one giant transaction
- [ ] Runs against replica lag / locks checked (what does this block, for how long?)
- [ ] App team surveyed: all write paths to users identified for dual-write

---

### Data-quality reality of the split (T5)

A naive `split(" ")` does NOT work. `full_name` is free-text and contains edge cases:

| Pattern | Example | Problem |
|---|---|---|
| Single name | "Cher" | No last name |
| Multiple first names | "Mary Jane Watson" | Where does first end, last begin? |
| Particles in last name | "van der Berg", "de la Cruz" | Multi-word last names |
| Titles / honorifics | "Dr. Smith", "Prof. Chen" | Not part of the legal name |
| Empty / null | "" or NULL | No-op, skip |
| Special characters | "O'Brien", "Jose-Maria" | Hyphens, apostrophes |

**Strategy:** Use a heuristic split on the LAST space:
- "Mary Jane Watson" -> first="Mary Jane", last="Watson"
- "van der Berg" -> first="van der", last="Berg"
- "Cher" -> first="Cher", last=NULL
- "Dr. Smith" -> first="Dr.", last="Smith" (titles pass through; flagged for manual review)

Records with NULL or empty full_name are skipped. Records with only one word get first_name set, last_name=NULL. A post-migration audit flags names with titles or unusual patterns for manual review.

---

### Verification queries (written BEFORE migrating)

```sql
-- Count: old shape == new shape (for rows that had a value)
SELECT COUNT(*) FROM users WHERE full_name IS NOT NULL AND full_name != '';
-- Should equal:
SELECT COUNT(*) FROM users WHERE first_name IS NOT NULL OR last_name IS NOT NULL;

-- No NULLs in first_name where full_name had a value
SELECT COUNT(*) FROM users
WHERE full_name IS NOT NULL AND full_name != ''
  AND first_name IS NULL;
-- Must be 0

-- Spot-check: 5 specific known records, verified by hand
SELECT id, full_name, first_name, last_name
FROM users
WHERE id IN (12345, 67890, 11111, 22222, 33333);
-- Compare full_name against first_name || ' ' || last_name for each
```

---

### Rollback

- **At step 1 (Expand):** `ALTER TABLE users DROP COLUMN IF EXISTS first_name, DROP COLUMN IF EXISTS last_name;` -- no data loss, old code unchanged.
- **At step 2 (Migrate):** Flip the feature flag back to read `full_name`. Stop the dual-write trigger. The backfill is resumable from the last completed batch. No data is lost.
- **At step 3 (Contract):** Restore from backup if the old column was already dropped and corruption is detected. Acceptable data-loss window: zero, if rollback is caught before step 3.

---

### Abort criteria

- Replica lag exceeds 30 seconds during batch backfill
- Any batch produces a row-count mismatch between old and new columns
- Error rate on writes during dual-write exceeds 0.1%
- Verification query finds NULLs in first_name where full_name had a value

---

## Step 1: EXPAND -- Add new columns (Deploy 1)

**Goal:** New columns exist alongside the old. Old code runs unchanged. Reversible by dropping the new columns.

```sql
ALTER TABLE users ADD COLUMN first_name text;
ALTER TABLE users ADD COLUMN last_name text;
```

No data change. No code change. The app continues reading/writing `full_name` only.

**Verification:**
```sql
SELECT COUNT(*) FROM users WHERE first_name IS NOT NULL;
-- Must be 0
```

**Rollback:** Drop the columns. Zero impact.

---

## Step 2: MIGRATE -- Backfill + dual-write (Deploy 2)

**Goal:** Populate new columns from existing data, then keep them in sync with new writes.

### 2a. Code change: dual-write

The application code that writes to `users` is updated to write to all three columns:

```
-- Old:
UPDATE users SET full_name = $1 WHERE id = $2

-- New (behind feature flag):
UPDATE users SET full_name = $1, first_name = $2, last_name = $3 WHERE id = $2
```

A database trigger provides a safety net so that any writes bypassing the app (ad-hoc SQL, other services) also stay in sync:

```sql
CREATE OR REPLACE FUNCTION sync_name_columns() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
    IF NEW.first_name IS NULL AND NEW.last_name IS NULL AND NEW.full_name IS NOT NULL THEN
      -- App hasn't written first/last yet; derive from full_name
      NEW.first_name := split_full_name_first(NEW.full_name);
      NEW.last_name  := split_full_name_last(NEW.full_name);
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_names
  BEFORE INSERT OR UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION sync_name_columns();
```

The trigger ensures that if `full_name` is written but `first_name`/`last_name` are NULL, they are auto-derived using the same heuristic. This is the safety net -- not the primary path.

### 2b. Batch backfill of historical data

Backfill the ~4M existing rows in batches of 10,000, with 50ms sleep between batches to limit lock contention and replica lag.

```sql
DO $$
DECLARE
  batch_size CONSTANT int := 10000;
  last_id int := 0;
  total_count int := 0;
  batch_count int := 0;
  start_ts timestamptz := clock_timestamp();
  row_count int;
BEGIN
  LOOP
    UPDATE users
    SET first_name = split_full_name_first(full_name),
        last_name  = split_full_name_last(full_name)
    WHERE id > last_id
      AND full_name IS NOT NULL
      AND full_name != ''
      AND id <= last_id + batch_size;

    GET DIAGNOSTICS row_count = ROW_COUNT;
    total_count := total_count + row_count;
    batch_count := batch_count + 1;

    -- Verify this batch
    IF row_count = 0 THEN
      EXIT; -- No more rows to process
    END IF;

    last_id := last_id + batch_size;

    -- Log progress
    RAISE NOTICE 'Batch %: processed % total rows (last_id=%)', batch_count, total_count, last_id;

    -- Sleep to limit impact on live traffic
    PERFORM pg_sleep(0.05);
  END LOOP;

  RAISE NOTICE 'Backfill complete: % rows in % batches over %',
    total_count, batch_count, clock_timestamp() - start_ts;
END $$;
```

The SQL functions `split_full_name_first()` and `split_full_name_last()` implement the heuristic described in the data-quality section above.

**Verification after backfill:**
```sql
-- All non-empty full_names should have first_name populated
SELECT COUNT(*) FROM users
WHERE full_name IS NOT NULL AND full_name != ''
  AND first_name IS NULL;
-- Must be 0

-- Spot-check known records
SELECT id, full_name, first_name, last_name
FROM users WHERE id IN (12345, 67890, 11111, 22222, 33333);
```

### 2c. Switch readers to new columns (behind feature flag)

The application's read paths are updated to read `first_name` and `last_name` instead of parsing `full_name`, behind a feature flag. If the flag is off, the app falls back to `full_name`.

**Rollback at any point during Step 2:** Flip the feature flag back to read `full_name`. Stop the dual-write trigger. The backfill is resumable from the last `last_id` checkpoint. No data is lost.

---

## Step 3: CONTRACT -- Remove old column (Deploy 3, deferred)

**Goal:** Only after the new shape has served production traffic and verification passes: remove old code paths, then drop the old column. This is the only irreversible step. It can wait weeks.

### 3a. Remove old code paths

Remove all code that reads or writes `full_name`. The dual-write trigger and app-level dual-write are removed. The app now only touches `first_name` and `last_name`.

### 3b. Drop the old column (later, after monitoring confirms stability)

```sql
ALTER TABLE users DROP COLUMN full_name;
DROP TRIGGER trg_sync_names ON users;
DROP FUNCTION sync_name_columns();
```

**Verification after drop:**
```sql
-- Confirm no rows were lost
SELECT COUNT(*) FROM users;
-- Must match pre-migration count

-- Confirm no NULL first_name where data existed
SELECT COUNT(*) FROM users WHERE first_name IS NULL;
-- Should be 0 (or only legitimately empty names)
```

---

## Timeline

| Step | Action | Duration estimate | Risk |
|---|---|---|---|
| Pre-flight | Backup, rehearse on prod-shaped copy | 1 day | None |
| Deploy 1 | Add columns (EXPAND) | < 1 second | None -- additive only |
| Deploy 2 | Dual-write code + trigger + batch backfill (MIGRATE) | 2-4 hours for 4M rows at 10k/batch | Low -- reversible, trigger safety net |
| Monitor | Observe error rates, replica lag, verification counts | 1-2 weeks | None |
| Deploy 3 | Remove old code, drop column (CONTRACT) | < 1 second | Low -- only after weeks of stable operation |