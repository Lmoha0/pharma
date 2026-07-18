"""
main.py
Biopharma Tracker - a desktop app to track patients, their medicines,
dosing schedules, and stock levels.

Run with:  python main.py
"""

import sys
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QFormLayout, QDoubleSpinBox, QSpinBox, QMessageBox, QGroupBox,
    QHeaderView, QComboBox, QDateEdit, QTextEdit, QSplitter
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont

import database as db


# ---------------------------------------------------------------
# Styling — clean clinical look (white / blue), similar to common
# pharmacy management software.
# ---------------------------------------------------------------
STYLE_SHEET = """
QMainWindow { background-color: #f4f7fa; }
QTabWidget::pane { border: 1px solid #cfd8e3; background: white; }
QTabBar::tab {
    background: #e8edf3; padding: 10px 20px; margin-right: 2px;
    font-weight: 600; color: #35516e;
}
QTabBar::tab:selected { background: #2f6fa3; color: white; }
QGroupBox {
    font-weight: 600; border: 1px solid #cfd8e3; border-radius: 6px;
    margin-top: 10px; padding-top: 14px; background: white;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton {
    background-color: #2f6fa3; color: white; border: none;
    padding: 8px 16px; border-radius: 4px; font-weight: 600;
}
QPushButton:hover { background-color: #255a85; }
QPushButton#danger { background-color: #c0392b; }
QPushButton#danger:hover { background-color: #992d22; }
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QDateEdit, QTextEdit {
    border: 1px solid #cfd8e3; border-radius: 4px; padding: 6px; background: white;
}
QTableWidget {
    border: 1px solid #cfd8e3; gridline-color: #e3e8ee; background: white;
}
QHeaderView::section {
    background-color: #eef2f7; padding: 6px; border: none; font-weight: 600;
}
"""

LOW_STOCK_COLOR = QColor("#fdecea")
OK_COLOR = QColor("#ffffff")


def fmt_dt(iso_str):
    if not iso_str:
        return "—"
    try:
        return datetime.fromisoformat(iso_str).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso_str


