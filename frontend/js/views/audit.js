/* ==========================================================================
   Immutable Audit Log View Renderer
   ========================================================================== */

async function renderAuditView() {
  const container = document.getElementById('view-content');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Immutable System Audit Trail</h1>
        <p class="page-subtitle">SOC-2 & SOX compliant append-only event log capturing all user actions, rule edits, and state transitions</p>
      </div>
    </div>

    <!-- Audit Logs Table Card -->
    <div class="table-card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Log ID</th>
              <th>Timestamp</th>
              <th>User</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Record ID</th>
              <th>IP Address</th>
              <th>JSON Delta</th>
            </tr>
          </thead>
          <tbody id="audit-table-body">
            <tr><td colspan="8" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading Audit Log...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  loadAuditLogsData();
}

async function loadAuditLogsData() {
  const res = await apiRequest('/api/audit');
  if (!res) return;

  const tbody = document.getElementById('audit-table-body');
  if (res.logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-dim); padding: 24px;">No audit log records found.</td></tr>`;
    return;
  }

  tbody.innerHTML = res.logs.map(l => {
    let deltaPreview = l.new_value_json ? l.new_value_json.substring(0, 45) + '...' : '-';

    return `
      <tr>
        <td>#${l.id}</td>
        <td>${l.created_at}</td>
        <td><strong style="color: var(--primary);">${l.username || 'System'}</strong></td>
        <td><span class="badge" style="background: var(--bg-input); color: var(--text-main); font-weight: 700;">${l.action}</span></td>
        <td>${l.entity}</td>
        <td><code>${l.record_id || '-'}</code></td>
        <td>${l.ip_address || '127.0.0.1'}</td>
        <td><button class="btn btn-secondary" style="padding: 2px 8px; font-size: 10px;" onclick="viewAuditDelta('${encodeURIComponent(l.new_value_json || '{}')}')">Inspect Delta</button></td>
      </tr>
    `;
  }).join('');
}

function viewAuditDelta(encodedJson) {
  const decoded = decodeURIComponent(encodedJson);
  let formatted = decoded;
  try {
    formatted = JSON.stringify(JSON.parse(decoded), null, 2);
  } catch (e) {}

  openModal('Immutable Audit Record JSON Delta', `<pre style="background: var(--bg-input); padding: 16px; border-radius: 8px; font-family: var(--font-mono); font-size: 12px; color: var(--success); overflow-x: auto;">${formatted}</pre>`);
}
