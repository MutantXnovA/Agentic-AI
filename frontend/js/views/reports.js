/* ==========================================================================
   Financial & Reconciliation Reports View Renderer
   ========================================================================== */

async function renderReportsView() {
  const container = document.getElementById('view-content');

  container.innerHTML = `<div style="padding: 20px; text-align: center;"><i class="fa-solid fa-spinner fa-spin"></i> Loading Financial Impact & Executive Reports...</div>`;

  const impact = await apiRequest('/api/reports/financial-impact');
  if (!impact) return;

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Executive Financial & Audit Reports</h1>
        <p class="page-subtitle">Discrepancy valuation, recovered monetary amounts, bank fee write-offs, and auditor compliance tracking</p>
      </div>
      <div>
        <button class="btn btn-primary" onclick="exportReport('exceptions')"><i class="fa-solid fa-file-csv"></i> Export Exceptions Report</button>
      </div>
    </div>

    <!-- Financial Impact Overview KPI Grid -->
    <div class="kpi-grid" style="margin-bottom: 24px;">
      <div class="kpi-card kpi-warning">
        <div class="kpi-header"><span>Total Discrepancy Value</span></div>
        <div class="kpi-value" style="color: var(--warning);">$${impact.total_discrepancy_value.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
        <div class="kpi-subtext">Sum of all exception amounts</div>
      </div>

      <div class="kpi-card kpi-success">
        <div class="kpi-header"><span>Recovered Monetary Value</span></div>
        <div class="kpi-value" style="color: var(--success);">$${impact.recovered_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
        <div class="kpi-subtext">Successfully reconciled & closed</div>
      </div>

      <div class="kpi-card kpi-danger">
        <div class="kpi-header"><span>Outstanding Risk Value</span></div>
        <div class="kpi-value" style="color: var(--danger);">$${impact.outstanding_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
        <div class="kpi-subtext">Active open exceptions pool</div>
      </div>

      <div class="kpi-card kpi-info">
        <div class="kpi-header"><span>Bank Fee Write-offs</span></div>
        <div class="kpi-value" style="color: var(--info);">$${impact.writeoffs_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
        <div class="kpi-subtext">Approved fee discrepancy write-offs</div>
      </div>
    </div>

    <!-- 5 Preset Report Cards -->
    <div class="charts-grid">
      
      <div class="chart-card">
        <div class="chart-title"><i class="fa-solid fa-file-contract" style="color: var(--primary);"></i> 1. Reconciliation Success Rate Report</div>
        <p style="font-size: 13px; color: var(--text-muted);">Detailed audit breakdown of matched, partially matched, and missing transactions across all sources.</p>
        <button class="btn btn-secondary" onclick="exportReport('transactions')"><i class="fa-solid fa-download"></i> Download Report CSV</button>
      </div>

      <div class="chart-card">
        <div class="chart-title"><i class="fa-solid fa-shield-cat" style="color: var(--warning);"></i> 2. Exception Ageing & SLA Breaches</div>
        <p style="font-size: 13px; color: var(--text-muted);">Ageing bucket analysis (0-1d, 2-3d, 4-7d, 8-15d, 16-30d, 30+d) and SLA compliance rate.</p>
        <button class="btn btn-secondary" onclick="exportReport('exceptions')"><i class="fa-solid fa-download"></i> Download Report CSV</button>
      </div>

      <div class="chart-card">
        <div class="chart-title"><i class="fa-solid fa-users-gear" style="color: var(--info);"></i> 3. Analyst Performance & Resolution Speed</div>
        <p style="font-size: 13px; color: var(--text-muted);">Tracks individual analyst workload, average resolution time, and manager sign-off latency.</p>
        <button class="btn btn-secondary" onclick="exportReport('exceptions')"><i class="fa-solid fa-download"></i> Download Report CSV</button>
      </div>

      <div class="chart-card">
        <div class="chart-title"><i class="fa-solid fa-vault" style="color: var(--success);"></i> 4. Financial Impact & Write-off Audit</div>
        <p style="font-size: 13px; color: var(--text-muted);">Summary of monetary discrepancies resolved via ledger adjustments vs bank fee write-offs.</p>
        <button class="btn btn-secondary" onclick="exportReport('exceptions')"><i class="fa-solid fa-download"></i> Download Report CSV</button>
      </div>

    </div>
  `;
}

function exportReport(reportType) {
  window.open(`/api/reports/export?type=${reportType}`, '_blank');
}
