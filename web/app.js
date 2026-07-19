// app.js — talks to Python via window.pywebview.api

let selectedPatientId = null;
let selectedPrescriptionId = null;
let selectedMedicineId = null;

function api() {
  return window.pywebview.api;
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2200);
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ================= Navigation =================
document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("page-" + btn.dataset.page).classList.add("active");

    if (btn.dataset.page === "patients") refreshPatients();
    if (btn.dataset.page === "medicines") refreshMedicines();
    if (btn.dataset.page === "dashboard") refreshDashboard();
  });
});

// ================= Patients page =================
async function refreshPatients() {
  const query = document.getElementById("patient-search").value.trim();
  const patients = await api().get_patients(query);
  const body = document.getElementById("patient-table-body");
  body.innerHTML = "";

  if (patients.length === 0) {
    body.innerHTML = `<tr class="empty-row"><td colspan="2">No patients found</td></tr>`;
  } else {
    patients.forEach((p) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${escapeHtml(p.name)}</td><td>${escapeHtml(p.phone || "—")}</td>`;
      tr.addEventListener("click", () => selectPatient(p.id, tr));
      body.appendChild(tr);
    });
  }

  // reset right panel if the selected patient disappeared from results
  if (!patients.find((p) => p.id === selectedPatientId)) {
    selectedPatientId = null;
    renderPatientMeds([]);
  }
}

function selectPatient(id, rowEl) {
  selectedPatientId = id;
  document.querySelectorAll("#patient-table-body tr").forEach((r) => r.classList.remove("selected"));
  rowEl.classList.add("selected");
  loadPatientMeds();
}

async function loadPatientMeds() {
  if (!selectedPatientId) return renderPatientMeds([]);
  const meds = await api().get_patient_prescriptions(selectedPatientId);
  renderPatientMeds(meds);
}

function renderPatientMeds(meds) {
  const body = document.getElementById("patient-meds-body");
  body.innerHTML = "";
  selectedPrescriptionId = null;

  if (meds.length === 0) {
    body.innerHTML = `<tr class="empty-row"><td colspan="6">${selectedPatientId ? "No medicines for this patient yet" : "Select a patient to see their medicines"}</td></tr>`;
    return;
  }

  meds.forEach((m) => {
    const tr = document.createElement("tr");
    const low = m.stock_quantity <= m.low_stock_threshold;
    tr.innerHTML = `
      <td>${escapeHtml(m.medicine_name)}</td>
      <td>${m.dose_amount} ${escapeHtml(m.unit)}</td>
      <td>${m.frequency_hours}h</td>
      <td>${fmtDate(m.last_taken)}</td>
      <td>${fmtDate(m.next_due)}</td>
      <td class="${low ? "low-stock" : ""}">${m.stock_quantity}</td>
    `;
    tr.addEventListener("click", () => {
      selectedPrescriptionId = m.prescription_id;
      document.querySelectorAll("#patient-meds-body tr").forEach((r) => r.classList.remove("selected"));
      tr.classList.add("selected");
    });
    body.appendChild(tr);
  });
}

document.getElementById("patient-search").addEventListener("input", refreshPatients);

document.getElementById("add-patient-btn").addEventListener("click", async () => {
  const name = document.getElementById("new-patient-name").value.trim();
  if (!name) return showToast("Patient name is required.", true);
  const res = await api().add_patient(
    name,
    document.getElementById("new-patient-phone").value,
    document.getElementById("new-patient-dob").value,
    document.getElementById("new-patient-notes").value
  );
  if (!res.ok) return showToast(res.error, true);
  document.getElementById("new-patient-name").value = "";
  document.getElementById("new-patient-phone").value = "";
  document.getElementById("new-patient-notes").value = "";
  showToast("Patient added.");
  refreshPatients();
});

document.getElementById("mark-taken-btn").addEventListener("click", async () => {
  if (!selectedPrescriptionId) return showToast("Select a medicine row first.", true);
  await api().record_dose_taken(selectedPrescriptionId);
  showToast("Dose recorded.");
  loadPatientMeds();
});

document.getElementById("remove-presc-btn").addEventListener("click", async () => {
  if (!selectedPrescriptionId) return showToast("Select a medicine row first.", true);
  await api().delete_prescription(selectedPrescriptionId);
  showToast("Prescription removed.");
  loadPatientMeds();
});

// ================= Medicines page =================
async function refreshMedicines() {
  const query = document.getElementById("medicine-search").value.trim();
  const medicines = await api().get_medicines(query);
  const body = document.getElementById("medicine-table-body");
  body.innerHTML = "";

  if (medicines.length === 0) {
    body.innerHTML = `<tr class="empty-row"><td colspan="3">No medicines found</td></tr>`;
  } else {
    medicines.forEach((m) => {
      const tr = document.createElement("tr");
      const low = m.stock_quantity <= m.low_stock_threshold;
      tr.innerHTML = `<td>${escapeHtml(m.name)}</td><td class="${low ? "low-stock" : ""}">${m.stock_quantity}</td><td>${escapeHtml(m.unit)}</td>`;
      tr.addEventListener("click", () => selectMedicine(m.id, tr));
      body.appendChild(tr);
    });
  }

  if (!medicines.find((m) => m.id === selectedMedicineId)) {
    selectedMedicineId = null;
    renderMedicinePatients([]);
  }

  await populatePatientPicker();
}

function selectMedicine(id, rowEl) {
  selectedMedicineId = id;
  document.querySelectorAll("#medicine-table-body tr").forEach((r) => r.classList.remove("selected"));
  rowEl.classList.add("selected");
  loadMedicinePatients();
}

async function loadMedicinePatients() {
  if (!selectedMedicineId) return renderMedicinePatients([]);
  const patients = await api().get_medicine_patients(selectedMedicineId);
  renderMedicinePatients(patients);
}

function renderMedicinePatients(patients) {
  const body = document.getElementById("medicine-patients-body");
  body.innerHTML = "";

  if (patients.length === 0) {
    body.innerHTML = `<tr class="empty-row"><td colspan="5">${selectedMedicineId ? "No patients on this medicine yet" : "Select a medicine to see who takes it"}</td></tr>`;
    return;
  }

  patients.forEach((p) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(p.patient_name)}</td>
      <td>${escapeHtml(p.phone || "—")}</td>
      <td>${p.dose_amount}</td>
      <td>${fmtDate(p.last_taken)}</td>
      <td>${fmtDate(p.next_due)}</td>
    `;
    body.appendChild(tr);
  });
}

