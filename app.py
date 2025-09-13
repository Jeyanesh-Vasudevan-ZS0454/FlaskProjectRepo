from flask import Flask, jsonify, request
import sqlite3
import traceback
import datetime
import os

app = Flask(__name__)
DB_FILE = "errors_sqlite.db"


def hit_api(inserted_id):
    try:
        import requests
        import json
        url = "http://localhost:8080/log/v1/submit"
        payload = json.dumps({
            "project_id": 1,
            "error_id": inserted_id
        })
        headers = {'Content-Type': 'application/json'}
        response = requests.request("POST", url, headers=headers, data=payload)
    except Exception as e:
        print(e)
# ---------- Global Error Handler ----------
from werkzeug.exceptions import HTTPException
import threading

@app.errorhandler(Exception)
def handle_exception(e):
    # Skip HTTP exceptions (404, 405, etc.)
    if isinstance(e, HTTPException):
        return e

    # This block handles only real runtime errors (API errors)
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
    inserted_id = cur.lastrowid
    con.commit()
    con.close()

    print("Inserted row ID:", inserted_id)
    threading.Thread(target=hit_api, args=(inserted_id,), daemon=True).start()
    # 🔥 Only call external API for API/runtime errors
    # hit_api(inserted_id)

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
    num1 = request.json.get("num1")
    num2 = request.json.get("num2")
    x = num1 / num2  # ZeroDivisionError if num2 = 0
    return str(x)


@app.route("/type_error", methods=["POST"])
def type_error():
    num1 = request.json.get("num1", 5)
    num2 = request.json.get("num2", 3)
    return str(num1 + num2)   # TypeError if types mismatch


@app.route("/value_error", methods=["POST"])
def value_error():
    num1 = request.json.get("num1", 5)
    return str(int(num1))  # ValueError if not convertible




if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
