
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
    return obj.some_attr  # AttributeError

@app.route("/index_out_of_range")
def index_out_of_range():
    arr = [1,2,3]
    idx = request.args.get("num1", default=1)
    return str(arr[idx])  # IndexError

@app.route("/invalid_operation")
def invalid_operation():
    num1 = request.args.get("num1", default=5)
    num2 = request.args.get("num2", default=3)
    x = num1 / num2  # ZeroDivisionError
    return str(x)

@app.route("/type_error")
def type_error():
    num1 = request.args.get("num1", default=5, type=int)
    num2 = request.args.get("num2", default=3, type=int)

    if num1 is None or num2 is None:
        return "Invalid input: num1 and num2 must be integers"
    return str(num1 + num2)@app.route("/value_error")
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


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
 
