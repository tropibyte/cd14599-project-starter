import pytest
from unittest.mock import Mock
from ..order_tracker import OrderTracker

# --- Fixtures for Unit Tests ---


@pytest.fixture
def mock_storage():
    """
    Provides a mock storage object for tests.
    This mock will be configured to simulate various storage behaviors.
    """
    mock = Mock()
    # By default, mock get_order to return None (no order found)
    mock.get_order.return_value = None
    # By default, mock get_all_orders to return an empty dict
    mock.get_all_orders.return_value = {}
    return mock


@pytest.fixture
def order_tracker(mock_storage):
    """
    Provides an OrderTracker instance initialized with the mock_storage.
    """
    return OrderTracker(mock_storage)

#
# --- TODO: add test functions below this line ---
#


def test_add_order_successfully(order_tracker, mock_storage):
    """Tests adding a new order with default 'pending' status."""
    order_tracker.add_order("ORD001", "Laptop", 1, "CUST001")

    # We expect save_order to be called once
    mock_storage.save_order.assert_called_once()


def test_add_order_raises_error_if_exists(order_tracker, mock_storage):
    """Tests that adding an order with a duplicate ID raises a ValueError."""
    # Simulate that the storage finds an existing order
    mock_storage.get_order.return_value = {"order_id": "ORD_EXISTING"}

    with pytest.raises(ValueError, match="Order with ID 'ORD_EXISTING' already exists."):
        order_tracker.add_order("ORD_EXISTING", "New Item", 1, "CUST001")


def test_add_order_stores_details_and_defaults_to_pending(order_tracker, mock_storage):
    """Tests that the saved payload carries every field and defaults to 'pending'."""
    order_tracker.add_order("ORD001", "Laptop", 1, "CUST001")

    mock_storage.save_order.assert_called_once_with(
        "ORD001",
        {
            "order_id": "ORD001",
            "item_name": "Laptop",
            "quantity": 1,
            "customer_id": "CUST001",
            "status": "pending",
        },
    )


def test_add_order_accepts_explicit_status(order_tracker, mock_storage):
    """Tests that an explicit initial status overrides the 'pending' default."""
    order_tracker.add_order("ORD002", "Monitor", 3, "CUST002", status="processing")

    saved_order = mock_storage.save_order.call_args[0][1]
    assert saved_order["status"] == "processing"


def test_add_order_returns_the_created_order(order_tracker, mock_storage):
    """Tests that the created order is returned so callers can echo it back."""
    created = order_tracker.add_order("ORD003", "Keyboard", 2, "CUST003")

    assert created == {
        "order_id": "ORD003",
        "item_name": "Keyboard",
        "quantity": 2,
        "customer_id": "CUST003",
        "status": "pending",
    }


@pytest.mark.parametrize("bad_quantity", [0, -1, 2.5, "3", True])
def test_add_order_rejects_invalid_quantity(order_tracker, mock_storage, bad_quantity):
    """Tests that only positive integers are accepted as a quantity."""
    with pytest.raises(ValueError, match="Quantity must be a positive integer."):
        order_tracker.add_order("ORD004", "Mouse", bad_quantity, "CUST004")

    mock_storage.save_order.assert_not_called()


def test_add_order_rejects_missing_item_name(order_tracker, mock_storage):
    """Tests that a blank required field is rejected before anything is saved."""
    with pytest.raises(ValueError, match="Item name must be a non-empty string."):
        order_tracker.add_order("ORD005", "   ", 1, "CUST005")

    mock_storage.save_order.assert_not_called()


def test_add_order_rejects_invalid_initial_status(order_tracker, mock_storage):
    """Tests that an unknown initial status is rejected."""
    with pytest.raises(ValueError, match="Invalid status 'teleported'"):
        order_tracker.add_order("ORD006", "Webcam", 1, "CUST006", status="teleported")

    mock_storage.save_order.assert_not_called()


# --- get_order_by_id --------------------------------------------------------

def test_get_order_by_id_returns_existing_order(order_tracker, mock_storage):
    """Tests fetching an order that exists in storage."""
    stored_order = {
        "order_id": "ORD001",
        "item_name": "Laptop",
        "quantity": 1,
        "customer_id": "CUST001",
        "status": "pending",
    }
    mock_storage.get_order.return_value = stored_order

    assert order_tracker.get_order_by_id("ORD001") == stored_order
    mock_storage.get_order.assert_called_once_with("ORD001")


def test_get_order_by_id_returns_none_when_missing(order_tracker, mock_storage):
    """Tests that a non-existent order ID yields None rather than an error."""
    mock_storage.get_order.return_value = None

    assert order_tracker.get_order_by_id("NOPE") is None


def test_get_order_by_id_raises_on_empty_id(order_tracker, mock_storage):
    """Tests that a blank order ID is rejected without a storage lookup."""
    with pytest.raises(ValueError, match="Order ID must be a non-empty string."):
        order_tracker.get_order_by_id("")

    mock_storage.get_order.assert_not_called()


# --- update_order_status ----------------------------------------------------

