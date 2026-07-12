# Code archaeology

You've been asked to change one thing in this legacy function: make the retry count configurable
(it's currently hardcoded to 3). Before you touch it, investigate what you'd need to understand so
you don't break something. Enumerate the questions you'd need answered, the hidden dependencies and
risks, and what you'd check before making the change.

```python
def sync_account(account_id, force=False):
    lock = redis.setnx(f"sync:{account_id}", 1)
    if not lock and not force:
        return
    redis.expire(f"sync:{account_id}", 300)
    for attempt in range(3):
        try:
            data = upstream.fetch(account_id, timeout=10 * (attempt + 1))
            if data.get('version') <= get_local_version(account_id):
                break
            db.write(account_id, data)
            emit_event("account.synced", account_id, data['version'])
            break
        except UpstreamError:
            if attempt == 2:
                emit_event("account.sync_failed", account_id)
            time.sleep(2 ** attempt)
    redis.delete(f"sync:{account_id}")
```
