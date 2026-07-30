// Thin wrappers around the Intake and Data service HTTP APIs.
// No business logic here -- just fetch calls and response shaping.

const API = {
  async upload(file) {
    const formData = new FormData();
    formData.append("file", file);
    const resp = await fetch(`${window.APP_CONFIG.INTAKE_URL}/upload`, {
      method: "POST",
      body: formData,
    });
    let body = null;
    try {
      body = await resp.json();
    } catch (_) {
      // non-JSON response, leave body null
    }
    return { ok: resp.ok, status: resp.status, body };
  },

  async listInvoices({ vendorName, status, skip = 0, limit = 20 } = {}) {
    const params = new URLSearchParams();
    if (vendorName) params.set("vendor_name", vendorName);
    if (status) params.set("status", status);
    params.set("skip", skip);
    params.set("limit", limit);
    const resp = await fetch(`${window.APP_CONFIG.DATA_URL}/invoices?${params}`);
    if (!resp.ok) {
      throw new Error(`Failed to load invoices (HTTP ${resp.status})`);
    }
    return resp.json();
  },

  async getInvoice(id) {
    const resp = await fetch(`${window.APP_CONFIG.DATA_URL}/invoices/${encodeURIComponent(id)}`);
    if (!resp.ok) {
      throw new Error(`Failed to load invoice (HTTP ${resp.status})`);
    }
    return resp.json();
  },

  async getDocumentBlob(id) {
    const resp = await fetch(`${window.APP_CONFIG.DATA_URL}/invoices/${encodeURIComponent(id)}/document`);
    if (!resp.ok) {
      throw new Error(`Failed to load document (HTTP ${resp.status})`);
    }
    const blob = await resp.blob();
    return { blob, contentType: resp.headers.get("content-type") || blob.type };
  },

  async updateStatus(id, status) {
    const resp = await fetch(
      `${window.APP_CONFIG.DATA_URL}/invoices/${encodeURIComponent(id)}/status`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      }
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => null);
      throw new Error(body?.detail || `Failed to update status (HTTP ${resp.status})`);
    }
    return resp.json();
  },

  async updateFields(id, fields) {
    const resp = await fetch(`${window.APP_CONFIG.DATA_URL}/invoices/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => null);
      const detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail);
      throw new Error(detail || `Failed to save changes (HTTP ${resp.status})`);
    }
    return resp.json();
  },
};

const Fmt = {
  escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
  },

  money(amount, currency) {
    if (amount === null || amount === undefined) return "—";
    const num = Number(amount).toFixed(2);
    return currency ? `${currency} ${num}` : num;
  },

  date(value) {
    if (!value) return "—";
    return String(value).slice(0, 10);
  },

  // Like date(), but returns "" instead of "—" for <input type="date"> values.
  dateInputValue(value) {
    return value ? String(value).slice(0, 10) : "";
  },

  dateTime(value) {
    if (!value) return "—";
    return String(value).replace("T", " ").slice(0, 19);
  },
};
