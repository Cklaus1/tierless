# Adversarial code review

Review this Python function for bugs. Find as many real defects as you can — correctness, edge
cases, resource handling, concurrency, security. For each: the line/area, what's wrong, and the
failure it causes.

```python
 1  import json, os, threading
 2  _cache = {}
 3  _hits = 0
 4
 5  def process_orders(path, discount_rate, tax_rate=0.08):
 6      global _hits
 7      f = open(path)
 8      orders = json.load(f)
 9      results = []
10      for o in orders:
11          if o['id'] in _cache:
12              _hits += 1
13              results.append(_cache[o['id']])
14              continue
15          subtotal = 0
16          for item in o['items']:
17              subtotal += item['price'] * item['qty']
18          discounted = subtotal * (1 - discount_rate)
19          total = discounted + discounted * tax_rate
20          o['total'] = round(total, 2)
21          _cache[o['id']] = o
22          results.append(o)
23      avg = sum(r['total'] for r in results) / len(results)
24      return {'orders': results, 'average': avg, 'cache_hits': _hits}
```
