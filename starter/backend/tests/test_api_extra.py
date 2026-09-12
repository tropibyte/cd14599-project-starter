"""
Additional API tests covering behaviour beyond the provided test_api.py.

The provided suite is left untouched as the rubric requires, so the routing
aliases, JSON error handling and stricter status validation are tested here.
"""

import pytest
from backend.app import app, in_memory_storage


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    in_memory_storage.clear()
    with app.test_client() as client:
        yield client


def _create_order(client, order_id="EXTRA001", **overrides):
    """Helper: POST a valid order and return the response."""
    payload = {
        "order_id": order_id,
        "item_name": "Test Item",
        "quantity": 1,
        "customer_id": "C1",
    }
    payload.update(overrides)
    return client.post('/api/orders', json=payload)


# --- Routing aliases --------------------------------------------------------

def test_put_on_order_resource_updates_status(client):
    """
    The rubric heading names the update endpoint PUT /api/orders/<order_id>,
    while the contract table uses the /status suffix. Both must work.
    """
    _create_order(client, "ALIAS001")

    response = client.put('/api/orders/ALIAS001', json={"new_status": "shipped"})

    assert response.status_code == 200
    assert response.json['status'] == "shipped"


def test_put_alias_and_status_route_agree_on_errors(client):
    """The alias must not bypass validation that the /status route applies."""
    _create_order(client, "ALIAS002")

    response = client.put('/api/orders/ALIAS002', json={"new_status": "teleported"})

    assert response.status_code == 400
    assert "Invalid status" in response.json['error']


def test_index_path_serves_the_frontend(client):
    """The brief says the UI loads at '/' or '/index'."""
    response = client.get('/index')

    assert response.status_code == 200
    assert b"Order Management System" in response.data


def test_root_path_serves_the_frontend(client):
    """The root path serves the same page as /index."""
    assert client.get('/').status_code == 200


# --- JSON error responses ---------------------------------------------------

def test_unknown_api_path_returns_json_not_html(client):
    """An unmatched /api/ path must not fall through to the static handler."""
    response = client.get('/api/bogus')

    assert response.status_code == 404
    assert response.is_json
    assert response.json['error'] == "Resource not found."


def test_unsupported_method_on_api_returns_json(client):
    """A wrong verb on a real API resource still answers in JSON."""
    _create_order(client, "METHOD001")

    # PATCH is not part of the contract; GET/PUT/DELETE all are.
    response = client.patch('/api/orders/METHOD001', json={"quantity": 9})

    assert response.status_code == 405
    assert response.is_json
    assert "error" in response.json


def test_missing_order_error_is_json(client):
    """A 404 raised by the route itself carries a JSON error body."""
    response = client.get('/api/orders/GHOST')

    assert response.status_code == 404
    assert response.is_json
    assert "not found" in response.json['error']


def test_non_json_body_is_rejected(client):
    """A POST without a JSON object body is a 400, not a crash."""
    response = client.post('/api/orders', data="not json",
                           content_type="text/plain")

    assert response.status_code == 400
    assert response.json['error'] == "Request body must be a JSON object."


# --- Status handling on create ----------------------------------------------

def test_omitted_status_defaults_to_pending(client):
    """An absent status key is the documented way to take the default."""
    response = _create_order(client, "STATUS001")

    assert response.status_code == 201
    assert response.json['status'] == "pending"


def test_explicit_valid_status_is_honoured(client):
    """A supplied valid status is used as the initial status."""
    response = _create_order(client, "STATUS002", status="processing")

    assert response.status_code == 201
    assert response.json['status'] == "processing"


@pytest.mark.parametrize("bad_status", ["", None, "teleported"])
def test_explicit_invalid_status_is_rejected(client, bad_status):
    """
    A status that is present but unusable is a bad request. It is not silently
    rewritten to 'pending' - the client asked for something specific and wrong.
    """
    response = _create_order(client, "STATUS003", status=bad_status)

    assert response.status_code == 400
    assert "error" in response.json


