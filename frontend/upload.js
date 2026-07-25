const form = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const submitBtn = document.getElementById("submit-btn");
const statusArea = document.getElementById("status-area");
const resultArea = document.getElementById("result-area");

function setBanner(area, kind, html) {
  area.innerHTML = `<div class="banner banner-${kind}">${html}</div>`;
}

function clear(area) {
  area.innerHTML = "";
}

function renderExtractedPreview(invoice, { warning = null, stored = true } = {}) {
  const lineItemsRows = (invoice.line_items || [])
    .map(
      (item) => `
        <tr>
          <td>${Fmt.escapeHtml(item.description)}</td>
          <td>${item.quantity ?? "—"}</td>
          <td>${Fmt.money(item.unit_price, invoice.currency)}</td>
          <td>${Fmt.money(item.amount, invoice.currency)}</td>
        </tr>`
    )
    .join("");

  const warningHtml = warning
    ? `<div class="banner banner-warn">
         <strong>Validation warning:</strong> ${Fmt.escapeHtml(warning)}
       </div>`
    : "";

  const successBanner = stored
    ? `<div class="banner banner-success">Invoice stored successfully.</div>`
    : "";

  const detailLink = stored
    ? `<p style="margin-top:1rem">
         <a href="invoice.html?id=${encodeURIComponent(invoice.id)}">View full detail →</a>
       </p>`
    : "";

  resultArea.innerHTML = `
    ${successBanner}
    ${warningHtml}
    <div class="card">
      <div class="field-grid">
        <div><div class="label">Vendor</div><div class="value">${Fmt.escapeHtml(invoice.vendor_name)}</div></div>
        <div><div class="label">Invoice #</div><div class="value">${Fmt.escapeHtml(invoice.invoice_number)}</div></div>
        <div><div class="label">Issue date</div><div class="value">${Fmt.date(invoice.issue_date)}</div></div>
        <div><div class="label">Total</div><div class="value">${Fmt.money(invoice.total, invoice.currency)}</div></div>
      </div>
      <table>
        <thead>
          <tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr>
        </thead>
        <tbody>${lineItemsRows || '<tr><td colspan="4" class="muted">No line items extracted</td></tr>'}</tbody>
      </table>
      ${detailLink}
    </div>
  `;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clear(resultArea);

  const file = fileInput.files[0];
  if (!file) {
    setBanner(statusArea, "error", "Choose a file first.");
    return;
  }

  submitBtn.disabled = true;
  setBanner(statusArea, "warn", '<span class="spinner"></span> Uploading and extracting — this can take a few seconds…');

  try {
    const { status, body } = await API.upload(file);

    if (!body) {
      setBanner(statusArea, "error", `Upload failed (HTTP ${status}) and the server didn't return details.`);
      return;
    }

    if (status === 201 && body.status === "stored") {
      clear(statusArea);
      renderExtractedPreview(body.invoice, { warning: body.warning, stored: true });
    } else if (body.status === "extraction_failed") {
      setBanner(statusArea, "error", `<strong>Extraction failed:</strong> ${Fmt.escapeHtml(body.detail)}`);
    } else if (body.status === "storage_failed") {
      setBanner(
        statusArea,
        "error",
        `<strong>Extraction succeeded but storage failed:</strong> ${Fmt.escapeHtml(body.detail)}` +
          `<br />The extracted data below was <em>not</em> saved — you'll need to retry the upload.`
      );
      if (body.extracted_data) {
        renderExtractedPreview(body.extracted_data, { stored: false });
      }
    } else {
      // Plain FastAPI validation error (bad content type / empty file), or unexpected shape.
      setBanner(statusArea, "error", Fmt.escapeHtml(body.detail || `Upload failed (HTTP ${status}).`));
    }
  } catch (err) {
    setBanner(
      statusArea,
      "error",
      `Could not reach the Intake service at ${Fmt.escapeHtml(window.APP_CONFIG.INTAKE_URL)}. ${Fmt.escapeHtml(err.message)}`
    );
  } finally {
    submitBtn.disabled = false;
  }
});
