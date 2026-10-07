/* ==========================================================================
   Dashboard View Renderer (KPI Cards + SVG Interactive Charts)
   ========================================================================== */

async function renderDashboardView() {
  const container = document.getElementById('view-content');
  container.innerHTML = `<div style="padding: 20px; text-align: center;"><i class="fa-solid fa-spinner fa-spin fa-2x"></i> Loading Financial Dashboard...</div>`;

  const res = await apiRequest('/api/reports/dashboard');
  if (!res) return;

  const kpis = res.kpis;
  const charts = res.charts;

  container.innerHTML = `
    <!-- Page Title & Date Filter Bar -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Financial Reconciliation Overview</h1>
        <p class="page-subtitle">Real-time settlement visibility, exception tracking, and matching performance</p>
      </div>
      <div class="filter-group">
        <select class="select-control" id="dash-date-filter">
          <option value="today">Today</option>
          <option value="last_7_days" selected>Last 7 Days</option>
          <option value="last_30_days">Last 30 Days</option>
          <option value="current_month">Current Month</option>
        </select>
        <button class="btn btn-secondary" onclick="renderDashboardView()"><i class="fa-solid fa-arrows-rotate"></i> Refresh</button>
      </div>
    </div>

    <!-- 9 Enterprise KPI Cards -->
    <div class="kpi-grid">
      <div class="kpi-card kpi-info">
        <div class="kpi-header">
          <span>Total Volume</span>
          <i class="fa-solid fa-receipt"></i>
        </div>
        <div class="kpi-value">${kpis.total_transactions.toLocaleString()}</div>
        <div class="kpi-subtext">Value: $${kpis.total_transaction_value.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
      </div>

      <div class="kpi-card kpi-success">
        <div class="kpi-header">
          <span>Reconciled</span>
          <i class="fa-solid fa-circle-check"></i>
        </div>
        <div class="kpi-value">${kpis.matched_transactions.toLocaleString()}</div>
        <div class="kpi-subtext">Success Rate: <strong style="color: var(--success);">${kpis.reconciliation_rate}%</strong></div>
      </div>

      <div class="kpi-card kpi-danger">
        <div class="kpi-header">
          <span>Unmatched</span>
          <i class="fa-solid fa-circle-xmark"></i>
        </div>
        <div class="kpi-value">${kpis.unmatched_transactions.toLocaleString()}</div>
        <div class="kpi-subtext">Discrepancy pool</div>
      </div>

      <div class="kpi-card kpi-warning">
        <div class="kpi-header">
          <span>Total Exceptions</span>
          <i class="fa-solid fa-triangle-exclamation"></i>
        </div>
        <div class="kpi-value">${kpis.total_exceptions}</div>
        <div class="kpi-subtext">Open: ${kpis.open_exceptions} | Resolved: ${kpis.resolved_exceptions}</div>
      </div>

      <div class="kpi-card kpi-danger">
        <div class="kpi-header">
          <span>Critical Exceptions</span>
          <i class="fa-solid fa-fire-flame-curved"></i>
        </div>
        <div class="kpi-value" style="color: var(--danger);">${kpis.critical_exceptions}</div>
        <div class="kpi-subtext">Requires immediate manager sign-off</div>
      </div>
    </div>

    <!-- Interactive SVG Charts Grid -->
    <div class="charts-grid">
      
      <!-- Chart 1: Reconciliation Status Donut Chart -->
      <div class="chart-card">
        <div class="chart-title"><i class="fa-solid fa-chart-pie" style="color: var(--primary);"></i> Reconciliation Status Breakdown</div>
        <div class="chart-container" id="svg-donut-container"></div>
      </div>

      <!-- Chart 2: Exception Ageing Stacked Bar Chart -->
      <div class="chart-card">
        <div class="chart-title"><i class="fa-solid fa-clock" style="color: var(--warning);"></i> Exception Ageing Buckets (Days)</div>
        <div class="chart-container" id="svg-ageing-container"></div>
      </div>

      <!-- Chart 3: Exception Priority Distribution -->
      <div class="chart-card">
        <div class="chart-title"><i class="fa-solid fa-layer-group" style="color: var(--danger);"></i> Open Exceptions by Priority</div>
        <div class="chart-container" id="svg-priority-container"></div>
      </div>

      <!-- Chart 4: Exceptions by Assigned Owner -->
      <div class="chart-card">
        <div class="chart-title"><i class="fa-solid fa-user-gear" style="color: var(--info);"></i> Workload Distribution by Owner</div>
        <div class="chart-container" id="svg-owner-container"></div>
      </div>

    </div>
  `;

  // Draw Charts
  drawDonutChart(charts.reconciliation_status);
  drawBarChart('svg-ageing-container', charts.ageing_buckets, 'bucket', 'count', ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']);
  drawBarChart('svg-priority-container', charts.priority_breakdown, 'priority', 'count', ['#ef4444', '#f97316', '#f59e0b', '#3b82f6']);
  drawHorizontalBarChart('svg-owner-container', charts.owner_breakdown);
  
  // Update sidebar exception badge
  document.getElementById('sidebar-open-exc-count').innerText = kpis.open_exceptions;
}

// Donut Chart Generator
function drawDonutChart(data) {
  const container = document.getElementById('svg-donut-container');
  if (!data || data.length === 0) {
    container.innerHTML = `<span style="color: var(--text-dim);">No data available</span>`;
    return;
  }

  const total = data.reduce((sum, d) => sum + d.count, 0) || 1;
  const colors = ['#10b981', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6'];
  let currentAngle = 0;

  let slices = '';
  let legendHtml = '<div style="display: flex; flex-direction: column; gap: 8px; margin-left: 20px;">';

  data.forEach((d, idx) => {
    const color = colors[idx % colors.length];
    const percentage = (d.count / total) * 100;
    const angle = (d.count / total) * 360;

    const x1 = 100 + 70 * Math.cos(Math.PI * currentAngle / 180);
    const y1 = 100 + 70 * Math.sin(Math.PI * currentAngle / 180);

    const endAngle = currentAngle + angle;
    const x2 = 100 + 70 * Math.cos(Math.PI * endAngle / 180);
    const y2 = 100 + 70 * Math.sin(Math.PI * endAngle / 180);

    const largeArc = angle > 180 ? 1 : 0;
    const pathData = `M 100 100 L ${x1} ${y1} A 70 70 0 ${largeArc} 1 ${x2} ${y2} Z`;

    slices += `<path d="${pathData}" fill="${color}" opacity="0.9"></path>`;
    legendHtml += `
      <div style="display: flex; align-items: center; gap: 8px; font-size: 12px;">
        <span style="width: 10px; height: 10px; background: ${color}; border-radius: 2px;"></span>
        <span style="color: var(--text-muted);">${d.match_status}:</span>
        <strong style="color: var(--text-main);">${d.count} (${percentage.toFixed(1)}%)</strong>
      </div>
    `;
    currentAngle = endAngle;
  });

  legendHtml += '</div>';

  container.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: center; width: 100%;">
      <svg width="180" height="180" viewBox="0 0 200 200">
        ${slices}
        <circle cx="100" cy="100" r="40" fill="var(--bg-card)" />
      </svg>
      ${legendHtml}
    </div>
  `;
}

// Vertical Bar Chart Generator
function drawBarChart(elementId, data, labelKey, valueKey, colors) {
  const container = document.getElementById(elementId);
  if (!data || data.length === 0) {
    container.innerHTML = `<span style="color: var(--text-dim);">No data available</span>`;
    return;
  }

  const maxVal = Math.max(...data.map(d => d[valueKey])) || 1;

  let barsHtml = `<div style="display: flex; align-items: flex-end; justify-content: space-around; height: 180px; width: 100%; padding-bottom: 24px;">`;

  data.forEach((d, idx) => {
    const val = d[valueKey];
    const heightPercent = Math.max(10, (val / maxVal) * 100);
    const color = colors[idx % colors.length];

    barsHtml += `
      <div style="display: flex; flex-direction: column; align-items: center; gap: 6px; flex: 1;">
        <span style="font-size: 11px; font-weight: 700; color: var(--text-main);">${val}</span>
        <div style="width: 28px; height: ${heightPercent}%; background: ${color}; border-radius: 4px 4px 0 0; transition: height 0.3s ease;"></div>
        <span style="font-size: 11px; color: var(--text-muted); text-align: center; white-space: nowrap;">${d[labelKey]}</span>
      </div>
    `;
  });

  barsHtml += `</div>`;
  container.innerHTML = barsHtml;
}

// Horizontal Bar Chart Generator
function drawHorizontalBarChart(elementId, data) {
  const container = document.getElementById(elementId);
  if (!data || data.length === 0) {
    container.innerHTML = `<span style="color: var(--text-dim);">No data available</span>`;
    return;
  }

  const maxVal = Math.max(...data.map(d => d.count)) || 1;
  let rowsHtml = `<div style="display: flex; flex-direction: column; gap: 12px; width: 100%;">`;

  data.forEach(d => {
    const widthPercent = (d.count / maxVal) * 100;
    rowsHtml += `
      <div style="display: flex; flex-direction: column; gap: 4px;">
        <div style="display: flex; justify-content: space-between; font-size: 12px;">
          <span style="color: var(--text-main); font-weight: 600;">${d.owner_name}</span>
          <span style="color: var(--primary); font-weight: 700;">${d.count} exceptions</span>
        </div>
        <div style="width: 100%; background: var(--bg-input); height: 8px; border-radius: 4px; overflow: hidden;">
          <div style="width: ${widthPercent}%; background: var(--primary); height: 100%; border-radius: 4px;"></div>
        </div>
      </div>
    `;
  });

  rowsHtml += `</div>`;
  container.innerHTML = rowsHtml;
}
