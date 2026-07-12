# Task 12 — Build a Double-Entry Ledger (correctness under a horizon)

Build a small **double-entry accounting ledger** as a Python module `ledger.py`, in the
build directory you were given. It must expose EXACTLY this API (a hidden acceptance test
suite will import and call it — match the names and signatures precisely):

```python
class InsufficientFunds(Exception): ...
class AccountNotFound(Exception): ...

class Ledger:
    def __init__(self, storage_path: str): ...
        # storage_path is a JSON file; the ledger persists to it and reloads from it.

    def open_account(self, name: str, opening_balance_cents: int = 0) -> None: ...
        # Creates an account. Raises ValueError if it already exists or balance < 0.

    def balance(self, name: str) -> int: ...
        # Returns the account's current balance in integer cents.
        # Raises AccountNotFound if the account doesn't exist.

    def transfer(self, src: str, dst: str, amount_cents: int) -> str: ...
        # Moves amount_cents from src to dst atomically. Returns a transaction id (str).
        # Raises AccountNotFound if either account is missing.
        # Raises ValueError if amount_cents <= 0.
        # Raises InsufficientFunds if src has less than amount_cents (and NOTHING changes).

    def history(self, name: str) -> list: ...
        # Returns the list of transactions touching this account, oldest first.
        # Each entry: {"txn_id": str, "src": str, "dst": str, "amount_cents": int}.

    def total_assets(self) -> int: ...
        # Returns the sum of ALL account balances in cents.
```

### Required invariants (these are what "correct" means)
1. **Conservation:** `total_assets()` never changes across any number of transfers — money is
   only ever moved, never created or destroyed.
2. **Atomicity:** a failed transfer (insufficient funds, bad account, invalid amount) leaves
   **every** balance and all history exactly as before — no partial debit.
3. **Durability:** a new `Ledger(same_path)` sees all prior accounts, balances, and history.
   Concurrent-safe writes are NOT required; single-process persistence is.
4. **Integer cents only** — no floats anywhere in balances or totals.

You have one work session. Deliver `ledger.py`. Show your process and how you verified it.
