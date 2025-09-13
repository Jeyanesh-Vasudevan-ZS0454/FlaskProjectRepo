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

@app.route("/index_out_of_range", methods=["POST"])
def index_out_of_range():
    arr = [1, 2, 3]
    idx = request.json.get("num1", 1)   # default = 1
    return str(arr[idx])  # IndexError if out of range


@app.route("/invalid_operation", methods=["POST"])
def invalid_operation():
    num1 = request.json.get("num1", 5)
    num2 = request.json.get("num2", 3)
    x = num1 / num2  # ZeroDivisionError if num2 = 0
    return str(x)


@app.route("/type_error", methods=["POST"])
def type_error():
    num1 = request.json.get("num1", 5)
    num2 = request.json.get("num2", 3)
    return str(num1 + num2)   # TypeError if types mismatch


@app.route("/value_error", methods=["POST"])
def value_error():
    try:
        num1 = request.json.get("num1", 5)
        if not isinstance(num1, (int, str)) or (isinstance(num1, str) and not num1.isdigit()):
            return jsonify({
                "error": "ValueError",
                "message": "Input must be an integer",
                "endpoint": request.path,
                "occurred_at": datetime.datetime.utcnow().isoformat()
            }), 400
        return str(int(num1))
    except ValueError as e:
        return jsonify({
            "error": type(e).__name__,
            "message": str(e),
            "endpoint": request.path,
            "occurred_at": datetime.datetime.utcnow().isoformat()
        }), 500

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
