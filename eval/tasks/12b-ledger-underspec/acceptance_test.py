#!/usr/bin/env python3
# GRADER-ONLY acceptance battery for task 12. NOT shown to arms.
# Usage: python3 acceptance_test.py /path/to/arm/build/dir
# Imports the arm's ledger.py, runs adversarial checks, prints a JSON scorecard.
# Correctness is measured by EXECUTION, not opinion — each check is pass/fail.

import sys, os, json, importlib.util, tempfile, traceback

def load_ledger(build_dir):
    path = os.path.join(build_dir, "ledger.py")
    if not os.path.exists(path):
        return None, f"ledger.py not found in {build_dir}"
    spec = importlib.util.spec_from_file_location("arm_ledger", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        return None, f"import failed: {e}"
    return mod, None

def fresh(mod):
    # Use a fresh path that does NOT exist yet (a new ledger starts empty).
    # Pre-creating an empty file would force arms to special-case empty-file parsing,
    # which the spec doesn't require — the durability check (C5) covers real reload.
    d = tempfile.mkdtemp()
    path = os.path.join(d, "ledger.json")
    return mod.Ledger(path), path

CHECKS = []
def check(name):
    def deco(fn): CHECKS.append((name, fn)); return fn
    return deco

# --- C1: basic transfer + balances ---
@check("C1_basic_transfer")
def c1(mod):
    lg, _ = fresh(mod)
    lg.open_account("alice", 1000)
    lg.open_account("bob", 0)
    lg.transfer("alice", "bob", 300)
    assert lg.balance("alice") == 700, f"alice={lg.balance('alice')}"
    assert lg.balance("bob") == 300, f"bob={lg.balance('bob')}"

# --- C2: CONSERVATION across many transfers ---
@check("C2_conservation")
def c2(mod):
    lg, _ = fresh(mod)
    lg.open_account("a", 5000); lg.open_account("b", 3000); lg.open_account("c", 0)
    before = lg.total_assets()
    assert before == 8000, f"total={before}"
    for _ in range(20):
        lg.transfer("a", "b", 100); lg.transfer("b", "c", 50); lg.transfer("c", "a", 25)
    assert lg.total_assets() == 8000, f"conservation broken: {lg.total_assets()} != 8000"

# --- C3: ATOMICITY — insufficient funds changes NOTHING ---
@check("C3_atomicity_insufficient")
def c3(mod):
    lg, _ = fresh(mod)
    lg.open_account("a", 100); lg.open_account("b", 0)
    try:
        lg.transfer("a", "b", 500)  # more than a has
        assert False, "expected InsufficientFunds"
    except mod.InsufficientFunds:
        pass
    assert lg.balance("a") == 100, f"a debited on failure: {lg.balance('a')}"
    assert lg.balance("b") == 0, f"b credited on failure: {lg.balance('b')}"
    assert lg.total_assets() == 100

# --- C4: ATOMICITY — bad dst after implicit debit path ---
@check("C4_atomicity_bad_account")
def c4(mod):
    lg, _ = fresh(mod)
    lg.open_account("a", 100)
    try:
        lg.transfer("a", "ghost", 50)  # dst missing
        assert False, "expected AccountNotFound"
    except mod.AccountNotFound:
        pass
    assert lg.balance("a") == 100, f"a changed on failed transfer: {lg.balance('a')}"

# --- C5: DURABILITY across reload ---
@check("C5_durability")
def c5(mod):
    lg, path = fresh(mod)
    lg.open_account("a", 1000); lg.open_account("b", 500)
    lg.transfer("a", "b", 200)
    lg2 = mod.Ledger(path)  # reopen same file
    assert lg2.balance("a") == 800, f"reload a={lg2.balance('a')}"
    assert lg2.balance("b") == 700, f"reload b={lg2.balance('b')}"
    assert lg2.total_assets() == 1500

# --- C6: history is recorded and shaped right ---
@check("C6_history")
def c6(mod):
    lg, _ = fresh(mod)
    lg.open_account("a", 1000); lg.open_account("b", 0)
    tid = lg.transfer("a", "b", 100)
    h = lg.history("a")
    assert isinstance(h, list) and len(h) == 1, f"history={h}"
    e = h[0]
    assert e["src"]=="a" and e["dst"]=="b" and e["amount_cents"]==100, f"entry={e}"
    assert e["txn_id"]==tid, f"txn_id mismatch {e['txn_id']} != {tid}"

# --- C7: invalid-amount rejection (<=0), atomic ---
@check("C7_invalid_amount")
def c7(mod):
    lg, _ = fresh(mod)
    lg.open_account("a", 100); lg.open_account("b", 0)
    for bad in (0, -50):
        try:
            lg.transfer("a", "b", bad); assert False, f"expected ValueError for {bad}"
        except ValueError:
            pass
    assert lg.balance("a")==100 and lg.balance("b")==0

# --- C8: AccountNotFound on balance of missing account ---
@check("C8_missing_account")
def c8(mod):
    lg, _ = fresh(mod)
    try:
        lg.balance("nobody"); assert False, "expected AccountNotFound"
    except mod.AccountNotFound:
        pass

# --- C9: duplicate open + negative opening rejected ---
@check("C9_open_validation")
def c9(mod):
    lg, _ = fresh(mod)
    lg.open_account("a", 100)
    try: lg.open_account("a", 0); assert False, "dup open allowed"
    except ValueError: pass
    try: lg.open_account("neg", -5); assert False, "negative opening allowed"
    except ValueError: pass

# --- C10: integer cents only (no float leakage after ops) ---
@check("C10_integer_cents")
def c10(mod):
    lg, _ = fresh(mod)
    lg.open_account("a", 1000); lg.open_account("b", 0)
    lg.transfer("a", "b", 333)
    for acct in ("a","b"):
        assert isinstance(lg.balance(acct), int), f"{acct} balance not int: {type(lg.balance(acct))}"
    assert isinstance(lg.total_assets(), int)

def main():
    build_dir = sys.argv[1]
    mod, err = load_ledger(build_dir)
    results = {}
    if mod is None:
        # total failure to import → all checks fail
        for name, _ in CHECKS: results[name] = {"pass": False, "err": err}
    else:
        for name, fn in CHECKS:
            try:
                fn(mod); results[name] = {"pass": True}
            except Exception as e:
                results[name] = {"pass": False, "err": f"{type(e).__name__}: {e}"}
    passed = sum(1 for r in results.values() if r["pass"])
    total = len(results)
    print(json.dumps({
        "build_dir": build_dir,
        "passed": passed, "total": total, "rate": round(passed/total, 3),
        "results": results,
    }, indent=2))

if __name__ == "__main__":
    main()
