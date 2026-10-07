// ==========================================================================
// RCS Control Room — Admin & Member Portal JavaScript
// ==========================================================================

let me = null;
let currentData = {};

const configs = {
  members: {
    title: 'Members',
    fields: [
      ['name', 'Name'],
      ['role', 'Role'],
      ['department', 'Department'],
      ['year', 'Year'],
      ['bio', 'Bio'],
      ['image_url', 'Image URL'],
      ['skills', 'Skills (comma separated)'],
      ['featured', 'Featured (1 or 0)']
    ]
  },
  projects: {
    title: 'Projects',
    fields: [
      ['title', 'Title'],
      ['category', 'Category'],
      ['description', 'Description'],
      ['tech', 'Tech Stack (comma separated)'],
      ['status', 'Status (Prototype / In Progress / Active)'],
      ['image_url', 'Image URL'],
      ['demo_url', 'Demo URL']
    ]
  },
  events: {
    title: 'Events',
    fields: [
      ['title', 'Title'],
      ['date', 'Date (YYYY-MM-DD)'],
      ['time', 'Time'],
      ['venue', 'Venue'],
      ['description', 'Description'],
      ['image_url', 'Image URL'],
      ['registration_url', 'Registration URL']
    ]
  },
  learning: {
    title: 'Learning Tracks',
    fields: [
      ['title', 'Title'],
      ['level', 'Level (Beginner / Intermediate / Advanced)'],
      ['category', 'Category'],
      ['description', 'Short Description'],
      ['content', 'Full Lesson Content'],
      ['order_no', 'Display Order (Number)']
    ]
  },
  games: {
    title: 'Games',
    fields: [
      ['title', 'Title'],
      ['topic', 'Topic'],
      ['description', 'Description'],
      ['game_type', 'Game Type (sensor / pid / path)'],
      ['difficulty', 'Difficulty']
    ]
  },
  quizzes: {
    title: 'Quizzes',
    fields: [
      ['title', 'Title'],
      ['topic', 'Topic'],
      ['difficulty', 'Difficulty'],
      ['description', 'Description'],
      ['questions_json', 'Questions JSON (array of {q, options, answer, explain})']
    ]
  }
};

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[c]));
}

async function api(url, opt = {}) {
  const r = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(opt.headers || {}) },
    ...opt
  });
  let j = {};
  try {
    j = await r.json();
  } catch (e) {}
  if (!r.ok) throw new Error(j.error || 'Request failed');
  return j;
}

// Bootstrap authentication check
async function boot() {
  try {
    me = await api('/api/auth/me');
    if (!me || !me.authenticated) {
      showLogin();
      return;
    }

    document.getElementById('loginPanel').classList.add('hidden');
    document.getElementById('dashboardPanel').classList.remove('hidden');

    const dashName = document.getElementById('dashName');
    if (dashName) dashName.textContent = me.name.split(' ')[0];

    const roleChip = document.getElementById('roleChip');
    if (roleChip) roleChip.textContent = (me.role || 'MEMBER').toUpperCase();

    const userBadge = document.getElementById('userBadge');
    if (userBadge) {
      userBadge.innerHTML = `
        <strong style="color:#FFFFFF;display:block">${esc(me.name)}</strong>
        <span style="display:block">${esc(me.email)}</span>
        <span class="pill-chip chip-blue" style="margin-top:6px">${esc(me.role)}</span>
      `;
    }

    showPanel('overview');
  } catch (err) {
    showLogin();
  }
}

function showLogin() {
  document.getElementById('loginPanel').classList.remove('hidden');
  document.getElementById('dashboardPanel').classList.add('hidden');
}

// Login form
document.getElementById('loginForm')?.addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.target;
  const b = Object.fromEntries(new FormData(form));
  const msg = document.getElementById('loginMsg');

  try {
    await api('/api/auth/login', { method: 'POST', body: JSON.stringify(b) });
    if (msg) {
      msg.style.color = 'var(--blue-bright)';
      msg.textContent = 'Authenticated. Loading control room...';
    }
    setTimeout(boot, 400);
  } catch (err) {
    if (msg) {
      msg.style.color = 'var(--red-bright)';
      msg.textContent = err.message || 'Login failed';
    }
  }
});

