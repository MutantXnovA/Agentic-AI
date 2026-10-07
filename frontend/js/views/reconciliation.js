/* ==========================================================================
   Reconciliation View Renderer (Run Engine & Manual Solver)
   ========================================================================== */

async function renderReconciliationView() {
  const container = document.getElementById('view-content');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Reconciliation Execution Engine</h1>
        <p class="page-subtitle">Multi-pass rule execution engine comparing bank feeds against ledger postings</p>
      </div>
      <div>
        <button class="btn btn-primary" onclick="triggerReconciliationRun()"><i class="fa-solid fa-play"></i> Run Reconciliation Engine</button>
      </div>
    </div>

    <!-- Active Rules Pipeline Card -->
    <div class="table-card" style="padding: 20px; margin-bottom: 20px;">
      <h3 style="margin-bottom: 12px; font-size: 15px;"><i class="fa-solid fa-sliders" style="color: var(--primary);"></i> Active Rule Execution Pipeline</h3>
      <div style="display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px;">
        <div style="background: var(--bg-input); border: 1px solid var(--border-color); padding: 12px; border-radius: 8px; min-width: 220px;">
          <strong style="color: var(--primary);">Pass 1: Rule 1 (Exact)</strong>
          <p style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Txn ID + Amount + Currency</p>
        </div>
        <div style="background: var(--bg-input); border: 1px solid var(--border-color); padding: 12px; border-radius: 8px; min-width: 220px;">
          <strong style="color: var(--primary);">Pass 2: Rule 2 (Ref & Date ±1d)</strong>
          <p style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Normalized Ref + Date ±1 Day</p>
        </div>
        <div style="background: var(--bg-input); border: 1px solid var(--border-color); padding: 12px; border-radius: 8px; min-width: 220px;">
          <strong style="color: var(--primary);">Pass 3: Rule 3 (Fuzzy Match)</strong>
          <p style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Amount ±$0.50 + Counterparty >= 85%</p>
        </div>
        <div style="background: var(--bg-input); border: 1px solid var(--border-color); padding: 12px; border-radius: 8px; min-width: 220px;">
          <strong style="color: var(--warning);">Pass 4: Auto Exception</strong>
          <p style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Unmatched Pool -> Exceptions</p>
        </div>
      </div>
    </div>

    <!-- Reconciliation Results Table -->
    <div class="table-card">
      <div class="table-header-tools">
        <h3>Reconciliation Pairings & Execution History</h3>
        <button class="btn btn-secondary" onclick="openManualMatchModal()"><i class="fa-solid fa-code-merge"></i> Manual Match Solver</button>
      </div>

      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Pair ID</th>
              <th>Source A Txn</th>
              <th>Source B Txn</th>
              <th>Rule Applied</th>
              <th>Match Score</th>
              <th>Amount Diff</th>
              <th>Date Diff</th>
              <th>Status</th>
              <th>Exception</th>
            </tr>
          </thead>
          <tbody id="recon-results-body">
            <tr><td colspan="9" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading Results...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  loadReconciliationResults();
}

async function loadReconciliationResults() {
  const res = await apiRequest('/api/reconciliation/results');
  if (!res) return;

  const tbody = document.getElementById('recon-results-body');
  if (res.results.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-dim); padding: 24px;">No reconciliation pairings generated yet. Click "Run Reconciliation Engine".</td></tr>`;
    return;
  }

  tbody.innerHTML = res.results.map(r => {
    let badge = 'badge-matched';
    if (r.match_status.includes('Missing')) badge = 'badge-unmatched';
    else if (r.match_status.includes('Mismatch')) badge = 'badge-mismatch';

    return `
      <tr>
        <td>#${r.id}</td>
        <td><strong style="color: var(--primary); font-family: var(--font-mono);">${r.source_a_ext_id || 'N/A'}</strong></td>
        <td><strong style="color: var(--info); font-family: var(--font-mono);">${r.source_b_ext_id || 'N/A'}</strong></td>
        <td>${r.rule_name || 'System / Manual'}</td>
        <td><strong style="color: var(--success);">${r.match_score}%</strong></td>
        <td>$${r.amount_diff.toFixed(2)}</td>
        <td>${r.date_diff_days}d</td>
        <td><span class="badge ${badge}">${r.match_status}</span></td>
        <td>${r.exc_code ? `<span class="badge badge-critical">${r.exc_code}</span>` : '-'}</td>
      </tr>
    `;
  }).join('');
}

async function triggerReconciliationRun() {
  showToast('Executing multi-pass matching engine...', 'info');
  const res = await apiRequest('/api/reconciliation/run', 'POST', {});
  if (!res) return;

  const s = res.summary;
  showToast(`Reconciliation Completed: Matched=${s.matched_count}, Partial/Mismatched=${s.partial_count}, Exceptions=${s.exceptions_created}`, 'success');
  renderReconciliationView();
}

function openManualMatchModal() {
  const html = `
    <p style="color: var(--text-muted); margin-bottom: 16px;">Manually pair two unmatched transactions from Source A and Source B.</p>
    <div style="display: flex; flex-direction: column; gap: 12px;">
      <div>
        <label class="filter-label">Source A Transaction ID:</label>
        <input type="number" class="input-control" id="manual-a-id" placeholder="Enter DB ID of Source A txn" style="width: 100%;">
      </div>
      <div>
        <label class="filter-label">Source B Transaction ID:</label>
        <input type="number" class="input-control" id="manual-b-id" placeholder="Enter DB ID of Source B txn" style="width: 100%;">
      </div>
      <div>
        <label class="filter-label">Reason / Justification:</label>
        <input type="text" class="input-control" id="manual-reason" placeholder="e.g. Verified with bank deposit slip" style="width: 100%;">
      </div>
    </div>
  `;

  const footer = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitManualMatch()"><i class="fa-solid fa-check"></i> Confirm Manual Match</button>
  `;

  openModal('Manual Transaction Match Solver', html, footer);
}

async function submitManualMatch() {
  const aId = document.getElementById('manual-a-id').value;
  const bId = document.getElementById('manual-b-id').value;
  const reason = document.getElementById('manual-reason').value;

  if (!aId || !bId) {
    showToast('Please enter both transaction IDs', 'error');
    return;
  }

  const res = await apiRequest('/api/reconciliation/manual-match', 'POST', {
    source_a_id: parseInt(aId),
    source_b_id: parseInt(bId),
    reason: reason
  });

  if (res) {
    showToast('Transactions manually matched successfully', 'success');
    closeModal();
    renderReconciliationView();
  }
}
