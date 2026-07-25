const content = document.getElementById("content");
const invoiceId = new URLSearchParams(window.location.search).get("id");

function statusChip(status) {
  return `<span class="chip chip-${status}">${status}</span>`;
}

function render(invoice, { actionMessage = "" } = {}) {
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

  const warningHtml = invoice.validation_warning
    ? `<div class="banner banner-warn">
         <strong>Validation warning — double-check the extracted totals:</strong>
         ${Fmt.escapeHtml(invoice.validation_warning)}
       </div>`
    : "";

  const actionHtml =
    invoice.status === "paid"
      ? `<p class="muted">Paid on ${Fmt.date(invoice.paid_date)}</p>`
      : `<button id="mark-paid-btn" type="button">Mark as paid</button>`;

  content.innerHTML = `
    ${warningHtml}
    ${actionMessage}
    <div class="card">
      <div class="field-grid">
        <div><div class="label">Vendor</div><div class="value">${Fmt.escapeHtml(invoice.vendor_name)}</div></div>
        <div><div class="label">Invoice #</div><div class="value">${Fmt.escapeHtml(invoice.invoice_number)}</div></div>
        <div><div class="label">Issue date</div><div class="value">${Fmt.date(invoice.issue_date)}</div></div>
        <div><div class="label">Due date</div><div class="value">${Fmt.date(invoice.due_date)}</div></div>
        <div><div class="label">Status</div><div class="value">${statusChip(invoice.status)}</div></div>
        <div><div class="label">Currency</div><div class="value">${Fmt.escapeHtml(invoice.currency || "—")}</div></div>
        <div><div class="label">Subtotal</div><div class="value">${Fmt.money(invoice.subtotal, invoice.currency)}</div></div>
        <div><div class="label">Tax</div><div class="value">${Fmt.money(invoice.tax, invoice.currency)}</div></div>
        <div><div class="label">Total</div><div class="value">${Fmt.money(invoice.total, invoice.currency)}</div></div>
      </div>

      <table>
        <thead>
          <tr><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr>
        </thead>
        <tbody>${lineItemsRows || '<tr><td colspan="4" class="muted">No line items extracted</td></tr>'}</tbody>
      </table>

      <p style="margin-top:1.25rem">${actionHtml}</p>
      <p class="muted" style="font-size:0.85rem">
        Stored ${Fmt.dateTime(invoice.created_at)} · last updated ${Fmt.dateTime(invoice.updated_at)}
      </p>
    </div>
  `;

  const markPaidBtn = document.getElementById("mark-paid-btn");
  if (markPaidBtn) {
    markPaidBtn.addEventListener("click", async () => {
      markPaidBtn.disabled = true;
      markPaidBtn.innerHTML = '<span class="spinner"></span> Updating…';
      try {
        const updated = await API.updateStatus(invoice.id, "paid");
        render(updated, {
          actionMessage: '<div class="banner banner-success">Marked as paid.</div>',
        });
      } catch (err) {
        render(invoice, {
          actionMessage: `<div class="banner banner-error">Could not update status: ${Fmt.escapeHtml(err.message)}</div>`,
        });
      }
    });
  }
}

async function load() {
  if (!invoiceId) {
    content.innerHTML = '<div class="banner banner-error">No invoice id given.</div>';
    return;
  }
  try {
    const invoice = await API.getInvoice(invoiceId);
    render(invoice);
  } catch (err) {
    content.innerHTML = `<div class="banner banner-error">${Fmt.escapeHtml(err.message)} — is the Data service running at ${Fmt.escapeHtml(window.APP_CONFIG.DATA_URL)}?</div>`;
  }
}

load();
