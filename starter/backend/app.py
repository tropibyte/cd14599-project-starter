# Flask API layer for the Order Tracker.
#
# The routes here stay deliberately thin: they parse the request, hand the work
# to OrderTracker, and translate the result (or the ValueError it raises) into
# JSON plus an HTTP status code. All business rules live in order_tracker.py.

from flask import Flask, request, jsonify, send_from_directory
from backend.order_tracker import OrderTracker
from backend.in_memory_storage import InMemoryStorage

app = Flask(__name__, static_folder='../frontend')
in_memory_storage = InMemoryStorage()
order_tracker = OrderTracker(in_memory_storage)


@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


@app.route('/api/orders', methods=['POST'])
def add_order_api():
    """Creates a new order from the JSON request body."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    try:
        order = order_tracker.add_order(
            order_id=payload.get("order_id"),
            item_name=payload.get("item_name"),
            quantity=payload.get("quantity"),
            customer_id=payload.get("customer_id"),
            status=payload.get("status") or "pending",
        )
    except ValueError as error:
        # A duplicate ID is a conflict; anything else is malformed input.
        status_code = 409 if "already exists" in str(error) else 400
        return jsonify({"error": str(error)}), status_code

    return jsonify(order), 201


@app.route('/api/orders/<string:order_id>', methods=['GET'])
def get_order_api(order_id):
    """Returns a single order by its ID."""
    try:
        order = order_tracker.get_order_by_id(order_id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if order is None:
        return jsonify({"error": f"Order with ID '{order_id}' not found."}), 404

    return jsonify(order), 200


@app.route('/api/orders/<string:order_id>/status', methods=['PUT'])
def update_order_status_api(order_id):
    """Updates the status of an existing order."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    new_status = payload.get("new_status")
    try:
        updated_order = order_tracker.update_order_status(order_id, new_status)
    except ValueError as error:
        # A missing order is a 404; a bad status is a 400.
        status_code = 404 if "not found" in str(error) else 400
        return jsonify({"error": str(error)}), status_code

    return jsonify(updated_order), 200


@app.route('/api/orders', methods=['GET'])
def list_orders_api():
    """Lists every order, or only those matching the ?status= query parameter."""
    status_filter = request.args.get("status")

    try:
        if status_filter is None:
            orders = order_tracker.list_all_orders()
        else:
            orders = order_tracker.list_orders_by_status(status_filter)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(orders), 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
