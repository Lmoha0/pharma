# Biopharma Tracker (HTML/CSS UI version)

A desktop app: Python + SQLite for all the logic and data, a native window
(via `pywebview`) showing a plain HTML/CSS/JS interface. No browser, no
internet connection needed — it's a real desktop window, just with a much
more flexible UI layer than typical Python GUI toolkits.

## Why this version instead of the PySide6 one

Qt's stylesheet system (QSS) is limited and quirky — form labels, spacing,
and effects are hard to control precisely. HTML/CSS gives full, predictable
control over layout, colors, gradients, shadows, and animations, while
`pywebview` still wraps it in a genuine native window (no browser chrome,
no address bar, no internet required).

## Setup

```bash
pip install -r requirements.txt
python main.py
```

On Windows 10/11, pywebview uses the built-in Edge WebView2 runtime, which
is already installed on almost all modern Windows machines — nothing extra
to install. On Linux it uses GTK/QtWebKit (`sudo apt install python3-gi
gir1.2-webkit2-4.0` if you hit an error about a missing renderer). On macOS
it uses the built-in WebKit — nothing extra needed.

A file `pharma.db` (SQLite) is created automatically next to `main.py` the
first time you run the app.

## Project structure

```
pharma_web/
├── main.py           # launches the pywebview window
├── api.py            # Python functions exposed to the JS frontend
├── database.py        # SQLite schema + all data access functions
├── requirements.txt
└── web/
    ├── index.html      # page structure
    ├── style.css       # all visual styling
    └── app.js          # frontend logic, calls api.py methods
```

## How it works

- `main.py` opens a native window pointing at `web/index.html` and exposes
  a Python `Api` object as `window.pywebview.api` inside the page's
  JavaScript.
- `app.js` calls `api().get_patients()`, `api().add_medicine(...)`, etc.
  Every call goes straight to Python — `api.py` — which reads/writes the
  local SQLite database via `database.py`.
- All styling lives in `style.css`, so you (or I) can change colors, spacing,
  fonts, or add animations without touching any Python code.

## Typical workflow

1. **Medicines** tab → add a medicine (name, unit, starting stock, low-stock
   threshold).
2. **Patients** tab → add a patient.
3. **Medicines** tab → select the medicine → in "Prescribe this medicine to
   a patient," pick the patient, set dose and frequency (hours) → Prescribe.
   Records the first dose as taken now and computes the next due time.
4. When a patient actually takes a dose: **Patients** tab → select them →
   select the medicine row → "Mark selected dose as taken now." Updates the
   schedule and deducts stock automatically.
5. **Dashboard** tab any time to see medicines running low.

## Packaging as a single .exe (optional, for later)

Once you're happy with it, `pyinstaller` can bundle this into a single
Windows executable so you don't need Python installed to run it:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --add-data "web;web" main.py
```
