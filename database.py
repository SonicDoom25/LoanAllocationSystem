# database.py
import os
import sqlite3
import json
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "loan_data.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(BASE_DIR, exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    # loan_requests table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS loan_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        processes INTEGER,
        resources INTEGER,
        allocation TEXT,
        max TEXT,
        available TEXT,
        applicantName TEXT,
        email TEXT,
        requestedAmount INTEGER,
        approvedAmount INTEGER DEFAULT 0,
        income INTEGER DEFAULT 0,
        months INTEGER DEFAULT 12,
        status TEXT DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # settings table to persist bank reserve and future settings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # ensure the bank_reserve entry exists (default 500000)
    cur.execute("SELECT value FROM settings WHERE key='bank_reserve'")
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("bank_reserve", json.dumps(500000)))
    conn.commit()
    conn.close()


# initialize DB on import
init_db()


# ---------- Reserve helpers ----------
def get_bank_reserve() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key='bank_reserve'")
    row = cur.fetchone()
    conn.close()
    if not row:
        return 0
    try:
        return int(json.loads(row["value"]))
    except Exception:
        try:
            return int(row["value"])
        except:
            return 0


def set_bank_reserve(amount: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", ("bank_reserve", json.dumps(int(amount))))
    conn.commit()
    conn.close()


def adjust_bank_reserve(delta: int):
    """Subtract (delta positive) or add (delta negative) from reserve"""
    current = get_bank_reserve()
    new = int(current - delta)
    if new < 0:
        new = 0
    set_bank_reserve(new)
    return new


def reset_bank_reserve_to_default():
    set_bank_reserve(500000)
    return 500000


# ---------- Loan CRUD ----------
def insert_loan_request_record(processes: int, resources: int, allocation: List[List[int]],
                               maximum: List[List[int]], available: List[int],
                               applicantName: str, email: str,
                               requestedAmount: int, approvedAmount: int,
                               income: int, months: int, status: str = "Pending") -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO loan_requests
        (processes, resources, allocation, max, available, applicantName, email,
         requestedAmount, approvedAmount, income, months, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        processes, resources,
        json.dumps(allocation), json.dumps(maximum), json.dumps(available),
        applicantName, email,
        requestedAmount, approvedAmount, income, months, status
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def insert_loan_request(processes: int, resources: int, allocation: List[List[int]],
                        maximum: List[List[int]], available: List[int],
                        name: str, email: str, loan_amount: int, status: str = "Pending") -> int:
    return insert_loan_request_record(processes, resources, allocation, maximum, available,
                                      name, email, loan_amount, 0, 0, 12, status)


def update_loan_request(id_: int, processes: int, resources: int, allocation: List[List[int]],
                        maximum: List[List[int]], available: List[int],
                        name: str, email: str, requestedAmount: int, status: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
      UPDATE loan_requests
      SET processes=?, resources=?, allocation=?, max=?, available=?, applicantName=?, email=?, requestedAmount=?, status=?
      WHERE id=?
    """, (processes, resources, json.dumps(allocation), json.dumps(maximum), json.dumps(available), name, email, requestedAmount, status, id_))
    conn.commit()
    conn.close()


def update_status_and_amount(id_: int, status: str, approvedAmount: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE loan_requests SET status=?, approvedAmount=? WHERE id=?", (status, approvedAmount, id_))
    conn.commit()
    conn.close()


def get_all_requests() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM loan_requests ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["allocation"] = json.loads(d["allocation"]) if d["allocation"] else []
        except Exception:
            d["allocation"] = []
        try:
            d["max"] = json.loads(d["max"]) if d["max"] else []
        except Exception:
            d["max"] = []
        try:
            d["available"] = json.loads(d["available"]) if d["available"] else []
        except Exception:
            d["available"] = []
        # For compatibility: requestedAmount and approvedAmount fallback
        d["requestedAmount"] = d.get("requestedAmount") or d.get("loanAmount") or 0
        d["approvedAmount"] = d.get("approvedAmount") or 0
        results.append(d)
    return results


def get_request_by_id(id_: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM loan_requests WHERE id=?", (id_,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["allocation"] = json.loads(d["allocation"]) if d["allocation"] else []
    except Exception:
        d["allocation"] = []
    try:
        d["max"] = json.loads(d["max"]) if d["max"] else []
    except Exception:
        d["max"] = []
    try:
        d["available"] = json.loads(d["available"]) if d["available"] else []
    except Exception:
        d["available"] = []
    d["requestedAmount"] = d.get("requestedAmount") or d.get("loanAmount") or 0
    d["approvedAmount"] = d.get("approvedAmount") or 0
    return d


def fetch_all_requests() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM loan_requests ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_request_by_id(id_: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM loan_requests WHERE id=?", (id_,))
    conn.commit()
    conn.close()


def delete_all_requests():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM loan_requests")
    conn.commit()
    conn.close()
    # Reset reserve when deleting all requests
    reset_bank_reserve_to_default()
