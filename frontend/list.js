const vendorFilter = document.getElementById("vendor-filter");
const statusFilter = document.getElementById("status-filter");
const applyBtn = document.getElementById("apply-filters");
const statusArea = document.getElementById("status-area");
const rowsBody = document.getElementById("invoice-rows");
const prevBtn = document.getElementById("prev-page");
const nextBtn = document.getElementById("next-page");
const pageInfo = document.getElementById("page-info");

const PAGE_SIZE = 20;
let skip = 0;
let lastTotal = 0;

function statusChip(status) {
  return `<span class="chip chip-${status}">${status}</span>`;
}

function renderRows(items) {
  if (items.length === 0) {
    rowsBody.innerHTML = '<tr><td colspan="5" class="muted">No invoices match.</td></tr>';
    return;
  }
  rowsBody.innerHTML = items
    .map(
      (inv) => `
        <tr class="clickable" data-id="${Fmt.escapeHtml(inv.id)}">
          <td>${Fmt.escapeHtml(inv.vendor_name)}</td>
          <td>${Fmt.escapeHtml(inv.invoice_number)}</td>
          <td>${Fmt.date(inv.issue_date)}</td>
          <td>${Fmt.money(inv.total, inv.currency)}</td>
          <td>${statusChip(inv.status)}</td>
        </tr>`
    )
    .join("");

  rowsBody.querySelectorAll("tr.clickable").forEach((row) => {
    row.addEventListener("click", () => {
      window.location.href = `invoice.html?id=${encodeURIComponent(row.dataset.id)}`;
    });
  });
}

async function load() {
  statusArea.innerHTML = "";
  rowsBody.innerHTML = '<tr><td colspan="5" class="muted"><span class="spinner"></span> Loading…</td></tr>';
  try {
    const result = await API.listInvoices({
      vendorName: vendorFilter.value.trim() || undefined,
      status: statusFilter.value || undefined,
      skip,
      limit: PAGE_SIZE,
    });
    lastTotal = result.total;
    renderRows(result.items);

    const shown = result.items.length;
    const from = shown === 0 ? 0 : skip + 1;
    const to = skip + shown;
    pageInfo.textContent = `${from}-${to} of ${lastTotal}`;
    prevBtn.disabled = skip === 0;
    nextBtn.disabled = skip + PAGE_SIZE >= lastTotal;
  } catch (err) {
    rowsBody.innerHTML = "";
    statusArea.innerHTML = `<div class="banner banner-error">${Fmt.escapeHtml(err.message)} — is the Data service running at ${Fmt.escapeHtml(window.APP_CONFIG.DATA_URL)}?</div>`;
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

load();
