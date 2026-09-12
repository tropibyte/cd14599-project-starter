# Flask API layer for the Order Tracker.
#
# The routes here stay deliberately thin: they parse the request, hand the work
# to OrderTracker, and translate the result (or the ValueError it raises) into
# JSON plus an HTTP status code. All business rules live in order_tracker.py.

import os

from flask import Flask, request, jsonify, send_from_directory
from backend.order_tracker import OrderTracker
from backend.in_memory_storage import InMemoryStorage

app = Flask(__name__, static_folder='../frontend')
in_memory_storage = InMemoryStorage()
order_tracker = OrderTracker(in_memory_storage)

# Sentinel so an absent "status" key can be told apart from one explicitly set
# to an empty or null value. The former defaults; the latter is a bad request.
_STATUS_OMITTED = object()


# --- Frontend ---------------------------------------------------------------

@app.route('/')
@app.route('/index')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


# --- Error handling ---------------------------------------------------------
#
# API clients should always get JSON back. Browser requests for the frontend
# keep Flask's default HTML pages.

@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Resource not found."}), 404
    return error.get_response()


@app.errorhandler(405)
def handle_method_not_allowed(error):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Method not allowed for this resource."}), 405
    return error.get_response()


# --- Orders API -------------------------------------------------------------

@app.route('/api/orders', methods=['POST'])
def add_order_api():
    """Creates a new order from the JSON request body."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    # An omitted status defaults to 'pending'; anything supplied is validated.
    status = payload.get("status", _STATUS_OMITTED)
    if status is _STATUS_OMITTED:
        status = "pending"

    try:
        order = order_tracker.add_order(
            order_id=payload.get("order_id"),
            item_name=payload.get("item_name"),
            quantity=payload.get("quantity"),
            customer_id=payload.get("customer_id"),
            status=status,
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


@app.route('/api/orders/<string:order_id>', methods=['PUT'])
def update_order_api(order_id):
    """
    Alias so a PUT on the order resource itself also updates its status.

    The project brief names this endpoint both ways: the rubric heading says
    PUT /api/orders/<order_id> while the contract table, the provided tests and
    the frontend all use the /status suffix. Supporting both costs one line.
    """
    return update_order_status_api(order_id)


@app.route('/api/orders', methods=['GET'])
def list_orders_api():
    """
    Lists orders, optionally narrowed by ?status= and/or ?customer_id=.

    With no query parameters this returns everything. The two filters combine,
    so ?customer_id=C123&status=pending is that customer's pending orders.
    """
    status_filter = request.args.get("status")
    customer_filter = request.args.get("customer_id")

    try:
        orders = order_tracker.list_orders(
            status=status_filter,
            customer_id=customer_filter,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(orders), 200


@app.route('/api/orders/<string:order_id>', methods=['DELETE'])
def delete_order_api(order_id):
    """Removes an order and returns the record that was deleted."""
    try:
        deleted_order = order_tracker.delete_order(order_id)
    except ValueError as error:
        status_code = 404 if "not found" in str(error) else 400
        return jsonify({"error": str(error)}), status_code

    return jsonify(deleted_order), 200


if __name__ == '__main__':
    # Binding 0.0.0.0 is what makes the Workspace "Flask App" link work.
    # PORT and FLASK_DEBUG are read from the environment so the same entry
    # point serves local development (debug on) and the container (debug off,
    # since the Werkzeug debugger must never be reachable from outside).
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "1") != "0",
    )