# ---------------------------------------------------------------
# Patients Tab
# ---------------------------------------------------------------
class PatientsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # --- Search ---
        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type a patient name to search...")
        self.search_box.textChanged.connect(self.refresh_patient_list)
        search_row.addWidget(QLabel("Search patient:"))
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # --- Patient list ---
        left = QWidget()
        left_l = QVBoxLayout(left)
        self.patient_table = QTableWidget(0, 2)
        self.patient_table.setHorizontalHeaderLabels(["Name", "Phone"])
        self.patient_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.patient_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.patient_table.itemSelectionChanged.connect(self.show_selected_patient_meds)
        left_l.addWidget(self.patient_table)

        add_box = QGroupBox("Add patient")
        form = QFormLayout()
        self.new_name = QLineEdit()
        self.new_phone = QLineEdit()
        self.new_dob = QDateEdit(calendarPopup=True)
        self.new_dob.setDate(QDate.currentDate())
        self.new_notes = QTextEdit()
        self.new_notes.setFixedHeight(50)
        form.addRow("Name:", self.new_name)
        form.addRow("Phone:", self.new_phone)
        form.addRow("Date of birth:", self.new_dob)
        form.addRow("Notes:", self.new_notes)
        add_btn = QPushButton("Add patient")
        add_btn.clicked.connect(self.add_patient)
        form.addRow(add_btn)
        add_box.setLayout(form)
        left_l.addWidget(add_box)

        splitter.addWidget(left)

        # --- Selected patient's medicines ---
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.addWidget(QLabel("<b>Medicines for selected patient</b>"))
        self.meds_table = QTableWidget(0, 6)
        self.meds_table.setHorizontalHeaderLabels(
            ["Medicine", "Dose", "Every (h)", "Last taken", "Next due", "Stock left"]
        )
        self.meds_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        right_l.addWidget(self.meds_table)

        btn_row = QHBoxLayout()
        mark_taken_btn = QPushButton("Mark selected dose as taken now")
        mark_taken_btn.clicked.connect(self.mark_dose_taken)
        remove_presc_btn = QPushButton("Remove this prescription")
        remove_presc_btn.setObjectName("danger")
        remove_presc_btn.clicked.connect(self.remove_prescription)
        btn_row.addWidget(mark_taken_btn)
        btn_row.addWidget(remove_presc_btn)
        right_l.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([350, 550])

        self.refresh_patient_list()

    def refresh_patient_list(self):
        query = self.search_box.text().strip()
        rows = db.search_patients(query) if query else db.get_all_patients()
        self.patient_table.setRowCount(0)
        for row in rows:
            r = self.patient_table.rowCount()
            self.patient_table.insertRow(r)
            name_item = QTableWidgetItem(row["name"])
            name_item.setData(Qt.UserRole, row["id"])
            self.patient_table.setItem(r, 0, name_item)
            self.patient_table.setItem(r, 1, QTableWidgetItem(row["phone"] or ""))
        self.meds_table.setRowCount(0)

    def selected_patient_id(self):
        items = self.patient_table.selectedItems()
        if not items:
            return None
        return self.patient_table.item(items[0].row(), 0).data(Qt.UserRole)

    def show_selected_patient_meds(self):
        pid = self.selected_patient_id()
        self.meds_table.setRowCount(0)
        if pid is None:
            return
        for presc in db.get_prescriptions_for_patient(pid):
            r = self.meds_table.rowCount()
            self.meds_table.insertRow(r)
            name_item = QTableWidgetItem(presc["medicine_name"])
            name_item.setData(Qt.UserRole, presc["prescription_id"])
            self.meds_table.setItem(r, 0, name_item)
            self.meds_table.setItem(r, 1, QTableWidgetItem(f'{presc["dose_amount"]} {presc["unit"]}'))
            self.meds_table.setItem(r, 2, QTableWidgetItem(str(presc["frequency_hours"])))
            self.meds_table.setItem(r, 3, QTableWidgetItem(fmt_dt(presc["last_taken"])))
            self.meds_table.setItem(r, 4, QTableWidgetItem(fmt_dt(presc["next_due"])))
            stock_item = QTableWidgetItem(str(presc["stock_quantity"]))
            if presc["stock_quantity"] <= presc["low_stock_threshold"]:
                for col in range(6):
                    pass
                stock_item.setBackground(LOW_STOCK_COLOR)
            self.meds_table.setItem(r, 5, stock_item)

    def selected_prescription_id(self):
        items = self.meds_table.selectedItems()
        if not items:
            return None
        return self.meds_table.item(items[0].row(), 0).data(Qt.UserRole)

    def mark_dose_taken(self):
        presc_id = self.selected_prescription_id()
        if presc_id is None:
            QMessageBox.warning(self, "No selection", "Select a medicine row first.")
            return
        db.record_dose_taken(presc_id)
        self.show_selected_patient_meds()

    def remove_prescription(self):
        presc_id = self.selected_prescription_id()
        if presc_id is None:
            QMessageBox.warning(self, "No selection", "Select a medicine row first.")
            return
        if QMessageBox.question(self, "Confirm", "Remove this prescription?") == QMessageBox.Yes:
            db.delete_prescription(presc_id)
            self.show_selected_patient_meds()

    def add_patient(self):
        name = self.new_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Patient name is required.")
            return
        db.add_patient(
            name,
            self.new_phone.text().strip(),
            self.new_dob.date().toString("yyyy-MM-dd"),
            self.new_notes.toPlainText().strip(),
        )
        self.new_name.clear()
        self.new_phone.clear()
        self.new_notes.clear()
        self.refresh_patient_list()