async function logout() {
  await api('/api/auth/logout', { method: 'POST' });
  location.reload();
}

// Switch between panels and update red active sidebar indicator
function showPanel(id) {
  // Hide all panels
  document.querySelectorAll('#dashboardPanel .admin-tab-panel').forEach(p => p.classList.add('hidden'));

  const target = document.getElementById(id);
  if (target) target.classList.remove('hidden');

  // Update active indicator in sidebar
  document.querySelectorAll('.side-nav-item').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById(`nav-${id}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Load panel content
  if (id === 'overview') {
    loadOverview();
  } else if (id === 'feedback') {
    loadFeedback();
  } else {
    loadResource(id);
  }

  // Close mobile sidebar if open
  document.getElementById('adminSidebar')?.classList.remove('mobile-open');
}

// Toggle mobile sidebar
function toggleAdminSidebar() {
  document.getElementById('adminSidebar')?.classList.toggle('mobile-open');
}

// 1. Overview Panel: dark cards with blue numbers, red quick-action buttons
async function loadOverview() {
  try {
    const all = await api('/api/public/all');
    const metricsContainer = document.getElementById('metrics');
    if (!metricsContainer) return;

    metricsContainer.innerHTML = Object.entries(all)
      .filter(([k]) => ['members', 'projects', 'events', 'learning'].includes(k))
      .map(([k, v]) => `
        <div class="card metric-card">
          <div class="metric-number">${Array.isArray(v) ? v.length : 0}</div>
          <div class="metric-label">${k}</div>
          <button class="btn btn-red btn-pill" style="margin-top:14px;padding:6px 14px;font-size:11px" onclick="showPanel('${k}')">
            Manage &rarr;
          </button>
        </div>
      `).join('');
  } catch (err) {
    console.error('Error loading overview metrics:', err);
  }
}

// 2. Resource Management: dark tables with hover rows, blue edit buttons, red delete buttons
async function loadResource(type) {
  const c = configs[type];
  if (!c) return;

  const data = await api('/api/admin/' + type);
  currentData[type] = data;
  const p = document.getElementById(type);
  if (!p) return;

  p.innerHTML = `
    <div class="panel-header-row">
      <div>
        <p class="section-eyebrow">RESOURCE CONTROLLER</p>
        <h2 class="panel-title">${c.title}</h2>
      </div>
      <button class="btn btn-red btn-pill" onclick="openEditor('${type}')">+ Add New ${c.title.replace(/s$/, '')}</button>
    </div>

    <div class="admin-editor-card hidden" id="${type}Editor"></div>

    <div class="table-wrapper">
      <table class="admin-data-table">
        <thead>
          <tr>
            ${c.fields.slice(0, 4).map(f => `<th>${f[1]}</th>`).join('')}
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${data.map(x => `
            <tr>
              ${c.fields.slice(0, 4).map(f => `<td>${esc(String(x[f[0]] ?? '').slice(0, 80))}</td>`).join('')}
              <td>
                <div class="table-actions">
                  <button class="btn-table-edit" onclick="openEditor('${type}', ${x.id})">Edit</button>
                  <button class="btn-table-delete" onclick="removeItem('${type}', ${x.id})">Delete</button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

// Editor modal form
function openEditor(type, id = null) {
  const c = configs[type];
  const item = id ? currentData[type].find(x => x.id === id) : {};
  const el = document.getElementById(type + 'Editor');
  if (!el) return;

  el.classList.remove('hidden');
  el.innerHTML = `
    <h3 style="font-size:18px;margin-bottom:16px">${id ? 'Edit' : 'Create'} ${c.title.replace(/s$/, '')}</h3>
    <form class="editor-form" onsubmit="event.preventDefault(); saveItem('${type}', ${id || 'null'});">
      <div class="admin-editor-grid">
        ${c.fields.map(([k, l]) => `
          <label class="${['bio', 'description', 'content', 'questions_json'].includes(k) ? 'full' : ''}">
            ${l}
            ${['bio', 'description', 'content', 'questions_json'].includes(k)
              ? `<textarea name="${k}" class="pill-input textarea-pill" rows="${k === 'questions_json' ? 6 : 3}">${esc(item[k] ?? '')}</textarea>`
              : `<input name="${k}" class="pill-input" value="${esc(item[k] ?? '')}">`
            }
          </label>
        `).join('')}
      </div>
      <div class="admin-editor-actions">
        <button type="submit" class="btn btn-red btn-pill">Save Changes</button>
        <button type="button" class="btn btn-ghost" onclick="document.getElementById('${type}Editor').classList.add('hidden')">Cancel</button>
      </div>
    </form>
  `;
}

async function saveItem(type, id) {
  const el = document.getElementById(type + 'Editor');
  const form = el.querySelector('.editor-form');
  const b = Object.fromEntries(new FormData(form));

  if (id) {
    await api(`/api/admin/${type}/${id}`, { method: 'PUT', body: JSON.stringify(b) });
  } else {
    await api(`/api/admin/${type}`, { method: 'POST', body: JSON.stringify(b) });
  }

  loadResource(type);
}

async function removeItem(type, id) {
  if (!confirm(`Are you sure you want to delete this ${type.replace(/s$/, '')}?`)) return;
  await api(`/api/admin/${type}/${id}`, { method: 'DELETE' });
  loadResource(type);
}

// 3. Feedback Signals: Status Badges RED = 'new', BLUE = 'reviewed' (NO green or gray allowed)
async function loadFeedback() {
  const data = await api('/api/admin/feedback');
  const p = document.getElementById('feedback');
  if (!p) return;

  p.innerHTML = `
    <div class="panel-header-row">
      <div>
        <p class="section-eyebrow">COMMUNITY INPUT</p>
        <h2 class="panel-title">Feedback &amp; Idea Signals</h2>
      </div>
    </div>
    
    <div style="display:grid;gap:14px">
      ${data.length ? data.map(x => {
        const isNew = (x.status || 'new') === 'new';
        const badgeClass = isNew ? 'badge-red' : 'badge-blue';
        const statusText = isNew ? 'NEW' : 'REVIEWED';

        return `
          <article class="card feedback-admin-card">
            <div class="feedback-head">
              <span class="status-badge ${badgeClass}">${statusText}</span>
              <small class="feedback-meta">${esc(x.created_at || '')}</small>
            </div>
            <h3 style="font-size:18px">${esc(x.title || x.type || 'Idea Proposal')}</h3>
            <div class="feedback-meta">
              <strong>${esc(x.name || 'Anonymous')}</strong> &bull; ${esc(x.email || 'No email provided')} &bull; Category: <span class="pill-chip chip-blue">${esc(x.type || 'idea')}</span>
            </div>
            <p style="color:var(--text);font-size:14px;line-height:1.6;background:var(--surface-2);padding:14px;border-radius:10px;border:1px solid var(--border-subtle)">
              ${esc(x.message)}
            </p>
            <div style="display:flex;gap:10px;margin-top:6px">
              ${isNew ? `
                <button class="btn btn-blue btn-pill" style="padding:6px 16px;font-size:12px" onclick="markFeedback(${x.id}, 'reviewed')">
                  Mark Reviewed
                </button>
              ` : `
                <button class="btn btn-red btn-pill" style="padding:6px 16px;font-size:12px" onclick="markFeedback(${x.id}, 'new')">
                  Mark as New
                </button>
              `}
            </div>
          </article>
        `;
      }).join('') : `
        <div class="card" style="padding:30px;text-align:center;color:var(--text-muted)">
          No feedback entries received yet.
        </div>
      `}
    </div>
  `;
}

async function markFeedback(id, newStatus = 'reviewed') {
  await api(`/api/admin/feedback/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ status: newStatus })
  });
  loadFeedback();
}

// Initialize admin boot
boot();

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}
