# This module contains the OrderTracker class, which encapsulates the core
# business logic for managing orders.
#
# It is deliberately framework-agnostic: nothing here imports Flask. The class
# talks to an injected storage object, so the same logic can be exercised
# against a mock in unit tests and against InMemoryStorage in the running app.


class OrderTracker:
    """
    Manages customer orders, providing functionalities to add, update,
    and retrieve order information.
    """

    # The complete set of states an order may occupy.
    VALID_STATUSES = ("pending", "processing", "shipped", "delivered", "cancelled")

    def __init__(self, storage):
        required_methods = ['save_order', 'get_order', 'get_all_orders']
        for method in required_methods:
            if not hasattr(storage, method) or not callable(getattr(storage, method)):
                raise TypeError(f"Storage object must implement a callable '{method}' method.")
        self.storage = storage

    # --- Internal validation helpers -------------------------------------

    @staticmethod
    def _validate_non_empty_string(value, field_name: str):
        """Rejects anything that is not a non-blank string."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string.")

    @staticmethod
    def _validate_quantity(quantity):
        """Quantity must be a positive integer (bools are not integers here)."""
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")

    @classmethod
    def _validate_status(cls, status):
        """Status must be one of the known lifecycle states."""
        cls._validate_non_empty_string(status, "Status")
        if status not in cls.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Valid statuses are: "
                f"{', '.join(cls.VALID_STATUSES)}."
            )

    # --- Create -----------------------------------------------------------

    def add_order(self, order_id: str, item_name: str, quantity: int,
                  customer_id: str, status: str = "pending") -> dict:
        """
        Creates a new order and returns it.

        Validates every field up front, then rejects duplicate order IDs so a
        malformed payload never reaches storage.
        """
        self._validate_non_empty_string(order_id, "Order ID")
        self._validate_non_empty_string(item_name, "Item name")
        self._validate_quantity(quantity)
        self._validate_non_empty_string(customer_id, "Customer ID")
        self._validate_status(status)

        if self.storage.get_order(order_id):
            raise ValueError(f"Order with ID '{order_id}' already exists.")

        order = {
            "order_id": order_id,
            "item_name": item_name,
            "quantity": quantity,
            "customer_id": customer_id,
            "status": status,
        }
        self.storage.save_order(order_id, order)
        return order

    # --- Read -------------------------------------------------------------

    def get_order_by_id(self, order_id: str):
        """Returns the order with the given ID, or None if it does not exist."""
        self._validate_non_empty_string(order_id, "Order ID")
        return self.storage.get_order(order_id)

    def list_all_orders(self) -> list:
        """Returns every stored order as a list of dictionaries."""
        return list(self.storage.get_all_orders().values())

    def list_orders_by_status(self, status: str) -> list:
        """Returns only the orders currently in the given status."""
        self._validate_status(status)
        return [
            order for order in self.storage.get_all_orders().values()
            if order.get("status") == status
        ]

    # --- Update -----------------------------------------------------------

    def update_order_status(self, order_id: str, new_status: str) -> dict:
        """
        Moves an existing order to a new status and returns the updated order.

        The status is checked before the storage lookup so an invalid request
        fails fast without touching storage. The stored dict is copied rather
        than mutated in place, which keeps the change explicit.
        """
        self._validate_non_empty_string(order_id, "Order ID")
        self._validate_status(new_status)

        existing_order = self.storage.get_order(order_id)
        if not existing_order:
            raise ValueError(f"Order with ID '{order_id}' not found.")

        updated_order = dict(existing_order)
        updated_order["status"] = new_status
        self.storage.save_order(order_id, updated_order)
        return updated_order
