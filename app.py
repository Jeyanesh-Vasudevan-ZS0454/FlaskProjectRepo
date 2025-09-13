
from flask import Flask, jsonify, request
import sqlite3
import traceback
import datetime
import os

app = Flask(__name__)
DB_FILE = "errors_sqlite.db"

# ---------- DB Helpers ----------
def get_sqlite_conn(read_only=False):
    if read_only:
        # Use URI mode for read-only
        return sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
    return sqlite3.connect(DB_FILE)

def create_tables():
    con = get_sqlite_conn()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS error_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exception_type TEXT,
        message TEXT,
        stacktrace TEXT,
        occurred_at TIMESTAMP,
        endpoint TEXT
    )
    """)
    con.commit()
    con.close()

class User:
    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name

def get_user_by_id(user_id):
    """Simulates fetching a user from a database.
    Returns a User object if found, otherwise None."""
    if user_id == 1:
        return User("Alice")
    else:
        return None

# Case 1: User found, no error

# ---------- Sample Error Routes ----------
@app.route("/null_reference")
def null_reference():

    user_id = request.args.get('user_id')
    obj = get_user_by_id(user_id)
    if obj is None:
        return jsonify({"error": "TypeError", "message": "Object is None", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500
    return obj.get_name()

@app.route("/index_out_of_range")
def index_out_of_range():
    arr = [1,2,3]
    idx = request.args.get("num1", default=1, type=int)
    if idx < 0 or idx >= len(arr):
        return jsonify({"error": "IndexError", "message": "Index out of range", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500
    return str(arr[idx])  

@app.route("/invalid_operation")
def invalid_operation():
    num1 = request.args.get("num1", default=5)
    num2 = request.args.get("num2", default=3)
    if num2 == '0':
        return jsonify({"error": "ZeroDivisionError", "message": "Cannot divide by zero", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500
    num2 = float(num2)
    if num2 == 0:
        return jsonify({"error": "ZeroDivisionError", "message": "Cannot divide by zero", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500
    x = float(num1) / num2  
    return str(x)

@app.route("/type_error")
def type_error():
    num1 = request.args.get("num1", default=5)
    num2 = request.args.get("num2", default=3)
    try:
        result = float(num1) + float(num2)
        return str(result)
    except (ValueError, TypeError):
        return jsonify({"error": "TypeError", "message": "Unsupported operand type(s) for +", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

@app.route("/value_error")
def value_error():
    try:
        num1 = request.args.get("num1", default=5)
        return int(num1)
    except ValueError as e:
        return jsonify({"error": type(e).__name__, "message": str(e), "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

# ---------- Global Error Handler ----------
@app.errorhandler(Exception)
def handle_exception(e):
    exc_type = type(e).__name__
    message = str(e)
    stacktrace = traceback.format_exc()
    occurred_at = datetime.datetime.utcnow()
    endpoint = request.path

    con = get_sqlite_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO error_logs (exception_type, message, stacktrace, occurred_at, endpoint)
        VALUES (?, ?, ?, ?, ?)
    """, (exc_type, message, stacktrace, occurred_at, endpoint))
    con.commit()
    con.close()

    return jsonify({
        "error": exc_type,
        "message": message,
        "endpoint": endpoint,
        "occurred_at": occurred_at.isoformat()
    }), 500

# ---------- Endpoint to view logs ----------
@app.route("/logs")
def get_logs():
    con = get_sqlite_conn(read_only=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM error_logs ORDER BY occurred_at DESC")
    rows = cur.fetchall()
    con.close()
    return jsonify([dict(row) for row in rows])

# test case 
@app.route("/test_null")
def test_null():
    return jsonify({"error": "TypeError", "message": "Object is None", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

@app.route("/test_index")
def test_index():
    return jsonify({"error": "IndexError", "message": "Index out of range", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

@app.route("/test_zero")
def test_zero():
    return jsonify({"error": "ZeroDivisionError", "message": "Cannot divide by zero", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

@app.route("/test_type")
def test_type():
    return jsonify({"error": "TypeError", "message": "Unsupported operand type(s) for +", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

@app.route("/test_value")
def test_value():
    return jsonify({"error": "ValueError", "message": "Invalid value", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
