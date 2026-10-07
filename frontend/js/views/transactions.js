/* ==========================================================================
   Transactions View Renderer (Advanced Table & Side-by-Side Split View Modal)
   ========================================================================== */

let txnState = { page: 1, limit: 15, search: '', status: '', source_id: '' };

async function renderTransactionsView() {
  const container = document.getElementById('view-content');
  
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Transaction Repository</h1>
        <p class="page-subtitle">Multi-source financial transaction master ledger with side-by-side reconciliation comparison</p>
      </div>
      <div>
        <button class="btn btn-secondary" onclick="exportTransactionsCSV()"><i class="fa-solid fa-download"></i> Export CSV</button>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Search:</span>
        <input type="text" class="input-control" id="txn-search-input" placeholder="Search ID, Ref, Amount..." value="${txnState.search}">
      </div>

      <div class="filter-group">
        <span class="filter-label">Status:</span>
        <select class="select-control" id="txn-status-filter">
          <option value="">All Statuses</option>
          <option value="Matched" ${txnState.status === 'Matched' ? 'selected' : ''}>Matched</option>
          <option value="Unmatched" ${txnState.status === 'Unmatched' ? 'selected' : ''}>Unmatched</option>
          <option value="Amount Mismatch" ${txnState.status === 'Amount Mismatch' ? 'selected' : ''}>Amount Mismatch</option>
          <option value="Date Mismatch" ${txnState.status === 'Date Mismatch' ? 'selected' : ''}>Date Mismatch</option>
          <option value="Pending" ${txnState.status === 'Pending' ? 'selected' : ''}>Pending</option>
        </select>
      </div>

      <button class="btn btn-primary" onclick="applyTxnFilters()"><i class="fa-solid fa-filter"></i> Apply Filters</button>
    </div>

    <!-- Data Table Card -->
    <div class="table-card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th><input type="checkbox"></th>
              <th>Transaction ID</th>
              <th>Date</th>
              <th>Reference Number</th>
              <th>Source</th>
              <th>Amount</th>
              <th>Currency</th>
              <th>Counterparty</th>
              <th>Match Status</th>
              <th>Exception ID</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="txn-table-body">
            <tr><td colspan="11" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading Transactions...</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Controls -->
      <div class="table-header-tools" style="border-top: 1px solid var(--border-color); border-bottom: none;">
        <span id="txn-pagination-info" style="font-size: 13px; color: var(--text-muted);">Showing 0 of 0 records</span>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary" id="btn-txn-prev" onclick="changeTxnPage(-1)"><i class="fa-solid fa-chevron-left"></i> Previous</button>
          <button class="btn btn-secondary" id="btn-txn-next" onclick="changeTxnPage(1)">Next <i class="fa-solid fa-chevron-right"></i></button>
        </div>
      </div>
    </div>
  `;

  loadTransactionsData();
}

async function loadTransactionsData() {
  const query = `page=${txnState.page}&limit=${txnState.limit}&search=${encodeURIComponent(txnState.search)}&status=${txnState.status}`;
  const res = await apiRequest(`/api/transactions?${query}`);
  if (!res) return;

  const tbody = document.getElementById('txn-table-body');
  if (res.transactions.length === 0) {
    tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: var(--text-dim); padding: 30px;">No transactions matching filter criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = res.transactions.map(t => {
    let badgeClass = 'badge-unmatched';
    if (t.status === 'Matched') badgeClass = 'badge-matched';
    else if (t.status.includes('Mismatch')) badgeClass = 'badge-mismatch';

    return `
      <tr>
        <td><input type="checkbox"></td>
        <td><strong style="color: var(--primary); font-family: var(--font-mono);">${t.external_txn_id}</strong></td>
        <td>${t.txn_date.substring(0, 10)}</td>
        <td><code style="font-family: var(--font-mono); color: var(--text-muted);">${t.ref_number || 'N/A'}</code></td>
        <td><span class="badge" style="background: var(--bg-input); color: var(--text-main);">${t.source_name || 'Source'}</span></td>
        <td><strong style="color: var(--text-main); font-family: var(--font-mono);">$${parseFloat(t.amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</strong></td>
        <td>${t.currency}</td>
        <td>${t.counterparty || 'N/A'}</td>
        <td><span class="badge ${badgeClass}">${t.status}</span></td>
        <td>${t.exc_code ? `<span class="badge badge-critical">${t.exc_code}</span>` : '<span style="color: var(--text-dim);">-</span>'}</td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="viewSideBySideComparison(${t.id})">
            <i class="fa-solid fa-columns"></i> Compare
          </button>
        </td>
      </tr>
    `;
  }).join('');

  document.getElementById('txn-pagination-info').innerText = `Showing page ${res.pagination.page} of ${res.pagination.total_pages} (${res.pagination.total} total transactions)`;
}

function applyTxnFilters() {
  txnState.search = document.getElementById('txn-search-input').value.trim();
  txnState.status = document.getElementById('txn-status-filter').value;
  txnState.page = 1;
  loadTransactionsData();
}

function changeTxnPage(delta) {
  txnState.page = Math.max(1, txnState.page + delta);
  loadTransactionsData();
}

// Side-by-Side Comparison Modal (SOURCE A | SOURCE B)
async function viewSideBySideComparison(txnId) {
  openModal('Side-by-Side Transaction Comparison', '<div style="text-align: center; padding: 20px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading pairing details...</div>');

  const res = await apiRequest(`/api/transactions/${txnId}/compare`);
  if (!res) return;

  const a = res.source_a;
  const b = res.source_b;
  const diff = res.diff_analysis || {};

  let bodyHtml = '';

  if (!b) {
    bodyHtml = `
      <div class="split-view">
        <div class="source-panel">
          <h4 style="color: var(--primary); margin-bottom: 12px;"><i class="fa-solid fa-building-columns"></i> SOURCE A: ${a.source_name}</h4>
          <p><strong>Txn ID:</strong> ${a.external_txn_id}</p>
          <p><strong>Ref Number:</strong> ${a.ref_number || 'N/A'}</p>
          <p><strong>Amount:</strong> $${parseFloat(a.amount).toLocaleString(undefined, {minimumFractionDigits: 2})} ${a.currency}</p>
          <p><strong>Date:</strong> ${a.txn_date}</p>
          <p><strong>Counterparty:</strong> ${a.counterparty}</p>
        </div>

        <div class="source-panel" style="border: 2px dashed var(--danger); display: flex; flex-direction: column; align-items: center; justify-content: center;">
          <i class="fa-solid fa-circle-xmark fa-3x" style="color: var(--danger); margin-bottom: 12px;"></i>
          <h4 style="color: var(--danger);">MISSING IN SOURCE B</h4>
          <p style="color: var(--text-muted); font-size: 13px; text-align: center; margin-top: 8px;">No matching transaction paired in counterparty source ledger.</p>
        </div>
      </div>
    `;
  } else {
    bodyHtml = `
      <div style="background: var(--bg-sidebar); padding: 12px; border-radius: 8px; margin-bottom: 16px; border: 1px solid var(--border-color);">
        <div style="display: flex; justify-content: space-between; font-size: 13px;">
          <span>Matched Rule: <strong>${diff.matched_rule_name}</strong></span>
          <span>Match Score: <strong style="color: var(--success);">${diff.match_score}%</strong></span>
        </div>
      </div>

      <div class="split-view">
        <div class="source-panel">
          <h4 style="color: var(--primary); margin-bottom: 12px;"><i class="fa-solid fa-building-columns"></i> SOURCE A: ${a.source_name}</h4>
          <p><strong>Txn ID:</strong> ${a.external_txn_id}</p>
          <p><strong>Ref Number:</strong> ${a.ref_number}</p>
          <p><strong>Amount:</strong> $${parseFloat(a.amount).toLocaleString(undefined, {minimumFractionDigits: 2})} ${a.currency}</p>
          <p><strong>Date:</strong> ${a.txn_date.substring(0, 10)}</p>
          <p><strong>Counterparty:</strong> ${a.counterparty}</p>
        </div>

        <div class="source-panel">
          <h4 style="color: var(--info); margin-bottom: 12px;"><i class="fa-solid fa-book"></i> SOURCE B: ${b.source_name}</h4>
          <p><strong>Txn ID:</strong> ${b.external_txn_id}</p>
          <p><strong>Ref Number:</strong> ${b.ref_number}</p>
          <p><strong>Amount:</strong> ${diff.amount_match ? `$${parseFloat(b.amount).toLocaleString(undefined, {minimumFractionDigits: 2})} ${b.currency}` : `<span class="diff-highlight">$${parseFloat(b.amount).toLocaleString(undefined, {minimumFractionDigits: 2})} (Diff: $${diff.amount_diff})</span>`}</p>
          <p><strong>Date:</strong> ${diff.date_diff_days === 0 ? b.txn_date.substring(0, 10) : `<span class="diff-highlight">${b.txn_date.substring(0, 10)} (${diff.date_diff_days}d diff)</span>`}</p>
          <p><strong>Counterparty:</strong> ${b.counterparty}</p>
        </div>
      </div>
    `;
  }

  openModal(`Side-by-Side Comparison (${a.external_txn_id})`, bodyHtml);
}

function exportTransactionsCSV() {
  window.open('/api/reports/export?type=transactions', '_blank');
}
