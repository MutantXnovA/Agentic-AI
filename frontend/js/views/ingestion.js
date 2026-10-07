/* ==========================================================================
   Data Ingestion View Renderer (4-Step Upload & Column Mapper Wizard)
   ========================================================================== */

let ingestionWizardState = {
  step: 1,
  temp_file_path: '',
  filename: '',
  headers: [],
  sample_rows: [],
  mapping: {}
};

function renderIngestionView() {
  const container = document.getElementById('view-content');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Data Ingestion Wizard</h1>
        <p class="page-subtitle">Import bank feeds, payment gateway settlements, and ledger CSVs with column mapping and validation</p>
      </div>
    </div>

    <!-- Wizard Stepper Header -->
    <div style="display: flex; justify-content: space-around; background: var(--bg-card); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); margin-bottom: 20px;">
      <div id="step-pill-1" style="font-weight: 700; color: var(--primary);"><i class="fa-solid fa-circle-1"></i> 1. File Upload</div>
      <div id="step-pill-2" style="color: var(--text-dim);"><i class="fa-solid fa-circle-2"></i> 2. Source Selection</div>
      <div id="step-pill-3" style="color: var(--text-dim);"><i class="fa-solid fa-circle-3"></i> 3. Column Mapping</div>
      <div id="step-pill-4" style="color: var(--text-dim);"><i class="fa-solid fa-circle-4"></i> 4. Validation Summary</div>
    </div>

    <div class="table-card" id="wizard-body-card" style="padding: 24px;">
      <!-- Step 1 Content default -->
      ${renderWizardStep1()}
    </div>
  `;
}

function renderWizardStep1() {
  return `
    <div style="text-align: center; padding: 40px; border: 2px dashed var(--border-color); border-radius: 12px; background: var(--bg-input);" id="drop-zone">
      <i class="fa-solid fa-cloud-arrow-up fa-3x" style="color: var(--primary); margin-bottom: 16px;"></i>
      <h3>Drag & Drop Financial CSV / Excel File</h3>
      <p style="color: var(--text-muted); margin: 8px 0 20px 0;">Supports bank statements, Stripe settlement exports, NetSuite journal feeds (.csv, .json)</p>
      <input type="file" id="file-input" style="display: none;" onchange="handleFileSelected(this.files[0])">
      <button class="btn btn-primary" onclick="document.getElementById('file-input').click()"><i class="fa-solid fa-folder-open"></i> Browse Files</button>
    </div>
  `;
}

async function handleFileSelected(file) {
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  showToast('Uploading file for preview structure...', 'info');

  try {
    const res = await fetch('/api/ingestion/preview', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${state.token}` },
      body: formData
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error);

    ingestionWizardState.temp_file_path = json.temp_file_path;
    ingestionWizardState.filename = json.filename;
    ingestionWizardState.headers = json.headers;
    ingestionWizardState.sample_rows = json.sample_rows;

    ingestionWizardState.step = 2;
    renderWizardStep2();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderWizardStep2() {
  document.getElementById('step-pill-2').style.fontWeight = '700';
  document.getElementById('step-pill-2').style.color = 'var(--primary)';

  const card = document.getElementById('wizard-body-card');
  card.innerHTML = `
    <h3 style="margin-bottom: 16px;">Step 2: Select Ingestion Source & Account</h3>
    <div style="display: flex; flex-direction: column; gap: 16px; max-width: 500px;">
      <div>
        <label class="filter-label" style="display: block; margin-bottom: 6px;">Target Data Source System:</label>
        <select class="select-control" id="ingest-source-select" style="width: 100%;">
          <option value="1">SRC-BANK-STMT (Bank Statement Feed)</option>
          <option value="2">SRC-INTERNAL-LEDGER (ERP General Ledger)</option>
          <option value="3">SRC-STRIPE-PG (Stripe Payment Gateway)</option>
          <option value="4">SRC-RAZORPAY-PG (Razorpay Payment Gateway)</option>
        </select>
      </div>

      <div>
        <label class="filter-label" style="display: block; margin-bottom: 6px;">Target Account & Entity:</label>
        <select class="select-control" id="ingest-account-select" style="width: 100%;">
          <option value="1">ACC-CHASE-9941 - Chase Merchant Primary USD (Acme US)</option>
          <option value="2">ACC-STRIPE-8812 - Stripe Gateway Operating USD (Acme US)</option>
          <option value="3">ACC-HDFC-4410 - HDFC Merchant Escrow INR (Acme India)</option>
        </select>
      </div>

      <div style="margin-top: 20px; display: flex; gap: 12px;">
        <button class="btn btn-primary" onclick="proceedToStep3()"><i class="fa-solid fa-arrow-right"></i> Continue to Mapping</button>
      </div>
    </div>
  `;
}

