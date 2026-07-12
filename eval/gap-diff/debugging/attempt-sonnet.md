# Technical Review: Intermittent `AttributeError` on `/checkout`

## Summary

The service crashes intermittently (~1% of requests) with `AttributeError: 'NoneType' object has no attribute 'total'` at the `return applied.total` line in `summarize()`. The root cause is a **stale deployed version of `app/checkout.py`** -- the traceback line numbers do not match the current source code, and `apply_discount()` as written never returns `None`, meaning the crash cannot occur from the code currently in the repository.

## Detailed Reasoning

### 1. The line number mismatch is the primary clue

The traceback reports the crash at **line 41** of `app/checkout.py`:

```
  File "app/checkout.py", line 41, in handle_checkout
    total = summarize(cart, user)
  File "app/checkout.py", line 41, in summarize
    return applied.total
```

But the current source shows `summarize()` starts at **line 25**, and `return applied.total` is at **line 27**. The traceback says `summarize()` is at line 41 -- a difference of 14 lines. This means the **running code is not the same as the code in the repo**.

The deployed version of `app/checkout.py` is older (or otherwise different) and has 14 extra lines before the `summarize()` function. Those extra lines could be:
- Dead code or commented-out blocks that were later removed.
- Additional functions or imports that were refactored away.
- A different version of the file that was never updated in the repo after deployment.

### 2. `apply_discount()` as written cannot return `None`

In the current source, `apply_discount()` has exactly two return paths:

- Line 21: `return Receipt(subtotal, Decimal("0"), subtotal)` -- when `rate is None`
- Line 23: `return Receipt(subtotal, discount, subtotal - discount)` -- when a discount applies

Both paths return a `Receipt` object. There is no `return None` statement, and no code path that can produce `None`. Therefore, `applied` in `summarize()` is always a `Receipt` object, and `applied.total` can never raise `AttributeError`.

**The crash is impossible with the current source code.** This confirms the running binary is a different version.

### 3. What the deployed version likely looks like

Reconstructing the deployed version from the line number offset (14 lines earlier), the deployed `summarize()` at line 41 suggests the file had roughly 14 more lines before it. A plausible deployed version would have `apply_discount()` structured differently -- perhaps with a missing `return` on one path, or an early `return None` that was later fixed in the repo but not redeployed.

For example, the deployed code might have looked like:

```python
def apply_discount(cart, user):
    subtotal = sum((item.price * item.qty for item in cart.items), Decimal("0"))
    rate = find_discount(user, subtotal)
    if rate is None:
        return Receipt(subtotal, Decimal("0"), subtotal)
    discount = subtotal * rate
    # BUG: missing return statement here -- falls through to implicit None
    Receipt(subtotal, discount, subtotal - discount)
```

Or the function might have had a conditional branch that could reach the end without returning anything. In either case, `applied` would be `None`, and `applied.total` would crash.

### 4. Why it is intermittent (~1% of requests)

The ~1% crash rate suggests the bug only triggers under a specific condition. Given the structure of `apply_discount()`, the most likely scenario is:

- **Gold/silver users** (the majority) always get a `Receipt` back -- no crash.
- **Users with no applicable discount** (the ~1%) hit the `rate is None` path. If the deployed code had a bug where this path returned `None` instead of a `Receipt`, only those users would crash.

Alternatively, if the bug is a missing `return` on the discount-applied path, then gold/silver users (~1%) would crash while users with no discount would not.

Either way, the intermittent nature is explained by the fact that only a subset of users trigger the `None`-returning code path.

### 5. Additional observations and risks

Even after fixing the deployed version mismatch, the current source has a latent fragility:

- **No defensive check in `summarize()`**: The function assumes `apply_discount()` always returns a non-`None` `Receipt`. If `apply_discount()` is ever modified in the future to return `None` on a new code path, this will crash silently. Adding an explicit check (`if applied is None: raise ValueError(...)`) would fail fast with a clearer error.

- **`find_discount()` takes a `subtotal` argument it never uses**: The function signature is `find_discount(user, subtotal)` but the body only checks `user.tier`. This is a code smell -- either `subtotal` should be used for tier eligibility logic, or the parameter should be removed. This could mask a real business logic bug where a discount should only apply above a certain cart value.

- **No error handling at the `/checkout` endpoint level**: If `summarize()` ever does raise (whether from `None` or any other cause), the error propagates to the HTTP handler. A 500 response to a customer at checkout is a poor user experience. The endpoint should catch exceptions and return a user-friendly error.

- **No logging around the crash**: With only a 1% crash rate, without structured logging of `user.tier`, cart contents, and the return value of `apply_discount()`, diagnosing this issue required source code archaeology. Adding observability would make future debugging faster.

## Root Cause

**The deployed version of `app/checkout.py` is stale and differs from the repo version.** The deployed code has a bug in `apply_discount()` (likely a missing `return` statement or an explicit `return None` on one path) that causes `summarize()` to receive `None` instead of a `Receipt` object. The repo was updated to fix this bug, but the fix was never deployed to production.

## Fix

1. **Immediate**: Redeploy the current (fixed) version of `app/checkout.py` from the repo to production. Verify the deployed line numbers match the source.

2. **Short-term**: Add a defensive check in `summarize()`:
   ```python
   def summarize(cart, user):
       applied = apply_discount(cart, user)
       if applied is None:
           raise RuntimeError("apply_discount returned None for user tier")
       return applied.total
   ```

3. **Process**: Ensure the deployment pipeline uses the exact source from the `main` branch (e.g., via CI/CD with version pinning) to prevent stale deployments.

4. **Cleanup**: Remove the unused `subtotal` parameter from `find_discount()` to avoid confusion.