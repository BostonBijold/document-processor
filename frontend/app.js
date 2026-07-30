const fileInput = document.getElementById("file-input");
const uploadBtn = document.getElementById("upload-btn");
const uploadStatus = document.getElementById("upload-status");

const vendorFilter = document.getElementById("vendor-filter");
const statusFilter = document.getElementById("status-filter");
const applyBtn = document.getElementById("apply-filters");
const listStatus = document.getElementById("list-status");
const accordionEl = document.getElementById("accordion");
const prevBtn = document.getElementById("prev-page");
const nextBtn = document.getElementById("next-page");
const pageInfo = document.getElementById("page-info");
const previewBody = document.getElementById("preview-body");

const PAGE_SIZE = 20;
let skip = 0;
let items = [];
let expandedId = null;
let editingId = null;
let currentPreviewUrl = null;

function statusChip(status) {
  return `<span class="chip chip-${status}">${status}</span>`;
}

function setBanner(area, kind, html) {
  area.innerHTML = `<div class="banner banner-${kind}">${html}</div>`;
}

// ---------- Preview panel ----------

function clearPreview() {
  if (currentPreviewUrl) {
    URL.revokeObjectURL(currentPreviewUrl);
    currentPreviewUrl = null;
  }
  previewBody.innerHTML = '<p class="muted">Select an invoice to preview its document.</p>';
}

async function loadPreview(id) {
  previewBody.innerHTML = '<p class="muted"><span class="spinner"></span> Loading document…</p>';
  try {
    const { blob, contentType } = await API.getDocumentBlob(id);
    if (currentPreviewUrl) URL.revokeObjectURL(currentPreviewUrl);
    currentPreviewUrl = URL.createObjectURL(blob);

    if (contentType.startsWith("image/")) {
      previewBody.innerHTML = `<img src="${currentPreviewUrl}" alt="Invoice document" />`;
    } else if (contentType === "application/pdf") {
      previewBody.innerHTML = `<iframe src="${currentPreviewUrl}" title="Invoice document"></iframe>`;
    } else {
      previewBody.innerHTML = `
        <p class="muted">Preview not available for ${Fmt.escapeHtml(contentType)}.</p>
        <p><a href="${currentPreviewUrl}" target="_blank" rel="noopener">Open file</a></p>
      `;
    }
  } catch (err) {
    previewBody.innerHTML = `<p class="muted">Could not load document: ${Fmt.escapeHtml(err.message)}</p>`;
  }
}

// ---------- Accordion ----------

function renderDetailFields(inv) {
  const lineItemsRows = (inv.line_items || [])
    .map(
      (item) => `
        <tr>
          <td>${Fmt.escapeHtml(item.description)}</td>
          <td>${item.quantity ?? "—"}</td>
          <td>${Fmt.money(item.unit_price, inv.currency)}</td>
          <td>${Fmt.money(item.amount, inv.currency)}</td>
        </tr>`
    )
    .join("");

  const warningHtml = inv.validation_warning
    ? `<div class="banner banner-warn">
         <strong>Validation warning — double-check the extracted totals:</strong>
         ${Fmt.escapeHtml(inv.validation_warning)}
       </div>`
    : "";

  const actionHtml =
    inv.status === "paid"
      ? `<p class="muted">Paid on ${Fmt.date(inv.paid_date)}</p>`
      : `<button class="mark-paid-btn" type="button" data-id="${Fmt.escapeHtml(inv.id)}">Mark as paid</button>`;

  return `
    ${warningHtml}
    <div class="field-grid">
      <div><div class="label">Vendor</div><div class="value">${Fmt.escapeHtml(inv.vendor_name)}</div></div>
      <div><div class="label">Invoice #</div><div class="value">${Fmt.escapeHtml(inv.invoice_number)}</div></div>
      <div><div class="label">Issue date</div><div class="value">${Fmt.date(inv.issue_date)}</div></div>
      <div><div class="label">Due date</div><div class="value">${Fmt.date(inv.due_date)}</div></div>
      <div><div class="label">Currency</div><div class="value">${Fmt.escapeHtml(inv.currency || "—")}</div></div>
      <div><div class="label">Subtotal</div><div class="value">${Fmt.money(inv.subtotal, inv.currency)}</div></div>
      <div><div class="label">Tax</div><div class="value">${Fmt.money(inv.tax, inv.currency)}</div></div>
      <div><div class="label">Total</div><div class="value">${Fmt.money(inv.total, inv.currency)}</div></div>
    </div>
    <table>
      <thead>
        <tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr>
      </thead>
      <tbody>${lineItemsRows || '<tr><td colspan="4" class="muted">No line items extracted</td></tr>'}</tbody>
    </table>
    <p style="margin-top:1rem">
      <button class="edit-btn secondary" type="button" data-id="${Fmt.escapeHtml(inv.id)}">Edit</button>
      ${actionHtml}
    </p>
    <p class="muted" style="font-size:0.85rem">
      Stored ${Fmt.dateTime(inv.created_at)} · last updated ${Fmt.dateTime(inv.updated_at)}
    </p>
  `;
}

