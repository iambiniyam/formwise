const fileInput = document.getElementById("file");
const drop = document.getElementById("drop");
const selected = document.getElementById("selected");
const inspectButton = document.getElementById("inspect");
const statusLine = document.getElementById("status");
const result = document.getElementById("result");
const resultTitle = document.getElementById("result-title");
const summary = document.getElementById("summary");
const profileNote = document.getElementById("profile-note");
const fieldsBox = document.getElementById("fields");
const preview = document.getElementById("preview");
const flatten = document.getElementById("flatten");
const fillButton = document.getElementById("fill");
const download = document.getElementById("download");
const fillStatus = document.getElementById("fill-status");

const MAX_BYTES = 25 * 1024 * 1024;
const state = { file: null, job: null, fields: [] };

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function setStatus(message, isError = false) {
  statusLine.textContent = message;
  statusLine.classList.toggle("is-error", isError);
}

function setFillStatus(message, isError = false) {
  fillStatus.textContent = message;
  fillStatus.classList.toggle("is-error", isError);
}

function setFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    setStatus("Choose a PDF file.", true);
    return;
  }
  if (file.size > MAX_BYTES) {
    setStatus("That PDF is larger than 25 MB.", true);
    return;
  }
  state.file = file;
  selected.hidden = false;
  selected.textContent = `${file.name} · ${Math.round(file.size / 1024)} KB`;
  result.hidden = true;
  setStatus("");
}

fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
["dragenter", "dragover"].forEach((name) => drop.addEventListener(name, (event) => {
  event.preventDefault(); drop.classList.add("is-over");
}));
["dragleave", "drop"].forEach((name) => drop.addEventListener(name, (event) => {
  event.preventDefault(); drop.classList.remove("is-over");
}));
drop.addEventListener("drop", (event) => setFile(event.dataTransfer.files[0]));

function fieldControl(field, index) {
  const id = `field-${index}`;
  const value = field.suggested || field.value || "";
  if (field.options && field.options.length) {
    return `<select id="${id}" data-name="${escapeHtml(field.name)}">${field.options
      .map((option) => `<option ${option === value ? "selected" : ""}>${escapeHtml(option)}</option>`)
      .join("")}</select>`;
  }
  if (field.type === "button") {
    const checked = ["yes", "true", "on", "1", "/yes"].includes(value.toLowerCase());
    return `<label class="toggle"><input id="${id}" type="checkbox" data-name="${escapeHtml(field.name)}" data-kind="checkbox" ${checked ? "checked" : ""}> Checked</label>`;
  }
  return `<input id="${id}" type="text" data-name="${escapeHtml(field.name)}" value="${escapeHtml(value)}">`;
}

function render(data) {
  state.job = data.job;
  state.fields = data.fields;
  result.hidden = false;
  profileNote.hidden = !data.profile_locked;
  profileNote.textContent = data.profile_locked
    ? "The local profile is encrypted. Values are blank until you fill them manually."
    : "";
  summary.textContent = `${data.fields.length} fields · ${data.pages} page${data.pages === 1 ? "" : "s"}`;
  fieldsBox.innerHTML = data.fields
    .map(
      (field, index) => `<div class="field">
        <label for="field-${index}">${escapeHtml(field.name)} <span class="type">${escapeHtml(field.type)}</span></label>
        ${fieldControl(field, index)}
      </div>`
    )
    .join("");
  preview.src = data.preview;
  download.hidden = true;
  setFillStatus("");
  resultTitle.focus();
}

inspectButton.addEventListener("click", async () => {
  if (!state.file) { setStatus("Choose a PDF first.", true); return; }
  inspectButton.disabled = true;
  inspectButton.textContent = "Reading...";
  setStatus("Reading the form locally.");
  const body = new FormData();
  body.append("file", state.file);
  try {
    const response = await fetch("/api/inspect", { method: "POST", body });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Server returned ${response.status}`);
    }
    render(await response.json());
    setStatus("Done. Review the values before filling.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    inspectButton.disabled = false;
    inspectButton.textContent = "Read form";
  }
});

fillButton.addEventListener("click", async () => {
  if (!state.job) return;
  const values = {};
  for (const control of fieldsBox.querySelectorAll("[data-name]")) {
    values[control.dataset.name] = control.dataset.kind === "checkbox"
      ? (control.checked ? "Yes" : "Off")
      : control.value;
  }
  fillButton.disabled = true;
  fillButton.textContent = "Filling...";
  setFillStatus("Writing the values into the PDF.");
  try {
    const response = await fetch("/api/fill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job: state.job, values, flatten: flatten.checked }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Server returned ${response.status}`);
    }
    const data = await response.json();
    preview.src = data.preview;
    download.href = data.download;
    download.hidden = false;
    setFillStatus(`Filled ${data.filled.length} fields.`);
  } catch (error) {
    setFillStatus(error.message, true);
  } finally {
    fillButton.disabled = false;
    fillButton.textContent = "Fill and download";
  }
});
