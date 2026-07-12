# Task 12b — Build a Money-Transfer Ledger

Build a small **money-transfer ledger** as a Python module `ledger.py`, in the build
directory you were given. It tracks account balances and lets you move money between
accounts, saving everything to a JSON file so it survives between runs.

It must expose EXACTLY this API (match names and signatures precisely):

```python
class InsufficientFunds(Exception): ...
class AccountNotFound(Exception): ...

class Ledger:
    def __init__(self, storage_path: str): ...
        # storage_path is a JSON file the ledger reads on startup and writes on changes.

    def open_account(self, name: str, opening_balance_cents: int = 0) -> None: ...
        # Create a new account with a starting balance.

    def balance(self, name: str) -> int: ...
        # Return the account's current balance in integer cents.

    def transfer(self, src: str, dst: str, amount_cents: int) -> str: ...
        # Move amount_cents from src to dst. Return a transaction id (str).

    def history(self, name: str) -> list: ...
        # Return the transactions touching this account, oldest first.
        # Each entry: {"txn_id": str, "src": str, "dst": str, "amount_cents": int}.

    def total_assets(self) -> int: ...
        # Return the sum of all account balances in cents.
```

Handle the error cases sensibly: `AccountNotFound` when an account doesn't exist,
`InsufficientFunds` when a transfer can't be covered, `ValueError` for clearly invalid
input. Make it robust enough to trust with real money.

You have one work session. Deliver `ledger.py`. Show your process and how you verified it.
