/* ==========================================================================
   ReconX Frontend App Core State & API Client
   ========================================================================== */

const state = {
  token: localStorage.getItem('reconx_jwt') || '',
  currentUser: JSON.parse(localStorage.getItem('reconx_user') || 'null'),
  currentView: 'dashboard',
  theme: localStorage.getItem('reconx_theme') || 'dark'
};

// Apply Theme
document.documentElement.setAttribute('data-theme', state.theme);

// API Client Helper
async function apiRequest(endpoint, method = 'GET', data = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  const opts = { method, headers };
  if (data && (method === 'POST' || method === 'PUT')) {
    opts.body = JSON.stringify(data);
  }

  try {
    const res = await fetch(endpoint, opts);
    if (res.status === 401 && !endpoint.includes('/auth/login')) {
      showToast('Session expired. Please log in.', 'error');
      logoutUser();
      return null;
    }
    const json = await res.json();
    if (!res.ok) {
      throw new Error(json.error || 'API Request Failed');
    }
    return json;
  } catch (err) {
    showToast(err.message, 'error');
    console.error('API Error:', err);
    return null;
  }
}

// Toast System
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const iconMap = {
    success: 'fa-circle-check',
    error: 'fa-circle-xmark',
    info: 'fa-circle-info'
  };
  
  toast.innerHTML = `<i class="fa-solid ${iconMap[type] || 'fa-info'}"></i> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 200);
  }, 4000);
}

// Modal Handlers
function openModal(title, contentHtml, footerHtml = '') {
  document.getElementById('modal-title').innerText = title;
  document.getElementById('modal-body-content').innerHTML = contentHtml;
  if (footerHtml) {
    document.getElementById('modal-footer-actions').innerHTML = footerHtml;
  }
  document.getElementById('app-modal').classList.add('active');
}

function closeModal() {
  document.getElementById('app-modal').classList.remove('active');
}

// Auth Helpers
function waitForFirebaseAuth() {
  return new Promise((resolve) => {
    if (window.firebaseAuth) {
      resolve(window.firebaseAuth);
    } else {
      const interval = setInterval(() => {
        if (window.firebaseAuth) {
          clearInterval(interval);
          resolve(window.firebaseAuth);
        }
      }, 50);
    }
  });
}

async function autoLoginAsAdmin() {
  const firebaseAuth = await waitForFirebaseAuth();
  
  return new Promise((resolve) => {
    let resolved = false;
    firebaseAuth.onStateChange(async (user) => {
      if (user) {
        // User is signed in with Firebase
        const token = await firebaseAuth.getToken();
        state.token = token;
        // In a real app, you might fetch user details from Firestore here
        state.currentUser = { full_name: user.email, role: 'super_admin', username: user.email };
        localStorage.setItem('reconx_jwt', state.token);
        localStorage.setItem('reconx_user', JSON.stringify(state.currentUser));
        updateUserProfileDisplay();
        closeModal();
        
        if (!resolved) {
          resolved = true;
          resolve();
        } else {
          navigateTo(state.currentView || 'dashboard');
        }
      } else {
        // User is signed out, show Firebase login modal
        state.token = '';
        state.currentUser = null;
        showLoginModal();
        // Don't resolve until user logs in
      }
    });
  });
}

function showLoginModal() {
  const content = `
    <div style="padding: 20px; display: flex; flex-direction: column; gap: 15px;">
      <p style="color: var(--text-muted); font-size: 14px;">Sign in with your Firebase account.</p>
      <input type="email" id="fb-email" class="input-control" placeholder="Email" style="width: 100%; padding: 10px;">
      <input type="password" id="fb-password" class="input-control" placeholder="Password" style="width: 100%; padding: 10px;">
      <div id="login-error" style="color: var(--danger); font-size: 12px; display: none;"></div>
      <button class="btn btn-primary" onclick="handleFirebaseLogin()" style="width: 100%; justify-content: center;">Sign In / Register</button>
    </div>
  `;
  openModal('Authentication Required', content);
  
  // Prevent closing the modal by clicking outside or the X if not logged in
  const closeBtn = document.querySelector('.modal-header .btn-icon');
  if (closeBtn) closeBtn.style.display = 'none';
  const footerBtn = document.getElementById('modal-footer-actions');
  if (footerBtn) footerBtn.innerHTML = '';
}

window.handleFirebaseLogin = async () => {
  const email = document.getElementById('fb-email').value;
  const password = document.getElementById('fb-password').value;
  const errorDiv = document.getElementById('login-error');
  
  if (!email || !password) {
    errorDiv.innerText = "Please enter email and password.";
    errorDiv.style.display = 'block';
    return;
  }
  
  errorDiv.style.display = 'none';
  const firebaseAuth = window.firebaseAuth;
  
  // Try login first
  let { user, error } = await firebaseAuth.login(email, password);
  
  // If user not found or invalid credential, try register (for convenience in this demo)
  if (error) {
     console.log("Login failed, attempting register. Error was:", error);
     const regResult = await firebaseAuth.register(email, password);
     user = regResult.user;
     error = regResult.error;
  }
  
  if (error) {
    console.error("Firebase Auth Error:", error);
    errorDiv.innerText = "Error: " + error;
    errorDiv.style.display = 'block';
  } else {
    showToast('Signed in successfully', 'success');
  }
};

function updateUserProfileDisplay() {
  if (state.currentUser) {
    document.getElementById('topbar-user-fullname').innerText = state.currentUser.full_name || state.currentUser.username;
    document.getElementById('topbar-user-role').innerText = (state.currentUser.role || 'USER').replace('_', ' ').toUpperCase();
    
    const initials = (state.currentUser.full_name || 'Admin').split(' ').map(n => n[0]).join('').substring(0, 2);
    document.getElementById('user-avatar-initials').innerText = initials;
  }
}

async function logoutUser() {
  localStorage.removeItem('reconx_jwt');
  localStorage.removeItem('reconx_user');
  state.token = '';
  state.currentUser = null;
  if (window.firebaseAuth) {
    await window.firebaseAuth.logout();
  }
  location.reload();
}

// Navigation & SPA Router
function navigateTo(viewName) {
  state.currentView = viewName;
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.getAttribute('data-view') === viewName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  const renderers = {
    dashboard: renderDashboardView,
    transactions: renderTransactionsView,
    ingestion: renderIngestionView,
    reconciliation: renderReconciliationView,
    exceptions: renderExceptionsView,
    rules: renderRulesView,
    reports: renderReportsView,
    audit: renderAuditView,
    users: renderUsersView,
    settings: renderSettingsView
  };

  const renderer = renderers[viewName] || renderDashboardView;
  renderer();
}

// Init Event Listeners
document.addEventListener('DOMContentLoaded', async () => {
  await autoLoginAsAdmin();
  
  // Nav Click Listeners
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const view = item.getAttribute('data-view');
      navigateTo(view);
    });
  });

  // Logout Button
  document.getElementById('btn-logout').addEventListener('click', logoutUser);

  // Theme Toggle
  document.getElementById('theme-toggle').addEventListener('click', () => {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', state.theme);
    localStorage.setItem('reconx_theme', state.theme);
  });

  // Initial View Load
  navigateTo('dashboard');
});