function editLineItemRowHtml(item = {}) {
  return `
    <tr class="ef-line-item">
      <td><input type="text" class="ef-li-desc" value="${Fmt.escapeHtml(item.description || "")}" /></td>
      <td><input type="number" step="any" class="ef-li-qty" value="${item.quantity ?? ""}" /></td>
      <td><input type="number" step="0.01" class="ef-li-price" value="${item.unit_price ?? ""}" /></td>
      <td><input type="number" step="0.01" class="ef-li-amount" value="${item.amount ?? ""}" /></td>
      <td><button class="remove-line-item-btn secondary" type="button">✕</button></td>
    </tr>
  `;
}

function renderEditForm(inv) {
  const lineItemRows = (inv.line_items && inv.line_items.length ? inv.line_items : [{}])
    .map(editLineItemRowHtml)
    .join("");

  return `
    <div class="edit-form" data-id="${Fmt.escapeHtml(inv.id)}">
      <div class="edit-error"></div>
      <div class="field-grid">
        <div><div class="label">Vendor</div><input type="text" class="ef-vendor" value="${Fmt.escapeHtml(inv.vendor_name)}" /></div>
        <div><div class="label">Invoice #</div><input type="text" class="ef-invoice-number" value="${Fmt.escapeHtml(inv.invoice_number)}" /></div>
        <div><div class="label">Issue date</div><input type="date" class="ef-issue-date" value="${Fmt.dateInputValue(inv.issue_date)}" /></div>
        <div><div class="label">Due date</div><input type="date" class="ef-due-date" value="${Fmt.dateInputValue(inv.due_date)}" /></div>
        <div><div class="label">Currency</div><input type="text" class="ef-currency" value="${Fmt.escapeHtml(inv.currency || "")}" /></div>
        <div><div class="label">Subtotal</div><input type="number" step="0.01" class="ef-subtotal" value="${inv.subtotal ?? ""}" /></div>
        <div><div class="label">Tax</div><input type="number" step="0.01" class="ef-tax" value="${inv.tax ?? ""}" /></div>
        <div><div class="label">Total</div><input type="number" step="0.01" class="ef-total" value="${inv.total ?? ""}" /></div>
      </div>
      <table class="ef-line-items">
        <thead>
          <tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th><th></th></tr>
        </thead>
        <tbody>${lineItemRows}</tbody>
      </table>
      <p><button class="add-line-item-btn secondary" type="button">+ Add line item</button></p>
      <p style="margin-top:1rem">
        <button class="save-btn" type="button" data-id="${Fmt.escapeHtml(inv.id)}">Save</button>
        <button class="cancel-btn secondary" type="button">Cancel</button>
      </p>
    </div>
  `;
}

