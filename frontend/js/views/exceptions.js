/* ==========================================================================
   Exception Management View Renderer (Queue, Detail Drawer, AI Recommendations)
   ========================================================================== */

let excState = { page: 1, limit: 15, filter: '', search: '' };

async function renderExceptionsView() {
  const container = document.getElementById('view-content');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Exception Management Center</h1>
        <p class="page-subtitle">Track, investigate, assign, and resolve settlement discrepancies with automated SLA & AI recommendations</p>
      </div>
    </div>

    <!-- Quick Filter Tabs -->
    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;">
      <button class="btn ${excState.filter === '' ? 'btn-primary' : 'btn-secondary'}" onclick="setExcFilter('')">All Exceptions</button>
      <button class="btn ${excState.filter === 'my_exceptions' ? 'btn-primary' : 'btn-secondary'}" onclick="setExcFilter('my_exceptions')"><i class="fa-solid fa-user"></i> My Assigned</button>
      <button class="btn ${excState.filter === 'critical' ? 'btn-danger' : 'btn-secondary'}" onclick="setExcFilter('critical')"><i class="fa-solid fa-fire"></i> Critical (${document.getElementById('sidebar-open-exc-count')?.innerText || 0})</button>
      <button class="btn ${excState.filter === 'sla_breached' ? 'btn-danger' : 'btn-secondary'}" onclick="setExcFilter('sla_breached')"><i class="fa-solid fa-clock-rotate-left"></i> SLA Breached</button>
      <button class="btn ${excState.filter === 'pending_approval' ? 'btn-primary' : 'btn-secondary'}" onclick="setExcFilter('pending_approval')"><i class="fa-solid fa-user-check"></i> Pending Manager Approval</button>
    </div>

    <!-- Exception Table Card -->
    <div class="table-card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Exception Code</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Assigned Owner</th>
              <th>Ageing</th>
              <th>SLA Due</th>
              <th>SLA Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="exc-table-body">
            <tr><td colspan="10" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading Exceptions Queue...</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="table-header-tools" style="border-top: 1px solid var(--border-color); border-bottom: none;">
        <span id="exc-pagination-info" style="font-size: 13px; color: var(--text-muted);">Showing 0 exceptions</span>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary" onclick="changeExcPage(-1)"><i class="fa-solid fa-chevron-left"></i> Prev</button>
          <button class="btn btn-secondary" onclick="changeExcPage(1)">Next <i class="fa-solid fa-chevron-right"></i></button>
        </div>
      </div>
    </div>
  `;

  loadExceptionsQueue();
}

async function loadExceptionsQueue() {
  const query = `page=${excState.page}&limit=${excState.limit}&filter=${excState.filter}&search=${encodeURIComponent(excState.search)}`;
  const res = await apiRequest(`/api/exceptions?${query}`);
  if (!res) return;

  const tbody = document.getElementById('exc-table-body');
  if (res.exceptions.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-dim); padding: 24px;">No exceptions matching current filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = res.exceptions.map(e => {
    let prioClass = `badge-${e.priority.toLowerCase()}`;
    let slaClass = 'badge-sla-ok';
    if (e.sla_status === 'SLA Breached') slaClass = 'badge-sla-breached';
    else if (e.sla_status === 'At Risk') slaClass = 'badge-sla-risk';

    return `
      <tr>
        <td><strong style="color: var(--primary); font-family: var(--font-mono);">${e.exception_code}</strong></td>
        <td>${e.exception_type}</td>
        <td><strong style="font-family: var(--font-mono);">$${parseFloat(e.amount).toLocaleString(undefined, {minimumFractionDigits: 2})} ${e.currency}</strong></td>
        <td><span class="badge ${prioClass}">${e.priority}</span></td>
        <td><span class="badge" style="background: var(--bg-input); color: var(--text-main);">${e.status}</span></td>
        <td>${e.owner_name || '<span style="color: var(--text-dim);">Unassigned</span>'}</td>
        <td>${e.ageing_bucket}</td>
        <td>${e.due_date ? e.due_date.substring(0, 16) : 'N/A'}</td>
        <td><span class="badge ${slaClass}">${e.sla_status}</span></td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="viewExceptionDetail(${e.id})">
            <i class="fa-solid fa-folder-open"></i> Inspect & Resolve
          </button>
        </td>
      </tr>
    `;
  }).join('');

  document.getElementById('exc-pagination-info').innerText = `Showing page ${res.pagination.page} of ${res.pagination.total_pages} (${res.pagination.total} total exceptions)`;
}

function setExcFilter(filterName) {
  excState.filter = filterName;
  excState.page = 1;
  renderExceptionsView();
}

function changeExcPage(delta) {
  excState.page = Math.max(1, excState.page + delta);
  loadExceptionsQueue();
}

// Exception Detail Drawer & AI Root Cause Recommendation Modal
async function viewExceptionDetail(excId) {
  openModal('Exception Investigation & AI Assistant', '<div style="text-align: center; padding: 20px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading exception drawer...</div>');

  const res = await apiRequest(`/api/exceptions/${excId}`);
  if (!res) return;

  const e = res.exception;
  const comments = res.comments || [];
  const ai = res.ai_recommendation || {};

  const bodyHtml = `
    <!-- Top Metadata Card -->
    <div style="background: var(--bg-sidebar); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h3 style="color: var(--primary); font-family: var(--font-mono);">${e.exception_code}</h3>
        <div>
          <span class="badge badge-${e.priority.toLowerCase()}">${e.priority} Priority</span>
          <span class="badge" style="background: var(--bg-input); color: var(--text-main); margin-left: 6px;">${e.status}</span>
        </div>
      </div>
      <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 8px;">${e.description}</p>
      <div style="display: flex; gap: 20px; font-size: 12px; color: var(--text-muted);">
        <span>Discrepancy Amount: <strong style="color: var(--text-main);">$${parseFloat(e.amount).toLocaleString(undefined, {minimumFractionDigits: 2})} ${e.currency}</strong></span>
        <span>Ageing: <strong>${e.ageing_bucket}</strong></span>
        <span>SLA Status: <strong style="color: ${e.sla_status === 'SLA Breached' ? 'var(--danger)' : 'var(--success)'};">${e.sla_status}</strong></span>
      </div>
    </div>

    <!-- AI Recommendation Box -->
    <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.15)); border: 1px solid var(--primary); border-radius: var(--radius-md); padding: 16px; margin-bottom: 20px;">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; color: var(--primary); font-weight: 700;">
        <i class="fa-solid fa-wand-magic-sparkles"></i> AI Root Cause & Resolution Recommendation
        <span style="font-size: 10px; background: var(--primary-glow); padding: 2px 6px; border-radius: 4px; margin-left: auto;">Confidence: ${ai.confidence}%</span>
      </div>
      <p style="font-size: 13px; margin-bottom: 6px;"><strong>Probable Cause:</strong> ${ai.probable_root_cause}</p>
      <p style="font-size: 13px;"><strong>Suggested Action:</strong> ${ai.suggested_resolution}</p>
    </div>

    <!-- Resolution & Manager Approval Form -->
    <div style="background: var(--bg-input); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; margin-bottom: 20px;">
      <h4 style="margin-bottom: 12px;"><i class="fa-solid fa-check-double"></i> Propose Resolution / Update Status</h4>
      <div style="display: flex; flex-direction: column; gap: 10px;">
        <div>
          <label class="filter-label">Root Cause Analysis:</label>
          <input type="text" class="input-control" id="exc-root-cause-input" value="${e.root_cause || ''}" placeholder="e.g. Bank fee deduction" style="width: 100%;">
        </div>
        <div>
          <label class="filter-label">Resolution Summary:</label>
          <input type="text" class="input-control" id="exc-res-summary-input" value="${e.resolution_summary || ''}" placeholder="e.g. Posted fee adjustment entry" style="width: 100%;">
        </div>
        <div style="display: flex; gap: 10px; margin-top: 6px;">
          <button class="btn btn-primary" onclick="submitExceptionResolution(${e.id}, 'Investigating')">Mark Investigating</button>
          <button class="btn btn-success" onclick="submitExceptionResolution(${e.id}, 'Resolved')"><i class="fa-solid fa-circle-check"></i> Propose / Resolve Exception</button>
        </div>
      </div>
    </div>

    <!-- Audit Timeline Comments -->
    <h4 style="margin-bottom: 12px;"><i class="fa-solid fa-comments"></i> Discussion & Evidence Log</h4>
    <div style="display: flex; flex-direction: column; gap: 10px; max-height: 180px; overflow-y: auto; margin-bottom: 16px;">
      ${comments.length === 0 ? '<p style="color: var(--text-dim); font-size: 12px;">No comments yet.</p>' : comments.map(c => `
        <div style="background: var(--bg-sidebar); border: 1px solid var(--border-color); padding: 10px; border-radius: 6px; font-size: 12px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <strong style="color: var(--primary);">${c.user_name} (${c.user_role})</strong>
            <span style="color: var(--text-dim);">${c.created_at}</span>
          </div>
          <p style="color: var(--text-main);">${c.comment}</p>
        </div>
      `).join('')}
    </div>

    <!-- Add Comment Box -->
    <div style="display: flex; gap: 8px;">
      <input type="text" class="input-control" id="exc-comment-input" placeholder="Type investigation notes or evidence link..." style="flex: 1;">
      <button class="btn btn-secondary" onclick="addCommentToException(${e.id})"><i class="fa-solid fa-paper-plane"></i> Comment</button>
    </div>
  `;

  openModal(`Exception Details: ${e.exception_code}`, bodyHtml);
}

async function submitExceptionResolution(excId, targetStatus) {
  const rootCause = document.getElementById('exc-root-cause-input').value;
  const resSummary = document.getElementById('exc-res-summary-input').value;

  const res = await apiRequest(`/api/exceptions/${excId}/status`, 'PUT', {
    status: targetStatus,
    root_cause: rootCause,
    resolution_summary: resSummary
  });

  if (res) {
    showToast(res.message, 'success');
    closeModal();
    renderExceptionsView();
  }
}

async function addCommentToException(excId) {
  const input = document.getElementById('exc-comment-input');
  const commentText = input.value.trim();
  if (!commentText) return;

  const res = await apiRequest(`/api/exceptions/${excId}/comments`, 'POST', { comment: commentText });
  if (res) {
    showToast('Comment added to exception log', 'success');
    viewExceptionDetail(excId);
  }
}
