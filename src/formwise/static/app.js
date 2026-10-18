const fileInput = document.getElementById("file");
const drop = document.getElementById("drop");
const selected = document.getElementById("selected");
const inspectButton = document.getElementById("inspect");
const statusLine = document.getElementById("status");
const result = document.getElementById("result");
const resultTitle = document.getElementById("result-title");
const summary = document.getElementById("summary");
const profileNote = document.getElementById("profile-note");
const scannedNote = document.getElementById("scanned-note");
const fieldsBox = document.getElementById("fields");
const preview = document.getElementById("preview");
const flatten = document.getElementById("flatten");
const fillButton = document.getElementById("fill");
const download = document.getElementById("download");
const fillStatus = document.getElementById("fill-status");
const overlayEditor = document.getElementById("overlay-editor");
const overlayFields = document.getElementById("overlay-fields");
const markers = document.getElementById("markers");
const addField = document.getElementById("add-field");
const detectFields = document.getElementById("detect-fields");
const previewWrap = document.getElementById("preview-wrap");
const pageNav = document.getElementById("page-nav");
const pageSelect = document.getElementById("page-select");

const MAX_BYTES = 25 * 1024 * 1024;
const state = { file: null, job: null, fields: [], scanned: false, overlay: [], previews: [], page: 0 };

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

function renderOverlay() {
  markers.innerHTML = state.overlay
    .filter((item) => item.page === state.page)
    .map((item) => {
      const index = state.overlay.indexOf(item);
      return `<span class="marker" style="left:${item.x * 100}%;top:${item.y * 100}%">${index + 1}</span>`;
    })
    .join("");
  overlayFields.innerHTML = state.overlay.map((item, index) => `<div class="field overlay-row">
    <label for="overlay-${index}">${escapeHtml(item.label || `Value ${index + 1}`)} <span class="type">page ${item.page + 1}</span></label>
    <input id="overlay-${index}" type="text" data-overlay="${index}" value="${escapeHtml(item.text)}" placeholder="Text to place">
    <button type="button" data-remove="${index}">Remove</button>
  </div>`).join("");
}

function setPage(index) {
  state.page = Math.max(0, Math.min(state.previews.length - 1, index));
  if (state.previews[state.page]) preview.src = state.previews[state.page];
  pageSelect.value = String(state.page);
  renderOverlay();
}

function addOverlay(x, y) {
  state.overlay.push({ x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)), page: state.page, text: "" });
  renderOverlay();
  const input = overlayFields.querySelector(`[data-overlay="${state.overlay.length - 1}"]`);
  if (input) input.focus();
}

function render(data) {
  state.job = data.job;
  state.fields = data.fields;
  state.scanned = Boolean(data.scanned);
  state.overlay = [];
  result.hidden = false;
  profileNote.hidden = !data.profile_locked;
  profileNote.textContent = data.profile_locked
    ? "The local profile is encrypted. Values are blank until you fill them manually."
    : "";
  scannedNote.hidden = !data.scanned;
  summary.textContent = state.scanned
    ? `No AcroForm fields · ${data.pages} page${data.pages === 1 ? "" : "s"}`
    : `${data.fields.length} fields · ${data.pages} page${data.pages === 1 ? "" : "s"}`;
  fieldsBox.hidden = state.scanned;
  overlayEditor.hidden = !state.scanned;
  if (!state.scanned) {
    fieldsBox.innerHTML = data.fields
      .map(
        (field, index) => `<div class="field">
          <label for="field-${index}">${escapeHtml(field.name)} <span class="type">${escapeHtml(field.type)}</span></label>
          ${fieldControl(field, index)}
        </div>`
      )
      .join("");
  }
  state.previews = data.previews || [data.preview];
  state.page = 0;
  pageNav.hidden = state.previews.length < 2;
  pageSelect.innerHTML = state.previews.map((url, index) => `<option value="${index}">Page ${index + 1}</option>`).join("");
  setPage(0);
  download.hidden = true;
  setFillStatus("");
  resultTitle.focus();
}

pageSelect.addEventListener("change", () => setPage(Number(pageSelect.value)));
preview.addEventListener("click", (event) => {
  if (!state.scanned) return;
  const rect = preview.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  addOverlay((event.clientX - rect.left) / rect.width, (event.clientY - rect.top) / rect.height);
});
addField.addEventListener("click", () => addOverlay(0.5, 0.5));
detectFields.addEventListener("click", async () => {
  if (!state.job) return;
  detectFields.disabled = true;
  detectFields.textContent = "Detecting...";
  setFillStatus("Looking for labels on the first page.");
  try {
    const response = await fetch("/api/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job: state.job }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Server returned ${response.status}`);
    state.overlay = (payload.fields || []).map((field) => ({
      x: field.x, y: field.y, page: field.page || 0, label: field.label, text: "",
    }));
    setPage(0);
    setFillStatus(state.overlay.length ? `Found ${state.overlay.length} labels across pages. Enter values.` : "No labels found. Place fields manually.", !state.overlay.length);
  } catch (error) {
    setFillStatus(error.message, true);
  } finally {
    detectFields.disabled = false;
    detectFields.textContent = "Detect fields";
  }
});
overlayFields.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-remove]");
  if (!button) return;
  state.overlay.splice(Number(button.dataset.remove), 1);
  renderOverlay();
});
overlayFields.addEventListener("input", (event) => {
  const index = event.target.dataset.overlay;
  if (index == null) return;
  state.overlay[Number(index)].text = event.target.value;
});

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
  if (!state.scanned) {
    for (const control of fieldsBox.querySelectorAll("[data-name]")) {
      values[control.dataset.name] = control.dataset.kind === "checkbox"
        ? (control.checked ? "Yes" : "Off")
        : control.value;
    }
  }
  const overlay = state.scanned
    ? state.overlay
      .map((item) => ({ page: item.page, x: item.x, y: item.y, text: item.text.trim() }))
      .filter((item) => item.text)
    : [];
  if (state.scanned && !overlay.length) {
    setFillStatus("Click the preview to place at least one value.", true);
    return;
  }
  fillButton.disabled = true;
  fillButton.textContent = "Filling...";
  setFillStatus(state.scanned ? "Placing the text on the page." : "Writing the values into the PDF.");
  try {
    const response = await fetch("/api/fill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job: state.job, values, overlay, flatten: flatten.checked }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Server returned ${response.status}`);
    }
    const data = await response.json();
    state.previews = data.previews || [data.preview];
    pageNav.hidden = state.previews.length < 2;
    pageSelect.innerHTML = state.previews.map((url, index) => `<option value="${index}">Page ${index + 1}</option>`).join("");
    setPage(Math.min(state.page, state.previews.length - 1));
    download.href = data.download;
    download.hidden = false;
    setFillStatus(data.stamped ? `Placed ${data.filled.length} text item(s).` : `Filled ${data.filled.length} fields.`);
  } catch (error) {
    setFillStatus(error.message, true);
  } finally {
    fillButton.disabled = false;
    fillButton.textContent = "Fill and download";
  }
});
