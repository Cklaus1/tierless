"""Shopping cart totals. Bug report: customers occasionally see a total that is
a few cents LOWER than the sum of their item prices. Finance flagged it.
Reproimport: intermittent, only some carts, always small amounts."""

from decimal import Decimal, ROUND_HALF_UP


class Cart:
    def __init__(self):
        self.items = []            # list of (name, unit_price_cents, qty)
        self._discount_rate = 0.0  # e.g. 0.10 for 10% off

    def add_item(self, name, unit_price_cents, qty=1):
        self.items.append((name, unit_price_cents, qty))

    def set_discount(self, rate):
        self._discount_rate = rate

    def line_total_cents(self, unit_price_cents, qty):
        return unit_price_cents * qty

    def subtotal_cents(self):
        return sum(self.line_total_cents(p, q) for _, p, q in self.items)

    def total_cents(self):
        subtotal = self.subtotal_cents()
        # Apply discount, then round to whole cents for charging.
        # Do the arithmetic in Decimal (not float) and round HALF_UP:
        #  - float rates like 0.10 aren't exact, so subtotal*(1-rate) drifts;
        #  - Python's built-in round() is banker's rounding (half-to-even),
        #    which sends an exact half-cent DOWN and undercharges.
        rate = Decimal(str(self._discount_rate))
        discounted = Decimal(subtotal) * (Decimal(1) - rate)
        return int(discounted.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def apply_loyalty_points(total_cents, points):
    """Each point is worth 1 cent off, capped at the total."""
    redeemed = min(points, total_cents)
    return total_cents - redeemed


# --- how it's used in checkout (simplified) ---
def checkout(cart, loyalty_points=0):
    total = cart.total_cents()
    total = apply_loyalty_points(total, loyalty_points)
    return total
