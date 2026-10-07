/* ==========================================================================
   Settings & SLA Policy Configuration View Renderer
   ========================================================================== */

async function renderSettingsView() {
  const container = document.getElementById('view-content');

  const res = await apiRequest('/api/sla/rules');
  const rules = res ? res.sla_rules : [];

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">System Settings & SLA Policies</h1>
        <p class="page-subtitle">Configure SLA resolution windows, escalation emails, and financial tolerances</p>
      </div>
    </div>

    <!-- SLA Config Table Card -->
    <div class="table-card" style="margin-bottom: 24px;">
      <div class="table-header-tools">
        <h3><i class="fa-solid fa-clock" style="color: var(--primary);"></i> Service Level Agreement (SLA) Resolution Targets</h3>
      </div>
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Priority Level</th>
              <th>Target Resolution Hours</th>
              <th>Warning Hours</th>
              <th>Escalation Email Target</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${rules.map(r => `
              <tr>
                <td><span class="badge badge-${r.priority.toLowerCase()}">${r.priority}</span></td>
                <td><strong>${r.allowed_hours} Hours</strong> (${(r.allowed_hours / 24).toFixed(1)} days)</td>
                <td>${r.warning_hours} Hours</td>
                <td><code>${r.escalation_email}</code></td>
                <td><span class="badge badge-matched">${r.is_active ? 'Active' : 'Disabled'}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <!-- System Info Card -->
    <div class="table-card" style="padding: 20px;">
      <h3 style="margin-bottom: 12px;"><i class="fa-solid fa-server"></i> FinTech Engine Health & Environment</h3>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 13px;">
        <div><strong>Reconciliation Engine:</strong> <span style="color: var(--success);">Multi-pass Deterministic v3.4</span></div>
        <div><strong>Database Engine:</strong> <span style="color: var(--primary);">SQLite Relational (Normalized 3NF)</span></div>
        <div><strong>AI Assistant Model:</strong> <span style="color: var(--info);">FinAI-Recon-v3.4 (Rule-Guided)</span></div>
        <div><strong>Security:</strong> <span style="color: var(--success);">Salted SHA-256 + JWT HS256 RBAC</span></div>
      </div>
    </div>
  `;
}
