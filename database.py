"""
database.py
SQLite data layer for the Biopharma Tracker app.
Handles schema creation and all CRUD / query operations.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "pharma.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            dob TEXT,
            notes TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            unit TEXT DEFAULT 'tablet',
            stock_quantity REAL NOT NULL DEFAULT 0,
            low_stock_threshold REAL NOT NULL DEFAULT 10
        )
    """)

    # A prescription links a patient to a medicine with a dosing schedule.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            medicine_id INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
            dose_amount REAL NOT NULL DEFAULT 1,
            frequency_hours REAL NOT NULL DEFAULT 24,
            last_taken TEXT,
            next_due TEXT,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()


# ---------------- Patients ----------------

def add_patient(name, phone="", dob="", notes=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO patients (name, phone, dob, notes) VALUES (?, ?, ?, ?)",
        (name, phone, dob, notes),
    )
    conn.commit()
    conn.close()


def search_patients(query):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM patients WHERE name LIKE ? ORDER BY name",
        (f"%{query}%",),
    ).fetchall()
    conn.close()
    return rows


def get_all_patients():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM patients ORDER BY name").fetchall()
    conn.close()
    return rows


def delete_patient(patient_id):
    conn = get_connection()
    conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    conn.commit()
    conn.close()


# ---------------- Medicines ----------------

def add_medicine(name, unit="tablet", stock_quantity=0, low_stock_threshold=10):
    conn = get_connection()
    conn.execute(
        "INSERT INTO medicines (name, unit, stock_quantity, low_stock_threshold) VALUES (?, ?, ?, ?)",
        (name, unit, stock_quantity, low_stock_threshold),
    )
    conn.commit()
    conn.close()


def search_medicines(query):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM medicines WHERE name LIKE ? ORDER BY name",
        (f"%{query}%",),
    ).fetchall()
    conn.close()
    return rows


def get_all_medicines():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM medicines ORDER BY name").fetchall()
    conn.close()
    return rows


def update_stock(medicine_id, new_quantity):
    conn = get_connection()
    conn.execute(
        "UPDATE medicines SET stock_quantity = ? WHERE id = ?",
        (new_quantity, medicine_id),
    )
    conn.commit()
    conn.close()


def delete_medicine(medicine_id):
    conn = get_connection()
    conn.execute("DELETE FROM medicines WHERE id = ?", (medicine_id,))
    conn.commit()
    conn.close()


# ---------------- Prescriptions ----------------

def add_prescription(patient_id, medicine_id, dose_amount, frequency_hours,
                      last_taken=None):
    """Create a prescription. If last_taken is given (ISO string), next_due
    is computed automatically from frequency_hours."""
    next_due = None
    if last_taken:
        dt = datetime.fromisoformat(last_taken)
        next_due = (dt + timedelta(hours=frequency_hours)).isoformat()

    conn = get_connection()
    conn.execute(
        """INSERT INTO prescriptions
           (patient_id, medicine_id, dose_amount, frequency_hours, last_taken, next_due)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (patient_id, medicine_id, dose_amount, frequency_hours, last_taken, next_due),
    )
    conn.commit()
    conn.close()


def record_dose_taken(prescription_id, taken_at=None):
    """Mark a dose as taken now, auto-compute next_due, and decrement stock."""
    taken_at = taken_at or datetime.now().isoformat(timespec="seconds")

    conn = get_connection()
    presc = conn.execute(
        "SELECT * FROM prescriptions WHERE id = ?", (prescription_id,)
    ).fetchone()
    if presc is None:
        conn.close()
        return

    next_due = (
        datetime.fromisoformat(taken_at) + timedelta(hours=presc["frequency_hours"])
    ).isoformat(timespec="seconds")

    conn.execute(
        "UPDATE prescriptions SET last_taken = ?, next_due = ? WHERE id = ?",
        (taken_at, next_due, prescription_id),
    )

    # Decrement medicine stock by the dose amount
    conn.execute(
        "UPDATE medicines SET stock_quantity = stock_quantity - ? WHERE id = ?",
        (presc["dose_amount"], presc["medicine_id"]),
    )

    conn.commit()
    conn.close()


def get_prescriptions_for_patient(patient_id):
    """Return prescriptions joined with medicine info for a given patient."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.id as prescription_id, p.dose_amount, p.frequency_hours,
                  p.last_taken, p.next_due, p.active,
                  m.id as medicine_id, m.name as medicine_name, m.unit,
                  m.stock_quantity, m.low_stock_threshold
           FROM prescriptions p
           JOIN medicines m ON m.id = p.medicine_id
           WHERE p.patient_id = ?
           ORDER BY m.name""",
        (patient_id,),
    ).fetchall()
    conn.close()
    return rows


def get_patients_for_medicine(medicine_id):
    """Return prescriptions joined with patient info for a given medicine."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.id as prescription_id, p.dose_amount, p.frequency_hours,
                  p.last_taken, p.next_due, p.active,
                  pt.id as patient_id, pt.name as patient_name, pt.phone
           FROM prescriptions p
           JOIN patients pt ON pt.id = p.patient_id
           WHERE p.medicine_id = ?
           ORDER BY pt.name""",
        (medicine_id,),
    ).fetchall()
    conn.close()
    return rows


def delete_prescription(prescription_id):
    conn = get_connection()
    conn.execute("DELETE FROM prescriptions WHERE id = ?", (prescription_id,))
    conn.commit()
    conn.close()


def get_low_stock_medicines():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM medicines WHERE stock_quantity <= low_stock_threshold ORDER BY name"
    ).fetchall()
    conn.close()
    return rows