def test_update_order_status_changes_status(order_tracker, mock_storage):
    """Tests moving an order from 'pending' to 'shipped'."""
    mock_storage.get_order.return_value = {
        "order_id": "ORD001",
        "item_name": "Laptop",
        "quantity": 1,
        "customer_id": "CUST001",
        "status": "pending",
    }

    updated = order_tracker.update_order_status("ORD001", "shipped")

    assert updated["status"] == "shipped"
    mock_storage.save_order.assert_called_once_with("ORD001", updated)


def test_update_order_status_does_not_mutate_stored_dict(order_tracker, mock_storage):
    """Tests that the dict handed back by storage is copied, not edited in place."""
    stored_order = {
        "order_id": "ORD001",
        "item_name": "Laptop",
        "quantity": 1,
        "customer_id": "CUST001",
        "status": "pending",
    }
    mock_storage.get_order.return_value = stored_order

    order_tracker.update_order_status("ORD001", "delivered")

    assert stored_order["status"] == "pending"


def test_update_order_status_raises_on_invalid_status(order_tracker, mock_storage):
    """Tests that an invalid status fails fast, before storage is ever read."""
    with pytest.raises(ValueError, match="Invalid status 'exploded'"):
        order_tracker.update_order_status("ORD001", "exploded")

    mock_storage.get_order.assert_not_called()
    mock_storage.save_order.assert_not_called()


def test_update_order_status_raises_when_order_missing(order_tracker, mock_storage):
    """Tests that updating an unknown order raises a ValueError."""
    mock_storage.get_order.return_value = None

    with pytest.raises(ValueError, match="Order with ID 'GHOST' not found."):
        order_tracker.update_order_status("GHOST", "shipped")

    mock_storage.save_order.assert_not_called()


def test_update_order_status_raises_on_empty_id(order_tracker, mock_storage):
    """Tests that a blank order ID is rejected."""
    with pytest.raises(ValueError, match="Order ID must be a non-empty string."):
        order_tracker.update_order_status("", "shipped")

    mock_storage.save_order.assert_not_called()


# --- list_all_orders --------------------------------------------------------

def test_list_all_orders_returns_empty_list_when_no_orders(order_tracker, mock_storage):
    """Tests that empty storage produces an empty list, not None."""
    mock_storage.get_all_orders.return_value = {}

    assert order_tracker.list_all_orders() == []


def test_list_all_orders_returns_every_order(order_tracker, mock_storage):
    """Tests that all stored orders are returned as a list of dicts."""
    first = {"order_id": "A1", "item_name": "A", "quantity": 1,
             "customer_id": "C1", "status": "pending"}
    second = {"order_id": "B2", "item_name": "B", "quantity": 2,
              "customer_id": "C2", "status": "shipped"}
    mock_storage.get_all_orders.return_value = {"A1": first, "B2": second}

    result = order_tracker.list_all_orders()

    assert len(result) == 2
    # Ordering is not part of the contract, so compare as a set of IDs.
    assert {order["order_id"] for order in result} == {"A1", "B2"}


# --- list_orders_by_status --------------------------------------------------

def test_list_orders_by_status_returns_only_matches(order_tracker, mock_storage):
    """Tests filtering down to the orders in a single status."""
    mock_storage.get_all_orders.return_value = {
        "A1": {"order_id": "A1", "item_name": "A", "quantity": 1,
               "customer_id": "C1", "status": "pending"},
        "B2": {"order_id": "B2", "item_name": "B", "quantity": 2,
               "customer_id": "C2", "status": "shipped"},
        "C3": {"order_id": "C3", "item_name": "C", "quantity": 3,
               "customer_id": "C3", "status": "shipped"},
    }

    shipped = order_tracker.list_orders_by_status("shipped")

    assert {order["order_id"] for order in shipped} == {"B2", "C3"}


def test_list_orders_by_status_returns_empty_when_no_matches(order_tracker, mock_storage):
    """Tests that a valid status with no matching orders returns an empty list."""
    mock_storage.get_all_orders.return_value = {
        "A1": {"order_id": "A1", "item_name": "A", "quantity": 1,
               "customer_id": "C1", "status": "pending"},
    }

    assert order_tracker.list_orders_by_status("delivered") == []


def test_list_orders_by_status_returns_empty_for_empty_storage(order_tracker, mock_storage):
    """Tests filtering against empty storage."""
    mock_storage.get_all_orders.return_value = {}

    assert order_tracker.list_orders_by_status("pending") == []


def test_list_orders_by_status_raises_on_empty_status(order_tracker, mock_storage):
    """Tests that a blank status is rejected."""
    with pytest.raises(ValueError, match="Status must be a non-empty string."):
        order_tracker.list_orders_by_status("")

    mock_storage.get_all_orders.assert_not_called()


def test_list_orders_by_status_raises_on_invalid_status(order_tracker, mock_storage):
    """Tests that an unknown status is rejected rather than silently returning []."""
    with pytest.raises(ValueError, match="Invalid status 'frozen'"):
        order_tracker.list_orders_by_status("frozen")

    mock_storage.get_all_orders.assert_not_called()