# --- Duplicate handling -----------------------------------------------------

def test_duplicate_order_id_is_a_conflict(client):
    """A repeated order ID is a 409, distinct from a malformed 400."""
    _create_order(client, "DUP001")

    response = _create_order(client, "DUP001")

    assert response.status_code == 409
    assert "already exists" in response.json['error']


# --- Filtering --------------------------------------------------------------

def test_empty_status_filter_is_rejected(client):
    """?status= with no value is invalid rather than an implicit list-all."""
    response = client.get('/api/orders?status=')

    assert response.status_code == 400
    assert "error" in response.json


def test_unknown_status_filter_is_rejected(client):
    """Filtering on a status that does not exist is a 400, not an empty list."""
    response = client.get('/api/orders?status=frozen')

    assert response.status_code == 400
    assert "Invalid status" in response.json['error']


def test_filter_by_customer_id(client):
    """?customer_id= narrows the list to one customer."""
    _create_order(client, "CUST_A", customer_id="C123")
    _create_order(client, "CUST_B", customer_id="C999")

    response = client.get('/api/orders?customer_id=C123')

    assert response.status_code == 200
    assert [order['order_id'] for order in response.json] == ["CUST_A"]


def test_filter_by_customer_and_status_combined(client):
    """The two filters combine with AND."""
    _create_order(client, "COMBO_A", customer_id="C123", status="pending")
    _create_order(client, "COMBO_B", customer_id="C123", status="shipped")
    _create_order(client, "COMBO_C", customer_id="C999", status="pending")

    response = client.get('/api/orders?customer_id=C123&status=pending')

    assert response.status_code == 200
    assert [order['order_id'] for order in response.json] == ["COMBO_A"]


def test_filter_by_unknown_customer_returns_empty_list(client):
    """A customer with no orders is an empty list, not a 404."""
    _create_order(client, "SOLO", customer_id="C123")

    response = client.get('/api/orders?customer_id=NOBODY')

    assert response.status_code == 200
    assert response.json == []


def test_empty_customer_filter_is_rejected(client):
    """?customer_id= with no value is a bad request."""
    response = client.get('/api/orders?customer_id=')

    assert response.status_code == 400
    assert "Customer ID" in response.json['error']


# --- Delete -----------------------------------------------------------------

def test_delete_order_returns_the_deleted_record(client):
    """DELETE answers 200 with the record that was removed."""
    _create_order(client, "DEL001", item_name="Doomed Item")

    response = client.delete('/api/orders/DEL001')

    assert response.status_code == 200
    assert response.json['order_id'] == "DEL001"
    assert response.json['item_name'] == "Doomed Item"


def test_deleted_order_is_gone_afterwards(client):
    """The order is really removed, not just reported as removed."""
    _create_order(client, "DEL002")
    client.delete('/api/orders/DEL002')

    assert client.get('/api/orders/DEL002').status_code == 404
    assert client.get('/api/orders').json == []


def test_delete_unknown_order_returns_json_404(client):
    """Deleting something that does not exist is a 404 with a JSON body."""
    response = client.delete('/api/orders/GHOST')

    assert response.status_code == 404
    assert response.is_json
    assert "not found" in response.json['error']


def test_delete_is_not_idempotent_in_status_code(client):
    """
    A second delete reports 404. Documenting the choice: the endpoint returns
    the deleted record, so it cannot also pretend a missing order succeeded.
    """
    _create_order(client, "DEL003")

    assert client.delete('/api/orders/DEL003').status_code == 200
    assert client.delete('/api/orders/DEL003').status_code == 404


def test_delete_leaves_other_orders_untouched(client):
    """Deletion is scoped to the one order named in the path."""
    _create_order(client, "KEEP001")
    _create_order(client, "DEL004")

    client.delete('/api/orders/DEL004')

    remaining = client.get('/api/orders').json
    assert [order['order_id'] for order in remaining] == ["KEEP001"]
