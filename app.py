
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

# ---------- Sample Error Routes ----------
@app.route("/null_reference")
def null_reference():
    obj = None
    return obj.some_attr  # AttributeError

@app.route("/index_out_of_range")
def index_out_of_range():
    arr = [1,2,3]
    return str(arr[5])  # IndexError

@app.route("/invalid_operation")
def invalid_operation():
    x = 10 / 0  # ZeroDivisionError
    return str(x)

@app.route("/type_error")
def type_error():
    num1 = 5
    num2 = "hello"
    try:
        if isinstance(num1, int) and isinstance(num2, int):
            return str(num1 + num2)
        elif isinstance(num1, str) and isinstance(num2, str):
            return num1 + num2
        else:
            try:
                num1 = int(num1)
                num2 = int(num2)
                return str(num1 + num2)
            except ValueError:
                return jsonify({"error": "ValueError", "message": "Cannot convert num1 or num2 to integer", "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500
    except TypeError as e:
        return jsonify({"error": type(e).__name__, "message": str(e), "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500
    except Exception as e:
        return jsonify({"error": type(e).__name__, "message": str(e), "endpoint": request.path, "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

@app.route("/value_error")
def value_error():
    return int("not_a_number")  # ValueError

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

@app.route("/test")
def test():
    return "Test success"

@app.route("/test_error")
def test_error():
    return jsonify({"error": "TypeError", "message": "Unsupported operand type(s) for +: 'int' and 'str'", "endpoint": "/test_error", "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

@app.route("/static_error")
def static_error():
    return jsonify({"error": "TypeError", "message": "Unsupported operand type(s) for +: 'int' and 'str'", "endpoint": "/static_error", "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

@app.route("/static_type_error", methods=['GET'])
def static_type_error():
    return jsonify({"error": "TypeError", "message": "Unsupported operand type(s) for +: 'int' and 'str'", "endpoint": "/static_type_error", "occurred_at": datetime.datetime.utcnow().isoformat()}), 500

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
