# Debugging task

A production Python service throws this error, intermittently, ~1% of requests to `/checkout`:

```
Traceback (most recent call last):
  File "app/checkout.py", line 88, in handle_checkout
    total = summarize(cart, user)
  File "app/checkout.py", line 41, in summarize
    return applied.total
AttributeError: 'NoneType' object has no attribute 'total'
```

Here is the current source of `app/checkout.py` (the version in the repo, `main` branch):

```python
 1  from decimal import Decimal
 2
 3  class Receipt:
 4      def __init__(self, subtotal, discount, total):
 5          self.subtotal = subtotal
 6          self.discount = discount
 7          self.total = total
 8
 9  def find_discount(user, subtotal):
10      # returns a Decimal rate (0..1), or None if no discount applies
11      if user.tier == "gold":
12          return Decimal("0.10")
13      if user.tier == "silver":
14          return Decimal("0.05")
15      return None
16
17  def apply_discount(cart, user):
18      subtotal = sum((item.price * item.qty for item in cart.items), Decimal("0"))
19      rate = find_discount(user, subtotal)
20      if rate is None:
21          return Receipt(subtotal, Decimal("0"), subtotal)
22      discount = subtotal * rate
23      return Receipt(subtotal, discount, subtotal - discount)
24
25  def summarize(cart, user):
26      applied = apply_discount(cart, user)
27      return applied.total
```

The traceback says the crash is at `return applied.total` — but note the source shows that on
**line 27**, and the traceback says **line 41**. Also, `apply_discount` never returns `None`.

Find the root cause and explain how to fix it. Walk through your reasoning.
