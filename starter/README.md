# Udatracker

A minimal order-tracking service built test-first: an `OrderTracker` class holding
the business rules, a thin Flask API in front of it, and in-memory storage behind it.

Run the tests from this directory (the project root):

```
pytest
```

Run the app, then open http://127.0.0.1:5000/ :

```
python -m backend.app
```

## Reflection

- **A parametrized test caught a real bug.** `isinstance(True, int)` is `True` in
  Python, so `quantity=True` sailed straight through the positive-integer check
  until the test forced me to exclude booleans explicitly.

- **Interaction assertions pinned down ordering, not just outcomes.** Asserting
  `mock_storage.get_order.assert_not_called()` on an invalid status is what forced
  `update_order_status` to validate *before* touching storage. The plain "does it
  raise" test passed either way.

- **Design trade-off: validate in the class, translate in the route.** Every rule
  lives in `OrderTracker` and surfaces as a `ValueError`; the routes only decide
  which code it deserves - 409 duplicate, 404 missing, 400 otherwise. The cost is
  routes matching on message text; the benefit is a rulebook fully testable against
  a mock with no HTTP involved.

- **Next steps.** Add `DELETE /api/orders/<order_id>`, enforce a transition graph so
  a `delivered` order cannot go back to `pending`, and swap `InMemoryStorage` for
  SQLite - the storage interface is narrow enough that the swap should not touch
  `OrderTracker` or the routes.

## API

| Endpoint | Method | Notes |
| --- | --- | --- |
| `/api/orders` | POST | 201 with the order; 400 invalid, 409 duplicate ID |
| `/api/orders/<order_id>` | GET | 200 with the order; 404 if unknown |
| `/api/orders/<order_id>/status` | PUT | 200 with the updated order; 400 bad status, 404 unknown |
| `/api/orders/<order_id>` | PUT | Alias for the above, since the brief names it both ways |
| `/api/orders` | GET | 200 with all orders |
| `/api/orders?status=<status>` | GET | 200 with matching orders; 400 if the status is empty or unknown |

Errors come back as `{"error": "..."}`, including for unmatched `/api/` paths.

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
│       ├── test_api.py          # provided, unmodified
│       ├── test_api_extra.py    # additional API tests
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
