# Udatracker

A minimal order-tracking service built test-first: an `OrderTracker` class holding
the business rules, a thin Flask API in front of it, and in-memory storage behind it.

Run the tests from this directory (the project root):

```
pytest
```

Run the app:

```
python -m backend.app
```

## Reflection

- **Design trade-off: validate in the class, translate in the route.** Every rule
  (non-empty IDs, positive integer quantities, known statuses, no duplicate IDs)
  lives in `OrderTracker` and is signalled with `ValueError`. The Flask routes only
  decide which HTTP code that error deserves - 409 for a duplicate ID, 404 for a
  missing order, 400 for everything else. The cost is that the routes inspect the
  error message text to pick a code, which is a little brittle; the benefit is that
  the entire rulebook is testable against a mock with no HTTP involved, and a second
  transport (a CLI, a queue consumer) would inherit the rules for free.

- **Update copies rather than mutates.** `update_order_status` reads the order,
  builds a new dict with the new status, and saves that. I wrote
  `test_update_order_status_does_not_mutate_stored_dict` before the implementation,
  and it earns its place: an in-place mutation would still pass the happy-path test
  while quietly making the save call redundant and coupling correctness to whether
  the storage layer happens to hand back a copy.

- **Testing insight: the mock caught ordering, not just outcomes.** Asserting
  `mock_storage.get_order.assert_not_called()` on an invalid status forced
  `update_order_status` to check the status *before* touching storage. The plain
  "does it raise" test passed either way - it was the interaction assertion that
  pinned down fail-fast behaviour. Parametrizing the quantity test also caught a real
  bug: `isinstance(True, int)` is `True` in Python, so a boolean sailed through the
  positive-integer check until I excluded it explicitly.

- **Next steps.** Add `DELETE /api/orders/<order_id>` to round out CRUD; enforce a
  status transition graph so an order cannot go from `delivered` back to `pending`;
  and swap `InMemoryStorage` for a SQLite-backed implementation. The storage
  interface is already narrow - `save_order`, `get_order`, `get_all_orders` - so that
  swap should not touch `OrderTracker` or the routes at all.

## Project structure

```
.
├── backend
│   ├── __init__.py
│   ├── app.py
│   ├── in_memory_storage.py
│   ├── order_tracker.py
│   ├── requirements.txt
│   └── tests
│       ├── __init__.py
│       ├── test_api.py
│       └── test_order_tracker.py
├── frontend
│   ├── css
│   │   └── style.css
│   ├── index.html
│   └── js
│       └── script.js
├── pytest.ini
└── README.md
```
