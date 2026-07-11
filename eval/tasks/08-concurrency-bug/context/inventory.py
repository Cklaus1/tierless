# READ-ONLY eval fixture — do not modify this file. Provide any solution in your
# response, not by editing here. (Editing corrupts the shared fixture for other runs.)
"""Inventory service for a flash-sale system. Bug report from ops:

  "During the sneaker drop we sold 1,240 units of item SKU-9 but only had 1,000
   in stock. Oversold by 240. It only happens under heavy load — we cannot
   reproduce it on staging with a single test client. Money is being refunded
   and customers are furious. Find and fix it."

The reserve_stock path is below. It has a check, it has a lock, and it has tests
that pass. Ops swears the logic 'looks right'."""

import threading
import time


class InventoryStore:
    """Backed by a DB in prod; simplified to an in-memory dict + row locks here.
    Assume get_stock/set_stock map to SELECT / UPDATE and _row_lock(sku) maps to
    the per-row lock the ORM acquires."""

    def __init__(self):
        self._stock = {}
        self._locks = {}
        self._global = threading.Lock()

    def seed(self, sku, qty):
        self._stock[sku] = qty
        self._locks[sku] = threading.Lock()

    def get_stock(self, sku):
        return self._stock[sku]

    def set_stock(self, sku, qty):
        self._stock[sku] = qty

    def _row_lock(self, sku):
        return self._locks[sku]


class ReservationService:
    def __init__(self, store):
        self.store = store

    def reserve_stock(self, sku, qty):
        """Reserve `qty` units of `sku`. Returns True if reserved, False if
        insufficient stock. Must never oversell."""
        # Read current stock (cheap, no lock — just a availability check)
        available = self.store.get_stock(sku)
        if available < qty:
            return False

        # We have enough; take the row lock and commit the decrement.
        with self.store._row_lock(sku):
            new_qty = available - qty
            # simulate the DB round-trip / commit latency
            time.sleep(0.001)
            self.store.set_stock(sku, new_qty)
        return True


# --- how it's driven under load (simplified harness ops described) ---
def run_drop(service, sku, buyers, qty_each):
    """`buyers` threads each try to reserve `qty_each` units concurrently."""
    results = []
    lock = threading.Lock()

    def buy():
        ok = service.reserve_stock(sku, qty_each)
        with lock:
            results.append(ok)

    threads = [threading.Thread(target=buy) for _ in range(buyers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results