# ---------------------------------------------------------------
# Medicines Tab
# ---------------------------------------------------------------
class MedicinesTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type a medicine name to search...")
        self.search_box.textChanged.connect(self.refresh_medicine_list)
        search_row.addWidget(QLabel("Search medicine:"))
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        left = QWidget()
        left_l = QVBoxLayout(left)
        self.med_table = QTableWidget(0, 3)
        self.med_table.setHorizontalHeaderLabels(["Name", "Stock", "Unit"])
        self.med_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.med_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.med_table.itemSelectionChanged.connect(self.show_selected_medicine_patients)
        left_l.addWidget(self.med_table)

        add_box = QGroupBox("Add medicine")
        form = QFormLayout()
        self.new_name = QLineEdit()
        self.new_unit = QLineEdit("tablet")
        self.new_stock = QDoubleSpinBox()
        self.new_stock.setMaximum(1_000_000)
        self.new_threshold = QDoubleSpinBox()
        self.new_threshold.setMaximum(1_000_000)
        self.new_threshold.setValue(10)
        form.addRow("Name:", self.new_name)
        form.addRow("Unit (tablet/ml/...):", self.new_unit)
        form.addRow("Initial stock:", self.new_stock)
        form.addRow("Low stock alert below:", self.new_threshold)
        add_btn = QPushButton("Add medicine")
        add_btn.clicked.connect(self.add_medicine)
        form.addRow(add_btn)
        add_box.setLayout(form)
        left_l.addWidget(add_box)

        stock_box = QGroupBox("Update stock for selected medicine")
        stock_form = QFormLayout()
        self.stock_update = QDoubleSpinBox()
        self.stock_update.setMaximum(1_000_000)
        update_btn = QPushButton("Set new stock quantity")
        update_btn.clicked.connect(self.update_stock)
        stock_form.addRow("New quantity:", self.stock_update)
        stock_form.addRow(update_btn)
        stock_box.setLayout(stock_form)
        left_l.addWidget(stock_box)

        splitter.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.addWidget(QLabel("<b>Patients taking selected medicine</b>"))
        self.patients_table = QTableWidget(0, 5)
        self.patients_table.setHorizontalHeaderLabels(
            ["Patient", "Phone", "Dose", "Last taken", "Next due"]
        )
        self.patients_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        right_l.addWidget(self.patients_table)

        prescribe_box = QGroupBox("Prescribe this medicine to a patient")
        p_form = QFormLayout()
        self.patient_picker = QComboBox()
        self.dose_amount = QDoubleSpinBox()
        self.dose_amount.setValue(1)
        self.dose_amount.setMaximum(1000)
        self.frequency = QDoubleSpinBox()
        self.frequency.setValue(24)
        self.frequency.setMaximum(720)
        self.first_dose_now = QPushButton("Prescribe (first dose = now)")
        self.first_dose_now.clicked.connect(self.add_prescription)
        p_form.addRow("Patient:", self.patient_picker)
        p_form.addRow("Dose amount:", self.dose_amount)
        p_form.addRow("Every (hours):", self.frequency)
        p_form.addRow(self.first_dose_now)
        prescribe_box.setLayout(p_form)
        right_l.addWidget(prescribe_box)

        splitter.addWidget(right)
        splitter.setSizes([400, 500])

        self.refresh_medicine_list()

    def refresh_medicine_list(self):
        query = self.search_box.text().strip()
        rows = db.search_medicines(query) if query else db.get_all_medicines()
        self.med_table.setRowCount(0)
        for row in rows:
            r = self.med_table.rowCount()
            self.med_table.insertRow(r)
            name_item = QTableWidgetItem(row["name"])
            name_item.setData(Qt.UserRole, row["id"])
            self.med_table.setItem(r, 0, name_item)
            stock_item = QTableWidgetItem(str(row["stock_quantity"]))
            if row["stock_quantity"] <= row["low_stock_threshold"]:
                stock_item.setBackground(LOW_STOCK_COLOR)
            self.med_table.setItem(r, 1, stock_item)
            self.med_table.setItem(r, 2, QTableWidgetItem(row["unit"]))
        self.patients_table.setRowCount(0)

        # Refresh patient picker for prescribing
        self.patient_picker.clear()
        for p in db.get_all_patients():
            self.patient_picker.addItem(p["name"], p["id"])

    def selected_medicine_id(self):
        items = self.med_table.selectedItems()
        if not items:
            return None
        return self.med_table.item(items[0].row(), 0).data(Qt.UserRole)

    def show_selected_medicine_patients(self):
        mid = self.selected_medicine_id()
        self.patients_table.setRowCount(0)
        if mid is None:
            return
        for presc in db.get_patients_for_medicine(mid):
            r = self.patients_table.rowCount()
            self.patients_table.insertRow(r)
            self.patients_table.setItem(r, 0, QTableWidgetItem(presc["patient_name"]))
            self.patients_table.setItem(r, 1, QTableWidgetItem(presc["phone"] or ""))
            self.patients_table.setItem(r, 2, QTableWidgetItem(str(presc["dose_amount"])))
            self.patients_table.setItem(r, 3, QTableWidgetItem(fmt_dt(presc["last_taken"])))
            self.patients_table.setItem(r, 4, QTableWidgetItem(fmt_dt(presc["next_due"])))

    def add_medicine(self):
        name = self.new_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Medicine name is required.")
            return
        try:
            db.add_medicine(
                name, self.new_unit.text().strip() or "tablet",
                self.new_stock.value(), self.new_threshold.value()
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not add medicine: {e}")
            return
        self.new_name.clear()
        self.refresh_medicine_list()

    def update_stock(self):
        mid = self.selected_medicine_id()
        if mid is None:
            QMessageBox.warning(self, "No selection", "Select a medicine first.")
            return
        db.update_stock(mid, self.stock_update.value())
        self.refresh_medicine_list()

    def add_prescription(self):
        mid = self.selected_medicine_id()
        if mid is None:
            QMessageBox.warning(self, "No selection", "Select a medicine first.")
            return
        if self.patient_picker.count() == 0:
            QMessageBox.warning(self, "No patients", "Add a patient first.")
            return
        pid = self.patient_picker.currentData()
        now_iso = datetime.now().isoformat(timespec="seconds")
        db.add_prescription(pid, mid, self.dose_amount.value(), self.frequency.value(), last_taken=now_iso)
        self.show_selected_medicine_patients()
        QMessageBox.information(self, "Done", "Prescription added with first dose recorded as now.")


# ---------------------------------------------------------------
# Dashboard Tab (low stock alerts)
# ---------------------------------------------------------------
class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Low stock alerts</h2>"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Medicine", "Stock left", "Alert threshold"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)
        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        for row in db.get_low_stock_medicines():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(row["name"]))
            stock_item = QTableWidgetItem(str(row["stock_quantity"]))
            stock_item.setBackground(LOW_STOCK_COLOR)
            self.table.setItem(r, 1, stock_item)
            self.table.setItem(r, 2, QTableWidgetItem(str(row["low_stock_threshold"])))


# ---------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Biopharma Tracker")
        self.resize(1150, 700)

        tabs = QTabWidget()
        self.patients_tab = PatientsTab()
        self.medicines_tab = MedicinesTab()
        self.dashboard_tab = DashboardTab()

        tabs.addTab(self.patients_tab, "Patients")
        tabs.addTab(self.medicines_tab, "Medicines")
        tabs.addTab(self.dashboard_tab, "Dashboard")

        # Keep tabs in sync: switching tabs refreshes cross-linked data
        tabs.currentChanged.connect(self.on_tab_changed)
        self.tabs = tabs

        self.setCentralWidget(tabs)

    def on_tab_changed(self, index):
        self.patients_tab.refresh_patient_list()
        self.medicines_tab.refresh_medicine_list()
        self.dashboard_tab.refresh()


def main():
    db.init_db()
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