function renderAccordion() {
  if (items.length === 0) {
    accordionEl.innerHTML = '<p class="muted">No invoices match.</p>';
    return;
  }

  accordionEl.innerHTML = items
    .map((inv) => {
      const isOpen = inv.id === expandedId;
      const isEditing = isOpen && inv.id === editingId;
      const detailHtml = isEditing ? renderEditForm(inv) : renderDetailFields(inv);
      return `
        <div class="accordion-item${isOpen ? " selected" : ""}" data-id="${Fmt.escapeHtml(inv.id)}">
          <div class="accordion-row" data-id="${Fmt.escapeHtml(inv.id)}">
            <span>${Fmt.escapeHtml(inv.vendor_name)}</span>
            <span>${Fmt.escapeHtml(inv.invoice_number)}</span>
            <span>${Fmt.date(inv.issue_date)}</span>
            <span>${Fmt.money(inv.total, inv.currency)}</span>
            <span>${statusChip(inv.status)}</span>
            <span class="chevron">▶</span>
          </div>
          ${isOpen ? `<div class="accordion-detail">${detailHtml}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

// Single delegated listener -- survives re-renders and dynamically added
// line-item rows, unlike per-element listeners attached in renderAccordion().
accordionEl.addEventListener("click", (e) => {
  const removeBtn = e.target.closest(".remove-line-item-btn");
  if (removeBtn) {
    e.stopPropagation();
    removeBtn.closest("tr").remove();
    return;
  }

  const addBtn = e.target.closest(".add-line-item-btn");
  if (addBtn) {
    e.stopPropagation();
    addBtn.closest(".edit-form").querySelector(".ef-line-items tbody").insertAdjacentHTML("beforeend", editLineItemRowHtml());
    return;
  }

  const editBtn = e.target.closest(".edit-btn");
  if (editBtn) {
    e.stopPropagation();
    editingId = editBtn.dataset.id;
    renderAccordion();
    return;
  }

  const cancelBtn = e.target.closest(".cancel-btn");
  if (cancelBtn) {
    e.stopPropagation();
    editingId = null;
    renderAccordion();
    return;
  }

  const saveBtn = e.target.closest(".save-btn");
  if (saveBtn) {
    e.stopPropagation();
    handleSaveEdit(saveBtn.dataset.id);
    return;
  }

  const markPaidBtn = e.target.closest(".mark-paid-btn");
  if (markPaidBtn) {
    e.stopPropagation();
    handleMarkPaid(markPaidBtn.dataset.id);
    return;
  }

  const row = e.target.closest(".accordion-row");
  if (row) {
    toggleItem(row.dataset.id);
  }
});

function toggleItem(id) {
  if (expandedId === id) {
    expandedId = null;
    editingId = null;
    clearPreview();
  } else {
    expandedId = id;
    editingId = null;
    loadPreview(id);
  }
  renderAccordion();
}

async function handleMarkPaid(id) {
  try {
    const updated = await API.updateStatus(id, "paid");
    items = items.map((inv) => (inv.id === id ? updated : inv));
    renderAccordion();
  } catch (err) {
    listStatus.innerHTML = `<div class="banner banner-error">Could not update status: ${Fmt.escapeHtml(err.message)}</div>`;
  }
}

function readLineItemsFromForm(form) {
  return Array.from(form.querySelectorAll(".ef-line-item"))
    .map((row) => {
      const qtyRaw = row.querySelector(".ef-li-qty").value.trim();
      const priceRaw = row.querySelector(".ef-li-price").value.trim();
      const amountRaw = row.querySelector(".ef-li-amount").value.trim();
      return {
        description: row.querySelector(".ef-li-desc").value.trim(),
        quantity: qtyRaw === "" ? null : Number(qtyRaw),
        unit_price: priceRaw === "" ? null : Number(priceRaw),
        amount: amountRaw === "" ? 0 : Number(amountRaw),
      };
    })
    .filter((item) => item.description !== "" || item.amount !== 0);
}

async function handleSaveEdit(id) {
  const form = accordionEl.querySelector(`.edit-form[data-id="${id}"]`);
  if (!form) return;
  const errorArea = form.querySelector(".edit-error");

  const readText = (selector) => form.querySelector(selector).value.trim();
  const readNumber = (selector) => {
    const raw = form.querySelector(selector).value.trim();
    return raw === "" ? null : Number(raw);
  };

  const vendorName = readText(".ef-vendor");
  const invoiceNumber = readText(".ef-invoice-number");
  const issueDate = readText(".ef-issue-date");
  const dueDate = readText(".ef-due-date");
  const currency = readText(".ef-currency");
  const total = readNumber(".ef-total");

  if (!vendorName || !invoiceNumber || !issueDate || total === null) {
    errorArea.innerHTML = `<div class="banner banner-error">Vendor, invoice #, issue date, and total are required.</div>`;
    return;
  }

  const payload = {
    vendor_name: vendorName,
    invoice_number: invoiceNumber,
    issue_date: issueDate,
    due_date: dueDate || null,
    line_items: readLineItemsFromForm(form),
    subtotal: readNumber(".ef-subtotal"),
    tax: readNumber(".ef-tax"),
    total,
    currency: currency || null,
  };

  const saveBtn = form.querySelector(".save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving…";
  errorArea.innerHTML = "";

  try {
    const updated = await API.updateFields(id, payload);
    items = items.map((inv) => (inv.id === id ? updated : inv));
    editingId = null;
    renderAccordion();
  } catch (err) {
    errorArea.innerHTML = `<div class="banner banner-error">${Fmt.escapeHtml(err.message)}</div>`;
    saveBtn.disabled = false;
    saveBtn.textContent = "Save";
  }
}

// ---------- List loading ----------

async function load({ preserveSelection = false } = {}) {
  listStatus.innerHTML = "";
  accordionEl.innerHTML = '<p class="muted"><span class="spinner"></span> Loading…</p>';
  if (!preserveSelection) {
    expandedId = null;
    clearPreview();
  }
  try {
    const result = await API.listInvoices({
      vendorName: vendorFilter.value.trim() || undefined,
      status: statusFilter.value || undefined,
      skip,
      limit: PAGE_SIZE,
    });
    items = result.items;
    renderAccordion();

    const shown = items.length;
    const from = shown === 0 ? 0 : skip + 1;
    const to = skip + shown;
    pageInfo.textContent = `${from}-${to} of ${result.total}`;
    prevBtn.disabled = skip === 0;
    nextBtn.disabled = skip + PAGE_SIZE >= result.total;
  } catch (err) {
    accordionEl.innerHTML = "";
    listStatus.innerHTML = `<div class="banner banner-error">${Fmt.escapeHtml(err.message)} — is the Data service running at ${Fmt.escapeHtml(window.APP_CONFIG.DATA_URL)}?</div>`;
  }
}

applyBtn.addEventListener("click", () => {
  skip = 0;
  load();
});
vendorFilter.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    skip = 0;
    load();
  }
});
prevBtn.addEventListener("click", () => {
  skip = Math.max(0, skip - PAGE_SIZE);
  load();
});
nextBtn.addEventListener("click", () => {
  skip = skip + PAGE_SIZE;
  load();
});

// ---------- Upload ----------

uploadBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  fileInput.value = ""; // allow re-selecting the same file later
  if (!file) return;

  uploadBtn.disabled = true;
  setBanner(uploadStatus, "warn", '<span class="spinner"></span> Uploading and extracting — this can take a few seconds…');

  try {
    const { status, body } = await API.upload(file);

    if (!body) {
      setBanner(uploadStatus, "error", `Upload failed (HTTP ${status}) and the server didn't return details.`);
      return;
    }

    if (status === 201 && body.status === "stored") {
      const warningNote = body.warning
        ? ` <strong>Validation warning:</strong> ${Fmt.escapeHtml(body.warning)}`
        : "";
      setBanner(
        uploadStatus,
        body.warning ? "warn" : "success",
        `Stored "${Fmt.escapeHtml(body.invoice.vendor_name)}" — ${Fmt.money(body.invoice.total, body.invoice.currency)}.${warningNote}`
      );
      skip = 0;
      await load();
      if (items.some((inv) => inv.id === body.invoice.id)) {
        toggleItem(body.invoice.id);
      }
    } else if (body.status === "extraction_failed") {
      setBanner(uploadStatus, "error", `<strong>Extraction failed:</strong> ${Fmt.escapeHtml(body.detail)}`);
    } else if (body.status === "storage_failed") {
      const extracted = body.extracted_data || {};
      setBanner(
        uploadStatus,
        "error",
        `<strong>Extraction succeeded but storage failed:</strong> ${Fmt.escapeHtml(body.detail)}<br />` +
          `Nothing was saved. Extracted data: ${Fmt.escapeHtml(extracted.vendor_name || "")} — ` +
          `${Fmt.money(extracted.total, extracted.currency)}. You'll need to retry the upload.`
      );
    } else {
      setBanner(uploadStatus, "error", Fmt.escapeHtml(body.detail || `Upload failed (HTTP ${status}).`));
    }
  } catch (err) {
    setBanner(
      uploadStatus,
      "error",
      `Could not reach the Intake service at ${Fmt.escapeHtml(window.APP_CONFIG.INTAKE_URL)}. ${Fmt.escapeHtml(err.message)}`
    );
  } finally {
    uploadBtn.disabled = false;
  }
});

load();
