/* ==========================================================================
   User Management & RBAC Permissions Matrix View Renderer
   ========================================================================== */

async function renderUsersView() {
  const container = document.getElementById('view-content');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">User & Access Management</h1>
        <p class="page-subtitle">Role-Based Access Control (RBAC) across 7 enterprise roles</p>
      </div>
      <div>
        <button class="btn btn-primary" onclick="openCreateUserModal()"><i class="fa-solid fa-user-plus"></i> Add New User</button>
      </div>
    </div>

    <!-- User Table Card -->
    <div class="table-card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Full Name</th>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Department</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="users-table-body">
            <tr><td colspan="8" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading Users...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

  loadUsersData();
}

async function loadUsersData() {
  const res = await apiRequest('/api/users');
  if (!res) return;

  const tbody = document.getElementById('users-table-body');
  tbody.innerHTML = res.users.map(u => `
    <tr>
      <td>#${u.id}</td>
      <td><strong>${u.full_name}</strong></td>
      <td><code style="color: var(--primary);">${u.username}</code></td>
      <td>${u.email}</td>
      <td><span class="badge" style="background: var(--primary-glow); color: var(--primary); font-weight: 700;">${u.role.toUpperCase()}</span></td>
      <td>${u.department || 'Finance'}</td>
      <td><span class="badge ${u.is_active ? 'badge-matched' : 'badge-unmatched'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
      <td>
        <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="openEditRoleModal(${u.id}, '${u.username}', '${u.role}')">
          <i class="fa-solid fa-user-gear"></i> Change Role
        </button>
      </td>
    </tr>
  `).join('');
}

function openCreateUserModal() {
  const html = `
    <div style="display: flex; flex-direction: column; gap: 12px;">
      <div>
        <label class="filter-label">Full Name:</label>
        <input type="text" class="input-control" id="new-user-fullname" placeholder="e.g. Sarah Connor" style="width: 100%;">
      </div>
      <div>
        <label class="filter-label">Username:</label>
        <input type="text" class="input-control" id="new-user-username" placeholder="e.g. sconnor" style="width: 100%;">
      </div>
      <div>
        <label class="filter-label">Email:</label>
        <input type="email" class="input-control" id="new-user-email" placeholder="e.g. sconnor@reconx.fintech" style="width: 100%;">
      </div>
      <div>
        <label class="filter-label">Password:</label>
        <input type="password" class="input-control" id="new-user-pwd" value="Analyst@123" style="width: 100%;">
      </div>
      <div>
        <label class="filter-label">Role:</label>
        <select class="select-control" id="new-user-role" style="width: 100%;">
          <option value="super_admin">Super Admin</option>
          <option value="finance_admin">Finance Admin</option>
          <option value="finance_manager">Finance Manager</option>
          <option value="reconciliation_analyst" selected>Reconciliation Analyst</option>
          <option value="reviewer">Reviewer</option>
          <option value="auditor">Auditor</option>
          <option value="readonly">Read-only User</option>
        </select>
      </div>
    </div>
  `;

  const footer = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitCreateUser()"><i class="fa-solid fa-check"></i> Create User</button>
  `;

  openModal('Add New System User', html, footer);
}

async function submitCreateUser() {
  const res = await apiRequest('/api/users', 'POST', {
    full_name: document.getElementById('new-user-fullname').value,
    username: document.getElementById('new-user-username').value,
    email: document.getElementById('new-user-email').value,
    password: document.getElementById('new-user-pwd').value,
    role: document.getElementById('new-user-role').value
  });

  if (res) {
    showToast('User created successfully', 'success');
    closeModal();
    renderUsersView();
  }
}

function openEditRoleModal(userId, username, currentRole) {
  const html = `
    <div style="display: flex; flex-direction: column; gap: 12px;">
      <p>Updating permissions for user <strong style="color: var(--primary);">${username}</strong>.</p>
      <div>
        <label class="filter-label">Select New Role:</label>
        <select class="select-control" id="edit-user-role-select" style="width: 100%;">
          <option value="super_admin" ${currentRole === 'super_admin' ? 'selected' : ''}>Super Admin</option>
          <option value="finance_admin" ${currentRole === 'finance_admin' ? 'selected' : ''}>Finance Admin</option>
          <option value="finance_manager" ${currentRole === 'finance_manager' ? 'selected' : ''}>Finance Manager</option>
          <option value="reconciliation_analyst" ${currentRole === 'reconciliation_analyst' ? 'selected' : ''}>Reconciliation Analyst</option>
          <option value="reviewer" ${currentRole === 'reviewer' ? 'selected' : ''}>Reviewer</option>
          <option value="auditor" ${currentRole === 'auditor' ? 'selected' : ''}>Auditor</option>
          <option value="readonly" ${currentRole === 'readonly' ? 'selected' : ''}>Read-only User</option>
        </select>
      </div>
    </div>
  `;

  const footer = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitEditUserRole(${userId})">Save Role</button>
  `;

  openModal('Update User Role', html, footer);
}

async function submitEditUserRole(userId) {
  const newRole = document.getElementById('edit-user-role-select').value;
  const res = await apiRequest(`/api/users/${userId}`, 'PUT', { role: newRole });
  if (res) {
    showToast('User role updated successfully', 'success');
    closeModal();
    renderUsersView();
  }
}