function proceedToStep3() {
  ingestionWizardState.source_id = document.getElementById('ingest-source-select').value;
  ingestionWizardState.account_id = document.getElementById('ingest-account-select').value;
  ingestionWizardState.step = 3;
  renderWizardStep3();
}

function renderWizardStep3() {
  document.getElementById('step-pill-3').style.fontWeight = '700';
  document.getElementById('step-pill-3').style.color = 'var(--primary)';

  const headers = ingestionWizardState.headers;
  const options = headers.map(h => `<option value="${h}">${h}</option>`).join('');

  const card = document.getElementById('wizard-body-card');
  card.innerHTML = `
    <h3 style="margin-bottom: 16px;">Step 3: Map Field Columns</h3>
    <p style="color: var(--text-muted); margin-bottom: 20px;">Map CSV column headers to ReconX standardized transaction fields.</p>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; max-width: 700px;">
      <div>
        <label class="filter-label">Transaction ID (Mandatory):</label>
        <select class="select-control" id="map-ext-id" style="width: 100%;">${options}</select>
      </div>

      <div>
        <label class="filter-label">Reference Number / UTR:</label>
        <select class="select-control" id="map-ref-num" style="width: 100%;">${options}</select>
      </div>

      <div>
        <label class="filter-label">Transaction Date (Mandatory):</label>
        <select class="select-control" id="map-date" style="width: 100%;">${options}</select>
      </div>

      <div>
        <label class="filter-label">Amount (Mandatory):</label>
        <select class="select-control" id="map-amount" style="width: 100%;">${options}</select>
      </div>

      <div>
        <label class="filter-label">Currency:</label>
        <select class="select-control" id="map-currency" style="width: 100%;">${options}</select>
      </div>

      <div>
        <label class="filter-label">Counterparty Name:</label>
        <select class="select-control" id="map-counterparty" style="width: 100%;">${options}</select>
      </div>
    </div>

    <div style="margin-top: 24px;">
      <button class="btn btn-primary" onclick="confirmImportExecution()"><i class="fa-solid fa-play"></i> Validate & Import Batch</button>
    </div>
  `;
}

async function confirmImportExecution() {
  const mapping = {
    external_txn_id: document.getElementById('map-ext-id').value,
    ref_number: document.getElementById('map-ref-num').value,
    txn_date: document.getElementById('map-date').value,
    amount: document.getElementById('map-amount').value,
    currency: document.getElementById('map-currency').value,
    counterparty: document.getElementById('map-counterparty').value
  };

  showToast('Processing import validation...', 'info');

  const res = await apiRequest('/api/ingestion/confirm', 'POST', {
    temp_file_path: ingestionWizardState.temp_file_path,
    source_id: ingestionWizardState.source_id,
    account_id: ingestionWizardState.account_id,
    entity_id: 1,
    mapping: mapping
  });

  if (!res) return;

  const s = res.summary;
  const card = document.getElementById('wizard-body-card');

  document.getElementById('step-pill-4').style.fontWeight = '700';
  document.getElementById('step-pill-4').style.color = 'var(--success)';

  card.innerHTML = `
    <div style="text-align: center; margin-bottom: 24px;">
      <i class="fa-solid fa-circle-check fa-3x" style="color: var(--success); margin-bottom: 12px;"></i>
      <h2>Batch Import Completed: ${s.batch_code}</h2>
    </div>

    <div class="kpi-grid" style="margin-bottom: 24px;">
      <div class="kpi-card kpi-info">
        <div class="kpi-header"><span>Received</span></div>
        <div class="kpi-value">${s.records_received}</div>
      </div>
      <div class="kpi-card kpi-success">
        <div class="kpi-header"><span>Accepted</span></div>
        <div class="kpi-value" style="color: var(--success);">${s.records_accepted}</div>
      </div>
      <div class="kpi-card kpi-danger">
        <div class="kpi-header"><span>Rejected</span></div>
        <div class="kpi-value" style="color: var(--danger);">${s.records_rejected}</div>
      </div>
      <div class="kpi-card kpi-warning">
        <div class="kpi-header"><span>Duplicates</span></div>
        <div class="kpi-value">${s.duplicate_records}</div>
      </div>
    </div>

    <div style="display: flex; gap: 12px; justify-content: center;">
      <button class="btn btn-primary" onclick="navigateTo('reconciliation')"><i class="fa-solid fa-code-compare"></i> Run Reconciliation Engine</button>
      <button class="btn btn-secondary" onclick="renderIngestionView()"><i class="fa-solid fa-upload"></i> Import Another File</button>
    </div>
  `;

  showToast('Import batch completed successfully', 'success');
}
