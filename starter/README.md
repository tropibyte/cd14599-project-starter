# Udatracker

A minimal order-tracking service built test-first: an `OrderTracker` class holding
the business rules, a thin Flask API in front of it, and in-memory storage behind it.
Orders are lost when the server restarts.

## Running

From this directory (the one containing `backend/`):

```
pytest                  # 68 tests
python -m backend.app   # then open http://127.0.0.1:5000/
```

`PORT` and `FLASK_DEBUG` are read from the environment, so `PORT=8000 python -m
backend.app` moves the server if port 5000 is taken.

### Docker

```
docker build -t udatracker .
docker run --rm -p 5000:5000 udatracker
```

Or `docker compose up --build`. The image runs as a non-root user with the Werkzeug
debugger disabled, since the container binds a published port.

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

- **Next steps.** Swap `InMemoryStorage` for SQLite - the interface is four methods
  wide, so nothing above it should change - and enforce a transition graph so a
  `delivered` order cannot go back to `pending`. Listing needs pagination before it
  holds a real catalogue.

## API reference

The full contract is in [openapi.yaml](openapi.yaml). Errors are always
`{"error": "..."}`, including for unmatched `/api/` paths and wrong HTTP verbs.

| Endpoint | Method | Success | Errors |
| --- | --- | --- | --- |
| `/api/orders` | POST | 201, the order | 400 invalid field, 409 duplicate ID |
| `/api/orders` | GET | 200, all orders | - |
| `/api/orders?status=&customer_id=` | GET | 200, matching orders | 400 empty or unknown filter |
| `/api/orders/<order_id>` | GET | 200, the order | 404 unknown |
| `/api/orders/<order_id>/status` | PUT | 200, updated order | 400 bad status, 404 unknown |
| `/api/orders/<order_id>` | PUT | 200, updated order | Alias for the route above |
| `/api/orders/<order_id>` | DELETE | 200, deleted order | 404 unknown |

Valid statuses: `pending`, `processing`, `shipped`, `delivered`, `cancelled`.
On create, an omitted `status` defaults to `pending`; one that is present but empty
or unknown is a 400 rather than a silent rewrite.

### Sample requests

Create an order:

```
curl -X POST http://127.0.0.1:5000/api/orders \
     -H "Content-Type: application/json" \
     -d '{"order_id":"CURL001","item_name":"Headphones","quantity":1,"customer_id":"CUST123"}'
```

Fetch it, then ship it:

```
curl http://127.0.0.1:5000/api/orders/CURL001

curl -X PUT http://127.0.0.1:5000/api/orders/CURL001/status \
     -H "Content-Type: application/json" \
     -d '{"new_status":"shipped"}'
```

List and filter:

```
curl http://127.0.0.1:5000/api/orders
curl "http://127.0.0.1:5000/api/orders?status=shipped"
curl "http://127.0.0.1:5000/api/orders?customer_id=CUST123&status=shipped"
```

Delete it (the deleted record comes back):

```
curl -X DELETE http://127.0.0.1:5000/api/orders/CURL001
```

## Project structure

```
.
├── backend
│   ├── __init__.py
│   ├── app.py                   # routes only; no business rules
│   ├── in_memory_storage.py
│   ├── order_tracker.py         # all business rules
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
├── Dockerfile
├── docker-compose.yml
├── openapi.yaml
├── pytest.ini
└── README.md
```
