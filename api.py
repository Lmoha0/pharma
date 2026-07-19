"""
api.py
The bridge between the HTML/CSS/JS frontend and the Python/SQLite backend.
Every method here is callable from JavaScript as window.pywebview.api.<method>(...)
and must return JSON-serializable data (plain dicts/lists), never sqlite3.Row objects.
"""

from datetime import datetime
import database as db


def row_to_dict(row):
    return {k: row[k] for k in row.keys()} if row is not None else None


def rows_to_list(rows):
    return [row_to_dict(r) for r in rows]


class Api:
    # ---------------- Patients ----------------

    def get_patients(self, query=""):
        rows = db.search_patients(query) if query else db.get_all_patients()
        return rows_to_list(rows)

    def add_patient(self, name, phone="", dob="", notes=""):
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "Name is required."}
        db.add_patient(name, phone.strip(), dob, notes.strip())
        return {"ok": True}

    def delete_patient(self, patient_id):
        db.delete_patient(patient_id)
        return {"ok": True}

    def get_patient_prescriptions(self, patient_id):
        return rows_to_list(db.get_prescriptions_for_patient(patient_id))

    # ---------------- Medicines ----------------

    def get_medicines(self, query=""):
        rows = db.search_medicines(query) if query else db.get_all_medicines()
        return rows_to_list(rows)

    def add_medicine(self, name, unit="tablet", stock_quantity=0, low_stock_threshold=10):
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "Name is required."}
        try:
            db.add_medicine(name, unit.strip() or "tablet", float(stock_quantity), float(low_stock_threshold))
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    def update_stock(self, medicine_id, new_quantity):
        db.update_stock(medicine_id, float(new_quantity))
        return {"ok": True}

    def delete_medicine(self, medicine_id):
        db.delete_medicine(medicine_id)
        return {"ok": True}

    def get_medicine_patients(self, medicine_id):
        return rows_to_list(db.get_patients_for_medicine(medicine_id))

    # ---------------- Prescriptions ----------------

    def add_prescription(self, patient_id, medicine_id, dose_amount, frequency_hours):
        now_iso = datetime.now().isoformat(timespec="seconds")
        db.add_prescription(patient_id, medicine_id, float(dose_amount), float(frequency_hours), last_taken=now_iso)
        return {"ok": True}

    def record_dose_taken(self, prescription_id):
        db.record_dose_taken(prescription_id)
        return {"ok": True}

    def delete_prescription(self, prescription_id):
        db.delete_prescription(prescription_id)
        return {"ok": True}

    # ---------------- Dashboard ----------------

    def get_dashboard(self):
        low_stock = rows_to_list(db.get_low_stock_medicines())
        return {
            "patient_count": len(db.get_all_patients()),
            "medicine_count": len(db.get_all_medicines()),
            "low_stock": low_stock,
        }