async function populatePatientPicker() {
  const picker = document.getElementById("prescribe-patient-picker");
  const currentValue = picker.value;
  const patients = await api().get_patients("");
  picker.innerHTML = "";
  if (patients.length === 0) {
    picker.innerHTML = `<option value="">No patients yet — add one first</option>`;
    return;
  }
  patients.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.name;
    picker.appendChild(opt);
  });
  if (currentValue) picker.value = currentValue;
}

document.getElementById("medicine-search").addEventListener("input", refreshMedicines);

document.getElementById("add-medicine-btn").addEventListener("click", async () => {
  const name = document.getElementById("new-med-name").value.trim();
  if (!name) return showToast("Medicine name is required.", true);
  const res = await api().add_medicine(
    name,
    document.getElementById("new-med-unit").value || "tablet",
    document.getElementById("new-med-stock").value || 0,
    document.getElementById("new-med-threshold").value || 10
  );
  if (!res.ok) return showToast(res.error, true);
  document.getElementById("new-med-name").value = "";
  document.getElementById("new-med-unit").value = "";
  showToast("Medicine added.");
  refreshMedicines();
});

document.getElementById("update-stock-btn").addEventListener("click", async () => {
  if (!selectedMedicineId) return showToast("Select a medicine first.", true);
  const val = document.getElementById("stock-update-value").value || 0;
  await api().update_stock(selectedMedicineId, val);
  showToast("Stock updated.");
  refreshMedicines();
});

document.getElementById("prescribe-btn").addEventListener("click", async () => {
  if (!selectedMedicineId) return showToast("Select a medicine first.", true);
  const picker = document.getElementById("prescribe-patient-picker");
  if (!picker.value) return showToast("Add a patient first.", true);
  const dose = document.getElementById("prescribe-dose").value || 1;
  const freq = document.getElementById("prescribe-frequency").value || 24;
  await api().add_prescription(picker.value, selectedMedicineId, dose, freq);
  showToast("Prescription added — first dose recorded as now.");
  loadMedicinePatients();
});

// ================= Dashboard page =================
async function refreshDashboard() {
  const data = await api().get_dashboard();
  document.getElementById("stat-patients").textContent = data.patient_count;
  document.getElementById("stat-medicines").textContent = data.medicine_count;
  document.getElementById("stat-low-stock").textContent = data.low_stock.length;

  const body = document.getElementById("low-stock-body");
  body.innerHTML = "";
  if (data.low_stock.length === 0) {
    body.innerHTML = `<tr class="empty-row"><td colspan="3">Nothing low on stock right now 🎉</td></tr>`;
  } else {
    data.low_stock.forEach((m) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${escapeHtml(m.name)}</td><td class="low-stock">${m.stock_quantity}</td><td>${m.low_stock_threshold}</td>`;
      body.appendChild(tr);
    });
  }
}

document.getElementById("refresh-dashboard-btn").addEventListener("click", refreshDashboard);

// ================= Utils =================
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ================= Init =================
window.addEventListener("pywebviewready", () => {
  refreshPatients();
});

// Fallback in case pywebviewready already fired before this script loaded
if (window.pywebview) {
  refreshPatients();
}
