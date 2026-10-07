/* ==========================================================================
   Match Rules Builder View Renderer
   ========================================================================== */

async function renderRulesView() {
  const container = document.getElementById('view-content');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Matching Rule Engine Configurator</h1>
        <p class="page-subtitle">Define deterministic matching rules, Priorities 1-N, date/amount tolerances, and fuzzy thresholds</p>
      </div>
      <div>
        <button class="btn btn-primary" onclick="openCreateRuleModal()"><i class="fa-solid fa-plus"></i> Create New Rule</button>
      </div>
    </div>

    <!-- Rules List Table -->
    <div class="table-card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Priority</th>
              <th>Rule Name</th>
              <th>Matching Fields</th>
              <th>Date Tolerance</th>
              <th>Amount Tolerance</th>
              <th>Fuzzy Threshold</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="rules-table-body">
            <tr><td colspan="8" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading Rules Pipeline...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  loadRulesPipeline();
}

async function loadRulesPipeline() {
  const res = await apiRequest('/api/rules');
  if (!res) return;

  const tbody = document.getElementById('rules-table-body');
  tbody.innerHTML = res.rules.map(r => {
    const fieldsArr = Array.isArray(r.match_fields) ? r.match_fields : JSON.parse(r.match_fields || '[]');
    const fieldsBadges = fieldsArr.map(f => `<span class="badge" style="background: var(--primary-glow); color: var(--primary); margin-right: 4px;">${f}</span>`).join('');

    return `
      <tr>
        <td><strong style="color: var(--primary); font-size: 16px;">Rule ${r.priority}</strong></td>
        <td><strong>${r.rule_name}</strong><br><span style="font-size: 11px; color: var(--text-dim);">${r.description || ''}</span></td>
        <td>${fieldsBadges}</td>
        <td>±${r.date_tolerance_days} Days</td>
        <td>$${r.amount_tolerance.toFixed(2)}</td>
        <td>${r.fuzzy_threshold}%</td>
        <td><span class="badge ${r.is_active ? 'badge-matched' : 'badge-unmatched'}">${r.is_active ? 'Active' : 'Disabled'}</span></td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="toggleRuleActive(${r.id}, ${r.is_active ? 0 : 1})">
            ${r.is_active ? 'Disable' : 'Enable'}
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

async function toggleRuleActive(ruleId, newActiveState) {
  const res = await apiRequest(`/api/rules/${ruleId}`, 'PUT', { is_active: newActiveState });
  if (res) {
    showToast('Rule status updated successfully', 'success');
    loadRulesPipeline();
  }
}

function openCreateRuleModal() {
  const html = `
    <div style="display: flex; flex-direction: column; gap: 12px;">
      <div>
        <label class="filter-label">Rule Name:</label>
        <input type="text" class="input-control" id="rule-name-input" placeholder="e.g. Rule 5: Reference + Date ±2 Days" style="width: 100%;">
      </div>

      <div>
        <label class="filter-label">Execution Priority (1 = Highest):</label>
        <input type="number" class="input-control" id="rule-prio-input" value="5" style="width: 100%;">
      </div>

      <div>
        <label class="filter-label">Matching Fields (Select fields that must match):</label>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px;">
          <label><input type="checkbox" id="chk-ext-id" value="external_txn_id"> Transaction ID</label>
          <label><input type="checkbox" id="chk-ref" value="ref_number" checked> Reference Number</label>
          <label><input type="checkbox" id="chk-amount" value="amount" checked> Amount</label>
          <label><input type="checkbox" id="chk-date" value="txn_date" checked> Transaction Date</label>
          <label><input type="checkbox" id="chk-counterparty" value="counterparty"> Counterparty Name</label>
        </div>
      </div>

      <div>
        <label class="filter-label">Date Tolerance (Days):</label>
        <select class="select-control" id="rule-date-tol" style="width: 100%;">
          <option value="0">0 Days (Exact Date)</option>
          <option value="1">±1 Day</option>
          <option value="2">±2 Days</option>
          <option value="3">±3 Days</option>
        </select>
      </div>

      <div>
        <label class="filter-label">Amount Tolerance ($):</label>
        <input type="number" step="0.1" class="input-control" id="rule-amount-tol" value="0.0" style="width: 100%;">
      </div>
    </div>
  `;

  const footer = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitCreateRule()"><i class="fa-solid fa-save"></i> Save Rule</button>
  `;

  openModal('Create New Reconciliation Rule', html, footer);
}

async function submitCreateRule() {
  const name = document.getElementById('rule-name-input').value;
  const prio = parseInt(document.getElementById('rule-prio-input').value);
  const dateTol = parseInt(document.getElementById('rule-date-tol').value);
  const amountTol = parseFloat(document.getElementById('rule-amount-tol').value);

  const fields = [];
  if (document.getElementById('chk-ext-id').checked) fields.push('external_txn_id');
  if (document.getElementById('chk-ref').checked) fields.push('ref_number');
  if (document.getElementById('chk-amount').checked) fields.push('amount');
  if (document.getElementById('chk-date').checked) fields.push('txn_date');
  if (document.getElementById('chk-counterparty').checked) fields.push('counterparty');

  if (!name || fields.length === 0) {
    showToast('Rule name and at least one matching field are required.', 'error');
    return;
  }

  const res = await apiRequest('/api/rules', 'POST', {
    rule_name: name,
    priority: prio,
    match_fields: fields,
    date_tolerance_days: dateTol,
    amount_tolerance: amountTol
  });

  if (res) {
    showToast('Matching rule saved successfully', 'success');
    closeModal();
    renderRulesView();
  }
}
