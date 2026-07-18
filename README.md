# Biopharma Tracker

A desktop app (Python + PySide6/Qt + SQLite) to track patients, their
medicines, dosing schedules, and stock levels.

## Features

- **Patients tab**: search a patient by name, see all their medicines with
  dose amount, frequency, last time taken, next due time, and remaining
  stock. Mark a dose as taken (auto-updates next due time and decrements
  medicine stock).
- **Medicines tab**: search a medicine by name, see its stock quantity and
  every patient currently taking it. Update stock manually (e.g. after a
  delivery) and prescribe the medicine to a patient.
- **Dashboard tab**: list of medicines at or below their low-stock threshold.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

A file `pharma.db` (SQLite) is created automatically next to `main.py` the
first time you run the app — no separate database setup needed.

## Typical workflow

1. Go to **Medicines** tab → add a medicine (name, unit, starting stock,
   low-stock threshold).
2. Go to **Patients** tab → add a patient.
3. Go back to **Medicines** tab → select the medicine → in "Prescribe this
   medicine to a patient", pick the patient, set dose amount and frequency
   (in hours) → click Prescribe. This records the first dose as taken now
   and computes the next due time automatically.
4. Whenever the patient actually takes a dose, select them in the
   **Patients** tab, select the medicine row, click "Mark selected dose as
   taken now" — this updates last/next times and reduces stock by the dose
   amount.
5. Check the **Dashboard** tab any time to see medicines running low.

## Project structure

```
pharma_app/
├── main.py         # GUI (PySide6)
├── database.py      # SQLite schema + all data access functions
├── requirements.txt
└── pharma.db         # created automatically on first run
```

## Extending it later

- Add authentication / multi-user roles.
- Export patient medicine schedules to PDF.
- Add desktop notifications when a dose is due.
- Switch `database.py` to PostgreSQL if you outgrow local SQLite (the
  function signatures wouldn't need to change much).
